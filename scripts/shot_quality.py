"""Deterministic shot measurements. Missing measurements stay explicit nulls."""
from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


def read_photo(path: Path):
    if path.suffix.lower() in {'.heic', '.heif'}:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    try:
        with Image.open(path) as source:
            return cv2.cvtColor(np.array(ImageOps.exif_transpose(source).convert('RGB')), cv2.COLOR_RGB2BGR)
    except (OSError, ValueError):
        return None


def read_frame(path: Path, timestamp: float, config: dict):
    result = subprocess.run([
        'ffmpeg', '-v', 'error', '-threads', '1', '-ss', str(timestamp), '-i', str(path),
        '-frames:v', '1', '-vf',
        f"scale={config['measurement_max_edge']}:{config['measurement_max_edge']}:force_original_aspect_ratio=decrease",
        '-threads', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True, timeout=90)
    if result.returncode or not result.stdout:
        return None
    return cv2.imdecode(np.frombuffer(result.stdout, dtype=np.uint8), cv2.IMREAD_COLOR)


def frame_metrics(frame, config: dict) -> dict:
    height, width = frame.shape[:2]
    scale = config['measurement_max_edge'] / max(height, width)
    # All blur measurements use the same long edge, including small synthetic fixtures.
    normalized = cv2.resize(frame, (round(width*scale), round(height*scale)), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(normalized, cv2.COLOR_BGR2GRAY)
    tiles = [float(cv2.Laplacian(tile,cv2.CV_64F).var())
             for strip in np.array_split(gray,4) for tile in np.array_split(strip,4,axis=1)]
    return {
        'blur_variance': float(np.mean(sorted(tiles)[-2:])),
        'whole_frame_variance': float(cv2.Laplacian(gray,cv2.CV_64F).var()),
        'tile_variances': tiles,
        'overexposed_fraction': float(np.mean(gray > config['overexposure_pixel'])),
        'underexposed_fraction': float(np.mean(gray < config['underexposure_pixel'])),
    }


def motion_series(proxy: Path, config: dict) -> dict:
    cap = cv2.VideoCapture(str(proxy))
    frames = []
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    finally:
        cap.release()
    return motion_metrics(frames, config['motion_fps'], config)


def motion_metrics(frames: list, fps: float, config: dict) -> dict:
    if len(frames) < 3:
        return {'samples': [], 'shake_high_frequency': None, 'tracking_fraction': 0.0}
    gray = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) if f.ndim == 3 else f for f in frames]
    width = gray[0].shape[1]
    height = gray[0].shape[0]
    corners = np.array([[0,0,1],[width,0,1],[0,height,1],[width,height,1]], dtype=np.float32)
    samples = []
    displacements = []
    for i, (left, right) in enumerate(zip(gray, gray[1:]), start=1):
        flow = cv2.calcOpticalFlowFarneback(left, right, None, .5, 3, 15, 3, 5, 1.2, 0)
        magnitude = np.linalg.norm(flow, axis=2)
        # Units are fractions of frame width per sampled interval, not raw source pixels.
        samples.append({'time_sec': i/fps, 'flow': float(np.mean(magnitude)/width)})
        features = cv2.goodFeaturesToTrack(left, maxCorners=150, qualityLevel=.01, minDistance=6)
        displacement = None
        if features is not None and len(features) >= 8:
            # Phase correlation supplies a large-translation seed. Without it,
            # LK can lose the scene precisely on the frames with strong shake.
            shift, response = cv2.phaseCorrelate(left.astype(np.float32),right.astype(np.float32))
            guess = features + np.array(shift,dtype=np.float32).reshape(1,1,2)
            tracked, status, _ = cv2.calcOpticalFlowPyrLK(
                left,right,features,guess if response>.1 else None,
                winSize=(31,31),maxLevel=4,
                flags=cv2.OPTFLOW_USE_INITIAL_FLOW if response>.1 else 0)
            if tracked is not None and status is not None:
                valid = status.ravel() == 1
                if np.count_nonzero(valid) >= 8:
                    affine, inliers = cv2.estimateAffinePartial2D(features[valid], tracked[valid], method=cv2.RANSAC)
                    if affine is not None and inliers is not None and np.mean(inliers) >= .5:
                        displacement = ((corners @ affine.T - corners[:,:2])/width).reshape(-1)
        displacements.append(displacement)
    fraction = sum(d is not None for d in displacements) / len(displacements)
    residuals = []
    half = config['shake_window']//2
    for i, displacement in enumerate(displacements):
        if displacement is None:
            continue
        neighbors = [d for d in displacements[max(0,i-half):i+half+1] if d is not None]
        if len(neighbors) >= 3:
            residuals.append(np.mean((displacement - np.median(neighbors, axis=0))**2))
    shake = float(np.sqrt(np.mean(residuals))) if residuals and fraction >= config['min_tracking_fraction'] else None
    return {'samples': samples, 'shake_high_frequency': shake, 'tracking_fraction': fraction}


def split_long_scene(start: float, end: float, flow: list[tuple[float,float]], config: dict):
    if end-start <= config['long_scene_sec']:
        return [(start,end)]
    segments = []
    cursor = start
    changes = [(t,abs(value-flow[i-1][1])) for i,(t,value) in enumerate(flow) if i]
    while end-cursor > config['split_max_sec']:
        low = cursor+config['split_min_sec']
        high = min(cursor+config['split_max_sec'],end-config['split_min_sec'])
        target = min(high,max(low,cursor+config['split_target_sec']))
        options = [(t,change) for t,change in changes if low<=t<=high]
        cut = max(options, key=lambda pair:(pair[1],-abs(pair[0]-target)))[0] if options else target
        segments.append((cursor,cut))
        cursor = cut
    segments.append((cursor,end))
    return segments
