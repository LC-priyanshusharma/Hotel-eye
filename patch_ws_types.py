with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/contexts/WebSocketContext.tsx", "r") as f:
    content = f.read()

content = content.replace("let reconnectTimeout: NodeJS.Timeout;", "let reconnectTimeout: ReturnType<typeof setTimeout>;")
content = content.replace("let keepAliveInterval: NodeJS.Timeout;", "let keepAliveInterval: ReturnType<typeof setInterval>;")

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/contexts/WebSocketContext.tsx", "w") as f:
    f.write(content)
