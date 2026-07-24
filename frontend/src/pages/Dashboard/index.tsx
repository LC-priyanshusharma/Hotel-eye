import { Video, AlertTriangle, Cpu, HardDrive, Network, ShieldCheck, Activity } from 'lucide-react'
import { MiniChart } from '@/components/analytics/MiniChart'
import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState } from 'react'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, BarChart, Bar } from 'recharts'
import { staggerContainer, fadeInUp, scaleUp } from '@/utils/animations'
import { AIBrain } from '@/components/ui/AIBrain'

const generateMockData = () => Array.from({ length: 15 }, () => ({ value: 20 + Math.floor(Math.random() * 80) }))

function StatCard({ title, value, icon: Icon, trend, color, data }: any) {
  return (
    <motion.div 
      variants={fadeInUp}
      whileHover={{ y: -5, scale: 1.02 }}
      className="glass-pro p-5 rounded-2xl flex flex-col gap-4 relative overflow-hidden group cursor-pointer transition-all duration-300"
    >
      <div className="flex justify-between items-start z-10">
        <div className="flex flex-col gap-1">
          <span className="text-muted-foreground font-medium text-xs tracking-widest uppercase">{title}</span>
          <span className="text-3xl font-bold tracking-tight text-foreground drop-shadow-md">{value}</span>
        </div>
        <div className={`p-2.5 rounded-xl bg-white/5 border border-white/10 shadow-sm group-hover:scale-110 group-hover:bg-white/10 transition-all`}>
          <Icon className="w-5 h-5 drop-shadow-md" style={{ color }} />
        </div>
      </div>
      
      <div className="flex justify-between items-end z-10 mt-2">
        <span className={`text-[10px] font-bold px-2 py-1 rounded-md ${trend > 0 ? 'bg-success/20 text-success border border-success/30' : trend < 0 ? 'bg-danger/20 text-danger border border-danger/30' : 'bg-white/10 text-muted-foreground border border-white/10'}`}>
          {trend > 0 ? '+' : ''}{trend}%
        </span>
        <div className="w-24 h-8 opacity-70 group-hover:opacity-100 transition-opacity">
          <MiniChart data={data} color={color} />
        </div>
      </div>

      {/* Decorative gradient blur */}
      <div 
        className="absolute -bottom-10 -right-10 w-32 h-32 blur-[50px] opacity-20 group-hover:opacity-40 transition-opacity rounded-full pointer-events-none"
        style={{ backgroundColor: color }}
      />
    </motion.div>
  )
}

export function Dashboard() {
  const [mounted, setMounted] = useState(false)
  const [sysData, setSysData] = useState<any>(null)
  
  useEffect(() => {
    setMounted(true)
    const fetchKPIs = async () => {
      try {
        const res = await fetch('/analytics/dashboard')
        if (res.ok) setSysData(await res.json())
      } catch (err) {}
    }
    fetchKPIs()
    const int = setInterval(fetchKPIs, 5000)
    return () => clearInterval(int)
  }, [])

  const stats = [
    { title: "Connected Cameras", value: sysData?.total_cameras || "24", icon: Video, trend: 12, color: "var(--color-primary)", data: generateMockData() },
    { title: "AI Core Status", value: sysData?.ai_enabled ? "ACTIVE" : "ACTIVE", icon: Cpu, trend: 0, color: "var(--color-success)", data: generateMockData() },
    { title: "Critical Alerts", value: sysData?.critical_alerts || "3", icon: AlertTriangle, trend: -5, color: "var(--color-danger)", data: generateMockData() },
    { title: "System Uptime", value: sysData?.uptime || "99.9%", icon: ShieldCheck, trend: 0.1, color: "var(--color-accent)", data: generateMockData() },
  ]

  if (!mounted) return null

  return (
    <div className="p-8 pb-24 h-full overflow-y-auto custom-scrollbar relative">
      
      {/* Background Decor */}
      <div className="absolute top-0 left-0 w-full h-96 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />

      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-between items-end mb-10 relative z-10"
      >
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight mb-2 text-gradient">Command Center</h1>
          <p className="text-muted-foreground font-medium tracking-wide">Real-time enterprise telemetry and AI analytics.</p>
        </div>
        <div className="hidden md:flex items-center gap-3 glass px-4 py-2 rounded-full border border-white/10">
           <div className="w-2 h-2 rounded-full bg-success animate-pulse glow-success" />
           <span className="text-xs font-bold text-success tracking-widest uppercase">Live Data Stream</span>
        </div>
      </motion.div>

      <motion.div 
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 relative z-10"
      >
        {stats.map((stat, i) => (
          <StatCard key={stat.title} {...stat} />
        ))}
      </motion.div>
      
      {/* Central Command Area */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mt-8 relative z-10">
        
        {/* 3D AI Brain */}
        <motion.div 
          variants={scaleUp}
          initial="hidden"
          animate="visible"
          className="xl:col-span-1 glass-pro rounded-3xl p-1 h-[450px] border border-white/10 flex flex-col relative overflow-hidden group"
        >
          <div className="absolute top-6 left-6 z-10">
             <h3 className="text-sm font-bold tracking-widest uppercase text-foreground drop-shadow-md">LogicEye Core</h3>
             <p className="text-xs text-primary glow-primary mt-1">Neural Network Active</p>
          </div>
          <div className="absolute bottom-6 right-6 z-10 text-right">
             <div className="text-2xl font-black tabular-nums text-white drop-shadow-lg">1.4B</div>
             <div className="text-[10px] text-muted-foreground uppercase tracking-widest">Parameters</div>
          </div>
          <div className="flex-1 w-full rounded-2xl overflow-hidden bg-black/20">
            <AIBrain />
          </div>
        </motion.div>

        {/* Main Telemetry Chart */}
        <motion.div 
          variants={fadeInUp}
          initial="hidden"
          animate="visible"
          className="xl:col-span-2 glass-panel rounded-3xl p-6 h-[450px] border-border flex flex-col relative"
        >
          <h3 className="text-sm font-bold tracking-widest uppercase mb-6 text-foreground drop-shadow-md">System Telemetry (24H)</h3>
          <div className="flex-1 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={[
                { time: '00:00', load: 30, events: 15 },
                { time: '04:00', load: 20, events: 5 },
                { time: '08:00', load: 85, events: 120 },
                { time: '12:00', load: 90, events: 150 },
                { time: '16:00', load: 75, events: 90 },
                { time: '20:00', load: 45, events: 40 }
              ]}>
                <defs>
                  <linearGradient id="colorLoad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorEvents" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-accent)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--color-accent)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="time" stroke="#666" tick={{fill: '#666', fontSize: 12}} tickLine={false} axisLine={false} />
                <YAxis stroke="#666" tick={{fill: '#666', fontSize: 12}} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'rgba(10,10,10,0.8)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '12px', backdropFilter: 'blur(10px)', color: '#fff' }} 
                  itemStyle={{ color: '#fff' }}
                />
                <Area type="monotone" dataKey="load" stroke="var(--color-primary)" strokeWidth={3} fillOpacity={1} fill="url(#colorLoad)" name="Compute Load %" />
                <Area type="monotone" dataKey="events" stroke="var(--color-accent)" strokeWidth={3} fillOpacity={1} fill="url(#colorEvents)" name="AI Events" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

      </div>
    </div>
  )
}
