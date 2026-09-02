"""Versioned, atomic persistence for the desktop analysis budget."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "analysis_budget_settings_v1"
FILE_NAME = "analysis-budget.json"
BUDGET_FIELDS = (
    "preview_images_per_asset",
    "deep_images_per_asset",
    "max_preview_assets",
    "max_deep_assets",
    "max_audio_minutes",
)
DEFAULT_BUDGET: dict[str, int | float] = {
    "preview_images_per_asset": 3,
    "deep_images_per_asset": 8,
    "max_preview_assets": 60,
    "max_deep_assets": 15,
    "max_audio_minutes": 60,
}


class AnalysisBudgetError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def validate_budget(value: object) -> dict[str, int | float]:
    if not isinstance(value, Mapping) or set(value) != set(BUDGET_FIELDS):
        raise AnalysisBudgetError("analysis_budget_invalid", "分析预算字段不完整或包含未知字段")
    result: dict[str, int | float] = {}
    for field in BUDGET_FIELDS:
        raw = value[field]
        if field == "max_audio_minutes":
            if isinstance(raw, bool) or not isinstance(raw, (int, float)) or raw < 0:
                raise AnalysisBudgetError("analysis_budget_invalid", "音频分钟预算必须是非负数字")
            result[field] = raw
            continue
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            raise AnalysisBudgetError("analysis_budget_invalid", "图像和素材预算必须是非负整数")
        result[field] = raw
    return result


class AnalysisBudgetStore:
    def __init__(self, settings_dir: Path) -> None:
        self.settings_dir = settings_dir.expanduser().resolve()
        self.path = self.settings_dir / FILE_NAME
        self._lock = threading.RLock()

    def _initial(self) -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "revision": 1, "budget": dict(DEFAULT_BUDGET)}

    def _validate_state(self, value: object) -> dict[str, Any]:
        if not isinstance(value, dict) or set(value) != {"schema_version", "revision", "budget"}:
            raise AnalysisBudgetError("analysis_budget_state_invalid", "分析预算存储格式无效")
        if value["schema_version"] != SCHEMA_VERSION:
            raise AnalysisBudgetError("analysis_budget_state_invalid", "分析预算存储版本无效")
        revision = value["revision"]
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise AnalysisBudgetError("analysis_budget_state_invalid", "分析预算 revision 无效")
        return {"schema_version": SCHEMA_VERSION, "revision": revision, "budget": validate_budget(value["budget"])}

    def _atomic_write(self, value: Mapping[str, object]) -> None:
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        descriptor: int | None = None
        temporary_path: str | None = None
        try:
            descriptor, temporary_path = tempfile.mkstemp(
                prefix=f".{FILE_NAME}.", suffix=".tmp", dir=self.settings_dir
            )
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                descriptor = None
                json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
        except OSError as exc:
            raise AnalysisBudgetError("analysis_budget_unavailable", "分析预算无法保存") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return self._initial()
            if self.path.is_symlink() or not self.path.is_file():
                raise AnalysisBudgetError("analysis_budget_unavailable", "分析预算存储不可用")
            try:
                value = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise AnalysisBudgetError("analysis_budget_state_invalid", "分析预算存储无法读取") from exc
            return self._validate_state(value)

    def update(self, budget: object, *, expected_revision: int) -> dict[str, Any]:
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise AnalysisBudgetError("revision_invalid", "expectedRevision 必须是正整数")
        normalized = validate_budget(budget)
        with self._lock:
            current = self.load()
            if current["revision"] != expected_revision:
                raise AnalysisBudgetError("revision_conflict", "分析预算已被更新，请刷新后重试")
            updated = {
                "schema_version": SCHEMA_VERSION,
                "revision": expected_revision + 1,
                "budget": normalized,
            }
            self._atomic_write(updated)
            return updated


__all__ = [
    "AnalysisBudgetError",
    "AnalysisBudgetStore",
    "BUDGET_FIELDS",
    "DEFAULT_BUDGET",
    "SCHEMA_VERSION",
    "validate_budget",
]
