import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// The dev server proxies /api to Django so the browser talks to a single origin
// during development; CORS then only matters for non-proxy setups
// (docs/07-security.md section 1 keeps origins explicit).
//
// The target is overridable: inside docker-compose the backend is a sibling
// container (http://backend:8000), while on the host it is localhost:8000.
// Hardcoding localhost would break the proxy inside the container, because
// localhost there is the container itself.
const apiProxyTarget = process.env.VITE_DEV_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'node',
    // Component tests opt into jsdom per file with a `@vitest-environment jsdom`
    // docblock; pure logic tests stay on the faster node environment.
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
