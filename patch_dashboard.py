with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/Dashboard/index.tsx", "r") as f:
    content = f.read()

if "import { useWebSocket }" not in content:
    content = "import { useWebSocket } from '@/contexts/WebSocketContext'\n" + content

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/Dashboard/index.tsx", "w") as f:
    f.write(content)
