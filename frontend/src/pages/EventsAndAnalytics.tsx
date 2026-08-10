import { useEffect, useState } from 'react'
import { Activity, Calendar, Camera, Cpu, Download, Filter, HardDrive, Network, Search, Server, ShieldAlert, Zap } from 'lucide-react'
import { motion } from 'framer-motion'
import { cn } from '@/utils/utils'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ScatterChart, Scatter, ZAxis } from 'recharts'
import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'

import { staggerContainer, fadeInUp } from '@/utils/animations'

function KPICard({ title, value, subValue, icon: Icon, trend, colorClass }: any) {
  return (
    <motion.div 
      variants={fadeInUp}
      whileHover={{ y: -5, scale: 1.02 }}
      className="glass-pro p-5 rounded-2xl flex flex-col justify-between relative overflow-hidden group border border-foreground/5 cursor-pointer transition-all duration-300"
    >
      <div className={cn("absolute top-0 right-0 w-24 h-24 bg-gradient-to-br opacity-20 group-hover:opacity-40 transition-opacity rounded-full blur-[40px] -mr-4 -mt-4", colorClass.replace('text-', 'from-'))} />
      <div className="flex justify-between items-start mb-4 relative z-10">
        <h3 className="text-xs font-bold tracking-widest uppercase text-muted-foreground drop-shadow-md">{title}</h3>
        <div className={cn("p-2 rounded-xl bg-foreground/5 border border-foreground/10 group-hover:scale-110 transition-transform", colorClass)}>
          <Icon className="w-4 h-4 drop-shadow-md" />
        </div>
      </div>
      <div className="relative z-10">
        <div className="text-3xl font-black tracking-tight text-white mb-2 drop-shadow-lg">{value}</div>
        <div className="flex items-center gap-2">
          {trend && (
            <span className={cn("text-[10px] font-black tracking-wider uppercase px-2 py-0.5 rounded shadow-sm", trend > 0 ? "bg-success/20 text-success border border-success/30" : "bg-danger/20 text-danger border border-danger/30")}>
              {trend > 0 ? '+' : ''}{trend}%
            </span>
          )}
          <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest">{subValue}</span>
        </div>
      </div>
    </motion.div>
  )
}

