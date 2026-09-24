import VoiceExplorer from '../components/voice-explorer';

export default function Home() {
  return (
    <main>
      <nav className="nav shell" aria-label="Primary navigation">
        <a className="brand" href="#top" aria-label="Stillwater home">
          <span className="mark">≋</span><span>stillwater<small>VOICE STUDIO</small></span>
        </a>
        <div className="navlinks"><a href="#voices">Voices</a><a href="#engines">Engines</a><a href="#about">About</a></div>
        <a className="navCta" href="#voices">Explore voices</a>
      </nav>

      <section className="hero shell" id="top">
        <div className="eyebrow"><span /> Natural speech, thoughtfully made</div>
        <h1>Give every word a voice<br /><em>worth hearing.</em></h1>
        <p className="lead">Browse hundreds of multilingual Edge voices and private local Kokoro voices from one calm, focused studio.</p>
        <div className="heroActions"><a className="primary" href="#voices">Find your voice <span>→</span></a><span className="privacy">● Local Kokoro support</span></div>
        <div className="wave" aria-hidden="true">⌁⌁⌁⌁⌁⌁⌁⌁⌁⌁⌁⌁⌁⌁⌁⌁</div>
      </section>

      <section className="voices shell" id="voices">
        <div className="sectionIntro"><span className="kicker">VOICE LIBRARY</span><h2>Meet the voices.</h2><p>Search the live API catalog by name, locale, engine, or gender.</p></div>
        <VoiceExplorer />
      </section>

      <section className="engines shell" id="engines">
        <article><span className="number">01</span><div><p className="kicker">CONNECTED</p><h3>Microsoft Edge TTS</h3><p>Broad multilingual coverage and provider voice IDs preserved exactly across the API boundary.</p></div></article>
        <article><span className="number">02</span><div><p className="kicker">PRIVATE</p><h3>Kokoro 82M</h3><p>Local neural speech with model files and inference kept entirely on the Python backend.</p></div></article>
      </section>

      <section className="about shell" id="about"><p className="kicker">BUILT FOR FOCUS</p><h2>Your words stay at the center.</h2><p>The frontend is a fast static Next.js site. Voice catalogs come from a separate FastAPI service, leaving synthesis, models, storage, PostgreSQL, and cache concerns on the backend.</p></section>
      <footer className="shell"><a className="brand compact" href="#top"><span className="mark">≋</span><span>stillwater</span></a><p>Voice Studio · Edge TTS + Kokoro</p></footer>
    </main>
  );
}
