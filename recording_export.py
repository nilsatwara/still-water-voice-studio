"""Combine explicitly selected recordings in original queue order."""
import json
import re
import numpy as np
import soundfile as sf
import imageio_ffmpeg
from audio_engine import command, FORMATS
from speech_text import write_subtitles

MAX_MERGE_SECONDS=5*60*60


def validate_merge(jobs):
    if len(jobs)<2:
        raise ValueError('Select at least two completed recordings to create a mega recording.')
    total=sum(float(job.get('duration') or 0) for job in jobs)
    if total>MAX_MERGE_SECONDS:
        raise ValueError('Mega recordings are currently limited to 5 hours. Select fewer parts.')
    identities={(j.get('engine','edge'),j['voice'],json.dumps(j.get('blend',[]),sort_keys=True)) for j in jobs}
    if len(identities)>1:
        raise ValueError('For consistent sound, select recordings with the same engine, voice, and blend.')
    return total


def read_srt(path):
    value=path.read_text(encoding='utf-8-sig')
    cues=[]
    def seconds(stamp):
        h,m,s,ms=map(int,re.split('[:,]',stamp))
        return h*3600+m*60+s+ms/1000
    for block in re.split(r'\r?\n\s*\r?\n',value.strip()):
        lines=block.splitlines()
        if len(lines)>=3 and ' --> ' in lines[1]:
            start,end=lines[1].split(' --> ')
            cues.append({'start':seconds(start),'end':seconds(end),'text':'\n'.join(lines[2:])})
    return cues


async def merge_recordings(jobs,outputs,folder,progress=None):
    validate_merge(jobs)
    def report(value,stage):
        if progress: progress(value,stage)
    report(.02,'Preparing selected recordings')
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    cues=[]
    offset=0
    chapters=[]
    with sf.SoundFile(folder/'combined-native.wav',mode='w',samplerate=24000,channels=1,subtype='PCM_24') as output:
        for index,job in enumerate(jobs,1):
            path=outputs/(job['id']+'.wav')
            if not path.exists(): path=outputs/(job['id']+'.mp3')
            raw=await command(ffmpeg,'-v','error','-i',path,'-ac','1','-ar','24000','-f','f32le','pipe:1')
            samples=np.frombuffer(raw,dtype='<f4')
            duration=len(samples)/24000
            output.write(samples)
            for cue in read_srt(outputs/(job['id']+'.srt')):
                cues.append({**cue,'start':cue['start']+offset,'end':min(duration,cue['end'])+offset})
            chapters.append({'title':job['title'],'start':offset,'end':offset+duration})
            offset+=duration
            if offset>MAX_MERGE_SECONDS+.01:
                raise ValueError('Mega recordings are currently limited to 5 hours. Select fewer parts.')
            report(.05+.55*index/len(jobs),f'Combining audio · part {index} of {len(jobs)}')
    _,rate,bitrate=FORMATS[jobs[0].get('export_format','mp3_44100_192')]
    report(.64,'Encoding the mega MP3')
    await command(ffmpeg,'-v','error','-y','-i',folder/'combined-native.wav','-ar',max(44100,rate),'-c:a','libmp3lame','-b:a',f'{bitrate}k',folder/'merged.mp3')
    report(.80,'Finalizing lossless audio')
    await command(ffmpeg,'-v','error','-y','-i',folder/'combined-native.wav','-ar',rate,'-c:a','pcm_s24le',folder/'merged.wav')
    report(.89,'Synchronizing SRT and VTT captions')
    write_subtitles(folder/'merged',cues,offset)
    (folder/'merged.json').write_text(json.dumps({'chapters':chapters,'voice':jobs[0]['voice'],'duration':offset},ensure_ascii=False,indent=2),encoding='utf-8')
    report(.92,'Packaging the download')
