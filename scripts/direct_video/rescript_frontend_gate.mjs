#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync,mkdirSync,mkdtempSync,rmSync,statfsSync,copyFileSync,existsSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {homedir,tmpdir} from 'node:os';
import {spawn,spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {testFormulas,testBrowser} from '../../tests/test_r278_direct_rescript.mjs';
import {testLibraryFormulas,testLibraryBrowser} from '../../tests/test_r283_frontend.mjs';
import {testHandoffFormulas,testHandoffBrowser} from '../../tests/test_r282_frontend.mjs';
const ROOT=resolve(import.meta.dirname,'../..');
export const R278_STATES=['entry','writing','composing','rescript','rescript-zoom','rescript-adjust','rescript-other','first-empty','first','first-new','first-new-text','first-new-drafting','first-new-ready','first-new-revising','first-new-accepted','first-new-failed','designing','inherited','adjusted'];
export const R283_STATES=['first-lib','first-none','library'];
export const R282_STATES=['first-handoff','rescript-newer'];
const R282_VARIANTS={'first-handoff-legacy':'first-handoff','rescript-newer-unversioned':'rescript-newer'};
const ALL_STATES=[...R278_STATES,...R283_STATES,...R282_STATES];
export function blockSelectors(state){
  const names=state.startsWith('rescript')||state.startsWith('first')?['steps','head','script','style','opts','gen']:['steps','head',...(['designing','inherited','adjusted','library'].includes(state)?['design']:[])];
  const selectors={steps:'[data-flow]',head:'[data-head]',script:'[data-script-slot]',style:'[data-style-slot]',opts:'.dv-opts',gen:'.dv-start',design:'[data-design]'};
  // Generation is collected inside a wrapper so the root design id is inventoried.
  selectors.gen='[data-gen-slot]';return Object.fromEntries(names.map(name=>[`${state}-${name}`,selectors[name]]));
}
// Compose the changed regions from the newer approved contract. The old gates
// retain their untouched surface and interaction checks; no extras are added.
export function composeLegacyContract(contract,r278,fixtures){
  for(const [state,spec] of Object.entries(contract.states)){
    const job=fixtures(state)?.job,form=['empty','filled','unavailable'].includes(state);
    const stopped=job&&['ready','done','failed'].includes(job.status)&&job.output.status!=='composing'&&!job.shots.some(s=>['writing','rendering'].includes(s.status)||s.look?.status==='running'||s.versions?.some(v=>v.version===s.currentVersion&&v.verify?.status==='running'))&&job.failureCode!=='claude_cli_unavailable';
    const hasSteps=spec.ids.includes('DV-STEPS'),added=hasSteps?['分镜脚本','等分镜脚本']:[];
    if(job&&hasSteps)added.push(stopped?'改分镜脚本':job.output.status==='composing'?'合成完才能改':'写完才能改');
    if(spec.ids.includes('DV-DESIGN')&&job?.design.status==='done')added.push('动作规矩','不用');
    if(form){
      const prefix=state==='empty'?'first-empty':'first';
      for(const block of [...['head','script','style','opts','gen'].map(part=>`${prefix}-${part}`),...(state==='empty'?[]:['rescript-adjust-opts','first-new-text-style'])]){
        const approved=r278.states[block];added.push(...approved.copy);spec.attr_copy=[...new Set([...(spec.attr_copy||[]),...(approved.attr_copy||[])])];spec.ids.push(...approved.ids);
      }
      if(state!=='empty'){
        // R276 types only the leading background clause of R278's approved
        // from-scratch example. Keep that exact approved excerpt in this form.
        const example=r278.states['first-new-text-style'].attr_copy.find(t=>t.startsWith('例：'));
        assert(example,'R278 approved from-scratch example is missing');
        added.push(example.slice(2).split('，')[0]);
      }
      spec.ids=spec.ids.filter(id=>id!=='DV-LINES');
    }
    spec.copy=[...new Set([...spec.copy.filter(t=>!t.includes('口播稿')),...added])];
    spec.attr_copy=(spec.attr_copy||[]).filter(t=>!t.includes('口播稿'));
    if(job&&hasSteps)spec.ids.push(stopped?'DV-RESCRIPT-ENTRY':'DV-RESCRIPT-LOCKED');
    spec.ids=[...new Set(spec.ids)];
  }
  return contract;
}
export async function checkBlocks(page,state,{core,contract,out,name=state,width}){
  state=R282_VARIANTS[state]||state;
  await page.evaluate(()=>{const bar=document.querySelector('.dv-genbar');if(bar&&!bar.parentElement.hasAttribute('data-gen-slot')){const wrap=document.createElement('div');wrap.className='dv-body';wrap.dataset.genSlot='';bar.before(wrap);wrap.append(bar);}});
  const source=readFileSync(join(core,'skills/ui-copy-quality/assets/collect_design_inventory.js'),'utf8');
  const inventory=await page.evaluate(({source,states})=>{const collect=new Function(`${source};return collectDesignInventory;`)();return collect({states});},{source,states:blockSelectors(state)});
  assert.equal(Object.keys(inventory.states).length,Object.keys(blockSelectors(state)).length,'missing state roots');
  const file=join(out,`${name}-${width}.inventory.json`);writeFileSync(file,JSON.stringify(inventory,null,2));
  const result=spawnSync(join(ROOT,'.venv/bin/python'),[join(core,'skills/ui-copy-quality/scripts/check_design_contract.py'),'check','--contract',contract,'--inventory',file,'--json'],{encoding:'utf8'});
  assert(result.stdout,result.stderr);writeFileSync(join(out,`${name}-${width}.contract.json`),result.stdout);return {state,name,width,exit_code:result.status,result:JSON.parse(result.stdout)};
}
async function main(){
  const CORE=process.env.HARNESS_CORE;assert(CORE,'Set HARNESS_CORE');
  const DESIGN=process.env.R278_DESIGN_ROOT||join(ROOT,'docs/tasks/R278-direct-rescript/design');
  const MEDIA=process.env.R278_DESIGN_MEDIA_ROOT||join(DESIGN,'img');
  const OUT=process.env.R278_FRONTEND_EVIDENCE||join(homedir(),'.photo-content-os/evidence/R278-direct-rescript/frontend');mkdirSync(OUT,{recursive:true});
  const PORT=Number(process.env.DIRECT_GATE_PORT||8768);assert.equal(PORT,8768,'R278 must use 8768');const BASE=`http://127.0.0.1:${PORT}`;
  const widths=process.argv.find(x=>x.startsWith('--widths='))?.slice(9).split(',').map(Number)||[1440,960];assert(widths.length&&widths.every(w=>Number.isInteger(w)&&w>=320),'Invalid viewport widths');
  const subset=process.argv.find(x=>x.startsWith('--states='))?.slice(9).split(',');
  if(subset)assert(subset.length&&subset.every(s=>ALL_STATES.includes(s)||Object.hasOwn(R282_VARIANTS,s)||s==='real-worst-rescript'),'Unknown capture state');
  const previous=subset&&!process.argv.includes('--checks-only')&&existsSync(join(OUT,'screenshot-manifest.json'))?JSON.parse(readFileSync(join(OUT,'screenshot-manifest.json'),'utf8')):null;
  const temp=mkdtempSync(join(tmpdir(),'r278-frontend-')),screenshots=previous?previous.screenshots.filter(x=>!subset.includes(x.state)||!widths.includes(x.viewport.width)):[],contracts=previous?previous.contracts.map((x,i)=>({...x,name:x.name||previous.screenshots[i]?.state||x.state})).filter(x=>!subset.includes(x.name)||!widths.includes(x.width)):[],errors=[],requests=[],realLayouts=[];let server,browser;
  const {chromium}=await import(pathToFileURL(process.env.VIDEO_RENDER_PLAYWRIGHT_MODULE.replace(/index\.js$/,'index.mjs')));
  const read=state=>{
    const source=state==='rescript-newer-unversioned'?'rescript-newer':state;
    const data=JSON.parse(readFileSync(source==='real'?join(OUT,'real-projection.json'):join(ROOT,'tests/fixtures',R282_STATES.includes(source)||source==='first-handoff-legacy'?'r282-direct':R283_STATES.includes(source)?'r283-direct':'r278-direct',source+'.json'),'utf8'));
    if(state==='rescript-newer-unversioned')data.handoff.handoff.revision=null;
    return data;
  };
  const disk=()=>{const s=statfsSync(OUT);assert(s.bavail*s.bsize>=3*1024**3,'Disk below 3 GiB; stop');};
  const hash=buf=>createHash('sha256').update(buf).digest('hex');
  async function open(state,width=1440,{prepare=true,omitCurrentStyle=false,handoff}={}){
    disk();const data=read(state),initial=structuredClone(data.latest),projectId=initial.job?.projectId||'fixture-piece';
    const project={id:projectId,title:'断更一年，我拆了四句话',revision:1,documents:{},workspace_key:projectId},piece={...project,group_id:'fixture-group',videos:0,photos:0,versions:0,outputs:[]},group={id:'fixture-group',title:'其他作品',pieces:[piece],count:1,pending:0,produced:0};
    if(omitCurrentStyle)data.styles.styles=data.styles.styles.filter(x=>x.jobId!==initial.job.jobId);
    let current=structuredClone(initial),draft=null,failCreate=false,draftReads=0;
    if(handoff!==undefined)data.handoff={ok:true,handoff};
    const mock={initial,requests:[],creates:[],revisions:[],uploads:[],get draftReads(){return draftReads;},get current(){return current;},setCreateFailure(value){failCreate=value;}};
    const page=await browser.newPage({viewport:{width,height:900},reducedMotion:'reduce',timezoneId:'Asia/Taipei'});page.setDefaultTimeout(12000);page.on('pageerror',e=>errors.push({state,message:e.message}));
    await page.clock.install({time:new Date('2026-10-26T01:10:42+08:00')});
    await page.route('https://fonts.googleapis.com/**',r=>r.abort());await page.route('https://fonts.gstatic.com/**',r=>r.abort());
    await page.route('**/api/**',async route=>{try{
      const req=route.request(),url=new URL(req.url()),p=url.pathname,method=req.method(),json=(body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
      if(p.includes('/direct/handoff/images/'))return route.fulfill({contentType:'image/jpeg',body:readFileSync(join(OUT,'media',`hand-${p.split('/').at(-1)}.jpg`))});
      if(p.endsWith('/direct/handoff'))return json(data.handoff||{ok:true,handoff:null});
      if(p.endsWith('/poster.jpg')||p.endsWith('/clip.mp4')||p.endsWith('/output.mp4')){
        if(p.startsWith('/api/direct/styles/library/')){const ident=p.split('/').at(-2),ext=p.endsWith('.mp4')?'mp4':'jpg';assert(data.styles.library.some(x=>x.id===ident));return route.fulfill({contentType:ext==='mp4'?'video/mp4':'image/jpeg',body:readFileSync(join(ROOT,'scripts/direct_video/style_library',`${ident}.${ext}`))});}
        let filename;if(p.includes('style-drafts'))filename='style-7719.jpg';else if(p.includes('dv_other1'))filename='style-0d6e.jpg';else if(p.includes('dv_other2'))filename='style-7719.jpg';else filename=`job-${p.includes('/shots/')?p.split('/').at(-2):'01'}.${p.endsWith('.mp4')?'mp4':'jpg'}`;
        const buffer=readFileSync(join(OUT,'media',filename));return route.fulfill({contentType:p.endsWith('.mp4')?'video/mp4':'image/jpeg',body:buffer});
      }
      if(method==='POST'){
        assert.equal(req.headers()['x-content-os-csrf'],'fixture-csrf');if(p.endsWith('/narration')){mock.uploads.push({path:p,bytes:req.postDataBuffer().length});return json(current);}
        const body=req.postDataJSON();mock.requests.push({path:p,body});requests.push({state,path:p,body});
        if(p.includes('/style-drafts')){if(p.endsWith('/revise')){mock.revisions.push(body);draft=structuredClone(data.draft.draft);}else {draft=structuredClone(data.draft.draft);draft.shot=body.shot;}return json({ok:true,draft},202);}
        if(p.endsWith('/direct/jobs')){mock.creates.push(body);if(failCreate)return json({ok:false,error:{code:'model_timeout'}},400);current=read('writing').latest;return json(current,201);}
        if(p.endsWith('/narration'))return json(current);
        throw new Error(`Unmocked mutation ${p}`);
      }
      if(p==='/api/direct/styles')return json(data.styles);
      if(p.includes('/style-drafts/')){draftReads++;return json({ok:true,draft});}
      if(p.includes('/direct/jobs/'))return json(current);
      if(p==='/api/bootstrap')return json({ok:true,csrfToken:'fixture-csrf',projects:[project]});
      if(p==='/api/review/catalog')return json({ok:true,groups:[group],pieces:[piece]});
      if(p===`/api/projects/${projectId}`)return json({ok:true,project,videoHandoff:null});
      if(p==='/api/diagnostics')return json({ok:true,diagnostics:{checks:[],checking:false}});
      if(p==='/api/settings')return json({ok:true,settings:{upstream:{upstream_features_available:false}}});
      if(p==='/api/settings/analysis-budget')return json({ok:true,analysisBudget:{budget:{},revision:1}});
      if(p==='/api/setup/state')return json({ok:true,setup:{current_step:'done'}});
      if(p==='/api/review/music-settings')return json({ok:true,egress:{state:'absent'},account:{state:'absent'}});
      if(p==='/api/upstream/tasks')return json({ok:true,tasks:[]});
      if(p==='/api/assets')return json({ok:true,assets:[]});
      if(p==='/api/assets/statistics')return json({ok:true,statistics:{categories:[],asset_count:0}});
      if(p==='/api/review/music')return json({ok:true,tracks:[]});
      throw new Error(`Unmocked API ${method} ${p}`);
    }catch(e){errors.push({state,message:e.stack});await route.abort();}});
    await page.goto(`${BASE}/#view=piece&piece=${projectId}&ptab=direct`);
    await page.locator(initial.job?'.dv-film':'.dv-start').waitFor();
    if(prepare){
      if(state.startsWith('rescript')||state==='real'){await page.locator('[data-rescript]').click();await page.locator('.dv-sb').waitFor();await page.locator('.dv-sw-card').first().waitFor();assert.equal(await page.locator('.dv-sb .sb-tag').count(),0,'Rescript pictures have no source labels');}
      if(state==='rescript-adjust')await page.locator('[data-adjust]').fill('强调色换成暖黄，其余不动');
      if(state==='rescript-other')await page.locator('[data-design-id="DV-STYLE-CARDS"] [data-style-card]').last().click();
      if(state.startsWith('first')&&!['first-empty','first-handoff','first-handoff-legacy'].includes(state)){
        const chooser=page.waitForEvent('filechooser');await page.locator('[data-import]').click();await(await chooser).setFiles({name:'storyboard.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data.script))});await page.locator('.dv-sb').waitFor();
        if(state.startsWith('first-new'))await page.locator('[data-mode="new"]').click();
        if(state.startsWith('first-new')&&state!=='first-new'){await page.locator('[data-desc]').fill(data.text);}
        if(['first-new-drafting','first-new-ready','first-new-revising','first-new-accepted','first-new-failed'].includes(state)){
          if(state==='first-new-revising'){const ready=read('first-new-ready').draft.draft;data.draft.draft=ready;}
          await page.locator('[data-draft]').click();
          if(state==='first-new-revising'){await page.locator('[data-revise]').waitFor();await page.locator('[data-revise]').fill('主色再深一点，标题再大一号');data.draft.draft=read(state).draft.draft;await page.locator('[data-revise-go]').click();await page.locator('[data-draft-clock]').waitFor();}
          else if(state==='first-new-ready'){await page.locator('[data-revise]').waitFor();await page.locator('[data-revise]').fill('主色再深一点，标题再大一号');}
          else if(state==='first-new-accepted'){await page.locator('[data-accept]').click();}
          else if(state==='first-new-drafting')await page.waitForFunction(start=>{const seconds=Math.max(0,Math.round((Date.now()-Date.parse(start))/1000));return document.querySelector('[data-draft-clock]')?.textContent===`已用 ${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;},data.draft.draft.startedAt);
          else await page.locator('.dv-sw-fail').waitFor();
        }
      }
      if(state==='first-lib')await page.locator('[data-library="flat"]').click();
    }
    return {page,mock};
  }
  async function testZoomAndClips(page){
    const videos=page.locator('.sb-pic video');assert.equal(await videos.count(),7);
    assert(await videos.first().evaluate(v=>v.muted&&v.loop&&v.playsInline&&!v.controls&&!!v.poster&&v.paused&&v.getAttribute('aria-hidden')==='true'));
    const pics=page.locator('button[data-pic]');
    for(const action of ['Escape','close','outside','scroll']){await pics.nth(1).click();await page.locator('.sb-zoom').waitFor();assert(await page.locator('.sb-zoom video').evaluate(v=>v.controls&&v.paused));if(action==='Escape')await page.keyboard.press('Escape');else if(action==='close')await page.locator('[data-zoom-close]').click();else if(action==='outside')await page.locator('.dv-script-sub').click();else await page.evaluate(()=>document.dispatchEvent(new Event('scroll')));assert.equal(await page.locator('.sb-zoom').count(),0);assert(await pics.nth(1).evaluate(b=>document.activeElement===b),`focus after ${action}`);}
    await pics.first().click();await pics.nth(1).click();assert((await page.locator('.sb-zoom header').textContent()).includes('02'));await page.keyboard.press('Escape');
    await page.emulateMedia({reducedMotion:'no-preference'});await pics.first().scrollIntoViewIfNeeded();await page.waitForFunction(()=>{const v=document.querySelector('.sb-pic video');return v&&!v.paused;});await page.locator('.dv-genbar').scrollIntoViewIfNeeded();await page.waitForFunction(()=>document.querySelector('.sb-pic video').paused);await page.emulateMedia({reducedMotion:'reduce'});
    await videos.first().evaluate(v=>v.dispatchEvent(new Event('error')));assert.equal(await pics.first().locator('video').count(),0);assert.equal(await pics.first().locator('img').count(),1);await pics.first().click();assert.equal(await page.locator('.sb-zoom img').count(),1);await page.keyboard.press('Escape');
  }
  async function capture(page,state,width){
    disk();await page.evaluate(async()=>{await document.fonts.ready;document.activeElement?.blur();for(let y=0;y<document.documentElement.scrollHeight;y+=650){scrollTo(0,y);await new Promise(r=>requestAnimationFrame(r));}scrollTo(0,0);});
    if(state==='rescript-zoom'){await page.locator('button[data-pic]').nth(1).click();await page.locator('.sb-zoom').waitFor();}
    await page.locator('img').evaluateAll(imgs=>Promise.all(imgs.map(i=>i.decode().catch(()=>{}))));
    const metrics=await page.evaluate(()=>({width:innerWidth,height:innerHeight,scrollHeight:document.documentElement.scrollHeight,scrollWidth:document.documentElement.scrollWidth,scrollY}));assert.equal(metrics.width,width);assert(metrics.scrollWidth<=width,`${state}: horizontal page overflow ${metrics.scrollWidth}`);
    const layout=await page.evaluate(()=>{
      const form=document.querySelector('.dv-form'),style=document.querySelector('.dv-style-wide'),bar=document.querySelector('.dv-genbar'),opts=document.querySelector('.dv-opts'),table=document.querySelector('.dv-sb');
      if(!form)return null;const f=form.getBoundingClientRect(),s=style.getBoundingClientRect(),b=bar.getBoundingClientRect(),o=opts.getBoundingClientRect();
      return {fullWidth:Math.abs(f.width-s.width)<1&&Math.abs(f.width-b.width)<1,ordered:f.bottom<=s.top&&s.bottom<=o.top&&o.bottom<=b.top,optionsColumns:getComputedStyle(opts).gridTemplateColumns.split(' ').length,tableWidth:table?.getBoundingClientRect().width,expectedTableWidth:table?Math.max(1100,f.width-2):null};
    });
    if(layout){assert(layout.fullWidth&&layout.ordered,`${state}: full-row ordering`);assert.equal(layout.optionsColumns,width<=960?1:2);if(layout.tableWidth)assert(Math.abs(layout.tableWidth-layout.expectedTableWidth)<2,`${state}: storyboard width formula`);}
    const path=join(OUT,`${state}-${width}.png`);await page.screenshot({path,fullPage:true});const buffer=readFileSync(path),dims={width:buffer.readUInt32BE(16),height:buffer.readUInt32BE(20)};assert.equal(dims.width,width);assert(dims.height>=metrics.scrollHeight);
    screenshots.push({state,route:page.url(),viewport:{width,height:900},capture_time:new Date().toISOString(),scroll_coverage:[0,metrics.scrollHeight],output_dimensions:dims,path,sha256:hash(buffer),browser:browser.version(),font_mode:'fallback-local',review_result:'PENDING',review_note:'Awaiting individual image inspection; fixture API data in real local Studio.'});
  }
  function prepareMedia(){
    mkdirSync(join(OUT,'media'),{recursive:true});for(const i of [1,2,3,4,5,6,7])for(const ext of ['jpg','mp4']){const name=`job-${String(i).padStart(2,'0')}.${ext}`;copyFileSync(join(MEDIA,name),join(OUT,'media',name));}
    for(const i of [1,2,3,4,5,6,7]){const name=`hand-${String(i).padStart(2,'0')}.jpg`;copyFileSync(join(MEDIA,name),join(OUT,'media',name));}
    for(const name of ['style-7719.jpg','style-0d6e.jpg'])copyFileSync(join(MEDIA,name),join(OUT,'media',name));
    const source=join(homedir(),'.photo-content-os/studio-r276/direct-jobs-parked/project-fc6baa3294/dv_0e184e961bd14ac084c67411/job.json');
    const before=hash(readFileSync(source));copyFileSync(source,join(OUT,'real-job.json'));
    const code=`import sys,json
from pathlib import Path
sys.path[:0]=['.','scripts']
from studio.direct_video import projection
p=Path(sys.argv[1]);raw=json.loads(p.read_text())
for s in raw['shots']:
 s.setdefault('currentVersion',1);s.setdefault('versions',[]);s.setdefault('boxes',[]);s.setdefault('look',{'status':'none','failureCode':None,'findings':[]});s.setdefault('sample',False)
j=projection(raw)
style={'projectId':j['projectId'],'jobId':j['jobId'],'title':'断更一年，我拆了四句话','createdAt':j['createdAt'],'design':{k:v for k,v in j['design'].items() if k not in ['status','source']},'posterUrl':'/api/projects/'+j['projectId']+'/direct/jobs/'+j['jobId']+'/shots/01/poster.jpg?v=1'}
print(json.dumps({'latest':{'ok':True,'job':j},'styles':{'ok':True,'styles':[style]}},ensure_ascii=False))`;
    const result=spawnSync(join(ROOT,'.venv/bin/python'),['-c',code,join(OUT,'real-job.json')],{cwd:ROOT,encoding:'utf8'});assert.equal(result.status,0,result.stderr);const real=JSON.parse(result.stdout);real.styles.library=read('first').styles.library;writeFileSync(join(OUT,'real-projection.json'),JSON.stringify(real));
    const after=hash(readFileSync(source));assert.equal(before,after);assert.equal(before,hash(readFileSync(join(OUT,'real-job.json'))));writeFileSync(join(OUT,'source-preservation.json'),JSON.stringify({before,after,copy:before,identical:true},null,2));
  }
  try{
    const expectedBlocks=Object.keys(JSON.parse(readFileSync(join(DESIGN,'contract.json'),'utf8')).states).sort();
    assert.deepEqual(ALL_STATES.flatMap(s=>Object.keys(blockSelectors(s))).sort(),expectedBlocks,'Every approved block must be collected');
    testFormulas();testLibraryFormulas();testHandoffFormulas();disk();prepareMedia();assert(!await fetch(BASE).catch(()=>null),'8768 already occupied; refusing to reuse or kill it');
    server=spawn(join(ROOT,'.venv/bin/python'),['-u','-c','from pathlib import Path; import sys; from studio.server import serve; serve(state_dir=Path(sys.argv[1]),port=int(sys.argv[2])).serve_forever()',temp,String(PORT)],{cwd:ROOT,env:{...process.env,LOCAL_MEDIA_ROOT:join(temp,'media')},stdio:['ignore','pipe','pipe']});
    server.stdout.on('data',d=>writeFileSync(join(OUT,'server.stdout.log'),d,{flag:'a'}));server.stderr.on('data',d=>writeFileSync(join(OUT,'server.stderr.log'),d,{flag:'a'}));
    let ready=false;for(let i=0;i<100;i++){if(await fetch(BASE).then(r=>r.ok).catch(()=>false)){ready=true;break;}await new Promise(r=>setTimeout(r,100));}assert(ready,'Studio failed to start');
    const live=await fetch(BASE+'/api/direct/styles').then(r=>{assert(r.ok);return r.json();});
    assert.deepEqual(live.library,read('first').styles.library,'Fixture library must match the real backend projection');
    const mediaChecks=[];
    for(const item of live.library){
      const poster=await fetch(BASE+item.posterUrl);assert.equal(poster.status,200);const bytes=Buffer.from(await poster.arrayBuffer());assert.equal(hash(bytes),hash(readFileSync(join(ROOT,'scripts/direct_video/style_library',item.id+'.jpg'))));
      const clip=await fetch(BASE+item.clipUrl,{headers:{Range:'bytes=0-63'}});assert.equal(clip.status,206);assert(Buffer.from(await clip.arrayBuffer()).equals(readFileSync(join(ROOT,'scripts/direct_video/style_library',item.id+'.mp4')).subarray(0,64)));
      mediaChecks.push({id:item.id,poster_status:poster.status,poster_sha256:hash(bytes),clip_status:clip.status,range:clip.headers.get('content-range')});
    }
    writeFileSync(join(OUT,'real-library-api.json'),JSON.stringify({library:live.library,media:mediaChecks},null,2));
    browser=await chromium.launch({headless:true,executablePath:process.env.VIDEO_RENDER_BROWSER});
    if(!process.argv.includes('--capture-only')){await testHandoffBrowser({open});await testLibraryBrowser({open});await testBrowser({open,testZoomAndClips});}
    const captureStates=subset||[...ALL_STATES,...Object.keys(R282_VARIANTS),'real-worst-rescript'];
    for(const state of captureStates)for(const width of state==='real-worst-rescript'?[1440,960]:widths){
      const {page}=await open(state==='real-worst-rescript'?'real':state,width);if(!process.argv.includes('--checks-only'))await capture(page,state,width);
      if(state==='real-worst-rescript'){
        const layout=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
        assert.equal(layout.width,width,'Real legacy job must use the requested viewport');
        realLayouts.push(layout);writeFileSync(join(OUT,'real-worst-layout.json'),JSON.stringify(realLayouts,null,2));
      }
      if(state==='rescript-zoom'&&process.argv.includes('--checks-only'))await page.locator('button[data-pic]').nth(1).click();
      contracts.push(await checkBlocks(page,state==='real-worst-rescript'?'rescript':state,{core:CORE,contract:join(DESIGN,'contract.json'),out:OUT,name:state,width}));await page.close();
    }
    writeFileSync(join(OUT,'contracts.json'),JSON.stringify(contracts,null,2));assert.deepEqual(errors,[]);assert.equal(contracts.filter(c=>c.exit_code!==0).length,0,JSON.stringify(contracts.filter(c=>c.exit_code!==0).map(c=>({state:c.state,width:c.width,result:c.result})),null,2));
    for(const layout of realLayouts)assert(layout.scrollWidth<=layout.width,`Real legacy rescript horizontal overflow: ${layout.scrollWidth} > viewport ${layout.width}; constrain the style metadata column`);
    console.log(`PASS R278/R282/R283: ${contracts.length} contract runs; ${screenshots.length} complete-page screenshots; mounted browser interactions`);
  }finally{
    await browser?.close();if(server){server.kill('SIGTERM');await new Promise(r=>server.once('exit',r));}rmSync(temp,{recursive:true,force:true});
    writeFileSync(join(OUT,'browser-requests.json'),JSON.stringify(requests,null,2));writeFileSync(join(OUT,'browser-errors.json'),JSON.stringify(errors,null,2));
    if(!process.argv.includes('--checks-only'))writeFileSync(join(OUT,'screenshot-manifest.json'),JSON.stringify({scope:'R278 local Studio 8768; mocked API projections, including one copied real legacy job; no production or model-generation claim',screenshots,contracts,browser_errors:errors},null,2));
  }
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)await main();
