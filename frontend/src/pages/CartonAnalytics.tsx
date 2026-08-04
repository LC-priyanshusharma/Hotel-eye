import { motion } from 'framer-motion'
import { Box, TrendingUp, AlertCircle, ArrowUpRight, ArrowDownRight, PackageCheck, PackageX, Activity } from 'lucide-react'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis, PieChart, Pie, Cell, CartesianGrid } from 'recharts'
import { cn } from '@/utils/utils'

const hourlyData = [
  { time: '08:00', loaded: 145, unloaded: 120 },
  { time: '09:00', loaded: 165, unloaded: 135 },
  { time: '10:00', loaded: 180, unloaded: 150 },
  { time: '11:00', loaded: 170, unloaded: 165 },
  { time: '12:00', loaded: 140, unloaded: 190 },
  { time: '13:00', loaded: 210, unloaded: 230 },
  { time: '14:00', loaded: 245, unloaded: 215 },
  { time: '15:00', loaded: 190, unloaded: 180 },
]

const pieData = [
  { name: 'Standard Size', value: 400 },
  { name: 'Oversized', value: 150 },
  { name: 'Fragile', value: 85 },
  { name: 'Damaged', value: 12 },
]
const COLORS = ['#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444']

export function CartonAnalytics() {
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
            <p className="text-foreground/60 mt-2 font-medium">Real-time box tracking, loading rates, and supply chain insights.</p>
          </div>
          
          <div className="flex gap-4">
            <span className="glass-panel px-4 py-2 rounded-xl text-sm font-medium text-foreground/80 border border-foreground/10 flex items-center gap-2 shadow-lg">
              <span className="w-2 h-2 rounded-full bg-success animate-pulse glow-success" />
              System Active
            </span>
          </div>
        </div>

        {/* KPI Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <KPICard 
            title="Total Cartons Today" 
            value="4,285" 
            trend="+12.5%" 
            trendUp={true} 
            icon={Box} 
            color="text-primary" 
            bg="bg-primary/10" 
            borderColor="border-primary/20"
          />
          <KPICard 
            title="Loading Rate / hr" 
            value="342" 
            trend="+5.2%" 
            trendUp={true} 
            icon={TrendingUp} 
            color="text-success" 
            bg="bg-success/10" 
            borderColor="border-success/20"
          />
          <KPICard 
            title="Safe Deliveries" 
            value="98.5%" 
            trend="-0.5%" 
            trendUp={false} 
            icon={PackageCheck} 
            color="text-warning" 
            bg="bg-warning/10" 
            borderColor="border-warning/20"
          />
          <KPICard 
            title="Exceptions (Damaged)" 
            value="12" 
            trend="-2" 
            trendUp={true} 
            icon={PackageX} 
            color="text-danger" 
            bg="bg-danger/10" 
            borderColor="border-danger/20"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Chart */}
          <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-foreground/10 shadow-2xl relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="flex justify-between items-center mb-6 relative z-10">
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-primary" />
                Hourly Loading vs Unloading
              </h3>
            </div>
            <div className="h-[350px] w-full relative z-10">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={hourlyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorLoaded" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorUnloaded" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="time" stroke="rgba(255,255,255,0.3)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} tickLine={false} axisLine={false} />
                  <YAxis stroke="rgba(255,255,255,0.3)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '12px', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Area type="monotone" dataKey="loaded" name="Loaded Cartons" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorLoaded)" />
                  <Area type="monotone" dataKey="unloaded" name="Unloaded Cartons" stroke="#8b5cf6" strokeWidth={3} fillOpacity={1} fill="url(#colorUnloaded)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Pie Chart */}
          <div className="glass-panel p-6 rounded-2xl border border-foreground/10 shadow-2xl relative overflow-hidden group">
             <div className="absolute inset-0 bg-gradient-to-bl from-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2 relative z-10">
              <Box className="w-5 h-5 text-accent" />
              Carton Types
            </h3>
            <div className="h-[250px] relative z-10 flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={5}
                    dataKey="value"
                    stroke="none"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    itemStyle={{ color: '#fff' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mt-2 relative z-10">
              {pieData.map((item, index) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full shadow-sm" style={{ backgroundColor: COLORS[index] }} />
                  <div className="flex flex-col">
                    <span className="text-xs text-foreground/50">{item.name}</span>
                    <span className="text-sm font-bold text-white">{item.value}</span>
                  </div>
                </div>
              ))}
            </div>
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
