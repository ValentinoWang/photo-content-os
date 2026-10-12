"""A real 30 fps edit map must survive arithmetic roundoff, not overlaps."""
import copy
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from _support import load_script

review = load_script("review_output_video.py", "roundoff_review", register=True)


def manifest():
    return {"contract": "video_pipeline_manifest.v1", "failure": None,
        "inputs": [{"role": "original_video", "path": "source.mp4", "sha256": "0" * 64}],
        "assets": [], "output": {"path": "candidate.mp4", "sha256": "0" * 64},
        "width": 1080, "height": 1920, "video_tracks": 1, "audio_tracks": 1,
        "duration": 63.86666666666667, "fps": 30,
        "time_map": [
            {"source_start": 41.13333333333333, "source_end": 44.0, "output_start": 32.36666666666667},
            {"source_start": 45.333333333333336, "source_end": 73.96666666666667, "output_start": 35.233333333333334}]}


def validate(value):
    with tempfile.TemporaryDirectory() as directory:
        file = Path(directory) / "manifest.json"
        file.write_text(json.dumps(value))
        with patch.object(review, "file_sha256", return_value="0" * 64), patch.object(
            review, "check_output_video", return_value={"status": "decoded"}) as decode:
            result = review.check_pipeline_manifest(file)
            return result, decode.call_count


def test_frame_thirds_reach_media_checks():
    result, calls = validate(manifest())
    assert result == {"status": "decoded"}
    assert calls == 1


def test_real_overlap_still_rejected_before_media_checks():
    for seconds in (.001, 1 / 30):
        value = copy.deepcopy(manifest())
        value["time_map"][1]["output_start"] -= seconds
        result, calls = validate(value)
        assert result["error_codes"] == ["manifest_invalid"]
        assert calls == 0
