"""Final main-app verification with a labelled Kokoro demonstration."""
import json
import time
from pathlib import Path
from urllib.request import Request,urlopen
from playwright.sync_api import sync_playwright
from mutagen.mp3 import MP3

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8766'
def api(path,body=None):
    with urlopen(Request(BASE+path,data=json.dumps(body).encode() if body is not None else None,
                         headers={'Content-Type':'application/json'}),timeout=90) as response:return json.load(response)

title='Demo - Kokoro calm voice with a 3-second pause'
items=api('/api/state')['jobs']
existing=next((j for j in items if j['title']==title),None)
job_id=existing['id'] if existing else api('/api/jobs',{'jobs':[{
    'title':title,'engine':'kokoro','voice':'af_heart','speed':.85,'live_preview':True,
    'text':'Take a slow breath and let your heart become still. [3s silence] May this quiet moment bring you comfort, strength, and peace for the day ahead.',
    'blend':[{'voice':'af_heart','weight':80},{'voice':'af_nicole','weight':20}],
    'export_format':'mp3_44100_320','normalize':True,'seed':12345,
}]})['ids'][0]
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1536,'height':1050})
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(BASE)
    page.wait_for_function("document.querySelector('#connection').textContent.includes('voices')")
    page.locator('#autoplay').uncheck()
    button=page.locator(f'#job-{job_id} [data-action="live"]')
    if button.count():
        button.click()
        page.wait_for_function("document.querySelector('#preview-player').src.includes('/api/live/')",timeout=180000)
        print('Live audio reached the browser before completion.',flush=True)
    started=time.time()
    while time.time()-started<300:
        job=next(j for j in api('/api/state')['jobs'] if j['id']==job_id)
        if job['status']=='completed':break
        if job['status']=='retrying':raise RuntimeError(job['error'])
        page.wait_for_timeout(1000)
    else:raise TimeoutError('Final demo did not complete')
    page.wait_for_selector(f'#job-{job_id} audio',timeout=10000)
    assert set(job['files'])=={'mp3','wav','srt','vtt','json'}
    assert job['live']['files']
    with urlopen(BASE+'/api/live/'+job_id+'/'+job['live']['files'][0]) as response:
        assert response.read(4)==b'RIFF'
    with page.expect_download() as download:
        page.locator(f'#job-{job_id} a').filter(has_text='ZIP').click()
    download.value.save_as(ROOT/'test-results'/'final-demo.zip')
    audio=MP3(ROOT/'data'/'outputs'/(job_id+'.mp3'))
    assert audio.info.sample_rate==44100 and audio.info.bitrate==320000
    assert not errors,errors
    page.locator('#toast').evaluate('(e)=>e.hidden=true')
    page.screenshot(path=str(ROOT/'test-results'/'final-main.png'),full_page=True)
    report={'job_id':job_id,'audio_seconds':audio.info.length,'render_seconds':job['completed']-job['started'],
            'mp3_kbps':audio.info.bitrate/1000,'sample_rate':audio.info.sample_rate,'live_chunks':len(job['live']['files']),
            'saved_recordings':len(api('/api/state')['jobs']),'page_errors':errors}
    (ROOT/'test-results'/'final-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
    browser.close()
