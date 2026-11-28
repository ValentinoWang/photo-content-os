#!/usr/bin/env python3
"""Capture an NFD-compatible screenshot package for Photo Content OS Studio.

Uses only synthetic demo data created in temporary directories and connects to a
real local Studio server on an ephemeral port (unless --port is specified).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
for _path in (str(REPO_ROOT), str(SCRIPT_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from studio.project_store import ProjectStore  # noqa: E402

if __package__:
    from .constants import (
        VIEWPORT_WIDTH,
        VIEWPORT_HEIGHT,
        DEVICE_SCALE_FACTOR,
        ROLE_ID,
        ROLE_TITLE,
        ROLE_COLOR,
        ROLE_VIEWPORT,
        UUID_NAMESPACE,
        DEMO_PROJECT_NAME,
        DEMO_PROJECT_PLATFORM,
        SERVER_READY_RE,
        SERVER_START_TIMEOUT_SEC,
        CAPTURE_TIMEOUT_SEC,
        NAV_ORDER,
        NODE_CAPTURE_DRIVER,
    )
else:
    from constants import (
        VIEWPORT_WIDTH,
        VIEWPORT_HEIGHT,
        DEVICE_SCALE_FACTOR,
        ROLE_ID,
        ROLE_TITLE,
        ROLE_COLOR,
        ROLE_VIEWPORT,
        UUID_NAMESPACE,
        DEMO_PROJECT_NAME,
        DEMO_PROJECT_PLATFORM,
        SERVER_READY_RE,
        SERVER_START_TIMEOUT_SEC,
        CAPTURE_TIMEOUT_SEC,
        NAV_ORDER,
        NODE_CAPTURE_DRIVER,
    )


@dataclass(frozen=True)
class PageSpec:
    id: str
    title: str
    nav_key: str
    group_id: str
    group_title: str
    route: str
    kind: str
    is_primary_entry: bool
    control_label: str



PAGE_SPECS: tuple[PageSpec, ...] = (
    PageSpec(
        id="studio-home",
        title="工作台",
        nav_key="home",
        group_id="nav-home",
        group_title="工作台",
        route="/#view=home",
        kind="页面",
        is_primary_entry=True,
        control_label="工作台",
    ),
    PageSpec(
        id="studio-inbox",
        title="整理台",
        nav_key="inbox",
        group_id="nav-inbox",
        group_title="整理台",
        route="/#view=inbox",
        kind="页面",
        is_primary_entry=True,
        control_label="整理台",
    ),
    PageSpec(
        id="studio-projects",
        title="项目",
        nav_key="projects",
        group_id="nav-projects",
        group_title="项目",
        route="/#view=projects",
        kind="页面",
        is_primary_entry=True,
        control_label="项目",
    ),
    PageSpec(
        id="studio-library",
        title="素材库",
        nav_key="library",
        group_id="nav-library",
        group_title="素材库",
        route="/#view=library",
        kind="页面",
        is_primary_entry=True,
        control_label="素材库",
    ),
    PageSpec(
        id="studio-music",
        title="音乐库",
        nav_key="music",
        group_id="nav-music",
        group_title="音乐库",
        route="/#view=music",
        kind="页面",
        is_primary_entry=True,
        control_label="音乐库",
    ),
    PageSpec(
        id="studio-settings",
        title="设置与诊断",
        nav_key="settings",
        group_id="nav-settings",
        group_title="设置与诊断",
        route="/#view=settings",
        kind="页面",
        is_primary_entry=True,
        control_label="设置与诊断",
    ),
    PageSpec(
        id="studio-project-detail",
        title="项目详情",
        nav_key="projects",
        group_id="nav-projects",
        group_title="项目",
        route="/#view=piece",
        kind="子页面",
        is_primary_entry=False,
        control_label="演示作品",
    ),
)

PAGE_SPECS_BY_ID: dict[str, PageSpec] = {spec.id: spec for spec in PAGE_SPECS}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_uuid(page_id: str) -> str:
    """Return a deterministic RFC 4122 UUID for a stable page identifier."""
    return str(uuid.uuid5(UUID_NAMESPACE, page_id))


def parse_studio_ready_url(line: str) -> str | None:
    """Extract the bound loopback URL printed by launch_studio.py."""
    match = SERVER_READY_RE.search(line)
    if not match:
        return None
    return match.group(1).rstrip("/")


def compute_scroll_segments(total_height: int, viewport_height: int) -> list[dict[str, int]]:
    """Plan non-overlapping vertical scroll offsets covering [0, total_height)."""
    if viewport_height <= 0:
        raise ValueError("viewport_height must be positive")
    effective_total = max(int(total_height), int(viewport_height))
    segments: list[dict[str, int]] = []
    offset = 0
    while offset < effective_total:
        height = min(viewport_height, effective_total - offset)
        segments.append({"offset": offset, "height": height})
        offset += height
    return segments


def stitch_vertical_tiles(
    tiles: Sequence[Mapping[str, Any]],
    *,
    width: int,
    total_height: int,
) -> bytes:
    """Stitch segmented viewport captures into one full-page PNG without gaps or overlap.

    Each tile must contain:
      - ``png_bytes``: raw PNG bytes of a single viewport capture
      - ``source_y``: vertical start pixel inside that viewport capture
      - ``height``: vertical height to copy from that capture
      - ``dest_y``: target vertical coordinate in the stitched image
    """
    if width <= 0 or total_height <= 0:
        raise ValueError("width and total_height must be positive")
    if not tiles:
        raise ValueError("at least one tile is required")

    ordered = sorted(tiles, key=lambda item: int(item["dest_y"]))
    canvas = Image.new("RGBA", (int(width), int(total_height)))
    cursor = 0
    for index, tile in enumerate(ordered):
        dest_y = int(tile["dest_y"])
        source_y = int(tile["source_y"])
        slice_height = int(tile["height"])
        if dest_y != cursor:
            raise ValueError(
                f"tile {index} has gap or overlap: expected dest_y={cursor}, got {dest_y}"
            )
        if source_y < 0 or slice_height <= 0:
            raise ValueError(f"tile {index} has invalid source_y={source_y} or height={slice_height}")
        with Image.open(io.BytesIO(tile["png_bytes"])) as img:
            if img.width != width:
                raise ValueError(f"tile {index} width mismatch: expected {width}, got {img.width}")
            if source_y + slice_height > img.height:
                raise ValueError(
                    f"tile {index} slice [{source_y}, {source_y + slice_height}) exceeds tile height {img.height}"
                )
            cropped = img.crop((0, source_y, width, source_y + slice_height)).convert("RGBA")
            canvas.paste(cropped, (0, dest_y))
        cursor += slice_height

    if cursor != total_height:
        raise ValueError(f"stitched height {cursor} does not match total_height {total_height}")

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer.getvalue()


def build_manifest_record(
    spec: PageSpec,
    *,
    relative_file: str,
    width: int,
    height: int,
    scroll_height: int,
    sha256_hex: str,
    captured_at: str,
    viewport_width: int = VIEWPORT_WIDTH,
    viewport_height: int = VIEWPORT_HEIGHT,
    actual_route: str | None = None,
) -> dict[str, Any]:
    """Build one manifest record matching NFD screenshot-package.md and gallery_graph.py."""
    if height != scroll_height:
        raise ValueError(
            f"{spec.id}: stitched height ({height}) does not match scrollHeight ({scroll_height})"
        )
    route_value = spec.route
    actual_value = actual_route or route_value
    return {
        "id": spec.id,
        "uuid": stable_uuid(spec.id),
        "title": spec.title,
        "role": ROLE_ID,
        "galleryRole": ROLE_ID,
        "route": route_value,
        "requestedRoute": route_value,
        "actualRoute": actual_value,
        "kind": spec.kind,
        "group": spec.group_id,
        "isPrimaryEntry": spec.is_primary_entry,
        "file": relative_file,
        "viewport": {"width": int(viewport_width), "height": int(viewport_height)},
        "deviceScaleFactor": DEVICE_SCALE_FACTOR,
        "scrollHeight": int(scroll_height),
        "cssHeight": int(height),
        "capturedAt": captured_at,
        "parts": [
            {
                "file": relative_file,
                "width": int(width),
                "height": int(height),
                "sha256": sha256_hex,
            }
        ],
    }


def build_groups(records: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group captured page IDs by sidebar navigation order, with home always first."""
    record_ids = {str(item["id"]) for item in records}
    by_group: dict[str, list[PageSpec]] = {}
    for spec in PAGE_SPECS:
        if spec.id in record_ids:
            by_group.setdefault(spec.group_id, []).append(spec)

    ordered_groups: list[dict[str, Any]] = []
    for _nav_key, group_id, group_title in NAV_ORDER:
        specs = by_group.get(group_id)
        if not specs:
            continue
        sorted_specs = sorted(specs, key=lambda s: (not s.is_primary_entry, PAGE_SPECS.index(s)))
        ordered_groups.append(
            {
                "id": group_id,
                "title": group_title,
                "ids": [spec.id for spec in sorted_specs],
            }
        )
    return {ROLE_ID: ordered_groups}


