"""Read and validate the vendored shot recipe cards."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "shot_recipes"
MEDIA = ROOT / "media"
# Top-level folders that are not recipe categories: media, upstream demo sources, upstream code kept verbatim.
NON_CATEGORY_DIRS = {"demos", "media", "upstream"}
CLIPS_MANIFEST = MEDIA / "clips.json"
# Upstream motion previews are 62 MB, so they live outside git; fetch-clips restores them by SHA-256.
CLIP_DIR = Path(os.environ.get("SHOT_RECIPE_CLIP_DIR", Path.home() / ".photo-content-os/media/shot_recipes/clips"))
UPSTREAM_COMMIT = "3ac67b75dd0b3bc2fd807c17f6b7ce35373eef3d"
OPENMOTION_COMMIT = "543c5002f6eebea04744927073e3e7bb873e541c"
REQUIRED_FIELDS = {
    "name": "id",
    "一句话": "summary",
    "适用": "use",
    "时长": "duration",
    "能量": "energy",
}


# Reviewed against the card action and timing for the pinned source.
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


def read_card(path, category):
    text = path.read_text(encoding='utf-8')
    frontmatter, delimiter, _ = text.removeprefix("---\n").partition("\n---\n")
    if not text.startswith("---\n") or not delimiter:
        raise ValueError(f'{path}: invalid frontmatter')
    fields = {}
    for line in frontmatter.split("\n"):
        if not line.strip():
            continue
        key, sep, value = line.partition(':')
        if not sep or not key.strip():
            raise ValueError(f"{path}: invalid frontmatter line: {line}")
        key = key.strip()
        if key in fields:
            raise ValueError(f'{path}: duplicate field {key}')
        fields[key] = value.strip()
    missing = [key for key in REQUIRED_FIELDS if not fields.get(key)]
    if missing:
        raise ValueError(f'{path}: missing fields: {", ".join(missing)}')
    if fields['name'] != path.stem:
        raise ValueError(f'{path}: name does not match filename')
    source = fields.get("来源", "video-shotcraft")
    if category == "openmotion":
        if source != "openmotion" or not fields.get("category") or not fields.get("中文名"):
            raise ValueError(f"{path}: expected OpenMotion source, category and Chinese name")
    elif source != "video-shotcraft":
        raise ValueError(f"{path}: unexpected recipe source {source}")
    entry = {dest: fields[key] for key, dest in REQUIRED_FIELDS.items()}
    relative = f"{category}/{path.name}"
    tags = [tag.strip() for tag in fields.get("标签", "").split("、") if tag.strip()]
    entry.update(
        category=fields["category"] if source == "openmotion" else category,
        path=relative,
        tags=tags,
        tags_source="upstream" if tags else "missing",
        portrait_fit=True if relative in PORTRAIT_READY else None,
    )
    if source == "openmotion":
        entry["name"] = fields["中文名"]
    return entry


def load_clips():
    return json.loads(CLIPS_MANIFEST.read_text(encoding="utf-8"))


POSTER_POSITION = 0.9  # closest to upstream gallery posters: mean abs diff 9.0 vs 12.4 at the last frame (50 posters)
PREVIEW_MAX_WIDTH = 960
PREVIEW_FPS = 30
LOCAL_CLIP_SOURCE = "render"


def media_fields(recipe_id, category, clips):
    """Upstream gallery poster first; otherwise a frame rendered from the card's demo."""
    poster, source = MEDIA / "posters" / f"{recipe_id}.jpg", "upstream"
    if not poster.is_file():
        poster, source = MEDIA / "posters" / f"{recipe_id}.render.jpg", "render"
    demo = ROOT / "demos" / category / recipe_id
    return {
        "poster": poster.relative_to(ROOT).as_posix() if poster.is_file() else None,
        "poster_source": source if poster.is_file() else None,
        "clip": clips[recipe_id]["file"] if recipe_id in clips else None,
        "demo": demo.relative_to(ROOT).as_posix() if demo.is_dir() else None,
    }


