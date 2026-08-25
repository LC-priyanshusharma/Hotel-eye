import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/EventsAndAnalytics.tsx", "r") as f:
    content = f.read()

if "import { useWebSocket }" not in content:
    content = content.replace("import { cn } from '@/utils/utils'", "import { cn } from '@/utils/utils'\nimport { useWebSocket } from '../contexts/WebSocketContext'")

# Patch Analytics Component
content = content.replace("export function Analytics() {\n  const [data, setData] = useState<any>(null)\n  const [timeline, setTimeline] = useState<any[]>([])", "export function Analytics() {\n  const [data, setData] = useState<any>(null)\n  const [timeline, setTimeline] = useState<any[]>([])\n  const { telemetry } = useWebSocket()")

old_analytics_effect = """    fetchKPIs()
    fetchTimeline()
    const int = setInterval(() => { fetchKPIs(); fetchTimeline() }, 5000)
    return () => clearInterval(int)
  }, [])"""

new_analytics_effect = """    fetchKPIs()
    fetchTimeline()
  }, [])
  
  useEffect(() => {
    if (telemetry && telemetry.type === 'telemetry') {
      const h = (telemetry as any).system_health;
      if (h) {
          setData((prev: any) => ({ ...prev, system_health: h }));
      }
    }
  }, [telemetry]);"""

content = content.replace(old_analytics_effect, new_analytics_effect)

# Patch Events Component
content = content.replace("export function Events() {\n  const [events, setEvents] = useState<any[]>([])", "export function Events() {\n  const [events, setEvents] = useState<any[]>([])\n  const { telemetry } = useWebSocket()")

old_events_effect = """    fetchEvents()
    const int = setInterval(fetchEvents, 2000)
    return () => clearInterval(int)
  }, [filter])"""

new_events_effect = """    fetchEvents()
  }, [filter])
  
  useEffect(() => {
    if (telemetry && telemetry.type === 'telemetry') {
       // Auto-refresh when live events happen
       let hasEvents = false;
       Object.values(telemetry.states || {}).forEach((s: any) => {
          if (Object.keys(s.events || {}).length > 0) hasEvents = true;
       });
       if (hasEvents) {
          const fetchEvents = async () => {
             try {
                const queryParams = new URLSearchParams()
                if (filter.camera) queryParams.append('camera_id', filter.camera)
                if (filter.severity) queryParams.append('severity', filter.severity)
                if (filter.category) queryParams.append('category', filter.category)
                const res = await fetch(`/events${queryParams.toString() ? '?' + queryParams.toString() : ''}`)
                if (res.ok) setEvents(await res.json())
             } catch (err) {}
          }
          fetchEvents();
       }
    }
  }, [telemetry]);"""

content = content.replace(old_events_effect, new_events_effect)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/EventsAndAnalytics.tsx", "w") as f:
    f.write(content)
