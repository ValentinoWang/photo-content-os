import {draftEditorNote} from './review-common.js';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const D=v=>`<span data-design-data>${esc(v)}</span>`;
const mmss=t=>{t=Math.max(0,Math.round(t));return Math.floor(t/60)+':'+String(t%60).padStart(2,'0');};
const s1=t=>(Math.round(t*10)/10).toFixed(1);
const SCENES={'selfie-moments':'自拍','sports-meet':'校运会','travel':'路上','travel/raw-pending':'路上'};
const frameOf=s=>s.frames?.[Math.min(1,s.frames.length-1)]||'';
export function presentPlan(data,shots,tracks){
 const raw=data.plan;if(!raw)return null;
 const clips=raw.clips.map(c=>({...c,n:c.index,srcIn:c.source_start,shot:shots.find(s=>s.id===c.shot_id)||{id:c.shot_id,scene:c.scene,kind:c.kind,frames:[]}}));
 const byId=id=>clips.find(c=>c.shot_id===id);
 const songs=raw.songs.map(s=>({...s,from:s.start,to:s.end,track:{...tracks.find(t=>(t.id||t.file_sha256)===s.track_id),title:s.title,bpm:s.bpm},kind:raw.mapped_sections.find(x=>x.song_id===s.id&&x.end>x.start)?.kind}));
 const occ=raw.occurrences.map(o=>({...o,key:o.id,tech:o.technique,clip:byId(o.shot_ids.at(-1)),prev:o.technique==='jcut'?byId(o.shot_ids[0]):null,clips:o.shot_ids.map(byId),src:byId(o.reason_data.source_shot_id),until:o.end,lead:o.reason_data.lead_sec,peak:o.reason_data.peak_sec,shift:o.reason_data.shift_sec||0}));
 const swaps=raw.swaps.map(w=>({...w,idx:byId(w.before_shot_id)?.n-1,from:byId(w.before_shot_id)?clips[byId(w.before_shot_id).n-2]?.shot:null,to:byId(w.before_shot_id)?.shot}));
 return {clips,songs,occ,live:occ.filter(o=>o.live),on:new Set(raw.techniques.filter(t=>t.enabled).map(t=>t.id)),
  total:raw.metrics.duration_sec,used:raw.metrics.used_technique_count,average:raw.metrics.average_cut_sec,preview:raw.metrics.preview_shot_ids,
  count:id=>raw.techniques.find(t=>t.id===id)?.count??0,secs:raw.mapped_sections.filter(s=>s.end>s.start),cuts:raw.cuts,downs:raw.mapped_downbeats.map(d=>d.t),
  swaps,swap:swaps[0]||null,cands:(swaps[0]?.alternatives||[]).map(c=>({...c,idx:byId(c.before_shot_id)?.n-1,from:byId(c.before_shot_id)?clips[byId(c.before_shot_id).n-2]?.shot:null,to:byId(c.before_shot_id)?.shot})),
  bedMisses:raw.warnings.bed_short_occurrences,shortWords:raw.warnings.missing_word_count};
}
export function beatMapOptions(data,selected,selectedSwap,onSeek,onSwapClick){
 const p=data.plan;
 return {duration:p.metrics.duration_sec,lane:false,fadeOut:p.metrics.fade_out_sec,
  songs:p.songs.map(s=>({id:s.id,title:s.title,start:s.start,end:s.end,offset:s.offset,beatMap:data.analysis.find(a=>a.song_instance_id===s.id)?.beat_map})),
  cuts:p.cuts.map(c=>({t:c.t,selected:p.occurrences.some(o=>o.technique===selected&&o.live&&o.at===c.t)})),selectedSwap,onSeek,onSwapClick};
}
const NOTICE_GROUPS=[
 ['csrf_invalid origin_forbidden host_forbidden body_invalid revision_invalid request_invalid roughcut_command_invalid roughcut_job_action_invalid music_count_invalid playlist_invalid preset_not_found preset_invalid occurrence_not_found overrides_invalid swap_boundary_invalid transcript_selection_invalid project_not_found roughcut_job_not_found music_part_invalid','这次操作没成功','请刷新页面后再试一次。',['刷新']],
 ['revision_conflict roughcut_inputs_stale','这件作品刚在别处改过','已经换成最新的内容，请再操作一次。',['知道了']],
 ['selection_not_confirmed','精选还没确认','回第 2 步确认这些精选以后，才能排粗剪。',['回去挑镜头']],
 ['roughcut_state_unreadable roughcut_job_unreadable settings_invalid builtin_presets_invalid shots_invalid','读不到这件作品的粗剪记录','本机记录读不出来，原素材没有受影响。可以重试；还不行就去设置与诊断看看。',['重试','去设置']],
 ['preset_write_failed','这个预设没存上','本机记录写不进去，可以再试一次。',['重试']],
 ['beat_analysis_unavailable beat_map_missing','拍子分析还不能用','这台电脑上的拍子分析还没准备好，准备好以后就能排。已经挑好的精选都留着。',['去设置']],
 ['song_too_short','这首歌比粗剪短，排不下','换一首长一点的歌，或者再加一首接在后面。',['换一首歌']],
 ['transcription_unavailable transcript_failed','这几段自拍没转写成','本机的转写没有跑成，可以再试一次。',['重试']],
 ['transcript_unreadable transcript_invalid','读不到自拍的转写结果','转写文件读不出来，可以重新转写一次。',['重新转写']],
 ['editor_diagnostics_unreadable editor_readiness_invalid editor_not_ready','读不到剪辑软件的状态','先去设置与诊断看看这台电脑上的剪辑软件。',['去设置']],
 ['draft_failed runtime_unavailable','草稿没出成','这次没有生成出来，粗剪还在。可以再试一次。',['重试']],
 ['preview_failed','预览没生成出来','粗剪排好了，但预览视频没有生成成功，可以再试一次。',['重试']],
 ['edl_provenance_required kdenlive_acceptance_required','这件作品还不能出草稿','出草稿这一步还没接好，粗剪可以先看、先调。',[]]
];
export function noticeForFailure(error){const row=NOTICE_GROUPS.find(r=>r[0].split(' ').includes(error.code));return row?{title:row[1],body:row[2],buttons:row[3]}:null;}
export function createCutView(ctx){
 const $=s=>ctx.root().querySelector(s),$$=s=>[...ctx.root().querySelectorAll(s)];
 let data,library,caps,shots=[],tracks=[],piece,tabs='',STYLES={},SEL=[],P=null,st={},poll,epoch=0,busy=false,beatView,beatLoader,localNotice=null,lastAction=null,lastCommand=null,progress=null,pollVersion=0,failedPreviewId=null;
 const TECH=[
 {id:'jcut',name:'声音先进',fam:'snd',desc:'下一个镜头的声音提前半秒进来，先听到再看到，换场不突兀。'},
 {id:'bed',name:'现场声连着',fam:'snd',desc:'同一个地方连着好几个镜头时，用一段现场声从头铺到尾，听起来是连着的一件事。'},
 {id:'duck',name:'说话时压低音乐',fam:'snd',desc:'自拍里你说话的时候，背景音乐压低 12 分贝，说完再回来。'},
 {id:'pause',name:'停顿处切',fam:'cut',desc:'自拍说话的镜头，切在两句话之间的停顿上，不切在半句话中间。'},
 {id:'action',name:'动作做完再切',fam:'cut',desc:'起跑、冲刺这类镜头，动作最猛的那一下落在切点前 0.25 秒，做完才切走。'}];
 const T=Object.fromEntries(TECH.map(t=>[t.id,t])),DOES={auto:'出草稿时直接做好',handoff:'要你在剪辑软件里做'};
 let SEC={};
 const EDITORS=[{key:'otio_kdenlive',id:'kdenlive',name:'Kdenlive',line:'出一份能直接打开的时间线，在 Kdenlive 里精剪。'},
 {key:'chatcut',id:'chatcut',name:'ChatCut',line:'在 ChatCut 里打开，接着用它精剪。'},
 {key:'openchatcut',id:'openchatcut',name:'OpenChatCut',line:'开源的网页剪辑工具，装在本仓库里。'},
 {key:'guide',id:'guide',name:'剪映',line:'不出工程，给你剪点清单和交接说明，照着在剪映里自己剪。'}];
 const modeOf=id=>caps?.selected?.techniques[id]?.mode==='auto'?'auto':'handoff';
 const doesOf=t=>modeOf(t.id),doesTag=t=>`<span class="does does--${doesOf(t)}">${DOES[doesOf(t)]}</span>`;
 const editorNote=k=>k==='unreadable'?'读不到这件作品用什么出草稿':draftEditorNote(caps.choice,caps.editors.filter(e=>e.id==='chatcut').map(e=>({id:'chatcut_mcp',status:e.availability.connected===true?'ready':'unavailable'})),caps.selected);
 const editorLabel=()=>st.editor==='chatcut'?'用 ChatCut':st.editor==='openchatcut'?'用 OpenChatCut':editorNote(st.editor);
 const editorStatus=e=>{const a=caps.editors.find(x=>x.id===e.id)?.availability;
  if(!a||['unknown','unreadable'].includes(a.status))return '';
  return e.id==='kdenlive'?(a.installed?'已安装 · 可选':'没装'):e.id==='chatcut'?(a.connected?'已连上 · 还出不了多镜头草稿':'没连上'):e.id==='guide'?(a.installed?'剪映已安装':'剪映没装，也能照清单剪'):(a.installed?'已安装 · 还出不了多镜头草稿':'');};
 const names=ids=>ids.map(id=>'「'+T[id].name+'」').join('');
 const diffText=(off,add)=>[off.length?'关掉了'+names(off):'',add.length?'打开了'+names(add):''].filter(Boolean).join('，');
 const preset=k=>STYLES[k];let RECOMMEND='trip';const SHOWN=['trip','race','calm'];
 const pct=t=>(t/P.total*100).toFixed(3)+'%';
 const clipAt=t=>P.clips.find(c=>t>=c.start&&t<c.end)||P.clips.at(-1);
 const startOf=o=>o.at;
 const activeAt=t=>P.live.filter(o=>t>=o.at-(o.tech==='jcut'?o.lead:0)&&t<Math.max(o.end,o.at+.4));
 const songOf=t=>P.songs.find(g=>t>=g.from&&t<g.to)||P.songs.at(-1);
 const ptabs=()=>tabs+'<div class="ov" id="songov" hidden role="dialog" aria-modal="true" aria-labelledby="song-t" data-design-id="R226-SONG-DIALOG"></div><div class="ov" id="libov" hidden role="dialog" aria-modal="true" aria-labelledby="lib-t" data-design-id="R226-PRESETS"></div>';
 function flow(cur3){const a=data.source_summary,d=data.draft,draftNote=['queued','running'].includes(d?.status)?'正在出草稿':d?.status==='ready'?'草稿已出好':d?.status==='stale'?'草稿是上一版':editorNote(st.editor);const steps=[['素材',D(`${a.inventory_video_count} 段视频 · ${a.inventory_photo_count} 张照片`),true],['挑镜头',D(`${a.selected_shot_count} 个精选 · 已确认`),true],['配乐卡点',D(cur3),false],['出草稿',D(draftNote),d?.status==='ready'],['人工精剪','在剪辑软件里改',false]];
  return `<nav class="flow full" aria-label="这件作品的步骤" data-design-id="R208-STEPS">${steps.map(([t,n,done],i)=>`<div class="fstep ${done?'done':''} ${i===2?'cur':''}" ${i===2?'aria-current="step"':''}><b data-design-data>${done?'✓':i+1}</b><span><strong>${t}</strong><small>${n}</small></span></div>`).join('')}</nav>`;}
 function head(title,lede,actions){return `<div class="stephead full" data-design-id="R226-HEAD"><div><p class="eyebrow">第 3 步 · 配乐卡点</p><h2>${title}</h2><p>${lede}</p></div><div class="actions">${actions}</div></div>`;}
 function previewPlan(k){const p=data.preset_previews.find(x=>x.preset_id===k);return {total:p?.duration_sec,average:p?.duration_sec==null?null:(p.duration_sec-data.plan.metrics.fade_out_sec)/data.plan.metrics.shot_count,preview:p?.preview_shot_ids||[],secs:p?.mapped_sections.filter(s=>s.end>s.start)||[],cuts:p?.cuts||[]};}
// R226 presentation templates follow the approved local design.
function render(){
  const previousVideo=$('#stage video'),preview=previewArtifact();
  const keepVideo=previousVideo&&preview&&previousVideo.dataset.artifactId===preview.id;
  if(previousVideo&&!keepVideo){previousVideo.pause();st.t=0;}
  st.playing=!!keepVideo&&!previousVideo.paused;
  const scr=ctx.root();scr.dataset.designState=st.state;ctx.mark(st.state);scr.classList.add('single','r226-cut');
  if($('#songov'))$('#songov').hidden=true;if($('#libov'))$('#libov').hidden=true;
  if(!data.plan&&['no_music','stopped'].includes(data.status))return renderPick(scr);
  if(['cut-arranging','cut-beat-queued','cut-beat-analyzing'].includes(st.state))return renderArranging(scr);
  if(st.state==='cut-failed'||st.state.startsWith('cut-failed-'))return renderFailed(scr);
  P=presentPlan(data,shots,tracks);if(!P){scr.innerHTML=ptabs()+flow('没排出来')+notices();bind();return;}if(st.swapIndex>1)P.swap=P.swaps.find(w=>w.index===st.swapIndex)||P.swap;
  const S=preset(st.style), changed=[...st.off].filter(id=>S.on.includes(id)), added=[...st.add].filter(id=>!S.on.includes(id)), multi=P.songs.length>1, used=`「${D(S.name)}」${S.name.endsWith('预设')?'':'预设'}`;
  const title=multi?`用 ${D(P.songs.length)} 首歌排好了 ${D(mmss(P.total))} 的粗剪`:`按《${D(st.tracks[0].title)}》排好了 ${D(mmss(P.total))} 的粗剪`;
  const lede=multi
    ?`${D(data.source_summary.selected_shot_count)} 个镜头，切点都对在各自那首歌的拍子上，从${D(SCENES[P.swap.from.scene])}进${D(SCENES[P.swap.to.scene])}时换成《${D((st.tracks[1]||SONG_B).title)}》。用的是${used}。先从头看一遍，不想要的剪辑手法在右边关掉。`
    :`${D(data.source_summary.selected_shot_count)} 个镜头，切点都对在拍子上，用的是${used}。先从头看一遍，不想要的剪辑手法在右边关掉。`;
  scr.innerHTML=ptabs()+flow(multi?`${P.songs.length} 首歌 · ${mmss(P.total)}`:`${st.tracks[0].title} · ${mmss(P.total)}`)+head(title,lede,draftBox())+draftStatusHTML()+notices()+
    `<section class="full" data-design-id="R226-STYLES"><h2 class="section-title wrap"><b>剪辑预设</b><span>每张卡都是用这件作品的镜头排出来的样子；换预设会重新排切点和手法</span></h2><div class="styles" role="radiogroup" aria-label="剪辑预设">${shownPresets().map(presetCard).join('')}<button class="preset-more" data-lib><b>更多预设</b><small>共 ${D(library.total)} 个，按旅行、运动、日常${!st.presetsUnreadable&&st.mine?'和我的':''}分好了</small><span>打开预设库 ›</span></button></div>
      ${st.style===RECOMMEND&&data.recommendation.dominant_scene==='travel'&&data.recommendation.sports_count>0?`<p class="why">推荐理由：<b>路上</b>的镜头最多（${D(data.recommendation.dominant_count)} 个），中间有一段<b>校运会</b>（${D(data.recommendation.sports_count)} 个），适合先松后紧。</p>`:''}
      ${changed.length||added.length?`<p class="changed">你改过：${diffText(changed,added)}。<button class="btn" data-save ${st.presetsUnreadable?'disabled':''}>存为我的预设</button><button class="link" data-restore>恢复「${esc(S.name)}」原样</button></p>`:''}</section>`+
    `<section class="hero full" data-design-id="R226-HERO"><div class="stage-wrap"><div class="stage" id="stage"></div><div class="hero-ctl"><button class="btn-round" id="play" aria-label="播放">▶</button><button class="btn" data-from0>从头播</button><span class="hero-pos" id="pos"></span></div><div class="nowbox" id="nowbox" data-design-id="R226-NOW"></div></div><aside class="shot-panel" data-design-id="R226-TECH"><div id="panel"></div></aside></section>`+
    timeline();
  if(keepVideo)$('#stage').append(previousVideo);
  renderLib();renderSong();bind();paintPanel();paintTime();mountMusic();
}

function draftBox(){
  const drafting=['queued','running'].includes(data.draft?.status),blocked=!data.display.draft_allowed||busy||drafting;
  const label=drafting?'正在出草稿':['ready','stale'].includes(data.draft?.status)?'重新出草稿':'出草稿';
  return `<div class="draft-box" data-design-id="R226-DRAFT"><span class="draft-to">${D(editorLabel())}${['openfilm','unreadable'].includes(st.editor)?' · ':''}<button class="link" data-editor-open aria-expanded="${st.editorOpen}">换</button></span><button class="btn btn--pri" ${blocked?'disabled aria-disabled="true"':'aria-disabled="false"'} data-draft>${label}</button>${st.editorOpen?editorPop():''}</div>`;
}
function draftStatusHTML(){
  const d=data.draft;if(!d||!['queued','running','ready','stale'].includes(d.status))return '';
  const editor=EDITORS.find(e=>e.key===(d.method==='guide'?'guide':d.editor))?.name,done=d.status==='ready';
  let title,body,actions='',id;
  if(['queued','running'].includes(d.status)){
    id='R226-DRAFTING-STATUS';title=`正在用 ${D(editor)} 出草稿`;
    body=`把这 ${D(data.plan.metrics.shot_count)} 个镜头和配乐放进时间线，通常一两分钟。可以先去做别的，出好后在工作台提醒你。`;
  }else if(done){
    const guide=d.design_state==='cut-drafted-guide';id=guide?'R226-DRAFTED-GUIDE-STATUS':'R226-DRAFTED-STATUS';
    title=guide?'剪点清单出好了':`草稿出好了，可以在 ${D(editor)} 里打开`;
    body=guide?'照着清单在剪映里剪：每个切点、每一处手法都写了时间码和做法。':'切点、配乐和能自动做的手法都放好了；标着「要你在剪辑软件里做」的那几处，写在剪辑交接说明里，带时间码。';
    if(d.can_open)actions=`<button class="btn" data-draft-open data-design-id="R226-DRAFT-OPEN">在 ${D(editor)} 里打开</button>`;
    const guideArtifact=data.artifacts.find(a=>a.id===d.guide_artifact_id&&a.kind==='guide');
    if(guideArtifact)actions+=`<a class="btn" data-design-id="R226-DRAFT-HANDOFF" href="${esc(guideArtifact.url)}" target="_blank" rel="noopener">看剪辑交接说明</a>`;
  }else{
    id='R226-DRAFT-STALE-STATUS';title='粗剪改过了，草稿还是上一版';body='再出一次草稿，Kdenlive 里才是现在这一版。';
  }
  return `<div class="attention draft-status full" role="status" data-tone="${done?'success':'neutral'}" data-design-id="${id}"><div><strong>${title}</strong><p>${body}</p></div>${actions?`<div class="actions">${actions}</div>`:''}</div>`;
}
function editorPop(){
  return `<div class="editor-pop" role="dialog" aria-label="这件作品用什么出草稿" data-design-id="R226-EDITOR"><div class="tl2-head"><p class="ep-h">这件作品用什么出草稿</p><button class="pl-x" data-editor-x aria-label="关闭" data-design-id="R226-EDITOR-CLOSE">×</button></div><div role="radiogroup">${EDITORS.map(e=>`<button class="ep-opt" role="radio" aria-checked="${st.editor===e.key}" data-editor-pick="${e.key}"><i class="radio"></i><span><b>${e.name}</b><small>${e.line}</small></span><em class="${(e.id==='guide'||e.id==='kdenlive'&&caps.editors.find(x=>x.id===e.id)?.availability.installed)?'':'warn'}" data-design-data>${editorStatus(e)}</em></button>`).join('')}</div><p class="ep-foot">只改这件作品；没选过的作品默认用 Kdenlive。</p></div>`;
}
function shownPresets(){const ids=[...library.presets.filter(p=>p.origin==='mine').slice(0,1).map(p=>p.id),RECOMMEND,...SHOWN].filter(id=>STYLES[id]);if(!ids.slice(0,3).includes(st.style))ids.splice(2,0,st.style);return [...new Set(ids)].slice(0,3);}
function presetCard(k){
  const x=preset(k), sel=k===st.style, p=sel?P:previewPlan(k), changed=sel&&([...st.off].some(id=>x.on.includes(id))||[...st.add].some(id=>!x.on.includes(id)));
  const f=t=>(t/p.total*100).toFixed(2)+'%';
  const pick=p.preview.map(id=>({shot:shots.find(s=>s.id===id)||{frames:[]}}));
  const thumbs=pick.map(c=>`<img src="${esc(frameOf(c.shot))}" data-shot-id="${esc(c.shot.id)}" alt="">`).join('');
  const bar=p.secs.map(s=>`<i class="${s.kind==='build'?'b':s.kind==='peak'?'p':''}" data-cut-left="${f(s.start)}" data-cut-width="${f(s.end-s.start)}"></i>`).join('')+p.cuts.map(c=>`<b data-cut-left="${(c.position*100).toFixed(3)}%"></b>`).join('');
  return `<button class="style" role="radio" aria-checked="${sel}" data-style="${esc(k)}"><div class="pv" aria-hidden="true"><div class="pv-thumbs">${thumbs}</div><div class="pv-bar">${bar}</div></div><div class="style-body"><div class="style-top"><i class="radio"></i><b>${D(x.name)}</b>${k===RECOMMEND?'<span class="chip chip--ai">AI 推荐</span>':''}${STYLES[k]?.origin==='mine'?'<span class="chip">我的</span>':''}${changed?'<span class="chip">改过</span>':''}</div><p>${D(x.line)}</p>${p.total==null?'':`<span class="rh">${D(mmss(p.total))} · 平均 ${D(s1(p.average))} 秒一切</span>`}<div class="uses">${TECH.map(t=>`<span class="tq-tag ${t.fam==='snd'?'snd':''} ${x.on.includes(t.id)?'':'off'}">${t.name}</span>`).join('')}</div></div></button>`;
}
function renderLib(){
  const box=$('#libov');if(!st.lib){box.hidden=true;box.innerHTML='';return;}
  const keys=Object.keys(STYLES), cats=['全部','旅行','运动','日常','我的'];
  const shown=keys.filter(k=>st.libCat==='全部'||preset(k).cat===st.libCat);
  box.hidden=false;
  box.innerHTML=`<div class="lib-pl"><header><div><strong id="lib-t">剪辑预设</strong><small>每个预设都用这件作品的 ${D(data.source_summary.selected_shot_count)} 个镜头和${P.songs.length>1?`这 ${D(P.songs.length)} 首歌`:`《${D(st.tracks[0].title)}》`}排一遍给你看</small></div><button class="pl-x" data-lib-x aria-label="关闭">×</button></header><div class="lib-body"><div class="tabs" role="group" aria-label="按类型看">${cats.map(c=>`<button data-cat="${c}" aria-pressed="${st.libCat===c}">${c}${c==='我的'&&st.presetsUnreadable?'':`<i data-design-data>${library.categories.find(x=>x.label===c)?.count}</i>`}</button>`).join('')}</div><div class="lib-grid styles" role="radiogroup" aria-label="剪辑预设">${st.libCat==='我的'&&st.presetsUnreadable?presetsNotice():shown.length?shown.map(presetCard).join(''):'<p class="lib-empty">还没有存过预设。在剪辑手法里改过开关以后，可以「存为我的预设」。</p>'}</div></div></div>`;
}

function timeline(){
  const end=P.total, cutsHL=st.sel&&T[st.sel].fam==='cut'?new Set(P.live.filter(o=>o.tech===st.sel).map(o=>o.at.toFixed(3))):new Set();
  const ticks=[];for(let x=0;x<=end;x+=15)ticks.push(`<i data-design-data data-cut-left="${pct(x)}">${mmss(x)}</i>`);
  const blocks=P.clips.map(c=>`<button class="blk" data-design-data data-clip="${c.n}" data-cut-left="calc(${pct(c.start)} + 1px)" data-cut-width="calc(${pct(c.end-c.start)} - 2px)" data-cut-frame="${esc(frameOf(c.shot))}" title="第 ${c.n} 个镜头 · ${esc(SCENES[c.shot.scene])}"><b data-design-data>${c.n}</b></button>`).join('');
  const audio=data.source_audio.map(a=>`<i class="au ${a.mode==='muted'?'mute':''}" data-cut-left="${a.position*100}%" data-cut-width="${(a.end_position-a.position)*100}%"></i>`).join('')+P.live.filter(o=>o.tech==='jcut').map(o=>`<i class="au lead" data-cut-left="${pct(Math.max(0,o.at-o.lead))}" data-cut-width="${pct(o.lead)}" title="声音先进"></i>`).join('')+P.live.filter(o=>o.tech==='bed').map(o=>`<i class="bed" data-cut-left="${o.position*100}%" data-cut-width="${(o.end_position-o.position)*100}%" title="现场声连着"></i>`).join('');
  const S=preset(st.style);
  const lanes=TECH.map(t=>{const on=P.on.has(t.id), inStyle=S.on.includes(t.id),events=P.live.filter(o=>o.tech===t.id),positions=events.map(o=>o.at).sort((a,b)=>a-b);
    const spacing=positions.length>1?Math.min(...positions.slice(1).map((x,i)=>x-positions[i])):null;
    const pointSize=spacing==null?'10px':`min(10px,${(spacing/P.total*80).toFixed(6)}cqw)`;
    const items=events.map(o=>{const span=o.tech==='bed'||o.tech==='duck', a=startOf(o), tip=`${t.name} · ${mmss(a)}${o.skipped?' · 这一处不用':''}`;
      return span?`<button class="span ${o.skipped?'skip':''}" data-design-data data-occ="${esc(o.key)}" data-cut-left="${pct(a)}" data-cut-width="${pct(o.until-a)}" aria-current="${st.occ===o.key}" title="${tip}" aria-label="${tip}"></button>`
                 :`<button class="ev ${o.skipped?'skip':''}" data-design-data data-occ="${esc(o.key)}" data-cut-left="${pct(o.at)}" aria-current="${st.occ===o.key}" title="${tip}" aria-label="${tip}"></button>`;}).join('');
    return `<div data-technique="${t.id}" data-cut-size="${pointSize}" class="lane ${t.fam} ${st.sel===t.id?'sel':''}">${on&&needsWords(t.id)?'<span class="lane-note" data-design-id="R226-WORDS-LANE-'+t.id+'">要先转写自拍</span>':on?items:`<span class="lane-note">${inStyle?'关掉了':'这个预设不用'}</span>`}</div>`;}).join('');
  const labs=TECH.map((t,i)=>`<span class="l-lane ${t.fam} ${P.on.has(t.id)?'':'off'} ${st.sel===t.id?'sel':''} ${i===0?'l-first':''}" role="button" tabindex="0" data-pick="${t.id}">${t.name}</span>`).join('');
  const chips=P.songs.map((g,i)=>`<div class="song-chip"><b data-design-data>${i+1}</b><div><strong data-design-data>${esc(g.track.title)}</strong><small>${D(mmss(g.from))}–${D(mmss(g.to))} · ${D(Math.round(g.track.bpm)+' BPM')}</small></div><span class="acts"><button class="link" data-replace-song="${i}">换一首</button>${i?`<button class="link" data-remove-song="${i}">去掉</button>`:''}</span></div>`).join('');
  return `<section class="tl2 full" data-design-id="R226-TIMELINE"><div class="tl2-head"><h2 class="section-title"><b>粗剪时间轴</b><span>点任意位置跳过去；点手法那几行里的点或条，看这一处怎么做</span></h2>
    <div class="tl2-legend"><span><i class="sw2 sw--quiet"></i>${D(SEC.quiet)}</span><span><i class="sw2 sw--build"></i>${D(SEC.build)}</span><span><i class="sw2 sw--peak"></i>${D(SEC.peak)}</span></div></div>
    <div class="songs-bar" data-design-id="R226-SONGS"><span class="lab">配乐</span>${chips}${P.songs.length<3?`<button class="btn" data-add-song>加一首歌</button>`:''}</div>
    <div class="tl2-scroll"><div class="tl2-grid"><div class="tl2-labs"><span class="l-ruler"></span><span class="l-songs"></span><span class="l-music">音乐</span><span class="l-video">画面</span><span class="l-audio">现场声</span>${labs}</div>
    <div class="tl2-body" id="tlbody"><div class="tl2-ruler">${ticks.join('')}</div><div class="cut-beat-map" id="cut-beat-map"></div><div class="tl2-video">${blocks}</div><div class="tl2-audio">${audio}</div><div class="tl2-lanes">${lanes}</div><i class="tl2-ph" id="ph"></i></div></div></div>
    <p class="tl2-note">现场声那一行：斜线是静掉的现场声，洋红框是用一段现场声铺底，洋红条是提前进来的声音。</p></section>`;
}

function paintPanel(){
  const box=$('#panel');if(!box)return;
  const o=st.occ&&P.occ.find(x=>x.key===st.occ);
  if(st.swapOpen&&P.swap){box.innerHTML=swapHTML();box.className='occ';box.parentElement.dataset.designId='R226-SWAP';bindPanel();return;}
  if(o){box.innerHTML=occHTML(o);box.className='occ';box.parentElement.dataset.designId='R226-OCC';bindPanel();return;}
  box.className='';box.parentElement.dataset.designId='R226-TECH';
  const S=preset(st.style);
  box.innerHTML=`<p class="eyebrow">剪辑手法 · ${D(S.name)}</p><h3>用了 ${D(P.used)} 种，共 ${D(data.plan.metrics.occurrence_count)} 处</h3>
  <ul class="tq">${TECH.map(t=>{const inStyle=S.on.includes(t.id), on=P.on.has(t.id), n=P.count(t.id);
    const short=t.id==='bed'&&on&&P.bedMisses.length?`<p class="short" data-design-id="R226-BED-SHORT">有 ${D(P.bedMisses.length)} 处连着的镜头现场声不够长，没铺上</p>`:t.id==='pause'&&on&&P.shortWords&&!st.allWordsMissing?`<p class="short">另有 ${D(P.shortWords)} 段自拍没有逐字时间，这里用不上。</p>`:'';
    return `<li data-technique-row="${t.id}" class="${on?'':'off'}" aria-current="${st.sel===t.id}"><button class="sw" role="switch" aria-checked="${on}" aria-label="${t.name}" data-sw="${t.id}"></button><div><div class="nm"><button data-pick="${t.id}">${t.name}</button><i data-design-data>${on&&needsWords(t.id)?'要先转写自拍':on?n+' 处':inStyle?'关掉了':'这个预设不用'}</i></div><p>${t.desc}</p>${short}<div class="foot">${doesTag(t)}${on&&n?`<button class="link" data-first="${t.id}">看第 1 处</button>`:''}</div></div></li>`;}).join('')}</ul>`;
  bindPanel();
}

const W=10, row=(lab,items)=>`<div class="dia-row"><span>${lab}</span><div>${items}</div></div>`;
const box=(a,b,cls)=>`<i class="${cls||''}" data-cut-left="${a*W}%" data-cut-width="${(b-a)*W}%"></i>`;
const cutAt=f=>`<i class="dia-cut" data-cut-left="calc(48px + (100% - 48px)*${f})"></i>`;

function occHTML(o){
  const t=T[o.tech], list=P.occ.filter(x=>x.tech===o.tech), i=list.indexOf(o), sc=x=>SCENES[x.shot.scene];
  let title, where, why, does, dia;
  if(o.tech==='jcut'){title=`${mmss(o.at)} · ${sc(o.prev)} → ${sc(o.clip)}`;where=`第 ${o.clip.n} 个镜头的现场声提前 ${s1(o.lead)} 秒进来`;
    why=`从${sc(o.prev)}换到${sc(o.clip)}，先听到${sc(o.clip)}那边的声音，再看到画面，换场不跳。`;
    does=`把第 ${o.clip.n} 个镜头的声音往前拖 ${s1(o.lead)} 秒，盖住第 ${o.prev.n} 个镜头的最后 ${s1(o.lead)} 秒。`;
    dia=row('画面',box(0,5)+box(5,10,'nx'))+row('声音',box(0,4)+box(4,10,'hl'))+cutAt(.5);}
  else if(o.tech==='bed'){const k=o.src.n;title=`${mmss(o.clips[0].start)}–${mmss(o.until)} · ${sc(o.clips[0])}`;where=`第 ${o.clips[0].n}–${o.clips[o.clips.length-1].n} 个镜头，共 ${o.clips.length} 个`;
    why=`这 ${o.clips.length} 个镜头都在${sc(o.clips[0])}，用第 ${k} 个镜头的现场声从头铺到尾，中间换镜头时声音不断。`;
    does=`把这几个镜头自己的声音关掉，只留第 ${k} 个镜头的现场声，拉长铺满这一段。`;
    dia=row('画面',box(0,3.3)+box(3.4,6.6,'nx')+box(6.7,10))+row('声音',box(0,10,'hl'));}
  else if(o.tech==='duck'){title=`${mmss(o.clip.start)}–${mmss(o.until)} · 自拍`;where=`第 ${o.clip.n} 个镜头，${s1(o.until-o.clip.start)} 秒`;
    why=`这个镜头里你在说话，背景音乐压低 12 分贝，让说的话听得清。`;does=`在这一段把音乐轨压低 12 分贝，镜头结束后恢复。`;
    dia=row('说话',box(2,8,'nx'))+row('音乐',box(0,2)+box(2,8,'mute')+box(8,10));}
  else if(o.tech==='pause'){title=`${mmss(o.at)} · 自拍`;where=`第 ${o.clip.n} 个镜头和第 ${o.clip.n+1} 个镜头之间`;
    why=o.shift?`停顿比拍子${o.shift>0?'晚':'早'} ${s1(Math.abs(o.shift))} 秒，切点跟着停顿走，等这句话说完再切。`:`这里的停顿正好落在拍子上，切点没动。`;
    does=null;dia=row('说话',box(0,4.4,'nx')+box(5.6,10,'nx'))+row('画面',box(0,5)+box(5,10))+cutAt(.5);}
  else {title=`${mmss(o.at)} · 校运会`;where=`第 ${o.clip.n} 个镜头，原片第 ${s1(o.peak)} 秒动作最猛`;
    why=`动作最猛的那一下放在切点前 0.25 秒，动作做完才切走，不会切在半个动作上。`;does=null;
    dia=row('动感',`<i class="hlc" data-cut-left="72%" data-cut-width="6%"></i>`)+row('画面',box(0,8)+box(8,10,'nx'))+cutAt(.8);}
  return `<button class="link back" data-back>‹ 全部手法</button>
   <p class="eyebrow ${t.fam}">${t.name} · 第 ${D(o.index)} / ${D(o.total)} 处</p><h3>${D(title)}</h3><p class="where">${D(where)}</p>
   <div class="dia" aria-hidden="true"><div class="dia-rows">${dia}</div><small>示意图，不按比例</small></div>
   <div class="verdict"><small>为什么在这里用</small><p>${['jcut','bed','pause'].includes(o.tech)?D(why):why}</p></div>
   <div class="verdict"><small>${doesTag(t)}</small><p>${does?D(does+' 出草稿时写进剪辑交接说明，带这一处的时间码。'):st.editor==='guide'?'剪点清单里已经按这个位置标好，照着切就行。':'已经按这个位置切好，出草稿时直接带上。'}</p></div>
   <div class="occ-act"><button class="btn btn--play" data-play-occ>从前 2 秒播放</button><button class="btn" data-step="-1" ${i?'':'disabled'}>上一处</button><button class="btn" data-step="1" ${i<list.length-1?'':'disabled'}>下一处</button></div>
   ${o.skipped?`<p class="skipped">这一处不用了。<button class="link" data-unskip>还是用</button></p>`:`<button class="link skip" data-skip>这一处不用</button>`}`;
}

function swapHTML(){
  const w=P.swap, B=P.songs.find(g=>g.id===w.song_id).track, d=w.bpm_delta, kind=SEC[P.songs.find(g=>g.id===w.song_id).kind]+'段';
  const others=(w.alternatives||[]).map(c=>({...c,idx:P.clips.findIndex(x=>x.shot_id===c.before_shot_id),to:{scene:c.to_scene}}));
  return `<button class="link back" data-back>‹ 全部手法</button>
   <p class="eyebrow">换歌处</p><h3>${D(mmss(w.at))} · 换成《${D(B.title)}》</h3><p class="where">${D(`从${SCENES[w.from.scene]}进${SCENES[w.to.scene]}的那一刀`)}</p>
   <div class="dia" aria-hidden="true"><div class="dia-rows">${row('前一首',box(0,5)+box(5,6,'fadeout'))+row('后一首',box(5,10,'nx'))+cutAt(.5)}</div><small>示意图，不按比例</small></div>
   <div class="verdict"><small>为什么在这里换</small><p>${D(`从${SCENES[w.from.scene]}进${SCENES[w.to.scene]}，换到《${B.title}》的${kind}；它每分钟 ${Math.round(B.bpm)} 拍，${w.speed_relation==='faster'?`比前一首快 ${d} 拍`:w.speed_relation==='slower'?`比前一首慢 ${-d} 拍`:'和前一首一样快'}。`)}</p></div>
   <div class="verdict"><small>换到别的地方</small><div class="alt-pos">${others.length?others.map(c=>`<button class="pill" data-design-data data-swap-to="${c.idx}">进${SCENES[c.to.scene]} · ${mmss(c.at)}</button>`).join(''):'<span class="muted">没有别的场景交界处。</span>'}</div></div>
   <div class="verdict"><small><span class="does does--handoff">${DOES.handoff}</span></small><p>${D(w.index===1?`在 ${mmss(w.at)} 接上第二首，第一首淡出 1 秒，第二首从重拍进来。出草稿时写进剪辑交接说明，带这一处的时间码。`:`在 ${mmss(w.at)} 接上第 ${w.index+1} 首，第 ${w.index} 首淡出 1 秒，第 ${w.index+1} 首从重拍进来。出草稿时写进剪辑交接说明，带这一处的时间码。`)}</p></div>
   <div class="occ-act"><button class="btn btn--play" data-play-swap>从前 2 秒播放</button></div>`;
}

 function attention(id,title,body,actions=''){return `<div class="attention full" role="alert" data-design-id="${id}"><div><strong>${title}</strong><p>${body}</p></div><div class="actions">${actions}</div></div>`;}
 function presetsNotice(){return attention('R226-PRESETS-UNREADABLE','读不到你存的剪辑预设','内置预设照常能用。读出来以前，先不能存新的。','<button class="btn" data-retry-library>重试</button>');}
 function notices(){let html='';
  const n=localNotice||(data.draft?.failure&&noticeForFailure(data.draft.failure))||(data.failure&&noticeForFailure(data.failure))||(data.playback.failure&&noticeForFailure(data.playback.failure));
  if(n)html+=attention('R226-NOTICE',n.title,n.body,n.buttons.map(b=>`<button class="btn" data-notice-action="${b}">${b}</button>`).join(''));
  if(data.plan&&!data.display.draft_allowed&&data.display.draft_blockers.some(x=>['media_first_provenance','r227_kdenlive_acceptance','edl_provenance_required','kdenlive_acceptance_required'].includes(x))&&!n){const n=noticeForFailure({code:'edl_provenance_required'});html+=attention('R226-NOTICE',n.title,n.body);}
  const notices=data.display.notices;
  if(st.editor==='chatcut'&&!st.chatConnected)html+=attention('R226-BLOCKED','ChatCut 还没连上本机','这件作品选了在 ChatCut 里精剪，连上之前出不了草稿。去设置里接上，或者改用 Kdenlive。','<button class="btn" data-settings>去设置</button><button class="btn" data-editor-pick="otio_kdenlive">改用 Kdenlive</button>');
  else if(caps.selected?.block_reason==='multi_source_unverified'){const name=EDITORS.find(e=>e.key===st.editor)?.name;
   html+=attention('R226-EDITOR-UNSUPPORTED',`这件作品的草稿还不能交给 ${D(name)}`,`${D(name)} 现在一次只能处理一段原片，这件作品排好的 ${D(data.plan.metrics.shot_count)} 个镜头交不过去。改用 Kdenlive，或者在剪映里照剪点清单自己剪。`,'<button class="btn" data-editor-pick="otio_kdenlive">改用 Kdenlive</button><button class="btn" data-editor-pick="guide">改用剪映</button>');
  }else if(st.editor==='otio_kdenlive'&&!st.kdenliveInstalled)html+=attention('R226-KDENLIVE-MISSING','本机还没装 Kdenlive','装好以后就能出草稿。也可以先在剪映里照剪点清单自己剪。','<button class="btn" data-settings>去设置</button><button class="btn" data-editor-pick="guide">改用剪映</button>');
  const failed=notices.find(n=>n.code==='rearrange_failed');
  if(failed&&!st.dismissed){const f=failed.failure;const body=f.code==='song_entry_unavailable'?`《${D(tracks.find(t=>t.id===f.details.track_id)?.title)}》第 8 秒以后没有推进段或高潮段，接不上前一首。换一首歌试试。`:f.code==='shot_too_short'?`有 ${D(f.details.short_shot_count)} 个镜头太短，按这首歌的拍子排不进去。`:'读不到这首歌的拍子分析结果。';html+=attention('R226-REARRANGE-FAILED','刚才的改动没排出来，原来的粗剪还在',body,'<button class="btn" data-dismiss-rearrange>知道了</button>');}
  if(st.presetsUnreadable)html+=presetsNotice();
  const speech=data.display.speech;
  if(speech.missing_video_count){const n=speech.missing_video_count,all=speech.mode==='all',affected=speech.affected_techniques.map(id=>T[id].name).join('和');
   const body=affected==='说话时压低音乐'?`这 ${D(n)} 段说话时音乐不会压低。${all?'转写':'重新转写'}后会自动补上。`:`这 ${D(n)} 段先按拍子切，可能切在半句话中间。${all?'转写':'重新转写'}后会自动补上。`;
   const fullBody=speech.affected_techniques.includes('duck')&&speech.affected_techniques.includes('pause')?`这 ${D(n)} 段先按拍子切，可能切在半句话中间，说话时音乐也不会压低。${all?'转写':'重新转写'}后会自动补上。`:body;
   html+=attention(all?'R226-PARTIAL-NONE':'R226-PARTIAL',`有 ${D(n)} 段自拍${all?'还没转写':'没有逐字时间'}，${affected}用不上`,fullBody,`<button class="btn" data-transcribe>${all?'转写':'重新转写'}这 ${D(n)} 段</button>`);
  }
  return html;
 }
 const needsWords=id=>data.display.speech.mode==='all'&&data.display.speech.affected_techniques.includes(id);
 function songRows(dialog){return tracks.map(t=>{const used=dialog&&data.selection.playlist.some(x=>x.track_id===t.id);return `<div class="pick-row" data-design-id="R226-SONG-ROW-${esc(t.id)}"><button class="play" aria-label="试听 ${esc(t.title)}" data-audition="${esc(t.id)}" data-design-data>▶</button><div><b data-design-data>${esc(t.title)}</b><small>${[t.artist,mmss(t.dur),t.bpm==null?null:Math.round(t.bpm)+' BPM'].filter(v=>v!=null&&v!=='').map(D).join(' · ')}</small></div>${used?'<small data-design-id="R226-SONG-IN-USE">已在用</small>':`<button class="btn" data-song-use="${esc(t.id)}">用这首</button>`}</div>`;}).join('');}
 function renderSong(){const box=$('#songov');if(!st.songMode){box.hidden=true;return;}const replace=st.songMode==='replace';box.hidden=false;box.innerHTML=`<div class="lib-pl" data-design-id="R226-SONG-PICKER"><header><strong id="song-t">${replace?'换一首歌':'加一首歌'}</strong><button class="pl-x" data-song-x aria-label="关闭">×</button></header><div class="lib-body"><div class="pick">${songRows(true)}</div><p class="why" data-design-id="R226-SONG-FOOT">${replace?'换了以后，这一段的切点按新歌的拍子重新排。':'加进来以后，会在场景交界处换到这首，后面的切点重新对拍子。'}</p></div></div>`;}
 function renderPick(scr){scr.innerHTML=ptabs()+flow('还没选歌')+head(`先给这 ${D(data.source_summary.selected_shot_count)} 个镜头选一首歌`,'选好后，本机会分析这首歌的拍子，把切点对在拍子上，再按剪辑预设加上声音先进、停顿处切这类剪辑手法。排好后还可以再加歌，在场景交界处换歌。原素材不会被改动。','')+notices()+`<section class="pick full" data-design-id="R226-PICK"><div class="pick-head"><h3>音乐库里的歌 <span class="chip" data-design-data>${tracks.length} 首</span></h3><button class="link" data-music-library>去音乐库导入别的歌</button></div>${songRows(false)}</section>`;bind();}
 function renderArranging(scr){const a=data.analysis[0],done=a?.status==='done',queued=a?.status==='queued',p=progress;
  const steps=[['分析这首歌的拍子',done?`${a.beat_count} 拍`:queued?'排队中':'正在分析',done?100:0,done?'done':''],['按拍子排切点',p?.phase==='cuts'&&p.determinate?`${p.completed} / ${p.total} 个镜头`:'',p?.phase==='cuts'&&p.determinate&&p.total?p.completed/p.total*100:0,''],['加剪辑手法',p?.phase==='techniques'&&p.determinate?`${p.completed} / ${p.total}`:'',p?.phase==='techniques'&&p.determinate&&p.total?p.completed/p.total*100:0,'']];
  scr.innerHTML=ptabs()+flow('正在排')+head(`正在按《${D(st.tracks[0]?.title)}》排粗剪`,done?'通常一分钟内排好。可以先去做别的，排好后在工作台提醒你。':'这首歌的拍子还没分析完，分析完会自动接着排。可以先去做别的，排好后在工作台提醒你。','<button class="btn" data-stop>停止</button>')+notices()+`<div class="progress" data-design-id="R226-PROGRESS"><div class="steps">${steps.map(([b,s,w,c])=>`<div class="step ${c}"><b>${b}</b><span data-design-data>${s}</span><div class="bar"><i data-cut-width="${w}%"></i></div></div>`).join('')}</div></div>`;bind();}
 function renderFailed(scr){const details=data.failure?.details||{};const [title,body,buttons]={
 'cut-failed':['这首歌的拍子没分析出来','分析到一半出错了，可以再试一次，或者换一首歌。',['重新分析','换一首歌']],
 'cut-failed-unreadable':['读不到这首歌的拍子分析结果','分析结果的文件读不出来，可以重新分析一次，或者换一首歌。',['重新分析','换一首歌']],
 'cut-failed-missing':['音乐库里找不到这首歌了','它可能被删掉了。换一首歌就能接着排。',['换一首歌']],
 'cut-failed-short':[`有 ${D(details.short_shot_count)} 个镜头太短，按这首歌的拍子排不进去`,'换一首慢一点的歌，或者回第 2 步换掉这几个镜头。',['换一首歌','回去挑镜头']]}[st.state];
 scr.innerHTML=ptabs()+flow('没排出来')+head('粗剪没排出来',`已经挑好的 ${D(data.source_summary.selected_shot_count)} 个精选都留着，不用重挑。`,'')+notices()+attention(st.state==='cut-failed'?'R226-FAILED':'R226-'+st.state.toUpperCase(),title,body,buttons.map(b=>`<button class="btn" data-failure-action="${b}">${b}</button>`).join(''));bind();}
 async function request(path,options={}){if(ctx.request)return ctx.request(path,options);const headers={Accept:'application/json',...options.headers};const init={credentials:'same-origin',...options,headers};
  if(init.body){init.body=JSON.stringify(init.body);headers['Content-Type']='application/json';}if(init.method&&init.method!=='GET')headers['X-Content-OS-CSRF']=ctx.state.csrf;
  const r=await fetch(path,init);let payload;try{payload=await r.json();}catch{throw Object.assign(new Error('roughcut response unreadable'),{code:'roughcut_state_unreadable'});}
  if(!r.ok||payload.ok!==true)throw Object.assign(new Error('roughcut request failed'),payload.error||{code:'roughcut_state_unreadable'});return payload;
 }
 const base=()=>`/api/review/pieces/${encodeURIComponent(piece.id)}`;
 function syncState(){SEL=shots.filter(s=>s.status==='selected');STYLES=Object.fromEntries(library.presets.map(p=>[p.id,{name:p.name,cat:p.category,line:p.description,on:p.recipe.techniques,origin:p.origin,revision:p.revision}]));RECOMMEND=data.recommendation.preset_id;
  const choice=caps.choice;st.style=data.plan?.preset_id||data.selection.preset_id;
  st.off=new Set(data.customization.disabled);st.add=new Set(data.customization.enabled);
  st.mine=library.presets.find(p=>p.origin==='mine')?.id||null;st.presetsUnreadable=library.mine_status==='unreadable';st.allWordsMissing=data.display.speech.mode==='all';
  st.editor=choice.error?'unreadable':choice.method==='guide'?'guide':choice.method==='self'?'openfilm':choice.editor;
  st.chatConnected=caps.editors.find(e=>e.id==='chatcut')?.availability.connected===true;
  st.kdenliveInstalled=caps.editors.find(e=>e.id==='kdenlive')?.availability.installed!==false;
  st.tracks=(data.plan?.songs||data.selection.playlist.map(s=>({...s,title:tracks.find(t=>t.id===s.track_id)?.title}))).map(s=>tracks.find(t=>t.id===s.track_id)||{id:s.track_id,title:s.title});
  st.state=data.status==='stopped'&&!data.plan?'cut-no-music':data.draft?.design_state||data.display.base_state||'cut-ready';
  if(st.songMode)st.state=st.songMode==='add'?'cut-add-song':'cut-replace-song';
  else if(st.lib)st.state=st.presetsUnreadable&&st.libCat==='我的'?'cut-presets-unreadable-mine':'cut-presets';
  else if(st.editorOpen)st.state=choice.error?'cut-editor-unreadable':st.editor==='openfilm'?'cut-editor-openfilm':st.editor==='guide'&&caps.editors.find(e=>e.id==='guide')?.availability.installed===false?'cut-editor-guide-missing':!st.kdenliveInstalled?'cut-editor-kdenlive-missing':st.editor==='chatcut'&&st.chatConnected?'cut-editor-chatcut-connected':'cut-editor';
  else if(st.swapOpen)st.state='cut-multi-swap';else if(st.occ)st.state='cut-occurrence';
 }
 function repaint(){if(!data||!caps||!library)return;beatView?.destroy();beatView=null;syncState();render();ctx.common?.();}
 async function reload(){const ticket=epoch,id=piece.id;
  const results=await Promise.allSettled([request(base()+'/roughcut'),request('/api/review/editing-presets'),request(base()+'/editor-capabilities'),request(base()+'/shots'),request('/api/review/music')]);
  if(ticket!==epoch||!ctx.active(id))return;
  const bad=results.find(r=>r.status==='rejected');if(bad){handleError(bad.reason);return;}
  [data,library,caps]=results.slice(0,3).map(r=>r.value);shots=results[3].value.shots;
  const music=results[4].value;tracks=music.tracks.map(t=>({...t,id:t.file_sha256||t.id,dur:t.duration_seconds??t.dur,bpm:t.beat?.bpm??t.bpm}));
  SEC=Object.fromEntries(music.taxonomy.sections.map(s=>[s.id,s.name]));
  if(!data.source_summary.selection_confirmed){ctx.go({view:'piece',piece:id,ptab:'vlog'});return;}
  localNotice=null;repaint();schedule();return true;
 }
 function handleError(error){console.error('R226',error.code||error);if(error.code==='unknown_track'||error.code==='music_track_not_found')localNotice=null;else localNotice=noticeForFailure(error);
  if(!localNotice&&error.design_state&&data){data={...data,failure:error,status:'failed',display:{...data.display,base_state:error.design_state}};}
  if(!localNotice&&!error.design_state){console.error('R226 unclassified failure',error);localNotice=noticeForFailure({code:'request_invalid'});}
  if(data&&library&&caps)repaint();else {ctx.mark('cut-no-music');ctx.root().classList.add('r226-cut','single');const n=localNotice;ctx.root().innerHTML=tabs+(n?attention('R226-NOTICE',n.title,n.body,n.buttons.map(b=>`<button class="btn" data-notice-action="${b}">${b}</button>`).join('')):'');bind();}
 }
 function activeJob(){
  if(data.job&&['queued','arranging','stopping'].includes(data.status))return {id:data.job.job_id,kind:'arrange'};
  if(data.draft?.job_id&&['queued','running'].includes(data.draft.status))return {id:data.draft.job_id,kind:'draft'};
  return null;
 }
 function schedule(){clearTimeout(poll);const version=++pollVersion,job=activeJob();if(job&&!busy)poll=setTimeout(()=>pollJob(job,version),1000);}
 async function pollJob(job,version){const ticket=epoch,id=piece.id;if(!ctx.active(id)||version!==pollVersion)return;
  try{const result=await request(`/api/review/roughcut-jobs/${encodeURIComponent(job.id)}`);if(ticket!==epoch||!ctx.active(id)||version!==pollVersion)return;
   if(job.kind==='draft'||['done','failed','stopped'].includes(result.status)){await reload();return;}
   progress=result.progress;data.analysis=result.analysis;repaint();schedule();
  }catch(e){if(ticket===epoch&&ctx.active(id)&&version===pollVersion)handleError(e);}
 }
 async function perform(action){if(busy)return;busy=true;clearTimeout(poll);pollVersion++;lastAction=action;$$('button[data-sw],button[data-style],button[data-draft]').forEach(b=>{b.disabled=true;if(b.hasAttribute('data-draft'))b.setAttribute('aria-disabled','true');});const ticket=epoch,id=piece.id;
  try{await action();if(ticket!==epoch||!ctx.active(id))return;st.dismissed=false;progress=null;await reload();}
  catch(e){if(ticket!==epoch||!ctx.active(id))return;if(['revision_conflict','roughcut_inputs_stale'].includes(e.code)){await reload();localNotice=noticeForFailure(e);repaint();}else handleError(e);}
  finally{if(ticket===epoch){busy=false;if(data&&caps&&library){repaint();schedule();}}}
 }
 async function sendCommand(c){
  lastCommand=structuredClone(c);
  return request(base()+'/roughcut/commands',{method:'POST',body:{expectedRevision:data.revision,projectRevision:data.project_revision,selectionDigest:data.source_summary.selection_digest,command:c}});
 }
 const command=c=>perform(()=>sendCommand(c));
 function reanalyze(){
  const retry=lastCommand||(!data.plan&&data.selection.playlist.length?{type:'select_music',track_ids:data.selection.playlist.map(s=>s.track_id)}:null);
  const trackId=data.failure?.details.track_id||data.analysis.find(a=>a.failure)?.track_id||retry?.track_id||data.selection.playlist[0]?.track_id;
  return perform(async()=>{const ticket=epoch,id=piece.id;
   await request(`/api/review/music/${encodeURIComponent(trackId)}/reanalyze`,{method:'POST',body:{part:'beat'}});
   if(ticket!==epoch||!ctx.active(id))return;
   if(!await reload()||ticket!==epoch||!ctx.active(id))return;
   if(!retry)throw Object.assign(new Error('failed command unavailable'),{code:'roughcut_command_invalid'});
   await sendCommand(retry);
  });
 }
 const setEditor=key=>perform(async()=>{const opt=caps.editors.find(e=>e.id===(key==='otio_kdenlive'?'kdenlive':key));if(!opt||caps.choice.error)return;
  await request(`/api/projects/${encodeURIComponent(piece.id)}`,{method:'PATCH',body:{expectedRevision:caps.project_revision,videoEditor:{...opt.choice,revision:caps.choice.revision}}});st.editorOpen=false;await ctx.refreshCatalog();});
 function openOcc(key){const o=P.occ.find(x=>x.key===key);if(!o)return;st.occ=key;st.sel=o.tech;st.swapOpen=false;repaint();seek(Math.max(0,startOf(o)-2));}
 function openSwap(index=1){st.swapIndex=index;st.swapOpen=true;st.occ=null;st.sel=null;repaint();seek(Math.max(0,P.swap.at-2));}
 function applyLayout(){
  // The Studio CSP rejects style attributes parsed from HTML templates.
  $$('[data-cut-left]').forEach(el=>el.style.left=el.dataset.cutLeft);
  $$('[data-cut-width]').forEach(el=>el.style.width=el.dataset.cutWidth);
  $$('[data-cut-size]').forEach(el=>el.style.setProperty('--ev-size',el.dataset.cutSize));
  $$('[data-cut-frame]').forEach(el=>el.style.backgroundImage=`url(${JSON.stringify(el.dataset.cutFrame)})`);
 }
 function bind(){
  ctx.bindTabs?.();
  applyLayout();
  $$('[data-style]').forEach(b=>b.onclick=()=>{st.lib=false;st.occ=null;st.sel=null;st.swapOpen=false;command({type:'apply_preset',preset_id:b.dataset.style,preset_revision:STYLES[b.dataset.style].revision});});
  $('[data-editor-open]')?.addEventListener('click',()=>{st.editorOpen=!st.editorOpen;repaint();});
  $('[data-editor-x]')?.addEventListener('click',()=>{st.editorOpen=false;repaint();});
  $$('[data-editor-pick]').forEach(b=>b.onclick=()=>setEditor(b.dataset.editorPick));
  $('[data-lib]')?.addEventListener('click',()=>{st.lib=true;st.libCat='全部';repaint();});
  $('[data-lib-x]')?.addEventListener('click',()=>{st.lib=false;repaint();});
  $$('[data-cat]').forEach(b=>b.onclick=()=>{st.libCat=b.dataset.cat;repaint();});
  $('[data-add-song]')?.addEventListener('click',()=>{st.songMode='add';repaint();});
  $$('[data-replace-song]').forEach(b=>b.onclick=()=>{st.replaceSong=+b.dataset.replaceSong;st.songMode='replace';repaint();});
  $('[data-song-x]')?.addEventListener('click',()=>{st.songMode=null;repaint();});
  $$('[data-song-use]').forEach(b=>b.onclick=()=>{const c=st.songMode==='replace'?{type:'replace_song',song_instance_id:data.plan.songs[st.replaceSong].id,track_id:b.dataset.songUse}:data.plan?{type:'add_song',track_id:b.dataset.songUse}:{type:'select_music',track_ids:[b.dataset.songUse]};st.songMode=null;command(c);});
  $$('[data-remove-song]').forEach(b=>b.onclick=()=>command({type:'remove_song',song_instance_id:data.plan.songs[+b.dataset.removeSong].id}));
  $('[data-save]')?.addEventListener('click',()=>perform(async()=>{const basePreset=library.presets.find(p=>p.id===st.style);const r=await request('/api/review/editing-presets',{method:'POST',body:{expectedRevision:library.revision,piece_id:piece.id,roughcut_revision:data.revision,base_preset_id:basePreset.base_preset_id||basePreset.id,overrides:data.selection.technique_overrides}});
    await request(base()+'/roughcut/commands',{method:'POST',body:{expectedRevision:data.revision,projectRevision:data.project_revision,selectionDigest:data.source_summary.selection_digest,command:{type:'apply_preset',preset_id:r.preset.id,preset_revision:r.preset.revision}}});}));
  $('[data-restore]')?.addEventListener('click',()=>command({type:'reset_customization'}));
  $$('[data-retry-library]').forEach(b=>b.onclick=()=>perform(()=>request('/api/review/editing-presets')));
  $('[data-dismiss-rearrange]')?.addEventListener('click',()=>{st.dismissed=true;repaint();});
  $$('[data-settings]').forEach(b=>b.onclick=()=>ctx.go({view:'settings',tab:'tools'}));
  $$('[data-music-library]').forEach(b=>b.onclick=()=>ctx.go({view:'music'}));
  $('[data-stop]')?.addEventListener('click',()=>perform(()=>request(`/api/review/roughcut-jobs/${encodeURIComponent(data.job.job_id)}`,{method:'POST',body:{action:'stop',expectedRevision:data.revision}})));
  $('[data-draft]')?.addEventListener('click',startDraft);
  $$('[data-draft-open]').forEach(b=>b.onclick=()=>{if(data.draft?.can_open)return perform(()=>request(base()+'/roughcut/drafts/open',{method:'POST',body:draftBinding(data.draft.edl_digest)}));});
  $('[data-transcribe]')?.addEventListener('click',transcribe);
  $$('[data-failure-action]').forEach(b=>b.onclick=()=>actionByLabel(b.dataset.failureAction));
  $$('[data-notice-action]').forEach(b=>b.onclick=()=>actionByLabel(b.dataset.noticeAction));
  $$('[data-audition]').forEach(b=>b.onclick=()=>{const track=tracks.find(t=>t.id===b.dataset.audition),audio=document.querySelector('#music-player');if(audio.dataset.id!==track.id){audio.src=track.audio;audio.dataset.id=track.id;}if(audio.paused)audio.play().catch(()=>handleError({code:'preview_failed'}));else audio.pause();});
  $('#play')?.addEventListener('click',toggle);$('[data-from0]')?.addEventListener('click',()=>{seek(0);toggle(true);});
  $('#tlbody')?.addEventListener('click',e=>{if(e.target.closest('[data-occ],[data-clip],.cut-beat-map'))return;const r=e.currentTarget.getBoundingClientRect();seek((e.clientX-r.left)/r.width*P.total);});
  $$('[data-clip]').forEach(b=>b.onclick=()=>seek(P.clips[+b.dataset.clip-1].start));
  $$('[data-occ]').forEach(b=>b.onclick=()=>openOcc(b.dataset.occ));
  $$('.tl2-labs [data-pick]').forEach(b=>b.onclick=()=>{st.sel=st.sel===b.dataset.pick?null:b.dataset.pick;repaint();});
  $$('.tl2-labs [data-pick]').forEach(b=>b.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();b.click();}});
  for(const [selector,close] of [['#libov',()=>st.lib=false],['#songov',()=>st.songMode=null]]){const overlay=$(selector);if(overlay)overlay.onclick=e=>{if(e.target===overlay){close();repaint();}};}
  ctx.root().onkeydown=e=>{if(e.key==='Escape'){st.editorOpen=false;st.lib=false;st.songMode=null;repaint();$('[data-editor-open]')?.focus();}
   if(e.key==='Tab'){const dialog=$$('.ov:not([hidden]),.editor-pop').at(-1);if(!dialog)return;const nodes=[...dialog.querySelectorAll('button:not(:disabled),[tabindex="0"]')];const first=nodes[0],last=nodes.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
  };
 }
 function bindPanel(){
  applyLayout();
  $$('[data-sw]').forEach(b=>b.onclick=()=>command({type:'set_technique',id:b.dataset.sw,enabled:!P.on.has(b.dataset.sw)}));
  $$('#panel [data-pick]').forEach(b=>b.onclick=()=>{st.sel=st.sel===b.dataset.pick?null:b.dataset.pick;repaint();});
  $$('[data-first]').forEach(b=>b.onclick=()=>openOcc(P.occ.find(o=>o.tech===b.dataset.first&&o.live)?.key));
  $('[data-back]')?.addEventListener('click',()=>{st.occ=null;st.sel=null;st.swapOpen=false;repaint();});
  $$('[data-step]').forEach(b=>b.onclick=()=>{const o=P.occ.find(x=>x.key===st.occ),list=P.occ.filter(x=>x.tech===o.tech);openOcc(list[list.indexOf(o)+ +b.dataset.step]?.key);});
  $('[data-play-occ]')?.addEventListener('click',()=>{seek(Math.max(0,P.occ.find(o=>o.key===st.occ).at-2));toggle(true);});
  $('[data-play-swap]')?.addEventListener('click',()=>{seek(Math.max(0,P.swap.at-2));toggle(true);});
  $$('[data-swap-to]').forEach(b=>b.onclick=()=>{const c=P.cands.find(c=>c.idx===+b.dataset.swapTo);command({type:'move_swap',swap_id:P.swap.id,before_shot_id:c.before_shot_id});});
  $('[data-skip]')?.addEventListener('click',()=>command({type:'set_occurrence',id:st.occ,enabled:false}));
  $('[data-unskip]')?.addEventListener('click',()=>command({type:'set_occurrence',id:st.occ,enabled:true}));
 }
 const draftBinding=edlDigest=>({expectedRevision:data.revision,projectRevision:data.project_revision,editorChoiceRevision:caps.choice.revision,edlDigest});
 const startDraft=()=>perform(()=>request(base()+'/roughcut/drafts',{method:'POST',body:draftBinding(data.plan_input_binding.edl_digest)}));
 function transcribe(){perform(()=>request(base()+'/roughcut/transcriptions',{method:'POST',body:{expectedRevision:data.revision,selectionDigest:data.source_summary.selection_digest,shot_ids:data.warnings?.missing_word_shot_ids||[]}}));}
 function actionByLabel(label){if(label==='去设置')return ctx.go({view:'settings',tab:'tools'});if(label==='回去挑镜头')return ctx.go({view:'piece',piece:piece.id,ptab:'vlog'});
  if(label==='换一首歌'){if(data.plan){st.songMode='replace';st.replaceSong=0;repaint();}else {st.state='cut-no-music';renderPick(ctx.root());}return;}
  if(label==='重新分析')return reanalyze();
  if(label==='重新转写')return transcribe();if(label==='知道了'){localNotice=null;repaint();return;}
  if(label==='重试'&&localNotice?.title===noticeForFailure({code:'preview_failed'}).title){failedPreviewId=null;return reload();}
  if(label==='重试'&&data.draft?.status==='failed')return startDraft();
  if(label==='重试'&&lastAction)return perform(lastAction);return reload().catch(handleError);
 }
 async function mountMusic(){if(!P)return;const generation=epoch,container=$('#cut-beat-map');if(!container)return;
  try{beatLoader ||= ctx.mountBeatMap?Promise.resolve({mountBeatMap:ctx.mountBeatMap}):import('/beat-map.js');const {mountBeatMap}=await beatLoader;if(generation!==epoch||!container.isConnected)return;
   beatView=mountBeatMap(container,beatMapOptions(data,st.sel,st.swapOpen?st.swapIndex:null,seek,openSwap));
  }catch(e){if(generation!==epoch||!container.isConnected)return;console.error('R226 beat map unavailable',e);const n=noticeForFailure({code:'beat_analysis_unavailable'});container.innerHTML=attention('R226-NOTICE',n.title,n.body,'<button class="btn" data-settings>去设置</button>');container.querySelector('[data-settings]').onclick=()=>ctx.go({view:'settings',tab:'tools'});}
 }
 function previewArtifact(){return data?.playback.status==='ready'&&data.playback.preview_artifact_id!==failedPreviewId?data.artifacts.find(a=>a.id===data.playback.preview_artifact_id&&a.kind==='preview'):null;}
 async function previewError(video){
  const ticket=epoch,id=piece.id,url=video.getAttribute('src');if(!video.isConnected)return;
  video.pause();video.removeAttribute('src');video.load();st.playing=false;
  try{
   // A media element hides the HTTP status. Probe only on error to distinguish
   // a revision-invalidated preview from a failed encode without buffering video.
   const response=await fetch(url,{headers:{Range:'bytes=0-0'},credentials:'same-origin'});await response.body?.cancel();
   if(ticket!==epoch||!ctx.active(id))return;
   if(response.status===409){await reload();return;}
  }catch{if(ticket!==epoch||!ctx.active(id))return;}
  failedPreviewId=video.dataset.artifactId;handleError({code:'preview_failed'});
 }
 function paintTime(){if(!P||!$('#stage'))return;const c=clipAt(st.t),stage=$('#stage'),artifact=previewArtifact(),available=!!artifact;
  if(available){if(!stage.querySelector('video')){
   const v=document.createElement('video');v.src=artifact.url;v.dataset.artifactId=artifact.id;v.playsInline=true;stage.replaceChildren(v);
   const current=()=>v.isConnected&&previewArtifact()?.id===v.dataset.artifactId;
   v.ontimeupdate=()=>{if(current()){st.t=v.currentTime;st.playing=!v.paused;paintTime();}};
   v.onplay=v.onpause=v.onended=()=>{if(current()){st.playing=!v.paused;paintTime();}};
   v.onloadedmetadata=()=>{if(current()&&st.t>0)v.currentTime=Math.min(st.t,v.duration);};
   v.onerror=()=>{if(current())void previewError(v);};
  }}else {const frame=frameOf(c.shot);stage.innerHTML=frame?`<img src="${esc(frame)}" alt="">`:'';}
  const act=activeAt(st.t),src=c.shot.kind==='photo'?'照片':`原片第 ${s1(c.srcIn)}–${s1(c.source_end)} 秒`,song=P.songs.length>1?` · 配乐《${songOf(st.t).track.title}》`:'';
  $('#nowbox').innerHTML=`<small>此刻</small><p>第 ${D(c.n)} / ${D(data.plan.metrics.shot_count)} 个镜头 · ${D(SCENES[c.shot.scene]||c.shot.scene_name)} · ${D(src)}${D(song)}</p>${act.length?`<div class="tags">${act.map(o=>`<span class="tq-tag ${T[o.tech].fam==='snd'?'snd':''}">${T[o.tech].name}</span>`).join('')}</div>`:'<span class="none">这一段没有用剪辑手法</span>'}`;
  $('#pos').innerHTML=`${D(mmss(st.t))} / ${D(mmss(P.total))}`;$('#play').disabled=!available;$('#play').setAttribute('aria-disabled',String(!available));$('#play').textContent=st.playing?'❚❚':'▶';
  $('[data-from0]').disabled=!available;$('#ph').style.left=pct(st.t);beatView?.setTime(st.t);$$('.blk').forEach(b=>b.setAttribute('aria-current',String(+b.dataset.clip===c.n)));
 }
 function seek(t){if(!P)return;st.t=Math.max(0,Math.min(P.total,t));const video=$('#stage video');if(video)video.currentTime=st.t;paintTime();}
 function toggle(force){const video=$('#stage video');if(!video)return;if(force===true||video.paused)video.play().catch(()=>handleError({code:'preview_failed'}));else video.pause();}
 function stop(){epoch++;busy=false;lastCommand=null;pollVersion++;clearTimeout(poll);beatView?.destroy();beatView=null;$('#stage video')?.pause();if(ctx.root())ctx.root().onkeydown=null;}
 return {stop,async render(p,html){stop();piece=p;tabs=html;st={state:'cut-no-music',t:0,sel:null,occ:null,swapOpen:false,swapIndex:1,lib:false,libCat:'全部',songMode:null,editorOpen:false,off:new Set(),add:new Set(),playing:false};localNotice=null;lastAction=null;progress=null;failedPreviewId=null;data=null;await reload();}};
}
