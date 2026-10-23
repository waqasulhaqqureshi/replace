import { useEffect, useRef, useState } from 'react'
import type { TimelineEvent } from './types'

/**
 * useActiveEvents — the timestamp trigger layer.
 *
 * Runs off the rAF clock and only calls setState when the *set of active
 * events changes*, so a 60fps playhead never re-renders the React tree.
 * Also fires semantic callbacks (onEnter / onExit) which is what you would
 * wire to sound, analytics, or a downstream composition.
 */
export function useActiveEvents(
  events: TimelineEvent[],
  clock: React.MutableRefObject<number>,
  opts: {
    enabled?: boolean
    offset?: number
    onEnter?: (ev: TimelineEvent) => void
    onExit?: (ev: TimelineEvent) => void
  } = {},
) {
  const { enabled = true, offset = 0, onEnter, onExit } = opts
  const [active, setActive] = useState<TimelineEvent[]>([])
  const ids = useRef<Set<string>>(new Set())

  useEffect(() => {
    let raf = 0
    const tick = () => {
      const t = clock.current + offset
      const next = new Set<string>()
      if (enabled) {
        for (const ev of events) if (t >= ev.t0 && t <= ev.t1) next.add(ev.id)
      }
      let changed = next.size !== ids.current.size
      if (!changed) {
        for (const id of next) if (!ids.current.has(id)) { changed = true; break }
      }
      if (changed) {
        const prev = ids.current
        ids.current = next
        onEnter && events.forEach((e) => next.has(e.id) && !prev.has(e.id) && onEnter(e))
        onExit && events.forEach((e) => prev.has(e.id) && !next.has(e.id) && onExit(e))
        setActive(events.filter((e) => next.has(e.id)))
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [events, enabled, offset])

  return active
}

/** Chapter lookup that only updates when the chapter actually changes. */
export function useChapter(chapters: { id: string; t0: number; t1: number; title: string; sub: string }[], clock: React.MutableRefObject<number>) {
  const [idx, setIdx] = useState(0)
  const current = useRef(0)
  useEffect(() => {
    let raf = 0
    const tick = () => {
      const t = clock.current
      const i = chapters.findIndex((c) => t >= c.t0 && t < c.t1)
      const next = i < 0 ? Math.max(0, chapters.length - 1) : i
      if (next !== current.current) {
        current.current = next
        setIdx(next)
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [chapters, clock])
  return { chapter: chapters[idx], index: idx }
}
