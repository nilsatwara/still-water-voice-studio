"""Isolated local inference process. Cancellation terminates this process safely."""
import json
import os
from pathlib import Path
import re
import sys
import time

os.environ.setdefault('TOKENIZERS_PARALLELISM','false')
os.environ.setdefault('HF_HUB_OFFLINE','1')
from speech_text import split_script
from voice_catalog import MODEL_DIR


def publish(source, destination):
    # On Windows a brief reader/antivirus handle can prevent replacement.
    for attempt in range(20):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if attempt == 19: raise
            time.sleep(.05)


def chunks(text, limit):
    sentences=re.split(r'(?<=[.!?。！？])\s*|\n+',text)
    current=''
    for sentence in sentences:
        if not sentence.strip(): continue
        pieces=[sentence]
        if len(sentence)>limit:
            import textwrap
            pieces=textwrap.wrap(sentence,width=limit,break_long_words=True,break_on_hyphens=False)
        for piece in pieces:
            if current and len(current)+len(piece)+1>limit:
                yield current
                current=''
            current+=((' ' if current else '')+piece)
    if current: yield current


def run(job, folder):
    import numpy as np
    import soundfile as sf
    import torch
    # Use the bundled offline Japanese dictionary instead of an absent full UniDic download.
    if job['voice'].startswith('j'):
        import unidic
        import unidic_lite
        unidic.DICDIR=unidic_lite.DICDIR
    from kokoro import KModel, KPipeline
    torch.set_num_threads(min(4,os.cpu_count() or 2))
    torch.manual_seed(job.get('seed',12345))
    torch.use_deterministic_algorithms(True, warn_only=True)
    device=job.get('device','cpu')
    if device=='auto': device='cuda' if torch.cuda.is_available() else 'cpu'
    if device=='cuda' and not torch.cuda.is_available(): raise ValueError('CUDA is not available on this PC. Choose CPU.')
    model=KModel(repo_id='hexgrad/Kokoro-82M',config=str(MODEL_DIR/'config.json'),model=str(MODEL_DIR/'kokoro-v1_0.pth')).to(device).eval()
    voice=job['voice']
    pipeline=KPipeline(lang_code=voice[0],repo_id='hexgrad/Kokoro-82M',model=model)
    weights=[(voice,1.0)]
    if job.get('blend'):
        weights=[(entry['voice'],entry['weight']) for entry in job['blend']]
    total=sum(weight for _,weight in weights)
    # One fixed embedding is reused for every segment in the entire recording.
    pack=sum(torch.load(MODEL_DIR/'voices'/f'{name}.pt',weights_only=True)*weight/total for name,weight in weights)
    pieces=split_script(job['text'],job.get('paragraph_pause',0))
    duration=0
    words=[]
    segments=[]
    count=0
    spoken_total=sum(len(text) for kind,text in pieces if kind=='text')
    progress_file=folder/'progress.json'
    live_files=[]
    live_folder=Path(job['_live_folder']) if job.get('_live_folder') else None
    def live(samples):
        if live_folder is None: return
        name=f"{job['_live_run']}-{len(live_files):05d}.wav"
        sf.write(live_folder/(name+'.tmp'),samples,24000,subtype='PCM_16',format='WAV')
        publish(live_folder/(name+'.tmp'),live_folder/name)
        live_files.append(name)
        manifest=live_folder/'manifest.tmp'
        manifest.write_text(json.dumps({'run':job['_live_run'],'files':live_files}),encoding='utf-8')
        publish(manifest,live_folder/'manifest.json')
    def progress():
        tmp=folder/'progress.tmp'
        tmp.write_text(json.dumps({'progress':min(.95,count/max(1,spoken_total))}),encoding='utf-8')
        publish(tmp,progress_file)
    with sf.SoundFile(folder/'master.wav',mode='w',samplerate=24000,channels=1,subtype='PCM_24') as output:
        for kind,value in pieces:
            if kind=='silence':
                samples=np.zeros(round(value*24000),dtype=np.float32)
                output.write(samples)
                live(samples)
                segments.append({'type':'silence','start':duration,'end':duration+len(samples)/24000})
                duration+=len(samples)/24000
                continue
            limit=300 if voice[0] in 'ab' else job.get('subtitle_width',42)*2-4
            for part in chunks(value,limit):
                produced=False
                for result in pipeline(part,voice=pack,speed=job['speed'],split_pattern=None):
                    if result.audio is None or not len(result.audio): raise RuntimeError('Kokoro returned empty audio.')
                    samples=result.audio.numpy().astype(np.float32)
                    if not np.isfinite(samples).all(): raise RuntimeError('Kokoro produced invalid audio samples.')
                    end=duration+len(samples)/24000
                    if result.tokens:
                        local=[]
                        pending=''
                        for token in result.tokens:
                            start=getattr(token,'start_ts',None)
                            stop=getattr(token,'end_ts',None)
                            if start is not None and stop is not None and stop>start:
                                local.append({'text':pending+token.text,'prefix':' ' if local else '',
                                              'start':min(end,duration+max(0,start)),
                                              'end':min(end,duration+max(0,stop))})
                                pending=''
                            elif token.text.strip():
                                if local: local[-1]['text']+=(' ' if token.text[0].isalnum() else '')+token.text
                                else: pending+=token.text
                        if local: words.extend(local)
                        else: raise RuntimeError('Kokoro produced no English token timings.')
                    else:
                        # Non-English output: measured phrase timing, not fabricated word alignment.
                        words.append({'text':result.graphemes,'prefix':' ','start':duration,'end':end})
                    output.write(samples)
                    live(samples)
                    segments.append({'type':'speech','start':duration,'end':end,'text':result.graphemes})
                    duration=end
                    produced=True
                if not produced: raise RuntimeError('Kokoro could not pronounce a text segment. Check the selected language.')
                count+=len(part)
                progress()
    result={'words':words,'segments':segments,'duration':duration,'source':'kokoro','device':device,
            'native_sample_rate':24000,'voice':voice,'blend':weights,'seed':job.get('seed',12345)}
    (folder/'timing.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')


if __name__=='__main__':
    folder=Path(sys.argv[1])
    try:
        run(json.loads((folder/'job.json').read_text(encoding='utf-8')),folder)
    except Exception as exc:
        (folder/'error.txt').write_text(f'{type(exc).__name__}: {exc}',encoding='utf-8')
        raise
