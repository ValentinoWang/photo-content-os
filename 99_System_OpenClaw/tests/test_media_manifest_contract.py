from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from PIL.TiffImagePlugin import IFDRational


SYSTEM = Path(__file__).resolve().parents[1]
SCRIPTS = SYSTEM / "scripts"
SCHEMA = SYSTEM / "schemas" / "media_manifest.schema.json"
sys.path.insert(0, str(SCRIPTS))


def load_scanner():
    source = SCRIPTS / "01_scan_media_manifest.py"
    spec = importlib.util.spec_from_file_location("scan_media_manifest_contract", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load scanner: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scanner = load_scanner()


def save_image(path: Path, *, gps: bool = False) -> None:
    image = Image.new("RGB", (12, 8), (10, 20, 30))
    if not gps:
        image.save(path, format="PNG")
        return
    exif = Image.Exif()
    exif[34853] = {
        1: "N",
        2: (IFDRational(37, 1), IFDRational(30, 1), IFDRational(0, 1)),
        3: "W",
        4: (IFDRational(122, 1), IFDRational(15, 1), IFDRational(0, 1)),
        5: 0,
        6: IFDRational(12, 1),
    }
    image.save(path, format="JPEG", exif=exif.tobytes())


def only_item(manifest: dict[str, object], filename: str) -> dict[str, object]:
    items = [item for item in manifest["items"] if item["filename"] == filename]
    if len(items) != 1:
        raise AssertionError(f"expected one item for {filename}, got {items}")
    return items[0]


class MediaManifestContractTests(unittest.TestCase):
    def test_valid_image_reports_content_hash_and_explicit_health(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            image = project / "valid.png"
            save_image(image)

            manifest = scanner.scan_project(str(project))
            item = only_item(manifest, image.name)

            self.assertEqual(item["sha256"], hashlib.sha256(image.read_bytes()).hexdigest())
            self.assertTrue(item["image_readable"])
            self.assertEqual(item["image_health"], "healthy")
            self.assertIsNone(item["image_health_reason"])

    def test_missing_exif_is_explicitly_unknown_without_coordinates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            image = project / "without-exif.png"
            save_image(image)

            item = only_item(scanner.scan_project(str(project)), image.name)
            location = item["exif_location"]

            self.assertEqual(location["state"], "unknown")
            self.assertIsNone(location["latitude"])
            self.assertIsNone(location["longitude"])
            self.assertIsNone(location["altitude"])
            self.assertIsNone(item["gps_latitude"])
            self.assertIsNone(item["gps_longitude"])

    def test_valid_exif_location_is_bounded_and_projected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            image = project / "with-exif.jpg"
            save_image(image, gps=True)

            item = only_item(scanner.scan_project(str(project)), image.name)
            location = item["exif_location"]

            self.assertEqual(location["state"], "present")
            self.assertAlmostEqual(location["latitude"], 37.5)
            self.assertAlmostEqual(location["longitude"], -122.25)
            self.assertEqual(location["altitude"], 12.0)
            self.assertGreaterEqual(location["latitude"], -90)
            self.assertLessEqual(location["latitude"], 90)
            self.assertGreaterEqual(location["longitude"], -180)
            self.assertLessEqual(location["longitude"], 180)
            self.assertEqual(item["gps_latitude"], location["latitude"])
            self.assertEqual(item["gps_longitude"], location["longitude"])

    def test_malformed_image_remains_reportable_with_stable_nonhealthy_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            image = project / "corrupt.jpg"
            image.write_bytes(b"this is not a JPEG")

            manifest = scanner.scan_project(str(project))
            item = only_item(manifest, image.name)

            self.assertEqual(item["sha256"], hashlib.sha256(image.read_bytes()).hexdigest())
            self.assertFalse(item["image_readable"])
            self.assertEqual(item["image_health"], "malformed")
            self.assertEqual(item["image_health_reason"], "malformed_image")
            self.assertEqual(item["exif_location"]["state"], "unknown")

    def test_schema_declares_fail_closed_image_contract(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        item_schema = schema["$defs"]["media_item"]
        required = set(item_schema["required"])

        self.assertEqual(schema["properties"]["manifest_version"]["const"], 2)
        self.assertTrue({"sha256", "image_readable", "image_health", "exif_location"} <= required)
        self.assertEqual(
            set(item_schema["properties"]["image_health"]["enum"]),
            {"healthy", "malformed", "unreadable", "probe_unavailable", "not_applicable"},
        )
        location_schema = schema["$defs"]["exif_location"]
        self.assertEqual(set(location_schema["properties"]["state"]["enum"]), {"present", "unknown"})
        self.assertEqual(
            set(location_schema["required"]),
            {"state", "latitude", "longitude", "altitude", "horizontal_accuracy"},
        )


if __name__ == "__main__":
    unittest.main()
