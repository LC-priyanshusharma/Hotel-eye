import { Save, Plus, Camera, Users, ShieldAlert, UserPlus, Loader2 } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useToastStore } from '@/store/useToastStore'
import { useAuth } from '../../contexts/AuthContext'
import { useUsers } from '../../api/hooks/useUsers'
import { api } from '../../api/api'
import { ZoneDrawer } from '../../components/ZoneDrawer'

export function Settings() {
  const [activeTab, setActiveTab] = useState('Cameras')
  const [cameraName, setCameraName] = useState('')
  const [rtspUrl, setRtspUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { addToast } = useToastStore()
  const { user } = useAuth()
  
  const [newUserEmail, setNewUserEmail] = useState('')
  const [newUserPassword, setNewUserPassword] = useState('')
  const { users, roles, isLoading: usersLoading, fetchUsers, fetchRoles, createUser, assignRole, error: usersError } = useUsers()
  
  const [backendConfig, setBackendConfig] = useState<any>({})
  const [configLoading, setConfigLoading] = useState(true)
  
  // Verify admin access
  const isAdmin = user?.is_superuser || user?.roles?.includes('users:manage')

  useEffect(() => {
    if (activeTab === 'Users & Roles' && isAdmin) {
      fetchUsers()
      fetchRoles()
    }
  }, [activeTab, isAdmin, fetchUsers, fetchRoles])

  useEffect(() => {
    if (isAdmin) {
      const loadConfig = async () => {
        try {
          const res = await api.get('/api/config')
          setBackendConfig(res.data)
        } catch (e) {
          addToast({ title: 'Config Error', message: 'Failed to load backend config', type: 'danger' })
        } finally {
          setConfigLoading(false)
        }
      }
      loadConfig()
    }
  }, [isAdmin, addToast])
  const handleSaveConfig = async () => {
    try {
      await api.post('/api/config', { updates: backendConfig })
      addToast({ title: 'Settings Saved', message: 'Global configuration has been updated successfully.', type: 'success' })
    } catch (e) {
      addToast({ title: 'Save Error', message: 'Failed to save config', type: 'danger' })
    }
  }

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
        <button onClick={handleSaveConfig} className="flex items-center gap-2 px-6 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20">
          <Save className="w-4 h-4" /> Save Changes
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
        <div className="col-span-1 flex flex-col gap-2 border-r border-border pr-4">
          {['General', 'Cameras', 'Zone Configurator', 'Streaming', 'AI Models', 'Video', 'Audio', 'Recording', ...(isAdmin ? ['Users & Roles'] : [])].map((tab) => (
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
              
              {configLoading ? (
                 <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
              ) : (
                <div className="space-y-6">
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium text-muted-foreground">AI Confidence Threshold (0.0 to 1.0)</label>
                    <input 
                      type="number" 
                      step="0.05"
                      value={backendConfig.CONFIDENCE_THRESHOLD || 0.4} 
                      onChange={e => setBackendConfig({...backendConfig, CONFIDENCE_THRESHOLD: parseFloat(e.target.value)})}
                      className="bg-background border border-border rounded-lg px-4 py-2 focus:outline-none focus:ring-1 focus:ring-primary w-full max-w-md" 
                    />
                  </div>

                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium text-muted-foreground">Loitering Threshold (Seconds)</label>
                    <input 
                      type="number" 
                      value={backendConfig.LOITERING_THRESHOLD_SECONDS || 10} 
                      onChange={e => setBackendConfig({...backendConfig, LOITERING_THRESHOLD_SECONDS: parseFloat(e.target.value)})}
                      className="bg-background border border-border rounded-lg px-4 py-2 focus:outline-none focus:ring-1 focus:ring-primary w-full max-w-md" 
                    />
                  </div>
                  
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium text-muted-foreground">Frame Skip (Process 1 in X frames)</label>
                    <input 
                      type="number" 
                      value={backendConfig.FRAME_SKIP || 3} 
                      onChange={e => setBackendConfig({...backendConfig, FRAME_SKIP: parseInt(e.target.value)})}
                      className="bg-background border border-border rounded-lg px-4 py-2 focus:outline-none focus:ring-1 focus:ring-primary w-full max-w-md" 
                    />
                  </div>

                  <div className="flex items-center gap-4 py-4 border-t border-border mt-6">
                    <div className="flex-1">
                      <h3 className="font-medium">Enable Gesture Detection</h3>
                      <p className="text-sm text-muted-foreground">Turn on gesture tracking (Hands/Poses) across all live feeds.</p>
                    </div>
                    <div 
                      onClick={() => setBackendConfig({...backendConfig, GESTURE_ENABLED: !backendConfig.GESTURE_ENABLED})}
                      className={`w-12 h-6 rounded-full relative cursor-pointer ${backendConfig.GESTURE_ENABLED ? 'bg-primary' : 'bg-muted border border-border'}`}
                    >
                      <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${backendConfig.GESTURE_ENABLED ? 'right-1' : 'left-1 bg-muted-foreground'}`} />
                    </div>
                  </div>
                </div>
              )}
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

          {activeTab === 'Zone Configurator' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold mb-1">Interactive Zones</h2>
                <p className="text-sm text-muted-foreground mb-6">Draw parking spots or restricted areas visually over the camera feed.</p>
                {!backendConfig?.CAMERA_URLS && (
                  <div className="bg-red-500/20 p-4 rounded-lg mb-4 text-red-400 text-sm">
                    Warning: CAMERA_URLS is missing from backend config! 
                    Raw config keys received: {Object.keys(backendConfig || {}).join(', ')}
                  </div>
                )}
              </div>

              {(typeof backendConfig?.CAMERA_URLS === 'string' ? backendConfig.CAMERA_URLS : "0").split(',').map((cam: string, i: number) => {
                const url = cam.trim();
                const rawPoints = backendConfig.RESTRICTED_ZONES?.[url] || backendConfig.RESTRICTED_ZONES?.['default'] || [];
                const parsedPoints = rawPoints.map((p: any) => ({ x: p[0], y: p[1] }));
                
                return (
                  <div key={i} className="glass p-6 rounded-2xl">
                    <ZoneDrawer 
                      title={`Intrusion Zone - Camera ${i + 1}`}
                      streamUrl={`http://localhost:8000/video?camera_id=${encodeURIComponent(url)}&t=${Date.now()}`}
                      points={parsedPoints}
                      onChange={(newPoints) => {
                        const newConfig = { ...backendConfig };
                        if (!newConfig.RESTRICTED_ZONES) newConfig.RESTRICTED_ZONES = {};
                        newConfig.RESTRICTED_ZONES[url] = newPoints.map(p => [Math.round(p.x), Math.round(p.y)]);
                        setBackendConfig(newConfig);
                      }}
                    />
                  </div>
                )
              })}
            </div>
          )}

          {activeTab === 'Users & Roles' && isAdmin && (
            <>
              <div className="flex items-center gap-2 mb-6 border-b border-border pb-4">
                <Users className="w-6 h-6 text-primary" />
                <h2 className="text-xl font-semibold">User Management</h2>
              </div>
              
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                
                {/* Users List */}
                <div className="xl:col-span-2">
                  <h3 className="font-medium mb-4 flex items-center justify-between">
                    Active Operators
                    <button onClick={fetchUsers} className="text-xs text-primary hover:underline">Refresh</button>
                  </h3>
                  
                  {usersError && (
                    <div className="bg-danger/10 border border-danger/20 text-danger p-3 rounded-lg text-sm flex items-center gap-2 mb-4">
                      <ShieldAlert className="w-4 h-4 shrink-0" />
                      <span>{usersError}</span>
                    </div>
                  )}

                  <div className="bg-muted/10 border border-border rounded-xl overflow-hidden">
                    <table className="w-full text-sm text-left">
                      <thead className="bg-muted/30 text-muted-foreground text-xs uppercase">
                        <tr>
                          <th className="px-4 py-3 font-medium">User Email</th>
                          <th className="px-4 py-3 font-medium">Role</th>
                          <th className="px-4 py-3 font-medium">Status</th>
                          <th className="px-4 py-3 font-medium text-right">Created</th>
                        </tr>
                      </thead>
                      <tbody>
                        {usersLoading ? (
                          <tr><td colSpan={4} className="px-4 py-8 text-center text-muted-foreground"><Loader2 className="w-5 h-5 animate-spin mx-auto" /></td></tr>
                        ) : users.length === 0 ? (
                          <tr><td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">No users found.</td></tr>
                        ) : (
                          users.map((u) => (
                            <tr key={u.id} className="border-t border-border/50 hover:bg-muted/10 transition-colors">
                              <td className="px-4 py-3 font-medium text-foreground">{u.email}</td>
                              <td className="px-4 py-3">
                                {u.is_superuser ? (
                                  <span className="px-2 py-0.5 rounded-full bg-danger/20 text-danger text-xs">Superuser</span>
                                ) : (
                                  <select 
                                    className="bg-background border border-border rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary w-full max-w-[120px] capitalize"
                                    value={u.roles?.[0] || ''}
                                    onChange={async (e) => {
                                      const success = await assignRole(u.id, e.target.value);
                                      if (success) addToast({ title: 'Role Updated', message: `Updated role for ${u.email}`, type: 'success' });
                                    }}
                                  >
                                    <option value="" disabled>Select Role</option>
                                    {roles.map((r) => (
                                      <option key={r.id} value={r.name}>{r.name}</option>
                                    ))}
                                  </select>
                                )}
                              </td>
                              <td className="px-4 py-3">
                                {u.is_active ? (
                                  <span className="flex items-center gap-1.5 text-xs text-success"><div className="w-1.5 h-1.5 rounded-full bg-success"></div>Active</span>
                                ) : (
                                  <span className="flex items-center gap-1.5 text-xs text-muted-foreground"><div className="w-1.5 h-1.5 rounded-full bg-muted-foreground"></div>Disabled</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-right text-muted-foreground text-xs">{new Date(u.created_at).toLocaleDateString()}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Add User Form */}
                <div className="xl:col-span-1">
                  <div className="bg-muted/20 border border-border rounded-xl p-5">
                    <h3 className="font-medium mb-4 flex items-center gap-2">
                      <UserPlus className="w-4 h-4 text-primary" />
                      Invite Operator
                    </h3>
                    
                    <form onSubmit={async (e) => {
                      e.preventDefault();
                      const success = await createUser(newUserEmail, newUserPassword);
                      if (success) {
                        addToast({ title: 'User Created', message: `${newUserEmail} has been added.`, type: 'success' });
                        setNewUserEmail('');
                        setNewUserPassword('');
                      }
                    }} className="space-y-4">
                      
                      <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-medium text-muted-foreground">Email Address</label>
                        <input 
                          type="email" 
                          value={newUserEmail}
                          onChange={(e) => setNewUserEmail(e.target.value)}
                          placeholder="operator@logiceye.ai" 
                          className="bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary w-full" 
                          required
                        />
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-medium text-muted-foreground">Temporary Password</label>
                        <input 
                          type="password" 
                          value={newUserPassword}
                          onChange={(e) => setNewUserPassword(e.target.value)}
                          placeholder="••••••••" 
                          className="bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary w-full" 
                          required
                        />
                      </div>

                      <button 
                        type="submit" 
                        disabled={usersLoading}
                        className="w-full flex justify-center items-center gap-2 px-4 py-2 bg-primary/20 text-primary hover:bg-primary hover:text-white border border-primary/50 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-2"
                      >
                        {usersLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Plus className="w-4 h-4" /> Create User</>}
                      </button>
                    </form>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
