import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // MIME 타입 및 SPA 라우팅 문제 해결
  server: {
    mimeTypes: {
      'js': 'application/javascript',
      'mjs': 'application/javascript'
    }
  },
  build: {
    // Netlify 배포용
    rollupOptions: {
      output: {
        manualChunks: undefined
      }
    }
  },
  base: './'
})