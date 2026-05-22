

from ultralytics import YOLO
import cv2
import numpy as np

# -----------------------------
# Load trained model
# -----------------------------
model = YOLO("best.pt")

# -----------------------------
# Load image
# -----------------------------
image_path = "pothole.png"

image = cv2.imread(image_path)

if image is None:
    raise Exception(f"Could not load image: {image_path}")

results = model(image)

annotated_image = results[0].plot()

boxes = results[0].boxes

if len(boxes) == 0:
    print("No cracks detected")

for box in boxes:

    cls_id = int(box.cls[0])
    confidence = float(box.conf[0])

    class_name = model.names[cls_id]

    print(
        f"Detected: {class_name} "
        f"Confidence: {confidence:.2f}"
    )

cv2.imshow("Detection Results", annotated_image)

cv2.waitKey(0)
cv2.destroyAllWindows()

output_path = "output.jpg"

cv2.imwrite(output_path, annotated_image)

print(f"Saved result to: {output_path}")