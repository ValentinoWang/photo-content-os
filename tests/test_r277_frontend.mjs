import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';

export function testFixtures(){
  const read=name=>JSON.parse(readFileSync(new URL(`./fixtures/r277-revise/${name}.json`,import.meta.url)));
  for(const name of ['review','select','picked','rewriting2','compare','kept-prev','saved','review-failed','log','look-running','no-boxes','no-boxes-look-running','verify-running','verify-missed','verify-failed','log-empty','proposal-running']){
    const value=read(name);assert(value.ok);assert.equal(value.job.shots.length,7);for(const shot of value.job.shots)for(const version of shot.versions)assert(Object.hasOwn(version,'baseVersion'));
  }
  const legacyLooking=read('no-boxes-look-running').job.shots[1];assert.deepEqual(legacyLooking.boxes,[]);assert.equal(legacyLooking.look.status,'running');
  const current=read('compare').job.shots[1];assert.equal(current.versions[1].baseVersion,1);assert.equal(current.currentVersion,2);
  assert.equal(current.versions[1].request.lines.reduce((n,l)=>n+Array.from(l.text).length,0),85);
  assert.equal(read('kept-prev').job.shots[1].versions.length,2);
  console.log('PASS R277 fixtures: 17 states, baseVersion lineage, 85-character brief, retained versions');
}

