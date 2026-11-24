"""Import reviewed, offline single clips from a pinned OpenMotion Git tree."""
from collections import Counter
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import re
import subprocess

try:
    from . import recipe_library
except ImportError:  # Direct command-line invocation.
    import recipe_library

COMMIT = recipe_library.OPENMOTION_COMMIT
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
MEDIA = re.compile(r"<(?:link|img|iframe|video|audio|source|object)\b|@font-face|@import|url\s*\(|\bnew\s+Image\b", re.I)
CLOCK = re.compile(r"\b(?:requestAnimationFrame|setTimeout|setInterval|Math\.random)\s*\(")
DEPENDENCIES = ["data.js", "common.js", "scene.js", "bridge.js"]
CATEGORIES = {
    "typography": "文字", "ui-entrance": "界面入场", "effects": "特效", "transition": "转场",
    "opening": "开场", "interaction": "交互", "camera": "运镜", "rhythm": "节奏",
    "outro": "收尾", "data": "数据",
}
DECISIONS = Path(__file__).with_name("openmotion_review.json")
REPORT = Path(__file__).resolve().parents[2] / "docs/tasks/om-recipes/excluded.md"

# Upstream common.js reads these values when setting up the clip renderer. Stage
# times and palette drive the animation; captions and brand defaults do not.
VISUAL_CONFIG = ("duration", "accent", "palette", "sourceCanvas", "actionRange", "mode", "mechanism", "templateId")


