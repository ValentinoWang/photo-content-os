#!/usr/bin/env python3
"""Compose unmodified design/application screenshots and verify local evidence links."""
import argparse
import hashlib
import html
import json
from pathlib import Path
from PIL import Image, ImageDraw


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design-dir', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    args = parser.parse_args()
    root = args.evidence_dir
    manifest = json.loads((root / 'screenshot-manifest.json').read_text())
    comparisons = []
    for item in manifest:
        actual = root / item['file']
        assert sha(actual) == item['sha256'], actual
        with Image.open(actual) as image:
            item['output_dimensions'] = list(image.size)
        item.update(role='本机创作者', timezone='Asia/Taipei', browser='Chrome', render='local-preview')
        if item.get('part'):
            continue
        design = args.design_dir / item['file']
        with Image.open(design).convert('RGB') as left, Image.open(actual).convert('RGB') as right:
            # Preserve both full-page renders at their native pixel sizes. The blank
            # remainder belongs to the comparison canvas, not to either source image.
            pair = Image.new('RGB', (left.width + 24 + right.width, max(left.height, right.height) + 40), '#0b1112')
            draw = ImageDraw.Draw(pair)
            draw.text((12, 12), f'DESIGN {left.width} x {left.height}', fill='white')
            draw.text((left.width + 36, 12), f'IMPLEMENTATION {right.width} x {right.height}', fill='white')
            pair.paste(left, (0, 40)); pair.paste(right, (left.width + 24, 40))
            target = 'compare-' + item['file']
            pair.save(root / target)
            comparisons.append(dict(state=item['name'], viewport=item['viewport'], file=target,
                                    sha256=sha(root / target), design_sha256=sha(design),
                                    implementation_sha256=item['sha256'], output_dimensions=list(pair.size)))
    assert len(comparisons) == 29 * 4
    (root / 'screenshot-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (root / 'comparison-manifest.json').write_text(json.dumps(comparisons, ensure_ascii=False, indent=2) + '\n')
    states = list(dict.fromkeys(i['state'] for i in comparisons))
    links = []
    for state in states:
        rows = [i for i in comparisons if i['state'] == state]
        links.append(f'<section id="{state}"><h2>{html.escape(state)}</h2>')
        for row in rows:
            width = row['viewport']['width']
            links.append(f'<details><summary>{width} px — full page, design left / implementation right</summary>'
                         f'<a href="{state}-{width}.png">Implementation render</a><a href="{row["file"]}"><img loading="lazy" src="{row["file"]}"></a></details>')
        links.append('</section>')
    extras = [i for i in manifest if i.get('part')]
    links.append('<h2>Inspector scroll coverage</h2>')
    for row in extras:
        links.append(f'<a href="{row["file"]}">{row["file"]}</a><br>')
    links.append('<h2>Supplemental failure / stopped / disconnected states</h2>')
    extra_manifest = root / 'exceptions/screenshot-manifest.json'
    if extra_manifest.exists():
        for row in json.loads(extra_manifest.read_text()):
            links.append(f'<a href="exceptions/{row["file"]}">{row["file"]}</a><br>')
    content = '<!doctype html><meta charset="utf-8"><title>R220 Round 2 comparisons</title><style>body{background:#101718;color:#ddd;font:14px system-ui;margin:24px}a{color:#7dc9ce}img{display:block;max-width:100%;height:auto}summary{padding:12px;cursor:pointer}section{margin:32px 0}</style><h1>R220 Round 2 — local evidence</h1><p>29 states × 4 actual viewport widths. Private media: keep this gallery local; do not add it to Git.</p>' + ''.join(links)
    (root / 'gallery.html').write_text(content)
    import re
    targets = set(re.findall(r'(?:href|src)="([^"#]+)"', content))
    for target in targets:
        assert (root / target).is_file(), target
    (root / 'artifact-verification.json').write_text(json.dumps(dict(states=len(states), screenshots=len(manifest), comparisons=len(comparisons), gallery_targets=len(targets), missing_files=0, hash_drift=0), indent=2) + '\n')


if __name__ == '__main__':
    main()
