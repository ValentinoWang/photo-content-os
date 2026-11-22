"""Read and validate the vendored shot recipe cards."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "shot_recipes"
MEDIA = ROOT / "media"
CLIPS_MANIFEST = MEDIA / "clips.json"
# Upstream motion previews are 62 MB, so they live outside git; fetch-clips restores them by SHA-256.
CLIP_DIR = Path(os.environ.get("SHOT_RECIPE_CLIP_DIR", Path.home() / ".photo-content-os/media/shot_recipes/clips"))
UPSTREAM_COMMIT = "3ac67b75dd0b3bc2fd807c17f6b7ce35373eef3d"
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
    entry = {dest: fields[key] for key, dest in REQUIRED_FIELDS.items()}
    relative = f"{category}/{path.name}"
    tags = [tag.strip() for tag in fields.get("标签", "").split("、") if tag.strip()]
    entry.update(
        category=category,
        path=relative,
        tags=tags,
        tags_source="upstream" if tags else "missing",
        portrait_fit=True if relative in PORTRAIT_READY else None,
    )
    return entry


def load_clips():
    return json.loads(CLIPS_MANIFEST.read_text(encoding="utf-8"))


def media_fields(recipe_id, category, clips):
    """Upstream gallery poster first; a mid-clip frame only when upstream ships no poster."""
    poster, source = MEDIA / "posters" / f"{recipe_id}.jpg", "upstream"
    if not poster.is_file():
        poster, source = MEDIA / "posters" / f"{recipe_id}.from-clip.jpg", "clip"
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


def build_index():
    cards = sorted(ROOT.glob('*/*.md'))
    errors, entries = [], []
    for path in cards:
        try:
            entries.append(read_card(path, path.parent.name))
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        raise ValueError('\n'.join(errors))
    if len(entries) != 124 or len({item['category'] for item in entries}) != 10:
        raise ValueError('expected 124 cards in 10 categories')
    if len({item['id'] for item in entries}) != len(entries):
        raise ValueError('duplicate recipe id')
    clips = load_clips()["clips"]
    unknown = set(clips) - {item["id"] for item in entries}
    if unknown:
        raise ValueError(f"clips.json lists unknown recipes: {sorted(unknown)}")
    for item in entries:
        item.update(media_fields(item["id"], item["category"], clips))
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

    local_paths = {entry["path"] for entry in entries}
    upstream_paths = {path.relative_to(upstream).as_posix() for path in upstream.glob("*/*.md")}
    if local_paths != upstream_paths:
        raise ValueError(
            f"upstream card set differs: missing {sorted(upstream_paths - local_paths)}, "
            f"extra {sorted(local_paths - upstream_paths)}"
        )
    files = [(ROOT / path, upstream / path) for path in sorted(local_paths)]
    gallery = repo / "gallery" / "media" / "poster"
    for entry in entries:
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

    missing_tags = sum(entry["tags_source"] == "missing" for entry in entries)
    print(f"OK: {len(entries)} cards, 10 categories; cards, posters, demos, attribution and license match upstream SHA-256")
    print(f"Posters: {sum(e['poster_source'] == 'upstream' for e in entries)} upstream, "
          f"{sum(e['poster_source'] == 'clip' for e in entries)} from clip; clips {sum(bool(e['clip']) for e in entries)}; "
          f"demos {sum(bool(e['demo']) for e in entries)}")
    print(f"Tags: {len(entries) - missing_tags} from upstream, {missing_tags} missing")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--upstream', type=Path)
    parser.add_argument('--fetch-clips', action='store_true', help='download upstream preview clips into SHOT_RECIPE_CLIP_DIR')
    args = parser.parse_args()
    try:
        if args.fetch_clips:
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
