import os

file_path = "/home/user/LogicEye-main/frontend/src/pages/Dashboard/index.tsx"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

with open(file_path, "r") as f:
    content = f.read()

# Fix 1: Properly clone the data array for AreaChart to prevent Recharts from mutating it
old_code_1 = "data={telemetryHistory.current.length > 0 ? telemetryHistory.current : [{ time: '—', load: 0, ram: 0 }].map(obj => ({...obj}))}"
new_code_1 = "data={telemetryHistory.current.length > 0 ? telemetryHistory.current.map((obj: any) => ({...obj})) : [{ time: '—', load: 0, ram: 0 }]}"

if old_code_1 in content:
    content = content.replace(old_code_1, new_code_1)
else:
    old_code_fallback = "data={telemetryHistory.current.length > 0 ? telemetryHistory.current : [{ time: '—', load: 0, ram: 0 }]}"
    content = content.replace(old_code_fallback, new_code_1)

# Fix 2: Clone the data array for MiniChart
old_code_2 = "<MiniChart data={data} color={color} />"
new_code_2 = "<MiniChart data={data ? data.map((d: any) => ({...d})) : []} color={color} />"

if old_code_2 in content:
    content = content.replace(old_code_2, new_code_2)

# Fix 3: Ensure pushHistory creates a new array if the old one was somehow frozen by React/Vite
old_push_func = """  const pushHistory = useCallback((arr: {value: number}[], val: number) => {
    arr.push({ value: val })
    if (arr.length > 15) arr.shift()
  }, [])"""

new_push_func = """  const pushHistory = useCallback((arrRef: React.MutableRefObject<{value: number}[]>, val: number) => {
    const newArr = [...arrRef.current, { value: val }]
    if (newArr.length > 15) newArr.shift()
    arrRef.current = newArr
  }, [])"""

if old_push_func in content:
    content = content.replace(old_push_func, new_push_func)
    content = content.replace("pushHistory(cpuHistory.current, newCpu)", "pushHistory(cpuHistory, newCpu)")
    content = content.replace("pushHistory(ramHistory.current, newRam)", "pushHistory(ramHistory, newRam)")
    content = content.replace("pushHistory(alertHistory.current, newAlerts)", "pushHistory(alertHistory, newAlerts)")
    content = content.replace("pushHistory(cameraHistory.current, newCams)", "pushHistory(cameraHistory, newCams)")

with open(file_path, "w") as f:
    f.write(content)

print("Dashboard Recharts readonly crash has been patched successfully!")
