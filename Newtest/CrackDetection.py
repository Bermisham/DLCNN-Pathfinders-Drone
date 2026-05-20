import cv2
from djitellopy import tello
from ultralytics import YOLO


position = {"x": 250, "y": 250, "heading": 0}  # start in centre of map
model = YOLO("final.pt")

drone = tello.Tello()
drone.connect()
drone.streamon()

cracks = []
crack_id_counter = 0

def run_crack_detection():
    global crack_id_counter
    try:
        while True:
            frame = drone.get_frame_read().frame
            if frame is None:
                continue

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = model(frame)

            annotated_image = results[0].plot()
            boxes = results[0].boxes
            print(f"Detected {len(boxes)} cracks")
            cv2.imshow("Frame", annotated_image)

            if len(boxes) == 0:
                print("No cracks detected")

            for box in boxes:
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0])
                class_name = model.names[cls_id]
                crack_id_counter += 1
                cracks.append({
                    "id": crack_id_counter,
                    "x": position["x"],  # TODO: update position from drone telemetry
                    "y": position["y"],
                    "box": box.xyxy[0].tolist(),
                    "confidence": round(confidence, 2),
                    "class": class_name,
                })

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print(cracks)
                break
    finally:
        drone.streamoff()
        cv2.destroyAllWindows()


run_crack_detection()