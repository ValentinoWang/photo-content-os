// 新增公共组件：状态徽标、事实条、步骤空状态、数字块、阶段条、素材计数。实现时原样进 studio/static/components.js
const svg=p=>`<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
export const glyphs={
 video:'<rect x="2" y="5" width="15" height="14" rx="2"/><path d="m17 10 5-3v10l-5-3"/>',
 photo:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="m5 19 6-6 3 3 2-2 3 3"/>',
 lock:'<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
 route:'<circle cx="6" cy="19" r="2.4"/><circle cx="18" cy="5" r="2.4"/><path d="M8.4 19H15a3.5 3.5 0 0 0 0-7H9a3.5 3.5 0 0 1 0-7h6.6"/>',
 bell:'<path d="M18 16V11a6 6 0 1 0-12 0v5l-2 2h16zM10 21h4"/>',
 link:'<path d="M9 15 15 9M11 6l1-1a4.5 4.5 0 0 1 6.4 6.4l-1 1M13 18l-1 1A4.5 4.5 0 0 1 5.6 12.600l1-1"/>',
 down:'<path d="M12 3v12M7 11l5 5 5-5M4 21h16"/>',
 one:'<circle cx="12" cy="12" r="9"/><path d="M12 8v8"/>',
 inbox:'<path d="M2 12h6l2 3h4l2-3h6M2 12l4-8h12l4 8v8H2z"/>',
 split:'<rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="8" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/><rect x="13" y="13" width="8" height="8" rx="1.5"/>',
 folder:'<path d="M2 20V4h7l3 3h10v13z"/>',
 scissors:'<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M8.100 8.100 20 20M20 4 8.100 15.900"/>',
 star:'<path d="m12 3 2.800 5.800 6.200.900-4.500 4.400 1.100 6.300L12 17.400l-5.600 3 1.100-6.300L3 9.700l6.200-.900z"/>',
 repeat:'<path d="M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3"/>',
};
export const glyph=k=>svg(glyphs[k]||'');
const TONE={'可用':'ok','已连接':'ok','已配置':'ok','已登录':'ok','没连上':'warn','未连接':'warn','没配置':'warn','没登录':'warn','没装好':'warn','暂不支持':'quiet','读取失败':'cut'};
export const statusBadge=(label,tone=TONE[label]||'quiet')=>`<span class="sbadge sbadge--${tone}" data-design-component="状态徽标"><i aria-hidden="true"></i>${label}</span>`;
export const factStrip=items=>`<ul class="fstrip" data-design-component="事实条">${items.map(([k,t])=>`<li>${glyph(k)}<span>${t}</span></li>`).join('')}</ul>`;
export const stepEmpty=(title,steps,foot='',actions='')=>`<div class="sempty" data-design-component="步骤空状态"><h2>${title}</h2><ol class="sempty-steps">${steps.map(([k,t,s])=>`<li><span class="sempty-ico">${glyph(k)}</span><b>${t}</b><small>${s}</small></li>`).join('')}</ol>${foot}${actions?`<div class="actions">${actions}</div>`:''}</div>`;
export const statTiles=items=>`<div class="ntiles" data-design-component="数字块">${items.map(([n,u,l])=>`<div class="ntile"><b data-design-data>${n}</b><i>${u}</i><small>${l}</small></div>`).join('')}</div>`;
export const stageTrack=p=>{const n=p.versions?3:p.pending?2:(p.videos||p.photos)?1:0,label=p.versions?`已出 ${p.versions} 版`:p.pending?'等你过目':n?'素材已归档':'还没有素材';return `<div class="stage-track stage-track--${n}${p.pending?' is-wait':''}" data-design-component="阶段条" role="img" aria-label="${label}"><span></span><span></span><span></span><em>${label}</em></div>`;};
export const mediaMeta=p=>{const a=[p.videos?`<span>${glyph('video')}<b data-design-data>${p.videos}</b></span>`:'',p.photos?`<span>${glyph('photo')}<b data-design-data>${p.photos}</b></span>`:''].filter(Boolean).join('');return a?`<span class="mmeta" data-design-component="素材计数" role="img" aria-label="${p.videos||0} 段视频，${p.photos||0} 张照片">${a}</span>`:'<span>还没有素材</span>';};