export async function testRevisionDetail(page,job){
  const result=await page.evaluate(async job=>{
    const {renderShotDetail}=await import('/direct-shot-detail.js');
    const container=document.createElement('div');document.body.append(container);
    const requests=[],originalFetch=window.fetch;let failure=null;
    window.fetch=async(url,options={})=>{requests.push({url,method:options.method,body:options.body?JSON.parse(options.body):null,token:options.headers?.['X-Content-OS-CSRF']});return {ok:!failure,json:async()=>failure?{ok:false,error:{code:failure}}:{ok:true,job:structuredClone(job)},text:async()=>'<html>code</html>'};};
    let currentShot=structuredClone(job.shots[1]);
    const render=shot=>{currentShot=structuredClone(shot);renderShotDetail(container,{job,shot:currentShot,projectId:job.projectId,api:async()=>({csrfToken:'fixture-csrf'}),onRewrite:()=>{}});};
    const click=selector=>{const el=container.querySelector(selector);if(!el)throw new Error(`missing ${selector}`);el.click();};
    const input=value=>{const el=container.querySelector('[data-extra]');el.value=value;el.dispatchEvent(new Event('input'));return el;};
    const snapshot=()=>({pick:container.querySelector('.rv-hs.on')?.dataset.box,selected:[...container.querySelectorAll('[data-act][aria-pressed="true"],[data-whole][aria-pressed="true"]')].map(e=>e.dataset.act||e.dataset.whole),text:container.querySelector('[data-extra]')?.value,brief:container.querySelector('[data-items]')?.textContent});
    try{
      render(currentShot);click('[data-box="b2"]');click('[data-act="dim"]');click('[data-whole="color"]');let box=input('底色😀不动');box.focus();box.setSelectionRange(1,3);container.querySelector('[data-design-id="DV-SAY"]').open=true;const before=snapshot();
      render(currentShot);const same=box===container.querySelector('[data-extra]');render({...currentShot,posterRevision:9});box=container.querySelector('[data-extra]');const preserved=JSON.stringify(before)===JSON.stringify(snapshot())&&document.activeElement===box&&box.selectionStart===1&&box.selectionEnd===3&&container.querySelector('[data-design-id="DV-SAY"]').open;
      const pollChanges=[{checks:{errors:[],warnings:[{code:'layout_bottom_gap',message:'画面下半截空着'}]}},{attempts:9},{look:{status:'done',findings:[{boxId:'b2',kind:'主次',text:'仍然太大',suggest:'dim'}]}},{boxes:currentShot.boxes.map(b=>({...b,y:b.y+1}))},{sample:true},{versions:[...currentShot.versions,{version:2,baseVersion:1,posterRevision:2,verify:{status:'running'}}]}];
      const pollPreserved=pollChanges.every(change=>{render({...currentShot,...change});const el=container.querySelector('[data-extra]');return snapshot().text===before.text&&snapshot().pick===before.pick&&document.activeElement===el&&el.selectionStart===1&&el.selectionEnd===3&&container.querySelector('[data-design-id="DV-SAY"]').open;});
      const retainedShot=currentShot;render(job.shots[0]);render(retainedShot);const restored=JSON.stringify(before)===JSON.stringify(snapshot());
      const coords=container.querySelector('[data-box="b2"]');const coordinate={left:parseFloat(coords.style.left)*360/100,top:parseFloat(coords.style.top)*640/100,width:parseFloat(coords.style.width)*360/100};
      const count=container.querySelector('.rv-count').textContent;input('字'.repeat(201));const over=container.querySelector('[data-revise]').disabled&&container.querySelector('.rv-count').classList.contains('over');input('字'.repeat(200));const combinedOver=container.querySelector('[data-revise]').disabled;
      // Clear selected items through the same controls, then exercise Unicode and limits.
      while(container.querySelector('[data-drop]'))click('[data-drop]');input('😀'.repeat(200));const unicode200=container.querySelector('.rv-count').textContent==='200 / 200 字'&&!container.querySelector('[data-revise]').disabled;
      const acceptedShot=structuredClone(job.shots[1]);acceptedShot.versions.push({version:4,baseVersion:1,posterRevision:4,request:{lines:[{text:'底色不动',own:true},{text:'缩小',boxId:'b2',action:'dim'}]},verify:{status:'done',items:[{index:0,result:'done'},{index:1,result:'missed',reason:'仍然太大'}]}});acceptedShot.currentVersion=4;
      render(acceptedShot);const compare=!!container.querySelector('[data-design-id="RV-COMPARE"]')&&container.querySelectorAll('.rv-num.ok').length===3&&container.querySelector('img').src.endsWith('poster.jpg?version=1')&&container.textContent.includes('仍然太大');
      click('[data-keep]');const kept=!container.querySelector('[data-design-id="RV-COMPARE"]');
      render({...acceptedShot,currentVersion:1});const reverted=container.querySelector('[data-design-id="RV-CHANGED"]')?.textContent.includes('第 4 版留着');
      render({...acceptedShot,currentVersion:2});const nonLatest=!container.querySelector('[data-design-id="RV-COMPARE"]')&&!container.querySelector('[data-design-id="RV-CHANGED"]');
      const noBase=structuredClone(acceptedShot);noBase.currentVersion=5;noBase.versions.push({version:5,baseVersion:null,request:{lines:[{text:'改',own:true}]}});render(noBase);const requiresBase=!container.querySelector('[data-design-id="RV-COMPARE"]');
      const looking={...job.shots[1],boxes:[],look:{status:'running',failureCode:null,findings:[]}};
      const isLooking=()=>container.querySelector('[data-design-id="RV-INSPECT"]').textContent==='Opus 正在看这一镜的画面'&&!container.querySelector('[data-look]')&&!container.querySelector('.rv-pin');
      render(looking);const lookWithoutBoxes=isLooking();render({...looking,boxes:job.shots[1].boxes});const lookWithBoxes=isLooking();
      render({...looking,look:{status:'done',failureCode:null,findings:[]}});const lookFinished=container.querySelector('[data-look]')?.textContent==='让 Opus 看一遍'&&container.querySelector('[data-design-id="RV-INSPECT"] h4')?.textContent==='这一镜还没有可以点的块';
      const busy={...job.shots[1],status:'writing',writingStartedAt:'2026-10-26T01:00:00Z'};render(busy);const busyDisabled=[...container.querySelectorAll('.rv-side button,.rv-side input')].every(e=>e.disabled);const genericBusy=container.querySelector('[data-busy-clock]').textContent.startsWith('正在重写这一镜');
      render({...busy,posterRevision:2,writingStartedAt:null});const noClock=!container.querySelector('[data-busy-clock]').textContent.includes(' · ');
      const errors={};
      for(const code of ['instruction_too_long','version_not_found','sample_not_found','proposal_not_found','proposal_not_ready','look_failed','verify_failed','unregistered_code']){
        render({...job.shots[1],posterRevision:Math.random()+10});failure=code;click('[data-sample]');await new Promise(r=>setTimeout(r,0));errors[code]=container.querySelector('[data-detail-error]').textContent;
      }
      failure=null;render({...job.shots[1],status:'failed',posterRevision:31});while(container.querySelector('[data-drop]'))click('[data-drop]');input('');click('[data-revise]');await new Promise(r=>setTimeout(r,0));const retry=requests.at(-1);
      render({...job.shots[1],status:'rendered',posterRevision:32});input('只改一点');click('[data-revise]');await new Promise(r=>setTimeout(r,0));const revise=requests.at(-1);
      return {same,preserved,pollPreserved,restored,coordinate,count,over,combinedOver,unicode200,compare,kept,reverted,nonLatest,requiresBase,busyDisabled,genericBusy,noClock,lookWithoutBoxes,lookWithBoxes,lookFinished,errors,retry,revise};
    }finally{window.fetch=originalFetch;container.remove();}
  },job);
  for(const key of ['same','preserved','pollPreserved','restored','over','combinedOver','unicode200','compare','kept','reverted','nonLatest','requiresBase','busyDisabled','genericBusy','noClock','lookWithoutBoxes','lookWithBoxes','lookFinished'])assert.equal(result[key],true,key);
  assert(Math.abs(result.coordinate.left-590/3)<.001);assert(Math.abs(result.coordinate.top-988/3)<.001);assert(Math.abs(result.coordinate.width-280/3)<.001);
  assert.equal(result.count,'51 / 200 字');
  const expected={instruction_too_long:'要改的超过 200 字了，删短一点再重写。',version_not_found:'这一版找不到了，刷新一下再选。',sample_not_found:'这个样例已经不在了，刷新一下。',proposal_not_found:'这条草稿已经处理过，刷新一下。',proposal_not_ready:'这条草稿已经处理过，刷新一下。',look_failed:'Opus 这次没看成画面：读不到渲染出的图。你照样可以自己点。',verify_failed:'Opus 这次没核对成，两版照样可以比。',unregistered_code:'读不到这一镜的状态，点重试'};
  assert.deepEqual(result.errors,expected);assert(result.retry.url.endsWith('/rewrite'));assert.deepEqual(result.retry.body,{instruction:''});assert.equal(result.retry.token,'fixture-csrf');assert(result.revise.url.endsWith('/revise'));assert.deepEqual(result.revise.body,{lines:[{text:'只改一点',own:true}]});
  console.log('PASS R277 browser detail: formulas, coordinates, selection/input/focus/disclosures, version conditions, retries, failures');
}

