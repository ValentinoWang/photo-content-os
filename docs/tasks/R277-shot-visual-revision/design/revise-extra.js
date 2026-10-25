// ---------- R277：选中一镜后改画面（本段由 build_revise.py 插进 R276 的稿） ----------
// 思路：在画面上直接点要改的地方。点哪块，右边就出这一块能做的改法；Opus 自己看出的问题用橙点标在画面上。
// 设计数据：热区位置、Opus 看出的问题、问题记录的次数和规则草稿、重写后的第 02 镜，都是按接口字段编的示意，不是实测。
let rv='review';
// 第 02 镜画面上能点的块（1080×1920 坐标，取自这一镜代码里各元素的位置）
const HS=[
  {id:'title',name:'标题',x:72,y:205,w:936,h:110},
  {id:'sub',name:'标题下的小字',x:72,y:325,w:936,h:72},
  {id:'ref',name:'「100%」虚线',x:114,y:598,w:856,h:56},
  {id:'big',name:'「约 50%」柱子',x:214,y:772,w:300,h:430},
  {id:'small',name:'「约 25%」柱子',x:580,y:886,w:300,h:316},
  {id:'take',name:'结论条',x:72,y:1256,w:936,h:136}];
// 重写后同一块在新画面上的位置（对比时标号用）
const HS_AFTER={big:{x:214,y:520,w:300,h:720},small:{x:580,y:836,w:300,h:404},sub:{x:72,y:330,w:936,h:40}};
const hsName=id=>(HS.find(h=>h.id===id)||{}).name;
// 点中一块后能做的改法 → 发给 Opus 的话（带数字，能对着画面检查）
const ACTS=[['main','做主角'],['dim','缩小变灰'],['del','删掉'],['short','字改短']];
const actText=(a,n)=>({main:`${n}做成这一镜唯一的主角：数字 150px 以上，柱子至少占画面高度的四分之一。`,dim:`${n}缩小一档、改成灰色，不和主角抢。`,del:`删掉${n}。`,short:`${n}只留关键词，不超过 8 个字。`})[a];
// 整镜的问题（不落在某一块上）
const WHOLE=[['space','太空或挤在上面','主画面放在页眉和字幕之间居中，下面空白不超过三成。'],['color','颜色乱','只用一个强调色，只标结论；其余用主色和灰。'],['sync','跟口播对不上','口播说到哪一部分，画面才出现哪一部分。']];
// Opus 看图自查：落在哪一块、说了什么、建议哪种改法
const LOOK={1:{small:{kind:'主次',text:'和「约 50%」一样大、一样醒目，看不出这一镜要记住哪个数。',rec:'dim'},sub:{kind:'字太多',text:'和字幕说的是同一句。这一屏一共有 7 处字。',rec:'del'},ref:{kind:'多余',text:'这一镜不用读刻度，多了一条线和一处字。',rec:'del'}}};
const LIMIT=200;
let pick='',items=[],extra='',rated=false,decided='',SENT=[];
const ORIG02=SHOTS[1].html;
// 重写后的第 02 镜（示意）：去掉小字和刻度，「约 50%」柱高 500px、大字 150px，「约 25%」变灰；两根柱子仍是 2:1
const AFTER02=ORIG02.replace('</style>','.sub{display:none}.main{top:330px!important;height:920px!important}#v1{font-size:150px}#v2,#l2{fill:#A7AFB2}#v2{font-size:60px}#b2{fill:#CFCBC2}.take{top:1290px!important}</style>')
  .replace('style="left:40px;top:180px" width="856" height="600" viewBox="0 0 856 600"','style="left:40px;top:190px" width="856" height="700" viewBox="0 0 856 700"')
  .replace('y1="500" x2="856" y2="500"','y1="640" x2="856" y2="640"')
  .replace('<line x1="0" y1="40"','<line visibility="hidden" x1="0" y1="40"').replace('<text x="0" y="28"','<text visibility="hidden" x="0" y="28"')
  .replace(/y="568"/g,'y="700"').replace('const H = 460','const H = 1000').replace(/500 - h/g,'640 - h');
