import { useMemo, useState } from 'react'
import { mmss } from '../lib/useFrame'
import type { Timeline, TimelineEvent } from '../lib/types'

const KIND_LABEL: Record<string, string> = {
  id_card: 'Nameplate', lower_third: 'Lower third', callout: 'Callout card',
  stat: 'Metric counter', ring: 'Highlight ring', bracket: 'HUD bracket',
  chapter: 'Chapter type', caption: 'Caption', corner: 'Margin note',
  equation: 'Equation', progress: 'Progress rail', bars: 'Bar chart',
  leaderboard: 'Leaderboard', quadrant: 'Quadrant lens', gauge: 'Gauge',
  donut: 'Donut', speed_hud: 'Speed HUD', ad_break: 'Stinger',
  end_card: 'End card', ticker: 'Ticker rail', waveform: 'Waveform',
}

const dot: Record<string, string> = {
  cyan: 'bg-cyan', electric: 'bg-electric', lime: 'bg-lime',
  amber: 'bg-amber', magenta: 'bg-magenta', paper: 'bg-paper', muted: 'bg-muted',
}

/** SceneIndex — the deliverable timestamp table, rendered from the same JSON
 *  the renderer consumes, so it can never drift from the burned-in output. */
export function SceneIndex({
  timeline, clock, onSeek,
}: { timeline: Timeline; clock: React.MutableRefObject<number>; onSeek: (t: number) => void }) {
  const [q, setQ] = useState('')
  const [kind, setKind] = useState<string>('all')
  const [live, setLive] = useState<string | null>(null)

  const kinds = useMemo(
    () => ['all', ...Array.from(new Set(timeline.events.map((e) => e.kind)))],
    [timeline.events],
  )

  const rows = useMemo(() => {
    const s = q.trim().toLowerCase()
    return timeline.events.filter((e) => {
      if (kind !== 'all' && e.kind !== kind) return false
      if (!s) return true
      return [e.id, e.kind, e.title, e.sub, e.kicker, e.label, e.note]
        .filter(Boolean).join(' ').toLowerCase().includes(s)
    })
  }, [q, kind, timeline.events])

  return (
    <div className="flex h-full min-h-0 flex-col rounded-xl border border-line/80 bg-panel/60">
      <div className="flex flex-wrap items-center gap-2 border-b border-line/70 p-3">
        <h2 className="mr-auto font-display text-sm font-bold tracking-tight text-paper">
          Timestamp scene index
          <span className="ml-2 font-mono text-[10px] font-normal text-muted">{rows.length} beats</span>
        </h2>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="search beats…"
          className="w-40 rounded-md border border-line bg-void/60 px-2 py-1 font-mono text-[10px] text-paper outline-none placeholder:text-muted/60 focus:border-cyan/60"
        />
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value)}
          className="rounded-md border border-line bg-void/60 px-2 py-1 font-mono text-[10px] text-paper outline-none focus:border-cyan/60"
        >
          {kinds.map((k) => <option key={k} value={k}>{k}</option>)}
        </select>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <table className="w-full border-collapse text-left">
          <thead className="sticky top-0 z-10 bg-panel/95 backdrop-blur">
            <tr className="font-mono text-[9px] uppercase tracking-widest text-muted">
              <th className="px-3 py-2 font-normal">in</th>
              <th className="px-2 py-2 font-normal">out</th>
              <th className="px-2 py-2 font-normal">graphic</th>
              <th className="px-2 py-2 font-normal">copy</th>
              <th className="px-2 py-2 font-normal">motion / lum</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((ev) => (
              <Row key={ev.id} ev={ev} clock={clock} onSeek={onSeek} live={live} setLive={setLive} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Row({
  ev, clock, onSeek, live, setLive,
}: {
  ev: TimelineEvent
  clock: React.MutableRefObject<number>
  onSeek: (t: number) => void
  live: string | null
  setLive: (id: string | null) => void
}) {
  const isLive = live === ev.id
  return (
    <tr
      onMouseEnter={() => setLive(ev.id)}
      onMouseLeave={() => setLive(null)}
      onClick={() => onSeek(ev.t0 + 0.6)}
      className={`cursor-pointer border-b border-white/[0.03] transition-colors ${
        isLive ? 'bg-cyan/[0.07]' : 'hover:bg-white/[0.03]'
      }`}
      title={ev.note}
    >
      <td className="whitespace-nowrap px-3 py-1.5 font-mono text-[10px] text-cyan tabnum">{mmss(ev.t0)}</td>
      <td className="whitespace-nowrap px-2 py-1.5 font-mono text-[10px] text-muted tabnum">{mmss(ev.t1)}</td>
      <td className="whitespace-nowrap px-2 py-1.5">
        <span className="flex items-center gap-1.5 font-mono text-[10px] text-paper/85">
          <span className={`h-[5px] w-[5px] rounded-full ${dot[ev.accent]}`} />
          {KIND_LABEL[ev.kind] ?? ev.kind}
        </span>
      </td>
      <td className="max-w-[240px] truncate px-2 py-1.5 text-[11px] text-paper/75">
        {ev.title || ev.kicker || ev.label || '—'}
      </td>
      <td className="whitespace-nowrap px-2 py-1.5 font-mono text-[9.5px] text-muted tabnum">
        {ev.measured ? `${ev.measured.motion.toFixed(1)} · ${ev.measured.lum.toFixed(0)}${ev.note ? ' ↗' : ''}` : '—'}
      </td>
    </tr>
  )
}
