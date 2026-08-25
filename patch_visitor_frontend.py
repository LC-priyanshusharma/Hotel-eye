import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/VisitorAnalytics.tsx", "r") as f:
    content = f.read()

if "import { useWebSocket }" not in content:
    content = content.replace("import { QrCode, X } from 'lucide-react';", "import { QrCode, X } from 'lucide-react';\nimport { useWebSocket } from '../contexts/WebSocketContext';")

content = content.replace("export default function VisitorAnalytics() {\n  const [events, setEvents] = useState<VisitorEvent[]>([]);\n  const ws = useRef<WebSocket | null>(null);", "export default function VisitorAnalytics() {\n  const [events, setEvents] = useState<VisitorEvent[]>([]);\n  const { telemetry } = useWebSocket();")

old_effect = """  useEffect(() => {
    // Fetch initial data
    axios.get('/api/plugins/visitor/events/all?limit=20').then(res => setEvents(res.data));

    // Connect WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const token = localStorage.getItem('access_token') || '';
    ws.current = new WebSocket(`${protocol}//${window.location.host}/ws/events?token=${encodeURIComponent(token)}`);
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      let newEvents: VisitorEvent[] = [];
      Object.values(data).forEach((camData: any) => {
        if (camData.events && camData.events.VisitorPlugin) {
          newEvents.push(...camData.events.VisitorPlugin);
        }
      });
      if (newEvents.length > 0) {
        setEvents(prev => [...newEvents, ...prev].slice(0, 50));
      }
    };
    return () => ws.current?.close();
  }, []);"""

new_effect = """  useEffect(() => {
    // Fetch initial data
    axios.get('/api/visitor/events/all?limit=20').then(res => setEvents(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (telemetry && telemetry.type === 'telemetry') {
      let newEvents: VisitorEvent[] = [];
      Object.values(telemetry.states || {}).forEach((camData: any) => {
        if (camData.events && camData.events.VisitorPlugin) {
          newEvents.push(...camData.events.VisitorPlugin.map((e:any) => ({
             event_id: Math.random().toString(),
             visitor_id: e.metadata?.visitor_id || 'UNKNOWN',
             event_type: e.event_type,
             timestamp: new Date().toISOString(),
             camera: camData.camera_id
          })));
        }
      });
      if (newEvents.length > 0) {
        setEvents(prev => {
           const merged = [...newEvents, ...prev];
           // Deduplicate just in case
           const unique = merged.filter((v, i, a) => a.findIndex(t => t.visitor_id === v.visitor_id && t.event_type === v.event_type) === i);
           return unique.slice(0, 50);
        });
      }
    }
  }, [telemetry]);"""

content = content.replace(old_effect, new_effect)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/VisitorAnalytics.tsx", "w") as f:
    f.write(content)
