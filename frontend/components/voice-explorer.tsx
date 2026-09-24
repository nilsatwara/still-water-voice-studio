'use client';

import { useEffect, useMemo, useState } from 'react';

type Engine = 'edge' | 'kokoro';
type Voice = { ShortName: string; FriendlyName?: string | null; Gender: string; Locale: string; LocaleName: string; Age: string; Uses: string[] };
type Response = { engine: Engine; count: number; voices: Voice[] };

const API = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8767/api/v1').replace(/\/$/, '');

export default function VoiceExplorer() {
  const [engine, setEngine] = useState<Engine>('edge');
  const [voices, setVoices] = useState<Voice[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    fetch(`${API}/voices?engine=${engine}`, { signal: controller.signal, headers: { Accept: 'application/json' } })
      .then(async (res) => { if (!res.ok) throw new Error(`API returned ${res.status}`); return res.json() as Promise<Response>; })
      .then((data) => setVoices(data.voices))
      .catch((reason: Error) => { if (reason.name !== 'AbortError') setError('Voice service is unavailable. Start FastAPI on port 8767 and try again.'); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [engine]);

  const shown = useMemo(() => {
    const term = query.trim().toLowerCase();
    return voices.filter((v) => !term || [v.FriendlyName, v.ShortName, v.Locale, v.LocaleName, v.Gender, ...v.Uses].join(' ').toLowerCase().includes(term)).slice(0, 12);
  }, [voices, query]);

  return <div className="explorer">
    <div className="toolbar">
      <div className="tabs" role="group" aria-label="Speech engine">
        <button className={engine === 'edge' ? 'active' : ''} onClick={() => setEngine('edge')}>Edge TTS</button>
        <button className={engine === 'kokoro' ? 'active' : ''} onClick={() => setEngine('kokoro')}>Kokoro</button>
      </div>
      <label className="search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search voices or languages" aria-label="Search voices" /></label>
      <span className="count">{voices.length} voices</span>
    </div>
    {loading && <div className="state">Loading the {engine === 'edge' ? 'Edge' : 'Kokoro'} voice catalog…</div>}
    {error && <div className="state error" role="alert">{error}</div>}
    {!loading && !error && <div className="voiceGrid">{shown.map((voice) => <article className="voiceCard" key={voice.ShortName}>
      <div className="avatar">{(voice.FriendlyName || voice.ShortName).charAt(0)}</div>
      <div className="voiceCopy"><h3>{voice.FriendlyName || voice.ShortName.replace(/Neural$/, '')}</h3><p>{voice.Gender} · {voice.LocaleName || voice.Locale}</p><div className="tags">{voice.Uses.slice(0, 3).map((use) => <span key={use}>{use}</span>)}</div></div>
      <span className="engineBadge">{engine}</span>
    </article>)}</div>}
    {!loading && !error && shown.length === 0 && <div className="state">No voices match “{query}”.</div>}
  </div>;
}
