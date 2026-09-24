"""Persistent, isolated Chatterbox Nano CPU inference worker.

The parent process sends one JSON job-file path per line. Model/library output is
kept off stdout so stdout remains a small machine-readable progress protocol.
"""
import json
import os
from pathlib import Path
import re
import sys
import traceback

os.environ.setdefault('HF_HUB_OFFLINE','1')
os.environ.setdefault('TOKENIZERS_PARALLELISM','false')
os.environ.setdefault('OMP_NUM_THREADS','3')
os.environ.setdefault('MKL_NUM_THREADS','3')

ROOT=Path(__file__).resolve().parent
DATA=Path(os.getenv('STILLWATER_DATA_DIR',str(ROOT/'data'))).expanduser().resolve()
MODEL_ROOT=Path(os.getenv('STILLWATER_MODEL_DIR',str(ROOT/'models'))).expanduser().resolve()
MODEL=(MODEL_ROOT/'chatterbox-nano').resolve()
protocol=sys.stdout
sys.stdout=sys.stderr


def emit(**value):
    protocol.write(json.dumps(value,ensure_ascii=False)+'\n')
    protocol.flush()


def chunks(text,limit=460):
    sentences=re.split(r'(?<=[.!?])\s+',text.strip())
    result=[]; current=''
    for sentence in sentences:
        while len(sentence)>limit:
            cut=sentence.rfind(' ',0,limit)
            cut=cut if cut>40 else limit
            head,sentence=sentence[:cut].strip(),sentence[cut:].strip()
            if current: result.append(current); current=''
            if head: result.append(head)
        candidate=(current+' '+sentence).strip()
        if current and len(candidate)>limit:
            result.append(current); current=sentence
        else: current=candidate
    if current: result.append(current)
    return result


def safe_path(value,root):
    path=Path(value).resolve()
    if path!=root and root not in path.parents: raise ValueError('Unsafe worker path.')
    return path


def run(model,job_path,voice_state):
    import numpy as np
    import soundfile as sf
    import torch
    from speech_text import split_script
    job_path=safe_path(job_path,DATA)
    job=json.loads(job_path.read_text(encoding='utf-8'))
    folder=safe_path(job['folder'],DATA)
    folder.mkdir(parents=True,exist_ok=True)
    voice=str(job['voice'])
    if voice==voice_state.get('voice'):
        # The previous job already prepared this exact voice. Reusing the
        # conditionals avoids rerunning the reference encoder between parts.
        pass
    elif voice=='builtin':
        # Restore the packaged conditionals if the previous job used a clone.
        from chatterbox.tts_turbo import Conditionals
        model.conds=Conditionals.load(MODEL/'conds.pt',map_location='cpu').to('cpu')
        voice_state['voice']=voice
    elif re.fullmatch(r'clone-[a-f0-9]{32}',voice):
        reference=safe_path(DATA/'chatterbox-voices'/(voice+'.wav'),DATA/'chatterbox-voices')
        if not reference.is_file(): raise ValueError('The selected cloned voice no longer exists.')
        model.prepare_conditionals(str(reference),norm_loudness=True)
        voice_state['voice']=voice
    else: raise ValueError('Unknown Chatterbox voice.')

    pieces=split_script(job['text'],job.get('paragraph_pause',0))
    speech=[chunk for kind,value in pieces if kind=='text' for chunk in chunks(value)]
    total=max(1,len(speech)); done=0; duration=0.0; words=[]; segments=[]
    sample_rate=int(model.sr)
    with sf.SoundFile(folder/'master-raw.wav',mode='w',samplerate=sample_rate,channels=1,subtype='PCM_24') as output:
        for kind,value in pieces:
            if kind=='silence':
                samples=np.zeros(round(value*sample_rate),dtype=np.float32)
                output.write(samples); segments.append({'type':'silence','start':duration,'end':duration+value}); duration+=value
                continue
            for text in chunks(value):
                torch.manual_seed(int(job['seed'])+done)
                with torch.inference_mode():
                    wav=model.generate(text,temperature=job['temperature'],top_p=job['top_p'],
                                       top_k=job['top_k'],repetition_penalty=job['repetition_penalty'])
                samples=wav.squeeze().detach().cpu().numpy().astype(np.float32)
                if not len(samples) or not np.isfinite(samples).all(): raise RuntimeError('Chatterbox returned invalid audio.')
                length=len(samples)/sample_rate; tokens=list(re.finditer(r'\S+',text)); weight=sum(max(1,len(m.group())) for m in tokens) or 1; cursor=0
                for index,match in enumerate(tokens):
                    start=duration+length*cursor/weight; cursor+=max(1,len(match.group()))
                    words.append({'text':match.group(),'prefix':text[tokens[index-1].end():match.start()] if index else text[:match.start()],
                                  'start':start,'end':duration+length*cursor/weight})
                output.write(samples); segments.append({'type':'speech','start':duration,'end':duration+length,'text':text}); duration+=length
                done+=1; emit(event='progress',progress=min(.88,done/total*.88))
    result={'words':words,'segments':segments,'duration':duration,'source':'chatterbox','native_sample_rate':sample_rate,
            'voice':voice,'timing_method':'measured proportional word timing','watermarked':True}
    (folder/'timing-raw.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    emit(event='done')


def main():
    import torch
    # Three threads uses this PC's logical CPU efficiently while leaving one
    # logical core responsive for the browser and queue server.
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    from chatterbox.tts_turbo import ChatterboxTurboTTS
    emit(event='loading')
    model=ChatterboxTurboTTS.from_local(MODEL,device='cpu',nano=True)
    emit(event='ready')
    voice_state={}
    for line in sys.stdin:
        try: run(model,line.strip(),voice_state)
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            emit(event='error',error=f'{type(exc).__name__}: {exc}')


if __name__=='__main__': main()
