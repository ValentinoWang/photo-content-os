"""Deterministic, local OpenChatCut bridge; no Electron or built-in AI agent."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import time
import urllib.request

from .interface import BackendError, CloseResult, Description, Probe
from . import kdenlive_render as planning
from .otio_kdenlive import FPS, frames, sha256_file, write_json

# These bridges use the editor's own store, commands, import and render pipeline.
# They are materialized beside its dependencies, never imported from Media.
RUNNER = r"""
import fs from 'node:fs/promises';
import { createProject, readProjectDoc } from './cli/store.ts';
import { runToolSession } from './cli/session.ts';
import { makeDraft } from './src/editor/store.ts';
import { setStoredEntry } from './server/plugins/project-store.ts';
import { parseSrt } from './src/captions/srt.ts';
import { captionTrackEntries } from './src/editor/types.ts';
import { resolveCaptionWords } from './src/captions/resolve.ts';
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
  await fs.writeFile(job.reply,JSON.stringify({projectId,doc,state,captions,media:doc.assets.map(a=>({id:a.id,path:a.src.startsWith("/media/uploads/")?resolveUploadFile(a.src.slice("/media/uploads/".length)):null}))}));
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


class Backend:
    def __init__(self):
        self.root = (
            Path(
                os.environ.get(
                    "CONTENT_OS_OPENCHATCUT_ROOT",
                    "/Users/vsiyo/Desktop/Opensource_Tool/OpenChatCut",
                )
            )
            .expanduser()
            .resolve()
        )
        self.node = Path(
            os.environ.get(
                "CONTENT_OS_OPENCHATCUT_NODE",
                "/Users/vsiyo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
            )
        )
        self.browser = Path(
            os.environ.get(
                "CONTENT_OS_OPENCHATCUT_BROWSER",
                "/Users/vsiyo/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell",
            )
        )
        self.slot = Path(
            os.environ.get(
                "CONTENT_OS_CHROMIUM_SLOT",
                "/Users/vsiyo/Desktop/创业项目/自媒体创作Agent/apps/media/web/scripts/qa/withChromiumSlot.sh",
            )
        )
        self.refine_browser = Path(
            os.environ.get(
                "CONTENT_OS_OPENCHATCUT_REFINE_BROWSER",
                "/Users/vsiyo/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
            )
        )
        self._processes = []
        self._started = []
        self._session = None
        self._readback = None
        self._token = secrets.token_urlsafe(32)
        self._rpc_id = 0
        self._mcp_session = None
        self._closed = None
        self._queue_seconds = 0.0

    def describe(self) -> Description:
        return {
            "id": "openchatcut",
            "display_name": "OpenChatCut",
            "license": "AGPL-3.0-or-later",
            "capabilities": {
                "automatic_first_cut": True,
                "transparent_overlay": True,
                "chinese_subtitle_burn_in": True,
                "web_refine": True,
                "undo": True,
                "read_back": True,
                "export_formats": ["mp4"],
            },
        }

    def probe(self) -> Probe:
        installed = (self.root / "cli/main.ts").is_file()
        result = {
            "id": "openchatcut",
            "installed": installed,
            "version": None,
            "runnable": False,
            "status": "unavailable",
            "reason": "openchatcut_runtime_missing",
        }
        if not all(
            p.is_file()
            for p in (
                self.node,
                self.browser,
                self.slot,
                self.root / "node_modules/tsx/dist/loader.mjs",
                self.root / "node_modules/playwright/package.json",
            )
        ):
            return result
        try:
            version = subprocess.run(
                [str(self.node), "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            ).stdout.strip()
            if not version.startswith("v24."):
                raise BackendError("openchatcut_requires_node24")
            command = subprocess.run(
                [str(self.node), "--import", "tsx", "cli/main.ts", "--help"],
                cwd=self.root,
                env=self._environment(),
                capture_output=True,
                text=True,
                check=True,
                timeout=20,
            )
            if "occ — OpenChatCut" not in command.stdout:
                raise BackendError("openchatcut_cli_probe_invalid")
            result.update(
                version=json.loads((self.root / "package.json").read_text())["version"],
                runnable=True,
                status="online",
                reason=None,
            )
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            result["reason"] = f"openchatcut_probe_failed:{type(exc).__name__}"
        return result

    def _environment(self, library=None, workspace=None):
        # Secrets and provider settings in the invoking shell never enter OCC.
        env = {
            k: os.environ[k]
            for k in ("HOME", "TMPDIR", "LANG", "LC_ALL")
            if k in os.environ
        }
        env.update(
            PATH=f"{self.node.parent}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
            CC_BROWSER_EXECUTABLE=str(self.browser),
            OPENCHATCUT_FFMPEG=shutil.which("ffmpeg") or "ffmpeg",
            OPENCHATCUT_FFPROBE=shutil.which("ffprobe") or "ffprobe",
            OPENCHATCUT_RENDER_CONCURRENCY="1",
            OPENCHATCUT_DISABLE_HARDWARE_ENCODING="1",
            CC_RENDER_VIDEO_DECODER="offthread",
            OPENCHATCUT_MCP_TOKEN=self._token,
        )
        if library:
            env["OPENCHATCUT_DATA_DIR"] = str(library)
        if workspace:
            env.update(
                OCC_PROCESS_TRACE=str(workspace / "process-trace.jsonl"),
                NODE_OPTIONS=f"--import={self.root / '.occ-guard.mjs'}",
                TMPDIR=str(workspace / "tmp"),
            )
        return env

    def _prepare(self):
        for name, value in (
            (".occ-runner.ts", RUNNER),
            (".occ-guard.mjs", GUARD),
            (".occ-vite.ts", SERVER),
            (".occ-browser.mjs", BROWSER),
        ):
            path = self.root / name
            if not path.exists() or path.read_text() != value:
                path.write_text(value)

    def _stop(self, process):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=8)

    def _run(self, job, workspace, library, timeout, browser=False):
        request = workspace / f"job-{job['mode']}.json"
        reply = workspace / f"reply-{job['mode']}.json"
        write_json(request, {**job, "reply": str(reply)})
        env = self._environment(library, workspace)
        cmd = [
            str(self.node),
            "--import",
            "tsx",
            str(self.root / ".occ-runner.ts"),
            str(request),
        ]
        if browser:
            cmd = ["bash", str(self.slot), "--", *cmd]
        with (workspace / f"{job['mode']}.log").open("w") as log:
            p = subprocess.Popen(
                cmd,
                cwd=self.root,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
            try:
                if browser:
                    # Queue time belongs to the shared Chromium scheduler. The
                    # render deadline starts only after it grants the slot.
                    queued_at = time.monotonic()
                    queue_deadline = queued_at + 900
                    while (
                        p.poll() is None and not Path(str(reply) + ".started").exists()
                    ):
                        if time.monotonic() >= queue_deadline:
                            raise BackendError("openchatcut_chromium_queue_timeout")
                        time.sleep(0.1)
                    self._queue_seconds += time.monotonic() - queued_at
                code = p.wait(timeout=max(0.001, timeout))
                if code or not reply.is_file():
                    raise BackendError(
                        f"openchatcut_{job['mode']}_failed:see_local_log"
                    )
            finally:
                self._stop(p)
        return json.loads(reply.read_text())

    def render(
        self,
        *,
        source: Path,
        suggestions_path: Path,
        output_dir: Path,
        subtitles: Path | None = None,
        animations: list[dict] | None = None,
        project_id: str = "spoken-test",
        project_revision: int = 1,
        timeout_seconds: float = 300,
    ) -> dict:
        output_dir = output_dir.expanduser().resolve()
        if output_dir.exists():
            raise BackendError("output_directory_already_exists")
        output_dir.mkdir(parents=True)
        result = {
            "status": "failed",
            "editor_backend": "openchatcut",
            "project_id": project_id,
            "project_revision": project_revision,
        }
        started = time.monotonic()
        self._queue_seconds = 0.0
        try:
            if (
                type(project_revision) is not int
                or project_revision < 1
                or not isinstance(project_id, str)
                or not project_id.strip()
            ):
                raise BackendError("render_project_identity_invalid")
            if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
                raise BackendError("render_timeout_invalid")
            source, suggestions_path = (
                source.expanduser().resolve(),
                suggestions_path.expanduser().resolve(),
            )
            subtitles = subtitles.expanduser().resolve() if subtitles else None
            metadata = planning.probe_media(source)
            video = next(v for v in metadata["streams"] if v["codec_type"] == "video")
            if not any(v["codec_type"] == "audio" for v in metadata["streams"]):
                raise BackendError("source_requires_video_and_audio")
            duration = float(video.get("duration") or metadata["format"]["duration"])
            width, height = int(video["width"]), int(video["height"])
            if width % 2 or height % 2:
                raise BackendError("h264_requires_even_dimensions")
            suggestions = json.loads(suggestions_path.read_text())
            ranges, ignored = planning.plan_ranges(suggestions, duration)
            inputs = [
                {
                    "path": str(source),
                    "sha256": sha256_file(source),
                    "role": "original_video",
                },
                {
                    "path": str(suggestions_path),
                    "sha256": sha256_file(suggestions_path),
                    "role": "edit_suggestions",
                },
            ]
            if subtitles:
                inputs.append(
                    {
                        "path": str(subtitles),
                        "sha256": sha256_file(subtitles),
                        "role": "source_subtitles",
                    }
                )
            conversions = []
            if not self.probe()["runnable"]:
                raise BackendError("openchatcut_runtime_unavailable")
            self._prepare()
            (output_dir / "tmp").mkdir()
            remaining = (
                lambda: timeout_seconds
                - (time.monotonic() - started)
                + self._queue_seconds
            )
            if remaining() <= 0:
                raise subprocess.TimeoutExpired("openchatcut", timeout_seconds)
            previous = self._readback
            if (
                previous
                and previous["source"] == str(source)
                and previous["project_id"] == project_id
                and previous["project_revision"] == project_revision
            ):
                library, occ_id = Path(previous["library"]), previous["occ_project_id"]
                data = self._run(
                    {"mode": "read", "projectId": occ_id},
                    output_dir,
                    library,
                    remaining(),
                )
                ranges = self._ranges(data, previous["source_asset_id"])
                inputs = previous["inputs"]
            else:
                library = output_dir / "library"
                paths, overlays = [str(source)], []
                for item in animations or []:
                    path = Path(item["path"]).expanduser().resolve()
                    info = planning.probe_media(path)
                    stream = next(
                        v for v in info["streams"] if v["codec_type"] == "video"
                    )
                    clip_duration = float(
                        stream.get("duration") or info["format"]["duration"]
                    )
                    if "start" not in item:
                        matches = [
                            s
                            for s in suggestions["suggestions"]
                            if s.get("type") == "animation"
                            and s.get("animation_id") == item.get("animation_id")
                        ]
                        if len(matches) != 1 or matches[0].get("ambiguous"):
                            raise BackendError(
                                "animation_position_missing_or_ambiguous"
                            )
                        start, end = planning.seconds(matches[0]["start"]), min(
                            planning.seconds(matches[0]["end"]),
                            planning.seconds(matches[0]["start"]) + clip_duration,
                        )
                    else:
                        start, end = planning.seconds(item["start"]), planning.seconds(
                            item.get("end", item["start"] + clip_duration)
                        )
                    if (
                        end <= start
                        or end > duration + 1e-6
                        or end - start > clip_duration + 1 / FPS
                    ):
                        raise BackendError("animation_range_invalid")
                    g = item.get(
                        "geometry",
                        {
                            "x": 0,
                            "y": 0,
                            "width": stream["width"],
                            "height": stream["height"],
                        },
                    )
                    if (
                        set(g) != {"x", "y", "width", "height"}
                        or any(type(v) is not int for v in g.values())
                        or min(g["x"], g["y"]) < 0
                        or min(g["width"], g["height"]) <= 0
                        or g["x"] + g["width"] > width
                        or g["y"] + g["height"] > height
                    ):
                        raise BackendError("animation_geometry_invalid")
                    if g["width"] / stream["width"] != g["height"] / stream["height"]:
                        raise BackendError("animation_nonuniform_geometry_unsupported")
                    fit = min(width / stream["width"], height / stream["height"])
                    scale = g["width"] / (stream["width"] * fit)
                    for a, b, offset in planning.remap_span(start, end, ranges):
                        overlays.append(
                            {
                                "path": str(path),
                                "name": path.name,
                                "startFrame": frames(a),
                                "durationInFrames": frames(b - a),
                                "srcInFrame": frames(offset),
                                "transform": {
                                    "scale": scale,
                                    "x": 100
                                    * ((g["x"] + g["width"] / 2) / width - 0.5),
                                    "y": 100
                                    * ((g["y"] + g["height"] / 2) / height - 0.5),
                                },
                            }
                        )
                    if path.suffix.lower() == ".mov" and str(
                        stream.get("pix_fmt", "")
                    ).startswith(("yuva", "rgba", "gbrap")):
                        converted = output_dir / f"overlay-{len(conversions)}.webm"
                        subprocess.run(
                            [
                                "ffmpeg",
                                "-v",
                                "error",
                                "-i",
                                str(path),
                                "-map",
                                "0:v:0",
                                "-an",
                                "-c:v",
                                "libvpx-vp9",
                                "-lossless",
                                "1",
                                "-pix_fmt",
                                "yuva420p",
                                "-auto-alt-ref",
                                "0",
                                "-metadata:s:v:0",
                                "alpha_mode=1",
                                str(converted),
                            ],
                            check=True,
                            capture_output=True,
                            timeout=max(0.001, remaining()),
                        )
                        for placement in overlays:
                            if placement["path"] == str(path):
                                placement.update(
                                    path=str(converted), name=converted.name
                                )
                        conversions.append(
                            {
                                "source": str(path),
                                "output": str(converted),
                                "operation": "lossless_vp9_alpha",
                                "sha256": sha256_file(converted),
                            }
                        )
                        paths.append(str(converted))
                    else:
                        paths.append(str(path))
                    inputs.append(
                        {
                            "path": str(path),
                            "sha256": sha256_file(path),
                            "role": "teaching_animation",
                        }
                    )
                data = self._run(
                    {
                        "mode": "create",
                        "name": f"{project_id}-r{project_revision}",
                        "width": width,
                        "height": height,
                        "paths": paths,
                        "source": str(source),
                        "sourceName": source.name,
                        "ranges": ranges,
                        "subtitles": str(subtitles) if subtitles else None,
                        "overlays": overlays,
                    },
                    output_dir,
                    library,
                    remaining(),
                )
                occ_id = data["projectId"]
            source_ids = {m["id"] for m in data["media"] if m["path"] == str(source)}
            if len(source_ids) != 1:
                raise BackendError("openchatcut_source_identity_ambiguous")
            source_asset = next(
                a for a in data["doc"]["assets"] if a["id"] in source_ids
            )
            ranges = self._ranges(data, source_asset["id"])
            if previous and library == Path(previous["library"]):
                conversions = previous.get("conversions", [])
            result["conversions"] = conversions
            binding = {
                "source": str(source),
                "suggestions_path": str(suggestions_path),
                "subtitles": str(subtitles) if subtitles else None,
                "animations": animations or [],
                "project_id": project_id,
                "project_revision": project_revision,
                "occ_project_id": occ_id,
                "source_asset_id": source_asset["id"],
                "library": str(library),
                "inputs": inputs,
                "conversions": conversions,
            }
            write_json(output_dir / "openchatcut-project.json", binding)
            output = output_dir / "candidate.mp4"
            native_output = output_dir / "openchatcut-native.mp4"
            data = self._run(
                {"mode": "render", "projectId": occ_id, "output": str(native_output)},
                output_dir,
                library,
                remaining(),
                browser=True,
            )
            if not native_output.is_file() or not native_output.stat().st_size:
                raise BackendError("openchatcut_missing_mp4")
            for asset in data["doc"]["assets"]:
                if not asset["src"].startswith("/media/uploads/"):
                    raise BackendError("openchatcut_nonlocal_media_rejected")
                media_path = next(
                    m["path"] for m in data["media"] if m["id"] == asset["id"]
                )
                if not media_path:
                    raise BackendError("openchatcut_local_media_missing")
                media = Path(media_path).resolve()
                inputs.append(
                    {
                        "path": str(media),
                        "sha256": sha256_file(media),
                        "role": "editor_imported_media",
                    }
                )
            by_path = {}
            for item in inputs:
                by_path.setdefault(item["path"], item)
            inputs = list(by_path.values())
            binding["inputs"] = inputs
            write_json(output_dir / "openchatcut-project.json", binding)
            total = (
                max(
                    i["startFrame"] + i["durationInFrames"]
                    for i in data["state"]["items"]
                )
                / FPS
            )
            if total != sum(r["source_end"] - r["source_start"] for r in ranges):
                raise BackendError("openchatcut_timeline_has_gap_or_tail")
            # Remotion's AAC priming adds a container tail. Stream-copy only:
            # no alternate renderer, filtering, re-encoding or timeline change.
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-i",
                    str(native_output),
                    "-c",
                    "copy",
                    "-t",
                    str(total),
                    "-movflags",
                    "+faststart",
                    str(output),
                ],
                check=True,
                capture_output=True,
                timeout=max(0.001, remaining()),
            )
            result["container_finalization"] = {
                "operation": "stream_copy_trim_aac_tail",
                "native_sha256": sha256_file(native_output),
            }
            native_output.unlink()
            subtitle_output = output_dir / "subtitles.srt" if data["captions"] else None
            if subtitle_output:
                words = data["captions"]
                subtitle_output.write_text(
                    "\n\n".join(
                        f"{i}\n{planning.srt_timestamp(w['start']/1000)} --> {planning.srt_timestamp(w['end']/1000)}\n{w['text']}"
                        for i, w in enumerate(words, 1)
                    )
                    + "\n"
                )
            cuts, cursor = [], 0.0
            for r in [
                *ranges,
                {
                    "source_start": frames(duration) / FPS,
                    "source_end": frames(duration) / FPS,
                },
            ]:
                if r["source_start"] > cursor:
                    contributors = [
                        i
                        for i in suggestions["suggestions"]
                        if i.get("auto_cut_allowed") is True
                        and i.get("type") in {"silence", "repetition"}
                        and i["start"] < r["source_start"]
                        and i["end"] > cursor
                    ]
                    cuts.append(
                        {
                            "kind": (
                                "editor_edit"
                                if previous and library == Path(previous["library"])
                                else (
                                    "retake"
                                    if any(
                                        i["type"] == "repetition" for i in contributors
                                    )
                                    else "silence"
                                )
                            ),
                            "startSeconds": cursor,
                            "endSeconds": r["source_start"],
                        }
                    )
                cursor = r["source_end"]
            manifest = {
                "contract": "video_pipeline_manifest.v1",
                "output": {"path": str(output), "sha256": sha256_file(output)},
                "inputs": inputs,
                "fps": float(FPS),
                "width": width,
                "height": height,
                "duration": total,
                "audio_tracks": 1,
                "video_tracks": 1,
                "time_map": ranges,
                "executed_cuts": cuts,
                "animation_placements": self._placements(data, source_asset["id"]),
                "assets": [],
                "ignored_review_only": ignored,
                "subtitles": str(subtitle_output) if subtitle_output else None,
                "subtitle_burned_in": bool(subtitle_output),
                "subtitle_bottom_ratio": 0.8 if subtitle_output else 0,
                "removed_seconds": frames(duration) / FPS - total,
            }
            manifest_path = output_dir / "candidate.mp4.manifest.json"
            write_json(manifest_path, manifest)
            checks = planning.review_module().check_pipeline_manifest(manifest_path)
            result.update(
                status="candidate" if checks["status"] == "passed" else "failed",
                output=str(output),
                manifest=str(manifest_path),
                duration=total,
                frames=frames(total),
                removed_seconds=manifest["removed_seconds"],
                checks=checks,
            )
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            StopIteration,
            subprocess.SubprocessError,
        ) as exc:
            result["reason"] = (
                str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            )
        finally:
            shutil.rmtree(output_dir / "tmp", ignore_errors=True)
        write_json(output_dir / "render-result.json", result)
        return result

    def _ranges(self, data, asset_id):
        if any(
            not a["src"].startswith("/media/uploads/") for a in data["doc"]["assets"]
        ):
            raise BackendError("openchatcut_nonlocal_media_rejected")
        state = data["state"]
        if state["fps"] != FPS:
            raise BackendError("openchatcut_changed_fps_unsupported")
        clips = sorted(
            (i for i in state["items"] if i.get("sourceAssetId") == asset_id),
            key=lambda i: i["startFrame"],
        )
        if not clips:
            raise BackendError("openchatcut_source_timeline_missing")
        ranges = []
        for item in clips:
            if item.get("playbackRate", 1) != 1:
                raise BackendError("openchatcut_speed_change_unsupported")
            start = item.get("srcInFrame", 0)
            ranges.append(
                {
                    "source_start": start / FPS,
                    "source_end": (start + item["durationInFrames"]) / FPS,
                    "output_start": item["startFrame"] / FPS,
                }
            )
        return ranges

    def _placements(self, data, source_id):
        state = data["state"]
        width, height = state["width"], state["height"]
        placements = []
        for item in state["items"]:
            if item.get("sourceAssetId") == source_id or item["kind"] != "video":
                continue
            transform = item.get("transform", {})
            fit = min(width / item["width"], height / item["height"])
            w = item["width"] * fit * transform.get("scaleX", transform.get("scale", 1))
            h = (
                item["height"]
                * fit
                * transform.get("scaleY", transform.get("scale", 1))
            )
            placements.append(
                {
                    "editor_item_id": item["id"],
                    "editor_asset_id": item.get("sourceAssetId"),
                    "start": item["startFrame"] / FPS,
                    "end": (item["startFrame"] + item["durationInFrames"]) / FPS,
                    "source_start": item.get("srcInFrame", 0) / FPS,
                    "geometry": {
                        "x": round(width * (0.5 + transform.get("x", 0) / 100) - w / 2),
                        "y": round(
                            height * (0.5 + transform.get("y", 0) / 100) - h / 2
                        ),
                        "width": round(w),
                        "height": round(h),
                    },
                    "transform": transform,
                }
            )
        return placements

    def _rpc(self, method, params=None, notification=False):
        self._rpc_id += 1
        payload = {"jsonrpc": "2.0", "method": method}
        if not notification:
            payload["id"] = self._rpc_id
        if params is not None:
            payload["params"] = params
        headers = {
            "Origin": self._session["origin"],
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self._token}",
        }
        if self._mcp_session:
            headers["Mcp-Session-Id"] = self._mcp_session
        req = urllib.request.Request(
            self._session["origin"] + "/api/external-mcp/mcp?toolExposure=full",
            json.dumps(payload).encode(),
            headers,
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            self._mcp_session = response.headers.get(
                "Mcp-Session-Id", self._mcp_session
            )
            raw = response.read().decode()
        if notification:
            return None
        if raw.startswith("event:") or raw.startswith("data:"):
            rows = [
                json.loads(line[5:].strip())
                for line in raw.splitlines()
                if line.startswith("data:")
            ]
            reply = next(r for r in rows if r.get("id") == self._rpc_id)
        else:
            reply = json.loads(raw)
        if "error" in reply:
            raise BackendError("openchatcut_mcp_error:" + str(reply["error"]))
        result = reply["result"]
        if result.get("isError"):
            raise BackendError("openchatcut_tool_failed:" + str(result.get("content")))
        return result

    def _tool(self, name, args):
        result = self._rpc("tools/call", {"name": name, "arguments": args})
        if result.get("structuredContent") is not None:
            content = result["structuredContent"]
            if isinstance(content, dict) and (
                content.get("error") or content.get("ok") is False
            ):
                raise BackendError("openchatcut_tool_rejected:" + str(content))
            return content
        texts = [c["text"] for c in result.get("content", []) if c["type"] == "text"]
        try:
            return json.loads("\n".join(texts))
        except ValueError:
            raise BackendError("openchatcut_tool_reply_invalid")

    def open_for_refine(self, *, project_dir: Path) -> dict:
        if self._session:
            raise BackendError("openchatcut_refine_session_already_open")
        self._closed = None
        project_dir = project_dir.resolve()
        binding = json.loads((project_dir / "openchatcut-project.json").read_text())
        self._prepare()
        (project_dir / "tmp").mkdir(exist_ok=True)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        origin = f"http://127.0.0.1:{port}"
        env = self._environment(binding["library"], project_dir)
        env.update(OCC_PORT=str(port), OPENCHATCUT_EDITOR_URL=origin)
        log = (project_dir / "refine-server.log").open("w")
        p = subprocess.Popen(
            [
                str(self.node),
                "--import",
                "tsx",
                str(self.root / "node_modules/vite/bin/vite.js"),
                "--config",
                str(self.root / ".occ-vite.ts"),
            ],
            cwd=self.root,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
        self._processes.append((p, log))
        self._started.append(p.pid)
        self._session = {
            "origin": origin,
            "binding": binding,
            "project_dir": str(project_dir),
        }
        try:
            for _ in range(100):
                if p.poll() is not None:
                    raise BackendError("openchatcut_refine_server_failed:see_local_log")
                try:
                    with urllib.request.urlopen(origin, timeout=1):
                        break
                except OSError:
                    time.sleep(0.2)
            else:
                raise BackendError("openchatcut_refine_server_timeout")
            env["OCC_HEADLESS_REFINE"] = (
                "1" if os.environ.get("EI_TEST_BACKEND") == "openchatcut" else "0"
            )
            if env["OCC_HEADLESS_REFINE"] == "0":
                if not self.refine_browser.is_file():
                    raise BackendError("openchatcut_visible_browser_missing")
                env["CC_BROWSER_EXECUTABLE"] = str(self.refine_browser)
            env["OCC_EDITOR_URL"] = origin + "/#/editor/" + binding["occ_project_id"]
            blog = (project_dir / "refine-browser.log").open("w")
            browser = subprocess.Popen(
                [
                    "bash",
                    str(self.slot),
                    "--",
                    str(self.node),
                    str(self.root / ".occ-browser.mjs"),
                ],
                cwd=self.root,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=blog,
                text=True,
                start_new_session=True,
            )
            self._processes.append((browser, blog))
            self._started.append(browser.pid)
            import selectors

            with selectors.DefaultSelector() as selector:
                selector.register(browser.stdout, selectors.EVENT_READ)
                if (
                    not selector.select(1000)
                    or browser.stdout.readline().strip() != "READY"
                ):
                    raise BackendError("openchatcut_refine_browser_failed")
            self._rpc(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "content-os-occ", "version": "1"},
                },
            )
            self._rpc("notifications/initialized", notification=True)
            for attempt in range(60):
                status = self._tool("openchatcut_status", {})
                if str(binding["occ_project_id"]) in json.dumps(status):
                    break
                time.sleep(0.3)
            self._tool("target_project", {"projectId": binding["occ_project_id"]})
            evidence = os.environ.get("EI_TEST_EVIDENCE")
            if evidence:
                image = Path(evidence).resolve() / "refine-editor.png"
                image.parent.mkdir(parents=True, exist_ok=True)
                browser.stdin.write(
                    json.dumps({"mode": "screenshot", "path": str(image)}) + "\n"
                )
                browser.stdin.flush()
                with selectors.DefaultSelector() as selector:
                    selector.register(browser.stdout, selectors.EVENT_READ)
                    if (
                        not selector.select(30)
                        or browser.stdout.readline().strip() != "DONE"
                    ):
                        raise BackendError("openchatcut_refine_capture_failed")
            return {
                "editor_backend": "openchatcut",
                "url": env["OCC_EDITOR_URL"],
                "project_id": binding["project_id"],
                "project_revision": binding["project_revision"],
                "local_only": True,
            }
        except BaseException:
            self.close()
            raise

    def read_back(self, *, project_dir: Path) -> dict:
        binding = json.loads(
            (project_dir.resolve() / "openchatcut-project.json").read_text()
        )
        workspace = project_dir.resolve()
        (workspace / "tmp").mkdir(exist_ok=True)
        data = self._run(
            {"mode": "read", "projectId": binding["occ_project_id"]},
            workspace,
            Path(binding["library"]),
            30,
        )
        ranges = self._ranges(data, binding["source_asset_id"])
        self._readback = binding
        return {
            "time_map": ranges,
            "render_kwargs": {
                "source": Path(binding["source"]),
                "suggestions_path": Path(binding["suggestions_path"]),
                "subtitles": (
                    Path(binding["subtitles"]) if binding["subtitles"] else None
                ),
                "animations": binding["animations"],
                "project_id": binding["project_id"],
                "project_revision": binding["project_revision"],
                "timeout_seconds": 300,
            },
        }

    def _owned_pids(self):
        rows = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,pgid="],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        table = [tuple(map(int, row.split())) for row in rows]
        owned = {p.pid for p, _ in self._processes}
        while True:
            expanded = owned | {
                pid for pid, parent, group in table if parent in owned or group in owned
            }
            if expanded == owned:
                return owned & {pid for pid, _, _ in table}
            owned = expanded

    def close(self) -> CloseResult:
        if self._closed is not None:
            return self._closed
        owned = self._owned_pids() if self._processes else set()
        self._started = sorted(set(self._started) | owned)
        for p, log in reversed(self._processes):
            self._stop(p)
            log.close()
            if p.stdin:
                p.stdin.close()
            if p.stdout:
                p.stdout.close()
        deadline = time.monotonic() + 5
        remaining = owned
        while remaining and time.monotonic() < deadline:
            observed = {
                int(row.strip())
                for row in subprocess.run(
                    ["ps", "-axo", "pid="], capture_output=True, text=True, check=True
                ).stdout.splitlines()
            }
            remaining = owned & observed
            if remaining:
                time.sleep(0.1)
        evidence = os.environ.get("EI_TEST_EVIDENCE")
        if evidence and self._session:
            destination = Path(evidence).resolve()
            destination.mkdir(parents=True, exist_ok=True)
            project = Path(self._session["project_dir"])
            for name in (
                "process-trace.jsonl",
                "refine-server.log",
                "refine-browser.log",
            ):
                if (project / name).exists():
                    shutil.copy2(project / name, destination / name)
            shutil.rmtree(project / "tmp", ignore_errors=True)
        remaining = sorted(remaining)
        self._closed = {
            "id": "openchatcut",
            "started_pids": self._started.copy(),
            "remaining_pids": remaining,
        }
        self._session = None
        return self._closed


