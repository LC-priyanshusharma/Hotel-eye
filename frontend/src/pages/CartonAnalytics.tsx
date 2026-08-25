import { useMemo, useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Box, TrendingUp, ArrowUpRight, ArrowDownRight, PackageCheck, Activity, Camera } from 'lucide-react'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from 'recharts'
import { useCameraStateStore } from '@/store/useCameraStateStore'
import { cn } from '@/utils/utils'

export function CartonAnalytics() {
  const states = useCameraStateStore(state => state.states)
  const [history, setHistory] = useState<{ time: string; count: number }[]>([])
  const lastTotalRef = useRef<number>(0)

  // Aggregate real-time carton metrics from all active camera streams
  const { totalCartons, activeConveyors, liveRate } = useMemo(() => {
    let total = 0
    let conveyors = 0

    Object.values(states || {}).forEach((camState: any) => {
      const pluginEvents = camState.events?.CartonCountingPlugin || []
      const statsEvent = pluginEvents.find((e: any) => e.event_type === 'CARTON_STATS')
      if (statsEvent?.metadata) {
        total += statsEvent.metadata.total_cartons_counted || 0
        conveyors += 1
      }
    })

    const rate = Math.max(0, total - lastTotalRef.current)
    lastTotalRef.current = total

    return { totalCartons: total, activeConveyors: conveyors, liveRate: rate }
  }, [states])

  // Rolling time-series for conveyor throughput
  useEffect(() => {
    const now = new Date()
    const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`

    setHistory(prev => {
      const updated = [...prev, { time: timeStr, count: totalCartons }]
      return updated.slice(-15) // Keep last 15 ticks
    })
  }, [totalCartons])

  return (
    <div className="flex-1 p-8 overflow-y-auto custom-scrollbar h-full relative">
      {/* Background ambient effects */}
      <div className="absolute top-0 left-0 w-full h-96 bg-primary/5 blur-3xl -z-10 pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-accent/5 blur-3xl -z-10 pointer-events-none" />

      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-black tracking-tight text-white flex items-center gap-4 drop-shadow-sm">
              <Box className="w-10 h-10 text-primary drop-shadow-[0_0_15px_rgba(59,130,246,0.6)]" />
              Carton Analytics
            </h1>
            <p className="text-foreground/60 mt-2 font-medium">Real-time conveyor tracking, package counting, and supply chain telemetry.</p>
          </div>
          
          <div className="flex gap-4">
            <span className="glass-panel px-4 py-2 rounded-xl text-sm font-medium text-foreground/80 border border-foreground/10 flex items-center gap-2 shadow-lg">
              <span className={`w-2 h-2 rounded-full ${activeConveyors > 0 ? 'bg-success animate-pulse glow-success' : 'bg-warning'}`} />
              {activeConveyors > 0 ? `${activeConveyors} Active Stream${activeConveyors > 1 ? 's' : ''}` : 'Awaiting Streams'}
            </span>
          </div>
        </div>

        {/* Real-time KPI Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <KPICard 
            title="Total Cartons Counted" 
            value={totalCartons.toLocaleString()} 
            trend="+100%" 
            trendUp={true} 
            icon={Box} 
            color="text-primary" 
            bg="bg-primary/10" 
            borderColor="border-primary/20"
          />
          <KPICard 
            title="Conveyor Lines Active" 
            value={activeConveyors.toString()} 
            trend={activeConveyors > 0 ? "Online" : "Idle"} 
            trendUp={activeConveyors > 0} 
            icon={Camera} 
            color="text-success" 
            bg="bg-success/10" 
            borderColor="border-success/20"
          />
          <KPICard 
            title="Live Flow Rate" 
            value={`${liveRate} / sec`} 
            trend="Real-Time" 
            trendUp={liveRate > 0} 
            icon={TrendingUp} 
            color="text-warning" 
            bg="bg-warning/10" 
            borderColor="border-warning/20"
          />
          <KPICard 
            title="Line Status" 
            value={activeConveyors > 0 ? "Tracking" : "Standby"} 
            trend="AI Vision" 
            trendUp={activeConveyors > 0} 
            icon={PackageCheck} 
            color="text-accent" 
            bg="bg-accent/10" 
            borderColor="border-accent/20"
          />
        </div>

        {/* Main Chart */}
        <div className="glass-panel p-6 rounded-2xl border border-foreground/10 shadow-2xl relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <div className="flex justify-between items-center mb-6 relative z-10">
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              Real-Time Conveyor Count History
            </h3>
            <span className="text-xs text-muted-foreground uppercase font-mono tracking-wider">Live WebSocket Feed</span>
          </div>
          <div className="h-[350px] w-full relative z-10">
            {history.length === 0 || totalCartons === 0 && activeConveyors === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground gap-3">
                <Box className="w-12 h-12 opacity-20" />
                <p className="text-sm font-medium">No carton tracking activity detected. Start a camera with CartonCountingPlugin enabled.</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={history.map(item => ({ ...item }))} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="time" stroke="rgba(255,255,255,0.3)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} tickLine={false} axisLine={false} />
                  <YAxis stroke="rgba(255,255,255,0.3)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '12px', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Area type="monotone" dataKey="count" name="Cumulative Cartons" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorCount)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}

function KPICard({ title, value, trend, trendUp, icon: Icon, color, bg, borderColor }: any) {
  return (
    <motion.div 
      whileHover={{ y: -5, scale: 1.02 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className={cn("glass-panel p-6 rounded-2xl border shadow-xl relative overflow-hidden group", borderColor)}
    >
      <div className={cn("absolute -right-6 -top-6 w-24 h-24 rounded-full blur-2xl opacity-50 group-hover:opacity-80 transition-opacity duration-500", bg)} />
      
      <div className="flex justify-between items-start mb-4 relative z-10">
        <div className={cn("p-3 rounded-xl", bg)}>
          <Icon className={cn("w-6 h-6", color)} />
        </div>
        <div className={cn("flex items-center gap-1 text-sm font-bold px-2 py-1 rounded-full", 
          trendUp ? "text-success bg-success/10" : "text-danger bg-danger/10"
        )}>
          {trendUp ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
          {trend}
        </div>
      </div>
      
      <div className="relative z-10">
        <h4 className="text-foreground/50 font-medium text-sm mb-1">{title}</h4>
        <div className="text-3xl font-black text-white tracking-tight">{value}</div>
      </div>
    </motion.div>
  )
}
