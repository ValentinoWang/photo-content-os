from collections import Counter
from pathlib import Path
import re

import pytest

from scripts.direct_video import recipe_library


def test_index_count_fields_and_unique_ids():
    entries = recipe_library.load_index()
    assert len(entries) == 124
    assert len({entry["category"] for entry in entries}) == 10
    assert len({entry["id"] for entry in entries}) == 124
    paths = [entry["path"] for entry in entries]
    assert paths == sorted(paths)
    for entry in entries:
        assert set(entry) == {
            "id", "category", "path", "summary", "use", "duration", "energy",
            "tags", "tags_source", "portrait_fit", "poster", "poster_source", "clip", "demo", "name", "seconds",
        }
        assert (recipe_library.ROOT / entry["path"]).is_file()
        assert entry["portrait_fit"] is True or entry["portrait_fit"] is None
    assert Counter(entry["tags_source"] for entry in entries) == {
        "upstream": 50, "missing": 74,
    }
    for entry in entries:
        assert bool(entry["tags"]) == (entry["tags_source"] == "upstream")

    # Upstream gallery posters first; every other card with upstream demo source gets a frame of upstream's own render.
    assert Counter(entry["poster_source"] for entry in entries) == {"upstream": 50, "render": 72, None: 2}
    for entry in entries:
        assert (entry["poster"] is None) == (entry["poster_source"] is None)
        if entry["poster"]:
            assert (recipe_library.ROOT / entry["poster"]).is_file()
        if entry["poster_source"] == "render":
            assert entry["demo"]
        if entry["poster"] is None:
            assert entry["demo"] is None
        if entry["demo"]:
            assert (recipe_library.ROOT / entry["demo"]).is_dir()
    clips = recipe_library.load_clips()["clips"]
    assert {e["id"] for e in entries if e["clip"]} == set(clips)
    assert all(re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) for item in clips.values())

    readme = (recipe_library.ROOT / "README.md").read_text(encoding="utf-8")
    documented = re.findall(r"^\| \[[^\]]+\]\(([^)]+\.md)\) \|", readme, flags=re.MULTILINE)
    assert documented == [entry["path"] for entry in entries if entry["portrait_fit"] is None]


def test_get_returns_recipe_and_rejects_unknown_id():
    entry = recipe_library.get("cursor-flyover")
    assert entry["path"] == "camera/cursor-flyover.md"
    assert entry["portrait_fit"] is None
    assert entry["tags"] == []
    assert entry["tags_source"] == "missing"
    assert recipe_library.get("list-reveal")["portrait_fit"] is True
    with pytest.raises(KeyError, match="not-a-recipe"):
        recipe_library.get("not-a-recipe")


def _write_card(tmp_path: Path, *, omit=None, tags=None):
    fields = {
        "name": "example",
        "一句话": "标题：从中央浮入",
        "适用": "章节标题",
        "时长": "1s",
        "能量": "中",
    }
    if tags is not None:
        fields["标签"] = tags
    frontmatter = "\n".join(f"{key}: {value}" for key, value in fields.items() if key != omit)
    card = tmp_path / "example.md"
    card.write_text(f"---\n{frontmatter}\n---\n\n正文提到竖屏。\n", encoding="utf-8")
    return card


@pytest.mark.parametrize("field", ["name", "一句话", "适用", "时长", "能量"])
def test_required_fields_cannot_be_omitted(tmp_path, field):
    with pytest.raises(ValueError, match=field):
        recipe_library.read_card(_write_card(tmp_path, omit=field), "example")


@pytest.mark.parametrize(("tags", "expected", "source"), [
    (None, [], "missing"),
    ("", [], "missing"),
    ("camera、data", ["camera", "data"], "upstream"),
])
def test_tags_preserve_their_source(tmp_path, tags, expected, source):
    entry = recipe_library.read_card(_write_card(tmp_path, tags=tags), "example")
    assert entry["tags"] == expected
    assert entry["tags_source"] == source
    assert entry["portrait_fit"] is None


def test_clip_path_follows_index(monkeypatch, tmp_path):
    monkeypatch.setattr(recipe_library, "CLIP_DIR", tmp_path)
    assert recipe_library.clip_path("blur-slide") == tmp_path / "blur-slide.mp4"
    no_clip = next(e["id"] for e in recipe_library.load_index() if not e["clip"])
    assert recipe_library.clip_path(no_clip) is None


def test_build_index_reads_only_category_cards():
    # demos/README.md and upstream/*.md are upstream docs, not recipe cards.
    entries = recipe_library.build_index()
    assert len(entries) == 124
    assert {entry["category"] for entry in entries}.isdisjoint(recipe_library.NON_CATEGORY_DIRS)


def test_upstream_demo_sources_resolve_inside_repo():
    upstream = recipe_library.ROOT / "upstream"
    assert "3ac67b75dd0b3bc2fd807c17f6b7ce35373eef3d" in (upstream / "UPSTREAM").read_text(encoding="utf-8")
    demos = recipe_library.ROOT / "demos"
    # Upstream's own render-demos.mjs reads workbench/demosrc -> ../demos; both must land on the one copy in shot_recipes/demos.
    assert (upstream / "workbench" / "demosrc").resolve() == demos.resolve()
    assert (upstream / "demos").resolve() == demos.resolve()
    assert (upstream / "workbench" / "scripts" / "render-demos.mjs").is_file()
    missing = []
    for source in demos.glob("*/*/*.tsx"):
        for target in re.findall(r"from '(\.{1,2}/[^']+)'", source.read_text(encoding="utf-8")):
            base = (source.parent / target).resolve()
            candidates = [base, *(base.with_name(base.name + ext) for ext in (".ts", ".tsx", ".json")), base / "index.ts"]
            if not any(path.is_file() for path in candidates):
                missing.append(f"{source.relative_to(demos)} -> {target}")
    assert missing == []


def test_catalog_has_chinese_names_duration_and_normalized_energy():
    import json
    entries = recipe_library.load_index()
    names = json.loads((recipe_library.ROOT / 'names.zh.json').read_text(encoding='utf-8'))
    assert set(names) == {entry['id'] for entry in entries}
    for entry in entries:
        assert entry['name'] == names[entry['id']]
        assert re.fullmatch(r'[\u4e00-\u9fff]{1,8}', entry['name'])
        if entry['duration'].startswith('n/a'):
            assert entry['seconds'] is None
        else:
            assert entry['seconds'] > 0
        assert entry['energy'] in {'低', '中', '高', None}
    assert recipe_library.build_index() == entries
