"""BCD 重测 · 2.3 个股池归因 + 复活判据核对。

输入：raw/bcd_retrial/stocks/*.json（run_bcd_stocks.py 产出）
产出：
  1. 每跑的判据核对表（C 类：expR>0 & OOS>0 & 排top3后>0 & N>=100；
     B/D 类：N>=30 & OOS>0 & 排top1 后不塌，标注统计力弱）
  2. 分行业 / 上市年限 / 波动档三维分组（行业组=stock_pool.txt 事前归类；
     上市三档 1996-2011/2012-2016/2017-2018；波动档=池内年化波动三分位）
  3. stocks_attribution.json 落盘
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "bcd_retrial"
sys.path.insert(0, str(ROOT / "src"))


def load_pool_meta() -> dict[str, dict]:
    meta: dict[str, dict] = {}
    for line in (RAW / "stock_pool.txt").read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        sym, name, ipo, industry = line.split("\t")
        meta[sym] = {"name": name, "ipo": int(ipo), "industry": industry}
    return meta


def vol_tiers() -> dict[str, str]:
    """池内年化波动率三分位（低/中/高）。"""
    import numpy as np

    from lei_signal.backtest import service as svc

    frames = svc._cached_frames()
    vols = {}
    for sym, frame in frames.items():
        ret = frame["close"].astype(float).pct_change().dropna()
        if len(ret) < 200:
            continue
        vols[sym] = float(ret.std() * np.sqrt(250))
    items = sorted(vols.items(), key=lambda kv: kv[1])
    n = len(items)
    return {
        sym: ("低" if i < n / 3 else "中" if i < 2 * n / 3 else "高")
        for i, (sym, _v) in enumerate(items)
    }


def ipo_tier(ipo: int) -> str:
    if ipo <= 2011:
        return "1996-2011（老股）"
    if ipo <= 2016:
        return "2012-2016（中期）"
    return "2017-2018（次新）"


def _group_attr(trades: list[dict], key_fn) -> dict[str, dict]:
    groups: dict[str, list[float]] = {}
    for t in trades:
        if t.get("r_net") is None:
            continue
        groups.setdefault(key_fn(t), []).append(t["r_net"])
    return {
        k: {"N": len(v), "expR": sum(v) / len(v), "totalR": sum(v)}
        for k, v in sorted(groups.items())
    }


def _ex_top(trades: list[dict], k: int) -> tuple[float | None, list[str]]:
    closed = [t for t in trades if t.get("r_net") is not None]
    by_sym: dict[str, float] = {}
    for t in closed:
        by_sym[t["symbol"]] = by_sym.get(t["symbol"], 0.0) + t["r_net"]
    top = sorted(by_sym.items(), key=lambda kv: -kv[1])[:k]
    top_syms = [s for s, _ in top]
    rest = [t for t in closed if t["symbol"] not in top_syms]
    rs = [t["r_net"] for t in rest]
    return (sum(rs) / len(rs) if rs else None), top_syms


def _fmt(v: float | None) -> str:
    return f"{v:+.3f}" if v is not None else "  -   "


def main() -> None:
    meta = load_pool_meta()
    tiers = vol_tiers()
    files = sorted((RAW / "stocks").glob("*.json"))
    print(f"{len(files)} run JSONs")
    out: dict[str, dict] = {}

    print("\n## 判据核对（个股池）")
    print("| 跑 | N | expR | IS | OOS | 排top1后 | 排top3后 | top1 | 判据 |")
    print("|---|---|---|---|---|---|---|---|---|")
    for fp in files:
        d = json.loads(fp.read_text(encoding="utf-8"))
        trades = d.get("trades_detail", [])
        if not trades:
            continue
        ex1, _ = _ex_top(trades, 1)
        ex3, _ = _ex_top(trades, 3)
        ov = d["overview"]
        is_c = fp.stem.startswith("C_")
        n = ov["trade_count"] or 0
        expr = ov["expectancy_r"]
        oos = d["oos_expectancy"]
        if is_c:
            ok = (
                n >= 100
                and expr is not None and expr > 0
                and oos is not None and oos > 0
                and ex3 is not None and ex3 > 0
            )
            verdict = "PASS" if ok else "FAIL"
        else:  # B/D/A：A 是基准对照（不判复活）；B/D 用稀疏形态判据
            ok = (
                n >= 30
                and oos is not None and oos > 0
                and ex1 is not None
                and (expr is None or ex1 >= expr - 0.3)  # 排 top1 后不塌（容差 0.3R）
            )
            is_baseline = fp.stem.startswith("A_")
            verdict = "基准" if is_baseline else (
                "PASS（统计力弱）" if ok else "FAIL"
            )
        print(
            f"| {fp.stem} | {n} | {_fmt(expr)} | {_fmt(d['is_expectancy'])} | "
            f"{_fmt(oos)} | {_fmt(ex1)} | {_fmt(ex3)} | {d.get('top1_symbol') or '-'} | {verdict} |"
        )
        by_industry = _group_attr(
            trades, lambda t: meta.get(t["symbol"], {}).get("industry", "未知")
        )
        by_ipo = _group_attr(
            trades, lambda t: ipo_tier(meta.get(t["symbol"], {}).get("ipo", 2015))
        )
        by_vol = _group_attr(trades, lambda t: tiers.get(t["symbol"], "未知"))
        out[fp.stem] = {
            "overview": ov,
            "IS": d["is_expectancy"],
            "OOS": d["oos_expectancy"],
            "top1": d.get("top1_symbol"),
            "ex_top1": ex1,
            "ex_top3": ex3,
            "verdict": verdict,
            "by_industry": by_industry,
            "by_ipo": by_ipo,
            "by_vol": by_vol,
        }

    print("\n## 三维归因（每跑：行业 / 上市 / 波动）")
    for name, v in out.items():
        print(f"\n### {name}  N={v['overview']['trade_count']} "
              f"expR={_fmt(v['overview']['expectancy_r'])}")
        print("| 维度 | 组 | N | expR | totalR |")
        print("|---|---|---|---|---|")
        for label, groups in (
            ("行业", v["by_industry"]),
            ("上市", v["by_ipo"]),
            ("波动", v["by_vol"]),
        ):
            for g, gv in groups.items():
                print(f"| {label} | {g} | {gv['N']} | {_fmt(gv['expR'])} | {gv['totalR']:+.1f} |")

    fp = RAW / "stocks_attribution.json"
    fp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[-> {fp.name}]")


if __name__ == "__main__":
    main()
