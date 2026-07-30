import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  // eslint-disable-next-line no-undef
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      proxy: {
        '^/api': {
          target: env.VITE_API_URL || 'http://api:5050',
          changeOrigin: true
        },
        // 本地检测服务代理（用于摄像头检测）
        // Docker 容器内需要用 host.docker.internal 访问宿主机
        '^/detect-api': {
          target: env.VITE_DETECT_API_URL || 'http://host.docker.internal:8081',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/detect-api/, '')
        }
      },
      watch: {
        usePolling: true,
        ignored: ['**/node_modules/**', '**/dist/**'],
      },
      host: '0.0.0.0',
    }
  }
})
