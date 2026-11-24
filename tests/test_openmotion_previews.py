import hashlib
import re
import subprocess

import pytest

from scripts.direct_video import recipe_library


def test_openmotion_cards_have_posters_and_clips_in_index():
    entries = recipe_library.load_index()
    imported = [entry for entry in entries if entry["path"].startswith("openmotion/")]
    assert len(imported) == 51
    for entry in imported:
        recipe_id = entry["id"]
        assert entry["poster"] == f"media/posters/{recipe_id}.render.jpg"
        assert entry["poster_source"] == "render"
        assert (recipe_library.ROOT / entry["poster"]).is_file()
        assert entry["clip"] == f"{recipe_id}.mp4"


def test_openmotion_clips_manifest_entries_have_sha256_and_render_source():
    manifest = recipe_library.load_openmotion_manifest()["clips"]
    clips = recipe_library.load_clips()["clips"]
    for recipe_id in manifest:
        assert recipe_id in clips, f"missing clip entry for {recipe_id}"
        item = clips[recipe_id]
        assert item["file"] == f"{recipe_id}.mp4"
        assert item["source"] == "render"
        assert isinstance(item["bytes"], int) and item["bytes"] > 0
        assert re.fullmatch(r"[0-9a-f]{64}", item["sha256"])


def test_fetch_clips_rerenders_local_entries_without_downloading(monkeypatch, tmp_path):
    payload = b"deterministic-preview-mp4"
    digest = hashlib.sha256(payload).hexdigest()
    recipe_id = "om-demo-clip-1"
    monkeypatch.setattr(recipe_library, "CLIP_DIR", tmp_path)
    monkeypatch.setattr(recipe_library, "load_clips", lambda: {
        "release": "Vincentwei1021/video-shotcraft@gallery-media",
        "clips": {
            recipe_id: {
                "file": f"{recipe_id}.mp4",
                "bytes": len(payload),
                "sha256": digest,
                "source": "render",
            },
        },
    })

    def forbid_download(*args, **kwargs):
        raise AssertionError(f"subprocess download should not run for local render clips: {args}")

    rendered = []

    def fake_render(rid, *, clip_dest=None, poster_dest=None):
        rendered.append(rid)
        assert clip_dest is not None
        clip_dest.write_bytes(payload)
        return {"id": rid, "file": clip_dest.name, "bytes": len(payload), "sha256": digest, "source": "render"}

    monkeypatch.setattr(subprocess, "run", forbid_download)
    monkeypatch.setattr(recipe_library, "render_openmotion_preview", fake_render)

    recipe_library.fetch_clips()
    assert rendered == [recipe_id]
    assert (tmp_path / f"{recipe_id}.mp4").read_bytes() == payload


def test_fetch_clips_raises_naming_recipe_on_local_render_sha256_mismatch(monkeypatch, tmp_path):
    recipe_id = "om-bad-hash-clip-2"
    monkeypatch.setattr(recipe_library, "CLIP_DIR", tmp_path)
    monkeypatch.setattr(recipe_library, "load_clips", lambda: {
        "release": "Vincentwei1021/video-shotcraft@gallery-media",
        "clips": {
            recipe_id: {
                "file": f"{recipe_id}.mp4",
                "bytes": 10,
                "sha256": "0" * 64,
                "source": "render",
            },
        },
    })
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("unexpected download")))

    def wrong_render(rid, *, clip_dest=None, poster_dest=None):
        clip_dest.write_bytes(b"different-bytes")
        return {"id": rid}

    monkeypatch.setattr(recipe_library, "render_openmotion_preview", wrong_render)
    with pytest.raises(ValueError, match=recipe_id):
        recipe_library.fetch_clips()


def test_openmotion_demo_dimensions_preserves_aspect_within_960(tmp_path):
    demo_big = tmp_path / "big"
    demo_big.mkdir()
    (demo_big / "index.html").write_text('<canvas width="1000" height="600"></canvas>', encoding="utf-8")
    assert recipe_library.openmotion_demo_dimensions(demo_big) == (960, 576)

    demo_small = tmp_path / "small"
    demo_small.mkdir()
    (demo_small / "index.html").write_text('<canvas width="800" height="450"></canvas>', encoding="utf-8")
    assert recipe_library.openmotion_demo_dimensions(demo_small) == (800, 450)
