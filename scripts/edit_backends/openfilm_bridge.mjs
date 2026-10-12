/** Pinned openfilm bridge. JSON-line IPC stays local; no provider or agent calls. */
import fs from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import readline from 'node:readline';

const runtime = process.env.CONTENT_OS_OPENFILM_PACKAGE;
const moduleOf = (relative) => import(pathToFileURL(path.join(runtime, relative)).href);
const { render } = await moduleOf('src/render.mjs');
const { launch, closeBrowsers } = await moduleOf('src/host.mjs');
const { readProjectFilm } = await moduleOf('studio/server/film.mjs');
const { subtitlesForExport, trimToWindow } = await moduleOf('studio/server/captions.mjs');
const { readTranscript } = await moduleOf('studio/server/transcripts.mjs');
const { filmSubtitleSrt, filmSubtitleShown } = await moduleOf('studio/server/film-subtitle.mjs');
const { chromium } = await import(pathToFileURL(path.join(runtime, '../playwright-core/index.mjs')).href);
const json = (value) => JSON.stringify(value).replace(/</g, '\\u003c');
let studio, browser, page, opened, project;
const events = [];
let stopping = false;
async function cleanup() {
  if (stopping) return;
  stopping = true;
  await page?.close().catch(() => {});
  await browser?.close().catch(() => {});
  if (studio) await studio.close();
  await closeBrowsers();
}
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, async () => { await cleanup(); process.exit(0); });
async function api(route, body) {
  const response = await fetch(`${studio.origin}/api/${route}`, {
    method: body ? 'POST' : 'GET',
    headers: { 'x-studio-key': studio.key, 'Content-Type': 'application/json' },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const value = await response.json();
  if (!response.ok) throw Error(`openfilm_api_${response.status}`);
  return value;
}
async function snapshot(root) {
  const film = await readProjectFilm(root);
  if (!film.doc || film.problems.length) throw Error(`openfilm_project_invalid:${film.problems.join(';')}`);
  const subtitles = await subtitlesForExport(root);
  // openfilm's captionText removes end punctuation even for hand-cut VTT.
  // Read the person's current transcript, keeping cue timing from the actual film.
  for (const cue of subtitles.cues) {
    const transcript = await readTranscript(root, cue.src);
    const line = transcript?.lines.find((line) => line.startMs === cue.line);
    const clip = film.doc.tracks.flatMap((t) => t.clips).find((clip) => clip.id === cue.clip);
    if (transcript?.cut && line && clip && cue.part == null) {
      cue.text = trimToWindow(line, clip.time[0] * 1000, clip.time[1] * 1000);
    }
  }
  return { value: film.value, doc: film.doc, rev: film.rev, subtitles };
}
async function exportVideo(request) {
  const state = await snapshot(request.project);
  const { cues, style } = state.subtitles;
  const shown = filmSubtitleShown(cues, style);
  await fs.writeFile(request.subtitles, filmSubtitleSrt(shown));
  let target = request.project;
  const scratch = path.join(request.project, '.film', 'oa-render');
  try {
    if (shown.length && style.on) {
      await fs.mkdir(scratch, { recursive: true });
      await fs.copyFile(path.join(runtime, 'studio/server/film-subtitle.mjs'), path.join(scratch, 'film-subtitle.mjs'));
      const { w, h } = state.doc.stage;
      // The engine's subtitle painter keeps preview and export typography identical.
      await fs.writeFile(path.join(scratch, 'index.html'), `<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:${w}px;height:${h}px;overflow:hidden;background:#000}
#film{position:absolute;left:0;top:0;width:${w}px;height:${h}px;border:0}
#subs{position:absolute;inset:0}
</style></head><body><div id="subs"></div><script type="module">
import {filmSubtitleFrameHtml} from './film-subtitle.mjs';
const cues=${json(cues)}, style=${json(style)}, size={w:${w},h:${h}};
const el=document.createElement('iframe');el.id='film';
const loaded=new Promise(ok=>el.addEventListener('load',ok,{once:true}));el.src='/film.html';document.body.prepend(el);
let inner;const ready=loaded.then(async()=>{inner=el.contentWindow;const start=performance.now();while(!inner.film){if(performance.now()-start>10000)throw Error('inner film initialization timed out');await new Promise(r=>setTimeout(r,20));}await (typeof inner.film.ready==='function'?inner.film.ready():inner.film.ready);});
window.film={width:size.w,height:size.h,ready,get duration(){return inner?.film.duration??0.001},async frame(t){
inner.filmHost?.time?.(t);await inner.film.frame(t);inner.filmHost?.settle?.(t);
document.getElementById('subs').innerHTML=filmSubtitleFrameHtml(cues,style,size,t*1000);await document.fonts.ready;}};
window.__filmSounds=()=>inner?.__filmSounds?.()??[];window.__filmCuts=()=>inner?.__filmCuts?.()??null;
</script></body></html>`);
      target = scratch;
    }
    const result = await render([target], {
      root: request.project, out: request.output, fps: 30, workers: 1,
      seekable: false, signal: AbortSignal.timeout(request.timeoutMs),
    });
    if (result.lines.some((line) => line.startsWith('✗'))) throw Error('openfilm_render_page_error');
    return { ...state, result, seekable: false, workers: 1 };
  } finally {
    await fs.rm(scratch, { recursive: true, force: true });
    if (!studio) await closeBrowsers();
  }
}
async function screen(name) {
  const evidence = process.env.CONTENT_OS_OPENFILM_EVIDENCE;
  if (!evidence) return;
  await fs.mkdir(evidence, { recursive: true });
  const state = await snapshot(project);
  const duration = Math.max(...state.doc.tracks.flatMap((t) => t.clips.map((c) => (c.at ?? 0) + (c.time[1] - c.time[0]) / (c.speed ?? 1))));
  const filmFrame = page.frames().find((f) => new URL(f.url()).pathname.endsWith('/film.html'));
  if (filmFrame) await filmFrame.waitForFunction((seconds) => window.film?.duration === seconds, duration, { timeout: 30000 });
  const output = path.join(evidence, `editor-${name}.png`);
  await page.screenshot({ path: output, fullPage: true });
  await fs.writeFile(path.join(evidence, `editor-${name}.json`), JSON.stringify({
    at: new Date().toISOString(), route: `/projects/${opened.project.id}`,
    viewport: await page.evaluate(() => ({ width: innerWidth, height: innerHeight })),
    screenshot: output, state: await snapshot(project), events,
    scroll: await page.evaluate(() => ({ height: document.documentElement.scrollHeight, width: document.documentElement.scrollWidth })),
  }, null, 2));
}
async function refine(root) {
  const { startStudio } = await moduleOf('studio/server/server.mjs');
  // Use the default engine launch; one owned browser serves editor and render pages.
  browser = await launch({ headed: process.env.CONTENT_OS_OPENFILM_HEADLESS !== '1' });
  const shared = new Proxy(browser, { get(target, key) {
    if (key === 'close') return async () => {};
    const value = target[key]; return typeof value === 'function' ? value.bind(target) : value;
  } });
  chromium.launch = async () => shared;
  studio = await startStudio({ port: 0, openBrowser: () => {} });
  opened = await api('open', { path: root, fallback: 0 });
  project = root;
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await page.context().route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (['http:', 'https:'].includes(url.protocol) && !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname)) {
      events.push({kind:'external-blocked', origin:url.origin});await route.abort();
    } else await route.continue();
  });
  page.on('console', (msg) => { if (msg.type() === 'error') events.push({ kind: 'console', message: msg.text() }); });
  page.on('pageerror', (error) => events.push({ kind: 'pageerror', message: error.message }));
  page.on('requestfailed', (req) => events.push({ kind: 'requestfailed', url: new URL(req.url()).pathname, error: req.failure()?.errorText }));
  await page.addInitScript(() => { if (location.hostname === '127.0.0.1') localStorage.setItem('openfilm.language', 'zh-CN'); });
  await page.goto(opened.url);
  await page.locator('[data-block-id]').first().waitFor({ timeout: 30000 });
  await page.waitForFunction(() => !document.body.innerText.includes('正在绘制第一帧'), null, { timeout: 30000 });
  await screen('initial');
  return { editor_backend: 'openfilm', url: opened.url, project_id: opened.project.id, local_only: true };
}
async function deleteSegment(index) {
  const before = await snapshot(project);
  const track = before.doc.tracks.find((t) => t.clips.some((c) => c.src === 'assets/source.mp4'));
  const clip = track?.clips[index];
  if (!clip) throw Error('openfilm_segment_missing');
  // Native waveform blocks are named from the file and clip ordinal, not clip id.
  const blockId = await page.locator('[data-block-id]').evaluateAll((els, id) => {
    const found = els.find((el) => el.getAttribute('data-clip-id') === id);
    return found?.getAttribute('data-block-id');
  }, clip.id);
  let block;
  if (blockId) block = page.locator(`[data-block-id=${JSON.stringify(blockId)}]`);
  else block = page.locator('[data-block-id]').filter({ hasText: 'source' }).nth(index);
  await block.click();
  const changed = page.waitForResponse((r) => r.url().endsWith('/edit') && r.request().method() === 'POST' && r.ok());
  changed.catch(() => {});
  await page.keyboard.press('Shift+Backspace');
  await changed;
  const state = await snapshot(project);
  if (state.doc.tracks.flatMap((t) => t.clips).some((c) => c.id === clip.id)) throw Error('openfilm_delete_not_saved');
  await screen('deleted');
  return { rev: state.rev };
}
async function undo() {
  const changed = page.waitForResponse((r) => r.url().endsWith('/edit') && r.request().method() === 'POST' && r.ok());
  changed.catch(() => {});
  await page.getByRole('button', { name: /^撤销/ }).click();
  await changed;
  await screen('restored');
  return { rev: (await snapshot(project)).rev };
}
async function dispatch(request) {
  switch (request.action) {
    case 'probe': {
      const pkg = JSON.parse(readFileSync(path.join(runtime, 'package.json')));
      const result = await snapshot(request.project);
      const probeBrowser = browser ?? await launch();
      try { return { version: pkg.version, valid: !!result.doc, chromium: chromium.executablePath(), browserVersion: probeBrowser.version() }; }
      finally { if (!browser) await probeBrowser.close(); }
    }
    case 'snapshot': return snapshot(request.project);
    case 'studio-host': {
      if (studio) throw Error('openfilm_host_already_active');
      const { startStudio } = await moduleOf('studio/server/server.mjs');
      studio = await startStudio({port: 0, editorDir: request.host, openBrowser: () => {}});
      opened = await api('open', {path: request.project, fallback: 0});
      project = request.project;
      const current = await api(`projects/${opened.project.id}`);
      return {origin: studio.origin, url: `${studio.origin}/open?key=${studio.key}&to=/`,
              project_id: opened.project.id, filmUrl: `${current.folder}film.html`, ...await snapshot(project)};
    }
    case 'studio-edit': {
      const before = await snapshot(project);
      if (request.base !== before.rev) throw Error('openfilm_revision_conflict');
      await api(`projects/${opened.project.id}/edit`, {base: request.base, ops: request.ops});
      return snapshot(project);
    }

    case 'render': return exportVideo(request);
    case 'refine': return refine(request.project);
    case 'delete': return deleteSegment(request.index);
    case 'undo': return undo();
    case 'close': await cleanup(); return { closed: true };
    default: throw Error('openfilm_action_unknown');
  }
}
const lines = readline.createInterface({ input: process.stdin });
try {
  for await (const line of lines) {
    try { const value = await dispatch(JSON.parse(line)); process.stdout.write(JSON.stringify({ ok: true, value }) + '\n'); }
    catch (error) { process.stdout.write(JSON.stringify({ ok: false, error: error.message }) + '\n'); }
  }
} finally { await cleanup(); }
