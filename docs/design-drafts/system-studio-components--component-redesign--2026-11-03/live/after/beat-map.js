const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const formatBeatTime = n => { const t=Math.round(n||0); return Math.floor(t/60)+':'+String(t%60).padStart(2,'0'); };
export function waveHeights(peaks) {
 const positive=peaks.filter(p=>p>.02),lo=positive.length?Math.min(...positive):0,hi=Math.max(0,...peaks);
 return peaks.map(p=>Math.round(6+(p<=.02?0:Math.pow(Math.max(0,(p-lo)/(hi-lo||1)),1.6))*94));
}
export function beatMetrics(map) {
 const gaps=map.beats.slice(1).map((b,i)=>b-map.beats[i]).sort((a,b)=>a-b),middle=Math.floor(gaps.length/2);
 const median=gaps.length%2?gaps[middle]:(gaps[middle-1]+gaps[middle])/2;
 const indices=new Map(map.beats.map((b,i)=>[b,i])),counts=new Map();
 map.downbeats.slice(1).forEach((b,i)=>{const n=indices.get(b)-indices.get(map.downbeats[i]);counts.set(n,(counts.get(n)||0)+1);});
 return {bpm:Math.round(60/median),meter:[...counts].sort((a,b)=>b[1]-a[1]||a[0]-b[0])[0]?.[0]};
}
export const sectionAt = (map,t) => map.sections?.find(s=>s.start<=t&&t<s.end)||map.sections?.at(-1);
export const barAt = (map,t) => map.downbeats.filter(b=>b<=t).length;
export const laneStart = (t,duration) => Math.min(Math.max(0,t-4),Math.max(0,duration-8));

