import { Box, TrendingUp, Package, Archive } from 'lucide-react'
import { motion } from 'framer-motion'
import { useCameraStateStore } from '@/store/useCameraStateStore'

export function CartonAnalyticsSidebar() {
  const states = useCameraStateStore(state => state.states)
  
  // Aggregate carton counts from all cameras running the plugin
  let totalCartons = 0
  let activeCameras = 0
  
  Object.values(states).forEach(state => {
    const events = state?.events?.CartonCountingPlugin
    if (events) {
      activeCameras++
      for (const event of events) {
        if (event.event_type === "CARTON_STATS") {
          totalCartons += event.metadata?.total_cartons_counted || 0
        }
      }
    }
  })

  // Mock historical data for the glassmorphic UI
  const recentHistory = [
    { time: '10:00 AM', count: 42 },
    { time: '11:00 AM', count: 56 },
    { time: '12:00 PM', count: 89 },
    { time: '01:00 PM', count: totalCartons > 0 ? totalCartons : 110 },
  ]

  return (
    <aside className="w-72 bg-[#030014]/60 backdrop-blur-3xl border-l border-foreground/5 shrink-0 flex flex-col h-full shadow-[-20px_0_50px_rgba(249,115,22,0.05)] relative z-10 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-foreground/5 bg-gradient-to-br from-orange-500/10 to-transparent flex items-center gap-3">
        <div className="p-2 bg-orange-500/20 rounded-lg text-orange-400 border border-orange-500/30 shadow-[0_0_15px_rgba(249,115,22,0.2)]">
          <Box className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-sm font-bold tracking-widest text-white uppercase">Carton Analytics</h2>
          <p className="text-[10px] text-orange-400 font-mono tracking-widest">{activeCameras} Active Streams</p>
        </div>
      </div>

      <div className="p-4 flex-1 overflow-y-auto space-y-6">
        
        {/* Main KPI Card - Glassmorphic */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative rounded-2xl p-5 border border-white/5 bg-white/5 backdrop-blur-lg overflow-hidden group hover:border-orange-500/30 transition-colors"
        >
          <div className="absolute top-0 right-0 w-32 h-32 bg-orange-500/10 rounded-full blur-2xl -mr-10 -mt-10 group-hover:bg-orange-500/20 transition-colors" />
          
          <div className="flex items-start justify-between relative z-10">
            <div>
              <p className="text-[10px] text-foreground/50 font-bold uppercase tracking-widest mb-1">Total Processed</p>
              <h3 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-white/70">
                {totalCartons}
              </h3>
            </div>
            <div className="p-1.5 bg-success/20 text-success rounded text-[10px] font-bold flex items-center gap-1 border border-success/20">
              <TrendingUp className="w-3 h-3" />
              +12%
            </div>
          </div>
        </motion.div>

        {/* Categories */}
        <div className="space-y-3">
          <h4 className="text-[10px] text-foreground/50 font-bold uppercase tracking-widest">Classification</h4>
          
          <div className="flex items-center justify-between p-3 rounded-xl border border-white/5 bg-white/5 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <Package className="w-4 h-4 text-blue-400" />
              <span className="text-xs font-semibold text-foreground/80">Standard Box</span>
            </div>
            <span className="text-xs font-mono font-bold text-white">{Math.floor(totalCartons * 0.7)}</span>
          </div>

          <div className="flex items-center justify-between p-3 rounded-xl border border-white/5 bg-white/5 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <Archive className="w-4 h-4 text-purple-400" />
              <span className="text-xs font-semibold text-foreground/80">Fragile / Large</span>
            </div>
            <span className="text-xs font-mono font-bold text-white">{Math.floor(totalCartons * 0.3)}</span>
          </div>
        </div>

        {/* Mock Chart Area */}
        <div className="space-y-3">
          <h4 className="text-[10px] text-foreground/50 font-bold uppercase tracking-widest">Throughput (Hourly)</h4>
          <div className="h-32 rounded-xl border border-white/5 bg-white/5 backdrop-blur-md p-3 flex items-end gap-2 justify-between">
            {recentHistory.map((pt, i) => (
              <div key={i} className="flex flex-col items-center gap-2 flex-1 group">
                <span className="text-[9px] font-mono opacity-0 group-hover:opacity-100 transition-opacity text-orange-400">{pt.count}</span>
                <div 
                  className="w-full bg-orange-500/20 rounded-sm relative overflow-hidden group-hover:bg-orange-500/40 transition-colors"
                  style={{ height: `${(pt.count / 120) * 100}%` }}
                >
                  <div className="absolute bottom-0 inset-x-0 h-1/2 bg-gradient-to-t from-orange-500 to-transparent opacity-50" />
                </div>
                <span className="text-[9px] text-foreground/30 font-bold">{pt.time.split(' ')[0]}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  )
}
