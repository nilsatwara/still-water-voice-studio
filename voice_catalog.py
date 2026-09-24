"""Engine capabilities and editable, subjective listening tags."""
from pathlib import Path
import importlib.util
import json
import os

ROOT = Path(__file__).resolve().parent
MODEL_ROOT = Path(os.getenv('STILLWATER_MODEL_DIR', str(ROOT / 'models'))).expanduser().resolve()
MODEL_DIR = MODEL_ROOT / 'kokoro'
PIPER_DIR = MODEL_ROOT / 'piper'
CHATTERBOX_DIR = MODEL_ROOT / 'chatterbox-nano'
LANGUAGES = {
    'a': ('en-US', 'English (United States)'), 'b': ('en-GB', 'English (United Kingdom)'),
    'e': ('es-ES', 'Spanish'), 'f': ('fr-FR', 'French'), 'h': ('hi-IN', 'Hindi'),
    'i': ('it-IT', 'Italian'), 'p': ('pt-BR', 'Portuguese (Brazil)'),
    'j': ('ja-JP', 'Japanese'), 'z': ('zh-CN', 'Mandarin Chinese'),
}
USES = ['deep','advertisement','social','announcement','news','audiobook','podcast',
        'narration','prayer','funny','comedy','sad','calm','warm','spiritual']
AGES = ['young','middle','older','child','unclassified']
LOCAL_ENGINES = ('kokoro', 'piper', 'kitten', 'chatterbox')


