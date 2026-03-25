import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendTarget = process.env.VITE_BACKEND_TARGET || 'http://127.0.0.1:8000'
const backendRoutes = [
  '/health',
  '/api',
  '/route-input',
  '/analyze-complaint',
  '/analyze-scam',
  '/service-info',
  '/service-guidance',
  '/voice-to-text',
  '/dashboard-data',
  '/map-data',
  '/clusters',
  '/generate-report',
  '/history',
]

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(
      backendRoutes.map((route) => [
        route,
        {
          target: backendTarget,
          changeOrigin: true,
        },
      ]),
    ),
  },
})
