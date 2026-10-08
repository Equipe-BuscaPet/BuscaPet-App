import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // usePolling: no Docker em Windows/macOS os eventos de arquivo não chegam ao container,
  // e sem isso o Vite continua servindo a versão antiga depois de uma edição.
  server: { host: true, port: 5173, watch: { usePolling: true, interval: 300 } },
})
