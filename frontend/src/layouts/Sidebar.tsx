import { LayoutDashboard, Video, PlaySquare, AlertTriangle, BarChart2, Map, Users, Settings, LifeBuoy, Server, Database, ChevronLeft, ChevronRight, Trash2, Clock, Car, BadgeCheck, Flame, UserCheck, UserPlus } from 'lucide-react'
import { useAppStore } from '@/store/useAppStore'
import { cn } from '@/utils/utils'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { motion, AnimatePresence } from 'framer-motion'

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
  { icon: Video, label: 'Live Cameras', path: '/cameras' },
  { icon: AlertTriangle, label: 'Events', path: '/events' },
  { icon: BarChart2, label: 'Analytics', path: '/analytics' },
  { icon: Car, label: 'Parking Analytics', path: '/parking' },
  { icon: BadgeCheck, label: 'Attendance', path: '/attendance' },
  { icon: Flame, label: 'Fire Detection', path: '/fire' },
  { icon: Car, label: 'ANPR Analytics', path: '/anpr' },
  { icon: UserCheck, label: 'Visitor Logs', path: '/visitor' },
  { icon: UserPlus, label: 'Visitor DB', path: '/visitor-db' },
  { icon: Users, label: 'Employee DB', path: '/employee-db' },
  { icon: Database, label: 'Storage', path: '/storage' },
  { icon: Server, label: 'AI Models', path: '/ai-models' },
]

const bottomNavItems = [
  { icon: Users, label: 'Users', path: '/users' },
  { icon: Settings, label: 'Settings', path: '/settings' },
  { icon: LifeBuoy, label: 'Support', path: '/support' },
]

export function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useAppStore()
  const location = useLocation()
  const { user } = useAuth()
  
  const isAdmin = user?.roles?.includes('admin') || user?.is_superuser

  const filteredNavItems = navItems.filter(item => {
    if (['Storage', 'AI Models'].includes(item.label) && !isAdmin) return false;
    return true;
  });

  const filteredBottomNavItems = bottomNavItems.filter(item => {
    if (['Users', 'Settings'].includes(item.label) && !isAdmin) return false;
    return true;
  });

  return (
    <motion.aside 
      layout
      className={cn(
        "glass-panel border-r border-white/5 flex flex-col justify-between shrink-0 h-full relative z-40 overflow-visible",
        sidebarOpen ? "w-64" : "w-20"
      )}
      initial={false}
      animate={{ width: sidebarOpen ? 256 : 80 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
    >
      <div className="flex flex-col py-6 gap-2 overflow-y-auto custom-scrollbar flex-1 px-3">
        {filteredNavItems.map((item) => {
          const isActive = location.pathname === item.path
          return (
            <Link 
              key={item.label} 
              to={item.path}
              className="relative group"
            >
              {isActive && (
                <motion.div 
                  layoutId="activeTab"
                  className="absolute inset-0 bg-primary/20 border border-primary/30 rounded-xl"
                  initial={false}
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              
              <div className={cn(
                "flex items-center gap-4 px-3 py-3 rounded-xl transition-all relative z-10",
                isActive ? "text-primary-foreground" : "text-muted-foreground hover:text-foreground hover:bg-white/5"
              )}>
                {isActive && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-primary rounded-r-md glow-primary" />}
                
                <motion.div whileHover={{ scale: 1.1, rotate: isActive ? 0 : 5 }} whileTap={{ scale: 0.95 }}>
                  <item.icon className={cn(
                    "w-5 h-5 shrink-0 transition-colors", 
                    isActive ? "text-primary drop-shadow-[0_0_8px_rgba(0,112,243,0.8)]" : ""
                  )} />
                </motion.div>
                
                <AnimatePresence>
                  {sidebarOpen && (
                    <motion.span 
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      transition={{ duration: 0.2 }}
                      className="font-medium whitespace-nowrap tracking-wide"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </div>
            </Link>
          )
        })}
      </div>

      <div className="flex flex-col py-4 gap-2 border-t border-white/5 px-3">
        {filteredBottomNavItems.map((item) => {
          const isActive = location.pathname === item.path
          return (
            <Link 
              key={item.label} 
              to={item.path}
              className={cn(
                "flex items-center gap-4 px-3 py-3 rounded-xl transition-all relative group",
                isActive ? "text-primary-foreground bg-primary/20 border border-primary/30" : "text-muted-foreground hover:text-foreground hover:bg-white/5"
              )}
            >
              <motion.div whileHover={{ rotate: 15 }} whileTap={{ scale: 0.9 }}>
                <item.icon className={cn("w-5 h-5 shrink-0", isActive && "text-primary drop-shadow-[0_0_8px_rgba(0,112,243,0.8)]")} />
              </motion.div>
              <AnimatePresence>
                {sidebarOpen && (
                  <motion.span 
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="font-medium whitespace-nowrap tracking-wide"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          )
        })}
        
        <button 
          onClick={toggleSidebar}
          className="flex items-center gap-4 px-3 py-3 mt-2 rounded-xl text-muted-foreground hover:bg-white/5 hover:text-foreground transition-all group"
        >
          <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
            {sidebarOpen ? <ChevronLeft className="w-5 h-5 shrink-0" /> : <ChevronRight className="w-5 h-5 shrink-0" />}
          </motion.div>
          <AnimatePresence>
            {sidebarOpen && (
              <motion.span 
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="font-medium whitespace-nowrap tracking-wide"
              >
                Collapse
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.aside>
  )
}
