export const sec = n => Number(n || 0).toFixed(1);
export function mediaSummary(piece, data = String) {
 return [piece.videos ? `${data(piece.videos)} 段视频` : '', piece.photos ? `${data(piece.photos)} 张照片` : ''].filter(Boolean).join(' · ') || '还没有素材';
}
export function deliveryLabel(value, log = console.warn) {
 const labels = {not_started:'还没开始',in_progress:'进行中',delivered:'已交付',done:'已交付',completed:'已交付',blocked:'受阻'};
 if (Object.hasOwn(labels,value)) return labels[value];
 log('studio.delivery.unknown: '+String(value));return '状态未知';
}
export function flowSteps(steps, designId = '') {
 return `<nav class="flow full" aria-label="这件作品的步骤" ${designId?`data-design-id="${designId}"`:''}>${steps.map(({title,note='',done=false,current=false},i)=>`<div class="fstep ${done?'done':''} ${current?'cur':''}" ${current?'aria-current="step"':''}><b data-design-data>${done?'✓':i+1}</b><span><strong>${title}</strong>${note?`<small>${note}</small>`:''}</span></div>`).join('')}</nav>`;
}
export function diagnosticGroups(checks, pieces, data=String) {
 const works=pieces??[];
 const selected=works.filter(p=>(p.editorChoice?.method??'external')==='external'&&p.editorChoice?.editor==='chatcut'),unreadable=works.filter(p=>!p.editorChoice?.editor||p.editorChoice.error);
 const chatcutNeeded=pieces===undefined||selected.length>0||unreadable.length>0;
 const good=checks.filter(c=>c.status==='ready'), optional=checks.filter(c=>c.status!=='ready'&&(['asset_library','creative_model','upstream_identity'].includes(c.id)||c.id==='chatcut_mcp'&&!chatcutNeeded));
 const issues=unreadable.map(p=>({id:'editor_choice',title:p.editorChoice?.error?.message||'无法读取本机记录',note:data(p.title)}));
 if(selected.length&&!checks.some(c=>c.id==='chatcut_mcp'&&c.status==='ready'))issues.push({id:'chatcut',title:'ChatCut 还没连上本机',note:(selected.length===1?`「${data(selected[0].title)}」选了`:`有 ${data(selected.length)} 件作品选了`)+'在 ChatCut 里精剪，连上之前出不了草稿。去设置里接上，或者在作品里改用 Kdenlive。'});
 if(pieces===undefined&&checks.some(c=>c.id==='chatcut_mcp'&&c.status!=='ready'))issues.push({id:'chatcut',title:'ChatCut 还没连上本机',note:'想在 ChatCut 里精剪，先去设置里接上。'});
 const tools=checks.filter(c=>c.id.startsWith('edit_tool_')&&c.status!=='ready');
 if(tools.length)issues.push({id:'edit_tools',title:'OpenChatCut、OpenFilm 还没装好',note:'出草稿要用到它们。去设置里看怎么装。',commands:[...new Set(tools.map(c=>c.repair).filter(Boolean))]});
 return {good,optional,issues};
}
export function draftEditorNote(choice, checks, capability=null) {
 if(choice?.error)return choice.error.message;
 if(choice?.method==='guide')return '在剪映里照清单剪';
 if(choice?.method==='self')return '用 OpenFilm';
 if(choice?.editor==='chatcut'&&!checks.some(c=>c.id==='chatcut_mcp'&&c.status==='ready'))return 'ChatCut 还没连上';
 if(capability?.block_reason==='multi_source_unverified')return ({chatcut:'ChatCut',openchatcut:'OpenChatCut'}[choice?.editor]||'')+' 还出不了这件作品';
 return {otio_kdenlive:'用 Kdenlive',chatcut:'用 ChatCut',openfilm:'用 OpenFilm',openchatcut:'用 OpenChatCut'}[choice?.editor]||'无法读取本机记录';
}
export function checkedTime(iso, now=new Date()) {
 if(!iso)return '';
 const date=new Date(iso),today=date.toDateString()===now.toDateString();
 return (today?'今天':`${date.getMonth()+1}月${date.getDate()}日`)+' '+date.toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',hour12:false});
}