export async function testRevisionLog(page){
  const result=await page.evaluate(async()=>{
    const {renderRevisionLog}=await import('/direct-revision-log.js');const container=document.createElement('div');document.body.append(container);
    const category=(name,count,status=null,throughCount=0)=>({category:name,count,sources:[{projectId:'p',projectTitle:'作品标题',shotId:'05'},{projectId:'p',projectTitle:'作品标题',shotId:'02'},{projectId:'p',projectTitle:'作品标题',shotId:'05'}],proposals:status?[{proposalId:name,throughCount,status,text:'规则原文'}]:[]});
    const data={ok:true,rulesRevision:7,categories:[category('零',0),category('一',1),category('二',2),category('三',4,'adopted',3),category('四',3,'adopted',3),category('五',6,'failed',6),category('六',7,'running',6),category('七',8,'pending',6)]};
    renderRevisionLog(container,{api:async path=>path.endsWith('revision-log')?data:{ok:true,samples:[{projectTitle:'一二三四五六七八九，尾巴',shotId:'09',savedAt:'2026-10-26T01:00:00Z',posterUrl:'/api/direct/samples?poster=sample_01'}]},onBack:()=>{}});await new Promise(r=>setTimeout(r,0));
    const rows=[...container.querySelectorAll('tbody tr')].map(r=>[...r.children].map(c=>c.textContent));const text=container.textContent;container.remove();return {rows,text};
  });
  assert.deepEqual(result.rows.map(r=>r[0]),['七','六','五','三','四','二','一']);
  const now=Object.fromEntries(result.rows.map(r=>[r[0],r[3]]));assert(now['七'].startsWith('建议写进规则'));assert.equal(now['六'],'正在起草规则');assert.equal(now['五'],'这次没起草成，再攒 3 次会重新起草。');assert.equal(now['三'],'记着');assert.equal(now['四'],'已写进规则');assert.equal(now['二'],'再有 1 次会起草规则');assert.equal(now['一'],'记着');
  assert.equal(result.rows[0][2],'作品标题 · 02、05');assert(result.text.includes('画面规则第 7 版 → 第 8 版'));assert(result.text.includes('依据：这 6 次你都点了「七」类改法。'));assert(result.text.includes('一二三四五六七八 · 第 09 镜'));assert(result.text.includes('10月26日存'));
  console.log('PASS R277 log: count sort/filter, source dedup/order, threshold since throughCount, rule revisions and sample labels');
}
export async function testPollingOwnership(page,job){
  await page.evaluate(async job=>{
    const {renderShotDetail}=await import('/direct-shot-detail.js');window.r277Polling={ready:0,writing:0};
    for(const status of ['ready','writing']){const container=document.createElement('div');container.dataset.pollTest=status;document.body.append(container);const copy=structuredClone(job);copy.status=status;const shot=copy.shots[1];shot.look={status:'running',findings:[]};renderShotDetail(container,{job:copy,shot,projectId:copy.projectId,api:async()=>({}),onRewrite:()=>{window.r277Polling[status]++;}});}
  },job);
  await page.clock.fastForward(2100);
  const result=await page.evaluate(()=>{const result=window.r277Polling;document.querySelectorAll('[data-poll-test]').forEach(e=>e.remove());delete window.r277Polling;return result;});
  assert.deepEqual(result,{ready:1,writing:0});console.log('PASS R277 polling ownership: detail polls only after the outer job poll has stopped');
}

