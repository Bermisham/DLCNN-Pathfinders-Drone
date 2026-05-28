from djitellopy import tello
from ultralytics import YOLO
import cv2
import time
import threading
import os
from datetime import datetime

def connect_drone() -> tello.Tello:
    drone = tello.Tello()
    drone.RETRY_COUNT = 1
    try:
        drone.connect()
        return drone
    except Exception:
        return None


def check_drone_connection(drone) -> bool:
    try:
        drone.get_battery()
        return True
    except:
        return False
    

def get_drone_battery(drone) -> int:
    try:
        return drone.get_battery()
    except:
        return None


def get_drone_serial_number(drone) -> str:
    try:
        return drone.query_serial_number()
    except:
        return None


def get_drone_SNR(drone) -> str:
    try:
        return drone.query_wifi_signal_noise_ratio()
    except:
        return None
    

def get_drone_temp(drone) -> int:
    try:
        f = drone.get_temperature()
        c = (f - 32) * 5.0/9.0
        return int(c)
    except:
        return None
    

_lock = threading.Lock()
_current_frame: bytes | None = None
_stream_active = False
_detection_thread: threading.Thread | None = None
_completed_naturally = False  # True when path finishes on its own; False if stopped early

_RECORD_FPS = 10



def generate_frames():
    while True:
        with _lock:
            frame = _current_frame
        if frame is None:
            time.sleep(0.05)
            continue
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
        )
        time.sleep(0.033)


# ---------------------------------------------------------------------------
# Path-based trip execution
# ---------------------------------------------------------------------------

# A step is a (direction, distance_cm) pair.
# Valid directions: "forward" | "back" | "left" | "right"
TripPath = list[tuple[str, int]]


def move_and_detect(
    drone,
    frame_reader,
    model,
    writer,
    direction: str,
    distance: int,
    x: float,
    y: float,
    save_dir: str,
    img_count: int,
    dwell_time: float = 3.0,
) -> tuple[dict, float, float, int]:
    global _current_frame

    # Update tracked position
    if direction == "forward":
        y += distance
    elif direction == "back":
        y -= distance
    elif direction == "right":
        x += distance
    elif direction == "left":
        x -= distance

    print(f"Moving {direction} {distance} cm  →  position ({x}, {y})")
    drone.move(direction, distance)

    detections = {}
    start_time = time.time()

    while time.time() - start_time < dwell_time:
        if not _stream_active:
            break

        frame = frame_reader.frame
        if frame is None:
            time.sleep(0.01)
            continue

        results = model(frame, verbose=False)
        annotated = results[0].plot()

        # Write annotated frame to the trip recording
        if writer is not None and writer.isOpened():
            writer.write(annotated)

        # Push latest frame to the live feed
        _, jpeg = cv2.imencode('.jpg', annotated)
        with _lock:
            _current_frame = jpeg.tobytes()

        for box in results[0].boxes:
            cls_id     = int(box.cls[0])
            confidence = float(box.conf[0])
            class_name = model.names[cls_id]

            filename = os.path.join(save_dir, f"img{img_count}.jpg")
            cv2.imwrite(filename, annotated)
            print(f"  Detected {class_name} ({confidence:.2f}) → {filename}")

            key = f"hazard{img_count}"
            detections[key] = {
                "class":         class_name,
                "confidence":    round(confidence, 2),
                "position":      {"x": x, "y": y},
                "time_detected": datetime.now().isoformat(),
                "image_path":    filename,
            }
            img_count += 1

    return detections, x, y, img_count


def _land_drone(drone):
    """Land and shut down the drone. Safe to call from any thread."""
    try:
        drone.land()
        drone.streamoff()
        drone.end()
    except Exception as e:
        print(f"Landing error: {e}")


def _trip_loop(drone, path: TripPath, save_dir: str, on_complete=None):
    global _stream_active, _completed_naturally

    model = YOLO("final.pt")
    frame_reader = drone.get_frame_read()
    writer = None
    x, y = 0.0, 0.0
    img_count = 0
    all_detections: dict = {}
    video_path: str | None = None

    try:
        for step_num, (direction, distance) in enumerate(path, start=1):
            if not _stream_active:
                print("Trip aborted by stop signal.")
                break

            print(f"\n── Step {step_num}/{len(path)}: {direction} {distance} cm")

            if writer is None:
                frame = frame_reader.frame
                if frame is not None:
                    h, w       = frame.shape[:2]
                    video_path = os.path.join(save_dir, "recording.mp4")
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    writer = cv2.VideoWriter(video_path, fourcc, _RECORD_FPS, (w, h))
                    if not writer.isOpened():
                        print("Warning: mp4v unavailable, trying avc1")
                        fourcc = cv2.VideoWriter_fourcc(*'avc1')
                        writer = cv2.VideoWriter(video_path, fourcc, _RECORD_FPS, (w, h))
                    print(f"Recording to {video_path}")

            try:
                step_detections, x, y, img_count = move_and_detect(
                    drone, frame_reader, model, writer,
                    direction, distance,
                    x, y,
                    save_dir, img_count,
                )
            except Exception as e:
                print(f"  Move error on step {step_num} ({direction} {distance} cm): {e}")
                print("  Aborting trip early.")
                break

            all_detections.update(step_detections)

        else:
            _completed_naturally = True
            print("All waypoints complete.")

    finally:
        if writer is not None:
            writer.release()
            print("Recording saved.")

        outcome = "complete" if _completed_naturally else "stopped early"
        print(f"\nTrip {outcome} — {len(all_detections)} hazard(s) detected.")

        if on_complete:
            on_complete(all_detections, video_path)

        if _stream_active:
            _land_drone(drone)


def start_stream(drone, path: TripPath, on_complete=None):
    global _stream_active, _current_frame, _detection_thread, _completed_naturally

    _completed_naturally = False  # reset for new trip

    trip_num = int(time.time())
    save_dir = f"droneimages/trip{trip_num}"
    os.makedirs(save_dir, exist_ok=True)

    print("Turning on video stream")
    drone.streamon()
    time.sleep(5)

    print("Taking off")
    drone.takeoff()
    try:
        drone.move_down(40)
    except Exception as e:
        print(f"Warning: move_down failed ({e}), continuing at takeoff height")

    _current_frame = None
    _stream_active = True
    _detection_thread = threading.Thread(
        target=_trip_loop, args=(drone, path, save_dir, on_complete), daemon=True
    )
    _detection_thread.start()
    print(f"Trip started — {len(path)} step(s) in path.")


def stop_stream(drone):
    """Interrupt the trip, wait for the recording to flush, then land.

    Safe to call even after natural completion — _completed_naturally prevents
    a double land.
    """
    global _stream_active, _detection_thread, _completed_naturally

    _stream_active = False

    if _detection_thread is not None:
        _detection_thread.join(timeout=15)
        _detection_thread = None

    _land_drone(drone)

    _completed_naturally = False 
    print("Trip stopped.")