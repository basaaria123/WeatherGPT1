import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// The dev server proxies /api to FastAPI (websockets included), so local
// development never depends on the backend's CORS configuration.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
          ws: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      chunkSizeWarningLimit: 1200,
      rollupOptions: {
        output: {
          // Three.js and Leaflet are heavy and rarely change; keep them out of
          // the main bundle so first paint is not waiting on them.
          manualChunks(id) {
            if (!id.includes('node_modules')) return undefined
            if (/[\\/]node_modules[\\/](three|@react-three)[\\/]/.test(id)) return 'three'
            if (/[\\/]node_modules[\\/](leaflet|react-leaflet)[\\/]/.test(id)) return 'maps'
            return undefined
          },
        },
      },
    },
  }
})
