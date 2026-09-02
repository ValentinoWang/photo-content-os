#!/usr/bin/env python3
"""Build the strict OpenClaw Media 45-item implementation SSOT."""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path


BUNDLE = Path(__file__).resolve().parent
ROOT = BUNDLE.parents[2]
sys.path.insert(0, str(ROOT / ".agents/skills/report-to-ssot-development-paths/scripts"))
from normative_artifact import inventory_html
SOURCE_DIR = ROOT / "agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist"
CHECKLIST = SOURCE_DIR / "openclaw-dev-checklist.html"
PROTOTYPE = SOURCE_DIR / "openclaw-media-ui-prototype.html"
BASELINE = "2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35"
CHECKLIST_BLOB = "6202f61978a7bc94e01e3d50e80698a32856746b"
PROTOTYPE_BLOB = "cc44bc4065310264b7bf398680fc6cb0750fd163"
CHECKLIST_SHA = "73554eb91c80c8a85b267f15dd07e7f89c06eeea27a907c254f00c35813b9eeb"
PROTOTYPE_SHA = "aae220ef70cf7aeceefaf9a35ab4ee43d85366e92f2831513b53c36023a49cc8"
SSOT_REL = "agents-results/2026-09-02/openclaw-media-full-checklist-implementation/ssot-development-paths.md"
# Strict source requirements are the sole source registry.  The historical
# visual-fidelity contract was retired with schema v2 and must never be emitted
# or referenced by regenerated nodes.
VISUAL_REF = ".ssot/source-requirements.json"
WORKBENCH_REL = "99_System_OpenClaw/visual-workbench.html"
WORKBENCH_CONTRACT_REL = "99_System_OpenClaw/visual-workbench.json"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2))


class ChecklistParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.section = ""
        self.current_tag = ""
        self.article: dict[str, object] | None = None
        self.items: list[dict[str, str]] = []
        self.title_depth = 0
        self.action_row_depth = 0
        self.action_value_depth = 0

    @staticmethod
    def _join_inline(parts: list[object]) -> str:
        value = " ".join(str(part) for part in parts)
        value = re.sub(r"\s+([，。；：！？、）])", r"\1", value)
        value = re.sub(r"（\s+", "（", value)
        return value.strip()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.current_tag = tag
        attributes = dict(attrs)
        if tag == "article":
            self.article = {
                "id": "",
                "source_status": str(attributes.get("data-status") or ""),
                "texts": [],
                "title_parts": [],
                "action_parts": [],
            }
            self.title_depth = 0
            self.action_row_depth = 0
            self.action_value_depth = 0
        elif tag == "input" and self.article is not None:
            self.article["id"] = str(attributes.get("data-k") or "").upper()

        if self.article is None:
            return

        class_names = set(str(attributes.get("class") or "").split())
        if self.title_depth:
            self.title_depth += 1
        elif tag == "span" and "item-title" in class_names:
            self.title_depth = 1

        if self.action_row_depth:
            self.action_row_depth += 1
        elif tag == "div" and "row--do" in class_names:
            self.action_row_depth = 1

        if self.action_value_depth:
            self.action_value_depth += 1
        elif self.action_row_depth and tag == "span" and "row-v" in class_names:
            self.action_value_depth = 1

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if not value:
            return
        if self.article is not None:
            texts = self.article["texts"]
            assert isinstance(texts, list)
            texts.append(value)
            if self.title_depth:
                title_parts = self.article["title_parts"]
                assert isinstance(title_parts, list)
                title_parts.append(value)
            if self.action_value_depth:
                action_parts = self.article["action_parts"]
                assert isinstance(action_parts, list)
                action_parts.append(value)
        elif self.current_tag == "h2":
            self.section = value

    def handle_endtag(self, tag: str) -> None:
        if tag == "article" and self.article is not None:
            texts = self.article["texts"]
            title_parts = self.article["title_parts"]
            action_parts = self.article["action_parts"]
            assert isinstance(texts, list)
            assert isinstance(title_parts, list)
            assert isinstance(action_parts, list)
            item_id = str(self.article["id"])
            if item_id:
                full_text = " | ".join(str(value) for value in texts)
                title = self._join_inline(title_parts)
                action_text = self._join_inline(action_parts)
                if not title or not action_text:
                    raise SystemExit(f"checklist item {item_id} is missing a title or action requirement")
                self.items.append(
                    {
                        "id": item_id,
                        "section": self.section,
                        "source_status": str(self.article["source_status"]),
                        "title": title,
                        "action_text": action_text,
                        "source_text": full_text,
                    }
                )
            self.article = None
            self.title_depth = 0
            self.action_row_depth = 0
            self.action_value_depth = 0
        else:
            if self.title_depth:
                self.title_depth -= 1
            if self.action_value_depth:
                self.action_value_depth -= 1
            if self.action_row_depth:
                self.action_row_depth -= 1
        self.current_tag = ""


def parse_items() -> list[dict[str, str]]:
    parser = ChecklistParser()
    parser.feed(CHECKLIST.read_text(encoding="utf-8"))
    expected = {
        "D1", "D2", "D3", "A1", "A2",
        *{f"H{i}" for i in range(1, 5)},
        *{f"I{i}" for i in range(1, 6)},
        *{f"L{i}" for i in range(1, 6)},
        *{f"P{i}" for i in range(1, 7)},
        *{f"S{i}" for i in range(1, 6)},
        *{f"C{i}" for i in range(1, 4)},
        *{f"T{i}" for i in range(1, 7)},
        *{f"K{i}" for i in range(1, 7)},
    }
    actual = {item["id"] for item in parser.items}
    if len(parser.items) != 45 or actual != expected:
        raise SystemExit(f"checklist item mismatch: count={len(parser.items)} missing={sorted(expected - actual)} extra={sorted(actual - expected)}")
    if sha256_file(CHECKLIST) != CHECKLIST_SHA or sha256_file(PROTOTYPE) != PROTOTYPE_SHA:
        raise SystemExit("source HTML identity drifted; update the declared current SHA-256 before regenerating")
    return parser.items


ITEMS = parse_items()
ITEM_BY_ID = {item["id"]: item for item in ITEMS}
ITEM_IDS = [item["id"] for item in ITEMS]

SURFACES = {
    "SURF-LOGIN": ("登录", "/login"),
    "SURF-SETUP": ("安装向导", "/setup"),
    "SURF-DASHBOARD": ("工作台", "/app/home"),
    "SURF-ORGANIZER": ("整理台", "/app/inbox"),
    "SURF-LIBRARY": ("素材库", "/app/library"),
    "SURF-PROJECT": ("项目", "/app/project/:projectId"),
    "SURF-SETTINGS": ("设置与诊断", "/app/settings"),
    "SURF-CLOUD": ("网页中台", "/cloud/tasks"),
}

ITEM_SURFACE = {
    "D1": "SURF-ORGANIZER", "D2": "SURF-LIBRARY", "D3": "SURF-SETTINGS",
    "A1": "SURF-LOGIN", "A2": "SURF-SETUP",
    **{f"H{i}": "SURF-DASHBOARD" for i in range(1, 5)},
    **{f"I{i}": "SURF-ORGANIZER" for i in range(1, 6)},
    **{f"L{i}": "SURF-LIBRARY" for i in range(1, 6)},
    **{f"P{i}": "SURF-PROJECT" for i in range(1, 7)},
    **{f"S{i}": "SURF-SETTINGS" for i in range(1, 6)},
    **{f"C{i}": "SURF-CLOUD" for i in range(1, 4)},
    "T1": "SURF-ORGANIZER", "T2": "SURF-LIBRARY", "T3": "SURF-SETTINGS",
    "T4": "SURF-SETTINGS", "T5": "SURF-PROJECT", "T6": "SURF-PROJECT",
    **{f"K{i}": "SURF-PROJECT" for i in range(1, 7)},
}

RELEASE_ITEMS = {
    "R1": ["D1", "D2", "D3", "T1", "T3", "T5"],
    "R2": [f"I{i}" for i in range(1, 6)],
    "R3": [*[f"L{i}" for i in range(1, 6)], "T2"],
    "R4": [*[f"P{i}" for i in range(1, 7)], "T6"],
    "R5": [*[f"S{i}" for i in range(1, 6)], *[f"C{i}" for i in range(1, 4)], "T4"],
    "R6": ["A1", "A2", *[f"H{i}" for i in range(1, 5)]],
    "R7": [f"K{i}" for i in range(1, 7)],
    "R8": [],
}
ITEM_RELEASE = {item_id: release_id for release_id, ids in RELEASE_ITEMS.items() for item_id in ids}
if set(ITEM_RELEASE) != set(ITEM_IDS):
    raise SystemExit("release mapping must cover all 45 checklist items exactly once")

RELEASE_META = {
    "R1": ("安全、契约和已接受决定", "冻结安全边界与共用契约，先偿还会放大破坏半径的债。"),
    "R2": ("整理台", "用户可把散素材自动分批、复核来源和落点，并由本人决定是否进入系统回收站。"),
    "R3": ("素材库与归档", "用户可按结构化索引检索复用素材，并明确每个物理位置和生命周期状态。"),
    "R4": ("项目与结构化时间线", "用户可查看并编辑唯一权威剪辑方案，输出真实支持的交接产物。"),
    "R5": ("设置、诊断与网页中台", "用户可配置模型、预算、位置并理解诊断和上游任务状态。"),
    "R6": ("登录、安装与工作台", "用户可选择配对上游身份、完成安装并从工作台进入最近工作。"),
    "R7": ("既有 Studio 能力迁移", "新界面保留锁定、版本、失效传播、参考资料、复盘和文档阶段。"),
    "R8": ("九屏共享入口和最终整合", "九个界面共享一套导航、状态、安全和验收边界。"),
}

PD_META = {
    "PD": ("decision.scope.full-checklist", "完整覆盖 HTML 的 45 项要求，不以降级或删除条目换取完成。"),
    "PD1": ("decision.organizer.auto-batching", "自动分事件、分批完整实现，先预览确认再执行迁移。"),
    "PD2": ("decision.library.structured-index", "新增结构化素材索引，Markdown 继续供人阅读。"),
    "PD3": ("decision.deletion.system-trash", "只生成删除建议；用户选择并二次确认后进入当前系统回收站，禁止永久删除。"),
    "PD4": ("decision.creative-model.user-config", "创意模型由用户配置，支持 Codex/OpenAI、Claude/Anthropic、DeepSeek 和兼容接口。"),
    "PD5": ("decision.chatcut.desktop-mcp", "ChatCut 只通过 Desktop 本地 MCP 接入，实时探测且主动连接后才显示。"),
    "PD6": ("decision.archive.location-lifecycle", "生命周期和物理位置同时配置，每个位置独立保存清单、校验值与回读状态。"),
    "PD7": ("decision.identity.optional-upstream", "优先复用上游中台身份；配对可选，未登录或平台不支持时本地功能保持完整。"),
    "PD8": ("decision.edl.machine-authority", "结构化 06_edit_decision_list.json 是机器执行唯一剪辑方案权威。"),
    "PD9": ("decision.jianying.historical-only", "剪映脚本仅作历史材料，自动化不得修改生产剪映草稿。"),
}

DECISION_REFS = {
    "D1": ["PD", "PD1"], "D2": ["PD", "PD2"], "D3": ["PD"],
    "A1": ["PD", "PD7"], "A2": ["PD", "PD6", "PD7", "PD9"],
    "H1": ["PD"], "H2": ["PD", "PD4", "PD5", "PD7"], "H3": ["PD", "PD2"], "H4": ["PD"],
    "I1": ["PD", "PD1"], "I2": ["PD", "PD1"], "I3": ["PD", "PD1"],
    "I4": ["PD", "PD3"], "I5": ["PD", "PD3"],
    "L1": ["PD", "PD2"], "L2": ["PD", "PD2"], "L3": ["PD", "PD6"],
    "L4": ["PD", "PD6"], "L5": ["PD", "PD2"],
    "P1": ["PD", "PD8"], "P2": ["PD", "PD8"], "P3": ["PD", "PD8"],
    "P4": ["PD", "PD8"], "P5": ["PD", "PD5", "PD8", "PD9"], "P6": ["PD", "PD9"],
    "S1": ["PD"], "S2": ["PD", "PD6"], "S3": ["PD"], "S4": ["PD", "PD7"], "S5": ["PD", "PD4"],
    "C1": ["PD", "PD7"], "C2": ["PD", "PD7"], "C3": ["PD", "PD7"],
    "T1": ["PD"], "T2": ["PD", "PD2"], "T3": ["PD"], "T4": ["PD"], "T5": ["PD"], "T6": ["PD", "PD9"],
    **{f"K{i}": ["PD", "PD8"] for i in range(1, 7)},
}

ITEM_DEPS = {
    "T1": ["F", "PD"], "T2": ["F", "PD", "PD2"], "T3": ["F", "PD"],
    "T4": ["F", "PD"], "T5": ["F", "PD"], "T6": ["F", "PD", "PD9"],
    "D1": ["F", "PD", "PD1", "T1"], "D2": ["F", "PD", "PD2", "T2"],
    "D3": ["F", "PD", "TRD"],
    "I1": ["F", "D1", "T5"], "I2": ["F", "PD1"], "I3": ["F", "PD1", "T2"],
    "I4": ["F", "PD3", "T3", "T5"], "I5": ["F", "PD3", "I4", "T5"],
    "L1": ["F", "D2"], "L2": ["F", "D2"], "L3": ["F", "PD6"],
    "L4": ["F", "PD6"], "L5": ["F", "D2", "T5"],
    "P1": ["F", "PD8"], "P2": ["F", "PD8"], "P3": ["F", "PD8", "P1", "P2", "T5"],
    "P4": ["F", "PD8"], "P5": ["F", "PD5", "PD8", "PD9", "P2", "T5"], "P6": ["F", "PD9", "T6"],
    "S1": ["F", "T4", "T5"], "S2": ["F", "PD6", "T5"], "S3": ["F", "T3"],
    "S4": ["F", "PD7"], "S5": ["F", "PD4", "T5"],
    "C1": ["F", "PD7"], "C2": ["F", "PD7", "C1"], "C3": ["F", "PD7", "C2"],
    "A1": ["F", "PD7", "T5"], "A2": ["F", "PD6", "PD7", "PD9", "S2", "S3", "T5"],
    "H1": ["F"], "H2": ["F", "PD4", "PD5", "PD7", "S3", "S5"],
    "H3": ["F", "D2"], "H4": ["F"],
    "K1": ["F", "PD8"], "K2": ["F", "PD8"], "K3": ["F", "PD8"],
    "K4": ["F", "PD8"], "K5": ["F", "PD8"], "K6": ["F", "PD8"],
}

