import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './layouts/Layout'
import { Dashboard } from './pages/Dashboard'
import { LiveCameras } from './pages/LiveCameras'
import { Analytics, Events } from './pages/EventsAndAnalytics'
import { GarbageAnalytics } from './pages/GarbageAnalytics'
import { QueueAnalytics } from './pages/QueueAnalytics'
import { ParkingAnalytics } from './pages/ParkingAnalytics'
import { AttendanceAnalytics } from './pages/AttendanceAnalytics'
import { FireAnalytics } from './pages/FireAnalytics'
import { Settings } from './pages/Settings'
import { Login } from './pages/Login'
import { AuthProvider } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'

import { useEffect } from 'react'
import { useCameraStateStore } from './store/useCameraStateStore'

function App() {
  const connect = useCameraStateStore(state => state.connect)
  const disconnect = useCameraStateStore(state => state.disconnect)
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [])

  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="cameras" element={<LiveCameras />} />
              <Route path="events" element={<Events />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="garbage" element={<GarbageAnalytics />} />
              <Route path="queue" element={<QueueAnalytics />} />
              <Route path="parking" element={<ParkingAnalytics />} />
              <Route path="attendance" element={<AttendanceAnalytics />} />
              <Route path="fire" element={<FireAnalytics />} />
              <Route path="maps" element={<div className="p-8 text-white"><h1 className="text-2xl font-bold">Maps Integration</h1><p className="text-muted-foreground mt-2">Facility mapping module is currently under construction.</p></div>} />
              <Route path="playback" element={<div className="p-8 text-white"><h1 className="text-2xl font-bold">NVR Playback</h1><p className="text-muted-foreground mt-2">Historical video playback module is currently under construction.</p></div>} />
              <Route path="settings" element={<Settings />} />
            </Route>
          </Route>
          
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
