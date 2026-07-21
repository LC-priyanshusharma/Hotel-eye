import os
import re

backend_dir = "backend"
frontend_dir = "frontend"

python_replacements = {
    r"from ai\.detector": "from detection.detector",
    r"import ai\.detector": "import detection.detector",
    r"from ai\.analytics": "from analytics.analytics",
    r"import ai\.analytics": "import analytics.analytics",
    r"from core\.config": "from config.config",
    r"import core\.config": "import config.config",
    r"from core\.stream_reader": "from camera.stream_reader",
    r"import core\.stream_reader": "import camera.stream_reader",
    r"from core\.persistence": "from database.persistence",
    r"import core\.persistence": "import database.persistence",
    r"from db\.models": "from models.models",
    r"import db\.models": "import models.models",
    r"from db\.session": "from database.session",
    r"import db\.session": "import database.session",
    r"from modules\.gesture": "from tracking.gesture",
    r"import modules\.gesture": "import tracking.gesture",
    r'default="yolo11n.pt"': 'default="detection/yolo11n.pt"',
}

ts_replacements = {
    r"components/layout/": "layouts/",
    r"lib/utils": "utils/utils",
}

for root, _, files in os.walk(backend_dir):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            with open(path, "r") as file:
                content = file.read()
            original_content = content
            for old, new in python_replacements.items():
                content = re.sub(old, new, content)
            if content != original_content:
                with open(path, "w") as file:
                    file.write(content)
                print(f"Updated {path}")

for root, _, files in os.walk(frontend_dir):
    for f in files:
        if f.endswith((".ts", ".tsx", ".js", ".jsx")):
            path = os.path.join(root, f)
            with open(path, "r") as file:
                content = file.read()
            original_content = content
            for old, new in ts_replacements.items():
                content = re.sub(old, new, content)
            if content != original_content:
                with open(path, "w") as file:
                    file.write(content)
                print(f"Updated {path}")
                
# update vite.config.ts if it has any lib alias
vite_config = "frontend/vite.config.ts"
if os.path.exists(vite_config):
    with open(vite_config, "r") as file:
        content = file.read()
    original_content = content
    content = content.replace("src/lib", "src/utils")
    if content != original_content:
        with open(vite_config, "w") as file:
            file.write(content)
        print(f"Updated {vite_config} aliases")

# update docker-compose.yml
dc_path = "docker-compose.yml"
if os.path.exists(dc_path):
    with open(dc_path, "r") as file:
        content = file.read()
    original_content = content
    content = content.replace("context: ./LC-VISION--CN", "context: ./backend")
    if content != original_content:
        with open(dc_path, "w") as file:
            file.write(content)
        print(f"Updated {dc_path}")

