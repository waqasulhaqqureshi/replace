// Emits the web runtime's easing / count-up values so the Python renderer can
// be diffed against them. Used by scripts/check_math_parity.sh.
import { ease, countAt, fmt } from '/home/user/replace/web/src/lib/useFrame'

const rows: string[] = []
for (const p of [0, 0.15, 0.4, 0.72, 1]) {
  for (const target of [155, 1000000, 39375, 42]) {
    rows.push(`${p}|${target}|${countAt(target, p).toFixed(4)}|${fmt(countAt(target, p), 'comma', '')}`)
  }
  rows.push(`${p}|ease|${ease.out(p).toFixed(6)}|${ease.in(p).toFixed(6)}|${ease.outBack(p).toFixed(6)}`)
}
console.log(rows.join('\n'))
