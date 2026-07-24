import { Search, Bell, Settings, Maximize, User, Moon, Sun, LogOut, Activity } from 'lucide-react'
import { useAppStore } from '@/store/useAppStore'
import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { motion } from 'framer-motion'

export function TopNav() {
  const { theme, toggleTheme, toggleRightPanel } = useAppStore()
  const { user, logout } = useAuth()
  const [time, setTime] = useState(new Date())
  
  const isAdmin = user?.roles?.includes('admin') || user?.is_superuser

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
    <header className="h-16 glass-pro z-50 flex items-center justify-between px-6 shrink-0 relative border-b border-white/[0.05]">
      
      {/* Decorative Top Highlight */}
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-primary/50 to-transparent opacity-50" />

      {/* Left */}
      <div className="flex items-center gap-8 w-1/3">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="relative">
             <div className="absolute inset-0 bg-primary rounded-full blur-md opacity-40 group-hover:opacity-80 transition-opacity" />
             <Activity className="w-6 h-6 text-primary relative z-10" />
          </div>
          <span className="font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/70">
            LogicEye
          </span>
        </motion.div>
        
        <div className="relative hidden md:block w-72 group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
          <input 
            type="text" 
            placeholder="Command / Search cameras..." 
            className="w-full bg-[#111111]/80 backdrop-blur-md border border-white/10 rounded-full py-1.5 pl-9 pr-4 text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all text-white placeholder:text-muted-foreground/70 shadow-inner"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
            <kbd className="hidden sm:inline-flex items-center gap-1 rounded border border-white/10 bg-white/5 px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
              <span className="text-xs">⌘</span>K
            </kbd>
          </div>
        </div>
      </div>

      {/* Center - Status & Time */}
      <div className="hidden lg:flex items-center justify-center gap-8 w-1/3 text-sm text-muted-foreground">
        <motion.div 
          whileHover={{ scale: 1.05 }}
          className="flex items-center gap-2 bg-success/10 px-3 py-1 rounded-full border border-success/20"
        >
          <div className="w-2 h-2 rounded-full bg-success animate-pulse glow-success shadow-[0_0_8px_var(--color-success)]" />
          <span className="text-success font-medium text-xs tracking-wider uppercase">System Healthy</span>
        </motion.div>
        <div className="flex flex-col items-center">
          <span className="text-foreground font-semibold tracking-widest tabular-nums drop-shadow-md">
            {time.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
          </span>
          <span className="text-[10px] text-muted-foreground uppercase tracking-widest">{time.toLocaleDateString()}</span>
        </div>
      </div>

      {/* Right */}
      <div className="flex items-center justify-end gap-3 w-1/3">
        
        {/* System Stats Mini */}
        <div className="hidden xl:flex items-center gap-5 mr-4 text-[10px] font-medium text-muted-foreground uppercase tracking-widest">
          <div className="flex flex-col items-end"><span>CPU</span><span className="text-primary glow-primary font-bold">42%</span></div>
          <div className="flex flex-col items-end"><span>RAM</span><span className="text-accent glow-accent font-bold">5.1GB</span></div>
          <div className="flex flex-col items-end"><span>GPU</span><span className="text-white font-bold">0%</span></div>
        </div>

        <motion.button whileHover={{ scale: 1.1, rotate: 15 }} whileTap={{ scale: 0.95 }} onClick={toggleTheme} className="p-2 rounded-full bg-white/5 hover:bg-white/10 border border-white/5 transition-colors text-muted-foreground hover:text-foreground">
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </motion.button>
        
        <motion.button whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.95 }} onClick={toggleFullscreen} className="p-2 rounded-full bg-white/5 hover:bg-white/10 border border-white/5 transition-colors text-muted-foreground hover:text-foreground">
          <Maximize className="w-4 h-4" />
        </motion.button>
        
        <motion.button whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.95 }} onClick={toggleRightPanel} className="relative p-2 rounded-full bg-white/5 hover:bg-white/10 border border-white/5 transition-colors text-muted-foreground hover:text-foreground">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-danger animate-pulse glow-danger" />
        </motion.button>
        
        {isAdmin && (
          <motion.button whileHover={{ scale: 1.1, rotate: 90 }} whileTap={{ scale: 0.95 }} className="p-2 rounded-full bg-white/5 hover:bg-white/10 border border-white/5 transition-colors text-muted-foreground hover:text-foreground">
            <Settings className="w-4 h-4" />
          </motion.button>
        )}
        
        <div className="flex items-center gap-3 ml-2 border-l border-white/10 pl-5">
          <div className="flex flex-col items-end hidden sm:flex">
            <span className="text-sm font-semibold text-foreground tracking-wide">{user?.email || 'Admin'}</span>
            <span className="text-[10px] text-primary uppercase tracking-widest">{user?.roles?.[0] || 'Administrator'}</span>
          </div>
          <motion.div whileHover={{ scale: 1.1 }} className="h-9 w-9 rounded-full bg-primary/20 border border-primary/50 flex items-center justify-center cursor-pointer hover:bg-primary/30 transition-all glow-primary">
            <User className="w-4 h-4 text-primary" />
          </motion.div>
          <motion.button 
            whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.95 }}
            onClick={logout}
            className="p-2 ml-1 rounded-full hover:bg-danger/20 hover:border-danger/50 border border-transparent transition-all text-muted-foreground hover:text-danger group"
            title="Logout"
          >
            <LogOut className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
          </motion.button>
        </div>
      </div>
    </header>
  )
}
