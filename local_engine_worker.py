"""One-shot Kitten/Piper worker used by memory-constrained deployments."""
import asyncio
import json
from pathlib import Path
import sys

from audio_engine import AudioEngine


async def run(engine, folder):
    folder = Path(folder).resolve()
    job = json.loads((folder/'job.json').read_text(encoding='utf-8'))
    instance = AudioEngine()

    def progress(value):
        temporary = folder/'progress.tmp'
        temporary.write_text(json.dumps({'progress':value}), encoding='utf-8')
        temporary.replace(folder/'progress.json')

    try:
        if engine == 'kitten': timing = await instance.kitten(job,folder,progress)
        elif engine == 'piper': timing = await instance.piper(job,folder,progress)
        else: raise ValueError('Unsupported isolated engine.')
        (folder/'timing.json').write_text(json.dumps(timing,ensure_ascii=False),encoding='utf-8')
    except Exception as exc:
        (folder/'error.txt').write_text(f'{type(exc).__name__}: {exc}',encoding='utf-8')
        raise
    finally:
        await instance.close()


if __name__ == '__main__':
    if len(sys.argv) != 3: raise SystemExit('Usage: local_engine_worker.py ENGINE FOLDER')
    asyncio.run(run(sys.argv[1],sys.argv[2]))
