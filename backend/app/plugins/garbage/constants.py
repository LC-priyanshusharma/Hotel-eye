# COCO Dataset generally doesn't have "garbage" specific classes, 
# but for demonstration we'll map a few classes that could represent waste.
# Real implementation would use a custom trained YOLO model with specific indices.

# Let's say our custom YOLO garbage model uses these classes:
GARBAGE_CLASS_IDS = [0, 1, 2, 3, 4, 5, 6, 7] # Mapping to the 8 categories

GARBAGE_CLASS_NAMES = {
    0: "plastic bottle",
    1: "paper",
    2: "cup",
    3: "bag",
    4: "wrapper",
    5: "can",
    6: "garbage pile",
    7: "other waste"
}
