#!/usr/bin/env python3
"""Publish-readiness checks for the repository.

Runs, when available: ruff format/check, mypy, the fast pytest suite, the
tracked-file/secret scan and `docker compose config`. Steps whose executable
is missing are skipped with a warning.

    python scripts/verify.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY_SERVER = ROOT / "py-server"

CHECKS: list[tuple[list[str], Path]] = [
    (["ruff", "format", "--check", "."], PY_SERVER),
    (["ruff", "check", "."], PY_SERVER),
    (["mypy", "."], PY_SERVER),
    ([sys.executable, "-m", "pytest", "-q"], PY_SERVER),
    ([sys.executable, "scripts/check_tracked_files.py"], ROOT),
    (["docker", "compose", "config", "--quiet"], ROOT),
]


def run(command: list[str], cwd: Path) -> bool:
    if shutil.which(command[0]) is None:
        print(f"SKIP (executable not found): {' '.join(command)}")
        return True
    print(f"RUN  {' '.join(command)}")
    return subprocess.run(command, cwd=cwd).returncode == 0


def main() -> int:
    failures = [command for command, cwd in CHECKS if not run(command, cwd)]
    if failures:
        print("\nVerification FAILED:")
        for command in failures:
            print(f"  - {' '.join(command)}")
        return 1
    print("\nAll available verification checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
