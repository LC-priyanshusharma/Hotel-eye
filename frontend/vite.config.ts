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
  define: {
    'process.env': {}
  },
  server: {
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/events': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/analytics': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/snapshots': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/video': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/cameras': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
