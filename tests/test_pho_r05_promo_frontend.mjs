import assert from 'node:assert/strict';
import {barSeconds, promoShotSeconds, promoShotTiming, autoBars, promoTotals, promoMissing, promoPayload, splitRows, recipeRewriteBody} from '../studio/static/direct-promo.js';
assert.equal(barSeconds(120), 2);
assert.equal(promoShotSeconds({bars:3},120),6);
assert.equal(promoShotTiming({bars:3},120),'3 小节 · 6.0 秒');
const {wholeIssues,detailContent}=await import('../studio/static/direct-shot-detail.js');
assert.deepEqual(wholeIssues('promo').map(x=>x[0]),['space','color']);
assert(wholeIssues('talk').some(x=>x[0]==='sync'));
assert.deepEqual(detailContent('promo',{visual:'画面',text:'标题',dialogue:'口播'}),[['要表现什么','画面'],['屏幕上的字','标题']]);
assert.deepEqual(detailContent('talk',{dialogue:'口播'}),[['口播','口播']]);
assert.equal(autoBars({seconds: 4.1}, 120), 3);
assert.deepEqual(promoTotals([{visual:'a', bars:'auto', recipeId:null}],120,[]),{bars:2,seconds:4});
assert.equal(promoMissing({shots:[],track:null,style:null}), 'shots');
assert.deepEqual(splitRows('a\nb').map(x=>x.visual),['a','b']);
assert.equal(promoPayload({brief:'x',track:{file_sha256:'t'},startBar:1,shots:[{visual:'a',bars:'auto',recipeId:null}]}).kind,'promo');
console.log('PASS promo calculations');

const {newPromoDraft, promoDraftAfter, failureMessage} = await import('../studio/static/direct-view.js');
const track={file_sha256:'music-1',promoBeat:{bpm:120,bars:8}};
const shots=[{visual:'界面',text:'标题',recipeId:'r1',bars:2,imageId:'img1'},{visual:'  ',bars:'auto'}];
assert.deepEqual(promoPayload({brief:'介绍',track,startBar:3,shots}),{kind:'promo',promo:{brief:'介绍',trackId:'music-1',startBar:3,fadeOutSeconds:1,shots:[{visual:'界面',text:'标题',recipeId:'r1',bars:2,imageId:'img1'}]}});
assert.equal(promoMissing({shots:[],track:null,style:null}), 'shots');
assert.equal(promoMissing({shots,track:null,style:null}), 'track');
assert.equal(promoMissing({shots,track,startBar:8,style:null}), 'short');
assert.equal(promoMissing({shots,track,startBar:1,style:null}), 'style');
assert.equal(promoMissing({shots,track,startBar:1,style:{id:'ui'}}), null);
const draft={brief:'介绍',shots,track,startBar:3};
assert.equal(promoDraftAfter(draft,'switch-to-talk'),draft);
assert.deepEqual(promoDraftAfter(draft,'generated'),newPromoDraft());
assert.deepEqual(promoDraftAfter(draft,'leave-project'),newPromoDraft());
for(const code of ['beat_map_unavailable','track_too_short','recipe_not_found']) assert.ok(!failureMessage(code).includes('错误码'));
console.log('PASS F3 request, missing fields, and draft lifecycle');

assert.equal(autoBars({seconds:null}, 120), 2);
assert.deepEqual(recipeRewriteBody('r2'), {recipeId:'r2'});
console.log('PASS F4 recipe rewrite and unknown duration');