export function mountBeatMap(container, options) {
 let opts={lane:true,cuts:[],fadeOut:0,songs:[],...options},time=0,destroyed=false,overview,head,lane,bars=[];
 const localTime=(song,t)=>t-song.start+(song.offset||0);
 const songAt=t=>opts.songs.find(s=>s.start<=t&&t<s.end)||opts.songs.at(-1);
 const pct=t=>100*t/opts.duration;
 function paint() {
  const names=Object.fromEntries((opts.taxonomy?.sections||[]).map(k=>[k.id,k.name]));
  container.innerHTML=`<div class="bm-overview" data-design-id="R223-BEAT-overview"><div class="bars" id="bars"></div>${opts.songs.length>1?'<div class="bm-song-names"></div>':''}<div class="bm-band"></div><div class="bm-cuts"></div><i class="bm-head"></i></div>${opts.lane?'<div class="bm-lane" data-design-id="R223-BEAT-lane" aria-label="播放位置前后 8 秒的拍子"></div>':''}`;
  overview=container.querySelector('.bm-overview');overview.dataset.multi=String(opts.songs.length>1);head=overview.querySelector('.bm-head');lane=container.querySelector('.bm-lane');
  const wave=overview.querySelector('.bars'),band=overview.querySelector('.bm-band'),cuts=overview.querySelector('.bm-cuts');bars=[];
  opts.songs.forEach((song,index)=>{
   const offset=song.offset||0,length=song.end-song.start,map=song.beatMap||{},peaks=song.peaks||[],total=map.duration_seconds||offset+length;
   waveHeights(peaks).forEach((height,i)=>{
    const local=(i+.5)/peaks.length*total,t=local-offset+song.start;if(t<song.start||t>=song.end)return;
    const node=document.createElement('i');node.style.cssText=`position:absolute;left:${pct(t)}%;width:${100*total/peaks.length/opts.duration*.8}%;height:${height}%`;node.dataset.t=t;wave.append(node);bars.push(node);
   });
   (map.sections||[]).forEach(section=>{
    const a=Math.max(song.start,song.start+section.start-offset),b=Math.min(song.end,song.start+section.end-offset);if(b<=a)return;
    const node=document.createElement('i');node.className=section.kind;node.style.cssText=`left:calc(${pct(a)}% + 1px);width:calc(${pct(b-a)}% - 2px)`;node.dataset.sectionKind=section.kind;node.dataset.start=a;node.dataset.end=b;
    node.title=[names[section.kind],formatBeatTime(a)+'–'+formatBeatTime(b)].filter(Boolean).join(' ');node.setAttribute('data-design-data','');band.append(node);
   });
   if(!opts.lane)(map.downbeats||[]).forEach((b,i)=>{const t=b-offset+song.start;if(t<song.start||t>=song.end)return;const line=document.createElement('i');line.className='bm-bar-line';line.style.left=pct(t)+'%';line.dataset.bar=i+1;cuts.append(line);});
   if(opts.songs.length>1){
    const name=document.createElement('span');name.textContent=song.title;name.style.left=pct(song.start)+'%';name.style.width=pct(length)+'%';name.title=song.title;name.setAttribute('data-design-data','');container.querySelector('.bm-song-names').append(name);
    if(index){const line=document.createElement('i');line.className='bm-song-change';line.style.left=pct(song.start)+'%';cuts.append(line);
     const swap=document.createElement('button');swap.type='button';swap.className='bm-swap';swap.textContent='换歌';swap.dataset.swap=index;swap.style.left=pct(song.start)+'%';swap.setAttribute('aria-pressed',String(opts.selectedSwap===index));swap.onclick=e=>{e.stopPropagation();opts.onSwapClick?.(index);};overview.append(swap);}
   }
  });
  for(const cut of opts.cuts){const line=document.createElement('i');line.className='bm-cut'+(cut.selected?' selected':'');line.style.left=pct(cut.t)+'%';line.dataset.t=cut.t;cuts.append(line);}
  if(opts.fadeOut>0){const fade=document.createElement('span');fade.className='bm-fade';fade.style.cssText=`left:${pct(Math.max(0,opts.duration-opts.fadeOut))}%;width:${pct(Math.min(opts.duration,opts.fadeOut))}%`;band.append(fade);}
  overview.onclick=e=>{const box=overview.getBoundingClientRect();opts.onSeek?.(Math.max(0,Math.min(opts.duration,(e.clientX-box.left)/box.width*opts.duration)));};
  overview.setAttribute('role','slider');overview.setAttribute('tabindex','0');overview.setAttribute('aria-label','播放');overview.setAttribute('aria-valuemin','0');overview.setAttribute('aria-valuemax',String(opts.duration));
  overview.onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();opts.onSeek?.(e.key==='Home'?0:e.key==='End'?opts.duration:Math.max(0,Math.min(opts.duration,time+(e.key==='ArrowLeft'?-1:1))));}};
  setTime(time);
 }
 function setTime(t) {
  if(destroyed)return;time=Math.max(0,Math.min(opts.duration,Number(t)||0));head.style.left=pct(time)+'%';head.hidden=time===0;overview.setAttribute('aria-valuenow',String(time));
  bars.forEach(node=>node.classList.toggle('on',Number(node.dataset.t)<time));
  if(!lane)return;
  const a=laneStart(time,opts.duration),song=songAt(time),pos=x=>((x-a)/8*100)+'%';lane.dataset.windowStart=a;lane.dataset.windowWidth=8;
  let content='';
  for(const s of opts.songs){const map=s.beatMap||{},offset=s.offset||0;
   (map.downbeats||[]).forEach((d,i)=>{const x=d-offset+s.start;if(x>=a&&x<=a+8&&x>=s.start&&x<s.end)content+=`<i class="bl" data-left="${pos(x)}"></i><span class="bn" data-left="${pos(x)}" data-design-data>${i+1}</span>`;});
   (map.beats||[]).forEach((b,i)=>{const x=b-offset+s.start;if(x<a||x>a+8||x<s.start||x>=s.end)return;const kind=sectionAt(map,b)?.kind||'',down=map.downbeats.includes(b);content+=`<i class="bc ${esc(kind)}${down?' down':''}${Math.abs(x-time)<.09?' hit':''}" data-beat="${x}" data-energy="${map.beat_energy[i]}" data-left="${pos(x)}" data-height="${10+40*map.beat_energy[i]}"></i>`;});
  }
  lane.innerHTML=content+(content?'':'<span class="none">这一段没有测到拍子</span>')+`<i class="ph" data-left="${pos(time)}"></i>`;
  lane.querySelectorAll('[data-left]').forEach(node=>{node.style.left=node.dataset.left;if(node.dataset.height)node.style.height=node.dataset.height+'px';});
  lane.dataset.localTime=song?localTime(song,time):0;
 }
 paint();
 return {update(partialOptions){if(destroyed)return;opts={...opts,...partialOptions};paint();},setTime,destroy(){destroyed=true;container.replaceChildren();}};
}
