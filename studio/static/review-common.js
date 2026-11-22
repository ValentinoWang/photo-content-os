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
