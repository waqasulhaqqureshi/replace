// Test entry: mounts the real App into a jsdom document and exposes a driver
// so the harness can move the playhead and inspect the rendered overlay.
import { createRoot } from 'react-dom/client'
import App from '../../web/src/App'

const root = createRoot(document.getElementById('root')!)
root.render(<App />)

export {}
