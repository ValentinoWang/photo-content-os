#!/usr/bin/env python3
"""Exercise the installed Mac Concat with disposable synthetic media."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory, mkdtemp

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from edit_backends.concat_adapter import _app
from edit_backends.concat_mcp import ConcatMCP
from edit_backends.registry import get_backend


FPS = 30
DURATION = 20
CUTS = [(2, 4), (10, 13)]


def generate(root: Path) -> tuple[Path, Path, Path, Path]:
    source, overlay = root / "source.mp4", root / "overlay.mov"
    ffmpeg = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error"]
    subprocess.run([*ffmpeg, "-f", "lavfi", "-i", f"testsrc2=s=1080x1920:r={FPS}:d={DURATION}",
                    "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={DURATION}",
                    "-c:v", "libx264", "-preset", "ultrafast", "-threads", "2",
                    "-c:a", "aac", str(source)], check=True)
    subprocess.run([*ffmpeg,
                    "-f", "lavfi", "-i", "color=c=black@0:s=1080x1920:r=30:d=2,format=yuva444p10le",
                    "-f", "lavfi", "-i", "color=c=red:s=300x300:r=30:d=2,format=yuva444p10le",
                    "-filter_complex_threads", "2",
                    "-filter_complex", "[0:v][1:v]overlay=x=390:y=800:format=auto,format=yuva444p10le",
                    "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
                    "-threads", "2", str(overlay)], check=True)
    subtitles = root / "source.srt"
    subtitles.write_text(
        "1\n00:00:00,500 --> 00:00:01,500\n这是第一条。\n\n"
        "2\n00:00:06,000 --> 00:00:08,000\n红块之外能看到原片。\n\n"
        "3\n00:00:14,000 --> 00:00:16,000\n这条字幕随剪辑移动。\n",
        encoding="utf-8",
    )
    suggestions = root / "suggestions.json"
    suggestions.write_text(json.dumps({"suggestions": [
        {"type": "silence", "start": start, "end": end, "auto_cut_allowed": True}
        for start, end in CUTS
    ]}), encoding="utf-8")
    return source, overlay, subtitles, suggestions


def main():
    evidence_root = Path.home() / ".photo-content-os" / "evidence" / "concat-backend-smoke"
    evidence_root.mkdir(parents=True, exist_ok=True)
    evidence = Path(mkdtemp(prefix="run-", dir=evidence_root)).resolve()
    with TemporaryDirectory(prefix="concat-smoke-") as temporary:
        root = Path(temporary).resolve()
        source, overlay, subtitles, suggestions = generate(root)
        backend = get_backend("concat")
        output_dir = root / "render"
        try:
            probe = backend.probe()
            if not probe["runnable"]:
                raise RuntimeError(probe["reason"])
            print(f"Concat: {probe['version']} ({probe['status']})", flush=True)
            receipt = backend.render(source=source, subtitles=subtitles, suggestions_path=suggestions,
                                     output_dir=output_dir,
                                     animations=[{"path": overlay, "start": 6, "end": 8}])
            state = backend.read_back(project_dir=Path(receipt["project_dir"]))
            mp4 = subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,duration",
                "-of", "json", receipt["output"],
            ], text=True)
            metadata = json.loads(mp4)
            exported = float(metadata["format"]["duration"])
            expected = DURATION - sum(end - start for start, end in CUTS)
            print(f"Segments: {len(state['time_map'])}")
            print(f"Timeline duration: {state['duration']:.6f}s (expected {expected:.6f}s)")
            print(f"Captions: {len(state['captions'])}")
            print(f"Export duration: {exported:.6f}s")
            if state["time_map"] != [
                {"source_start": 0.0, "source_end": 2.0, "output_start": 0.0},
                {"source_start": 4.0, "source_end": 10.0, "output_start": 2.0},
                {"source_start": 13.0, "source_end": 20.0, "output_start": 8.0},
            ]:
                raise RuntimeError(f"unexpected source ranges: {state['time_map']}")
            if [(cue["start"], cue["end"], cue["text"]) for cue in state["captions"]] != [
                (0.5, 1.5, "这是第一条。"), (4.0, 6.0, "红块之外能看到原片。"),
                (9.0, 11.0, "这条字幕随剪辑移动。"),
            ]:
                raise RuntimeError(f"unexpected captions: {state['captions']}")
            if [(row["start"], row["end"]) for row in state["animations"]] != [(4.0, 6.0)]:
                raise RuntimeError(f"unexpected overlay: {state['animations']}")
            streams = {item["codec_type"]: float(item["duration"]) for item in metadata["streams"]}
            if (set(streams) != {"video", "audio"}
                    or any(abs(actual - expected) > 1 / FPS
                           for actual in (state["duration"], exported, *streams.values()))):
                raise RuntimeError(f"duration or stream mismatch: {streams}")

            project = receipt["project_dir"]
            frame = output_dir / "overlay-frame.png"
            with ConcatMCP(_app(), output_dir, Path(receipt["call_log"])) as mcp:
                mcp.call("project_open", {"path": project})
                mcp.call("preview_frame", {"path": project, "time": 5.0, "output": str(frame)})
                mcp.call("project_close", {"path": project, "save": False})
            delivered = evidence / frame.name
            shutil.copyfile(frame, delivered)
            print(f"Overlay preview at 5.000s: {delivered}")
        finally:
            backend.close()
            for name in ("concat-mcp.jsonl", "concat-mcp.stderr.log"):
                if (output_dir / name).is_file():
                    shutil.copyfile(output_dir / name, evidence / name)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(exc.returncode if exc.returncode > 0 else 128 - exc.returncode) from exc