def clip_path(recipe_id):
    """Local path of the upstream preview clip, or None when the card has none."""
    clip = get(recipe_id)["clip"]
    return CLIP_DIR / clip if clip else None


def openmotion_demo_dimensions(demo_dir):
    """Preserve the OpenMotion demo canvas aspect ratio with even dimensions and width <= 960."""
    index_html = Path(demo_dir) / "index.html"
    html = index_html.read_text(encoding="utf-8")
    match = re.search(r'<canvas\b[^>]*\bwidth=["\'](\d+)["\'][^>]*\bheight=["\'](\d+)["\']', html, re.I)
    if not match:
        match = re.search(r'<canvas\b[^>]*\bheight=["\'](\d+)["\'][^>]*\bwidth=["\'](\d+)["\']', html, re.I)
        if not match:
            raise ValueError(f"{index_html}: missing canvas width/height")
        raw_h, raw_w = int(match.group(1)), int(match.group(2))
    else:
        raw_w, raw_h = int(match.group(1)), int(match.group(2))
    if raw_w <= 0 or raw_h <= 0:
        raise ValueError(f"{index_html}: invalid canvas size {raw_w}x{raw_h}")
    if raw_w > PREVIEW_MAX_WIDTH:
        width = PREVIEW_MAX_WIDTH
        height = max(2, round(raw_h * PREVIEW_MAX_WIDTH / raw_w / 2) * 2)
    else:
        width = max(2, raw_w - (raw_w % 2))
        height = max(2, raw_h - (raw_h % 2))
    return width, height


def _load_teaching_clips():
    scripts_dir = str(Path(__file__).resolve().parents[1])
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from video_render.teaching_clips import teaching_clips
    return teaching_clips


def render_openmotion_preview(recipe_id, *, clip_dest=None, poster_dest=None):
    """Render one OpenMotion demo with the local video renderer to MP4 and/or JPG poster."""
    card = read_card(ROOT / "openmotion" / f"{recipe_id}.md", "openmotion")
    seconds = recipe_seconds(card["duration"])
    if not seconds or seconds <= 0:
        raise ValueError(f"{recipe_id}: invalid duration {card['duration']!r}")
    demo_dir = ROOT / "demos" / "openmotion" / recipe_id
    if not (demo_dir / "index.html").is_file():
        raise ValueError(f"{recipe_id}: missing OpenMotion demo in {demo_dir}")
    width, height = openmotion_demo_dimensions(demo_dir)
    frames = max(1, round(seconds * PREVIEW_FPS))
    font = os.environ.get("DIRECT_VIDEO_FONT") or os.environ.get("VIDEO_RENDER_TEST_FONT") or "/System/Library/Fonts/STHeiti Medium.ttc"
    manifest = {
        "width": width,
        "height": height,
        "fps": PREVIEW_FPS,
        "assets_dir": str(demo_dir.resolve()),
        "fonts": [{"path": font}],
        "timeout_seconds": max(120, frames),
        "shots": [{"id": recipe_id, "html": "index.html", "frames": frames, "start_frame": 0}],
    }
    browser = os.environ.get("VIDEO_RENDER_BROWSER") or os.environ.get("VIDEO_RENDER_TEST_BROWSER")
    if browser:
        manifest["browser_executable"] = browser
    teaching_clips = _load_teaching_clips()
    with tempfile.TemporaryDirectory(prefix=f"om-preview-{recipe_id}-") as tmp:
        tmp_dir = Path(tmp)
        manifest_path = tmp_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = teaching_clips(manifest_path, tmp_dir / "out", transparent=False)
        clip_info = result["clips"][0] if result.get("clips") else {}
        if result.get("status") != "completed" or clip_info.get("status") != "completed":
            raise ValueError(f"{recipe_id}: preview render failed: {clip_info.get('reason') or result.get('reason')}")
        rendered_mp4 = Path(clip_info["file"])
        size = rendered_mp4.stat().st_size
        digest = clip_info["sha256"]
        if clip_dest is not None:
            clip_dest = Path(clip_dest)
            clip_dest.parent.mkdir(parents=True, exist_ok=True)
            tmp_clip = clip_dest.with_name(f".{clip_dest.name}.tmp.{os.getpid()}")
            try:
                shutil.copyfile(rendered_mp4, tmp_clip)
                tmp_clip.replace(clip_dest)
            finally:
                tmp_clip.unlink(missing_ok=True)
        if poster_dest is not None:
            poster_dest = Path(poster_dest)
            poster_dest.parent.mkdir(parents=True, exist_ok=True)
            poster_frame = min(frames - 1, max(0, int(round((frames - 1) * POSTER_POSITION))))
            frame_png = Path(result["shots"][0]["frames_dir"]) / f"frame-{poster_frame:06d}.png"
            tmp_poster = poster_dest.with_name(f".{poster_dest.name}.tmp.{os.getpid()}.jpg")
            try:
                subprocess.run(
                    ["ffmpeg", "-v", "error", "-y", "-i", str(frame_png), "-vf", "scale=640:-2", "-q:v", "3", str(tmp_poster)],
                    check=True,
                    timeout=120,
                )
                tmp_poster.replace(poster_dest)
            finally:
                tmp_poster.unlink(missing_ok=True)
    return {
        "id": recipe_id,
        "file": f"{recipe_id}.mp4",
        "bytes": size,
        "sha256": digest,
        "source": LOCAL_CLIP_SOURCE,
        "width": width,
        "height": height,
        "frames": frames,
    }


