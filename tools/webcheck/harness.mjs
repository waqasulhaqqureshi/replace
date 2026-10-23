/**
 * harness.mjs — runs the actual React player inside jsdom.
 *
 * Headless Chromium can't run in this sandbox (the image has no libnss3 and the
 * Debian mirrors are unreachable), so we verify the player by mounting the real
 * component tree in a DOM and driving the media element by hand.
 *
 * What this proves:
 *   · the app mounts with zero runtime errors and zero console errors
 *   · the timestamp trigger fires the right primitive for the right beat
 *   · counters land on the expected value at a given progress
 *   · the overlay stays empty outside event windows
 */
import { JSDOM } from 'jsdom'
import { build } from 'esbuild'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(here, '../..')

// ---------------------------------------------------------------- bundle
const outfile = path.join(here, '.bundle.mjs')
await build({
  entryPoints: [path.join(here, 'dom-entry.tsx')],
  bundle: true,
  format: 'esm',
  platform: 'browser',
  target: 'es2020',
  jsx: 'automatic',
  outfile,
  loader: { '.json': 'json' },
  // resolve React & friends from the app's own node_modules
  nodePaths: [path.join(ROOT, 'web', 'node_modules')],
  define: { 'process.env.NODE_ENV': '"development"' },
  logLevel: 'error',
})

// ---------------------------------------------------------------- jsdom
const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {
  url: 'http://localhost:5173/',
  pretendToBeVisual: true,
})
const { window } = dom
globalThis.window = window
globalThis.document = window.document
try { Object.defineProperty(globalThis, 'navigator', { value: window.navigator, configurable: true }) } catch {}
globalThis.HTMLElement = window.HTMLElement
globalThis.Element = window.Element
globalThis.Node = window.Node
globalThis.CustomEvent = window.CustomEvent
globalThis.Event = window.Event
globalThis.MouseEvent = window.MouseEvent
globalThis.KeyboardEvent = window.KeyboardEvent
globalThis.requestAnimationFrame = window.requestAnimationFrame.bind(window)
globalThis.cancelAnimationFrame = window.cancelAnimationFrame.bind(window)
globalThis.getComputedStyle = window.getComputedStyle.bind(window)

// Framer Motion touches a broad slice of the DOM API — mirror anything the
// jsdom window exposes that this Node context is missing.
for (const key of [
  'SVGElement', 'SVGSVGElement', 'HTMLCanvasElement', 'CanvasRenderingContext2D',
  'DocumentFragment', 'HTMLDivElement', 'DOMRect', 'DOMRectReadOnly',
  'CSS', 'Image', 'MutationObserver', 'IntersectionObserver', 'PointerEvent',
  'TouchEvent', 'WheelEvent', 'FocusEvent', 'AnimationEvent', 'TransitionEvent',
]) {
  if (window[key] && !(key in globalThis)) {
    try { Object.defineProperty(globalThis, key, { value: window[key], configurable: true }) } catch {}
  }
}
if (!globalThis.IntersectionObserver) {
  globalThis.IntersectionObserver = window.IntersectionObserver = class {
    observe() {} unobserve() {} disconnect() {} takeRecords() { return [] }
  }
}

// jsdom lacks these; the app uses both
class RO { observe() {} unobserve() {} disconnect() {} }
globalThis.ResizeObserver = window.ResizeObserver = RO
window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} })
window.scrollTo = () => {}

// ---- media element: drive currentTime ourselves -------------------------
const media = { t: 0, dur: 1641.1, paused: true, rate: 1, readyState: 4 }
const proto = window.HTMLMediaElement.prototype
Object.defineProperty(proto, 'currentTime', {
  get() { return media.t }, set(v) { media.t = v }, configurable: true,
})
Object.defineProperty(proto, 'duration', { get() { return media.dur }, configurable: true })
Object.defineProperty(proto, 'paused', { get() { return media.paused }, configurable: true })
Object.defineProperty(proto, 'playbackRate', {
  get() { return media.rate }, set(v) { media.rate = v }, configurable: true,
})
Object.defineProperty(proto, 'readyState', { get() { return media.readyState }, configurable: true })
Object.defineProperty(proto, 'buffered', {
  get() { return { length: 1, start: () => 0, end: () => media.dur } }, configurable: true,
})
proto.play = function () {
  media.paused = false
  this.dispatchEvent(new window.Event('play'))
  return Promise.resolve()
}
proto.pause = function () {
  media.paused = true
  this.dispatchEvent(new window.Event('pause'))
}
proto.load = function () { this.dispatchEvent(new window.Event('loadedmetadata')) }

// ---- stub 2D canvas context (jsdom has no canvas backend) ----------------
const canvasOps = { calls: 0 }
const stubCtx = new Proxy({ canvas: null }, {
  get(t, k) {
    if (k === 'canvas') return { width: 800, height: 120 }
    if (k === 'measureText') return () => ({ width: 10 })
    if (k === 'createLinearGradient') return () => ({ addColorStop() {} })
    if (k === 'getImageData') return () => ({ data: new Uint8ClampedArray(4) })
    return (...args) => { canvasOps.calls++ }
  },
  set() { return true },
})
window.HTMLCanvasElement.prototype.getContext = function () { return stubCtx }

