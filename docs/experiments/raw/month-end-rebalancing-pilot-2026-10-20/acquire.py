"""Bounded public-source acquisition; no market-effect calculations."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research.output_storage import recheck_saved_plan

HERE = Path(__file__).resolve().parent


def main():
    plan = json.loads((HERE / "storage-plan.json").read_text())
    recheck_saved_plan(ROOT, plan, plan["task_id"], plan["estimated_bytes"],
                       plan["internal_metadata_bytes"])
    out = Path(plan["output"])
    out.mkdir(parents=True, exist_ok=False)
    ledger = []
    sources = [
        ("paper.pdf", "https://afajof.org/management/viewp.php?n=144452"),
        *[(f"{s}.json", f"https://query1.finance.yahoo.com/v8/finance/chart/{s}"
           "?period1=1025481600&period2=1792368000&interval=1d&events=div%2Csplits")
          for s in ("SPY", "IEF")],
    ]
    for name, url in sources:
        rec = {"name": name, "url": url, "retrieved_at": datetime.now(timezone.utc).isoformat()}
        try:
            with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=45) as response:
                content = response.read()
                rec["content_type"] = response.headers.get("Content-Type")
            if name.endswith(".json"):
                data = json.loads(content)["chart"]
                if data.get("error"):
                    raise ValueError(str(data["error"]))
                item = data["result"][0]
                rec.update(rows=len(item["timestamp"]), first_epoch=item["timestamp"][0],
                           last_epoch=item["timestamp"][-1],
                           currency=item["meta"]["currency"],
                           timezone=item["meta"]["exchangeTimezoneName"],
                           dividend_events=len(item.get("events", {}).get("dividends", {})),
                           split_events=len(item.get("events", {}).get("splits", {})))
            else:
                assert content.startswith(b"%PDF")
            (out / name).write_bytes(content)
            rec.update(status="saved", bytes=len(content),
                       sha256=hashlib.sha256(content).hexdigest(), path=str(out / name))
        except Exception as exc:
            rec.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        ledger.append(rec)
        (HERE / "acquisition.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2))
        print(json.dumps({k: v for k, v in rec.items() if k not in {"url", "path"}}, ensure_ascii=False),
              flush=True)


if __name__ == "__main__":
    main()