def render_openmotion_previews(recipe_ids=None, *, workers=1):
    """Render OpenMotion preview MP4s into CLIP_DIR, posters into media/posters, and update clips.json + index.json."""
    manifest = load_openmotion_manifest()["clips"]
    targets = sorted(recipe_ids) if recipe_ids else sorted(manifest)
    unknown = sorted(set(targets) - set(manifest))
    if unknown:
        raise ValueError(f"unknown OpenMotion recipes: {unknown}")
    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    (MEDIA / "posters").mkdir(parents=True, exist_ok=True)

    def _one(rid):
        return render_openmotion_preview(
            rid,
            clip_dest=CLIP_DIR / f"{rid}.mp4",
            poster_dest=MEDIA / "posters" / f"{rid}.render.jpg",
        )

    results = {}
    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_one, rid): rid for rid in targets}
            for idx, future in enumerate(as_completed(futures), 1):
                rid = futures[future]
                info = future.result()
                results[rid] = info
                print(f"[{idx}/{len(targets)}] {rid} ({info['width']}x{info['height']}, {info['frames']}f, {info['bytes']}B)", flush=True)
    else:
        for idx, rid in enumerate(targets, 1):
            info = _one(rid)
            results[rid] = info
            print(f"[{idx}/{len(targets)}] {rid} ({info['width']}x{info['height']}, {info['frames']}f, {info['bytes']}B)", flush=True)

    clips_data = load_clips()
    clips = dict(clips_data["clips"])
    for rid, info in results.items():
        clips[rid] = {
            "file": info["file"],
            "bytes": info["bytes"],
            "sha256": info["sha256"],
            "source": LOCAL_CLIP_SOURCE,
        }
    clips_data["clips"] = dict(sorted(clips.items()))
    CLIPS_MANIFEST.write_text(json.dumps(clips_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    entries = build_index()
    (ROOT / "index.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: rendered {len(results)} OpenMotion previews into {CLIP_DIR} and posters into {MEDIA / 'posters'}")
    return results


def fetch_clips():
    clips = load_clips()["clips"]
    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    def ok(item):
        path = CLIP_DIR / item["file"]
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    missing = [(recipe_id, item) for recipe_id, item in clips.items() if not ok(item)]
    download_missing = [(rid, item) for rid, item in missing if item.get("source") != LOCAL_CLIP_SOURCE]
    render_missing = [(rid, item) for rid, item in missing if item.get("source") == LOCAL_CLIP_SOURCE]
    if download_missing:
        args = [arg for _, item in download_missing for arg in ("-p", item["file"])]
        subprocess.run(["gh", "release", "download", "gallery-media", "--repo", "Vincentwei1021/video-shotcraft",
                        "--dir", str(CLIP_DIR), "--clobber", *args], check=True, timeout=1800)
    for recipe_id, item in render_missing:
        render_openmotion_preview(recipe_id, clip_dest=CLIP_DIR / item["file"])
    bad_render = [recipe_id for recipe_id, item in render_missing if not ok(item)]
    if bad_render:
        raise ValueError(f"clip SHA-256 mismatch after local render: {bad_render}")
    bad = [item["file"] for item in clips.values() if not ok(item)]
    if bad:
        raise ValueError(f"clip SHA-256 mismatch after download: {bad}")
    print(f"OK: {len(clips)} clips in {CLIP_DIR} ({len(download_missing)} downloaded, {len(render_missing)} rendered)")


def posters_from_renders(render_dir):
    """Write <id>.render.jpg from upstream renders (workbench/scripts/render-demos.mjs --out render_dir)."""
    render_dir = Path(render_dir)
    written = 0
    for entry in load_index():
        if entry["path"].startswith("openmotion/") or entry["poster_source"] == "upstream" or not entry["demo"]:
            continue
        stems = [p.stem for p in sorted((ROOT / entry["demo"]).glob("*.tsx")) if (render_dir / f"{p.stem}.mp4").is_file()]
        if not stems:
            raise ValueError(f"{entry['id']}: no rendered demo in {render_dir}")
        if len(stems) > 1:
            # Cards with several demos list them in order; the first one the card names is its lead shot.
            card = (ROOT / entry["path"]).read_text(encoding="utf-8")
            named = sorted((card.find(stem), stem) for stem in stems if stem in card)
            if not named:
                raise ValueError(f"{entry['id']}: card names none of its demos {stems}")
            stems = [named[0][1]]
        mp4 = render_dir / f"{stems[0]}.mp4"
        duration = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                                        check=True, capture_output=True, text=True, timeout=60).stdout)
        out = MEDIA / "posters" / f"{entry['id']}.render.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, duration * POSTER_POSITION - 0.05):.3f}", "-i", str(mp4),
                        "-frames:v", "1", "-vf", "scale=640:360", "-q:v", "3", str(out)], check=True, timeout=120)
        written += 1
    print(f"OK: {written} posters from {render_dir}")


