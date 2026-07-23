import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { QRCodeSVG } from 'qrcode.react';
import { QrCode, X } from 'lucide-react';

interface VisitorEvent {
  event_id: string;
  visitor_id: string;
  visit_id?: string;
  event_type: string;
  timestamp: string;
  camera?: string;
  metadata_?: any;
}



export default function VisitorAnalytics() {
  const [events, setEvents] = useState<VisitorEvent[]>([]);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Fetch initial data
    axios.get('/api/plugins/visitor/events/all?limit=20').then(res => setEvents(res.data));

    // Connect WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws.current = new WebSocket(`${protocol}//${window.location.host}/ws/events`);
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
  }, []);

  return (
    <div className="p-6 bg-[#0a0a0a] min-h-screen text-white">
      <h1 className="text-3xl font-bold mb-6 bg-gradient-to-r from-purple-400 to-indigo-500 bg-clip-text text-transparent">
        Visitor Identity Management
      </h1>
      
      <div className="max-w-4xl mx-auto">
        {/* Live Visitor Feed */}
        <div className="bg-[#1a1a1a] p-4 rounded-xl shadow-lg shadow-black/50 border border-gray-800">
          <h2 className="text-xl font-semibold mb-4 text-purple-400">Live Entry Logs</h2>
          <div className="space-y-3 h-[600px] overflow-y-auto pr-2 custom-scrollbar">
            {events.map((ev, i) => (
              <div key={i} className="bg-[#222] p-4 rounded-lg flex justify-between items-center border border-gray-700/50 hover:bg-[#2a2a2a] transition">
                <div>
                  <div className="text-xs text-gray-400">{new Date(ev.timestamp).toLocaleString()}</div>
                  <div className="font-semibold text-lg flex items-center gap-2">
                    {ev.event_type}
                    {ev.event_type === 'UNKNOWN_PERSON' && <span className="bg-red-500/20 text-red-400 text-xs px-2 py-1 rounded">Companion</span>}
                  </div>
                  <div className="text-sm text-gray-300">ID: <span className="font-mono text-purple-300">{ev.visitor_id}</span></div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium text-gray-400">{ev.camera || 'Cam-1'}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
