export type Accent = 'cyan' | 'electric' | 'lime' | 'amber' | 'magenta' | 'paper' | 'muted'

export type EventKind =
  | 'id_card' | 'lower_third' | 'callout' | 'stat' | 'ring' | 'bracket'
  | 'chapter' | 'caption' | 'corner' | 'equation' | 'progress' | 'bars'
  | 'leaderboard' | 'quadrant' | 'gauge' | 'donut' | 'speed_hud'
  | 'ad_break' | 'end_card' | 'ticker' | 'waveform'

export interface Measured {
  motion: number
  lum: number
  sat: number
  black: number
  audio_db: number | null
  dominant_hue_deg: number
  dur: number
  recommended_ink: 'light' | 'dark'
}

export interface TimelineEvent {
  id: string
  t0: number
  t1: number
  kind: EventKind
  box: [number, number, number, number]
  motion: 'slide_up' | 'slide_down' | 'pop' | 'wipe' | 'draw' | 'type' | 'count'
  accent: Accent
  kicker?: string
  title?: string
  sub?: string
  value?: number
  suffix?: string
  fmt?: 'comma' | 'compact' | 'pct'
  label?: string
  items?: { label: string; value: string; num?: number; delta?: string }[]
  anchor?: [number, number]
  pointer?: boolean
  note?: string
  total?: number
  pct?: number
  serif?: boolean
  measured?: Measured
}

export interface Chapter {
  id: string
  t0: number
  t1: number
  title: string
  sub: string
}

export interface Timeline {
  version: number
  brand: {
    name: string
    source: string
    resolution: string
    source_fps: number
    target_fps: number
    palette: Record<string, string>
    motion: {
      enter_s: number
      exit_s: number
      stagger_s: number
      safe_area: number[]
    }
  }
  duration_s: number
  duration_hms: string
  source_stats: { resolution: string; fps: number; cuts: number; blocks: unknown[] }
  chapters: Chapter[]
  events: TimelineEvent[]
  audio_cues: { t: number; type: string; note: string }[]
}

export interface Waveform {
  hz: number
  duration_s: number
  peak: number[]
  rms: number[]
}
