# Piper voice assets

`py-server` loads a Piper voice from this directory at runtime. The model
binaries are **not** committed (they are large and machine-independent
downloads). Provision them before starting the stack.

Required files for the default voice:

```
py-server/voices/hal.onnx
py-server/voices/hal.onnx.json
```

`hal.onnx.json` is the voice config emitted alongside a Piper `.onnx` model.
Both files must share the same basename.

## How to obtain a voice

1. Download an ONNX voice from the official Piper voices repository
   (`rhasspy/piper-voices` on Hugging Face) or export/existing voice.
2. Place the `.onnx` and matching `.onnx.json` files here.
3. To use a different voice, set `TTS_VOICE_PATH` (see the root `README.md`)
   or update the default in the runtime configuration.

If the files are missing, the server logs a clear startup error instead of
failing mid-request. CUDA libraries for GPU inference are mounted from
`py-server/cuda_libs/` at runtime and are likewise not committed.
