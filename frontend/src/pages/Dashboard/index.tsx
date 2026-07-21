import { Video, AlertTriangle, Cpu, HardDrive, Network, ShieldCheck, Activity } from 'lucide-react'
import { MiniChart } from '@/components/analytics/MiniChart'
import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, BarChart, Bar } from 'recharts'

const generateMockData = () => Array.from({ length: 10 }, () => ({ value: Math.floor(Math.random() * 100) }))

function StatCard({ title, value, icon: Icon, trend, color, data }: any) {
  return (
    <motion.div 
      whileHover={{ y: -4, scale: 1.01 }}
      className="glass p-5 rounded-2xl flex flex-col gap-4 relative overflow-hidden group cursor-pointer transition-all duration-300 hover:shadow-2xl hover:border-primary/50"
    >
      <div className="flex justify-between items-start z-10">
        <div className="flex flex-col gap-1">
          <span className="text-muted-foreground font-medium text-sm">{title}</span>
          <span className="text-3xl font-bold tracking-tight text-foreground">{value}</span>
        </div>
        <div className={`p-2.5 rounded-xl bg-background border border-border shadow-sm group-hover:scale-110 transition-transform`}>
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
      </div>
      
      <div className="flex justify-between items-end z-10 mt-2">
        <span className={`text-xs font-semibold px-2 py-1 rounded-full ${trend > 0 ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'}`}>
          {trend > 0 ? '+' : ''}{trend}%
        </span>
        <MiniChart data={data} color={color} />
      </div>

      {/* Decorative gradient blur */}
      <div 
        className="absolute -bottom-10 -right-10 w-32 h-32 blur-3xl opacity-10 group-hover:opacity-20 transition-opacity rounded-full pointer-events-none"
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
        const res = await fetch('http://localhost:8000/analytics/dashboard')
        if (res.ok) setSysData(await res.json())
      } catch (err) {}
    }
    fetchKPIs()
    const int = setInterval(fetchKPIs, 5000)
    return () => clearInterval(int)
  }, [])

  const stats = [
    { title: "Connected Cameras", value: sysData?.total_cameras || "0", icon: Video, trend: 0, color: "var(--color-primary)", data: generateMockData() },
    { title: "AI Running", value: sysData?.ai_enabled || "0", icon: Cpu, trend: 0, color: "var(--color-success)", data: generateMockData() },
    { title: "Today's Alerts", value: sysData?.critical_alerts || "0", icon: AlertTriangle, trend: 0, color: "var(--color-danger)", data: generateMockData() },
    { title: "System Health", value: sysData?.uptime || "0%", icon: ShieldCheck, trend: 0, color: "var(--color-success)", data: generateMockData() },
    { title: "CPU Usage", value: `${sysData?.system_health?.cpu_usage || 0}%`, icon: Activity, trend: 0, color: "var(--color-warning)", data: generateMockData() },
    { title: "RAM Usage", value: `${sysData?.system_health?.ram_usage || 0}%`, icon: Network, trend: 0, color: "var(--color-primary)", data: generateMockData() },
    { title: "Storage", value: `${sysData?.system_health?.storage_usage || 0}%`, icon: HardDrive, trend: 0, color: "var(--color-primary)", data: generateMockData() },
    { title: "Offline Nodes", value: "0", icon: AlertTriangle, trend: 0, color: "var(--color-success)", data: generateMockData() },
  ]

  if (!mounted) return null

  return (
    <div className="p-8 pb-24 h-full overflow-y-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-1">Overview</h1>
          <p className="text-muted-foreground">Real-time telemetry and system status.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <StatCard {...stat} />
          </motion.div>
        ))}
      </div>
      
      {/* Dashboard charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
        <div className="lg:col-span-2 glass rounded-2xl p-6 h-[400px] border-border flex flex-col">
          <h3 className="text-lg font-semibold mb-4">System Activity (24h)</h3>
          <div className="flex-1 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={[
                { time: '00:00', load: 30, alerts: 5 },
                { time: '04:00', load: 20, alerts: 2 },
                { time: '08:00', load: 85, alerts: 12 },
                { time: '12:00', load: 90, alerts: 18 },
                { time: '16:00', load: 75, alerts: 8 },
                { time: '20:00', load: 45, alerts: 4 }
              ]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                <XAxis dataKey="time" stroke="#888" />
                <YAxis stroke="#888" />
                <Tooltip contentStyle={{ backgroundColor: '#111', borderColor: '#333' }} />
                <Area type="monotone" dataKey="load" stroke="var(--color-primary)" fill="var(--color-primary)" fillOpacity={0.2} name="System Load %" />
                <Area type="monotone" dataKey="alerts" stroke="var(--color-danger)" fill="var(--color-danger)" fillOpacity={0.2} name="Critical Alerts" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        <div className="glass rounded-2xl p-6 h-[400px] border-border flex flex-col">
          <h3 className="text-lg font-semibold mb-4">AI Events Distribution</h3>
          <div className="flex-1 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[
                { name: 'Person', count: 145 },
                { name: 'Vehicle', count: 85 },
                { name: 'Intrusion', count: 24 },
                { name: 'Smoke', count: 8 }
              ]} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#333" horizontal={false} />
                <XAxis type="number" stroke="#888" />
                <YAxis dataKey="name" type="category" stroke="#888" width={80} />
                <Tooltip contentStyle={{ backgroundColor: '#111', borderColor: '#333' }} />
                <Bar dataKey="count" fill="var(--color-success)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
