# Lightweight Render deployment

The root `aiohttp` application supports two modes without changing the UI:

- `STILLWATER_PROFILE=full` (the default) preserves every installed local engine.
- `STILLWATER_PROFILE=lightweight` defaults to Edge-only and is used by `render.yaml`.

The Render Blueprint uses the Free 512 MB plan, installs
`requirements-lightweight.txt`, and downloads no AI models. Edge TTS remains
available because it is an online service. Unavailable engines remain visible
in the UI with an explicit server-availability message.

## Selective engines

Each local engine can be enabled independently at build and runtime:

```text
ENABLE_KOKORO=false
ENABLE_PIPER=false
ENABLE_KITTEN=false
ENABLE_CHATTERBOX=false
```

Change only the desired flag to `true`, then trigger **Clear build cache &
deploy**. `render-build.sh` installs and downloads only enabled engines. A flag
cannot make an engine available without rebuilding because its dependency and
model assets are intentionally absent from the lightweight artifact.

`MODEL_IDLE_TIMEOUT_SECONDS=120` releases retained models after two inactive
minutes. Kokoro already runs once per job and exits immediately. Chatterbox
runs in an isolated worker that is terminated after inactivity. Kitten and
Piper discard their in-process model objects after inactivity in full local
mode. The lightweight profile also sets `ISOLATE_LOCAL_ENGINES=true`, so Kitten
and Piper run in one-shot workers and the operating system reclaims their
Python, ONNX, and model memory after every job.

## Actual memory measurements

`tests/memory_profile.py` measured the complete process tree on the repository's
installed models using a short sentence, CPU inference, final audio processing,
and subtitle/export generation:

| Engine | Idle before load | Peak generation RSS | After explicit unload |
|---|---:|---:|---:|
| Edge | 65.5 MiB | 93.3 MiB | 69.0 MiB |
| Piper (largest installed voice) | 65.7 MiB | 408.1 MiB | 66.8 MiB |
| Kitten | 65.6 MiB | 482.5 MiB | 67.1 MiB |
| Kokoro | 65.7 MiB | 1,433.8 MiB | 67.0 MiB |
| Chatterbox Nano | 65.7 MiB | 4,236.5 MiB | 66.1 MiB |

The running Edge-only server smoke test measured 74.8 MiB idle after loading
the Edge voice catalog. These figures are measurements from the current model
files and Intel i3-1005G1 Windows machine, not vendor estimates. Production
containers still need safety margin for longer text chunks, concurrent HTTP
responses, native allocators, and platform processes.

Practical tiers:

- 512 MB: Edge. Piper's largest installed voice leaves too little safety margin for a reliable web service.
- 1 GB: Edge, Piper, and Kitten.
- 2 GB: Edge, Piper, Kitten, and Kokoro.
- 4 GB: all above; Chatterbox exceeds the limit.
- Chatterbox: use at least 6 GB, preferably 8 GB.

The Free Blueprint intentionally enables Edge only. A small Piper pack can fit
the raw limit, but the largest installed pack measured 408.1 MiB before HTTP
traffic headroom, and the Free plan's very small CPU allocation makes local
inference an unreliable default.

## Storage behavior

`STILLWATER_DATA_DIR=/tmp/stillwater-data` is ephemeral in the Free profile.
Generated recordings, uploads, clone references, and the SQLite queue disappear
when the service restarts, redeploys, or spins down. Full local mode continues
to use the project `data/` directory. Move to a paid persistent disk or external
object/database storage if cloud persistence becomes necessary.

## Commands and security

- Build: `bash render-build.sh`
- Start: `python server.py`
- Health: `/health`
- Required secret: `STILLWATER_PASSWORD`
- Default username: `stillwater`

The health endpoint remains public and does not import or initialize a TTS
model. The rest of the application is protected by HTTP Basic authentication
when `STILLWATER_PASSWORD` is set.
