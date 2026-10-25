import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import { pathToFileURL } from 'node:url';
import {splitScript,shotSeconds,totalSeconds,writtenCount,elapsed,writtenSeconds,mmss,shouldPoll,failureMessage,FAILURE_COPY,defaultShot,shotStart,safeText,posterUrl,writingSeconds,canRewrite} from '../studio/static/direct-view.js';

// Build the endpoint-shaped fixtures stored in tests/fixtures/r276-direct/.
export function fixture(state,source) {
  if(['empty','filled','unavailable','read-error'].includes(state))return {ok:true,job:null};
  const now=Date.now(),createdAt=new Date(now-680000).toISOString();
  const shots=source.map((s,i)=>({shotId:String(i+1).padStart(2,'0'),dialogue:s.dialogue,mainAction:['「91%」大字落地','两根柱子一高一低','方格逐个亮起再褪去','进度条停在「够好 · 发」','习惯曲线断一下又接上','三个节点转成一个圈','两条横条一长一短'][i],estimatedSeconds:shotSeconds(s),measuredSeconds:['composing','done'].includes(state)?s.D:null,timingSource:['composing','done'].includes(state)?'narration':'estimate',status:'rendered',failureCode:null,attempts:i===5?2:1,lastInstruction:null,writingStartedAt:new Date(Date.parse(createdAt)+100000).toISOString(),writtenAt:new Date(Date.parse(createdAt)+[221,245,322,510,552,647,680][i]*1000).toISOString(),renderedAt:new Date(now).toISOString(),codeChars:s.html?.length||1500,posterRevision:1,checks:{errors:[],warnings:i===1?[{code:'number_unspoken',message:'画面上的「50%」口播里写的是「约一半」'}]:i===5?[{code:'stagnant',message:'3.2–6.6 秒画面没有变化，停了 3.4 秒'}]:[]}}));
  const done=state.startsWith('done'),composing=state.startsWith('composing');
  const job={jobId:'dv_frontend_fixture',projectId:'fixture-piece',model:'claude-opus-5-5',status:done?'done':composing?'composing':({designing:'designing',writing:'writing','failed-shot':'failed',rewriting:'writing'})[state]||'ready',createdAt,updatedAt:new Date(now).toISOString(),failureCode:null,design:{status:'done',palette:{background:'#F3F0E8',primary:'#1E5E6A',accent:'#D8552A',neutral:'#52616A'},typeScale:[84,52,44],motionRules:'一镜一个主动作，图解跟着口播一步步长出来',banned:['光晕霓虹','紫蓝渐变','三张卡片并排','全部同时淡入']},shots,narration:{status:['composing','done'].includes(state)?'ready':'none',durationSeconds:['composing','done'].includes(state)?totalSeconds(shots):null},output:{status:done?'ready':composing?'composing':'none',composedAt:done?new Date(now).toISOString():null,kind:['done','composing'].includes(state)?'narrated':'silent',durationSeconds:done?totalSeconds(shots):null,frames:done?Math.round(totalSeconds(shots)*30):null,revision:done?1:0,checks:{playable:done?'pass':'unknown',avOffsetSeconds:state==='done'?.01:null,blackFrames:done?'pass':null}}};
  if(state==='ready')shots[0].checks.warnings.push({code:'layout_bottom_gap',message:'画面下半截空着：主画面只占到 y=900，离字幕带还空 46.2%'});
  if(state==='designing'){job.design={status:'writing',palette:null,typeScale:null,motionRules:null,banned:[]};shots.forEach(s=>Object.assign(s,{status:'queued',attempts:0,codeChars:0,posterRevision:0,writingStartedAt:null,writtenAt:null,renderedAt:null,checks:{errors:[],warnings:[]}}));}
  if(state==='writing')shots.slice(3).forEach((s,i)=>Object.assign(s,{status:i===3?'queued':'writing',writingStartedAt:i===3?null:new Date(now-(72-i*20)*1000).toISOString(),attempts:i===2?2:i===3?0:1,posterRevision:i===2?1:0,writtenAt:null,renderedAt:null}));
  if(state==='failed-shot'){job.failureCode='lint_failed_after_retry';Object.assign(shots[4],{status:'failed',failureCode:'lint_failed_after_retry',posterRevision:0,attempts:2,writtenAt:null,renderedAt:null,checks:{errors:[{code:'subtitle_band',message:'字放进了字幕带：画面最下面五分之一要留给烧录字幕'}],warnings:[]}});}
  if(state==='rewriting')Object.assign(shots[2],{status:'writing',writingStartedAt:new Date(now-51000).toISOString(),attempts:1,lastInstruction:'数字再大一点'});
  return {ok:true,job};
}
// Execute the actual header branches so these assertions guard the rendered copy.
export function testCompositionHeader(){
  const view=readFileSync(new URL('../studio/static/direct-view.js',import.meta.url),'utf8');
  const positive=JSON.parse(readFileSync(new URL('./fixtures/r276-direct/done.json',import.meta.url),'utf8')).job;
  const negative=JSON.parse(readFileSync(new URL('./fixtures/r276-direct/done-no-composed-time.json',import.meta.url),'utf8')).job;
  for(const state of ['done','done-silent']){
    const branch=view.split('\n').find(line=>line.includes(`else if(st==='${state}')`)).trim().replace(/^else /,'');
    const render=job=>runInNewContext(`let title='',lede='',actions='';${branch};lede`,{st:state,job,D:x=>x,mmss,elapsed,btn:()=>''});
    assert.match(render(positive),/从点「生成」到出片用了 3:41。/);
    assert(!render(positive).includes('135:17'));
    assert(!render(negative).includes('从点「生成」到出片用了'));
    assert(!render(negative).includes('135:17'));
  }
}
export function testFormulas(){
  testCompositionHeader();
  assert.deepEqual(splitScript('  第一镜。\r\n\n 第二镜！ \n  '),['第一镜。','第二镜！']);
  assert.equal(shotSeconds({dialogue:'你好吗？'}),.8);
  assert.equal(shotSeconds({dialogue:'😀'}),.2);
  assert.equal(shotSeconds({dialogue:'长口播',estimatedSeconds:999,measuredSeconds:2.75}),2.75);
  assert.equal(shotSeconds({dialogue:'长口播',measuredSeconds:0}),0);
  assert.equal(shotSeconds({dialogue:'长口播',measuredSeconds:NaN}),.6);
  assert.equal(mmss(totalSeconds([{dialogue:'一',measuredSeconds:29.8},{dialogue:'二',measuredSeconds:30.8}])),'1:01');
  const statuses=['queued','writing','written','rendering','rendered','failed','interrupted'];
  assert.equal(writtenCount(statuses.map(status=>({status}))),3);
  assert.equal(elapsed('2026-10-26T00:00:00Z',Date.parse('2026-10-26T00:01:12Z')),72);
  assert.equal(writtenSeconds({createdAt:'2026-10-26T00:00:00Z'},{writtenAt:'2026-10-26T00:03:41Z'}),221);
  assert.equal(writingSeconds({writingStartedAt:'2026-10-26T00:00:00Z'},Date.parse('2026-10-26T00:01:12Z')),72);
  assert.equal(writingSeconds({writingStartedAt:null}),null);
  for(const status of ['failed','interrupted']){assert(canRewrite({status},''));assert(canRewrite({status},'  '));assert(canRewrite({status},'改大'));assert(!canRewrite({status},'字'.repeat(201)));}
  for(const status of ['rendered','written','writing','rendering','queued']){assert(!canRewrite({status},''));assert(!canRewrite({status},'  '));assert(canRewrite({status},'字'.repeat(200)));assert(!canRewrite({status},'字'.repeat(201)));}
  assert.equal(elapsed(null),0);assert.equal(mmss(NaN),'0:00');
  for(const status of ['ready','done','failed']) {
    assert.equal(shouldPoll({status,shots:[],output:{status:'none'}}),false);
    for(const s of ['writing','rendering'])assert.equal(shouldPoll({status,shots:[{status:s}],output:{status:'none'}}),true);
    assert.equal(shouldPoll({status,shots:[],output:{status:'composing'}}),true);
  }
  assert.equal(shouldPoll({status:'writing',shots:[],output:{status:'none'}}),true);
  assert.equal(shouldPoll(null),false);
  const expectedFailures={claude_cli_unavailable:'本机的 Claude 调不通，现在用不了 Opus',model_timeout:'Opus 这一镜写了太久没写完，可以重试',code_invalid:'Opus 写出来的不是一段完整的动画代码，可以重试',lint_failed_after_retry:'写了两次都没过自查（下面写卡在哪条）',render_failed:'这一镜没渲染出来，可以只重试这一镜',narration_invalid:'配音文件读不出来，换一个 WAV 再传'};
  for(const [code,text] of Object.entries(expectedFailures))assert.equal(failureMessage(code),text);
  for(const [code,text] of Object.entries(FAILURE_COPY)){assert.equal(failureMessage(code),text);assert.match(text,/[\u4e00-\u9fff]/);assert(!text.includes(code));}
  for(const code of ['unregistered_code',null,undefined])assert.equal(failureMessage(code),'读不到这一镜的状态，点重试');
  assert.equal(defaultShot([{shotId:'01',status:'rendered'},{shotId:'02',status:'writing',lastInstruction:'重写'},{shotId:'03',status:'failed'}]),'03');
  assert.equal(defaultShot([{shotId:'01',status:'rendered'},{shotId:'02',status:'writing',attempts:2}]),'02');
  assert.equal(shotStart([{measuredSeconds:2.4},{measuredSeconds:3.6}],2),6);
  assert.equal(posterUrl('p',{jobId:'j'},{shotId:'03',posterRevision:8}),'/api/projects/p/direct/jobs/j/shots/03/poster.jpg?v=8');
  assert(!safeText('render_failed /private/tmp/example/file').includes('render_failed'));
  console.log('PASS R276: split, Unicode, measured/estimated duration, totals, counts, elapsed/written time, polling, failures, selection, jumps, cache URLs');
}
export async function testDetail(page,job){
  const result=await page.evaluate(async job=>{
    const {renderShotDetail}=await import('/direct-shot-detail.js');
    const container=document.createElement('div');document.body.append(container);
    const options={job,shot:job.shots[0],projectId:job.projectId,api:async()=>({csrfToken:'test'}),onRewrite:()=>{}};
    renderShotDetail(container,options);let input=container.querySelector('input');input.value='保留意见';input.dispatchEvent(new Event('input'));input.focus();input.setSelectionRange(2,3);
    renderShotDetail(container,{...options,job:structuredClone(job),shot:structuredClone(options.shot)});const same=input===container.querySelector('input');
    const next={...options,job:structuredClone(job),shot:structuredClone(options.shot)};next.shot.posterRevision++;renderShotDetail(container,next);input=container.querySelector('input');
    const preserved=input.value==='保留意见'&&document.activeElement===input&&input.selectionStart===2&&input.selectionEnd===3;
    const other={...next,shot:job.shots[1]};renderShotDetail(container,other);renderShotDetail(container,next);const restored=container.querySelector('input').value==='保留意见';
    const block={...next,shot:{...next.shot,status:'writing'}};renderShotDetail(container,block);const disabled=container.querySelector('input').disabled&&container.querySelector('[data-rewrite]').disabled;
    const matrix=[];
    for(const status of ['failed','interrupted','rendered']){
      renderShotDetail(container,{...next,shot:{...next.shot,status}});const box=container.querySelector('input');box.value='';box.dispatchEvent(new Event('input'));
      matrix.push({status,emptyEnabled:!container.querySelector('[data-rewrite]').disabled,label:container.querySelector('[data-rewrite]').textContent});
      box.value='数字再大一点';box.dispatchEvent(new Event('input'));if(container.querySelector('[data-rewrite]').disabled)throw new Error('valid instruction disabled');
      if(container.querySelector('[data-rewrite]').textContent!=='让 Opus 重写这一镜')throw new Error('rewrite label mismatch');
    }
    container.remove();return {same,preserved,restored,disabled,matrix,exports:Object.keys(await import('/direct-shot-detail.js'))};
  },job);
  assert.deepEqual(result,{same:true,preserved:true,restored:true,disabled:true,matrix:[{status:'failed',emptyEnabled:true,label:'重试这一镜'},{status:'interrupted',emptyEnabled:true,label:'重试这一镜'},{status:'rendered',emptyEnabled:false,label:'让 Opus 重写这一镜'}],exports:['renderShotDetail']});
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href)testFormulas();
