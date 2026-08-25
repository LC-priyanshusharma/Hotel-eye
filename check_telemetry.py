import os

def check_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    if 'telemetry' in content and 'useWebSocket' not in content:
        print(f"Missing useWebSocket in {filepath}")

for root, _, files in os.walk('/home/user/LogicEye-main/frontend/src'):
    for f in files:
        if f.endswith('.tsx') or f.endswith('.ts'):
            check_file(os.path.join(root, f))
