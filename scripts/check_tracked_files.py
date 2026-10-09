#!/usr/bin/env python3
"""Fail if the Git index contains secrets, local state or large binaries.

Run from the repository root:

    python scripts/check_tracked_files.py

Only file paths and generic categories are printed; file contents are never
shown. Exits non-zero when a problem is found.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

MAX_BYTES = 5 * 1024 * 1024

# Paths that must never be tracked. .env.example and the voices README are
# intentional exceptions.
FORBIDDEN_PATHS = [
    re.compile(r"(^|/)\.env$"),
    re.compile(r"\.pem$", re.IGNORECASE),
    re.compile(r"\.key$", re.IGNORECASE),
    re.compile(r"\.(p12|pfx)$", re.IGNORECASE),
    re.compile(r"\.(onnx|gguf|pt|bin)$", re.IGNORECASE),
    re.compile(r"\.(wav|webm|ogg|opus|mp3|flac|m4a)$", re.IGNORECASE),
    re.compile(r"^db/"),
    re.compile(r"^router/"),
    re.compile(r"^ollama/"),
    re.compile(r"^models/"),
    re.compile(r"(^|/)cuda_libs/"),
    re.compile(r"^py-server/certs/"),
]
ALLOWED = {".env.example", "py-server/voices/README.md"}

SECRET_CONTENT = [
    re.compile(rb"BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY"),
    re.compile(rb"hf_[A-Za-z0-9]{20,}"),
    re.compile(rb"sk-[A-Za-z0-9]{20,}"),
]


def tracked_files() -> list[str]:
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True, cwd=root)
    return [name for name in result.stdout.decode("utf-8").split("\x00") if name]


def check() -> list[str]:
    problems: list[str] = []
    for name in tracked_files():
        if name in ALLOWED:
            continue
        if any(pattern.search(name) for pattern in FORBIDDEN_PATHS):
            problems.append(f"tracked sensitive/local path: {name}")
            continue
        path = Path(name)
        try:
            if path.stat().st_size > MAX_BYTES:
                problems.append(f"tracked file larger than 5MB: {name}")
            data = path.read_bytes()
        except OSError:
            continue
        if any(pattern.search(data) for pattern in SECRET_CONTENT):
            problems.append(f"possible secret content in: {name}")
    return problems


def main() -> int:
    problems = check()
    if problems:
        print("Tracked-file check FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("Tracked-file check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
