from djitellopy import tello
from ultralytics import YOLO
import cv2
import time

#model = YOLO("final.pt")
model = YOLO("best.pt")

drone = tello.Tello()

print("Connecting to drone...")
drone.connect()

battery = drone.get_battery()
print(f"Battery: {battery}%")

# Optional safety check
if battery < 20:
    raise Exception("Battery too low for flight")

drone.streamon()

frame_reader = drone.get_frame_read()

# Give camera time to start
time.sleep(10)

# drone.takeoff()
# drone.move_up(50)

print("Starting crack detection...")

try:
    while True:

        # Get current frame from drone
        frame = frame_reader.frame
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        if frame is None:
            continue

        results = model(frame)

        annotated_frame = results[0].plot()

        boxes = results[0].boxes

        for box in boxes:

            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])

            class_name = model.names[cls_id]

            print(
                f"Detected: {class_name} "
                f"Confidence: {confidence:.2f}"
            )
        cv2.imshow("Tello Crack Detection", annotated_frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

except KeyboardInterrupt:
    print("Stopping...")

finally:
    try:
        # drone.land()
        pass
    except:
        pass

    drone.streamoff()
    drone.end()

    cv2.destroyAllWindows()

    print("Program ended cleanly.")