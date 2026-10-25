import { createShotView, seconds } from '/review-shots.js';
import { createDirectView } from '/direct-view.js';
import { createMusicView } from '/review-music.js';
import {mediaSummary, diagnosticGroups, checkedTime, sec} from '/review-common.js';
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
export const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const D = v => `<span data-design-data>${esc(v)}</span>`;
export const button = (text, attrs='', pri=false) => `<button class="btn${pri?' btn--pri':''}" ${attrs}>${text}</button>`;
export const icons = {
 home:'<path d="M15 21v-8h-6v8M3 10l9-8 9 8v11H3z"/>',
 inbox:'<path d="M2 12h6l2 3h4l2-3h6M2 12l4-8h12l4 8v8H2z"/>',
 projects:'<path d="M2 20V3h7l4 3h9v14z"/>',
 library:'<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m6 21 10-10 5 5"/>',
 music:'<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
 settings:'<path d="M20 7h-9M14 17H5"/><circle cx="17" cy="17" r="3"/><circle cx="7" cy="7" r="3"/>',
 places:'<line x1="22" x2="2" y1="12" y2="12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><line x1="6" x2="6.01" y1="16" y2="16"/><line x1="10" x2="10.01" y1="16" y2="16"/>',
 tools:'<circle cx="6" cy="6" r="3"/><path d="M8.12 8.12 12 12"/><path d="M20 4 8.12 15.88"/><circle cx="6" cy="18" r="3"/><path d="M14.8 14.8 20 20"/>',
 models:'<rect width="16" height="16" x="4" y="4" rx="2"/><rect width="6" height="6" x="9" y="9" rx="1"/><path d="M15 2v2"/><path d="M15 20v2"/><path d="M2 15h2"/><path d="M2 9h2"/><path d="M20 15h2"/><path d="M20 9h2"/><path d="M9 2v2"/><path d="M9 20v2"/>',
 account:'<path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>',
 download:'<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
 doctor:'<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>'
};
export const icon = key => `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${icons[key]||icons.settings}</svg>`;

