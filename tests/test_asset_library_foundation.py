"""Focused filesystem contracts for reusable-asset scripts 12, 14, and 15."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from _support import load_script


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"
sys.path.insert(0, str(SCRIPTS))

repeat_photos = load_script("12_select_repeat_photo_groups.py", "select_repeat_photo_groups")
group_distribution = load_script("14_distribute_group_photos_by_name.py", "distribute_group_photos")
register_asset = load_script("15_register_reusable_asset.py", "register_reusable_asset")
import asset_library_index  # noqa: E402


class RepeatPhotoSelectionTests(unittest.TestCase):
    def make_project(self, root: Path) -> tuple[Path, Path]:
        project = root / "project"
        additions = project / "待增加"
        additions.mkdir(parents=True)
        return project, additions

    def test_default_command_plans_without_moving_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project, additions = self.make_project(Path(directory))
            source = additions / "photo.jpg"
            source.write_bytes(b"source")
            argv = ["12_select_repeat_photo_groups.py", str(project)]

            with patch.object(repeat_photos, "generate_contact_sheets", return_value=[]), patch.object(
                sys, "argv", argv
            ):
                repeat_photos.main()

            self.assertEqual(source.read_bytes(), b"source")
            self.assertTrue((repeat_photos.default_output_dir(project) / repeat_photos.PLAN_NAME).is_file())

    def test_apply_moves_only_selected_source_and_keeps_everything_else(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project, additions = self.make_project(Path(directory))
            selected = additions / "selected" / "one.jpg"
            selected.parent.mkdir()
            selected.write_bytes(b"selected")
            unselected = additions / "two.jpg"
            unselected.write_bytes(b"unselected")
            note = additions / "keep.txt"
            note.write_text("keep", encoding="utf-8")
            plan = {
                "items": [
                    {
                        "status": "pending",
                        "source_relative_path": "selected/one.jpg",
                        "action": "merge",
                        "target_relative_path": "03_Group/one.jpg",
                    },
                    {
                        "status": "ignored",
                        "source_relative_path": "two.jpg",
                        "action": None,
                    },
                ]
            }

            operations = repeat_photos.validate_operations(project, additions, plan)
            repeat_photos.apply_operations(operations)
            repeat_photos.prune_empty_addition_dirs(additions)

            self.assertEqual((project / "03_Group/one.jpg").read_bytes(), b"selected")
            self.assertFalse(selected.exists())
            self.assertFalse(selected.parent.exists())
            self.assertEqual(unselected.read_bytes(), b"unselected")
            self.assertEqual(note.read_text(encoding="utf-8"), "keep")

    def test_source_escape_is_rejected_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project, additions = self.make_project(Path(directory))
            outside = project / "outside.jpg"
            outside.write_bytes(b"outside")
            plan = {
                "items": [
                    {
                        "status": "pending",
                        "source_relative_path": "../outside.jpg",
                        "action": "merge",
                        "target_relative_path": "03_Group/outside.jpg",
                    }
                ]
            }

            with self.assertRaisesRegex(RuntimeError, "source escapes"):
                repeat_photos.validate_operations(project, additions, plan)

            self.assertEqual(outside.read_bytes(), b"outside")
            self.assertFalse((project / "03_Group/outside.jpg").exists())

    def test_duplicate_target_is_rejected_before_any_move(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project, additions = self.make_project(Path(directory))
            for name in ("one.jpg", "two.jpg"):
                (additions / name).write_bytes(name.encode("utf-8"))
            plan = {
                "items": [
                    {
                        "status": "pending",
                        "source_relative_path": name,
                        "action": "merge",
                        "target_relative_path": "03_Group/same.jpg",
                    }
                    for name in ("one.jpg", "two.jpg")
                ]
            }

            with self.assertRaisesRegex(RuntimeError, "duplicate target"):
                repeat_photos.validate_operations(project, additions, plan)

            self.assertTrue((additions / "one.jpg").is_file())
            self.assertTrue((additions / "two.jpg").is_file())


class GroupPhotoDistributionTests(unittest.TestCase):
    def make_project(self, root: Path) -> Path:
        project = root / "project"
        project.mkdir()
        return project

    def write_mapping(self, project: Path, rows: list[tuple[str, str, str]]) -> Path:
        mapping = project / "mapping.csv"
        lines = ["photo_path,names,note"]
        lines.extend(",".join(row) for row in rows)
        mapping.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return mapping

    def test_default_command_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self.make_project(Path(directory))
            source = project / "source.jpg"
            source.write_bytes(b"source")
            mapping = self.write_mapping(project, [("source.jpg", "小王", "")])
            argv = [
                "14_distribute_group_photos_by_name.py",
                str(project),
                "--mapping",
                str(mapping),
            ]

            with patch.object(sys, "argv", argv):
                group_distribution.main()

            self.assertEqual(source.read_bytes(), b"source")
            self.assertFalse((project / group_distribution.DISTRIBUTION_DIR).exists())

    def test_apply_preserves_source_and_repeated_apply_adds_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self.make_project(Path(directory))
            source = project / "source.jpg"
            source.write_bytes(b"source")
            mapping = self.write_mapping(project, [("source.jpg", "小王", "")])

            group_distribution.distribute(str(project), str(mapping), None, dry_run=False)
            output_root = project / group_distribution.DISTRIBUTION_DIR
            target = output_root / "按姓名" / "小王" / "source.jpg"
            first_files = sorted(path.relative_to(output_root) for path in output_root.rglob("*") if path.is_file())
            log_before = (output_root / "合照发放记录.md").read_bytes()

            group_distribution.distribute(str(project), str(mapping), None, dry_run=False)

            second_files = sorted(path.relative_to(output_root) for path in output_root.rglob("*") if path.is_file())
            self.assertEqual(source.read_bytes(), b"source")
            self.assertEqual(target.read_bytes(), b"source")
            self.assertEqual(second_files, first_files)
            self.assertEqual((output_root / "合照发放记录.md").read_bytes(), log_before)

    def test_same_filename_different_content_gets_stable_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self.make_project(Path(directory))
            first = project / "one" / "photo.jpg"
            second = project / "two" / "photo.jpg"
            first.parent.mkdir()
            second.parent.mkdir()
            first.write_bytes(b"first")
            second.write_bytes(b"second")
            mapping = self.write_mapping(
                project,
                [("one/photo.jpg", "小王", ""), ("two/photo.jpg", "小王", "")],
            )

            group_distribution.distribute(str(project), str(mapping), None, dry_run=False)

            target_dir = project / group_distribution.DISTRIBUTION_DIR / "按姓名" / "小王"
            suffix = group_distribution.media_id("two/photo.jpg")
            self.assertEqual((target_dir / "photo.jpg").read_bytes(), b"first")
            self.assertEqual((target_dir / f"photo_{suffix}.jpg").read_bytes(), b"second")

    def test_escape_and_external_output_are_rejected_without_output_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = self.make_project(root)
            outside = root / "outside.jpg"
            outside.write_bytes(b"outside")
            mapping = self.write_mapping(project, [("../outside.jpg", "小王", "")])
            output_root = project / group_distribution.DISTRIBUTION_DIR

            with self.assertRaisesRegex(RuntimeError, "photo_path must stay inside project"):
                group_distribution.distribute(str(project), str(mapping), None, dry_run=False)
            with self.assertRaisesRegex(RuntimeError, "output directory must stay inside project"):
                group_distribution.distribute(str(project), str(mapping), str(root / "external"), dry_run=True)

            self.assertFalse(output_root.exists())
            self.assertEqual(outside.read_bytes(), b"outside")


class ReusableAssetRegistrationTests(unittest.TestCase):
    def make_project(self, root: Path) -> tuple[Path, Path]:
        project = root / "project"
        project.mkdir()
        media = project / "source.mp4"
        media.write_bytes(b"source-media")
        return project, media

    def args(self, project: Path, media: Path, library: Path, **overrides: object) -> argparse.Namespace:
        values: dict[str, object] = {
            "project_dir": str(project),
            "media_path": str(media),
            "library_root": str(library),
            "category": "Reusable_校园",
            "title": "同名素材",
            "tags": "校园、人物",
            "uses": "开场、转场",
            "cuts": "00:00-00:03",
            "public_status": "待确认",
            "icloud_copy": "80_To_iCloudPhotos_精选入库/source.mp4",
            "notes": "fixture",
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_default_command_is_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project, media = self.make_project(root)
            library = root / "library"
            argv = [
                "15_register_reusable_asset.py",
                str(project),
                str(media),
                "--library-root",
                str(library),
            ]

            with patch.object(sys, "argv", argv):
                register_asset.main()

            self.assertEqual(media.read_bytes(), b"source-media")
            self.assertFalse(library.exists())

    def test_apply_writes_valid_queryable_index_and_preserves_media(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project, media = self.make_project(root)
            library = root / "library"

            markdown_path, card_path = register_asset.register_asset(
                self.args(project, media, library), apply=True
            )
            structured_path = library / asset_library_index.INDEX_NAME
            data = json.loads(structured_path.read_text(encoding="utf-8"))

            asset_library_index.validate_index(data)
            schema = json.loads((SCHEMAS / "asset_library_index.schema.json").read_text(encoding="utf-8"))
            self.assertEqual(schema["properties"]["schema_version"]["const"], data["schema_version"])
            self.assertEqual(data["revision"], 1)
            self.assertEqual(data["asset_count"], 1)
            self.assertEqual(data["categories"], [{"name": "Reusable_校园", "asset_count": 1}])
            self.assertEqual(len(asset_library_index.query_assets(data, category="Reusable_校园", tags=["人物", "校园"])), 1)
            self.assertEqual(asset_library_index.query_assets(data, tags=["不存在"]), [])
            self.assertNotIn(str(project), structured_path.read_text(encoding="utf-8"))
            self.assertTrue(markdown_path.is_file())
            self.assertTrue(card_path.is_file())
            self.assertEqual(media.read_bytes(), b"source-media")

    def test_same_asset_is_byte_idempotent_and_same_title_keeps_distinct_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project, first = self.make_project(root)
            second = project / "second.mp4"
            second.write_bytes(b"second-media")
            library = root / "library"
            first_args = self.args(project, first, library)

            markdown_path, first_card = register_asset.register_asset(first_args, apply=True)
            structured_path = library / asset_library_index.INDEX_NAME
            first_snapshot = {
                path: path.read_bytes() for path in (structured_path, markdown_path, first_card)
            }
            register_asset.register_asset(first_args, apply=True)
            self.assertEqual(
                {path: path.read_bytes() for path in (structured_path, markdown_path, first_card)},
                first_snapshot,
            )

            _, second_card = register_asset.register_asset(
                self.args(project, second, library, icloud_copy=None), apply=True
            )
            data = json.loads(structured_path.read_text(encoding="utf-8"))
            self.assertEqual(data["revision"], 2)
            self.assertEqual(data["asset_count"], 2)
            self.assertEqual(len({asset["asset_id"] for asset in data["assets"]}), 2)
            self.assertEqual(len({asset["card_path"] for asset in data["assets"]}), 2)
            self.assertNotEqual(first_card, second_card)
            self.assertEqual(markdown_path.read_text(encoding="utf-8").count("- [同名素材]("), 2)

            malformed = json.loads(structured_path.read_text(encoding="utf-8"))
            malformed["assets"][1]["card_path"] = malformed["assets"][0]["card_path"]
            with self.assertRaisesRegex(asset_library_index.AssetIndexError, "duplicate card_path"):
                asset_library_index.validate_index(malformed)

    def test_malformed_index_and_media_escape_fail_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project, media = self.make_project(root)
            library = root / "library"
            library.mkdir()
            structured_path = library / asset_library_index.INDEX_NAME
            structured_path.write_text("{invalid", encoding="utf-8")

            with self.assertRaises(asset_library_index.AssetIndexError):
                register_asset.register_asset(self.args(project, media, library), apply=True)

            self.assertEqual(sorted(path.name for path in library.iterdir()), [asset_library_index.INDEX_NAME])
            outside = root / "outside.mp4"
            outside.write_bytes(b"outside")
            empty_library = root / "empty-library"
            with self.assertRaisesRegex(RuntimeError, "media path must be inside project"):
                register_asset.register_asset(self.args(project, outside, empty_library), apply=True)
            self.assertFalse(empty_library.exists())


if __name__ == "__main__":
    unittest.main()
