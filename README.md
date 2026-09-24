# Stillwater Voice Studio — Version 3

Open **http://127.0.0.1:8766** on this computer. After a restart, double-click the **Edge TTS Studio** desktop shortcut or `start.cmd`.

For the Edge-only free Render profile, selective local-engine flags, measured
RAM use, and storage limitations, see [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md).

## Engines and consistency

**Microsoft Edge** uses the online Edge service. **Kokoro 82M**, **Kitten Micro 40M**, **Piper**, and **Chatterbox Nano 110M** run locally. Chatterbox is English-only and adds a built-in expressive voice plus local voice cloning. Each engine remembers its own voice and controls.

Every submitted script saves its engine, voice, speed, pitch/volume where supported, Kokoro blend/seed, pauses, export format, and caption layout. Changing controls cannot affect queued scripts. The app never silently switches voice or engine after a failure. Kokoro uses one fixed voice embedding or weighted blend throughout each script, a reproducible seed, and fixed local model files. Audio finishing adjusts the whole recording instead of normalizing segments separately.

These measures prevent app-induced voice changes. Natural prosody can still vary with sentence context; neither engine guarantees identical emotion or timbre in every sentence. Kokoro quality also varies between voices and languages.

## Editor and voice library

- Larger text, redesigned sliders, light/dark themes, and responsive layouts.
- Searchable languages, name/personality search, male/female filters, suggested use/style filters, and perceived-age filters. **Edit tags** saves your listening labels for any voice. Labels are discovery suggestions, not verified ages or native emotion controls. Unclassified voices remain available under All or Not classified.
- **Speed:** a continuous slider with 0.01 increments and quick buttons. Edge: 0.5–1.0×. Kokoro: 0.5–2.0×.
- **Silence:** click a 1s–5s button or type `[3s silence]`. Commands become actual silent samples and are not spoken. Subtitle timestamps include the pauses. An optional slider adds pauses at blank lines.
- **Batch:** scripts split automatically at any line of three or more hyphens (`---`, `--------------------`, or Markdown `**-----**`). No checkbox is needed. Each part gets its own queued recording with the same saved voice settings. Up to 50 parts per submission, each up to 40,000 characters.
- **Instant library previews (both engines):** all 322 Edge and 54 Kokoro voice samples are pre-rendered and saved locally. Clicking a voice plays its saved original, unblended sample directly, without loading a model or contacting the voice service. Speed changes browser playback with pitch preservation; this is a quick audition, not an exact simulation of synthesis at that speed. **Preview script** generates your actual text with your blend and settings and still takes generation time. The button changes to **Ⅱ Pause** while playing. Standard and multilingual variants with the same name may share the same underlying voice identity.
- **Languages:** Hindi and Gujarati auditions use native-script samples. Gujarati is available in Edge; Kokoro does not include Gujarati. Hindi is available in both engines. Use a voice matching the script language; Romanized Hindi/Gujarati pronunciation can differ from native-script input.
- **Import:** TXT, PDF, and EPUB, with optional chapter splitting and retained titles. Review extracted text before submitting. Documents are parsed locally. Scanned PDFs require OCR first; OCR is not included.

## Engine-specific features

Edge exposes voice, speed, pitch, and voice volume. Its community client needs internet and sends the selected script to Microsoft's service.

Kokoro exposes voice, speed, weighted blending of up to eight same-language voices, reproducible seed, CPU/automatic device selection, and optional listening while generation is in progress. Enable **Local model controls → Listen while Kokoro generates**, submit, then select **Listen live** on the queue card. Live playback uses rendered chunks before final audio finishing and may wait between chunks on a slower CPU. Final exported audio is continuous.

This PC has CPU-only Torch and Intel graphics, so Kokoro can be slower than Edge. Automatic device selection uses CUDA when supported Torch and hardware are available. The integration uses the official `kokoro` library for token timing, fixed embeddings, and PCM output, and implements document/chapter, blending, streaming, and export workflows described by the Kokoro CLI project.

Kokoro does not supply native stability, emotion, or pitch sliders. English pronunciation overrides use `[word](/phonemes/)` syntax.

Chatterbox Nano runs in `.venv-chatterbox`, isolated from the other engines. Selecting it starts a persistent CPU worker in the background; later jobs reuse the loaded model. It supports temperature, top-p, top-k, repetition penalty, reproducible seed, native action tags such as `[laugh]`, and 6–30 second local reference clips for voice cloning. References are decoded, capped, converted to mono 24 kHz WAV, and kept under `data/chatterbox-voices/`. The model adds its built-in Perth watermark to generated audio. Its first model load and actual synthesis remain CPU-bound; the built-in library audition is pre-rendered and plays from cache immediately.

