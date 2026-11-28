"""Package constants."""

from __future__ import annotations
import json
from pathlib import Path
import re

# --- direct_style_contract.py ---
COLUMN_FIELDS = ('visual', 'subtitle', 'camera', 'audio')
SHORT_FIELDS = {
    'motionSummary': {'type': ['string', 'null'], 'maxLength': 30},
    'bannedShort': {'type': ['array', 'null'], 'minItems': 1, 'maxItems': 8,
                    'items': {'type': 'string', 'minLength': 1, 'maxLength': 12}},
    'source': {'oneOf': [
        {'type': 'null'},
        {'type': 'object', 'required': ['kind', 'id', 'name', 'instruction'], 'additionalProperties': False,
         'properties': {'kind': {'const': 'library'},
                        **{key: {'type': 'string'} for key in ('id', 'name', 'instruction')}}},
        {'type': 'object', 'required': ['kind', 'projectId', 'title', 'instruction'],
         'oneOf': [{'required': ['jobId']}, {'required': ['draftId']}],
         'properties': {'kind': {'enum': ['inherited', 'adjusted', 'drafted']},
                        **{key: {'type': 'string'} for key in ('projectId', 'jobId', 'draftId', 'title', 'instruction')}}}]},
}
SHOT_INPUT = {'type': 'object', 'required': ['shotId', 'dialogue'], 'properties': {
    'shotId': {'type': 'string', 'pattern': '^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$'},
    'dialogue': {'type': 'string', 'minLength': 1, 'maxLength': 2000},
    **{key: {'type': 'string', 'maxLength': 2000, 'description': 'Trimmed; blank means absent.'} for key in COLUMN_FIELDS}}}
STYLE_BASE = {'oneOf': [
    {'type': 'object', 'required': ['kind', 'projectId', ident], 'additionalProperties': False,
     'properties': {'kind': {'const': kind}, 'projectId': {'type': 'string'}, ident: {'type': 'string'}}}
    for kind, ident in [('job', 'jobId'), ('draft', 'draftId')]] + [
        {'type': 'object', 'required': ['kind', 'id'], 'additionalProperties': False,
         'properties': {'kind': {'const': 'library'}, 'id': {'type': 'string'}}}]}

# --- ai_patch.py ---
SYSTEM_PROMPT = """你是 Photo Content OS 的区块编辑代理。
只修改用户明确选中的区块，不得输出未选区块，不得改变区块 ID，不得解释过程。

写作规范：
1. 先读 read_only_context；它包含当前文档、项目与同账号历史复盘，只能作为修改约束，不能被改写。current_project 中的平台、账号和人设是明确记录的写作边界：按目标平台和该账号人设改写；人设为空时不得猜测。接住这份文档已有的说话方式：称呼、句长、语气和用词习惯；改出来的段落要像同一个作者写的，不要换一副腔调。
2. 只改指令要求改的部分；指令没提到的句子，能保留原句就保留原句，不做顺手润色。
3. 口播、台词、字幕类区块必须写成能直接读出声的话：一句尽量不超过 22 个字，允许口语连接词和自然的不完整句。
4. 禁止书面套话和 AI 腔：不用『首先/其次/最后』连用、『总之』『综上所述』『值得一提的是』『不难发现』，不写连续排比，不给每句加感叹号，不堆与内容无关的网络热词。
5. 事实边界：不得新增素材、地点、人物、成绩或时间等文档里没有的事实；需要新事实时在正文用（待确认：……）标出，而不是编造。

输出严格 JSON：{"replacements":{"block-id":"新的正文"}}。不得使用 Markdown 代码围栏。"""

# --- analysis_budget.py ---
ANALYSIS_BUDGET_SCHEMA_VERSION = "analysis_budget_settings_v1"
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

