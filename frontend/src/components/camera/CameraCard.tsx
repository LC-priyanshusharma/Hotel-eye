import { Maximize, Camera as CameraIcon, Video, Crosshair, Mic, Volume2, Settings, PictureInPicture, Signal, Users } from 'lucide-react'
import { memo, useEffect, useState } from 'react'
import { cn } from '@/utils/utils'
import { motion } from 'framer-motion'
import { VideoPlayer } from './VideoPlaceholder'
import { useAppStore } from '@/store/useAppStore'
import { useToastStore } from '@/store/useToastStore'
import { useCameraStateStore } from '@/store/useCameraStateStore'

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
        "w-full h-full relative group overflow-hidden rounded-xl bg-black shadow-md transition-all",
        isActive ? "border-2 border-primary" : "border border-border"
      )}
      onClick={() => setActiveCamera(isActive ? null : id)}
    >
      {/* Top Overlay */}
      <div className="absolute top-0 inset-x-0 p-3 bg-gradient-to-b from-black/80 to-transparent z-10 flex justify-between items-start pointer-events-none">
        <div className="flex flex-col gap-2">
          <div className="flex flex-col gap-1">
            <span className="font-semibold text-sm text-white drop-shadow-md flex items-center gap-2">
              {name}
              <span className="text-[10px] bg-black/50 px-1.5 py-0.5 rounded text-muted-foreground">{location}</span>
            </span>
            <div className="flex gap-2">
              <span className="flex items-center gap-1 text-[10px] bg-danger/20 text-danger border border-danger/50 px-1.5 rounded uppercase font-bold tracking-wider">
                <span className="w-1.5 h-1.5 rounded-full bg-danger animate-pulse" /> Live
              </span>
              <span className="flex items-center gap-1 text-[10px] bg-primary/20 text-primary border border-primary/50 px-1.5 rounded uppercase font-bold tracking-wider">
                AI
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
                  fetch('http://localhost:8000/events/manual', {
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
                  fetch('http://localhost:8000/events/manual', {
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
        
        {/* Top Right: CW & Signal */}
        <div className="flex flex-col items-end gap-1.5 pointer-events-none">
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

      {/* Video Content */}
      <VideoPlayer cameraId={id} streamUrl="mock" poster="https://images.unsplash.com/photo-1577962917302-cd874c4e31d2?auto=format&fit=crop&q=80&w=640" />

      {/* Bottom Overlay */}
      <div className="absolute bottom-0 inset-x-0 p-3 bg-gradient-to-t from-black/90 via-black/50 to-transparent z-10 flex justify-between items-end pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <div className="flex gap-4 text-[10px] text-gray-300 font-mono">
          <span className="flex flex-col"><span>FPS</span><strong className="text-white">30</strong></span>
          <span className="flex flex-col"><span>LATENCY</span><strong className="text-white">45ms</strong></span>
          <span className="flex flex-col"><span>BITRATE</span><strong className="text-white">2.4M</strong></span>
          <span className="flex flex-col"><span>RES</span><strong className="text-white">1080p</strong></span>
        </div>
        <span className="text-[10px] text-gray-500 font-mono">ID:{id}</span>
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
          <button key={i} onClick={(e) => { e.stopPropagation(); btn.action(e); }} className="p-2 bg-black/60 hover:bg-primary backdrop-blur-sm border border-white/10 rounded-lg text-white/80 hover:text-white transition-all group/btn relative">
            <btn.icon className="w-4 h-4" />
            <span className="absolute right-full mr-2 top-1/2 -translate-y-1/2 px-2 py-1 bg-black/80 text-[10px] rounded opacity-0 group-hover/btn:opacity-100 pointer-events-none whitespace-nowrap">
              {btn.label}
            </span>
          </button>
        ))}
      </motion.div>
    </div>
  )
})

CameraCard.displayName = 'CameraCard'
