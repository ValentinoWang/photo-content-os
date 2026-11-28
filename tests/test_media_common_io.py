from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import media_common
import jianying_roughcut_common
import media_project_selection


def test_time_entry_points_preserve_local_and_utc_types(monkeypatch):
    class FixedDatetime:
        @staticmethod
        def now(tz=None):
            if tz is None:
                return datetime(2026, 11, 28, 1, 2, 3)
            assert tz is timezone.utc
            return datetime(2026, 11, 28, 1, 2, 3, 456789, tzinfo=tz)

    monkeypatch.setattr(media_common, 'datetime', FixedDatetime)
    assert jianying_roughcut_common.now_compact() == '20261128_010203'
    assert media_project_selection._now() == datetime(2026, 11, 28, 1, 2, 3, 456789, tzinfo=timezone.utc)