# --- api_contract.py ---
ROUGH_CUT_ROUTE_SPECS: tuple[dict[str, object], ...] = (
    {'method': 'GET', 'path': '/api/review/pieces/{id}/roughcut', 'operation_id': 'getRoughcut', 'summary': 'Read the version-bound roughcut plan'},
    {'method': 'POST', 'path': '/api/review/pieces/{id}/roughcut/commands', 'operation_id': 'commandRoughcut', 'summary': 'Accept a CAS-bound roughcut command (202)', 'write': True},
    {'method': 'GET', 'path': '/api/review/roughcut-jobs/{jobId}', 'operation_id': 'getRoughcutJob', 'summary': 'Read an owned roughcut job'},
    {'method': 'POST', 'path': '/api/review/roughcut-jobs/{jobId}', 'operation_id': 'stopRoughcutJob', 'summary': 'Stop only this roughcut job (202)', 'write': True},
    {'method': 'GET', 'path': '/api/review/editing-presets', 'operation_id': 'getEditingPresets', 'summary': 'Read built-in and local editing recipes'},
    {'method': 'POST', 'path': '/api/review/editing-presets', 'operation_id': 'saveEditingPreset', 'summary': 'Save a cross-project recipe with CAS (201)', 'write': True},
    {'method': 'GET', 'path': '/api/review/pieces/{id}/editor-capabilities', 'operation_id': 'getRoughcutEditorCapabilities', 'summary': 'Read R228 choice and roughcut capabilities'},
    {'method': 'POST', 'path': '/api/review/pieces/{id}/roughcut/transcriptions', 'operation_id': 'transcribeRoughcutShots', 'summary': 'Accept selected local transcription work (202)', 'write': True},
    {'method': 'POST', 'path': '/api/review/pieces/{id}/roughcut/drafts', 'operation_id': 'createRoughcutDraft', 'summary': 'Generate the saved editor choice in an owned job (202)', 'write': True},
    {'method': 'POST', 'path': '/api/review/pieces/{id}/roughcut/drafts/open', 'operation_id': 'openRoughcutDraft', 'summary': 'Open only this piece latest current Kdenlive project', 'write': True},
    {'method': 'GET', 'path': '/api/review/pieces/{id}/roughcut/media/{artifactId}', 'operation_id': 'getRoughcutMedia', 'summary': 'Read a bound derived roughcut artifact', 'response_media': 'video/mp4', 'byte_ranges': True},
)
WORK_DELETE_OPERATIONS = {'previewProjectDeletion', 'deleteProjects', 'listDeletedProjects',
                          'restoreProjects', 'restoreProject', 'dismissDeletedProject'}

# --- archive_location_config.py ---
ARCHIVE_LOCATION_CONFIG_SCHEMA_VERSION = 1
CONFIG_FILE_NAME = "archive_location_config.json"

# --- chatcut_mcp.py ---
PROBE_COMMAND = ("codex", "mcp", "get", "chatcut_desktop")
DEFAULT_PROBE_TIMEOUT_SECONDS = 3.0
MAX_PROBE_TIMEOUT_SECONDS = 5.0
CHATCUT_MCP_SCHEMA_VERSION = "chatcut_desktop_local_mcp_v1"

# --- direct_handoff_contract.py ---
MAX_DESCRIPTOR_BYTES = 2 * 1024 * 1024
DIRECT_HANDOFF_CONTRACT_SAFE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}')
RUN_RECORD_SCHEMA = 'p1a_run_record_v1'
RUN_RECORD_KEYS = frozenset({
    'schema', 'job_id', 'device_id', 'project_id', 'project_revision', 'binding_id', 'binding_generation',
    'confirmation_ref', 'handoff_digest', 'input_ref', 'catalog_digest', 'identity', 'workspace_ref',
    'project_root_ref', 'source_refs', 'steps', 'candidate_ref', 'request_id', 'delivered_at'})
RUN_RECORD_IDENTITY_KEYS = RUN_RECORD_KEYS - {'source_refs', 'steps', 'delivered_at'}
HANDOFF_REF = {'type': 'object', 'required': ['jobId', 'revision'], 'additionalProperties': False,
               'properties': {'jobId': {'type': 'string'}, 'revision': {'type': ['integer', 'null'], 'minimum': 1,
                   'description': 'Top-level storyboardRevision; null when absent or invalid. A null request revision compares jobId only.'}}}

