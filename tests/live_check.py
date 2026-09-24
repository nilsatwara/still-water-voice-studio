"""Opt-in live service check. Leaves two clearly labelled demo recordings."""
import json
from pathlib import Path
import time
import sys
from urllib.request import Request, urlopen

BASE = 'http://127.0.0.1:8766'
ROOT = Path(__file__).resolve().parents[1]


def api(path, body=None):
    req = Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                  headers={'Content-Type':'application/json'})
    with urlopen(req, timeout=90) as response:
        return json.load(response)


PRAYER = '''Father, as this day begins, help me become still. I bring you the thoughts I cannot settle and the questions I cannot answer. Let me take a slow breath and remember that I do not have to carry the whole week in this moment. There is grace for today, and there will be grace for tomorrow.

Thank you for the small gifts I sometimes hurry past. Thank you for the morning light, for a place to rest, for the kindness of another person, and for every chance to begin again. Open my eyes to goodness that is already here. Teach me to receive ordinary moments with a grateful heart instead of always looking ahead to something more.

When I feel tired, give me permission to rest. When I feel discouraged, help me take one faithful step. I do not need to prove my worth by doing everything at once. Show me what belongs to this day, and help me release what does not. Let my work be thoughtful, my words be gentle, and my attention be present.

I pray for the people I love. Some are carrying burdens they have not spoken about. Some are waiting for news. Some are finding their way through change. Meet them with comfort and give them people who will listen. Help me notice when a kind word, a patient answer, or a simple act of care could make their day a little lighter.

I also bring you the places in my own heart that feel unsettled. There are disappointments I still remember and conversations I wish had gone differently. Give me the courage to make things right where I can. Give me wisdom where I need boundaries, and patience where healing takes time. Help me let go of the need to control every outcome.

Guide my decisions with clarity. When I am uncertain, help me pause before I react. When the world feels loud, bring me back to what is true and good. May I choose honesty over convenience, compassion over judgment, and hope over the habit of expecting the worst. Let the way I live make a little more room for peace.

For anyone feeling alone today, I ask for companionship and comfort. For anyone who is grieving, I ask for a gentle place to be heard. For those who are beginning again after a difficult season, I ask for courage that grows a little at a time. Help us remember that needing support is part of being human, and that we can offer that support to one another.

As I move through the hours ahead, remind me to breathe and return to this moment. I can listen carefully. I can speak with kindness. I can do the next small thing with love. Even when the day is imperfect, let me notice the ways that goodness is still at work, quietly and patiently, in ordinary life.

Help me find a rhythm that leaves room for the people around me. Let there be space for a conversation without checking the clock, for a walk without needing to arrive somewhere quickly, and for a meal shared with gratitude. Remind me that a meaningful life is made of these small moments of attention. I do not have to turn every hour into an achievement. Sometimes the most faithful thing I can do is be fully present with someone who needs to know they matter.

Where I have been impatient with myself, teach me gentleness. Where I have been impatient with others, teach me understanding. Every person I meet has a story I cannot fully see. Let me be slow to assume and willing to listen. When I make a mistake, help me acknowledge it honestly and begin again without shame. When someone else makes a mistake, help me offer the same patience I hope to receive. May my home, my work, and my conversations reflect a steady kindness that does not depend on everything going according to plan.

Tonight, when the work is finished, help me set it down. Let me be thankful for what was possible and gentle with myself about what remains. May my home be a place of welcome, my heart a place of gratitude, and my rest a time of renewal. Thank you for walking with me through this day. Amen.'''


if __name__ == '__main__':
    voices = api('/api/voices')['voices']
    print('Voice count:', len(voices), 'American English:', sum(v['Locale']=='en-US' for v in voices), flush=True)
    started = time.time()
    ids = [j['id'] for j in api('/api/state')['jobs'] if j['title'] in ('Demo · Five-minute calm prayer', 'Demo · Gentle female voice')] if '--existing' in sys.argv else api('/api/jobs', {'jobs':[
        {'title':'Demo · Five-minute calm prayer', 'text':PRAYER, 'voice':'en-US-ChristopherNeural', 'speed':.8, 'pitch':-12, 'volume':0},
        {'title':'Demo · Gentle female voice', 'text':'Take a slow breath. Let your heart be still. May you find strength for today, comfort in the quiet moments, and hope for the path ahead.', 'voice':'en-US-JennyNeural', 'speed':.9, 'pitch':-3, 'volume':0}
    ]})['ids']
    previous = None
    while time.time() - started < 360:
        jobs = [j for j in api('/api/state')['jobs'] if j['id'] in ids]
        state = [(j['status'], round(j['progress'], 2), j['attempts']) for j in jobs]
        if state != previous:
            print(state, flush=True)
            previous = state
        if any(j['attempts'] >= 3 for j in jobs):
            raise RuntimeError(str([(j['title'],j['error']) for j in jobs]))
        if all(j['status']=='completed' for j in jobs):
            break
        time.sleep(2)
    else:
        raise RuntimeError('Live generation timed out')
    assert jobs[1]['started'] >= jobs[0]['completed'], 'FIFO violated'
    report = {'voices':len(voices), 'american_english':sum(v['Locale']=='en-US' for v in voices),
              'elapsed_seconds':round(time.time()-started, 2), 'words':len(PRAYER.split()), 'jobs':[]}
    for job in jobs:
        for ext in ('mp3','srt','vtt'):
            with urlopen(BASE+f'/files/{job["id"]}.{ext}?download=1') as response:
                content=response.read()
                assert len(content)>50
                assert 'attachment' in response.headers['Content-Disposition']
                if ext=='srt': assert b' --> ' in content
                if ext=='vtt': assert content.replace(b'\r\n', b'\n').startswith(b'WEBVTT\n') and b'.' in content
        from mutagen.mp3 import MP3
        audio = MP3(ROOT / 'data' / 'outputs' / (job['id']+'.mp3'))
        assert audio.info.length >= job['duration'] - 2
        report['jobs'].append({'id':job['id'], 'title':job['title'], 'duration_seconds':audio.info.length,
                               'subtitle_end_seconds':job['duration'], 'attempts':job['attempts'],
                               'generation_seconds':round(job['completed']-job['started'],2)})
    assert report['jobs'][0]['duration_seconds'] >= 270, 'Long-form check was shorter than expected'
    (ROOT / 'test-results').mkdir(exist_ok=True)
    (ROOT / 'test-results' / 'live-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2), flush=True)
