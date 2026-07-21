import { X, Activity, ShieldAlert, Clock, Fingerprint, Car } from 'lucide-react'
import { useAppStore } from '@/store/useAppStore'
import { cn } from '@/utils/utils'
import { useState } from 'react'

const TABS = [
  { id: 'alerts', icon: ShieldAlert, label: 'Alerts' },
  { id: 'ai', icon: Fingerprint, label: 'AI Detection' },
  { id: 'health', icon: Activity, label: 'Health' },
  { id: 'events', icon: Clock, label: 'Events' },
]

export function RightPanel() {
  const { rightPanelOpen, toggleRightPanel } = useAppStore()
  const [activeTab, setActiveTab] = useState('alerts')

  return (
    <aside 
      className={cn(
        "bg-card border-l border-border transition-all duration-300 ease-in-out shrink-0 flex flex-col z-40 fixed right-0 top-16 bottom-0 shadow-2xl",
        rightPanelOpen ? "w-80 translate-x-0" : "w-80 translate-x-full"
      )}
    >
      <div className="flex items-center justify-between p-4 border-b border-border bg-background/50">
        <h2 className="font-semibold text-lg tracking-wide">Live Intel</h2>
        <button onClick={toggleRightPanel} className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="flex p-2 gap-1 border-b border-border bg-background/30">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex-1 flex flex-col items-center gap-1.5 p-2 rounded-md transition-all text-xs font-medium",
              activeTab === tab.id ? "bg-primary text-primary-foreground shadow-md" : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {activeTab === 'alerts' && (
          <>
            <div className="p-3 rounded-lg border-l-4 border-danger bg-danger/10 flex flex-col gap-1 cursor-pointer hover:bg-danger/20 transition-colors">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span className="font-semibold text-danger">🔴 Critical Alert</span>
                <span>10:35:22</span>
              </div>
              <p className="text-sm font-medium">Unauthorized Person Detected</p>
              <p className="text-xs text-muted-foreground">Camera 1 - Lobby • Track ID: 12</p>
            </div>
            
            <div className="p-3 rounded-lg border-l-4 border-warning bg-warning/10 flex flex-col gap-1 cursor-pointer hover:bg-warning/20 transition-colors">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span className="font-semibold text-warning">🟡 Warning</span>
                <span>10:32:10</span>
              </div>
              <p className="text-sm font-medium">Crowd Density High (85%)</p>
              <p className="text-xs text-muted-foreground">Camera 3 - Restaurant</p>
            </div>
          </>
        )}

        {activeTab === 'ai' && (
          <>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 cursor-pointer transition-colors border border-border">
              <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center shrink-0">
                <Fingerprint className="w-5 h-5 text-primary" />
              </div>
              <div className="flex flex-col flex-1 overflow-hidden">
                <span className="text-sm font-medium truncate">Employee: John Doe</span>
                <span className="text-xs text-muted-foreground">Confidence: 98% • Cam 2</span>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 cursor-pointer transition-colors border border-border">
              <div className="w-10 h-10 rounded-full bg-secondary flex items-center justify-center shrink-0">
                <Car className="w-5 h-5 text-success" />
              </div>
              <div className="flex flex-col flex-1 overflow-hidden">
                <span className="text-sm font-medium truncate">Vehicle: XYZ-1234</span>
                <span className="text-xs text-muted-foreground">Authorized • Cam 4</span>
              </div>
            </div>
          </>
        )}
      </div>
    </aside>
  )
}
