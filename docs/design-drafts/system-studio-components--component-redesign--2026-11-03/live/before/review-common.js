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
export function diagnosticGroups(checks) {
 const good=checks.filter(c=>c.status==='ready'), optional=checks.filter(c=>c.status!=='ready'&&['asset_library','creative_model','upstream_identity'].includes(c.id));
 const issues=[];
 if(checks.some(c=>c.id==='chatcut_mcp'&&c.status!=='ready'))issues.push({id:'chatcut',title:'ChatCut 还没连上本机',note:'出草稿时会先用剪映。想在 ChatCut 里精剪，先去设置里接上。'});
 const tools=checks.filter(c=>c.id.startsWith('edit_tool_')&&c.status!=='ready');
 if(tools.length)issues.push({id:'edit_tools',title:'OpenChatCut、OpenFilm 还没装好',note:'出草稿要用到它们。去设置里看怎么装。',commands:[...new Set(tools.map(c=>c.repair).filter(Boolean))]});
 return {good,optional,issues};
}
export function checkedTime(iso, now=new Date()) {
 if(!iso)return '';
 const date=new Date(iso),today=date.toDateString()===now.toDateString();
 return (today?'今天':`${date.getMonth()+1}月${date.getDate()}日`)+' '+date.toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',hour12:false});
}
