import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Bind to all interfaces so the app is reachable from another machine
    // on the LAN (e.g. http://SERVER-IP:5173), not just localhost.
    host: true,
    port: 5173,
  },
})
