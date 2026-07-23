import { useState, useEffect } from 'react'
import { Responsive, WidthProvider } from 'react-grid-layout/legacy'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import { CameraCard } from '@/components/camera/CameraCard'
import { LayoutGrid, Grid3X3, Grid2X2, Grid, LayoutTemplate } from 'lucide-react'
import { cn } from '@/utils/utils'
import { LiveNotificationSidebar } from './LiveNotificationSidebar'

const ResponsiveGridLayout = WidthProvider(Responsive)

const PRESET_LAYOUTS = [
  { id: '1x1', icon: LayoutTemplate, label: '1 Cam', cols: 1, cameras: 1 },
  { id: '2x2', icon: Grid2X2, label: '4 Cams', cols: 2, cameras: 4 },
  { id: '3x3', icon: Grid3X3, label: '9 Cams', cols: 3, cameras: 9 },
  { id: '4x4', icon: Grid, label: '16 Cams', cols: 4, cameras: 16 },
  { id: '8x8', icon: LayoutGrid, label: '64 Cams', cols: 8, cameras: 64 },
]

import { useAppStore } from '@/store/useAppStore'
import { useCameraStateStore } from '@/store/useCameraStateStore'

export function LiveCameras() {
  const [activeLayout, setActiveLayout] = useState(PRESET_LAYOUTS[1]) // Default 2x2
  const { activeCameraId, setActiveCamera } = useAppStore()
  
  const cameraIdsStr = useCameraStateStore(state => Object.keys(state.states).join(','))
  
  const cameras = (cameraIdsStr ? cameraIdsStr.split(',') : [])
    .filter(camId => camId !== 'SYSTEM')
    .map((camId, idx) => {
    let name = `Camera ${idx + 1}`
    if (camId.includes('.mp4')) name = 'Camera 1 Test Video'
    if (camId.includes('192.168.1.121')) name = 'Camera 2 Lobby'
    if (camId.includes('192.168.1.122')) name = 'Camera 3 Room'
    return {
      id: camId,
      name
    }
  })

  // Generate react-grid-layout configuration
  const generateLayout = (camList: any[], cols: number) => {
    return camList.map((c, i) => ({
      i: c.id,
      x: i % cols,
      y: Math.floor(i / cols),
      w: 1,
      h: 1,
      minW: 1,
      minH: 1
    }))
  }

  const [layout, setLayout] = useState<any[]>([])
  
  useEffect(() => {
    setLayout(generateLayout(cameras, activeLayout.cols))
  }, [cameras.length, activeLayout.cols])

  // When changing layouts, regenerate grid
  const handleLayoutChange = (preset: typeof PRESET_LAYOUTS[0]) => {
    setActiveLayout(preset)
    setLayout(generateLayout(cameras, preset.cols))
  }

  return (
    <div className="flex h-full w-full bg-transparent overflow-hidden">
      {/* Main Grid Area */}
      <div className="flex flex-col flex-1 overflow-hidden relative">
        {/* Toolbar */}
        <div className="h-12 border-b border-white/5 bg-black/40 backdrop-blur-md flex items-center justify-between px-4 shrink-0 z-10">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">View Configuration</span>
            {activeCameraId && (
              <button 
                onClick={() => setActiveCamera(null)}
                className="ml-4 px-4 py-1.5 bg-primary/20 text-primary border border-primary/50 text-xs font-bold rounded-full shadow-[0_0_15px_rgba(124,58,237,0.3)] hover:bg-primary hover:text-white hover:shadow-[0_0_20px_rgba(124,58,237,0.6)] transition-all"
              >
                ← Back to Grid
              </button>
            )}
          </div>
          
          {!activeCameraId && (
            <div className="flex bg-black/50 p-1 rounded-lg border border-white/10 shadow-inner backdrop-blur-sm">
            {PRESET_LAYOUTS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => handleLayoutChange(preset)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                  activeLayout.id === preset.id 
                    ? "bg-primary text-primary-foreground shadow-sm" 
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                )}
                title={preset.label}
              >
                <preset.icon className="w-4 h-4" />
                <span className="hidden sm:inline">{preset.label}</span>
              </button>
            ))}
          </div>
          )}
        </div>

        {/* Grid Area */}
        <div className="flex-1 overflow-y-auto p-2 flex flex-col">
          {activeCameraId ? (
            <div className="flex-1 w-full p-4 flex items-center justify-center">
              <div className="w-full h-full max-w-7xl">
                {cameras.filter(c => c.id === activeCameraId).map(cam => (
                  <CameraCard key={cam.id} {...cam} />
                ))}
              </div>
            </div>
          ) : (
            <ResponsiveGridLayout
            key={activeLayout.id} // Force re-render on layout change to reset grid proportions
            className="layout"
            layouts={{ lg: layout }}
            breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
            cols={{ lg: activeLayout.cols, md: Math.min(activeLayout.cols, 3), sm: Math.min(activeLayout.cols, 2), xs: 1, xxs: 1 }}
            rowHeight={window.innerHeight / activeLayout.cols - (50 / activeLayout.cols)} // Approximate square aspect ratio
            isDraggable={true}
            isResizable={true}
            margin={[8, 8]}
            onLayoutChange={(newLayout: any) => setLayout(newLayout)}
            useCSSTransforms={true}
          >
            {cameras.map((cam) => (
              <div key={cam.id} className="cursor-move">
                <CameraCard {...cam} />
              </div>
            ))}
          </ResponsiveGridLayout>
          )}
        </div>
      </div>
      
      {/* Right Side Notification Panel */}
      <LiveNotificationSidebar />
    </div>
  )
}
