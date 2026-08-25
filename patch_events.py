with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/EventsAndAnalytics.tsx", "r") as f:
    content = f.read()

# Add useWebSocket to Events component
if "const { telemetry } = useWebSocket()" not in content.split("export function Events(")[1]:
    content = content.replace("export function Events({ filter = 'All Events' }: { filter?: string }) {\n  const [events", "export function Events({ filter = 'All Events' }: { filter?: string }) {\n  const { telemetry } = useWebSocket()\n  const [events")

# Fix filter.camera
content = content.replace("if (filter.camera) queryParams.append('camera_id', filter.camera)\n                if (filter.severity) queryParams.append('severity', filter.severity)\n                if (filter.category) queryParams.append('category', filter.category)", "")

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/EventsAndAnalytics.tsx", "w") as f:
    f.write(content)
