import json

from scripts.direct_video import openmotion_import, recipe_library


def test_filters_single_clips_and_writes_repeatable_output(tmp_path):
    catalog = tmp_path / "catalog"
    source = catalog / "fixture-template" / "source"
    demos = source / "demos"
    demos.mkdir(parents=True)
    blocks = []
    for number in range(1, 5):
        metadata = {"id": f"clip-{number}", "src": f"demos/clip-{number}.html", "title": f"Clip {number}", "duration": 2.5, "description": "Shapes appear."}
        blocks.append(f"## Clip {number}\n\n```motion-demo\n{json.dumps(metadata)}\n```")
    (source / "motion.md").write_text("\n\n".join(blocks), encoding="utf-8")
    valid = "<html><script>window.seekFrame = (frame, fps) => {};</script></html>"
    for number, html in enumerate((
        valid, valid.replace("<script>", '<img src="../assets/reference-1.webp"><script>'),
        valid, "<html><p>No frame hook</p></html>",
    ), 1):
        (demos / f"clip-{number}.html").write_text(html, encoding="utf-8")
    (demos / "sequence.html").write_text(valid, encoding="utf-8")
    editorial = {
        "fixture-template/clip-1": {
            "category": "data", "name": "数据入场", "summary": "图形依次出现",
            "use": "数据对比", "energy": "中",
        },
        "fixture-template/clip-3": {"duplicate": "data/example.md"},
    }
    root = tmp_path / "recipes"
    (root / "data").mkdir(parents=True)
    (root / "data" / "example.md").touch()
    report = tmp_path / "excluded.md"
    openmotion_import.import_catalog(catalog, editorial, root, report, "Apache license\n")
    first = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    first[report] = report.read_bytes()
    openmotion_import.import_catalog(catalog, editorial, root, report, "Apache license\n")
    assert {path: path.read_bytes() for path in first} == first
    assert len(list((root / "openmotion").glob("*.md"))) == 1
    card = root / "openmotion" / "om-fixture-template-clip-1.md"
    entry = recipe_library.read_card(card, "openmotion")
    assert (entry["category"], entry["duration"]) == ("data", "2.5s")
    assert entry["path"] == "openmotion/om-fixture-template-clip-1.md"
    assert openmotion_import.COMMIT in (root / "ATTRIBUTION-openmotion.md").read_text()
    excluded = report.read_text()
    assert "clip-2" in excluded and "参考图" in excluded
    assert "clip-3" in excluded and "data/example.md" in excluded
    assert "clip-4" in excluded and "seekFrame" in excluded
    assert "sequence" not in excluded


def test_openmotion_manifest_matches_installed_cards():
    manifest = recipe_library.load_openmotion_manifest()
    entries = recipe_library.load_index()
    installed = {entry["id"] for entry in entries if entry["path"].startswith("openmotion/")}
    assert installed
    assert installed == set(manifest["clips"])
    assert manifest["commit"] == openmotion_import.COMMIT
    assert openmotion_import.COMMIT in (recipe_library.ROOT / "ATTRIBUTION-openmotion.md").read_text()
    recipe_library.check_openmotion()
