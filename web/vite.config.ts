import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'

/** Repo root — the 27-minute source video lives here, outside web/. */
const REPO = path.resolve(__dirname, '..')

/**
 * Streams the source video (and any rendered overlays) straight out of the
 * repository with HTTP Range support. Range is non-negotiable: <video> seeking
 * and scrubbing both break without 206 responses.
 */
function mediaServer(): Plugin {
  const roots = [path.join(REPO, 'render'), REPO]
  return {
    name: 'media-server',
    configureServer(server) {
      server.middlewares.use('/media', (req, res, next) => {
        const rel = decodeURIComponent((req.url || '/').split('?')[0]).replace(/^\/+/, '')
        const file = roots
          .map((r) => path.join(r, rel))
          .find((p) => fs.existsSync(p) && fs.statSync(p).isFile())
        if (!file) return next()

        const size = fs.statSync(file).size
        const range = req.headers.range
        const type = file.endsWith('.mp4') ? 'video/mp4'
          : file.endsWith('.webm') ? 'video/webm'
          : file.endsWith('.mp3') ? 'audio/mpeg' : 'application/octet-stream'

        if (range) {
          const [s, e] = range.replace(/bytes=/, '').split('-')
          const start = parseInt(s, 10) || 0
          const end = e ? parseInt(e, 10) : size - 1
          res.writeHead(206, {
            'Content-Range': `bytes ${start}-${end}/${size}`,
            'Accept-Ranges': 'bytes',
            'Content-Length': end - start + 1,
            'Content-Type': type,
            'Cache-Control': 'public, max-age=3600',
          })
          fs.createReadStream(file, { start, end }).pipe(res)
        } else {
          res.writeHead(200, {
            'Content-Length': size,
            'Content-Type': type,
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'public, max-age=3600',
          })
          fs.createReadStream(file).pipe(res)
        }
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), mediaServer()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    // the sandbox preview is served from a generated host — accept any origin
    allowedHosts: true,
    fs: { allow: [REPO] },
  },
  build: { target: 'es2020', chunkSizeWarningLimit: 1200 },
})
