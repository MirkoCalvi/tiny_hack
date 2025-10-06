import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync, existsSync } from 'node:fs'

export default defineConfig(({ command }) => {
  const isServe = command === 'serve'
  const hasCerts = existsSync('./localhost+2-key.pem') && existsSync('./localhost+2.pem')

  return {
    plugins: [react()],
    server: {
      port: 3000,
      open: true,
      https: isServe && hasCerts
        ? {
            key: readFileSync('./localhost+2-key.pem'),
            cert: readFileSync('./localhost+2.pem')
          }
        : false,
      host: true
    },
    build: {
      outDir: 'dist',
      sourcemap: true
    }
  }
})