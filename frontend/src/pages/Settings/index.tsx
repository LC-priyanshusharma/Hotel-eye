import { Save, Plus, Camera, Users, ShieldAlert, UserPlus, Loader2, Sliders } from 'lucide-react'
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useToastStore } from '@/store/useToastStore'
import { useAuth } from '../../contexts/AuthContext'
import { useUsers } from '../../api/hooks/useUsers'
import { api } from '../../api/api'
import { ZoneDrawer } from '../../components/ZoneDrawer'

function CameraStatusList() {
  const [statuses, setStatuses] = useState<Record<string, string>>({})
  
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await api.get('/cameras/status')
        if (res.data) setStatuses(res.data)
      } catch (e) {
        console.error(e)
      }
    }
    fetchStatus()
    const int = setInterval(fetchStatus, 3000)
    return () => clearInterval(int)
  }, [])

  return (
    <div className="glass-panel p-6 rounded-2xl border border-white/10 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full blur-[40px] pointer-events-none -mt-10 -mr-10" />
      <h3 className="text-xs font-bold tracking-widest uppercase text-foreground mb-4 drop-shadow-md">Live Connections</h3>
      {Object.keys(statuses).length === 0 ? (
        <p className="text-sm text-muted-foreground italic">No cameras configured or backend unreachable.</p>
      ) : (
        <div className="space-y-3 relative z-10">
          {Object.entries(statuses).map(([url, status]) => (
            <div key={url} className="flex flex-col gap-1 bg-black/40 p-4 rounded-xl border border-white/5 hover:bg-black/60 transition-colors">
              <span className="text-sm font-medium truncate text-white" title={url}>{url}</span>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${status === 'Connected' ? 'bg-success animate-pulse glow-success' : 'bg-warning animate-pulse glow-warning'}`} />
                <span className={`text-[10px] font-bold tracking-widest uppercase ${status === 'Connected' ? 'text-success' : 'text-warning'}`}>{status}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

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
      const res = await api.post('/api/cameras', { name: cameraName, rtsp_url: rtspUrl })

      if (res.status === 200) {
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
    <div className="p-8 pb-24 h-full overflow-y-auto custom-scrollbar relative">
      <div className="absolute top-0 left-0 w-full h-96 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />

      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-between items-end mb-10 relative z-10"
      >
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight mb-2 text-gradient">System Settings</h1>
          <p className="text-muted-foreground font-medium tracking-wide">Manage global configuration, cameras, and AI policies.</p>
        </div>
        <button onClick={handleSaveConfig} className="flex items-center gap-2 px-6 py-2.5 bg-primary text-white rounded-xl font-bold hover:bg-primary/90 transition-all shadow-lg glow-primary hover-lift">
          <Save className="w-4 h-4" /> Save Configuration
        </button>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-8 relative z-10">
        <div className="col-span-1 flex flex-col gap-2">
          {['General', 'Cameras', 'Streaming', 'AI Models', 'Video', 'Audio', 'Recording', ...(isAdmin ? ['Users & Roles'] : [])].map((tab) => (
            <button 
              key={tab} 
              onClick={() => setActiveTab(tab)}
              className={cn(
                "text-left px-5 py-3 rounded-xl font-bold text-sm transition-all relative overflow-hidden group",
                activeTab === tab 
                  ? "bg-primary text-white shadow-lg glow-primary" 
                  : "text-muted-foreground hover:text-white glass-panel border border-white/5 hover:border-white/20"
              )}
            >
              {activeTab === tab && (
                <motion.div layoutId="settingsTab" className="absolute inset-0 bg-white/10" />
              )}
              <span className="relative z-10">{tab}</span>
            </button>
          ))}
        </div>

        <div className="col-span-1 md:col-span-3 glass-pro rounded-3xl p-8 border border-white/10 relative overflow-hidden min-h-[500px]">
          <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-[60px] pointer-events-none -mr-20 -mt-20" />
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
            >
          {activeTab === 'General' && (
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-8">
                <div className="p-2.5 bg-primary/20 text-primary rounded-xl border border-primary/30 shadow-lg">
                   <Sliders className="w-5 h-5" />
                </div>
                <h2 className="text-xl font-bold text-white tracking-wide">General Configuration</h2>
              </div>
              
              {configLoading ? (
                 <div className="flex justify-center p-12"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
              ) : (
                <div className="space-y-6">
                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-bold tracking-widest uppercase text-muted-foreground">AI Confidence Threshold (0.0 to 1.0)</label>
                    <input 
                      type="number" 
                      step="0.05"
                      value={backendConfig.CONFIDENCE_THRESHOLD || 0.4} 
                      onChange={e => setBackendConfig({...backendConfig, CONFIDENCE_THRESHOLD: parseFloat(e.target.value)})}
                      className="bg-black/50 text-white border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 w-full max-w-md transition-all shadow-inner" 
                    />
                  </div>

                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-bold tracking-widest uppercase text-muted-foreground">Loitering Threshold (Seconds)</label>
                    <input 
                      type="number" 
                      value={backendConfig.LOITERING_THRESHOLD_SECONDS || 10} 
                      onChange={e => setBackendConfig({...backendConfig, LOITERING_THRESHOLD_SECONDS: parseFloat(e.target.value)})}
                      className="bg-black/50 text-white border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 w-full max-w-md transition-all shadow-inner" 
                    />
                  </div>
                  
                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-bold tracking-widest uppercase text-muted-foreground">Frame Skip (Process 1 in X frames)</label>
                    <input 
                      type="number" 
                      value={backendConfig.FRAME_SKIP || 3} 
                      onChange={e => setBackendConfig({...backendConfig, FRAME_SKIP: parseInt(e.target.value)})}
                      className="bg-black/50 text-white border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 w-full max-w-md transition-all shadow-inner" 
                    />
                  </div>

                  <div className="flex items-center gap-4 py-6 border-t border-white/5 mt-8">
                    <div className="flex-1">
                      <h3 className="font-bold text-white tracking-wide mb-1">Enable Gesture Detection</h3>
                      <p className="text-sm text-muted-foreground">Turn on gesture tracking (Hands/Poses) across all live feeds.</p>
                    </div>
                    <div 
                      onClick={() => setBackendConfig({...backendConfig, GESTURE_ENABLED: !backendConfig.GESTURE_ENABLED})}
                      className={`w-14 h-7 rounded-full relative cursor-pointer shadow-inner transition-colors duration-300 ${backendConfig.GESTURE_ENABLED ? 'bg-primary glow-primary' : 'bg-black/50 border border-white/10'}`}
                    >
                      <motion.div 
                        layout
                        className="absolute top-1 w-5 h-5 bg-white rounded-full shadow-md"
                        initial={false}
                        animate={{ x: backendConfig.GESTURE_ENABLED ? 26 : 4 }}
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'Cameras' && (
            <>
              <div className="flex items-center gap-2 mb-6">
                <Camera className="w-6 h-6 text-primary" />
                <h2 className="text-xl font-semibold">Camera Connections</h2>
              </div>
              <p className="text-sm text-muted-foreground mb-6">Manage RTSP streams and view connection status.</p>
              
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                {/* Add Camera Form */}
                <form onSubmit={handleAddCamera} className="space-y-6 max-w-md bg-muted/20 p-6 rounded-xl border border-border h-fit">
                  <h3 className="font-medium text-foreground mb-2">Connect New Camera</h3>
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

                {/* Camera Status List */}
                <CameraStatusList />
              </div>
            </>
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
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