# --- direct_recipes.py ---
CATEGORIES = [('opening', '开场'), ('typography', '文字'), ('ui-entrance', '界面入场'),
              ('transition', '转场'), ('rhythm', '节奏'), ('data', '数据'),
              ('effects', '特效'), ('interaction', '交互'), ('camera', '运镜'), ('outro', '收尾')]

# --- direct_revision_contract.py ---
LINE = {'type': 'object', 'required': ['text'], 'additionalProperties': False,
        'properties': {'text': {'type': 'string', 'minLength': 1, 'maxLength': 200},
                       'boxId': {'type': 'string'}, 'action': {'enum': ['main', 'dim', 'del', 'short']},
                       'issue': {'enum': ['space', 'color', 'sync']}, 'own': {'const': True}},
        'oneOf': [{'required': ['boxId', 'action']}, {'required': ['issue']}, {'required': ['own']}]}
REQUEST = {'type': 'object', 'required': ['lines'], 'properties': {
    'lines': {'type': 'array', 'minItems': 1, 'maxItems': 200, 'items': LINE}},
    'description': 'Each line is nonblank. Combined text length is 1–200 Unicode characters. boxId must identify a current visible box.'}
VERIFY = {'type': ['object', 'null'], 'required': ['status', 'items'], 'properties': {
    'status': {'enum': ['running', 'done', 'failed']}, 'failureCode': {'const': 'verify_failed'},
    'items': {'type': 'array', 'items': {'type': 'object', 'required': ['index', 'result', 'reason'], 'properties': {
        'index': {'type': 'integer', 'minimum': 0}, 'result': {'enum': ['done', 'missed']}, 'reason': {'type': 'string'}}}}}}
LOOK = {'type': 'object', 'required': ['status', 'failureCode', 'findings'], 'properties': {
    'status': {'enum': ['none', 'running', 'done', 'failed']}, 'failureCode': {'enum': [None, 'look_failed']},
    'findings': {'type': 'array', 'maxItems': 5, 'items': {'type': 'object', 'required': ['boxId', 'kind', 'text', 'suggest'],
        'properties': {'boxId': {'type': ['string', 'null']}, 'kind': {'type': 'string'}, 'text': {'type': 'string'},
                       'suggest': {'enum': ['main', 'dim', 'del', 'short']}}}}}}
SHOT_PROPERTIES = {
    'currentVersion': {'type': 'integer', 'minimum': 0, 'description': 'Zero before the first written version. A version whose rendering failed retains its code without a poster.'},
    'versions': {'type': 'array', 'items': {'type': 'object', 'required': ['version', 'baseVersion', 'createdAt', 'posterRevision', 'codeChars', 'request', 'verify'],
        'properties': {'version': {'type': 'integer', 'minimum': 1}, 'createdAt': {'type': 'string'},
                       'baseVersion': {'type': ['integer', 'null'], 'minimum': 1,
                                       'description': 'Current version before revision or narration rerender. Null for the first version or unavailable pre-field provenance.'},
                       'posterRevision': {'type': 'integer'}, 'codeChars': {'type': 'integer'},
                       'request': {'anyOf': [REQUEST, {'type': 'null'}]}, 'verify': VERIFY}}},
    'boxes': {'type': 'array', 'items': {'type': 'object', 'required': ['id', 'name', 'x', 'y', 'w', 'h'],
        'properties': {'id': {'type': 'string'}, 'name': {'type': 'string'},
                       **{key: {'type': 'number'} for key in ('x', 'y', 'w', 'h')}}}},
    'look': LOOK, 'sample': {'type': 'boolean'},
}

# --- direct_video.py ---
JOB_FIELDS = ('jobId', 'projectId', 'model', 'status', 'createdAt', 'updatedAt', 'failureCode',
              'design', 'shots', 'narration', 'output')
SHOT_FIELDS = ('shotId', 'dialogue', 'mainAction', 'estimatedSeconds', 'measuredSeconds', 'timingSource',
               'status', 'failureCode', 'attempts', 'lastInstruction', 'writingStartedAt', 'writtenAt', 'renderedAt',
               'codeChars', 'posterRevision', 'checks', 'visual', 'subtitle', 'camera', 'audio', 'fromDraft', 'currentVersion', 'versions', 'boxes', 'look', 'sample')
