import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const apiUrl = process.env.VITE_API_URL || 'http://localhost:8000'
const wsUrl = process.env.VITE_WS_URL || apiUrl.replace(/^http/, 'ws')

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': apiUrl,
      '/v1': apiUrl,
      '/ws': {
        target: wsUrl,
        ws: true,
      },
    },
  },
})
