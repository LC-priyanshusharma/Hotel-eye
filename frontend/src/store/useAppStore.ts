import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'dark' | 'light' | 'colorful'

interface AppState {
  sidebarOpen: boolean
  toggleSidebar: () => void
  rightPanelOpen: boolean
  toggleRightPanel: () => void
  activeCameraId: string | null
  setActiveCamera: (id: string | null) => void
  theme: Theme
  cycleTheme: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      rightPanelOpen: false,
      toggleRightPanel: () => set((state) => ({ rightPanelOpen: !state.rightPanelOpen })),
      activeCameraId: null,
      setActiveCamera: (id) => set({ activeCameraId: id }),
      theme: 'dark',
      cycleTheme: () => set((state) => {
        const themes: Theme[] = ['dark', 'light', 'colorful'];
        const currentIndex = themes.indexOf(state.theme);
        const nextIndex = (currentIndex + 1) % themes.length;
        return { theme: themes[nextIndex] };
      }),
    }),
    {
      name: 'logiceye-app-storage',
      partialize: (state) => ({ theme: state.theme }), // Only persist the theme
    }
  )
)