export async function testLookRunningState(page){
  const state=await page.locator('[data-design-id="RV-INSPECT"]').evaluate(e=>({text:e.textContent,lookButtons:e.querySelectorAll('[data-look]').length}));
  assert.equal(state.text,'Opus 正在看这一镜的画面');assert.equal(state.lookButtons,0);assert.equal(await page.locator('.rv-pin').count(),0);
  return state;
}
export async function testB2Layout(page,{name,width}){
  const metrics=await page.evaluate(()=>{
    const rect=e=>e?.getBoundingClientRect().toJSON(),inspector=document.querySelector('[data-design-id="RV-INSPECT"]'),look=inspector?.querySelector('[data-look]'),heading=inspector?.querySelector('h4'),log=document.querySelector('.rv-log-page .stephead'),lede=log?.querySelector('.rv-log-lede'),comparison=document.querySelector('.rv-detail.cmp');
    return {
      noBoxes:look?.classList.contains('btn--sm')?{title:heading.textContent,heading:rect(heading),button:rect(look),buttonClass:look.className,text:inspector.textContent}:null,
      log:log?{lede:rect(lede),lineHeight:parseFloat(getComputedStyle(lede).lineHeight),title:rect(log.querySelector('h2')),back:rect(log.querySelector('[data-back]'))}:null,
      compare:comparison?{headCount:comparison.querySelectorAll('.rv-head').length,head:rect(comparison.querySelector('.rv-head')),pair:rect(comparison.querySelector('.rv-pair')),decide:rect(comparison.querySelector('.rv-decide')),changed:rect(comparison.querySelector('[data-design-id="RV-CHANGED"]')),more:rect(comparison.querySelector('.rv-more'))}:null
    };
  });
  if(name==='no-boxes'||name.startsWith('real-worst')){
    assert(metrics.noBoxes,`${name}/${width}: standalone look button missing`);
    const m=metrics.noBoxes;assert.equal(m.title,'这一镜还没有可以点的块');assert(!m.text.includes('在左边画面上点要改的地方'));assert(!m.buttonClass.includes('rv-link'));assert(m.button.top>=m.heading.bottom+5);assert(Math.abs(m.button.left-m.heading.left)<1);
  }
  if(metrics.log&&width>=960){const m=metrics.log;assert(m.lede.width>=600,`${name}/${width}: lede ${m.lede.width}px`);if(width===1440)assert(m.lede.height<=m.lineHeight+1,`${name}: desktop lede wrapped`);assert(Math.abs(m.title.bottom-m.back.bottom)<2);assert(m.back.right>m.title.right);assert(m.lede.top>=m.title.bottom);}
  if(metrics.compare){const m=metrics.compare;assert.equal(m.headCount,1);if(width<=1180){assert(m.head.bottom<=m.pair.top);assert(m.pair.bottom<=m.decide.top);assert(m.decide.bottom<=m.changed.top);assert(m.changed.bottom<=m.more.top);}else{assert(m.head.left>m.pair.right);assert(Math.abs(m.head.top-m.pair.top)<2);}}
  return {name,width,...metrics};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)testFixtures();

