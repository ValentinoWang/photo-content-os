import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {createRequire} from 'node:module';
const {chromium}=createRequire(process.env.PW_REQ)('playwright'),base=process.env.STUDIO_URL;if(!base||new URL(base).port==='8765')throw Error('Use isolated Studio');
const fixture=state=>JSON.parse(fs.readFileSync('tests/fixtures/r223/frontend/'+state+'.json')),browser=await chromium.launch({channel:'chrome'}),checks=[];
async function pageWith(payload){const c=await browser.newContext({viewport:{width:1440,height:960},locale:'zh-CN'});await c.route('**/*',r=>new URL(r.request().url()).origin===base?r.continue():r.abort());await c.route('**/api/review/music',r=>r.fulfill({json:payload}));const page=await c.newPage();await page.goto(base+'/#view=music');await page.waitForSelector('[data-track]');return {c,page};}
try{
 for(const [state,title,part]of [['music-beats-failed','CRUSH VIBE','beat'],['music-tags-failed','Fever Pitch','tags']]){
  const {c,page}=await pageWith(fixture(state));let request;
  await c.route('**/reanalyze',async r=>{request=r.request().postDataJSON();await new Promise(resolve=>setTimeout(resolve,2000));await r.fulfill({status:500,json:{ok:false,error:{message:'请求失败'}}});});
  await page.locator('[data-track]').filter({hasText:title}).click();await page.locator(`[data-retry-part="${part}"]`).click();
  if(part==='beat'){await page.waitForFunction(()=>document.querySelector('.main').dataset.designState==='music-beats-analyzing');assert((await page.locator('[data-track][aria-selected="true"]').innerText()).includes('分析中'));}
  else{assert.equal(await page.locator('.tg .bm-state').innerText(),'分析中');assert((await page.locator('[data-track][aria-selected="true"]').innerText()).includes('分析中'));assert.equal(await page.locator('.bm-lane').count(),1);}
  if(process.env.R223_EVIDENCE){const canonical=await page.locator('.main').getAttribute('data-design-state'),collect=fs.readFileSync(path.join(process.env.HARNESS_CORE_ROOT,'skills/ui-copy-quality/assets/collect_design_inventory.js'),'utf8');const inv=await page.evaluate(({collect,canonical})=>new Function(collect+';return collectDesignInventory;')()({states:{[canonical]:'.main'}}),{collect,canonical});fs.writeFileSync(process.env.R223_EVIDENCE+'/optimistic-'+part+'-inventory.json',JSON.stringify(inv,null,2));}
  await page.waitForSelector(`[data-retry-part="${part}"]`);assert.deepEqual(request,{part});assert.equal(await page.locator('.main').getAttribute('data-design-state'),state);assert.equal(await page.locator('#toast').innerText(),'请求失败');checks.push(part+' optimistic list+rail; delayed HTTP failure restores state; correct part');await c.close();
 }
 {
  const payload=fixture('music-beats-failed');payload.tracks[0].tags=fixture('music-tags-failed').tracks.find(t=>t.tags.status==='failed').tags;const {c,page}=await pageWith(payload);
  await c.route('**/reanalyze',async r=>{await new Promise(resolve=>setTimeout(resolve,r.request().postDataJSON().part==='beat'?300:2400));await r.fulfill({status:500,json:{ok:false,error:{message:'请求失败'}}});});
  await page.locator('[data-track]').filter({hasText:'CRUSH VIBE'}).click();await page.locator('[data-retry-part="beat"]').click();await page.locator('[data-retry-part="tags"]').click();await page.waitForSelector('[data-retry-part="beat"]');await page.waitForTimeout(1100);assert.equal(await page.locator('.tg .bm-state').innerText(),'分析中');if(process.env.R223_EVIDENCE){const canonical=await page.locator('.main').getAttribute('data-design-state'),collect=fs.readFileSync(path.join(process.env.HARNESS_CORE_ROOT,'skills/ui-copy-quality/assets/collect_design_inventory.js'),'utf8');const inv=await page.evaluate(({collect,canonical})=>new Function(collect+';return collectDesignInventory;')()({states:{[canonical]:'.main'}}),{collect,canonical});fs.writeFileSync(process.env.R223_EVIDENCE+'/optimistic-concurrent-inventory.json',JSON.stringify(inv,null,2));}await page.waitForSelector('[data-retry-part="tags"]');checks.push('simultaneous beat/tags retry: one failure cannot clear the other optimistic state');await c.close();
 }
 {
  const {c,page}=await pageWith(fixture('music'));await page.locator('[data-toggle-music]').click();await page.waitForFunction(()=>document.querySelector('#music-player').currentTime>.1);const before=await page.locator('.bm-overview').elementHandle();await page.waitForTimeout(350);assert(await before.evaluate(n=>n===document.querySelector('.bm-overview')));assert.equal(await page.locator('[data-toggle-music]').getAttribute('aria-label'),'暂停');
  await page.locator('#music-player').evaluate(p=>{p.pause();p.currentTime=4.18;p.dispatchEvent(new Event('timeupdate'));});await page.waitForSelector('.bc.hit');assert.equal(await page.locator('.bc.hit').first().evaluate(n=>getComputedStyle(n).backgroundColor),'rgb(228, 235, 235)');
  await page.locator('.bm-band').click({position:{x:160,y:3}});assert((await page.locator('#music-player').evaluate(p=>p.currentTime))>20);checks.push('real copied audio plays; RAF keeps overview node; current beat becomes white; band seeks');await c.close();
 }
 {
  const c=await browser.newContext();await c.route('**/*',r=>new URL(r.request().url()).origin===base?r.continue():r.abort());const times=[];let calls=0;
  await c.route('**/api/review/music',r=>{times.push(Date.now());calls++;let value=fixture(calls<3?'music-beats-queued':'music');if(calls===2){const active=fixture('music-beats-analyzing').tracks.find(t=>t.beat.status==='analyzing');value.tracks[1].beat=active.beat;value.tracks[1].tags=active.tags;}return r.fulfill({json:value});});
  const page=await c.newPage();await page.goto(base+'/#view=music');await page.waitForFunction(()=>document.querySelector('.main').dataset.designState==='music-beats-queued');await page.waitForFunction(()=>document.querySelector('.main').dataset.designState==='music-beats-analyzing');await page.waitForFunction(()=>document.querySelector('.main').dataset.designState==='music');const count=calls;await page.waitForTimeout(1600);assert.equal(calls,count);assert(times[1]-times[0]<=1200&&times[2]-times[1]<=1200);checks.push('queued → analyzing → done without reload; ~1s non-overlapping polling stops when complete');await c.close();
 }
 {
  const payload=fixture('music'),display=payload.taxonomy.display;display.panel_order.reverse();display.filter_order.reverse();display.panel_title='临时测试标题';payload.taxonomy.sections[0].name='临时测试段名';payload.taxonomy.tag_categories.find(c=>c.id==='genre').name='临时测试组名';
  const {c,page}=await pageWith(payload);
  const actualOrder=await page.locator('[data-tag]').evaluateAll(ns=>ns.map(n=>n.dataset.tag));
  const expectedOrder=display.filter_order.flatMap(g=>payload.taxonomy.tag_categories.find(c=>c.id===g).tags.filter(t=>t.status==='active').map(t=>({id:t.id,n:payload.tracks.filter(m=>m.tags.status==='done'&&(m.tags[g]||[]).includes(t.id)).length})).filter(t=>t.n).sort((a,b)=>b.n-a.n).map(t=>t.id));
  assert.deepEqual(actualOrder,expectedOrder);checks.push('facet order: descending count; equal counts follow taxonomy order');
  assert.equal(await page.locator('.tg-head').innerText(),display.panel_title);assert.deepEqual(await page.locator('.tg-row').evaluateAll(ns=>ns.map(n=>n.dataset.category)),display.panel_order);assert((await page.locator('.bm-legend').innerText()).includes('临时测试段名'));assert((await page.locator('.tg').innerText()).includes('临时测试组名'));checks.push('taxonomy panel title, group names, section names and order reach the mounted page');await c.close();
 }
 console.log('PASS',checks.length,'music interaction checks');
 if(process.env.R223_EVIDENCE)fs.writeFileSync(process.env.R223_EVIDENCE+'/interactions.json',JSON.stringify({result:'PASS',checks},null,2));
}finally{await browser.close();}
