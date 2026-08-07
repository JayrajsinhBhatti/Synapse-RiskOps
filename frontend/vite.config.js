import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// =====================================================
// Synapse RiskOps - Vite Configuration
// =====================================================
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0', // Required for Docker
    proxy: {
      // Proxy API calls to Spring Boot backend during development
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
});
