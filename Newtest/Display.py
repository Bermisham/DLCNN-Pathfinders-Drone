from djitellopy import tello
import cv2

drone = tello.Tello()
drone.connect()
drone.streamon()

bat = drone.get_battery()
print(bat)

drone.takeoff()
print("Moving Down")
drone.move_down(40)
print("Moved Down")

while True:
    frame = drone.get_frame_read().frame
    img = cv2.resize(frame, (360, 240))
    cv2.imshow("Image", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

drone.land()
drone.streamoff()
cv2.destroyAllWindows()