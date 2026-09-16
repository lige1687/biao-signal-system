#!/usr/bin/env python3
"""黄金持有腿扩池·预注册实验：B9 + 518880 价格外分散（2026-08-31）。

依据：m5-final-review「下一个有增量信息的指数方向只剩『价格外数据』
（港股通/黄金为持有腿的扩池、基本面入池）」——本实验做黄金项。

【预注册协议】（跑前写死，跑后不改）
架构（分账制，与 run_combined_cert 同构）：
- 主腿 = B9：9 标的等权 × B200 三档 43.3/56.7 周频次日生效；5% 带；
  单边 10bp。机械与 run_portfolio_split 的 B_全宽度闸 臂逐位一致。
- 黄金腿 = 518880 华安黄金 ETF 前复权收盘、纯持有：无闸、零换手、
  零成本（与美股持有腿同待遇；M5 已证伪「美股任何形式的闸」，
  黄金为价格外资产同理不过闸——附闸版对照仅作报告项）。
- 分账 = 两腿独立复利、永不再平衡；合体权益 = 两腿之和。

窗口：2015-06-16 → 2026-08-18（与 portfolio_split 全窗一致；黄金
2013-07-29 上市，全覆盖，无暖机问题）。

臂：hold / b9 / gold / combo_gold w∈{5%,10%(主),15%,20%} / 月度再平衡10%对照。

判定（冻结）：
- G1（收益不稀释）：combo_gold(10%) 年化 >= b9 年化；
- G2（回撤纪律）：combo_gold(10%) maxDD <= b9 maxDD + 1.0pp；
- G3（阴跌段贡献）：2021-06-18→2024-02-29 段内（段前权益起算）
  combo_gold(10%) 回撤 <= b9 同段回撤；
- G4（权重敏感性）：w=5%/15%/20% 下 G1∧G2 方向均不变；
- G5（分窗）：前半(→2020-12-31)/后半(2021-01-01→) G1∧G2 均不变；
- 总 PASS = G1∧G2∧G3∧G4∧G5。

纪律：不改 configs/web/engine/service；数据 = 腾讯前复权日线
（raw/gold_expand/518880_close.parquet，本日新拉全历史 3184 根）。
结论只到「建议」级。
输出：docs/experiments/raw/gold_expand/gold_expand_results.json
复现：PYTHONHASHSEED=0 python3 scripts/run_gold_expand.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw"
sys.path.insert(0, str(REPO / "scripts"))

import run_portfolio_split as rps  # noqa: E402

RAW = SRC / "gold_expand"

# ── 冻结配置 ──
W_GOLDS = (0.05, 0.10, 0.15, 0.20)
W_STD = 0.10
G2_TOL = 1.0
SEG_LO, SEG_HI = "2021-06-18", "2024-02-29"
SPLIT_HALF = "2021-01-01"


def seg_dd(eq: pd.Series, lo: str, hi: str) -> float:
    seg = eq[(eq.index >= pd.Timestamp(lo)) & (eq.index <= pd.Timestamp(hi))]
    base = eq[eq.index < pd.Timestamp(lo)]
    start = float(base.iloc[-1]) if len(base) else float(seg.iloc[0])
    peak, worst = start, 0.0
    for v in seg.values:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return worst * 100.0


def metrics(eq: pd.Series) -> dict:
    m = rps.metrics(eq)
    m["seg_dd_pct"] = round(seg_dd(eq, SEG_LO, SEG_HI), 2)
    return m


def q12(ann_c: float, dd_c: float, ann_b: float, dd_b: float) -> tuple[bool, bool]:
    return (bool(float(ann_c) >= float(ann_b)),
            bool(float(dd_c) >= float(dd_b) - G2_TOL))


def rebalance_series(eq_main_n: pd.Series, eq_g_n: pd.Series, w: float) -> pd.Series:
    r_main = eq_main_n.pct_change().fillna(0.0)
    r_g = eq_g_n.pct_change().fillna(0.0)
    idx = eq_main_n.index
    months = [(d.year, d.month) for d in idx]
    a, b = 1.0 - w, w
    vals = []
    for i in range(len(idx)):
        a *= 1.0 + r_main.iloc[i]
        b *= 1.0 + r_g.iloc[i]
        total = a + b
        vals.append(total)
        if i + 1 < len(idx) and months[i + 1] != months[i]:
            a, b = total * (1.0 - w), total * w
    return pd.Series(vals, index=idx)


def main() -> None:
    b200 = rps.load_breadth()
    members = [(k, v) for k, v in {**rps.GATED, **rps.TREND}.items()]
    frames = {}
    for name, rel in members:
        s = pd.read_parquet(SRC / rel)["close"].astype(float)
        s.index = pd.to_datetime(s.index)
        frames[name] = s
    gold = pd.read_parquet(RAW / "518880_close.parquet")["close"].astype(float)
    gold.index = pd.to_datetime(gold.index)

    prices = pd.DataFrame(frames)
    prices = prices[(prices.index >= pd.Timestamp(rps.WIN_START))
                    & (prices.index <= pd.Timestamp(rps.WIN_END))] \
        .dropna(axis=0, how="any")
    idx = prices.index
    gold_w = gold.reindex(idx).ffill().dropna()
    idx = gold_w.index
    prices = prices.reindex(idx)

    tier = rps.tier_daily(b200, idx)
    eq_hold = rps.simulate(prices, pd.DataFrame(1.0, index=idx,
                                                columns=prices.columns))["eq"]
    eq_b9 = rps.simulate(prices, pd.DataFrame({c: tier for c in prices.columns}))["eq"]

    hold_n = eq_hold / eq_hold.iloc[0]
    b9_n = eq_b9 / eq_b9.iloc[0]
    gold_n = gold_w / gold_w.iloc[0]

    arms: dict[str, pd.Series] = {"hold": hold_n, "b9": b9_n, "gold": gold_n}
    for w in W_GOLDS:
        arms[f"gold_{int(w*100)}"] = b9_n * (1.0 - w) + gold_n * w
    arms["gold_rebal_10"] = rebalance_series(b9_n, gold_n, W_STD)
    # 黄金闸版对照（报告项：预期劣化，佐证黄金不过闸）——持仓模拟口径
    tier_g = rps.tier_daily(b200, gold_w.index).reindex(gold_w.index).ffill().fillna(1.0)
    r_g = gold_w.pct_change().fillna(0.0)
    gold_gated = (1.0 + r_g * tier_g).cumprod()
    arms["gold_gated_ref"] = gold_gated / gold_gated.iloc[0]

    met = {k: metrics(v) for k, v in arms.items()}
    b9m, gm = met["b9"], met["gold_10"]
    g1, g2 = q12(gm["ann_pct"], gm["maxdd_pct"], b9m["ann_pct"], b9m["maxdd_pct"])
    g3 = bool(float(gm["seg_dd_pct"]) >= float(b9m["seg_dd_pct"]))
    g4 = all(q12(met[f"gold_{int(w*100)}"]["ann_pct"],
                 met[f"gold_{int(w*100)}"]["maxdd_pct"],
                 b9m["ann_pct"], b9m["maxdd_pct"]) for w in (0.05, 0.15, 0.20))

    half = idx < pd.Timestamp(SPLIT_HALF)
    g5_parts = []
    for mask, tag in ((half, "front"), (~half, "back")):
        b9_sub = b9_n[mask] / b9_n[mask].iloc[0]
        # 分窗内重算黄金腿与合成（黄金腿无需重算机械，直接归一截断）
        g_sub = gold_n[mask] / gold_n[mask].iloc[0]
        c_sub = b9_sub * (1.0 - W_STD) + g_sub * W_STD
        m_b, m_c = metrics(b9_sub), metrics(c_sub)
        g5_parts.append((tag,) + q12(m_c["ann_pct"], m_c["maxdd_pct"],
                                     m_b["ann_pct"], m_b["maxdd_pct"]))
    g5 = all(j1 and j2 for _, j1, j2 in g5_parts)

    # 报告项：相关性
    r_b9 = b9_n.pct_change().dropna()
    r_gold = gold_n.pct_change().dropna()
    common = r_b9.index.intersection(r_gold.index)
    corr = float(r_b9[common].corr(r_gold[common]))

    out = {
        "experiment": "gold_expand_b9_518880",
        "window": [str(idx[0].date()), str(idx[-1].date())],
        "corr_b9_gold": round(corr, 3),
        "arms": met,
        "verdict_rules": {
            "G1": "gold10 ann >= b9 ann",
            "G2": f"gold10 maxdd <= b9 maxdd + {G2_TOL}pp",
            "G3": f"gold10 seg_dd <= b9 seg_dd ({SEG_LO}~{SEG_HI})",
            "G4": "G1&G2 hold at w 5%/15%/20%",
            "G5": "G1&G2 hold in front/back half windows",
        },
        "half_detail": [
            {"half": t, "G1": j1, "G2": j2} for t, j1, j2 in g5_parts
        ],
        "verdict": {
            "G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5,
            "PASS_all": bool(g1 and g2 and g3 and g4 and g5),
        },
    }
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True)
    (RAW / "gold_expand_results.json").write_text(text)
    pd.DataFrame({k: v for k, v in arms.items()}).to_csv(
        RAW / "gold_curves.csv", float_format="%.6f")

    print(json.dumps(out["arms"], ensure_ascii=False, indent=1))
    print("corr(b9, gold):", corr)
    print("verdict:", json.dumps(out["verdict"], ensure_ascii=False))
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