def build_pages_map(records: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build manifest['pages'] mapping id -> {kind, path}."""
    pages: dict[str, dict[str, Any]] = {}
    for record in records:
        ident = str(record["id"])
        spec = PAGE_SPECS_BY_ID[ident]
        path = [spec.group_title] if spec.group_title == spec.title else [spec.group_title, spec.title]
        pages[ident] = {"kind": spec.kind, "path": path}
    return pages


def build_manifest(
    records: Sequence[Mapping[str, Any]],
    *,
    generated_at: str,
    source_commit: str,
) -> dict[str, Any]:
    """Assemble the complete NFD manifest.json payload."""
    groups = build_groups(records)
    pages = build_pages_map(records)
    return {
        "schemaVersion": 3,
        "package": {
            "version": 1,
            "generatedAt": generated_at,
            "sourceCommit": source_commit,
        },
        "roles": [
            {
                "id": ROLE_ID,
                "title": ROLE_TITLE,
                "color": ROLE_COLOR,
                "viewport": ROLE_VIEWPORT,
            }
        ],
        "groups": groups,
        "pages": pages,
        "records": list(records),
        "unreadable": [],
    }


def build_steps_payload(
    transitions: Sequence[Mapping[str, Any]],
    *,
    generated_at: str,
) -> dict[str, Any]:
    """Build steps.json with registered navigation steps and click-verified entries."""
    steps: list[dict[str, Any]] = []
    verified: list[dict[str, Any]] = []
    for order, item in enumerate(transitions):
        kind = str(item.get("kind", "step"))
        if kind not in ("step", "back"):
            raise ValueError(f"unsupported step kind: {kind}")
        from_id = str(item["from"])
        to_id = str(item["to"])
        control = str(item["control"])
        one_way = bool(item.get("oneWay", False))
        steps.append(
            {
                "from": from_id,
                "to": to_id,
                "control": control,
                "kind": kind,
                "oneWay": one_way,
                "order": order,
            }
        )
        ok = bool(item.get("ok", True))
        verified.append(
            {
                "from": from_id,
                "to": to_id,
                "control": control,
                "kind": kind,
                "ok": ok,
                "verifiedAt": str(item.get("verifiedAt") or generated_at),
            }
        )
    return {
        "version": 1,
        "generatedAt": generated_at,
        "steps": steps,
        "verified": verified,
    }


def git_head_commit(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        commit = result.stdout.strip()
        if re.fullmatch(r"[0-9a-f]{40}", commit):
            return commit
    except (OSError, subprocess.SubprocessError):
        pass
    return "unreadable"


def parse_demo_project_output(stdout: str) -> dict[str, Any]:
    """Extract the trailing JSON object printed by create_demo_project.py."""
    decoder = json.JSONDecoder()
    for index in range(len(stdout) - 1, -1, -1):
        if stdout[index] != "{":
            continue
        try:
            value, end = decoder.raw_decode(stdout, index)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and not stdout[end:].strip():
            return value
    raise ValueError(f"create_demo_project.py did not emit a trailing JSON object: {stdout[-200:]!r}")


def prepare_demo_environment(tmp_root: Path) -> tuple[Path, Path, dict[str, Any]]:
    """Create a synthetic demo project and register it inside an isolated Studio state dir."""
    media_root = tmp_root / "media-root"
    state_dir = tmp_root / "studio-state"
    media_root.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "create_demo_project.py"),
        "--workspace-root",
        str(media_root),
        "--project-name",
        DEMO_PROJECT_NAME,
    ]
    env = {**os.environ, "LOCAL_MEDIA_ROOT": str(media_root)}
    proc = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True, timeout=60)
    demo_result = parse_demo_project_output(proc.stdout)
    project_dir = Path(str(demo_result["project_dir"]))

    store = ProjectStore(state_dir)
    project = store.create_project(
        title=DEMO_PROJECT_NAME,
        platform=DEMO_PROJECT_PLATFORM,
        local_workspace=str(project_dir),
    )
    return media_root, state_dir, project


def start_studio_server(
    *,
    state_dir: Path,
    media_root: Path,
    port: int,
) -> tuple[subprocess.Popen[str], str]:
    """Start scripts/launch_studio.py on the requested (or ephemeral) port and read back its URL."""
    env = {
        **os.environ,
        "LOCAL_MEDIA_ROOT": str(media_root),
        "PYTHONUNBUFFERED": "1",
    }
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "launch_studio.py"),
        "--state-dir",
        str(state_dir),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--no-browser",
    ]
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    assert proc.stdout is not None
    deadline = time.monotonic() + SERVER_START_TIMEOUT_SEC
    output_lines: list[str] = []
    try:
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                rest = proc.stdout.read()
                if rest:
                    output_lines.append(rest)
                raise RuntimeError(
                    f"Studio exited before ready (rc={proc.returncode}): {''.join(output_lines).strip()}"
                )
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.05)
                continue
            output_lines.append(line)
            url = parse_studio_ready_url(line)
            if url:
                return proc, url
        raise TimeoutError(
            f"Timed out waiting for Studio ready URL after {SERVER_START_TIMEOUT_SEC}s: {''.join(output_lines).strip()}"
        )
    except Exception:
        stop_process(proc)
        raise


def stop_process(proc: subprocess.Popen[Any] | None) -> None:
    """Terminate a spawned process group cleanly, escalating to SIGKILL if needed."""
    if proc is None:
        return
    if proc.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            proc.terminate()
    except ProcessLookupError:
        return
    except OSError:
        try:
            proc.terminate()
        except OSError:
            return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            else:
                proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def _resolve_browser_executable() -> str | None:
    env_browser = os.environ.get("VIDEO_RENDER_BROWSER", "").strip()
    if env_browser and Path(env_browser).is_file():
        return env_browser
    for base in _tool_search_roots():
        for rel in (
            ".tools/browsers/chromium_headless_shell-1228/chrome-headless-shell-linux64/chrome-headless-shell",
            ".tools/browsers/chromium-1228/chrome-linux64/chrome",
        ):
            candidate = base / rel
            if candidate.is_file():
                return str(candidate)
    return None


def _tool_search_roots() -> list[Path]:
    roots: list[Path] = [REPO_ROOT]
    venv_path = REPO_ROOT / ".venv"
    if venv_path.is_symlink():
        resolved_parent = venv_path.resolve().parent
        if resolved_parent not in roots:
            roots.append(resolved_parent)
    return roots


def _resolve_node_and_playwright() -> tuple[str, str]:
    node_bin = shutil.which("node")
    if not node_bin:
        for base in _tool_search_roots():
            candidate = base / ".tools/node/bin/node"
            if candidate.is_file():
                node_bin = str(candidate)
                break
    if not node_bin:
        raise RuntimeError("Node.js binary not found for Playwright capture fallback")

    candidates: list[str] = []
    for env_name in ("PLAYWRIGHT_MODULE", "VIDEO_RENDER_PLAYWRIGHT_MODULE"):
        value = os.environ.get(env_name, "").strip()
        if value:
            candidates.append(value)
    for base in _tool_search_roots():
        candidates.append(str(base / ".tools/browser-runtime/node_modules/playwright/index.mjs"))
        candidates.append(str(base / ".tools/browser-runtime/node_modules/playwright/index.js"))

    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            if path.name == "index.js" and path.with_name("index.mjs").is_file():
                return node_bin, str(path.with_name("index.mjs"))
            return node_bin, str(path)

    raise RuntimeError(
        "Neither Python playwright.sync_api nor Node.js Playwright module could be located"
    )


def _capture_via_python_playwright(
    base_url: str,
    raw_dir: Path,
    *,
    browser_executable: str | None,
) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

    raw_dir.mkdir(parents=True, exist_ok=True)
    captures: list[dict[str, Any]] = []
    transitions: list[dict[str, Any]] = []
    page_errors: list[str] = []
    failed_requests: list[str] = []

    def wait_view_ready(page: Any, expected_state_prefix: str, required_selector: str) -> None:
        page.wait_for_function(
            """([prefix, selector]) => {
              const main = document.querySelector('.main');
              const state = main ? (main.dataset.designState || '') : '';
              const root = document.querySelector('#review-screen');
              if (!root || !state.startsWith(prefix)) return false;
              const target = document.querySelector(selector);
              if (!target) return false;
              const text = (root.textContent || '').trim();
              if (!text) return false;
              const imgs = [...root.querySelectorAll('img')];
              return imgs.every(img => img.complete && img.naturalWidth > 0);
            }""",
            arg=[expected_state_prefix, required_selector],
            timeout=15000,
        )
        page.wait_for_load_state("networkidle", timeout=15000)
        page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
        page.wait_for_timeout(150)

        error_text = page.evaluate(
            """() => {
              const rootAlert = document.querySelector('#review-screen > p[role="alert"]');
              if (rootAlert && rootAlert.textContent.trim()) return rootAlert.textContent.trim();
              const toast = document.querySelector('#toast.error');
              if (toast && toast.textContent.trim()) return toast.textContent.trim();
              return '';
            }"""
        )
        if error_text:
            raise RuntimeError(f"Studio rendered error state: {error_text}")

    def capture_segmented(page: Any, page_id: str) -> dict[str, Any]:
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(80)
        total_height = int(
            page.evaluate(
                """() => {
                  const el = document.scrollingElement || document.documentElement;
                  return Math.max(window.innerHeight, el.scrollHeight, document.body.scrollHeight);
                }"""
            )
        )
        segments = compute_scroll_segments(total_height, VIEWPORT_HEIGHT)
        tile_meta: list[dict[str, Any]] = []
        for idx, segment in enumerate(segments):
            offset = segment["offset"]
            slice_height = segment["height"]
            actual_y = int(
                page.evaluate(
                    """(y) => { window.scrollTo(0, y); return Math.round(window.scrollY); }""",
                    offset,
                )
            )
            page.wait_for_timeout(100)
            source_y = offset - actual_y
            if source_y < 0 or source_y + slice_height > VIEWPORT_HEIGHT:
                raise RuntimeError(
                    f"{page_id}: uncovered scroll segment offset={offset}, actual_y={actual_y}, slice_height={slice_height}"
                )
            tile_path = raw_dir / f"{page_id}-tile-{idx}.png"
            page.screenshot(path=str(tile_path), full_page=False, animations="disabled")
            tile_meta.append(
                {
                    "file": str(tile_path),
                    "source_y": source_y,
                    "height": slice_height,
                    "dest_y": offset,
                }
            )
        page.evaluate("() => window.scrollTo(0, 0)")
        actual_hash = str(page.evaluate("() => '/' + (location.hash || '')"))
        return {
            "id": page_id,
            "scroll_height": total_height,
            "actual_route": actual_hash,
            "captured_at": utc_now_iso(),
            "tiles": tile_meta,
        }

    launch_kwargs: dict[str, Any] = {"headless": True}
    if browser_executable:
        launch_kwargs["executable_path"] = browser_executable

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**launch_kwargs)
        try:
            context = browser.new_context(
                viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
                device_scale_factor=DEVICE_SCALE_FACTOR,
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            page = context.new_page()
            page.on("pageerror", lambda err: page_errors.append(str(err)))
            page.on(
                "response",
                lambda resp: failed_requests.append(f"{resp.status} {resp.url}")
                if resp.status >= 400 and resp.url.startswith(base_url)
                else None,
            )

            page.goto(base_url + "/", wait_until="networkidle", timeout=20000)
            wait_view_ready(page, "home", '[data-design-id="R208-HOME-recent"] [data-piece]')
            captures.append(capture_segmented(page, "studio-home"))

            nav_targets = [
                ("studio-home", "studio-inbox", "inbox", "整理台", "inbox", '[data-design-id="R208-INBOX-empty"]'),
                ("studio-inbox", "studio-projects", "projects", "项目", "projects", '[data-design-id="R208-PROJECTS"]'),
                ("studio-projects", "studio-library", "library", "素材库", "library", '[data-design-id^="R208-LIBRARY"]'),
                ("studio-library", "studio-music", "music", "音乐库", "music", '[data-design-id="R208-MUSIC-import"]'),
                ("studio-music", "studio-settings", "settings", "设置与诊断", "settings-", '[data-design-id="R208-SETTINGS"]'),
            ]
            for from_id, to_id, nav_key, control, state_prefix, selector in nav_targets:
                page.locator(f'.nav [data-nav="{nav_key}"]').click()
                wait_view_ready(page, state_prefix, selector)
                transitions.append(
                    {
                        "from": from_id,
                        "to": to_id,
                        "control": control,
                        "kind": "step",
                        "oneWay": False,
                        "ok": True,
                        "verifiedAt": utc_now_iso(),
                    }
                )
                captures.append(capture_segmented(page, to_id))

            # Return to home and click into the demo project detail
            page.locator('.nav [data-nav="home"]').click()
            wait_view_ready(page, "home", '[data-design-id="R208-HOME-recent"] [data-piece]')
            transitions.append(
                {
                    "from": "studio-settings",
                    "to": "studio-home",
                    "control": "工作台",
                    "kind": "step",
                    "oneWay": False,
                    "ok": True,
                    "verifiedAt": utc_now_iso(),
                }
            )

            piece_card = page.locator('[data-design-id="R208-HOME-recent"] [data-piece]').first
            piece_title = (piece_card.locator("b").first.text_content() or "").strip() or "演示作品"
            piece_card.click()
            wait_view_ready(page, "piece-", '[data-design-id="R208-STEPS"]')
            transitions.append(
                {
                    "from": "studio-home",
                    "to": "studio-project-detail",
                    "control": piece_title,
                    "kind": "step",
                    "oneWay": False,
                    "ok": True,
                    "verifiedAt": utc_now_iso(),
                }
            )
            captures.append(capture_segmented(page, "studio-project-detail"))

            # Verify breadcrumb back to projects
            page.locator('#crumb button[data-go="projects"]').click()
            wait_view_ready(page, "projects", '[data-design-id="R208-PROJECTS"]')
            transitions.append(
                {
                    "from": "studio-project-detail",
                    "to": "studio-projects",
                    "control": "项目",
                    "kind": "back",
                    "oneWay": False,
                    "ok": True,
                    "verifiedAt": utc_now_iso(),
                }
            )
            context.close()
        finally:
            browser.close()

    if page_errors:
        raise RuntimeError(f"Page JS errors during capture: {'; '.join(page_errors)}")
    if failed_requests:
        raise RuntimeError(f"HTTP errors during capture: {'; '.join(failed_requests)}")

    return {"captures": captures, "transitions": transitions}




def _capture_via_node_playwright(
    base_url: str,
    raw_dir: Path,
    *,
    browser_executable: str | None,
) -> dict[str, Any]:
    node_bin, pw_module = _resolve_node_and_playwright()
    driver_path = raw_dir / "capture_driver.mjs"
    result_path = raw_dir / "capture_raw.json"
    raw_dir.mkdir(parents=True, exist_ok=True)
    driver_path.write_text(NODE_CAPTURE_DRIVER, encoding="utf-8")

    env = {
        **os.environ,
        "NFD_PW_MODULE": pw_module,
        "NFD_BROWSER_EXE": browser_executable or "",
        "NFD_BASE_URL": base_url,
        "NFD_RAW_DIR": str(raw_dir),
        "NFD_RESULT_PATH": str(result_path),
        "NFD_VIEWPORT_WIDTH": str(VIEWPORT_WIDTH),
        "NFD_VIEWPORT_HEIGHT": str(VIEWPORT_HEIGHT),
    }
    proc = subprocess.Popen(
        [node_bin, str(driver_path)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=CAPTURE_TIMEOUT_SEC)
    except Exception:
        stop_process(proc)
        raise
    if proc.returncode != 0:
        raise RuntimeError(
            f"Node Playwright capture failed (rc={proc.returncode}): {(stderr or stdout).strip()}"
        )
    return json.loads(result_path.read_text(encoding="utf-8"))


def run_browser_capture(base_url: str, raw_dir: Path) -> dict[str, Any]:
    """Capture Studio views using Python playwright.sync_api, falling back to repo Node Playwright."""
    browser_executable = _resolve_browser_executable()
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return _capture_via_node_playwright(
            base_url,
            raw_dir,
            browser_executable=browser_executable,
        )
    return _capture_via_python_playwright(
        base_url,
        raw_dir,
        browser_executable=browser_executable,
    )


def validate_output_directory(out_dir: Path) -> Path:
    resolved = out_dir.expanduser().resolve()
    parent = resolved.parent
    if not parent.exists() or not parent.is_dir():
        raise FileNotFoundError(f"output parent directory does not exist or is not a directory: {parent}")
    if resolved.exists() and not resolved.is_dir():
        raise NotADirectoryError(f"output path exists and is not a directory: {resolved}")
    return resolved


def write_package_from_raw(
    raw_data: Mapping[str, Any],
    *,
    out_dir: Path,
    source_commit: str,
) -> dict[str, Any]:
    """Stitch raw tiles and write screenshots/, manifest.json, and steps.json into out_dir."""
    out_dir.mkdir(parents=False, exist_ok=True)
    screenshots_dir = out_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for item in raw_data["captures"]:
        page_id = str(item["id"])
        spec = PAGE_SPECS_BY_ID[page_id]
        scroll_height = int(item["scroll_height"])
        tiles_input = [
            {
                "png_bytes": Path(str(tile["file"])).read_bytes(),
                "source_y": int(tile["source_y"]),
                "height": int(tile["height"]),
                "dest_y": int(tile["dest_y"]),
            }
            for tile in item["tiles"]
        ]
        stitched_png = stitch_vertical_tiles(
            tiles_input,
            width=VIEWPORT_WIDTH,
            total_height=scroll_height,
        )
        with Image.open(io.BytesIO(stitched_png)) as stitched_img:
            stitched_width, stitched_height = stitched_img.size

        relative_file = f"screenshots/{page_id}.png"
        dest_file = out_dir / relative_file
        dest_file.write_bytes(stitched_png)
        sha_hex = hashlib.sha256(stitched_png).hexdigest()

        records.append(
            build_manifest_record(
                spec,
                relative_file=relative_file,
                width=stitched_width,
                height=stitched_height,
                scroll_height=scroll_height,
                sha256_hex=sha_hex,
                captured_at=str(item["captured_at"]),
                actual_route=str(item.get("actual_route") or spec.route),
            )
        )

    generated_at = utc_now_iso()
    manifest = build_manifest(records, generated_at=generated_at, source_commit=source_commit)
    steps_payload = build_steps_payload(raw_data["transitions"], generated_at=generated_at)

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "steps.json").write_text(
        json.dumps(steps_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "out_dir": str(out_dir),
        "pages": [
            {
                "id": record["id"],
                "title": record["title"],
                "route": record["route"],
                "scrollHeight": record["scrollHeight"],
                "stitchedHeight": record["parts"][0]["height"],
                "width": record["parts"][0]["width"],
                "file": record["file"],
            }
            for record in records
        ],
        "step_count": len(steps_payload["steps"]),
        "verified_count": len(steps_payload["verified"]),
    }


def capture_gallery(*, out_dir: Path, port: int = 0) -> dict[str, Any]:
    """Run the full isolated demo Studio capture and always clean up temp state and processes."""
    if port < 0 or port > 65535:
        raise ValueError(f"port out of range: {port}")

    tmp_root = Path(tempfile.mkdtemp(prefix="pco-nfd-gallery-"))
    server_proc: subprocess.Popen[str] | None = None
    try:
        validated_out = validate_output_directory(out_dir)
        media_root, state_dir, _project = prepare_demo_environment(tmp_root)
        server_proc, base_url = start_studio_server(
            state_dir=state_dir,
            media_root=media_root,
            port=port,
        )
        raw_data = run_browser_capture(base_url, tmp_root / "raw-captures")
        summary = write_package_from_raw(
            raw_data,
            out_dir=validated_out,
            source_commit=git_head_commit(REPO_ROOT),
        )
        summary["studio_url"] = base_url
        return summary
    finally:
        stop_process(server_proc)
        shutil.rmtree(tmp_root, ignore_errors=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture an NFD-compatible screenshot package for Photo Content OS Studio."
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Destination directory for the screenshot package (parent directory must exist).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Loopback port for isolated Studio server (default: 0 for OS-assigned free port).",
    )
    args = parser.parse_args(argv)
    summary = capture_gallery(out_dir=args.out, port=args.port)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