def read_pinned(repo):
    git = ["git", "-C", str(repo)]
    head = subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()
    if head != COMMIT:
        raise ValueError(f"Expected OpenMotion HEAD {COMMIT}, found {head}")
    tree = subprocess.check_output([*git, "ls-tree", "-r", "--name-only", COMMIT, "--", CATALOG, "LICENSE"],
                                   text=True).splitlines()
    catalog = {p.removeprefix(CATALOG) for p in tree if p.startswith(CATALOG)}
    templates = {match[1] for path in catalog if (match := CLIP_PATH.fullmatch(path))}
    paths = sorted(path for path in catalog if path.split("/", 1)[0] in templates and (
        CLIP_PATH.fullmatch(path) or path.endswith("/source/motion.md") or
        any(path.endswith(f"/source/demos/{dep}") for dep in DEPENDENCIES)
    ))
    if not templates:
        raise ValueError("No OpenMotion single clips in the pinned Git tree")
    # Read Git objects rather than the worktree so a local edit or untracked file
    # cannot be imported accidentally. Keep reference media out of the read list.
    names = ["LICENSE", *(CATALOG + path for path in paths)]
    with subprocess.Popen([*git, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
        values = {}
        for path in names:
            proc.stdin.write(f"{COMMIT}:{path}\n".encode())
            proc.stdin.flush()
            header = proc.stdout.readline().split()
            if len(header) != 3 or header[1] != b"blob":
                raise ValueError(f"Missing pinned OpenMotion blob: {path}")
            content = proc.stdout.read(int(header[2]))
            if proc.stdout.read(1) != b"\n":
                raise ValueError(f"Invalid Git blob response for {path}")
            values[path.removeprefix(CATALOG)] = content.decode("utf-8")
        proc.stdin.close()
        if proc.wait():
            raise ValueError("Could not read pinned OpenMotion sources")
    return values.pop("LICENSE"), values


def metadata_by_clip(markdown):
    entries = {}
    for block in DEMO_META.findall(markdown):
        metadata = json.loads(block)
        clip = metadata.get("id")
        if not isinstance(clip, str) or not re.fullmatch(r"clip-\d+", clip):
            continue
        if metadata.get("src") != f"demos/{clip}.html" or clip in entries:
            raise ValueError(f"Invalid single-clip metadata: {clip}")
        entries[clip] = metadata
    return entries


def asset_problem(source):
    if ASSET.search(source) or MEDIA.search(source):
        return "依赖参考图、媒体或字体资源"
    if REMOTE.search(source):
        return "依赖远程地址或网络请求"
    if CLOCK.search(source):
        return "使用实时计时或非确定性随机数"
    return None


def canvas_demo(page, source, choice, metadata):
    # The upstream HTML uses one canvas and the same four scripts. Keep the
    # scene and its timing, and replace the wrapper and nonvisual metadata.
    title_free = re.sub(r"<title>.*?</title>", "", page, flags=re.I | re.S)
    if problem := asset_problem(title_free):
        return None, problem
    if SCRIPT_SRC.findall(page) != DEPENDENCIES:
        return None, "seekFrame 缺失且没有受支持的本地逐帧接口"
    if set(source) != set(DEPENDENCIES):
        return None, "单镜缺少本地动画脚本"
    common, scene = source["common.js"], source["scene.js"]
    prefix = r"const CONFIG=(.*?);\nconst DATA="
    config_match = re.match(prefix, source["data.js"])
    bounds = re.search(r'data-mode="clip" data-start="([\d.]+)" data-end="([\d.]+)"', page)
    canvas = re.search(r'<canvas width="(\d+)" height="(\d+)"></canvas>', page)
    if not (config_match and bounds and canvas and "window.motionDemo={duration,renderAt" in common):
        return None, "seekFrame 缺失且无法接到已有逐帧接口"
    start, end = map(float, bounds.groups())
    if end <= start or not math.isclose(end - start, metadata["duration"], abs_tol=1e-6):
        return None, "单镜时间段和 motion-demo 时长不一致"
    for needle, replacement in choice.get("replacements", {}).items():
        if needle not in scene:
            raise ValueError(f"Reviewed scene replacement no longer matches: {needle!r}")
        scene = scene.replace(needle, replacement)
    # These two shared helpers draw an unrelated brand mark. They are shipped in
    # many scene sources even when the scene never calls them.
    scene = re.sub(r"^function cc(?:Path)?\(.*\n", "", scene, flags=re.M)
    if re.search(r"\bcc(?:Path)?\(", scene):
        return None, "依赖程序绘制的品牌标志"
    if re.search(r"\bDATA\b", scene):
        return None, "依赖原片量测或识别数据"
    # Drop upstream sequence, color, object and measurement renderers. Retain
    # the drawing primitives and dispatch only the requested single clip.
    common = common.split("function paletteDemo(", 1)[0]
    if "function stageProgress(" not in common:
        return None, "缺少已核实的 Canvas 单镜绘制函数"
    if problem := asset_problem(common + "\n" + scene):
        return None, problem
    # The renderer loads this family before seeking. Standalone previews use
    # the system fonts already named by the source for the fallback.
    def pinned_font(source_text):
        return re.sub(r"\.font\s*=\s*[^;\n]+",
                      lambda match: match[0].replace("px ", "px PCPinned0, "), source_text)

    common, scene = pinned_font(common), pinned_font(scene)
    upstream = json.loads(config_match[1])
    config = {key: upstream[key] for key in VISUAL_CONFIG if key in upstream}
    config.update(
        demoTitle=choice.get("demo_title", choice["name"]), brand="示例",
        labels=choice.get("labels", ["示例", "步骤一", "步骤二"]),
        objects=choice.get("objects", ["对象一", "对象二", "对象三"]),
        stages=[{"start": stage["start"], "label": f"阶段 {i}"}
                for i, stage in enumerate(upstream["stages"], 1)],
    )
    initial = max(0, min(float(metadata.get("initialTime", 0)), float(metadata["duration"])))
    width, height = canvas.groups()
    # Open file:// at a meaningful frame. The renderer supplies its own clock
    # and may seek in any order, including before the browser preview frame.
    wrapper = f"""<!doctype html>
<!-- Adapted from OpenMotion {COMMIT}: offline wrapper and neutral sample content. -->
<html lang="zh-CN">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(choice["name"])}</title>
<style>
html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:{config["palette"][0]}}}
canvas{{display:block;width:100%;height:100%;object-fit:contain}}
</style>
<body data-mode="clip" data-start="{start:g}" data-end="{end:g}">
<canvas width="{width}" height="{height}"></canvas>
<script src="data.js"></script>
<script src="common.js"></script>
<script src="scene.js"></script>
<script>
const CLIP_START = {start:g};
const CLIP_DURATION = {format(metadata["duration"], ".12g")};
let usingPinnedFont = false;
window.seekFrame = (frame, fps) => {{
  const pinnedFontReady = Array.from(document.fonts).some(
    font => font.family.replace(/["']/g, "") === "PCPinned0" && font.status === "loaded");
  if (pinnedFontReady !== usingPinnedFont) {{
    maskCache.clear();
    usingPinnedFont = pinnedFontReady;
  }}
  time = clamp(frame / fps, 0, CLIP_DURATION);
  ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
  ctx.globalAlpha = 1;
  ctx.filter = "none";
  ctx.shadowBlur = 0;
  ctx.clearRect(0, 0, W, H);
  drawScene(CLIP_START + time);
}};
window.seekFrame({initial:g}, 1);
</script>
</body>
</html>
"""
    return {
        "index.html": wrapper,
        "common.js": "// Adapted from OpenMotion: keep the single-clip drawing helpers and select the local font.\n"
                     + common.rstrip() + "\n",
        "scene.js": "// Adapted from OpenMotion: offline drawing with neutral example content.\n"
                    + scene.rstrip() + "\n",
        "data.js": "// Adapted from OpenMotion: keep timing and geometry with neutral example content.\n"
                   "const CONFIG = " + json.dumps(config, ensure_ascii=False) + ";\n",
    }, None


def prepare_demo(page, source, choice, metadata):
    if SEEK_FRAME.search(page) and not SCRIPT_SRC.search(page):
        problem = asset_problem(page)
        return (None, problem) if problem else ({"index.html": page}, None)
    return canvas_demo(page, source, choice, metadata)


def get_catalog_files(catalog):
    """Read a directory fixture in the same format as the pinned Git tree."""
    return {p.relative_to(catalog).as_posix(): p.read_text(encoding="utf-8")
            for p in catalog.glob("*/source/**/*")
            if p.is_file() and p.suffix in {".md", ".html", ".js"}}


def card_text(slug, choice, metadata):
    duration = format(metadata["duration"], ".12g")
    return f"""---
name: {slug}
来源: openmotion
category: {choice["category"]}
中文名: {choice["name"]}
一句话: {choice["summary"]}
适用: {choice["use"]}
时长: {duration}s
能量: {choice["energy"]}
---

## 动效核心

{choice["summary"]}。{choice.get("detail", "")}

## 参考实现

[离线单镜演示](../demos/openmotion/{slug}/index.html)
"""


def sha256(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def import_catalog(catalog, editorial, root, report, license_text):
    files = get_catalog_files(catalog) if isinstance(catalog, Path) else catalog
    output = {}
    excluded = []
    categories = Counter()
    reasons = Counter()
    clips = {}
    metadata_cache = {}
    seen = set()
    for path in sorted(files):
        match = CLIP_PATH.fullmatch(path)
        if not match:
            continue
        template, clip = match.groups()
        key = f"{template}/{clip}"
        seen.add(key)
        folder = f"{template}/source"
        if template not in metadata_cache:
            metadata_cache[template] = metadata_by_clip(files.get(f"{folder}/motion.md", ""))
        metadata = metadata_cache[template].get(clip, {})
        duration = metadata.get("duration")
        choice = editorial.get(key, {})
        page = files[path]
        scripts = {name: files[f"{folder}/demos/{name}"] for name in DEPENDENCIES
                   if f"{folder}/demos/{name}" in files}
        reason = None
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
            reason = "缺少有效的 motion-demo 时长"
        elif choice.get("duplicate"):
            duplicate = choice["duplicate"]
            if not (root / duplicate).is_file():
                raise ValueError(f"{key}: missing existing duplicate {duplicate}")
            reason = f"与已有配方重复：`{duplicate}`"
        elif choice.get("exclude"):
            reason = choice["exclude"]
        elif not choice:
            bare_page = re.sub(r"<title>.*?</title>", "", page, flags=re.I | re.S)
            reason = asset_problem(bare_page)
            if not reason:
                reason = ("seekFrame 缺失且没有受支持的本地逐帧接口"
                          if not SEEK_FRAME.search(page) and SCRIPT_SRC.findall(page) != DEPENDENCIES
                          else "尚无可核实的去品牌单镜实现")
        else:
            demo, reason = prepare_demo(page, scripts, choice, metadata)
        if reason:
            excluded.append((template, clip, reason))
            reasons[reason.partition("：")[0]] += 1
            continue
        category = choice["category"]
        if category not in CATEGORIES or choice["energy"] not in {"低", "中", "高"}:
            raise ValueError(f"{key}: invalid reviewed category or energy")
        if not re.fullmatch(r"[\u4e00-\u9fff]{1,8}", choice["name"]):
            raise ValueError(f"{key}: expected a short Chinese recipe name")
        slug = f"om-{template.removeprefix('motion-')}-{clip}"
        output[f"openmotion/{slug}.md"] = card_text(slug, choice, metadata)
        for name, value in demo.items():
            output[f"demos/openmotion/{slug}/{name}"] = value
        clips[slug] = {"template": template, "clip": clip,
                       "demo_files": {name: sha256(value) for name, value in demo.items()}}
        categories[category] += 1

    if extra := editorial.keys() - seen:
        raise ValueError(f"Review contains unknown single clips: {sorted(extra)}")
    if not clips:
        raise ValueError("OpenMotion import produced no cards")

    lines = ["# OpenMotion 镜头配方来源", "",
             f"- 仓库 [{REPOSITORY}]({REPOSITORY})",
             f"- 固定提交 `{COMMIT}`，代码许可 Apache-2.0，见 [LICENSE-openmotion.txt](LICENSE-openmotion.txt)。",
             "- 动作说明按上游单镜整理。演示保留动作代码和时间区间，替换示例内容并接入离线帧定位。"
             "独立预览用系统字体，视频渲染使用制作台提供的字体。",
             "", "| 配方 | 上游模板 | 单镜 | 链接 |", "| --- | --- | --- | --- |"]
    for slug, info in clips.items():
        folder = f"{REPOSITORY}/tree/{COMMIT}/{CATALOG}{info['template']}"
        lines.append(f"| `{slug}` | `{info['template']}` | `{info['clip']}` | [上游]({folder}) |")
    output["ATTRIBUTION-openmotion.md"] = "\n".join(lines) + "\n"
    output["LICENSE-openmotion.txt"] = license_text
    output["openmotion/manifest.json"] = json.dumps(
        {"commit": COMMIT, "license_sha256": sha256(license_text), "clips": clips},
        ensure_ascii=False, indent=2, sort_keys=True,
    ) + "\n"

    # Only replace files owned by the previous manifest; other work in the same
    # directories is outside the importer's scope.
    manifest_path = root / "openmotion/manifest.json"
    if manifest_path.is_file():
        old_clips = json.loads(manifest_path.read_text(encoding="utf-8"))["clips"]
        for slug, info in old_clips.items():
            if not re.fullmatch(r"om-[a-z0-9-]+-clip-\d+", slug):
                raise ValueError(f"Invalid previously imported recipe id: {slug}")
            old = [f"openmotion/{slug}.md"]
            for name in info["demo_files"]:
                if Path(name).name != name:
                    raise ValueError(f"Invalid previously imported demo file: {name}")
                old.append(f"demos/openmotion/{slug}/{name}")
            for relative in old:
                if relative not in output:
                    (root / relative).unlink(missing_ok=True)
            demo_dir = root / "demos/openmotion" / slug
            if demo_dir.is_dir() and not any(demo_dir.iterdir()):
                demo_dir.rmdir()
    for relative, value in output.items():
        dest = root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(value, encoding="utf-8", newline="\n")

    lines = ["# OpenMotion 单镜导入清单", "",
             f"固定提交 `{COMMIT}`。单镜共 {len(seen)} 个，收录 {len(clips)} 个，排除 {len(excluded)} 个。",
             "", "| 类别 | 收录 |", "| --- | ---: |"]
    lines.extend(f"| {label} | {categories[category]} |" for category, label in CATEGORIES.items())
    lines.extend(["", "| 排除原因 | 数量 |", "| --- | ---: |"])
    lines.extend(f"| {reason} | {count} |" for reason, count in reasons.most_common())
    lines.extend(["", "| 模板 ID | 单镜 | 排除原因 |", "| --- | --- | --- |"])
    lines.extend(f"| `{template}` | `{clip}` | {reason} |" for template, clip, reason in excluded)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, default=Path.home() / ".local/share/openmotion-src")
    args = parser.parse_args()
    try:
        license_text, files = read_pinned(args.upstream)
        editorial = json.loads(DECISIONS.read_text(encoding="utf-8"))
        import_catalog(files, editorial, recipe_library.ROOT, REPORT, license_text)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
