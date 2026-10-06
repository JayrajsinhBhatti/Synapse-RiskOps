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
      // Proxy Chatbot API calls to GenAI Agent (port 8001)
      '/api/chatbot': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        secure: false,
      },
      // Proxy other API calls to FastAPI backend during development
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        secure: false,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            // Silently suppress ECONNREFUSED logs while backend/stream is offline
          });
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
});
