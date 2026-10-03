"""Render frozen aggregate facts; never generate signals or run an account."""
import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path

LABELS = {"B0": "一直持有", "A_ALL": "旧早期机会都参与", "A_SMA": "当天SMA确认才参与", "A_WAIT": "机会内等待确认", "A_HALF": "5万元参与+5万元现金", "A_STOP": "只守初始止损"}
SYMBOLS = ["510300.SS", "510050.SS", "510500.SS", "512100.SS", "159915.SZ", "588000.SS"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, help="Optional: verify original local JSON hashes and exact pointers")
    args = parser.parse_args()
    raw = args.extract.read_bytes()
    data = json.loads(raw)
    rows = data["rows"]
    assert data["kind"] == "saved_aggregate_extract_not_new_backtest"
    index = {(r["symbol"], r["policy_id"], r["fee_scenario_id"]): r for r in rows}
    assert len(index) == len(rows) == 72
    assert set(r["symbol"] for r in rows) == set(SYMBOLS)
    fees = {r["fee_scenario_id"]: r["fee"] for r in rows}
    assert set(fees.values()) == {"0.001", "0.002"}
    for r in rows:
        assert r["period_start"] == "2022-01-01" and r["period_end"] == "2026-09-25"
        assert r["trade_sides"] == sum(a["trade_sides"] for a in r["annual"])
        assert len(r["annual"]) == 5
        assert all(a["trade_sides"] == 0 for a in r["annual"][:3]) if r["policy_id"] != "B0" else True
    verified = []
    if args.source_root:
        for item in data["input_manifest"]:
            original = (args.source_root / item["path"]).read_bytes()
            assert len(original) == item["size"]
            assert hashlib.sha256(original).hexdigest() == item["sha256"]
            objects = json.loads(original)
            for r in rows:
                if r["source_path"] != item["path"]:
                    continue
                value = objects[int(r["json_pointer"].removeprefix("/"))]
                for key in ("symbol", "policy_id", "fee_scenario_id", "fee", "period_start", "period_end", "ending_assets_100k_cny", "total_fees_cny", "net_annualized_return_pct", "max_account_drawdown_pct", "average_invested_pct", "completed_trade_windows", "open_positions"):
                    assert r[key] == value.get(key), (r["json_pointer"], key)
                for actual, expected in zip(r["annual"], value["annual"], strict=True):
                    assert all(v == expected.get(k) for k, v in actual.items())
            verified.append(item["path"])
    args.out.mkdir(parents=True, exist_ok=False)
    lines = ["# C 基准：保存账户全表", "", "这是旧结果摘录，不是新回测。每行是独立10万元研究账户；六只不能相加当共享资金组合。历史均已接触，完整原文资格未成立。", "", "金额已扣该情景费用；最大跌幅指账户从此前最高金额向下跌最多的比例；成交次数为买或卖的单边次数。", ""]
    for fee_id, fee in sorted(fees.items(), key=lambda x: Decimal(x[1])):
        lines += [f"## 买、卖每次费用 {100 * Decimal(fee):.1f}%", "", "| ETF | 旧方法 | 期末金额/元 | 最深跌幅 | 成交次数 | 平均投入 | 2025金额变化/元 | 2026截至9/25变化/元 |", "|---|---|---:|---:|---:|---:|---:|---:|"]
        for symbol in SYMBOLS:
            for policy, label in LABELS.items():
                r = index[symbol, policy, fee_id]
                years = {a["year"]: a for a in r["annual"]}
                lines.append(f"| {symbol} | {label} | {Decimal(r['ending_assets_100k_cny']):,.2f} | {r['max_account_drawdown_pct']:.2f}% | {r['trade_sides']} | {r['average_invested_pct']:.2f}% | {Decimal(years[2025]['profit_cny']):+,.2f} | {Decimal(years[2026]['profit_cny']):+,.2f} |")
        lines.append("")
    lines += ["## 固定比较的增量（基础费用）", "", "差额=候选减基准；跌幅差为负表示这段历史跌得少。资金用途不同的B0只作机会成本参照，不称入场因果增量。", "", "| ETF | 候选相对基准 | 期末金额差/元 | 最大跌幅差/百分点 |", "|---|---|---:|---:|"]
    for symbol in SYMBOLS:
        for candidate, baseline in [("A_SMA", "A_ALL"), ("A_WAIT", "A_SMA"), ("A_HALF", "A_SMA"), ("A_STOP", "A_ALL")]:
            a, b = index[symbol, candidate, "base"], index[symbol, baseline, "base"]
            lines.append(f"| {symbol} | {candidate} − {baseline} | {Decimal(a['ending_assets_100k_cny'])-Decimal(b['ending_assets_100k_cny']):+,.2f} | {a['max_account_drawdown_pct']-b['max_account_drawdown_pct']:+.2f} |")
    (args.out / "tables.md").write_text("\n".join(lines) + "\n")
    receipt = {"kind": "saved_aggregate_validation_only", "rows": len(rows), "key_count": len(index), "fee_scenarios": fees, "source_files_verified": verified, "extract_sha256": hashlib.sha256(raw).hexdigest(), "new_market_runs": 0, "fits": 0, "limits": "Does not revalidate historical signal generation, cash engine, data licence, live arrival, or complete LEI eligibility."}
    (args.out / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
