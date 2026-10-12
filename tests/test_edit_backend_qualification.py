"""Shared real qualification: EI_TEST_BACKEND selects exactly one adapter.

EI_TEST_FIXTURE is mandatory. EI_TEST_EVIDENCE optionally retains small evidence,
never intermediate videos. Refine adapters require EI_TEST_REFINE_DRIVER, a module
with delete_segment(backend, project_dir, index) and undo(backend, project_dir).
Those hooks must operate the real editor; the common assertions stay here.
"""
from __future__ import annotations

from functools import lru_cache
from importlib import import_module
from array import array
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image, ImageChops, ImageStat
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from edit_backends.interface import BackendError
from edit_backends.registry import get_backend
from _support import load_script

review = load_script("review_output_video", "ei_output_review", register=True)
EXPECTED_MAP = [
    {"source_start": 0, "source_end": 4, "output_start": 0},
    {"source_start": 6, "source_end": 8, "output_start": 4},
    {"source_start": 10, "source_end": 12, "output_start": 6},
    {"source_start": 14, "source_end": 20, "output_start": 8},
]


def run(*args):
    return subprocess.run(args, capture_output=True, check=True, timeout=120).stdout


def processes():
    """Observe executable identities, not shell strings that mention melt."""
    rows = run("ps", "-axo", "pid=,ppid=,comm=").decode().splitlines()
    table = {int(pid): (int(parent), command) for row in rows
             for pid, parent, command in [row.strip().split(None, 2)]}
    descendants = {os.getpid()}
    while True:
        expanded = descendants | {pid for pid, (parent, _) in table.items() if parent in descendants}
        if expanded == descendants:
            break
        descendants = expanded
    return {pid: command for pid, (_, command) in table.items()
            if (pid in descendants and pid != os.getpid() and Path(command).name != "ps")
            or Path(command).name.lower() == "melt"}


@lru_cache(maxsize=8)
def frame(path: str, number: int, width: int = 640, height: int = 360, rgba: bool = False):
    channels = 4 if rgba else 3
    raw = run("ffmpeg", "-v", "error", "-i", path, "-vf", f"select=eq(n\\,{number})",
              "-frames:v", "1", "-pix_fmt", "rgba" if rgba else "rgb24", "-f", "rawvideo", "-")
    assert len(raw) == height * width * channels
    return Image.frombytes("RGBA" if rgba else "RGB", (width, height), raw)


def pixel_error(first, second, mask=None):
    return sum(ImageStat.Stat(ImageChops.difference(first, second), mask).mean) / 3


def character_errors(expected, actual):
    """Levenshtein distance for OCR's character error rate, without substitutions."""
    previous = list(range(len(actual) + 1))
    for i, first in enumerate(expected, 1):
        current = [i]
        for j, second in enumerate(actual, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (first != second)))
        previous = current
    return previous[-1]


