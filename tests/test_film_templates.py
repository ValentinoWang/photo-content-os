import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("film_templates", Path(__file__).parents[1] / "scripts/direct_video/film_templates.py")
film = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(film)


def item(i, kind, media):
    return {"repositoryId": str(i), "templateId": i, "title": {"zh": "中文", "en": "English"}, "summary": {"zh": "简介"}, "group": "talk", "orientation": "landscape", "ratio": "16:9", "width": 1920, "height": 1080, "fps": 30, "version": "1", "website": "https://example.org", "repository": None, "download": {"type": kind}, "media": media, "materials": {"zh": "素材"}}


def test_build_three_shapes(tmp_path):
    import json
    source = tmp_path / "upstream.json"
    source.write_text(json.dumps({"templates": [item(3, "official-page", {"en": {"demo": "https://example.org/en", "poster": "https://example.org/poster"}}), item(1, "direct-package", {"zh": {"demo": "https://example.org/a", "poster": "https://example.org/b"}}), item(2, "official-page", {"zh": {"demo": "https://example.org/a", "poster": "https://example.org/b"}})]}))
    catalog = film.build_catalog(str(source), open_license="MIT")
    assert [x["id"] for x in catalog["templates"]] == ["1", "2", "3"]
    assert [x["source_status"] for x in catalog["templates"]] == ["open-package", "account-required", "account-required"]
    assert catalog["templates"][0]["license"] == "MIT"
    assert catalog["templates"][2]["demo_url"] == "https://example.org/en"


def test_check_rejects_duplicate():
    with pytest.raises(ValueError):
        film.check_catalog({"upstream_commit": "a" * 40, "count": 206, "templates": []})


def test_scene_validation(tmp_path):
    scene = {"id": "1", "commit": "a" * 40, "license": "MIT", "scenes": [{"key": "B1", "purpose": "开场", "required_fields": ["title"], "duration_seconds": 2, "source_file": "README.zh-CN.md", "source_commit": "a" * 40}]}
    entry = {"id": "1", "commit": "a" * 40}
    film.check_scene(scene, entry)
    scene["scenes"][0]["duration_seconds"] = 0
    with pytest.raises(ValueError):
        film.check_scene(scene, entry)


def test_download_hash_mismatch_removes_partial(tmp_path, monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def raise_for_status(self): pass
        def iter_content(self, chunk_size): yield b"incorrect"
    monkeypatch.setattr(film.requests, "get", lambda *args, **kwargs: Response())
    destination = tmp_path / "template.motion"
    with pytest.raises(ValueError):
        film.fetch_open(destination)
    assert not destination.exists()
    assert not destination.with_suffix(".motion.part").exists()
