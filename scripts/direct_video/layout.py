"""Raster content-bound measurement adapted from direct-video-shots preview_frames.

来源：用户技能 direct-video-shots；构图规则部分借自 HeyGen HyperFrames（Apache-2.0）。

The upstream CONTENT_BOX uses y=200..1500 (36px above subtitles) and a 30%
bottom-gap limit. Pixel bounds use edge-sampled background rather than DOM box
sizes, so a large empty SVG or canvas is not counted as filled content.
"""
from __future__ import annotations

import math
from pathlib import Path
from statistics import median

from PIL import Image, ImageChops, ImageFilter

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
CONTENT_TOP = 200
SUBTITLE_TOP = 1536
CONTENT_BOTTOM = SUBTITLE_TOP - 36
MAX_BOTTOM_GAP = .30


def inspect_layout(poster: Path) -> dict:
    """Return a nonblocking review warning and private, reproducible geometry."""
    try:
        with Image.open(poster) as source:
            image = source.convert('RGB').filter(ImageFilter.MedianFilter(3))
    except (OSError, ValueError):
        return {'status': 'unmeasurable', 'reason': 'image_unreadable', 'warnings': []}
    width, height = image.size
    if width < 8 or height < 8 or abs(width * CANVAS_HEIGHT - height * CANVAS_WIDTH) > CANVAS_HEIGHT:
        return {'status': 'unmeasurable', 'reason': 'canvas_geometry_invalid', 'warnings': []}
    pixels = image.load()
    edge = ([pixels[x, 0] for x in range(width)] + [pixels[x, height - 1] for x in range(width)]
            + [pixels[0, y] for y in range(height)] + [pixels[width - 1, y] for y in range(height)])
    background = tuple(round(median([color[channel] for color in edge])) for channel in range(3))
    deviations = sorted(max(abs(a - b) for a, b in zip(color, background)) for color in edge)
    edge_noise = deviations[math.floor(.95 * (len(deviations) - 1))]
    measured = {'imageWidth': width, 'imageHeight': height, 'backgroundRgb': list(background),
                'edgeNoise95': edge_noise, 'contentTop': CONTENT_TOP, 'contentBottomLimit': CONTENT_BOTTOM,
                'subtitleTop': SUBTITLE_TOP, 'bottomGapLimit': MAX_BOTTOM_GAP}
    if edge_noise > 20:
        return {**measured, 'status': 'unmeasurable', 'reason': 'edge_background_not_uniform', 'warnings': []}
    threshold = max(18, edge_noise * 3 + 6)
    difference = ImageChops.difference(image, Image.new('RGB', image.size, background))
    red, green, blue = difference.split()
    contrast = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    mask = contrast.point(lambda value: 255 if value > threshold else 0)
    left = math.ceil(72 * width / CANVAS_WIDTH)
    right = math.floor((CANVAS_WIDTH - 72) * width / CANVAS_WIDTH)
    first = math.ceil(CONTENT_TOP * height / CANVAS_HEIGHT)
    last = math.floor(CONTENT_BOTTOM * height / CANVAS_HEIGHT)
    # Reject isolated compression specks rather than treating each JPEG pixel
    # as an element. Body text at the renderer's minimum font remains visible.
    minimum_pixels = max(3, round(width * .01))
    occupied = [y for y in range(first, last) if mask.crop((left, y, right, y + 1)).histogram()[255] >= minimum_pixels]
    bottom = min(CONTENT_BOTTOM, (occupied[-1] + 1) * CANVAS_HEIGHT / height) if occupied else CONTENT_TOP
    gap = (CONTENT_BOTTOM - bottom) / (CONTENT_BOTTOM - CONTENT_TOP)
    warning = []
    if gap > MAX_BOTTOM_GAP:
        warning = [{'code': 'layout_bottom_gap',
                    'message': f'画面下半截空着：主画面只占到 y={round(bottom)}，离字幕带还空 {gap:.1%}'}]
    return {**measured, 'status': 'measured', 'contrastThreshold': threshold, 'minPixelsPerRow': minimum_pixels,
            'contentFound': bool(occupied), 'contentBottom': round(bottom, 3), 'bottomGapRatio': round(gap, 6), 'warnings': warning}
