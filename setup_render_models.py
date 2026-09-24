"""Download the fixed Piper and Kitten assets used by a Render build."""
import argparse
import json
import os
from pathlib import Path
import shutil

from huggingface_hub import hf_hub_download, snapshot_download

ROOT = Path(__file__).resolve().parent
MODEL_ROOT = Path(os.getenv('STILLWATER_MODEL_DIR', str(ROOT / 'models'))).expanduser().resolve()
PIPER_REPO = 'rhasspy/piper-voices'
PIPER_REVISION = 'c10ece1aade47bb51c153c893d14e5bf8e5b7117'
KITTEN_REPO = 'KittenML/kitten-tts-micro-0.8'
KITTEN_REVISION = '1ccf72b2c2048fd17efac7de2fab32d10e225084'
PIPER_FILES = [
    'en/en_US/arctic/medium/en_US-arctic-medium.onnx',
    'en/en_US/arctic/medium/en_US-arctic-medium.onnx.json',
    'en/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx',
    'en/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx.json',
    'en/en_US/hfc_male/medium/en_US-hfc_male-medium.onnx',
    'en/en_US/hfc_male/medium/en_US-hfc_male-medium.onnx.json',
    'en/en_US/lessac/high/en_US-lessac-high.onnx',
    'en/en_US/lessac/high/en_US-lessac-high.onnx.json',
    'en/en_US/ryan/high/en_US-ryan-high.onnx',
    'en/en_US/ryan/high/en_US-ryan-high.onnx.json',
]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=('piper','kitten','all'), default='all')
    args = parser.parse_args()
    os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
    if args.engine in ('piper','all'):
        piper_dir = MODEL_ROOT / 'piper'
        piper_dir.mkdir(parents=True, exist_ok=True)
        for filename in PIPER_FILES:
            source = Path(hf_hub_download(PIPER_REPO, filename, revision=PIPER_REVISION))
            shutil.copy2(source, piper_dir / source.name)
        (piper_dir / 'revision.json').write_text(
            json.dumps({'repository': PIPER_REPO, 'revision': PIPER_REVISION}), encoding='utf-8')

    if args.engine in ('kitten','all'):
        snapshot_download(KITTEN_REPO, revision=KITTEN_REVISION,
                          cache_dir=MODEL_ROOT / 'kitten',
                          allow_patterns=['*.onnx', '*.npz', '*.json'])
        (MODEL_ROOT / 'kitten' / 'revision.json').write_text(
            json.dumps({'repository': KITTEN_REPO, 'revision': KITTEN_REVISION}), encoding='utf-8')
    print(args.engine.title(), 'model assets are ready.')
