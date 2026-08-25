import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/EventsAndAnalytics.tsx", "r") as f:
    content = f.read()

old_code = "setTimelineData(chartData.length > 0 ? chartData : [{ time: '—', detections: 0 }])"
new_code = "setTimelineData(chartData.length > 0 ? chartData : [{ time: '—', detections: 0 }].map(obj => ({...obj})))"

content = content.replace(old_code, new_code)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/EventsAndAnalytics.tsx", "w") as f:
    f.write(content)
