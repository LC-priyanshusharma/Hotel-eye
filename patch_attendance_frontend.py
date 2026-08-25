import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/AttendanceAnalytics.tsx", "r") as f:
    content = f.read()

if "import { useWebSocket }" not in content:
    content = content.replace("import { cn } from '@/utils/utils'", "import { cn } from '@/utils/utils'\nimport { useWebSocket } from '../contexts/WebSocketContext'")

content = content.replace("export function AttendanceAnalytics() {\n  const [stats, setStats] = useState<any>({})\n  const [loading, setLoading] = useState(true)", "export function AttendanceAnalytics() {\n  const [stats, setStats] = useState<any>({})\n  const [loading, setLoading] = useState(true)\n  const { telemetry } = useWebSocket()")

old_effect = """    fetchData()
    const int = setInterval(fetchData, 3000)
    return () => clearInterval(int)
  }, [])"""

new_effect = """    fetchData()
  }, [])
  
  // Overlay live websocket data on top of historical stats
  useEffect(() => {
    if (telemetry && telemetry.type === 'telemetry') {
      setStats((prevStats: any) => {
         const newStats = { ...prevStats };
         Object.values(telemetry.states || {}).forEach((state: any) => {
            const camId = state.camera_id;
            if (!newStats[camId]) {
               newStats[camId] = { attendance_logs: [] };
            }
            
            // Extract live frame data
            const evts = state.events?.AttendancePlugin || [];
            let auth: any[] = [];
            let unauthCount = 0;
            
            evts.forEach((e: any) => {
               if (e.event_type === 'AUTHORIZED_VISIBLE') {
                  auth.push(e.metadata);
               } else if (e.event_type === 'UNAUTHORIZED_VISIBLE') {
                  unauthCount++;
               }
            });
            
            newStats[camId].authorized_employees_in_frame = auth;
            newStats[camId].unauthorized_count = unauthCount;
         });
         return newStats;
      });
    }
  }, [telemetry]);"""

content = content.replace(old_effect, new_effect)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/AttendanceAnalytics.tsx", "w") as f:
    f.write(content)