export function createStudio(ctx) {
 const {state,api,notice,openProjectDialog,openSurface,renderProject,renderInbox,loadLibrary,loadInboxPlan,loadDeleteRecommendations}=ctx;
 let route={view:'home'}, catalog={groups:[],pieces:[]}, request=0;
 let shots, music, direct, assetCategory='', musicSettings;
 const root=()=>$('#review-screen');
 const piece=id=>catalog.pieces.find(p=>p.id===id);
 const issues=()=>diagnosticGroups(state.diagnostics?.checks||[]).issues;
 const pending=()=>catalog.pieces.filter(p=>p.pending);
 const media=p=>mediaSummary(p,D);
 const frame=s=>s.frames[Math.floor(s.frames.length/2)]||'';
 function top(title,sub='',actions='',crumb='') {
  $('#screen-title').innerHTML=title; $('#screen-sub').innerHTML=sub; $('#screen-sub').hidden=!sub;
  $('#crumb').innerHTML=crumb; $('#top-actions').innerHTML=actions;
  $('.main > .topbar .topbar-actions').hidden=false;
 }
 function mark(name){$('.main').dataset.designState=name;const ids={home:'R208-HOME-recent',inbox:'R208-INBOX-empty',projects:'R208-PROJECTS',project:'R208-PROJECT-pieces',library:'R208-LIBRARY','library-empty':'R208-LIBRARY-empty'};$('.topbar').dataset.designId=ids[name]||(name.startsWith('settings-')?'R208-SETTINGS':name.startsWith('music')?'R208-MUSIC-import':'R208-REV-topbar');root().className='review-screen';}
 function nav() {
  const count=pending().length+issues().length;
  $$('.nav [data-nav]').forEach(b=>b.setAttribute('aria-current', String(b.dataset.nav===(['piece','project'].includes(route.view)?'projects':route.view))));
  $('#home-count').textContent=count; $('#home-count').hidden=!count;
  const upstream=state.settings?.upstream;
  $('#upstream-state').textContent=state.settingsError?state.settingsError:upstream?(upstream.upstream_features_available?'上游中台已连接':'上游中台未连接'):'无法读取本机记录';
 }
 function common() {
  $$('[data-go]').forEach(b=>b.onclick=()=>go({view:b.dataset.go}));
  $$('[data-go-project]').forEach(b=>b.onclick=()=>go({view:'project',project:b.dataset.goProject}));
  $$('[data-piece]').forEach(b=>{b.onclick=()=>go({view:'piece',piece:b.dataset.piece});b.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();b.click();}};});
  $$('[data-piece-go]').forEach(b=>b.onclick=()=>go({view:'piece',piece:b.dataset.pieceGo}));
  $$('[data-set]').forEach(b=>b.onclick=()=>go({view:'settings',tab:b.dataset.set}));
  $$('[data-new]').forEach(b=>b.onclick=openProjectDialog);
  $$('[data-versions]').forEach(b=>b.onclick=e=>{e.stopPropagation();openVersions(piece(b.dataset.versions));});
 }
 function card(p,withProject=false) {
  const group=catalog.groups.find(g=>g.id===p.group_id);
  const status=p.pending?'挑镜头 · 等你过目':p.versions?`已出 ${D(p.versions)} 版`:p.videos||p.photos?'素材已归档':'';
  const chip=status?`<span class="chip">${status}</span>`:'';
  const play=p.versions?`<button class="playv" data-versions="${esc(p.id)}">看成片</button>`:'';
  return `<article class="piece ${p.cover?'':'piece--compact'}" role="link" tabindex="0" data-piece="${esc(p.id)}">${p.cover?`<div class="cover"><img src="${esc(p.cover)}" alt="" loading="lazy">${chip}${play}</div>`:''}<div class="piece-body"><b data-design-data>${esc(p.title)}</b><small>${[withProject?D(group?.title):'',p.date?D(p.date):'',`<span>${media(p)}</span>`].filter(Boolean).join(' · ')}</small>${p.cover||(!chip&&!play)?'':`<div class="chips">${chip}${play}</div>`}</div></article>`;
 }
 function capabilities() {
  const checks=state.diagnostics?.checks||[],ready=id=>checks.some(c=>c.id===id&&c.status==='ready');
  const tools=ready('edit_tool_openchatcut')&&ready('edit_tool_openfilm');
  const egress=musicSettings.egress;
  return [['剪映',ready('jianying')?'可用':'没装好'],['ChatCut',ready('chatcut_mcp')?'可用':'没连上'],['OpenChatCut、OpenFilm',tools?'装在本仓库里，可用':'没装好'],['创意和看图模型',ready('creative_provider')?'Codex 可用':ready('creative_model')?'可用':'没配置'],['音乐下载',egress.state==='configured'?'经广州服务器，可用':egress.state==='unreadable'?D(egress.reason):'没配置出口']].map(([name,value])=>`<div class="cap-row"><i class="dot ${['可用','装在本仓库里，可用','Codex 可用','经广州服务器，可用'].includes(value)?'dot--ok':''}"></i><div>${name}<small>${value}</small></div></div>`).join('');
 }
 async function home() {
  mark('home'); top('工作台','等你处理的事和最近的作品',button('新建作品','data-new',true));
  const need=pending(); const checks=issues();
  const reviews=await Promise.all(need.map(p=>api(`/api/review/pieces/${encodeURIComponent(p.id)}/shots`)));
  if(route.view!=='home')return;
  root().innerHTML=(need.length+checks.length?`<section class="full" data-design-id="R208-HOME-todo"><h2 class="section-title">等你处理<span>${D(need.length+checks.length)} 件</span></h2><div class="todo">${need.map((p,i)=>`<div class="task task--review"><div><strong>${D(p.title)}：挑镜头做完了</strong><p>${D(p.selected)} 个精选等你过目。</p><div class="thumbs5">${reviews[i].hook_candidates.slice(0,5).map(h=>reviews[i].shots.find(s=>s.id===h.id)).filter(Boolean).map(s=>`<img src="${esc(frame(s))}" alt="">`).join('')}</div></div><div class="actions"><button class="btn btn--play" data-reel="${esc(p.id)}">预览精选</button>${button('去过目',`data-piece-go="${esc(p.id)}"`,true)}</div></div>`).join('')}${checks.map(c=>`<div class="task"><div><strong>${c.title}</strong><p>${c.note}</p></div>${button('去设置','data-set="doctor"')}</div>`).join('')}</div></section>`:'')+`<section data-design-id="R208-HOME-recent"><h2 class="section-title">最近的作品<span>${D(Math.min(8,catalog.pieces.length))} 件</span></h2><div class="pieces">${catalog.pieces.slice(0,8).map(p=>card(p,true)).join('')}</div></section><aside class="cap" data-design-id="R208-HOME-cap"><h3>本机能力</h3>${capabilities()}${button('设置与诊断','data-set="doctor"')}</aside>`;
  common();$$('[data-reel]').forEach(b=>b.onclick=async()=>{const r=await api(`/api/review/pieces/${b.dataset.reel}/shots`);openReel(piece(b.dataset.reel),r);});
 }
 function projects() {
  mark('projects');root().classList.add('single');top('项目',`${D(catalog.groups.length)} 个项目 · ${D(catalog.pieces.length)} 件作品`,button('新建作品','data-new',true));
  root().innerHTML=`<div class="projects" data-design-id="R208-PROJECTS">${catalog.groups.map(g=>{const covers=g.pieces.map(p=>p.cover).filter(Boolean).slice(0,3);return `<button class="proj ${covers.length?'':'proj--compact'}" data-go-project="${esc(g.id)}">${covers.length?`<div class="collage ${covers.length<3?'one':''}">${(covers.length<3?covers.slice(0,1):covers).map(c=>`<img src="${esc(c)}" alt="">`).join('')}</div>`:''}<div><h2 data-design-data>${esc(g.title)}</h2><p>${D(g.count)} 件作品</p><div class="chips">${g.pending?`<span class="chip">${D(g.pending)} 件等你过目</span>`:''}${g.produced?`<span class="chip">${D(g.produced)} 件出过成片</span>`:''}</div></div><i>›</i></button>`;}).join('')}</div>`;common();
 }
 function project() {
  mark('project');root().classList.add('single');const g=catalog.groups.find(g=>g.id===route.project);if(!g){projects();return;}
  top(D(g.title),'',button('添加作品','data-new'),'<button data-go="projects">项目</button>');
  root().innerHTML=`<section data-design-id="R208-PROJECT-pieces"><h2 class="section-title">作品<span>${D(g.count)} 件</span></h2><div class="pieces">${g.pieces.map(p=>card(p)).join('')}</div></section>`;common();
 }
 async function work() {
  const p=piece(route.piece);if(!p){projects();return;}
  const data=await api(`/api/projects/${encodeURIComponent(p.id)}`);if(route.view!=='piece'||route.piece!==p.id)return; state.project=data.project;state.videoHandoff=data.videoHandoff||null;
  let tab=route.ptab;
  if(!tab){try{tab=localStorage.getItem('studio-piece-tab:'+p.id);}catch{ /* Storage is optional. */ }}
  tab=['vlog','script','direct'].includes(tab)?tab:state.videoHandoff?'script':'vlog';
  route.ptab=tab;
  top(D(p.title),p.date?D(p.date):'',p.versions?button('看已出的成片 '+D(p.outputs.map(o=>o.version).filter((v,i,a)=>a.indexOf(v)===i).join(' · ')),`data-versions="${esc(p.id)}"`):'',`<button data-go="projects">项目</button>›<button data-go-project="${esc(p.group_id)}" data-design-data>${esc(catalog.groups.find(g=>g.id===p.group_id)?.title)}</button>`);
  $('#crumb').parentElement.dataset.designId='R208-REV-topbar';
  const tabs=`<nav class="ptabs" role="tablist" aria-label="做法" data-design-id="R208-PIECE-tabs">${[['vlog','按素材剪 vlog'],['script','按脚本做视频'],['direct','脚本直出']].map(([key,label])=>`<button role="tab" data-ptab="${key}" aria-selected="${tab===key}">${label}</button>`).join('')}</nav>`;
  root().classList.add('single');root().innerHTML=tabs;
  if(tab==='script') {mark('piece-script');root().classList.add('single');$('[data-screen-panel="project"]').hidden=false;renderProject();$('[data-screen-panel="project"]').dataset.designId='R208-PIECE-script';}
  else if(tab==='direct') {await direct.render(p,tabs);}
  else {await shots.render(p,tabs);}
  $$('[data-ptab]').forEach(b=>b.onclick=()=>{try{localStorage.setItem('studio-piece-tab:'+p.id,b.dataset.ptab);}catch{}go({...route,ptab:b.dataset.ptab});});common();
 }
 async function inbox() {
  if(state.project)await Promise.all([loadInboxPlan(),loadDeleteRecommendations()]);
  if(route.view!=='inbox')return;
  mark('inbox');root().classList.add('single');top('整理台','新导入的素材先在这里分批，再放进项目',button('导入照片和视频','data-new',true));
  if(state.inboxPlan?.batches?.length || state.deleteCandidates.length || (state.project&&(state.inboxPlanError||state.deleteError))){root().innerHTML='';$('[data-screen-panel="inbox"]').hidden=false;renderInbox();return;}
  root().innerHTML=`<div class="empty" data-design-id="R208-INBOX-empty"><h2>没有要整理的新素材</h2><p>从手机或相机导入的照片和视频，会按拍摄时间和地点自动分成一批批放在这里，你决定每一批放进哪个项目。太短、损坏、完全重复的会列出来让你勾选删除。原文件不会被改动。</p><div class="facts"><span>已整理进项目的作品<b data-design-data>${catalog.pieces.length}</b>件</span><span>视频<b data-design-data>${catalog.pieces.reduce((a,p)=>a+p.videos,0)}</b>段</span><span>照片<b data-design-data>${catalog.pieces.reduce((a,p)=>a+p.photos,0)}</b>张</span></div><div class="actions">${button('导入照片和视频','data-new',true)}${button('去看项目','data-go="projects"')}</div></div>`;common();
 }
 function row(title,note='',value='') {return `<div class="setrow"><div><strong>${title}</strong>${note?`<small>${note}</small>`:''}</div><span class="val">${value}</span></div>`;}
 const setTabs=[['places','存放位置'],['tools','剪辑软件'],['models','模型'],['music','音乐下载'],['account','上游账号'],['doctor','诊断']];
 async function settings() {
  if(route.view!=='settings')return;
  const tab=setTabs.some(t=>t[0]===route.tab)?route.tab:'tools';route.tab=tab;mark('settings-'+tab);root().classList.add('single');top('设置与诊断','本机配置与可选连接');
  if(state.settingsError)throw new Error(state.settingsError);
  const settings=state.settings||{},checks=state.diagnostics?.checks||[];const budget=state.analysisBudget?.budget||{};
  let body='';
  if(tab==='places')body=`<h3>存放位置</h3><p>素材、成片、音乐都在本机这个文件夹里，不上传。</p>${row('素材根',`${D(catalog.groups.length)} 个项目 · ${D(catalog.pieces.length)} 件作品`)}${row('音乐库','',`${D((await api('/api/review/music')).tracks.length)} 首`)}${row('素材库','',`${D(state.assetStatistics?.asset_count||0)} 项`)}<h3 class="set-actions">归档生命周期与物理位置</h3><p>每个物理位置独立保留清单与回读状态。</p>${row('生命周期',D(settings.archive?.lifecycle||''))}${(settings.archive?.locations||[]).map(x=>row(D(x.label||x.name),D(x.status||''))).join('')}`;
  if(tab==='models')body=`<h3>模型</h3><p>写脚本、挑镜头时看图都用这里的模型。密钥只存本机。</p>${row('创意和看图',(settings.model_providers||[]).map(p=>D(p.display_name||p.provider_id||p.model)).join(' · '),D((settings.model_providers||[]).length))}<div class="set-actions">${button('添加模型','data-add-provider')}</div>${row('音频转写','默认使用阿里云在线转写。音频会发送给阿里云；请求失败后才尝试已安装的本机 FunASR。','阿里云在线转写')}<h3 class="set-actions">分析预算</h3><p>分析档位和预算由本机配置读取，耗尽后应显示明确状态而非静默降级。</p>${[['preview_images_per_asset','每素材预览图'],['deep_images_per_asset','每素材深度图'],['max_preview_assets','预览素材上限'],['max_deep_assets','深度素材上限'],['max_audio_minutes','音频分钟上限']].map(([key,label])=>row(label,D(budget[key]||0),`<div class="segmented"><button data-budget="${key}" data-delta="-1" aria-label="减少 ${label}">−</button><button data-budget="${key}" data-delta="1" aria-label="增加 ${label}">+</button></div>`)).join('')}<div class="set-actions">${button('保存预算','data-save-budget',true)}</div>`;
  if(tab==='account')body=`<h3>上游账号</h3><p>连上后能在网页中台看任务进度。不连也不影响本机创作。</p>${row('上游中台',settings.upstream?.upstream_features_available?'这台 Mac 已配对':'',state.settingsError?D(state.settingsError):settings.upstream?.upstream_features_available?'已连接':'未连接')}<div class="set-actions">${button('上游账号','data-pair')}${button('解除配对','data-unpair')}${button('打开网页中台','data-cloud')}</div>`;
  if(tab==='music') {
   const info=await api('/api/review/music-settings');
   const label=(x,kind='account')=>x.state==='unreadable'?D(x.reason):x.state==='configured'?'已配置':kind==='egress'?'没配置':'没登录';
   body=`<h3>音乐下载</h3><p>只在你粘贴链接时下载那一首，不批量抓取。</p>${row('下载出口',info.egress.state==='absent'?'网易云音乐、汽水音乐要经出口服务器下载，先配置出口':'网易云音乐、汽水音乐经广州服务器下载',label(info.egress,'egress'))}${row('汽水音乐','匿名取不到音乐','可用')}${row('网易云账号','没登录也能下免费歌曲；会员歌曲下载不了',info.account.state==='configured'?'已登录':label(info.account))}${row('抖音','','暂不支持')}`;
  }
  if(tab==='tools')body=`<h3>剪辑软件</h3><p>出草稿时 ChatCut 连上就用 ChatCut，否则用剪映。没连上的不会被悄悄换掉，会在工作台提醒你。</p>${checks.filter(c=>/chatcut|jianying|kdenlive|edit_tool/.test(c.id)).map(c=>row(D(c.summary),D(c.repair||''),c.status==='ready'?'可用':'没连上')).join('')}<div class="set-actions">${button('重新检查','data-recheck')}</div>`;
  if(tab==='doctor') {
   const {good,optional,issues:bad}=diagnosticGroups(checks),total=good.length+bad.length;
   body=`<header class="dx-hero"><div class="dx-ring" data-design-data data-ratio="${total?good.length/total:0}" role="img" aria-label="${total} 项里 ${good.length} 项正常"><b>${good.length}<i>/${total}</i></b></div><div class="dx-hero-t"><h3>${bad.length?`有 ${D(bad.length)} 项需要处理`:'本机环境一切正常'}</h3><p>${bad.length?`其余 <em>${D(good.length)} 项正常</em> · `:''}${D(checkedTime(state.diagnostics.checked_at))} 检查</p></div></header>${bad.map(c=>`<section class="dx-issue" role="alert"><div class="dx-issue-top"><span class="dx-tile">${icon('tools')}</span><div><h4>${c.id==='chatcut'?'ChatCut Desktop 还没连上本机':c.title}</h4><p>${c.id==='chatcut'?'没连上之前，出草稿只能用剪映。':'出草稿要用到它们，现在还没装在本仓库里。'}</p></div></div><ol class="dx-steps"><li><b>1</b><div>${c.id==='chatcut'?'在 ChatCut 里开启本机连接':`复制下面这条命令，在仓库目录的终端里运行${c.commands.map((command,i)=>`<div class="command"><code data-design-data>${esc(command)}</code>${button('复制',`data-copy-command="${i}"`)}</div>`).join('')}`}</div></li><li><b>2</b>回到这里点「重新检查」</li></ol><div class="dx-issue-act">${button('重新检查','data-recheck',true)}${c.id==='chatcut'?button('剪辑软件设置','data-set="tools"'):''}</div></section>`).join('')}${optional.length?`<section class="dx-group"><h4>可选</h4><ul class="dx-list dx-optional">${optional.map(c=>`<li><i class="dot"></i><span data-design-data>${esc(c.summary)}${c.repair?' · '+esc(c.repair):''}</span></li>`).join('')}</ul></section>`:''}<section class="dx-group"><h4>运行正常 <span data-design-data>${good.length}</span></h4><ul class="dx-list">${good.map(c=>`<li><span class="dx-tile">${icon(c.id==='creative_provider'?'models':c.id==='jianying'||c.id==='kdenlive'?'tools':'doctor')}</span><div><b data-design-data>${esc(c.summary)}</b><small data-design-data>${esc(c.repair||'')}</small></div><span class="dx-ok" aria-label="正常"><svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="m20 6-11 11-5-5"/></svg></span></li>`).join('')}</ul></section><footer class="dx-foot"><small>出问题时把报告复制给开发者。</small><div class="set-actions">${button('复制报告','data-copy-report')}${button('重新跑安装向导','data-wizard')}</div></footer>`;
  }
  if(route.view!=='settings'||route.tab!==tab)return;
  root().innerHTML=`<section class="settings" data-design-id="R208-SETTINGS"><nav class="set-nav" aria-label="设置分类"><span class="set-group">设置</span>${setTabs.map(([key,label],i)=>`${i===5?'<span class="set-group">检查</span>':''}<button data-set="${key}" aria-current="${tab===key}">${icon(key==='music'?'download':key)}${label}${['tools','doctor'].includes(key)&&issues().length?'<i class="dot dot--warn" aria-hidden="true"></i>':''}</button>`).join('')}</nav><div class="set-main">${body}</div></section>`;common();
  $$('[data-copy-command]').forEach(b=>b.onclick=()=>navigator.clipboard.writeText(b.previousElementSibling.textContent).catch(e=>notice(e.message,true)));
  const ring=$('.dx-ring');if(ring)ring.style.setProperty('--p',ring.dataset.ratio);
  $('[data-add-provider]')?.addEventListener('click',()=>notice('模型配置需要提供方、模型、端点和本机密钥引用。'));
  $('[data-pair]')?.addEventListener('click',()=>openSurface('login'));
  $('[data-unpair]')?.addEventListener('click',()=>$('#logout-upstream').click());
  $('[data-cloud]')?.addEventListener('click',()=>openSurface('cloud'));
  $('[data-wizard]')?.addEventListener('click',()=>openSurface('setup'));
  $('[data-copy-report]')?.addEventListener('click',()=>navigator.clipboard.writeText(JSON.stringify(state.diagnostics,null,2)).catch(e=>notice(e.message,true)));
  $$('[data-recheck]').forEach(b=>b.onclick=async()=>{await loadDiagnostics(true);await settings();nav();});
  $$('[data-budget]').forEach(b=>b.onclick=()=>{budget[b.dataset.budget]=Math.max(0,(budget[b.dataset.budget]||0)+Number(b.dataset.delta));settings();});
  $('[data-save-budget]')?.addEventListener('click',async()=>{state.analysisBudget=(await api('/api/settings/analysis-budget',{method:'POST',body:{expectedRevision:state.analysisBudget.revision,budget}})).analysisBudget;settings();});
 }
 async function library() {
  mark('library');top('素材库','跨作品复用的镜头和照片');
  const category=assetCategory;await loadLibrary(category);if(route.view!=='library'||category!==assetCategory)return;const assets=state.assets,selected=assets.find(a=>a.asset_id===route.asset)||assets[0];
  const sourcePiece=selected?catalog.pieces.find(p=>p.workspace_key===selected.source_project):null;
  const categories=state.assetStatistics?.categories||[];
  const preview=a=>`/api/review/assets/${encodeURIComponent(a.asset_id)}/preview`;
  if(!assets.length&&!state.assetError){mark('library-empty');root().classList.add('single');top('素材库','跨作品复用的镜头和照片',button('登记素材','data-register-asset'));root().innerHTML=`<div class="empty" data-design-id="R208-LIBRARY-empty"><h2>素材库还是空的</h2><p>在作品的「挑镜头」里选中一个镜头，点「收进素材库」，它就会出现在这里，别的作品也能直接用。</p><div class="actions">${button('去看项目','data-go="projects"',true)}${button('登记素材','data-register-asset')}</div></div>`;common();$$('[data-register-asset]').forEach(b=>b.onclick=()=>notice('请从本地素材登记流程选择文件。'));return;}
  root().innerHTML=`<div class="lib" data-design-id="R208-LIBRARY"><nav class="tree" aria-label="分类"><button data-category="">全部 <i data-design-data>${assets.length}</i></button>${categories.map(c=>`<button data-category="${esc(c.name)}">${D(c.name)} ${D(c.asset_count)}</button>`).join('')}</nav><div class="assets">${assets.map(a=>`<button class="asset" data-asset="${esc(a.asset_id)}"><div class="cover"><video src="${preview(a)}#t=0.01" muted playsinline preload="metadata"></video></div><div class="piece-body"><b data-design-data>${esc(a.title)}</b><small data-design-data>${esc(a.category)}</small></div></button>`).join('')}${state.assetError?`<p data-design-data>${esc(state.assetError)}</p>`:''}</div></div><aside class="review-rail" id="rail" data-design-id="R208-LIBRARY-rail">${selected?`<button class="rail-close" data-close-rail aria-label="关闭">×</button><div class="viewer"><video src="${preview(selected)}" controls playsinline preload="metadata"></video></div><div class="rail-body"><h3 data-design-data>${esc(selected.title)}</h3><div class="kv"><span>来自</span><strong>${sourcePiece?`<button class="link" data-piece-go="${esc(sourcePiece.id)}" data-design-data>${esc(sourcePiece.title)}</button>`:''}</strong></div><div class="kv"><span>能不能公开</span><strong data-design-data>${esc(selected.public_status)}</strong></div><div class="kv"><span>适合用途</span><strong data-design-data>${esc((selected.uses||[]).join('、'))}</strong></div><div class="set-actions">${button('加入作品','data-add-asset',true)}</div></div>`:''}</aside>`;common();
  $$('[data-category]').forEach(b=>b.onclick=()=>{assetCategory=b.dataset.category;library();});
  $$('[data-asset]').forEach(b=>b.onclick=()=>{route.asset=b.dataset.asset;library().then(()=>$('#rail').classList.add('open'));});
  $('[data-close-rail]')?.addEventListener('click',()=>$('#rail').classList.remove('open'));
  $('[data-add-asset]')?.addEventListener('click',async()=>{if(!state.project)return;const result=await api(`/api/projects/${state.project.id}/assets`,{method:'POST',body:{expectedRevision:state.project.revision,assetId:selected.asset_id,intendedUse:'b_roll'}});state.project=result.project;});
 }
 let reel=null,photoTimer;
 function openPlayer(config) {$('#music-player').pause();reel={...config,index:0};$('#ov').hidden=false;$('.main').dataset.designState=config.mode==='versions'?'player-versions':'player-reel';paintPlayer();$('#pl-x').focus();}
 function paintPlayer() {
  clearTimeout(photoTimer);const it=reel.items[reel.index];if(!it)return;
  $('#pl-title').innerHTML=D(reel.title);$('#pl-sub').innerHTML=D(it.title+(reel.mode==='reel'?` · ${sec(it.duration)} 秒`:''));
  $('#pl-stage').innerHTML=it.kind==='photo'?`<img src="${esc(it.src)}" alt="">`:`<video src="${esc(it.src)}" controls autoplay playsinline></video>`;
  $('#pl-ctl').innerHTML=reel.mode==='reel'?`${button('上一个','data-pl-step="-1"')}${button('下一个','data-pl-step="1"')}<span>第 ${D(reel.index+1)} / ${D(reel.items.length)} 个 · 共 ${D(seconds(reel.items.reduce((a,i)=>a+(i.duration||0),0)))}</span>`:'';
  $('#pl-strip').innerHTML=reel.items.map((i,n)=>`<button data-pi="${n}" aria-current="${n===reel.index}" data-design-data>${i.thumb?`<img src="${esc(i.thumb)}" alt="">`:''}<span>${esc(i.label||n+1)}</span></button>`).join('');
  const next=()=>{if(reel&&reel.index<reel.items.length-1){reel.index++;paintPlayer();}};
  const v=$('#pl-stage video');if(v){v.onended=()=>{if(reel.mode==='reel')next();};v.play().catch(()=>{});}else if(reel.mode==='reel')photoTimer=setTimeout(next,2500);
  $$('[data-pl-step]').forEach(b=>b.onclick=()=>{reel.index=Math.max(0,Math.min(reel.items.length-1,reel.index+Number(b.dataset.plStep)));paintPlayer();});
  $$('[data-pi]').forEach(b=>b.onclick=()=>{reel.index=Number(b.dataset.pi);paintPlayer();});
 }
 function closePlayer(){clearTimeout(photoTimer);$('#pl-stage').innerHTML='';$('#ov').hidden=true;reel=null;render();}
 function openVersions(p) {if(!p?.outputs.length)return;openPlayer({title:p.title,mode:'versions',items:p.outputs.map(o=>({kind:'video',src:`/api/review/pieces/${p.id}/media/output/${o.id}`,thumb:`/api/review/pieces/${p.id}/media/poster/${o.id}`,title:o.name,label:o.version}))});}
 function openReel(p,data){const items=data.shots.filter(s=>s.status==='selected').map(s=>({kind:s.kind,src:s.preview,thumb:frame(s),title:s.name,duration:s.duration}));if(items.length)openPlayer({title:'预览精选',mode:'reel',items});}
 async function render() {
  const generation=++request;shots.stop();music.stopPolling();direct.stop();$('#music-player').pause();
  state.screen=route.view==='piece'?'project':route.view;
  $$('[data-screen-panel]').forEach(p=>p.hidden=true);delete $('#crumb').parentElement.dataset.designId;
  root().hidden=false;root().innerHTML='';nav();
  try {if(route.view==='home')await home();else if(route.view==='projects')projects();else if(route.view==='project')project();else if(route.view==='piece')await work();else if(route.view==='inbox')await inbox();else if(route.view==='settings')await settings();else if(route.view==='library')await library();else if(route.view==='music')await music.render();else projects();
   if(generation!==request)return;common();
  }catch(error){notice(error.message,true);root().innerHTML=`<p role="alert" data-design-data>${esc(error.message)}</p>`;}
 }
 async function loadDiagnostics(refresh=false){let d=(await api('/api/diagnostics'+(refresh?'?refresh=1':''))).diagnostics;while(d.checking){await new Promise(r=>setTimeout(r,150));d=(await api('/api/diagnostics')).diagnostics;}state.diagnostics=d;}
 async function refreshCatalog(){catalog=await api('/api/review/catalog');nav();}
 function go(value){const hash=new URLSearchParams(value).toString();route=value;if(location.hash.slice(1)===hash)render();else location.hash=hash;}
 function restore(){const params=new URLSearchParams(location.hash.slice(1));route=Object.fromEntries(params);if(!route.view){const path=location.pathname;route=path.startsWith('/app/project/')?{view:'piece',piece:decodeURIComponent(path.slice(13))}:{view:({'/app/inbox':'inbox','/app/library':'library','/app/settings':'settings'})[path]||'home'};}render();}
 shots=createShotView({state,api,notice,root,mark,route:()=>route,refreshCatalog,render,common,D,esc,button});
 direct=createDirectView({api,root,mark,active:id=>route.view==='piece'&&route.ptab==='direct'&&route.piece===id,go});
 music=createMusicView({api,notice,root,top,mark,D,esc,button,active:()=>route.view==='music'});
 window.addEventListener('hashchange',restore);
 $$('.nav [data-nav]').forEach(b=>b.onclick=()=>go({view:b.dataset.nav}));
 $('#pl-x').onclick=closePlayer;$('#ov').onclick=e=>{if(e.target.id==='ov')closePlayer();};
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&reel)closePlayer();});
 return {async start(){await Promise.all([loadDiagnostics(),refreshCatalog(),api('/api/review/music-settings').then(value=>musicSettings=value)]);restore();},render,go,refreshCatalog};
}
