"""Regression tests for rotated portrait sources in Concat backend."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from tests.test_concat_backend import _setup_fake_concat


@pytest.mark.parametrize("stream,expected", [
    ({"codec_type": "video", "width": 1920, "height": 1080, "side_data_list": [{"rotation": 90}]}, (1080, 1920)),
    ({"codec_type": "video", "width": 1920, "height": 1080, "side_data_list": [{"rotation": -90}]}, (1080, 1920)),
    ({"codec_type": "video", "width": 1920, "height": 1080, "tags": {"rotate": "270"}}, (1080, 1920)),
    ({"codec_type": "video", "width": 1920, "height": 1080, "side_data_list": [{"rotation": 180}]}, (1920, 1080)),
    ({"codec_type": "video", "width": 1920, "height": 1080}, (1920, 1080)),
])
def test_rotated_source_uses_display_dimensions(tmp_path, monkeypatch, stream, expected):
    concat_adapter, source, _ = _setup_fake_concat(tmp_path, monkeypatch, duration=10.0)
    monkeypatch.setattr(concat_adapter, "probe_media", lambda _: {"streams": [stream]})

    calls = []
    fake_cls = concat_adapter.ConcatMCP

    class RecordingConcatMCP(fake_cls):
        def call(self, tool, args, *, timeout=None):
            calls.append((tool, dict(args)))
            return super().call(tool, args, timeout=timeout)

    monkeypatch.setattr(concat_adapter, "ConcatMCP", RecordingConcatMCP)
    suggestions = tmp_path / "suggestions.json"
    suggestions.write_text(json.dumps({"suggestions": []}), encoding="utf-8")

    output = tmp_path / "output"
    receipt = concat_adapter.Backend().render(source=source, suggestions_path=suggestions, output_dir=output)
    manifest = json.loads(Path(receipt["manifest"]).read_text(encoding="utf-8"))

    created = next(args["video"] for tool, args in calls if tool == "project_create")
    exported = next((args["width"], args["height"]) for tool, args in calls if tool == "export_start")
    assert (created["width"], created["height"]) == expected
    assert exported == expected
    assert (manifest["width"], manifest["height"]) == expected
