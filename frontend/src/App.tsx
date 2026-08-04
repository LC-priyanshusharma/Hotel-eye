

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from './layouts/Layout'
import { Dashboard } from './pages/Dashboard'
import { LiveCameras } from './pages/LiveCameras'
import { Analytics, Events } from './pages/EventsAndAnalytics'

import { ParkingAnalytics } from './pages/ParkingAnalytics'
import { AttendanceAnalytics } from './pages/AttendanceAnalytics'
import { FireAnalytics } from './pages/FireAnalytics'
import { CartonAnalytics } from './pages/CartonAnalytics'
import PPEAnalytics from './pages/PPEAnalytics';
import ANPRAnalytics from './pages/ANPRAnalytics';
import VisitorAnalytics from './pages/VisitorAnalytics';
import RegisteredVisitors from './pages/RegisteredVisitors';
import EmployeeDirectory from './pages/EmployeeDirectory';
import VisitorRegistration from './pages/VisitorRegistration';
import { Settings } from './pages/Settings'
import { Login } from './pages/Login'
import { AuthProvider } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'

import { useEffect } from 'react'
import { useCameraStateStore } from './store/useCameraStateStore'
import { useAppStore } from './store/useAppStore'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 30, // 30 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  const connect = useCameraStateStore(state => state.connect)
  const disconnect = useCameraStateStore(state => state.disconnect)
  const theme = useAppStore(state => state.theme)
  
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<VisitorRegistration />} />
          
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="cameras" element={<LiveCameras />} />
              <Route path="events" element={<Events />} />
              <Route path="analytics" element={<Analytics />} />

              <Route path="parking" element={<ParkingAnalytics />} />
              <Route path="attendance" element={<AttendanceAnalytics />} />
              <Route path="fire" element={<FireAnalytics />} />
              <Route path="carton" element={<CartonAnalytics />} />
              <Route path="ppe" element={<PPEAnalytics />} />
              <Route path="anpr" element={<ANPRAnalytics />} />
              <Route path="visitor" element={<VisitorAnalytics />} />
              <Route path="visitor-db" element={<RegisteredVisitors />} />
              <Route path="employee-db" element={<EmployeeDirectory />} />

              <Route path="settings" element={<Settings />} />
            </Route>
          </Route>
          
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster theme={theme === 'colorful' ? 'light' : theme} position="bottom-right" />
    </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
