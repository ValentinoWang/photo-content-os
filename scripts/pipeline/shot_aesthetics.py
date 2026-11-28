"""Local LAION image aesthetic predictors; all downloads stay in .tools/models."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_ROOT_DIR = str(_Path(__file__).resolve().parents[1])
if _SCRIPTS_ROOT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_ROOT_DIR)
import gc
import hashlib
import os
import time
import urllib.request
from pathlib import Path

if __package__ and "." in __package__:
    from ..constants import (
        V1_REV,
        MODELS,
    )
else:
    import sys as _sys
    from pathlib import Path as _Path
    _sdir = str(_Path(__file__).resolve().parents[1])
    if _sdir not in _sys.path:
        _sys.path.insert(0, _sdir)
    from constants import (
        V1_REV,
        MODELS,
    )


def model_cache() -> Path:
    cache = Path(__file__).resolve().parents[2] / '.tools' / 'models'
    cache.mkdir(parents=True, exist_ok=True)
    # Set before importing libraries which initialize download defaults.
    for name, child in [('HF_HOME','huggingface'),('TORCH_HOME','torch'),('XDG_CACHE_HOME','cache')]:
        os.environ[name] = str(cache/child)
    return cache


class AestheticScorer:
    def __init__(self, name: str, device: str = 'auto'):
        cache = model_cache()
        import torch
        import open_clip
        self.torch = torch
        torch.set_num_threads(2)
        self.name = name
        self.device = 'mps' if device == 'auto' and torch.backends.mps.is_available() else ('cpu' if device=='auto' else device)
        spec = MODELS[name]
        head_path = cache/f'{name}.pth'
        if not head_path.exists():
            temporary = head_path.with_suffix('.download')
            urllib.request.urlretrieve(spec['head_url'], temporary)
            temporary.replace(head_path)
        backbone_path = cache/'clip'/Path(spec['backbone_url']).name
        backbone_path.parent.mkdir(exist_ok=True)
        if not backbone_path.exists():
            temporary = backbone_path.with_suffix('.download')
            urllib.request.urlretrieve(spec['backbone_url'],temporary)
            temporary.replace(backbone_path)
        with backbone_path.open('rb') as stream:
            backbone_hash = hashlib.file_digest(stream,'sha256').hexdigest()
        if backbone_hash != spec['backbone_sha256']:
            raise ValueError('CLIP backbone SHA-256 mismatch; remove the corrupt cached file and retry')
        # The official URL embeds the content hash. Load its verified state into
        # the same QuickGELU architecture; never download a substituted backbone.
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            spec['clip'], pretrained=None, force_quick_gelu=True, device='cpu')
        checkpoint = torch.jit.load(str(backbone_path),map_location='cpu')
        state = checkpoint.state_dict()
        for key in ['input_resolution','context_length','vocab_size']:
            state.pop(key,None)
        self.model.load_state_dict(state)
        del checkpoint, state
        self.model.to(self.device)
        # Text tower is never used for aesthetic scoring.
        if hasattr(self.model, 'transformer'):
            del self.model.transformer
        self.head = torch.nn.Linear(spec['dimension'],1)
        state = torch.load(head_path,map_location='cpu',weights_only=True)
        self.head.load_state_dict(state)
        self.model.eval()
        self.head.to(self.device).eval()
        self.metadata = {**spec, 'name': name, 'device': self.device,
                         'head_sha256': hashlib.sha256(head_path.read_bytes()).hexdigest(),
                         'implementation_license': 'MIT',
                         'implementation_source': 'https://github.com/mlfoundations/open_clip/blob/main/LICENSE'}

    def score(self, image) -> tuple[float,float]:
        torch = self.torch
        started = time.perf_counter()
        tensor = self.preprocess(image.convert('RGB')).unsqueeze(0).to(self.device)
        with torch.inference_mode():
            embedding = self.model.encode_image(tensor).float()
            embedding = embedding/embedding.norm(dim=-1, keepdim=True)
            value = float(self.head(embedding).squeeze().cpu())
        return value, time.perf_counter()-started

    def close(self):
        del self.model, self.head
        gc.collect()
        if self.device=='mps':
            self.torch.mps.empty_cache()
