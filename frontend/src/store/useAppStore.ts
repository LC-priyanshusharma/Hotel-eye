import { create } from 'zustand'

interface AppState {
  sidebarOpen: boolean
  toggleSidebar: () => void
  rightPanelOpen: boolean
  toggleRightPanel: () => void
  activeCameraId: string | null
  setActiveCamera: (id: string | null) => void
  theme: 'dark' | 'light'
  toggleTheme: () => void
}

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  rightPanelOpen: false,
  toggleRightPanel: () => set((state) => ({ rightPanelOpen: !state.rightPanelOpen })),
  activeCameraId: null,
  setActiveCamera: (id) => set({ activeCameraId: id }),
  theme: 'dark',
  toggleTheme: () => set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),
}))
