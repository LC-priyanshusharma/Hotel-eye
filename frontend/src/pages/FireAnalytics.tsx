import { useEffect, useState } from 'react'
import { Flame, AlertTriangle, Clock, Camera } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/utils/utils'

export function FireAnalytics() {
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/fire/events', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        if (res.ok) {
          const data = await res.json()
          setEvents(data.events)
        }
      } catch (err) {
        console.error("Failed to fetch fire events", err)
      } finally {
        setLoading(false)
      }
    }
    
    fetchEvents()
    const int = setInterval(fetchEvents, 3000)
    return () => clearInterval(int)
  }, [])

  if (loading) {
    return <div className="p-8 flex items-center justify-center h-full"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>
  }

  // A simple way to check if there is a very recent fire (within 10 seconds)
  const now = Date.now() / 1000
  const activeAlerts = events.filter(e => (now - e.timestamp) < 10)

  return (
    <div className="p-8 h-full overflow-y-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-1 text-white flex items-center gap-3">
            Fire & Safety Monitoring
            {activeAlerts.length > 0 && (
              <span className="flex h-3 w-3 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-danger opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-danger"></span>
              </span>
            )}
          </h1>
          <p className="text-muted-foreground">Critical safety alerts and historical fire detection logs.</p>
        </div>
      </div>

      {activeAlerts.length > 0 && (
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mb-8 p-6 rounded-2xl bg-danger/20 border border-danger shadow-[0_0_50px_rgba(255,50,50,0.2)] flex items-center justify-between"
        >
          <div className="flex items-center gap-6">
            <div className="p-4 bg-danger text-white rounded-full animate-pulse">
              <Flame className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white mb-1 tracking-tight">ACTIVE FIRE DETECTED</h2>
              <p className="text-danger-foreground">
                Critical alerts reported on {activeAlerts.length} camera(s) in the last 10 seconds.
              </p>
            </div>
          </div>
          <button className="px-6 py-3 bg-danger hover:bg-danger/80 text-white rounded-lg font-bold transition-colors">
            Acknowledge
          </button>
        </motion.div>
      )}

      <div className="glass rounded-2xl border border-white/5 overflow-hidden">
        <div className="p-6 border-b border-white/5 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-orange-400" />
          <h3 className="text-lg font-bold text-white">Detection History</h3>
        </div>
        
        {events.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            No fire events detected.
          </div>
        ) : (
          <div className="divide-y divide-white/5 max-h-[600px] overflow-y-auto">
            {events.map((event) => (
              <div key={event.id} className="p-6 hover:bg-white/5 transition-colors flex items-center justify-between group">
                <div className="flex items-center gap-6">
                  <div className="p-3 bg-orange-500/10 text-orange-400 rounded-xl group-hover:bg-orange-500/20 transition-colors">
                    <Flame className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
                      Fire Alert
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-danger/20 text-danger uppercase">Critical</span>
                    </h4>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1.5"><Camera className="w-4 h-4" /> Cam: {event.camera_id.split('/').pop() || event.camera_id}</span>
                      <span className="flex items-center gap-1.5"><Clock className="w-4 h-4" /> {new Date(event.timestamp * 1000).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
                
                <div className="text-right flex items-center gap-4">
                  <span className="text-xs font-mono text-muted-foreground bg-black/40 px-3 py-1.5 rounded-lg border border-white/5">
                    {event.fire_boxes?.length || 0} cluster(s) tracked
                  </span>
                  {event.snapshot_file && (
                    <img 
                      src={`http://localhost:8000/snapshots/${event.snapshot_file}`} 
                      alt="Fire Snapshot" 
                      className="w-24 h-16 object-cover rounded border border-danger/30" 
                    />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
