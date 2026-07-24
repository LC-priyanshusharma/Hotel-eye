import { useState, useEffect } from 'react'
import { Responsive, WidthProvider } from 'react-grid-layout/legacy'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import { CameraCard } from '@/components/camera/CameraCard'
import { LayoutGrid, Grid3X3, Grid2X2, Grid, LayoutTemplate, Plus, X } from 'lucide-react'
import { cn } from '@/utils/utils'
import { api } from '@/api/api'
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
  const [backendCameras, setBackendCameras] = useState<{id: string, name: string, rtsp_url: string}[]>([])
  const [isAddingCamera, setIsAddingCamera] = useState(false)
  const [cameraName, setCameraName] = useState('')
  const [rtspUrl, setRtspUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const fetchCameras = () => {
    fetch('/api/cameras')
      .then(res => res.json())
      .then(data => {
        if (data && data.status === 'success' && Array.isArray(data.cameras)) {
          setBackendCameras(data.cameras)
        }
      })
      .catch(err => console.error("Failed to fetch active cameras", err))
  }

  useEffect(() => {
    fetchCameras()
  }, [])
  
  const handleAddCamera = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!cameraName || !rtspUrl) return

    setIsSubmitting(true)
    try {
      const res = await api.post('/api/cameras', { name: cameraName, rtsp_url: rtspUrl })
      if (res.status === 200) {
        fetchCameras()
        setCameraName('')
        setRtspUrl('')
        setIsAddingCamera(false)
      }
    } catch (error) {
      console.error(error)
    } finally {
      setIsSubmitting(false)
    }
  }
  
  const allCameraIds = Array.from(new Set([...(cameraIdsStr ? cameraIdsStr.split(',') : []), ...backendCameras.map(c => c.rtsp_url)]))
  
  const cameras = allCameraIds
    .filter(camId => camId !== 'SYSTEM')
    .map((camId, idx) => {
    const dbCam = backendCameras.find(c => c.rtsp_url === camId)
    let name = dbCam ? dbCam.name : `Camera ${idx + 1}`
    
    if (!dbCam) {
      if (camId.includes('hlo.mp4')) name = 'ANPR Camera'
      else if (camId.includes('.mp4')) name = 'Camera 1 Test Video'
      if (camId.includes('192.168.1.121')) name = 'Camera 2 Lobby'
      if (camId.includes('192.168.1.122')) name = 'Camera 3 Room'
    }
    
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
        <div className="h-14 glass-panel border-b border-white/5 flex items-center justify-between px-6 shrink-0 z-10">
          <div className="flex items-center gap-3">
            <span className="font-bold text-sm tracking-widest uppercase text-foreground drop-shadow-md">NVR Grid Control</span>
            {activeCameraId && (
              <button 
                onClick={() => setActiveCamera(null)}
                className="ml-4 px-4 py-1.5 bg-primary/10 text-primary border border-primary/30 text-xs font-bold rounded-full shadow-[0_0_15px_rgba(0,112,243,0.1)] hover:bg-primary hover:text-white hover:shadow-[0_0_20px_rgba(0,112,243,0.4)] hover-lift transition-all"
              >
                ← Return to Grid
              </button>
            )}
          </div>
          
          {!activeCameraId && (
            <div className="flex items-center gap-4">
              <button
                onClick={() => setIsAddingCamera(true)}
                className="flex items-center gap-2 px-4 py-1.5 bg-primary/20 hover:bg-primary/40 text-primary hover:text-white rounded-lg text-xs font-bold transition-all border border-primary/30 glow-primary hover-lift"
              >
                <Plus className="w-4 h-4" /> Add Stream
              </button>
              
              <div className="flex bg-[#0A0A0A]/60 p-1.5 rounded-xl border border-white/10 shadow-inner backdrop-blur-md gap-1">
              {PRESET_LAYOUTS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => handleLayoutChange(preset)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all",
                  activeLayout.id === preset.id 
                    ? "bg-primary text-white shadow-md glow-primary" 
                    : "text-muted-foreground hover:text-white hover:bg-white/5"
                )}
                title={preset.label}
              >
                <preset.icon className="w-4 h-4" />
                <span className="hidden sm:inline uppercase tracking-wider text-[10px]">{preset.label}</span>
              </button>
            ))}
            </div>
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
        
        {/* Add Camera Modal Overlay */}
        {isAddingCamera && (
          <div className="absolute inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
            <div className="glass-pro rounded-2xl p-8 w-full max-w-md shadow-2xl relative border border-white/10">
              <button 
                onClick={() => setIsAddingCamera(false)}
                className="absolute top-4 right-4 text-muted-foreground hover:text-white bg-white/5 p-2 rounded-full transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
              
              <h3 className="font-extrabold text-xl text-white mb-2 tracking-tight">Add Video Stream</h3>
              <p className="text-sm text-muted-foreground mb-8">Connect a new RTSP stream or upload a test video source.</p>
              
              <form onSubmit={handleAddCamera} className="space-y-6">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-foreground">Camera Name</label>
                  <input 
                    type="text" 
                    value={cameraName}
                    onChange={(e) => setCameraName(e.target.value)}
                    placeholder="e.g. Front Gate" 
                    className="bg-muted/30 border border-border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary/50 w-full" 
                    required
                  />
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-foreground">RTSP URL</label>
                  <input 
                    type="text" 
                    value={rtspUrl}
                    onChange={(e) => setRtspUrl(e.target.value)}
                    placeholder="rtsp://admin:pass@192.168.1.100/stream" 
                    className="bg-muted/30 border border-border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary/50 w-full font-mono text-sm" 
                    required
                  />
                  <p className="text-xs text-muted-foreground">Credentials containing special characters will be automatically encoded.</p>
                </div>

                <button 
                  type="submit" 
                  disabled={isSubmitting}
                  className="w-full flex justify-center items-center gap-2 px-6 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20 disabled:opacity-50 mt-2"
                >
                  <Plus className="w-4 h-4" /> {isSubmitting ? 'Connecting...' : 'Add Camera'}
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
      
      {/* Right Side Notification Panel */}
      <LiveNotificationSidebar />
    </div>
  )
}
