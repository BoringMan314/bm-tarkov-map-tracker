#!/usr/bin/env python3
"""Re-sync all DEV map assets: variant A (satellite) + variant B (abstract SVG)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run(cmd: list[str]) -> None:
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    run([PY, "tools/download_tarkov_dev_maps.py", "--variant=A"])
    run([PY, "tools/download_tarkov_dev_maps.py", "--variant=B"])
    print("\nOK DEV A + B map sync complete", flush=True)


if __name__ == "__main__":
    main()
