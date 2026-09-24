"""Exercise real local inference in all nine supported language variants."""
import json
import os
from pathlib import Path
import time
os.environ['HF_HUB_OFFLINE']='1'
import torch
import unidic
import unidic_lite
import soundfile as sf
from kokoro import KModel,KPipeline

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'models'/'kokoro'
OUT=ROOT/'test-results'/'languages'
OUT.mkdir(exist_ok=True)
unidic.DICDIR=unidic_lite.DICDIR
torch.set_num_threads(4)
model=KModel(repo_id='hexgrad/Kokoro-82M',config=str(MODEL/'config.json'),model=str(MODEL/'kokoro-v1_0.pth')).eval()
examples=[
('af_heart','May peace and kindness be with you today.'),
('bf_emma','May peace and kindness be with you today.'),
('ef_dora','Que la paz y la bondad te acompañen hoy.'),
('ff_siwis','Que la paix et la bonté vous accompagnent aujourd’hui.'),
('hf_alpha','आज आपके जीवन में शांति और खुशियाँ हों।'),
('if_sara','Che la pace e la gentilezza siano con te oggi.'),
('pf_dora','Que a paz e a bondade estejam com você hoje.'),
('jf_alpha','今日も心穏やかに過ごせますように。'),
('zf_xiaobei','愿你今天平安喜乐，心中充满希望。'),
]
report=[]
for voice,text in examples:
    started=time.time()
    pipeline=KPipeline(lang_code=voice[0],repo_id='hexgrad/Kokoro-82M',model=model)
    pack=torch.load(MODEL/'voices'/f'{voice}.pt',weights_only=True)
    results=list(pipeline(text,voice=pack,speed=.9))
    assert results and all(r.audio is not None and len(r.audio)>0 for r in results)
    audio=torch.cat([r.audio for r in results]).numpy()
    sf.write(OUT/f'{voice}.wav',audio,24000,subtype='PCM_24')
    item={'voice':voice,'audio_seconds':len(audio)/24000,'render_seconds':round(time.time()-started,2)}
    report.append(item)
    print(json.dumps(item),flush=True)
(OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
