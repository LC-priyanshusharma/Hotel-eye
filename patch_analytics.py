with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/EventsAndAnalytics.tsx", "r") as f:
    content = f.read()

content = content.replace("export function Analytics() {\n  const [data", "export function Analytics() {\n  const { telemetry } = useWebSocket()\n  const [data")

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/EventsAndAnalytics.tsx", "w") as f:
    f.write(content)
