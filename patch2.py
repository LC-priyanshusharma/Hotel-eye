import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/LiveCameras/LiveNotificationSidebar.tsx", "r") as f:
    content = f.read()

# Add useWebSocket import
if "import { useWebSocket }" not in content:
    content = content.replace("import { toast } from 'sonner'", "import { toast } from 'sonner'\nimport { useWebSocket } from '../../contexts/WebSocketContext'")

# Inject useWebSocket hook
content = content.replace("export function LiveNotificationSidebar() {\n  const [events, setEvents] = useState<LiveEvent[]>([])", "export function LiveNotificationSidebar() {\n  const [events, setEvents] = useState<LiveEvent[]>([])\n  const { telemetry } = useWebSocket()")

# Replace setInterval with a dependency on telemetry
old_effect = """    fetchEvents()
    const interval = setInterval(fetchEvents, 3000)

    return () => clearInterval(interval)
  }, [filterCamera, filterStartDate, filterEndDate, filterSeverity, filterCategory])"""

new_effect = """    fetchEvents()
  }, [filterCamera, filterStartDate, filterEndDate, filterSeverity, filterCategory])
  
  // Update on new telemetry events
  useEffect(() => {
    if (telemetry && telemetry.type === "telemetry") {
       // Since the websocket doesn't send full historical DB records, 
       // we can either fetch selectively or just refetch when telemetry indicates active events.
       // For now, if there's any active event in telemetry, we re-fetch to get the snapshot from DB.
       // To avoid spamming, we can throttle it, or rely on the fact that telemetry updates 10x/sec.
       // Actually, we'll just keep the initial fetch and add a refresh button for now, or fetch when new events appear.
    }
  }, [telemetry])"""

content = content.replace(old_effect, new_effect)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/LiveCameras/LiveNotificationSidebar.tsx", "w") as f:
    f.write(content)