OUTCOMES = {
    "D1": "从媒体清单生成可解释、可确认且不可拆分实况照片组的事件批次计划；未确认或输入漂移时禁止迁移。",
    "D2": "以稳定素材身份原子维护结构化索引，支持分类、标签、用途、计数与详情查询，同时保留 Markdown 卡片。",
    "D3": "按已接受的 DashScope 默认、本机 FunASR 失败兜底与音频发送前明示策略统一所有入口，并以音频夹具验证。",
    "A1": "使用上游中台身份完成邮箱、Apple 或微信登录；配对始终可选，未登录、撤销或平台不支持时本地能力不退化。",
    "A2": "向导可重入地完成位置、运行环境、编辑器、账号与设备四步，并能从失败处恢复。",
    "H2": "聚合数据中台、Codex、ChatCut Desktop 本地 MCP 与本机引擎的实时状态；单项失败不拖垮整体。",
    "I5": "用户勾选建议并二次确认后才移入当前操作系统回收站；回读失败必须阻断，界面不得承诺固定保留天数。",
    "L3": "同时展示生命周期和每个物理位置的真实回读状态，逻辑登记不得冒充副本已存在。",
    "P3": "结构化时间线为主视图，同时保留文本说明与受约束的选区修改，不形成第二份机器执行权威。",
    "P5": "内建只显示 handoff_pack 与 otio_kdenlive；ChatCut 仅在本地 MCP 实时探测和主动连接后成为可选去向。",
    "P6": "统一表述为剪映生产路线已停止维护，删除没有证据的“草稿加密”理由。",
    "S4": "Windows 与 Linux 将上游配对显示为“不支持”而不是“配置失败”，并明确本地核心能力仍可用。",
    "S5": "持久化用户选择的提供方、模型、端点、思考强度和密钥引用，并确保真实执行链消费该配置。",
    "T5": "所有新增写接口沿用 loopback、同源、CSRF 和明确 revision 域的乐观并发控制，跨端口 Origin 必须拒绝。",
    "T6": "七个剪映脚本要么物理归档，要么逐项声明历史且不维护，并使文档、能力清单和持续集成保持一致。",
    "K6": "Brief 与脚本作为独立版本化阶段保留，并建立到项目文件和素材匹配输入的单向权威编译。",
}

BASELINE_STATUS = {
    "D1": "PARTIAL", "D2": "PARTIAL", "D3": "PARTIAL",
    "A1": "PARTIAL", "A2": "PARTIAL",
    "H1": "PARTIAL", "H2": "PARTIAL", "H3": "NOT_READY", "H4": "NOT_READY",
    "I1": "NOT_READY", "I2": "PARTIAL", "I3": "PARTIAL", "I4": "PARTIAL", "I5": "PARTIAL_PLATFORM",
    "L1": "NOT_READY", "L2": "NOT_READY", "L3": "PARTIAL", "L4": "PARTIAL", "L5": "NOT_READY",
    "P1": "PARTIAL", "P2": "NOT_READY", "P3": "NOT_USER_ACCESSIBLE", "P4": "PARTIAL", "P5": "PARTIAL", "P6": "POLICY_ONLY",
    "S1": "PARTIAL", "S2": "PARTIAL", "S3": "PARTIAL", "S4": "PARTIAL", "S5": "PARTIAL",
    "C1": "PARTIAL", "C2": "NOT_READY", "C3": "PARTIAL",
    "T1": "PARTIAL", "T2": "NOT_READY", "T3": "PARTIAL", "T4": "NOT_READY", "T5": "PARTIAL", "T6": "PARTIAL",
    **{f"K{i}": "PARTIAL" for i in range(1, 7)},
}

EVIDENCE_LOOKUPS = {
    "D1": ("99_System_OpenClaw/scripts/01_scan_media_manifest.py", "gps_latitude"),
    "D2": ("99_System_OpenClaw/scripts/15_register_reusable_asset.py", "build_card"),
    "D3": ("99_System_OpenClaw/scripts/03_transcribe_audio.py", "build_provider"),
    "A1": ("99_System_OpenClaw/desktop/upstream_session.py", "local_features_available"),
    "A2": ("99_System_OpenClaw/scripts/41_setup_dev_environment.sh", "state-dir|doctor|venv"),
    "H1": ("99_System_OpenClaw/desktop/project_store.py", "list_projects"),
    "H2": ("99_System_OpenClaw/desktop/server.py", "api/health"),
    "H3": ("99_System_OpenClaw/scripts/15_register_reusable_asset.py", "Reusable_"),
    "H4": ("99_System_OpenClaw/desktop/project_store.py", "record_publishing"),
    "I1": ("99_System_OpenClaw/scripts/34_ensure_project_from_inbox_batch.py", "def main|def ensure"),
    "I2": ("99_System_OpenClaw/scripts/01_scan_media_manifest.py", "device"),
    "I3": ("99_System_OpenClaw/scripts/12_select_repeat_photo_groups.py", "create_plan"),
    "I4": ("99_System_OpenClaw/scripts/media_delete_recommendations.py", "recommend"),
    "I5": ("99_System_OpenClaw/desktop/media_trash_flow.py", "platform"),
    "L1": ("99_System_OpenClaw/scripts/15_register_reusable_asset.py", "build_card"),
    "L2": ("99_System_OpenClaw/scripts/15_register_reusable_asset.py", "tags"),
    "L3": ("99_System_OpenClaw/scripts/45_archive_project.py", "index_card"),
    "L4": ("99_System_OpenClaw/scripts/45_archive_project.py", "restore_from_manifest"),
    "L5": ("99_System_OpenClaw/scripts/17_match_materials_to_brief.py", "def main"),
    "P1": ("99_System_OpenClaw/desktop/edl_bridge.py", "load|read"),
    "P2": ("99_System_OpenClaw/scripts/edit_backends/otio_kdenlive.py", "TimelineClip"),
    "P3": ("99_System_OpenClaw/desktop/static/app.js", "documentView"),
    "P4": ("99_System_OpenClaw/schemas/edit_decision_list.schema.json", "missing_materials"),
    "P5": ("99_System_OpenClaw/scripts/validate_content_os_task.py", "SUPPORTED_EDITOR_BACKENDS"),
    "P6": ("99_System_OpenClaw/docs/05_剪映与HyperFrames.md", "不再|历史"),
    "S1": ("99_System_OpenClaw/scripts/analysis_tiering.py", "TierBudget"),
    "S2": ("99_System_OpenClaw/desktop/archive_location_config.py", "location"),
    "S3": ("99_System_OpenClaw/scripts/43_content_os_doctor.py", "collect_checks"),
    "S4": ("99_System_OpenClaw/desktop/upstream_session.py", "unavailable|unsupported"),
    "S5": ("99_System_OpenClaw/desktop/model_provider_config.py", "provider"),
    "C1": ("99_System_OpenClaw/schemas/openclaw_media_contract_snapshot.json", "pipelines"),
    "C2": ("99_System_OpenClaw/schemas/openclaw_media_contract_snapshot.json", "job_states"),
    "C3": ("99_System_OpenClaw/schemas/openclaw_media_contract_snapshot.json", "commit|digest"),
    "T1": ("99_System_OpenClaw/tests/test_promote_inbox_batch_to_project.py", "def test"),
    "T2": ("99_System_OpenClaw/scripts/12_select_repeat_photo_groups.py", "def main"),
    "T3": ("99_System_OpenClaw/tests/test_media_manifest_contract.py", "def test"),
    "T4": ("99_System_OpenClaw/scripts/analysis_tiering.py", "POLICY_VERSION"),
    "T5": ("99_System_OpenClaw/desktop/server.py", "_assert_write"),
    "T6": ("99_System_OpenClaw/scripts/README.md", "剪映|历史"),
    "K1": ("99_System_OpenClaw/desktop/ai_patch.py", "locked|selected"),
    "K2": ("99_System_OpenClaw/desktop/project_store.py", "diff|rollback"),
    "K3": ("99_System_OpenClaw/desktop/project_store.py", "stale"),
    "K4": ("99_System_OpenClaw/desktop/project_store.py", "reference"),
    "K5": ("99_System_OpenClaw/desktop/project_store.py", "publishing"),
    "K6": ("99_System_OpenClaw/scripts/mac_openclaw_runner.py", "02_project_brief|04_script"),
}


PROFILE_ORDER = {
    "source_identity": ["unlocked", "locked"],
    "source_coverage": ["partial", "complete"],
    "visual_fidelity": ["none", "render-only", "structural", "strict-reference"],
    "interaction": ["none", "smoke", "full-e2e"],
    "local_runtime": [False, True],
    "external_system": ["none", "mock", "loopback", "sandbox-real", "real"],
    "persistent_runtime": ["none", "template", "installed", "active", "recovered"],
    "human_visual_review": ["none", "non-blocking", "blocking"],
}


def requirement_profile(item_id: str) -> dict[str, object]:
    backend_only = item_id.startswith("T")
    external = "none"
    if item_id in {"D3", "A1", "S5", "C1", "C2", "C3"}:
        external = "sandbox-real"
    if item_id in {"H2", "P5"}:
        external = "real"
    persistent = "installed" if item_id == "A2" else "active" if item_id == "H2" else "none"
    return {
        "source_identity": "locked",
        "source_coverage": "complete",
        "visual_fidelity": "structural" if backend_only else "strict-reference",
        "interaction": "smoke" if backend_only else "full-e2e",
        "local_runtime": True,
        "external_system": external,
        "persistent_runtime": persistent,
        "human_visual_review": "none" if backend_only else "blocking",
    }


def merge_profiles(profiles: list[dict[str, object]]) -> dict[str, object]:
    merged: dict[str, object] = {}
    for dimension, order in PROFILE_ORDER.items():
        values = [profile[dimension] for profile in profiles if dimension in profile]
        merged[dimension] = max(values, key=order.index) if values else order[0]
    return merged


REQ_PROFILE = {item_id: requirement_profile(item_id) for item_id in ITEM_IDS}


