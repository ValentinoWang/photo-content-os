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
            "tags", "tags_source", "portrait_fit",
        }
        assert (recipe_library.ROOT / entry["path"]).is_file()
        assert entry["portrait_fit"] is True or entry["portrait_fit"] is None
    assert Counter(entry["tags_source"] for entry in entries) == {
        "upstream": 50, "missing": 74,
    }
    for entry in entries:
        assert bool(entry["tags"]) == (entry["tags_source"] == "upstream")

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
