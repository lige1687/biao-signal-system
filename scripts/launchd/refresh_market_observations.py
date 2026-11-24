#!/usr/bin/env python3
"""Daily CN/US breadth and ERP refresh; no trading or notifications."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from lei_signal.market_context.observation_refresh import SCOPES, run

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", action="append", choices=SCOPES)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(scopes=tuple(args.scope or SCOPES), force=args.force), ensure_ascii=False))
