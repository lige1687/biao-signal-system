#!/usr/bin/env python3
"""Repository entry point for the local delegation runner."""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

def _main() -> int:
    from tools.agent_delegate.cli import main

    return main()


if __name__ == "__main__":
    raise SystemExit(_main())
