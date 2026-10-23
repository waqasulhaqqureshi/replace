import chromium from '@sparticuz/chromium'
import puppeteer from 'puppeteer-core'

const exe = await chromium.executablePath()
console.log('executablePath:', exe)
const browser = await puppeteer.launch({
  args: [...chromium.args, '--autoplay-policy=no-user-gesture-required'],
  executablePath: exe,
  headless: 'shell',
})
const page = await browser.newPage()
await page.setViewport({ width: 1440, height: 1000, deviceScaleFactor: 1 })
await page.goto('http://localhost:5173/', { waitUntil: 'networkidle2', timeout: 60000 })
console.log('title:', await page.title())
console.log('root children:', await page.evaluate(() => document.querySelector('#root')?.children.length))
console.log('h264 support:', await page.evaluate(() => document.createElement('video').canPlayType('video/mp4; codecs="avc1.42E01E"')))
console.log('vp9 support:', await page.evaluate(() => document.createElement('video').canPlayType('video/webm; codecs="vp9"')))
await browser.close()