@pytest.fixture(scope="module")
def qualification(tmp_path_factory):
    backend_id = os.environ.get("EI_TEST_BACKEND")
    if not backend_id:
        pytest.skip("real adapter qualification requires EI_TEST_BACKEND and EI_TEST_FIXTURE")
    fixture = Path(os.environ["EI_TEST_FIXTURE"]).expanduser().resolve()
    hashes = json.loads((fixture / "fixture-hashes.json").read_text())
    for name, digest in hashes.items():
        assert review.file_sha256(fixture / name) == digest, f"fixture hash changed: {name}"
    assert shutil.which("ffmpeg") and shutil.which("ffprobe")
    backend = get_backend(backend_id)
    root = tmp_path_factory.mktemp(f"editor-{backend_id}")
    evidence = Path(os.environ["EI_TEST_EVIDENCE"]).resolve() if os.environ.get("EI_TEST_EVIDENCE") else root / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    before = processes()
    kwargs = {"source": fixture / "source.mp4", "suggestions_path": fixture / "edit_suggestions.json",
              "subtitles": fixture / "source.srt",
              "animations": [{**item, "path": str(fixture / Path(item["path"]).name)}
                             for item in json.loads((fixture / "animations.json").read_text())],
              "project_id": "ei-qualification", "project_revision": 18, "timeout_seconds": 120}
    try:
        probe = backend.probe()
        assert probe["id"] == backend_id and probe["runnable"] is True, probe
        result = backend.render(**kwargs, output_dir=root / "render")
        receipt = json.loads((root / "render/render-result.json").read_text())
        assert result == receipt
        assert result["editor_backend"] == backend_id
        manifest = json.loads(Path(result["manifest"]).read_text())
        (evidence / "qualification.json").write_text(json.dumps({
            "backend": backend.describe(), "probe": probe, "fixture_hashes": hashes,
            "result": result, "time_map": manifest["time_map"]}, ensure_ascii=False, indent=2))
        yield {"backend": backend, "id": backend_id, "root": root, "evidence": evidence,
               "fixture": fixture, "result": result, "manifest": manifest, "kwargs": kwargs, "before": before}
    finally:
        closed = backend.close()
        after = processes()
        remaining = {pid: command for pid, command in after.items() if pid not in before}
        (evidence / "process-cleanup.json").write_text(json.dumps({
            "before": before, "after": after, "new_remaining": remaining, "close": closed}, indent=2))
        frame.cache_clear()
        try:
            assert closed["remaining_pids"] == [], closed
            assert not remaining, remaining
            for pid in closed["started_pids"]:
                with pytest.raises(ProcessLookupError):
                    os.kill(pid, 0)
            for name, digest in hashes.items():
                assert review.file_sha256(fixture / name) == digest, f"fixture modified: {name}"
        finally:
            shutil.rmtree(root)


def test_candidate_duration_frames_audio_and_manifest(qualification):
    q = qualification
    result = q["result"]
    assert result["status"] == "candidate", result
    assert result["duration"] == 14 and result["frames"] == 420
    assert result["removed_seconds"] == 6
    assert q["manifest"]["contract"] == "video_pipeline_manifest.v1"
    assert q["manifest"]["time_map"] == EXPECTED_MAP
    assert Path(result["output"]).name == "candidate.mp4"
    checks = review.check_pipeline_manifest(Path(result["manifest"]), expected_output=Path(result["output"]))
    assert checks["status"] == "passed", checks
    pcm = run("ffmpeg", "-v", "error", "-i", result["output"], "-vn", "-f", "f32le", "-")
    samples = array("f", pcm)
    assert math.sqrt(sum(v * v for v in samples) / len(samples)) > 0.02
    source_cues = review.read_srt_cues(q["fixture"] / "source.srt")
    output_cues = review.read_srt_cues(Path(q["manifest"]["subtitles"]))
    assert output_cues == [(0, 4, source_cues[0][2]), (4, 6, source_cues[1][2]),
                           (6, 8, source_cues[3][2]), (8, 14, source_cues[4][2])]


@pytest.mark.parametrize("segment", EXPECTED_MAP)
def test_source_frames_at_each_retained_interval(qualification, segment):
    q = qualification
    for offset in (0, (segment["source_end"] - segment["source_start"]) / 2,
                   segment["source_end"] - segment["source_start"] - 1 / 30):
        src = round((segment["source_start"] + offset) * 30)
        dst = round((segment["output_start"] + offset) * 30)
        original = frame(str(q["fixture"] / "source.mp4"), src)
        candidate = frame(q["result"]["output"], dst)
        # Exclude overlay at top-left and caption at bottom; compare source pixels.
        difference = pixel_error(original.crop((0, 100, 640, 270)), candidate.crop((0, 100, 640, 270)))
        assert difference < 4, (src, dst, difference)
        # Fixture carries its source clock in the top-left pixels. Comparing the
        # adjacent frame clocks prevents broad color bars hiding a one-frame shift.
        clock = candidate.crop((0, 0, 110, 20))
        correct = pixel_error(clock, original.crop((0, 0, 110, 20)))
        alternatives = [pixel_error(clock, frame(str(q["fixture"] / "source.mp4"), n).crop((0, 0, 110, 20)))
                        for n in (src - 1, src + 1) if 0 <= n < 600]
        assert correct < min(alternatives), (src, dst, correct, alternatives)