export function Analytics() {
  const [data, setData] = useState<any>(null)
  const [activeTab, setActiveTab] = useState('All Events')
  const [timelineData, setTimelineData] = useState<any[]>([])

  useEffect(() => {
    const fetchKPIs = async () => {
      try {
        const res = await fetch('/analytics/dashboard')
        if (res.ok) setData(await res.json())
      } catch (err) {}
    }
    
    const fetchTimeline = async () => {
      try {
        const res = await fetch('/events')
        if (res.ok) {
          const events = await res.json()
          // Aggregate events by hour/minute buckets
          const buckets: Record<string, number> = {}
          events.forEach((ev: any) => {
             const d = new Date(ev.timestamp)
             const timeStr = `${d.getHours().toString().padStart(2, '0')}:${(Math.floor(d.getMinutes() / 15) * 15).toString().padStart(2, '0')}`
             buckets[timeStr] = (buckets[timeStr] || 0) + 1
          })
          const chartData = Object.entries(buckets).map(([time, count]) => ({ time, detections: count })).sort((a, b) => a.time.localeCompare(b.time))
          setTimelineData(chartData.length > 0 ? chartData : [{ time: '—', detections: 0 }])
        }
      } catch (err) {}
    }
    
    fetchKPIs()
    fetchTimeline()
    const int = setInterval(() => { fetchKPIs(); fetchTimeline() }, 5000)
    return () => clearInterval(int)
  }, [])

  if (!data) return <div className="p-8 flex items-center justify-center h-full"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>

  const generatePDF = async () => {
    try {
      const doc = new jsPDF()
      doc.setFontSize(20)
      doc.text("LogicEye Enterprise Security Report", 14, 22)
      
      doc.setFontSize(11)
      doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 30)
      
      const res = await fetch('/events')
      if (res.ok) {
        const events = await res.json()
        const tableData = events.slice(0, 100).map((ev: any) => [
          ev.timestamp?.replace('T', ' '),
          ev.camera_id,
          ev.event_type,
          ev.description
        ])
        
        autoTable(doc, {
          startY: 40,
          head: [['Timestamp', 'Camera', 'Type', 'Description']],
          body: tableData,
          theme: 'grid',
          styles: { fontSize: 8 },
          headStyles: { fillColor: [41, 128, 185] }
        })
      }
      
      doc.save('security_report.pdf')
    } catch (err) {
      console.error("Failed to generate PDF", err)
    }
  }

  return (
    <div className="p-8 h-full overflow-y-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-1 text-white">Executive Dashboard</h1>
          <p className="text-muted-foreground">Real-time system health and operational analytics.</p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-4 py-2 bg-muted rounded-lg text-sm font-medium hover:bg-muted/80 transition-colors">
            <Calendar className="w-4 h-4" /> Last 24 Hours
          </button>
          <button onClick={generatePDF} className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20 cursor-pointer">
            <Download className="w-4 h-4" /> Export Report
          </button>
        </div>
      </div>

      <div className="mb-10 relative z-10">
        <h2 className="text-sm font-bold tracking-widest uppercase mb-4 text-foreground drop-shadow-md">Operational Overview</h2>
        <motion.div 
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
        >
          <KPICard title="Total Cameras" value={data.total_cameras} subValue="Active streams" icon={Camera} colorClass="text-primary" />
          <KPICard title="AI Enabled" value={data.ai_enabled} subValue="YOLOv8 active" icon={Zap} trend={12} colorClass="text-accent" />
          <KPICard title="Critical Alerts" value={data.critical_alerts} subValue="Unresolved" icon={ShieldAlert} trend={-5} colorClass="text-danger" />
          <KPICard title="System Uptime" value={data.uptime} subValue="99.99% SLA" icon={Activity} colorClass="text-success" />
        </motion.div>
      </div>

      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-4 text-foreground/90">Hardware Telemetry</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <KPICard title="CPU Usage" value={`${data.system_health.cpu_usage}%`} subValue="Avg load" icon={Cpu} colorClass="text-indigo-400" />
          <KPICard title="GPU Usage" value={`${data.system_health.gpu_usage}%`} subValue="CUDA Core" icon={Server} colorClass="text-purple-400" />
          <KPICard title="RAM Usage" value={`${data.system_health.ram_usage}%`} subValue="Memory" icon={HardDrive} colorClass="text-emerald-400" />
          <KPICard title="Storage Usage" value={`${data.system_health.storage_usage}%`} subValue="Capacity" icon={DatabaseIcon} colorClass="text-rose-400" />
          <KPICard title="Bandwidth" value={`${data.system_health.network_bandwidth}M`} subValue="Mbps" icon={Network} colorClass="text-cyan-400" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10 relative z-10">
        <motion.div variants={fadeInUp} initial="hidden" animate="visible" className="glass-panel rounded-3xl p-6 h-[350px] flex flex-col border border-foreground/5 relative">
          <h3 className="text-xs font-bold tracking-widest uppercase mb-6 text-foreground drop-shadow-md">AI Detection Timeline</h3>
          <div className="flex-1 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timelineData}>
                <defs>
                  <linearGradient id="colorDetections" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="time" stroke="#666" tick={{fill: '#666', fontSize: 12}} tickLine={false} axisLine={false} />
                <YAxis stroke="#666" tick={{fill: '#666', fontSize: 12}} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ backgroundColor: 'rgba(10,10,10,0.8)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '12px', backdropFilter: 'blur(10px)', color: '#fff' }} />
                <Area type="monotone" dataKey="detections" stroke="var(--color-primary)" strokeWidth={3} fillOpacity={1} fill="url(#colorDetections)" name="Events" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
        <motion.div variants={fadeInUp} initial="hidden" animate="visible" className="glass-panel rounded-3xl p-6 h-[350px] flex flex-col border border-foreground/5 relative">
          <h3 className="text-xs font-bold tracking-widest uppercase mb-6 text-foreground drop-shadow-md">Camera Latency Heatmap</h3>
          <div className="flex-1 w-full relative">
            <div className="absolute inset-0 flex items-center justify-center bg-background/40 backdrop-blur-sm z-20 rounded-xl">
              <span className="text-sm font-bold text-muted-foreground uppercase tracking-widest">Real-time Data Coming Soon</span>
            </div>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="time" type="category" allowDuplicatedCategory={false} stroke="#666" tick={{fill: '#666', fontSize: 12}} tickLine={false} axisLine={false} />
                <YAxis dataKey="latency" type="number" stroke="#666" tick={{fill: '#666', fontSize: 12}} tickLine={false} axisLine={false} name="Latency (ms)" />
                <ZAxis dataKey="z" type="number" range={[50, 200]} />
                <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: 'rgba(10,10,10,0.8)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '12px', backdropFilter: 'blur(10px)', color: '#fff' }} />
                <Scatter name="Camera 1" data={[]} fill="var(--color-success)" />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      {/* Analytics Submenu */}
      <div className="flex gap-2 border-b border-foreground/10 mb-6 overflow-x-auto pb-2">
        {['All Events', 'Attendance', 'Person Count', 'Intrusions', 'Safety Alerts'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap",
              activeTab === tab 
                ? "bg-primary text-primary-foreground shadow-md" 
                : "text-muted-foreground hover:bg-foreground/5 hover:text-white"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Embedded Events Table */}
      <Events filter={activeTab} />
    </div>
  )
}

