import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/ANPRAnalytics.tsx", "r") as f:
    content = f.read()

# Replace hardcoded websocket with context
if "import { useWebSocket }" not in content:
    content = content.replace("import { useQuery } from '@tanstack/react-query';", "import { useQuery } from '@tanstack/react-query';\nimport { useWebSocket } from '../contexts/WebSocketContext';")

old_ws = """  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/events`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'telemetry') {
          // Extract ANPR events from telemetry
          const anprEvents: any[] = [];
          Object.values(data.states || {}).forEach((state: any) => {
             const evts = state.events?.ANPRPlugin || [];
             evts.forEach((e: any) => {
                if (e.event_type === 'NEW_PLATE') {
                   anprEvents.push({
                      plate_number: e.metadata?.plate_number,
                      camera_id: state.camera_id,
                      vehicle_snapshot: e.snapshot_path,
                      timestamp: Date.now()
                   });
                }
             });
          });
          
          if (anprEvents.length > 0) {
            setLiveEvents(prev => {
              const merged = [...anprEvents, ...prev];
              // Keep unique plates to avoid spam
              const unique = merged.filter((v, i, a) => {
                const idx = a.findIndex(t => t.plate_number === v.plate_number);
                if (idx !== i) {
                  // Only keep if the new one is much newer (e.g. > 10 seconds)
                  const existing = a[idx];
                  if (v.timestamp - existing.timestamp > 10000) return true;
                  return false;
                }
                return true;
              });
              return unique.slice(0, 10);
            });
          }
        }
      } catch(e) {}
    };
    return () => ws.close();
  }, []);"""

new_ws = """  const { telemetry } = useWebSocket();
  useEffect(() => {
    if (telemetry && telemetry.type === 'telemetry') {
      const anprEvents: any[] = [];
      Object.values(telemetry.states || {}).forEach((state: any) => {
         const evts = state.events?.ANPRPlugin || [];
         evts.forEach((e: any) => {
            if (e.event_type === 'NEW_PLATE') {
               anprEvents.push({
                  plate_number: e.metadata?.plate_number,
                  camera_id: state.camera_id,
                  vehicle_snapshot: e.snapshot_path,
                  timestamp: Date.now()
               });
            }
         });
      });
      
      if (anprEvents.length > 0) {
        setLiveEvents(prev => {
          const merged = [...anprEvents, ...prev];
          const unique = merged.filter((v, i, a) => {
            const idx = a.findIndex(t => t.plate_number === v.plate_number);
            if (idx !== i) {
              const existing = a[idx];
              if (v.timestamp - existing.timestamp > 10000) return true;
              return false;
            }
            return true;
          });
          return unique.slice(0, 10);
        });
      }
    }
  }, [telemetry]);"""

content = content.replace(old_ws, new_ws)

old_chart = """            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={[{time: '08:00', count: 12}, {time: '09:00', count: 45}, {time: '10:00', count: 32}]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="time" stroke="#888" />
                  <YAxis stroke="#888" />
                  <Tooltip contentStyle={{backgroundColor: '#18181b', borderColor: '#27272a'}} />
                  <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={3} dot={{r: 4, fill: '#3b82f6'}} />
                </LineChart>
              </ResponsiveContainer>
            </div>"""

new_chart = """            <div className="h-64 flex items-center justify-center border border-dashed border-zinc-700 rounded-lg">
              <span className="text-zinc-500">Historical traffic API not yet implemented</span>
            </div>"""
content = content.replace(old_chart, new_chart)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/ANPRAnalytics.tsx", "w") as f:
    f.write(content)
