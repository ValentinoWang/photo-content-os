import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import assert from 'node:assert/strict';import {createRequire} from 'node:module';import {fileURLToPath} from 'node:url';
const {chromium}=createRequire(process.env.PW_REQ)('playwright'),root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),base=process.env.STUDIO_URL;
if(!base||new URL(base).port==='8765')throw Error('Use isolated Studio URL');
const out=path.resolve(process.env.R223_SCREENSHOTS),evidence=path.resolve(process.env.R223_EVIDENCE),core=process.env.HARNESS_CORE_ROOT;fs.mkdirSync(out,{recursive:true});fs.mkdirSync(evidence,{recursive:true});
const collect=fs.readFileSync(path.join(core,'skills/ui-copy-quality/assets/collect_design_inventory.js'),'utf8');
const contract=JSON.parse(fs.readFileSync(path.join(root,'docs/tasks/R223-music-beat-map/mock/design-contract.json'))),approved=JSON.parse(fs.readFileSync(path.join(root,'tests/fixtures/r223/frontend/approved-copy.json')));
const sizes=[[1440,960],[1180,860],[430,932]],cases=[['music','music','Turn Back Time',0],['music-playing','music','Turn Back Time',88.4],['music-intro','music','CRUSH VIBE',2],['music-end','music','Fever Pitch',133],['music-beats-queued','music-beats-queued','Turn Back Time',0],['music-beats-analyzing','music-beats-analyzing','夏日漱石',0],['music-beats-failed','music-beats-failed','CRUSH VIBE',0],['music-beats-failed-unreadable','music-beats-failed-unreadable','CRUSH VIBE',0],['music-beats-failed-unknown','music-beats-failed-unknown','CRUSH VIBE',0],['music-tags-failed','music-tags-failed','Fever Pitch',0],['music-filtered','music','Turn Back Time',0],['music-filter-empty','music-filter-empty','Turn Back Time',0]];
const only=process.env.ONLY_STATES?new Set(process.env.ONLY_STATES.split(',')):null,onlyWidths=process.env.ONLY_WIDTHS?new Set(process.env.ONLY_WIDTHS.split(',').map(Number)):null;
const affected=r=>(!only||only.has(r.name))&&(!onlyWidths||onlyWidths.has(r.width));
const read=name=>JSON.parse(fs.readFileSync(path.join(evidence,name)));
if(only&&[...only].some(s=>s.startsWith('real-')))cases.push(['real-queued-projection','music-beats-queued','Turn Back Time',0],['real-normal-projection','music','Turn Back Time',0]);
const browser=await chromium.launch({channel:'chrome'}),manifest=only?read('screenshot-manifest.json').filter(r=>!affected(r)):[],numbers=only?read('number-formulas.json').filter(r=>!affected(r)):[],inventories=only?read('inventory-index.json').filter(r=>{const match=r.key.match(/^(.*)-(1440|1180|430)(?:-open)?$/);return !match||!affected({name:match[1],width:Number(match[2])});}):[],errors=[];
const checksum=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
async function context(real=false,scale=1){const c=await browser.newContext({viewport:{width:1440,height:960},deviceScaleFactor:scale,locale:'zh-CN',timezoneId:'Asia/Taipei'});await c.route('**/*',r=>{const u=new URL(r.request().url());return u.protocol==='file:'||u.origin===base?r.continue():r.abort();});return c;}
async function inventory(page,state){return page.evaluate(({collect,state})=>{const fn=new Function(collect+';return collectDesignInventory;')();return fn({states:{[state]:'.main'}}).states[state];},{collect,state});}
async function capture(page,name,width,height,kind,open=false){
 const file=path.join(out,`${kind}-${name}-${width}${open?'-open':''}.png`);await page.screenshot({path:file,fullPage:true});
 const measure=await page.evaluate(()=>({width:innerWidth,height:innerHeight,scrollHeight:document.documentElement.scrollHeight,scrollWidth:document.documentElement.scrollWidth,rail:document.querySelector('#rail')?{height:document.querySelector('#rail').clientHeight,scrollHeight:document.querySelector('#rail').scrollHeight}:null}));assert.equal(measure.width,width);assert(measure.scrollWidth<=width+1,'horizontal overflow '+name);
 const item={name,width,height,open,kind,file:path.basename(file),sha256:checksum(file),captured_at:new Date().toISOString(),route:kind==='mock'?`mock/beat-map.html?state=${name}`:'#view=music',browser:'Chrome',font_mode:'fallback-local',animation_clock:name==='music-playing'?'frozen playback sample at 88.4s':'live',measure};manifest.push(item);
 if(open&&measure.rail?.scrollHeight>measure.rail?.height+1){
  const rail=page.locator('#rail'),total=measure.rail.scrollHeight,view=measure.rail.height;item.scroll_frames=[];
  for(let scroll=0;scroll<total;scroll+=Math.max(1,view-80)){await rail.evaluate((n,y)=>{n.scrollTop=y;},scroll);const actual=await rail.evaluate(n=>n.scrollTop);const part=file.replace('.png',`-panel-${item.scroll_frames.length+1}.png`);await rail.screenshot({path:part});item.scroll_frames.push({file:path.basename(part),top:actual,height:view});if(actual+view>=total)break;}
  await rail.evaluate(n=>n.scrollTop=0);
 }
 return item;
}
async function seek(page,t){if(!t)return;await page.locator('#music-player').evaluate(async(p,t)=>{const row=document.querySelector('[data-track][aria-selected="true"]');if(!p.src){p.src='/api/review/music/'+row.dataset.track+'/audio';p.dataset.id=row.dataset.track;}if(p.readyState<1)await new Promise((resolve,reject)=>{p.addEventListener('loadedmetadata',resolve,{once:true});p.addEventListener('error',reject,{once:true});p.load();});p.currentTime=t;await new Promise(r=>p.addEventListener('seeked',r,{once:true}));p.dispatchEvent(new Event('timeupdate'));},t);}
async function freezeFrame(page,t,install=false){
 if(install){const instant=new Date('2026-10-21T04:00:00+08:00');await page.clock.install({time:instant});await page.clock.pauseAt(instant);}
 await page.locator('#music-player').evaluate(async(p,t)=>{await p.play();await new Promise(resolve=>{p.addEventListener('seeked',resolve,{once:true});p.currentTime=t;});p.__captureTick=p.ontimeupdate||p.__captureTick;p.ontimeupdate=null;p.__captureTick?.();},t);
}
function expectedMetrics(map){const d=map.beats.slice(1).map((x,i)=>x-map.beats[i]).sort((a,b)=>a-b),n=d.length,median=n%2?d[(n-1)/2]:(d[n/2-1]+d[n/2])/2;const counts={};map.downbeats.slice(1).forEach((x,i)=>{const v=map.beats.indexOf(x)-map.beats.indexOf(map.downbeats[i]);counts[v]=(counts[v]||0)+1;});return {bpm:Math.round(60/median),meter:Number(Object.keys(counts).sort((a,b)=>counts[b]-counts[a]||Number(a)-Number(b))[0])};}
async function checkNumbers(page,payload,name,t){
 const result=await page.evaluate(({payload,t})=>{
  const selected=document.querySelector('[data-track][aria-selected="true"]')?.dataset.track,m=payload.tracks.find(m=>m.file_sha256===selected);const shown=[...document.querySelectorAll('[data-track]')].map(n=>n.dataset.track),src=document.querySelector('[data-src][aria-pressed="true"]')?.dataset.src,tags=[...document.querySelectorAll('[data-tag][aria-pressed="true"]')].map(n=>n.dataset.tag);
  return {selected,shown,src,tags,sourceCounts:Object.fromEntries([...document.querySelectorAll('[data-src]')].map(n=>[n.dataset.src,Number(n.querySelector('i').textContent)])),tagCounts:Object.fromEntries([...document.querySelectorAll('[data-tag]')].map(n=>[n.dataset.tag,Number(n.querySelector('i').textContent)])),listSpeeds:Object.fromEntries([...document.querySelectorAll('[data-track]')].map(n=>[n.dataset.track,n.children[4]?.textContent.trim()])),speed:document.querySelector('[data-design-id="R223-BEAT-speed"]')?.textContent,bar:document.querySelector('.bm-bar')?.textContent,kind:document.querySelector('.bm-kind')?.textContent,queue:document.querySelector('.bm-status')?.textContent,windowStart:Number(document.querySelector('.bm-lane')?.dataset.windowStart),columns:[...document.querySelectorAll('.bc')].map(n=>({t:Number(n.dataset.beat),energy:Number(n.dataset.energy),height:parseFloat(n.style.height)})),barNumbers:[...document.querySelectorAll('.bn')].map(n=>({n:Number(n.textContent),left:parseFloat(n.style.left)})),bands:[...document.querySelectorAll('[data-section-kind]')].map(n=>({start:Number(n.dataset.start),end:Number(n.dataset.end),width:n.style.width})),panelOrder:[...document.querySelectorAll('.tg-row')].map(n=>n.dataset.category),rowTags:Object.fromEntries([...document.querySelectorAll('[data-track]')].map(n=>[n.dataset.track,[...n.querySelectorAll('.tag')].map(n=>n.textContent)]))};
 },{payload,t});
 const srcOK=m=>result.src==='all'||(m.platform==='netease_client'?'netease':m.platform)===result.src,groups=payload.taxonomy.display.filter_order,tagIds=(m,g)=>m.tags.status==='done'?m.tags[g]||[]:[],groupOK=(m,g)=>{const selected=result.tags.filter(x=>x.startsWith(g+'.'));return !selected.length||selected.some(x=>tagIds(m,g).includes(x));};
 const expected=payload.tracks.filter(m=>srcOK(m)&&groups.every(g=>groupOK(m,g))).map(m=>m.file_sha256);assert.deepEqual(result.shown,expected,name+' filtered rows');
 for(const [source,n]of Object.entries(result.sourceCounts))assert.equal(n,source==='all'?payload.tracks.length:payload.tracks.filter(m=>(m.platform==='netease_client'?'netease':m.platform)===source).length,name+' source counts');
 for(const [id,n]of Object.entries(result.tagCounts)){const g=id.split('.')[0];assert.equal(n,payload.tracks.filter(m=>srcOK(m)&&groups.every(o=>o===g||groupOK(m,o))&&tagIds(m,g).includes(id)).length,name+' facets');}
 const labels=Object.fromEntries(payload.taxonomy.tag_categories.flatMap(c=>c.tags.map(t=>[t.id,t.name])));
 for(const m of payload.tracks.filter(m=>result.shown.includes(m.file_sha256))){if(m.beat.status==='done')assert.equal(result.listSpeeds[m.file_sha256],expectedMetrics(m.beat).bpm+' BPM');if(m.tags.status==='done'){const ids=payload.taxonomy.display.row.map(r=>tagIds(m,r.category)[0]||(r.fallback?tagIds(m,r.fallback)[0]:null)).filter(Boolean);assert.deepEqual(result.rowTags[m.file_sha256],ids.map(id=>labels[id]));}}
 const m=payload.tracks.find(m=>m.file_sha256===result.selected);
 if(m?.beat.status==='done'){
  const metrics=expectedMetrics(m.beat);assert(result.speed.includes(metrics.bpm+' BPM'));assert(result.speed.includes('每小节 '+metrics.meter+' 拍'));
  const bar=m.beat.downbeats.filter(x=>x<=t).length;assert.equal(result.bar?.replace(/\s+/g,''),bar?`第${bar}小节`:'');
  const section=m.beat.sections.find(s=>s.start<=t&&t<s.end)||m.beat.sections.at(-1);assert.equal(result.kind,payload.taxonomy.sections.find(s=>s.id===section.kind).name);
  const a=Math.min(Math.max(0,t-4),Math.max(0,m.duration_seconds-8));assert(Math.abs(result.windowStart-a)<.001,name+' window');
  for(const column of result.columns)assert(Math.abs(column.height-(10+40*column.energy))<.001,'column height');
  for(const item of result.barNumbers){const x=m.beat.downbeats[item.n-1];assert(Math.abs(item.left-(x-a)/8*100)<.01,'bar label');}
  for(const band of result.bands)assert(band.width.includes(String(100*(band.end-band.start)/m.duration_seconds).slice(0,6))||Math.abs(parseFloat(band.width.match(/[\d.]+/)[0])-100*(band.end-band.start)/m.duration_seconds)<.001,'band width');
  if(m.tags.status==='done')assert.deepEqual(result.panelOrder,payload.taxonomy.display.panel_order);
 }
 if(m?.beat.status==='queued'){const n=payload.tracks.slice(0,payload.tracks.indexOf(m)).filter(m=>['queued','analyzing'].includes(m.beat.status)).length;assert(result.queue.includes('前面还有 '+n+' 首。'));}
 numbers.push({name,result:'PASS',checked:['BPM','meter','current bar','lane bar ordinal','section name','ahead count','8s window','energy height','section width','source counts','facet counts','derived tags'],observed:result});
}
try{
 // The actual copied library remains queued until these screenshots are complete.
 if(!only){const realContext=await context(true),real=await realContext.newPage();await real.goto(base+'/#view=music');await real.waitForSelector('[data-track]');
 const realQueued=await (await fetch(base+'/api/review/music')).json();assert(realQueued.tracks.every(m=>['queued','analyzing'].includes(m.beat.status)));
 for(const [w,h] of sizes){await real.setViewportSize({width:w,height:h});await capture(real,'real-queued',w,h,'implementation');if(w===430){await real.locator('[data-track]').filter({hasText:'Turn Back Time'}).click();await capture(real,'real-queued',w,h,'implementation',true);await real.locator('[data-close-rail]').click();}}
 await realContext.close();}
 for(const [name,state,title,t]of cases){if(only&&!only.has(name))continue;
  const payload=JSON.parse(fs.readFileSync(name.startsWith('real-')?path.join(process.env.R223_REAL_FIXTURES,name+'.json'):path.join(root,'tests/fixtures/r223/frontend',state+'.json'))),ctx=await context();await ctx.route('**/api/review/music',r=>r.fulfill({json:payload}));const page=await ctx.newPage();page.on('pageerror',e=>errors.push({name,message:e.message}));await page.goto(base+'/#view=music');await page.waitForSelector('[data-track]');
  if(title!=='Turn Back Time')await page.locator('[data-track]').filter({hasText:title}).click();
  if(name==='music-filtered'||name==='music-filter-empty')await page.locator('[data-tag="scene.summer"]').click();if(name==='music-filtered')await page.locator('[data-tag="voice.voice"]').click();if(name==='music-filter-empty')await page.locator('[data-src="local"]').click();
  await seek(page,t);assert.equal(await page.locator('.main').getAttribute('data-design-state'),state,name+' state');await checkNumbers(page,payload,name,t);if(name==='music-playing')await freezeFrame(page,t,true);
  const mc=await context(),mock=await mc.newPage();await mock.goto('file://'+path.join(root,'docs/tasks/R223-music-beat-map/mock/beat-map.html')+'?state='+(name.startsWith('real-')?state:name));await mock.addStyleTag({content:'#mockbar{display:none}'});
  for(const [w,h]of sizes){if(onlyWidths&&!onlyWidths.has(w))continue;await page.setViewportSize({width:w,height:h});await mock.setViewportSize({width:w,height:h});if(w===430){await page.locator('[data-close-rail]').evaluateAll(ns=>ns.forEach(n=>n.click()));}
   if(name==='music-playing')await freezeFrame(page,t);await capture(page,name,w,h,'implementation');await capture(mock,name,w,h,'mock');
   const inv=await inventory(page,state),mi=await inventory(mock,state),extras=structuredClone(approved);extras.optional_ids={[state]:contract.states[state].ids.filter(id=>!mi.ids.includes(id))};
   const key=name+'-'+w;fs.writeFileSync(path.join(evidence,key+'-inventory.json'),JSON.stringify({states:{[state]:inv}},null,2));fs.writeFileSync(path.join(evidence,key+'-extras.json'),JSON.stringify(extras,null,2));inventories.push({key,state});
   if(w===430&&name!=='music-filter-empty'){await page.locator('[data-track][aria-selected="true"]').click();await mock.evaluate(()=>document.querySelector('#rail')?.classList.add('open'));if(name==='music-playing')await freezeFrame(page,t);await capture(page,name,w,h,'implementation',true);await capture(mock,name,w,h,'mock',true);const openInv=await inventory(page,state);fs.writeFileSync(path.join(evidence,key+'-open-inventory.json'),JSON.stringify({states:{[state]:openInv}},null,2));fs.writeFileSync(path.join(evidence,key+'-open-extras.json'),JSON.stringify(approved,null,2));inventories.push({key:key+'-open',state});}
  }
  if(['music','music-playing','music-intro','music-end'].includes(name)&&(!onlyWidths||onlyWidths.has(1440))){
   const zc=await context(false,2);await zc.route('**/api/review/music',r=>r.fulfill({json:payload}));const zp=await zc.newPage();await zp.goto(base+'/#view=music');await zp.waitForSelector('[data-track]');if(title!=='Turn Back Time')await zp.locator('[data-track]').filter({hasText:title}).click();await seek(zp,t);if(name==='music-playing')await freezeFrame(zp,t,true);
   const zmc=await context(false,2),zmp=await zmc.newPage();await zmp.goto('file://'+path.join(root,'docs/tasks/R223-music-beat-map/mock/beat-map.html')+'?state='+name);await zmp.addStyleTag({content:'#mockbar{display:none}'});
   for(const [kind,p] of [['implementation',zp],['mock',zmp]]){const file=path.join(out,kind+'-'+name+'-rail-2x.png');await p.locator('#rail').screenshot({path:file});manifest.push({name,kind,width:1440,height:960,deviceScaleFactor:2,file:path.basename(file),sha256:checksum(file),captured_at:new Date().toISOString(),route:kind==='mock'?'mock/beat-map.html?state='+name:'#view=music',browser:'Chrome',font_mode:'fallback-local'});}
   await zc.close();await zmc.close();
  }
  await ctx.close();await mc.close();console.log('Captured',name);
 }
 if(!only){fs.writeFileSync(path.join(out,'release-analysis'),'ready');
 const end=Date.now()+240000;let payload;
 while(Date.now()<end){payload=await (await fetch(base+'/api/review/music')).json();if(payload.tracks.every(m=>m.beat.status==='done'&&m.tags.status==='done'))break;await new Promise(r=>setTimeout(r,500));}
 assert(payload.tracks.every(m=>m.beat.status==='done'&&m.tags.status==='done'),'copy real analysis');
 const doneCtx=await context(true),done=await doneCtx.newPage();await done.goto(base+'/#view=music');await done.waitForSelector('.bm-lane');await checkNumbers(done,payload,'real-normal',0);
 for(const [w,h]of sizes){if(onlyWidths&&!onlyWidths.has(w))continue;await done.setViewportSize({width:w,height:h});await capture(done,'real-normal',w,h,'implementation');if(w===430){await done.locator('[data-track][aria-selected="true"]').click();await capture(done,'real-normal',w,h,'implementation',true);}}
 await doneCtx.close();}assert.deepEqual(errors,[]);
 console.log('PASS capture matrix and all 12 numeric formula rows');
}finally{fs.writeFileSync(path.join(evidence,'screenshot-manifest.json'),JSON.stringify(manifest,null,2));fs.writeFileSync(path.join(evidence,'number-formulas.json'),JSON.stringify(numbers,null,2));fs.writeFileSync(path.join(evidence,'inventory-index.json'),JSON.stringify(inventories,null,2));fs.writeFileSync(path.join(evidence,'browser-errors.json'),JSON.stringify(errors,null,2));await browser.close();}
