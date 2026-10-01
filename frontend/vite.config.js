import { svelte } from '@sveltejs/vite-plugin-svelte'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import { readFileSync } from 'fs'
import { resolve } from 'path'

// Read version from Python single source of truth
function getAppVersion() {
  try {
    const versionPy = readFileSync(resolve(__dirname, '..', 'app', 'version.py'), 'utf-8');
    const match = versionPy.match(/__version__\s*=\s*"([^"]+)"/);
    if (match) return match[1];
  } catch (_) {}
  return '0.0.0';
}

// https://vite.dev/config/
export default defineConfig({
  base: './',
  plugins: [tailwindcss(), svelte()],
  define: {
    __APP_VERSION__: JSON.stringify(getAppVersion())
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:58850',
        changeOrigin: true
      },
      '/v1': {
        target: 'http://127.0.0.1:58850',
        changeOrigin: true
      },
      '/sync': {
        target: 'http://127.0.0.1:58850',
        changeOrigin: true,
        ws: true
      }
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
})
