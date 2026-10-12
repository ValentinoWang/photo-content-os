import {renderHandoff} from './handoff.js';
import {videoActions} from './video-actions.js';
const authorized=await fetch('/api/projects');
if(!authorized.ok)throw new Error('本机连接已过期，请回到 Studio 重新打开');
const config=await (await fetch(new URL('./session.json',import.meta.url))).json();
const bootstrap=await (await fetch(config.photoOrigin+'/api/bootstrap')).json();
config.csrf=bootstrap.csrfToken;
let data=(await (await fetch(`${config.photoOrigin}/api/projects/${encodeURIComponent(config.projectId)}`)).json()).videoHandoff;
const actions=videoActions({projectId:config.projectId,csrf:config.csrf,photoOrigin:config.photoOrigin,getData:()=>data});
actions.leaveHost=async()=>{location.assign(`${config.photoOrigin}/app/project/${encodeURIComponent(config.projectId)}`);};
renderHandoff(document.querySelector('#host'),data,actions);
window.addEventListener('pagehide',()=>document.querySelector('#host')._handoffCleanup?.());

document.querySelectorAll('[data-screen]').forEach(button=>button.onclick=()=>location.assign(button.dataset.screen==='project'?`${config.photoOrigin}/app/project/${encodeURIComponent(config.projectId)}`:`${config.photoOrigin}/app/${encodeURIComponent(button.dataset.screen)}`));