// Execute the renderer's own collector so fixture geometry cannot drift from the backend method.
export async function measureFixtureBoxes(page){
  const source=readFileSync(new URL('../scripts/video_render/render-frames.mjs',import.meta.url),'utf8');
  const needle='const boxes = await page.evaluate(',start=source.indexOf(needle)+needle.length,end=source.indexOf('\n      });',start);
  assert(start>=needle.length&&end>start,'renderer box collector not found; update R277 fixture measurement');
  return page.evaluate('('+source.slice(start,end)+'\n      })()');
}

export async function testMarkerGeometry(page,{required=false}={}){
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const rows=await page.locator('.rv-stage').evaluateAll(stages=>stages.flatMap((stage,stageIndex)=>{
    const rect=e=>e.getBoundingClientRect().toJSON(),hosts=[...stage.querySelectorAll('.rv-hs')],blocks=hosts.map((host,hostIndex)=>({hostIndex,boxId:host.dataset.box,...rect(host)}));
    return hosts.flatMap((host,hostIndex)=>[...host.querySelectorAll(':scope > .rv-num,:scope > .rv-pin')].sort((a,b)=>Number(b.matches('.rv-num'))-Number(a.matches('.rv-num'))).map(marker=>({stageIndex,hostIndex,boxId:host.dataset.box,kind:marker.classList.contains('rv-num')?'number':'pin',block:rect(host),blocks,stage:rect(stage),marker:rect(marker),fontSize:parseFloat(getComputedStyle(marker).fontSize),placement:marker.dataset.placement,mode:marker.dataset.placementMode})));
  }));
  if(required)assert(rows.length>0,'marker geometry check received no badges');
  const area=(a,b)=>Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
  const previous=new Map();
  for(const row of rows){
    const {marker:m,stage:s,block:b}=row,placed=previous.get(row.stageIndex)||[],size=s.width<=300.1?16:20;
    assert(Math.abs(m.width-size)<.1&&Math.abs(m.height-size)<.1,`${row.boxId}: badge must scale to ${size}px`);
    assert(Math.abs(row.fontSize-size*11.5/20)<.1,`${row.boxId}: badge font must scale`);
    assert(area(m,b)<.1,`${row.kind}/${row.boxId} covers its block`);
    assert(m.left>=s.left-.1&&m.top>=s.top-.1&&m.right<=s.right+.1&&m.bottom<=s.bottom+.1,`${row.kind}/${row.boxId} leaves the frame`);
    assert(placed.every(p=>area(m,p)<.1),`${row.boxId}: badges overlap within frame`);
    const rect=(left,top,side)=>({left,top,right:left+size,bottom:top+size,side}),number=row.kind==='number';
    const left=rect(b.left-2-size,b.top,'left'),right=rect(b.right+2,b.top,'right'),top=rect(number?b.left:b.right-size,b.top-2-size,'top'),bottom=rect(number?b.left:b.right-size,b.bottom+2,'bottom');
    const candidates=(number?[left,top,bottom,right]:[right,top,bottom,left]).filter(p=>p.left>=s.left-.01&&p.top>=s.top-.01&&p.right<=s.right+.01&&p.bottom<=s.bottom+.01&&area(p,b)<.1&&placed.every(other=>area(p,other)<.1));
    const scored=candidates.map(p=>({...p,overlap:row.blocks.filter(o=>o.hostIndex!==row.hostIndex).reduce((sum,o)=>sum+area(p,o),0)}));
    const expected=scored.find(p=>p.overlap<.1)||scored.reduce((best,p)=>!best||p.overlap<best.overlap-.01?p:best,null);
    assert(expected,`${row.boxId}: screenshot unexpectedly needs corner fallback`);
    row.otherOverlaps=row.blocks.filter(o=>o.hostIndex!==row.hostIndex&&area(m,o)>.1).map(o=>({boxId:o.boxId,area:area(m,o)}));
    row.overlapArea=row.otherOverlaps.reduce((sum,o)=>sum+o.area,0);
    assert.equal(row.placement,expected.side,`${row.boxId}: wrong candidate order/minimum`);
    assert(Math.abs(m.left-expected.left)<.1&&Math.abs(m.top-expected.top)<.1,`${row.boxId}: candidate gap/alignment differs`);
    if(row.otherOverlaps.length){assert.equal(row.mode,'minimum-overlap',`${row.boxId}: intersects other blocks without declared fallback`);assert(scored.every(p=>p.overlap>.1),`${row.boxId}: clear candidate exists`);assert(Math.abs(row.overlapArea-expected.overlap)<.1,`${row.boxId}: fallback is not minimum area`);}
    else assert.equal(row.mode,'clear',`${row.boxId}: unnecessary fallback`);
    placed.push(m);previous.set(row.stageIndex,placed);
  }
  return rows;
}

