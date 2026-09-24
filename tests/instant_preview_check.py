import json
import statistics
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
report=[]
requests=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url) if r.method=='POST' and '/api/preview' in r.url else None)
    page.goto('http://127.0.0.1:8766')
    page.wait_for_function("document.querySelector('#connection').textContent.includes('voices') && !document.querySelector('#choose-voice').disabled")
    page.evaluate("""() => {
      document.addEventListener('click',e=>{if(e.target.closest('[data-preview]')){window.previewStart=performance.now();window.previewElapsed=null;}},true);
      document.querySelector('#library-player').addEventListener('playing',()=>{window.previewElapsed=performance.now()-window.previewStart;});
    }""")
    for engine,voices in [
        ('edge',['en-US-AndrewNeural','en-US-JennyNeural','en-US-ChristopherNeural','en-US-AriaNeural']),
        ('kokoro',['af_alloy','af_aoede','af_bella','af_heart','am_michael']),
        ('kitten',['Bella','Jasper']),
        ('piper',['en_US-arctic-medium::0','en_US-arctic-medium::3','en_US-hfc_female-medium']),
    ]:
        page.locator('#engine').select_option(engine)
        page.wait_for_function("!document.querySelector('#choose-voice').disabled")
        page.locator('#choose-voice').click()
        for voice in voices:
            page.locator('[data-preview="'+voice+'"]').click()
            page.wait_for_function('window.previewElapsed!==null',timeout=5000)
            milliseconds=page.evaluate('window.previewElapsed')
            player=page.locator('#library-player')
            assert player.evaluate('p=>!p.paused && p.preservesPitch && p.playbackRate===.8')
            assert 'Pause' in page.locator('[data-preview="'+voice+'"]').inner_text()
            assert milliseconds<1500,(voice,milliseconds)
            report.append({'engine':engine,'voice':voice,'click_to_playing_ms':round(milliseconds,1)})
        page.locator('[data-close="voice-library"]').click()
    page.locator('#engine').select_option('kokoro')
    page.wait_for_function("!document.querySelector('#choose-voice').disabled")
    page.locator('#speed').fill('0.5')
    page.locator('#choose-voice').click()
    page.locator('[data-preview="af_alloy"]').click()
    page.wait_for_function('window.previewElapsed!==null')
    assert page.locator('#library-player').evaluate('p=>p.playbackRate===.5&&p.preservesPitch')
    assert not requests,requests
    assert not errors,errors
    browser.close()
result={'samples':report,'median_ms':round(statistics.median(x['click_to_playing_ms'] for x in report),1),'synthesis_requests':len(requests),'page_errors':errors}
(ROOT/'test-results/instant-preview-report.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
