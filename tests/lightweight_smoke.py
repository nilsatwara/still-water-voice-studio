"""Opt-in process smoke test for the Edge-only lightweight deployment profile."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

import psutil


ROOT = Path(__file__).resolve().parents[1]
PORT = 8877


def request(path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {'Content-Type':'application/json'} if body else {}
    with urllib.request.urlopen(urllib.request.Request(
            f'http://127.0.0.1:{PORT}{path}', data=body, headers=headers), timeout=30) as response:
        return response.status, json.loads(response.read()) if 'json' in response.headers.get_content_type() else None


if __name__ == '__main__':
    environment = os.environ.copy()
    environment.update({
        'HOST':'127.0.0.1', 'PORT':str(PORT), 'STILLWATER_PROFILE':'lightweight',
        'ENABLE_KOKORO':'false', 'ENABLE_PIPER':'false', 'ENABLE_KITTEN':'false',
        'ENABLE_CHATTERBOX':'false',
        'STILLWATER_DATA_DIR':str(ROOT/'test-results'/'lightweight-data'),
    })
    process = subprocess.Popen([sys.executable, 'server.py'], cwd=ROOT, env=environment,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        deadline = time.monotonic()+40
        while time.monotonic()<deadline:
            try:
                if request('/health')[0]==200: break
            except Exception: time.sleep(.25)
        else: raise RuntimeError('Lightweight server did not become healthy.')
        edge = request('/api/voices?engine=edge')[1]
        assert edge['capabilities']['edge']['ready'] and edge['voices']
        for engine in ('kokoro','piper','kitten','chatterbox'):
            result = request('/api/voices?engine='+engine)[1]
            assert not result['capabilities'][engine]['enabled']
            assert not result['voices']
        try:
            request('/api/jobs', {'jobs':[{'engine':'kokoro','voice':'af_heart','text':'Hello'}]})
            raise AssertionError('Disabled engine accepted a job.')
        except urllib.error.HTTPError as error:
            detail = json.loads(error.read())
            assert error.code==400 and 'disabled' in detail['error'].lower()
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page()
            page.goto(f'http://127.0.0.1:{PORT}/')
            page.wait_for_function("document.querySelector('#engine option[value=\"kokoro\"]').textContent.includes('Unavailable')")
            page.locator('#engine').select_option('kokoro')
            page.wait_for_function("document.querySelector('#generate').disabled && !document.querySelector('#banner').hidden")
            assert 'unavailable on this server' in page.locator('#banner').text_content().lower()
            page.goto(f'http://127.0.0.1:{PORT}/voice-cloning')
            page.wait_for_function("document.querySelector('#generate-clone').disabled")
            assert 'unavailable' in page.locator('#clone-banner').text_content().lower()
            browser.close()
        root = psutil.Process(process.pid)
        members = [root,*root.children(recursive=True)]
        rss = sum(member.memory_info().rss for member in members if member.is_running())
        print(json.dumps({'status':'PASS','edge_voices':len(edge['voices']),
                          'idle_rss_mib':round(rss/1024/1024,1)}))
    finally:
        try:
            parent=psutil.Process(process.pid)
            for child in parent.children(recursive=True): child.kill()
            parent.kill()
        except psutil.NoSuchProcess: pass
