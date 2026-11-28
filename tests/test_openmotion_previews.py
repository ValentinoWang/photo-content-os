import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

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


def _node_binary():
    found = shutil.which("node")
    if found:
        return found
    for candidate in ("/root/pco/.tools/node/bin/node", "/opt/homebrew/bin/node"):
        if Path(candidate).is_file():
            return candidate
    raise RuntimeError("node binary not found")


def _render_picker_html(recipes, categories):
    repo_root = Path(__file__).resolve().parent.parent
    module_url = (repo_root / "studio" / "static" / "direct-promo.js").as_uri()
    script = """
import { readFileSync } from 'node:fs';
const { openRecipePicker } = await import(process.argv[1]);
const { recipes, categories } = JSON.parse(readFileSync(0, 'utf8'));
const noopEl = () => ({ onclick: null, onmouseenter: null, onmouseleave: null, focus() {}, querySelector() { return null; } });
const overlay = {
  className: '',
  innerHTML: '',
  onkeydown: null,
  remove() {},
  querySelector() { return noopEl(); },
  querySelectorAll() { return []; },
};
const host = {
  ownerDocument: { activeElement: null, createElement() { return overlay; } },
  append() {},
};
openRecipePicker(host, { recipes, categories, selected: null, index: 0, onChoose() {} });
process.stdout.write(overlay.innerHTML);
"""
    payload = json.dumps({"recipes": recipes, "categories": categories}, ensure_ascii=False)
    proc = subprocess.run(
        [_node_binary(), "--input-type=module", "-e", script, module_url],
        input=payload,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.stdout


def test_recipe_picker_header_computes_sources_from_data():
    repo_root = Path(__file__).resolve().parent.parent
    scripts_dir = str(repo_root / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from studio.direct import recipes as direct_recipes

    catalog = direct_recipes.catalog()
    html_all = _render_picker_html(catalog["recipes"], catalog["categories"])
    assert "<p>175 张，来自开源项目 video-shotcraft 和 OpenMotion（都是 Apache-2.0）。鼠标停在卡上看样片。</p>" in html_all

    legacy_only = [r for r in catalog["recipes"] if not r["id"].startswith("om-")][:2]
    html_legacy = _render_picker_html(legacy_only, catalog["categories"])
    assert "<p>2 张，来自开源项目 video-shotcraft（Apache-2.0）。鼠标停在卡上看样片。</p>" in html_legacy

    om_only = [r for r in catalog["recipes"] if r["id"].startswith("om-")][:2]
    html_om = _render_picker_html(om_only, catalog["categories"])
    assert "<p>2 张，来自开源项目 OpenMotion（Apache-2.0）。鼠标停在卡上看样片。</p>" in html_om


def test_recipe_picker_marks_only_openmotion_cards_with_om_badge():
    recipes = [
        {
            "id": "blur-slide",
            "name": "模糊滑入",
            "category": "typography",
            "categoryName": "文字",
            "summary": "标题滑入",
            "use": "开场",
            "seconds": 2.0,
            "energy": "中",
            "posterUrl": "/api/direct/recipes/blur-slide/poster.jpg",
            "clipUrl": "/api/direct/recipes/blur-slide/clip.mp4",
        },
        {
            "id": "om-0053d84c-c358-4a52-9baa-8d3381e2ca1e-clip-1",
            "name": "透视线框穿行",
            "category": "camera",
            "categoryName": "运镜",
            "summary": "绿色线框透视走廊",
            "use": "科技开场",
            "seconds": 4.0,
            "energy": "中",
            "posterUrl": "/api/direct/recipes/om-0053d84c-c358-4a52-9baa-8d3381e2ca1e-clip-1/poster.jpg",
            "clipUrl": "/api/direct/recipes/om-0053d84c-c358-4a52-9baa-8d3381e2ca1e-clip-1/clip.mp4",
        },
    ]
    html = _render_picker_html(recipes, [{"key": "typography", "name": "文字", "count": 1}, {"key": "camera", "name": "运镜", "count": 1}])
    cards = dict(re.findall(r'data-recipe="([^"]+)"[^>]*>.*?<em>(.*?)</em>', html, flags=re.S))
    assert cards["blur-slide"] == "文字"
    assert "OM" not in cards["blur-slide"]
    assert "运镜" in cards["om-0053d84c-c358-4a52-9baa-8d3381e2ca1e-clip-1"]
    assert "OM" in cards["om-0053d84c-c358-4a52-9baa-8d3381e2ca1e-clip-1"]
