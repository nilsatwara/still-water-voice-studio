"""Live integration checks against the isolated V2 server."""
import io
import json
from pathlib import Path
import re
import time
import sys
import zipfile
from urllib.request import Request,urlopen
import numpy as np
import soundfile as sf
from mutagen.mp3 import MP3
from live_check import PRAYER

BASE='http://127.0.0.1:8767'
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results'/'v2-data'/'outputs'

def api(path,body=None):
    with urlopen(Request(BASE+path,data=json.dumps(body).encode() if body is not None else None,
                         headers={'Content-Type':'application/json'}),timeout=120) as r:return json.load(r)


if __name__=='__main__':
    edge=api('/api/voices?engine=edge')
    kokoro=api('/api/voices?engine=kokoro')
    assert len(edge['voices'])>300 and len(kokoro['voices'])==54
    script='Take a slow breath. [1s silence] Let your heart be still. [2s silence] You can rest for a moment. [3s silence] May peace be with you today. [4s silence] There is hope for tomorrow. [5s silence] Begin again with a gentle heart.'
    ids=[j['id'] for j in api('/api/state')['jobs'] if j['title'].startswith('V2 test - ')] if '--existing' in sys.argv else api('/api/jobs',{'jobs':[
        {'title':'V2 test - Edge exact pauses','text':script,'engine':'edge','voice':'en-US-ChristopherNeural','speed':.85,'pitch':-5,'volume':0,'export_format':'mp3_44100_320'},
        {'title':'V2 test - Kokoro fixed female blend','text':script,'engine':'kokoro','voice':'af_heart','speed':.85,
         'blend':[{'voice':'af_heart','weight':70},{'voice':'af_bella','weight':30}],'export_format':'mp3_48000_320','seed':12345},
        {'title':'V2 test - Edge long prayer','text':PRAYER.replace('\n\n','\n\n[3s silence]\n\n',1),'engine':'edge','voice':'en-US-ChristopherNeural','speed':.8,'pitch':-12,'export_format':'mp3_44100_192'},
        {'title':'V2 test - Kokoro male prayer','text':PRAYER[:PRAYER.index('I pray for')].strip()+' [3s silence] Amen.','engine':'kokoro','voice':'am_michael','speed':.8,'export_format':'wav_24000'},
    ]})['ids']
    started=time.time()
    previous=None
    while time.time()-started<1000:
        jobs=[j for j in api('/api/state')['jobs'] if j['id'] in ids]
        status=[(j['status'],round(j['progress'],1),j['attempts']) for j in jobs]
        if status!=previous:print(status,flush=True);previous=status
        if any(j['status']=='retrying' for j in jobs):raise RuntimeError(str([(j['title'],j['error']) for j in jobs if j['error']]))
        if all(j['status']=='completed' for j in jobs):break
        time.sleep(2)
    else:raise TimeoutError('Long-form generation timed out')
    report=[]
    for index,job in enumerate(jobs):
        meta=json.loads((OUT/(job['id']+'.json')).read_text(encoding='utf-8'))
        samples,rate=sf.read(OUT/(job['id']+'.wav'),dtype='float32')
        for segment in meta['segments']:
            if segment['type']=='silence':
                center=samples[round((segment['start']+.02)*rate):round((segment['end']-.02)*rate)]
                assert len(center)>0 and np.max(np.abs(center))<1e-5,'Pause contains spoken audio'
                assert round(segment['end']-segment['start']) in range(1,6)
        previous_end=0
        for cue in meta['captions']:
            assert cue['start']>=previous_end and cue['end']>cue['start'] and cue['end']<=len(samples)/rate+.01
            assert '[3s silence]' not in cue['text']
            assert len(cue['text'].splitlines())<=2,(job['title'],cue)
            assert all(len(line)<=job['subtitle_width'] for line in cue['text'].splitlines())
            previous_end=cue['end']
        srt=(OUT/(job['id']+'.srt')).read_bytes()
        assert re.search(rb'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}',srt)
        assert b'\r\n\r\n' in srt
        mp3=MP3(OUT/(job['id']+'.mp3'))
        assert mp3.info.sample_rate==meta['export_sample_rate']
        assert abs(mp3.info.bitrate/1000-meta['export_mp3_kbps'])<2
        if index:assert job['started']>=jobs[index-1]['completed'],'Queue overlap'
        report.append({'title':job['title'],'engine':job['engine'],'audio_seconds':round(mp3.info.length,3),
                       'render_seconds':round(job['completed']-job['started'],2),'sample_rate':mp3.info.sample_rate,
                       'mp3_kbps':round(mp3.info.bitrate/1000),'captions':len(meta['captions']),'pauses':sum(x['type']=='silence' for x in meta['segments'])})
    with urlopen(BASE+'/api/archive?ids='+','.join(ids),timeout=120) as response:bundle=response.read()
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        assert len(archive.namelist())==20
        assert archive.testzip() is None
    with urlopen(BASE+'/api/archive?merge=1&ids='+ids[0]+','+ids[2],timeout=120) as response:bundle=response.read()
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        assert 'Combined recording/merged.srt' in archive.namelist()
        merged=json.loads(archive.read('Combined recording/merged.json'))
        assert len(merged['chapters'])==2
    (ROOT/'test-results'/'v2-live.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
