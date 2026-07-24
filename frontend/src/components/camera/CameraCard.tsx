import { Maximize, Camera as CameraIcon, Video, Crosshair, Mic, Volume2, Settings, PictureInPicture, Signal, Users, SlidersHorizontal, Check } from 'lucide-react'
import { memo, useEffect, useState } from 'react'
import { cn } from '@/utils/utils'
import { motion } from 'framer-motion'
import { VideoPlayer } from './VideoPlaceholder'
import { useAppStore } from '@/store/useAppStore'
import { useToastStore } from '@/store/useToastStore'
import { useCameraStateStore } from '@/store/useCameraStateStore'

const AVAILABLE_PLUGINS = [
  "ANPRPlugin",
  "ParkingDetectionPlugin",
  "IntrusionDetectionPlugin",
  "PeopleCountingPlugin",
  "AttendanceDetectionPlugin",
  "EnterpriseSafetyPlugin",

  "GestureDetectionPlugin"
];

const CameraFeatureFilter = ({ cameraId }: { cameraId: string }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [allowedPlugins, setAllowedPlugins] = useState<string[]>([]);
  const [isAll, setIsAll] = useState(true);

  useEffect(() => {
    fetch('/api/config')
      .then(res => res.json())
      .then(data => {
        const plugins = data?.CAMERA_PLUGINS?.[cameraId];
        if (plugins && Array.isArray(plugins) && plugins.length > 0) {
          setAllowedPlugins(plugins);
          setIsAll(false);
        } else {
          setIsAll(true);
        }
      });
  }, [cameraId]);

  const togglePlugin = (pluginName: string) => {
    let newPlugins = [...allowedPlugins];
    if (isAll) {
      newPlugins = AVAILABLE_PLUGINS.filter(p => p !== pluginName);
      setIsAll(false);
    } else {
      if (newPlugins.includes(pluginName)) {
        newPlugins = newPlugins.filter(p => p !== pluginName);
      } else {
        newPlugins.push(pluginName);
      }
    }
    
    if (newPlugins.length === 0) {
      setIsAll(true);
      newPlugins = [];
    }

    setAllowedPlugins(newPlugins);
    fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        updates: {
          CAMERA_PLUGINS: {
            [cameraId]: newPlugins
          }
        }
      })
    });
  };

  return (
    <div className="relative pointer-events-auto">
      <button 
        onClick={(e) => { e.stopPropagation(); setIsOpen(!isOpen); }}
        className="p-1.5 bg-black/40 hover:bg-primary/40 rounded backdrop-blur border border-white/10 transition-colors"
        title="Filter Features"
      >
        <SlidersHorizontal size={14} className="text-white" />
      </button>
      
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-56 bg-black/90 backdrop-blur-xl border border-white/10 rounded-xl overflow-hidden shadow-2xl z-50 p-2" onClick={(e) => e.stopPropagation()}>
          <div className="text-xs font-bold text-white/50 mb-2 px-2 uppercase tracking-wider">Active Analytics</div>
          <div className="max-h-60 overflow-y-auto flex flex-col gap-1">
            {AVAILABLE_PLUGINS.map(plugin => {
              const active = isAll || allowedPlugins.includes(plugin);
              return (
                <button
                  key={plugin}
                  onClick={() => togglePlugin(plugin)}
                  className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-white/10 text-left w-full transition-colors"
                >
                  <div className={`w-4 h-4 rounded border flex items-center justify-center ${active ? 'bg-primary border-primary' : 'border-white/20'}`}>
                    {active && <Check size={12} className="text-white" />}
                  </div>
                  <span className={`text-xs ${active ? 'text-white' : 'text-white/50'}`}>
                    {plugin.replace('Plugin', '')}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}


export const CameraCard = memo(({ id, name, location }: any) => {
  const { activeCameraId, setActiveCamera } = useAppStore()
  const { addToast } = useToastStore()
  const personCount = useCameraStateStore(state => {
    const events = state.states[id]?.events?.PeopleCountingPlugin;
    if (!events) return 0;
    for (const event of events) {
      if (event.event_type === "PERSON_COUNT") {
        return event.metadata?.current_people_in_frame || 0;
      }
    }
    return 0;
  })
  
  const isActive = activeCameraId === id;

  return (
    <div 
      className={cn(
        "w-full h-full relative group overflow-hidden rounded-2xl transition-all duration-500",
        isActive ? "ring-2 ring-primary glow-primary border-transparent glass-pro shadow-[0_0_40px_rgba(0,112,243,0.3)]" : "glass hover-lift border border-white/5 hover:border-white/20"
      )}
      onClick={() => setActiveCamera(isActive ? null : id)}
    >
      {/* Top Overlay */}
      <div className="absolute top-0 inset-x-0 p-4 bg-gradient-to-b from-black/80 via-black/40 to-transparent z-10 flex justify-between items-start pointer-events-none transition-opacity duration-300">
        <div className="flex flex-col gap-2">
          <div className="flex flex-col gap-1.5">
            <span className="font-bold text-sm text-white drop-shadow-lg flex items-center gap-2 tracking-wide">
              {name}
              <span className="text-[10px] bg-white/10 px-2 py-0.5 rounded text-white/70 uppercase tracking-widest">{location}</span>
            </span>
            <div className="flex gap-2">
              <span className="flex items-center gap-1.5 text-[10px] bg-danger/20 text-danger border border-danger/30 px-2 py-0.5 rounded shadow-sm uppercase font-black tracking-widest">
                <span className="w-1.5 h-1.5 rounded-full bg-danger animate-pulse glow-danger" /> LIVE
              </span>
              <span className="flex items-center gap-1.5 text-[10px] bg-accent/20 text-accent border border-accent/30 px-2 py-0.5 rounded shadow-sm uppercase font-black tracking-widest glow-accent">
                AI ACTIVE
              </span>
            </div>
          </div>

          {/* Conditional Check In / Check Out Buttons */}
          {isActive && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }} 
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-1.5 mt-1 pointer-events-auto"
            >
              <button 
                onClick={(e) => { 
                  e.stopPropagation();
                  fetch('/events/manual', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ camera_id: id, event_type: 'info', description: `Manual check-in recorded for ${name}` })
                  });
                  addToast({ title: 'Checked In', message: `Manual check-in recorded for ${name}`, type: 'success', cameraName: name })
                }}
                className="px-2 py-1 bg-success/90 hover:bg-success text-success-foreground text-[10px] font-bold rounded shadow-sm transition-colors border border-success/50"
                title="Check In"
              >
                CI
              </button>
              <button 
                onClick={(e) => { 
                  e.stopPropagation();
                  fetch('/events/manual', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ camera_id: id, event_type: 'warning', description: `Manual check-out recorded for ${name}` })
                  });
                  addToast({ title: 'Checked Out', message: `Manual check-out recorded for ${name}`, type: 'warning', cameraName: name })
                }}
                className="px-2 py-1 bg-danger/90 hover:bg-danger text-danger-foreground text-[10px] font-bold rounded shadow-sm transition-colors border border-danger/50"
                title="Check Out"
              >
                CO
              </button>
            </motion.div>
          )}
        </div>
        
        {/* Top Right: Controls & Info */}
        <div className="flex flex-col items-end gap-1.5 pointer-events-none">
          <div className="flex items-center gap-1.5 pointer-events-auto">
            <CameraFeatureFilter cameraId={id} />
            <div className="flex items-center gap-1.5 text-[10px] bg-black/60 border border-white/10 px-2 py-1 rounded backdrop-blur-sm text-white font-mono shadow-md">
              <Users className="w-3 h-3 text-primary" />
              <span className="font-semibold text-gray-300">CW:</span>
              <span className={cn(
                "font-bold",
                personCount > 10 ? "text-danger" : personCount > 5 ? "text-warning" : "text-success"
              )}>
                {personCount}
              </span>
            </div>
            <Signal className="w-4 h-4 text-success drop-shadow-md" />
          </div>
        </div>
      </div>

      {/* Video Content */}
      <VideoPlayer cameraId={id} streamUrl="mock" poster="https://images.unsplash.com/photo-1577962917302-cd874c4e31d2?auto=format&fit=crop&q=80&w=640" />

      {/* Bottom Overlay - Telemetry HUD */}
      <div className="absolute bottom-0 inset-x-0 p-4 bg-gradient-to-t from-black/90 via-black/50 to-transparent z-10 flex justify-between items-end pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <div className="flex gap-5 text-[10px] text-white/50 font-mono tracking-widest">
          <span className="flex flex-col gap-0.5"><span>FPS</span><strong className="text-white text-xs">60</strong></span>
          <span className="flex flex-col gap-0.5"><span>LATENCY</span><strong className="text-success text-xs">12ms</strong></span>
          <span className="flex flex-col gap-0.5"><span>BITRATE</span><strong className="text-white text-xs">4.2M</strong></span>
          <span className="flex flex-col gap-0.5"><span>RES</span><strong className="text-white text-xs">4K</strong></span>
        </div>
        <span className="text-[10px] text-white/30 font-mono uppercase tracking-widest">ID:{id.substring(0,8)}</span>
      </div>

      {/* Floating Controls (Right) */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        whileHover={{ opacity: 1, x: 0 }}
        className="absolute right-2 top-1/2 -translate-y-1/2 flex flex-col gap-2 z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-auto"
      >
        {[
          { icon: Maximize, label: 'Fullscreen', action: (e: any) => { e.currentTarget.closest('.group')?.requestFullscreen() } },
          { icon: CameraIcon, label: 'Snapshot', action: () => addToast({ title: 'Hardware Error', message: 'Hardware not supported by this camera model.', type: 'danger' }) },
          { icon: Video, label: 'Record', action: () => addToast({ title: 'Hardware Error', message: 'Hardware not supported by this camera model.', type: 'danger' }) },
          { icon: Crosshair, label: 'PTZ', action: () => addToast({ title: 'Hardware Error', message: 'Hardware not supported by this camera model.', type: 'danger' }) },
          { icon: Mic, label: 'Mic', action: () => addToast({ title: 'Hardware Error', message: 'Hardware not supported by this camera model.', type: 'danger' }) },
          { icon: Volume2, label: 'Audio', action: () => addToast({ title: 'Hardware Error', message: 'Hardware not supported by this camera model.', type: 'danger' }) },
          { icon: PictureInPicture, label: 'PIP', action: () => addToast({ title: 'Picture-in-Picture', message: 'Feature coming soon.', type: 'default' }) },
          { icon: Settings, label: 'Settings', action: () => addToast({ title: 'Hardware Error', message: 'Hardware not supported by this camera model.', type: 'danger' }) }
        ].map((btn, i) => (
          <motion.button whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }} key={i} onClick={(e) => { e.stopPropagation(); btn.action(e); }} className="p-2 bg-black/60 hover:bg-primary backdrop-blur-sm border border-white/10 rounded-lg text-white/80 hover:text-white transition-all shadow-lg group/btn relative">
            <btn.icon className="w-4 h-4" />
            <span className="absolute right-full mr-2 top-1/2 -translate-y-1/2 px-2 py-1 bg-black/80 text-[10px] rounded opacity-0 group-hover/btn:opacity-100 pointer-events-none whitespace-nowrap">
              {btn.label}
            </span>
          </motion.button>
        ))}
      </motion.div>
    </div>
  )
})

CameraCard.displayName = 'CameraCard'