_NUM = r'(\d+(?:\.\d+)?)'
_SPAN = _NUM + r'(?:\s*[–~-]\s*' + _NUM + r')?'


def recipe_seconds(duration):
    """整段时长的估计（秒）。卡片文字常先写分段（「闪光 0.3s + 飞行 1.6s …；全段 5.2s」），
    所以先认「全段 / 总 / 约」写明的整段，取区间上限；再认总帧数；都没有才取文中最大的秒数或帧数。"""
    def upper(match):
        return float(match.group(2) or match.group(1))
    # 「两式串播 246f」「全片合计」说的是多段拼起来的长度，不是一镜。
    duration = re.sub(r'[^；;（(]*(?:串播|合计)[^；;）)]*', '', duration)
    total = re.search(r'(?:全段|全长|总长|整段|总)\s*[~≈约]?\s*' + _SPAN + r'\s*s', duration)
    if total:
        return round(upper(total), 1)
    frames = re.search(r'^(\d+)\s*f\b|(\d+)\s*f\s*@\s*30', duration)
    if frames:
        return round(int(frames.group(1) or frames.group(2)) / 30, 1)
    lead = re.match(r'约\s*' + _SPAN + r'\s*s(?!\s*动作)', duration)
    if lead:
        return round(upper(lead), 1)
    seconds = [float(x) for pair in re.findall(_SPAN + r'\s*s\b', duration) for x in pair if x]
    counted = [int(x) / 30 for x in re.findall(r'(\d+)\s*f\b', duration)]
    values = seconds + counted
    return round(max(values), 1) if values else None


def load_openmotion_manifest():
    return json.loads((ROOT / "openmotion" / "manifest.json").read_text(encoding="utf-8"))