/* Shared public UI components (statusBadge, factStrip, stepEmpty, statTiles, stageTrack, mediaMeta). */
const svgGlyph = p => `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${p}</svg>`;
export const glyphs = {
 video:'<rect x="2" y="5" width="15" height="14" rx="2"/><path d="m17 10 5-3v10l-5-3"/>',
 photo:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="m5 19 6-6 3 3 2-2 3 3"/>',
 lock:'<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
 route:'<circle cx="6" cy="19" r="2.4"/><circle cx="18" cy="5" r="2.4"/><path d="M8.4 19H15a3.5 3.5 0 0 0 0-7H9a3.5 3.5 0 0 1 0-7h6.6"/>',
 bell:'<path d="M18 16V11a6 6 0 1 0-12 0v5l-2 2h16zM10 21h4"/>',
 link:'<path d="M9 15 15 9M11 6l1-1a4.5 4.5 0 0 1 6.4 6.4l-1 1M13 18l-1 1A4.5 4.5 0 0 1 5.6 12.6l1-1"/>',
 down:'<path d="M12 3v12M7 11l5 5 5-5M4 21h16"/>',
 one:'<circle cx="12" cy="12" r="9"/><path d="M12 8v8"/>',
 inbox:'<path d="M2 12h6l2 3h4l2-3h6M2 12l4-8h12l4 8v8H2z"/>',
 split:'<rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="8" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/><rect x="13" y="13" width="8" height="8" rx="1.5"/>',
 folder:'<path d="M2 20V4h7l3 3h10v13z"/>',
 scissors:'<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M8.1 8.1 20 20M20 4 8.1 15.9"/>',
 star:'<path d="m12 3 2.8 5.8 6.2.9-4.5 4.4 1.1 6.3L12 17.4l-5.6 3 1.1-6.3L3 9.7l6.2-.9z"/>',
 repeat:'<path d="M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3"/>',
 music:'<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
 wave:'<path d="M3 12h3l2-6 4 12 3-8 2 2h4"/>',
 spark:'<path d="M12 3l2.2 6.8L21 12l-6.8 2.2L12 21l-2.2-6.8L3 12l6.8-2.2z"/>',
 check:'<path d="m20 6-11 11-5-5"/>',
 alert:'<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
};
export const glyph = k => svgGlyph(glyphs[k] || '');
const STATUS_TONE = {
 '可用':'ok','已连接':'ok','已配置':'ok','已登录':'ok','已就绪':'ok',
 '没连上':'warn','未连接':'warn','没配置':'warn','没配置出口':'warn','没登录':'warn','没装好':'warn',
 '暂不支持':'quiet','读取失败':'cut','失败':'cut',
};
export const statusBadge = (label, tone = STATUS_TONE[label] || (/可用/.test(label) ? 'ok' : 'quiet')) =>
 `<span class="sbadge sbadge--${tone}" data-design-component="状态徽标"><i aria-hidden="true"></i>${label}</span>`;
export const factStrip = items =>
 `<ul class="fstrip" data-design-component="事实条">${items.map(([k,t])=>`<li>${glyph(k)}<span>${t}</span></li>`).join('')}</ul>`;
export const stepEmpty = (title, steps, foot = '', actions = '', designId = '') =>
 `<div class="sempty" ${designId?`data-design-id="${designId}"`:''} data-design-component="步骤空状态"><h2>${title}</h2><ol class="sempty-steps">${steps.map(([k,t,s])=>`<li><span class="sempty-ico">${glyph(k)}</span><b>${t}</b><small>${s}</small></li>`).join('')}</ol>${foot}${actions?`<div class="actions">${actions}</div>`:''}</div>`;
export const statTiles = items =>
 `<div class="ntiles" data-design-component="数字块">${items.map(([n,u,l])=>`<div class="ntile"><b data-design-data>${n}</b><i>${u}</i><small>${l}</small></div>`).join('')}</div>`;
export const stageTrack = p => {
 const n = p.versions ? 3 : p.pending ? 2 : (p.videos || p.photos) ? 1 : 0;
 const label = p.versions ? `已出 ${p.versions} 版` : p.pending ? '等你过目' : n ? '素材已归档' : '还没有素材';
 return `<div class="stage-track stage-track--${n}${p.pending?' is-wait':''}" data-design-component="阶段条" role="img" aria-label="${label}"><span></span><span></span><span></span><em>${label}</em></div>`;
};
export const mediaMeta = p => {
 const parts = [
  p.videos ? `<span>${glyph('video')}<b data-design-data>${p.videos}</b></span>` : '',
  p.photos ? `<span>${glyph('photo')}<b data-design-data>${p.photos}</b></span>` : '',
 ].filter(Boolean).join('');
 return parts ? `<span class="mmeta" data-design-component="素材计数" role="img" aria-label="${p.videos||0} 段视频，${p.photos||0} 张照片">${parts}</span>` : '<span>还没有素材</span>';
};
export function formatRepairNote(raw, escFn = s => String(s ?? '')) {
 const text = String(raw || '').trim();
 if (!text) return '';
 if (/^python3?\s+scripts\//.test(text)) return `终端运行 <code class="cmd-chip" data-design-data>${escFn(text)}</code>`;
 const clean = text
  .replace(/剪映[：:]\s*app_missing_or_version_unknown/g, '本机未检测到剪映应用，需要时可手动安装后重新检查')
  .replace(/Kdenlive[：:]\s*kdenlive_version_unknown/g, '本机未检测到 Kdenlive，安装后即可自动生成可编辑时间线')
  .replace(/\bapp_missing_or_version_unknown\b/g, '未检测到本机应用')
  .replace(/\bkdenlive_version_unknown\b/g, '未检测到本机版本');
 return `<span data-design-data>${escFn(clean)}</span>`;
}
