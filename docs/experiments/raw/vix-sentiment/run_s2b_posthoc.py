"""S2b 后验补测：VIX/VIX3M 扩张分位 >= 90（深度倒挂）——报告专用，永不采纳。

诚实条款（2026-09-01）：预注册 S2 的文字标签写"长端深度倒挂"，但冻结
规则误写为"分位 <= 10"——低分位实为深度 contango（平静市），与标签相反。
as-run 结果（≤10，判负）维持有效；本脚本补测标签本意（≥90 倒挂方向），
性质 = 后验（看完 ≤10 结果后补的方向翻转），只报告，不进判定，
任何采用都需全新预注册。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("m", HERE / "run_vix_sentiment.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

vix = m._read_cboe_index("VIX_History.csv")
v3 = m._read_cboe_index("VIX3M_History.csv")
gspc = m._load_prices()["gspc_ohlc"]["close"]

q = (vix / v3).dropna()
pct = m.expanding_pctile(q)
dates = m.apply_cooldown(
    list(q.index[(pct >= 90.0).fillna(False)]), m.COOLDOWN_TD, q.index
)
start = q.index[m.MIN_PCT_PERIODS - 1]

ev = m.forward_returns(gspc, dates)
base = m.baseline_returns(gspc, start, q.index.max())
pl = m.placebo_test(gspc, dates, start, q.index.max())

out = {
    "status": "POST-HOC, report-only, never adopt without new pre-registration",
    "reason": "pre-registered S2 label(rule) inconsistency: label=backwardation, rule=pctile<=10 (contango)",
    "definition": "VIX/VIX3M expanding pctile >= 90, cooldown 10td",
    "n_signals": len(dates),
    "signal_mean": {h: m.R6(ev[f"fwd_{h}"].mean()) for h in m.HORIZONS},
    "baseline_mean": {h: m.R6(base[h]) for h in m.HORIZONS},
    "win_rate_252": m.R6(ev["fwd_252"].mean() and (ev["fwd_252"] > 0).mean()),
    "placebo": pl,
    "first_last": [str(dates[0].date()) if dates else None,
                    str(dates[-1].date()) if dates else None],
    "sample_dates_2020_2022_check": [
        str(d.date()) for d in dates if pd.Timestamp("2020-02-01") <= d <= pd.Timestamp("2020-04-30")
    ],
}
(HERE / "s2b_posthoc_results.json").write_text(
    json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
)
print(json.dumps({k: v for k, v in out.items() if k != "sample_dates_2020_2022_check"},
                 indent=1, sort_keys=True))
print("2020-02→04 signals:", out["sample_dates_2020_2022_check"])
