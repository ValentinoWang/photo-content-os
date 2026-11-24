"""Read and validate the vendored shot recipe cards."""
import argparse
import hashlib
import json
import os
import re
import subprocess
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


def media_fields(recipe_id, category, clips):
    """Upstream gallery poster first; otherwise a frame of upstream's own demo rendered by its render-demos.mjs."""
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


def fetch_clips():
    clips = load_clips()["clips"]
    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    def ok(item):
        path = CLIP_DIR / item["file"]
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    missing = [item for item in clips.values() if not ok(item)]
    if missing:
        args = [arg for item in missing for arg in ("-p", item["file"])]
        subprocess.run(["gh", "release", "download", "gallery-media", "--repo", "Vincentwei1021/video-shotcraft",
                        "--dir", str(CLIP_DIR), "--clobber", *args], check=True, timeout=1800)
    bad = [item["file"] for item in clips.values() if not ok(item)]
    if bad:
        raise ValueError(f"clip SHA-256 mismatch after download: {bad}")
    print(f"OK: {len(clips)} clips in {CLIP_DIR} ({len(missing)} downloaded)")


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
    parser.add_argument('--fetch-clips', action='store_true', help='download upstream preview clips into SHOT_RECIPE_CLIP_DIR')
    parser.add_argument('--posters-from-renders', type=Path, metavar='DIR', help='upstream render-demos.mjs output directory')
    args = parser.parse_args()
    try:
        if args.posters_from_renders:
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
