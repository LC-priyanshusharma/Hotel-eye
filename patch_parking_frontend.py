import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/ParkingAnalytics.tsx", "r") as f:
    content = f.read()

if "import { useWebSocket }" not in content:
    content = content.replace("import { cn } from '@/utils/utils'", "import { cn } from '@/utils/utils'\nimport { useWebSocket } from '../contexts/WebSocketContext'")

content = content.replace("export function ParkingAnalytics() {\n  const [stats, setStats] = useState<any>({})\n  const [loading, setLoading] = useState(true)", "export function ParkingAnalytics() {\n  const [stats, setStats] = useState<any>({})\n  const [loading, setLoading] = useState(true)\n  const { telemetry } = useWebSocket()")

old_effect = """    fetchData()
    const int = setInterval(fetchData, 3000)
    return () => clearInterval(int)
  }, [])"""

new_effect = """    fetchData()
  }, [])
  
  // Overlay live websocket data
  useEffect(() => {
    if (telemetry && telemetry.type === 'telemetry') {
      setStats((prevStats: any) => {
         const newStats = { ...prevStats };
         Object.values(telemetry.states || {}).forEach((state: any) => {
            const evts = state.events?.ParkingPlugin || [];
            evts.forEach((e: any) => {
               if (e.event_type === 'PARKING_STATS') {
                  newStats[state.camera_id] = {
                      ...newStats[state.camera_id],
                      occupied_spots: e.metadata?.occupied_spots || 0,
                      available_spots: e.metadata?.available_spots || 0,
                      total_spots: e.metadata?.total_spots || 0,
                      spot_status: e.metadata?.spot_status || []
                  };
               }
            });
         });
         return newStats;
      });
    }
  }, [telemetry]);"""

content = content.replace(old_effect, new_effect)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/ParkingAnalytics.tsx", "w") as f:
    f.write(content)
