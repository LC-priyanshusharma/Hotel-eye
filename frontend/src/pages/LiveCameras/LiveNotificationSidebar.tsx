import { useState, useEffect } from 'react'
import { Activity } from 'lucide-react'
import { cn } from '@/utils/utils'

interface LiveEvent {
  id: string
  time: string
  title: string
  cameraName: string
  type: string
  category: string
}

const getCategoryFromTitle = (title: string) => {
  const upper = title?.toUpperCase() || ""
  if (upper.includes("CHECK IN") || upper.includes("CHECK OUT") || upper.includes("ATTENDANCE")) return "ATTENDANCE"
  if (upper.includes("INTRUSION")) return "INTRUSION"
  if (upper.includes("SMOKE") || upper.includes("FIRE")) return "SAFETY ALERT"
  if (upper.includes("PERSON COUNT") || upper.includes("PEOPLE")) return "PEOPLE COUNT"
  return "EVENT"
}

export function LiveNotificationSidebar() {
  const [events, setEvents] = useState<LiveEvent[]>([])

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await fetch('http://localhost:8000/events')
        if (res.ok) {
          const dbEvents = await res.json()
          
          const mapCameraName = (id: string) => {
            if (!id) return 'UNKNOWN'
            if (id.includes('.mp4')) return 'CAMERA 1'
            if (id.includes('192.168.1.121')) return 'LOBBY CAM'
            if (id.includes('192.168.1.122')) return 'ROOM CAM'
            return id.split('/').pop() || id
          }

          const formattedEvents: LiveEvent[] = dbEvents
            .filter((dbEvent: any) => {
              const desc = dbEvent.description?.toLowerCase() || "";
              return !desc.includes('analytics update');
            })
            .map((dbEvent: any) => ({
              id: dbEvent.id?.toString() || Math.random().toString(),
              time: new Date(dbEvent.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
              title: dbEvent.description || "No Title",
              cameraName: mapCameraName(dbEvent.camera_id).toUpperCase(),
              type: dbEvent.event_type || "info",
              category: getCategoryFromTitle(dbEvent.description)
            }))
          
          setEvents(formattedEvents)
        }
      } catch (e) {
        console.error("Failed to fetch events", e)
      }
    }

    fetchEvents()
    const interval = setInterval(fetchEvents, 3000)

    return () => clearInterval(interval)
  }, [])

  return (
    <aside className="w-80 bg-[#0B0C10] border-l border-[#1F2833] shrink-0 flex flex-col h-full shadow-2xl relative z-10">
      <div className="p-4 border-b border-[#1F2833] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-danger animate-pulse" />
          <h2 className="text-sm font-bold tracking-widest text-[#45A29E] uppercase">Global Event Stream</h2>
        </div>
        <span className="text-[10px] text-white font-bold bg-[#1F2833] px-3 py-1 rounded-full uppercase tracking-wider">
          {events.length} Captured
        </span>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-muted-foreground gap-2">
            <Activity className="w-8 h-8 opacity-20" />
            <span className="text-sm font-medium opacity-50">Awaiting Events...</span>
          </div>
        ) : (
          events.map(event => (
            <div 
              key={event.id}
              style={{ minHeight: '80px', display: 'flex', backgroundColor: 'rgba(31,40,51,0.5)', borderRadius: '12px', overflow: 'hidden' }}
            >
              <div className={cn(
                "w-1 shrink-0",
                event.type === 'danger' && "bg-danger",
                event.type === 'warning' && "bg-warning",
                event.type === 'success' && "bg-success",
                event.type === 'info' && "bg-[#45A29E]"
              )} />
              
              <div className="p-3 w-full flex flex-col justify-center">
                <div className="flex justify-between items-center mb-1">
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      "w-1.5 h-1.5 rounded-full",
                      event.type === 'danger' && "bg-danger",
                      event.type === 'warning' && "bg-warning",
                      event.type === 'success' && "bg-success",
                      event.type === 'info' && "bg-[#45A29E]"
                    )} />
                    <span className="text-[10px] font-bold tracking-wider text-white">
                      {event.cameraName}
                    </span>
                  </div>
                  <span className="text-[10px] text-gray-400 font-mono tracking-wider">
                    {event.time}
                  </span>
                </div>
                
                <div className={cn(
                  "text-[10px] font-bold tracking-widest uppercase mb-1",
                  event.type === 'danger' && "text-danger",
                  event.type === 'warning' && "text-warning",
                  event.type === 'success' && "text-success",
                  event.type === 'info' && "text-[#45A29E]"
                )}>
                  {event.category}
                </div>
                
                <div className="text-sm text-gray-300 font-medium">
                  {event.title}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  )
}
