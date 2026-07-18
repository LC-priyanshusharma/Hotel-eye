import { Search, Bell, Monitor, Settings, Maximize, User, Moon, Sun } from 'lucide-react'
import { useAppStore } from '@/store/useAppStore'
import { useState, useEffect } from 'react'

export function TopNav() {
  const { theme, toggleTheme, toggleRightPanel } = useAppStore()
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen()
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen()
      }
    }
  }

  return (
    <header className="h-16 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-50 flex items-center justify-between px-6 shrink-0">
      
      {/* Left */}
      <div className="flex items-center gap-6 w-1/3">
        <div className="flex items-center gap-2">
          <img src="/logo.png" alt="Logic Clutch" className="h-8 object-contain" />
        </div>
        
        <div className="relative hidden md:block w-64 group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
          <input 
            type="text" 
            placeholder="Search cameras..." 
            className="w-full bg-muted/50 border border-border rounded-full py-1.5 pl-9 pr-4 text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:bg-background transition-all"
          />
        </div>
      </div>

      {/* Center - Status & Time */}
      <div className="hidden lg:flex items-center justify-center gap-6 w-1/3 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse shadow-[0_0_8px_var(--color-success)]" />
          <span>System Healthy</span>
        </div>
        <div className="flex flex-col items-center">
          <span className="text-foreground font-medium tracking-wider">{time.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}</span>
          <span className="text-xs">{time.toLocaleDateString()}</span>
        </div>
      </div>

      {/* Right */}
      <div className="flex items-center justify-end gap-3 w-1/3">
        
        {/* System Stats Mini */}
        <div className="hidden xl:flex items-center gap-4 mr-4 text-xs font-medium text-muted-foreground">
          <div className="flex flex-col"><span>CPU</span><span className="text-foreground">42%</span></div>
          <div className="flex flex-col"><span>RAM</span><span className="text-foreground">5.1GB</span></div>
          <div className="flex flex-col"><span>GPU</span><span className="text-foreground">0%</span></div>
        </div>

        <button onClick={toggleTheme} className="p-2 rounded-full hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
          {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
        
        <button onClick={toggleFullscreen} className="p-2 rounded-full hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
          <Maximize className="w-5 h-5" />
        </button>
        
        <button onClick={toggleRightPanel} className="relative p-2 rounded-full hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-2 w-2 h-2 rounded-full bg-danger animate-pulse shadow-[0_0_5px_var(--color-danger)]" />
        </button>
        
        <button className="p-2 rounded-full hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
          <Settings className="w-5 h-5" />
        </button>
        
        <div className="h-8 w-8 rounded-full bg-primary/20 border border-primary/50 flex items-center justify-center ml-2 cursor-pointer hover:bg-primary/30 transition-colors">
          <User className="w-4 h-4 text-primary" />
        </div>
      </div>
    </header>
  )
}
