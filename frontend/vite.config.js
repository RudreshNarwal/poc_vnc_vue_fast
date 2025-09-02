import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    target: 'esnext',
    rollupOptions: {
      external: []
    }
  },
  optimizeDeps: {
    include: ['@novnc/novnc'],
    force: true
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      // API proxy
      '/api': {
        target: 'http://app:8000',
        changeOrigin: true
      },
      // WebSocket proxy for automation control
      '/ws': {
        target: 'ws://app:8000',
        ws: true,
        changeOrigin: true
      },
      // VNC WebSocket and HTTP interface
      '/websockify': {
        target: 'ws://app:7900',
        ws: true,
        changeOrigin: true
      },
      '/vnc.html': {
        target: 'http://app:7900',
        changeOrigin: true
      },
      // Static files
      '/screenshots': {
        target: 'http://app:8000',
        changeOrigin: true
      },
      '/uploads': {
        target: 'http://app:8000',
        changeOrigin: true
      }
    }
  }
})
