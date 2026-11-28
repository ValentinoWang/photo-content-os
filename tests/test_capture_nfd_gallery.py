"""Unit tests for pure functions and cleanup guarantees in scripts/capture_nfd_gallery.py."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest import mock

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import capture_nfd_gallery as cap  # noqa: E402


def _make_solid_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    image = Image.new("RGBA", (width, height), (*rgb, 255))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_build_manifest_record_stable_id_uuid_and_heights() -> None:
    spec = cap.PAGE_SPECS_BY_ID["studio-home"]
    record = cap.build_manifest_record(
        spec,
        relative_file="screenshots/studio-home.png",
        width=1440,
        height=1200,
        scroll_height=1200,
        sha256_hex="a" * 64,
        captured_at="2026-11-28T05:00:00Z",
    )
    assert record["id"] == "studio-home"
    assert record["uuid"] == cap.stable_uuid("studio-home")
    assert record["uuid"] == cap.stable_uuid("studio-home")
    assert record["title"] == "工作台"
    assert record["role"] == "studio"
    assert record["galleryRole"] == "studio"
    assert record["route"] == "/#view=home"
    assert record["group"] == "nav-home"
    assert record["isPrimaryEntry"] is True
    assert record["viewport"] == {"width": 1440, "height": 900}
    assert record["scrollHeight"] == 1200
    assert record["cssHeight"] == 1200
    assert record["parts"] == [
        {
            "file": "screenshots/studio-home.png",
            "width": 1440,
            "height": 1200,
            "sha256": "a" * 64,
        }
    ]


def test_build_manifest_record_rejects_height_mismatch() -> None:
    spec = cap.PAGE_SPECS_BY_ID["studio-home"]
    with pytest.raises(ValueError, match="stitched height"):
        cap.build_manifest_record(
            spec,
            relative_file="screenshots/studio-home.png",
            width=1440,
            height=900,
            scroll_height=1150,
            sha256_hex="b" * 64,
            captured_at="2026-11-28T05:00:00Z",
        )


def test_build_groups_orders_by_nav_with_home_first_and_primary_entry_first() -> None:
    shuffled = [
        {"id": "studio-settings"},
        {"id": "studio-project-detail"},
        {"id": "studio-music"},
        {"id": "studio-home"},
        {"id": "studio-projects"},
        {"id": "studio-inbox"},
        {"id": "studio-library"},
    ]
    groups = cap.build_groups(shuffled)
    assert list(groups.keys()) == ["studio"]
    studio_groups = groups["studio"]
    assert [g["id"] for g in studio_groups] == [
        "nav-home",
        "nav-inbox",
        "nav-projects",
        "nav-library",
        "nav-music",
        "nav-settings",
    ]
    assert studio_groups[0]["ids"] == ["studio-home"]
    assert studio_groups[2]["ids"] == ["studio-projects", "studio-project-detail"]


def test_build_manifest_structure_matches_nfd_package_contract() -> None:
    records = [
        cap.build_manifest_record(
            spec,
            relative_file=f"screenshots/{spec.id}.png",
            width=1440,
            height=900,
            scroll_height=900,
            sha256_hex="c" * 64,
            captured_at="2026-11-28T05:00:00Z",
        )
        for spec in cap.PAGE_SPECS
    ]
    manifest = cap.build_manifest(
        records,
        generated_at="2026-11-28T05:01:00Z",
        source_commit="1" * 40,
    )
    assert manifest["schemaVersion"] == 3
    assert manifest["package"] == {
        "version": 1,
        "generatedAt": "2026-11-28T05:01:00Z",
        "sourceCommit": "1" * 40,
    }
    assert manifest["roles"] == [
        {"id": "studio", "title": "制作台", "color": "#2F6FED", "viewport": "desktop"}
    ]
    assert manifest["unreadable"] == []
    assert set(manifest["pages"].keys()) == {spec.id for spec in cap.PAGE_SPECS}
    assert manifest["pages"]["studio-project-detail"] == {
        "kind": "子页面",
        "path": ["项目", "项目详情"],
    }


def test_build_steps_payload_assigns_unique_order_and_verified_entries() -> None:
    transitions = [
        {
            "from": "studio-home",
            "to": "studio-inbox",
            "control": "整理台",
            "kind": "step",
            "oneWay": False,
            "ok": True,
            "verifiedAt": "2026-11-28T05:00:10Z",
        },
        {
            "from": "studio-project-detail",
            "to": "studio-projects",
            "control": "项目",
            "kind": "back",
            "oneWay": False,
            "ok": True,
            "verifiedAt": "2026-11-28T05:00:20Z",
        },
    ]
    payload = cap.build_steps_payload(transitions, generated_at="2026-11-28T05:01:00Z")
    assert payload["version"] == 1
    assert payload["generatedAt"] == "2026-11-28T05:01:00Z"
    assert [step["order"] for step in payload["steps"]] == [0, 1]
    assert payload["steps"][0] == {
        "from": "studio-home",
        "to": "studio-inbox",
        "control": "整理台",
        "kind": "step",
        "oneWay": False,
        "order": 0,
    }
    assert payload["steps"][1]["kind"] == "back"
    assert all("evidence" not in step for step in payload["steps"])
    assert payload["verified"] == [
        {
            "from": "studio-home",
            "to": "studio-inbox",
            "control": "整理台",
            "kind": "step",
            "ok": True,
            "verifiedAt": "2026-11-28T05:00:10Z",
        },
        {
            "from": "studio-project-detail",
            "to": "studio-projects",
            "control": "项目",
            "kind": "back",
            "ok": True,
            "verifiedAt": "2026-11-28T05:00:20Z",
        },
    ]


def test_compute_scroll_segments_and_stitch_vertical_tiles_seamless() -> None:
    segments = cap.compute_scroll_segments(total_height=1350, viewport_height=900)
    assert segments == [{"offset": 0, "height": 900}, {"offset": 900, "height": 450}]

    # Simulate a 1350px page captured in two 900px viewports where second scroll clamps at y=450.
    tile0 = _make_solid_png(16, 900, (10, 20, 30))
    tile1_img = Image.new("RGBA", (16, 900), (10, 20, 30, 255))
    bottom_band = Image.new("RGBA", (16, 450), (200, 100, 50, 255))
    tile1_img.paste(bottom_band, (0, 450))
    buf = io.BytesIO()
    tile1_img.save(buf, format="PNG")
    tile1 = buf.getvalue()

    stitched = cap.stitch_vertical_tiles(
        [
            {"png_bytes": tile0, "source_y": 0, "height": 900, "dest_y": 0},
            {"png_bytes": tile1, "source_y": 450, "height": 450, "dest_y": 900},
        ],
        width=16,
        total_height=1350,
    )
    with Image.open(io.BytesIO(stitched)) as out:
        assert out.size == (16, 1350)
        assert out.getpixel((0, 0))[:3] == (10, 20, 30)
        assert out.getpixel((0, 899))[:3] == (10, 20, 30)
        assert out.getpixel((0, 900))[:3] == (200, 100, 50)
        assert out.getpixel((0, 1349))[:3] == (200, 100, 50)


def test_stitch_vertical_tiles_rejects_gap_or_overlap() -> None:
    tile = _make_solid_png(16, 100, (1, 2, 3))
    with pytest.raises(ValueError, match="gap or overlap"):
        cap.stitch_vertical_tiles(
            [
                {"png_bytes": tile, "source_y": 0, "height": 100, "dest_y": 0},
                {"png_bytes": tile, "source_y": 0, "height": 100, "dest_y": 90},
            ],
            width=16,
            total_height=190,
        )


def test_parse_studio_ready_url() -> None:
    assert (
        cap.parse_studio_ready_url("Photo Content OS Studio: http://127.0.0.1:54321/\n")
        == "http://127.0.0.1:54321"
    )
    assert cap.parse_studio_ready_url("Local state: /tmp/state\n") is None


def test_parse_demo_project_output_ignores_child_script_logs() -> None:
    stdout = (
        "项目结构检查完成：/tmp/demo\n"
        "新建文件：7 个\n"
        '{\n  "status": "passed",\n  "project_dir": "/tmp/demo/p1",\n  "media_count": 3\n}\n'
    )
    parsed = cap.parse_demo_project_output(stdout)
    assert parsed == {"status": "passed", "project_dir": "/tmp/demo/p1", "media_count": 3}


def test_capture_gallery_cleans_temp_dir_and_stops_server_on_failure(tmp_path: Path) -> None:
    created_tmp_dirs: list[Path] = []
    real_mkdtemp = cap.tempfile.mkdtemp

    def track_mkdtemp(*args: object, **kwargs: object) -> str:
        path = Path(real_mkdtemp(*args, **kwargs))
        created_tmp_dirs.append(path)
        return str(path)

    fake_proc = mock.MagicMock()
    out_dir = tmp_path / "gallery"

    with (
        mock.patch.object(cap.tempfile, "mkdtemp", side_effect=track_mkdtemp),
        mock.patch.object(cap, "prepare_demo_environment", return_value=(tmp_path, tmp_path, {"id": "demo"})),
        mock.patch.object(cap, "start_studio_server", return_value=(fake_proc, "http://127.0.0.1:49999")),
        mock.patch.object(cap, "run_browser_capture", side_effect=RuntimeError("boom")),
        mock.patch.object(cap, "stop_process") as mock_stop,
    ):
        with pytest.raises(RuntimeError, match="boom"):
            cap.capture_gallery(out_dir=out_dir, port=0)

    mock_stop.assert_called_once_with(fake_proc)
    assert len(created_tmp_dirs) == 1
    assert not created_tmp_dirs[0].exists()


def test_capture_gallery_bad_out_parent_cleans_up_without_starting_server(tmp_path: Path) -> None:
    created_tmp_dirs: list[Path] = []
    real_mkdtemp = cap.tempfile.mkdtemp

    def track_mkdtemp(*args: object, **kwargs: object) -> str:
        path = Path(real_mkdtemp(*args, **kwargs))
        created_tmp_dirs.append(path)
        return str(path)

    bad_out = tmp_path / "missing-parent" / "gallery"
    with (
        mock.patch.object(cap.tempfile, "mkdtemp", side_effect=track_mkdtemp),
        mock.patch.object(cap, "start_studio_server") as mock_start,
    ):
        with pytest.raises(FileNotFoundError, match="parent directory"):
            cap.capture_gallery(out_dir=bad_out, port=0)

    mock_start.assert_not_called()
    assert len(created_tmp_dirs) == 1
    assert not created_tmp_dirs[0].exists()


def test_write_package_from_raw_outputs_valid_json_and_png(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    tile_path = raw_dir / "home-0.png"
    tile_path.write_bytes(_make_solid_png(1440, 900, (240, 244, 248)))
    out_dir = tmp_path / "pkg"
    raw_data = {
        "captures": [
            {
                "id": "studio-home",
                "scroll_height": 900,
                "actual_route": "/#view=home",
                "captured_at": "2026-11-28T05:00:00Z",
                "tiles": [{"file": str(tile_path), "source_y": 0, "height": 900, "dest_y": 0}],
            }
        ],
        "transitions": [],
    }
    summary = cap.write_package_from_raw(raw_data, out_dir=out_dir, source_commit="2" * 40)
    assert summary["pages"][0]["stitchedHeight"] == 900
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    steps = json.loads((out_dir / "steps.json").read_text(encoding="utf-8"))
    assert manifest["records"][0]["id"] == "studio-home"
    assert (out_dir / manifest["records"][0]["file"]).is_file()
    assert steps["version"] == 1
