import { fileURLToPath, URL } from 'node:url'
import { join, dirname } from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import electron from 'vite-plugin-electron';

// 获取当前文件所在目录（ES 模块中替代 __dirname）
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig({
  plugins: [
    vue(),
    electron({
      entry: join(__dirname, 'electron/main.js')
    })
  ],
  base: './',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  css: {},
})