export async function testMarkerPlacementEdges(page,job){
  const cases=await page.evaluate(async job=>{
    const {renderShotDetail}=await import('/direct-shot-detail.js'),container=document.createElement('div');document.body.append(container);
    const tick=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))),result=[];
    const specs=[['number-left',90,90,90,60,'number','left'],['number-top',0,90,90,60,'number','top'],['number-bottom',0,0,90,60,'number','bottom'],['number-right',0,0,90,640,'number','right'],['pin-right',90,90,90,60,'pin','right'],['pin-top',270,90,90,60,'pin','top'],['pin-bottom',270,0,90,60,'pin','bottom'],['pin-left',270,0,90,640,'pin','left'],['corner',0,0,360,640,'number','corner']];
    try{
      for(const [name,x,y,w,h,kind,expected] of specs){
        const shot={...structuredClone(job.shots[1]),shotId:name,posterRevision:0,currentVersion:1,versions:[{version:1,baseVersion:null,request:null}],boxes:[{id:'edge',name:'边界块',x:x*3,y:y*3,w:w*3,h:h*3}],look:{status:'done',findings:kind==='pin'?[{boxId:'edge',kind:'主次',text:'边界检查',suggest:'dim'}]:[]}};
        renderShotDetail(container,{job,shot,projectId:job.projectId,api:async()=>({}),onRewrite:()=>{}});
        if(kind==='number'){container.querySelector('[data-box="edge"]').click();container.querySelector('[data-act="dim"]').click();}
        await tick();const marker=container.querySelector('.rv-stage .'+(kind==='number'?'rv-num':'rv-pin')),host=marker.parentElement,rect=e=>e.getBoundingClientRect().toJSON();
        result.push({name,expected,actual:marker.dataset.placement,marker:rect(marker),block:rect(host),stage:rect(host.closest('.rv-stage'))});
      }
      const shot={...structuredClone(job.shots[1]),shotId:'coexist',posterRevision:0,currentVersion:1,versions:[{version:1,baseVersion:null,request:null}],boxes:[{id:'both',name:'两个徽标',x:270,y:270,w:270,h:180}],look:{status:'done',findings:[]}};
      renderShotDetail(container,{job,shot,projectId:job.projectId,api:async()=>({}),onRewrite:()=>{}});container.querySelector('[data-box]').click();container.querySelector('[data-act="dim"]').click();
      // Exercise coexisting badges without changing the product's replacement rule.
      const pin=document.createElement('i');pin.className='rv-pin';pin.textContent='!';container.querySelector('.rv-hs').append(pin);const stage=container.querySelector('.rv-stage');stage.style.width='300px';await tick();
      result.push({name:'coexist-resized',stage:stage.getBoundingClientRect().toJSON(),markers:[...stage.querySelectorAll('.rv-num,.rv-pin')].map(e=>e.getBoundingClientRect().toJSON()),placements:[...stage.querySelectorAll('.rv-num,.rv-pin')].map(e=>e.dataset.placement)});
      return result;
    }finally{container.remove();}
  },job);
  const overlap=(a,b)=>Math.min(a.right,b.right)>Math.max(a.left,b.left)+.1&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top)+.1;
  for(const c of cases.filter(c=>c.name!=='coexist-resized')){assert.equal(c.actual,c.expected,c.name);if(c.expected==='corner'){assert(overlap(c.marker,c.block),'full-frame block must exercise the documented corner fallback');continue;}assert(!overlap(c.marker,c.block),c.name);const gap=c.actual==='left'?c.block.left-c.marker.right:c.actual==='right'?c.marker.left-c.block.right:c.actual==='top'?c.block.top-c.marker.bottom:c.marker.top-c.block.bottom;assert(Math.abs(gap-2)<.1,`${c.name}: gap ${gap}`);}
  const pair=cases.at(-1);assert.equal(pair.stage.width,300);assert.deepEqual(pair.placements,['left','right']);assert(pair.markers.every(m=>m.width===16&&m.height===16));assert(!overlap(...pair.markers));
  console.log('PASS R277 marker edges: ordered four directions, 2px gap, corner fallback, coexisting badges and resize');return cases;
}

