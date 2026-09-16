"""BCD 重测 · 第一步归因：C × 缩量 × 真空矩阵（24 配置 × 3 池 = 72 JSON）。

产出（stdout 表格 + summary JSON）：
  1. a6_1_costbasis 侧 12 配置 × 3 池主表：N / expR / IS / OOS / 排top3后 / top1
  2. a6_3_structure_stop 侧同表（带 open_at_end 占比警示：A6③ 只在止损时平仓，
     盈利单全部 open_at_end 被剔除出统计 -- 表内数字是「左尾」，不是全貌）
  3. 分年份 + 分标的类型（候选档 v2/v3 shrink）
  4. dropped-group 逐笔归因：shrink 砍掉的交易的均值 R（base 有、shrink 无）
复活判据（C，样本充分类）：全池期望>0 且 OOS>0 且排 top3 后仍>0 且 N>=100。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "bcd_retrial" / "c_matrix"
sys.path.insert(0, str(ROOT / "scripts"))
from run_shrink_filter import (  # type: ignore # noqa: E402
    POOL_BROAD,
    POOL_ETF,
    POOL_INDEX,
    POOL_INDUSTRY,
)

POOLS = ("A股ETF", "行业ETF", "全池")
VERSIONS = ("v1", "v2", "v3")
FILTERS = ("base", "shrink", "vacuum", "shvac")

SPLIT = "2024-08-25"


def _load(pool: str, version: str, exit_short: str, filt: str) -> dict | None:
    fp = RAW / f"C_{version}_{exit_short}_{filt}__{pool}.json"
    if not fp.exists():
        return None
    return json.loads(fp.read_text(encoding="utf-8"))


def _avg(trades: list[dict]) -> float | None:
    rs = [t["r_net"] for t in trades if t.get("r_net") is not None]
    return sum(rs) / len(rs) if rs else None


def _n(trades: list[dict]) -> int:
    return sum(1 for t in trades if t.get("r_net") is not None)


def _ex_top(trades: list[dict], k: int) -> tuple[float | None, list[str]]:
    closed = [t for t in trades if t.get("r_net") is not None]
    by_sym: dict[str, float] = {}
    for t in closed:
        by_sym[t["symbol"]] = by_sym.get(t["symbol"], 0.0) + t["r_net"]
    top = sorted(by_sym.items(), key=lambda kv: -kv[1])[:k]
    top_syms = [s for s, _ in top]
    rest = [t for t in closed if t["symbol"] not in top_syms]
    return _avg(rest), top_syms


def _sym_type(symbol: str) -> str:
    if symbol in POOL_ETF:
        return "A股ETF池(round4)"
    if symbol in POOL_INDUSTRY:
        return "行业ETF"
    if symbol in POOL_BROAD:
        return "宽基ETF"
    if symbol in POOL_INDEX:
        return "指数本体"
    if symbol.startswith("TH"):
        return "TH板块指数"
    if symbol.startswith("^"):
        return "海外/港指数"
    if symbol.endswith((".SS", ".SZ")):
        return "A股个股"
    return "美股ETF"


def _fmt(v: float | None) -> str:
    return f"{v:+.3f}" if v is not None else "  -  "


def _row(label: str, d: dict) -> str:
    trades = d.get("trades_detail", [])
    ex3, tops = _ex_top(trades, 3)
    open_n = sum(1 for t in trades if t.get("r_net") is None)
    ov = d["overview"]
    return (
        f"| {label} | {ov['trade_count'] or 0} | {_fmt(ov['expectancy_r'])} | "
        f"{_fmt(d['is_expectancy'])} | {_fmt(d['oos_expectancy'])} | "
        f"{_fmt(ex3)} | {d.get('top1_symbol') or '-'} | {open_n} |"
    )


def main() -> None:
    out: dict[str, dict] = {"cb": {}, "ss": {}, "attribution": {}, "dropped": {}}

    for exit_short, title in (("cb", "a6_1_costbasis（抵扣价退出，公平台）"),
                              ("ss", "a6_3_structure_stop（C 原生失效=破 L2）")):
        print(f"\n## {title}")
        for pool in POOLS:
            print(f"\n### {pool}")
            print("| 配置 | N | expR | IS | OOS | 排top3后 | top1 | open |")
            print("|---|---|---|---|---|---|---|---|")
            for version in VERSIONS:
                for filt in FILTERS:
                    d = _load(pool, version, exit_short, filt)
                    if d is None:
                        continue
                    print(_row(f"{version}/{filt}", d))
                    out[exit_short][f"{pool}::{version}/{filt}"] = {
                        "N": d["overview"]["trade_count"],
                        "expR": d["overview"]["expectancy_r"],
                        "IS": d["is_expectancy"],
                        "OOS": d["oos_expectancy"],
                        "ex_top3": _ex_top(d.get("trades_detail", []), 3)[0],
                        "top1": d.get("top1_symbol"),
                    }

    # 候选档归因：全池 v2/v3 × base/shrink（cb 侧）
    print("\n## 候选档归因（全池，a6_1_costbasis）")
    for version in ("v2", "v3"):
        for filt in ("base", "shrink"):
            d = _load("全池", version, "cb", filt)
            if d is None:
                continue
            trades = [t for t in d["trades_detail"] if t.get("r_net") is not None]
            # 分年份
            by_year: dict[str, list[float]] = {}
            for t in trades:
                yr = t["signal_date"][:4]
                by_year.setdefault(yr, []).append(t["r_net"])
            # 分标的类型
            by_type: dict[str, list[float]] = {}
            for t in trades:
                by_type.setdefault(_sym_type(t["symbol"]), []).append(t["r_net"])
            key = f"{version}/{filt}"
            out["attribution"][key] = {
                "by_year": {
                    y: {"N": len(v), "expR": sum(v) / len(v)}
                    for y, v in sorted(by_year.items())
                },
                "by_type": {
                    y: {"N": len(v), "expR": sum(v) / len(v)}
                    for y, v in sorted(by_type.items())
                },
            }
            print(f"\n### {key}")
            print("| 年份 | N | expR |    | 标的类型 | N | expR |")
            print("|---|---|---|---|---|---|---|")
            years = sorted(by_year)
            types = sorted(by_type)
            def _cell(groups: dict[str, list[float]], names: list[str], i: int) -> str:
                if i >= len(names):
                    return "| | |"
                rs = groups[names[i]]
                return f"| {names[i]} | {len(rs)} | {_fmt(sum(rs)/len(rs))} |"

            for i in range(max(len(years), len(types))):
                print(_cell(by_year, years, i) + _cell(by_type, types, i))

    # dropped-group 逐笔归因：shrink 砍掉的交易（base 有 shrink 无）
    print("\n## 被缩量砍掉的组（逐笔归因，a6_1_costbasis）")
    print("| 池 | 版本 | 砍掉N | 砍掉组expR | 保留组expR | 基线expR |")
    print("|---|---|---|---|---|---|")
    for pool in POOLS:
        for version in VERSIONS:
            base = _load(pool, version, "cb", "base")
            shrink = _load(pool, version, "cb", "shrink")
            if base is None or shrink is None:
                continue
            kept_keys = [(t["symbol"], t["signal_date"]) for t in shrink["trades_detail"]]
            kept_set = set(kept_keys)
            dropped = [
                t for t in base["trades_detail"]
                if (t["symbol"], t["signal_date"]) not in kept_set
            ]
            # 保留组直接用 shrink 的明细（同口径重算）
            row = {
                "dropped_N": _n(dropped),
                "dropped_expR": _avg(dropped),
                "kept_expR": _avg(shrink["trades_detail"]),
                "base_expR": _avg(base["trades_detail"]),
            }
            out["dropped"][f"{pool}::{version}"] = row
            print(
                f"| {pool} | {version} | {row['dropped_N']} | {_fmt(row['dropped_expR'])} | "
                f"{_fmt(row['kept_expR'])} | {_fmt(row['base_expR'])} |"
            )

    fp = ROOT / "docs" / "experiments" / "raw" / "bcd_retrial" / "c_matrix_summary.json"
    fp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[summary -> {fp.name}]")


if __name__ == "__main__":
    main()
