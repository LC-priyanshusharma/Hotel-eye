import { useState, useEffect } from 'react'
import { CameraCard } from '@/components/camera/CameraCard'
import { LayoutGrid, Grid3X3, Grid2X2, Grid, LayoutTemplate, Plus, X, Play, Square } from 'lucide-react'
import { cn } from '@/utils/utils'
import { api } from '@/api/api'
import { LiveNotificationSidebar } from './LiveNotificationSidebar'

const PRESET_LAYOUTS = [
  { id: '1x1', icon: LayoutTemplate, label: '1 Cam', cols: 1, cameras: 1 },
  { id: '2x2', icon: Grid2X2, label: '4 Cams', cols: 2, cameras: 4 },
  { id: '3x3', icon: Grid3X3, label: '9 Cams', cols: 3, cameras: 9 },
  { id: '4x4', icon: Grid, label: '16 Cams', cols: 4, cameras: 16 },
  { id: '5x5', icon: LayoutGrid, label: '25 Cams', cols: 5, cameras: 25 },
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
  const [sourceType, setSourceType] = useState<'rtsp' | 'video_file'>('video_file')
  const [selectedPlugins, setSelectedPlugins] = useState<string[]>([
    "IntrusionDetectionPlugin",
    "PPEDetectionPlugin",
    "PeopleCountingPlugin"
  ])
  const [isSubmitting, setIsSubmitting] = useState(false)

  const fetchCameras = () => {
    api.get('/api/cameras')
      .then(res => res.data)
      .then(data => {
        if (data && data.status === 'success' && Array.isArray(data.cameras)) {
          setBackendCameras(data.cameras)
        }
      })
      .catch(err => console.error("Failed to fetch active cameras", err))
  }

  const [pipelineStatuses, setPipelineStatuses] = useState<Record<string, string>>({})

  useEffect(() => {
    fetchCameras()
    
    const fetchStatuses = () => {
      api.get(`/api/cameras/status?t=${Date.now()}`)
        .then(res => res.data)
        .then(data => {
          if (data) setPipelineStatuses(data)
        })
        .catch(err => console.error("Failed to fetch camera statuses", err))
    }
    
    fetchStatuses()
    const interval = setInterval(fetchStatuses, 3000)
    return () => clearInterval(interval)
  }, [])
  
  const handleAddCamera = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!cameraName || !rtspUrl) return

    setIsSubmitting(true)
    try {
      const res = await api.post('/api/cameras', { 
        name: cameraName, 
        rtsp_url: rtspUrl,
        source_type: sourceType,
        source: rtspUrl
      })
      if (res.status === 200) {
        const newCameraId = res.data.camera_id || res.data.camera?.id;
        if (newCameraId) {
          // Configure plugins if selected
          if (selectedPlugins.length > 0) {
            try {
              await api.post('/api/config', {
                updates: { CAMERA_PLUGINS: { [newCameraId]: selectedPlugins } }
              })
            } catch (e) {
              console.warn("Could not set initial plugins", e)
            }
          }
          // Immediately start pipeline on backend
          try {
            await api.post('/api/cameras/start', { camera_id: newCameraId });
          } catch (e) {
            console.error("Failed to auto-start camera", e);
          }
        }
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
  
  // Use real backend IDs
  const allCameraIds = Array.from(new Set(backendCameras.map((c: any) => c.id)))
  
  const cameras = allCameraIds
    .filter(camId => camId !== 'SYSTEM')
    .map((camId, idx) => {
    const dbCam = backendCameras.find((c: any) => c.id === camId)
    const name = dbCam ? dbCam.name : `Camera ${idx + 1}`
    
    return {
      id: camId,
      name,
      location: `Zone ${idx + 1}`
    }
  })

  const handleLayoutChange = (preset: typeof PRESET_LAYOUTS[0]) => {
    setActiveLayout(preset)
  }

  return (
    <div className="flex h-full w-full bg-transparent overflow-hidden">
      {/* Main Grid Area */}
      <div className="flex flex-col flex-1 overflow-hidden relative">
        {/* Toolbar */}
        <div className="h-14 glass-panel border-b border-foreground/5 flex items-center justify-between px-6 shrink-0 z-10">
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
                onClick={async () => {
                  try {
                    await api.post('/api/cameras/start-all');
                    // Force refresh statuses after a short delay
                    setTimeout(() => fetchCameras(), 500);
                  } catch (err) { console.error(err) }
                }}
                className="flex items-center gap-2 px-4 py-1.5 bg-success/20 hover:bg-success/40 text-success hover:text-white rounded-lg text-xs font-bold transition-all border border-success/30 glow-success hover-lift"
              >
                <Play className="w-4 h-4 fill-current" /> Start All
              </button>
              
              <button
                onClick={async () => {
                  try {
                    await api.post('/api/cameras/stop-all');
                  } catch (err) { console.error(err) }
                }}
                className="flex items-center gap-2 px-4 py-1.5 bg-danger/20 hover:bg-danger/40 text-danger hover:text-white rounded-lg text-xs font-bold transition-all border border-danger/30 glow-danger hover-lift"
              >
                <Square className="w-4 h-4 fill-current" /> Stop All
              </button>

              <button
                onClick={() => setIsAddingCamera(true)}
                className="flex items-center gap-2 px-4 py-1.5 bg-primary/20 hover:bg-primary/40 text-primary hover:text-white rounded-lg text-xs font-bold transition-all border border-primary/30 glow-primary hover-lift"
              >
                <Plus className="w-4 h-4" /> Add Stream
              </button>
              
              <div className="flex bg-card/60 p-1.5 rounded-xl border border-foreground/10 shadow-inner backdrop-blur-md gap-1">
              {PRESET_LAYOUTS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => handleLayoutChange(preset)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all",
                  activeLayout.id === preset.id 
                    ? "bg-primary text-white shadow-md glow-primary" 
                    : "text-muted-foreground hover:text-white hover:bg-foreground/5"
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
        <div className="flex-1 overflow-y-auto p-2 flex flex-col relative">
          {activeCameraId && (
            <div className="absolute inset-0 z-20 p-4 flex items-center justify-center bg-background/95 backdrop-blur-sm">
              <div className="w-full h-full max-w-7xl">
                {cameras.filter(c => c.id === activeCameraId).map(cam => (
                  <CameraCard key={`active-${cam.id}`} {...cam} pipelineStatus={pipelineStatuses[cam.id] || "Stopped"} />
                ))}
              </div>
            </div>
          )}

          <div className={cn("w-full h-full p-2 overflow-y-auto custom-scrollbar", activeCameraId ? "invisible pointer-events-none" : "visible")}>
            <div 
              className="grid gap-4 w-full transition-all duration-200"
              style={{
                gridTemplateColumns: `repeat(${activeLayout.cols}, minmax(0, 1fr))`
              }}
            >
              {cameras.map((cam) => (
                <div 
                  key={cam.id} 
                  className={cn(
                    "w-full rounded-2xl overflow-hidden shadow-lg border border-border/40 transition-transform duration-150",
                    activeLayout.cols === 1 ? "h-[75vh]" : activeLayout.cols === 2 ? "h-[380px]" : activeLayout.cols === 3 ? "h-[290px]" : "h-[220px]"
                  )}
                >
                  <CameraCard {...cam} pipelineStatus={pipelineStatuses[cam.id] || "Stopped"} />
                </div>
              ))}
            </div>
          </div>
        </div>
        
        {/* Add Camera Modal Overlay */}
        {isAddingCamera && (
          <div className="absolute inset-0 z-50 bg-background/80 backdrop-blur-md flex items-center justify-center p-4">
            <div className="glass-pro rounded-2xl p-8 w-full max-w-md shadow-2xl relative border border-foreground/10">
              <button 
                onClick={() => setIsAddingCamera(false)}
                className="absolute top-4 right-4 text-muted-foreground hover:text-white bg-foreground/5 p-2 rounded-full transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
              
              <h3 className="font-extrabold text-xl text-white mb-2 tracking-tight">Add Video Stream</h3>
              <p className="text-sm text-muted-foreground mb-8">Connect a new RTSP stream or upload a test video source.</p>
              
              <form onSubmit={handleAddCamera} className="space-y-4 max-h-[80vh] overflow-y-auto pr-1 custom-scrollbar">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-foreground">Camera / Stream Name</label>
                  <input 
                    type="text" 
                    value={cameraName}
                    onChange={(e) => setCameraName(e.target.value)}
                    placeholder="e.g. Front Gate or Video 1" 
                    className="bg-muted/30 border border-border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary/50 w-full" 
                    required
                  />
                </div>

                {/* Source Type Selector */}
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-foreground">Source Type</label>
                  <div className="grid grid-cols-2 gap-2 bg-muted/20 p-1 rounded-xl border border-border/50">
                    <button
                      type="button"
                      onClick={() => setSourceType('video_file')}
                      className={cn(
                        "py-2 text-xs font-semibold rounded-lg transition-all text-center",
                        sourceType === 'video_file' 
                          ? "bg-primary text-primary-foreground shadow-md shadow-primary/20" 
                          : "text-muted-foreground hover:text-foreground hover:bg-background/40"
                      )}
                    >
                      📁 Local Video (MP4)
                    </button>
                    <button
                      type="button"
                      onClick={() => setSourceType('rtsp')}
                      className={cn(
                        "py-2 text-xs font-semibold rounded-lg transition-all text-center",
                        sourceType === 'rtsp' 
                          ? "bg-primary text-primary-foreground shadow-md shadow-primary/20" 
                          : "text-muted-foreground hover:text-foreground hover:bg-background/40"
                      )}
                    >
                      📹 RTSP Stream
                    </button>
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-foreground">
                    {sourceType === 'video_file' ? 'Local Video File Path' : 'RTSP Stream URL'}
                  </label>
                  <input 
                    type="text" 
                    value={rtspUrl}
                    onChange={(e) => setRtspUrl(e.target.value)}
                    placeholder={sourceType === 'video_file' ? "/home/user/Videos/1.mp4" : "rtsp://admin:pass@192.168.1.100/stream"} 
                    className="bg-muted/30 border border-border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary/50 w-full font-mono text-sm" 
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    {sourceType === 'video_file' 
                      ? "Path to any local .mp4 file on the Jetson machine."
                      : "Credentials containing special characters will be automatically encoded."}
                  </p>
                </div>

                {/* Analytics Selection */}
                <div className="flex flex-col gap-2 pt-2 border-t border-border/50">
                  <div className="flex justify-between items-center">
                    <label className="text-sm font-medium text-foreground">Select Analytics (Optional)</label>
                    <span className="text-xs text-muted-foreground">{selectedPlugins.length} selected</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 max-h-36 overflow-y-auto pr-1 custom-scrollbar">
                    {[
                      { id: "IntrusionDetectionPlugin", label: "Intrusion" },
                      { id: "PPEDetectionPlugin", label: "PPE Safety" },
                      { id: "FireDetectionPlugin", label: "Fire & Smoke" },
                      { id: "ANPRPlugin", label: "ANPR Plate" },
                      { id: "PeopleCountingPlugin", label: "People Counting" },
                      { id: "ParkingAnalyticsPlugin", label: "Parking" },
                      { id: "AttendanceDetectionPlugin", label: "Attendance" },
                      { id: "VisitorPlugin", label: "Visitor" },
                      { id: "CartonCountingPlugin", label: "Carton Counting" },
                      { id: "RestrictionZonePlugin", label: "Restriction Zone" },
                    ].map(plugin => {
                      const isSelected = selectedPlugins.includes(plugin.id);
                      return (
                        <button
                          key={plugin.id}
                          type="button"
                          onClick={() => {
                            setSelectedPlugins(prev => 
                              isSelected ? prev.filter(p => p !== plugin.id) : [...prev, plugin.id]
                            );
                          }}
                          className={cn(
                            "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium text-left transition-all",
                            isSelected 
                              ? "border-primary/50 bg-primary/10 text-primary" 
                              : "border-border/60 bg-muted/20 text-muted-foreground hover:bg-muted/40 hover:text-foreground"
                          )}
                        >
                          <div className={cn(
                            "w-2 h-2 rounded-full",
                            isSelected ? "bg-primary" : "bg-muted-foreground/30"
                          )} />
                          <span className="truncate">{plugin.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <button 
                  type="submit" 
                  disabled={isSubmitting}
                  className="w-full flex justify-center items-center gap-2 px-6 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20 disabled:opacity-50 mt-2"
                >
                  <Plus className="w-4 h-4" /> {isSubmitting ? 'Connecting...' : 'Add & Start Stream'}
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
