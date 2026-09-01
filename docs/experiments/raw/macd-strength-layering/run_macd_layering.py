#!/usr/bin/env python3
"""MACD 强度状态 × 入场模块信号质量分层（Prompt E，2026-09-01 预注册）。

任务定位（唯一合法测法）：MACD 强度状态（macd_strength 八状态，研究代理）
能否给**已经能产生买卖点的入场模块 A/B/C/D** 的历史信号做质量分层。
不产生任何交易事件，不下买卖结论，不测"MACD 单独预判转折"。

═══════════════════════════════════════════════════════════════════
判定标准（预注册，跑前写死，跑完不得调整）
═══════════════════════════════════════════════════════════════════

【信号本体（只读，不重跑引擎）】当前分支 backtest 包处于半重构状态
（A/B/C 检测器已不满足 engine.py 的事件契约：缺 stop_price/variant 字段，
直接 import 即 ImportError），无法重跑。故信号本体取自已归档的
execute_run 全量逐笔输出（2026-08-27/28 工作树状态产出，已入 git），
全部 standard 费用 + limit_guard，窗口 2016-08→2026-08：

  cn-A: raw/breadth_overlay/wf_a_noshrink.json   N=655  A early, a6_1_costbasis, cm0.5, 无量能过滤, 44 只 ETF 池
  cn-B: raw/lifecycle_combo/T1_Bp_a61.json       N=101  B breakout, a6_1_costbasis, cb30/cl3%, 83 只个股池
        （稳健性副本 T1_Bp_b3.json：同参数 b3_dual 退出，只做方向对照不进判定）
  cn-C: raw/lifecycle_combo/T2_C_stocks_v3_b15.json N=177 C v3, a6_1_costbasis, bias-15% 过滤
  cn-D: raw/lifecycle_combo/T2_D_stocks_default.json N=2  D 默认（预期样本不足，只记录）
  us-A: raw/stage_b200/A_us.json                 N=96   A early, a6_1_costbasis, cm0.5, shrink 过滤, XLK/IGV/SOXX
  us-B: raw/stage_b200/B_us.json                 N=37   B breakout, a6_1_costbasis, cb20/cl10%, XLK/IGV/SOXX

选择规则（先于看结果固定）：每模块×市场取唯一可用全量逐笔归档；A 取无量能
过滤版（标注层最少），B/C 取 lifecycle 认证组合同参数版，us 侧仅 stage_b200 有逐笔。

【标注层（本脚本新算，只用信号日 T 及以前数据）】
- MACD 状态：标的自身日线 compute_features（账本 12/26/9）+ 生产读数器
  read_macd_strength(row[T], row[T-1])。分组（口径 v1.1.0：状态看 |DIF|，
  交叉是定时量）：
    扩散 = {多头扩散, 空头扩散}；收敛 = {多头收敛, 空头收敛}；
    交叉日 = {金叉, 死叉, 上穿0轴, 下穿0轴}（不进二元对比，单列计数）。
  次级标注：排列方向（DIF>0 多头 / DIF<0 空头），仅描述不判定。
- 牛熊：逐笔自带 benchmark_clock_type（原运行口径：cn=000300.SS、us=^GSPC
  时钟）。映射沿用 run_regime_gate.py：牛={1,2} 横={3} 熊={4,5}。
- 宽度：市场宽度 b200 于信号日 T 的值（cn=cache/timing/breadth_cn_all，
  us=breadth_sp500）。三分区 低≤30 / 中30–70 / 高≥70（对齐冠军三档边界
  30/70）。b50 同分区作次级判定维度（与 b200 高相关，视为近复制检验而非
  独立假设；多重检验风险由阴性对照的打乱基线统一约束）。

【结果变量】主 = r_net（引擎原模拟净 R）；次 = fwd20 = 入场日后第 20 根
收盘/入场价−1（退出无关稳健性对照；数据不足记 NaN 剔除并计数）。
排除：exit_reason ∈ {skipped_limit_up_at_entry, signal_at_end_not_entered}
（未真正入场）；r_net 为 None 的未平仓单不进 r_net 统计。

【单元格局级判定】格 = (市场, 模块, 维度, 层)。格内对比 扩散 vs 收敛 的
r_net：N/均值/中位数/胜率(R>0)/Mann-Whitney 双侧 p/置换 p(1000 次组内标签
重排，rng=20260901)。
  「格成立」= N_扩散≥20 且 N_收敛≥20 且 置换 p<0.05。
  N<20 任一侧 → 标「样本不足，仅供参考」，不进任何判定。

【模块×维度级判定】「MACD 分层有信息量(该模块×该维度)」=
  ≥1 格成立 且 其余所有 N≥20 双侧格的 (扩散均值−收敛均值) 与成立格同号。
  若无格成立但存在 N≥20 格 → 判「无差异」。符号互斥 → 判「方向不一致，
  不构成可用分层规则」。

【阴性对照（必须通过才算整体有效）】在 (市场,模块) 内保持三层标签计数
不变随机打乱 MACD 分组标签 200 次（rng=20260901+rep），每次重算全部格的
「成立」数。真实成立格数必须 > 打乱分布 95 分位，否则整体判
「不高于随机噪音基线」。

【冲突检查（先验写死）】
  a. 牛熊主效应（忽略 MACD）：牛 vs 熊格 r_net 均值差 + 置换 p。若主效应
     显著而 MACD 格内全部不成立 → 判「分层无增量，与 regime/仓位门判负
     机制（trd-gate）信息重复」。MACD 格内成立 → 提供主效应之外的细粒度，
     仍需阴性对照通过。
  b. 宽度主效应（忽略 MACD）：低区 vs 高区均值差。若只是重现「宽度低位
     信号更好」且 MACD 格内无差异 → 判「与 kuandu-quanzhan 宽度结论重复，
     MACD 无增量」。
  c. 资产交互：同模块 cn vs us 的 (扩散−收敛) 差值符号相反、或一侧 N≥20
     成立而另一侧 N≥20 不成立 → 报「分层适用范围划界」，禁止泛化。

【fwd20 分歧披露】fwd20 方向与 r_net 主结论冲突时以 r_net（系统口径）为
主，如实披露。

【双跑】PYTHONHASHSEED=0/42 各跑一次，records/analysis 两 JSON 的 sha256
必须一致，写入 HASH_MANIFEST.txt。

明确不做：不产生买卖点；不改 macd_strength.py；不接入仓位系数；不把 MACD
单独当触发；不测周线 MACD；不调参。
═══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from lei_signal.data.cache import ParquetCache  # noqa: E402
from lei_signal.features.indicators import compute_features  # noqa: E402
from lei_signal.rules.lei_color import classify_colors  # noqa: E402
from lei_signal.rules.macd_strength import read_macd_strength  # noqa: E402

RAW = REPO / "docs/experiments/raw"
OUT_DIR = RAW / "macd-strength-layering"
OUT_DIR.mkdir(parents=True, exist_ok=True)

#: 与 backtest.runner.load_pool_frames 同一实现（≥300 根才入池）。
#: 不直接 import runner：其模块级 import 坏引擎（见 docstring 声明），
#: 而本脚本只需要特征列（macd_dif/dea/hist 等），不需要引擎本身。
POOL_ROOT = Path.home() / ".lei_signal_lab" / "backtest_pool"


def load_pool_frames_local() -> dict[str, pd.DataFrame]:
    cache = ParquetCache(str(POOL_ROOT))
    frames: dict[str, pd.DataFrame] = {}
    for path in sorted(POOL_ROOT.glob("*.bars.parquet")):
        symbol = path.name[: -len(".bars.parquet")]
        bars = cache.read(symbol)
        if bars is None or len(bars) < 300:
            continue
        frames[symbol] = classify_colors(compute_features(bars))
    return frames

TIMING = Path.home() / ".lei_signal_lab/cache/timing"

#: 预注册运行清单：(市场, 模块, 角色, 相对路径)
RUNS: tuple[tuple[str, str, str, str], ...] = (
    ("cn", "A", "primary", "breadth_overlay/wf_a_noshrink.json"),
    ("cn", "B", "primary", "lifecycle_combo/T1_Bp_a61.json"),
    ("cn", "B", "robust_b3", "lifecycle_combo/T1_Bp_b3.json"),
    ("cn", "C", "primary", "lifecycle_combo/T2_C_stocks_v3_b15.json"),
    ("cn", "D", "primary", "lifecycle_combo/T2_D_stocks_default.json"),
    ("us", "A", "primary", "stage_b200/A_us.json"),
    ("us", "B", "primary", "stage_b200/B_us.json"),
)

EXCLUDED_EXIT_REASONS = {"skipped_limit_up_at_entry", "signal_at_end_not_entered"}
MIN_N = 20
PERM_SEED = 20260901
N_PERM = 1000
N_SHUFFLE = 200

REGIME_MAP = {1: "牛", 2: "牛", 3: "横", 4: "熊", 5: "熊", 0: "无基准"}
EXPAND_STATUS = {"多头扩散", "空头扩散"}
CONTRACT_STATUS = {"多头收敛", "空头收敛"}
CROSS_STATUS = {"金叉", "死叉", "上穿0轴", "下穿0轴"}

BREADTH_FILE = {"cn": TIMING / "breadth_cn_all.parquet", "us": TIMING / "breadth_sp500.parquet"}


def zone(v: float) -> str:
    if v <= 30.0:
        return "低"
    if v >= 70.0:
        return "高"
    return "中"


def stable_seed(*parts: object) -> int:
    """跨 PYTHONHASHSEED 稳定的种子（md5 派生，双跑一致性前提）。"""
    h = hashlib.md5(".".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:8], 16)


def perm_p(a: np.ndarray, b: np.ndarray, seed: int) -> float:
    """两组均值差双侧置换检验（组内标签重排）。"""
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    rng = np.random.default_rng(seed)
    obs = abs(float(a.mean()) - float(b.mean()))
    pool = np.concatenate([a, b])
    n_a = len(a)
    cnt = 0
    for _ in range(N_PERM):
        idx = rng.permutation(len(pool))
        d = abs(float(pool[idx[:n_a]].mean()) - float(pool[idx[n_a:]].mean()))
        if d >= obs - 1e-12:
            cnt += 1
    return (cnt + 1) / (N_PERM + 1)


def perm_p_safe(a: np.ndarray, b: np.ndarray, seed: int) -> float | None:
    if len(a) < 2 or len(b) < 2:
        return None
    return perm_p(a, b, seed)


def cell_stats(vals_e: list[float], vals_c: list[float], seed: int) -> dict:
    a, b = np.array(vals_e, dtype=float), np.array(vals_c, dtype=float)
    out: dict = {
        "N_扩散": int(a.size),
        "N_收敛": int(b.size),
        "mean_扩散": round(float(a.mean()), 4) if a.size else None,
        "mean_收敛": round(float(b.mean()), 4) if b.size else None,
        "median_扩散": round(float(np.median(a)), 4) if a.size else None,
        "median_收敛": round(float(np.median(b)), 4) if b.size else None,
        "winrate_扩散": round(float((a > 0).mean()), 4) if a.size else None,
        "winrate_收敛": round(float((b > 0).mean()), 4) if b.size else None,
        "mean_diff_扩散减收敛": round(float(a.mean()) - float(b.mean()), 4)
        if a.size and b.size
        else None,
    }
    if a.size and b.size:
        out["mw_p"] = round(float(mannwhitneyu(a, b, alternative="two-sided").pvalue), 5)
        pp = perm_p_safe(a, b, seed)
        out["perm_p"] = round(pp, 4) if pp is not None else None
        out["格成立"] = bool(a.size >= MIN_N and b.size >= MIN_N and pp is not None and pp < 0.05)
        out["样本充分"] = bool(a.size >= MIN_N and b.size >= MIN_N)
    else:
        out["mw_p"] = None
        out["perm_p"] = None
        out["格成立"] = False
        out["样本充分"] = False
    return out


def group_label(status: str | None) -> str:
    if status is None:
        return "数据不足"
    if status in EXPAND_STATUS:
        return "扩散"
    if status in CONTRACT_STATUS:
        return "收敛"
    if status in CROSS_STATUS:
        return "交叉日"
    return "数据不足"


def main() -> None:
    frames = load_pool_frames_local()
    breadth: dict[str, pd.DataFrame] = {
        m: pd.read_parquet(p)[["b50", "b200"]] for m, p in BREADTH_FILE.items()
    }
    bday = {m: {ts.date(): i for i, ts in enumerate(df.index)} for m, df in breadth.items()}

    records: list[dict] = []
    run_meta: dict[str, dict] = {}
    for market, module, role, rel in RUNS:
        run = json.loads((RAW / rel).read_text(encoding="utf-8"))
        trades = run.get("trades", [])
        n_all = len(trades)
        n_excluded = 0
        n_no_frame = 0
        n_no_day = 0
        n_no_breadth = 0
        for t in sorted(trades, key=lambda x: (x["symbol"], x["signal_date"], x["entry_date"])):
            if t.get("exit_reason") in EXCLUDED_EXIT_REASONS:
                n_excluded += 1
                continue
            sym = t["symbol"]
            frame = frames.get(sym)
            if frame is None:
                n_no_frame += 1
                continue
            day = date.fromisoformat(t["signal_date"])
            idx = {ts.date(): i for i, ts in enumerate(frame.index)}
            pos = idx.get(day)
            if pos is None or pos < 1:
                n_no_day += 1
                continue
            reading = read_macd_strength(frame.iloc[pos], frame.iloc[pos - 1])
            status = reading.status if reading else None
            g = group_label(status)
            # 宽度标注（信号日 T 当日值，收盘可得）
            bi = bday[market].get(day)
            if bi is None or not pd.notna(breadth[market]["b200"].iloc[bi]):
                n_no_breadth += 1
                b200z = b50z = None
                b200 = b50 = None
            else:
                b200 = float(breadth[market]["b200"].iloc[bi])
                b50 = float(breadth[market]["b50"].iloc[bi])
                b200z, b50z = zone(b200), zone(b50)
            # fwd20：入场日后第 20 根收盘 / 入场价
            entry_day = date.fromisoformat(t["entry_date"])
            epos = idx.get(entry_day)
            fwd20 = None
            if epos is not None and epos + 20 < len(frame):
                fwd20 = round(float(frame["close"].iloc[epos + 20]) / float(t["entry_price"]) - 1.0, 6)
            records.append(
                {
                    "market": market,
                    "module": module,
                    "role": role,
                    "symbol": sym,
                    "signal_date": t["signal_date"],
                    "entry_date": t["entry_date"],
                    "benchmark_clock_type": int(t.get("benchmark_clock_type", 0)),
                    "regime": REGIME_MAP.get(int(t.get("benchmark_clock_type", 0)), "无基准"),
                    "macd_status": status,
                    "macd_group": g,
                    "macd_alignment": ("多头" if reading.dif > 0 else "空头") if reading else None,
                    "b200": round(b200, 3) if b200 is not None else None,
                    "b50": round(b50, 3) if b50 is not None else None,
                    "b200zone": b200z,
                    "b50zone": b50z,
                    "r_net": t.get("r_net"),
                    "fwd20": fwd20,
                    "exit_reason": t.get("exit_reason"),
                }
            )
        run_meta[f"{market}-{module}-{role}"] = {
            "file": rel,
            "trades_total": n_all,
            "excluded_not_entered": n_excluded,
            "no_frame": n_no_frame,
            "no_signal_day": n_no_day,
            "no_breadth_day": n_no_breadth,
        }

    records.sort(key=lambda r: (r["market"], r["module"], r["role"], r["symbol"], r["signal_date"]))

    # ── 主分析：primary 角色的 r_net 分层 ──────────────────────────
    prim = [r for r in records if r["role"] == "primary" and r["r_net"] is not None]
    dims = {"regime": "regime", "b200zone": "b200zone", "b50zone": "b50zone"}
    cells: dict[str, dict] = {d: {} for d in dims}
    for dim_key, rec_col in dims.items():
        for market in ("cn", "us"):
            for module in ("A", "B", "C", "D"):
                sub = [r for r in prim if r["market"] == market and r["module"] == module]
                for layer in sorted({r[rec_col] for r in sub if r[rec_col] is not None}):
                    ve = [
                        r["r_net"]
                        for r in sub
                        if r[rec_col] == layer and r["macd_group"] == "扩散"
                    ]
                    vc = [
                        r["r_net"]
                        for r in sub
                        if r[rec_col] == layer and r["macd_group"] == "收敛"
                    ]
                    seed = PERM_SEED + stable_seed(market, module, dim_key, layer) % 100000
                    cells[dim_key][f"{market}.{module}.{layer}"] = cell_stats(ve, vc, seed)

    # 模块×维度判定
    verdicts: dict[str, dict] = {}
    for dim_key in dims:
        for market in ("cn", "us"):
            for module in ("A", "B", "C", "D"):
                md = {k: v for k, v in cells[dim_key].items() if k.startswith(f"{market}.{module}.")}
                if not md:
                    continue
                est = [k for k, v in md.items() if v["格成立"]]
                full = [k for k, v in md.items() if v["样本充分"]]
                diffs = [v["mean_diff_扩散减收敛"] for v in md.values() if v["样本充分"]]
                if not est:
                    verdict = "无差异" if full else "样本不足"
                elif diffs and all((d > 0) == (diffs[0] > 0) for d in diffs):
                    verdict = "MACD分层有信息量"
                else:
                    verdict = "方向不一致"
                verdicts[f"{dim_key}:{market}.{module}"] = {
                    "判定": verdict,
                    "成立格": est,
                    "充分格数": len(full),
                }

    # ── 主效应（冲突检查用）──────────────────────────────────────
    main_effects: dict[str, dict] = {}
    for label, first_set, second_set in (
        ("牛熊主效应_牛减熊", {"牛"}, {"熊"}),
        ("宽度b200主效应_低减高", {"低"}, {"高"}),
    ):
        col = "regime" if label.startswith("牛熊") else "b200zone"
        for market in ("cn", "us"):
            for module in ("A", "B", "C", "D"):
                sub = [
                    r
                    for r in prim
                    if r["market"] == market
                    and r["module"] == module
                    and r[col] in (first_set | second_set)
                ]
                ga = np.array([r["r_net"] for r in sub if r[col] in first_set], dtype=float)
                gb = np.array([r["r_net"] for r in sub if r[col] in second_set], dtype=float)
                if ga.size and gb.size:
                    main_effects[f"{label}:{market}.{module}"] = {
                        "N_第一组": int(ga.size),
                        "N_第二组": int(gb.size),
                        "mean_diff": round(float(ga.mean()) - float(gb.mean()), 4),
                        "perm_p": round(perm_p_safe(ga, gb, PERM_SEED + 7), 4),
                    }

    # ── 阴性对照：MACD 标签打乱 200 次 ───────────────────────────
    groups_by_mm: dict[tuple[str, str], list[str]] = {}
    for r in prim:
        groups_by_mm.setdefault((r["market"], r["module"]), []).append(r["macd_group"])

    def count_established(assign: dict[tuple[str, str], list[str]]) -> int:
        """打乱标签后重算全部分析格的「成立」数（与真实口径一致的近似：置换种子固定）。"""
        n = 0
        for dim_key, rec_col in dims.items():
            for market in ("cn", "us"):
                for module in ("A", "B", "C", "D"):
                    sub_idx = [
                        i
                        for i, r in enumerate(prim)
                        if r["market"] == market and r["module"] == module
                    ]
                    if not sub_idx:
                        continue
                    labels_local = assign[(market, module)]
                    lay: dict[str, tuple[list[float], list[float]]] = {}
                    for local_i, i in enumerate(sub_idx):
                        z = prim[i][rec_col]
                        if z is None:
                            continue
                        g = labels_local[local_i]
                        ve, vc = lay.setdefault(z, ([], []))
                        if g == "扩散":
                            ve.append(prim[i]["r_net"])
                        elif g == "收敛":
                            vc.append(prim[i]["r_net"])
                    for z, (ve, vc) in lay.items():
                        if len(ve) >= MIN_N and len(vc) >= MIN_N:
                            p = perm_p(np.array(ve), np.array(vc), 12345)
                            if p < 0.05:
                                n += 1
        return n

    real_est = sum(1 for d in cells.values() for v in d.values() if v["格成立"])
    shuffle_counts: list[int] = []
    mm_keys = sorted(groups_by_mm)
    for rep in range(N_SHUFFLE):
        rng = np.random.default_rng(PERM_SEED + rep)
        assign: dict[tuple[str, str], list[str]] = {}
        for mm in mm_keys:
            labels = list(groups_by_mm[mm])
            rng.shuffle(labels)
            assign[mm] = labels
        shuffle_counts.append(count_established(assign))
    shuffle_p95 = float(np.percentile(shuffle_counts, 95)) if shuffle_counts else None
    negative_control = {
        "真实成立格数": real_est,
        "打乱200次成立格数_95分位": shuffle_p95,
        "打乱分布_均值": round(float(np.mean(shuffle_counts)), 2),
        "打乱分布_最大": int(max(shuffle_counts)) if shuffle_counts else None,
        "整体判负_不高于随机基线": bool(shuffle_p95 is not None and real_est <= shuffle_p95),
        "分析格总数": sum(len(d) for d in cells.values()),
    }

    # ── fwd20 稳健性对照（描述性）────────────────────────────────
    fwd_check: dict[str, dict] = {}
    for market in ("cn", "us"):
        for module in ("A", "B", "C", "D"):
            sub = [
                r
                for r in records
                if r["role"] == "primary"
                and r["market"] == market
                and r["module"] == module
                and r["fwd20"] is not None
            ]
            ve = [r["fwd20"] for r in sub if r["macd_group"] == "扩散"]
            vc = [r["fwd20"] for r in sub if r["macd_group"] == "收敛"]
            if ve and vc:
                fwd_check[f"{market}.{module}"] = {
                    "N_扩散": len(ve),
                    "N_收敛": len(vc),
                    "mean_fwd20_扩散": round(float(np.mean(ve)), 5),
                    "mean_fwd20_收敛": round(float(np.mean(vc)), 5),
                    "diff": round(float(np.mean(ve)) - float(np.mean(vc)), 5),
                }

    # ── 资产交互（cn vs us 同模块）───────────────────────────────
    asset_interaction: dict[str, dict] = {}
    for module in ("A", "B", "C", "D"):
        row: dict = {}
        for market in ("cn", "us"):
            ve = [r["r_net"] for r in prim if r["market"] == market and r["module"] == module and r["macd_group"] == "扩散"]
            vc = [r["r_net"] for r in prim if r["market"] == market and r["module"] == module and r["macd_group"] == "收敛"]
            if ve and vc:
                row[market] = {
                    "diff": round(float(np.mean(ve)) - float(np.mean(vc)), 4),
                    "N_扩散": len(ve),
                    "N_收敛": len(vc),
                }
        if "cn" in row and "us" in row:
            row["符号相反"] = bool((row["cn"]["diff"] > 0) != (row["us"]["diff"] > 0))
        asset_interaction[module] = row

    # ── MACD 状态分布 / 交叉日计数 ────────────────────────────────
    status_dist: dict[str, dict[str, int]] = {}
    for r in prim:
        k = f"{r['market']}.{r['module']}"
        d = status_dist.setdefault(k, {})
        d[r["macd_status"] or "数据不足"] = d.get(r["macd_status"] or "数据不足", 0) + 1

    # 指数标的抽查（描述性）
    spot: dict[str, dict] = {}
    for r in prim:
        if r["symbol"] in ("000300.SS", "399006.SZ", "510300.SS", "159915.SZ", "^GSPC", "XLK"):
            k = f"{r['symbol']}.{r['market']}.{r['module']}"
            d = spot.setdefault(k, {"N": 0, "R合计": 0.0})
            d["N"] += 1
            d["R合计"] = round(d["R合计"] + (r["r_net"] or 0.0), 3)

    # ── B 的 b3_dual 稳健性副本（方向对照）────────────────────────
    robust_b3: dict[str, dict] = {}
    sub_b3 = [r for r in records if r["role"] == "robust_b3" and r["r_net"] is not None]
    for market in ("cn",):
        ve = [r["r_net"] for r in sub_b3 if r["macd_group"] == "扩散"]
        vc = [r["r_net"] for r in sub_b3 if r["macd_group"] == "收敛"]
        if ve and vc:
            robust_b3[f"{market}.B.b3"] = {
                "N_扩散": len(ve),
                "N_收敛": len(vc),
                "diff": round(float(np.mean(ve)) - float(np.mean(vc)), 4),
            }

    analysis = {
        "date": "2026-09-01",
        "criteria_note": "预注册判定标准见脚本 docstring（跑前写死）",
        "run_meta": run_meta,
        "primary_signals_used": len(prim),
        "macd_status_distribution": status_dist,
        "cells": cells,
        "module_dim_verdicts": verdicts,
        "main_effects": main_effects,
        "negative_control": negative_control,
        "fwd20_check": fwd_check,
        "asset_interaction": asset_interaction,
        "index_spot_check": spot,
        "robust_b3_exit": robust_b3,
    }

    rec_fp = OUT_DIR / "records_macd_layering.json"
    ana_fp = OUT_DIR / "analysis_macd_layering.json"
    rec_fp.write_text(
        json.dumps(records, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
    )
    ana_fp.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
    )

    seed = os.environ.get("PYTHONHASHSEED", "unset")
    hashes = {
        "PYTHONHASHSEED": seed,
        "records_sha256": hashlib.sha256(rec_fp.read_bytes()).hexdigest(),
        "analysis_sha256": hashlib.sha256(ana_fp.read_bytes()).hexdigest(),
    }
    with (OUT_DIR / "HASH_MANIFEST.txt").open("a", encoding="utf-8") as f:
        f.write(json.dumps(hashes, sort_keys=True) + "\n")

    print(json.dumps({"negative_control": negative_control, "hashes": hashes}, ensure_ascii=False, indent=1))
    print("\n== 模块×维度判定 ==")
    for k in sorted(verdicts):
        print(k, verdicts[k]["判定"], "成立格:", verdicts[k]["成立格"])
    print("\n== 格明细（样本充分的格）==")
    for dim_key in dims:
        for k in sorted(cells[dim_key]):
            v = cells[dim_key][k]
            if v["样本充分"] or v["格成立"]:
                print(dim_key, k, "diff=", v["mean_diff_扩散减收敛"], "perm_p=", v["perm_p"], "N=", v["N_扩散"], v["N_收敛"], "成立" if v["格成立"] else "")
    print("\n== 主效应 ==")
    for k in sorted(main_effects):
        print(k, main_effects[k])
    print("\n== 资产交互 ==")
    for k in sorted(asset_interaction):
        print(k, asset_interaction[k])


if __name__ == "__main__":
    main()
