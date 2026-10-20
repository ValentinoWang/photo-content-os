// TASK explicitly requests this Playwright matrix. Mock file URLs are excluded.
import {createRequire} from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {expectedShots,compareNumbers} from './r220_number_formulas.mjs';
const require=createRequire(process.env.PW_REQ),{chromium}=require('playwright');
const base=process.env.STUDIO_URL||'http://127.0.0.1:8870',out=path.resolve(process.env.R220_EVIDENCE||'evidence/2026-10-20/R220/round-2');
const json=async url=>{const r=await fetch(base+url);if(!r.ok)throw Error(url+': '+r.status);return r.json();};
const catalog=await json('/api/review/catalog');
const p=catalog.pieces.find(p=>p.pending),g=catalog.groups.find(g=>g.id===p.group_id),other=catalog.pieces.find(x=>x.photos&&!x.pending&&!x.versions);
if(!p)throw Error('Real shot-result piece is missing');
const shotData=await json(`/api/review/pieces/${p.id}/shots`),musicData=await json('/api/review/music');
const diagnostics=(await json('/api/diagnostics')).diagnostics;
const clean=()=>structuredClone(shotData);
const recount=d=>{const x=expectedShots(d);d.counts=x.counts;d.duration=x.duration;d.selected=d.shots.filter(s=>s.status==='selected').map(s=>s.id);return d;};
const cases=[
 ['home',{view:'home'}],['inbox',{view:'inbox'}],['projects',{view:'projects'}],['project',{view:'project',project:g.id}],
 ['piece-review',{view:'piece',piece:p.id,ptab:'vlog'}],['piece-review-alt',{view:'piece',piece:p.id,ptab:'vlog'},'alt'],
 ['piece-confirmed',{view:'piece',piece:p.id,ptab:'vlog'},'confirmed'],['piece-partial',{view:'piece',piece:p.id,ptab:'vlog'},'partial'],
 ['piece-running',{view:'piece',piece:p.id,ptab:'vlog'},'running'],['piece-empty',{view:'piece',piece:p.id,ptab:'vlog'},'empty'],
 ['piece-not-started',{view:'piece',piece:p.id,ptab:'vlog'},'not-started'],
 ['piece-not-started-photos',{view:'piece',piece:other.id,ptab:'vlog'}],
 ['piece-script',{view:'piece',piece:p.id,ptab:'script'}],['player-reel',{view:'home'},'reel'],['player-versions',{view:'project',project:g.id},'versions'],
 ['library',{view:'library'},'library'],['library-empty',{view:'library'}],['music',{view:'music'}],['music-empty',{view:'music'},'music-empty'],['music-importing',{view:'music'},'importing'],
 ['music-dup',{view:'music'},'duplicate'],['music-vip',{view:'music'},'member'],['music-douyin',{view:'music'},'douyin'],
 ...['places','tools','models','music','account','doctor'].map(t=>['settings-'+t,{view:'settings',tab:t}])
];
if(process.env.R220_SUPPLEMENT){cases.length=0;cases.push(['piece-failed',{view:'piece',piece:p.id,ptab:'vlog'},'failed'],['piece-stopped',{view:'piece',piece:p.id,ptab:'vlog'},'stopped'],['piece-unconnected',{view:'piece',piece:catalog.pieces[0].id,ptab:'vlog'},'unconnected']);}
const selectedCases=process.env.ONLY_STATES?new Set(process.env.ONLY_STATES.split(',')):null;
const existing=selectedCases?JSON.parse(fs.readFileSync(path.join(out,'number-formulas.json'))):{numbers:[],errors:[]};
const browser=await chromium.launch({channel:'chrome'}),manifest=selectedCases?JSON.parse(fs.readFileSync(path.join(out,'screenshot-manifest.json'))).filter(r=>!selectedCases.has(r.name)):[],inventory=selectedCases?JSON.parse(fs.readFileSync(path.join(out,'design-inventory.json'))):{states:{}},numbers=existing.numbers.filter(r=>!selectedCases?.has(r.name)),errors=existing.errors.filter(r=>!selectedCases?.has(r.name));
if(!process.env.HARNESS_CORE_ROOT)throw Error('Set HARNESS_CORE_ROOT to the installed Harness Core directory');
const collect=fs.readFileSync(path.join(process.env.HARNESS_CORE_ROOT,'skills/ui-copy-quality/assets/collect_design_inventory.js'),'utf8');
try{
 for(const [name,route,mode]of cases){
  if(selectedCases&&!selectedCases.has(name))continue;
  const context=await browser.newContext({viewport:{width:1440,height:960},locale:'zh-CN',timezoneId:'Asia/Taipei'});
  let fixture=['confirmed','partial','running','empty','not-started','failed','stopped','unconnected','library','music-empty','importing','duplicate','member','douyin'].includes(mode),activeData=clean();
  if(mode==='confirmed')activeData.confirmed=true;
  if(mode==='partial'){activeData.partial=true;activeData.confirmed=false;activeData.model_progress.completed=Math.floor(activeData.model_progress.total/2);activeData.shots.filter(s=>s.scene.startsWith('travel')&&s.status!=='rejected').forEach(s=>{s.status=null;s.model_decision=null;});recount(activeData);}
  if(['failed','stopped'].includes(mode)){activeData.partial=true;activeData.confirmed=false;activeData.run_status=mode;activeData.progress={status:mode,reason:mode==='failed'?'看图请求中断。':'挑选进程因信号 15 停止。'};}
  if(mode==='running')activeData.progress={status:'running',phase:'model',completed:3,total:activeData.model_progress.total||10};
  if(['empty','not-started'].includes(mode)){activeData.shots=[];activeData.partial=false;activeData.run_status='not_started';recount(activeData);}
  await context.route('**/*',async request=>{
   const url=new URL(request.request().url());
   if(url.origin!==base)return request.abort();
   if(url.pathname===`/api/review/pieces/${p.id}/shots`&&fixture&&['confirmed','partial','running','empty','not-started','failed','stopped'].includes(mode))return request.fulfill({json:activeData});
   if(mode==='unconnected'&&url.pathname==='/api/review/catalog'){const c=structuredClone(catalog);for(const x of [...c.pieces,...c.groups.flatMap(g=>g.pieces)])if(x.id===catalog.pieces[0].id)x.connected=false;return request.fulfill({json:{ok:true,...c}});}
   if(mode==='not-started'&&url.pathname==='/api/review/catalog'){const c=structuredClone(catalog);for(const x of [...c.pieces,...c.groups.flatMap(g=>g.pieces)])if(x.id===p.id){x.outputs=[];x.versions=0;}return request.fulfill({json:{ok:true,...c}});}
   if(mode==='library'&&url.pathname==='/api/assets'){return request.fulfill({json:{ok:true,assets:shotData.shots.filter(s=>s.status==='selected'&&s.kind==='video').slice(0,3).map(s=>({asset_id:s.id,title:s.name,category:s.scene_name,source_project:p.workspace_key,public_status:'还没定',uses:[]}))}});}
   if(mode==='library'&&url.pathname==='/api/assets/statistics')return request.fulfill({json:{ok:true,statistics:{asset_count:3,categories:[],tags:[]}}});
   if(mode==='library'&&url.pathname.startsWith('/api/review/assets/')){const id=url.pathname.split('/')[4];return request.fulfill({response:await request.fetch({url:base+`/api/review/pieces/${p.id}/media/shot/${id}`})});}
   if(mode==='music-empty' &&url.pathname==='/api/review/music')return request.fulfill({json:{ok:true,tracks:[]}});
   if(['importing','duplicate','member','douyin'].includes(mode)&&url.pathname==='/api/review/music/import')return request.fulfill({json:{ok:true,job:{id:'fixture',state:'importing'}}});
   if(url.pathname==='/api/review/imports/fixture')return request.fulfill({json:{ok:true,job:{id:'fixture',state:mode==='douyin'?'error':mode,title:musicData.tracks[0].title,reason:'没从抖音取到这首的音乐。可以在剪映里直接用原声，或者找这首歌在汽水音乐、网易云音乐的分享链接。'}}});
   // Capture never starts an AI job or writes actual shot decisions.
   if(request.request().method()!=='GET'&&url.pathname.startsWith('/api/review/'))return request.abort();
   return request.continue();
  });
  const page=await context.newPage();page.on('pageerror',e=>errors.push({name,message:e.message}));
  await page.goto(base+'/#'+new URLSearchParams(route));
  await page.waitForFunction(()=>document.querySelector('.main')?.dataset.designState&&document.querySelector('#review-screen')?.children.length);
  await page.waitForTimeout(350);
  if(name==='library'){await page.waitForSelector('[data-design-id="R208-LIBRARY"]');await page.waitForFunction(()=>[...document.querySelectorAll('#review-screen video')].every(v=>v.readyState>=2&&v.videoWidth>0));await page.locator('.viewer video').evaluate(v=>{v.muted=true;return v.play();});await page.waitForFunction(()=>document.querySelector('.viewer video').currentTime>.15);await page.locator('.viewer video').evaluate(v=>v.pause());}
  if(mode==='alt'){await page.locator('[data-shot]').first().click();await page.locator('.more-d summary').click();await page.waitForTimeout(150);}
  if(mode==='reel'){await page.locator('[data-reel]').first().click();await page.waitForSelector('#ov:not([hidden])');}
  if(mode==='versions'){await page.locator('[data-versions]').first().click();await page.waitForSelector('#ov:not([hidden])');}
  if(['importing','duplicate','member','douyin'].includes(mode)){await page.locator('#paste').fill('https://music.163.com/song?id=123');await page.locator('#music-import').evaluate(form=>form.requestSubmit());await page.waitForTimeout(250);}
  const actual=await page.locator('.main').getAttribute('data-design-state');
  if(actual!==(name==='piece-unconnected'?'piece-empty':['piece-failed','piece-stopped'].includes(name)?'piece-partial':name))errors.push({name,message:'State mismatch: '+actual});
  const inv=await page.evaluate(({collect,name})=>{
   const collectDesignInventory=new Function(collect+';return collectDesignInventory;')();const result=collectDesignInventory({states:{[name]:'#app'}}).states[name];
   const ov=document.querySelector('#ov');if(!ov.hidden){const extra=collectDesignInventory({states:{[name]:'#ov'}}).states[name];result.texts.push(...extra.texts);result.ids=[...new Set([...result.ids,...extra.ids,ov.dataset.designId])];}
   return result;
  },{collect,name});inventory.states[name]=inv;
  if(name.startsWith('piece-')&&name!=='piece-script'&&name!=='piece-unconnected'&&!['piece-empty','piece-not-started','piece-not-started-photos'].includes(name)){
   const expected=expectedShots(activeData);const observed={};
   if(mode!=='running'){
    observed.selected=Number((await page.locator('[data-design-id="R208-REV-head"] h2').innerText()).match(/\d+/)?.[0]);
    for(const status of ['usable','unused','rejected'])observed[status]=Number(await page.locator(`[data-filter="${status}"] i`).innerText());
    numbers.push({name,failures:compareNumbers(observed,expected.counts),expected,observed});
    const widths=await page.locator('#hero-prog button').evaluateAll(nodes=>nodes.map(n=>Number(getComputedStyle(n).flexGrow)));
    const expectedWidths=activeData.shots.filter(s=>s.status==='selected').map(s=>s.kind==='photo'?2.5:s.duration_sec);
    if(widths.length!==expectedWidths.length||widths.some((v,i)=>Math.abs(v-expectedWidths[i])>0.0001))errors.push({name,message:'Duration-weighted progress differs'});
   }else{
    const progress=await page.locator('[data-design-id="R208-REV-progress"]').innerText();if(!progress.includes(activeData.progress.completed+' / '+activeData.progress.total))errors.push({name,message:'Job progress differs'});
   }
  }
  const formulaFailures=[];
  const equal=(key,a,b)=>{if(a!==b)formulaFailures.push({key,observed:a,expected:b});};
  const numeric=async selector=>Number((await page.locator(selector).innerText()).match(/\d+/)?.[0]);
  const liveChecks=(await json('/api/diagnostics')).diagnostics.checks;
  const problems=liveChecks.filter(c=>c.status!=='ready');const issueCount=Number(problems.some(c=>c.id==='chatcut_mcp'))+Number(problems.some(c=>c.id.startsWith('edit_tool_')));
  const todo=catalog.pieces.filter(p=>p.pending).length+issueCount;
  equal('workbench badge',await numeric('#home-count'),todo);
  if(name==='home'||name==='player-reel'){
   equal('attention rows',await page.locator('.todo .task').count(),todo);
   equal('recent count',await page.locator('[data-design-id="R208-HOME-recent"] .piece').count(),Math.min(8,catalog.pieces.length));
  }
  if(name==='projects'){
   equal('project groups',await page.locator('.proj').count(),catalog.groups.length);
   for(let i=0;i<catalog.groups.length;i++){
    const card=page.locator('.proj').nth(i),group=catalog.groups[i];
    equal('group works '+i,Number((await card.locator('p').innerText()).match(/\d+/)[0]),group.pieces.length);
    const chips=(await card.locator('.chips').innerText()).replace(/\s+/g,'');
    if(group.pending&&!chips.includes(group.pending+'件等你过目'))formulaFailures.push({key:'pending group '+i});
    if(group.produced&&!chips.includes(group.produced+'件出过成片'))formulaFailures.push({key:'produced group '+i});
   }
  }
  if(name==='project'||name==='player-versions')equal('group grid',await page.locator('.pieces .piece').count(),g.pieces.length);
  if(name==='inbox'){
   const text=await page.locator('.facts').innerText();const ns=[...text.matchAll(/\d+/g)].map(x=>Number(x[0]));
   equal('organized works',ns[0],catalog.pieces.length);equal('videos',ns[1],catalog.pieces.reduce((a,p)=>a+p.videos,0));equal('photos',ns[2],catalog.pieces.reduce((a,p)=>a+p.photos,0));
  }
  if(name==='music'){
   equal('music total',await numeric('[data-src="all"] i'),musicData.tracks.length);
   for(const platform of ['qishui','netease','local']){
    const n=musicData.tracks.filter(t=>(t.platform==='netease_client'?'netease':t.platform)===platform).length;
    if(n)equal('platform '+platform,await numeric(`[data-src="${platform}"] i`),n);
   }
   for(const track of musicData.tracks){const text=await page.locator(`[data-track="${track.file_sha256}"]`).innerText();const t=Math.round(track.duration_seconds),duration=Math.floor(t/60)+':'+String(t%60).padStart(2,'0');if(!text.includes(duration))formulaFailures.push({key:'measured music duration '+track.file_sha256});}
  }
  if(name.startsWith('piece-')&&!['piece-unconnected','piece-script','piece-empty','piece-not-started','piece-not-started-photos','piece-running'].includes(name)){
   const list=activeData.shots.filter(s=>s.status==='selected'),t=Math.round(expectedShots(activeData).duration),duration=Math.floor(t/60)+':'+String(t%60).padStart(2,'0');
   const playerText=await page.locator('#hero-pos').innerText();if(!playerText.includes(duration))formulaFailures.push({key:'reel duration'});
   equal('board selected count',await page.locator('#hero-board [data-hero]').count(),list.length);
   for(const card of await page.locator('.scene-head').all()){
    const sceneName=await card.locator('h2').innerText(),ns=[...(await card.locator(':scope > span').innerText()).matchAll(/\d+/g)].map(x=>Number(x[0]));
    equal('scene usable '+sceneName,ns[0],activeData.shots.filter(s=>s.scene_name===sceneName&&s.status==='usable').length);equal('scene total '+sceneName,ns[1],activeData.shots.filter(s=>s.scene_name===sceneName).length);
   }
  }
  if(name==='settings-places'){
   const ns=[...(await page.locator('.setrow').first().innerText()).matchAll(/\d+/g)].map(x=>Number(x[0]));equal('stored projects',ns[0],catalog.groups.length);equal('stored works',ns[1],catalog.pieces.length);equal('stored music',await numeric('.setrow:nth-of-type(2) .val'),musicData.tracks.length);
  }
  if(name==='settings-doctor'){
   const ns=[...(await page.locator('.dx-ring').innerText()).matchAll(/\d+/g)].map(x=>Number(x[0]));equal('doctor passed',ns[0],liveChecks.filter(c=>c.status==='ready').length);equal('doctor total',ns[1],liveChecks.filter(c=>c.status==='ready').length+issueCount);
  }
  numbers.push({name,scope:'cross-surface formulas',failures:formulaFailures});
  for(const width of [1440,1180,900,430]){
   await page.setViewportSize({width,height:960});await page.evaluate(()=>window.scrollTo(0,0));
   // Load every lazy image across the actual document; then restore the top.
   await page.evaluate(async()=>{for(let y=0;y<document.documentElement.scrollHeight;y+=700){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,30));}window.scrollTo(0,0);});
   await page.evaluate(async()=>{const images=[...document.images];images.forEach(i=>i.loading='eager');await Promise.all(images.map(i=>i.decode().catch(()=>{})));});
   await page.waitForTimeout(100);
   const dimensions=await page.evaluate(()=>({width:innerWidth,height:innerHeight,scrollHeight:document.documentElement.scrollHeight,scrollWidth:document.documentElement.scrollWidth}));
   if(dimensions.width!==width)throw Error('Viewport did not take effect');
   const filename=`${name}-${width}.png`,file=path.join(out,filename);await page.screenshot({path:file,fullPage:true});
   manifest.push({name,route:page.url(),viewport:dimensions,captured_at:new Date().toISOString(),file:filename,sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),source:fixture?'real-media-state-fixture':'real-data',font_mode:'fallback-local',scroll_coverage:[0,dimensions.scrollHeight],review_result:'UNREVIEWED'});
   if(dimensions.scrollWidth>width)errors.push({name,width,message:'Horizontal overflow: '+dimensions.scrollWidth});
   console.log(name,width,dimensions.scrollHeight);
   if(name==='piece-review-alt'){
    const inspector=page.locator('#shot-panel > div');
    const size=await inspector.evaluate(n=>({total:n.scrollHeight,height:n.clientHeight}));
    if(size.total>size.height+1){
     let part=0;
     for(let offset=0;offset<size.total;offset+=Math.max(1,size.height-60)){
      const y=await inspector.evaluate((n,y)=>{n.scrollTop=y;return n.scrollTop;},offset);
      const file=`${name}-${width}-inspector-part-${++part}.png`;
      await inspector.screenshot({path:path.join(out,file)});
      manifest.push({name,part,viewport:dimensions,file,source:'real-data',captured_at:new Date().toISOString(),scroll_coverage:[y,Math.min(size.total,y+size.height)],sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(out,file))).digest('hex'),review_result:'UNREVIEWED'});
      if(y+size.height>=size.total)break;
     }
     await inspector.evaluate(n=>n.scrollTop=0);
    }
   }
  }
  if(mode==='library'){await page.locator('[data-asset]').first().click();await page.locator('[data-piece-go]').click();await page.waitForFunction(id=>document.querySelector('.main')?.dataset.designState.startsWith('piece-')&&new URLSearchParams(location.hash.slice(1)).get('piece')===id,p.id);fs.writeFileSync(path.join(out,'library-walkthrough.json'),JSON.stringify({source:'real-media-state-fixture',video_decoded_and_played:true,source_link_piece:p.id,source_link_pass:true},null,2));}
  await context.close();
 }
}finally{await Promise.race([browser.close(),new Promise(r=>setTimeout(()=>{console.log('QA browser shutdown deadline reached');r();},3000))]);fs.writeFileSync(path.join(out,'screenshot-manifest.json'),JSON.stringify(manifest,null,2));fs.writeFileSync(path.join(out,'design-inventory.json'),JSON.stringify(inventory,null,2));fs.writeFileSync(path.join(out,'number-formulas.json'),JSON.stringify({numbers,errors},null,2));}
if(errors.length)console.log(JSON.stringify(errors,null,2));

process.exit(0);
