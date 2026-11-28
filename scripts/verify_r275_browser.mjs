// R275 G5/G6: real local server, temporary synthetic records, no production port or media.
import {createRequire} from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import vm from 'node:vm';
import {spawn,spawnSync} from 'node:child_process';
import readline from 'node:readline';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const require=createRequire(process.env.PW_REQ),{chromium}=require('playwright');
const out=path.resolve(process.env.R275_EVIDENCE),images=path.resolve(process.env.R275_SCREENSHOTS);
fs.mkdirSync(out,{recursive:true});fs.mkdirSync(images,{recursive:true});
const root=fs.mkdtempSync(path.join(os.tmpdir(),'r275-browser-'));
const html=fs.readFileSync('docs/R275-delete-works/index.html','utf8');
const data=Object.fromEntries(['OTHER','LZU'].map(k=>{const start=html.indexOf(`const ${k} = [`)+`const ${k} = `.length;return [k,vm.runInNewContext(html.slice(start,html.indexOf('\n];',start)+2))];}));
const fixture=spawn('.venv/bin/python',['-u','scripts/qa/r275_browser_fixture.py'],{env:{...process.env,R275_FIXTURE_ROOT:root,STUDIO_PORT:process.env.STUDIO_PORT||'0'},stdio:['pipe','pipe','pipe']});
const stderr=fs.createWriteStream(path.join(out,'fixture.log'));fixture.stderr.pipe(stderr);
const lines=readline.createInterface({input:fixture.stdout})[Symbol.asyncIterator]();
const next=async()=>{const r=await lines.next();assert(!r.done,'fixture terminated');const v=JSON.parse(r.value);assert(!v.fixture_error,v.fixture_error);return v;};
const base=(await next()).url;assert.notEqual(new URL(base).port,'8765');
const command=async(action,args={})=>{fixture.stdin.write(JSON.stringify({action,...args})+'\n');return next();};
const core=process.env.HARNESS_CORE_ROOT;
const collector=fs.readFileSync(path.join(core,'skills/ui-copy-quality/assets/collect_design_inventory.js'),'utf8');
const checkInventory=(inventory,name)=>{const file=path.join(out,name+'.json');fs.writeFileSync(file,JSON.stringify(inventory,null,2));return spawnSync('.venv/bin/python',[path.join(core,'skills/ui-copy-quality/scripts/check_design_contract.py'),'check','--contract','docs/R275-delete-works/contract.json','--approved-extras','docs/R275-delete-works/approved-extras.json','--inventory',file,'--json'],{encoding:'utf8'});};
const browser=await chromium.launch({channel:'chrome'}),checks=[],inventories={states:{}};
let context,page;
try{
 const catalog=await command('reset',{data});
 context=await browser.newContext({viewport:{width:1280,height:800},deviceScaleFactor:2,locale:'zh-CN',timezoneId:'Asia/Taipei'});
 await context.route('**/*',r=>new URL(r.request().url()).origin===base?r.continue():r.abort());
 page=await context.newPage();page.setDefaultTimeout(5000);
 await page.goto(base+'/#view=project&project=other');await page.locator('.piece').first().waitFor();
 if(process.env.R275_RED==='1'){
  const inventory=await page.evaluate(collector+';collectDesignInventory({states:{"pick-other":"#app"}})');
  const result=checkInventory(inventory,'red-g6-inventory');fs.writeFileSync(path.join(out,'red-g6.log'),result.stdout+result.stderr);
  assert.notEqual(result.status,0,'G6 baseline must be red');
  assert.equal(await page.getByRole('button',{name:'选择',exact:true}).count(),1,'G5: project page needs 选择');
 }else{
  await runWalkthrough({page,context,browser,base,data,catalog,command,checks,collector,inventories,images,out,checkInventory});
 }
}catch(error){fs.writeFileSync(path.join(out,process.env.R275_RED==='1'?'red-g5.log':'browser-failure.log'),error.stack);throw error;}
finally{await browser.close();await command('stop');fixture.stdin.end();await new Promise(resolve=>fixture.on('exit',resolve));stderr.end();fs.rmSync(root,{recursive:true,force:true});fs.writeFileSync(path.join(out,'browser-checks.json'),JSON.stringify({checks},null,2));}
console.log('PASS',checks.length);

