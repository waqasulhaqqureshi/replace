import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import timelineJson from './data/timeline.json'
import waveformJson from './data/waveform.json'
import type { Timeline, TimelineEvent, Waveform } from './lib/types'
import { useActiveEvents, useChapter } from './lib/useActiveEvents'
import { useVideoClock } from './lib/useVideoClock'
import { TimelineOverlay } from './overlay/TimelineOverlay'
import { Overview } from './ui/Overview'
import { SceneIndex } from './ui/SceneIndex'
import { Telemetry } from './ui/Telemetry'
import { Transport } from './ui/Transport'

const timeline = timelineJson as unknown as Timeline
const wave = waveformJson as unknown as Waveform
const DEFAULT_SRC = '/media/Deepseek%20strikes%20again.mp4'

export default function App() {
  const [src, setSrc] = useState(DEFAULT_SRC)
  const clock = useVideoClock(src)
  const [overlayOn, setOverlayOn] = useState(true)
  const [offset, setOffset] = useState(0)
  const [stage, setStage] = useState({ w: 1280, h: 720, scale: 1 })
  const wrap = useRef<HTMLDivElement>(null)
  const [dragging, setDragging] = useState(false)

  const { chapter, index: chapterIndex } = useChapter(timeline.chapters, clock.t)
  const active = useActiveEvents(timeline.events, clock.t, { enabled: overlayOn, offset })

  /** Broadcast beat boundaries so any host page can hook sound / analytics. */
  const emit = useCallback((type: 'enter' | 'exit', ev: TimelineEvent) => {
    window.dispatchEvent(new CustomEvent(`dg:${type}`, { detail: ev }))
  }, [])

  // fit the 16:9 stage to whatever room the layout gives it
  useEffect(() => {
    const el = wrap.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      const w = el.clientWidth
      const h = w * (9 / 16)
      setStage({ w, h, scale: w / 1280 })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const seek = useCallback((t: number) => clock.seek(t), [clock])

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f && f.type.startsWith('video/')) setSrc(URL.createObjectURL(f))
  }

  const progressPct = useMemo(
    () => (clock.duration ? (clock.time / clock.duration) * 100 : 0),
    [clock.time, clock.duration],
  )

  return (
    <div className="mx-auto flex min-h-full max-w-[1680px] flex-col gap-3 p-3 lg:p-5">
      <header className="flex flex-wrap items-end gap-x-4 gap-y-2">
        <div>
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.28em] text-cyan">
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-cyan" />
            timeline-synced motion graphics
          </div>
          <h1 className="mt-1 font-display text-2xl font-extrabold leading-none tracking-tight text-paper lg:text-[28px]">
            DeepSeek V4.1-Flash · 1017 <span className="text-muted">/ live overlay player</span>
          </h1>
        </div>
        <div className="ml-auto flex items-center gap-3 font-mono text-[10px] text-muted">
          <span>{timeline.events.length} beats</span>
          <span className="text-line">|</span>
          <span>{timeline.chapters.length} chapters</span>
          <span className="text-line">|</span>
          <span>{timeline.source_stats.cuts} cuts detected</span>
          <span className="text-line">|</span>
          <span className="text-lime">60 fps</span>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_400px]">
        {/* ---------------- video stage ---------------- */}
        <div className="flex flex-col gap-3">
          <div
            ref={wrap}
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={`relative overflow-hidden rounded-xl border bg-black scanlines vignette ${
              dragging ? 'border-cyan' : 'border-line/80'
            }`}
            style={{ aspectRatio: '16 / 9' }}
          >
            <video
              ref={clock.videoRef}
              src={src}
              className="absolute inset-0 h-full w-full object-contain"
              playsInline
              preload="metadata"
              onClick={clock.toggle}
            />
            {overlayOn && (
              <TimelineOverlay
                timeline={timeline}
                wave={wave}
                clock={clock.t}
                enabled={overlayOn}
                offset={offset}
                scale={stage.scale}
                onEnter={(ev) => emit('enter', ev)}
                onExit={(ev) => emit('exit', ev)}
              />
            )}
            {!clock.playing && clock.time === 0 && (
              <button
                onClick={clock.play}
                className="absolute inset-0 grid place-items-center bg-void/50 backdrop-blur-[1px]"
              >
                <span className="flex items-center gap-3 rounded-full bg-cyan px-5 py-3 font-display text-sm font-extrabold text-void shadow-glow">
                  <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
                  Play with graphics
                </span>
              </button>
            )}
            {/* live chapter chip */}
            <div className="pointer-events-none absolute left-3 top-3 flex items-center gap-2 rounded-md bg-void/70 px-2 py-1 backdrop-blur">
              <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-muted">
                CH {String(chapterIndex + 1).padStart(2, '0')}
              </span>
              <span className="font-mono text-[10px] text-paper">{chapter.title}</span>
            </div>
          </div>

          <Transport
            clock={clock}
            overlayOn={overlayOn}
            setOverlayOn={setOverlayOn}
            offset={offset}
            setOffset={setOffset}
          />

          <Overview timeline={timeline} wave={wave} clock={clock.t} onSeek={seek} />

          <Telemetry timeline={timeline} active={active} clock={clock.t} chapter={chapter} />
        </div>

        {/* ---------------- scene index ---------------- */}
        <div className="min-h-[520px] xl:h-[calc(100vh-140px)]">
          <SceneIndex timeline={timeline} clock={clock.t} onSeek={seek} />
        </div>
      </div>

      <footer className="flex flex-wrap items-center gap-x-4 gap-y-1 pb-2 font-mono text-[9.5px] text-muted/70">
        <span>source · {timeline.brand.source} · {timeline.brand.resolution} · {timeline.duration_hms}</span>
        <span className="text-line">|</span>
        <span>progress {progressPct.toFixed(1)}%</span>
        <span className="text-line">|</span>
        <span>drop any video file on the stage to re-sync</span>
      </footer>
    </div>
  )
}
