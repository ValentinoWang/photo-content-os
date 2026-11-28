"""Package constants."""

from __future__ import annotations
from pathlib import Path
import sys
from types import MappingProxyType
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from edl_contract import AUDIO_CLIP_FIELDS

# --- concat_adapter.py ---
MIN_RETAINED_SECONDS = 0.2
MIN_CAPTION_SECONDS = 0.3

# --- handoff_pack.py ---
SPEC_VERSION = "content_os_v0.2"
BACKEND = "handoff_pack"
MANIFEST_TYPE = "edit_handoff_manifest"
RESULT_TYPE = "edit_handoff_result"
VALIDATION_TYPE = "edit_handoff_validation"
TIMING_TOLERANCE = 0.000_001
CSV_FIELDS = [
    "timeline_order",
    "slot",
    "layer",
    "role",
    "timeline_start_sec",
    "timeline_end_sec",
    "duration_sec",
    "source_file",
    "source_start_sec",
    "source_end_sec",
    "purpose",
    "visual_need",
    "edit_note",
    "caption",
]
AUDIO_CSV_FIELDS = [*AUDIO_CLIP_FIELDS, "audio_plan", "audio_beds", "music"]
LEGACY_CSV_FIELDS = CSV_FIELDS.copy()
LAYER_STACK = ("background", "primary", "overlay")
DEFAULT_LAYER = "primary"
CONTIGUOUS_LAYER = "primary"

