# Browser dictation

The tutor composer accepts optional English/German dictation using
[Cactus Whistle](https://huggingface.co/Cactus-Compute/whistle). A student chooses
the speech language, clicks the microphone, and stops after a short answer.
Recording stops automatically after 30 seconds. The transcript joins the editable
message draft; only the ordinary Send action submits it. This adds no TTS.

## Ownership and privacy

- `useSpeechInput.ts` owns loading, permission errors and recording lifecycle.
- `speech/microphoneRecording.ts` captures mono PCM with an AudioWorklet and uses
  the browser's audio resampler to produce 16 kHz audio.
- `speech/whistleClient.ts` owns a worker that runs the transcription-only C API.
- `speech/whistleInference.ts` validates clips and releases native allocations.
- `SpeechInputControls.tsx` owns the microphone and EN/DE controls.

Audio is transient device memory. No audio reaches the API, provider or analytics.
Closing the composer, hiding the page or starting a pending tutor turn cancels
capture and discards the result. The browser cache contains public model files,
never recordings. Transcripts remain drafts until the student sends them; normal
tutor storage and provider processing then apply. The tutor backend remains the
authority for assessment, gates and model requests.

## Assets and deployment

`npm run dev --workspace apps/web` and `npm run build --workspace apps/web`
prepare the assets through `tooling/prepareWhistle.mjs`. The script downloads
revision-pinned files from the official Hugging Face repositories and verifies
SHA-256 digests from `speech/whistleAssets.json`. Missing downloads or mismatched
digests fail the command. Verified local files are reused without a network call.
Build machines need outbound HTTPS for the first download. The web Docker build
runs the same preparation step.

Generated assets live in ignored `apps/web/public/speech/whistle-*/` directories
and are copied into the web build. The upstream JavaScript receives only an ES
module export; model and WebAssembly bytes are unchanged. The upstream Apache
2.0 license is distributed beside the assets. The browser loads those files from
LecturePilot's own origin, with immutable caching on the pinned directory.
`/speech/` returns 404 for missing files instead of the application HTML.

The web CSP permits same-origin workers and WebAssembly compilation through
`wasm-unsafe-eval`. It still restricts connections to the application origin.
Microphone permission is limited to that origin with `microphone=(self)`.
The API's own restrictive microphone policy remains unchanged. Production needs
HTTPS; localhost is suitable for development. Browsers need AudioWorklet,
WebAssembly SIMD and module workers. Unsupported browsers report a visible error.

Whistle's model weighs about 17 MB; runtime, working memory and cached downloads
are additional. Its published first-token timing is a completed-clip desktop CPU
benchmark. This integration transcribes after recording and makes no claim about
live streaming, phone latency or recognition quality for mathematical notation.

## Verification

Run the composer speech, native boundary and capture tests before `verify:web`.
Use actual English/German audio against the pinned worker for recognition checks.
Also check stop, cancellation, denied permission, empty speech and the production
CSP. Synthetic speech verifies integration; it does not establish student speech
accuracy or phone battery use.
