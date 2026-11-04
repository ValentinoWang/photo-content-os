import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {resolve, extname, join} from 'node:path';
import {homedir} from 'node:os';
import {pathToFileURL} from 'node:url';

// A browser is required: the regression depends on CSS cascade and :focus.
const root = resolve('studio/static');
const modulePath = process.env.VIDEO_RENDER_PLAYWRIGHT_MODULE || process.env.PLAYWRIGHT_MODULE || join(homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs');
const {chromium} = await import(pathToFileURL(modulePath.replace(/index\.js$/, 'index.mjs')));
const server = createServer(async (req, res) => {
  try {
    const name = new URL(req.url, 'http://localhost').pathname.slice(1) || 'index.html';
    const file = resolve(root, name);
    if (!file.startsWith(root + '/')) throw new Error('invalid path');
    const body = await readFile(name === 'styles.css' && process.env.TEST_OLD_STYLES ? process.env.TEST_OLD_STYLES : file);
    res.writeHead(200, {'content-type': ({'.html':'text/html','.js':'text/javascript','.css':'text/css'})[extname(file)] || 'application/octet-stream'});
    res.end(body);
  } catch { res.writeHead(404); res.end(); }
});
await new Promise(resolveListen => server.listen(0, '127.0.0.1', resolveListen));
let browser;
try {
  browser = await chromium.launch({headless:true, ...(process.env.VIDEO_RENDER_BROWSER ? {executablePath:process.env.VIDEO_RENDER_BROWSER} : {channel:'chrome'})});
  const page = await browser.newPage({viewport:{width:1440,height:900}});
  const base = `http://127.0.0.1:${server.address().port}`;
  await page.goto(base);
  await page.evaluate(async () => {
    const original = document.documentElement.outerHTML;
    const doc = new DOMParser().parseFromString(original, 'text/html');
    document.body.innerHTML = '<div id="fixtures"></div>';
    const root = document.querySelector('#fixtures');
    for (const id of ['pair-form','project-form']) {
      const clone = doc.getElementById(id).cloneNode(true);
      root.append(clone);
    }
    root.insertAdjacentHTML('beforeend','<div id="story"></div><div id="style-base"></div><div id="style-new"></div>');
    const {bindLimits} = await import('/input-limit.js');
    const {renderStoryboard} = await import('/direct-storyboard.js');
    const {renderStyle} = await import('/direct-style.js');
    bindLimits(root);
    renderStoryboard(root.querySelector('#story'), {rows:[{dialogue:'示例',visual:'',subtitle:'',camera:'',audio:'',image:null}],onChange:()=>{},onImport:()=>{}});
    const args = {styles:[],library:[],rows:[{dialogue:'示例'}],projectId:'fixture',jobId:'fixture',unavailable:false,busy:false,onChange:()=>{},onDraft:()=>{},onRevise:()=>{},onRedo:()=>{},mmss:()=>'',elapsed:()=>0,failureMessage:()=>''};
    renderStyle(root.querySelector('#style-base'), {...args,state:{mode:'base',base:null,adjust:''}});
    renderStyle(root.querySelector('#style-new'), {...args,state:{mode:'new',draft:null,accepted:false,revising:true,text:'',revise:''}});
  });
  const fields = page.locator('[data-limit]');
  assert.equal(await fields.count(), 13, 'all declared limited fields must be exercised');
  const failures = [];
  for (let i=0; i<await fields.count(); i++) {
    const field = fields.nth(i);
    const id = await field.evaluate(el => el.id || el.name || el.dataset.f);
    const limit = Number(await field.getAttribute('data-limit'));
    await field.fill('字'.repeat(limit + 1));
    for (const focused of [false,true]) {
      if (focused) await field.focus(); else await field.blur();
      const colors = await field.evaluate(el => {
        const probe = document.createElement('span');
        probe.style.color = 'var(--cut)'; el.parentElement.append(probe);
        const expected = getComputedStyle(probe).color; probe.remove();
        return {actual:getComputedStyle(el).borderTopColor, expected};
      });
      console.log(JSON.stringify({id,focused,...colors}));
      if (colors.actual !== colors.expected) failures.push(`${id} focused=${focused}: ${colors.actual} != ${colors.expected}`);
    }
  }
  assert.deepEqual(failures, [], 'limited input border must use the error token');
} finally {
  await browser?.close();
  await new Promise(resolveClose => server.close(resolveClose));
}
