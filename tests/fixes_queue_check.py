import io
import json
from pathlib import Path
import time
import zipfile
from urllib.request import Request, urlopen
import numpy as np
import soundfile as sf

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8767'
def api(path,body=None):
    with urlopen(Request(BASE+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'}),timeout=60) as r:return json.load(r)

text="As this morning continues, prepare my heart. [1s silence] There is mercy for a new morning.\n\n**-----------------------------------------------------------------------------------------**\n\nFather, thank You for a new morning. [3s silence] Help me find peace today."
ids=api('/api/jobs',{'jobs':[{'title':'Separator and pause verification','engine':'edge','voice':'en-US-ChristopherNeural','speed':.8,'text':text}]})['ids']
assert len(ids)==2
for _ in range(120):
    jobs=[j for j in api('/api/state')['jobs'] if j['id'] in ids]
    assert all(j['status']!='retrying' for j in jobs),jobs
    if all(j['status']=='completed' for j in jobs): break
    time.sleep(1)
else:raise TimeoutError('The queue did not finish')
assert jobs[1]['started']>=jobs[0]['completed']
for job,pause in zip(jobs,[1,3]):
    stem=ROOT/'test-results/fixes-data/outputs'/job['id']
    meta=json.loads(stem.with_suffix('.json').read_text(encoding='utf-8'))
    silence=next(s for s in meta['segments'] if s['type']=='silence')
    assert abs(silence['end']-silence['start']-pause)<.001
    samples,sr=sf.read(stem.with_suffix('.wav'),dtype='float32')
    center=samples[round((silence['start']+.05)*sr):round((silence['end']-.05)*sr)]
    assert np.max(np.abs(center))<.0001
    captions=meta['captions']
    assert not any('silence' in c['text'] or '---' in c['text'] for c in captions)
    assert any(c['start']>=silence['end']-.001 for c in captions)
with urlopen(BASE+'/api/archive?ids='+','.join(ids)) as response:
    archive=zipfile.ZipFile(io.BytesIO(response.read()))
    assert len(archive.namelist())==10
    assert all(sum(name.endswith('.'+ext) for name in archive.namelist())==2 for ext in ('mp3','wav','srt','vtt','json'))
result={'passed':True,'jobs':ids,'fifo':True,'exact_pauses':[1,3],'zip_files':10}
(ROOT/'test-results/fixes-queue-report.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
