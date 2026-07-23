import { LayoutDashboard, Video, PlaySquare, AlertTriangle, BarChart2, Map, Users, Settings, LifeBuoy, Server, Database, ChevronLeft, ChevronRight, Trash2, Clock, Car, BadgeCheck, Flame, UserCheck, UserPlus } from 'lucide-react'
import { useAppStore } from '@/store/useAppStore'
import { cn } from '@/utils/utils'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
  { icon: Video, label: 'Live Cameras', path: '/cameras' },
  { icon: PlaySquare, label: 'Playback', path: '/playback' },
  { icon: AlertTriangle, label: 'Events', path: '/events' },
  { icon: BarChart2, label: 'Analytics', path: '/analytics' },
  { icon: Trash2, label: 'Garbage Analytics', path: '/garbage' },
  { icon: Clock, label: 'Queue Analytics', path: '/queue' },
  { icon: Car, label: 'Parking Analytics', path: '/parking' },
  { icon: BadgeCheck, label: 'Attendance', path: '/attendance' },
  { icon: Flame, label: 'Fire Detection', path: '/fire' },
  { icon: Car, label: 'ANPR Analytics', path: '/anpr' },
  { icon: UserCheck, label: 'Visitor Logs', path: '/visitor' },
  { icon: UserPlus, label: 'Visitor DB', path: '/registered-visitors' },
  { icon: Map, label: 'Maps', path: '/maps' },
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

  // Filter items based on role
  const filteredNavItems = navItems.filter(item => {
    if (['Storage', 'AI Models'].includes(item.label) && !isAdmin) return false;
    return true;
  });

  const filteredBottomNavItems = bottomNavItems.filter(item => {
    if (['Users', 'Settings'].includes(item.label) && !isAdmin) return false;
    return true;
  });

  return (
    <aside 
      className={cn(
        "bg-sidebar border-r border-border flex flex-col justify-between transition-all duration-300 ease-in-out shrink-0",
        sidebarOpen ? "w-64" : "w-16"
      )}
    >
      <div className="flex flex-col py-4 gap-2">
        {filteredNavItems.map((item) => {
          const isActive = location.pathname === item.path
          return (
            <Link 
              key={item.label} 
              to={item.path}
              className={cn(
                "flex items-center gap-4 px-4 py-3 mx-2 rounded-lg transition-all relative overflow-hidden group",
                isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              )}
            >
              {isActive && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary rounded-r-md" />}
              <item.icon className={cn("w-5 h-5 shrink-0 transition-transform group-hover:scale-110", isActive && "text-primary")} />
              <span className={cn("font-medium whitespace-nowrap transition-opacity duration-300", sidebarOpen ? "opacity-100" : "opacity-0 hidden")}>
                {item.label}
              </span>
            </Link>
          )
        })}
      </div>

      <div className="flex flex-col py-4 gap-2 border-t border-border">
        {filteredBottomNavItems.map((item) => {
          const isActive = location.pathname === item.path
          return (
            <Link 
              key={item.label} 
              to={item.path}
              className={cn(
                "flex items-center gap-4 px-4 py-3 mx-2 rounded-lg transition-all group",
                isActive ? "text-primary bg-primary/10" : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              )}
            >
              <item.icon className="w-5 h-5 shrink-0 transition-transform group-hover:rotate-12" />
              <span className={cn("font-medium whitespace-nowrap transition-opacity duration-300", sidebarOpen ? "opacity-100" : "opacity-0 hidden")}>
                {item.label}
              </span>
            </Link>
          )
        })}
        
        <button 
          onClick={toggleSidebar}
          className="flex items-center gap-4 px-4 py-3 mx-2 mt-2 rounded-lg text-muted-foreground hover:bg-muted/50 hover:text-foreground transition-all"
        >
          {sidebarOpen ? <ChevronLeft className="w-5 h-5 shrink-0" /> : <ChevronRight className="w-5 h-5 shrink-0" />}
          <span className={cn("font-medium whitespace-nowrap transition-opacity duration-300", sidebarOpen ? "opacity-100" : "opacity-0 hidden")}>
            Collapse Sidebar
          </span>
        </button>
      </div>
    </aside>
  )
}
