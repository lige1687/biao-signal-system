"""R2 事后补充诊断（2026-09-03，非判定，跑前已知主实验结果后追加）。

定位：主实验（run_us_treasury_r2.py，判定已冻结）的 RA 臂用扩张窗口分位，
结构性只出 3 枚事件（1967/1971/1972）——扩张分位下 1965-82 高位年代把整条
历史分布抬高，post-1985 的 4-5% 收益率在全史分位仅 ~40-65，永不触发。
用户直觉（"5-6% 就是很高压制"）的参照系是**近 5 年**，对应滚动窗口分位。
本脚本只做诊断呈现（滚动 5 年分位事件 + 五分位条件表），不改主实验判定，
不设新判定线，输出单独落盘 posthoc_*。

- 滚动 5 年（1260 交易日，仅过去）分位 ≥85 / ≤15 事件（同主实验滞回参数）；
  事件后 12 个月前瞻 vs 资格日基线 + 安慰剂 2000 组（seed 同主实验）。
- 五分位条件表：按当日滚动 5 年分位分桶（0-20/20-40/40-60/60-80/80-100），
  各桶未来 12 个月平均收益 / 胜率 / 平均路径回撤——检验"水平越高未来越差"
  是否单调成立。
- DGS10 主表 + DGS30 附表（滚动窗在其 1977 起样本内）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parent
sys.path.insert(0, str(RAW))
from run_us_treasury_r2 import (load_fred, load_gspc, expanding_pct,  # noqa: E402
                                hysteresis_events, next_exec, WIN_START,
                                RA_HI, RA_LO, RA_REARM_DROP, RA_REARM_DAYS)

ROLL = 1260  # 滚动 5 年窗口（观测数）


def rolling_pct(x: pd.Series, window: int = ROLL) -> pd.Series:
    """t 日分位 = x[t] 在 x[t-window..t-1]（仅过去）的秩 ×100。"""
    v = x.values
    out = np.full(len(v), np.nan)
    for i in range(window, len(v)):
        if np.isnan(v[i]):
            continue
        h = v[i - window:i]
        h = h[~np.isnan(h)]
        if len(h) >= window - 1:
            out[i] = float((h < v[i]).sum() / len(h) * 100.0)
    return pd.Series(out, index=x.index)


def main() -> None:
    dgs10 = load_fred("DGS10")
    dgs30 = load_fred("DGS30")
    px = load_gspc()
    px = px[px.index >= WIN_START]
    opens, closes = px["open"].values, px["close"].values
    pos = {d: i for i, d in enumerate(px.index)}

    def fwd12(i):
        return closes[i + 252] / opens[i] - 1 if i + 252 < len(closes) else None

    def fwd_dd(i, w=252):
        j = min(i + w, len(closes) - 1)
        if j <= i:
            return None
        path = np.concatenate(([opens[i]], closes[i:j + 1]))
        return float((path / np.maximum.accumulate(path)).min() - 1)

    out: dict = {}
    for nm, s in (("dgs10", dgs10), ("dgs30", dgs30)):
        p = rolling_pct(s)
        if p.dropna().empty:
            continue
        pvf = p.dropna().index[0]
        elig = px.index[(px.index >= pvf)
                        & (px.index <= px.index[-1] - pd.Timedelta(days=370))]
        hi = hysteresis_events(p >= RA_HI, p <= RA_HI - RA_REARM_DROP, RA_REARM_DAYS)
        lo = hysteresis_events(p <= RA_LO, p >= RA_LO + RA_REARM_DROP, RA_REARM_DAYS)
        hi_x, lo_x = next_exec(hi, px), next_exec(lo, px)

        def stats(ex):
            rows = []
            for d in ex:
                i = pos.get(d)
                if i is None:
                    continue
                r12, dd = fwd12(i), fwd_dd(i)
                rows.append({"exec_date": str(d.date()),
                             "12m": None if r12 is None else round(r12, 4),
                             "dd252": None if dd is None else round(dd, 4)})
            vals = [r["12m"] for r in rows if r["12m"] is not None]
            dds = [r["dd252"] for r in rows if r["dd252"] is not None]
            return {"n": len(rows), "rows": rows,
                    "mean_12m": round(float(np.mean(vals)), 4) if vals else None,
                    "win_12m": round(float(np.mean([v > 0 for v in vals])), 3) if vals else None,
                    "mean_dd252": round(float(np.mean(dds)), 4) if dds else None}

        base12 = [fwd12(pos[d]) for d in elig if pos.get(d) is not None]
        base12 = [v for v in base12 if v is not None]
        basedd = [fwd_dd(pos[d]) for d in elig if pos.get(d) is not None]
        basedd = [v for v in basedd if v is not None]
        blk = {"pct_valid_from": str(pvf.date()),
               "hi_events": [str(d.date()) for d in hi],
               "lo_events": [str(d.date()) for d in lo],
               "hi_stats": stats(hi_x), "lo_stats": stats(lo_x),
               "baseline": {"n": len(base12),
                            "mean_12m": round(float(np.mean(base12)), 4),
                            "mean_dd252": round(float(np.mean(basedd)), 4)}}
        # 安慰剂（hi 臂）
        n = blk["hi_stats"]["n"]
        if n >= 5:
            rng = np.random.default_rng(20260903)
            e = np.array([d for d in elig if d in pos], dtype="datetime64[ns]")

            def stat_of(days):
                vals = [fwd12(pos[d]) for d in days
                        if pos.get(d) is not None and fwd12(pos[d]) is not None]
                return float(np.mean(vals)) if vals else np.nan
            draws = []
            for _ in range(2000):
                pick = rng.choice(len(e), size=min(n, len(e)), replace=False)
                draws.append(stat_of(pd.DatetimeIndex(e[pick])))
            draws = np.array([d for d in draws if not np.isnan(d)])
            below = float((draws < blk["hi_stats"]["mean_12m"]).mean() * 100)
            blk["hi_placebo_low_pct"] = round(100 - below, 2)
        # 五分位条件表
        tabs = []
        p_px = p.reindex(px.index).ffill(limit=5)
        for q in range(5):
            lo_b, hi_b = q * 20, q * 20 + 20
            days = [d for d in elig if not np.isnan(p_px.get(d, np.nan))
                    and lo_b <= p_px[d] < hi_b]
            vals = [fwd12(pos[d]) for d in days if fwd12(pos[d]) is not None]
            dds = [fwd_dd(pos[d]) for d in days if fwd_dd(pos[d]) is not None]
            tabs.append({"bucket": f"Q{q+1}[{lo_b},{hi_b})",
                         "n": len(vals),
                         "mean_12m": round(float(np.mean(vals)), 4) if vals else None,
                         "win_12m": round(float(np.mean([v > 0 for v in vals])), 3) if vals else None,
                         "mean_dd252": round(float(np.mean(dds)), 4) if dds else None})
        blk["quintile_table"] = tabs
        out[nm] = blk

    (RAW / "posthoc_rolling_level.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True, default=str))
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    sys.exit(main())
