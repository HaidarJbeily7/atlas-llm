import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const BACKEND_URL = process.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  publicDir: 'public',
  build: {
    // Exclude raw experiment data from build — only summary.json + findings/ are needed
    copyPublicDir: true,
  },
  server: {
    proxy: {
      // Forward investigation/annotation API to the FastAPI backend during dev.
      '/api': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
    },
  },
})