// Exercise the detail handler and its real mutation path through the POST body.
const {readFileSync}=await import('node:fs');
const {runInNewContext}=await import('node:vm');
const detail=readFileSync(new URL('../studio/static/direct-shot-detail.js',import.meta.url),'utf8');
const code=detail.slice(detail.indexOf('  async function mutate('),detail.indexOf("  container.querySelector('[data-revise]')?.addEventListener"));
let click, request;
const detailContainer={isConnected:true,querySelector:()=>({addEventListener:(_,fn)=>{click=fn;}})};
const detailShot={shotId:'02',recipe:{id:'r1'}};
runInNewContext(code,{container:detailContainer,locked:false,draft:{},redraw:()=>{},api:async()=>({csrfToken:'token'}),fetch:async(url,options)=>{request={url,options};return {ok:true,json:async()=>({ok:true})};},base:'/api/projects/p/direct/jobs/j/shots/02',message:()=>'',job:{shots:[detailShot]},shot:detailShot,state:{shotId:'02'},onRewrite:()=>{},renderShotDetail:()=>{},projectId:'p',loadPromo:async()=>({recipes:[],categories:[]}),pickerHost:{},openRecipePicker:(_host,opts)=>opts.onChoose('r2'),recipeRewriteBody,JSON});
await click();
await new Promise(resolve=>setImmediate(resolve));
assert.equal(request.url,'/api/projects/p/direct/jobs/j/shots/02/rewrite');
assert.equal(request.options.method,'POST');
assert.deepEqual(JSON.parse(request.options.body),{recipeId:'r2'});
console.log('PASS F4 picker sends selected recipe to shot rewrite');