async function runWalkthrough({page,context,browser,base,data,command,checks,collector,inventories,images,out,checkInventory}){
 const designContext=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:2});
 await designContext.route('**/*',r=>r.request().url().startsWith('file:')?r.continue():r.abort());
 const design=await designContext.newPage();await design.goto('file://'+path.resolve('docs/R275-delete-works/index.html'));
 await design.evaluate(()=>document.fonts.ready);
 // Freeze the shared CSS used by the approved mock, so new implementation rules cannot alter the reference.
 const referenceCss=Object.fromEntries(['styles.css','review.css'].map(file=>{const r=spawnSync('git',['show','HEAD:studio/static/'+file],{encoding:'utf8'});assert.equal(r.status,0);return [file,r.stdout];}));
 await design.evaluate(css=>{for(const link of document.querySelectorAll('link[rel="stylesheet"]')){const file=link.getAttribute('href').split('/').pop();if(css[file]){const style=document.createElement('style');style.textContent=css[file];link.replaceWith(style);}}},referenceCss);

 await design.addStyleTag({content:'.d-frame {--k:1!important;} .d-doc {max-width:none!important;}'});
 fs.mkdirSync(path.join(images,'design'),{recursive:true});
 for(const name of ['pick-other','confirm-other','deleted-other','partial-fail','confirm-lzu','projects-recent','recent']){
  const file=path.join(images,'design',name+'.png');const canvas=design.locator(`[data-design-state="${name}"]`).first();
  await canvas.evaluate(n=>{document.body.append(n);Object.assign(n.style,{position:'fixed',top:'0px',left:'0px',zIndex:'9999',transform:'none'});});
  await canvas.screenshot({path:file});await canvas.evaluate(n=>n.remove());
  const png=fs.readFileSync(file);assert.equal(png.readUInt32BE(16),2560);assert.equal(png.readUInt32BE(20),1600);
 }
 await designContext.close();
 const errors=[];page.on('pageerror',e=>{errors.push(e.message);fs.writeFileSync(path.join(out,'page-errors.json'),JSON.stringify(errors));});
 const card=id=>page.locator(`#review-screen [data-pick="${id}"]`);
 const selection=()=>page.getByRole('button',{name:'选择',exact:true});
 const ask=()=>page.locator('[data-delete-ask]');
 const confirm=()=>page.locator('[data-delete-submit]');
 const toast=()=>page.locator('.work-delete-toast');
 const rows=()=>page.locator('.recent-list .setrow');
 const manifest=[];
 let catalog,byFolder,csrf,resetSerial=0;
 async function saveExtra(filename,fullPage=true,coverage='complete document'){
  const file=path.join(images,filename),viewport=await page.evaluate(()=>({width:innerWidth,height:innerHeight,dpr:devicePixelRatio,scroll:document.documentElement.scrollHeight}));
  await page.screenshot({path:file,fullPage,animations:'disabled'});
  const png=fs.readFileSync(file);manifest.push({state:filename.replace('.png',''),path:file,route:page.url(),viewport,output_dimensions:{width:png.readUInt32BE(16),height:png.readUInt32BE(20)},sha256:crypto.createHash('sha256').update(png).digest('hex'),captured_at:new Date().toISOString(),coverage});
 }

 async function reset(view='project'){
  catalog=await command('reset',{data});byFolder=Object.fromEntries(catalog.pieces.map(p=>[p.folder_name,p]));
  csrf=(await (await fetch(base+'/api/bootstrap')).json()).csrfToken;
  await page.goto(base+'/?fixture='+ ++resetSerial +'#view='+view+(view==='project'?'&project=other':''));
  await page.locator(view==='project'?'.piece':'.proj').first().waitFor();
 }
 async function api(url,body){const r=await fetch(base+url,{method:body?'POST':'GET',headers:{'Content-Type':'application/json','X-Content-OS-CSRF':csrf},...(body?{body:JSON.stringify(body)}:{})});assert(r.ok,url+' '+r.status);return r.json();}
 async function remove(folders,move=false){const projects=folders.map(f=>byFolder[f]);return api('/api/projects/delete',{projectIds:projects.map(p=>p.id),expectedRevisions:Object.fromEntries(projects.map(p=>[p.id,p.revision])),moveFolders:move});}
 async function pick(folders){await selection().click();for(const folder of folders)await card(byFolder[folder].id).click();}
 async function count(n){await page.waitForFunction(n=>document.querySelectorAll('#review-screen .piece').length===n,n);assert.equal((await page.locator('.section-title').innerText()).replace(/\s+/g,''),`作品${n}件`);}
 async function capture(name,{inventory=true}={}){
  await page.evaluate(()=>document.fonts.ready);
  const actual=await page.evaluate(()=>({width:innerWidth,height:innerHeight,dpr:devicePixelRatio,scroll:document.documentElement.scrollHeight,client:document.documentElement.clientHeight}));
  assert.equal(actual.width,1280);assert.equal(actual.height,800);assert.equal(actual.dpr,2);
  const file=path.join(images,name+'.png');await page.screenshot({path:file,fullPage:true,animations:'disabled'});
  manifest.push({state:name,path:file,route:page.url(),viewport:actual,captured_at:new Date().toISOString(),sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),coverage:'complete document, fullPage; no nested scroll area except dialog list'});
  if(inventory){const v=await page.evaluate(collector+`;collectDesignInventory({states:{${JSON.stringify(name)}:"#app"}})`);Object.assign(inventories.states,v.states);}
 }
 const first=data.OTHER[0].folder,second=data.OTHER[1].folder,last=data.OTHER[7].folder;
 await reset('projects');
 assert.equal(await page.locator('.recent-row').count(),0);checks.push('Recent entry absent at zero');
 await page.locator('.proj').filter({hasText:'其他作品'}).click();await selection().waitFor();
 await pick([first,second]);const hash=page.url();
 assert.match(await page.locator('.pick-bar').innerText(),/已选 2 件/);assert.equal(page.url(),hash);
 assert.match(await card(byFolder[first].id).innerText(),/10月16日建.*文件夹 R131-hiatus-video-v4-render2/s);
 assert.match(await card(byFolder[second].id).innerText(),/10月16日建.*文件夹 R131-hiatus-video-v4-render/s);
 await capture('pick-other');checks.push('List entry → project → two distinguishable same-name cards, stable URL');
 await ask().click();await page.locator('dialog[open]').waitFor();
 assert.equal(await page.locator('.trash-opt').getAttribute('aria-checked'),'false');
 assert.equal(await page.locator('[data-delete-close]').evaluate(n=>n===document.activeElement),true);
 assert.equal(await page.locator('.del-list li').count(),2);
 await capture('confirm-other');
 await page.locator('[data-delete-close]').click();assert.equal(await page.locator('[data-pick][aria-checked="true"]').count(),2);
 await page.keyboard.press('Escape');assert.equal(await page.locator('[data-pick]').count(),0);
 checks.push('Unchecked folder option, cancel focus, selection retained, Esc exits');
 await page.goto(base+'/#view=project&project=other');await pick([first,second]);await ask().click();
 const delay=async r=>{await new Promise(resolve=>setTimeout(resolve,600));if(!page.isClosed())await r.continue();};
 await page.route('**/api/projects/delete',delay);
 const deleting=page.waitForResponse(r=>r.url()===base+'/api/projects/delete');
 await confirm().click();await count(6);await deleting;await page.unroute('**/api/projects/delete',delay);
 await toast().waitFor();assert.equal((await toast().innerText()).replace(/\s+/g,''),'已删除2件作品撤销');
 await capture('deleted-other');
 const names=await command('folder_names');assert(names.includes(first)&&names.includes(second));
 await page.locator('[data-delete-undo]').click();await count(8);checks.push('Direct URL; delayed deletion removes immediately; folders kept; undo returns eight');
 await pick([first,second]);await ask().click();await confirm().click();await toast().waitFor();
 await page.locator('.nav [data-nav="projects"]').click();await page.locator('.recent-row').waitFor();
 assert.match(await page.locator('#screen-sub').innerText(),/2 个项目 · 9 件作品/);
 assert.match(await page.locator('.recent-row').innerText(),/最近删除.*2 件/s);
 // Keep the undo notice outside this dedicated projects-state capture by waiting on its real timeout.
 await toast().waitFor({state:'hidden',timeout:10000});await capture('projects-recent');
 await page.locator('.recent-row').click();await rows().first().waitFor();assert.equal(await rows().count(),2);assert.equal(await page.locator('.nav [data-nav="projects"]').getAttribute('aria-current'),'true');
 await rows().first().getByRole('button',{name:'恢复',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('.recent-list .setrow').length===1);
 await page.locator('[data-recent-back]').click();await page.locator('.proj').filter({hasText:'其他作品'}).click();await count(7);
 checks.push('M/K counters, recent count 2→1, single restore returns to original group with seven');
 await reset();await command('fail',{folders:[last]});await pick([first,last]);await ask().click();await page.locator('.trash-opt').click();await confirm().click();await toast().waitFor();await count(7);
 assert.match(await toast().innerText(),/已删除 1 件。「P3 合成口播实践：平均速度」没删成：文件夹移不到废纸篓/);
 await capture('partial-fail');await page.locator('[data-delete-undo]').click();await count(8);checks.push('Real per-item backend failure and successful-only undo');
 await reset('projects');const lzu=catalog.groups.find(g=>g.id!=='other');await page.locator(`[data-go-project="${lzu.id}"]`).click();await selection().click();
 await card(catalog.pieces.find(p=>p.folder_name===data.LZU[1].folder).id).click();
 assert(await card(catalog.pieces.find(p=>p.folder_name===data.LZU[1].folder).id).locator('.pick-box').evaluate(n=>{const r=n.getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('.pick-box')===n;}));
 await ask().click();await page.locator('dialog[open]').waitFor();
 assert.equal(await page.locator('.trash-opt').getAttribute('aria-disabled'),'true');await page.locator('.trash-opt').dispatchEvent('click');assert.equal(await page.locator('.trash-opt').getAttribute('aria-checked'),'false');

 await capture('confirm-lzu');await page.locator('[data-delete-close]').click();checks.push('Populated project refuses folder move and cancelling preserves work');
 await reset();await remove([first]);await remove([last],true);const gone=await remove([data.OTHER[4].folder],true);await command('missing',{id:gone.results[0].id});
 await page.goto(base+'/#view=recent');await rows().first().waitFor();assert.equal(await rows().count(),3);await capture('recent');
 assert.equal(await rows().getByRole('button',{name:'移出列表',exact:true}).count(),1);checks.push('Recent: original / trash / missing rows from real stored receipts');
 await page.getByRole('button',{name:'移出列表',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('.recent-list .setrow').length===2);
 checks.push('Unrecoverable item dismissed without another dialog');
 // Worst empty-group boundary uses the real soft-delete route, not a modified image or catalog stub.
 await reset();await remove(data.OTHER.slice(0,7).map(p=>p.folder));await page.reload();await count(1);await pick([last]);await ask().click();await confirm().click();await page.locator('.recent-row').waitFor();
 assert.equal(await page.locator('.proj').filter({hasText:'其他作品'}).count(),0);await capture('worst-last-work',{inventory:false});checks.push('Deleting last work removes group and returns to project list');
 await reset();const missing=await remove([first],true);await command('missing',{id:missing.results[0].id});await page.goto(base+'/#view=recent');await rows().first().waitFor();
 const missingStatus=await rows().first().locator('small').last().innerText();
 assert.doesNotMatch(missingStatus,/^没恢复成/,'C1: recent status before recovery must describe the folder without a failure prefix');
 assert.equal(missingStatus,'文件夹已经不在废纸篓里，恢复不了。');await capture('worst-unrecoverable',{inventory:false});
 await reset();const occupied=await remove([first],true);await command('occupied',{id:occupied.results[0].id});await page.goto(base+'/#view=recent');await rows().first().waitFor();
 assert.equal(await rows().first().locator('small').last().innerText(),'原来的位置已经有同名文件夹，恢复不了。');
 checks.push('C1: recent missing/occupied status before recovery uses design copy without failure prefix');
 // Count / interaction boundary variants, including mixed folder eligibility, keyboard and reload.
 await reset();await selection().click();assert.match(await page.locator('.pick-bar').innerText(),/还没选作品/);assert(await ask().isDisabled());
 await page.locator('[data-delete-all]').click();assert.equal(await page.locator('[data-pick][aria-checked="true"]').count(),8);assert.equal(await page.locator('[data-delete-all]').innerText(),'全不选');await page.reload();await selection().waitFor();assert.equal(await page.locator('[data-pick]').count(),0);
 await selection().click();await card(byFolder[first].id).focus();await page.keyboard.press('Space');assert.equal(await card(byFolder[first].id).getAttribute('aria-checked'),'true');await page.keyboard.press('Escape');
 checks.push('Zero selection, all/unselect-all, keyboard checkbox and reload clears selection');
 // Mixed selection: count comes exclusively from backend preflight, and only that subset moves.
 await reset();await command('set_media',{id:byFolder[second].id});await page.reload();await pick([first,second]);await ask().click();
 assert.equal((await page.locator('.trash-opt b').innerText()).replace(/\s+/g,''),'同时把1件没有素材的作品的文件夹移到废纸篓');
 assert.equal(await page.locator('.del-list .keep').innerText(),'有素材，文件夹留在原处');
 await page.locator('.trash-opt').click();await confirm().click();await count(6);await toast().waitFor();
 const mixedNames=await command('folder_names');assert(!mixedNames.includes(first)&&mixedNames.includes(second));
 await page.locator('[data-delete-undo]').click();await count(8);checks.push('Mixed eligibility M=1 of N=2; only explicitly selected eligible folder moves');
 // Failed requests restore the optimistic list and do not present a successful deletion.
 await reset();await pick([first,second]);await ask().click();
 const failRequest=r=>r.fulfill({status:503,json:{ok:false,error:{code:'service_unavailable',message:'test-only transport failure'}}});
 await page.route('**/api/projects/delete',failRequest);await confirm().click();await count(8);await toast().waitFor();
 assert.equal(await toast().innerText(),'已删除 0 件，2 件没删成');assert.equal(await page.locator('[data-delete-undo]').count(),0);
 await page.unroute('**/api/projects/delete',failRequest);checks.push('HTTP failure restores cards/counts and keeps folders/records');
 // Eight real seconds, including hover pause and expiry after route navigation. No clock/rAF override.
 await reset();await pick([first,second]);await ask().click();await confirm().click();await toast().waitFor();await toast().hover();
 await page.waitForTimeout(8200);assert(await toast().isVisible());await page.locator('.nav [data-nav="projects"]').click();await page.locator('.recent-row').waitFor();
 let extraRequests=0;const onRequest=r=>{if(r.url().startsWith(base+'/api/'))extraRequests++;};page.on('request',onRequest);
 await toast().waitFor({state:'hidden',timeout:10000});page.off('request',onRequest);assert.equal(extraRequests,0);
 checks.push('Undo notice pauses under pointer for >8 s, expires after navigation, no expiry request');
 await reset();
 // Desktop and actual phone layouts must retain all content and avoid horizontal clipping.
 for(const width of [1280,390]){
  await page.setViewportSize({width,height:800});await page.goto(base+'/#view=project&project=other');await pick([first,second]);
  const overflow=await page.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth}));assert.equal(overflow.viewport,width);assert(overflow.scroll<=width+1);
  await saveExtra(`selection-${width}-full.png`);
  if(width===390){
   const metrics=await page.evaluate(()=>({height:innerHeight,total:document.documentElement.scrollHeight,dpr:devicePixelRatio,bar_top:document.querySelector('.pick-bar').getBoundingClientRect().top})),offsets=[];
   for(let y=0;y<metrics.total;y+=Math.floor(metrics.height*.65)){
    const actual=await page.evaluate(y=>{scrollTo(0,y);return scrollY;},y);offsets.push(actual);
    await saveExtra(`selection-390-scroll-${offsets.length}.png`,false,`document scroll ${actual}..${actual+metrics.height}`);
    if(actual+metrics.height>=metrics.total)break;
   }
   assert(offsets.at(-1)+metrics.height>=metrics.total);
   fs.writeFileSync(path.join(out,'phone-scroll-coverage.json'),JSON.stringify({metrics,offsets},null,2));
   await page.evaluate(()=>scrollTo(0,0));
  }

  await ask().click();await page.locator('dialog[open]').waitFor();assert(await page.locator('.work-delete-dialog').evaluate(n=>n.getBoundingClientRect().right<=innerWidth&&n.getBoundingClientRect().left>=0));
  await saveExtra(`confirm-${width}.png`);await page.locator('[data-delete-close]').click();await page.keyboard.press('Escape');
 }
 checks.push('Desktop 1280 and real phone 390; full page, wrapping and dialog bounds');
 // Check the complete internal dialog list with overlapping captures, ending on the last item.
 await page.setViewportSize({width:1280,height:800});await reset();await selection().click();await page.locator('[data-delete-all]').click();await ask().click();
 const list=page.locator('.del-list'),metrics=await list.evaluate(n=>{const r=n.getBoundingClientRect(),s=getComputedStyle(n);return {height:n.clientHeight,width:n.clientWidth,total:n.scrollHeight,x:r.x+parseFloat(s.borderLeftWidth),y:r.y+parseFloat(s.borderTopWidth),dpr:devicePixelRatio};});assert(metrics.total>metrics.height);
 const coverage=[];for(let y=0;y<metrics.total;y+=Math.floor(metrics.height*.7)){
  const actual=await list.evaluate((n,y)=>{n.scrollTop=y;return n.scrollTop;},y);coverage.push(actual);
  await saveExtra(`confirm-eight-part-${coverage.length}.png`,false,`dialog list scroll ${actual}..${Math.min(actual+metrics.height,metrics.total)} of ${metrics.total}`);
  if(actual+metrics.height>=metrics.total)break;
 }
 assert(coverage.at(-1)+metrics.height>=metrics.total);assert(await page.locator('.del-list li').last().evaluate(n=>n.getBoundingClientRect().bottom<=n.parentElement.getBoundingClientRect().bottom+1));
 fs.writeFileSync(path.join(out,'dialog-scroll-coverage.json'),JSON.stringify({metrics,offsets:coverage,step_overlap:.3},null,2));
 await page.locator('[data-delete-close]').click();await page.keyboard.press('Escape');
 await reset();const phoneGone=await remove([first],true);await command('missing',{id:phoneGone.results[0].id});await page.setViewportSize({width:390,height:800});await page.goto(base+'/#view=recent');await rows().first().waitFor();
 await saveExtra('recent-390-full.png');
 checks.push('Eight-item dialog: overlapping numbered parts cover bottom; phone unrecoverable state');

 assert.deepEqual(errors,[]);checks.push('No JavaScript exceptions');
 assert.equal(Object.keys(inventories.states).length,7,'G6 must cover all seven states');
 const g6=checkInventory(inventories,'green-g6-inventory');fs.writeFileSync(path.join(out,'green-g6.log'),g6.stdout+g6.stderr);assert.equal(g6.status,0,g6.stdout+g6.stderr);checks.push('G6: seven states; no unapproved copy, blocks or missing blocks');
 for(const m of manifest){if(!m.output_dimensions){const png=fs.readFileSync(m.path);m.output_dimensions={width:png.readUInt32BE(16),height:png.readUInt32BE(20)};}}
 fs.writeFileSync(path.join(out,'screenshot-manifest.json'),JSON.stringify({screenshots:manifest,review_result:'PENDING',font_mode:'fallback-local',note:'Review actual saved images before assigning a result.'},null,2));
}
