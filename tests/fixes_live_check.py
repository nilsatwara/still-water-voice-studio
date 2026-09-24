"""Real previews: voice identity, non-silent PCM, Indic captions, and pause offsets."""
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen
import numpy as np
import soundfile as sf

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results/fixes-data/outputs'
def api(path,body=None):
    with urlopen(Request('http://127.0.0.1:8767'+path,data=json.dumps(body).encode() if body is not None else None,
                         headers={'Content-Type':'application/json'}),timeout=240) as r:return json.load(r)

def normalized(text):return ''.join(c for c in text if not c.isspace())

report=[]
for engine,names in [
    ('edge',['en-US-AndrewNeural','en-US-ChristopherNeural','en-US-JennyNeural','en-US-AriaNeural','gu-IN-DhwaniNeural','gu-IN-NiranjanNeural','hi-IN-SwaraNeural','hi-IN-MadhurNeural']),
    ('kokoro',['af_heart','af_nicole','am_michael','am_adam','hf_alpha','hm_omega']),
]:
    catalog=api('/api/voices?engine='+engine)['voices']
    assert len({v['ShortName'] for v in catalog})==len(catalog)
    for voice in names:
        started=time.time()
        result=api('/api/preview',{'engine':engine,'voice':voice,'speed':.8,'audition':True})
        stem=OUT/Path(result['url']).stem
        meta=json.loads(stem.with_suffix('.json').read_text(encoding='utf-8'))
        assert result['voice']==meta['voice']==meta['settings']['voice']==voice
        assert meta['settings']['blend']==[]
        audio,sr=sf.read(stem.with_suffix('.wav'),dtype='float32')
        rms=float(np.sqrt(np.mean(audio**2)))
        assert rms>.01 and float(np.max(np.abs(audio)))<1
        assert normalized(''.join(c['text'] for c in meta['captions']))==normalized(meta['settings']['text']), (voice,meta['captions'])
        end=0
        for cue in meta['captions']:
            assert 0<=end<=cue['start']<cue['end']<=meta['duration']+.001
            end=cue['end']
        raw=stem.with_suffix('.srt').read_bytes()
        assert re.search(rb'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}',raw)
        assert b'\r\n\r\n' in raw
        item={'engine':engine,'voice':voice,'url':result['url'],'rms':round(rms,4),'duration':round(len(audio)/sr,2),
              'pcm_sha256':hashlib.sha256(audio.tobytes()).hexdigest(),'elapsed':round(time.time()-started,1)}
        report.append(item)
        (ROOT/'test-results/fixes-audio-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(item),flush=True)
assert len({r['pcm_sha256'] for r in report})==len(report),'Duplicate audio across different voices'
print('PASS: all tested voices produced distinct non-silent audio and valid captions',flush=True)