export async function testMarkerAvoidance(page,job){
  const results=[];
  for(const name of ['other-block','minimum-area','earlier-badge']){
    await page.evaluate(async({job,name})=>{
      const {renderShotDetail}=await import('/direct-shot-detail.js'),container=document.createElement('div');container.dataset.markerAvoidance=name;document.body.append(container);
      const box=(id,x,y,w,h)=>({id,name:id,x:x*3,y:y*3,w:w*3,h:h*3});
      const boxes=name==='earlier-badge'?[box('pin',90,90,90,60),box('number',204,90,90,60)]:[box('number',90,90,90,60),box('left-blocker',68,90,20,20),...(name==='minimum-area'?[box('cover',0,0,360,640)]:[])];
      const shot={...structuredClone(job.shots[1]),shotId:name,posterRevision:0,currentVersion:1,versions:[{version:1,baseVersion:null,request:null}],boxes,look:{status:'done',findings:name==='earlier-badge'?[{boxId:'pin',kind:'主次',text:'待看',suggest:'dim'}]:[]}};
      renderShotDetail(container,{job,shot,projectId:job.projectId,api:async()=>({}),onRewrite:()=>{}});container.querySelector('[data-box="number"]').click();container.querySelector('[data-act="dim"]').click();
    },{job,name});
    try{
      const rows=await testMarkerGeometry(page,{required:true}),target=rows.find(r=>r.boxId==='number');assert.equal(target.placement,'top',name);assert.equal(target.mode,name==='minimum-area'?'minimum-overlap':'clear');results.push({name,placement:target.placement,mode:target.mode,otherOverlaps:target.otherOverlaps});
      if(name==='other-block'){
        await page.locator('[data-marker-avoidance] [data-box="number"] .rv-num').evaluate(e=>{e.style.left='-24px';e.style.top='-2px';e.dataset.placement='left';});
        await assert.rejects(()=>testMarkerGeometry(page),/wrong candidate|intersects other blocks/);results.push({name:'negative-neighbor-overlap',rejected:true});
      }
    }finally{await page.locator('[data-marker-avoidance]').evaluate(e=>e.remove());}
  }
  console.log('PASS R277 avoidance: neighboring blocks, minimum-area fallback, earlier badges, negative overlap');return results;
}
