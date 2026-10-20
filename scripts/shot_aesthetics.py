"""Local LAION image aesthetic predictors; all downloads stay in .tools/models."""
from __future__ import annotations

import gc
import hashlib
import os
import time
import urllib.request
from pathlib import Path

V1_REV = '6d122adad522ab246644d9dc1c6d7a3810ee255f'
MODELS = {
    'laion-v1-b32': {
        'clip': 'ViT-B-32', 'dimension': 512,
        'backbone_url': 'https://openaipublic.azureedge.net/clip/models/40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af/ViT-B-32.pt',
        'backbone_sha256': '40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af',
        'head_url': f'https://raw.githubusercontent.com/LAION-AI/aesthetic-predictor/{V1_REV}/sa_0_4_vit_b_32_linear.pth',
        'code_license': 'MIT', 'weights_license': 'MIT repository distribution (predictor head); independent CLIP weight license not explicitly stated',
        'code_source': f'https://github.com/LAION-AI/aesthetic-predictor/blob/{V1_REV}/LICENSE',
        'weights_source': f'https://github.com/LAION-AI/aesthetic-predictor/tree/{V1_REV}',
        'backbone_license_source': 'https://github.com/openai/CLIP/blob/main/LICENSE',
        'backbone_weight_license_status': 'unconfirmed_separate_weight_terms',
        'backbone_weight_license_question': 'https://github.com/openai/CLIP/issues/203',
    },

}


def model_cache() -> Path:
    cache = Path(__file__).resolve().parents[1] / '.tools' / 'models'
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
