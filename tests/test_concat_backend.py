"""Concat contract tests with a real stdio child and synthetic tool responses."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from edit_backends.concat_mcp import ConcatMCP
from edit_backends.interface import BackendError


SERVER = """\
import json
import os
import signal
import sys
import time

assert sys.argv[1:] == ["--mcp", "headless"]
signal.signal(signal.SIGTERM, signal.SIG_IGN)
initialized = False
for line in sys.stdin:
    msg = json.loads(line)
    method = msg["method"]
    if method == "notifications/initialized":
        initialized = True
        continue
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}}
    else:
        assert initialized
        name = msg["params"]["name"]
        if name == "stall":
            sys.stdout.write('{"jsonrpc":')
            sys.stdout.flush()
            time.sleep(60)
        if name == "rpc_error":
            print(json.dumps({"jsonrpc": "2.0", "id": msg["id"],
                              "error": {"code": -32602, "message": "参数错误"}}), flush=True)
            continue
        if name == "fail":
            result = {"isError": True, "content": [{"type": "text", "text": "原始错误\\n详情"}]}
        else:
            data = {"root": os.environ["CONCAT_MCP_ROOTS"], "args": msg["params"]["arguments"]}
            result = {"content": [{"type": "text", "text": json.dumps(data)}]}
    print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}), flush=True)
