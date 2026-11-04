import {chromium} from '<本机 Playwright 模块>';
import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
const scratch='<隔离合成工作目录>';
const evidence='<仓库外证据目录>';
const media=path.join(scratch,'media'),workspace=path.join(media,'workspace'),state=path.join(scratch,'state');
await fs.mkdir(path.join(workspace,'ai-analysis'),{recursive:true});await fs.mkdir(state,{recursive:true});await fs.mkdir(evidence,{recursive:true});
const nonce=crypto.randomUUID(),items=[];
for(let i=0;i<2;i++){const name=`photo-h02-${nonce}-${i}.mov`,content=Buffer.from(`synthetic media ${nonce} ${i}`);await fs.writeFile(path.join(workspace,name),content);items.push({media_id:String(i+1).padStart(12,'0'),relative_path:name,sha256:crypto.createHash('sha256').update(content).digest('hex'),media_type:'video',duration_sec:0.4,image_health:'not_applicable',image_readable:null});}
await fs.writeFile(path.join(workspace,'ai-analysis/media-manifest.json'),JSON.stringify({items}));
const code='import sys; from pathlib import Path; from studio.server import serve; s=serve(state_dir=Path(sys.argv[1]),host="127.0.0.1",port=0); print("READY %d" % s.server_address[1],flush=True); s.serve_forever()';
const server=spawn('<项目 Python 解释器>',['-u','-c',code,state],{env:{...process.env,LOCAL_MEDIA_ROOT:media},stdio:['ignore','pipe','pipe']});
const port=await new Promise((resolve,reject)=>{let data='';server.stdout.on('data',c=>{data+=c;const m=data.match(/READY (\d+)/);if(m)resolve(m[1]);});server.on('exit',c=>reject(Error('server exited '+c)));setTimeout(()=>reject(Error('server startup timed out')),15000).unref();});
let browser, page, project, receiptRows=[], cleanupErrors=[];const pageErrors=[];
const shot=async name=>page.screenshot({path:path.join(evidence,name),fullPage:true});
try{
 browser=await chromium.launch({channel:'chrome',headless:true});page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});page.on('pageerror',e=>pageErrors.push(e.message));
 await page.goto(`http://127.0.0.1:${port}/`);await page.waitForSelector('.nav [data-nav]');
 project=await page.evaluate(async workspace=>{const token=(await(await fetch('/api/bootstrap')).json()).csrfToken;const r=await fetch('/api/projects',{method:'POST',headers:{'Content-Type':'application/json','X-Content-OS-CSRF':token},body:JSON.stringify({title:'合成回收站验收',localWorkspace:workspace})});const data=await r.json();if(!r.ok)throw Error(JSON.stringify(data));return data.project;},workspace);
 await page.reload();await page.locator(`[data-piece="${project.id}"]`).click();await page.waitForSelector('[data-ptab]');await page.locator('[data-nav="inbox"]').click();await page.waitForSelector('[data-delete]');
 await page.locator('[data-delete]').nth(0).check();await page.locator('[data-delete]').nth(1).check();await page.locator('#confirm-delete').click();await page.waitForSelector('#confirm-dialog[open]');
 const count=await page.locator('#confirm-dialog-message').textContent();if(!count.includes('2 项'))throw Error('wrong count: '+count);
 await shot('H-02-task3-confirm-desktop.png');await page.setViewportSize({width:390,height:844});await shot('H-02-task3-confirm-phone.png');await page.locator('#confirm-dialog button[value="cancel"]').click();
 if(await page.locator('[data-delete]:checked').count()!==2)throw Error('selection changed on cancel');for(const item of items)await fs.access(path.join(workspace,item.relative_path));console.log('CANCEL: 2 selected, both synthetic files unchanged');
 await page.route('**/media-delete/confirm',async route=>{const {selectedCandidateNumbers:[a,b]}=route.request().postDataJSON();await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true,status:'partial',receipts:[{candidate_number:a,status:'trashed'}],pending:[{candidate_number:b,failure_code:'post_move_verification_failed'}]})});});
 await page.locator('#confirm-delete').click();await page.locator('#confirm-dialog button[value="confirm"]').click();await page.waitForSelector('.feedback-error[role="alert"]');const partial=await page.locator('.feedback-error').textContent();
 if(!partial.includes('状态待确认')||!partial.includes('post_move_verification_failed')||await page.locator('[data-delete]:checked').count()!==1)throw Error('partial UI incorrect: '+partial);
 await shot('H-02-task3-uncertain-phone.png');await page.setViewportSize({width:1440,height:1000});await shot('H-02-task3-uncertain-desktop.png');console.log('SIMULATED_PARTIAL:',partial);
 await page.unroute('**/media-delete/confirm');await page.locator('#reanalyze').click();await page.waitForFunction(()=>document.querySelectorAll('[data-delete]').length===2);await page.locator('[data-delete]').nth(0).check();await page.locator('[data-delete]').nth(1).check();
 const next=page.waitForResponse(r=>r.url().includes('/media-delete/confirm'),{timeout:20000});await page.locator('#confirm-delete').click();await page.locator('#confirm-dialog button[value="confirm"]').click();const response=await next,body=await response.json();receiptRows=body.receipts||[];
 if(response.status()!==200||body.status!=='completed'||receiptRows.length!==2)throw Error('real confirm failed '+JSON.stringify({status:response.status(),body}));
 await page.waitForFunction(()=>document.querySelector('#toast')?.textContent?.includes('已移入系统回收站：2 项'));for(const item of items)if(await fs.stat(path.join(workspace,item.relative_path)).catch(()=>null))throw Error('synthetic source remains');
 const publicReceipts=await page.evaluate(async id=>{let r=await fetch(`/api/projects/${id}/media-delete/receipts`);return {status:r.status,body:await r.json()};},project.id);
 if(publicReceipts.status!==200||publicReceipts.body.receipts?.length!==2||publicReceipts.body.receipts.some(r=>r.status!=='trashed'||!r.receipt_id))throw Error('receipts missing');
 await shot('H-02-task3-moved-desktop.png');await page.setViewportSize({width:390,height:844});await shot('H-02-task3-moved-phone.png');
 if(pageErrors.length)throw Error('browser errors: '+JSON.stringify(pageErrors));
 console.log('REAL_CONFIRM:',JSON.stringify({http:response.status(),status:body.status,receiptCount:receiptRows.length,visibleReceiptCount:publicReceipts.body.receipts.length,filesMoved:true,pageErrors}));
}finally{
 if(page&&project){for(const row of receiptRows){try{const result=await page.evaluate(async({id,rid})=>{const token=(await(await fetch('/api/bootstrap')).json()).csrfToken;const r=await fetch(`/api/projects/${id}/media-delete/restore`,{method:'POST',headers:{'Content-Type':'application/json','X-Content-OS-CSRF':token},body:JSON.stringify({receiptId:rid})});return {status:r.status,body:await r.json()};},{id:project.id,rid:row.receipt_id});if(result.status!==200||result.body.receipt?.status!=='restored')cleanupErrors.push('restore failed '+JSON.stringify(result));}catch(e){cleanupErrors.push('restore exception '+e.message);}}}
 for(const item of items){const source=path.join(workspace,item.relative_path);let b=await fs.readFile(source).catch(()=>null);if(!b){const trash=path.join(process.env.HOME,'.Trash',item.relative_path);b=await fs.readFile(trash).catch(()=>null);if(b&&crypto.createHash('sha256').update(b).digest('hex')===item.sha256)await fs.rename(trash,source);else cleanupErrors.push('synthetic file missing or hash mismatch: '+item.relative_path);}if(b&&crypto.createHash('sha256').update(b).digest('hex')!==item.sha256)cleanupErrors.push('synthetic source hash mismatch: '+item.relative_path);}
 if(browser)await browser.close();server.kill('SIGINT');console.log('CLEANUP:',cleanupErrors.length?JSON.stringify(cleanupErrors):'two synthetic files restored and hash verified');if(cleanupErrors.length)process.exitCode=2;
}
