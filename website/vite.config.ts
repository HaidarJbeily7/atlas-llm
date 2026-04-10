import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  publicDir: 'public',
  build: {
    // Exclude raw experiment data from build — only summary.json + findings/ are needed
    copyPublicDir: true,
  },
})
