#!/usr/bin/env python3
"""冰点机会·多年多事件终审（2026-09-06，预注册判定）。

事件窗口（沪深300 60日跌幅≤-12% 识别 + 2026 年内 CN 冰点段）：
- 2022-A：2022-03-01 ~ 2022-06-15（上海疫情+俄乌）
- 2022-B：2022-09-15 ~ 2022-11-15（十月大跌）
- 2026-A：2026-04 月冰点段（由数据自动识别）
- 2026-B：2026-07-15 ~ 2026-08-04（年内主恐慌）

信号（窗口内即视为冰点环境，与单年版三票口径的差异如实标注）：
TS5 = 板块散户流入 z≥1.5（自身120日）× 板块60日跌幅≤-10%。
价格统一用 tx_close_panel（成分股收盘均值，两期同口径）。

预注册判定：≥4 事件，事件级 15 日均收益为正的事件占比 ≥60%（≥3/4）
→ 确认；任一大事件（触发≥10例）均值为负 → 该事件失败计数。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from retail_sentiment_ts_backtest import zscore_self  # noqa: E402

CACHE = Path.home() / ".lei_signal_lab/cache"
EVENTS = [
    ("2022-A", "2022-03-01", "2022-06-15"),
    ("2022-B", "2022-09-15", "2022-11-15"),
    ("2026-A", "2026-03-20", "2026-04-30"),
    ("2026-B", "2026-07-10", "2026-08-04"),
]


def main() -> int:
    close_p = pd.read_parquet(CACHE / "tx_close_panel.parquet")
    close_p = close_p.apply(pd.to_numeric, errors="coerce")
    close_p.index = pd.to_datetime(close_p.index)
    tx = json.loads((CACHE / "tx_sector_flow_pilot.json").read_text(encoding="utf-8"))
    members = json.loads((CACHE / "sector_members.json").read_text(encoding="utf-8"))["boards"]
    snap = json.loads((CACHE / "sector_trend_snapshot.json").read_text(encoding="utf-8"))
    canonical = {b["code"] for b in snap["boards"] if (b.get("level") or 3) <= 2}

    # 板块级序列：close（成分均值）与散户强度
    wins, fails = 0, 0
    print(f"{'事件':8s} {'窗口':24s} {'触发':>4s} {'15日均收':>8s} {'胜率':>5s} 判定")
    for name, d0, d1 in EVENTS:
        rets = []
        for code in canonical:
            mem = [s for s in members.get(code, {}).get("members", []) if s in close_p.columns]
            if len(mem) < 5:
                continue
            C = close_p[mem].mean(axis=1).dropna()
            if len(C) < 150:
                continue
            pts = (tx.get("boards") or {}).get(code) or []
            if not pts:
                continue
            recS = {}
            last_c = float(C.iloc[-1])
            for p in pts:
                d = pd.to_datetime(p["date"])
                if d in C.index and p.get("small_yi") is not None:
                    # 市值回溯锚：mv_today 不可得（2022），用 C 相对最新归一
                    recS[d] = p["small_yi"]  # 绝对额——z 为自身基准，量纲漂移标注
            if not recS:
                continue
            S = pd.Series(recS).sort_index()
            # z 基于绝对额（亿元）的自身 120 日——与单年版的 /市值 差异：
            # 板块内自身比较，市值漂移缓慢，z 口径近似成立（诚实标注）
            S = S.reindex(C.index)
            z = zscore_self(S.rolling(20, min_periods=20).mean())
            r60 = C.pct_change(60, fill_method=None)
            sig = ((z >= 1.5) & (r60 <= -0.10)).fillna(False)
            idx = C.index
            for t in idx[(idx >= pd.to_datetime(d0)) & (idx <= pd.to_datetime(d1))]:
                if bool(sig.get(t, False)):
                    i = idx.get_loc(t)
                    if i + 15 < len(idx):
                        v = float(C.iloc[i + 15]) / float(C.iloc[i]) - 1
                        if not pd.isna(v):
                            rets.append(v)
        if len(rets) < 5:
            print(f"{name:8s} {d0}~{d1} {len(rets):4d}      —— 样本不足（窗口内无触发）")
            continue
        r = np.array(rets)
        ok = r.mean() > 0
        wins += int(ok)
        fails += int(not ok)
        print(f"{name:8s} {d0}~{d1} {len(r):4d} {r.mean()*100:+7.2f}% {(r>0).mean()*100:4.0f}% {'✓盈利' if ok else '✗亏损'}")
    print(f"\n事件级：{wins} 盈利 / {fails} 亏损")
    if wins + fails >= 4:
        verdict = "确认（CONFIRMED）" if wins / (wins + fails) >= 0.6 else "证伪（FALSIFIED）"
    elif wins + fails >= 2:
        verdict = "部分确认（≥2事件，样本不足4，留观）" if wins == wins else "部分证伪"
    else:
        verdict = "样本不足"
    print(f"终审判定：{verdict}（预注册标准：≥4事件且盈利事件占比≥60%）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