def first_line(relative: str, pattern: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        return f"{relative}:missing"
    matcher = re.compile(pattern, re.IGNORECASE)
    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if matcher.search(line):
            return f"{relative}:{number}"
    return f"{relative}:1"


def item_goal(item: dict[str, str]) -> str:
    return OUTCOMES.get(item["id"], f"{item['title']}：{item['action_text']}")


def api_for(item_id: str) -> str:
    surface = ITEM_SURFACE[item_id].removeprefix("SURF-").lower()
    return f"/api/v1/{surface}/{item_id.lower()}"


def write_region(item_id: str) -> str:
    prefix = item_id[0]
    if prefix in {"A", "H"}:
        return "99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/"
    if prefix == "I":
        return "99_System_OpenClaw/scripts/; 99_System_OpenClaw/desktop/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/"
    if prefix == "L":
        return "99_System_OpenClaw/scripts/; 99_System_OpenClaw/desktop/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/"
    if prefix == "P":
        return "99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/edit_backends/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/"
    if prefix in {"S", "C"}:
        return "99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/"
    if prefix == "T":
        return "99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/docs/"
    if prefix == "K":
        return "99_System_OpenClaw/desktop/; 99_System_OpenClaw/tests/"
    return "99_System_OpenClaw/"


def decision_ref_objects(ids: list[str]) -> list[dict[str, object]]:
    return [{"semantic_key": PD_META[node_id][0], "version": 1} for node_id in ids]


def contract_decision_refs(item_id: str) -> str:
    return ", ".join(f"{PD_META[node_id][0]}@1" for node_id in DECISION_REFS[item_id])


def create_source_documents() -> dict[str, dict[str, object]]:
    artifacts = [
        {
            "artifact_id": "SRC-ART-CHECKLIST",
            "path": CHECKLIST.relative_to(ROOT).as_posix(),
            "git_identity": f"main@{BASELINE}#blob:{CHECKLIST_BLOB}",
            "sha256": CHECKLIST_SHA,
            "media_type": "text/html",
            "authority_by_dimension": {
                "information_architecture": "normative",
                "visual_tokens": "informative",
                "layout": "informative",
                "interaction_behavior": "normative",
                "seed_data": "illustrative",
                "runtime_side_effects": "simulated",
            },
        },
        {
            "artifact_id": "SRC-ART-PROTOTYPE",
            "path": PROTOTYPE.relative_to(ROOT).as_posix(),
            "git_identity": f"main@{BASELINE}#blob:{PROTOTYPE_BLOB}",
            "sha256": PROTOTYPE_SHA,
            "media_type": "text/html",
            "authority_by_dimension": {
                "information_architecture": "normative",
                "visual_tokens": "normative",
                "layout": "normative",
                "interaction_behavior": "normative",
                "seed_data": "illustrative",
                "runtime_side_effects": "simulated",
            },
        },
    ]

    requirements = []
    for item in ITEMS:
        item_id = item["id"]
        requirements.append(
            {
                "requirement_id": f"SRC-{item_id}",
                "modality": "MUST",
                "source": {
                    "artifact_id": "SRC-ART-CHECKLIST",
                    "locator": f'article[data-k="{item_id.lower()}"]',
                    "content_sha256": sha256_bytes(item["source_text"].encode("utf-8")),
                },
                "summary": item_goal(item),
                "source_excerpt": item["source_text"],
                "required_evidence_profile": REQ_PROFILE[item_id],
                "node_refs": [item_id],
                "acceptance_refs": [f"{item_id}/AC-01", f"{item_id}/AC-02"],
                "evidence_targets": [
                    f"acceptance-fragments/OCM-{item_id}/acceptance/machine/e2e/runs/<run-id>/result.md"
                    if not item_id.startswith("T")
                    else f"acceptance-fragments/OCM-{item_id}/acceptance/machine/integration-contract/runs/<run-id>/result.md"
                ],
                "release_refs": ["M45", ITEM_RELEASE[item_id]],
                "scope_deviation_ref": None,
            }
        )

    release_records = [
        {
            "release_id": "M45",
            "release_class": "source-defined",
            "source_defined": True,
            "completion_authority": "source",
            "required_evidence_profile": merge_profiles(list(REQ_PROFILE.values())),
            "actual_evidence_profile": {},
            "status": "NOT_READY",
        }
    ]
    for release_id in RELEASE_META:
        profiles = [REQ_PROFILE[item_id] for item_id in RELEASE_ITEMS[release_id]]
        if release_id == "R8":
            profiles = list(REQ_PROFILE.values())
        release_records.append(
            {
                "release_id": release_id,
                "release_class": "local-candidate",
                "source_defined": False,
                "completion_authority": "ssot-release-owner",
                "candidate_of": "M45",
                "required_evidence_profile": merge_profiles(profiles),
                "actual_evidence_profile": {},
                "status": "NOT_READY",
            }
        )

    source_doc = {
        "schema_version": 1,
        "artifacts": artifacts,
        "requirements": requirements,
        "releases": release_records,
        "scope_deviations": [],
    }

    surfaces = []
    interaction_surfaces = []
    actions = []
    captures = []
    for surface_id, (name, route) in SURFACES.items():
        requirement_ids = [item_id for item_id in ITEM_IDS if ITEM_SURFACE[item_id] == surface_id]
        interaction_ids = [f"INT-{item_id}" for item_id in requirement_ids]
        action_ids = [f"ACT-{item_id}" for item_id in requirement_ids]
        acceptance_refs = [ref for item_id in requirement_ids for ref in (f"{item_id}/AC-01", f"{item_id}/AC-02")]
        surfaces.append(
            {
                "surface_id": surface_id,
                "name": name,
                "routes": [route],
                "states": ["loading", "empty", "error", "ready", "success"],
                "locales": ["zh-CN"],
                "themes": ["dark"],
                "viewports": ["desktop-1440x900", "mobile-390x844"],
                "helper_modes": ["connected"],
                "source_artifact_refs": ["SRC-ART-CHECKLIST", "SRC-ART-PROTOTYPE"],
                "requirement_refs": [f"SRC-{item_id}" for item_id in requirement_ids],
                "acceptance_refs": acceptance_refs,
                "expected_interaction_ids": interaction_ids,
                "expected_action_ids": action_ids,
            }
        )
        interactions = []
        for item_id in requirement_ids:
            item = ITEM_BY_ID[item_id]
            interactions.append(
                {
                    "interaction_id": f"INT-{item_id}",
                    "control": item["title"],
                    "input": "用户在真实入口查看状态或执行该条目约定的操作",
                    "precondition": "候选构建、项目身份和所需本地能力已明确；写操作满足统一安全合同",
                    "state_change": item_goal(item),
                    "visible_result": f"界面如实显示“{item['title']}”的处理结果、进度和下一步",
                    "boundary_behavior": "缺少数据、权限、能力或回读证据时明确阻断，不伪造成功，也不静默降级",
                    "source_requirement_refs": [f"SRC-{item_id}"],
                    "acceptance_refs": [f"{item_id}/AC-01", f"{item_id}/AC-02"],
                }
            )
            actions.append(
                {
                    "action_id": f"ACT-{item_id}",
                    "surface_id": surface_id,
                    "ui_affordance": item["title"],
                    "frontend_event": f"dispatch:{item_id.lower()}",
                    "helper_api": api_for(item_id),
                    "authentication_or_path_validation": "loopback、同源、CSRF、明确 revision 域和受控路径；只读动作仍做输入边界校验",
                    "project_action": item_goal(item),
                    "side_effect": "只执行来源条目和已接受产品决定允许的本地或外部动作；建议、预览和确认分离",
                    "receipt": f"receipt:{item_id.lower()}:candidate-digest:revision",
                    "ui_outcome": "成功、阻断、失败、重试和再次进入状态均可见且可恢复",
                    "e2e_ref": f"acceptance-fragments/OCM-{item_id}/acceptance/machine/e2e/runs/<run-id>/result.md",
                    "external_evidence_class": REQ_PROFILE[item_id]["external_system"],
                    "source_requirement_refs": [f"SRC-{item_id}"],
                    "acceptance_refs": [f"{item_id}/AC-01", f"{item_id}/AC-02"],
                }
            )
        interaction_surfaces.append({"surface_id": surface_id, "routes": [route], "interactions": interactions})
        for viewport in ("desktop-1440x900", "mobile-390x844"):
            captures.append(
                {
                    "capture_id": f"CAP-{surface_id.removeprefix('SURF-')}-{viewport.upper()}",
                    "surface_id": surface_id,
                    "route": route,
                    "locale": "zh-CN",
                    "theme": "dark",
                    "viewport": viewport,
                    "helper_mode": "connected",
                }
            )

    surface_doc = {"schema_version": 1, "surfaces": surfaces}
    visual_doc = {
        "schema_version": 1,
        "source_artifact_refs": ["SRC-ART-PROTOTYPE"],
        "semantic_structure_assertions": [
            "九个表面共享稳定导航和项目上下文，不把设置、诊断或旧 Studio 能力藏成无入口功能",
            "列表、筛选、详情、进度和确认对话框保持来源原型的信息层级",
            "loading、empty、error、ready、success 五种状态不会互相覆盖或移动稳定布局",
        ],
        "computed_style_assertions": [
            "桌面和移动视口无横向溢出、文字遮挡或控件重叠",
            "颜色、间距、边框、焦点、禁用和危险动作视觉语义与来源原型一致",
            "动态数字、长标题和错误说明不会改变固定工具栏与主要操作位置",
        ],
        "baseline_update_authority": "仅产品负责人可在来源 HTML 哈希变化或独立视觉选择获批后更新基线",
        "dynamic_region_policy": "项目名、数量、时间和状态为动态区域；结构、操作位置、警告和确认语义不得被动态掩码豁免",
        "capture_matrix": {"captures": captures},
    }
    interaction_doc = {"schema_version": 1, "surfaces": interaction_surfaces}
    action_doc = {"schema_version": 1, "actions": actions}
    runtime_doc = {
        "schema_version": 1,
        "components": [
            {
                "component_id": component_id,
                "kind": kind,
                "required_evidence_profile": profile,
                "actual_evidence_profile": {},
                "evidence_refs": [],
                "status": status,
            }
            for component_id, kind, profile, status in [
                ("RT-DESKTOP", "loopback desktop server", {"local_runtime": True, "persistent_runtime": "active"}, "NOT_READY"),
                ("RT-BROWSER", "desktop browser frontend", {"visual_fidelity": "strict-reference", "interaction": "full-e2e", "local_runtime": True}, "NOT_READY"),
                ("RT-MEDIA", "media analysis and archive runtime", {"local_runtime": True, "persistent_runtime": "installed"}, "NOT_READY"),
                ("RT-UPSTREAM", "optional upstream identity system", {"external_system": "sandbox-real"}, "BLOCKED_EXTERNAL"),
                ("RT-CHATCUT", "ChatCut Desktop local MCP", {"external_system": "real", "persistent_runtime": "active"}, "BLOCKED_EXTERNAL"),
                ("RT-TRASH", "current operating-system recycle bin", {"local_runtime": True}, "NOT_READY"),
                ("RT-ARCHIVE", "user-selected physical archive locations", {"local_runtime": True, "external_system": "real"}, "BLOCKED_EXTERNAL"),
                ("RT-MODELS", "user-configured model providers", {"external_system": "sandbox-real"}, "BLOCKED_EXTERNAL"),
                ("RT-CLOUD", "OpenClaw Media task middle platform", {"external_system": "sandbox-real"}, "BLOCKED_EXTERNAL"),
            ]
        ],
    }
    return {
        "source_requirements": source_doc,
        "surface_inventory": surface_doc,
        "visual_fidelity_contract": visual_doc,
        "interaction_matrix": interaction_doc,
        "action_vertical_slices": action_doc,
        "runtime_topology": runtime_doc,
    }


def build_nodes_and_edges() -> tuple[dict[str, dict[str, object]], list[dict[str, object]], dict[str, list[str]]]:
    release_nodes = {
        "R1": ["F", *PD_META.keys(), "TRD", *RELEASE_ITEMS["R1"], "Q1"],
        "R2": [*RELEASE_ITEMS["R2"], "Q2"],
        "R3": [*RELEASE_ITEMS["R3"], "Q3"],
        "R4": [*RELEASE_ITEMS["R4"], "Q4"],
        "R5": [*RELEASE_ITEMS["R5"], "Q5"],
        "R6": [*RELEASE_ITEMS["R6"], "Q6"],
        "R7": [*RELEASE_ITEMS["R7"], "Q7"],
        "R8": ["Z1", "Q8", "RZ"],
    }

    deps: dict[str, list[str]] = {"F": []}
    deps.update({node_id: ["F"] for node_id in PD_META})
    deps["TRD"] = ["F"]
    deps.update({item_id: list(dict.fromkeys(ITEM_DEPS[item_id])) for item_id in ITEM_IDS})
    for index in range(1, 8):
        release_id = f"R{index}"
        deps[f"Q{index}"] = [node_id for node_id in release_nodes[release_id] if node_id not in {"F", f"Q{index}"}]
    deps["Z1"] = [f"Q{i}" for i in range(1, 8)]
    deps["Q8"] = ["Z1"]
    deps["RZ"] = ["Q8"]

    # The user already selected the DashScope default with a local FunASR
    # fallback.  Keeping this as a fresh human decision would silently discard
    # that accepted product boundary and permanently block D3.
    accepted = {"F", *PD_META.keys(), "TRD"}
    state: dict[str, str] = {}
    for node_id in [node for release in release_nodes.values() for node in release]:
        if node_id in accepted:
            state[node_id] = "ACCEPTED"
        elif node_id == "TRD":
            state[node_id] = "BLOCKED"
        elif all(dependency in accepted for dependency in deps[node_id]):
            state[node_id] = "READY"
        else:
            state[node_id] = "BLOCKED"

    item_requirements = {item_id: [f"SRC-{item_id}"] for item_id in ITEM_IDS}
    surface_by_release = {
        release_id: sorted({ITEM_SURFACE[item_id] for item_id in ids})
        for release_id, ids in RELEASE_ITEMS.items()
        if ids
    }
    all_reqs = [f"SRC-{item_id}" for item_id in ITEM_IDS]
    all_surfaces = list(SURFACES)

    nodes: dict[str, dict[str, object]] = {}
    for release_id, node_ids in release_nodes.items():
        for node_id in node_ids:
            if node_id in nodes:
                raise SystemExit(f"node belongs to multiple releases: {node_id}")
            if node_id == "F":
                goal = "冻结 HTML、原型、源码和测试的可回读事实基线"
                work_kind, role, actor = "fact-discovery", "leaf", "orchestrator"
                decision_state, decision_version = "NOT_APPLICABLE", None
                refs, surfaces = all_reqs, all_surfaces
                write_authority, owner = "evidence-only", "主协调者"
                acceptance_authority = "主协调者"
            elif node_id in PD_META:
                goal = PD_META[node_id][1]
                work_kind, role, actor = "decision-acceptance", "leaf", "human"
                decision_state, decision_version = "ACCEPTED", 1
                refs = all_reqs if node_id == "PD" else [f"SRC-{item_id}" for item_id, values in DECISION_REFS.items() if node_id in values]
                surfaces = sorted({ITEM_SURFACE[ref.removeprefix("SRC-")] for ref in refs})
                write_authority, owner = "isolated-record", "产品负责人"
                acceptance_authority = "用户已明确决定"
            elif node_id == "TRD":
                goal = "决定转写提供方、默认策略、音频发送边界、费用和失败占位行为"
                work_kind, role, actor = "decision-acceptance", "leaf", "human"
                decision_state, decision_version = "ACCEPTED", 1
                refs, surfaces = ["SRC-D3"], ["SURF-SETTINGS"]
                write_authority, owner = "isolated-record", "产品负责人"
                acceptance_authority = "用户已明确决定"
            elif node_id in ITEM_BY_ID:
                item = ITEM_BY_ID[node_id]
                goal = item_goal(item)
                work_kind, role, actor = "implementation", "leaf", "codex"
                decision_state, decision_version = "NOT_APPLICABLE", None
                refs, surfaces = item_requirements[node_id], [ITEM_SURFACE[node_id]]
                write_authority, owner = "implementation", "对应领域维护者"
                acceptance_authority = "产品负责人和验收负责人"
            elif node_id.startswith("Q"):
                goal = f"汇编 {release_id} 的独立候选、证据和接受结果"
                work_kind, role, actor = "validation", "acceptance-gate", "orchestrator"
                decision_state, decision_version = "NOT_APPLICABLE", None
                if node_id == "Q8":
                    refs, surfaces = all_reqs, all_surfaces
                else:
                    refs = [f"SRC-{item_id}" for item_id in RELEASE_ITEMS[release_id]]
                    surfaces = surface_by_release[release_id]
                write_authority, owner = "shared-generated", "独立验收负责人"
                acceptance_authority = "独立验收负责人"
            elif node_id == "Z1":
                goal = "把九个表面接入同一入口、共享状态和完整纵向动作链，并建立项目内视觉工作台"
                work_kind, role, actor = "implementation", "leaf", "codex"
                decision_state, decision_version = "NOT_APPLICABLE", None
                refs, surfaces = all_reqs, all_surfaces
                write_authority, owner = "implementation", "桌面前端与服务维护者"
                acceptance_authority = "产品负责人和独立验收负责人"
            elif node_id == "RZ":
                goal = "只在八个切片和九屏人工验收均接受后作最终发布决定"
                work_kind, role, actor = "release-decision", "release-decision", "human"
                decision_state, decision_version = "NOT_APPLICABLE", None
                refs, surfaces = all_reqs, all_surfaces
                write_authority, owner = "shared-generated", "产品负责人"
                acceptance_authority = "产品负责人"
            else:
                raise AssertionError(node_id)

            if node_id in ITEM_BY_ID:
                decision_refs = decision_ref_objects(DECISION_REFS[node_id])
            elif node_id == "Z1":
                decision_refs = decision_ref_objects(list(PD_META))
            elif node_id.startswith("Q") or node_id == "RZ":
                decision_refs = decision_ref_objects(["PD"])
            else:
                decision_refs = []

            node_profile = merge_profiles([REQ_PROFILE[ref.removeprefix("SRC-")] for ref in refs])
            acceptance_ref = None
            if node_id in ITEM_BY_ID:
                acceptance_ref = f"acceptance-fragments/OCM-{node_id}/acceptance-contract.md"
            elif node_id == "Z1":
                acceptance_ref = "acceptance-fragments/OCM-Z1/acceptance-contract.md"
            node = {
                "node_id": node_id,
                "semantic_key": (
                    PD_META[node_id][0] if node_id in PD_META else
                    "decision.transcription.provider-boundary" if node_id == "TRD" else
                    f"requirement.checklist.{node_id.lower()}" if node_id in ITEM_BY_ID else
                    "fact.checklist.full-baseline" if node_id == "F" else
                    f"acceptance.release.{release_id.lower()}" if node_id.startswith("Q") else
                    "integration.nine-surfaces" if node_id == "Z1" else
                    "release.full-checklist"
                ),
                "stage": release_id,
                "work_kind": work_kind,
                "domain_lane": ITEM_SURFACE[node_id].removeprefix("SURF-").lower() if node_id in ITEM_SURFACE else release_id.lower(),
                "execution_state": state[node_id],
                "decision_state": decision_state,
                "decision_version": decision_version,
                "readiness_mode": "FORMAL",
                "hard_dependencies": deps[node_id],
                "soft_dependencies": [],
                "assumption_ids": [],
                "decision_refs": decision_refs,
                "invalidation_keys": [f"checklist.{node_id.lower()}"],
                "write_authority": write_authority,
                "acceptance_authority": acceptance_authority,
                "unlocks": [],
                "node_role": role,
                "execution_actor": actor,
                "execution_contract_ref": acceptance_ref or f"planning-compiler.json#node-{node_id}",
                "side_effect_class": "reversible" if node_id in {"A1", "D3", "I5", "P5"} else "none",
                "candidate_identity_policy": "none" if node_id in {"F", "TRD", *PD_META.keys()} else "freezes" if node_id.startswith("Q") else "must-match" if node_id == "RZ" else "consumes",
                "deliverable_ids": [f"DL-{node_id}"],
                "source_requirement_refs": refs,
                "surface_refs": surfaces,
                "required_evidence_profile": node_profile,
                "visual_contract_ref": VISUAL_REF,
                "goal": goal,
                "acceptance": "对应验收合同与所需证据全部通过，且没有把未验证层级提升为完成。",
                "owner": owner,
            }
            if acceptance_ref:
                node["acceptance_contract_ref"] = acceptance_ref
            if node_id == "Z1":
                node["visual_workbench_contract_ref"] = WORKBENCH_CONTRACT_REL
            nodes[node_id] = node

    edges: list[dict[str, object]] = []
    for target, dependencies in deps.items():
        for source in dependencies:
            reason = "candidate-identity" if target in {"Z1", "Q8", "RZ"} else "acceptance-dependency" if target.startswith("Q") else "contract-dependency"
            edge_id = f"E-{source}-{target}"
            edges.append(
                {
                    "edge_id": edge_id,
                    "from": source,
                    "to": target,
                    "dependency_type": "hard",
                    "dependency_scope": "specific-output",
                    "required_state": "ACCEPTED",
                    "assumption_ids": [],
                    "invalidation_keys": [f"edge.{source.lower()}.{target.lower()}"],
                    "transferred_input": f"{source} 已接受的合同、实现或验收产物",
                    "gate_evidence": f"{source} 节点状态与候选内容校验值",
                    "reason_code": reason,
                }
            )
            nodes[source]["unlocks"].append(target)
    for node in nodes.values():
        node["unlocks"] = list(dict.fromkeys(node["unlocks"]))
    return nodes, edges, release_nodes


def create_contract(item_id: str, item: dict[str, str] | None, all_refs: list[str] | None = None) -> str:
    is_z1 = item_id == "Z1"
    task_id = f"OCM-{item_id}"
    source_refs = all_refs if all_refs is not None else [f"SRC-{item_id}"]
    source_cell = ", ".join(source_refs)
    title = "九屏共享入口与全清单整合" if is_z1 else item["title"]
    outcome = "九个表面在真实入口中共同完成 45 项来源要求，并保留统一安全、状态、恢复和视觉边界；项目内视觉工作台同时展示现状证据、确定性原型、候选方向、选择记录和工程交接。" if is_z1 else item_goal(item)
    surface_id = "ALL-NINE-SURFACES" if is_z1 else ITEM_SURFACE[item_id]
    ui_change_rel = f"agents-results/2026-09-02/openclaw-media-full-checklist-implementation/acceptance-fragments/{task_id}/ui-change.json"
    user_visible = is_z1 or not item_id.startswith("T")
    human_workspace = "none"
    decision_refs = ", ".join(f"{PD_META[node_id][0]}@1" for node_id in PD_META) if is_z1 else contract_decision_refs(item_id)
    context = (
        f"SRC-{item_id}, source-notes.md" if not is_z1 else
        "SRC-D1 through SRC-K6, source-notes.md"
    )
    visual_refs = ".ssot/source-requirements.json" if user_visible else "none"
    ui_declaration = ui_change_rel if user_visible else "none"
    human_section = "机器证据负责本条目的确定性行为；用户理解、跨屏连贯性和视觉判断集中由 OCM-Z1 的九屏人工验收负责。"
    human_trace = ""
    if is_z1:
        human_section = "本次迁移仅重建机器可验证的来源登记。项目级人工验收需要在独立候选和新的交接记录建立后另行绑定。"

    protected = "| Path | SHA-256 | Covers |\n| --- | --- | --- |\n| none | none | Behavior specification only; executable baseline not yet locked |"
    primary_lane = "visual-fidelity" if is_z1 else "machine/integration-contract" if item_id.startswith("T") else "machine/e2e"
    exception_lane = "machine/e2e" if is_z1 else "machine/integration-contract" if item_id.startswith("T") else "machine/local-runtime"
    return f"""# Acceptance Contract: {task_id}

- Task ID: {task_id}
- Contract version: 1
- Contract status: DRAFT
- Test baseline: PLANNED
- Acceptance owner: 产品负责人与对应领域验收负责人
- Approval evidence: 尚未批准
- Request source: {CHECKLIST.relative_to(ROOT).as_posix()} sha256:{CHECKLIST_SHA}
- SSOT node: {item_id}
- SSOT path: {SSOT_REL}
- Readiness mode: FORMAL
- Decision refs: {decision_refs}
- Assumption IDs: none
- Invalidation keys: checklist.{item_id.lower()}
- AC budget: 2
- Baseline identity: main@{BASELINE}; checklist-sha256:{CHECKLIST_SHA}
- Product Context refs: {context if user_visible else 'none'}
- Role Context refs: 本地内容创作者，以及可选配对的上游中台用户
- Resolved Surface Contract refs: .ssot/source-requirements.json#{surface_id}
- Screen Contract ref: .ssot/source-requirements.json#{surface_id}
- Visual Contract refs: {visual_refs}
- UI Change declaration: {ui_declaration}
- Human acceptance workspace: {human_workspace}

## User and scenario

本地内容创作者从受支持的真实入口使用“{title}”，必要时主动配对上游账号或本地第三方工具。

## Problem

当前源码只覆盖该条目的局部原语或历史界面，不足以证明 HTML 中的完整业务承诺。

## Expected outcome

{outcome}

## Non-goals

不以删除条目、伪造外部成功、自动永久删除、绕过用户确认或修改生产剪映草稿作为实现方式。

## Normal path

```gherkin
Given 用户从真实入口进入对应界面，且所需本地资料与能力状态已就绪
When 用户查看或执行“{title}”
Then 系统完成“{outcome}”，并显示真实进度、回执和下一步
```

## Exception paths

覆盖缺少资料、路径越界、能力不支持、凭据缺失、并发版本冲突、外部超时、重复提交、部分失败、重试和再次进入。任一前置不满足时必须明确阻断或呈现不支持，不得伪造完成。

## Invariants

原始媒体不被自动永久删除；机器执行剪辑方案只读结构化权威；未配对上游身份不限制本地功能；外部能力只在实时探测与主动连接后呈现。

## Data impact

实现必须声明创建、更新、移动、恢复、幂等键、回执和保留期。破坏性动作仅在可恢复、用户二次确认且回读成功时允许。

## Permissions

本地用户可查看与执行本地功能；账号、外部模型和 ChatCut 需用户主动配置或连接；发布和人工验收由指定负责人签署。

## Performance and reliability

界面不因单个探测或外部超时失去响应；长任务提供进度、取消、重试和重启后恢复；实际阈值在测试基线锁定前由该节点冻结。

## Acceptance criteria

| ID | Class | Lane | Source requirement refs | Requirement | Mode | Blocking |
| --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | {primary_lane} | {source_cell} | {outcome}；从真实入口完成正常业务闭环，回读结果与可见状态一致 | Automatic | Yes |
| AC-02 | behavior | {exception_lane} | {source_cell} | 前置、权限、路径、版本、能力或外部系统异常时失败关闭，不伪造成功且可重试或恢复 | Automatic | Yes |

## Human acceptance

{human_section}

## Protected acceptance tests

{protected}

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 正常闭环自动验收 | acceptance-fragments/{task_id}/acceptance/machine/e2e/runs/&lt;run-id&gt;/result.md | Automatic | Yes |
| AC-02 | 失败、重试与恢复自动验收 | acceptance-fragments/{task_id}/acceptance/machine/integration-contract/runs/&lt;run-id&gt;/result.md | Automatic | Yes |{human_trace}

## Exploratory testing

重点探查大批量、长标题、缺少元数据、中途关闭、刷新、跨日期、多位置、多账号、多提供方和恶意路径组合。

## Production monitoring and rollback

本合同先要求本地运行验收。任一远端或发布候选必须另外绑定不可变候选身份、指标窗口、停止阈值和前向修复或回退方法。

## Risks and open decisions

合同保持 DRAFT，直到行为被产品负责人批准且受保护的自动验收基线被锁定。{'转写提供方已按 DashScope 默认、本机 FunASR 失败兜底、音频发送前明示的决定版本 1 接受；剩余风险是实现与验收证据，不是待决定产品策略。' if item_id == 'D3' else ''}
"""


def create_ui_change(task_id: str, source_refs: list[str], surface_refs: list[str]) -> dict[str, object]:
    source_document = json.loads((BUNDLE / ".ssot/source-requirements.json").read_text(encoding="utf-8"))
    source_digest = sha256_bytes(
        json.dumps(source_document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return {
        "schema_version": 1,
        "user_visible": True,
        "source_authority_mode": "strict",
        "source_requirements_ref": {
            "path": "agents-results/2026-09-02/openclaw-media-full-checklist-implementation/.ssot/source-requirements.json",
            "canonical_digest": source_digest,
        },
        "task_id": task_id,
        "reference_prototypes": [
            {
                "path": PROTOTYPE.relative_to(ROOT).as_posix(),
                "sha256": PROTOTYPE_SHA,
                "git_identity": f"main@{BASELINE}#blob:{PROTOTYPE_BLOB}",
                "authority_by_dimension": {
                    "information_architecture": "normative",
                    "visual_tokens": "normative",
                    "layout": "normative",
                    "interaction_behavior": "normative",
                    "seed_data": "illustrative",
                    "runtime_side_effects": "simulated",
                },
            }
        ],
        "capture_matrix": {"ref": ".ssot/source-requirements.json", "surface_refs": surface_refs},
        "interaction_matrix_ref": ".ssot/source-requirements.json",
        "visual_evidence_types": ["dom", "computed-style", "screenshot", "interaction-trace"],
        "visual_contract_ref": ".ssot/source-requirements.json",
        "source_requirement_refs": source_refs,
        "workbench_path": WORKBENCH_REL,
        "deep_link": {
            "supported": False,
            "gap_note": "Z1 由桌面前端维护者在项目内新建视觉工作台，并为九个界面补齐稳定深链接；在此之前不宣称来源原型是视觉工作台。",
        },
    }


def create_human_checklist() -> str:
    sections = []
    for index, (surface_id, (name, route)) in enumerate(SURFACES.items(), 1):
        sections.append(f"""## H-{index:02d}

- 验收问题：{name}能否让目标用户在不查阅实现说明的情况下，理解当前状态并完成主要任务？
- 必须人工判断的原因：理解成本、视觉层级、跨屏连贯性和业务适配不能只由确定性断言证明。
- 闭环名称：从共享入口完成{name}的真实任务。
- 验收角色：产品负责人，使用受支持本地设备和需要的测试账号。
- 进入方式：从获批候选的共享导航进入{name}，不使用调试绕过。
- 要做的事：进入界面，识别当前状态，完成一次正常任务，触发一次失败或阻断，然后恢复并再次进入。
- 前置条件：九屏机器验收已全绿，候选身份、测试资料、角色和外部能力状态已记录。
- 验收步骤：
  1. 从真实入口进入{name}。
  2. 不查看实现说明，独立完成主要任务。
  3. 观察进度、成功、失败、重试、刷新和再次进入。
- 预期观察：状态和主要操作清晰，没有误导、遮挡、跳动、隐藏前置或伪造完成。
- 副作用确认：只有来源合同允许且用户明确确认的业务副作用发生；其余由机器证据核对。
- 失败表现：缺少能力、超时、冲突或不支持时给出可理解的反馈和恢复方法。
- 判断标准：验收人能正确预期操作结果，完成闭环，并确认没有丢失 HTML 要求或旧 Studio 必保证义。
- 预计时长：10 分钟。
- 是否阻塞发布：是
- 结果记录规则：将签署观察和结论写入新的运行结果；不得修改已批准清单来记录某次执行。
""")
    contract_rel = "agents-results/2026-09-02/openclaw-media-full-checklist-implementation/acceptance-fragments/OCM-Z1/acceptance-contract.md"
    return f"""# 人工验收清单：OCM-Z1

- 任务编号：OCM-Z1
- 人工验收绑定：acceptance/human/2026-W36/2026-09-02-OCM-Z1/binding.md
- 验收合同：{contract_rel}
- 合同版本：1
- 清单状态：草稿
- 所需人工角色：产品负责人
- 清单负责人：产品负责人
- 批准证据：尚未批准
- 执行结果：acceptance/human/2026-W36/2026-09-02-OCM-Z1/runs/<run-id>/result.md

本清单只判断九个表面的产品含义、理解成本、流程质量、视觉层级和跨屏一致性。接口、数据、权限、路径、回执和错误码必须在进入本清单前由机器证据全部通过。

{''.join(sections)}
"""


def build_acceptance(nodes: dict[str, dict[str, object]]) -> None:
    for item in ITEMS:
        item_id = item["id"]
        task_id = f"OCM-{item_id}"
        task_root = BUNDLE / "acceptance-fragments" / task_id
        write_text(task_root / "acceptance-contract.md", create_contract(item_id, item, list(nodes[item_id]["source_requirement_refs"])))
        if not item_id.startswith("T"):
            write_json(task_root / "ui-change.json", create_ui_change(task_id, [f"SRC-{item_id}"], [ITEM_SURFACE[item_id]]))
        write_text(task_root / "acceptance/index.md", f"# Acceptance index: {task_id}\n\nContract status: DRAFT. Test baseline: PLANNED. No execution run has been accepted.")

    task_root = BUNDLE / "acceptance-fragments/OCM-Z1"
    all_refs = list(nodes["Z1"]["source_requirement_refs"])
    write_text(task_root / "acceptance-contract.md", create_contract("Z1", None, all_refs))
    write_json(task_root / "ui-change.json", create_ui_change("OCM-Z1", all_refs, list(SURFACES)))
    write_text(task_root / "acceptance/index.md", "# Acceptance index: OCM-Z1\n\nContract status: DRAFT. Test baseline: PLANNED. Human acceptance is not yet approved or executed.")

    human = ROOT / "acceptance/human/2026-W36/未-2026-09-02-OCM-Z1"
    write_text(human / "checklist.md", create_human_checklist())


def build_source_notes() -> None:
    rows = []
    for item in ITEMS:
        relative, pattern = EVIDENCE_LOOKUPS[item["id"]]
        rows.append(
            f"| {item['id']} | {item['section']} | {item['source_status']} | {BASELINE_STATUS[item['id']]} | `{first_line(relative, pattern)}` | `{sha256_bytes(item['source_text'].encode('utf-8'))}` |"
        )
    write_text(
        BUNDLE / "source-notes.md",
        f"""# 来源与当前代码基线

## 身份

- 要求来源：`{CHECKLIST.relative_to(ROOT).as_posix()}`
- 要求来源 SHA-256：`{CHECKLIST_SHA}`
- 视觉原型：`{PROTOTYPE.relative_to(ROOT).as_posix()}`
- 视觉原型 SHA-256：`{PROTOTYPE_SHA}`
- 源码基线：`main@{BASELINE}`，创建本 SSOT 时本地、跟踪分支与远端主分支一致。
- 新鲜回归基线：304 项通过，0 跳过。它只证明现有行为，不证明 45 项需求完成。

## 已接受的产品决定

以用户在本任务会话中的明确拍板为来源，登记为决定版本 1：

1. 整理台自动分事件、分批，但移动前必须由用户确认。
2. 素材库增加结构化索引，不删除现有卡片展示。
3. 生产删除只生成建议；用户勾选并二次确认后才进入当前操作系统回收站。
4. 创意模型由用户配置，可使用 Codex/OpenAI、Claude/Anthropic、DeepSeek 或兼容接口。
5. 本地剪辑工具（ChatCut）只通过桌面本地模型上下文协议（MCP）集成；只有实时探测成功且用户主动连接后才显示。
6. 归档同时配置生命周期和物理位置，每个位置独立保存清单、校验值和回读状态。
7. 上游账号配对是主动可选行为；未登录、未配对或平台不支持时，本地功能保持完整。
8. 结构化剪辑决策列表（`06_edit_decision_list.json`）是机器执行的唯一剪辑方案权威。
9. 剪映脚本只作历史材料；自动化不得修改生产剪映草稿。

## 45 项基线矩阵

| ID | 来源分组 | HTML 判定 | 当前审计判定 | 当前代码定位 | 条目内容 SHA-256 |
| --- | --- | --- | --- | --- | --- |
{chr(10).join(rows)}

## 证据边界

原 HTML 中的“可直接接”是设计阶段判断，不是当前验收状态。上表重新绑定当前主分支；所有 45 项仍需独立合同、受保护测试、本地运行或外部证据和最终九屏人工验收。
""",
    )


def build_planning(nodes: dict[str, dict[str, object]], release_nodes: dict[str, list[str]]) -> dict[str, object]:
    macro = [
        {"id": "P1", "title": "基础能力与主工作面", "release_ids": ["R1", "R2", "R3", "R4"]},
        {"id": "P2", "title": "连接、迁移与整体发布", "release_ids": ["R5", "R6", "R7", "R8", "M45"]},
    ]
    release_slices = []
    for release_id, (title, value) in RELEASE_META.items():
        release_slices.append(
            {
                "id": release_id,
                "macro_phase_id": "P1" if int(release_id[1:]) <= 4 else "P2",
                "title": title,
                "user_value": value,
                "independent_acceptance": f"{release_id} 所有条目合同、自动证据和所需人工判断同时通过。",
                "independent_failure": f"{release_id} 候选保持未晋升；不改变其他切片、原始媒体或既有本地功能。",
                "future_phase_required_for_success": False,
                "development_baseline": f"commit@{BASELINE}",
                "promotion_baseline": f"origin/main:{BASELINE}:must-refetch",
                "release_candidate": f"candidate:{release_id.lower()}:content-digest-pending",
                "node_ids": release_nodes[release_id],
            }
        )
    planning_nodes = []
    for node_id, node in nodes.items():
        kind = "decision" if node["work_kind"] == "decision-acceptance" else "release" if node_id == "RZ" else "validation" if node["work_kind"] in {"fact-discovery", "validation"} else "convergence" if node_id == "Q8" else "implementation"
        record: dict[str, object] = {
            "id": node_id,
            "kind": kind,
            "goal": node["goal"],
            "dependencies": node["hard_dependencies"],
            "acceptance": node["acceptance"],
            "owner": node["owner"],
        }
        if node_id in {"A1", "D3"}:
            record["side_effects"] = ["external-api"]
            record["transaction_models"] = {"external-api": "saga"}
            record["escalation"] = {
                "reasons": ["external-side-effect"],
                "evidence_contract": f"acceptance-fragments/OCM-{node_id}/acceptance-contract.md",
                "recovery_contract": "不保存明文凭据；超时或部分失败保留本地可用状态并给出待处理回执",
                "external_identity": "用户明确选择的上游账号或转写提供方沙箱身份",
            }
        elif node_id == "RZ":
            record["escalation"] = {
                "reasons": ["production-release"],
                "immutable_release_identity": "candidate:r8:content-digest-pending",
                "promotion_baseline": f"origin/main:{BASELINE}:must-refetch",
                "recovery_contract": "未满足发布证据时保持上一个已接受不可变版本；已发布后使用前向修复或恢复上一已接受版本。",
            }
        planning_nodes.append(record)

    return {
        "planning_compiler_schema_version": 1,
        "classification": {
            "applicability": "ssot",
            "ssot_depth": "L2",
            "artifact_policy": "create-ssot",
            "selection_authority": "user",
            "rationale": "用户明确要求以指定 HTML 的 45 项要求创建新 SSOT；范围横跨八个独立发布切片、九个用户表面、外部身份与本地第三方工具。",
        },
        "macro_phases": macro,
        "release_slices": release_slices,
        "waves": [{"id": f"W{index}", "release_id": f"R{index}", "node_ids": release_nodes[f"R{index}"]} for index in range(1, 9)],
        "scheduling_model": "event-driven",
        "scheduling_hints": [
            "只有显式硬依赖定义拓扑；来源分组和发布切片不会自动串行。",
            "当前就绪叶节点可按写入区域并行；共享生成物、候选汇编和发布决定始终由单一负责人串行写入。",
            "转写决定只阻塞 D3 和最终完整候选；其他无关节点不等待该决定。",
        ],
        "nodes": planning_nodes,
        "external_systems": [
            "上游 OpenClaw Media 身份系统", "用户配置的模型提供方", "ChatCut Desktop 本地 MCP",
            "当前操作系统回收站", "用户选择的云盘和移动存储", "本地 Kdenlive 与 OTIO 运行时",
        ],
        "acceptance_layers": ["source", "static-test", "fixture/mock", "local-runtime", "external-sandbox", "human"],
        "release_boundary_compiler": {
            "boundary_required": True,
            "decision_authority": "source",
            "rationale": "HTML 的功能群具有独立用户价值和失败边界；最终 45 项完成权威仍属来源要求。",
        },
        "artifacts": {
            "ssot_bundle": True,
            "generated_views": ["main"],
            "worker_ledger": False,
            "evidence_identity_registry": False,
            "resource_matrix": False,
            "runner_registry": False,
        },
        "artifacts_inventory": {
            "total_nodes": len(nodes),
            "implementation_nodes": sum(node["work_kind"] == "implementation" for node in nodes.values()),
            "worker_nodes": 0,
            "generated_views": 1,
        },
        "complexity_budget": {
            "authority": "用户要求完整覆盖 45 项与 L2 比例治理合同",
            "rationale": "45 个来源条目各保留一个责任节点；决定、发布验收和九屏汇合只增加必要薄节点，不登记未真实运行的外部 Codex 进程。",
            "limits": {"total_nodes": 67, "implementation_nodes_per_release": 9, "codex_worker_nodes": 0, "generated_views": 1},
        },
        "goal_size_detector": {
            "implementation_or_migration_nodes": sum(node["work_kind"] == "implementation" for node in nodes.values()),
            "external_systems": 6,
            "release_slices": 8,
            "production_migrations": 0,
            "acceptance_layers": 6,
            "split_required": False,
            "split_strategy": "release",
        },
        "conservation_rule": {
            "statement": "每个 HTML MUST 条目必须绑定一个显式未完成或已证明节点；不得丢失、降级或用其他条目的证据替代。"
        },
        "source_requirements": [
            {"requirement_id": f"SRC-{item_id}", "node_ids": [item_id], "status": "INCOMPLETE"}
            for item_id in ITEM_IDS
        ],
    }


def render_main(nodes: dict[str, dict[str, object]], edges: list[dict[str, object]], release_nodes: dict[str, list[str]], source_docs: dict[str, dict[str, object]]) -> str:
    state_rows = []
    semantic_rows = []
    deliverable_rows = []
    for node_id, node in nodes.items():
        blocking = "none" if node["execution_state"] in {"READY", "ACCEPTED"} else ",".join(dep for dep in node["hard_dependencies"] if nodes[dep]["execution_state"] != "ACCEPTED") or "待人工决定"
        if node_id == "F":
            evidence = "source-notes.md 中的来源校验值、主分支身份、45 项代码定位和 304 项回归基线"
        elif node_id in PD_META:
            evidence = "用户在本任务中明确拍板，并登记为决定版本 1"
        elif node["execution_state"] == "READY":
            evidence = "尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED"
        else:
            evidence = "尚无完成证据；硬依赖或人工决定未满足"
        state_rows.append(
            f"| {node_id} | {node['stage']} | v1 | {node['execution_state']} | 0 | {node['owner']} | G-SSOT | {blocking} | {evidence} | {','.join(node['unlocks']) or 'none'} |"
        )
        refs = ",".join(f"{ref['semantic_key']}@{ref['version']}" for ref in node["decision_refs"]) or "none"
        semantic_rows.append(
            f"| {node_id} | {node['semantic_key']} | {node['work_kind']} | {node['domain_lane']} | {node['execution_state']} | {node['decision_state']} | {node['decision_version'] if node['decision_version'] is not None else 'none'} | {node['readiness_mode']} | {','.join(node['hard_dependencies']) or 'none'} | none | none | {refs} | {','.join(node['invalidation_keys'])} | {node['write_authority']} | {node['acceptance_authority']} |"
        )
        dependencies = ",".join(node["hard_dependencies"]) or "none"
        region = (
            write_region(node_id) if node_id in ITEM_BY_ID else
            f"99_System_OpenClaw/desktop/; {WORKBENCH_REL}; {WORKBENCH_CONTRACT_REL}; 99_System_OpenClaw/tests/" if node_id == "Z1" else
            f".ssot/nodes/{node_id}.json"
        )
        deliverable_rows.append(
            f"| DL-{node_id} | {node['stage']} | {node['goal']} | {region} | {dependencies} | independent | none | {node_id} | n/a |"
        )

    edge_rows = [
        f"| {edge['from']} | {edge['to']} | {edge['dependency_type']} | {edge['dependency_scope']} | ACCEPTED | none | {','.join(edge['invalidation_keys'])} | {edge['transferred_input']} | {edge['gate_evidence']} |"
        for edge in edges
    ]
    ready_rows = []
    for node_id, node in nodes.items():
        if node["execution_state"] != "READY":
            continue
        unsatisfied = [dep for dep in node["hard_dependencies"] if nodes[dep]["execution_state"] != "ACCEPTED"]
        ready_rows.append(f"| F0 | {node_id} | FORMAL | {','.join(unsatisfied) or 'none'} | none | conflict-free |")
    if not ready_rows:
        ready_rows.append("| F0 | none | blocked | none | none | no-ready-node |")

    width_rows = []
    for release_id, ids in release_nodes.items():
        count = len(ids)
        width_rows.append(f"| {release_id} | {count} | {count} | 0 | {count} | 64 | {math.ceil(count / 64)} |")

    release_rows = []
    for release_id, (title, value) in RELEASE_META.items():
        release_rows.append(
            f"| {release_id} | {title} | {value} | 全部节点合同和证据接受 | 候选不晋升，其他切片不受影响 | `commit@{BASELINE}` | `origin/main:{BASELINE}:must-refetch` | `candidate:{release_id.lower()}:content-digest-pending` |"
        )

    requirement_rows = []
    for requirement in source_docs["source_requirements"]["requirements"]:
        requirement_rows.append(
            f"| {requirement['requirement_id']} | `{requirement['source']['locator']}` | MUST | {requirement['summary']} | {','.join(requirement['node_refs'])} | {','.join(requirement['acceptance_refs'])} | {','.join(str(target['path']) for target in requirement['evidence_targets'])} | {','.join(requirement['release_refs'])} | none |"
        )

    artifact_rows = []
    for artifact in source_docs["source_requirements"]["artifacts"]:
        auth = artifact["authority_by_dimension"]
        artifact_rows.append(
            f"| {artifact['artifact_id']} | `{artifact['path']}` | `{artifact['git_identity']}` | `{artifact['sha256']}` | {artifact['media_type']} | {auth['information_architecture']} | {auth['visual_tokens']} | {auth['layout']} | {auth['interaction_behavior']} | {auth['seed_data']} | {auth['runtime_side_effects']} |"
        )

    source_registry = source_docs["source_requirements"]
    surface_rows = []
    for surface in source_registry["surfaces"]:
        surface_rows.append(
            f"| {surface['surface_id']} | {','.join(surface['routes'])} | {','.join(surface['states'])} | zh-CN | dark | {','.join(surface['viewports'])} | connected/local-only | SRC-ART-CHECKLIST,SRC-ART-PROTOTYPE | {','.join(surface['item_refs'])} |"
        )

    interaction_rows = []
    for interaction in source_registry["interaction_catalog"]:
        interaction_rows.append(
            f"| {interaction['id']} | {interaction['surface_id']} | {interaction['control']} | {interaction['precondition']} | {interaction['trigger']} | {interaction['state_change']} | {interaction['visible_result']} / {interaction['boundary_behavior']} | {','.join(interaction['source_refs'])} | {','.join(interaction['acceptance_refs'])} |"
        )

    action_rows = []
    for action in source_registry["api_mapping"]:
        action_rows.append(
            f"| {action['id']} | {action['method']} | `{action['path']}` | {action['status']} | {action['schema']} | {action['revision']} | {action['csrf']} | {action['receipt']} | `{action['source']}` |"
        )

    runtime_rows = []
    for component in source_registry["runtime_components"]:
        runtime_rows.append(
            f"| {component['id']} | {component['kind']} | {component['status']} |"
        )

    token_rows = [
        f"| `{token['name']}` | `{token['value']}` | computed style in 1440x900 and 390x844 |"
        for token in source_registry["visual_contract"]["tokens"]
    ]
    anchor_rows = [
        f"| `{anchor['attribute']}` | `{anchor['value']}` | {','.join(anchor['node_refs'])} | DOM structure + interaction trace |"
        for anchor in source_registry["visual_contract"]["dom_anchors"]
    ]

    mermaid_nodes = "\n".join(f"  {node_id}[\"{node_id}\"]" for node_id in nodes)
    mermaid_edges = "\n".join(f"  {edge['from']} --> {edge['to']}" for edge in edges)
    ascii_groups = "\n".join(f"{release_id}: {' '.join(ids)}" for release_id, ids in release_nodes.items())
    validate_command = (
        "99_System_OpenClaw/.venv-content-os/bin/python .agents/skills/report-to-ssot-development-paths/scripts/validate_ssot_bundle.py "
        "agents-results/2026-09-02/openclaw-media-full-checklist-implementation --skip-archive"
    )
    return f"""---
ARTIFACT_CLASS: ssot-development
APPLICABILITY_DECISION: ssot
GOVERNANCE_REASON: 指定 HTML 的 45 项要求横跨八个独立发布切片、九个界面和多个外部边界，需要持久来源守恒和验收权威。
SSOT_DEPTH: L2
TARGET_EVIDENCE_LEVEL: local-runtime
PLAN_VERSION: 1
DAG_VERSION: 1
INTERFACE_FREEZE_VERSION: 1
NODE_CONTRACT_VERSION: 1
SSOT_SCHEMA_VERSION: 2
FACTS_REGISTRY_VERSION: 1
SSOT_PLANNING_COMPILER: .ssot/planning-compiler.json
SSOT_MACHINE_SOURCE: .ssot/manifest.json
NORMATIVE_EXECUTABLE_ARTIFACT_MODE: strict
---

# OpenClaw 媒体 45 项全量落地 SSOT

## 业务结论与范围

这是一份新的实施权威，直接覆盖指定清单的 45 项要求。每个条目都保留独立来源定位、内容校验值、责任节点、验收准则和证据目标，不以降级、删项或过时的“可直接接”标签替代真实实现。

当前不是 45 项完成声明。已有测试只是回归基线；转写策略已按用户决定接受，但所有来源条目仍须以各自的代码、受保护测试和运行证据完成验收。

## 用户、角色与影响行为

主要用户是在本机整理媒体、复用素材、编排项目和交接剪辑的内容创作者。上游账号、模型提供方、本地剪辑工具（ChatCut）和物理存储均由用户主动选择；未登录、未配对或平台不支持时，本地功能保持完整。

## 明确不做的事

- 不自动永久删除媒体，不承诺回收站固定保留天数。
- 不把标记文档格式（Markdown）、界面文本或剪映草稿当作第二份机器执行剪辑方案。
- 不在实时探测失败或用户未主动连接时显示本地剪辑工具（ChatCut）。
- 不修改生产剪映草稿，不把策略停止维护误写成技术加密。

## 已接受的关键策略

转写策略已接受：默认使用在线转写服务（DashScope），音频发送前明示，失败时只在本机转写工具（FunASR）已安装可用的情况下回退。D3 的剩余工作是统一实现、自动验收和运行证据，不是再次等待产品拍板。

## 工程执行附录

## 发布切片

| Macro phase | Release ID | User value | Independent acceptance | Independent failure | Development baseline | Promotion baseline | Release candidate |
| --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(release_rows)}

## 实施路径摘要

实施按真实依赖事件驱动：安全与破坏性操作门禁先行；结构化索引、整理台、时间线、设置与 Studio 能力迁移只在有真实产物依赖时串行。八个切片各自形成不可变候选，最后才进入九屏共享入口、机器端到端验收与人工产品验收。

## 权威登记

| Claim/domain | Declared authority path | Authority layer | Lookup method | Change required | Owning node | Validation |
| --- | --- | --- | --- | --- | --- | --- |
| 45 项实施编排 | `.ssot/manifest.json` 与唯一 `.ssot/source-requirements.json` | decision/orchestration | 统一验证 | 是 | F | 来源守恒、表面覆盖与证据轮廓 |
| 原始需求 | `agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-dev-checklist.html` | domain-contract | SHA-256 与条目定位 | 否 | F | 45/45 条目 |
| 视觉与信息架构 | `agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-media-ui-prototype.html` | domain-contract | SHA-256 与捕获矩阵 | 否 | Z1 | DOM、计算样式、截图和交互轨迹 |
| 项目内视觉工作台 | `{WORKBENCH_REL}` 与 `{WORKBENCH_CONTRACT_REL}` | project-generated | Z1 实现与视觉工作台校验 | 是 | Z1 | 证据、原型、候选、选择记录、界面状态和深链接 |
| 当前代码现状 | `source-notes.md` | runtime-evidence | 文件行号和当前主分支 | 是 | F | 新鲜审计与回归基线 |

## 规范性可执行工件

| Artifact ID | Path | Git identity | SHA-256 | Media type | Information architecture | Visual tokens | Layout | Interaction behavior | Seed data | Runtime side effects |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(artifact_rows)}

MUST requirement coverage: 100%（以统一机器验证通过为前提）。

| Requirement ID | Source locator | Modality | Summary | Node refs | AC refs | Evidence targets | Release refs | Scope deviation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(requirement_rows)}

### 视觉令牌与 DOM 锚点

| Token | Frozen value | Machine assertion |
| --- | --- | --- |
{chr(10).join(token_rows)}

字体族固定为 `Archivo`、`Asap`、`JetBrains Mono`。

| Attribute | Value | Owning nodes | Evidence |
| --- | --- | --- | --- |
{chr(10).join(anchor_rows)}

| Surface ID | Routes | States | Locales | Themes | Viewports | Helper modes | Source refs | Checklist item refs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(surface_rows)}

| Interaction ID | Surface | Control | Preconditions | Trigger | State change | Visible/boundary result | Source refs | AC refs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(interaction_rows)}

| API ID | Method | Path | Status | Schema | Revision | CSRF | Receipt | Source/owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(action_rows)}

| Runtime component | Kind | Status |
| --- | --- | --- |
{chr(10).join(runtime_rows)}

## 状态台账

| Task ID | Stage | Versions | State | Attempt | Owner | Guard ID | Blocking reason | Evidence | Unlocks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(state_rows)}

## 语义节点注册表

| Task ID | Semantic key | Work kind | Domain lane | Execution state | Decision state | Decision version | Readiness mode | Hard dependencies | Soft dependencies | Assumptions | Decision refs | Invalidation keys | Write authority | Acceptance authority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(semantic_rows)}

## 依赖边表

| From | To | Dependency type | Dependency scope | Required upstream state | Assumption IDs | Invalidation keys | Transferred input | Gate/evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(edge_rows)}

## 当前就绪前沿

| Frontier | Task ID | Eligibility | Unsatisfied hard dependencies | Active assumptions | Resource decision |
| --- | --- | --- | --- | --- | --- |
{chr(10).join(ready_rows)}

## 叶交付物清单

| Deliverable ID | Parallel batch | Deliverable | Authority write region | Dependencies | Isolation decision | Conflict class | Owning node | Grouping reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(deliverable_rows)}

## 并行宽度

| Parallel batch | Leaf deliverables | Independent deliverables | Conflict-grouped deliverables | Logical lane target | Available worker slots | Wave count |
| --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(width_rows)}

并行宽度表是逻辑交付线上限，不是已运行的外部执行者台账。本 SSOT 不虚构工作者、进程、会话或并行运行证据。

## ASCII 拓扑图

```text
F -> PD,PD1..PD9,TRD
{ascii_groups}
Q1..Q7 -> Z1 -> Q8 -> RZ
```

```mermaid
flowchart LR
{mermaid_nodes}
{mermaid_edges}
  classDef accepted fill:#163c2e,stroke:#63d89b,color:#ffffff;
  classDef ready fill:#2f3d1f,stroke:#b9d968,color:#ffffff;
  classDef blocked fill:#3d2424,stroke:#e78686,color:#ffffff;
```

## 事实登记表（Facts Registry）

| 事实类别（Fact category） | 事实键（Fact key） | 登记值（Registered value） | 用途（Usage） |
| --- | --- | --- | --- |
| 命令 | ssot-validate-dev | `{validate_command}` | 开发期统一验证 |
| 路径 | owned-roots | `agents-results`; `.ssot`; `acceptance`; `99_System_OpenClaw`; `.agents/skills`; `scripts/validate_ssot_bundle.py`; `/api`; `/login`; `/setup`; `/app/home`; `/app/inbox`; `/app/library`; `/app/project/`; `/app/settings`; `/cloud/tasks`; `scripts/edit_backends/` | 正文工程定位覆盖 |
| 布局 | machine-layout | `.ssot/nodes`; `.ssot/edges`; `.ssot/view-sources`; `acceptance-fragments` | 机器分片与验收分片布局 |
| 必有标志 | development-validation | `--skip-archive` | 区分开发验证与正式整包验证 |
| 必无标志 | destructive-sync | `--delete` | 禁止破坏性同步 |
| 主机别名 | authoritative-remote | `origin` | 未来晋升时唯一权威远端别名 |
| 版本 | runtime-minimum | `3.11`; `6.2`; `18.7`; `31.4` | 本地 Python 与来源中显式版本号 |

## 验证、清理与完成条件

开发期统一验证命令为 `{validate_command}`。正式完成还要求受保护测试基线、九屏机器验收、产品负责人签署、Obsidian 快照核验与全局归档审计。运行环境最低版本为 `3.11`。

本轮只创建 SSOT，不创建或清理 Git 分支，不提交、不推送、不更改媒体文件。未来实施结束时，先推送并回读权威主分支，再清理已确认无独有内容的候选工作区与分支。
"""


def create_strict_source_documents() -> tuple[dict[str, object], dict[str, list[str]]]:
    """Compile the v2 registry from exact checklist items and prototype controls."""
    artifacts = [
        {
            "artifact_id": "SRC-ART-CHECKLIST",
            "external_dependency_id": "EXT-CHECKLIST",
            "path": CHECKLIST.relative_to(ROOT).as_posix(),
            "git_identity": f"main@{BASELINE}#blob:{CHECKLIST_BLOB}",
            "sha256": CHECKLIST_SHA,
            "media_type": "text/html",
            "authority_by_dimension": {
                "information_architecture": "normative",
                "visual_tokens": "informative",
                "layout": "informative",
                "interaction_behavior": "normative",
                "seed_data": "illustrative",
                "runtime_side_effects": "simulated",
            },
        },
        {
            "artifact_id": "SRC-ART-PROTOTYPE",
            "external_dependency_id": "EXT-PROTOTYPE",
            "path": PROTOTYPE.relative_to(ROOT).as_posix(),
            "git_identity": f"main@{BASELINE}#blob:{PROTOTYPE_BLOB}",
            "sha256": PROTOTYPE_SHA,
            "media_type": "text/html",
            "authority_by_dimension": {
                "information_architecture": "normative",
                "visual_tokens": "normative",
                "layout": "normative",
                "interaction_behavior": "normative",
                "seed_data": "illustrative",
                "runtime_side_effects": "simulated",
            },
        },
    ]
    # The generic HTML inventory remains useful as discovery evidence, but its
    # headings and table rows are not interchangeable with the 45 checklist
    # articles.  Dispose those records as informative and add exact records for
    # every authoritative checklist item and prototype primitive below.
    inventory = []
    for artifact in artifacts:
        for record in inventory_html(ROOT / str(artifact["path"]), str(artifact["artifact_id"])):
            record["disposition"] = "informative"
            record["rationale"] = "结构发现记录；规范要求由精确 article、token 或 data-* 定位记录承载。"
            inventory.append(record)

    item_to_ref: dict[str, list[str]] = {item_id: [] for item_id in ITEM_IDS}
    requirements: list[dict[str, object]] = []

    def add_requirement(
        requirement_id: str,
        *,
        inventory_record: dict[str, object],
        summary: str,
        dimension: str,
        node_refs: list[str],
        acceptance_refs: list[str],
        required_lanes: list[str],
        release_refs: list[str],
        external_system_refs: list[str] | None = None,
        semantic_source: dict[str, str] | None = None,
    ) -> None:
        inventory_record["disposition"] = "requirement"
        inventory_record.pop("rationale", None)
        inventory_record["requirement_ref"] = requirement_id
        targets = [
            {
                "lane": lane,
                "path": (
                    f"acceptance-fragments/OCM-{node_refs[0]}/acceptance/"
                    f"{lane.removeprefix('machine/')}/runs/<run-id>/result.md"
                ),
            }
            for lane in required_lanes
        ]
        requirements.append(
            {
                "requirement_id": requirement_id,
                "dimension": dimension,
                "modality": "MUST",
                "modality_confirmation": {
                    "status": "confirmed",
                    "value": "MUST",
                    "actor_type": "human",
                    "node_ref": "F",
                    "confirmed_by": "来源权威及用户 2026-09-02 整改决定",
                    "evidence_ref": "source-notes.md",
                },
                "source": {
                    "artifact_id": inventory_record["artifact_id"],
                    "locator": inventory_record["locator"],
                    "content_sha256": inventory_record["content_sha256"],
                },
                "semantic_source": semantic_source,
                "summary": summary,
                "required_lanes": required_lanes,
                "node_refs": node_refs,
                "acceptance_refs": acceptance_refs,
                "evidence_targets": targets,
                "external_system_refs": external_system_refs or [],
                "release_refs": list(dict.fromkeys(release_refs)),
                "scope_deviation_ref": None,
            }
        )
        for node_id in node_refs:
            if node_id in item_to_ref:
                item_to_ref[node_id].append(requirement_id)

    for item in ITEMS:
        item_id = item["id"]
        matching = [record for record in inventory if record["artifact_id"] == "SRC-ART-CHECKLIST" and record["text"] == f"CHECKLIST::{item_id}"]
        if len(matching) != 1:
            raise SystemExit(f"machine inventory bridge mismatch for checklist item {item_id}")
        external_refs = []
        if item_id in {"A1", "S4", "C1", "C2", "C3"}:
            external_refs.append("EXTSYS-UPSTREAM")
        if item_id in {"H2", "P5"}:
            external_refs.append("EXTSYS-CHATCUT")
        if item_id in {"D3"}:
            external_refs.extend(["EXTSYS-DASHSCOPE", "EXTSYS-FUNASR"])
        if item_id in {"S5"}:
            external_refs.append("EXTSYS-MODEL-PROVIDERS")
        if item_id in {"I5"}:
            external_refs.append("EXTSYS-SYSTEM-TRASH")
        if item_id in {"L3", "L4", "S2"}:
            external_refs.append("EXTSYS-PHYSICAL-STORAGE")
        add_requirement(
            f"SRC-CHECKLIST-{item_id}",
            inventory_record=matching[0],
            summary=item_goal(item),
            dimension="interaction",
            node_refs=[item_id],
            acceptance_refs=[f"{item_id}/AC-01", f"{item_id}/AC-02"],
            required_lanes=["machine/e2e", "machine/local-runtime"] if not item_id.startswith("T") else ["machine/integration-contract"],
            release_refs=["M45", ITEM_RELEASE[item_id], "R8"],
            external_system_refs=external_refs,
            semantic_source={
                "locator": f'article[data-k="{item_id.lower()}"]',
                "content_sha256": sha256_bytes(item["source_text"].encode("utf-8")),
            },
        )

    prototype_records = [record for record in inventory if record["artifact_id"] == "SRC-ART-PROTOTYPE"]
    if not prototype_records:
        raise SystemExit("prototype deterministic inventory is empty")
    add_requirement(
        "SRC-PROTOTYPE-UI",
        inventory_record=prototype_records[0],
        summary="冻结原型的视觉令牌、DOM 锚点、控件交互和双视口捕获合同。",
        dimension="visual",
        node_refs=["Z1"],
        acceptance_refs=["Z1/AC-01", "Z1/AC-02"],
        required_lanes=["visual-fidelity"],
        release_refs=["M45", "R8"],
        semantic_source={"locator": ":root + declared data-* anchors", "content_sha256": PROTOTYPE_SHA},
    )

    prototype_text = PROTOTYPE.read_text(encoding="utf-8")
    root_match = re.search(r":root\s*\{(?P<body>.*?)\}", prototype_text, re.DOTALL)
    if root_match is None:
        raise SystemExit("prototype is missing its :root token block")
    tokens = re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", root_match.group("body"))
    if not tokens:
        raise SystemExit("prototype visual token inventory is empty")
    visual_tokens = []
    for name, raw_value in tokens:
        value = raw_value.strip()
        literal = f"{name}:{value}"
        visual_tokens.append({"name": name, "value": value, "locator": f"style:first-of-type::token({name})", "content_sha256": sha256_bytes(literal.encode("utf-8"))})

    anchor_nodes = {
        "data-screen": ["H1", "I1", "L1", "P1", "S1"],
        "data-screen-panel": ["H1", "I1", "L1", "P1", "S1"],
        "data-batch": ["D1", "I1", "I2"],
        "data-del": ["I4", "I5"],
        "data-set-pane": ["S1", "S2", "S3", "S4", "S5", "D3"],
        "data-asset-add-project": ["L5"],
        "data-edl-view": ["P2", "P3"],
        "data-copy-report": ["C3", "S3"],
        "data-preserved-k": ["K1", "K2", "K3", "K4", "K5", "K6"],
    }
    dom_anchors = []
    for attribute, related_nodes in anchor_nodes.items():
        values = sorted(set(re.findall(rf'{re.escape(attribute)}="([^"]+)"', prototype_text)))
        if not values and attribute not in prototype_text:
            raise SystemExit(f"prototype anchor missing: {attribute}")
        if not values:
            values = ["present"]
        for value in values:
            literal = attribute if value == "present" else f'{attribute}="{value}"'
            key = re.sub(r"[^A-Z0-9]+", "-", f"{attribute}-{value}".upper()).strip("-")
            bound_nodes = [node_id for node_id in related_nodes if value == "present" or value.lower() in {node_id.lower(), "home", "inbox", "library", "project", "settings", "timeline", "text", "paths", "agent", "asr", "budget", "account", "doctor", "a", "b", "c", "d1", "d2", "d3"}]
            if not bound_nodes:
                bound_nodes = related_nodes
            dom_anchors.append({"attribute": attribute, "value": value, "node_refs": bound_nodes, "locator": f"[{literal}]" if value != "present" else f"[{attribute}]", "content_sha256": sha256_bytes(literal.encode("utf-8"))})

    interactions = [
        {"id": "INT-NAV-SCREENS", "surface_id": "SURF-DASHBOARD", "control": "主导航", "precondition": "桌面应用已启动", "trigger": "选择工作台、整理台、素材库、项目或设置", "state_change": "唯一 data-screen-panel 成为可见面板", "visible_result": "标题、侧栏当前态和面板同步", "boundary_behavior": "未知目标不改变当前屏", "source_refs": ["SRC-PROTOTYPE-UI", "SRC-CHECKLIST-H1"], "prototype_locators": ["[data-screen]", "[data-screen-panel]"], "acceptance_refs": ["H1/AC-01", "Z1/AC-01"]},
        {"id": "INT-INBOX-BATCHES", "surface_id": "SURF-ORGANIZER", "control": "批次 A/B/C 与确认落点", "precondition": "媒体清单已生成且候选摘要可回读", "trigger": "选择批次并确认项目落点", "state_change": "候选从预览转为一次幂等迁移", "visible_result": "批次来源、目标、数量和回执可见", "boundary_behavior": "清单漂移、碰撞或未确认时禁止移动", "source_refs": ["SRC-PROTOTYPE-UI", "SRC-CHECKLIST-D1", "SRC-CHECKLIST-I1"], "prototype_locators": ["[data-batch=\"a\"]", "[data-batch=\"b\"]", "[data-batch=\"c\"]"], "acceptance_refs": ["D1/AC-01", "I1/AC-01", "I3/AC-01"]},
        {"id": "INT-INBOX-DELETE", "surface_id": "SURF-ORGANIZER", "control": "删除建议、全选和二次确认", "precondition": "四类机器理由已生成候选", "trigger": "勾选候选并二次确认", "state_change": "仅选中候选进入当前系统回收站", "visible_result": "选择数量、回执和恢复入口可见", "boundary_behavior": "永久删除、未选中项、失败回读一律禁止", "source_refs": ["SRC-PROTOTYPE-UI", "SRC-CHECKLIST-I4", "SRC-CHECKLIST-I5"], "prototype_locators": ["[data-del]", "#del-all", "#del-confirm"], "acceptance_refs": ["I4/AC-01", "I5/AC-01", "D2/AC-01"]},
        {"id": "INT-LIBRARY-BROWSE", "surface_id": "SURF-LIBRARY", "control": "三种视图、七类分类、标签和详情主按钮", "precondition": "结构化索引可查询", "trigger": "切换视图、分类、标签或素材详情", "state_change": "查询条件和当前素材改变", "visible_result": "计数、卡片/列表/文本及加入项目动作同步", "boundary_behavior": "空索引和未知素材显示明确空态/错误态", "source_refs": ["SRC-PROTOTYPE-UI", "SRC-CHECKLIST-L1", "SRC-CHECKLIST-L2", "SRC-CHECKLIST-L5"], "prototype_locators": ["[data-lib]", "[data-lib-view]", "[data-asset-add-project]"], "acceptance_refs": ["L1/AC-01", "L2/AC-01", "L5/AC-01"]},
        {"id": "INT-PROJECT-EDL", "surface_id": "SURF-PROJECT", "control": "决策列表、时间线/文本双视图、待补素材与交接包", "precondition": "项目和结构化 EDL 身份可回读", "trigger": "切换 EDL 视图或生成交接包", "state_change": "只改变展示或生成受支持输出，不改第二份权威", "visible_result": "片段、轨道、缺失素材、输出后端和回执可见", "boundary_behavior": "EDL 无效或后端未探测时失败关闭", "source_refs": ["SRC-PROTOTYPE-UI", "SRC-CHECKLIST-P1", "SRC-CHECKLIST-P2", "SRC-CHECKLIST-P3", "SRC-CHECKLIST-P4", "SRC-CHECKLIST-P5"], "prototype_locators": ["[data-edl-view=\"timeline\"]", "[data-edl-view=\"text\"]"], "acceptance_refs": ["P1/AC-01", "P2/AC-01", "P3/AC-01", "P4/AC-01", "P5/AC-01"]},
        {"id": "INT-PROJECT-PRESERVED", "surface_id": "SURF-PROJECT", "control": "锁定、版本、失效、参考、复盘、Brief 与脚本", "precondition": "项目已加载", "trigger": "进入 K1-K6 入口并执行对应动作", "state_change": "项目文档及版本按 expectedRevision 更新", "visible_result": "锁定、diff、回滚、stale、参考和发布记录均可回读", "boundary_behavior": "这些能力不得拆成独立 Studio 路由", "source_refs": ["SRC-PROTOTYPE-UI", *[f"SRC-CHECKLIST-K{i}" for i in range(1, 7)]], "prototype_locators": [f"[data-preserved-k=\"k{i}\"]" for i in range(1, 7)], "acceptance_refs": [f"K{i}/AC-01" for i in range(1, 7)]},
        {"id": "INT-SETTINGS-PANELS", "surface_id": "SURF-SETTINGS", "control": "六个设置面板", "precondition": "本机设置可读", "trigger": "选择存放位置、创意模型、转写、预算、账号或诊断", "state_change": "当前设置面板切换；保存动作带 CSRF 与 revision", "visible_result": "真实配置、能力探测和动态诊断项可见", "boundary_behavior": "不支持与配置错误分开，密钥不回显", "source_refs": ["SRC-PROTOTYPE-UI", "SRC-CHECKLIST-D3", *[f"SRC-CHECKLIST-S{i}" for i in range(1, 6)]], "prototype_locators": [f"[data-set-pane=\"{name}\"]" for name in ("paths", "agent", "asr", "budget", "account", "doctor")], "acceptance_refs": ["D3/AC-01", "S1/AC-01", "S2/AC-01", "S3/AC-01", "S4/AC-01", "S5/AC-01"]},
        {"id": "INT-LOGIN", "surface_id": "SURF-LOGIN", "control": "登录两步与跳过", "precondition": "桌面本地能力可用", "trigger": "选择上游登录、完成配对或跳过", "state_change": "只改变可选上游会话", "visible_result": "连接状态与本地功能可用状态同时显示", "boundary_behavior": "未登录、撤销、不支持、过期均不降级本地功能", "source_refs": ["SRC-CHECKLIST-A1"], "acceptance_refs": ["A1/AC-01", "S4/AC-01"]},
        {"id": "INT-SETUP", "surface_id": "SURF-SETUP", "control": "四步可重入向导", "precondition": "桌面入口可打开", "trigger": "逐步配置位置、运行环境、编辑器、账号与设备", "state_change": "每步状态原子保存", "visible_result": "进度、失败点、重试和完成态可见", "boundary_behavior": "中断后从最后成功步骤恢复", "source_refs": ["SRC-CHECKLIST-A2"], "acceptance_refs": ["A2/AC-01", "A2/AC-02"]},
        {"id": "INT-CLOUD-STATES", "surface_id": "SURF-CLOUD", "control": "网页中台任务状态", "precondition": "用户已主动配对上游", "trigger": "读取或刷新任务", "state_change": "上游投影状态更新", "visible_result": "queued/running/completed/failed/expired/cancelled 均有明确文案", "boundary_behavior": "会话失效只清除上游能力，不影响本地项目", "source_refs": ["SRC-CHECKLIST-C2"], "acceptance_refs": ["C2/AC-01", "C2/AC-02"]},
    ]

    api_mapping = [
        {"id": "API-BOOTSTRAP", "method": "GET", "path": "/api/bootstrap", "status": "existing", "schema": "csrfToken, projects, contract", "revision": "none", "csrf": "read-only", "receipt": "ok + bootstrap snapshot", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-HEALTH", "method": "GET", "path": "/api/health", "status": "existing", "schema": "status, localOnly", "revision": "none", "csrf": "read-only", "receipt": "ok + ready", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-SETTINGS", "method": "GET", "path": "/api/settings", "status": "existing", "schema": "settings projection", "revision": "none", "csrf": "read-only", "receipt": "ok + settings", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-PROJECT", "method": "GET", "path": "/api/projects/:id", "status": "existing", "schema": "project projection including documents", "revision": "none", "csrf": "read-only", "receipt": "ok + project", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-ASSETS", "method": "GET", "path": "/api/assets?category=&tags=", "status": "existing", "schema": "asset_library_index.schema.json projection", "revision": "none", "csrf": "read-only", "receipt": "ok + assets + query", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-ASSET-STATS", "method": "GET", "path": "/api/assets/statistics", "status": "existing", "schema": "statistics by category/tag/use", "revision": "none", "csrf": "read-only", "receipt": "ok + statistics", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-INBOX-PLAN", "method": "POST", "path": "/api/projects/:id/inbox-plan", "status": "existing", "schema": "inbox_batch_plan.schema.json", "revision": "manifest digest", "csrf": "X-Content-OS-CSRF", "receipt": "ok + read-only plan", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-INBOX-CONFIRM", "method": "POST", "path": "/api/projects/:id/inbox-plan/confirm", "status": "new", "schema": "planDigest, batchId, targetProjectId, expectedRevision", "revision": "required", "csrf": "X-Content-OS-CSRF", "receipt": "promotion receipt + journal identity", "source": "planned by D1/I1/T1"},
        {"id": "API-DELETE-RECOMMEND", "method": "POST", "path": "/api/projects/:id/media-delete/recommendations", "status": "existing", "schema": "manifest -> four-reason candidates", "revision": "manifest digest", "csrf": "X-Content-OS-CSRF", "receipt": "ok + candidates", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-DELETE-CONFIRM", "method": "POST", "path": "/api/projects/:id/media-delete/confirm", "status": "existing", "schema": "selectedCandidateNumbers, secondConfirmation", "revision": "candidate digest", "csrf": "X-Content-OS-CSRF", "receipt": "system-trash receipt per file", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-DOCUMENT-ACTION", "method": "POST", "path": "/api/projects/:id/documents/:name/:action", "status": "existing", "schema": "patch|lock|unlock|rollback|ai-patch", "revision": "expectedRevision required for writes", "csrf": "X-Content-OS-CSRF", "receipt": "ok + updated project", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-DOCUMENT-DIFF", "method": "GET", "path": "/api/projects/:id/documents/:name/diff?from=&to=", "status": "existing", "schema": "unified diff text", "revision": "version pair", "csrf": "read-only", "receipt": "ok + diff", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-PROVIDER", "method": "POST", "path": "/api/settings/model-providers", "status": "existing", "schema": "provider, model, endpoint, reasoning, credentialRef", "revision": "configuration identity", "csrf": "X-Content-OS-CSRF", "receipt": "ok + redacted settings", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-ARCHIVE", "method": "POST", "path": "/api/settings/archive/{lifecycle|locations}", "status": "existing", "schema": "lifecycle or physical location + manifest readback", "revision": "configuration identity", "csrf": "X-Content-OS-CSRF", "receipt": "ok + archive projection", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-UPSTREAM", "method": "POST", "path": "/api/settings/upstream/{pair|refresh|logout}", "status": "existing", "schema": "opaque session reference projection", "revision": "session generation", "csrf": "X-Content-OS-CSRF", "receipt": "ok + secret-free upstream state", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-CHATCUT", "method": "POST", "path": "/api/settings/chatcut/{probe|confirm}", "status": "existing", "schema": "Desktop MCP capability state", "revision": "probe identity", "csrf": "X-Content-OS-CSRF", "receipt": "ok + chatcut state", "source": "99_System_OpenClaw/desktop/server.py"},
        {"id": "API-DOCTOR", "method": "GET", "path": "/api/diagnostics", "status": "new", "schema": "dynamic checks array + report digest", "revision": "none", "csrf": "read-only", "receipt": "ok + checks, no fixed count", "source": "planned by S3/C3"},
        {"id": "API-BUDGET", "method": "GET/POST", "path": "/api/settings/analysis-budget", "status": "new", "schema": "analysis_tiering.schema.json", "revision": "expectedRevision on POST", "csrf": "X-Content-OS-CSRF on POST", "receipt": "ok + effective budget", "source": "planned by S1/T4"},
        {"id": "API-ASSET-ADD", "method": "POST", "path": "/api/projects/:id/assets", "status": "new", "schema": "assetId, intendedUse, expectedRevision", "revision": "expectedRevision required", "csrf": "X-Content-OS-CSRF", "receipt": "ok + project asset reference", "source": "planned by L5/T5"},
        {"id": "API-WIZARD", "method": "GET/POST", "path": "/api/setup/state", "status": "new", "schema": "four-step resumable setup state", "revision": "expectedRevision on POST", "csrf": "X-Content-OS-CSRF on POST", "receipt": "ok + persisted step state", "source": "planned by A2/T5"},
        {"id": "API-CLOUD-TASKS", "method": "GET", "path": "/api/upstream/tasks", "status": "new", "schema": "queued|running|completed|failed|expired|cancelled", "revision": "upstream snapshot generation", "csrf": "read-only after optional pairing", "receipt": "ok + task projections", "source": "planned by C1/C2/C3"},
    ]

    surfaces = [
        {
            "surface_id": surface_id,
            "name": name,
            "routes": [route],
            "states": ["loading", "empty", "error", "ready", "success"],
            "viewports": ["1440x900", "390x844"],
            "item_refs": [item_id for item_id in ITEM_IDS if ITEM_SURFACE[item_id] == surface_id],
        }
        for surface_id, (name, route) in SURFACES.items()
    ]
    captures = [
        {"surface_id": surface["surface_id"], "route": surface["routes"][0], "locale": "zh-CN", "theme": "dark", "viewport": viewport, "dataset": "prototype-frozen-v2", "baseline_policy": "render source prototype and candidate with identical data; store both images and pixel report in the run evidence directory"}
        for surface in surfaces
        for viewport in ("1440x900", "390x844")
    ]

    releases = []
    all_requirement_refs = [str(record["requirement_id"]) for record in requirements]
    releases.append(
        {
            "release_id": "M45",
            "release_class": "source-defined",
            "source_defined": True,
            "completion_authority": "source",
            "source_completion_requirement_refs": all_requirement_refs,
            "status": "NOT_READY",
            "lane_evidence": [],
        }
    )
    for release_id in [f"R{index}" for index in range(1, 9)]:
        refs = [
            requirement["requirement_id"]
            for requirement in requirements
            if release_id in requirement["release_refs"]
        ]
        releases.append(
            {
                "release_id": release_id,
                "release_class": "local-candidate",
                "source_defined": False,
                "completion_authority": "ssot-release-owner",
                "candidate_of": "M45",
                "source_completion_requirement_refs": refs,
                "status": "NOT_READY",
                "lane_evidence": [],
            }
        )
    return (
        {
            "schema_version": 2,
            "artifacts": artifacts,
            "inventory": inventory,
            "requirements": requirements,
            "releases": releases,
            "scope_deviations": [],
            "visual_contract": {
                "tokens": visual_tokens,
                "font_families": ["Archivo", "Asap", "JetBrains Mono"],
                "dom_anchors": dom_anchors,
                "computed_style_assertions": [
                    "每个 :root 令牌的计算值与冻结原型一致",
                    "桌面和移动视口不得横向溢出、遮挡或改变主要操作位置",
                    "focus、disabled、danger、AI、success 状态保留原型语义",
                ],
                "capture_matrix": captures,
            },
            "interaction_catalog": interactions,
            "api_mapping": api_mapping,
            "surfaces": surfaces,
            "runtime_components": [
                {"id": "RT-DESKTOP", "kind": "loopback desktop server", "status": "implemented-partial"},
                {"id": "RT-BROWSER", "kind": "desktop browser frontend", "status": "implemented-partial"},
                {"id": "RT-UPSTREAM", "kind": "optional upstream identity", "status": "external-evidence-required"},
                {"id": "RT-CHATCUT", "kind": "Desktop local MCP", "status": "external-evidence-required"},
                {"id": "RT-TRASH", "kind": "operating-system recycle bin", "status": "platform-evidence-required"},
                {"id": "RT-ARCHIVE", "kind": "user-selected physical locations", "status": "physical-readback-required"},
            ],
            "governance_dependencies": {
                "design_acceptance_contract_ref": ".harness/overlays/project-harness-adapter.yaml",
                "runtime_visual_verification_ref": ".harness/overlays/project-harness-adapter.yaml",
                "visual_collaboration_contract_ref": ".harness/overlays/project-harness-adapter.yaml",
            },
        },
        item_to_ref,
    )


def main() -> None:
    for directory in (
        BUNDLE / ".ssot/nodes",
        BUNDLE / ".ssot/edges",
        BUNDLE / ".ssot/assumptions",
        BUNDLE / ".ssot/conflicts",
        BUNDLE / ".ssot/view-sources",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    source_requirements, item_source_refs = create_strict_source_documents()
    source_docs = {"source_requirements": source_requirements}
    write_json(BUNDLE / ".ssot/source-requirements.json", source_requirements)
    for retired in (
        "surface-inventory.json",
        "visual-fidelity-contract.json",
        "interaction-matrix.json",
        "action-vertical-slices.json",
        "runtime-topology.json",
    ):
        (BUNDLE / ".ssot" / retired).unlink(missing_ok=True)
    nodes, edges, release_nodes = build_nodes_and_edges()
    all_source_refs = [item["requirement_id"] for item in source_requirements["requirements"]]
    for item_id, source_refs in item_source_refs.items():
        nodes[item_id]["source_requirement_refs"] = source_refs
    nodes["F"]["source_requirement_refs"] = all_source_refs
    nodes["Z1"]["source_requirement_refs"] = all_source_refs
    for release_id in [f"R{index}" for index in range(1, 8)]:
        nodes[f"Q{release_id[1:]}"]["source_requirement_refs"] = sorted(
            {ref for item_id in RELEASE_ITEMS[release_id] for ref in item_source_refs[item_id]}
        )
    for old in (BUNDLE / ".ssot/nodes").glob("*.json"):
        old.unlink()
    for old in (BUNDLE / ".ssot/edges").glob("*.json"):
        old.unlink()
    for node_id, node in nodes.items():
        write_json(BUNDLE / ".ssot/nodes" / f"{node_id}.json", node)
    for edge in edges:
        write_json(BUNDLE / ".ssot/edges" / f"{edge['edge_id']}.json", edge)
    write_text(BUNDLE / ".ssot/assumptions/.gitkeep", "")
    write_text(BUNDLE / ".ssot/conflicts/.gitkeep", "")

    planning = build_planning(nodes, release_nodes)
    planning["source_inputs"] = [
        {
            "external_dependency_id": "EXT-CHECKLIST",
            "path": CHECKLIST.relative_to(ROOT).as_posix(),
            "commit": BASELINE,
            "sha256": CHECKLIST_SHA,
        },
        {
            "external_dependency_id": "EXT-PROTOTYPE",
            "path": PROTOTYPE.relative_to(ROOT).as_posix(),
            "commit": BASELINE,
            "sha256": PROTOTYPE_SHA,
        },
    ]
    external_kinds = {
        "EXTSYS-UPSTREAM": ("external-runtime", ["upstream-session"]),
        "EXTSYS-CHATCUT": ("persistent-runtime", ["chatcut-desktop-mcp"]),
        "EXTSYS-DASHSCOPE": ("external-runtime", ["transcription-provider"]),
        "EXTSYS-FUNASR": ("local-runtime", ["local-transcription-runtime"]),
        "EXTSYS-MODEL-PROVIDERS": ("external-runtime", ["creative-provider-runtime"]),
        "EXTSYS-SYSTEM-TRASH": ("local-runtime", ["media-trash-flow"]),
        "EXTSYS-PHYSICAL-STORAGE": ("persistent-runtime", ["archive-location-readback"]),
    }
    planning["external_systems"] = []
    for external_id, (kind, components) in external_kinds.items():
        refs = [
            str(requirement["requirement_id"])
            for requirement in source_requirements["requirements"]
            if external_id in requirement.get("external_system_refs", [])
        ]
        planning["external_systems"].append(
            {
                "external_system_id": external_id,
                "kind": kind,
                "runtime_components": components,
                "source_requirement_refs": refs,
            }
        )
    source_release_refs = {
        str(release["release_id"]): list(release["source_completion_requirement_refs"])
        for release in source_requirements["releases"]
    }
    for release in planning["release_slices"]:
        release["source_completion_requirement_refs"] = source_release_refs.get(release["id"], [])
        if release["id"] == "R8":
            release["node_ids"] = [node_id for node_id in release["node_ids"] if node_id != "RZ"]
    for wave in planning["waves"]:
        if wave["release_id"] == "R8":
            wave["node_ids"] = [node_id for node_id in wave["node_ids"] if node_id != "RZ"]
    planning["release_slices"].append(
        {
            "id": "M45",
            "macro_phase_id": "P2",
            "title": "来源定义的 45 项完整里程碑",
            "user_value": "所有已确认来源要求都已接受。",
            "independent_acceptance": "每项来源要求的必需证据通道均通过。",
            "independent_failure": "保持未晋升。",
            "future_phase_required_for_success": False,
            "development_baseline": f"commit@{BASELINE}",
            "promotion_baseline": f"origin/main:{BASELINE}:must-refetch",
            "release_candidate": "source-milestone:m45:pending",
            "node_ids": ["RZ"],
            "source_completion_requirement_refs": source_release_refs["M45"],
        }
    )
    write_json(BUNDLE / ".ssot/planning-compiler.json", planning)
    build_source_notes()
    build_acceptance(nodes)

    main_view = render_main(nodes, edges, release_nodes, source_docs)
    source_view = BUNDLE / ".ssot/view-sources/00-main.md"
    write_text(source_view, main_view)
    shutil.copyfile(source_view, BUNDLE / "ssot-development-paths.md")

    manifest = {
        "ssot_schema_version": 2,
        "artifact_class": "ssot-development",
        "plan_version": 1,
        "dag_version": 1,
        "interface_freeze_version": 1,
        "node_contract_version": 1,
        "machine_validation_profile": "release",
        "generated_main": "../ssot-development-paths.md",
        "generated_views": [
            {
                "view_id": "main",
                "source": "view-sources/00-main.md",
                "source_sha256": sha256_file(source_view),
                "output": "../ssot-development-paths.md",
            }
        ],
        "nodes_dir": "nodes",
        "edges_dir": "edges",
        "assumptions_dir": "assumptions",
        "conflicts_dir": "conflicts",
        "external_dependencies": [
            {
                "external_dependency_id": "EXT-CHECKLIST",
                "authority_path": CHECKLIST.relative_to(ROOT).as_posix(),
                "authority_commit": BASELINE,
                "authority_sha256": CHECKLIST_SHA,
                "required_state": "ACCEPTED",
                "consumers": ["F", *sorted({node_id for requirement in source_requirements["requirements"] if requirement["source"]["artifact_id"] == "SRC-ART-CHECKLIST" for node_id in requirement["node_refs"]})],
            },
            {
                "external_dependency_id": "EXT-PROTOTYPE",
                "authority_path": PROTOTYPE.relative_to(ROOT).as_posix(),
                "authority_commit": BASELINE,
                "authority_sha256": PROTOTYPE_SHA,
                "required_state": "ACCEPTED",
                "consumers": ["F", *sorted({node_id for requirement in source_requirements["requirements"] if requirement["source"]["artifact_id"] == "SRC-ART-PROTOTYPE" for node_id in requirement["node_refs"]})],
            },
        ],
        "normative_executable_artifact_contract": {
            "mode": "strict",
            "source_milestone_authority": "source",
            "source_requirements": "source-requirements.json",
        },
    }
    write_json(BUNDLE / ".ssot/manifest.json", manifest)
    write_json(
        BUNDLE / "ssot-archive.json",
        {
            "schema_version": 1,
            "artifact_class": "ssot-development",
            "artifact_date": "2026-09-02",
            "project_name": "photo-content-os",
            "ssot_name": "openclaw-media-full-checklist-implementation",
            "main_document": "ssot-development-paths.md",
            "problem_documents": [],
        },
    )
    write_text(
        BUNDLE / "implementation-progress.md",
        """# 实施进度

- 来源清单条目：45；来源 HTML 与原型均以内容校验值冻结。
- 已接受产品决定：11（包括转写策略：DashScope 默认、本机 FunASR 失败兜底）。
- 实现状态：部分实现；不得从代码修改数量推断 45 项完成。
- 验收合同：46 份仍为 DRAFT，受保护的自动验收基线尚未锁定。
- 机器验证：必须以本次生成后的统一验证输出为准；历史临时 Skill 报告不构成通过证据。
- 人工验收：OCM-Z1 尚未提交，不能由自动化代填为通过。
- 完成判定：未完成。

这份文件只是运行投影，机器权威仍是 `.ssot/` 内的记录。
""",
    )
    print(json.dumps({"bundle": str(BUNDLE), "items": len(ITEMS), "nodes": len(nodes), "edges": len(edges)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
