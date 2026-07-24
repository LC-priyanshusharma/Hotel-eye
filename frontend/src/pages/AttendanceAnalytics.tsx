import { useEffect, useState } from 'react'
import { BadgeCheck, Users, Clock, AlertTriangle, LogIn, LogOut } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/utils/utils'

export function AttendanceAnalytics() {
  const [stats, setStats] = useState<any>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('/api/attendance/stats', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        if (res.ok) {
          const data = await res.json()
          setStats(data.current)
        }
      } catch (err) {
        console.error("Failed to fetch attendance data", err)
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
          <h1 className="text-3xl font-bold tracking-tight mb-1 text-white">Attendance Tracking</h1>
          <p className="text-muted-foreground">Live Re-ID checking and employee time logging.</p>
        </div>
      </div>

      {cameraKeys.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground glass rounded-2xl">
          No attendance data available. Make sure the Attendance plugin is active.
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {cameraKeys.map((camId, i) => {
            const data = stats[camId]
            
            return (
              <motion.div 
                key={camId}
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.1 }}
                className="glass rounded-2xl border border-white/5 overflow-hidden flex flex-col group"
              >
                <div className="p-6 bg-gradient-to-r from-emerald-500/10 to-transparent border-b border-white/5">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-emerald-500/20 rounded-lg text-emerald-400">
                        <BadgeCheck className="w-5 h-5" />
                      </div>
                      <h3 className="text-lg font-bold text-white">Zone Check-in</h3>
                    </div>
                    <span className="text-xs text-muted-foreground font-mono">
                      {camId.split('/').pop() || camId}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 mt-6">
                    <div className="flex flex-col">
                      <span className="text-xs text-muted-foreground mb-1">Authorized Visible</span>
                      <div className="flex items-end gap-2">
                        <span className="text-3xl font-bold text-white">{data.authorized_employees_in_frame?.length || 0}</span>
                        <Users className="w-5 h-5 text-emerald-400 mb-1" />
                      </div>
                    </div>
                    
                    <div className="flex flex-col">
                      <span className="text-xs text-muted-foreground mb-1">Unauthorized Detected</span>
                      <div className="flex items-end gap-2">
                        <span className="text-3xl font-bold text-white">{data.unauthorized_count || 0}</span>
                        <AlertTriangle className={cn("w-5 h-5 mb-1", data.unauthorized_count > 0 ? "text-danger" : "text-muted-foreground")} />
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="p-6">
                  <h4 className="text-sm font-semibold text-white/80 mb-4 flex items-center gap-2">
                    <Clock className="w-4 h-4" /> Live Action Logs
                  </h4>
                  
                  {(!data.attendance_logs || data.attendance_logs.length === 0) ? (
                    <div className="text-center py-6 text-sm text-muted-foreground">
                      No check-ins/check-outs detected recently.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {data.attendance_logs.slice().reverse().map((log: any, idx: number) => {
                        const isCheckIn = log.action === 'CHECK IN'
                        return (
                          <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-black/40 border border-white/5">
                            <div className="flex items-center gap-3">
                              <div className={cn("p-1.5 rounded-full", isCheckIn ? "bg-emerald-500/20 text-emerald-400" : "bg-orange-500/20 text-orange-400")}>
                                {isCheckIn ? <LogIn className="w-4 h-4" /> : <LogOut className="w-4 h-4" />}
                              </div>
                              <div className="flex flex-col">
                                <span className="font-semibold text-sm text-white">{log.employee}</span>
                                <span className={cn("text-xs font-medium", isCheckIn ? "text-emerald-400" : "text-orange-400")}>
                                  {log.action}
                                </span>
                              </div>
                            </div>
                            <span className="text-xs text-muted-foreground">
                              {new Date(log.time * 1000).toLocaleTimeString()}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
