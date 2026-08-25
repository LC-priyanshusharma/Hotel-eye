import re

with open("/home/user/LogicEye-main/start.sh", "r") as f:
    content = f.read()

# Add Model Download step
old_launch = """# 5. Launch Services
echo "5/6 Launching Platform Services...\""""

new_launch = """# 4.5 Download ANPR Models if missing
echo "4.5/6 Checking ANPR Models..."
cd "$DIR/backend"
if [ ! -f "indian_plate_yolo.pt" ]; then
    echo "Downloading License Plate YOLOv8 Model..."
    wget -qO indian_plate_yolo.pt "https://huggingface.co/keremberke/yolov8m-license-plate/resolve/main/best.pt" || echo "Warning: Failed to download model"
fi
cd "$DIR"

# 5. Launch Services
echo "5/6 Launching Platform Services...\""""

content = content.replace(old_launch, new_launch)

with open("/home/user/LogicEye-main/start.sh", "w") as f:
    f.write(content)
