import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results'

async def main():
    errors=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='chrome',headless=True)
        page=await browser.new_page(viewport={'width':1536,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        await page.goto('http://127.0.0.1:8767')
        await page.wait_for_function("document.querySelector('#connection').textContent.includes('voices')")
        await page.locator('#script').fill('First script.\n\n**-----------------------------------------------------------------------------------------**\n\nSecond script.\n--------------------\nThird script.')
        assert not await page.locator('#batch').is_checked()
        assert '3 scripts' in await page.locator('#generate').inner_text()
        payloads=[]
        async def capture(route):
            payloads.append(route.request.post_data_json)
            await route.fulfill(json={'ids':['a','b','c']})
        await page.route('**/api/jobs',capture)
        await page.locator('#generate').click()
        await page.wait_for_function("document.querySelector('#script').value==='' ")
        assert [j['text'] for j in payloads[0]['jobs']]==['First script.','Second script.','Third script.']
        gap=await page.evaluate("document.querySelector('#recordings').getBoundingClientRect().top-document.querySelector('.editor-card').getBoundingClientRect().bottom")
        assert 0<=gap<40,gap
        await page.screenshot(path=str(OUT/'fixes-desktop.png'),full_page=True)
        await page.locator('#choose-voice').click()
        andrew=page.locator('[data-preview="en-US-AndrewNeural"]')
        await andrew.click()
        await page.wait_for_function("document.querySelector('[data-preview=\"en-US-AndrewNeural\"]').textContent.includes('Pause')",timeout=60000)
        await page.wait_for_function("document.querySelector('#library-player').currentTime>.2")
        assert await page.locator('#library-player').evaluate('p=>!p.muted&&p.volume===1&&p.readyState>=2')
        await andrew.click()
        assert await page.locator('#library-player').evaluate('p=>p.paused')
        assert 'Preview' in await andrew.inner_text()
        await andrew.click()
        await page.wait_for_function("!document.querySelector('#library-player').paused")
        await page.locator('[data-preview="en-US-ChristopherNeural"]').click()
        await page.wait_for_function("document.querySelector('[data-preview=\"en-US-ChristopherNeural\"]').textContent.includes('Pause')",timeout=60000)
        assert 'Preview' in await andrew.inner_text()
        await page.locator('#library-player').evaluate('p=>{p.currentTime=p.duration-.1}')
        await page.wait_for_function("document.querySelector('#library-player').ended")
        assert 'Preview' in await page.locator('[data-preview="en-US-ChristopherNeural"]').inner_text()
        # Simulate a stale response arriving after another voice was clicked.
        report=json.loads((OUT/'fixes-audio-report.json').read_text())
        urls={r['voice']:r['url'] for r in report}
        async def delayed(route):
            job=route.request.post_data_json
            await asyncio.sleep(.8 if job['voice']=='en-US-AndrewNeural' else .1)
            try: await route.fulfill(json={'voice':job['voice'],'engine':'edge','url':urls[job['voice']],'sample_language':'en'})
            except Exception: pass # expected for the deliberately aborted request
        await page.route('**/api/preview',delayed)
        await andrew.click()
        await page.locator('[data-preview="en-US-ChristopherNeural"]').click()
        await page.wait_for_function("document.querySelector('[data-preview=\"en-US-ChristopherNeural\"]').textContent.includes('Pause')")
        await page.wait_for_timeout(1000)
        assert urls['en-US-ChristopherNeural'] in await page.locator('#library-player').get_attribute('src')
        await page.screenshot(path=str(OUT/'fixes-voice-library.png'),full_page=True)
        # Errors remain visible inside the modal, not hidden behind it.
        await page.unroute('**/api/preview',delayed)
        async def failed(route):await route.fulfill(status=500,json={'error':'Check your internet connection and try again.'})
        await page.route('**/api/preview',failed)
        await andrew.click()
        await page.wait_for_function("document.querySelector('#library-preview-label').textContent.includes('Check your internet')")
        await page.locator('[data-close="voice-library"]').click()
        await page.set_viewport_size({'width':390,'height':844})
        assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        await page.locator('#choose-voice').click()
        box=await page.locator('.library-preview').bounding_box()
        assert box['y']+box['height']<=844,box
        await page.screenshot(path=str(OUT/'fixes-mobile-library.png'),full_page=True)
        assert not errors,errors
        print(json.dumps({'passed':True,'page_errors':errors,'scripts':3,'editor_recordings_gap':gap,'play_pause_ended_race_errors_mobile':'passed'}))
        await browser.close()

asyncio.run(main())
