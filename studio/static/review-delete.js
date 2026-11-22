import {mediaSummary} from '/review-common.js';
// Project-page selection and recoverable work deletion. All folder decisions come from preflight.
export function createWorkDeleteView(ctx) {
 const {api,root,top,go,route,getCatalog,setCatalog,paintProject,paintProjects,refreshCatalog,state,D,esc,button,icon}=ctx;
 let picking=false,groupId=null,selected=new Set(),preview=[],dialog=null,busy=false,recent=[],recentGeneration=0;
 let toast=null,toastTimer=null,toastDeadline=0,toastRemaining=8000,undo=null;
 const main=document.querySelector('.main'),app=document.querySelector('#app'),side=app.querySelector('.side'),nav=side.querySelector('.nav');
 const originalNav={side:side.dataset.designId,nav:nav.dataset.designId,label:nav.getAttribute('aria-label')};
 const eligibility={folder_has_media:'有素材，文件夹留在原处',folder_formal_project:'有素材，文件夹留在原处',
  folder_unreadable:'读不到这个文件夹，文件夹留在原处',folder_not_connected:'找不到这个文件夹',folder_missing:'找不到这个文件夹',
  ...Object.fromEntries(['folder_outside_media_root','folder_is_media_root','folder_symlink','folder_shared','folder_contains_work','folder_runtime_unavailable'].map(k=>[k,'这个文件夹不能从这里移走，留在原处']))};
 const recentStatusText={trash_item_missing:'文件夹已经不在废纸篓里，恢复不了。',restore_target_occupied:'原来的位置已经有同名文件夹，恢复不了。'};
 const restoreText={trash_item_missing:'没恢复成：文件夹已经不在废纸篓里，恢复不了。',restore_target_occupied:'没恢复成：原来的位置已经有同名文件夹，恢复不了。',
  ...Object.fromEntries(['folder_fingerprint_mismatch','folder_restore_failed','folder_restore_unsafe','folder_unreadable'].map(k=>[k,'没恢复成：文件夹没能放回原处，作品还在最近删除里。'])),
  ...Object.fromEntries(['revision_conflict','deletion_batch_conflict','deleted_work_not_found','project_not_found'].map(k=>[k,'没恢复成：页面不是最新的，刷新后再试。']))};
 const date=value=>{const d=new Date(value);return `${d.getMonth()+1}月${d.getDate()}日`;};
 const deletedTime=value=>{const d=new Date(value);return `${date(value)} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;};
 const check=()=>'<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>';
 function setState(name) {
  if(name)app.dataset.designState=name;else delete app.dataset.designState;
  main.querySelector('.topbar').dataset.designId='R208-REV-topbar';
  main.querySelector('#top-actions').dataset.designId='R275-1-actions';
  side.dataset.designId='unchanged-nav';delete nav.dataset.designId;
  nav.removeAttribute('aria-label');nav.setAttribute('aria-labelledby','studio-brand-title');
 }
 function removeIds(ids) {
  const remaining=getCatalog().pieces.filter(p=>!ids.has(p.id));
  replacePieces(remaining);
  state.projects=state.projects.filter(p=>!ids.has(p.id));
  if(ids.has(state.project?.id))state.project=null;
 }
 function replacePieces(pieces) {
  const groups=[];
  for(const p of pieces){let g=groups.find(g=>g.id===p.group_id);if(!g){g={id:p.group_id,title:p.group_title||'其他作品',pieces:[]};groups.push(g);}g.pieces.push(p);}
  for(const g of groups)Object.assign(g,{count:g.pieces.length,pending:g.pieces.filter(p=>p.pending).length,produced:g.pieces.filter(p=>p.versions>0).length});
  setCatalog({...getCatalog(),pieces,groups:groups.sort((a,b)=>(a.id==='other')-(b.id==='other'))});
 }
 function repaint() {if(route().view==='project')paintProject();else if(route().view==='projects')paintProjects();}
 function resetSelection(){picking=false;selected.clear();groupId=null;}
 function closeDialog(focus=true){if(!dialog)return;const node=dialog;dialog=null;node.close();node.remove();if(focus)root().querySelector('[data-delete-ask]')?.focus();setState('pick-other');}
 function leave() {
  recentGeneration++;closeDialog(false);resetSelection();main.classList.remove('work-picking');delete app.dataset.designState;
  side.dataset.designId=originalNav.side;nav.dataset.designId=originalNav.nav;nav.setAttribute('aria-label',originalNav.label);nav.removeAttribute('aria-labelledby');
  delete main.querySelector('#top-actions').dataset.designId;
 }
 function card(p) {
  if(!picking)return null;
  const marked=selected.has(p.id);
  const card=document.createElement('article');
  card.className=`piece ${p.cover?'':'piece--compact'} is-picking`;
  card.dataset.pick=p.id;card.dataset.designId='R275-2-card';card.tabIndex=0;
  card.setAttribute('role','checkbox');card.setAttribute('aria-checked',String(marked));
  card.setAttribute('aria-labelledby',`work-title-${p.id} work-where-${p.id}`);
  card.innerHTML=`<span class="pick-box" aria-hidden="true">${marked?check():''}</span>${p.cover?`<div class="cover"><img src="${esc(p.cover)}" alt="" loading="lazy">${p.pending?'<span class="chip" data-design-data>挑镜头 · 等你过目</span>':p.versions?`<span class="chip" data-design-data>已出 ${p.versions} 版</span>`:'<span class="chip" data-design-data>素材已归档</span>'}</div>`:''}<div class="piece-body"><b id="work-title-${p.id}" data-design-data>${esc(p.title)}</b><small data-design-data>${p.date?esc(p.date)+' · ':''}${mediaSummary(p,esc)}</small><span id="work-where-${p.id}" class="where-line" data-design-id="R275-2-where" data-design-data>${date(p.created_at)}建 · 文件夹 ${esc(p.folder_name)}</span></div>`;
  return card.outerHTML;
 }
 function project(group) {
  if(groupId!==group.id){resetSelection();groupId=group.id;}
  main.classList.toggle('work-picking',picking);
  const actions=main.querySelector('#top-actions');
  actions.innerHTML=picking?button(selected.size===group.count?'全不选':'全选','data-delete-all'):button('选择','data-delete-pick')+button('添加作品','data-new');
  actions.querySelector('[data-delete-pick]')?.addEventListener('click',()=>{picking=true;selected.clear();paintProject();});
  actions.querySelector('[data-delete-all]')?.addEventListener('click',()=>{selected=selected.size===group.count?new Set():new Set(group.pieces.map(p=>p.id));paintProject();});
  if(picking){
   root().querySelectorAll('[data-pick]').forEach(node=>{
    node.onclick=()=>{selected.has(node.dataset.pick)?selected.delete(node.dataset.pick):selected.add(node.dataset.pick);const id=node.dataset.pick;paintProject();root().querySelector(`[data-pick="${CSS.escape(id)}"]`)?.focus();};
    node.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();node.click();}};
   });
   root().insertAdjacentHTML('beforeend',`<div class="pick-bar" role="toolbar" aria-label="选择作品" data-design-id="R275-3-bar"><span class="count" aria-live="polite" data-design-data>${selected.size?`已选 ${selected.size} 件`:'还没选作品'}</span>${button('取消','data-delete-cancel')}${button(selected.size?`删除 ${selected.size} 件`:'删除',`data-delete-ask ${selected.size?'':'disabled'}`)}</div>`);
   root().querySelector('[data-delete-ask]').classList.add('btn--danger');
   root().querySelector('[data-delete-cancel]').onclick=()=>{resetSelection();main.classList.remove('work-picking');paintProject();actions.querySelector('[data-delete-pick]')?.focus();};
   root().querySelector('[data-delete-ask]').onclick=ask;
  }
  setState(picking?'pick-other':null);
 }
 async function ask() {
  if(busy)return;
  const ids=[...selected],current=route().project;busy=true;
  try{
   const result=await api('/api/projects/delete-preview',{method:'POST',body:{projectIds:ids}});
   if(route().view!=='project'||route().project!==current||!picking)return;
   preview=result.items;
   if(preview.some(item=>!item.can_move_folder&&!eligibility[item.reason_code]))throw Error('Unmapped folder eligibility code');
   const movable=preview.filter(p=>p.can_move_folder),off=!movable.length;
   const materialOnly=preview.every(p=>['folder_has_media','folder_formal_project'].includes(p.reason_code));
   const label=movable.length&&movable.length<preview.length?`同时把 ${D(movable.length)} 件没有素材的作品的文件夹移到废纸篓`:'同时把文件夹移到废纸篓';
   dialog=document.createElement('dialog');dialog.className='work-delete-dialog';
   dialog.setAttribute('aria-labelledby','work-delete-title');
   dialog.innerHTML=`<form class="dialog-form del-dialog" data-design-id="R275-4-dialog"><header><div><p class="eyebrow">项目</p><h2 id="work-delete-title">删除 ${D(preview.length)} 件作品？</h2></div></header><p>作品从项目里移走，连同它的脚本、分镜和修改记录，放进项目列表底部的「最近删除」，随时可以恢复。</p><ul class="del-list del-ul" data-design-id="R275-4-list">${preview.map(p=>`<li><b data-design-data>${esc(p.title)}</b><small data-design-data>文件夹 ${esc(p.folder_name)}</small>${p.can_move_folder?'':`<small class="keep">${eligibility[p.reason_code]}</small>`}</li>`).join('')}</ul><div class="trash-opt" role="checkbox" aria-checked="false" aria-disabled="${off}" aria-describedby="work-trash-note" tabindex="${off?-1:0}" data-design-id="R275-4-trash"><span class="pick-box" aria-hidden="true"></span><div><b>${label}</b><small id="work-trash-note">${off?(materialOnly?'选中的作品都有素材，文件夹不能从这里移走；要删素材，去素材库。':'选中作品的文件夹都不能从这里移走。'):'文件夹里的成片和中间文件一起移走。恢复作品时，会从废纸篓放回原处。'}</small></div></div><footer>${button('取消','type="button" data-delete-close')}${button(`删除 ${D(preview.length)} 件`,'data-delete-submit')}</footer></form>`;
   const node=dialog;main.append(node);
   const opt=node.querySelector('.trash-opt');
   function toggle(){if(off)return;const checked=opt.getAttribute('aria-checked')!=='true';opt.setAttribute('aria-checked',String(checked));opt.querySelector('.pick-box').innerHTML=checked?check():'';}
   opt.onclick=toggle;opt.onkeydown=e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();toggle();}};
   node.querySelector('[data-delete-submit]').classList.add('btn--danger');
   node.querySelector('[data-delete-close]').onclick=()=>closeDialog();
   node.oncancel=e=>{e.preventDefault();closeDialog();};
   node.querySelector('form').onsubmit=e=>{e.preventDefault();commit(opt.getAttribute('aria-checked')==='true');};
   node.showModal();node.querySelector('[data-delete-close]').focus();
   setState(materialOnly?'confirm-lzu':'confirm-other');
  }catch(error){showToast('已删除 0 件，'+ids.length+' 件没删成',true,null);console.error('Work deletion preview failed',error);}
  finally{busy=false;}
 }
 async function commit(moveFolders) {
  if(busy)return;busy=true;
  const items=preview,ids=new Set(items.map(p=>p.id)),before=structuredClone(getCatalog()),beforeProjects=[...state.projects],beforeProject=state.project,originalGroup=route().project;
  closeDialog(false);resetSelection();main.classList.remove('work-picking');removeIds(ids);
  if(!getCatalog().groups.some(g=>g.id===originalGroup))go({view:'projects'});else paintProject();
  try{
   const result=await api('/api/projects/delete',{method:'POST',body:{projectIds:[...ids],expectedRevisions:Object.fromEntries(items.map(p=>[p.id,p.revision])),moveFolders,...(moveFolders?{folderProjectIds:items.filter(p=>p.can_move_folder).map(p=>p.id)}:{})}});
   const failed=new Set(result.results.filter(p=>!p.ok).map(p=>p.id));
   if(failed.size){replacePieces(before.pieces.filter(p=>failed.has(p.id)||!ids.has(p.id)));state.projects=beforeProjects.filter(p=>failed.has(p.id)||!ids.has(p.id));if(!state.project&&failed.has(beforeProject?.id))state.project=beforeProject;}
   repaint();
   undo=result.succeeded?{body:result.undo,group:originalGroup}:null;
   let text=`已删除 ${result.succeeded} 件作品`;
   if(result.failed===1){const failure=result.results.find(p=>!p.ok),title=items.find(p=>p.id===failure.id).title;
    const reason=failure.code==='folder_trash_failed'?'文件夹移不到废纸篓':failure.code?.startsWith('folder_')?'文件夹不能从这里移走':'页面不是最新的，刷新后再试';
    text=`已删除 ${result.succeeded} 件。「${title}」没删成：${reason}`;
   }else if(result.failed)text=`已删除 ${result.succeeded} 件，${result.failed} 件没删成`;
   showToast(text,!!result.failed,undo);
   if(route().view==='project')setState(result.failed?'partial-fail':'deleted-other');
  }catch(error){setCatalog(before);state.projects=beforeProjects;if(!state.project)state.project=beforeProject;if(route().view==='projects'||route().view==='project')go({view:'project',project:originalGroup});showToast(`已删除 0 件，${items.length} 件没删成`,true,null);}
  finally{busy=false;}
 }
 function hideToast(){clearTimeout(toastTimer);toast?.remove();toast=null;undo=null;}
 function startToastTimer(){toastDeadline=performance.now()+toastRemaining;toastTimer=setTimeout(hideToast,toastRemaining);}
 function showToast(text,bad,batch){
  hideToast();undo=batch;toast=document.createElement('div');toast.className=`toast show work-delete-toast${bad?' error':''}`;toast.dataset.designId='R275-5-toast';toast.setAttribute('role','status');
  toast.innerHTML=`<span data-design-data>${esc(text)}</span>${batch?'<button class="link" data-delete-undo>撤销</button>':''}`;
  main.append(toast);toast.querySelector('[data-delete-undo]')?.addEventListener('click',undoBatch);
  toastRemaining=8000;startToastTimer();
  toast.onmouseenter=()=>{toastRemaining=Math.max(0,toastDeadline-performance.now());clearTimeout(toastTimer);};
  toast.onmouseleave=startToastTimer;
 }
 async function undoBatch(){
  if(!undo||busy)return;busy=true;const batch=undo;hideToast();
  try{
   const result=await api('/api/projects/restore',{method:'POST',body:batch.body});
   await refreshCatalog();
   if(result.failed){const failure=result.results.find(p=>!p.ok);showToast(restoreText[failure.code]||restoreText.folder_restore_failed,true,null);repaint();}
   else go({view:'project',project:batch.group});
  }catch{showToast(restoreText.revision_conflict,true,null);}
  finally{busy=false;}
 }
 async function projects(){
  setState(null);const generation=++recentGeneration;
  try{const result=await api('/api/projects/deleted');if(generation!==recentGeneration||route().view!=='projects')return;recent=result.items;
   if(!recent.length)return;setState('projects-recent');const list=root().querySelector('.projects');
   list.insertAdjacentHTML('beforeend',`<button class="recent-row" data-design-id="R275-6-recent">${icon('trash')}最近删除${D(recent.length+' 件')}<i>›</i></button>`);
   list.querySelector('.recent-row').onclick=()=>go({view:'recent'});
  }catch(error){console.error('Recent work list failed',error);}
 }
 async function recentPage(){
  const generation=++recentGeneration;main.dataset.designState='recent';setState('recent');
  const result=await api('/api/projects/deleted');if(generation!==recentGeneration||route().view!=='recent')return;recent=result.items;
  if(!recent.length){go({view:'projects'});return;}
  top(D('最近删除'),D(`${recent.length} 件 · 恢复后回到原来的项目`),'','<button data-recent-back>项目</button>›');
  main.querySelector('[data-recent-back]').onclick=()=>go({view:'projects'});
  root().classList.add('single');
  root().innerHTML=`<div class="recent-list" data-design-id="R275-7-list">${recent.map(p=>`<div class="setrow" data-recent-id="${esc(p.id)}"><div><strong data-design-data>${esc(p.title)}</strong><small data-design-data>原来在 ${esc(p.group_title)} · 文件夹 ${esc(p.folder_name)} · ${deletedTime(p.deleted_at)} 删除</small><small class="${p.reason_code?'gone':''}">${p.reason_code?(recentStatusText[p.reason_code]||restoreText[p.reason_code]||restoreText.folder_restore_failed):(p.folder_status==='trash'?'文件夹在废纸篓里，恢复时放回原处':'文件夹还在原处')}</small></div>${button(p.can_dismiss?'移出列表':'恢复',`data-recent-action="${p.can_dismiss?'dismiss':'restore'}" ${!p.can_dismiss&&!p.can_restore?'disabled':''}`)}</div>`).join('')}</div>`;
  setState('recent');
  root().querySelectorAll('[data-recent-action]').forEach(node=>node.onclick=()=>recover(node));
 }
 async function recover(node){
  if(busy)return;busy=true;const p=recent.find(p=>p.id===node.closest('[data-recent-id]').dataset.recentId);node.disabled=true;
  try{
   const result=await api(`/api/projects/${encodeURIComponent(p.id)}/${node.dataset.recentAction}`,{method:'POST',body:{expectedRevision:p.revision}});
   if(result.failed)showToast(restoreText[result.results.find(p=>!p.ok).code]||restoreText.folder_restore_failed,true,null);
   await refreshCatalog();if(route().view==='recent')await recentPage();
  }catch{showToast(restoreText.revision_conflict,true,null);}
  finally{busy=false;node.disabled=false;}
 }
 main.addEventListener('keydown',e=>{if(e.key==='Escape'&&!dialog&&picking){e.preventDefault();resetSelection();main.classList.remove('work-picking');paintProject();}});
 return {card,project,projects,recent:recentPage,leave,picking:()=>picking};
}
