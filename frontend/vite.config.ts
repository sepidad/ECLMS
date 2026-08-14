import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        // Use explicit IPv4 so Windows does not resolve localhost to an
        // unreachable IPv6 loopback while Docker publishes the API on IPv4.
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
