"""Prepare every library sample once so voice cards play without live synthesis."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import numpy as np
import soundfile as sf
import edge_tts
import imageio_ffmpeg
from auditions import audition_name, audition_text
from voice_catalog import kokoro_voices, kitten_voices, piper_voices, chatterbox_voices, MODEL_DIR
from audio_engine import AudioEngine

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'data/auditions'
OUT.mkdir(parents=True,exist_ok=True)
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()
FLAGS=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0

async def edge_samples():
    voices=json.loads((ROOT/'data/voices.json').read_text(encoding='utf-8'))
    limit=asyncio.Semaphore(4)
    async def generate(voice):
        name=voice['ShortName'];target=OUT/audition_name('edge',name)
        if target.exists(): return
        async with limit:
            for attempt in range(3):
                try:
                    text,_=audition_text(name,voices)
                    temp=target.with_suffix('.tmp')
                    # Provider Name also handles locales with a script subtag
                    # (iu-Latn-CA), which edge-tts's ShortName regex rejects.
                    await edge_tts.Communicate(text,voice['Name'],rate='+0%',pitch='+0Hz',volume='+0%').save(str(temp))
                    if temp.stat().st_size<1000: raise RuntimeError('Empty sample')
                    os.replace(temp,target)
                    print('READY edge '+name,flush=True)
                    return
                except Exception as exc:
                    if attempt==2: print('FAILED edge '+name+' '+str(exc),flush=True)
                    else: await asyncio.sleep(2)
    await asyncio.gather(*(generate(v) for v in voices))

def kokoro_samples():
    voices=kokoro_voices()
    missing=[v for v in voices if not (OUT/audition_name('kokoro',v['ShortName'])).exists()]
    if not missing: return
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TOKENIZERS_PARALLELISM']='false'
    import torch
    import unidic
    import unidic_lite
    unidic.DICDIR=unidic_lite.DICDIR
    from kokoro import KModel,KPipeline
    torch.set_num_threads(4)
    model=KModel(repo_id='hexgrad/Kokoro-82M',config=str(MODEL_DIR/'config.json'),model=str(MODEL_DIR/'kokoro-v1_0.pth')).eval()
    pipelines={}
    for voice in missing:
        name=voice['ShortName'];target=OUT/audition_name('kokoro',name)
        try:
            torch.manual_seed(12345)
            if name[0] not in pipelines:
                pipelines[name[0]]=KPipeline(lang_code=name[0],repo_id='hexgrad/Kokoro-82M',model=model)
            pack=torch.load(MODEL_DIR/'voices'/f'{name}.pt',weights_only=True)
            text,_=audition_text(name,voices)
            with torch.inference_mode():
                samples=np.concatenate([r.audio.numpy() for r in pipelines[name[0]](text,voice=pack,speed=1)])
            peak=float(np.max(np.abs(samples)))
            if peak<=0 or not np.isfinite(samples).all(): raise RuntimeError('Silent sample')
            with tempfile.TemporaryDirectory(dir=OUT) as folder:
                wav=Path(folder)/'sample.wav';mp3=Path(folder)/'sample.mp3'
                sf.write(wav,samples*(.89/peak),24000)
                subprocess.run([FFMPEG,'-v','error','-y','-i',str(wav),'-ar','44100','-b:a','128k',str(mp3)],check=True,creationflags=FLAGS)
                os.replace(mp3,target)
            print('READY kokoro '+name,flush=True)
        except Exception as exc: print('FAILED kokoro '+name+' '+str(exc),flush=True)


async def local_samples(engine, voices):
    """Render lightweight local-engine auditions through the production path."""
    speech=AudioEngine()
    missing=[v for v in voices if not (OUT/audition_name(engine,v['ShortName'])).exists()]
    for voice in missing:
        name=voice['ShortName'];target=OUT/audition_name(engine,name)
        try:
            text,_=audition_text(name,voices)
            with tempfile.TemporaryDirectory(dir=OUT) as folder_name:
                folder=Path(folder_name)
                job={'engine':engine,'voice':name,'text':text,'speed':1.0,
                     'paragraph_pause':0,'pitch':0,'volume':0}
                if engine=='piper': await speech.piper(job,folder,None)
                elif engine=='chatterbox':
                    job.update(seed=12345,temperature=.8,top_p=.95,top_k=1000,repetition_penalty=1.2)
                    await speech.chatterbox(job,folder,None)
                else: await speech.kitten(job,folder,None)
                await asyncio.to_thread(subprocess.run,
                    [FFMPEG,'-v','error','-y','-i',str(folder/'master.wav'),
                     '-ar','44100','-b:a','128k',str(folder/'sample.mp3')],
                    check=True,creationflags=FLAGS)
                os.replace(folder/'sample.mp3',target)
            print('READY '+engine+' '+name,flush=True)
        except Exception as exc:
            print('FAILED '+engine+' '+name+' '+str(exc),flush=True)
    await speech.close()

if __name__=='__main__':
    import sys
    started=time.time()
    if '--edge' in sys.argv: asyncio.run(edge_samples())
    elif '--piper' in sys.argv: asyncio.run(local_samples('piper',piper_voices()))
    elif '--kitten' in sys.argv: asyncio.run(local_samples('kitten',kitten_voices()))
    elif '--chatterbox' in sys.argv: asyncio.run(local_samples('chatterbox',chatterbox_voices()))
    else: kokoro_samples()
    from publish_auditions import publish
    publish()
    print('DONE seconds '+str(round(time.time()-started,1)),flush=True)
