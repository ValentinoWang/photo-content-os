"""Package constants."""

from __future__ import annotations
from pathlib import Path
import re

# --- dreamverse_bridge.py ---
PROVIDERS_ROOT = Path(__file__).resolve().parents[2] / "integrations/dreamverse"
DEFAULT_PROVIDER = "wanxiang"
PROVIDERS = ("wanxiang", "seedance")
DEFAULT_WAN_PROMPT_EXTEND = True
DEFAULT_WAN_NEGATIVE_PROMPT = "品牌标识、logo、商标、水印、文字"
MAX_WAN_NEGATIVE_PROMPT_CHARS = 500
SHOT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", re.ASCII)
TASK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", re.ASCII)
DIGEST = re.compile(r"[a-f0-9]{64}", re.ASCII)
