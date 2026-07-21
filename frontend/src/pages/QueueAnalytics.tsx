import { useEffect, useState } from 'react'
import { Users, Clock, Activity } from 'lucide-react'
import { motion } from 'framer-motion'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'
import { cn } from '@/utils/utils'

export function QueueAnalytics() {
  const [stats, setStats] = useState<any>({})
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const headers = { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        
        // Fetch current stats
        const resStats = await fetch('http://localhost:8000/api/queue/stats', { headers })
        if (resStats.ok) {
          const data = await resStats.json()
          setStats(data.current)
        }

        // Fetch history for default camera (or first available)
        const resHist = await fetch('http://localhost:8000/api/queue/history?camera_id=0&limit=30', { headers })
        if (resHist.ok) {
          const data = await resHist.json()
          setHistory(data.history)
        }
      } catch (err) {
        console.error("Failed to fetch queue data", err)
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
          <h1 className="text-3xl font-bold tracking-tight mb-1 text-white">Queue Analytics</h1>
          <p className="text-muted-foreground">Real-time waiting time predictions and crowd density.</p>
        </div>
      </div>

      {cameraKeys.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground glass rounded-2xl">
          No queue data available. Ensure cameras are active and Queue plugin is running.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {cameraKeys.map((camId, i) => (
            <motion.div 
              key={camId}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="glass p-6 rounded-2xl border border-white/5 relative overflow-hidden group"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl -mr-10 -mt-10" />
              
              <h3 className="text-sm font-medium text-muted-foreground mb-4">Camera: {camId}</h3>
              
              <div className="flex justify-between items-end">
                <div>
                  <div className="text-4xl font-bold tracking-tight text-white mb-1">
                    {Math.round(stats[camId].predicted_wait_seconds)}s
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Clock className="w-4 h-4 text-blue-400" /> Wait Time (SMA)
                  </div>
                </div>
                
                <div className="text-right">
                  <div className="text-2xl font-bold tracking-tight text-white mb-1">
                    {stats[camId].people_in_queue}
                  </div>
                  <div className="flex items-center justify-end gap-2 text-sm text-muted-foreground">
                    <Users className="w-4 h-4 text-emerald-400" /> People
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* History Chart */}
      {history.length > 0 && (
        <div className="glass rounded-2xl p-6 h-[400px] flex flex-col border border-white/5">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white/90">Wait Time Trend (Historical)</h3>
            <div className="flex items-center gap-2 px-3 py-1 bg-primary/20 text-primary rounded-full text-xs font-medium">
              <Activity className="w-3 h-3" /> Live
            </div>
          </div>
          
          <div className="flex-1 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorWait" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                <XAxis dataKey="time" stroke="rgba(255,255,255,0.5)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="rgba(255,255,255,0.5)" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `${val}s`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Area type="monotone" dataKey="wait" name="Wait Time (s)" stroke="hsl(var(--primary))" strokeWidth={3} fillOpacity={1} fill="url(#colorWait)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}
