import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results'
errors=[]
payloads=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1536,'height':1100},device_scale_factor=1)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8767')
    page.wait_for_function("document.querySelector('#connection').textContent.includes('322 voices')")
    assert page.locator('#script').evaluate('e=>parseFloat(getComputedStyle(e).fontSize)')>=18
    page.locator('#script').fill('Let your heart be still. May peace be with you today.')
    page.locator('#script').evaluate('(e)=>e.setSelectionRange(23,23)')
    page.locator('[data-pause="3"]').click()
    assert '[3s silence]' in page.locator('#script').input_value()
    page.locator('#speed').fill('0.87')
    assert '0.87' in page.locator('#speed-value').inner_text()
    page.locator('#choose-voice').click()
    page.locator('#language-search').fill('Hindi')
    page.locator('[data-locale="hi-IN"]').click()
    assert page.locator('.voice-card').count()>=2
    page.locator('#language-search').fill('United States')
    page.locator('[data-locale="en-US"]').click()
    page.locator('#use-filter').select_option('prayer')
    page.locator('[data-gender="Female"]').click()
    assert page.locator('.voice-card').count()>0
    page.locator('[data-gender="Male"]').click()
    assert page.locator('.voice-card').count()>0
    page.locator('#reset-filters').click()
    page.locator('#language-search').fill('United States')
    page.locator('[data-locale="en-US"]').click()
    page.screenshot(path=str(OUT/'v2-voice-library.png'),full_page=True)
    page.locator('[data-voice="en-US-AndrewNeural"]').click()
    page.locator('#engine').select_option('kokoro')
    page.wait_for_function("document.querySelector('#connection').textContent.includes('54 voices')")
    assert page.locator('#edge-settings').is_hidden()
    assert page.locator('#kokoro-settings').is_visible()
    assert page.locator('#speed').get_attribute('max')=='2'
    page.locator('#speed').fill('0.91')
    page.locator('.blend-panel summary').click()
    page.locator('#add-blend').click()
    assert page.locator('.blend-row').count()==2
    page.locator('[data-blend-index="1"]').select_option('af_bella')
    page.locator('[data-weight-index="0"]').fill('65')
    page.locator('[data-weight-index="1"]').fill('35')
    page.locator('#export-format').select_option('mp3_44100_320')
    page.locator('#engine').select_option('edge')
    page.wait_for_function("document.querySelector('#connection').textContent.includes('322 voices')")
    assert page.locator('#speed').input_value()=='0.87'
    assert page.locator('#edge-settings').is_visible()
    page.locator('#engine').select_option('kokoro')
    page.wait_for_function("document.querySelector('#connection').textContent.includes('54 voices')")
    assert page.locator('#speed').input_value()=='0.91'
    assert page.locator('[data-blend-index="1"]').input_value()=='af_bella'
    # Capture browser submission while the separate live test exercises real synthesis.
    def capture(route):
        payloads.append(route.request.post_data_json)
        route.fulfill(status=200,content_type='application/json',body='{"ids":[]}')
    page.route('**/api/jobs',capture)
    page.locator('#title').fill('Browser payload check')
    page.locator('#generate').click()
    page.wait_for_function("document.querySelector('#script').value === ''")
    job=payloads[0]['jobs'][0]
    assert job['engine']=='kokoro' and job['voice']=='af_heart'
    assert job['speed']==.91 and job['export_format']=='mp3_44100_320'
    assert job['blend']==[{'voice':'af_heart','weight':65},{'voice':'af_bella','weight':35}]
    assert '[3s silence]' in job['text']
    page.unroute('**/api/jobs',capture)
    page.locator('#import-files').set_input_files({'name':'chapters.txt','mimeType':'text/plain','buffer':b'Chapter 1\nA peaceful morning.\n\nChapter 2\nA quiet evening.'})
    page.wait_for_function("document.querySelector('#script').value.includes('Chapter 2')")
    assert page.locator('#batch').is_checked()
    assert '2 separate scripts' in page.locator('#word-count').inner_text()
    page.locator('#batch').uncheck()
    page.locator('#title').fill('A moment of peace')
    page.locator('#script').fill('Father, help me slow down and find peace in this moment.\n\n[3s silence]\n\nLet my words be gentle, my heart be patient, and my steps be guided by love.\n\nGive me strength for what is ahead, and grace to rest when I need it. Amen.')
    page.locator('#toast').evaluate('(e)=>e.hidden=true')
    page.screenshot(path=str(OUT/'v2-desktop.png'),full_page=True)
    page.reload()
    page.wait_for_function("document.querySelector('#connection').textContent.includes('54 voices')")
    assert '[3s silence]' in page.locator('#script').input_value()
    assert page.locator('#speed').input_value()=='0.91'
    page.locator('#theme').click()
    page.screenshot(path=str(OUT/'v2-dark.png'),full_page=True)
    page.locator('#theme').click()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(OUT/'v2-mobile.png'),full_page=True)
    page.locator('#choose-voice').click()
    assert page.evaluate("document.querySelector('#voice-library').scrollWidth<=document.querySelector('#voice-library').clientWidth")
    assert not errors,errors
    print(json.dumps({'page_errors':errors,'submitted_settings':job,'screenshots':['v2-desktop.png','v2-voice-library.png','v2-dark.png','v2-mobile.png']},indent=2))
    browser.close()
