with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/EventsAndAnalytics.tsx", "r") as f:
    content = f.read()

content = content.replace("setData((prev: any) => ({ ...prev, system_health: h }));", "setData((prev: any) => prev ? ({ ...prev, system_health: h }) : null);")

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/EventsAndAnalytics.tsx", "w") as f:
    f.write(content)
