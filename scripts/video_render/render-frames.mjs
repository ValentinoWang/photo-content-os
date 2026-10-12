#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync, realpathSync, existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { resolve, relative, extname, sep } from 'node:path';

const require = createRequire(import.meta.url);
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const emit = event => process.stdout.write(`${JSON.stringify(event)}\n`);
let browser;
let browserServer;
let browserLaunch;
let timeoutReject;
let watchdog;
let progress = 0;

function fail(code, message, details = {}) {
  return Object.assign(new Error(message), { code, ...details });
}

async function main() {
  if (process.argv.length !== 4) throw fail('invalid_input', 'Usage: node render-frames.mjs REQUEST.json OUTPUT_DIR');
  const request = JSON.parse(readFileSync(process.argv[2], 'utf8'));
  const output = resolve(process.argv[3]);
  for (const key of ['width', 'height', 'fps', 'frames']) {
    if (!Number.isSafeInteger(request[key]) || request[key] <= 0) throw fail('invalid_input', `Invalid ${key}`);
  }
  if (!(request.timeout_seconds > 0) || !Number.isFinite(request.timeout_seconds)) throw fail('invalid_input', 'Invalid timeout_seconds');
  if (!Array.isArray(request.fonts) || !request.fonts.length) throw fail('font_missing', 'At least one pinned local font is required');
  watchdog = setTimeout(() => timeoutReject(fail('shot_timeout', 'Shot exceeded timeout')), request.timeout_seconds * 1000);

  const root = realpathSync(request.assets_dir);
  const htmlPath = realpathSync(request.html);
  const within = path => {
    const name = relative(root, path);
    return name !== '..' && !name.startsWith(`..${sep}`) && !name.startsWith(sep);
  };
  if (!within(htmlPath)) throw fail('asset_outside_root', 'HTML must be inside assets_dir');
  const dependencies = new Map();
  const trackedRead = path => {
    const bytes = readFileSync(path);
    dependencies.set(path, digest(bytes));
    return bytes;
  };
  const html = trackedRead(htmlPath).toString('utf8');
  const fonts = request.fonts.map((font, index) => ({
    family: `PCPinned${index}`,
    data: trackedRead(realpathSync(font.path)).toString('base64'),
  }));
  const moduleName = process.env.VIDEO_RENDER_PLAYWRIGHT_MODULE || 'playwright';
  const playwright = require(moduleName);
  emit({ status: 'running', phase: 'browser_launch', progress_frames: 0 });
  browserLaunch = playwright.chromium.launchServer({
    executablePath: request.browser_executable || undefined,
    headless: true,
    timeout: request.timeout_seconds * 1000,
    args: ['--disable-gpu', '--force-color-profile=srgb', '--hide-scrollbars'],
  });
  browserServer = await browserLaunch;
  emit({ status: 'running', phase: 'browser_owned', browser_pid: browserServer.process().pid });
  browser = await playwright.chromium.connect(browserServer.wsEndpoint());
  const context = await browser.newContext({
    viewport: { width: request.width, height: request.height }, deviceScaleFactor: 1,
    locale: 'en-US', timezoneId: 'UTC', colorScheme: 'light', serviceWorkers: 'block',
  });
  await context.addInitScript(({ seed }) => {
    let state = seed >>> 0;
    Math.random = () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state / 4294967296; };
    const RealDate = Date;
    window.__pcTime = 0;
    window.Date = class extends RealDate {
      constructor(...args) { super(...(args.length ? args : [1704067200000 + window.__pcTime])); }
      static now() { return 1704067200000 + window.__pcTime; }
    };
    performance.now = () => window.__pcTime;
    // Timeline changes must be explicit; wall-clock timers cannot advance a shot.
    window.setTimeout = window.setInterval = () => 0;
    window.requestAnimationFrame = () => 0;
    window.crypto.getRandomValues = () => { throw new Error('Use seeded Math.random in render shots'); };
    window.crypto.randomUUID = () => { throw new Error('Use seeded Math.random in render shots'); };
    window.WebSocket = class { constructor() { throw new Error('Network is disabled in render shots'); } };
  }, { seed: request.seed ?? 1 });

  const errors = [];
  const origin = 'https://pc-render.invalid';
  const mime = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.mp4': 'video/mp4' };
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== origin || route.request().method() !== 'GET') {
      errors.push(fail('remote_asset', `External resource is forbidden: ${url.origin}`));
      return route.abort();
    }
    const path = resolve(root, `.${decodeURIComponent(url.pathname)}`);
    if (!within(path) || (existsSync(path) && !within(realpathSync(path)))) {
      errors.push(fail('asset_outside_root', `Resource escapes assets_dir: ${url.pathname}`));
      return route.abort();
    }
    try {
      const bytes = trackedRead(path);
      return await route.fulfill({ body: bytes, contentType: mime[extname(path)] || 'application/octet-stream' });
    } catch (error) {
      if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') throw error;
      const filename = relative(root, path).split(sep).join('/');
      const lineIndex = html.split('\n').findIndex(line => line.includes(filename) || line.includes(url.pathname.split('/').at(-1)));
      const line = lineIndex >= 0 ? lineIndex + 1 : null;
      errors.push(fail('missing_asset', line ? `第 ${line} 行要读 ${filename}，素材目录里没有` : `要读 ${filename}，素材目录里没有`, { file: filename, line }));
      return route.abort();
    }
  });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(fail('script_error', error.message)));
  const htmlRelative = relative(root, htmlPath).split(sep).map(encodeURIComponent).join('/');
  emit({ status: 'running', phase: 'resource_load', progress_frames: 0 });
  await page.goto(`${origin}/${htmlRelative}`, { waitUntil: 'networkidle', timeout: request.timeout_seconds * 1000 });
  if (errors.length) throw errors[0];
  emit({ status: 'running', phase: 'font_load', progress_frames: 0 });
  await page.addStyleTag({ content: `${fonts.map(font => `@font-face {font-family:"${font.family}";src:url(data:font/ttf;base64,${font.data});font-display:block;}`).join('\n')}\n* { font-family: "PCPinned0" !important; }\nhtml,body { margin:0; overflow:hidden; }` });
  await page.evaluate(async () => {
    await document.fonts.load('16px PCPinned0');
    await document.fonts.ready;
    if (!document.fonts.check('16px PCPinned0')) throw new Error('Pinned font failed to load');
    if (typeof window.seekFrame !== 'function') throw new Error('HTML must define window.seekFrame(frame, fps)');
    for (const animation of document.getAnimations()) animation.pause();
    if (document.querySelector('video,audio')) throw new Error('Pre-render media into local still frames; video/audio clocks are forbidden');
  });
  mkdirSync(output, { recursive: true });
  emit({ status: 'running', phase: 'frames', progress_frames: 0 });
  for (let frame = 0; frame < request.frames; frame += 1) {
    try {
      await page.evaluate(async ({ frame, fps }) => {
      window.__pcTime = frame * 1000 / fps;
      await window.seekFrame(frame, fps);
      for (const animation of document.getAnimations()) { animation.pause(); animation.currentTime = window.__pcTime; }
      await Promise.all([...document.images].map(img => img.decode()));
      await document.fonts.ready;
      }, { frame, fps: request.fps });
    } catch (error) {
      throw errors[0] || error;
    }
    if (errors.length) throw errors[0];
    await page.screenshot({ path: resolve(output, `frame-${String(frame).padStart(6, '0')}.png`), omitBackground: Boolean(request.transparent), animations: 'allow', caret: 'hide', timeout: request.timeout_seconds * 1000 });
    if (errors.length) throw errors[0];
    progress = frame + 1;
    emit({ status: 'running', progress_frames: progress, total_frames: request.frames });
  }
  const result = { status: 'completed', progress_frames: progress, total_frames: request.frames, browser_version: browser.version(), dependencies: [...dependencies].map(([path, sha256]) => ({ path, sha256 })) };
  writeFileSync(resolve(output, 'render-manifest.json'), `${JSON.stringify(result, null, 2)}\n`);
  return result;
}

const timeout = new Promise((_, reject) => { timeoutReject = reject; });
let final;
process.on('SIGTERM', () => timeoutReject(fail('shot_cancelled', 'Shot cancelled')));
try {
  final = await Promise.race([main(), timeout]);
} catch (error) {
  final = { status: 'failed', code: error.code || 'render_failed', reason: error.message, file: error.file ?? null, line: error.line ?? null, progress_frames: progress };
  process.exitCode = 1;
} finally {
  clearTimeout(watchdog);
  // A terminal receipt is emitted only after the browser and its children exit.
  if (!browserServer && browserLaunch) browserServer = await browserLaunch.catch(() => null);
  if (browserServer) await browserServer.close();
}
emit(final);
