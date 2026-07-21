import { useEffect, useState } from 'react'
import { Car, Clock, ShieldCheck, AlertCircle } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/utils/utils'

export function ParkingAnalytics() {
  const [stats, setStats] = useState<any>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/parking/stats', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        if (res.ok) {
          const data = await res.json()
          setStats(data.current)
        }
      } catch (err) {
        console.error("Failed to fetch parking data", err)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
    const int = setInterval(fetchData, 3000)
    return () => clearInterval(int)
  }, [])

  if (loading) {
    return <div className="p-8 flex items-center justify-center h-full"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>
  }

  const cameraKeys = Object.keys(stats)

  return (
    <div className="p-8 h-full overflow-y-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-1 text-white">Parking Analytics</h1>
          <p className="text-muted-foreground">Live occupancy tracking across defined parking zones.</p>
        </div>
      </div>

      {cameraKeys.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground glass rounded-2xl">
          No parking stats found. Please ensure Parking zones are configured in the backend and vehicles are detected.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {cameraKeys.map((camId, i) => {
            const data = stats[camId]
            const utilization = data.total_spots > 0 ? (data.occupied_spots / data.total_spots) * 100 : 0
            
            return (
              <motion.div 
                key={camId}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="glass rounded-2xl border border-white/5 overflow-hidden flex flex-col group"
              >
                {/* Header Graphic */}
                <div className="h-24 bg-muted relative flex items-center justify-between px-6">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 rounded-full blur-3xl -mr-10 -mt-10" />
                  <div className="flex flex-col relative z-10">
                    <span className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-1">Camera</span>
                    <span className="text-lg font-bold text-white truncate max-w-[150px]" title={camId}>
                      {camId.split('/').pop() || camId}
                    </span>
                  </div>
                  <div className="relative z-10 w-16 h-16 rounded-full bg-black/40 border border-white/10 flex items-center justify-center">
                    <Car className={cn("w-7 h-7", utilization > 90 ? "text-danger" : "text-primary")} />
                  </div>
                </div>
                
                {/* Stats */}
                <div className="p-6 flex flex-col gap-6">
                  <div className="flex justify-between items-end">
                    <div>
                      <div className="text-3xl font-bold tracking-tight text-white mb-1">
                        {data.available_spots}
                      </div>
                      <div className="flex items-center gap-2 text-sm text-success font-medium">
                        <ShieldCheck className="w-4 h-4" /> Available Slots
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-3xl font-bold tracking-tight text-white mb-1">
                        {data.occupied_spots}
                      </div>
                      <div className="flex items-center justify-end gap-2 text-sm text-danger font-medium">
                        <AlertCircle className="w-4 h-4" /> Occupied
                      </div>
                    </div>
                  </div>
                  
                  {/* Utilization Bar */}
                  <div>
                    <div className="flex justify-between text-xs text-muted-foreground mb-2">
                      <span>Utilization</span>
                      <span>{Math.round(utilization)}%</span>
                    </div>
                    <div className="w-full h-2 bg-black/40 rounded-full overflow-hidden">
                      <div 
                        className={cn("h-full transition-all duration-1000 ease-out", 
                          utilization > 90 ? "bg-danger" : utilization > 60 ? "bg-warning" : "bg-primary"
                        )}
                        style={{ width: `${utilization}%` }}
                      />
                    </div>
                  </div>
                  
                  {/* Spot Map Mock */}
                  <div className="mt-4 border-t border-white/5 pt-4">
                    <div className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wider">Live Slot Map</div>
                    <div className="flex gap-2 flex-wrap">
                      {data.spot_status.map((isOccupied: boolean, idx: number) => (
                        <div 
                          key={idx}
                          className={cn(
                            "px-3 py-1.5 rounded text-xs font-bold transition-colors",
                            isOccupied ? "bg-danger/20 text-danger border border-danger/30" : "bg-success/20 text-success border border-success/30"
                          )}
                        >
                          P{idx + 1}
                        </div>
                      ))}
                    </div>
                  </div>
                  
                </div>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