def delete_segment(backend: Backend, project_dir: Path, index: int) -> None:
    """Apply a native browser edit session; linked layers follow the ripple cut."""
    data = backend._run(
        {"mode": "read", "projectId": backend._session["binding"]["occ_project_id"]},
        project_dir,
        Path(backend._session["binding"]["library"]),
        30,
    )
    source_id = backend._session["binding"]["source_asset_id"]
    clips = sorted(
        (i for i in data["state"]["items"] if i.get("sourceAssetId") == source_id),
        key=lambda i: i["startFrame"],
    )
    clip = clips[index]
    end = clip["startFrame"] + clip["durationInFrames"]
    updates = [
        {
            "type": i["kind"],
            "itemId": i["id"],
            "fromFrame": i["startFrame"] - clip["durationInFrames"],
        }
        for i in data["state"]["items"]
        if i["id"] != clip["id"] and i["startFrame"] >= end
    ]
    session = backend._tool(
        "begin_edit_session",
        {"clientName": "Content OS qualification", "approvalMode": "auto"},
    )
    session_id = session["editSessionId"]
    backend._tool(
        "edit_item",
        {
            "editSessionId": session_id,
            "deletes": [{"type": "video", "itemId": clip["id"]}],
        },
    )
    backend._tool("edit_item", {"editSessionId": session_id, "updates": updates})
    backend._tool(
        "review_edit_session",
        {
            "editSessionId": session_id,
            "summary": "Delete one retained segment and ripple linked layers",
        },
    )
    time.sleep(0.5)


def undo(backend: Backend, project_dir: Path) -> None:
    """Click the editor's native Undo control, then read its saved project."""
    browser = backend._processes[-1][0]
    payload = {"mode": "undo"}
    if os.environ.get("EI_TEST_EVIDENCE"):
        payload["path"] = str(
            Path(os.environ["EI_TEST_EVIDENCE"]).resolve() / "refine-restored.png"
        )
    browser.stdin.write(json.dumps(payload) + "\n")
    browser.stdin.flush()
    import selectors

    with selectors.DefaultSelector() as selector:
        selector.register(browser.stdout, selectors.EVENT_READ)
        if not selector.select(30) or browser.stdout.readline().strip() != "DONE":
            raise BackendError("openchatcut_native_undo_failed")
