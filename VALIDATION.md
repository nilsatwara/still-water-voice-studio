# Validation — 19 September 2026

## Instant library previews — 22 September 2026

- Pre-rendered all 322 Edge and all 54 Kokoro voices. All 376 MP3s decoded successfully and contained non-silent finite audio. Total audio size: 17.85 MB. See `test-results/audition-library-report.json`.
- Chrome tested nine distinct voices across both engines using direct saved-file playback, with zero synthesis API requests and zero JavaScript errors. Latest click-to-playing range: 35–603 ms; median: 61.6 ms. Measurements are from this PC, not a guarantee for every browser/device.
- Changing speed to 0.5× reused the saved sample, with browser pitch preservation enabled. Library speed changes playback; custom script previews still synthesize at the chosen model speed.
- Existing running studio received the static sample manifest and frontend update without interrupting its generation queue. Samples persist across app/PC restarts.

## Version 3 fixes — 22 September 2026

- Nineteen regression tests passed, including real Windows launcher/descendant cancellation with an open audio file and cleanup after a non-cancellation exception. The original exception is no longer masked by WinError 32.
- Fourteen real preview generations passed voice-ID/settings checks, non-silent PCM checks, distinct waveform hashes, exact caption text preservation, SRT syntax, and ordered timing intervals. Coverage: four US English Edge voices, both Gujarati Edge voices, both Hindi Edge voices, four US English Kokoro voices, and female/male Hindi Kokoro voices. See `test-results/fixes-audio-report.json`.
- All 54 downloaded Kokoro voice tensors have distinct hashes. This verifies different embeddings; it does not establish perceptual differences for every sentence or voice variant.
- Chrome browser checks passed actual media playback time progression, unmuted volume, play/pause/end icons, stale-request switching, visible in-dialog errors, automatic three-part splitting without a checkbox, and mobile player visibility. No JavaScript page errors. Screenshots: `test-results/fixes-*.png`.
- Live two-part batch test passed FIFO order, exact 1-second/3-second pauses, caption timing after pauses, and a ZIP containing all ten expected artifacts. See `test-results/fixes-queue-report.json`.
- The user confirmed both Windows speaker test tones were audible. Browser checks verify playback behavior, not physical audibility through the user's existing Chrome tab.

## Version 2 — 20 September 2026

- Fifteen regression tests passed: per-job engine/blend settings, silence parsing, SRT structure, PDF/EPUB chapters, queue recovery, cancellation, and restart persistence.
- Real Edge and Kokoro jobs passed 1–5 second silence checks. Central waveform samples in each pause were zero within encoding tolerance. Pause commands do not appear in captions.
- The new Edge pipeline generated a 314.54-second prayer in 32.67 seconds, with 69 captions. Every cue was positive, ordered, non-overlapping, inside the audio duration, and at most two lines wide.
- Local Kokoro passed weighted female blending and male narration. An 82.39-second male recording took 102.52 seconds on this CPU. Speed varies and can be slower than Edge.
- Mutagen verified MP3 rates/bitrates. Native-rate WAV receives a 44.1 kHz / 192 kbps MP3 companion to avoid invalid high-bitrate MPEG-2 output.
- ZIPs contained all five artifacts per new recording. Combined exports included audio, correctly shifted captions, and chapter metadata.
- Real local inference passed all nine language variants. All 54 voice embeddings are downloaded. See `test-results/languages/report.json`.
- Edge browser checks passed language search, gender/style filters, separate engine settings, weighted blend submission, chapter import, draft persistence, dark mode, and mobile layout. No page errors were reported.

These checks verify audio and subtitle structure. They do not establish identical perceptual quality for every voice or create higher-resolution source detail by upsampling.

## Version 1 checks

- Python 3.12.10; installed Edge TTS 7.2.8.
- Live service returned 322 voices, including 17 American English voices: 9 male and 8 female.
- A 719-word prayer generated with Christopher, 0.8× speed, and -12 Hz pitch produced a **5:11.352 MP3 in 23.46 seconds** on this PC. The final subtitle ended at 5:11.250. This is one measured run; service and network speed vary.
- A Jenny recording at 0.9× / -3 Hz started after that job completed and produced 10.8 seconds of audio. Both jobs succeeded on their first attempt.
- MP3 files parsed successfully with Mutagen; SRT and VTT downloads contain timestamped cues and return download filenames.
- Nine queue/API regression tests passed: FIFO recovery after failure, pause/restart persistence, atomic batch validation, setting bounds, partial-file cleanup, truncated-output rejection, active cancellation, editing/retrying in place, and cross-origin rejection.
- Automated headless Microsoft Edge checks passed: voice filters, six speeds, prayer preset, saved draft, batch splitting, live voice preview, audio duration, browser download, dark appearance, and a 390-pixel mobile layout without horizontal overflow. No JavaScript page errors.
- Browser screenshots and detailed live reports are under `test-results/`.

Two labelled demo recordings remain in the application so you can listen immediately. Live scripts are transmitted to Microsoft's online service for generation. Retry logic handles transient failures; it cannot guarantee availability of an external service or repair a disconnected internet connection.
