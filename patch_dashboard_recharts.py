import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/Dashboard/index.tsx", "r") as f:
    content = f.read()

# Replace the inline array
old_code = "data={telemetryHistory.current.length > 0 ? telemetryHistory.current : [{ time: '—', load: 0, ram: 0 }]}"
new_code = "data={telemetryHistory.current.length > 0 ? telemetryHistory.current : [{ time: '—', load: 0, ram: 0 }].map(obj => ({...obj}))}"

content = content.replace(old_code, new_code)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/Dashboard/index.tsx", "w") as f:
    f.write(content)
