#!/usr/bin/env python3
"""Remove broken pydantic_core *.dist-info dirs (missing RECORD) under .venv — stops uv uninstall warnings."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    site = root / ".venv" / "Lib" / "site-packages"
    if not site.is_dir():
        print("No .venv; nothing to repair.", file=sys.stderr)
        return 1

    removed: list[str] = []
    for d in sorted(site.glob("pydantic_core-*.dist-info")):
        if not (d / "RECORD").is_file():
            shutil.rmtree(d, ignore_errors=True)
            removed.append(d.name)

    if removed:
        print("Removed stale dist-info (no RECORD):", ", ".join(removed))
    else:
        print("No stale pydantic_core dist-info found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
