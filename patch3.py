import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/LiveCameras/CartonAnalyticsSidebar.tsx", "r") as f:
    content = f.read()

# Remove fake classification breakdown
old_class = """        {/* Categories */}
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
        </div>"""

new_class = """        {/* Categories (No backend support yet) */}
        <div className="space-y-3 opacity-50">
          <h4 className="text-[10px] text-foreground/50 font-bold uppercase tracking-widest">Classification</h4>
          
          <div className="flex items-center justify-between p-3 rounded-xl border border-white/5 bg-white/5 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <Package className="w-4 h-4 text-blue-400" />
              <span className="text-xs font-semibold text-foreground/80">Standard Box</span>
            </div>
            <span className="text-xs font-mono font-bold text-white">—</span>
          </div>

          <div className="flex items-center justify-between p-3 rounded-xl border border-white/5 bg-white/5 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <Archive className="w-4 h-4 text-purple-400" />
              <span className="text-xs font-semibold text-foreground/80">Fragile / Large</span>
            </div>
            <span className="text-xs font-mono font-bold text-white">—</span>
          </div>
          <div className="text-[9px] text-center text-orange-400">Classification API Not Implemented</div>
        </div>"""

content = content.replace(old_class, new_class)

# Remove fake history array and chart
old_history = """  // Mock historical data for the glassmorphic UI
  const recentHistory = [
    { time: '10:00 AM', count: 42 },
    { time: '11:00 AM', count: 56 },
    { time: '12:00 PM', count: 89 },
    { time: '01:00 PM', count: totalCartons > 0 ? totalCartons : 110 },
  ]"""
content = content.replace(old_history, "  const recentHistory: any[] = [] // Backend historical API not implemented")

old_chart = """        {/* Mock Chart Area */}
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
        </div>"""

new_chart = """        {/* Historical Chart Area */}
        <div className="space-y-3 opacity-50">
          <h4 className="text-[10px] text-foreground/50 font-bold uppercase tracking-widest">Throughput (Hourly)</h4>
          <div className="h-32 rounded-xl border border-white/5 bg-white/5 backdrop-blur-md p-3 flex items-center justify-center">
            <span className="text-xs text-foreground/40 font-medium">Historical API Unavailable</span>
          </div>
        </div>"""

content = content.replace(old_chart, new_chart)
content = content.replace("+12%", "—") # fake trend

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/LiveCameras/CartonAnalyticsSidebar.tsx", "w") as f:
    f.write(content)
