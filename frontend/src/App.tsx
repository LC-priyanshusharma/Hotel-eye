

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


import React, { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "20px", color: "white", backgroundColor: "black", height: "100vh", overflow: "auto" }}>
          <h1 style={{ color: "red" }}>Oops, React crashed!</h1>
          <p>Please take a screenshot of this error and send it to the agent:</p>
          <pre style={{ color: "lime", backgroundColor: "#222", padding: "10px" }}>
            {this.state.error?.toString()}
          </pre>
          <pre style={{ color: "pink", backgroundColor: "#222", padding: "10px" }}>
            {this.state.errorInfo?.componentStack}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  const connect = useCameraStateStore(state => state.connect)
  const disconnect = useCameraStateStore(state => state.disconnect)
  const theme = useAppStore(state => state.theme)
  
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [])

  return (
    <ErrorBoundary>
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
    </ErrorBoundary>
  )
}

export default App