# --- openchatcut_adapter.py ---
RUNNER = r"""
import fs from 'node:fs/promises';
import { createProject, readProjectDoc } from './cli/store.ts';
import { runToolSession } from './cli/session.ts';
import { makeDraft } from './src/editor/store.ts';
import { setStoredEntry } from './server/plugins/project-store.ts';
import { parseSrt } from './src/captions/srt.ts';
import { captionTrackEntries } from './src/editor/types.ts';
import { resolveCaptionWords } from './src/captions/resolve.ts';
import { containerStyle, effectivePreset } from './src/captions/renderStyles.ts';
import { acceptExportSubmission } from './server/plugins/export-submission.ts';
import { renderTimeline, setUploadsDirProvider } from './server/plugins/export-rendering.ts';
import { uploadDir, resolveUploadFile } from './server/media-dir.ts';
import { disposeServeBundle } from './remotion/serve-bundle.mjs';
const job = JSON.parse(await fs.readFile(process.argv[2], 'utf8'));
await fs.writeFile(job.reply+'.started','started');
let projectId = job.projectId;
try {
  if (job.mode === 'create') {
    const project = await createProject({name:job.name, width:job.width,height:job.height,fps:30});
    projectId = project.id;
    await runToolSession(projectId, [{tool:'import_assets',args:{paths:job.paths}}], {apply:true});
    const doc = await readProjectDoc(projectId);
    const draft = makeDraft(doc);
    const source = doc.assets.find(a=>resolveUploadFile(a.src.slice('/media/uploads/'.length))===job.source);
    if (!source) throw Error('source import missing');
    const v1 = draft.getState().trackOrder.find(t=>draft.getState().tracks[t]?.kind==='video');
    const words = job.subtitles ? parseSrt(await fs.readFile(job.subtitles,'utf8')) : [];
    for (const r of job.ranges) {
      const id = draft.commands.addMediaItem(source,{track:v1,startFrame:Math.round(r.output_start*30),srcInFrame:Math.round(r.source_start*30)});
      draft.commands.setItemTiming(id,{durationInFrames:Math.round((r.source_end-r.source_start)*30)});
      if(words.length) draft.commands.setItemTranscript(id,words);
    }
    for (const placement of job.overlays) {
      const asset=doc.assets.find(a=>resolveUploadFile(a.src.slice('/media/uploads/'.length))===placement.path);
      if(!asset) throw Error('animation import missing');
      const track=draft.commands.createTrack('video',{name:'Teaching overlay'});
      draft.commands.updateTrack(track,{muted:true});
      const id=draft.commands.addMediaItem(asset,{track,startFrame:placement.startFrame,srcInFrame:placement.srcInFrame});
      draft.commands.setItemTiming(id,{durationInFrames:placement.durationInFrames});
      draft.commands.setItemTransform(id,placement.transform);
    }
    if(words.length) draft.commands.createCaptionTrack({enabled:true,template:'plain',pacing:'word',sourceMode:'timeline',motionPreset:'none',
      styleOverride:{fontFamily:'PingFang SC',fontSize:20/job.height,color:'#ffffff',strokeColor:'#000000',strokeWidth:1},
      layout:{anchor:'bottom-center'}},{name:'Subtitles'});
    // Initialization owns a new UUID and library. All later edits use native
    // browser sessions and CAS; initialization never writes an existing project.
    await setStoredEntry(`project:${projectId}`,draft.getDoc());
  }
  const doc=await readProjectDoc(projectId);
  const state=doc.timelines.find(t=>t.id===doc.activeTimelineId);
  if(!state) throw Error('active timeline missing');
  if(job.mode==='render') {
    setUploadsDirProvider(uploadDir);
    const accepted=await acceptExportSubmission({state:{...state,assets:doc.assets},project:doc,timelineId:state.id,format:'video',codec:'h264'});
    try { const p=accepted.plan; await renderTimeline({state:p.state,project:p.project,timelineId:p.timelineId,
      outputLocation:job.output,codec:'h264',scale:p.scale,frameRange:p.frameRange,videoBitrate:8000000,
      hardwareAcceleration:'disable'}); }
    finally {await accepted.cleanup();}
  }
  const captions=captionTrackEntries(state).filter(e=>e.captions?.enabled)
    .flatMap(e=>resolveCaptionWords(e.captions,state.items,state.fps));
  await fs.writeFile(job.reply,JSON.stringify({projectId,doc,state,captions,captionTracks:captionTrackEntries(state).filter(e=>e.captions?.enabled).map(e=>({...e.captions,nativePlacement:containerStyle(effectivePreset(e.captions),e.captions.template,state.width,state.height,e.captions.layout)})),media:doc.assets.map(a=>({id:a.id,path:a.src.startsWith("/media/uploads/")?resolveUploadFile(a.src.slice("/media/uploads/".length)):null}))}));
} finally {await disposeServeBundle();}
"""
GUARD = r"""
import cp from 'node:child_process';
import {syncBuiltinESMExports} from 'node:module';
import {appendFileSync} from 'node:fs';
import {basename} from 'node:path';
for(const method of ['spawn','spawnSync','execFile','execFileSync','exec','execSync','fork']) {
 const original=cp[method]; cp[method]=function(file,...args) {
  const name=basename(String(file));
  const blocked=/codex|electron/i.test(name) || (['exec','execSync'].includes(method));
  appendFileSync(process.env.OCC_PROCESS_TRACE,JSON.stringify({pid:process.pid,method,executable:name,blocked})+'\n');
  if(blocked) throw Error('occ_builtin_agent_process_disabled');
  return original.call(this,file,...args);
 };
}
syncBuiltinESMExports();
"""
SERVER = r"""
import base from './config/vite.config.ts';
const essential=new Set(['vite:react-babel','vite:react-refresh','vite:react','openchatcut-ort-wasm-loader',
 'openchatcut-system-fonts','openchatcut-cross-origin-isolation','openchatcut-product-assets',
 'openchatcut-project-store','openchatcut-extension-store','openchatcut-external-agent',
 'openchatcut-upload','openchatcut-media-preview','openchatcut-probe-media']);
export default async function(env) {
 const cfg=typeof base==='function'?await base(env):base;
 const gate={name:'occ-deterministic-only',enforce:'pre',configureServer(server){
  server.middlewares.use((req,res,next)=>{
   const p=(req.url||'').split('?')[0];
   if(p.startsWith('/api/external-mcp') &&
      (!['127.0.0.1','::1','::ffff:127.0.0.1'].includes(req.socket.remoteAddress) ||
       req.headers.host !== `127.0.0.1:${process.env.OCC_PORT}` ||
       req.headers.origin !== `http://127.0.0.1:${process.env.OCC_PORT}`)) {
    res.statusCode=403;res.end('invalid local MCP origin');return;
   }
   if(p.startsWith('/api/') && !['/api/project-store','/api/extension-store','/api/external-agent','/api/external-mcp',
      '/api/system-font','/api/upload','/api/media-preview','/api/probe-media'].some(a=>p.startsWith(a))) {
    res.statusCode=403;res.setHeader('Content-Type','application/json');res.end('{"error":"occ_builtin_agent_disabled"}');return;
   }
   if(p.startsWith('/api/external-agent/connect-client')){res.statusCode=403;res.end('disabled');return;}
   next();
  });
 }};
 cfg.plugins=[gate,...cfg.plugins.flat(Infinity).filter(p=>p && essential.has(p.name))];
 cfg.server={...cfg.server,host:'127.0.0.1',port:Number(process.env.OCC_PORT),strictPort:true,open:false,proxy:{}};
 return cfg;
}
"""
BROWSER = r"""
import {chromium} from 'playwright';
import readline from 'node:readline';
const browser=await chromium.launch({executablePath:process.env.CC_BROWSER_EXECUTABLE,headless:process.env.OCC_HEADLESS_REFINE === "1"});
try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'?route.continue():route.abort());
 await page.goto(process.env.OCC_EDITOR_URL,{waitUntil:'domcontentloaded',timeout:90000});
 process.stdout.write('READY\n');
 const lines=readline.createInterface({input:process.stdin});
 for await(const line of lines) {
  const job=JSON.parse(line);
  if(job.mode==='close') break;
  if(job.mode==='undo') {
   await page.getByRole('button',{name:/^(Undo|撤销)$/}).click();
   await page.waitForTimeout(1000);
   if(job.path) await page.screenshot({path:job.path,fullPage:true});
   process.stdout.write('DONE\n');
  }
  if(job.mode==='screenshot') {
   await page.screenshot({path:job.path,fullPage:true});process.stdout.write('DONE\n');
  }
 }
} finally {await browser.close();}
"""

# --- openfilm_adapter.py ---
DEFAULT_PACKAGE = Path(__file__).resolve().parents[2] / ".tools/openfilm/node_modules/openfilm"
BRIDGE = Path(__file__).with_name('openfilm_bridge.mjs')

# --- otio_kdenlive.py ---
FPS = 30
EXCLUSIVE_LAYERS = frozenset({"primary"})
LAYER_TRACK_NAMES = {
    "background": "背景",
    "primary": "主画面",
    "overlay": "叠加",
}
KDENLIVE_REOPEN_PROBE_SECONDS = 2.0
KDENLIVE_SHUTDOWN_TIMEOUT_SECONDS = 5.0

# --- registry.py ---
BACKENDS = MappingProxyType({
    "otio_kdenlive": "edit_backends.kdenlive_adapter",
    "openfilm": "edit_backends.openfilm_adapter",
    "openchatcut": "edit_backends.openchatcut_adapter",
    "chatcut": "edit_backends.chatcut_adapter",
    "concat": "edit_backends.concat_adapter",
})
