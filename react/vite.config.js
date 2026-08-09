import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// base './' 相对路径 —— GitHub Pages 部署在子路径 /samc-dashboard/ 下也能工作
export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
  server: { host: '127.0.0.1', port: 5199 },
  build: { outDir: 'dist', assetsDir: 'assets' },
})