def _boolean_env(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def engine_enabled(engine):
    """Full local mode is default; lightweight/cloud profiles opt local engines out."""
    if engine == 'edge':
        return True
    profile = os.getenv('STILLWATER_PROFILE', 'full').strip().lower()
    default = profile not in ('light', 'lightweight', 'cloud', 'edge-only')
    return _boolean_env('ENABLE_' + engine.upper(), default)

# These are discovery suggestions, NOT demographic facts or supported emotion modes.
CURATED = {
    'Christopher': ('middle', ['deep','announcement','news','narration','audiobook','prayer','spiritual']),
    'Andrew': ('middle', ['warm','calm','prayer','spiritual','podcast','narration','sad']),
    'Brian': ('middle', ['deep','warm','podcast','audiobook','narration']),
    'Guy': ('middle', ['deep','advertisement','announcement','news','narration']),
    'Eric': ('middle', ['calm','news','narration','audiobook']),
    'Roger': ('middle', ['funny','comedy','advertisement','social','podcast']),
    'Steffan': ('middle', ['calm','deep','narration','prayer']),
    'Jenny': ('young', ['warm','calm','prayer','spiritual','narration','sad']),
    'Ava': ('young', ['warm','prayer','spiritual','podcast','social']),
    'Emma': ('young', ['social','advertisement','funny','comedy','podcast']),
    'Aria': ('middle', ['announcement','news','audiobook','narration','deep']),
    'Michelle': ('middle', ['calm','warm','narration','prayer']),
    'Ana': ('child', ['funny','comedy','social']),
    'am_michael': ('middle', ['deep','warm','narration','audiobook','prayer','spiritual']),
    'am_fenrir': ('middle', ['deep','announcement','advertisement','narration']),
    'am_puck': ('young', ['funny','comedy','social','podcast']),
    'am_onyx': ('middle', ['deep','calm','prayer','narration']),
    'am_santa': ('older', ['funny','comedy','narration']),
    'bm_george': ('older', ['deep','narration','audiobook','prayer']),
    'af_heart': ('young', ['warm','calm','prayer','spiritual','narration','podcast','sad']),
    'af_bella': ('young', ['advertisement','social','podcast','funny','comedy']),
    'af_nicole': ('middle', ['calm','prayer','spiritual','sad','narration']),
    'af_sarah': ('middle', ['warm','narration','audiobook','news','announcement']),
    'af_sky': ('young', ['social','funny','comedy']),
    'bf_emma': ('middle', ['warm','narration','audiobook','prayer']),
}


def enrich(voice, engine):
    voice = dict(voice)
    key = voice['ShortName'] if engine == 'kokoro' else voice['ShortName'].split('-')[-1].replace('Multilingual','').replace('Neural','')
    age, uses = CURATED.get(key, ('unclassified', []))
    uses = set(uses)
    tags = voice.get('VoiceTag', {})
    source = ' '.join(tags.get('VoicePersonalities', []) + tags.get('ContentCategories', [])).lower()
    for words, suggested in [(['news'], ['news','announcement']), (['novel'], ['audiobook','narration']),
                             (['friendly','pleasant','comfort','caring','warm'], ['warm','calm','prayer']),
                             (['conversation'], ['podcast','social']), (['lively','cheerful'], ['advertisement','funny','comedy']),
                             (['reliable','authority'], ['deep','narration'])]:
        if any(w in source for w in words): uses.update(suggested)
    voice.update(Engine=engine, Uses=sorted(uses), Age=age, TagsSource='Suggested listening tags · editable')
    return voice


def kokoro_voices():
    result = []
    for path in sorted((MODEL_DIR / 'voices').glob('*.pt')):
        code = path.stem
        if code[0] not in LANGUAGES: continue
        locale, name = LANGUAGES[code[0]]
        result.append(enrich({'ShortName':code, 'Name':code.split('_',1)[1].title(),
                             'Locale':locale, 'LocaleName':name, 'Gender':'Female' if code[1]=='f' else 'Male',
                             'VoiceTag':{}}, 'kokoro'))
    return result


def kitten_voices():
    details={
        'Bella':('Female','young',['warm','social','advertisement']),
        'Jasper':('Male','middle',['deep','calm','narration','prayer','audiobook']),
        'Luna':('Female','young',['calm','warm','prayer','spiritual']),
        'Bruno':('Male','middle',['deep','advertisement','announcement','news']),
        'Rosie':('Female','middle',['warm','narration','podcast','audiobook']),
        'Hugo':('Male','middle',['podcast','narration','news']),
        'Kiki':('Female','young',['funny','comedy','social']),
        'Leo':('Male','young',['social','funny','podcast']),
    }
    return [dict(ShortName=name,Name=name,Locale='en-US',LocaleName='English (United States)',
                 Gender=gender,Engine='kitten',Age=age,Uses=uses,
                 TagsSource='Suggested listening tags · editable')
            for name,(gender,age,uses) in details.items()]


def piper_voices():
    genders={
        'lessac':'Female','ryan':'Male','hfc_female':'Female','hfc_male':'Male',
        'awb':'Male','rms':'Male','slt':'Female','ksp':'Male','clb':'Female','lnh':'Female',
        'aew':'Male','bdl':'Male','jmk':'Male','rxr':'Male','fem':'Female','ljm':'Female',
        'slp':'Female','aup':'Male','ahw':'Male','axb':'Male','eey':'Female','gka':'Male',
    }
    result=[]
    for config_path in sorted(PIPER_DIR.glob('en_US-*.onnx.json')):
        model_id=config_path.name[:-10]
        model_path=PIPER_DIR/(model_id+'.onnx')
        if not model_path.is_file(): continue
        config=json.loads(config_path.read_text(encoding='utf-8'))
        quality=config.get('audio',{}).get('quality','medium')
        speakers=config.get('speaker_id_map') or {}
        entries=speakers.items() if speakers else [(model_id.split('-')[1],None)]
        for speaker,speaker_id in entries:
            base=model_id.split('-')[1]
            display=(speaker.upper() if speakers else base.replace('_',' ').title())
            voice_id=model_id+(f'::{speaker_id}' if speaker_id is not None else '')
            gender=genders.get(speaker,genders.get(base,'Male'))
            uses=['narration','audiobook','podcast']
            if gender=='Female': uses+=['warm','calm','prayer']
            else: uses+=['deep','announcement','news']
            result.append(dict(ShortName=voice_id,Name=f'{display} · {quality.title()}',Locale='en-US',
                               LocaleName='English (United States)',Gender=gender,Engine='piper',
                               Age='middle',Uses=uses,TagsSource='Suggested listening tags · editable'))
    return result


def chatterbox_voices(data=ROOT/'data'):
    result=[dict(ShortName='builtin',Name='Nano Built-in',Locale='en-US',LocaleName='English (United States)',
                 Gender='Neutral',Engine='chatterbox',Age='unclassified',
                 Uses=['narration','audiobook','podcast','social'],
                 TagsSource='Official built-in voice · watermarked')]
    folder=Path(data)/'chatterbox-voices'
    for metadata in sorted(folder.glob('clone-*.json')):
        try:
            value=json.loads(metadata.read_text(encoding='utf-8')); voice_id=metadata.stem
            if (folder/(voice_id+'.wav')).is_file():
                result.append(dict(ShortName=voice_id,Name=str(value.get('name','Cloned voice'))[:60],Locale='en-US',
                    LocaleName='English (United States)',Gender='Neutral',Engine='chatterbox',Age='unclassified',
                    Uses=['narration','audiobook','podcast'],TagsSource='Your local reference voice · watermarked'))
        except (OSError,ValueError): pass
    return result


def capabilities():
    kokoro_enabled = engine_enabled('kokoro')
    kitten_enabled = engine_enabled('kitten')
    piper_enabled = engine_enabled('piper')
    chatterbox_enabled = engine_enabled('chatterbox')
    kokoro_ready = (kokoro_enabled and (MODEL_DIR/'kokoro-v1_0.pth').exists()
                    and importlib.util.find_spec('kokoro') is not None)
    configured_worker = os.getenv('CHATTERBOX_PYTHON')
    worker_candidates = [Path(configured_worker).expanduser() if configured_worker else None,
                         ROOT/'.venv-chatterbox'/'Scripts'/'python.exe',
                         ROOT/'.venv-chatterbox'/'bin'/'python']
    chatterbox_runtime = chatterbox_enabled and (
        any(path and path.is_file() for path in worker_candidates)
        or importlib.util.find_spec('chatterbox') is not None)
    kitten_ready = (kitten_enabled and importlib.util.find_spec('kittentts') is not None
                    and (MODEL_ROOT/'kitten').exists())
    piper_ready = (piper_enabled and importlib.util.find_spec('piper') is not None
                   and bool(piper_voices()))

    def status(enabled, ready, install_message):
        if not enabled:
            return {'enabled':False, 'ready':False,
                    'reason':'Disabled on this server by deployment configuration.'}
        if not ready:
            return {'enabled':True, 'ready':False, 'reason':install_message}
        return {'enabled':True, 'ready':True, 'reason':''}

    return {
        'edge': {'name':'Microsoft Edge', 'enabled':True, 'ready':True, 'reason':'',
                 'local':False, 'speed_min':.5, 'speed_max':1,
                 'pitch':True, 'volume':True, 'blend':False,
                 'source':'24 kHz · 48 kbps MP3 source. Higher export rates do not restore source detail.',
                 'timing':'Word timing supplied by Edge.'},
        'kokoro': {'name':'Kokoro 82M',
                   **status(kokoro_enabled, kokoro_ready, 'Kokoro dependencies or model files are not installed.'),
                   'local':True, 'speed_min':.5, 'speed_max':2,
                   'pitch':False, 'volume':False, 'blend':True,
                   'source':'24 kHz native PCM · loaded in a per-job worker and released after generation.',
                   'timing':'English uses model word timings. Other languages use measured phrase boundaries.'},
        'kitten': {'name':'Kitten Micro 40M',
                   **status(kitten_enabled, kitten_ready, 'Kitten dependencies or model files are not installed.'),
                   'local':True, 'speed_min':.5, 'speed_max':2,
                   'pitch':False, 'volume':False, 'blend':False,
                   'source':'24 kHz native PCM · 40M ONNX model · released after the configured idle timeout.',
                   'timing':'Captions use measured audio length with proportional English word timing.'},
        'piper': {'name':'Piper American',
                  **status(piper_enabled, piper_ready, 'Piper dependencies or voice packs are not installed.'),
                  'local':True, 'speed_min':.5, 'speed_max':2,
                  'pitch':False, 'volume':False, 'blend':False,
                  'source':'22.05 kHz native PCM · recent ONNX voice packs are released after the configured idle timeout.',
                  'timing':'Captions use measured audio length with proportional English word timing.'},
        'chatterbox': {'name':'Chatterbox Nano 110M',
                  **status(chatterbox_enabled,
                           chatterbox_runtime and (CHATTERBOX_DIR/'t3_nano_v1.safetensors').is_file(),
                           'Chatterbox dependencies or model files are not installed.'),
                  'local':True, 'speed_min':.5, 'speed_max':2,
                  'pitch':False, 'volume':False, 'blend':False,
                  'source':'24 kHz native PCM · isolated CPU worker exits after the configured idle timeout · model-watermarked output.',
                  'timing':'Captions use measured audio length with proportional English word timing.'},
    }


def require_engine(engine):
    capability = capabilities().get(engine)
    if capability is None:
        raise ValueError('Choose a supported speech engine.')
    if not capability['enabled']:
        raise ValueError(f"{capability['name']} is unavailable on this server because it is disabled.")
    if not capability['ready']:
        raise ValueError(f"{capability['name']} is unavailable on this server. {capability['reason']}")
    return capability
