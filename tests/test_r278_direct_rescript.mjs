import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import * as view from '../studio/static/direct-view.js';
import {composeLegacyContract} from '../scripts/direct_video/rescript_frontend_gate.mjs';
import {blankRow,normalizeRows,rowTimes,rowSummary,storyboard,splitRow,mergeRow,pasteRows} from '../studio/static/direct-storyboard.js';
import {canGenerate,canDraft,stylePayload,styleTime,sameSampleShot,appendHint} from '../studio/static/direct-style.js';

export function testFormulas(){
  const rows=normalizeRows([{dialogue:'  一😀。 ',visual:'画',subtitle:'字',camera:'推',audio:'鼓'},{dialogue:'',visual:'留'},{dialogue:'二'.repeat(306)}]);
  assert.equal(rows[0].dialogue,'一😀。');assert.equal(rows[0].audio,'鼓');
  const times=rowTimes(rows);assert.equal(times[0][0],0);assert.equal(times[0][1],3/5.1);assert.deepEqual(times[1],null);assert.equal(times[2][0],3/5.1);assert.equal(times[2][1],309/5.1);
  assert.deepEqual(rowSummary(rows),{count:2,seconds:309/5.1,measured:false});
  const timed=[{dialogue:'一',startSeconds:2,endSeconds:9},{dialogue:'二',startSeconds:9,endSeconds:13}];assert.deepEqual(rowTimes(timed,true),[[2,9],[9,13]]);assert.deepEqual(rowSummary(timed,true),{count:2,seconds:13,measured:true});
  assert.deepEqual(storyboard(rows),{shots:[{shotId:'01',dialogue:'一😀。',visual:'画',subtitle:'字',camera:'推',audio:'鼓'},{shotId:'02',dialogue:'二'.repeat(306)}]});
  const image={poster:'poster',clip:'clip'};const original={...blankRow('前面后面'),visual:'画',subtitle:'字',camera:'推',audio:'鼓',image};const parts=splitRow([original],0,2,2);assert.equal(parts[0].dialogue,'前面');assert.equal(parts[0].image,image);assert.deepEqual(parts[1],blankRow('后面'));
  const merged=mergeRow([original,{...blankRow('新'),visual:'新画',subtitle:'新字',camera:'拉',audio:'铃'}],1);assert.equal(merged[0].dialogue,'前面后面新');assert.equal(merged[0].visual,'画；新画');assert.equal(merged[0].subtitle,'字；新字');assert.equal(merged[0].camera,'推；拉');assert.equal(merged[0].audio,'鼓；铃');assert.equal(merged[0].image,image);
  const pasted=pasteRows([original],0,2,2,'甲\n\n乙\r\n丙');assert.deepEqual(pasted.map(r=>r.dialogue),['前面甲','乙','丙后面']);assert.equal(pasted[0].image,image);assert.equal(pasted[1].visual,'');
  const base={projectId:'p',jobId:'j'},draft={draftId:'d',status:'ready',shot:storyboard(rows).shots[0]};
  const state={mode:'base',base,adjust:'改',text:'说明',draft:null,accepted:false};
  assert(canGenerate(rows,state,false,false));for(const bad of [true])assert(!canGenerate(rows,state,bad,false));assert(!canGenerate(rows,state,false,true));assert(!canGenerate([],state,false,false));assert(!canGenerate(rows,{...state,base:null},false,false));
  assert(!canGenerate(rows,{...state,mode:'new',draft},false,false));assert(canGenerate(rows,{...state,mode:'new',draft,accepted:true},false,false));assert(!canGenerate(rows,{...state,mode:'new',draft:{...draft,status:'writing'},accepted:true},false,false));
  assert(canDraft(rows,state,false,false));assert(!canDraft(rows,{...state,text:' '},false,false));assert(!canDraft([],state,false,false));assert(!canDraft(rows,{...state,draft:{status:'writing'}},false,false));assert(!canDraft(rows,state,true,false));
  assert.deepEqual(stylePayload(state,'p'),{styleBase:{kind:'job',projectId:'p',jobId:'j'},style:'改'});assert.deepEqual(stylePayload({...state,mode:'new',draft,accepted:true},'p'),{styleBase:{kind:'draft',projectId:'p',draftId:'d'},style:''});
  assert.equal(appendHint('已有\n','强调色'),'已有\n强调色：');assert.equal(appendHint('','底色和主色'),'底色和主色：');
  assert.equal(styleTime('2026-10-26T01:04:00+08:00'),'10 月 26 日 01:04');assert.equal(view.elapsed('2026-10-26T00:00:00Z',Date.parse('2026-10-26T00:00:42Z')),42);
  assert(sameSampleShot(draft.shot,storyboard(rows).shots[0]));for(const key of ['dialogue','visual','subtitle','camera'])assert(!sameSampleShot(draft.shot,{...draft.shot,[key]:'变'}));assert(sameSampleShot(draft.shot,{...draft.shot,audio:'另一个'}));
  const job={status:'done',shots:[],output:{status:'ready'},failureCode:null};assert(view.canRescript(job,false));assert(!view.canRescript(job,true));assert(!view.canRescript({...job,status:'writing'},false));assert(!view.canRescript({...job,output:{status:'composing'}},false));for(const shot of [{look:{status:'running'}},{versions:[{version:1,verify:{status:'running'}}],currentVersion:1}])assert(!view.canRescript({...job,shots:[shot]},false));
  console.log('PASS R278 formulas, editing, request bodies, availability and entry locks');
}

