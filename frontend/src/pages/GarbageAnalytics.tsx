import { useEffect, useState } from 'react'
import { Trash2, Calendar, MapPin, Clock } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/utils/utils'

export function GarbageAnalytics() {
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/garbage/events', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        if (res.ok) {
          const data = await res.json()
          setEvents(data.events)
        }
      } catch (err) {
        console.error("Failed to fetch garbage events", err)
      } finally {
        setLoading(false)
      }
    }
    
    fetchEvents()
    const int = setInterval(fetchEvents, 5000)
    return () => clearInterval(int)
  }, [])

  if (loading) {
    return <div className="p-8 flex items-center justify-center h-full"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>
  }

  return (
    <div className="p-8 h-full overflow-y-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-1 text-white">Garbage Detection</h1>
          <p className="text-muted-foreground">Monitor unauthorized dumping and stationary debris.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {events.length === 0 ? (
          <div className="col-span-full text-center py-12 text-muted-foreground">
            No garbage events detected recently.
          </div>
        ) : (
          events.map((event, i) => (
            <motion.div 
              key={event.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="glass rounded-xl overflow-hidden border border-white/5 flex flex-col"
            >
              <div className="h-48 bg-muted relative group">
                {event.snapshot_url ? (
                  <img src={`http://localhost:8000${event.snapshot_url}`} alt="Garbage" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                    <Trash2 className="w-10 h-10 opacity-20" />
                  </div>
                )}
                <div className="absolute top-2 right-2 px-2 py-1 bg-black/60 rounded text-xs font-medium text-white backdrop-blur">
                  {(event.confidence * 100).toFixed(1)}% Conf
                </div>
              </div>
              <div className="p-4 flex flex-col gap-3">
                <div className="flex justify-between items-start">
                  <h3 className="font-semibold text-lg capitalize">{event.category}</h3>
                  <span className="text-xs bg-danger/20 text-danger px-2 py-1 rounded font-medium">
                    {Math.round(event.duration_seconds)}s Dwell
                  </span>
                </div>
                
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <MapPin className="w-4 h-4" />
                  <span className="truncate" title={event.camera_id}>Cam: {event.camera_id.split('/').pop() || event.camera_id}</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="w-4 h-4" />
                  <span>{new Date(event.timestamp * 1000).toLocaleString()}</span>
                </div>
              </div>
            </motion.div>
          ))
        )}
      </div>
    </div>
  )
}
