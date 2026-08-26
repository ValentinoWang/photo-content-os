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
from dataclasses import asdict, dataclass
from pathlib import Path

from runtime_paths import MINIMUM_PYTHON, platform_contract_name, repository_root, runtime_python, supported_python

UPSTREAM_OPENCLAW_MEDIA_SHA = "f0460b4ce84ca7efc7eb6d2f05c77d20eef68aaf"
UPSTREAM_DEVICE_PLATFORMS = {"macos"}


@dataclass(frozen=True)
class Check:
    id: str
    ok: bool
    required: bool
    summary: str
    action: str = ""


def writable_directory(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path, delete=True):
            pass
        return True
    except OSError:
        return False


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
        checks.append(Check("creative_provider", shutil.which(os.getenv("OPENCLAW_CODEX_BIN") or "codex") is not None, False, "Codex CLI 可用", "安装 Codex CLI，或切换 OPENCLAW_CREATIVE_PROVIDER=openai_api。"))
    elif provider in {"openai", "openai_api", "openai-api"}:
        checks.append(Check("openai_key", bool(os.getenv("OPENAI_API_KEY")), False, "OPENAI_API_KEY 已配置", "设置 OPENAI_API_KEY。"))
        checks.append(Check("openai_package", importlib.util.find_spec("openai") is not None, False, "openai Python 包可用", "在固定运行时安装 openai 包。"))
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
        )
    )
    runtime = runtime_python(root)
    metadata = {
        "schema_version": "content_os_doctor_v1",
        "repository_root": str(root),
        "platform": platform_name,
        "runtime_python": str(runtime),
        "runtime_exists": runtime.is_file(),
        "creative_provider": provider,
        "upstream_openclaw_media_sha": UPSTREAM_OPENCLAW_MEDIA_SHA,
        "cloud_pairing_supported": upstream_supported,
        "local_core_supported": platform_name in {"macos", "windows", "linux"},
    }
    return checks, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument("--allow-offline", action="store_true", help="模型 provider 不可用时仍允许通过本地核心检查")
    args = parser.parse_args()
    checks, metadata = collect_checks()
    required_failed = [check for check in checks if check.required and not check.ok]
    optional_failed = [check for check in checks if not check.required and not check.ok]
    status = "ready" if not required_failed and (args.allow_offline or not optional_failed) else "blocked"
    payload = {**metadata, "status": status, "checks": [asdict(check) for check in checks]}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Photo Content OS doctor: {status}")
        for check in checks:
            marker = "✓" if check.ok else ("✗" if check.required else "!")
            print(f"{marker} {check.id}: {check.summary}")
            if not check.ok and check.action:
                print(f"  处理：{check.action}")
    return 0 if status == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
