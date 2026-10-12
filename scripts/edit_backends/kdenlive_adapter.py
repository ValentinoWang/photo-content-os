"""Headless Kdenlive adapter delegating all timeline/render work to the producer."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess

from . import kdenlive_render
from .interface import BackendError, CloseResult, Description, Probe


class Backend:
    def __init__(self):
        self._application = None
        self._started = set()
        self._readback = None

    def describe(self) -> Description:
        return {"id": "otio_kdenlive", "display_name": "Kdenlive / MLT",
                "license": "GPL-3.0-only", "capabilities": {
                    "automatic_first_cut": True, "transparent_overlay": True,
                    "chinese_subtitle_burn_in": True, "web_refine": False,
                    "undo": False, "read_back": True, "export_formats": ["mp4"]}}

    def probe(self) -> Probe:
        executable = kdenlive_render.melt_executable()
        result: Probe = {"id": "otio_kdenlive", "installed": executable is not None,
                         "version": None, "runnable": False,
                         "status": "unavailable", "reason": "melt_unavailable"}
        if executable is None:
            return result
        try:
            completed = subprocess.run([executable, "-query", "filter=subtitle"],
                                       capture_output=True, text=True, timeout=15,
                                       env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
            text = completed.stdout + completed.stderr
            version = subprocess.run([executable, "--version"], capture_output=True,
                                     text=True, timeout=15,
                                     env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
            if completed.returncode or "identifier: subtitle" not in text or version.returncode:
                result["reason"] = "melt_probe_failed"
            else:
                kdenlive_render.require_otio()
                result.update(version=next((line.strip() for line in (version.stdout + version.stderr).splitlines()
                                            if line.strip().startswith("melt ")), None),
                              runnable=True, status="online", reason=None)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            result["reason"] = f"melt_probe_failed:{type(exc).__name__}"
        return result

    def render(self, *, source: Path, suggestions_path: Path, output_dir: Path,
               subtitles: Path | None = None, animations: list[dict] | None = None,
               project_id: str = "spoken-test", project_revision: int = 1,
               timeout_seconds: float = 300) -> dict:
        output_dir = output_dir.expanduser().resolve()
        # Never overwrite another run's receipt, including on preflight failure.
        if output_dir.exists():
            raise BackendError("output_directory_already_exists")
        if self._readback and Path(source).resolve()==self._readback['render_kwargs']['source'] and project_id==self._readback['project_id'] and project_revision==self._readback['project_revision']:
            from .kdenlive_readback import render_saved
            return render_saved(project_dir=self._readback['directory'],expected_revision=self._readback['engine_revision'],output_dir=output_dir,timeout_seconds=timeout_seconds)
        try:
            return kdenlive_render.render(
                source=source, suggestions_path=suggestions_path, output_dir=output_dir,
                subtitles=subtitles, animations=animations, project_id=project_id,
                project_revision=project_revision, timeout_seconds=timeout_seconds)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            output_dir.mkdir(parents=True, exist_ok=True)
            receipt = output_dir / "render-result.json"
            if not receipt.exists():
                kdenlive_render.write_json(receipt, {
                    "status": "failed", "editor_backend": "otio_kdenlive",
                    "project_id": project_id, "project_revision": project_revision,
                    "reason": str(exc) if isinstance(exc, ValueError) else type(exc).__name__})
            raise BackendError(str(exc)) from exc

    def open_for_refine(self, *, project_dir: Path) -> dict:
        import json
        project=project_dir.resolve()/'timeline.kdenlive'
        receipt=project_dir.resolve()/'render-result.json'
        executable=Path('/Applications/kdenlive.app/Contents/MacOS/kdenlive')
        if not receipt.is_file() or not project.is_file() or not executable.is_file():
            raise BackendError('kdenlive_refine_unsupported_missing_project')
        result=json.loads(receipt.read_text())
        if result.get('status')!='candidate' or result.get('editor_backend')!='otio_kdenlive':
            raise BackendError('kdenlive_owned_project_required')
        if self._application is None or self._application.poll() is not None:
            self._application=subprocess.Popen([str(executable),str(project)],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self._started.add(self._application.pid)
        return {'editor_backend':'otio_kdenlive','opened':True,'local_only':True}

    def read_back(self, *, project_dir: Path) -> dict:
        from .kdenlive_readback import read_project
        result=read_project(project_dir)
        self._readback={**result,'directory':project_dir.resolve()}
        return result

    def close(self) -> CloseResult:
        from .openfilm_adapter import _stop, _process_table
        if self._application:
            self._started.update(_stop(self._application))
            self._application=None
        return {'id':'otio_kdenlive','started_pids':sorted(self._started),'remaining_pids':sorted(self._started.intersection(_process_table()))}