## Audio exports and source quality

Select MP3 at 128/192/256/320 kbps and 44.1/48 kHz delivery options. WAV uses 24-bit PCM at 24/44.1/48 kHz. New recordings include MP3, WAV, SRT, VTT, and a JSON timing/settings report. With native 24 kHz WAV selected, the MP3 companion uses 44.1 kHz / 192 kbps to support that bitrate correctly.

**Edge source:** 24 kHz / 48 kbps MP3. Converting to 320 kbps or WAV cannot restore missing detail. **Kokoro source:** native 24 kHz PCM; choose 24 kHz WAV to preserve the generated signal for editing. Higher export rates are delivery formats, not a higher-resolution model. The app cannot promise the sound of ElevenLabs or a recorded studio performer.

Use **ZIP** on one recording or **Download all** for completed recordings. Select recordings to download a subset. **Merge selected + ZIP** adds combined MP3/WAV/SRT/VTT and a chapter timeline. Combining requires the same engine, voice, and blend, and follows queue order. It inserts no extra silence. Version 1 recordings retain their original MP3/SRT/VTT downloads.

## Subtitle timing

SRT uses UTF-8, sequential cue numbers, `HH:MM:SS,mmm` timestamps, CRLF line endings, blank lines between cues, and non-overlapping intervals. VTT uses the WEBVTT header and dot-separated milliseconds. Silence and merged chapters shift timestamps by actual audio sample durations. Caption width and preferred cue duration are configurable.

Edge uses service word timings; English Kokoro uses model token-duration timings. Other Kokoro languages use measured phrase start/end times, not invented word alignment. A single long token or non-English phrase can exceed the preferred cue duration.

## Queue recovery

The saved SQLite queue processes one script at a time. Failures retry after 5, 15, 30, then 60 seconds; 60-second retries continue until success or cancellation. Later scripts never bypass a failure automatically. Partial generation is discarded. **Edit & fix** pauses the queue and retries the edited script in its original position. Saving resumes a previously running queue; a manually paused queue stays paused. **Cancel script** explicitly skips a job. **Pause queue** allows the current generation to finish.

Closing the browser leaves the background server running. Restarting the server resumes unfinished scripts from the beginning. Service outages, disconnected internet, removed voices, and local resource failures may need your intervention.

Cancellation stops Kokoro's Windows launcher and its child processes before removing temporary audio files. Friendly errors appear in the app; detailed tracebacks are saved in `server-error.log`.

## Sound troubleshooting

Use **Voice library → Test sound** to play a short browser tone. If the player moves but both the voice and test tone are silent, check the browser tab/site sound permission, Windows Volume mixer browser volume, and the selected output device. This PC's Realtek speaker output was unmuted at 100%, and the Windows test tones were confirmed audible on 20 September. Physical speaker audibility cannot be established by waveform checks alone.

## Files and setup

- `data/studio.sqlite3`: jobs, queue settings, and custom voice tags.
- `data/outputs/`: audio, subtitles, timing reports, and optional `live/` previews.
- `models/kokoro/`: model, all voice embeddings, and `revision.json`.
- `data/auditions/` and `static-v2/auditions/`: saved library audio (hard-linked on this PC). `static-v2/auditions.json` maps each engine/voice to its exact sample. Regenerate missing samples with `.venv\Scripts\python.exe build_auditions.py` (Kokoro) and `.venv\Scripts\python.exe build_auditions.py --edge` (Edge); then run `.venv\Scripts\python.exe publish_auditions.py`.
- `backups/v1/`: original code and database backup before migration.
- Browser local storage: draft, appearance, and independent engine settings.
- `test-results/`: validation reports, language samples, and screenshots.

Dependencies and models are installed. For a fresh setup with Python 3.12, run `setup.ps1`. It installs into `.venv`, downloads the English tokenizer and Kokoro assets, and uses bundled Windows phonemizer components. Setup needs internet; normal Kokoro generation does not.

For Chatterbox on a fresh machine, run `.venv\Scripts\python.exe setup_chatterbox.py`. This creates the isolated environment and downloads only the Nano checkpoint files.

Regression tests: `.venv\Scripts\python.exe -m unittest discover -s tests -v`.

Separate test server: `.venv\Scripts\python.exe server.py --port 8767 --data-dir test-results/v2-data`.

Upstream: [Edge TTS](https://github.com/rany2/edge-tts), [official Kokoro library](https://github.com/hexgrad/kokoro), [Kokoro model](https://huggingface.co/hexgrad/Kokoro-82M), and [Kokoro CLI workflows](https://github.com/nazdridoy/kokoro-tts).
