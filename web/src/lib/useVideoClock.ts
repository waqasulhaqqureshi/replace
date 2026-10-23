import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * useVideoClock — a 60fps, rAF-driven clock derived from an HTMLVideoElement.
 *
 * Why not just read `video.currentTime` during render?
 *  · `timeupdate` fires ~4x/second: far too coarse to drive frame-tight motion.
 *  · `requestVideoFrameCallback` gives exact presented frames, but is Chromium-only.
 *  · Interpolating with rAF fixes both: we sample the element, then advance the
 *    clock by wall time between samples, re-syncing whenever drift exceeds 80ms.
 *
 * Returns a ref-backed clock (`t`), a React state mirror throttled to ~20Hz for
 * UI chrome, and helpers. Motion components read `t` via context without
 * re-rendering the React tree 60 times a second.
 */
export interface VideoClock {
  /** Live playhead in seconds — mutate-free, read inside rAF/GSAP. */
  t: React.MutableRefObject<number>
  /** Throttled mirror for React UI (≈20Hz). */
  time: number
  duration: number
  playing: boolean
  buffered: number
  videoRef: React.RefObject<HTMLVideoElement>
  play: () => void
  pause: () => void
  toggle: () => void
  seek: (t: number) => void
  scrubTo: (t: number) => void
  setRate: (r: number) => void
  rate: number
}

export function useVideoClock(src: string): VideoClock {
  const videoRef = useRef<HTMLVideoElement>(null)
  const t = useRef(0)
  const lastSample = useRef(0)
  const wall = useRef(0)
  const raf = useRef(0)

  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [buffered, setBuffered] = useState(0)
  const [rate, setRateState] = useState(1)

  useEffect(() => {
    const v = videoRef.current
    if (!v) return

    const sync = () => {
      t.current = v.currentTime
      lastSample.current = v.currentTime
      wall.current = performance.now()
    }
    const onLoaded = () => { setDuration(v.duration || 0); sync() }
    const onPlay = () => { sync(); setPlaying(true) }
    const onPause = () => { sync(); setPlaying(false) }
    const onSeeking = () => { sync() }
    const onProgress = () => {
      try {
        if (v.buffered.length) setBuffered(v.buffered.end(v.buffered.length - 1) / (v.duration || 1))
      } catch { /* ignore */ }
    }
    /** Native frame callback when available: gives exact presented-frame time.
     *  It only refreshes the interpolation anchor — it must never schedule
     *  another rAF loop (that would multiply loops on every frame). */
    const onFrame = (_: unknown, meta: { mediaTime: number }) => {
      lastSample.current = meta.mediaTime
      wall.current = performance.now()
      const el = videoRef.current as (HTMLVideoElement & {
        requestVideoFrameCallback?: (cb: typeof onFrame) => number
      }) | null
      el?.requestVideoFrameCallback?.(onFrame)
    }

    v.addEventListener('loadedmetadata', onLoaded)
    v.addEventListener('play', onPlay)
    v.addEventListener('pause', onPause)
    v.addEventListener('seeking', onSeeking)
    v.addEventListener('seeked', sync)
    v.addEventListener('timeupdate', sync)
    v.addEventListener('progress', onProgress)
    v.addEventListener('ratechange', () => setRateState(v.playbackRate))

    let uiClock = 0
    const loop = () => {
      const el = videoRef.current
      if (!el) return
      if (el.paused || el.seeking) {
        t.current = el.currentTime
      } else {
        const now = performance.now()
        const predicted = lastSample.current + ((now - wall.current) / 1000) * el.playbackRate
        // drift guard: never let interpolation run away from the element
        t.current = Math.abs(predicted - el.currentTime) > 0.08 ? el.currentTime : predicted
        if (Math.abs(predicted - el.currentTime) > 0.08) {
          lastSample.current = el.currentTime
          wall.current = now
        }
      }
      // throttle the React mirror so UI re-renders stay cheap
      if (performance.now() - uiClock > 50) {
        uiClock = performance.now()
        setTime(t.current)
      }
      raf.current = requestAnimationFrame(loop)
    }

    const rvfc = (v as HTMLVideoElement & {
      requestVideoFrameCallback?: (cb: typeof onFrame) => number
    }).requestVideoFrameCallback
    if (rvfc) rvfc.call(v, onFrame)
    raf.current = requestAnimationFrame(loop)


    return () => {
      cancelAnimationFrame(raf.current)
      v.removeEventListener('loadedmetadata', onLoaded)
      v.removeEventListener('play', onPlay)
      v.removeEventListener('pause', onPause)
      v.removeEventListener('seeking', onSeeking)
      v.removeEventListener('seeked', sync)
      v.removeEventListener('timeupdate', sync)
      v.removeEventListener('progress', onProgress)
    }
  }, [src])

  const play = useCallback(() => { videoRef.current?.play().catch(() => {}) }, [])
  const pause = useCallback(() => { videoRef.current?.pause() }, [])
  const toggle = useCallback(() => {
    const v = videoRef.current
    if (!v) return
    if (v.paused) v.play().catch(() => {}); else v.pause()
  }, [])
  const seek = useCallback((to: number) => {
    const v = videoRef.current
    if (!v) return
    v.currentTime = Math.max(0, Math.min(to, (v.duration || 0) - 0.05))
    t.current = v.currentTime
  }, [])
  const scrubTo = useCallback((to: number) => {
    // scrubbing: keep the element pinned so the picture follows the thumb
    seek(to)
  }, [seek])
  const setRate = useCallback((r: number) => {
    if (videoRef.current) videoRef.current.playbackRate = r
    setRateState(r)
  }, [])

  return { t, time, duration, playing, buffered, videoRef, play, pause, toggle, seek, scrubTo, setRate, rate }
}