// The browser checks exercise the actual Studio entry, routing and rendered contract.
const {mkdtempSync, mkdirSync, rmSync, writeFileSync} = await import('node:fs');
const {tmpdir, homedir} = await import('node:os');
const {join, resolve} = await import('node:path');
const {spawn, spawnSync} = await import('node:child_process');
const {createServer} = await import('node:net');
const {pathToFileURL} = await import('node:url');
const root=resolve(import.meta.dirname,'..');
const python=process.env.STUDIO_PYTHON || join(root,'.venv/bin/python');
const core=process.env.HARNESS_CORE;
if(!core) throw new Error('设置 HARNESS_CORE，指向 Harness Engineering 的 Core 目录（设计合同检查脚本在那里）');
const out=process.env.PHO_R05_PROMO_EVIDENCE || join(homedir(),'.photo-content-os/evidence/Pho_R05-shotcraft-line/promo-studio/fe-shots');
// 纯色 16:9 小图，代替海报和截图；仓库忽略 *.jpg，所以内联在这里。
const FIXTURE_JPG=Buffer.from('/9j/4AAQSkZJRgABAgAAAQABAAD//gAPTGF2YzYzLjEuMTAyAP/bAEMACBAQExATFhYWFhYWGhgaGxsbGhoaGhsbGx0dHSIiIh0dHRsbHR0gICIiJSYlIyMiIyYmKCgoMDAuLjg4OkVFU//EAE0AAQEAAAAAAAAAAAAAAAAAAAAEAQEBAQAAAAAAAAAAAAAAAAAABAUQAQAAAAAAAAAAAAAAAAAAAAARAQAAAAAAAAAAAAAAAAAAAAD/wAARCABaAKADASIAAhEAAxEA/9oADAMBAAIRAxEAPwCEBUygAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH//2Q==','base64');
const data=JSON.parse(readFileSync(join(root,'tests/fixtures/pho-r05-promo/state-fixtures.json'),'utf8'));
// 锁定切换条长在生成后的页面上；节拍图读不到是合成失败：镜头都写好、渲好，任务失败码 beat_map_unavailable。
data.states['promo-locked']=data.states['promo-done'];
{const failed=structuredClone(data.states['promo-done']); Object.assign(failed.job,{status:'failed',failureCode:'beat_map_unavailable'}); Object.assign(failed.job.output,{status:'failed',composedAt:null}); data.states['promo-beat-fail']=failed;}
const temp=mkdtempSync(join(tmpdir(),'pho-r05-'));
const socket=createServer(); await new Promise((ok,fail)=>socket.once('error',fail).listen(0,'127.0.0.1',ok));
const port=socket.address().port; await new Promise(ok=>socket.close(ok));
const base=`http://127.0.0.1:${port}`;
const server=spawn(python,[join(root,'scripts/launch_studio.py'),'--no-browser','--state-dir',temp,'--port',String(port)],{cwd:root,env:{...process.env,LOCAL_MEDIA_ROOT:join(temp,'media')},stdio:['ignore','ignore','pipe']});
let stderr=''; server.stderr.on('data',chunk=>stderr+=chunk); let browser;
try {
 let ready=false; for(let i=0;i<150;i++){if(server.exitCode!==null)throw new Error(`Studio exited ${server.exitCode}: ${stderr}`); if(await fetch(base).then(r=>r.ok).catch(()=>false)){ready=true;break;} await new Promise(r=>setTimeout(r,100));} assert(ready,`Studio failed to start: ${stderr}`);
 const pw=process.env.PLAYWRIGHT_MODULE || join(homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs');
 const {chromium}=await import(pathToFileURL(pw)); browser=await chromium.launch({headless:true,channel:'chrome'}); mkdirSync(out,{recursive:true});
 const collector=readFileSync(join(core,'skills/ui-copy-quality/assets/collect_design_inventory.js'),'utf8');
 const project={id:'fixture-piece',title:'示例作品',revision:1,documents:{},workspace_key:'fixture-piece'};
 const styles=JSON.parse(readFileSync(join(root,'tests/fixtures/r278-direct/first.json'),'utf8')).styles;
 const failures=[];
 for(const state of ['promo-empty','promo-filled','promo-filled-b','promo-short','promo-no-music','promo-picker','promo-done','promo-locked','promo-beat-fail']){
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'}); const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://fonts.googleapis.com/**',r=>r.abort()); await page.route('https://fonts.gstatic.com/**',r=>r.abort());
  await page.route('**/api/**',route=>{
   const p=new URL(route.request().url()).pathname; let result;
   if(p.endsWith('.jpg')) return route.fulfill({contentType:'image/jpeg',body:FIXTURE_JPG});
   if(p==='/api/bootstrap')result={ok:true,csrfToken:'fixture-csrf',projects:[project]};
   else if(p==='/api/review/catalog')result={ok:true,groups:[{id:'group',title:'其他作品',pieces:[project],count:1,pending:0,produced:0}],pieces:[project]};
   else if(p===`/api/projects/${project.id}`)result={ok:true,project,videoHandoff:null};
   else if(p.endsWith('/direct/handoff'))result={ok:true,handoff:null};
   else if(p.includes('/direct/jobs'))result=data.states[state]||{ok:true,job:null};
   else if(p==='/api/direct/styles')result=styles;
   else if(p==='/api/direct/recipes'){ if(state==='promo-picker') return route.continue(); result=data.recipes; } // 选配方弹窗用仓库里真实的 124 张配方目录，和稿子同一份数据
   else if(p==='/api/review/music')result=state==='promo-no-music'?{ok:true,tracks:[]}:data.music;
   else if(p==='/api/diagnostics')result={ok:true,diagnostics:{checks:[],checking:false}};
   else if(p==='/api/settings')result={ok:true,settings:{upstream:{upstream_features_available:false}}};
   else if(p==='/api/settings/analysis-budget')result={ok:true,analysisBudget:{budget:{},revision:1}};
   else if(p==='/api/setup/state')result={ok:true,setup:{current_step:'done'}};
   else if(p==='/api/review/music-settings')result={ok:true,egress:{state:'absent'},account:{state:'absent'}};
   else if(p==='/api/upstream/tasks')result={ok:true,tasks:[]};
   else if(p==='/api/assets')result={ok:true,assets:[]};
   else if(p==='/api/assets/statistics')result={ok:true,statistics:{categories:[],asset_count:0}};
   else return route.fulfill({status:404,body:`Unmocked ${p}`});
   return route.fulfill({contentType:'application/json',body:JSON.stringify(result)});
  });
  await page.goto(base+'/#view=piece&piece=fixture-piece&ptab=direct');
  if(!data.states[state]){
   await page.locator('[data-kind="promo"]').click(); await page.locator('[data-design-id="DV-PROMO"]').waitFor();
   if(state!=='promo-empty' && state!=='promo-no-music'){
    await page.locator('[data-empty]').fill('开场：产品名\n界面：展示功能\n收尾：结束');
    await page.locator('[data-track="track-1"]').click();
    if(state==='promo-filled') for(let i=0;i<3;i++){await page.locator('[data-design-id="DV-RC"]').nth(i).click();await page.locator('[data-recipe="r1"]').click();await page.locator('[data-use]').click();}
    if(state==='promo-short') for(let i=0;i<20;i++) await page.locator('[data-start="1"]').click();
    if(state==='promo-picker'){await page.locator('[data-design-id="DV-RC"]').nth(1).click(); await page.locator('[data-design-id="DV-RPCARD"]').first().waitFor();}
   }
  } else if(state==='promo-done'){ await page.locator('[data-design-id="DV-FILM"]').waitFor(); await page.locator('[data-shot]').first().click(); await page.locator('[data-design-id="DV-RCBOX"]').waitFor(); }
  else await page.locator('[data-shot]').first().waitFor();
  await page.evaluate(()=>document.fonts.ready); assert.deepEqual(errors,[],`${state} page errors`);
  const metrics=await page.evaluate(()=>({width:innerWidth,height:innerHeight,scrollHeight:document.documentElement.scrollHeight}));
  await page.screenshot({path:join(out,`${state}.png`),fullPage:state!=='promo-picker'}); // 弹窗固定在视口里，只截一屏
  const inventory=await page.evaluate(`(()=>{${collector};return collectDesignInventory({states:{${JSON.stringify(state)}:'#app'}});})()`);
  const contract=JSON.parse(readFileSync(join(root,'docs/design-drafts/page-script-to-video--promo-line--Pho_R05/contract.json'),'utf8'));
  const excluded=new Set(['R208-NAV','DV-TOPBAR','DV-MODEL','DV-TABS','DV-STYLE','DV-STYLE-LIB','DV-STYLE-CUSTOM','DV-DESIGN','DV-SCRUB','DV-RESCRIPT-ENTRY']);
  const allowed=new Set(contract.states[state].ids); const invState=inventory.states[state];
  if(state!=='promo-filled') invState.texts=invState.texts.filter(t=>allowed.has(t.design_id));
  else invState.texts=invState.texts.filter(t=>!excluded.has(t.design_id)&&!String(t.design_id||'').startsWith('DV-STYLE'));
  invState.ids=invState.ids.filter(id=>allowed.has(id));
  const file=join(temp,`${state}.json`); writeFileSync(file,JSON.stringify(inventory));
  const check=spawnSync(python,[join(core,'skills/ui-copy-quality/scripts/check_design_contract.py'),'check','--contract',join(root,'docs/design-drafts/page-script-to-video--promo-line--Pho_R05/contract.json'),'--inventory',file,'--json'],{encoding:'utf8'});
  assert(check.stdout,check.stderr); const result=JSON.parse(check.stdout); const inv=inventory.states[state];
  console.log(`${state}: viewport=${metrics.width}x${metrics.height}, height=${metrics.scrollHeight}, texts=${inv.texts.length}, ids=${inv.ids.length}, contract_exit=${check.status}, differences=${result.failures.length}`);
  if(check.status!==0) failures.push({state,failures:result.failures}); await page.close();
 }
 if(failures.length){console.error(JSON.stringify(failures,null,2)); process.exitCode=1;}
} finally {
 await browser?.close(); if(server.exitCode===null){server.kill('SIGTERM'); await new Promise(ok=>server.once('exit',ok));} rmSync(temp,{recursive:true,force:true});
}