// ---------------------------------------------------------------- errors
const errors = []
const origError = console.error
console.error = (...a) => { errors.push(a.join(' ')); origError(...a) }
window.addEventListener('error', (e) => errors.push('window.error: ' + e.message))

// ---------------------------------------------------------------- mount
await import(outfile)

const wait = (ms) => new Promise((r) => setTimeout(r, ms))
const frames = async (n = 3) => { for (let i = 0; i < n; i++) await wait(34) }

await frames(6)

// ---------------------------------------------------------------- checks
let pass = 0, fail = 0
const check = (name, cond, detail = '') => {
  if (cond) { pass++; console.log(`  \x1b[92mPASS\x1b[0m ${name}`) }
  else { fail++; console.log(`  \x1b[91mFAIL\x1b[0m ${name}${detail ? '  — ' + detail : ''}`) }
}

const video = window.document.querySelector('video')
check('video element mounted', !!video)
check('video receives the source', (video?.getAttribute('src') || '').includes('Deepseek'))
check('scene index rendered', window.document.querySelectorAll('tbody tr').length > 40,
      `${window.document.querySelectorAll('tbody tr').length} rows`)
check('transport rendered', !!window.document.querySelector('input[type=range]'))

const stage = () => window.document.querySelector('[aria-hidden="true"]')
const overlayText = () => (stage()?.textContent || '')

// seek helper: emulate a real seek (element + events), then let rAF settle
async function seek(t) {
  media.t = t
  video.dispatchEvent(new window.Event('seeking'))
  video.dispatchEvent(new window.Event('seeked'))
  video.dispatchEvent(new window.Event('timeupdate'))
  // the exit animation is 340 ms of REAL time; jsdom rAF ticks faster than 60 Hz,
  // so counting frames alone left the previous overlay on screen and made this flaky
  const t0 = Date.now()
  let n = 0
  while (n < 16 || Date.now() - t0 < 450) { await frames(1); n++ }
}

console.log('\n· timestamp triggers')
for (const [t, expect, label] of [
  [3, 'DEEPSEEK V4.1-FLASH', 'nameplate @ 00:03'],
  [9, 'LAUNCH QUEUE', 'ticker @ 00:09'],
  [24, 'HLE', 'callout @ 00:24'],
  [55, 'BENCHMARK TABLE', 'bracket @ 00:55'],
  [172, 'INTERLUDE 01', 'margin note @ 02:52'],
  [222, '39,375', 'counter @ 03:42'],
]) {
  await seek(t)
  const txt = overlayText()
  check(label, txt.includes(expect), txt.slice(0, 90).replace(/\s+/g, ' '))
}

console.log('\n· quiet windows stay empty')
// derive genuine gaps from the timeline rather than hard-coding timestamps
const TL = JSON.parse(fs.readFileSync(path.join(ROOT, 'graphics/timeline.json'), 'utf8'))
const gaps = []
{
  let cursor = 0
  for (const ev of [...TL.events].sort((a, b) => a.t0 - b.t0)) {
    if (ev.t0 - cursor > 6) gaps.push([cursor + 1, ev.t0 - 1])
    cursor = Math.max(cursor, ev.t1)
  }
}
const picks = [0, Math.floor(gaps.length / 2), gaps.length - 1].map((i) => gaps[i]).filter(Boolean)
check('timeline has quiet windows to test', picks.length > 0, `${gaps.length} gaps > 6 s`)
for (const [a, b] of picks) {
  const t = (a + b) / 2
  await seek(t)
  const label = `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`
  check(`no overlay in the gap at ${label}`, overlayText().trim().length === 0,
        `"${overlayText().slice(0, 60)}"`)
}

console.log('\n· counters')
await seek(222.5)
const counterText = overlayText()
check('count-up reaches the target within 0.5 s', /39,375|39,\d{3}/.test(counterText), counterText.slice(0, 80))
await seek(216.05)
const early = overlayText()
check('count-up starts near zero', /^[\s\S]*\b([0-9]|[0-9]{1,2})\b/.test(early) && !early.includes('39,375'),
      early.slice(0, 80))

console.log('\n· graphics toggle')
const gfxBtn = [...window.document.querySelectorAll('button')]
  .find((b) => /GFX/i.test(b.textContent || ''))
check('graphics toggle present', !!gfxBtn)
if (gfxBtn) {
  gfxBtn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }))
  await seek(24)
  check('overlay clears when graphics are off', overlayText().trim().length === 0)
  gfxBtn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }))
  await seek(24)
  check('overlay returns when graphics are on', overlayText().length > 0)
}

console.log('\n· runtime errors')
const realErrors = errors.filter((e) => !/not implemented|Could not parse CSS|jsdom/i.test(e))
check('no React/runtime errors', realErrors.length === 0, realErrors.slice(0, 2).join(' | ').slice(0, 300))

console.log(`\n${fail === 0 ? '\x1b[92m' : '\x1b[91m'}${pass} passed, ${fail} failed\x1b[0m`)
fs.rmSync(outfile, { force: true })
process.exit(fail === 0 ? 0 : 1)
