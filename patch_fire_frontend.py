import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/FireAnalytics.tsx", "r") as f:
    content = f.read()

if "import { useWebSocket }" not in content:
    content = content.replace("import { cn } from '@/utils/utils'", "import { cn } from '@/utils/utils'\nimport { useWebSocket } from '../contexts/WebSocketContext'")

# Replace hook definition
content = content.replace("export function FireAnalytics() {\n  const [events, setEvents] = useState<any[]>([])\n  const [loading, setLoading] = useState(true)", "export function FireAnalytics() {\n  const [events, setEvents] = useState<any[]>([])\n  const [loading, setLoading] = useState(true)\n  const { telemetry } = useWebSocket()")

old_effect = """    fetchEvents()
    const int = setInterval(fetchEvents, 3000)
    return () => clearInterval(int)
  }, [])"""

new_effect = """    fetchEvents()
  }, [])
  
  useEffect(() => {
    if (telemetry && telemetry.type === 'telemetry') {
      let newFireEvents = false;
      Object.values(telemetry.states || {}).forEach((state: any) => {
         const evts = state.events?.FireDetectionPlugin || [];
         if (evts.some((e: any) => e.event_type === 'FIRE_DETECTED')) {
            newFireEvents = true;
         }
      });
      if (newFireEvents) {
          // Re-fetch to get latest from DB with snapshots
          const fetchEvents = async () => {
             try {
               const res = await fetch('/api/fire/events', { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
               if (res.ok) setEvents((await res.json()).events)
             } catch (err) {}
          }
          fetchEvents()
      }
    }
  }, [telemetry]);"""

content = content.replace(old_effect, new_effect)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/FireAnalytics.tsx", "w") as f:
    f.write(content)
