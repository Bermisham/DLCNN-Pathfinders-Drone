import cv2
from flask import Flask, render_template, jsonify, Response
import threading
import time
import math
from djitellopy import tello
import base64



app = Flask(__name__)

# --- Drone (comment out when testing without drone) ---
"""drone = tello.Tello()
drone.connect()
drone.streamon()"""

from sympy import true
import torch
from ultralytics import YOLO
model = YOLO("final.pt")

# --- State ---
position = {"x": 250, "y": 250, "heading": 0}  # start in centre of map
path = [{"x": 250, "y": 250}]
cracks = []
crack_id_counter = 0
state_lock = threading.Lock()


def move(direction, distance=50):
    """Update dead reckoning position after a move command."""
    global position
    step = distance / 10  # scale to map pixels
    rad = math.radians(position["heading"])

    if direction == "forward":
        position["x"] += step * math.sin(rad)
        position["y"] -= step * math.cos(rad)
        #drone.move_forward(50)
    elif direction == "back":
        position["x"] -= step * math.sin(rad)
        position["y"] += step * math.cos(rad)
        #drone.move_back(50)
    elif direction == "left":
        position["x"] -= step * math.cos(rad)
        position["y"] -= step * math.sin(rad)
        #drone.move_left(50)
    elif direction == "right":
        position["x"] += step * math.cos(rad)
        position["y"] += step * math.sin(rad)
        #drone.move_right(50)

    position["x"] = max(0, min(500, position["x"]))
    position["y"] = max(0, min(500, position["y"]))
    path.append({"x": position["x"], "y": position["y"]})


def run_crack_detection():
    global crack_id_counter
    while True:
        #frame = drone.get_frame_read().frame
        #frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_path = "pothole.png"

        frame = cv2.imread(image_path)
        if frame is None:
            return
        results = model(frame)

        annotated_image = results[0].plot()
        """_, buffer = cv2.imencode('.jpg', annotated_image)
        image_b64 = base64.b64encode(buffer).decode('utf-8')"""

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
                "x": position["x"],
                "y": position["y"],
                "box": box.xyxy[0].tolist(),
                "confidence": round(confidence, 2),
                "class": class_name,
                #"image": image_b64
            })
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
                break
        



# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/takeoff", methods=["POST"])
def takeoff():
    #drone.takeoff()
    return jsonify({"message": "Taking off!"})


@app.route("/land", methods=["POST"])
def land():
    """drone.land()
    drone.end()"""
    #drone.streamoff()
    #drone.end()

    cv2.destroyAllWindows()
    return jsonify({"message": "Landed!"})

@app.route("/battery", methods=["POST"])
def battery():
    level = 85  # dummy value for testing
    #evel = drone.get_battery()
    return jsonify({"message": f"Battery: {level}%"})

@app.route("/modeltest", methods=["POST"])
def modeltest():
    run_crack_detection()
    return jsonify({"message": "Model test completed!"})


@app.route("/move/<direction>", methods=["POST"])
def move_drone(direction):
    with state_lock:
        move(direction)
        #run_crack_detection()
    return jsonify({"message": f"Moved {direction}"})


@app.route("/state", methods=["GET"])
def get_state():
    with state_lock:
        return jsonify({
            "position": position,
            "path": path,
            "cracks": cracks
        })


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5004, debug=True, use_reloader=False)
