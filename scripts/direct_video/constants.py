"""Package constants."""

from __future__ import annotations
from pathlib import Path
import re

# --- media.py ---
FPS = 30

# --- film_templates.py ---
FILM_TEMPLATES_ROOT = Path(__file__).resolve().parent / "film_templates"
COMMIT = "b74e9c9e800cc3158bc16f6e9468f0f560248243"
REPO = "https://github.com/motiontemplates/all"
OPEN_URL = "https://motiontemplates.github.io/385712/downloads/kinetic-tech-zh.motion"
OPEN_SHA256 = "472a95af35f8e0c09c0f7dc2ca0992b7c9a3405c5aa8063730c347fc4e015c21"
OPEN_SIZE = 17596250
OPEN_DEST = Path.home() / ".photo-content-os/media/film_templates/385712/kinetic-tech-zh.motion"
LICENSE_URL = "https://raw.githubusercontent.com/motiontemplates/385712/9dfbe7d7c6a6d4aa03f6f8e2f2285e631099faae/template.json"

# --- generate.py ---
MODEL = 'claude-opus-5-5'
RULES = Path(__file__).with_name('rules') / 'shots.md'
PROMO_RULES = """
## 本片是横屏宣传片（以下几条覆盖上面规则里的对应数字）
- 画布 1920×1080：`html,body{margin:0;width:1920px;height:1080px;overflow:hidden}`。不要按竖屏排、只用左半边：主体占画面宽度 ≥ 50%，横向铺开（左右分栏、居中大字、横排卡片都可以）。
- 安全区：左右各 ≥ 96px，上下各 ≥ 72px；所有文字和关键图形都在 1920×1080 之内，y > 1008 不放东西。上面「底部 y ≥ 1536」那条不适用。
- 构图撑满横屏：主画面落在 y 72–1008 之间的中部，末帧不留超过画面宽度或高度 30% 的空带。上面「竖屏构图要撑满内容区」那条按横屏理解，不把竖屏版式缩在左上角。
- 没有口播：dialogue / visual 是「这一镜要表现什么」，不是台词；text 是画面上要出现的字（可空）。recipeCard 是这一镜的动作配方，照它的结构和节奏做。
- 时长：一小节 {bar} 秒，镜头切在小节线上。D 写成整小节的长度（小节数 × {bar}）；元素在 0.7·D 前出完，最后一个元素不晚于 D − 0.4 秒，之后停在完整画面上。
"""
SAFE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}')

# --- layout.py ---
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
CONTENT_TOP = 200
SUBTITLE_TOP = 1536
CONTENT_BOTTOM = SUBTITLE_TOP - 36
MAX_BOTTOM_GAP = .30

# --- lint.py ---
FORBIDDEN = ('Math.random', 'setTimeout', 'setInterval', 'requestAnimationFrame',
             'fetch(', 'XMLHttpRequest', 'WebSocket', '<video', '<audio', '@import', 'url(')
HALF_PUNCT = re.compile(r'(?<=[一-鿿])[?!,:;]|[?!,:;](?=[一-鿿])')

