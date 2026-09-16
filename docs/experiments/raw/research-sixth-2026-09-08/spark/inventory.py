import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


def _to_identity_value(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, (str, int, float, bool)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, (dict, list, tuple)):
        return json.dumps(v, sort_keys=True, ensure_ascii=False)
    return repr(v)


def _is_missing_identity_value(v: Any) -> bool:
    return v is None


def summarize_json_tree(root: str) -> dict:
    root = Path(root)
    files = []
    if not root.exists():
        return {
            "scanned_path": str(root),
            "files_scanned": 0,
            "files_loaded": 0,
            "json_errors": [{"file": str(root), "error": "path does not exist"}],
            "candidate_trade_dicts": 0,
            "missing_optional_identity": {"entry_variant": 0, "exit_variant": 0},
            "key_counts": {},
            "duplicate_identity_occurrences": [],
            "total_duplicate_identity_overcount": 0,
        }

    if root.is_file():
        files = [root]
    else:
        for p in root.rglob("*.json"):
            if p.is_file():
                files.append(p)

    required = ("symbol", "signal_date")
    optional = ("entry_variant", "exit_variant")

    summary = {
        "scanned_path": str(root),
        "files_scanned": len(files),
        "files_loaded": 0,
        "json_errors": [],
        "candidate_trade_dicts": 0,
        "missing_optional_identity": {k: 0 for k in optional},
        "key_counts": {},
        "duplicate_identity_occurrences": [],
        "total_duplicate_identity_overcount": 0,
    }

    dup: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    key_seen = Counter()

    def visit(obj: Any, json_path: str, current_file: Path):
        if isinstance(obj, dict):
            for k in obj.keys():
                key_seen[k] += 1
            has_req = all(k in obj for k in required)
            if has_req:
                summary["candidate_trade_dicts"] += 1
                miss = [k for k in optional if _is_missing_identity_value(obj.get(k))]
                if miss:
                    for k in miss:
                        summary["missing_optional_identity"][k] += 1
                else:
                    identity_key = (
                        _to_identity_value(obj["symbol"]),
                        _to_identity_value(obj["signal_date"]),
                        _to_identity_value(obj["entry_variant"]),
                        _to_identity_value(obj["exit_variant"]),
                    )
                    dup[identity_key].append({
                        "file": str(current_file),
                        "json_path": json_path,
                    })
            for k, v in obj.items():
                next_path = f"{json_path}.{k}" if json_path != "$" else f"$.{k}"
                visit(v, next_path, current_file)
        elif isinstance(obj, list):
            for idx, x in enumerate(obj):
                visit(x, f"{json_path}[{idx}]", current_file)

    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            summary["files_loaded"] += 1
            visit(data, "$", fp)
        except Exception as e:
            summary["json_errors"].append({"file": str(fp), "error": repr(e)})

    for (symbol, signal_date, entry_variant, exit_variant), occ in sorted(dup.items()):
        count = len(occ)
        if count > 1:
            summary["duplicate_identity_occurrences"].append({
                "symbol": symbol,
                "signal_date": signal_date,
                "entry_variant": entry_variant,
                "exit_variant": exit_variant,
                "count": count,
                "occurrences": occ,
            })
            summary["total_duplicate_identity_overcount"] += count - 1

    summary["key_counts"] = dict(sorted(key_seen.items()))
    return summary


def _write(path: Path, obj: Any):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def run_self_test():
    with TemporaryDirectory() as d:
        p = Path(d)
        _write(p / "a.json", {"items": [
            {"symbol": "AAA", "signal_date": "2026-09-08", "entry_variant": "A", "exit_variant": "E", "x": 1},
            {"symbol": "AAA", "signal_date": "2026-09-08", "x": 2},
            {"symbol": "AAA", "signal_date": "2026-09-08", "entry_variant": "A", "exit_variant": "E", "y": 3},
            {"symbol": "BBB", "signal_date": "2026-09-08", "entry_variant": "B", "exit_variant": "F"},
        ]})
        _write(p / "b.json", {"payload": {"symbol": "XXX", "signal_date": "2026-09-07", "entry_variant": "A", "exit_variant": "F"}})
        (p / "bad.json").write_text("{ not json", encoding="utf-8")

        s = summarize_json_tree(d)
        assert s["candidate_trade_dicts"] == 5
        assert any(d["file"].endswith("bad.json") for d in s["json_errors"])
        assert s["missing_optional_identity"]["entry_variant"] == 1
        assert s["missing_optional_identity"]["exit_variant"] == 1
        assert any(x["count"] == 2 for x in s["duplicate_identity_occurrences"])
        assert any(o["file"].endswith("a.json") for x in s["duplicate_identity_occurrences"] for o in x["occurrences"])

        empty_dir = p / "empty"
        empty_dir.mkdir()
        empty_summary = summarize_json_tree(str(empty_dir))
        assert empty_summary["files_scanned"] == 0
        assert empty_summary["candidate_trade_dicts"] == 0
        assert empty_summary["duplicate_identity_occurrences"] == []

        missing_summary = summarize_json_tree(str(p / "missing"))
        assert missing_summary["files_scanned"] == 0
        assert any(e["error"] == "path does not exist" for e in missing_summary["json_errors"])

        _write(p / "mixed.json", {"items": [
            {"symbol": {"raw": "AAA"}, "signal_date": "2026-09-08", "entry_variant": ["A"], "exit_variant": {"tag": "E"}},
            {"symbol": {"raw": "AAA"}, "signal_date": "2026-09-08", "entry_variant": ["A"], "exit_variant": {"tag": "E"}},
            {"symbol": ["A", "A"], "signal_date": "2026-09-08", "entry_variant": None, "exit_variant": "E"},
        ]})
        mixed_summary = summarize_json_tree(str(p / "mixed.json"))
        assert mixed_summary["candidate_trade_dicts"] == 3
        assert mixed_summary["missing_optional_identity"]["entry_variant"] == 1
        assert mixed_summary["total_duplicate_identity_overcount"] == 1

        print(json.dumps(s, ensure_ascii=False, indent=2, sort_keys=True))


def main():
    ap = argparse.ArgumentParser(description="Inventory nested JSON dicts with symbol+signal_date.")
    ap.add_argument("path", nargs="?", help="Directory or JSON file path.")
    ap.add_argument("--self-test", action="store_true", help="Run synthetic nested-data self-test.")
    args = ap.parse_args()

    if args.self_test:
        run_self_test()
        return
    if not args.path:
        raise SystemExit("path is required unless --self-test is used")

    print(json.dumps(summarize_json_tree(args.path), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
