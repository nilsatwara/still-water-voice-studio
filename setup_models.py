"""Download a pinned local Kokoro model and all of its voice embeddings."""
import json
import os
from pathlib import Path

os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parent
REVISION = 'f3ff3571791e39611d31c381e3a41a3af07b4987'
if __name__ == '__main__':
    model_root = Path(os.getenv('STILLWATER_MODEL_DIR', str(ROOT / 'models'))).expanduser().resolve()
    folder = model_root / 'kokoro'
    print('Downloading Kokoro revision', REVISION, flush=True)
    snapshot_download('hexgrad/Kokoro-82M', revision=REVISION, local_dir=folder,
                      allow_patterns=['config.json','kokoro-v1_0.pth','voices/*.pt','VOICES.md','LICENSE'], max_workers=4)
    (folder / 'revision.json').write_text(json.dumps({'repository':'hexgrad/Kokoro-82M','revision':REVISION}),encoding='utf-8')
    print('Kokoro model and',len(list((folder/'voices').glob('*.pt'))),'voices ready.',flush=True)
