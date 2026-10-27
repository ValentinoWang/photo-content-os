"""R280 palette, stray dark UI surfaces and readable text; no browser or media IO."""
import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "studio/static"
PALETTE = dict(zip(
    "sec-quiet sec-build sec-peak bg panel panel-2 raise rule rule-2 ink ink-2 ink-3 ink-4 ink-5 ac ac-2 ac-bg ac-soft ok ok-bg ok-line warn warn-bg warn-line cut cut-bg".split(),
    "#C9D6D7 #7FB7BD #1F8D96 #F5F6F4 #FFFFFF #F7F8F7 #EEF2F1 #E4E8E7 #D2D9D8 #152021 #3A4849 #5F6E6F #7F8C8D #A5AFB0 #1F8D96 #A9D5D9 #E6F3F4 #18727A #2E7D4B #E7F4EC #BFE0CB #9A6B10 #FBF2DE #E8CB8C #B5412F #FCE9E5".split(),
))


def rules(name):
    css = re.sub(r"/\*.*?\*/", "", (STATIC / name).read_text(), flags=re.S)
    return [(m[1].strip(), m[2]) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css)]


def tokens():
    root = next(body for selector, body in rules("styles.css") if selector.endswith(":root"))
    return dict(re.findall(r"--([\w-]+)\s*:\s*([^;{}]+)", root))


def rgba(value):
    if value.startswith("#"):
        digits = value[1:]
        if len(digits) in (3, 4):
            digits = "".join(c * 2 for c in digits)
        rgb = [int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        return (*rgb, int(digits[6:8], 16) / 255 if len(digits) == 8 else 1)
    values = [float(x) for x in re.findall(r"[\d.]+", value)]
    return (*(x / 255 for x in values[:3]), values[3] if len(values) == 4 else 1)


def luminance(rgb):
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb[:3]]
    return sum(c * w for c, w in zip(linear, (.2126, .7152, .0722)))


def test_approved_light_palette_and_native_controls():
    actual = tokens()
    assert {key: actual.get(key, "").upper() for key in PALETTE} == PALETTE
    assert "color-scheme:light" in re.sub(r"\s", "", (STATIC / "styles.css").read_text())
    assert '<meta name="color-scheme" content="light">' in (STATIC / "index.html").read_text()


@pytest.mark.parametrize("name", ["styles.css", "workflow.css"])
def test_no_unapproved_dark_literals_outside_video(name):
    violations = []
    for selector, body in rules(name):
        if selector.endswith(":root"):
            continue  # Exact UI palette above; media tokens have a separate preservation check.
        if selector in {".handoff .stage", ".handoff .stage .preview-play"}:
            continue
        for color in re.findall(r"#[\da-fA-F]{3,8}\b|rgba?\([^)]*\)", body):
            if selector == ".btn--pri:hover" and color.upper() == "#18767E":
                continue  # Explicit approved primary-button hover.
            r, g, b, a = rgba(color)
            if luminance([c * a + 1 - a for c in (r, g, b)]) < .30:
                violations.append(f"{selector}: {color}")
        # SVG URL hex escapes also need to follow the approved light-theme icons.
        if re.search(r"%23071719|%238FC7CD", body, re.I):
            violations.append(f"{selector}: stale encoded SVG color")
    assert not violations, "Replace dark UI literals with R280 tokens: " + "; ".join(violations)


@pytest.mark.parametrize("ink,minimum", [("ink", 4.5), ("ink-2", 4.5), ("ink-3", 4.5), ("ink-4", 3)])
def test_text_contrast_on_light_surfaces(ink, minimum):
    palette = tokens()
    for surface in ("bg", "panel", "panel-2", "raise", "ac-bg", "ok-bg", "warn-bg", "cut-bg"):
        text = ink
        if ink == "ink-4" and surface == "cut-bg":
            # The approved ink-4/cut-bg pair is 2.969: error surfaces must
            # promote their inherited small-note color, not change the palette.
            for path in STATIC.glob("*.css"):
                for selector, body in rules(path.name):
                    if "background:var(--cut-bg)" in body:
                        assert "--ink-4:var(--ink-3)" in body, (path.name, selector)
            text = "ink-3"
        pair = sorted([luminance(rgba(palette[text])), luminance(rgba(palette[surface]))])
        ratio = (pair[1] + .05) / (pair[0] + .05)
        assert ratio >= minimum, f"--{ink} on --{surface}: {ratio:.3f} < {minimum}"


def test_ink4_is_reserved_for_placeholders_and_small_notes():
    violations = []
    for path in STATIC.glob("*.css"):
        for selector, body in rules(path.name):
            if re.search(r"(?:^|;)\s*color:var\(--ink-4\)", body):
                if "small" not in selector and "placeholder" not in selector:
                    violations.append(f"{path.name}: {selector}")
    assert not violations, "Use --ink-3 for secondary text/controls: " + "; ".join(violations)


def test_video_canvas_is_independent_of_page_theme():
    palette = tokens()
    assert palette.get("media-bg", "").upper() == "#0D1314"
    assert palette.get("media-ink", "").upper() == "#E4EBEB"
    for name, selectors in {
        "review.css": [".stage", ".pl-stage", ".viewer video"],
        "direct.css": [".dv-poster", ".dv-player .dv-stage"],
        "direct-shot-detail.css": [".rv-stage"],
        "direct-rescript.css": [".sb-zoom video,.sb-zoom img"],
    }.items():
        for selector in selectors:
            assert any(s == selector and "background:var(--media-bg)" in body for s, body in rules(name)), (name, selector)
