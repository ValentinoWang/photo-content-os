const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const source={qishui:'汽水音乐',netease:'网易云音乐',netease_client:'网易云音乐',local:'本机文件'};
const mmss=n=>{const t=Math.round(n||0);return Math.floor(t/60)+':'+String(t%60).padStart(2,'0');};
export function waveHeights(peaks){const positive=peaks.filter(p=>p>.02),lo=positive.length?Math.min(...positive):0,hi=Math.max(0,...peaks);return peaks.map(p=>Math.round(6+(p<=.02?0:Math.pow(Math.max(0,(p-lo)/(hi-lo||1)),1.6))*94));}
export function createMusicView(ctx) {
 const {api,notice,root,top,mark,D,esc,button,active}=ctx;
 let tracks=[],selectedId,filter='all',job=null,paste='',poll,opened=false;
 const player=()=>$('#music-player');
 const current=()=>tracks.find(t=>t.file_sha256===selectedId)||tracks.find(t=>t.platform==='netease')||tracks[0];
 const fmt=(iso,time=false)=>new Date(iso).toLocaleString('zh-CN',{year:'numeric',month:'numeric',day:'numeric',...(time?{hour:'2-digit',minute:'2-digit',hour12:false}:{})});
 function stopPolling(){clearTimeout(poll);}
 function result() {
  if(job?.state==='duplicate')return `<div class="note full" role="status" data-design-id="R208-MUSIC-result">《${D(job.title)}》已经在库里了，没有重新下载。</div>`;
  if(job?.state==='member')return `<div class="attention full" role="alert" data-design-id="R208-MUSIC-result"><div><strong>《${D(job.title)}》要网易云会员才能下载</strong><p>你的网易云账号不是会员，库里没有多出任何东西。可以去汽水音乐找同名歌。</p></div>${button('去汽水音乐找同名歌','data-search-elsewhere')}</div>`;
  if(job?.state==='error'){
   const douyin=job.reason?.startsWith('没从抖音取到这首的音乐。');
   return `<div class="attention full" role="alert" data-design-id="R208-MUSIC-result"><div>${douyin?'<strong>没从抖音取到这首的音乐</strong><p>可以在剪映里直接用原声，或者找这首歌在汽水音乐、网易云音乐的分享链接。</p>':`<p data-design-data>${esc(job.reason)}</p>`}</div></div>`;
  }
  return '';
 }
 function rail(m) {
  if(!m)return '';
  return `<button class="rail-close" data-close-rail aria-label="关闭">×</button><div class="wave"><div class="bars" id="bars">${waveHeights(m.peaks||[]).map(n=>`<i data-height="${n}"></i>`).join('')}</div><div class="wave-ctl"><button data-toggle-music aria-label="播放">${player().paused?'▶':'❚❚'}</button><span id="ptime" data-design-data>0:00 / ${mmss(m.duration_seconds)}</span></div></div><div class="rail-body"><h3 data-design-data>${esc(m.title)}</h3><p class="where" data-design-data>${esc(m.artist)}</p><div class="kv"><span>来源</span><strong>${source[m.platform]||D(m.platform)}${m.original_url?`<small><a class="link" href="${esc(m.original_url)}" target="_blank" rel="noopener noreferrer">打开原页面</a></small>`:''}</strong></div><div class="kv"><span>时长</span><strong data-design-data>${mmss(m.duration_seconds)}</strong></div><div class="kv"><span>节拍</span><strong>还没分析<small>第一次用来配乐时自动分析</small></strong></div><div class="kv"><span>导入时间</span><strong data-design-data>${fmt(m.imported_at,true)}</strong></div></div>`;
 }
 function paint() {
  if(!active())return;
  const importing=job?.state==='importing';const state=importing?'music-importing':job?.state==='duplicate'?'music-dup':job?.state==='member'?'music-vip':job?.state==='error'&&job.reason?.startsWith('没从抖音')?'music-douyin':!tracks.length?'music-empty':'music';
  mark(state);top('音乐库','配乐卡点从这里选歌',button('从文件夹导入','data-from-folder'));
  const form=`<form class="import" data-design-id="R208-MUSIC-import" id="music-import"><label for="paste">粘贴分享链接导入</label><div class="import-row"><input id="paste" value="${esc(paste)}" placeholder="粘贴汽水音乐或网易云音乐的分享文字" ${importing?'disabled':''}>${button(importing?'导入中':'导入',importing?'disabled':'',true)}</div><small>每首只下载一次，之后都用本机这份。</small></form>`;
  if(!tracks.length){root().classList.add('single');root().innerHTML=form+result()+`<div class="empty" data-design-id="R208-MUSIC-empty"><h2>音乐库还是空的</h2><p>在上面粘贴一首歌在汽水音乐或网易云音乐的分享文字；手里已有的歌，用右上角「从文件夹导入」。配乐卡点时只从这里选歌。</p></div>`;bind();return;}
  const rows=tracks.filter(m=>filter==='all'||(m.platform==='netease_client'?'netease':m.platform)===filter),m=current();
  root().innerHTML=form+result()+`<div class="subfilters full" data-design-id="R208-MUSIC-filters">${[['all','全部'],['qishui','汽水音乐'],['netease','网易云音乐'],['local','本机文件']].map(([k,l])=>{const n=k==='all'?tracks.length:tracks.filter(t=>(t.platform==='netease_client'?'netease':t.platform)===k).length;return n||k==='all'?`<button class="pill" data-src="${k}" aria-pressed="${filter===k}">${l}<i data-design-data>${n}</i></button>`:'';}).join('')}</div><div class="music-tracks" data-design-id="R208-MUSIC-list"><div class="trow head"><span></span><span>歌名</span><span>来源</span><span>时长</span><span>导入时间</span></div>${importing?'<div class="trow" data-design-id="R208-MUSIC-importing"><span>—</span><span class="t"><b>正在导入</b></span></div>':''}${rows.map(m=>`<button class="trow" data-track="${m.file_sha256}" aria-selected="${current()?.file_sha256===m.file_sha256}"><span class="play" data-play="${m.file_sha256}" aria-label="播放">${player().dataset.id===m.file_sha256&&!player().paused?'❚❚':'▶'}</span><span class="t"><b data-design-data>${esc(m.title)}</b><small data-design-data>${esc(m.artist)}</small><small class="meta">${source[m.platform]}</small></span><span>${source[m.platform]}</span><span data-design-data>${mmss(m.duration_seconds)}</span><span data-design-data>${fmt(m.imported_at)}</span></button>`).join('')}</div><aside class="review-rail ${opened?'open':''}" id="rail" data-design-id="R208-MUSIC-rail">${rail(m)}</aside>`;
  bind();paintProgress();
 }
 function paintProgress(){const m=current();if(!m)return;const p=player(),ratio=p.dataset.id===m.file_sha256&&p.duration?p.currentTime/p.duration:0;$$('#bars i').forEach((b,i,a)=>b.classList.toggle('on',i<ratio*a.length));if($('#ptime'))$('#ptime').textContent=`${mmss(p.dataset.id===m.file_sha256?p.currentTime:0)} / ${mmss(m.duration_seconds)}`;}
 function play(m){const p=player();if(p.dataset.id!==m.file_sha256){p.src=m.audio;p.dataset.id=m.file_sha256;}if(p.paused)p.play().catch(e=>notice(e.message,true));else p.pause();}
 async function importMusic(value){try{job=(await api('/api/review/music/import',{method:'POST',body:value})).job;paint();await pollJob();}catch(e){notice(e.message,true);}}
 async function pollJob(){job=(await api(`/api/review/imports/${job.id}`)).job;if(!active())return;if(job.state==='importing')poll=setTimeout(()=>pollJob().catch(e=>notice(e.message,true)),1000);else tracks=(await api('/api/review/music')).tracks;paint();}
 function bind(){
  $$('[data-height]').forEach(n=>n.style.height=n.dataset.height+'%');
  $('#paste').oninput=e=>{paste=e.target.value;};
  $('#music-import').onsubmit=e=>{e.preventDefault();if(job?.state!=='importing')importMusic({text:paste});};
  $$('[data-src]').forEach(b=>b.onclick=()=>{filter=b.dataset.src;paint();});
  $$('[data-track]').forEach(b=>b.onclick=e=>{selectedId=b.dataset.track;opened=true;if(e.target.closest('[data-play]'))play(current());paint();});
  $('[data-toggle-music]')?.addEventListener('click',()=>play(current()));
  $('[data-close-rail]')?.addEventListener('click',()=>{opened=false;$('#rail').classList.remove('open');});
  $('[data-search-elsewhere]')?.addEventListener('click',()=>importMusic({text:paste,searchElsewhere:true}));
  $('[data-from-folder]')?.addEventListener('click',()=>$('#folder-dialog').showModal());
  $('#folder-form').onsubmit=e=>{e.preventDefault();const folder=new FormData(e.target).get('folder');$('#folder-dialog').close();importMusic({folder});};
  const bars=$('#bars');if(bars)bars.onclick=e=>{const p=player(),m=current(),ratio=Math.min(1,Math.max(0,(e.clientX-bars.getBoundingClientRect().left)/bars.clientWidth));const seek=()=>{p.currentTime=ratio*p.duration;paintProgress();};if(p.dataset.id!==m.file_sha256){p.src=m.audio;p.dataset.id=m.file_sha256;}if(Number.isFinite(p.duration))seek();else {p.addEventListener('loadedmetadata',seek,{once:true});p.load();}};
  player().ontimeupdate=paintProgress;player().onplay=player().onpause=()=>{if($('.main').dataset.designState?.startsWith('music'))paint();};
 }
 return {stopPolling,async render(){tracks=(await api('/api/review/music')).tracks;if(!active())return;paint();if(job?.state==='importing')pollJob();}};
}
