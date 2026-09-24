#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -r requirements-lightweight.txt

enabled() {
  case "${1:-false}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

if enabled "${ENABLE_KOKORO:-false}"; then
  python -m pip install 'torch==2.6.0+cpu' --index-url https://download.pytorch.org/whl/cpu
  python -m pip install -r requirements-kokoro.txt
  python setup_models.py
fi

if enabled "${ENABLE_KITTEN:-false}"; then
  python -m pip install -r requirements-kitten.txt
  python setup_render_models.py --engine kitten
fi

if enabled "${ENABLE_PIPER:-false}"; then
  python -m pip install -r requirements-piper.txt
  python setup_render_models.py --engine piper
fi

if enabled "${ENABLE_CHATTERBOX:-false}"; then
  python -m pip install 'torch==2.6.0+cpu' --index-url https://download.pytorch.org/whl/cpu
  python -m venv --system-site-packages .venv-chatterbox
  .venv-chatterbox/bin/python -m pip install 'torchaudio==2.6.0+cpu' --index-url https://download.pytorch.org/whl/cpu
  CHATTERBOX_VENV="$PWD/.venv-chatterbox" .venv-chatterbox/bin/python setup_chatterbox.py
fi

python -m compileall -q server.py audio_engine.py voice_catalog.py local_engine_worker.py
echo 'Stillwater Render build completed.'
