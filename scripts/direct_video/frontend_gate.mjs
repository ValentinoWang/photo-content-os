#!/usr/bin/env node
// Task-scoped gate: rendered contract drift, formulas and interactions. Repairs
// belong in the approved frontend files; never edit the design contract to pass.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {existsSync,readFileSync,writeFileSync,mkdirSync,mkdtempSync,rmSync} from 'node:fs';
import {homedir,tmpdir} from 'node:os';
import {resolve,join} from 'node:path';
import {spawn,spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {runInNewContext} from 'node:vm';
import {composeLegacyContract} from './rescript_frontend_gate.mjs';
import {fixture,testDetail,testFormulas} from '../../tests/test_r276_direct_frontend.mjs';

const ROOT=resolve(import.meta.dirname,'../..');
const detailIds=new Set(['DV-DETAIL','DV-FACTS','DV-CHECKS','DV-REWRITE','DV-CODE','DV-PVNOTE']);
function outerContract(path){const contract=composeLegacyContract(JSON.parse(readFileSync(path,'utf8')),JSON.parse(readFileSync(join(process.env.R278_DESIGN_ROOT||join(ROOT,'docs/tasks/R278-direct-rescript/design'),'contract.json'),'utf8')),state=>JSON.parse(readFileSync(join(ROOT,'tests/fixtures/r276-direct',state+'.json'),'utf8')));for(const spec of Object.values(contract.states))spec.ids=spec.ids.filter(id=>!detailIds.has(id));const file=join(temp,'r276-outer-contract.json');writeFileSync(file,JSON.stringify(contract));return file;}
function outerCollector(source){return source.replace('for (let n = el;', `if(el.closest('[data-design-id="DV-DETAIL"]'))return false; for (let n = el;`);}

const DESIGN=process.env.R276_DESIGN_ROOT||join(ROOT,'docs/tasks/R276-direct-video-opus/design');
const CORE=process.env.HARNESS_CORE;
if(!CORE) throw new Error('设置 HARNESS_CORE，指向 Harness Engineering 的 Core 目录（设计合同检查脚本在那里）');
const OUT=process.env.R276_FRONTEND_EVIDENCE||join(homedir(),'.photo-content-os/evidence/R276-direct-video-opus/frontend-f2');
const PORT=Number(process.env.DIRECT_GATE_PORT||8767);
const BASE=`http://127.0.0.1:${PORT}`;
const STATES=['empty','read-error','filled','unavailable','designing','writing','failed-shot','ready','rewriting','composing','composing-silent','done','done-silent'];
const pw=process.env.VIDEO_RENDER_PLAYWRIGHT_MODULE?.replace(/index\.js$/,'index.mjs')||process.env.PLAYWRIGHT_MODULE||join(homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs');
const {chromium}=await import(pathToFileURL(pw));
const sandbox={window:{}};runInNewContext(readFileSync(join(DESIGN,'shots-data.js'),'utf8'),sandbox);
const source=JSON.parse(JSON.stringify(sandbox.window.R131.shots));
const script=source.map(s=>s.dialogue).join('\n');
const project={id:'fixture-piece',title:sandbox.window.R131.title,revision:1,documents:{},workspace_key:'fixture-piece'};
const piece={...project,group_id:'fixture-group',videos:0,photos:0,versions:0,outputs:[]};
const group={id:'fixture-group',title:'其他作品',pieces:[piece],count:1,pending:0,produced:0};
mkdirSync(OUT,{recursive:true});mkdirSync(join(OUT,'fixtures'),{recursive:true});
const temp=mkdtempSync(join(tmpdir(),'r276-frontend-'));
const screenshots=[],contracts=[],browserErrors=[];
let server,browser;
async function mocks(page,state){
  let current=JSON.parse(readFileSync(join(ROOT,'tests/fixtures/r276-direct',state+'.json'),'utf8')),
      anchor=Date.parse(current.job?.updatedAt),polls=0,createCalls=0,codeCalls=0,narrationCalls=0,rewriteCalls=0,composeCalls=0;
  if(Number.isFinite(anchor)){const shift=Date.now()-anchor;for(const item of [current.job,...current.job.shots])for(const key of ['createdAt','updatedAt','writingStartedAt','writtenAt','renderedAt'])if(item[key])item[key]=new Date(Date.parse(item[key])+shift).toISOString();}
  if(['unavailable','read-error'].includes(state))current={ok:true,job:null};
  await page.route('https://fonts.googleapis.com/**',r=>r.abort());
  await page.route('https://fonts.gstatic.com/**',r=>r.abort());
  await page.route('**/api/**',async route=>{
    const req=route.request(),url=new URL(req.url()),path=url.pathname;
    const json=(body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
    if(path.startsWith('/api/direct/styles/library/')){const ident=path.split('/').at(-2),ext=path.endsWith('.mp4')?'mp4':'jpg';assert(JSON.parse(readFileSync(join(ROOT,'tests/fixtures/r278-direct/first.json'),'utf8')).styles.library.some(x=>x.id===ident));return route.fulfill({contentType:ext==='mp4'?'video/mp4':'image/jpeg',body:readFileSync(join(ROOT,'scripts/direct_video/style_library',`${ident}.${ext}`))});}
    if(path.endsWith('/poster.jpg'))return route.fulfill({contentType:'image/jpeg',body:readFileSync(join(OUT,`poster-${path.split('/').at(-2)}.jpg`))});
    if(path.endsWith('/output.mp4')){
      const body=readFileSync(join(OUT,'synthetic-output.mp4')),range=req.headers().range?.match(/^bytes=(\d+)-(\d*)$/);
      if(range){const start=Number(range[1]),end=range[2]?Math.min(Number(range[2]),body.length-1):body.length-1;return route.fulfill({status:206,contentType:'video/mp4',headers:{'Content-Range':`bytes ${start}-${end}/${body.length}`,'Accept-Ranges':'bytes'},body:body.subarray(start,end+1)});}
      return route.fulfill({contentType:'video/mp4',headers:{'Accept-Ranges':'bytes'},body});
    }
    if(path==='/api/direct/styles')return json(JSON.parse(readFileSync(join(ROOT,'tests/fixtures/r278-direct/first.json'),'utf8')).styles);
    if(path.endsWith('/code')){codeCalls++;return route.fulfill({contentType:'text/plain; charset=utf-8',body:source[0].html});}
    if(path.includes('/direct/jobs')){
      if(state==='read-error')return json({ok:false,error:{code:'fixture_read_failed',message:'read failed'}},500);
      if(req.method()==='POST'){
        assert.equal(req.headers()['x-content-os-csrf'],'fixture-csrf');
        if(path.endsWith('/narration')){narrationCalls++;assert.equal(req.headers()['content-type'],'audio/wav');assert(req.postDataBuffer().equals(Buffer.from('RIFFfixtureWAVE')));current.job.narration={status:'ready',durationSeconds:120};return json(current);}
        if(path.endsWith('/rewrite')||path.endsWith('/revise')){rewriteCalls++;if(path.endsWith('/revise')){const lines=req.postDataJSON().lines;assert.deepEqual(lines,[{text:'数字再大一点',own:true}]);req.postDataJSON=()=>({instruction:lines[0].text});}assert(['数字再大一点','',undefined].includes(req.postDataJSON().instruction));const id=path.split('/').at(-2);const before=current.job.shots.filter(s=>s.shotId!==id).map(s=>JSON.stringify(s));const shot=current.job.shots.find(s=>s.shotId===id);Object.assign(shot,{status:'writing',writingStartedAt:new Date().toISOString(),lastInstruction:req.postDataJSON().instruction||shot.lastInstruction});current.job.status='writing';assert.deepEqual(current.job.shots.filter(s=>s.shotId!==id).map(s=>JSON.stringify(s)),before);return json(current);}
        if(path.endsWith('/compose')){composeCalls++;current.job.output.status='composing';current.job.status='composing';return json(current);}
        createCalls++;
        if(state==='unavailable')return json({ok:false,error:{code:'claude_cli_unavailable',message:'not available'}},400);
        assert.deepEqual(req.postDataJSON().storyboard.shots,source.map((s,i)=>({shotId:String(i+1).padStart(2,'0'),dialogue:s.dialogue})));assert.equal(req.postDataJSON().styleBase.kind,'job');assert.equal(req.postDataJSON().style,'浅米色底');current=fixture('designing',source);return json(current,201);
      }
      polls++;return json(current);
    }
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
    throw new Error(`Unmocked API: ${req.method()} ${path}`);
  });
  return {get current(){return current;},get polls(){return polls;},get createCalls(){return createCalls;},get codeCalls(){return codeCalls;},get narrationCalls(){return narrationCalls;},get rewriteCalls(){return rewriteCalls;},get composeCalls(){return composeCalls;},set(value){current=value;}};
}
async function open(state,width=1440){
  const page=await browser.newPage({viewport:{width,height:900},reducedMotion:'reduce'});
  page.on('pageerror',e=>browserErrors.push(e.message));
  await page.clock.install();
  const mock=await mocks(page,state);
  await page.goto(BASE+'/#view=piece&piece=fixture-piece&ptab=direct');
  await page.locator('[data-design-id="DV-MODEL"]').waitFor();
  if(state==='read-error')await page.getByText('读不到这件作品的直出任务',{exact:true}).waitFor();
  else if(['filled','unavailable'].includes(state)){
    await page.getByRole('textbox',{name:'台词',exact:true}).fill(script);
    await page.locator('[data-adjust]').fill('浅米色底');
    if(state==='unavailable'){await page.getByRole('button',{name:'生成',exact:true}).click();await page.locator('[data-design-id="DV-UNAVAILABLE"]').waitFor();}
  }else await page.locator(`[data-design-id="${state==='empty'?'DV-START':'DV-FILM'}"]`).waitFor();
  return {page,mock};
}
async function capture(page,state,width){
  await page.evaluate(()=>{document.activeElement?.blur();document.querySelectorAll('textarea').forEach(t=>t.scrollTop=0);return document.fonts.ready;});
  await page.evaluate(async()=>{for(let y=0;y<document.documentElement.scrollHeight;y+=600){scrollTo(0,y);await new Promise(r=>requestAnimationFrame(r));}scrollTo(0,0);});
  const metrics=await page.evaluate(()=>({width:innerWidth,height:innerHeight,scrollHeight:document.documentElement.scrollHeight,scrollWidth:document.documentElement.scrollWidth}));
  if(metrics.scrollWidth>width){const overflow=await page.evaluate(()=>[...document.querySelectorAll('#app *')].map(e=>({tag:e.tagName,cls:e.className,rect:e.getBoundingClientRect().toJSON()})).filter(e=>e.rect.right>innerWidth+1));writeFileSync(join(OUT,`${state}-${width}.overflow.json`),JSON.stringify(overflow,null,2));await page.screenshot({path:join(OUT,`${state}-${width}.overflow.png`),fullPage:true});}
  if(state==='read-error')assert.equal(await page.locator('.dv-start:visible').count(),0);
  const film=page.locator('.dv-film');if(await film.count()){const columns=await film.evaluate(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length);assert.equal(columns,width<=620?3:width<=1180?4:7);}
  assert.equal(metrics.width,width);assert(metrics.scrollWidth<=width,`${state}/${width} overflows: ${metrics.scrollWidth}`);
  if(process.argv.includes('--checks-only'))return;
  const filename=`${state}-${width}.png`,path=join(OUT,filename);
  await page.screenshot({path,fullPage:true});
  const buffer=readFileSync(path);const imageWidth=buffer.readUInt32BE(16),imageHeight=buffer.readUInt32BE(20);
  assert.equal(imageWidth,width);assert(imageHeight>=metrics.scrollHeight);
  screenshots.push({state,route:page.url(),viewport:{width,height:metrics.height},capture_time:new Date().toISOString(),scroll_coverage:[0,metrics.scrollHeight],output_dimensions:{width:imageWidth,height:imageHeight},path:filename,sha256:createHash('sha256').update(buffer).digest('hex'),browser:page.context().browser().version(),font_mode:'fallback-local',review_result:'PENDING',review_note:'Captured; awaiting personal image inspection.'});
}
async function runReal() {
  const sourceState=join(homedir(),'.photo-content-os/studio-r276');
  const realOut=join(OUT,'real');mkdirSync(realOut,{recursive:true});
  const checkScript=join(CORE,'skills/ui-copy-quality/scripts/check_design_contract.py');
  const collect=readFileSync(join(CORE,'skills/ui-copy-quality/assets/collect_design_inventory.js'),'utf8');
  const realTemp=mkdtempSync(join(tmpdir(),'r276-f2-real-'));
  const first=join(realTemp,'silent'),second=join(realTemp,'narrated');
  let processServer=null,realBrowser=null;
  const jsonFetch=async(path,options={})=>{const r=await fetch(BASE+path,options),v=await r.json();assert(r.ok&&v.ok,JSON.stringify(v));return v;};
  const sourceHashes=()=>{
    const code='from pathlib import Path; import hashlib,json,sys; r=Path(sys.argv[1]); print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob("*") if p.is_file()}))';
    const r=spawnSync(join(ROOT,'.venv/bin/python'),['-c',code,sourceState],{encoding:'utf8',maxBuffer:20*1024*1024});assert.equal(r.status,0,r.stderr);return JSON.parse(r.stdout);
  };
  const before=sourceHashes();writeFileSync(join(realOut,'source-state-hashes-before.json'),JSON.stringify(before,null,2));
  const copy=target=>{const r=spawnSync('/bin/cp',['-cR',sourceState,target],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);};
  async function start(state){
    assert(!await fetch(BASE).catch(()=>null),'Gate port already in use');
    processServer=spawn(join(ROOT,'.venv/bin/python'),['-u','-c','from pathlib import Path; import sys; from studio.server import serve; serve(state_dir=Path(sys.argv[1]),port=int(sys.argv[2])).serve_forever()',state,String(PORT)],{cwd:ROOT,env:process.env,stdio:['ignore','pipe','pipe']});
    processServer.stdout.on('data',d=>writeFileSync(join(realOut,'server.stdout.log'),d,{flag:'a'}));processServer.stderr.on('data',d=>writeFileSync(join(realOut,'server.stderr.log'),d,{flag:'a'}));
    for(let i=0;i<200;i++){if(await fetch(BASE).then(r=>r.ok).catch(()=>false))return;await new Promise(r=>setTimeout(r,100));}throw new Error('real Studio failed to start');
  }
  async function stopServer(){if(processServer){const child=processServer;processServer=null;child.kill('SIGTERM');await new Promise(r=>child.once('exit',r));}}
  async function pageFor(width){const page=await realBrowser.newPage({viewport:{width,height:900},reducedMotion:'reduce'});await page.route('https://fonts.googleapis.com/**',r=>r.abort());await page.route('https://fonts.gstatic.com/**',r=>r.abort());page.on('pageerror',e=>browserErrors.push(e.message));return page;}
  async function inspect(page,state,name,width){
    await capture(page,name,width);
    const inventory=await page.evaluate(`(()=>{${outerCollector(collect)};return collectDesignInventory({states:{${JSON.stringify(state)}:'#app'}});})()`);
    const file=join(realOut,`${name}-${width}.inventory.json`);writeFileSync(file,JSON.stringify(inventory,null,2));
    const result=spawnSync(join(ROOT,'.venv/bin/python'),[checkScript,'check','--contract',outerContract(join(DESIGN,'contract.json')),'--inventory',file,'--approved-extras',join(ROOT,'tests/fixtures/r276-direct/approved-extras.json'),'--json'],{encoding:'utf8'});
    const value=JSON.parse(result.stdout);contracts.push({state,name,width,exit_code:result.status,result:value});writeFileSync(join(realOut,`${name}-${width}.contract.json`),result.stdout);
    return result.status;
  }
  const projectId='project-fc6baa3294',url=BASE+`/#view=piece&piece=${projectId}&ptab=direct`,baseJob=`/api/projects/${projectId}/direct/jobs`;
  async function outputScreens(state,name){
    const projection=await jsonFetch(baseJob+'/latest');writeFileSync(join(realOut,name+'.projection.json'),JSON.stringify(projection,null,2));
    for(const width of [1440,960]){
      const page=await pageFor(width);await page.goto(url);await page.locator('[data-design-id="DV-OUTPUT"]').waitFor({timeout:60000});
      assert.equal(await page.locator('.main').getAttribute('data-design-state'),state);
      await inspect(page,state,name,width);
      await page.locator('[data-play]').click();await page.waitForFunction(()=>{const v=document.querySelector('video');return v&&!v.paused&&v.currentTime>=2;},null,{timeout:30000});
      const playing=await page.locator('video').evaluate(v=>({currentTime:v.currentTime,duration:v.duration,paused:v.paused,readyState:v.readyState,videoWidth:v.videoWidth,videoHeight:v.videoHeight,src:v.getAttribute('src')}));assert(playing.videoWidth===1080&&playing.videoHeight===1920);writeFileSync(join(realOut,`${name}-playing-${width}.json`),JSON.stringify(playing,null,2));
      await inspect(page,state,name+'-playing',width);await page.locator('video').evaluate(v=>v.pause());await page.close();
    }
  }
  try {
    assert(process.env.VIDEO_RENDER_PLAYWRIGHT_MODULE&&existsSync(process.env.VIDEO_RENDER_PLAYWRIGHT_MODULE));assert(process.env.VIDEO_RENDER_BROWSER&&existsSync(process.env.VIDEO_RENDER_BROWSER));
    copy(first);await start(first);realBrowser=await chromium.launch({headless:true,...(process.env.VIDEO_RENDER_BROWSER?{executablePath:process.env.VIDEO_RENDER_BROWSER}:{channel:'chrome'})});
    await outputScreens('done-silent','real-done-silent');console.log('REAL silent output captured and played at both widths');await stopServer();
    copy(second);rmSync(join(second,'direct-jobs',projectId,'dv_0e184e961bd14ac084c67411'),{recursive:true});
    await start(second);await outputScreens('done','real-done');console.log('REAL narrated output captured and played at both widths');
    if(process.env.R276_REAL_OUTPUTS_ONLY){assert(contracts.length===8&&contracts.every(c=>c.exit_code===0));console.log('PASS REAL refreshed output and playback inventories');return;}
    const token=(await jsonFetch('/api/bootstrap')).csrfToken;
    const created=await jsonFetch(baseJob,{method:'POST',headers:{'Content-Type':'application/json','X-Content-OS-CSRF':token,Origin:BASE},body:JSON.stringify({script,style:'浅米色底，一个深青主色，结论只用橙色'})});
    writeFileSync(join(realOut,'new-job-created.projection.json'),JSON.stringify(created,null,2));console.log('REAL new seven-shot job started',created.job.jobId);
    const live=new Map();for(const width of [1440,960]){const page=await pageFor(width);await page.goto(url);live.set(width,page);}
    let halfway=false,ready=false,attempts=0;const startTime=Date.now(),timeline=[];
    while(Date.now()-startTime<25*60*1000){
      const response=await jsonFetch(baseJob+'/'+created.job.jobId),job=response.job,count=job.shots.filter(s=>['written','rendering','rendered'].includes(s.status)).length;
      const point={at:new Date().toISOString(),status:job.status,shots:job.shots.map(s=>({shotId:s.shotId,status:s.status,attempts:s.attempts,writingStartedAt:s.writingStartedAt})),written:count};timeline.push(point);writeFileSync(join(realOut,'new-job-timeline.json'),JSON.stringify(timeline,null,2));
      console.log('REAL progress',job.status,count+'/7',job.shots.map(s=>s.status).join(','));
      if(!halfway&&job.shots[0]?.status==='rendered'&&count>0&&count<7&&job.shots.some(s=>['writing','rendering'].includes(s.status))){
        writeFileSync(join(realOut,'real-writing.projection.json'),JSON.stringify(response,null,2));
        for(const [width,page] of live){await page.reload();await page.locator('.dv-film').waitFor();await inspect(page,'writing','real-writing',width);}halfway=true;console.log('REAL halfway screenshots captured');
      }
      if(job.status==='ready'){
        writeFileSync(join(realOut,'real-ready.projection.json'),JSON.stringify(response,null,2));
        for(const [width,page] of live){await page.reload();await page.getByRole('button',{name:'先合成无声预览',exact:true}).waitFor();await inspect(page,'ready','real-ready',width);}ready=true;break;
      }
      if(job.status==='failed'){
        const failed=job.shots.filter(s=>['failed','interrupted'].includes(s.status));
        if(!failed.length||attempts>=3)throw new Error(`Real job failed ${job.failureCode}; explicit retries ${attempts}`);
        attempts++;
        for(const shot of failed){const r=await jsonFetch(baseJob+'/'+job.jobId+`/shots/${shot.shotId}/rewrite`,{method:'POST',headers:{'Content-Type':'application/json','X-Content-OS-CSRF':token,Origin:BASE},body:'{}'});writeFileSync(join(realOut,`retry-${attempts}-${shot.shotId}.projection.json`),JSON.stringify(r,null,2));break;}
      }
      await new Promise(r=>setTimeout(r,10000));
    }
    assert(halfway&&ready,'Real generation did not reach both requested states');for(const page of live.values())await page.close();
    assert.deepEqual(browserErrors,[]);assert(contracts.length===12&&contracts.every(c=>c.exit_code===0),JSON.stringify(contracts.filter(c=>c.exit_code!==0),null,2));
    console.log('PASS REAL 4 states at 1440/960 plus 4 playing captures; all 12 inventories checked');
  } finally {
    const after=sourceHashes();writeFileSync(join(realOut,'source-state-hashes-after.json'),JSON.stringify(after,null,2));writeFileSync(join(realOut,'source-state-preservation.json'),JSON.stringify({identical:JSON.stringify(before)===JSON.stringify(after),files:Object.keys(before).length},null,2));
    writeFileSync(join(realOut,'screenshot-manifest.json'),JSON.stringify({scope:'F2 real Studio, copied production jobs and a real new Claude job; no API mocks',screenshots:screenshots.map(s=>({...s,path:'../'+s.path})),contracts,browser_errors:browserErrors,renderer:{playwrightModule:process.env.VIDEO_RENDER_PLAYWRIGHT_MODULE,browser:process.env.VIDEO_RENDER_BROWSER},temporaryStateRoot:realTemp},null,2));
    await realBrowser?.close();await stopServer();rmSync(realTemp,{recursive:true,force:true});rmSync(temp,{recursive:true,force:true});
  }
}

async function captureLive() {
  browser=await chromium.launch({headless:true,...(process.env.VIDEO_RENDER_BROWSER?{executablePath:process.env.VIDEO_RENDER_BROWSER}:{channel:'chrome'})});
  try {
    const projection=await fetch(BASE+'/api/projects/project-fc6baa3294/direct/jobs/latest').then(r=>r.json());
    assert(projection.job.jobId===process.env.R276_REAL_JOB_ID);assert(projection.job.shots.some(s=>s.status==='rendered'));assert(projection.job.shots.some(s=>s.status==='writing'));
    writeFileSync(join(OUT,'real-writing-final.projection.json'),JSON.stringify(projection,null,2));
    const collect=readFileSync(join(CORE,'skills/ui-copy-quality/assets/collect_design_inventory.js'),'utf8');
    for(const width of [1440,960]){
      const page=await browser.newPage({viewport:{width,height:900},reducedMotion:'reduce'});await page.route('https://fonts.googleapis.com/**',r=>r.abort());await page.route('https://fonts.gstatic.com/**',r=>r.abort());
      await page.goto(BASE+'/#view=piece&piece=project-fc6baa3294&ptab=direct');await page.locator('[data-design-id="DV-PVNOTE"]').waitFor();await capture(page,'real-writing-final',width);
      const inventory=await page.evaluate(`(()=>{${outerCollector(collect)};return collectDesignInventory({states:{writing:'#app'}});})()`),file=join(OUT,`real-writing-final-${width}.inventory.json`);writeFileSync(file,JSON.stringify(inventory,null,2));
      const r=spawnSync(join(ROOT,'.venv/bin/python'),[join(CORE,'skills/ui-copy-quality/scripts/check_design_contract.py'),'check','--contract',outerContract(join(DESIGN,'contract.json')),'--inventory',file,'--approved-extras',join(ROOT,'tests/fixtures/r276-direct/approved-extras.json'),'--json'],{encoding:'utf8'});writeFileSync(join(OUT,`real-writing-final-${width}.contract.json`),r.stdout);assert.equal(r.status,0,r.stdout);await page.close();
    }
  } finally {writeFileSync(join(OUT,'real-writing-final.manifest.json'),JSON.stringify({scope:'Live real writing stage, no mocks',screenshots},null,2));await browser.close();rmSync(temp,{recursive:true,force:true});}
}
if(process.argv.includes('--capture-live')){await captureLive();}else if(process.argv.includes('--real')){await runReal();}else

try {
  testFormulas();
  if(!process.env.R276_EXTERNAL_SERVER){
  const probe=await fetch(BASE).catch(()=>null);assert(!probe,'Gate port is already in use; refusing to reuse or stop another process');
  server=spawn(join(ROOT,'.venv/bin/python'),['-u','-c','from pathlib import Path; import sys; from studio.server import serve; s=serve(state_dir=Path(sys.argv[1]),port=int(sys.argv[2])); s.serve_forever()',temp,String(PORT)],{cwd:ROOT,env:{...process.env,LOCAL_MEDIA_ROOT:join(temp,'media')},stdio:['ignore','pipe','pipe']});
  server.stdout.on('data',d=>writeFileSync(join(OUT,'server.stdout.log'),d,{flag:'a'}));server.stderr.on('data',d=>writeFileSync(join(OUT,'server.stderr.log'),d,{flag:'a'}));
  let serverReady=false;for(let i=0;i<100;i++){if(await fetch(BASE).then(r=>r.ok).catch(()=>false)){serverReady=true;break;}await new Promise(r=>setTimeout(r,100));}assert(serverReady,'Studio gate port did not start');
  }
  browser=await chromium.launch({headless:true,...(process.env.VIDEO_RENDER_BROWSER?{executablePath:process.env.VIDEO_RENDER_BROWSER}:{channel:'chrome'})});
  const reference=await browser.newPage({viewport:{width:1440,height:900}});
  await reference.goto(pathToFileURL(join(DESIGN,'direct.html')).href+'#s=ready&chrome=0');
  await reference.locator('.dv-card').first().waitFor();
  await reference.waitForTimeout(700);
  for(let i=0;i<7;i++)await reference.locator('.dv-poster').nth(i).screenshot({path:join(OUT,`poster-${String(i+1).padStart(2,'0')}.jpg`),type:'jpeg'});
  if(!process.argv.includes('--checks-only'))for(const state of STATES)for(const width of [1440,960]){
    await reference.setViewportSize({width,height:900});
    await reference.goto(pathToFileURL(join(DESIGN,'direct.html')).href+`#s=${state}&chrome=0`);
    await reference.waitForTimeout(150);
    await reference.screenshot({path:join(OUT,`reference-${state}-${width}.png`),fullPage:true});
  }
  await reference.close();
  const ffmpeg=process.env.FFMPEG||spawnSync('which',['ffmpeg'],{encoding:'utf8'}).stdout.trim();
  const media=spawnSync(ffmpeg,['-y','-loop','1','-i',join(OUT,'poster-01.jpg'),'-t','140','-vf','scale=288:512','-r','1','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',join(OUT,'synthetic-output.mp4')],{encoding:'utf8'});assert.equal(media.status,0,media.stderr);
  const collectSource=readFileSync(join(CORE,'skills/ui-copy-quality/assets/collect_design_inventory.js'),'utf8');
  for(const state of STATES){
    writeFileSync(join(OUT,'fixtures',state+'.json'),JSON.stringify(fixture(state,source),null,2));
    for(const width of [1440,960]){
      const {page,mock}=await open(state,width);
      await capture(page,state,width);
      {
        const inventory=await page.evaluate(`(()=>{${outerCollector(collectSource)};return collectDesignInventory({states:{${JSON.stringify(state)}:'#app'}});})()`);
        const path=join(OUT,`${state}-${width}.inventory.json`);writeFileSync(path,JSON.stringify(inventory,null,2));
        const result=spawnSync(join(ROOT,'.venv/bin/python'),[join(CORE,'skills/ui-copy-quality/scripts/check_design_contract.py'),'check','--contract',outerContract(join(DESIGN,'contract.json')),'--inventory',path,'--approved-extras',join(ROOT,'tests/fixtures/r276-direct/approved-extras.json'),'--json'],{encoding:'utf8'});
        writeFileSync(join(OUT,`${state}-${width}.contract.json`),result.stdout);contracts.push({state,width,exit_code:result.status,result:JSON.parse(result.stdout)});
      }
      if(state==='ready'){await page.locator('[data-design-id="DV-CHECKS"] summary').click();assert(await page.getByText('画面下半截空着：主画面只占到 y=900，离字幕带还空 46.2%',{exact:true}).isVisible());}
      if(state==='empty')assert(await page.getByRole('button',{name:'生成',exact:true}).isDisabled());
      if(state==='unavailable')assert(await page.getByRole('button',{name:'生成',exact:true}).isDisabled());
      if(state.startsWith('done')){assert.equal(await page.locator('.dv-outchecks li.warn,.dv-outchecks li.fail').count(),0);if(state==='done-silent'){assert.equal(await page.locator('.dv-outchecks .none').textContent(),'无声预览，不检查声音');assert.equal(await page.locator('.dv-outchecks .none').evaluate(e=>getComputedStyle(e,'::before').content),'"–"');}}
      if(state==='writing')assert.equal(await page.locator('.dv-card').count(),7);
      await page.close();
    }
  }
  // A phone viewport is checked in addition to the task's two prescribed widths.
  for(const state of ['empty','writing','done','unavailable','read-error']){const {page}=await open(state,390);await capture(page,state,390);await page.close();}
  const {page,mock}=await open('ready');
  await testDetail(page,mock.current.job);
  assert.equal(mock.codeCalls,0);await page.locator('[data-design-id="DV-CODE"] summary').click();await page.waitForFunction(()=>document.querySelector('[data-design-id="DV-CODE"] pre')?.textContent.startsWith('<!doctype'));assert.equal(mock.codeCalls,1);
  const untouchedCards=()=>page.locator('.dv-card').evaluateAll(cards=>cards.filter(c=>c.dataset.shot!=='03').map(c=>({shot:c.dataset.shot,poster:c.querySelector('img')?.getAttribute('src'),status:c.querySelector('.st').textContent})));
  const beforeCards=await untouchedCards();
  await page.locator('[data-shot="03"]').click();await page.locator('[data-extra]').fill('数字再大一点');await page.getByRole('button',{name:'重写这一镜',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.main')?.dataset.designState==='rewriting');assert.equal(mock.rewriteCalls,1);assert.deepEqual(await untouchedCards(),beforeCards);
  const original=mock.current.job.shots.filter(s=>s.shotId!=='03').map(s=>({shotId:s.shotId,posterRevision:s.posterRevision,writtenAt:s.writtenAt}));
  const count=mock.polls;await page.clock.fastForward(2100);await page.waitForTimeout(100);assert(mock.polls>count);
  assert.equal(await page.locator('.dv-card[aria-current="true"]').getAttribute('data-shot'),'03');
  assert.deepEqual(mock.current.job.shots.filter(s=>s.shotId!=='03').map(s=>({shotId:s.shotId,posterRevision:s.posterRevision,writtenAt:s.writtenAt})),original);
  await page.evaluate(()=>{location.hash='view=projects';});await page.locator('[data-design-id="R208-PROJECTS"]').first().waitFor();const stopped=mock.polls;await page.clock.fastForward(61000);assert.equal(mock.polls,stopped);await page.close();
  const retry=await open('failed-shot');assert(await retry.page.getByRole('button',{name:'重试这一镜',exact:true}).isEnabled());await retry.page.getByRole('button',{name:'重试这一镜',exact:true}).click();await retry.page.waitForFunction(()=>document.querySelector('.main')?.dataset.designState==='writing');assert.equal(retry.mock.rewriteCalls,1);await retry.page.close();
  const interrupted=await open('ready');const interruptedData=structuredClone(interrupted.mock.current);interruptedData.job.status='failed';interruptedData.job.shots[0].status='interrupted';interrupted.mock.set(interruptedData);await interrupted.page.reload();await interrupted.page.locator('[data-retry-shot]').click();await interrupted.page.waitForFunction(()=>document.querySelector('.main')?.dataset.designState==='writing');assert.equal(interrupted.mock.rewriteCalls,1);await interrupted.page.close();
  const ready=await open('ready');const terminalCount=ready.mock.polls;await ready.page.clock.fastForward(61000);assert.equal(ready.mock.polls,terminalCount);await ready.page.close();
  const form=await open('empty');const chooser=form.page.waitForEvent('filechooser');await form.page.getByRole('button',{name:'导入分镜文件',exact:true}).click();await (await chooser).setFiles({name:'storyboard.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({shots:source.map(s=>({dialogue:s.dialogue}))}))});await form.page.waitForFunction(()=>document.querySelector('[data-f=dialogue]')?.value.length>20);assert.deepEqual(await form.page.locator('[data-f=dialogue]').evaluateAll(es=>es.map(e=>e.value)),source.map(s=>s.dialogue));await form.page.locator('[data-adjust]').fill('浅米色底');
  const voice=form.page.waitForEvent('filechooser');await form.page.getByRole('button',{name:'上传配音…',exact:true}).click();await (await voice).setFiles({name:'fixture.wav',mimeType:'audio/wav',buffer:Buffer.from('RIFFfixtureWAVE')});await form.page.getByText('fixture.wav',{exact:true}).waitFor();await form.page.getByRole('button',{name:'生成',exact:true}).click();await form.page.waitForFunction(()=>document.querySelector('[data-design-id="DV-FILM"]'));await form.page.waitForTimeout(100);assert.equal(form.mock.createCalls,1);assert.equal(form.mock.narrationCalls,1);await form.page.close();
  const out=await open('done');await out.page.locator('video').evaluate(v=>v.readyState>=1?null:new Promise(r=>v.addEventListener('loadedmetadata',r,{once:true})));await out.page.locator('[data-jump="2"]').click();const time=await out.page.locator('video').evaluate(v=>v.currentTime);assert(Math.abs(time-source[0].D-source[1].D)<.05,JSON.stringify({actual:time,expected:source[0].D+source[1].D}));const oldVideo=await out.page.locator('video').elementHandle();await out.page.getByRole('button',{name:'重新合成',exact:true}).click();await out.page.locator('[data-design-id="DV-COMPOSE"]').waitFor();assert.equal(out.mock.composeCalls,1);await oldVideo.evaluate(v=>v.ontimeupdate());await oldVideo.dispose();await out.page.close();
  assert.deepEqual(browserErrors,[]);
  const failures=contracts.filter(c=>c.exit_code!==0);writeFileSync(join(OUT,'contracts.json'),JSON.stringify(contracts,null,2));assert.equal(failures.length,0,JSON.stringify(failures.slice(0,3),null,2));
  console.log(`PASS ${contracts.length} design comparisons, ${screenshots.length} complete-page captures, formulas and browser interactions`);
} finally {
  writeFileSync(join(OUT,'screenshot-manifest.json'),JSON.stringify({scope:'F2 local Studio on configured gate port, intercepted projection fixtures; no backend generation claim',screenshots,contracts,browser_errors:browserErrors},null,2));
  await browser?.close();if(server){server.kill('SIGTERM');await new Promise(r=>server.once('exit',r));}rmSync(temp,{recursive:true,force:true});
}
