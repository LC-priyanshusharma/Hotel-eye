import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from "path"

export default defineConfig({
  plugins: [
    tailwindcss(),
    react()
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },

  server: {
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://106.201.231.217:8000',
        changeOrigin: true
      },
      '/auth': {
        target: 'http://106.201.231.217:8000',
        changeOrigin: true
      },
      '/users': {
        target: 'http://106.201.231.217:8000',
        changeOrigin: true
      },
      '/roles': {
        target: 'http://106.201.231.217:8000',
        changeOrigin: true
      },
      '/events': {
        target: 'http://106.201.231.217:8000',
        changeOrigin: true
      },
      '/analytics': {
        target: 'http://106.201.231.217:8000',
        changeOrigin: true
      },
      '/snapshots': {
        target: 'http://106.201.231.217:8000',
        changeOrigin: true
      },
      '/video': {
        target: 'http://106.201.231.217:8000',
        changeOrigin: true
      },
      '/kill-stream': {
        target: 'http://106.201.231.217:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://106.201.231.217:8000',
        ws: true
      }
    }
  }
})
