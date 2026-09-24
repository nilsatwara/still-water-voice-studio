"""Opt-in headless Edge check; requires playwright in the development venv."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results'
OUT.mkdir(exist_ok=True)
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width':1536,'height':1080}, device_scale_factor=1)
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8766')
    page.wait_for_function("document.querySelectorAll('.voice-card').length === 17")
    assert page.locator('#locale').input_value() == 'en-US'
    page.get_by_role('button', name='Female', exact=True).click()
    female_count = page.locator('.voice-card').count()
    assert 0 < female_count < 17
    page.get_by_role('button', name='Male', exact=True).click()
    male_count = page.locator('.voice-card').count()
    assert female_count + male_count == 17
    page.get_by_role('button', name='All voices', exact=True).click()
    for speed in ('0.5','0.6','0.7','0.8','0.9','1'):
        page.locator(f'[data-speed="{speed}"]').click()
        assert page.locator(f'[data-speed="{speed}"]').get_attribute('aria-pressed') == 'true'
    page.get_by_role('button', name='Deep & calm', exact=True).click()
    assert 'Christopher' in page.locator('#selected-voice').inner_text()
    assert page.locator('#pitch').input_value() == '-12'
    page.locator('#script').fill('Father, help me slow down and find peace in this moment.\n\nThank you for the gift of this day. Let my words be gentle, my heart be patient, and my steps be guided by love.\n\nGive me strength for what is ahead, and grace to rest when I need it. Amen.')
    page.locator('#title').fill('A moment of peace')
    page.reload()
    page.wait_for_function("document.querySelectorAll('.voice-card').length === 17")
    assert 'Father, help me slow down' in page.locator('#script').input_value()
    page.locator('#batch').check()
    page.locator('#script').fill('First script.\n---\nSecond script.')
    assert '2 scripts' in page.locator('#word-count').inner_text()
    page.locator('#batch').uncheck()
    page.locator('#script').fill('Father, help me slow down and find peace in this moment.\n\nThank you for the gift of this day. Let my words be gentle, my heart be patient, and my steps be guided by love.\n\nGive me strength for what is ahead, and grace to rest when I need it. Amen.')
    page.locator('[data-preview="en-US-ChristopherNeural"]').click()
    page.wait_for_function("!document.querySelector('#preview-player').hidden", timeout=90000)
    page.wait_for_function("!document.querySelector('[data-preview]').disabled")
    page.locator('#preview-player').evaluate('(audio) => audio.pause()')
    page.wait_for_function("document.querySelectorAll('.job.completed').length >= 2")
    page.wait_for_function("Array.from(document.querySelectorAll('.job audio')).some(a=>a.duration>270)")
    with page.expect_download() as download:
        page.locator('.downloads a').filter(has_text='MP3 audio').first.click()
    download.value.save_as(OUT / 'browser-download.mp3')
    assert (OUT / 'browser-download.mp3').stat().st_size > 1000
    page.locator('#toast').evaluate('(e) => e.hidden = true')
    assert 'voice preview' in page.locator('#preview-label').inner_text()
    page.screenshot(path=str(OUT / 'desktop.png'), full_page=True)
    page.locator('#theme').click()
    assert page.locator('body').evaluate("e=>e.classList.contains('dark')")
    page.screenshot(path=str(OUT / 'dark.png'), full_page=True)
    page.locator('#theme').click()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(OUT / 'mobile.png'), full_page=True)
    assert not errors, errors
    report={'browser':'Microsoft Edge (headless)', 'female_us_voices':female_count, 'male_us_voices':male_count,
            'checks':['voice filters','six speed controls','prayer preset','draft persistence','batch splitting',
                      'live voice preview','audio metadata','browser MP3 download','dark theme','mobile overflow'],
            'page_errors':errors}
    (OUT / 'browser-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    browser.close()