def build_index():
    cards = sorted(path for path in ROOT.glob('*/*.md') if path.parent.name not in NON_CATEGORY_DIRS)
    errors, entries = [], []
    for path in cards:
        try:
            entries.append(read_card(path, path.parent.name))
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        raise ValueError('\n'.join(errors))
    legacy = [item for item in entries if not item["path"].startswith("openmotion/")]
    imported = [item for item in entries if item["path"].startswith("openmotion/")]
    categories = {item["category"] for item in legacy}
    if len(legacy) != 124 or len(categories) != 10:
        raise ValueError("expected 124 video-shotcraft cards in 10 categories")
    manifest = load_openmotion_manifest()
    if manifest["commit"] != OPENMOTION_COMMIT or set(manifest["clips"]) != {item["id"] for item in imported}:
        raise ValueError("OpenMotion cards differ from the pinned import manifest")
    if any(item["category"] not in categories for item in imported):
        raise ValueError("OpenMotion card uses an unknown recipe category")
    if len({item['id'] for item in entries}) != len(entries):
        raise ValueError('duplicate recipe id')
    names = json.loads((ROOT / 'names.zh.json').read_text(encoding='utf-8'))
    ids = {item['id'] for item in legacy}
    if set(names) != ids:
        raise ValueError(f"recipe names mismatch: missing {sorted(ids - set(names))}, extra {sorted(set(names) - ids)}")
    bad_durations = []
    for item in entries:
        duration = item['duration']
        if duration.startswith('n/a'):
            value = None
        else:
            value = recipe_seconds(duration)
            if value is None:
                bad_durations.append(item['id'])
        energy = item['energy'].split('（', 1)[0]
        level = next((x for x in ('高', '中', '低') if x in energy), None)
        if '峰值' in energy:
            level = '高'
        item.update(name=names[item['id']] if item['id'] in names else item["name"], seconds=value, energy=level)
    if bad_durations:
        raise ValueError(f"unparseable recipe durations: {bad_durations}")
    clips = load_clips()["clips"]
    unknown = set(clips) - {item["id"] for item in entries}
    if unknown:
        raise ValueError(f"clips.json lists unknown recipes: {sorted(unknown)}")
    for item in entries:
        item.update(media_fields(item["id"], item["path"].split("/", 1)[0], clips))
    return entries


def load_index():
    return json.loads((ROOT / 'index.json').read_text(encoding='utf-8'))


def get(recipe_id):
    for entry in load_index():
        if entry['id'] == recipe_id:
            return entry
    raise KeyError(recipe_id)