const PRESET=[{k:'big',a:'main'},{k:'small',a:'dim'},{k:'sub',a:'del'}];
const itemText=it=>it.k.startsWith('whole:')?WHOLE.find(w=>'whole:'+w[0]===it.k)[2]:actText(it.a,hsName(it.k));
function rvReset(){
  pick='';items=[];extra='';rated=false;decided='';SENT=[];
  if(rv==='select')pick='small';
  if(['picked','rewriting2'].includes(rv)){pick=rv==='picked'?'small':'';items=PRESET.map(o=>({...o}));extra='底色不动';}
  if(['compare','kept-prev'].includes(rv)){SENT=[...PRESET.map(itemText),'底色不动'];}
  if(rv==='kept-prev')decided='old';
  if(rv==='saved')rated=true;
  SHOTS[1].html=rv==='compare'?AFTER02:ORIG02;
}
const lines=()=>[...items.map(itemText),...(extra.trim()?[extra.trim()]:[])];
const pct=(v,t)=>`${(v/t*100).toFixed(2)}%`;
const box=b=>`left:${pct(b.x,1080)};top:${pct(b.y,1920)};width:${pct(b.w,1080)};height:${pct(b.h,1920)}`;
// 一张可点的画面：热区 + 橙点（Opus 看出的）+ 青色标号（你要改的）
function stage(i,{click=true,look=true,nums=true,busy=false,after=false,html=null}={}){
  let f=ifr(i,frameOf(i));
  if(html)f=f.replace(esc(SHOTS[i].html.replace('</body>',bridge+'</body>')),esc(html.replace('</body>',bridge+'</body>')));
  const L=(look&&rv!=='review-failed'&&LOOK[i])||{};
  const spots=i===1?HS.map(h=>{
    const b=after?HS_AFTER[h.id]:h; if(!b)return '';
    const n=nums?items.findIndex(it=>it.k===h.id)+1:0, done=after?SENT_IDX[h.id]:0;
    const pin=L[h.id]&&!n?`<i class="rv-pin" aria-hidden="true">!</i>`:'';
    const num=n?`<b class="rv-num">${n}</b>`:done?`<b class="rv-num ok">${done}</b>`:'';
    if(!click)return (num||pin)?`<span class="rv-hs ro" style="${box(b)}">${pin}${num}</span>`:'';
    return `<button class="rv-hs ${pick===h.id?'on':''}" style="${box(b)}" data-hs="${h.id}" aria-label="选中${h.name}" aria-pressed="${pick===h.id}">${pin}${num}</button>`;
  }).join(''):'';
  const veil=busy?`<div class="rv-busy" data-design-id="RV-BUSY"><b>正在按 4 处改法重写</b><span>0:42 · 写好后和上一版并排给你看</span></div>`:'';
  return `<div class="rv-stage">${f}${spots}${veil}</div>`;
}
const SENT_IDX={big:1,small:2,sub:3};
function inspector(i,busy){
  const L=(rv!=='review-failed'&&LOOK[i])||{}, n=Object.keys(L).length;
  if(!pick){
    const lead=rv==='review-failed'
      ?`<p class="rv-warnline">Opus 这次没看成画面：读不到渲染出的图。你照样可以自己点。<button class="rv-link" data-toast="重新让 Opus 看这一镜">重试</button></p>`
      :n?`<p>画面上 <i class="rv-pin inline">!</i> 是 Opus 自己看出的 ${n} 处问题，点开看它怎么说。</p>`:`<p>Opus 看了这一镜，没看出要改的地方。</p>`;
    return `<section class="rv-insp empty" data-design-id="RV-INSPECT"><h4>${busy?'正在重写，先别点':'在左边画面上点要改的地方'}</h4>${busy?'':lead}</section>`;
  }
  const f=L[pick], cur=(items.find(it=>it.k===pick)||{}).a;
  return `<section class="rv-insp" data-design-id="RV-INSPECT"><header><small>选中</small><h4>${hsName(pick)}</h4><button class="rv-x" data-unpick aria-label="不选了">×</button></header>
    ${f?`<p class="rv-note"><b>Opus 看出 · ${f.kind}</b>${f.text}</p>`:''}
    <div class="rv-acts" role="group" aria-label="这一块怎么改">${ACTS.map(([a,label])=>`<button class="rv-act" data-act="${a}" aria-pressed="${cur===a}">${label}${f&&f.rec===a?'<em>建议</em>':''}</button>`).join('')}</div></section>`;
}
function changeList(busy){
  const ls=lines(),n=ls.join('').length,over=n>LIMIT;
  const li=items.map((it,k)=>`<li><b class="rv-num">${k+1}</b><p>${esc(itemText(it))}</p>${busy?'':`<button class="rv-x" data-drop="${k}" aria-label="去掉这一条">×</button>`}</li>`).join('');
  return `<section class="rv-list" data-design-id="RV-BRIEF"><header><h4>要改的</h4><span>${items.length?`${items.length} 处`:''}</span></header>
    ${items.length?`<ol>${li}</ol>`:`<p class="rv-empty">还没有。点画面上的一块，或者选下面整镜的问题。</p>`}
    <div class="rv-whole" data-design-id="RV-WHOLE"><small>整镜</small>${WHOLE.map(([k,label])=>`<button class="rv-chip" data-whole="${k}" aria-pressed="${items.some(it=>it.k==='whole:'+k)}" ${busy?'disabled':''}>${label}</button>`).join('')}</div>
    <input type="text" data-extra maxlength="${LIMIT}" placeholder="再补一句（可不填），例：底色不动" value="${esc(extra)}" ${busy?'disabled':''}>
    <footer><span class="rv-count ${over?'over':''}" aria-live="polite">${ls.length?`${n} / ${LIMIT} 字${over?' · 超了，去掉一两条':''}`:''}</span>${C.btn(busy?'正在重写 · 0:42':'重写这一镜',{pri:true,cls:'rv-go',disabled:busy||!ls.length||over})}</footer>
    <small class="rv-foot">只重写这一镜，其他六镜不动。</small></section>`;
}
function more(i,s){
  const warn=WARN[i]||[];
  return `<div class="rv-more"><details data-design-id="DV-SAY"><summary>口播<span>${esc(s.dialogue.slice(0,22))}…</span></summary><p>${esc(s.dialogue)}</p></details>
    <details data-design-id="DV-CHECKS"><summary>规则检查<span class="${warn.length?'w':''}">${warn.length?`${warn.length} 项要看`:'都过了'}</span></summary><ul>${warn.map(w=>`<li class="w">${w}</li>`).join('')}${['动画在这一镜时长内做完','页眉标好了','字幕带里没放字','不读网络和外部文件','不用定时器和随机数'].map(t=>`<li>${t}</li>`).join('')}</ul></details>
    <details data-design-id="DV-CODE"><summary>代码<span>${s.html.length.toLocaleString()} 字 · 上限 100,000</span></summary><pre>${esc(s.html)}</pre></details></div>`;
}
function detail2(){
  const i=sel,s=SHOTS[i],busy=rv==='rewriting2',cmp=rv==='compare'&&i===1&&!decided;
  const ver=i!==1?'第 1 版':busy?'第 1 版 · 正在写第 2 版':rv==='compare'?(decided==='old'?'用第 1 版 · 共 2 版':'第 2 版 · 共 2 版'):rv==='kept-prev'?'用第 1 版 · 共 2 版':'第 1 版';
  const head=`<header class="rv-head"><div><h3>第 ${s.shotId} 镜</h3><span data-design-data>按字数估 ${s.est.toFixed(1)} 秒 · ${ver}</span></div><button class="rv-rate" data-design-id="RV-RATE" aria-pressed="${rated}">${rated?'♥ 已存为样例':'♡ 这镜好'}</button></header>`;
  const scrub=`<div class="dv-scrub" data-design-id="DV-SCRUB"><button class="btn btn--sm" data-play aria-label="播放这一镜">▶</button><input type="range" min="0" max="${Math.round(dur(i)*FPS)}" value="${frameOf(i)}" data-scrub aria-label="拖到第几帧"><span data-readout>${(frameOf(i)/FPS).toFixed(1)} / ${dur(i).toFixed(1)} 秒</span></div>`;
  if(cmp){
    const done=SENT.map((t,k)=>`<li><b class="rv-num ok">${k+1}</b><p>${esc(t)}</p><em class="ok">做到了</em></li>`).join('');
    return `<section class="rv-detail cmp" data-design-id="DV-DETAIL"><div class="dv-pv" data-design-id="RV-COMPARE">
      <div class="rv-pair"><figure><figcaption>第 1 版</figcaption>${stage(1,{click:false,look:false,nums:false,html:ORIG02})}</figure>
      <figure class="new"><figcaption>第 2 版 · 按你的 4 处改法</figcaption>${stage(1,{click:false,look:false,nums:false,after:true})}</figure></div>
      <div class="rv-decide">${C.btn('退回第 1 版',{cls:'rv-old'})}${C.btn('用第 2 版',{pri:true,cls:'rv-new'})}</div></div>
      <div class="rv-side">${head}<section class="rv-list done" data-design-id="RV-CHANGED"><header><h4>这次改的</h4><span>Opus 对着新画面核过</span></header><ol>${done}</ol></section>${more(i,s)}</div></section>`;
  }
  const note=decided==='old'?`<p class="rv-back" data-design-id="RV-CHANGED">已退回第 1 版。第 2 版留着，你点的问题已经记下。</p>`:'';
  return `<section class="rv-detail" data-design-id="DV-DETAIL"><div class="dv-pv">${stage(i,{busy,after:i===1&&rv==='compare'&&decided==='new'})}${scrub}</div>
    <div class="rv-side">${head}${note}${inspector(i,busy)}${changeList(busy)}${more(i,s)}</div></section>`;
}
function logPage(){
  const prop=`<div class="rv-prop" data-design-id="RV-PROPOSAL"><small>起草的规则修改 · 画面规则第 3 版 → 第 4 版</small><p class="add">每一镜只有一个最大的元素：主角至少占画面高度的 40%，同一屏只有一个数字用最大字号，其余数字缩小、用灰色。</p><p class="why">依据：这 3 次你都点了「主次」类改法，其中 2 次是两个数字一样大。</p><div class="actions">${C.btn('采用',{pri:true,cls:'btn--sm',toast:'画面规则改成第 4 版，之后新写的镜按新规则'})}${C.btn('不用',{cls:'btn--sm',toast:'这条不写进规则；次数继续记着'})}<span>采用后，之后新写的镜按第 4 版；已经写好的镜不变。</span></div></div>`;
  const rows=[['主次不清','3','断更一年，我拆了四句话 · 02、05<br>P3 合成口播实践：平均速度 · 03',`<span class="hot">建议写进规则</span>${prop}`],['字太多','2','断更一年，我拆了四句话 · 02<br>P3 合成口播实践：平均速度 · 01','再有 1 次会起草规则'],['跟口播对不上','1','断更一年，我拆了四句话 · 06','记着']];
  return head('画面问题记录','你在各作品里改过的画面问题和存下的样例。同一种问题到 3 次，会起草一条画面规则给你看，点「采用」才生效。',C.btn('回到作品',{cls:'rv-back-btn'}))+
    `<div class="full" data-design-id="RV-LOG"><table class="rv-log"><thead><tr><th>问题</th><th>几次</th><th>出在哪几镜</th><th>现在</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r[0]}</td><td class="n" data-design-data>${r[1]}</td><td data-design-data>${r[2]}</td><td>${r[3]}</td></tr>`).join('')}</tbody></table>
    <div class="rv-sec" data-design-id="RV-SAMPLES"><h3>存下的样例 · <span data-design-data>2</span> 镜</h3><p>写新镜时，Opus 会参考和这一镜最像的两个样例。</p><div class="rv-samples">${[0,3].map(k=>`<figure><div class="dv-poster">${ifr(k,frameOf(k))}</div><figcaption data-design-data>断更一年 · 第 ${SHOTS[k].shotId} 镜<br>10月26日存</figcaption></figure>`).join('')}</div></div></div>`;
}
function bind2(){
  $$('[data-hs]').forEach(b=>b.onclick=()=>{pick=pick===b.dataset.hs?'':b.dataset.hs;render();});
  $$('[data-unpick]').forEach(b=>b.onclick=()=>{pick='';render();});
  $$('[data-act]').forEach(b=>b.onclick=()=>{const a=b.dataset.act,k=items.findIndex(it=>it.k===pick);
    if(k<0)items.push({k:pick,a});else if(items[k].a===a)items.splice(k,1);else items[k].a=a;render();});
  $$('[data-whole]').forEach(b=>b.onclick=()=>{const key='whole:'+b.dataset.whole,k=items.findIndex(it=>it.k===key);k<0?items.push({k:key}):items.splice(k,1);render();});
  $$('[data-drop]').forEach(b=>b.onclick=()=>{items.splice(+b.dataset.drop,1);render();});
  const ex=$('[data-extra]');ex&&ex.addEventListener('change',()=>{extra=ex.value;render();});
  const go2=k=>{const q=new URLSearchParams(location.hash.slice(1));q.set('s',k);location.hash=q.toString();};
  $$('.rv-go').forEach(b=>b.onclick=()=>{go2('rewriting2');setTimeout(()=>go2('compare'),1800);});
  $$('.rv-old').forEach(b=>b.onclick=()=>{decided='old';SHOTS[1].html=ORIG02;render();toast('已退回第 1 版');});
  $$('.rv-new').forEach(b=>b.onclick=()=>{decided='new';items=[];pick='';render();toast('第 02 镜用第 2 版');});
  $$('.rv-rate').forEach(b=>b.onclick=()=>{rated=!rated;render();toast(rated?'已存为样例，以后写新镜时 Opus 会参考它':'已取消样例');});
  $$('.rv-go-log').forEach(b=>b.onclick=()=>go2('log'));
  $$('.rv-back-btn').forEach(b=>b.onclick=()=>go2('review'));
}
