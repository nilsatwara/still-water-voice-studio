"""Pause instructions and standards-compatible, non-overlapping subtitles."""
import re
import textwrap

PAUSE = re.compile(r'\[\s*([0-9]+(?:\.[0-9]+)?)\s*s\s+silence\s*\]', re.I)
BATCH_SEPARATOR = re.compile(r'^[ \t]*(?:\*\*|__)?[ \t]*-{3,}[ \t]*(?:\*\*|__)?[ \t]*\r?$', re.M)


def split_batch(text):
    return [part.strip() for part in BATCH_SEPARATOR.split(text) if part.strip()]


def split_script(text, paragraph_pause=0):
    # Reject malformed silence commands instead of accidentally speaking them.
    for marker in re.findall(r'\[[^\]\n]*silence[^\]\n]*\]', text, re.I):
        match = PAUSE.fullmatch(marker)
        if not match or float(match[1]) not in (1,2,3,4,5):
            raise ValueError('Silence instructions must be [1s silence] through [5s silence].')
    if paragraph_pause:
        # Internal fractional paragraph pauses use a separate split, not the user command syntax.
        paragraphs = re.split(r'\n\s*\n', text)
    else:
        paragraphs = [text]
    result=[]
    for index, paragraph in enumerate(paragraphs):
        if index and paragraph_pause: result.append(('silence',float(paragraph_pause)))
        last=0
        for match in PAUSE.finditer(paragraph):
            if paragraph[last:match.start()].strip(): result.append(('text',paragraph[last:match.start()].strip()))
            result.append(('silence',float(match[1])))
            last=match.end()
        if paragraph[last:].strip(): result.append(('text',paragraph[last:].strip()))
    if not any(kind=='text' and any(c.isalnum() for c in value) for kind,value in result):
        raise ValueError('Add spoken words as well as silence markers.')
    return result


def timestamp(seconds, separator=','):
    ms=max(0,round(seconds*1000))
    hour, ms=divmod(ms,3600000)
    minute,ms=divmod(ms,60000)
    second,ms=divmod(ms,1000)
    return f'{hour:02d}:{minute:02d}:{second:02d}{separator}{ms:03d}'


def caption_groups(words, width=42, max_duration=6):
    """Group real timing spans; never estimate word positions from character counts."""
    result=[]
    current=[]
    def emit():
        if not current: return
        text=''.join(w.get('prefix','')+w['text'] for w in current).strip()
        # Never split an Indic combining character away from its word.
        lines=textwrap.wrap(text,width=width,break_long_words=False,break_on_hyphens=False)
        result.append({'start':current[0]['start'],'end':current[-1]['end'],'text':'\n'.join(lines)})
        current.clear()
    for word in words:
        word=dict(word)
        if not word['text'].strip() or word['end']<=word['start']: continue
        if current:
            text=''.join(w.get('prefix','')+w['text'] for w in current)+word.get('prefix',' ')+word['text']
            if (len(textwrap.wrap(text,width=width))>2 or word['end']-current[0]['start']>max_duration
                    or word['start']-current[-1]['end']>.7): emit()
        if not current: word['prefix']=''
        current.append(word)
        if re.search(r'[.!?。！？]["”\']?$',word['text']): emit()
    emit()
    return result


def write_subtitles(stem, cues, duration):
    clean=[]
    previous_end=0
    for cue in cues:
        start=max(previous_end,round(cue['start'],3))
        end=min(round(duration,3),round(cue['end'],3))
        text=cue['text'].strip().replace('-->', '→')
        if end<=start or not text: continue
        if '\x00' in text: text=text.replace('\x00','')
        clean.append({'start':start,'end':end,'text':text})
        previous_end=end
    if not clean: raise RuntimeError('No subtitle timings were produced.')
    srt='\r\n\r\n'.join(f'{i}\r\n{timestamp(c["start"])} --> {timestamp(c["end"])}\r\n{c["text"].replace(chr(10),chr(13)+chr(10))}' for i,c in enumerate(clean,1))+'\r\n\r\n'
    vtt='WEBVTT\n\n'+'\n\n'.join(f'{timestamp(c["start"],".")} --> {timestamp(c["end"],".")}\n{c["text"]}' for c in clean)+'\n'
    stem.with_suffix('.srt').write_bytes(srt.encode('utf-8'))
    stem.with_suffix('.vtt').write_bytes(vtt.encode('utf-8'))
    return clean
