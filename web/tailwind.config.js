/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        void: '#05070D',
        ink: '#0B1020',
        panel: '#0F1526',
        line: '#22304B',
        cyan: '#2FE9FF',
        electric: '#4D6BFE',
        lime: '#B6FF3C',
        amber: '#FFB020',
        magenta: '#FF2D6F',
        paper: '#F2F6FF',
        muted: '#8FA2C4',
      },
      fontFamily: {
        display: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        glass: '0 20px 60px -20px rgba(0,0,0,.85), inset 0 1px 0 rgba(255,255,255,.06)',
        glow: '0 0 24px -4px currentColor',
      },
    },
  },
  plugins: [],
}
