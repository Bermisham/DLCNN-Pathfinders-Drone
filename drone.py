from djitellopy import tello
from ultralytics import YOLO
import cv2
import time
import threading
import os

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
    

def get_drone_temp(drone) -> float:
    try:
        return drone.get_temperature()
    except:
        return None
    

_lock = threading.Lock()
_current_frame: bytes | None = None
_stream_active = False


def _detection_loop(drone, model, save_dir):
    global _current_frame, _stream_active
    frame_reader = drone.get_frame_read()

    img_count = 0
    writer = None

    try:
        while _stream_active:
            frame = frame_reader.frame
            if frame is None:
                time.sleep(0.01)
                continue

            results = model(frame, verbose=False)
            annotated = results[0].plot()

            # Initialise video writer on first frame so size is known
            if writer is None:
                h, w = annotated.shape[:2]
                video_path = os.path.join(save_dir, "recording.mp4")
                writer = cv2.VideoWriter(
                    video_path,
                    cv2.VideoWriter_fourcc(*'avc1'),
                    30,
                    (w, h),
                )
                print(f"Recording to {video_path}")

            writer.write(annotated)

            _, jpeg = cv2.imencode('.jpg', annotated)
            with _lock:
                _current_frame = jpeg.tobytes()

            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0])
                print(f"Detected: {model.names[cls_id]} Confidence: {confidence:.2f}")

                filename = os.path.join(save_dir, f"img{img_count}.jpg")
                cv2.imwrite(filename, annotated)
                print(f"Saved: {filename}")
                img_count += 1
    finally:
        if writer is not None:
            writer.release()
            print("Recording saved.")


def start_stream(drone):
    global _stream_active, _current_frame
    model = YOLO("best.pt")

    trip_num = int(time.time())
    save_dir = f"droneimages/trip{trip_num}"
    os.makedirs(save_dir, exist_ok=True)

    print("Turn on stream")
    drone.streamon()
    time.sleep(5)

    print("Start takeoff")
    drone.takeoff()
    drone.move_down(20)

    _current_frame = None
    _stream_active = True
    threading.Thread(target=_detection_loop, args=(drone, model, save_dir), daemon=True).start()
    print("Detection stream started.")


def stop_stream(drone):
    global _stream_active
    _stream_active = False
    time.sleep(0.5)
    try:
        drone.land()
        drone.streamoff()
        drone.end()
    except Exception as e:
        print(f"Stop error: {e}")
    print("Detection stream stopped.")


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