import sys

file_path = "/Users/ibm/Downloads/LogicEye-main-main-2/backend/app/plugins/counting/plugin.py"

with open(file_path, "r") as f:
    content = f.read()

content = content.replace("events = []\n        \n        state = tracker_context.get_state", "events = []\n        logger.debug(f\"PeopleCountingPlugin running for {camera_id} with {len(frame_data.detections)} detections\")\n        state = tracker_context.get_state")

with open(file_path, "w") as f:
    f.write(content)
