#!/usr/bin/env python3
"""Diagnose local Photo Content OS prerequisites without changing the machine."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import plistlib
import subprocess
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from runtime_paths import MINIMUM_PYTHON, platform_contract_name, repository_root, runtime_python, supported_python

_SYSTEM_ROOT = Path(__file__).resolve().parents[1]
if str(_SYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(_SYSTEM_ROOT))
from studio.chatcut_mcp import LocalMcpSession, McpError, read_registration
from edit_backends.kdenlive_render import melt_executable
from edit_backends.otio_kdenlive import kdenlive_executable

UPSTREAM_OPENCLAW_MEDIA_SHA = "f0460b4ce84ca7efc7eb6d2f05c77d20eef68aaf"
UPSTREAM_DEVICE_PLATFORMS = {"macos"}


class CheckState(str, Enum):
    READY = "ready"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


@dataclass(frozen=True)
class Check:
    id: str
    ok: bool
    required: bool
    summary: str
    action: str = ""
    state: str | CheckState | None = None

    def __post_init__(self) -> None:
        if type(self.ok) is not bool or type(self.required) is not bool:
            raise ValueError("check_boolean_invalid")
        if self.state is None:
            resolved = CheckState.READY if self.ok else CheckState.ERROR
        else:
            try:
                resolved = self.state if isinstance(self.state, CheckState) else CheckState(self.state)
            except (TypeError, ValueError) as exc:
                raise ValueError("check_state_invalid") from exc
        if self.ok is not (resolved is CheckState.READY):
            raise ValueError("check_state_inconsistent")
        object.__setattr__(self, "state", resolved.value)


def writable_directory(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, delete=True):
            pass
        return True
    except OSError:
        return False


def probe_app(path: Path) -> dict[str, object]:
    if not path.is_dir():
        return {"installed": False, "path": str(path), "version": None}
    try:
        with (path / "Contents/Info.plist").open("rb") as handle:
            info = plistlib.load(handle)
        version = info.get("CFBundleShortVersionString") or info.get("CFBundleVersion")
        return {"installed": True, "path": str(path), "version": version}
    except (OSError, ValueError, plistlib.InvalidFileException):
        return {"installed": True, "path": str(path), "version": None}


def probe_editing_tools(*, applications: Path = Path("/Applications"), session_factory=LocalMcpSession,
                        registration_reader=read_registration) -> dict[str, object]:
    """Installation checks and read-only MCP handshake; no draft traversal."""
    chatcut = probe_app(applications / "ChatCut.app")
    chatcut.update(status="unknown", reason="connection_not_verified", mcp_registered=None, connection_verified=False)
    try:
        config = registration_reader()
        chatcut["mcp_registered"] = True
        with session_factory(config) as session:
            tools = session.list_tools()
        chatcut.update(status="online", reason="mcp_handshake_and_tools_verified", connection_verified=True,
                       tool_count=len(tools))
    except McpError as exc:
        reason = str(exc)
        if reason in {"mcp_not_registered", "mcp_disabled"}:
            chatcut.update(status="unavailable", reason=reason, mcp_registered=False)
        else:
            chatcut.update(reason="mcp_handshake_failed")
    except (OSError, ValueError, subprocess.SubprocessError):
        chatcut.update(reason="mcp_probe_failed")
    if chatcut["installed"] is False:
        chatcut.update(status="unavailable", reason="app_missing", connection_verified=False)
    elif chatcut["version"] is None and chatcut["status"] == "online":
        chatcut.update(status="unknown", reason="app_version_unknown")
    kdenlive = probe_app(applications / "kdenlive.app")
    kdenlive.update(status="unavailable", reason="melt_unavailable", executable=kdenlive_executable(),
                    melt_path=melt_executable(), melt_version=None)
    if kdenlive["melt_path"]:
        try:
            result = subprocess.run([kdenlive["melt_path"], "--version"], capture_output=True, text=True, timeout=5, check=True)
            version = (result.stdout or result.stderr).strip()
            if not version:
                raise ValueError()
            kdenlive.update(melt_version=version, status="online" if kdenlive["executable"] and kdenlive["version"] else "unknown",
                            reason="versions_verified" if kdenlive["executable"] and kdenlive["version"] else "kdenlive_version_unknown")
        except (OSError, ValueError, subprocess.SubprocessError):
            kdenlive.update(status="unknown", reason="melt_version_probe_failed")
    jianying = probe_app(applications / "VideoFusion-macOS.app")
    jianying.update(status="online" if jianying["installed"] and jianying["version"] else ("unknown" if jianying["installed"] else "unavailable"),
                    reason="installation_and_version_only" if jianying["version"] else "app_missing_or_version_unknown",
                    scope="app_and_version_only")
    return {"chatcut": chatcut, "kdenlive": kdenlive, "jianying": jianying}


def collect_checks(repo: Path | None = None) -> tuple[list[Check], dict[str, object]]:
    root = (repo or repository_root()).resolve()
    platform_name = platform_contract_name()
    provider = (os.getenv("OPENCLAW_CREATIVE_PROVIDER") or "codex_cli").strip().lower()
    checks = [
        Check(
            "python_version",
            supported_python(),
            True,
            f"Python {sys.version.split()[0]}（最低 {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]}）",
            "安装 Python 3.11 或更新版本。",
        ),
        Check("repository_write", writable_directory(root / ".content-os-doctor"), True, "仓库工作目录可写", "检查目录权限。"),
        Check("ffmpeg", shutil.which("ffmpeg") is not None, True, "ffmpeg 可用于关键帧、音频与预览", "安装 ffmpeg 并加入 PATH。"),
        Check("ffprobe", shutil.which("ffprobe") is not None, True, "ffprobe 可读取媒体元数据", "安装 ffmpeg/ffprobe 并加入 PATH。"),
    ]
    try:
        (root / ".content-os-doctor").rmdir()
    except OSError:
        pass

    if provider in {"codex", "codex_cli", "codex-cli"}:
        provider_available = shutil.which(os.getenv("OPENCLAW_CODEX_BIN") or "codex") is not None
        checks.append(
            Check(
                "creative_provider",
                provider_available,
                False,
                "Codex CLI 可用",
                "安装 Codex CLI，或切换 OPENCLAW_CREATIVE_PROVIDER=openai_api。",
                state=CheckState.READY if provider_available else CheckState.UNAVAILABLE,
            )
        )
    elif provider in {"openai", "openai_api", "openai-api"}:
        key_available = bool(os.getenv("OPENAI_API_KEY"))
        package_available = importlib.util.find_spec("openai") is not None
        checks.append(
            Check(
                "openai_key",
                key_available,
                False,
                "OPENAI_API_KEY 已配置",
                "设置 OPENAI_API_KEY。",
                state=CheckState.READY if key_available else CheckState.UNAVAILABLE,
            )
        )
        checks.append(
            Check(
                "openai_package",
                package_available,
                False,
                "openai Python 包可用",
                "在固定运行时安装 openai 包。",
                state=CheckState.READY if package_available else CheckState.UNAVAILABLE,
            )
        )
    else:
        checks.append(Check("creative_provider", False, False, f"不支持的 provider：{provider}", "使用 codex_cli 或 openai_api。"))

    upstream_supported = platform_name in UPSTREAM_DEVICE_PLATFORMS
    checks.append(
        Check(
            "openclaw_cloud_pairing",
            upstream_supported,
            False,
            f"上游 {UPSTREAM_OPENCLAW_MEDIA_SHA[:12]} 的设备合同支持：{', '.join(sorted(UPSTREAM_DEVICE_PLATFORMS))}",
            "Windows/Linux 可使用本地桌面与核心流水线；云端配对需上游合同先正式加入对应平台。",
            state=CheckState.READY if upstream_supported else CheckState.UNSUPPORTED,
        )
    )
    runtime = runtime_python(root)
    metadata = {
        "schema_version": "content_os_doctor_v2",
        "repository_root": str(root),
        "platform": platform_name,
        "runtime_python": str(runtime),
        "runtime_exists": runtime.is_file(),
        "creative_provider": provider,
        "upstream_openclaw_media_sha": UPSTREAM_OPENCLAW_MEDIA_SHA,
        "cloud_pairing_supported": upstream_supported,
        "local_core_supported": platform_name in {"macos", "windows", "linux"},
        "tools": probe_editing_tools(),
    }
    return checks, metadata


def diagnosis_status(checks: list[Check], *, allow_offline: bool = False) -> str:
    for check in checks:
        if check.ok:
            continue
        if check.required:
            return "blocked"
        if check.state != CheckState.UNSUPPORTED.value and not allow_offline:
            return "blocked"
    return "ready"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument("--allow-offline", action="store_true", help="模型 provider 不可用时仍允许通过本地核心检查")
    args = parser.parse_args()
    checks, metadata = collect_checks()
    required_failed = [check for check in checks if check.required and not check.ok]
    status = diagnosis_status(checks, allow_offline=args.allow_offline)
    payload = {
        **metadata,
        "status": status,
        "local_features_available": not required_failed,
        "upstream_login_required_for_local_features": False,
        "checks": [asdict(check) for check in checks],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Photo Content OS doctor: {status}")
        for name, tool in metadata["tools"].items():
            print(f"{name}: {tool['status']} ({tool['reason']})")
        for check in checks:
            marker = "✓" if check.ok else ("✗" if check.required else "!")
            print(f"{marker} {check.id}: {check.summary}")
            if not check.ok and check.action:
                print(f"  处理：{check.action}")
    return 0 if status == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
