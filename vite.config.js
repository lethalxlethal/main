import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// В режиме разработки /api и /media проксируются на Django.
// Адрес можно поменять переменной окружения DEV_API_TARGET.
const target = process.env.DEV_API_TARGET || 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': { target, changeOrigin: true },
      '/media': { target, changeOrigin: true },
    },
  },
});