PATH_TEXT = re.compile(r'(?:[A-Za-z]:[\\/][^\s"<>]+|/(?:[^\s/"<>]+/)+[^\s"<>]*)')

# --- edl_bridge.py ---
EDL_BRIDGE_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
AUTHORITY_FILE = "06_edit_decision_list.json"
BRIDGE_SCHEMA_VERSION = "studio_edl_bridge_v1"
VALIDATOR = "edl_contract.normalise_edl"
EDL_SCHEMA_VERSIONS = frozenset({"edit_decision_list_v1", "edit_decision_list_v2"})
EDL_SCHEMA_PATH = EDL_BRIDGE_SCRIPTS_DIR.parent / "schemas" / "edit-decision-list.schema.json"

# --- media_review.py ---
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
SCENE_NAMES = json.loads((Path(__file__).parent / 'static/scene-names.json').read_text())
STATES = ('selected', 'usable', 'unused', 'rejected')
DECISIONS = {'精选': 'selected', '可用': 'usable', '不用': 'unused'}

# --- model_provider_config.py ---
MODEL_PROVIDER_CONFIG_SCHEMA_VERSION = "model_provider_config_v2"
LEGACY_SCHEMA_VERSION = "model_provider_config_v1"
SUPPORTED_SCHEMA_VERSIONS = frozenset({LEGACY_SCHEMA_VERSION, MODEL_PROVIDER_CONFIG_SCHEMA_VERSION})
DEFAULT_CONFIG_FILENAME = "model-provider-config.json"
DEFAULT_REASONING_EFFORT = "xhigh"

# --- onboarding_state.py ---
ONBOARDING_STATE_SCHEMA_VERSION = "photo_content_os_onboarding_v1"
STATE_FILE_NAME = "onboarding_state.json"
VERSIONED_STATE_FILE_NAME = "onboarding_state_versioned.json"
VERSIONED_SCHEMA_VERSION = "photo_content_os_onboarding_versioned_v1"

# --- project_store.py ---
PROJECT_STORE_SCHEMA_VERSION = "creative_project_store_v1"
PROJECT_SCHEMA_VERSION = "creative_project_v1"
DOCUMENT_NAMES = ("brief", "script", "storyboard", "edl")
DOCUMENT_LABELS = {"brief": "创作 Brief", "script": "脚本", "storyboard": "分镜", "edl": "剪辑方案"}
DOWNSTREAM = {"brief": ("script", "storyboard", "edl", "delivery"), "script": ("storyboard", "edl", "delivery"), "storyboard": ("edl", "delivery"), "edl": ("delivery",)}
PROJECT_STORE_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{7,63}$")
PUBLISHING_METRICS = ("views", "likes", "comments", "shares", "saves", "follows")
MAX_PUBLIC_LINKS = 8
LOCAL_ABSOLUTE_PATH = re.compile(r"(?:^|\s)(?:/(?:Users|home|private|var|Volumes)/|[A-Za-z]:[\\/])")
REFERENCE_ASSET_ROLE = "reference"
AUTHORITY_BRIDGE_SCHEMA_VERSION = "document_authority_bridge_v1"
AUTHORITY_BRIDGE_TARGETS = {"brief": "02_project_brief.md", "script": "04_script.md"}
DEFAULTS = {
    "brief": (("brief-goal", "创作目标"), ("brief-audience", "目标受众"), ("brief-angle", "核心角度"), ("brief-constraints", "平台与边界")),
    "script": (("script-hook", "开头钩子"), ("script-body", "主体推进"), ("script-ending", "结尾与行动")),
    "storyboard": (("storyboard-opening", "开场镜头"), ("storyboard-development", "展开镜头"), ("storyboard-ending", "收束镜头")),
    "edl": (("edl-plan", "剪辑顺序"), ("edl-captions", "字幕与声音"), ("edl-notes", "人工精剪提示")),
}

