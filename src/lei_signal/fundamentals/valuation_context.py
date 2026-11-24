"""Read qualified concentration months, preserving unknown months and source notes."""

import json
from pathlib import Path

from lei_signal.api.config import cache_root

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = ROOT / "web/public/research/turnover-concentration/observation.v1.json"


def read_concentration(cache: Path | None = None) -> dict:
    live = (cache or Path(cache_root())) / "turnover_concentration_live.json"
    data = json.loads((live if live.exists() else REFERENCE).read_text())
    if data.get(
        "definitionId"
    ) != "observation.cn_supplier_amount_monthly_top5pct.v2" or not data.get("points"):
        raise ValueError("Unrecognized concentration definition")
    return data
