import { Save, Plus, Camera } from 'lucide-react'
import { useState } from 'react'
import { useToastStore } from '@/store/useToastStore'

export function Settings() {
  const [activeTab, setActiveTab] = useState('Cameras')
  const [cameraName, setCameraName] = useState('')
  const [rtspUrl, setRtspUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { addToast } = useToastStore()

  const handleAddCamera = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!cameraName || !rtspUrl) return

    setIsSubmitting(true)
    try {
      const res = await fetch('http://localhost:8000/cameras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: cameraName, rtsp_url: rtspUrl })
      })

      if (res.ok) {
        addToast({ title: 'Camera Added', message: `Successfully connected to ${cameraName}`, type: 'success' })
        setCameraName('')
        setRtspUrl('')
      } else {
        throw new Error('Failed to add camera')
      }
    } catch (error) {
      addToast({ title: 'Connection Error', message: 'Could not connect to camera stream.', type: 'danger' })
    } finally {
      setIsSubmitting(false)
    }
  }
  return (
    <div className="p-8 h-full overflow-y-auto max-w-5xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-1">System Settings</h1>
          <p className="text-muted-foreground">Manage global configuration, cameras, and AI policies.</p>
        </div>
        <button onClick={() => addToast({ title: 'Settings Saved', message: 'Global configuration has been updated successfully.', type: 'success' })} className="flex items-center gap-2 px-6 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20">
          <Save className="w-4 h-4" /> Save Changes
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
        <div className="col-span-1 flex flex-col gap-2 border-r border-border pr-4">
          {['General', 'Cameras', 'Streaming', 'AI Models', 'Video', 'Audio', 'Recording'].map((tab, i) => (
            <button 
              key={tab} 
              onClick={() => setActiveTab(tab)}
              className={`text-left px-4 py-2.5 rounded-lg font-medium text-sm transition-all ${activeTab === tab ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="col-span-1 md:col-span-3 glass rounded-2xl p-8 border-border">
          {activeTab === 'General' && (
            <>
              <h2 className="text-xl font-semibold mb-6">General Configuration</h2>
              
              <div className="space-y-6">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-muted-foreground">System Name</label>
                  <input type="text" defaultValue="HQ Primary Server" className="bg-background border border-border rounded-lg px-4 py-2 focus:outline-none focus:ring-1 focus:ring-primary w-full max-w-md" />
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-muted-foreground">Location</label>
                  <input type="text" defaultValue="Datacenter Alpha" className="bg-background border border-border rounded-lg px-4 py-2 focus:outline-none focus:ring-1 focus:ring-primary w-full max-w-md" />
                </div>

                <div className="flex items-center gap-4 py-4 border-t border-border mt-6">
                  <div className="flex-1">
                    <h3 className="font-medium">Enable Global AI Processing</h3>
                    <p className="text-sm text-muted-foreground">Turn on tensor processing across all live feeds by default.</p>
                  </div>
                  <div className="w-12 h-6 bg-primary rounded-full relative cursor-pointer">
                    <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full" />
                  </div>
                </div>
                
                <div className="flex items-center gap-4 py-4 border-t border-border">
                  <div className="flex-1">
                    <h3 className="font-medium">Strict Privacy Mode</h3>
                    <p className="text-sm text-muted-foreground">Automatically blur faces in exported video clips.</p>
                  </div>
                  <div className="w-12 h-6 bg-muted rounded-full relative cursor-pointer border border-border">
                    <div className="absolute left-1 top-1 w-4 h-4 bg-muted-foreground rounded-full" />
                  </div>
                </div>
              </div>
            </>
          )}

          {activeTab === 'Cameras' && (
            <>
              <div className="flex items-center gap-2 mb-6">
                <Camera className="w-6 h-6 text-primary" />
                <h2 className="text-xl font-semibold">Connect New Camera</h2>
              </div>
              <p className="text-sm text-muted-foreground mb-6">Add a new RTSP stream. It will be instantly connected and passed through the AI detection pipeline.</p>
              
              <form onSubmit={handleAddCamera} className="space-y-6 max-w-md bg-muted/20 p-6 rounded-xl border border-border">
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-foreground">Camera Name</label>
                  <input 
                    type="text" 
                    value={cameraName}
                    onChange={(e) => setCameraName(e.target.value)}
                    placeholder="e.g. Front Gate" 
                    className="bg-background border border-border rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-primary/50 w-full" 
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
                    className="bg-background border border-border rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-primary/50 w-full font-mono text-sm" 
                    required
                  />
                  <p className="text-xs text-muted-foreground">Credentials containing special characters will be automatically encoded.</p>
                </div>

                <button 
                  type="submit" 
                  disabled={isSubmitting}
                  className="w-full flex justify-center items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed mt-4"
                >
                  <Plus className="w-4 h-4" /> {isSubmitting ? 'Connecting...' : 'Add Camera Stream'}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
