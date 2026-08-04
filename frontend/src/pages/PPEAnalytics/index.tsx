import React, { useMemo } from 'react';
import { ShieldAlert, Users, AlertTriangle, TrendingUp, Activity, CheckCircle2 } from 'lucide-react';
import { useCameraStateStore } from '@/store/useCameraStateStore';
import { cn } from '@/utils/utils';
import { motion } from 'framer-motion';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';

const mockChartData = Array.from({ length: 24 }).map((_, i) => ({
  time: `${i}:00`,
  compliance: 80 + Math.random() * 20
}));

export default function PPEAnalytics() {
  const { states } = useCameraStateStore();

  // Aggregate real-time stats from all active cameras
  const realTimeStats = useMemo(() => {
    let blueCount = 0;
    let yellowCount = 0;
    let missingCount = 0;

    Object.values(states).forEach((state: any) => {
      const ppeEvents = state.events?.PPEDetectionPlugin || [];
      const statsEvent = ppeEvents.find((e: any) => e.event_type === "PPE_STATS");
      if (statsEvent?.metadata) {
        blueCount += statsEvent.metadata.contractor_1_count || 0;
        yellowCount += statsEvent.metadata.contractor_2_count || 0;
        missingCount += statsEvent.metadata.missing_ppe_count || 0;
      }
    });

    return { blueCount, yellowCount, missingCount };
  }, [states]);

  const totalLabour = realTimeStats.blueCount + realTimeStats.yellowCount + realTimeStats.missingCount;
  const complianceRate = totalLabour > 0 
    ? Math.round(((realTimeStats.blueCount + realTimeStats.yellowCount) / totalLabour) * 100) 
    : 100;

  return (
    <div className="h-full w-full p-8 overflow-y-auto">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header Section */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-600 mb-2 tracking-tight">
              Contractor PPE Analytics
            </h1>
            <p className="text-gray-400 font-medium">Real-time live monitoring of contractor labor and safety compliance.</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-success/20 border border-success/30 text-success text-sm font-bold uppercase tracking-wider">
              <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
              Live AI Feed
            </span>
          </div>
        </div>

        {/* Global KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <KPICard 
            title="Total Active Labour" 
            value={totalLabour.toString()} 
            icon={<Users className="w-6 h-6 text-blue-400" />} 
            trend="+12% today"
          />
          <KPICard 
            title="Overall Compliance" 
            value={`${complianceRate}%`} 
            icon={<ShieldAlert className="w-6 h-6 text-success" />} 
            trend="Target: 100%"
            valueColor={complianceRate < 90 ? "text-danger" : "text-success"}
          />
          <KPICard 
            title="Safety Violations" 
            value={realTimeStats.missingCount.toString()} 
            icon={<AlertTriangle className="w-6 h-6 text-danger" />} 
            trend="Active Warnings"
            valueColor={realTimeStats.missingCount > 0 ? "text-danger" : "text-white"}
          />
          <KPICard 
            title="Site Activity" 
            value="High" 
            icon={<Activity className="w-6 h-6 text-indigo-400" />} 
            trend="Peak Hours"
          />
        </div>

        {/* Contractor Breakdown Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Contractor 1: Blue */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-panel p-6 border-l-4 border-l-blue-500 relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 p-6 opacity-10 pointer-events-none">
              <ShieldAlert className="w-32 h-32 text-blue-500" />
            </div>
            
            <div className="flex justify-between items-start mb-6 relative z-10">
              <div>
                <h2 className="text-2xl font-bold text-white tracking-wide">Contractor Alpha</h2>
                <div className="flex items-center gap-2 mt-2">
                  <span className="px-2 py-1 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30 text-[10px] uppercase font-black tracking-widest">
                    Blue PPE Required
                  </span>
                  <span className="text-sm text-gray-400">Electrical & HVAC</span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-xs text-gray-500 uppercase tracking-widest font-bold">Live Labour Count</span>
                <div className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-b from-white to-blue-200 mt-1">
                  {realTimeStats.blueCount}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 relative z-10">
              <div className="bg-background/40 rounded-xl p-4 border border-foreground/5">
                <span className="text-xs text-gray-500 uppercase font-bold tracking-wider block mb-1">Supervisor</span>
                <span className="text-white font-medium">Surender Singh</span>
              </div>
              <div className="bg-background/40 rounded-xl p-4 border border-foreground/5">
                <span className="text-xs text-gray-500 uppercase font-bold tracking-wider block mb-1">Clearance</span>
                <span className="text-success font-medium flex items-center gap-1"><CheckCircle2 className="w-4 h-4" /> Zone A & B</span>
              </div>
            </div>
          </motion.div>

          {/* Contractor 2: Yellow */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-panel p-6 border-l-4 border-l-yellow-500 relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 p-6 opacity-10 pointer-events-none">
              <ShieldAlert className="w-32 h-32 text-yellow-500" />
            </div>
            
            <div className="flex justify-between items-start mb-6 relative z-10">
              <div>
                <h2 className="text-2xl font-bold text-white tracking-wide">Contractor Beta</h2>
                <div className="flex items-center gap-2 mt-2">
                  <span className="px-2 py-1 rounded bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 text-[10px] uppercase font-black tracking-widest">
                    Yellow PPE Required
                  </span>
                  <span className="text-sm text-gray-400">Heavy Machinery</span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-xs text-gray-500 uppercase tracking-widest font-bold">Live Labour Count</span>
                <div className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-b from-white to-yellow-200 mt-1">
                  {realTimeStats.yellowCount}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 relative z-10">
              <div className="bg-background/40 rounded-xl p-4 border border-foreground/5">
                <span className="text-xs text-gray-500 uppercase font-bold tracking-wider block mb-1">Supervisor</span>
                <span className="text-white font-medium">Rajesh Kumar</span>
              </div>
              <div className="bg-background/40 rounded-xl p-4 border border-foreground/5">
                <span className="text-xs text-gray-500 uppercase font-bold tracking-wider block mb-1">Clearance</span>
                <span className="text-warning font-medium flex items-center gap-1"><CheckCircle2 className="w-4 h-4" /> Zone C Only</span>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Charts Section */}
        <div className="glass-panel p-6 mt-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-bold text-white">Compliance Trend (24h)</h3>
            <button className="text-sm text-primary hover:text-primary-400 transition-colors">Export Report</button>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockChartData}>
                <defs>
                  <linearGradient id="colorCompliance" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="#4b5563" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#4b5563" fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="compliance" 
                  stroke="#10b981" 
                  strokeWidth={3}
                  fillOpacity={1} 
                  fill="url(#colorCompliance)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
}

function KPICard({ title, value, icon, trend, valueColor = "text-white" }: any) {
  return (
    <div className="glass-panel p-5 hover:bg-white/[0.02] transition-colors relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-24 h-24 bg-foreground/5 rounded-full blur-2xl -mr-10 -mt-10 group-hover:bg-primary/10 transition-colors" />
      <div className="flex justify-between items-start mb-4">
        <div className="p-2 bg-background/40 rounded-lg border border-foreground/5">
          {icon}
        </div>
        <span className="text-xs font-bold text-gray-500 uppercase tracking-widest">{title}</span>
      </div>
      <div className="flex flex-col gap-1">
        <span className={cn("text-3xl font-black tracking-tight", valueColor)}>{value}</span>
        <span className="text-xs text-gray-400 font-medium">{trend}</span>
      </div>
    </div>
  )
}
