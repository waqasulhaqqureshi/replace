import { AnimatePresence } from 'framer-motion'
import { createContext, useContext } from 'react'
import type { Timeline, TimelineEvent, Waveform } from '../lib/types'
import { useActiveEvents } from '../lib/useActiveEvents'
import { AdBreak, Chapter, Ring, Ticker, Waveform as WaveViz } from './primitives/Motion'
import { Bars, Bracket, Donut, Equation, Gauge, Leaderboard, Progress, Quadrant } from './primitives/Data'
import { Callout, Corner, EndCard, IdCard, SpeedHud, Stat } from './primitives/Cards'

interface SyncCtx {
  clock: React.MutableRefObject<number>
  wave: Waveform
  stage: number
}
const Ctx = createContext<SyncCtx | null>(null)
export const useSync = () => {
  const c = useContext(Ctx)
  if (!c) throw new Error('useSync outside TimelineOverlay')
  return c
}

/**
 * TimelineOverlay — the compositor.
 *
 * The stage is authored at a fixed 1280×720 design resolution (identical to the
 * Python burn-in renderer) and uniformly scaled to the video element, so the
 * web graphics and the burned-in graphics are pixel-equivalent.
 */
export function TimelineOverlay({
  timeline, wave, clock, enabled, offset = 0, scale,
  onEnter, onExit,
}: {
  timeline: Timeline
  wave: Waveform
  clock: React.MutableRefObject<number>
  enabled: boolean
  offset?: number
  scale: number
  onEnter?: (ev: TimelineEvent) => void
  onExit?: (ev: TimelineEvent) => void
}) {
  const active = useActiveEvents(timeline.events, clock, { enabled, offset, onEnter, onExit })

  return (
    <Ctx.Provider value={{ clock, wave, stage: scale }}>
      <div
        className="pointer-events-none absolute left-0 top-0 origin-top-left"
        style={{ width: 1280, height: 720, transform: `scale(${scale})` }}
        aria-hidden
      >
        <AnimatePresence>
          {active.map((ev) => (
            <Renderer key={ev.id} ev={ev} />
          ))}
        </AnimatePresence>
      </div>
    </Ctx.Provider>
  )
}

function Renderer({ ev }: { ev: TimelineEvent }) {
  const { clock, wave } = useSync()
  switch (ev.kind) {
    case 'id_card':
    case 'lower_third': return <IdCard ev={ev} clock={clock} />
    case 'callout': return <Callout ev={ev} clock={clock} />
    case 'stat': return <Stat ev={ev} clock={clock} />
    case 'speed_hud': return <SpeedHud ev={ev} clock={clock} />
    case 'corner': return <Corner ev={ev} clock={clock} />
    case 'end_card': return <EndCard ev={ev} clock={clock} />
    case 'leaderboard': return <Leaderboard ev={ev} clock={clock} />
    case 'bars': return <Bars ev={ev} clock={clock} />
    case 'progress': return <Progress ev={ev} clock={clock} />
    case 'gauge': return <Gauge ev={ev} clock={clock} />
    case 'donut': return <Donut ev={ev} clock={clock} />
    case 'quadrant': return <Quadrant ev={ev} clock={clock} />
    case 'equation':
    case 'caption': return <Equation ev={ev} clock={clock} />
    case 'bracket': return <Bracket ev={ev} clock={clock} />
    case 'ticker': return <Ticker ev={ev} clock={clock} />
    case 'ring': return <Ring ev={ev} clock={clock} />
    case 'waveform': return <WaveViz ev={ev} clock={clock} wave={wave} />
    case 'ad_break': return <AdBreak ev={ev} />
    case 'chapter': return <Chapter ev={ev} />
    default: return null
  }
}