def test_alpha_overlay_preserves_background_and_contains_animation(qualification):
    q = qualification
    metrics = []
    for seconds in (10, 11.5, 12.9):
        source_number, output_number = round((seconds + 6) * 30), round(seconds * 30)
        original = frame(str(q["fixture"] / "source.mp4"), source_number)
        candidate = frame(q["result"]["output"], output_number)
        overlay = frame(str(q["fixture"] / "overlay.mov"), round((seconds - 10) * 30), 160, 90, True)
        transparent = overlay.getchannel("A").point(lambda v: 255 if v < 5 else 0)
        opaque = overlay.getchannel("A").point(lambda v: 255 if v > 250 else 0)
        assert transparent.histogram()[255] > 100 and opaque.histogram()[255] > 100
        original_inside, candidate_inside = original.crop((0, 0, 160, 90)), candidate.crop((0, 0, 160, 90))
        alpha_error = pixel_error(candidate_inside, original_inside, transparent)
        outside_error = pixel_error(candidate.crop((0, 100, 640, 270)), original.crop((0, 100, 640, 270)))
        painted_error = pixel_error(candidate_inside, overlay.convert("RGB"), opaque)
        assert alpha_error < 5 and outside_error < 4 and painted_error < 15, (alpha_error, outside_error, painted_error)
        assert pixel_error(candidate_inside, original_inside, opaque) > 20, "animation absent"
        metrics.append({"seconds": seconds, "alpha_error": float(alpha_error),
                        "outside_error": float(outside_error), "painted_error": float(painted_error)})
        candidate.save(q["evidence"] / f"overlay-{seconds}.png")
    (q["evidence"] / "alpha-pixels.json").write_text(json.dumps(metrics, indent=2))


def test_chinese_captions_are_burned_in_and_recognizable(qualification):
    q = qualification
    assert q["manifest"]["subtitle_burned_in"] is True
    assert sys.platform == "darwin" and shutil.which("swift"), "Chinese OCR requires local Apple Vision and swift"
    # Verbatim SRT is checked above. OCR measures readability with <=10% character
    # error: local Vision reads the outlined 保 as 像 even in an inspected valid frame.
    # No custom OCR words or character substitutions are used.
    samples = [(1, "这是合成彩条"), (5, "这一段保留"),
               (7, "接着讲解"), (11, "保留这一遍随后叠动画")]
    recognized = []
    for seconds, expected in samples:
        image = q["evidence"] / f"caption-{seconds}.png"
        pixels = frame(q["result"]["output"], seconds * 30)
        pixels.crop((0, 280, 640, 360)).resize((1280, 160)).save(image)
        lines = json.loads(run("swift", str(Path(__file__).with_name("editor_backend_ocr.swift")), str(image)))
        bodies = ["".join(c for c in line.partition("：")[-1] if "\u4e00" <= c <= "\u9fff") for line in lines]
        errors = min((character_errors(expected, body) for body in bodies), default=len(expected))
        recognized.append({"seconds": seconds, "expected": expected, "recognized": lines,
                           "character_errors": errors, "max_error_rate": 0.1})
        assert errors / len(expected) <= 0.1, recognized[-1]
    (q["evidence"] / "chinese-ocr.json").write_text(json.dumps(recognized, ensure_ascii=False, indent=2))

    # Negative proof: colorful source pixels without burned-in subtitles fail OCR.
    original = frame(str(q["fixture"] / "source.mp4"), 30)
    negative = q["evidence"] / "caption-negative-source.png"
    original.crop((0, 280, 640, 360)).resize((1280, 160)).save(negative)
    lines = json.loads(run("swift", str(Path(__file__).with_name("editor_backend_ocr.swift")), str(negative)))
    assert not any(expected in "".join(lines) for _, expected in samples)


