import os
target_dir = "/Users/ibm/Downloads/LogicEye-main/frontend/src"
for root, _, files in os.walk(target_dir):
    for file in files:
        if file.endswith(('.tsx', '.ts')):
            path = os.path.join(root, file)
            with open(path, 'r') as f:
                content = f.read()
            if 'http://localhost:8000' in content:
                content = content.replace('http://localhost:8000', '')
                with open(path, 'w') as f:
                    f.write(content)
