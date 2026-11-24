"""Export the frozen historical focus-momentum observation for the web app."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lei_signal.market_context.focus_momentum import build_observation_bundle, export_observation_bundle  # noqa: E402


OUTPUT = ROOT / "web/public/research/focus-momentum/observation.v1.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the saved bundle without writing")
    args = parser.parse_args()
    if args.check:
        expected = build_observation_bundle(ROOT)
        actual = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if actual != expected:
            raise ValueError("saved focus-momentum bundle differs from frozen inputs")
    else:
        export_observation_bundle(ROOT, OUTPUT)
    print(f"focus-momentum bundle verified: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