// Invoked by the screenshot gate against the real mounted Studio, with API fixtures.
export async function testBrowser(h){
  let x=await h.open('entry');let {page,mock}=x;
  await page.evaluate(()=>{window.r278OldOutput=document.querySelector('.dv-out video');});
  assert.equal(await page.locator('button[data-rescript]').count(),1);await page.locator('[data-rescript]').click();await page.locator('.dv-sb').waitFor();
  assert.equal(await page.locator('[data-f="dialogue"]').first().inputValue(),mock.initial.job.shots[0].dialogue);assert.equal(await page.locator('[data-f="visual"]').first().inputValue(),mock.initial.job.shots[0].visual||'');
  assert.equal(await page.locator('[data-style-card][aria-pressed="true"]').getAttribute('data-job'),mock.initial.job.jobId);
  assert.equal(await page.locator('.dv-lines').count(),0);assert.equal(await page.locator('.dv-form [data-generate]').count(),0);assert.equal(await page.locator('.dv-genbar [data-generate]').count(),1);
  assert.equal(await page.evaluate(()=>{try{window.r278OldOutput.ontimeupdate();return null;}catch(e){return e.message;}}),null,'Detached output video must not update the rescript screen');
  assert.equal(await page.locator('[data-f="visual"]').first().getAttribute('placeholder'),'写这一镜画什么（可不填）');
  for(const f of ['subtitle','camera','audio'])assert.equal(await page.locator(`[data-f="${f}"]`).first().getAttribute('placeholder'),'—');
  const placeholderColors=await page.locator('.dv-sb').evaluate(e=>['visual','subtitle','camera','audio'].map(f=>getComputedStyle(e.querySelector(`[data-f="${f}"]`),'::placeholder').color));
  assert(placeholderColors.every(c=>c===placeholderColors[0]),'All empty cells use the same muted placeholder token');
  assert.equal(await page.locator('.dv-sb .sb-tag').count(),0,'Rescript pictures have no source labels');
  const sourceTags=await page.evaluate(async()=>{
    const {renderStoryboard,blankRow}=await import('/direct-storyboard.js');
    const container=document.createElement('div');document.body.append(container);let editor;
    try{
      const poster=document.querySelector('.sb-pic video').poster;
      editor=renderStoryboard(container,{rows:[{...blankRow('来源测试'),image:{poster,tag:'代码渲染'}}],onChange:()=>{},onImport:()=>{}});
      const tag=container.querySelector('.sb-tag')?.textContent;editor.dispose();
      editor=renderStoryboard(container,{rows:[{...blankRow('转义测试'),image:{poster,tag:'参考关键帧 <b>原文</b>'}}],onChange:()=>{},onImport:()=>{}});
      return {tag,escaped:container.querySelector('.sb-tag')?.textContent,htmlElements:container.querySelectorAll('.sb-tag b').length};
    }finally{editor?.dispose();container.remove();}
  });
  assert.deepEqual(sourceTags,{tag:'代码渲染',escaped:'参考关键帧 <b>原文</b>',htmlElements:0});
  assert.deepEqual(await page.locator('.dv-sb th').allTextContents(),['镜头','画面','台词','字幕 / 花字','景别 · 运镜','音乐 / 音效暂不进成片']);
  const before=mock.requests.length;await page.locator('[data-rescript-back]').click();assert.equal(mock.requests.length,before);await page.locator('[data-rescript]').click();
  const ta=page.locator('[data-f="dialogue"]').first();await ta.focus();await ta.evaluate(t=>t.setSelectionRange(2,2));const count=await page.locator('.dv-sb tbody tr').count();await ta.press('Enter');assert.equal(await page.locator('.dv-sb tbody tr').count(),count+1);await page.locator('[data-f="dialogue"]').nth(1).press('Backspace');assert.equal(await page.locator('.dv-sb tbody tr').count(),count);
  await ta.evaluate(t=>t.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',isComposing:true,bubbles:true})));assert.equal(await page.locator('.dv-sb tbody tr').count(),count);
  await ta.evaluate(t=>{t.setSelectionRange(0,t.value.length);const d=new DataTransfer();d.setData('text/plain','第一行\n\n第二行');t.dispatchEvent(new ClipboardEvent('paste',{clipboardData:d,bubbles:true,cancelable:true}));});assert.equal(await page.locator('.dv-sb tbody tr').count(),count+1);
  await page.locator('[data-adjust]').fill('强调色换成暖黄');await page.locator('[data-mode="new"]').click();assert(await page.locator('[data-draft]').isDisabled());assert(await page.locator('[data-generate]').isDisabled());
  await page.locator('[data-desc]').fill('浅底');await page.locator('[data-hint="强调色"]').click();assert.equal(await page.locator('[data-desc]').inputValue(),'浅底\n强调色：');await page.locator('[data-mode="base"]').click();assert.equal(await page.locator('[data-adjust]').inputValue(),'强调色换成暖黄');await page.locator('[data-mode="new"]').click();assert.equal(await page.locator('[data-desc]').inputValue(),'浅底\n强调色：');
  await page.locator('[data-draft]').click();await page.locator('[data-accept]').waitFor();assert(await page.locator('[data-generate]').isDisabled());assert((await page.locator('.dv-genbar').textContent()).includes('风格还没定好'));
  await page.locator('[data-revise]').fill('主色再深一点');await page.locator('[data-revise-go]').click();await page.locator('[data-accept]').waitFor();assert.equal(mock.revisions.at(-1).instruction,'主色再深一点');await page.locator('[data-accept]').click();assert(await page.locator('[data-generate]').isEnabled());await page.locator('[data-generate]').click();await page.locator('.dv-film').waitFor();assert.equal(mock.creates.at(-1).styleBase.kind,'draft');assert(!Object.hasOwn(mock.creates.at(-1),'script'));await page.close();
  x=await h.open('first-empty');({page,mock}=x);const chooser=page.waitForEvent('filechooser');await page.locator('[data-import]').click();const imported={shots:[{dialogue:'导入台词',visual:'图解',subtitle:'关键词',camera:'近景',audio:'鼓点'},{dialogue:'   '}]};await(await chooser).setFiles({name:'storyboard.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(imported))});await page.locator('.dv-sb').waitFor();for(const [f,value] of Object.entries(imported.shots[0]))assert.equal(await page.locator(`[data-f="${f}"]`).first().inputValue(),value);mock.setCreateFailure(true);await page.locator('[data-generate]').click();await page.locator('[data-message] .attention').waitFor();assert.equal(await page.locator('[data-f=dialogue]').first().inputValue(),'导入台词');mock.setCreateFailure(false);await page.locator('[data-generate]').click();await page.locator('.dv-film').waitFor();assert.deepEqual(mock.creates.at(-1).storyboard,{shots:[{shotId:'01',...imported.shots[0]}]});assert.equal(mock.creates.at(-1).styleBase.kind,'job');await page.close();
  for(const [state,reason] of [['writing','写完才能改'],['composing','合成完才能改']]){({page}=await h.open(state));assert.equal(await page.locator('[data-rescript]').count(),0);assert.equal(await page.locator('.dv-step-lock').textContent(),reason);await page.close();}
  ({page}=await h.open('first-none'));assert(await page.locator('[data-mode="base"]').isEnabled());assert.equal(await page.locator('[data-mode="base"]').getAttribute('aria-checked'),'true');assert.equal(await page.locator('[data-style-card][aria-pressed="true"]').count(),0);await page.close();
  ({page}=await h.open('rescript'));await h.testZoomAndClips(page);await page.close();
  ({page,mock}=await h.open('entry',1440,{omitCurrentStyle:true}));await page.locator('[data-rescript]').click();await page.locator('.dv-sw-card').first().waitFor();assert(await page.locator('[data-generate]').isEnabled());await page.locator('[data-generate]').click();await page.locator('.dv-film').waitFor();assert.equal(mock.creates.at(-1).styleBase.jobId,mock.initial.job.jobId);await page.close();
  ({page,mock}=await h.open('first-new-drafting'));
  await page.clock.pauseAt(new Date(await page.evaluate(()=>Date.now()+1000)));
  const polls=mock.draftReads,nextPoll=page.waitForResponse(r=>r.request().method()==='GET'&&r.url().includes('/style-drafts/'));
  await page.clock.fastForward(2100);await nextPoll;
  const expectedClock=await page.evaluate(()=>{const n=Math.round((Date.now()-Date.parse('2026-10-26T01:10:00+08:00'))/1000);return `已用 ${Math.floor(n/60)}:${String(n%60).padStart(2,'0')}`;});
  await page.waitForFunction(expected=>document.querySelector('[data-draft-clock]')?.textContent===expected,expectedClock);assert(mock.draftReads>polls);await page.evaluate(()=>{location.hash='view=projects';});await page.locator('[data-design-id="R208-PROJECTS"]').first().waitFor();const stopped=mock.draftReads;await page.clock.fastForward(61000);assert.equal(mock.draftReads,stopped);await page.close();
  console.log('PASS R278 mounted Studio: entry/back, editor keys/IME/paste/import, styles, samples/revise/accept and jobs');
}
export async function testLegacyContracts(){
  const {readFileSync}=await import('node:fs');
  const read=path=>JSON.parse(readFileSync(new URL(path,import.meta.url),'utf8'));
  const combined=composeLegacyContract(read('../docs/tasks/R276-direct-video-opus/design/contract.json'),read('../docs/tasks/R278-direct-rescript/design/contract.json'),state=>read(`./fixtures/r276-direct/${state}.json`));
  for(const state of ['filled','unavailable']){
    assert(combined.states[state].copy.includes('Opus 先按你写的改全片设计'),`${state} must include the approved adjusted-style explanation`);
    assert(combined.states[state].ids.includes('DV-STYLE-LIB'));assert(combined.states[state].copy.includes('风格库'));
    assert(combined.states[state].copy.includes('浅米色底'),`${state} must include the approved new-style example`);
  }
  const r277=read('../docs/tasks/R277-shot-visual-revision/design/contract.json'),r278=read('../docs/tasks/R278-direct-rescript/design/contract.json');
  for(const [name,state] of [['review','review'],['look-running','review'],['no-boxes-look-running','review'],['verify-running','compare'],['rewriting2','rewriting2']]){
    const payload=read(`./fixtures/r277-revise/${name}.json`);
    if(name==='rewriting2'){payload.job.status='writing';payload.job.shots[1].status='writing';}
    const resolved=composeLegacyContract({...r277,states:{[state]:structuredClone(r277.states[state])}},r278,()=>payload).states[state];
    const unlocked=view.canRescript(payload.job,false);
    assert(resolved.ids.includes(unlocked?'DV-RESCRIPT-ENTRY':'DV-RESCRIPT-LOCKED'),name);
    assert(!resolved.ids.includes(unlocked?'DV-RESCRIPT-LOCKED':'DV-RESCRIPT-ENTRY'),name);
  }
  console.log('PASS R276 approved block composition + R277 current-projection step locks');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){testFormulas();await testLegacyContracts();}
