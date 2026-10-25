#!/usr/bin/env node
// R277 gate: actual Studio shell, endpoint-shaped fixtures, strict approved-copy comparison.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync,mkdirSync,mkdtempSync,rmSync,existsSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {tmpdir,homedir} from 'node:os';
import {spawn,spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {createServer} from 'node:net';
import {testFixtures,testRevisionDetail,testRevisionLog,testPollingOwnership,testB2Layout,testLookRunningState,testMarkerGeometry,testMarkerPlacementEdges,measureFixtureBoxes,testMarkerAvoidance} from '../../tests/test_r277_frontend.mjs';
import {testDetail} from '../../tests/test_r276_direct_frontend.mjs';

const ROOT=resolve(import.meta.dirname,'../..'),CORE=process.env.HARNESS_CORE;
assert(CORE,'Set HARNESS_CORE to the Harness Engineering Core directory');
const DESIGN=join(ROOT,'docs/tasks/R277-shot-visual-revision/design'),OUT=process.env.R277_FRONTEND_EVIDENCE||join(homedir(),'.photo-content-os/evidence/R277-shot-visual-revision/frontend');
const BASE='http://127.0.0.1:8768',SOURCE=join(homedir(),'.photo-content-os/studio-r276');
const TEMP=mkdtempSync(join(tmpdir(),'r277-frontend-')),STATE=join(TEMP,'state');
const load=name=>JSON.parse(readFileSync(join(ROOT,'tests/fixtures/r277-revise',name+'.json'),'utf8'));
const screenshots=[],contracts=[],errors=[],checks=[],layoutChecks=[],markerChecks=[];let markerEdgeCases=[];let server,browser;
const sha=buffer=>createHash('sha256').update(buffer).digest('hex');
mkdirSync(OUT,{recursive:true});
const project={id:'fixture-piece',title:'断更一年，我拆了四句话',revision:1,documents:{},workspace_key:'fixture-piece'},piece={...project,group_id:'fixture-group',videos:0,photos:0,versions:0,outputs:[]},group={id:'fixture-group',title:'其他作品',pieces:[piece],count:1,pending:0,produced:0};
const collector=readFileSync(join(CORE,'skills/ui-copy-quality/assets/collect_design_inventory.js'),'utf8');
const clockTime=new Date('2026-10-26T01:10:00Z');
function sourceHashes(){const code='from pathlib import Path; import hashlib,json,sys; r=Path(sys.argv[1]); print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(r.rglob("*")) if p.is_file()},sort_keys=True))';const r=spawnSync(join(ROOT,'.venv/bin/python'),['-c',code,SOURCE],{encoding:'utf8',maxBuffer:30*1024*1024});assert.equal(r.status,0,r.stderr);return JSON.parse(r.stdout);}
const before=sourceHashes();writeFileSync(join(OUT,'source-hashes-before.json'),JSON.stringify(before,null,2));
async function newPage(width){const page=await browser.newPage({viewport:{width,height:900},reducedMotion:'reduce'});page.setDefaultTimeout(15000);page.on('pageerror',e=>errors.push(e.message));await page.route('https://fonts.googleapis.com/**',r=>r.abort());await page.route('https://fonts.gstatic.com/**',r=>r.abort());return page;}
async function capture(page,name,width,{viewportOnly=false}={}){
  if(['look-running','no-boxes-look-running'].includes(name))await testLookRunningState(page);
  markerChecks.push({name,width,markers:await testMarkerGeometry(page,{required:['review','picked','compare','kept-prev'].includes(name)||name.startsWith('real-boxes')})});
  layoutChecks.push(await testB2Layout(page,{name,width}));
  await page.evaluate(()=>document.fonts.ready);
  if(!viewportOnly)await page.evaluate(async()=>{for(let y=0;y<document.documentElement.scrollHeight;y+=600){scrollTo(0,y);await new Promise(r=>requestAnimationFrame(r));}scrollTo(0,0);});
  await page.locator('img').evaluateAll(async images=>{await Promise.all(images.map(img=>img.complete?null:new Promise(r=>{img.onload=img.onerror=r;})));});
  const metrics=await page.evaluate(()=>({width:innerWidth,height:innerHeight,scrollHeight:document.documentElement.scrollHeight,scrollWidth:document.documentElement.scrollWidth,scrollY}));
  assert.equal(metrics.width,width);if(metrics.scrollWidth>width){await page.screenshot({path:join(OUT,`${name}-${width}-overflow.png`),fullPage:true});writeFileSync(join(OUT,`${name}-${width}-overflow.json`),JSON.stringify(await page.locator('#app *').evaluateAll(es=>es.map(e=>({tag:e.tagName,cls:e.className,rect:e.getBoundingClientRect().toJSON()})).filter(e=>e.rect.right>innerWidth+1)),null,2));}assert(metrics.scrollWidth<=width,`${name}/${width} overflow ${metrics.scrollWidth}`);
  const file=join(OUT,`${name}-${width}.png`);await page.screenshot({path:file,fullPage:!viewportOnly});const buffer=readFileSync(file);const dims={width:buffer.readUInt32BE(16),height:buffer.readUInt32BE(20)};assert.equal(dims.width,width);if(!viewportOnly)assert(dims.height>=metrics.scrollHeight);
  screenshots.push({state:name,route:page.url(),viewport:{width,height:900},capture_time:new Date().toISOString(),scroll_coverage:viewportOnly?[metrics.scrollY,metrics.scrollY+900]:[0,metrics.scrollHeight],capture_kind:viewportOnly?'first-screen':'complete-page',output_dimensions:dims,path:file,sha256:sha(buffer),browser:browser.version(),font_mode:'fallback-local',review_result:'PENDING',review_note:'Awaiting personal inspection of this image.'});
}
async function contract(page,state,name,width){const inventory=await page.evaluate(`(()=>{${collector};return collectDesignInventory({states:{${JSON.stringify(state)}:'#app'}});})()`),path=join(OUT,`${name}-${width}.inventory.json`);writeFileSync(path,JSON.stringify(inventory,null,2));const r=spawnSync(join(ROOT,'.venv/bin/python'),[join(CORE,'skills/ui-copy-quality/scripts/check_design_contract.py'),'check','--contract',join(DESIGN,'contract.json'),'--approved-extras',join(DESIGN,'approved-extras.json'),'--inventory',path,'--json'],{encoding:'utf8'});assert(r.stdout,r.stderr);writeFileSync(join(OUT,`${name}-${width}.contract.json`),r.stdout);contracts.push({state,name,width,exit_code:r.status,result:JSON.parse(r.stdout)});}
async function mocks(page,name){let payload=load(name);const requests=[];let codeCalls=0;
  const anchor=Date.parse(payload.job.updatedAt),shift=clockTime.getTime()-anchor;
  for(const entry of [payload.job,...payload.job.shots])for(const key of ['createdAt','updatedAt','writingStartedAt','writtenAt','renderedAt'])if(entry[key])entry[key]=new Date(Date.parse(entry[key])+shift).toISOString();
  await page.route('**/api/**',async route=>{try{
    const request=route.request(),url=new URL(request.url()),path=url.pathname,method=request.method(),json=(body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
    if(path.endsWith('/poster.jpg')||path==='/api/direct/samples'&&url.searchParams.has('poster')){const id=path.endsWith('/poster.jpg')?path.split('/').at(-2):url.searchParams.get('poster').slice(-2);const version=url.searchParams.get('version')||url.searchParams.get('v');const file=id==='02'&&version==='2'?'poster-02-after.jpg':`poster-${id}.jpg`;return route.fulfill({contentType:'image/jpeg',body:readFileSync(join(OUT,file))});}
    if(path.endsWith('/code')){codeCalls++;return route.fulfill({contentType:'text/plain',body:'<!doctype html><html><body>代码</body></html>'});}
    if(method!=='GET'){
      assert.equal(request.headers()['x-content-os-csrf'],'fixture-csrf');const body=request.postData()?request.postDataJSON():null;requests.push({path,method,body});
      if(path.includes('/rules/proposals/')){const p=payload.revisionLog.categories[0].proposals[0];p.status=path.endsWith('/adopt')?'adopted':'rejected';if(p.status==='adopted')payload.revisionLog.rulesRevision++;return json({ok:true,proposal:p});}
      const shot=payload.job.shots.find(s=>s.shotId===path.split('/').at(-2));assert(shot,path);
      if(path.endsWith('/revise')){assert.equal(body.lines.length,4);shot.status='writing';shot.writingStartedAt=new Date(clockTime.getTime()-42000).toISOString();shot.lastInstruction=body.lines.map(l=>l.text).join('');payload.job.status='writing';}
      else if(path.endsWith('/current')){shot.currentVersion=body.version;shot.posterRevision=shot.versions.find(v=>v.version===body.version).posterRevision;payload.job.output.status='none';}
      else if(path.endsWith('/sample'))shot.sample=method==='PUT';
      else if(path.endsWith('/look'))shot.look={status:'running',failureCode:null,findings:[]};
      else throw new Error(`Unmocked mutation ${method} ${path}`);
      return json({ok:true,job:payload.job});
    }
    if(path==='/api/direct/revision-log')return json(payload.revisionLog);
    if(path==='/api/direct/samples')return json(payload.samples);
    if(path.includes('/direct/jobs'))return json({ok:true,job:payload.job});
    if(path==='/api/bootstrap')return json({ok:true,csrfToken:'fixture-csrf',projects:[project]});
    if(path==='/api/review/catalog')return json({ok:true,groups:[group],pieces:[piece]});
    if(path===`/api/projects/${project.id}`)return json({ok:true,project,videoHandoff:null});
    if(path==='/api/diagnostics')return json({ok:true,diagnostics:{checks:[],checking:false}});
    if(path==='/api/settings')return json({ok:true,settings:{upstream:{upstream_features_available:false}}});
    if(path==='/api/settings/analysis-budget')return json({ok:true,analysisBudget:{budget:{},revision:1}});
    if(path==='/api/setup/state')return json({ok:true,setup:{current_step:'done'}});
    if(path==='/api/review/music-settings')return json({ok:true,egress:{state:'absent'},account:{state:'absent'}});
    if(path==='/api/upstream/tasks')return json({ok:true,tasks:[]});
    if(path==='/api/assets')return json({ok:true,assets:[]});
    if(path==='/api/assets/statistics')return json({ok:true,statistics:{categories:[],asset_count:0}});
    if(path==='/api/review/music')return json({ok:true,tracks:[]});
    throw new Error(`Unmocked API ${method} ${path}`);
  }catch(e){errors.push(e.stack||e.message);await route.fulfill({status:500,contentType:'application/json',body:JSON.stringify({ok:false,error:{code:'fixture_failure'}})});}});
  return {requests,get payload(){return payload;},get codeCalls(){return codeCalls;}};
}
async function pick(page){await page.locator('[data-box="b1"]').click();await page.locator('[data-act="main"]').click();await page.locator('[data-box="b2"]').click();await page.locator('[data-act="dim"]').click();await page.locator('[data-box="2"]').click();await page.locator('[data-act="del"]').click();await page.locator('[data-box="b2"]').click();await page.locator('[data-extra]').fill('底色不动');assert.equal(await page.locator('.rv-count').textContent(),'93 / 200 字');}
async function open(name,width){const page=await newPage(width);await page.clock.install({time:clockTime});await page.clock.setFixedTime(clockTime);const mock=await mocks(page,name);await page.goto(BASE+'/#view=piece&piece=fixture-piece&ptab=direct');await page.locator('[data-design-id="DV-DETAIL"]').waitFor();await page.locator(`[data-shot="${name==='saved'?'01':'02'}"]`).click();
  if(name==='select')await page.locator('[data-box="b2"]').click();
  if(['picked','rewriting2'].includes(name))await pick(page);
  if(name==='rewriting2'){await page.locator('[data-revise]').click();await page.locator('[data-design-id="RV-BUSY"]').waitFor();assert.equal(mock.requests.length,1);assert.equal(await page.locator('[data-busy-clock]').textContent(),'正在按 4 处改法重写 · 0:42');}
  if(['log','log-empty','proposal-running'].includes(name)){await page.locator('[data-revision-log]').click();await page.locator('[data-design-id="RV-LOG"]').waitFor();}
  return {page,mock};
}
async function replayRealMarkers(){
  // Replay hash-bound real model evidence; no model calls or business mutations.
  const evidence=process.env.R277_REPLAY_EVIDENCE||join(homedir(),'.photo-content-os/evidence/R277-shot-visual-revision');
  const sourceFiles=new Map(),inputs=[],mutations=[];
  const source=relative=>{const path=join(evidence,relative);if(!sourceFiles.has(path)){const bytes=readFileSync(path);sourceFiles.set(path,sha(bytes));inputs.push({path,sha256:sha(bytes)});}return path;};
  const cases=[
    {name:'real-boxes-review-02',projection:'real-c/c02-look-02-finished.job.json',shot:'02',artifacts:'real-c/artifacts/versions/02'},
    {name:'real-boxes-review-05',projection:'real-c2/real/r02-look-05-done.job.json',shot:'05',artifacts:'real-c2/real/artifacts/versions/05'},
    {name:'real-boxes-picked-05',projection:'real-c2/real/r02-look-05-done.job.json',shot:'05',artifacts:'real-c2/real/artifacts/versions/05',pick:true},
    {name:'real-boxes-compare-05',projection:'real-c2/real/r05-compare-05.job.json',shot:'05',artifacts:'real-c2/real/artifacts/versions/05'}
  ];
  for(const spec of cases)for(const width of [1440,960,390]){
    const payload=JSON.parse(readFileSync(source(spec.projection),'utf8')),job=payload.job,page=await newPage(width);
    page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/')&&r.method()!=='GET')mutations.push({method:r.method(),url:r.url()});});
    await page.route('**/api/projects/project-fc6baa3294/direct/jobs/**',async route=>{
      const request=route.request(),url=new URL(request.url()),path=url.pathname;
      if(request.method()!=='GET'){await route.abort();return;}
      if(path.endsWith('/latest')||path.endsWith('/'+job.jobId))return route.fulfill({contentType:'application/json',body:JSON.stringify(payload)});
      if(path.endsWith('/shots/'+spec.shot+'/poster.jpg')){const version=url.searchParams.get('version')||job.shots.find(s=>s.shotId===spec.shot).currentVersion;return route.fulfill({contentType:'image/jpeg',body:readFileSync(source(spec.artifacts+'/'+version+'/poster.jpg'))});}
      return route.continue();
    });
    await page.goto(BASE+'/#view=piece&piece=project-fc6baa3294&ptab=direct');await page.locator('[data-shot="'+spec.shot+'"]').click();await page.locator('.rv-head h3').filter({hasText:'第 '+spec.shot+' 镜'}).waitFor();
    if(spec.pick)for(const id of ['num','nl2','c2']){await page.locator('[data-box="'+id+'"]').click();await page.locator('[data-act="dim"]').click();}
    writeFileSync(join(OUT,spec.name+'-'+width+'.projection.json'),JSON.stringify(payload,null,2));
    await capture(page,spec.name,width);await page.locator('.rv-detail').evaluate(e=>e.scrollIntoView({block:'start'}));await capture(page,spec.name+'-detail',width,{viewportOnly:true});await page.close();
  }
  assert.deepEqual(mutations,[]);for(const [path,hash] of sourceFiles)assert.equal(sha(readFileSync(path)),hash);
  writeFileSync(join(OUT,'real-marker-replay.json'),JSON.stringify({scope:'Retained real projections/posters rendered in current Studio; no fresh model call',inputs,source_unchanged:true,business_mutations:mutations},null,2));
}
try{
  testFixtures();await new Promise((resolve,reject)=>{const probe=createServer();probe.once('error',reject);probe.listen(8768,'127.0.0.1',()=>probe.close(resolve));});
  const copied=spawnSync('/bin/cp',['-cR',SOURCE,STATE],{encoding:'utf8'});assert.equal(copied.status,0,copied.stderr);
  server=spawn(join(ROOT,'.venv/bin/python'),['-u','-c','from pathlib import Path; import sys; from studio.server import serve; serve(state_dir=Path(sys.argv[1]),port=8768).serve_forever()',STATE],{cwd:ROOT,env:process.env,stdio:['ignore','pipe','pipe']});server.stdout.on('data',d=>writeFileSync(join(OUT,'server.stdout.log'),d,{flag:'a'}));server.stderr.on('data',d=>writeFileSync(join(OUT,'server.stderr.log'),d,{flag:'a'}));
  let ready=false;for(let i=0;i<100;i++){if(server.exitCode!==null)throw new Error('Temporary Studio exited during startup');if(await fetch(BASE).then(r=>r.ok).catch(()=>false)){ready=true;break;}await new Promise(r=>setTimeout(r,100));}assert(ready,'Studio 8768 startup failed');
  const pw=process.env.PLAYWRIGHT_MODULE||join(homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs');const {chromium}=await import(pathToFileURL(pw));browser=await chromium.launch({channel:'chrome',headless:true});
  // Real first screen: copied state, no synthetic projection or generated media.
  for(const width of [1440,960,390]){
    const page=await newPage(width);await page.goto(BASE+'/#view=piece&piece=project-fc6baa3294&ptab=direct');await page.locator('[data-shot="02"]').waitFor();await page.locator('[data-shot="02"]').click();await page.getByRole('button',{name:'让 Opus 看一遍',exact:true}).waitFor();assert.equal(await page.locator('.rv-hs').count(),0);
    const actual=await page.request.get(BASE+'/api/projects/project-fc6baa3294/direct/jobs/latest').then(r=>r.json());assert.equal(actual.job.jobId,'dv_0e184e961bd14ac084c67411');writeFileSync(join(OUT,'real-worst.projection.json'),JSON.stringify(actual,null,2));
    await capture(page,'real-worst-complete',width);await page.locator('[data-design-id="DV-DETAIL"]').evaluate(e=>e.scrollIntoView({block:'start'}));await capture(page,'real-worst-first-screen',width,{viewportOnly:true});await page.close();
  }
  await replayRealMarkers();
  // Rasterize the approved shot code only inside the design page, never inside Studio.
  const reference=await browser.newPage({viewport:{width:1440,height:900}});await reference.goto(pathToFileURL(join(DESIGN,'revise.html')).href+'#s=review&chrome=0');await reference.locator('.dv-card').first().waitFor();await reference.waitForTimeout(500);
  const raster=async(html,duration,file)=>{const page=await browser.newPage({viewport:{width:1080,height:1920},reducedMotion:'reduce'});await page.route('https://fonts.googleapis.com/**',r=>r.abort());await page.route('https://fonts.gstatic.com/**',r=>r.abort());await page.setContent(html);await page.evaluate(({duration})=>{window.seekFrame(Math.floor(duration*30*.8),30);}, {duration});await page.evaluate(()=>document.fonts.ready);const boxes=await measureFixtureBoxes(page);await page.screenshot({path:join(OUT,file),type:'jpeg',quality:90});await page.close();return boxes;};
  const shotCode=await reference.evaluate(()=>SHOTS.map(s=>({html:s.html,D:s.D}))),measured=[];for(let i=0;i<7;i++)measured.push(await raster(shotCode[i].html,shotCode[i].D,`poster-${String(i+1).padStart(2,'0')}.jpg`));
  await reference.goto(pathToFileURL(join(DESIGN,'revise.html')).href+'#s=compare&chrome=0');await reference.locator('.rv-pair .new .rv-stage').waitFor();const afterCode=await reference.evaluate(()=>({html:SHOTS[1].html,D:SHOTS[1].D}));const afterBoxes=await raster(afterCode.html,afterCode.D,'poster-02-after.jpg');
  const fixtureGeometry=[];for(const name of ['review','select','picked','rewriting2','compare','kept-prev','saved','review-failed','log','look-running','no-boxes','no-boxes-look-running','verify-running','verify-missed','verify-failed','log-empty','proposal-running'])for(const shot of load(name).job.shots){if(!shot.boxes.length)continue;const expected=shot.shotId==='02'&&shot.currentVersion===2?afterBoxes:measured[Number(shot.shotId)-1];assert.deepEqual(shot.boxes,expected,`${name}/${shot.shotId}: fixture boxes drifted from renderer measurement; regenerate at 0.8*D`);fixtureGeometry.push({name,shotId:shot.shotId,boxes:expected});}
  writeFileSync(join(OUT,'fixture-geometry.json'),JSON.stringify({collector:'scripts/video_render/render-frames.mjs',frame:'floor(0.8 * D * 30)',source_sha256:sha(readFileSync(join(ROOT,'scripts/video_render/render-frames.mjs'))),fixtures:fixtureGeometry},null,2));
  for(const state of ['review','select','picked','compare','log']){await reference.goto(pathToFileURL(join(DESIGN,'revise.html')).href+`#s=${state}&chrome=0`);await reference.waitForTimeout(100);await reference.screenshot({path:join(OUT,`reference-${state}.png`),fullPage:true});}await reference.close();
  const matrix={review:'review',select:'select',picked:'picked',rewriting2:'rewriting2',compare:'compare','kept-prev':'kept-prev',saved:'saved','review-failed':'review-failed',log:'log','look-running':'review','no-boxes':'review-failed','no-boxes-look-running':'review','verify-running':'compare','verify-missed':'compare','verify-failed':'compare','log-empty':'log','proposal-running':'log'};
  for(const [name,state] of Object.entries(matrix))for(const width of [1440,960]){const {page,mock}=await open(name,width);await capture(page,name,width);await contract(page,state,name,width);
    if(name==='review'){assert.equal(mock.codeCalls,0);await page.locator('[data-design-id="DV-CODE"] summary').click();await page.waitForFunction(()=>document.querySelector('[data-design-id="DV-CODE"] pre')?.textContent.startsWith('<!doctype'));assert.equal(mock.codeCalls,1);await page.locator('.rv-more details').evaluateAll(es=>es.forEach(e=>e.open=true));await capture(page,'review-expanded',width);await contract(page,'review','review-expanded',width);}
    if(name==='no-boxes'){assert.equal(await page.locator('.rv-chip:enabled').count(),3);await page.locator('[data-extra]').fill('底色不动');assert(await page.locator('[data-revise]').isEnabled());}
    if(name==='verify-missed')assert(await page.getByText('柱子仍然和主角一样醒目。',{exact:true}).isVisible());
    if(name==='log'){await page.getByRole('button',{name:'采用',exact:true}).click();await page.getByText('已写进规则',{exact:true}).waitFor();assert.equal(mock.payload.revisionLog.rulesRevision,4);await page.getByRole('button',{name:'回到作品',exact:true}).click();await page.locator('[data-box="b2"]').waitFor();}
    await page.close();console.log(`captured ${name}/${width}`);
  }
  for(const name of ['review','picked','compare','kept-prev','no-boxes','log']){const {page}=await open(name,390);await capture(page,name,390);await contract(page,matrix[name],name,390);await page.close();}
  const detail=await open('review',1440);await testDetail(detail.page,detail.mock.payload.job);await testRevisionDetail(detail.page,detail.mock.payload.job);await testRevisionLog(detail.page);await testPollingOwnership(detail.page,detail.mock.payload.job);markerEdgeCases=await testMarkerPlacementEdges(detail.page,detail.mock.payload.job);markerEdgeCases.push(...await testMarkerAvoidance(detail.page,detail.mock.payload.job));await detail.page.close();checks.push('R276 detail intent + R277 detail/log behavior');
  // Real clicks prove that revert and sample actions send the scoped request.
  const compare=await open('compare',1440);await compare.page.locator('[data-previous]').click();await compare.page.getByText('已退回第 1 版。第 2 版留着，你点的问题已经记下。',{exact:true}).waitFor();assert.deepEqual(compare.mock.requests[0].body,{version:1});assert.equal(compare.mock.payload.job.shots[1].versions.length,2);await compare.page.locator('[data-sample]').click();await compare.page.getByRole('button',{name:'♥ 已存为样例',exact:true}).waitFor();await compare.page.locator('[data-sample]').click();await compare.page.getByRole('button',{name:'♡ 这镜好',exact:true}).waitFor();assert.deepEqual(compare.mock.requests.slice(1).map(r=>r.method),['PUT','DELETE']);await compare.page.close();checks.push('revert retains both versions; sample PUT/DELETE; proposal adopt and back navigation');
  assert.deepEqual(errors,[]);writeFileSync(join(OUT,'contracts.json'),JSON.stringify(contracts,null,2));writeFileSync(join(OUT,'marker-overlap-exceptions.json'),JSON.stringify(markerChecks.flatMap(c=>c.markers.filter(m=>m.otherOverlaps.length).map(m=>({name:c.name,width:c.width,boxId:m.boxId,kind:m.kind,placement:m.placement,area:m.overlapArea,otherBlocks:m.otherOverlaps}))),null,2));
  console.log(`Functional PASS; ${screenshots.length} captures; contracts ${contracts.filter(c=>c.exit_code===0).length}/${contracts.length} passed`);
  if(contracts.some(c=>c.exit_code!==0))process.exitCode=1;
}finally{
  await browser?.close();if(server){const child=server;server=null;if(child.exitCode===null&&child.signalCode===null){const exited=new Promise(r=>child.once('exit',r));child.kill('SIGTERM');await exited;}}
  const after=sourceHashes();writeFileSync(join(OUT,'source-hashes-after.json'),JSON.stringify(after,null,2));const identical=JSON.stringify(before)===JSON.stringify(after);writeFileSync(join(OUT,'source-preservation.json'),JSON.stringify({identical,files:Object.keys(before).length},null,2));
  writeFileSync(join(OUT,'screenshot-manifest.json'),JSON.stringify({scope:'R277 local Studio 8768; real copied seven-shot legacy job + intercepted synthetic endpoints',source_preserved:identical,checks,errors,screenshots,contracts,layout_checks:layoutChecks,marker_checks:markerChecks,marker_edge_cases:markerEdgeCases},null,2));rmSync(TEMP,{recursive:true,force:true});assert(identical,'Source state changed during gate; inspect preservation evidence');
}
