import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import * as board from '../studio/static/direct-storyboard.js';
const read=state=>JSON.parse(readFileSync(new URL(`./fixtures/r282-direct/${state}.json`,import.meta.url),'utf8'));
export function testHandoffFormulas(){
  assert.equal(typeof board.handoffRows,'function','Handoff image provenance must map into storyboard rows');
  const hand=read('first-handoff').handoff.handoff,rows=board.handoffRows(hand);
  assert.deepEqual(board.rowTimes(rows,true),hand.shots.map(s=>[s.startSeconds,s.endSeconds]));
  assert.deepEqual(rows.map(r=>r.image.tag),['代码渲染','参考关键帧','AI 示意 · 非实拍 · 待确认','原片截帧 1:12','代码渲染','参考关键帧','AI 示意 · 非实拍']);
  assert.equal(rows[2].image.pending,true);assert.equal(rows[0].image.poster,hand.shots[0].image.url);
  const missing=structuredClone(hand);missing.shots[0].image.url=null;
  assert.equal(board.handoffRows(missing)[0].image.poster,null);
  assert.deepEqual(board.storyboard(rows).shots[0],Object.fromEntries(['shotId','dialogue','visual','subtitle','camera','audio'].map(k=>[k,hand.shots[0][k]])));
  console.log('PASS R282 handoff provenance and timing formulas');
}
export async function testHandoffBrowser({open}){
  let {page,mock}=await open('first-handoff');const hand=read('first-handoff').handoff.handoff;
  for(const f of ['dialogue','visual','subtitle','camera','audio'])assert.deepEqual(await page.locator(`[data-f="${f}"]`).evaluateAll(es=>es.map(e=>e.value)),hand.shots.map(s=>s[f]));
  assert.equal(await page.locator('.sb-pic img').count(),7);
  assert.equal(await page.locator('[data-flow] small').first().textContent(),'7 镜 · 2:08');
  assert((await page.locator('[data-design-id="DV-SB-SOURCE"]').textContent()).includes('第 3 版 · 10 月 26 日 14:02'));
  assert((await page.locator('[data-design-id="DV-VOICE"]').textContent()).includes('配音（从中台带过来）'));
  assert((await page.locator('[data-design-id="DV-VOICE"]').textContent()).includes('百炼 Cherry · 2:08'));
  assert.equal(await page.locator('[data-sb-time]').first().textContent(),'0:00–0:16');
  assert.equal(await page.locator('.sb-tag.sb-warn').count(),1);
  assert.notEqual(await page.locator('.sb-tag.sb-warn').evaluate(e=>getComputedStyle(e).color),await page.locator('.sb-tag').first().evaluate(e=>getComputedStyle(e).color));
  await page.locator('button[data-pic]').first().click();assert.equal(await page.locator('.sb-zoom img').count(),1);assert((await page.locator('.sb-zoom header').textContent()).includes('0:00–0:16'));await page.keyboard.press('Escape');
  await page.locator('[data-f="visual"]').first().fill('本机画面');assert.equal(await page.locator('[data-sb-time]').first().textContent(),'0:00–0:16');
  await page.locator('[data-f="dialogue"]').first().fill('一二三四五');assert.equal(await page.locator('[data-sb-time]').first().textContent(),'0:00–0:01');
  await page.locator('[data-generate]').click();await page.locator('.dv-film').waitFor();
  assert.deepEqual(mock.creates.at(-1).handoff,{jobId:hand.jobId,revision:3});assert.equal(mock.creates.at(-1).storyboard.shots[0].visual,'本机画面');await page.close();
  ({page,mock}=await open('rescript-newer'));
  assert.equal(await page.locator('[data-f="dialogue"]').nth(1).inputValue(),mock.initial.job.shots[1].dialogue);
  assert((await page.locator('[data-design-id="DV-SB-SOURCE"]').textContent()).includes('中台又交过来新的分镜：第 4 版'));
  await page.locator('[data-f="visual"]').first().fill('将被替换');await page.locator('[data-take-handoff]').click();
  const newer=read('rescript-newer').handoff.handoff;
  for(const f of ['dialogue','visual','subtitle','camera','audio'])assert.deepEqual(await page.locator(`[data-f="${f}"]`).evaluateAll(es=>es.map(e=>e.value)),newer.shots.map(s=>s[f]));
  assert.equal(await page.locator('.sb-pic video').count(),0);assert.equal(await page.locator('.sb-pic img').count(),7);assert.equal(await page.locator('[data-take-handoff]').count(),0);
  assert.equal(await page.locator('[data-sb-time]').first().textContent(),'0:00–0:16');assert((await page.locator('[data-design-id="DV-VOICE"]').textContent()).includes('百炼 Cherry'));
  await page.locator('[data-generate]').click();await page.locator('.dv-film').waitFor();assert.deepEqual(mock.creates.at(-1).handoff,{jobId:newer.jobId,revision:4});await page.close();
  ({page,mock}=await open('rescript-newer'));await page.locator('[data-generate]').click();await page.locator('.dv-film').waitFor();assert(!Object.hasOwn(mock.creates.at(-1),'handoff'),'Newer handoff is opt-in');await page.close();
  const partial=structuredClone(hand);partial.handedAt=null;partial.narration=null;partial.shots[0].image.url=null;
  ({page,mock}=await open('first-handoff',1440,{handoff:partial}));
  assert.equal(await page.locator('.sb-pic img').count(),6);assert.equal(await page.locator('.sb-none').count(),1);
  const source=await page.locator('[data-design-id="DV-SB-SOURCE"]').textContent();
  assert(!source.includes('1 月 1 日')&&!source.includes('NaN')&&!source.includes('带配音'));
  assert(!(await page.locator('[data-head]').textContent()).includes('配音都已带上'));
  assert((await page.locator('[data-design-id="DV-VOICE"]').textContent()).includes('配音（可以之后再加）'));
  assert.equal(await page.locator('[data-sb-time]').first().textContent(),'0:00–0:16');
  assert(!(await page.locator('[data-sb-note]').textContent()).includes('按中台的配音'));await page.close();
  ({page,mock}=await open('first-handoff'));
  const chooser=page.waitForEvent('filechooser');await page.locator('[data-voice]').click();await(await chooser).setFiles({name:'替换配音.wav',mimeType:'audio/wav',buffer:Buffer.from('RIFF fixture audio')});
  await page.waitForFunction(()=>document.querySelector('.dv-voice-name').textContent==='替换配音.wav');
  const uploaded=page.waitForResponse(r=>r.url().endsWith('/narration'));await page.locator('[data-generate]').click();await page.locator('.dv-film').waitFor();await uploaded;
  assert.equal(mock.uploads.length,1);assert(mock.uploads[0].path.includes(mock.current.job.jobId));assert(mock.uploads[0].bytes>0);await page.close();
  const legacy=read('first-handoff-legacy').handoff.handoff;
  for(const revision of [null,3])for(const handedAt of [null,hand.handedAt]){
    const metadata={...legacy,revision,handedAt};
    ({page,mock}=await open('first-handoff',1440,{handoff:metadata}));
    const text=await page.locator('[data-design-id="DV-SB-SOURCE"] [data-design-data]').textContent();
    assert.equal(text,`从中台交过来：「${hand.title}」${revision===null?'':`第 ${revision} 版`}${handedAt===null?'':' · 10 月 26 日 14:02'} · 带配音（百炼 Cherry · 2:08）。`);
    assert.equal(await page.locator('.dv-sb tbody tr').count(),7);assert.equal(await page.locator('.sb-pic img').count(),7);
    await page.locator('[data-generate]').click();await page.locator('.dv-film').waitFor();assert.deepEqual(mock.creates.at(-1).handoff,{jobId:legacy.jobId,revision});await page.close();
    ({page,mock}=await open('rescript-newer',1440,{handoff:metadata}));
    assert.equal(await page.locator('[data-design-id="DV-SB-SOURCE"] [data-design-data]').textContent(),revision===null?'中台又交过来新的分镜。':`中台又交过来新的分镜：第 ${revision} 版${handedAt===null?'':' · 10 月 26 日 14:02'}。`);
    assert(await page.locator('[data-take-handoff]').isVisible());await page.locator('[data-take-handoff]').click();
    assert.equal(await page.locator('[data-f="dialogue"]').nth(1).inputValue(),legacy.shots[1].dialogue);
    await page.locator('[data-generate]').click();await page.locator('.dv-film').waitFor();assert.deepEqual(mock.creates.at(-1).handoff,{jobId:legacy.jobId,revision});await page.close();
  }
  const unvoiced={...legacy,narration:null};
  ({page}=await open('first-handoff',1440,{handoff:unvoiced}));
  assert.equal(await page.locator('[data-design-id="DV-SB-SOURCE"] [data-design-data]').textContent(),`从中台交过来：「${hand.title}」。`);await page.close();
  for(const state of ['first-handoff','rescript-newer']){
    ({page}=await open(state,390));
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),390);
    assert.equal(await page.locator('[data-generate]').evaluate(e=>{const range=document.createRange();range.selectNodeContents(e);return range.getClientRects().length;}),1,'Generate label must fit on one line on phones');
    await page.close();
  }
  console.log('PASS R282 mounted handoff prefill, local edits, replacement and request identity');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)testHandoffFormulas();