def test_bad_input_writes_failure_receipt_without_backend_change(qualification):
    q = qualification
    bad = q["root"] / "bad-suggestions.json"
    bad.write_text('{"suggestions":[{"type":"silence","start":0,"end":999,"auto_cut_allowed":true}]}')
    output = q["root"] / "bad-render"
    try:
        result = q["backend"].render(**{**q["kwargs"], "suggestions_path": bad}, output_dir=output)
        assert result["status"] == "failed"
    except (BackendError, ValueError):
        pass
    receipt = json.loads((output / "render-result.json").read_text())
    assert receipt["status"] == "failed" and receipt["editor_backend"] == q["id"]
    assert receipt.get("reason")
    assert not (output / "candidate.mp4").exists()
    (q["evidence"] / "bad-input-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2))


def test_render_timeout_writes_failure_and_reaps_process(qualification):
    q = qualification
    output = q["root"] / "timeout-render"
    try:
        result = q["backend"].render(**{**q["kwargs"], "timeout_seconds": 0.001}, output_dir=output)
        assert result["status"] == "failed"
    except (BackendError, ValueError):
        pass
    receipt = json.loads((output / "render-result.json").read_text())
    assert receipt["status"] == "failed" and receipt["editor_backend"] == q["id"]
    assert receipt.get("reason")
    assert not {pid: name for pid, name in processes().items() if pid not in q["before"]}
    (q["evidence"] / "timeout-receipt.json").write_text(json.dumps(receipt, indent=2))


def test_refine_delete_undo_read_back_and_export_or_explicitly_unsupported(qualification):
    q = qualification
    backend, project = q["backend"], q["root"] / "render"
    capabilities = backend.describe()["capabilities"]
    if not capabilities["web_refine"]:
        assert capabilities["undo"] is False
        if capabilities["read_back"]:
            assert backend.describe()['id']=='otio_kdenlive'
            assert backend.read_back(project_dir=project)['time_map']==EXPECTED_MAP
            return
        for method in (backend.open_for_refine, backend.read_back):
            with pytest.raises(BackendError, match="unsupported"):
                method(project_dir=project)
        return
    assert capabilities["undo"] is True and capabilities["read_back"] is True
    driver = import_module(os.environ["EI_TEST_REFINE_DRIVER"])
    backend.open_for_refine(project_dir=project)
    driver.delete_segment(backend, project, 0)
    deleted = backend.read_back(project_dir=project)
    expected_deleted = [{**r, "output_start": r["output_start"] - 4} for r in EXPECTED_MAP[1:]]
    assert deleted["time_map"] == expected_deleted
    result = backend.render(**deleted["render_kwargs"], output_dir=q["root"] / "deleted-export")
    assert result["status"] == "candidate" and result["frames"] == 300 and result["duration"] == 10
    assert json.loads(Path(result["manifest"]).read_text())["time_map"] == expected_deleted
    assert review.check_pipeline_manifest(Path(result["manifest"]))["status"] == "passed"
    driver.undo(backend, project)
    restored = backend.read_back(project_dir=project)
    assert restored["time_map"] == EXPECTED_MAP
    result = backend.render(**restored["render_kwargs"], output_dir=q["root"] / "restored-export")
    assert result["status"] == "candidate" and result["frames"] == 420 and result["duration"] == 14
    assert json.loads(Path(result["manifest"]).read_text())["time_map"] == EXPECTED_MAP
    assert review.check_pipeline_manifest(Path(result["manifest"]))["status"] == "passed"


def test_close_leaves_no_owned_editor_processes(qualification):
    q = qualification
    result = q["backend"].close()
    assert result == q["backend"].close()
    assert result["remaining_pids"] == []
    assert not {pid: name for pid, name in processes().items() if pid not in q["before"]}
