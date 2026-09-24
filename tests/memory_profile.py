"""Opt-in process-tree RSS measurement for the repository's installed TTS engines."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'test-results' / 'memory-profile'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VOICES = {
    'edge': 'en-US-AndrewNeural',
    'kokoro': 'af_heart',
    'kitten': 'Jasper',
    # The largest installed Piper pack gives a conservative measured peak.
    'piper': 'en_US-ryan-high',
    'chatterbox': 'builtin',
}


async def child(engine, control):
    os.environ['STILLWATER_PROFILE'] = 'full'
    os.environ['MODEL_IDLE_TIMEOUT_SECONDS'] = '0'
    if engine in ('kitten','piper'):
        os.environ['ISOLATE_LOCAL_ENGINES'] = 'true'
    from audio_engine import AudioEngine

    base = ROOT/'data'/'outputs' if engine == 'chatterbox' else RESULTS
    folder = base / (engine + '-' + uuid.uuid4().hex)
    folder.mkdir(parents=True, exist_ok=True)
    instance = AudioEngine()
    control.write_text(json.dumps({'phase':'idle'}), encoding='utf-8')
    while json.loads(control.read_text(encoding='utf-8'))['phase'] != 'go':
        await asyncio.sleep(.05)
    job = {
        'engine':engine, 'voice':VOICES[engine],
        'text':'Take a slow breath and let this peaceful morning begin.',
        'speed':.8, 'pitch':-5 if engine=='edge' else 0, 'volume':0,
        'export_format':'mp3_44100_192', 'normalize':True, 'output_gain':0,
        'paragraph_pause':0, 'subtitle_width':42, 'subtitle_seconds':6,
        'seed':12345, 'device':'cpu', 'blend':[], 'live_preview':False,
        'temperature':.8, 'top_p':.95, 'top_k':1000, 'repetition_penalty':1.2,
    }
    started = time.monotonic()
    try:
        duration = await instance.generate(job, folder/'result')
        detail = {'engine':engine, 'audio_seconds':duration,
                  'wall_seconds':round(time.monotonic()-started,2)}
        await instance.unload(engine)
        control.write_text(json.dumps({'phase':'unloaded','detail':detail}), encoding='utf-8')
        while json.loads(control.read_text(encoding='utf-8'))['phase'] != 'exit':
            await asyncio.sleep(.05)
        print(json.dumps(detail), flush=True)
    finally:
        await instance.close()
        shutil.rmtree(folder, ignore_errors=True)


def rss_tree(process):
    import psutil
    try:
        root = psutil.Process(process.pid)
        members = [root, *root.children(recursive=True)]
    except psutil.NoSuchProcess:
        return 0
    total = 0
    for member in members:
        try: total += member.memory_info().rss
        except psutil.NoSuchProcess: pass
    return total


def measure(engine, timeout):
    RESULTS.mkdir(parents=True, exist_ok=True)
    control = RESULTS / (engine + '-control.json')
    control.unlink(missing_ok=True)
    environment = os.environ.copy()
    environment.update({'STILLWATER_PROFILE':'full', 'MODEL_IDLE_TIMEOUT_SECONDS':'0'})
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), '--child', engine, str(control)],
        cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )
    deadline = time.monotonic() + 30
    while not control.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(.05)
    if not control.exists():
        output, _ = process.communicate(timeout=5)
        raise RuntimeError(f'{engine} did not reach idle measurement state: {output}')
    time.sleep(.5)
    idle = rss_tree(process)
    control.write_text(json.dumps({'phase':'go'}), encoding='utf-8')
    peak = idle
    deadline = time.monotonic() + timeout
    unloaded = None
    while process.poll() is None and time.monotonic() < deadline:
        peak = max(peak, rss_tree(process))
        try:
            state = json.loads(control.read_text(encoding='utf-8'))
            if state.get('phase') == 'unloaded':
                unloaded = state
                break
        except (OSError, ValueError): pass
        time.sleep(.05)
    if unloaded is None and process.poll() is None:
        process.kill()
        raise TimeoutError(f'{engine} exceeded {timeout} seconds')
    if unloaded is not None:
        time.sleep(.75)
        post_unload = rss_tree(process)
        control.write_text(json.dumps({'phase':'exit'}), encoding='utf-8')
    else:
        post_unload = 0
    process.wait(timeout=30)
    output, _ = process.communicate()
    control.unlink(missing_ok=True)
    if process.returncode:
        raise RuntimeError(f'{engine} failed:\n{output}')
    detail = json.loads(output.strip().splitlines()[-1])
    result = {**detail, 'idle_rss_mib':round(idle/1024/1024,1),
              'peak_tree_rss_mib':round(peak/1024/1024,1),
              'post_unload_rss_mib':round(post_unload/1024/1024,1)}
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('engines', nargs='*', choices=tuple(VOICES))
    parser.add_argument('--child', nargs=2, metavar=('ENGINE','CONTROL'))
    parser.add_argument('--timeout', type=int, default=1200)
    args = parser.parse_args()
    if args.child:
        asyncio.run(child(args.child[0], Path(args.child[1])))
    else:
        engines = args.engines or list(VOICES)
        results = [measure(engine, args.timeout) for engine in engines]
        (RESULTS/'latest.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
