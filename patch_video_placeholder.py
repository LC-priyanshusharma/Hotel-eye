with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/components/camera/VideoPlaceholder.tsx", "r") as f:
    content = f.read()

content = content.replace("object-contain", "object-cover")

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/components/camera/VideoPlaceholder.tsx", "w") as f:
    f.write(content)
