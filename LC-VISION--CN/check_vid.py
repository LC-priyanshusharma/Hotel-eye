import cv2
from ultralytics import YOLO

model = YOLO("yolo11n.pt")
cap = cv2.VideoCapture("Screen Recording 2026-07-17 at 11.26.10 AM.mov")
detected_classes = set()

frame_count = 0
while cap.isOpened() and frame_count < 300: # check first 300 frames
    ret, frame = cap.read()
    if not ret: break
    
    results = model(frame, verbose=False, conf=0.1)
    for r in results:
        for c in r.boxes.cls:
            detected_classes.add(int(c))
    frame_count += 1

print("Detected classes:", detected_classes)
for c in detected_classes:
    print(f"{c}: {model.names[c]}")
cap.release()