function DatabaseIcon(props: any) {
  return <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/></svg>
}


export function Events({ filter = 'All Events' }: { filter?: string }) {
  const [events, setEvents] = useState<any[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await fetch('/events')
        if (res.ok) {
          const allEvents = await res.json()
          
          // Apply frontend filtering based on active tab
          const filtered = allEvents.filter((ev: any) => {
            const desc = ev.description?.toUpperCase() || "";
            if (filter === 'All Events') return true
            if (filter === 'Attendance') return desc.includes('CHECK IN') || desc.includes('CHECK OUT')
            if (filter === 'Person Count') return desc.includes('PERSON COUNT')
            if (filter === 'Intrusions') return desc.includes('INTRUSION')
            if (filter === 'Safety Alerts') return desc.includes('FIRE')
            return true
          })
          
          setEvents(filtered)
        }
      } catch (err) {}
    }
    fetchEvents()
    const int = setInterval(fetchEvents, 2000)
    return () => clearInterval(int)
  }, [filter])

  const displayEvents = events.filter((ev) => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      const match = 
        (ev.description?.toLowerCase() || '').includes(q) ||
        (ev.camera_id?.toLowerCase() || '').includes(q) ||
        (ev.type?.toLowerCase() || '').includes(q)
      if (!match) return false
    }

    if (startDate || endDate) {
      const evDate = new Date(ev.timestamp)
      if (startDate && evDate < new Date(startDate)) return false
      if (endDate) {
        const end = new Date(endDate)
        end.setHours(23, 59, 59, 999)
        if (evDate > end) return false
      }
    }
    return true
  })

  return (
    <div className="pt-4 h-full">
      <div className="flex justify-between items-end mb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight mb-1 text-white">Event & Snapshot Log</h1>
          <p className="text-sm text-muted-foreground">Comprehensive searchable history of all system events.</p>
        </div>
        <div className="flex gap-2">
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input 
              type="text" 
              placeholder="Search events..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-muted/50 border border-foreground/10 rounded-lg py-2 pl-9 pr-4 text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:bg-background transition-all text-white placeholder-white/30"
            />
          </div>
          <div className="flex items-center gap-2 bg-muted/50 px-3 py-1.5 rounded-lg border border-foreground/10">
            <Filter className="w-4 h-4 text-muted-foreground" />
            <input 
              type="date" 
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="bg-transparent border-none text-sm text-gray-300 focus:outline-none focus:ring-0 w-[110px] [color-scheme:dark]"
            />
            <span className="text-muted-foreground text-sm">to</span>
            <input 
              type="date" 
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="bg-transparent border-none text-sm text-gray-300 focus:outline-none focus:ring-0 w-[110px] [color-scheme:dark]"
            />
            {(startDate || endDate) && (
              <button onClick={() => {setStartDate(''); setEndDate('')}} className="text-xs bg-foreground/10 hover:bg-foreground/20 px-2 py-1 rounded text-white transition ml-1">
                Clear
              </button>
            )}
          </div>
        </div>
      </div>
      
      {/* Day-Wise Summary (Visible for Person Count) */}
      {filter === 'Person Count' && (
        <div className="flex gap-4 mb-6 overflow-x-auto pb-2">
          {Object.entries(events.reduce((acc: any, ev) => {
            const date = ev.timestamp?.split('T')[0] || 'Unknown Date'
            acc[date] = (acc[date] || 0) + 1
            return acc
          }, {})).map(([date, count]) => (
            <div key={date} className="glass border border-foreground/10 rounded-xl p-4 min-w-[150px] flex flex-col items-center justify-center">
              <span className="text-xs text-muted-foreground mb-1">{date}</span>
              <span className="text-2xl font-bold text-white">{String(count)}</span>
              <span className="text-xs text-info font-medium mt-1">Total People</span>
            </div>
          ))}
          {events.length === 0 && (
            <div className="glass border border-foreground/10 rounded-xl p-4 w-full flex items-center justify-center text-muted-foreground text-sm">
              No daily counts available yet.
            </div>
          )}
        </div>
      )}

      <div className="glass rounded-2xl overflow-hidden border border-foreground/5 shadow-2xl">
        <table className="w-full text-left text-sm text-foreground/90">
          <thead className="bg-background/40 text-muted-foreground border-b border-foreground/10">
            <tr>
              <th className="px-6 py-4 font-medium">Snapshot</th>
              <th className="px-6 py-4 font-medium">Timestamp</th>
              <th className="px-6 py-4 font-medium">Camera</th>
              <th className="px-6 py-4 font-medium">Type</th>
              <th className="px-6 py-4 font-medium">Description</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {displayEvents.map((ev, i) => (
              <tr key={ev.id || i} className="hover:bg-foreground/5 transition-colors group">
                <td className="px-6 py-4">
                  {ev.snapshot_file ? (
                    <img 
                      src={ev.snapshot_file.startsWith('/') ? ev.snapshot_file : `/${ev.snapshot_file}`} 
                      alt="Snapshot" 
                      className="w-20 h-14 object-contain rounded shadow border border-foreground/10 bg-black/40"
                    />
                  ) : (
                    <div className="w-24 h-16 bg-foreground/5 rounded flex items-center justify-center text-xs text-muted-foreground">No Photo</div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">{ev.timestamp?.replace('T', ' ')}</td>
                <td className="px-6 py-4 font-medium" title={ev.camera_id}>
                  {(() => {
                    if (!ev.camera_id) return '';
                    if (ev.camera_id.includes('.mp4')) return 'Camera 1 Test Video';
                    if (ev.camera_id.includes('192.168.1.121')) return 'Camera 2 Lobby';
                    return ev.camera_id.split('/').pop();
                  })()}
                </td>
                <td className="px-6 py-4">
                  <span className={cn(
                    "px-2 py-1 rounded text-xs font-semibold capitalize",
                    ev.event_type === 'success' ? "bg-success/20 text-success" : 
                    ev.event_type === 'warning' ? "bg-warning/20 text-warning" : 
                    "bg-info/20 text-info"
                  )}>
                    {ev.event_type}
                  </span>
                </td>
                <td className="px-6 py-4">{ev.description}</td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-muted-foreground">No events recorded yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
