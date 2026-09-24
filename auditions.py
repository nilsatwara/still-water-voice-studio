"""Versioned, pre-rendered voice auditions independent of recording settings."""
import hashlib
from preview_samples import sample_for


def audition_text(voice, catalog):
    text, language = sample_for(voice, catalog)
    if language == 'en': text = 'Hello. May your day be peaceful and bright.'
    return text, language


def audition_name(engine, voice):
    return hashlib.sha256(f'audition-v1-natural:{engine}:{voice}'.encode()).hexdigest()[:24]+'.mp3'


def audition_url(data, engine, voice):
    name=audition_name(engine,voice)
    return '/auditions/'+name if (data/'auditions'/name).is_file() else None
