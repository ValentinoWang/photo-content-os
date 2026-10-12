"""Local editing adapter contract; render arguments match kdenlive_render.render."""
from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, TypedDict, runtime_checkable


class BackendError(ValueError):
    """An explicitly selected backend cannot complete the requested operation."""


class Capabilities(TypedDict):
    automatic_first_cut: bool
    transparent_overlay: bool
    chinese_subtitle_burn_in: bool
    web_refine: bool
    undo: bool
    read_back: bool
    export_formats: list[str]


class Description(TypedDict):
    id: str
    display_name: str
    license: str
    capabilities: Capabilities


class Probe(TypedDict):
    id: str
    installed: bool
    version: str | None
    runnable: bool
    status: Literal["online", "unavailable", "unknown"]
    reason: str | None


class CloseResult(TypedDict):
    id: str
    started_pids: list[int]
    remaining_pids: list[int]


@runtime_checkable
class EditBackend(Protocol):
    def describe(self) -> Description: ...

    def probe(self) -> Probe: ...

    def render(self, *, source: Path, suggestions_path: Path, output_dir: Path,
               subtitles: Path | None = None, animations: list[dict] | None = None,
               project_id: str = "spoken-test", project_revision: int = 1,
               timeout_seconds: float = 300) -> dict: ...

    def open_for_refine(self, *, project_dir: Path) -> dict:
        """Return a local session descriptor; unsupported adapters raise BackendError."""
        ...

    def read_back(self, *, project_dir: Path) -> dict:
        """Return {time_map, render_kwargs} from the actual edited project.

        render_kwargs matches render's keyword arguments, excluding output_dir.
        Subsequent render on this instance must honor the read-back timeline.
        Never infer user edits from a previously generated plan.
        """
        ...

    def close(self) -> CloseResult:
        """Reap only this instance's processes, including descendants; idempotent."""
        ...