def check(upstream):
    entries = build_index()
    if load_index() != entries:
        raise ValueError('index.json differs from cards')

    upstream = upstream.resolve()
    repo = upstream.parent.parent
    if upstream != repo / "references" / "shots":
        raise ValueError("--upstream must point to the clone's references/shots directory")
    git = ["git", "-C", str(repo)]
    head = subprocess.run(
        [*git, "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=10,
    ).stdout.strip()
    if head != UPSTREAM_COMMIT:
        raise ValueError(f"expected upstream commit {UPSTREAM_COMMIT}, found {head}")
    subprocess.run(
        [*git, "diff", "--exit-code", "--no-ext-diff", "--no-textconv", UPSTREAM_COMMIT,
         "--", "references/shots", "LICENSE"],
        stdout=subprocess.DEVNULL,
        check=True,
        timeout=10,
    )

    legacy = [entry for entry in entries if not entry["path"].startswith("openmotion/")]
    local_paths = {entry["path"] for entry in legacy}
    upstream_paths = {path.relative_to(upstream).as_posix() for path in upstream.glob("*/*.md")}
    if local_paths != upstream_paths:
        raise ValueError(
            f"upstream card set differs: missing {sorted(upstream_paths - local_paths)}, "
            f"extra {sorted(local_paths - upstream_paths)}"
        )
    files = [(ROOT / path, upstream / path) for path in sorted(local_paths)]
    gallery = repo / "gallery" / "media" / "poster"
    for entry in legacy:
        if entry["poster_source"] == "upstream":
            files.append((ROOT / entry["poster"], gallery / f"{entry['id']}.jpg"))
        if entry["demo"]:
            local_demo = ROOT / entry["demo"]
            source_demo = repo / "demos" / entry["category"] / entry["id"]
            names = {p.relative_to(local_demo).as_posix() for p in local_demo.rglob("*") if p.is_file()}
            if names != {p.relative_to(source_demo).as_posix() for p in source_demo.rglob("*") if p.is_file()}:
                raise ValueError(f"demo file set differs from upstream: {entry['demo']}")
            files.extend((local_demo / name, source_demo / name) for name in sorted(names))
    files.append((ROOT / "demos" / "LICENSE-video-shotcraft.txt", repo / "LICENSE"))
    files.extend((
        (ROOT / "ATTRIBUTION.md", upstream / "ATTRIBUTION.md"),
        (ROOT / "LICENSE-video-shotcraft.txt", repo / "LICENSE"),
    ))
    for local, source in files:
        if hashlib.sha256(local.read_bytes()).digest() != hashlib.sha256(source.read_bytes()).digest():
            raise ValueError(f"upstream SHA-256 mismatch: {local.relative_to(ROOT)}")

    check_openmotion()
    missing_tags = sum(entry["tags_source"] == "missing" for entry in entries)
    print(f"OK: {len(entries)} cards, 10 categories; {len(legacy)} video-shotcraft cards and their "
          "posters, demos, attribution and license match upstream SHA-256")
    print(f"Posters: {sum(e['poster_source'] == 'upstream' for e in entries)} upstream, "
          f"{sum(e['poster_source'] == 'render' for e in entries)} from upstream render; clips {sum(bool(e['clip']) for e in entries)}; "
          f"demos {sum(bool(e['demo']) for e in entries)}")
    print(f"Tags: {len(entries) - missing_tags} from upstream, {missing_tags} missing")


def check_openmotion():
    manifest = load_openmotion_manifest()
    attribution = (ROOT / "ATTRIBUTION-openmotion.md").read_text(encoding="utf-8")
    if OPENMOTION_COMMIT not in attribution:
        raise ValueError("OpenMotion attribution is missing the pinned commit")
    files = {"LICENSE-openmotion.txt": manifest["license_sha256"]}
    for recipe_id, item in manifest["clips"].items():
        if f"| `{recipe_id}` | `{item['template']}` | `{item['clip']}` |" not in attribution:
            raise ValueError(f"OpenMotion attribution is missing {recipe_id}")
        directory = ROOT / "demos" / "openmotion" / recipe_id
        if {p.name for p in directory.iterdir()} != set(item["demo_files"]):
            raise ValueError(f"OpenMotion demo file set differs for {recipe_id}")
        files.update({f"demos/openmotion/{recipe_id}/{name}": digest
                      for name, digest in item["demo_files"].items()})
    for relative, digest in files.items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise ValueError(f"OpenMotion SHA-256 mismatch: {relative}")
    print(f"OK: {len(manifest['clips'])} OpenMotion cards with pinned attribution, license and demo hashes")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--upstream', type=Path)
    parser.add_argument('--fetch-clips', action='store_true', help='download upstream preview clips and render local ones into SHOT_RECIPE_CLIP_DIR')
    parser.add_argument('--posters-from-renders', type=Path, metavar='DIR', help='upstream render-demos.mjs output directory')
    parser.add_argument('--render-openmotion-previews', action='store_true', help='render OpenMotion preview MP4s and posters with the local renderer')
    parser.add_argument('--workers', type=int, default=1, help='parallel render workers for --render-openmotion-previews')
    parser.add_argument('--recipe', action='append', help='limit --render-openmotion-previews to specific OpenMotion recipe ID(s)')
    args = parser.parse_args()
    try:
        if args.render_openmotion_previews:
            render_openmotion_previews(args.recipe, workers=max(1, args.workers))
        elif args.posters_from_renders:
            posters_from_renders(args.posters_from_renders)
        elif args.fetch_clips:
            fetch_clips()
        elif args.check:
            if args.upstream is None:
                parser.error('--check requires --upstream')
            check(args.upstream)
        else:
            entries = build_index()
            (ROOT / 'index.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