"""


@pytest.fixture
def fake_app(tmp_path):
    app = tmp_path / "Concat.app"
    binary = app / "Contents/MacOS/concat"
    binary.parent.mkdir(parents=True)
    binary.write_text(f"#!{sys.executable}\n" + SERVER, encoding="utf-8")
    binary.chmod(0o755)
    return app


def test_stdio_handshake_call_and_log(fake_app, tmp_path):
    log = tmp_path / "calls.jsonl"
    with ConcatMCP(fake_app, tmp_path, log) as mcp:
        assert mcp.call("echo", {"text": "字幕"}) == {
            "root": str(tmp_path.resolve()), "args": {"text": "字幕"},
        }
    sent = [row["message"] for line in log.read_text().splitlines()
            if (row := json.loads(line))["direction"] == "out"]
    assert [row["method"] for row in sent] == [
        "initialize", "notifications/initialized", "tools/call",
    ]


@pytest.mark.parametrize(("tool", "message"), [("fail", "原始错误"), ("rpc_error", "参数错误")])
def test_stdio_preserves_tool_error(fake_app, tmp_path, tool, message):
    with ConcatMCP(fake_app, tmp_path, tmp_path / "calls.jsonl") as mcp:
        with pytest.raises(BackendError) as exc:
            mcp.call(tool, {})
        assert str(exc.value) == f"concat_tool_error:{tool}:{message}"


def test_stdio_timeout_and_owned_process_cleanup(fake_app, tmp_path):
    binary = fake_app / "Contents/MacOS/concat"
    peer = subprocess.Popen([str(binary), "--mcp", "headless"], stdin=subprocess.PIPE)
    try:
        with ConcatMCP(fake_app, tmp_path, tmp_path / "calls.jsonl", close_timeout=0.2) as mcp:
            pid = mcp.pid
            started = time.monotonic()
            with pytest.raises(BackendError, match="concat_timeout:stall"):
                mcp.call("stall", {}, timeout=0.2)
            assert time.monotonic() - started < 3
        mcp.close()
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
        assert peer.poll() is None
    finally:
        peer.send_signal(signal.SIGKILL)
        peer.communicate(timeout=5)


def test_probe_reports_missing_app_separately(tmp_path, monkeypatch):
    from edit_backends.registry import get_backend

    monkeypatch.setenv("CONTENT_OS_CONCAT_APP", str(tmp_path / "missing.app"))
    probe = get_backend("concat").probe()
    assert probe == {"id": "concat", "installed": False, "runnable": False,
                     "version": None, "status": "unavailable", "reason": "concat_app_unavailable"}


def test_failed_save_keeps_original_mcp_reason_and_stops_export(tmp_path, monkeypatch):
    from edit_backends import concat_adapter

    monkeypatch.setenv("CONTENT_OS_CONCAT_APP", str(tmp_path / "Concat.app"))
    binary = tmp_path / "Concat.app/Contents/MacOS/concat"
    binary.parent.mkdir(parents=True)
    binary.touch(mode=0o755)
    source = tmp_path / "source.mp4"
    source.touch()
    suggestions = tmp_path / "suggestions.json"
    suggestions.write_text(json.dumps({"suggestions": []}))
    monkeypatch.setattr(concat_adapter, "probe_media", lambda _: {
        "streams": [{"codec_type": "video", "width": 1080, "height": 1920}],
    })
    seen = []

    class RefusingSave:
        def __init__(self, *args):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def call(self, tool, args, **kwargs):
            seen.append(tool)
            if tool == "project_create":
                return {"timeline": {"tracks": [{"id": "T1", "index": 0}]}}
            if tool == "media_import":
                return {"createdId": "m1", "media": [{"id": "m1", "duration": 20}]}
            if tool == "clip_add":
                return {"createdId": "c1"}
            if tool == "project_save":
                raise BackendError("concat_tool_error:project_save:原文")
            pytest.fail(f"unexpected call {tool}")

    monkeypatch.setattr(concat_adapter, "ConcatMCP", RefusingSave)
    output = tmp_path / "output"
    with pytest.raises(BackendError, match="^concat_tool_error:project_save:原文$"):
        concat_adapter.Backend().render(source=source, suggestions_path=suggestions, output_dir=output)
    assert seen == ["project_create", "media_import", "clip_add", "project_save"]
    receipt = json.loads((output / "render-result.json").read_text())
    assert (receipt["status"], receipt["reason"]) == ("failed", "concat_tool_error:project_save:原文")


def _make_fake_concat_mcp(source: Path, duration: float, recorded: dict):
    class FakeConcatMCP:
        def __init__(self, *args):
            self._clips = []
            self._captions = []
            self._next_id = 1
            self._width = 1080
            self._height = 1920
            self._fps = 30

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def _state(self):
            all_clips = [*self._clips, *self._captions]
            timeline_duration = max((c["end"] for c in self._clips), default=0.0)
            return {
                "project": {"width": self._width, "height": self._height, "fps": self._fps},
                "media": [{"id": "m1", "path": str(source.resolve()), "duration": duration}],
                "timeline": {
                    "duration": timeline_duration,
                    "tracks": [{"id": "T1", "index": 0}],
                    "clips": all_clips,
                },
            }

        def _new_id(self, prefix: str) -> str:
            cid = f"{prefix}{self._next_id}"
            self._next_id += 1
            return cid

        def call(self, tool, args, **kwargs):
            recorded.setdefault("calls", []).append((tool, args))
            if tool == "project_create":
                self._width = args["video"]["width"]
                self._height = args["video"]["height"]
                self._fps = args["video"]["rateNum"]
                return self._state()
            if tool == "media_import":
                return {"createdId": "m1", "media": [{"id": "m1", "path": args["file"], "duration": duration}]}
            if tool == "clip_add":
                clip = {
                    "id": self._new_id("c"),
                    "kind": "video",
                    "media": args["mediaId"],
                    "start": float(args["start"]),
                    "end": float(args["start"]) + duration,
                    "duration": duration,
                    "sourceStart": 0.0,
                    "speed": 1,
                }
                self._clips.append(clip)
                return self._state()
            if tool == "clips_split":
                at = float(args["time"])
                target_id = args["clipIds"][0]
                updated = []
                for clip in self._clips:
                    if clip["id"] == target_id:
                        left_dur = at - clip["start"]
                        right_dur = clip["end"] - at
                        updated.append({
                            **clip,
                            "end": at,
                            "duration": left_dur,
                        })
                        updated.append({
                            **clip,
                            "id": self._new_id("c"),
                            "start": at,
                            "duration": right_dur,
                            "sourceStart": clip["sourceStart"] + left_dur,
                        })
                    else:
                        updated.append(clip)
                self._clips = updated
                return self._state()
            if tool == "clips_remove":
                drop = set(args["clipIds"])
                kept = [clip for clip in self._clips if clip["id"] not in drop]
                cursor = 0.0
                for clip in kept:
                    clip["start"] = cursor
                    clip["end"] = cursor + clip["duration"]
                    cursor = clip["end"]
                self._clips = kept
                return self._state()
            if tool == "captions_add":
                recorded["captions"] = list(args["captions"])
                for cue in args["captions"]:
                    self._captions.append({
                        "id": self._new_id("t"),
                        "kind": "text",
                        "start": float(cue["start"]),
                        "end": float(cue["end"]),
                        "text": cue["text"],
                    })
                return self._state()
            if tool in {"project_save", "project_close"}:
                return {"ok": True}
            if tool == "timeline_read":
                return self._state()
            if tool == "export_start":
                recorded["export_output"] = Path(args["output"])
                return {"job": "j1"}
            if tool == "export_wait":
                recorded["export_output"].write_bytes(b"mp4-stub")
                return {"state": "done", "frame": int(round(self._state()["timeline"]["duration"] * self._fps))}
            pytest.fail(f"unexpected tool {tool}")

    return FakeConcatMCP


def _setup_fake_concat(tmp_path, monkeypatch, duration: float):
    from edit_backends import concat_adapter

    monkeypatch.setenv("CONTENT_OS_CONCAT_APP", str(tmp_path / "Concat.app"))
    binary = tmp_path / "Concat.app/Contents/MacOS/concat"
    binary.parent.mkdir(parents=True)
    binary.touch(mode=0o755)
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source-stub")
    monkeypatch.setattr(concat_adapter, "probe_media", lambda _: {
        "streams": [{"codec_type": "video", "width": 1080, "height": 1920}],
    })
    recorded = {}
    monkeypatch.setattr(concat_adapter, "ConcatMCP", _make_fake_concat_mcp(source, duration, recorded))
    return concat_adapter, source, recorded


def test_sliver_retained_segments_are_merged_into_cuts(tmp_path, monkeypatch):
    concat_adapter, source, _ = _setup_fake_concat(tmp_path, monkeypatch, duration=73.99)
    suggestions = tmp_path / "suggestions.json"
    suggestions.write_text(json.dumps({
        "precision": "word",
        "auto_cut_allowed": True,
        "suggestions": [
            {"type": "silence", "start": 0.10, "end": 1.00, "auto_cut_allowed": True},
            {"type": "silence", "start": 4.48, "end": 6.521333, "auto_cut_allowed": True},
            {"type": "repetition", "start": 6.59, "end": 9.15, "auto_cut_allowed": True, "precision": "word"},
            {"type": "repetition", "start": 15.87, "end": 16.47, "auto_cut_allowed": True, "precision": "word"},
            {"type": "repetition", "start": 16.67, "end": 17.50, "auto_cut_allowed": True, "precision": "word"},
            {"type": "silence", "start": 37.54, "end": 39.615583, "auto_cut_allowed": True},
            {"type": "repetition", "start": 39.64, "end": 41.12, "auto_cut_allowed": True, "precision": "word"},
        ],
    }), encoding="utf-8")

    output = tmp_path / "output"
    receipt = concat_adapter.Backend().render(source=source, suggestions_path=suggestions, output_dir=output)
    time_map = receipt["time_map"]

    assert all(seg["source_end"] - seg["source_start"] >= 0.2 - 1e-9 for seg in time_map), (
        f"sliver retained segment found: {time_map}"
    )
    assert [(round(s["source_start"], 4), round(s["source_end"], 4)) for s in time_map] == [
        (1.0, 4.4667),
        (9.1333, 15.8667),
        (16.4667, 16.6667),
        (17.5, 37.5333),
        (41.1333, 73.99),
    ]
    assert getattr(concat_adapter, "MIN_RETAINED_SECONDS", None) == 0.2


def test_captions_merge_adjacent_identical_and_drop_short(tmp_path, monkeypatch):
    from review_output_video import read_srt_cues

    concat_adapter, source, recorded = _setup_fake_concat(tmp_path, monkeypatch, duration=73.99)
    suggestions = tmp_path / "suggestions.json"
    suggestions.write_text(json.dumps({
        "precision": "word",
        "auto_cut_allowed": True,
        "suggestions": [
            {"type": "silence", "start": 4.48, "end": 6.521333, "auto_cut_allowed": True},
            {"type": "repetition", "start": 6.59, "end": 9.15, "auto_cut_allowed": True, "precision": "word"},
            {"type": "repetition", "start": 15.87, "end": 16.47, "auto_cut_allowed": True, "precision": "word"},
            {"type": "silence", "start": 37.54, "end": 39.615583, "auto_cut_allowed": True},
            {"type": "repetition", "start": 39.64, "end": 41.12, "auto_cut_allowed": True, "precision": "word"},
            {"type": "repetition", "start": 44.0, "end": 45.32, "auto_cut_allowed": True, "precision": "word"},
        ],
    }), encoding="utf-8")
    subtitles = tmp_path / "subtitles.srt"
    subtitles.write_text(
        "1\n00:00:00,000 --> 00:00:04,440\n我们用一个生活中的例子，讲清楚怎样计算一段旅程的平均速度。\n\n"
        "2\n00:00:06,440 --> 00:00:09,185\n平均速度等于总路程除以总时间。\n\n"
        "3\n00:00:09,185 --> 00:00:11,930\n平均速度等于总路程除以总时间。\n\n"
        "4\n00:00:11,930 --> 00:00:21,623\n假设你骑车去公园，去的时候道路平坦，骑得比较快，回来的时候遇到上坡，骑得比较慢，两段路的距离完全相同。\n\n"
        "5\n00:00:39,520 --> 00:00:41,300\n计算总时间的时候，\n\n"
        "6\n00:00:41,300 --> 00:00:50,236\n计算总时间的时候，要先用去程距离除以去程速度，再用回程距离除以回程速度，把两个时间相加。\n",
        encoding="utf-8",
    )

    output = tmp_path / "output"
    concat_adapter.Backend().render(
        source=source, suggestions_path=suggestions, subtitles=subtitles, output_dir=output,
    )
    sent = recorded["captions"]
    written = read_srt_cues(output / "subtitles.srt")

    assert all(cue["end"] - cue["start"] >= 0.3 - 1e-9 for cue in sent), f"short caption found: {sent}"
    assert all(a["text"] != b["text"] for a, b in zip(sent, sent[1:])), f"consecutive duplicate captions: {sent}"
    assert [cue["text"] for cue in sent] == [
        "我们用一个生活中的例子，讲清楚怎样计算一段旅程的平均速度。",
        "平均速度等于总路程除以总时间。",
        "假设你骑车去公园，去的时候道路平坦，骑得比较快，回来的时候遇到上坡，骑得比较慢，两段路的距离完全相同。",
        "计算总时间的时候，要先用去程距离除以去程速度，再用回程距离除以回程速度，把两个时间相加。",
    ]
    assert len(written) == 4
    assert all(end - start >= 0.3 - 1e-9 for start, end, _ in written)
    assert getattr(concat_adapter, "MIN_CAPTION_SECONDS", None) == 0.3


def test_caption_merge_gap_and_duration_boundaries(tmp_path, monkeypatch):
    concat_adapter, source, recorded = _setup_fake_concat(tmp_path, monkeypatch, duration=20.0)
    suggestions = tmp_path / "suggestions.json"
    suggestions.write_text(json.dumps({"suggestions": []}), encoding="utf-8")
    subtitles = tmp_path / "subtitles.srt"
    subtitles.write_text(
        "1\n00:00:01,000 --> 00:00:01,150\n一帧间隔应合并。\n\n"
        "2\n00:00:01,183 --> 00:00:01,400\n一帧间隔应合并。\n\n"
        "3\n00:00:02,000 --> 00:00:02,120\n合完仍短要丢掉。\n\n"
        "4\n00:00:02,120 --> 00:00:02,250\n合完仍短要丢掉。\n\n"
        "5\n00:00:03,000 --> 00:00:03,500\n两帧间隔不合并。\n\n"
        "6\n00:00:03,567 --> 00:00:04,000\n两帧间隔不合并。\n\n"
        "7\n00:00:05,100 --> 00:00:05,400\n刚好零点三秒留。\n\n"
        "8\n00:00:06,000 --> 00:00:06,290\n零点二九秒丢掉。\n",
        encoding="utf-8",
    )

    output = tmp_path / "output"
    concat_adapter.Backend().render(
        source=source, suggestions_path=suggestions, subtitles=subtitles, output_dir=output,
    )
    sent = [(round(c["start"], 3), round(c["end"], 3), c["text"]) for c in recorded["captions"]]
    assert sent == [
        (1.0, 1.4, "一帧间隔应合并。"),
        (3.0, 3.5, "两帧间隔不合并。"),
        (3.567, 4.0, "两帧间隔不合并。"),
        (5.1, 5.4, "刚好零点三秒留。"),
    ]
