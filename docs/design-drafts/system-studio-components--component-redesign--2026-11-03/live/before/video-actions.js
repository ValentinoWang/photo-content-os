// Shared by the Photo page and the authenticated openfilm editor-origin host.
export function videoActions({projectId,csrf,photoOrigin=location.origin,getData,onChoice}) {
 const path=`${photoOrigin}/api/projects/${encodeURIComponent(projectId)}`;
 async function request(url,options={}){const response=await fetch(url,{...options,headers:{'X-Content-OS-CSRF':csrf,...options.headers}});const body=await response.json();if(!response.ok||!body.ok){const error=new Error(body.error?.message||'操作失败，请重试');error.code=body.error?.code;throw error;}return body;}
 const identity=()=>({identity:getData().identity,expectedRevision:getData().projectRevision});
 return {photoOrigin,choose:async choice=>{const r=await request(path,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({expectedRevision:getData().projectRevision,videoEditor:choice})});onChoice?.(r.videoEditor);return r.videoEditor;},
 refresh:async()=>{const r=await request(path);Object.assign(getData(),r.videoHandoff);return r.videoHandoff;},
 command:async(op,extra={})=>{const r=await request(path+'/video-workflow',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...identity(),op,...extra})});Object.assign(getData(),r.videoHandoff);return r.videoHandoff;},
 upload:async file=>{const r=await request(path+'/video-return',{method:'POST',headers:{'Content-Type':file.type||'video/mp4','X-Video-Identity':JSON.stringify(identity())},body:file});Object.assign(getData(),r.videoHandoff);return r.videoHandoff;},
 srt:async()=>{const response=await fetch(path+'/video-subtitles');if(!response.ok)throw new Error('字幕尚未生成');const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download='subtitles.srt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 };
}