# --- openmotion_import.py ---
REPOSITORY = "https://github.com/nexu-io/openmotion"
CATALOG = "library/templates/catalog/"
CLIP_PATH = re.compile(r"([a-z0-9-]+)/source/demos/(clip-\d+)\.html")
DEMO_META = re.compile(r"^```motion-demo[ \t]*\n(.*?)^\x60{3}[ \t]*$", re.M | re.S)
SCRIPT_SRC = re.compile(r"<script\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.I)
SEEK_FRAME = re.compile(r"\bwindow\.seekFrame\s*=")
ASSET = re.compile(
    r"(?:\breference-[\w.-]+|(?:\.\./|/|\b)assets/|\bdata:(?:image|audio|video|font)/|"
    r"\.(?:webp|png|jpe?g|gif|avif|woff2?|ttf|otf|mp[34]|webm|mov)(?=[\"'\s)]))", re.I,
)
REMOTE = re.compile(r"https?://|[\"']\s*//[\w.-]+\.|\b(?:fetch|XMLHttpRequest|WebSocket|importScripts)\s*\(", re.I)
OPENMOTION_IMPORT_MEDIA = re.compile(r"<(?:link|img|iframe|video|audio|source|object)\b|@font-face|@import|url\s*\(|\bnew\s+Image\b", re.I)
CLOCK = re.compile(r"\b(?:requestAnimationFrame|setTimeout|setInterval|Math\.random)\s*\(")
DEPENDENCIES = ["data.js", "common.js", "scene.js", "bridge.js"]
OPENMOTION_IMPORT_CATEGORIES = {
    "typography": "文字", "ui-entrance": "界面入场", "effects": "特效", "transition": "转场",
    "opening": "开场", "interaction": "交互", "camera": "运镜", "rhythm": "节奏",
    "outro": "收尾", "data": "数据",
}
DECISIONS = Path(__file__).with_name("openmotion_review.json")
REPORT = Path(__file__).resolve().parents[2] / "docs/tasks/om-recipes/excluded.md"
VISUAL_CONFIG = ("duration", "accent", "palette", "sourceCanvas", "actionRange", "mode", "mechanism", "templateId")

# --- promo_plan.py ---
PEAK_LIMIT = 10 ** (-1 / 20)

# --- recipe_library.py ---
RECIPE_LIBRARY_ROOT = Path(__file__).resolve().parent / "shot_recipes"
RECIPE_LIBRARY_MEDIA = RECIPE_LIBRARY_ROOT / "media"
NON_CATEGORY_DIRS = {"demos", "media", "upstream"}
CLIPS_MANIFEST = RECIPE_LIBRARY_MEDIA / "clips.json"
UPSTREAM_COMMIT = "3ac67b75dd0b3bc2fd807c17f6b7ce35373eef3d"
OPENMOTION_COMMIT = "543c5002f6eebea04744927073e3e7bb873e541c"
REQUIRED_FIELDS = {
    "name": "id",
    "一句话": "summary",
    "适用": "use",
    "时长": "duration",
    "能量": "energy",
}
PORTRAIT_READY = {
    "camera/crash-zoom-punch.md",
    "camera/tension-camera-moves.md",
    "data/before-after-slider-scrub.md",
    "data/scroll-brake-moves.md",
    "effects/aurora-bloom-bg-flip.md",
    "effects/fui-hud-moves.md",
    "effects/glow-flyline-moves.md",
    "effects/icon-performance-moves.md",
    "effects/impact-feedback.md",
    "effects/light-play-moves.md",
    "effects/riso-print-hits.md",
    "effects/scan-bracket-sweep.md",
    "effects/slam-entrance-moves.md",
    "effects/spotlight-sweep-moves.md",
    "interaction/glass-pill-dictation-typing.md",
    "interaction/hashtag-to-pill-materialize.md",
    "interaction/picker-carousel-feature-cycle.md",
    "interaction/segmented-thumb-hero.md",
    "interaction/theme-switch-moves.md",
    "interaction/voice-waveform-live.md",
    "opening/brand-ink-open.md",
    "opening/fracture.md",
    "opening/icon-field-colorize.md",
    "opening/letterspace-materialize.md",
    "opening/spotlight-hero-card.md",
    "opening/stroke-segment-build.md",
    "outro/grain-dissolve.md",
    "outro/logo-shrink-wordmark-lockup.md",
    "outro/ui-strip-away-outro.md",
    "outro/ui-to-brand-morph.md",
    "rhythm/beat-cut-moves.md",
    "rhythm/beat-step-list-theme-cycle.md",
    "rhythm/rhythm-interrupt-moves.md",
    "rhythm/sakuga-timing-shift.md",
    "rhythm/speed-ramp-freeze.md",
    "rhythm/trailer-grammar-moves.md",
    "transition/bottom-push-stack-wipe.md",
    "transition/circle-match-iris.md",
    "transition/gradient-transition.md",
    "transition/page-turn-transitions.md",
    "transition/print-texture-transitions.md",
    "transition/shot-transitions.md",
    "transition/tear-streak-transitions.md",
    "transition/transition-travel.md",
    "transition/white-flash-logo-simplify-cut.md",
    "transition/wipe-transitions.md",
    "typography/blur-slide.md",
    "typography/brace-expand.md",
    "typography/flying-words.md",
    "typography/glitch-cycle.md",
    "typography/gradient-word-sweep.md",
    "typography/marker-underline-title.md",
    "typography/outline-word-fill.md",
    "typography/paper-title-card.md",
    "typography/pill-slot-cycle.md",
    "typography/title-demote-to-label.md",
    "typography/type-assembly-moves.md",
    "typography/type-entrance-moves.md",
    "typography/type-rhythm-sync.md",
    "typography/typewriter-moves.md",
    "typography/vertical-word-roll-blur-cycle.md",
    "typography/word-relay-geometry.md",
    "ui-entrance/avatar-bracket-carousel.md",
    "ui-entrance/cloner-depth-echo.md",
    "ui-entrance/draw-svg-trace.md",
    "ui-entrance/element-body-moves.md",
    "ui-entrance/list-reveal.md",
    "ui-entrance/list-stack-press.md",
    "ui-entrance/neon-frame-forerun.md",
    "ui-entrance/neon-frame-orbit-drop.md",
    "ui-entrance/product-card-progressive-assemble.md",
    "ui-entrance/radial-wave.md",
    "ui-entrance/research-card-stack-scroll.md",
    "ui-entrance/row-embed.md",
    "ui-entrance/value-stagger-gradient.md",
}
POSTER_POSITION = 0.9  # closest to upstream gallery posters: mean abs diff 9.0 vs 12.4 at the last frame (50 posters)
PREVIEW_MAX_WIDTH = 960
PREVIEW_FPS = 30
LOCAL_CLIP_SOURCE = "render"

# --- revision_library.py ---
REVISION_LIBRARY_CATEGORIES = {'main': '主次不清', 'dim': '主次不清', 'del': '字太多', 'short': '字太多',
              'space': '太空或挤在上面', 'color': '颜色乱', 'sync': '跟口播对不上'}

# --- revisions.py ---
VERSION_FIELDS = ('status', 'failureCode', 'attempts', 'lastInstruction', 'writingStartedAt', 'writtenAt',
                  'renderedAt', 'codeChars', 'posterRevision', 'checks', 'boxes', 'look')

# --- styles.py ---
DESIGN_FIELDS = ('palette', 'typeScale', 'motionRules', 'banned', 'motionSummary', 'bannedShort')
SCRIPT_FIELDS = ('dialogue', 'visual', 'subtitle', 'camera')
STYLE_LIBRARY_ROOT = Path(__file__).with_name('style_library')
LIBRARY_ID = re.compile(r'[a-z][a-z0-9_-]{0,79}')
