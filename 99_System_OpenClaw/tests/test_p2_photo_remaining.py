import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


review = load("19_review_output_video")
bootstrap = load("project_bootstrap_common")
native = load("26_create_native_import_pack")


class P2PhotoRegressionTests(unittest.TestCase):
    def test_platform_aliases_and_unknown_platform_are_explicit(self):
        self.assertEqual(review.normalize_platforms("发布平台：B 站、快手、YouTube"), ["B站", "快手", "YouTube"])
        context = review.load_project_context(self._readme("发布平台：未知平台\n剪辑目标：旅行记录"))
        self.assertTrue(any("未识别发布平台" in note for note in context.notes))

    def test_personal_title_replacement_is_not_global(self):
        self.assertNotIn("清华大学深圳国际研究生院", bootstrap.TITLE_REPLACEMENTS)

    def test_raw360_filter_requires_supported_configured_lens(self):
        self.assertIn("crop=iw/2:ih:0:0", native.raw360_lrf_filter(1080, 1920, 30, lens="left"))
        with self.assertRaises(native.ContractError):
            native.raw360_lrf_filter(1080, 1920, 30, lens="center")

    def test_runner_and_analysis_contracts_consume_audio_and_context(self):
        runner = (SCRIPTS / "mac_openclaw_runner.py").read_text(encoding="utf-8")
        analysis = (SCRIPTS / "run_analyze_project.py").read_text(encoding="utf-8")
        helper = (SCRIPTS / "03_extract_audio_helper.py").read_text(encoding="utf-8")
        self.assertIn("--audio", runner)
        self.assertIn("--transcript-provider", runner)
        self.assertIn("OPENCLAW_TRANSCRIPTION_PROVIDER", analysis)
        self.assertIn("audio_seconds_budget", helper)

    def _readme(self, text: str) -> Path:
        directory = Path(tempfile.mkdtemp())
        path = directory / "readme.md"
        path.write_text(text, encoding="utf-8")
        self.addCleanup(lambda: directory.rmdir())
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return directory


if __name__ == "__main__":
    unittest.main()