# --- roughcut.py ---
TECHNIQUES = ('jcut','bed','duck','pause','action')
BEAT_WAIT_TIMEOUT_SEC = 30 * 60
BEAT_POLL_MAX_SEC = 30

# --- roughcut_drafts.py ---
PLANNER_VERSION = '1.0'
FPS = 30

# --- roughcut_store.py ---
SCHEMAS = {name: json.loads((Path(__file__).resolve().parents[1] / 'schemas' / name).read_text()) for name in
           ('roughcut-api.schema.json', 'editing-presets.schema.json')}
VALIDATORS = {}
NOTICE_GROUPS = {
    'N1': 'csrf_invalid origin_forbidden host_forbidden body_invalid revision_invalid request_invalid roughcut_command_invalid roughcut_job_action_invalid music_count_invalid playlist_invalid preset_not_found preset_invalid occurrence_not_found overrides_invalid swap_boundary_invalid transcript_selection_invalid project_not_found roughcut_job_not_found',
    'N2': 'revision_conflict roughcut_inputs_stale', 'N3': 'selection_not_confirmed',
    'N4': 'roughcut_state_unreadable roughcut_job_unreadable settings_invalid builtin_presets_invalid shots_invalid',
    'N5': 'preset_write_failed', 'N6': 'beat_analysis_unavailable beat_map_missing',
    'N7': 'song_too_short', 'N8': 'transcription_unavailable transcript_failed',
    'N9': 'transcript_unreadable transcript_invalid',
    'N10': 'editor_diagnostics_unreadable editor_readiness_invalid',
    'N11': 'draft_failed runtime_unavailable', 'N12': 'preview_failed',
    'N13': 'edl_provenance_required',
}
TITLES = dict(zip(NOTICE_GROUPS, ('这次操作没成功','这件作品刚在别处改过','精选还没确认','读不到这件作品的粗剪记录','这个预设没存上','拍子分析还不能用','这首歌比粗剪短，排不下','这几段自拍没转写成','读不到自拍的转写结果','读不到剪辑软件的状态','草稿没出成','预览没生成出来','这件作品还不能出草稿')))
CODE_NOTICE = {code: group for group, codes in NOTICE_GROUPS.items() for code in codes.split()}

# --- server.py ---
SERVER_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
STATIC_ROOT = Path(__file__).resolve().parent / "static"
MAX_BODY_BYTES = 2 * 1024 * 1024
SETTINGS_DIRNAME = "settings"
ASSET_LIBRARY_DIRNAME = "asset-library"
TRASH_RECEIPT_SCHEMA_VERSION = "studio_trash_receipts_v1"
INBOX_MANIFEST_RELATIVE_PATH = Path("ai-analysis") / "media-manifest.json"

# --- upstream_identity.py ---
LOCAL_DEVICE_PLATFORMS = frozenset({"macos", "windows", "linux"})
UPSTREAM_DEVICE_PLATFORMS = frozenset({"macos"})

# --- upstream_session.py ---
E4_RESULT_FIELDS = frozenset(
    {
        "upstream_principal_id",
        "roles",
        "revoked",
        "pairing_status",
        "session_ref",
    }
)

# --- work_trash.py ---
ELIGIBILITY_CODES = (
    'folder_not_connected', 'folder_missing', 'folder_outside_media_root',
    'folder_is_media_root', 'folder_symlink', 'folder_formal_project',
    'folder_has_media', 'folder_shared', 'folder_contains_work', 'folder_unreadable', 'folder_runtime_unavailable',
)
RESULT_CODES = ELIGIBILITY_CODES + (
    'project_not_found', 'project_id_invalid', 'revision_conflict', 'revision_invalid',
    'folder_trash_failed', 'trash_item_missing', 'restore_target_occupied',
    'folder_fingerprint_mismatch', 'folder_restore_failed', 'folder_restore_unsafe',
    'deleted_work_not_found', 'deleted_work_recoverable', 'deletion_batch_conflict',
    'review_unreadable',
)
UNRECOVERABLE = {'trash_item_missing', 'restore_target_occupied'}
