"""Publish the saved library into the running studio without interrupting its queue."""
import json
import os
from pathlib import Path
import shutil
import uuid
from auditions import audition_name, audition_text
from voice_catalog import kokoro_voices, kitten_voices, piper_voices, chatterbox_voices

ROOT=Path(__file__).resolve().parent
def publish():
    manifest={}
    media=ROOT/'static-v2/auditions'
    media.mkdir(exist_ok=True)
    catalogs=[
        ('edge',json.loads((ROOT/'data/voices.json').read_text(encoding='utf-8'))),
        ('kokoro',kokoro_voices()),('kitten',kitten_voices()),('piper',piper_voices()),
        ('chatterbox',chatterbox_voices()),
    ]
    for engine,voices in catalogs:
        for voice in voices:
            name=voice['ShortName']; filename=audition_name(engine,name)
            source=ROOT/'data/auditions'/filename
            if not source.exists():continue
            target=media/filename
            if not target.exists():
                try: os.link(source,target)
                except OSError: shutil.copy2(source,target)
            # The audition route sends a one-year immutable cache header. The
            # filename is content/version-derived, so browsers can safely reuse it.
            manifest[engine+':'+name]={'url':'/auditions/'+target.name,'language':audition_text(name,voices)[1]}
    temp=ROOT/'static-v2'/('auditions-'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(manifest,ensure_ascii=False),encoding='utf-8')
    os.replace(temp,ROOT/'static-v2/auditions.json')
    print(json.dumps({engine:sum(k.startswith(engine+':') for k in manifest)
                      for engine,_ in catalogs}))

if __name__=='__main__':publish()
