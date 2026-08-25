import re

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/PPEAnalytics/index.tsx", "r") as f:
    content = f.read()

# Remove the Math.random array
old_mock = """const mockChartData = Array.from({ length: 24 }).map((_, i) => ({
  time: `${i}:00`,
  compliance: 80 + Math.random() * 20
}));"""

new_mock = "const mockChartData: any[] = []; // Backend historical API not implemented"

content = content.replace(old_mock, new_mock)

old_chart = """          <div className="h-64 w-full">
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
          </div>"""

new_chart = """          <div className="h-64 w-full flex items-center justify-center border border-dashed border-zinc-700 rounded-lg">
            <span className="text-zinc-500">Historical compliance API unavailable</span>
          </div>"""

content = content.replace(old_chart, new_chart)

with open("/Users/ibm/Downloads/LogicEye-main-main-2/frontend/src/pages/PPEAnalytics/index.tsx", "w") as f:
    f.write(content)
