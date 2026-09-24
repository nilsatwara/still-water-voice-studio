"""Create the isolated Chatterbox runtime and fetch the pinned Nano model."""
import os
from pathlib import Path
import subprocess
import venv

ROOT = Path(__file__).resolve().parent
MODEL_ROOT = Path(os.getenv('STILLWATER_MODEL_DIR', str(ROOT / 'models'))).expanduser().resolve()
VENV = Path(os.getenv('CHATTERBOX_VENV', str(ROOT / '.venv-chatterbox'))).expanduser().resolve()
REVISION = '5de7a54aa4e5e2baadb0182dde554908b48b85c2'
MODEL_REVISION = '71ccd1d0081b430592cea481f4307e764e07bc64'


def venv_python():
    return VENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


if __name__ == '__main__':
    python = venv_python()
    if not python.is_file():
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(VENV)
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements-chatterbox.txt')], check=True)
    subprocess.run([str(python), '-m', 'pip', 'install', '--no-deps',
                    f'git+https://github.com/resemble-ai/chatterbox.git@{REVISION}'], check=True)
    env = {**os.environ, 'HF_HUB_DISABLE_XET': '1'}
    target = MODEL_ROOT / 'chatterbox-nano'
    code = (
        "from huggingface_hub import snapshot_download; "
        f"print(snapshot_download('ResembleAI/chatterbox-nano', local_dir={str(target)!r}, "
        f"revision='{MODEL_REVISION}', "
        "allow_patterns=['ve.safetensors','t3_nano_v1.safetensors','s3gen_meanflow.safetensors',"
        "'conds.pt','*.json','*.txt']))"
    )
    subprocess.run([str(python), '-c', code], check=True, env=env)
    print('Chatterbox Nano is ready in the isolated CPU environment.')
