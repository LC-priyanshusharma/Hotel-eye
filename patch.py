import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/Dashboard/index.tsx", "r") as f:
    content = f.read()

# Add useWebSocket import
if "import { useWebSocket }" not in content:
    content = content.replace("import { useAppStore } from '../../store/useAppStore'", "import { useAppStore } from '../../store/useAppStore'\nimport { useWebSocket } from '../../contexts/WebSocketContext'")

# Replace fetchKPIs with WebSocket subscription and initial fetch
old_effect = """  useEffect(() => {
    setMounted(true)
    const fetchKPIs = async () => {
      try {
        const res = await fetch('/analytics/dashboard')
        if (res.ok) {
          const d = await res.json()
          setSysData(d)
          // Build rolling history from real data
          pushHistory(cpuHistory.current, d.system_health?.cpu_usage ?? 0)
          pushHistory(ramHistory.current, d.system_health?.ram_usage ?? 0)
          pushHistory(alertHistory.current, d.critical_alerts ?? 0)
          pushHistory(cameraHistory.current, d.total_cameras ?? 0)
          // Telemetry time-series
          const now = new Date()
          const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`
          telemetryHistory.current.push({ time: timeStr, load: d.system_health?.cpu_usage ?? 0, ram: d.system_health?.ram_usage ?? 0 })
          if (telemetryHistory.current.length > 30) telemetryHistory.current.shift()
        }
      } catch (err) {}
    }
    fetchKPIs()
    const int = setInterval(fetchKPIs, 5000)
    return () => clearInterval(int)
  }, [])"""

new_effect = """  const { telemetry, isConnected } = useWebSocket();

  useEffect(() => {
    setMounted(true)
    const fetchInitial = async () => {
      try {
        const res = await fetch('/analytics/dashboard') // Ensure it maps to /api/analytics/dashboard if needed
        if (res.ok) {
          const d = await res.json()
          setSysData((prev: any) => ({ ...prev, ...d }))
        }
      } catch (err) {}
    }
    fetchInitial()
  }, [])

  useEffect(() => {
    if (telemetry && telemetry.type === "telemetry") {
      const h = (telemetry as any).system_health;
      if (h) {
          const newCpu = h.cpu_usage ?? 0;
          const newRam = h.ram_usage ?? 0;
          pushHistory(cpuHistory.current, newCpu)
          pushHistory(ramHistory.current, newRam)
          
          const now = new Date()
          const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`
          telemetryHistory.current.push({ time: timeStr, load: newCpu, ram: newRam })
          if (telemetryHistory.current.length > 30) telemetryHistory.current.shift()
          
          setSysData((prev: any) => ({ ...prev, system_health: h }));
      }
    }
  }, [telemetry]);"""

content = content.replace(old_effect, new_effect)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/Dashboard/index.tsx", "w") as f:
    f.write(content)
