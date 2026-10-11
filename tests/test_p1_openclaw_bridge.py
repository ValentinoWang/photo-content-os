from __future__ import annotations

import ast
import json
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS))

import openclaw_product_contract as contract  # noqa: E402


class OpenClawBridgeTests(unittest.TestCase):
    def test_core_has_no_mandatory_openclaw_media_dependency(self):
        requirements = (REPOSITORY_ROOT / "requirements-dev.txt").read_text(encoding="utf-8").lower()
        self.assertNotIn("openclaw-media", requirements)

        direct_imports: list[str] = []
        for path in (REPOSITORY_ROOT / "99_System_OpenClaw").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                if any(name == "openclaw_media" or name.startswith("openclaw_media.") for name in names):
                    direct_imports.append(str(path.relative_to(REPOSITORY_ROOT)))
        self.assertEqual(direct_imports, [])

    def test_missing_optional_package_is_reported_without_breaking_core(self):
        with patch.object(contract, "_installed_catalog", return_value=(None, None)):
            result = contract.compatibility()
        self.assertFalse(result.available)
        self.assertFalse(result.compatible)
        self.assertEqual(result.reason, "openclaw_media_not_installed")

    def test_snapshot_has_valid_reviewed_commit_and_supported_identity(self):
        snapshot = contract.load_snapshot()
        self.assertRegex(snapshot["upstream_commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(snapshot["catalog_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(snapshot["upstream_contract_id"], "openclaw_media_product_v1")
        self.assertEqual(len(snapshot["pipelines"]), 9)

    def test_pipeline_allowlist(self):
        self.assertEqual(contract.pipeline_id("match"), "media.material.match.v1")
        with self.assertRaisesRegex(contract.ProductContractError, "pipeline_not_allowed"):
            contract.pipeline_id("shell.exec")

    def test_workspace_ref_is_posix_relative(self):
        self.assertEqual(contract.safe_workspace_ref("projects/demo"), "projects/demo")
        for bad in ("../secret", "/absolute", "C:\\media", "https://example.com"):
            with self.subTest(bad=bad), self.assertRaises(contract.ProductContractError):
                contract.safe_workspace_ref(bad)

    def test_windows_local_compatibility_but_cloud_pairing_fails_closed(self):
        snapshot = contract.load_snapshot()
        pipelines = [{"pipeline_id": p, "version": "1.0.0"} for p in sorted(snapshot["pipelines"].values())]
        raw = json.dumps(pipelines, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        digest = "sha256:" + hashlib.sha256(raw.encode()).hexdigest()
        snapshot["catalog_digest"] = digest
        catalog = {"catalog_digest": digest, "pipelines": pipelines}
        with patch.object(contract, "load_snapshot", return_value=snapshot), patch.object(contract, "_installed_catalog", return_value=("0.1.0", catalog)), patch.object(contract, "platform_contract_name", return_value="windows"):
            self.assertTrue(contract.compatibility(require_cloud_platform=False).compatible)
            result = contract.compatibility(require_cloud_platform=True)
            self.assertFalse(result.compatible)
            self.assertEqual(result.reason, "upstream_platform_unsupported")


if __name__ == "__main__":
    unittest.main()
