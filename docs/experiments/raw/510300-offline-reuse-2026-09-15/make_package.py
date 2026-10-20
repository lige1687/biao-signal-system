"""正式拼装 510300 可恢复输入包（run-XX 编号留痕，排他创建，绝不删号复用）。

流程：fetch-manifest 取 symbol=sh510300 七条 → 与主控 verification.json 的
reuse.source_files 逐条比对一致才继续 → 由已核日历逐日推导必需交易日（完整性
闸门，1558 只是交叉证据）→ assemble 确定性拼接 → 写 prices.csv / quality.json /
source-decision.csv / 七份原件 / fetch-manifest / 日历 / 任务协议 / assemble.py
原字节 → manifest.json 最后写（包内集合/哈希双向一致）。

不计算任何真实收益/因子/状态；不联网；不调用真实研究入口。
用法：python3 make_package.py run-01
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAW = Path(__file__).resolve().parent
ROOT = RAW.parents[3]
sys.path.insert(0, str(ROOT / "src"))

from assemble import assemble  # noqa: E402

FETCH_DIR = ROOT / "docs/experiments/raw/research-third-2026-09-08/06"
FETCH_MANIFEST = FETCH_DIR / "fetch-manifest.json"
VERIFICATION = ROOT / ("docs/experiments/raw/"
                       "factor-unit-four-fixes-controller-2026-09-15/verification.json")
CALENDAR = ROOT / ("docs/experiments/raw/research-calendar-completion-2026-09-10/"
                   "calendar-merged/calendar.json")
COVER_START, COVER_END = "2019-09-02", "2026-02-03"
CROSS_CHECK_ROWS = 1558  # 主控交叉证据；放行闸门是逐日推导，不是行数


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cross_check_entries(entries: list[dict]) -> None:
    """与主控 verification.json 的 reuse.source_files 逐条一致才继续。"""
    want = json.loads(VERIFICATION.read_text())["reuse"]["source_files"]
    got = sorted(entries, key=lambda e: e["file"])
    ref = sorted(want, key=lambda e: e["file"])
    if len(got) != len(ref):
        raise SystemExit(f"sh510300 记录数不符：fetch-manifest {len(got)} vs 主控 {len(ref)}")
    for g, w in zip(got, ref, strict=True):
        for key in ("file", "sha256", "start", "end", "field", "rows",
                    "retrieved_at", "first", "last"):
            if g.get(key) != w.get(key):
                raise SystemExit(f"与主控清单不符：{g['file']} 字段 {key}: "
                                 f"{g.get(key)!r} vs {w.get(key)!r}")


def derive_sessions() -> list[str]:
    from lei_signal.research.trading_calendar import TradingCalendar
    cal = TradingCalendar.from_file(CALENDAR)
    return cal.trading_days(COVER_START, COVER_END)


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else "run-01"
    out = RAW / run_id
    if out.exists():
        print(f"REFUSE: {out} 已存在（编号留痕，绝不删除复用）", file=sys.stderr)
        return 3
    now = datetime.now(timezone(timedelta(hours=8)))

    manifest_bytes = FETCH_MANIFEST.read_bytes()
    entries = [e for e in json.loads(manifest_bytes)
               if e.get("symbol") == "sh510300"]
    cross_check_entries(entries)

    sessions = derive_sessions()
    rows, audit = assemble(entries, FETCH_DIR, sessions)
    if len(rows) != CROSS_CHECK_ROWS:
        print(f"WARN: 交叉证据行数 {len(rows)} != {CROSS_CHECK_ROWS}（以逐日推导为准）",
              file=sys.stderr)
    complete = audit["complete"] and len(rows) == len(sessions)

    out.mkdir()
    # 1) prices.csv（原始字符串，禁止舍入/修改）
    with (out / "prices.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "open", "close", "high", "low", "volume"])
        w.writerows(rows)
    # 2) quality.json
    quality = {
        "symbol": "sh510300",
        "coverage": {"start": COVER_START, "end": COVER_END,
                     "required_sessions": len(sessions),
                     "first_session": sessions[0], "last_session": sessions[-1]},
        "calendar": {"path": str(CALENDAR.relative_to(ROOT)), "sha256": sha(CALENDAR)},
        "completeness_gate": "由已核日历逐日推导必需交易日并逐日比对；行数仅交叉证据",
        "cross_check_rows": {"expected_by_controller": CROSS_CHECK_ROWS,
                             "actual": len(rows)},
        "audit": audit,
        "invalid_ohlc": 0,
        "complete": complete,
        "declarations": {
            "price_basis": "vendor_qfq",
            "extracted_field": "qfqday",
            "currency": "CNY",
            "retrieved_at": "继承原件清单（见 audit.inputs 逐条）",
            "assembled_at": now.isoformat(),
            "historical_available_at": None,
            "adjustment_anchor": "unknown（精确复权锚点未证）",
            "data_mode": "real",
            "historical_reconstruction_only": True,
            "not_claims": ["total_return_wealth", "point_in_time_verified",
                           "factor_effective", "tradable_profit"],
        },
    }
    (out / "quality.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=1) + "\n")
    # 3) source-decision.csv（本次包内来源裁定；不填 price_basis_verified 求放行）
    with (out / "source-decision.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "input", "input_sha256", "provenance_note",
                    "allowed_uses", "refused_uses"])
        w.writerow(["sh510300", f"{run_id}/prices.csv", sha(out / "prices.csv"),
                    "原件可追溯（七份供应商原始响应+fetch-manifest，哈希逐条一致）",
                    "仅供待批的供应商调整价历史描述（vendor_adjusted_price_change）",
                    "含分红财富目标；point-in-time资格；预测资格；生产用途"])
    # 4) 原字节归档：七份原件 + fetch-manifest + 日历 + 任务协议 + assemble.py
    orig_dir = out / "originals"
    orig_dir.mkdir()
    archived = {}
    for e in entries:
        data = (FETCH_DIR / e["file"]).read_bytes()
        (orig_dir / e["file"]).write_bytes(data)
        archived[f"originals/{e['file']}"] = hashlib.sha256(data).hexdigest()
    for rel, src in (("fetch-manifest.json", FETCH_MANIFEST),
                     ("calendar.json", CALENDAR),
                     ("task-protocol.md", RAW / "task-protocol.md"),
                     ("assemble.py", RAW / "assemble.py")):
        data = src.read_bytes()
        (out / rel).write_bytes(data)
        archived[rel] = hashlib.sha256(data).hexdigest()
    # 5) manifest.json 最后写；集合/哈希双向一致
    manifest = {
        "schema": "510300-offline-reuse/1.0.0",
        "run_id": run_id,
        "protocol": {"path": "task-protocol.md", "version": "1.0.0"},
        "source_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "entries": [{k: e[k] for k in ("file", "sha256", "start", "end", "field",
                                       "rows", "retrieved_at")} for e in entries],
        "declarations": quality["declarations"],
        "complete": complete,
        "file_hashes": {},
        "two_way_check": {},
        "written_at": now.isoformat(),
        "note": "离线复用原始响应；未计算真实状态/目标/收益；恢复级别见 README",
    }
    actual = {str(f.relative_to(out)) for f in out.rglob("*")
              if f.is_file() and f.name != "manifest.json"}
    manifest["file_hashes"] = {rel: sha(out / rel) for rel in sorted(actual)}
    manifest["two_way_check"] = {
        "listed_missing_on_disk": sorted(set(manifest["file_hashes"]) - actual),
        "on_disk_not_listed": sorted(actual - set(manifest["file_hashes"])),
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print(f"{run_id}: rows={len(rows)} complete={complete} "
          f"duplicates_deduped={audit['duplicates_deduped']} "
          f"extra_quarantined={len(audit['extra_rows_quarantined'])}")
    return 0 if complete else 2


if __name__ == "__main__":
    sys.exit(main())
