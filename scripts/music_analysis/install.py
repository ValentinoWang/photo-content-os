"""Install the isolated, pinned music runtime and authenticated offline model assets."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request


def fetch(url, target, expected):
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        return
    temp = target.with_suffix(target.suffix + '.download')
    try:
        urllib.request.urlretrieve(url, temp)
        if hashlib.sha256(temp.read_bytes()).hexdigest() != expected:
            raise ValueError('model SHA-256 mismatch: ' + target.name)
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)


def install(root, *, python=None):
    lock = json.loads((root / 'third_party/edit-tools.lock.json').read_text())['music_analysis']
    env = root / lock['directory']
    interpreter = env / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    python = python or os.environ.get('MUSIC_ANALYSIS_PYTHON', 'python3.12')
    if not interpreter.exists():
        subprocess.run([python, '-m', 'venv', str(env)], check=True)
    version = subprocess.run([str(interpreter), '-c', 'import sys;print("%s.%s"%sys.version_info[:2])'], check=True, capture_output=True, text=True).stdout.strip()
    if version != lock['python']:
        raise ValueError('music runtime Python mismatch; recreate .tools/music-analysis with Python ' + lock['python'])
    subprocess.run([str(interpreter), '-m', 'ensurepip', '--upgrade'], check=True)
    subprocess.run([str(interpreter), '-m', 'pip', 'install', '-r', str(root / 'third_party/music-analysis.requirements.lock.txt')], check=True)
    models = env / 'models'
    models.mkdir(exist_ok=True)
    registry = json.loads((root / 'music-analysis.registry.json').read_text())
    for spec in registry['analyzers']['tags']['models']:
        fetch(spec['url'], models / (spec['id']+'.pb'), spec['sha256'])
    for spec in [lock['beat_checkpoint'], *lock['metadata'].values()]:
        fetch(spec['url'], models / spec['file'], spec['sha256'])
    versions = subprocess.run([str(interpreter), '-c', 'import importlib.metadata,json;print(json.dumps({p:importlib.metadata.version(p) for p in '+repr(list(lock['packages']))+'}))'], check=True, capture_output=True, text=True)
    if json.loads(versions.stdout) != lock['packages']:
        raise ValueError('music runtime package version mismatch')
    print('Music analysis runtime and model hashes OK')
