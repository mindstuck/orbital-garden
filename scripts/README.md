# Scripts

- `verify.py` — runs formatting, lint, type checks, the fast unit suite, the
  tracked-file scan and Compose validation. Missing executables are skipped.
- `check_tracked_files.py` — fails if the Git index contains secrets, local
  state (data dirs, certs, models, voices, audio) or files larger than 5 MB.
  It never prints file contents.

The image build (`docker compose build py-server`) is the slow installability
check and is intentionally not part of `verify.py`.

## Notes

- The unit suite does not require a GPU. Install dev dependencies with
  `pip install -r py-server/requirements-dev.txt`.
- FastAPI/httpx are needed by the WebSocket tests and are listed in the dev
  requirements so the fast suite runs without the GPU/STT/TTS stack.
