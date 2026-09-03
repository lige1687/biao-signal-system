# -*- coding: utf-8 -*-
"""Prompt AF：语义四 P1（创业板专属宽度三档 × 全A宽度三档）增量信息检验。

==============================================================================
预注册协议（本 docstring 在任何统计运行之前写死冻结，跑后不得修改任何
判定线；本文件为新增文件，不改 src/ 与任何既有归档）
==============================================================================

一、信号重建（完全复用 AB 口径，不发明新口径）

  两条宽度序列与档位线与 scripts/agent_AB/run_multi_confirm_frequency.py
  逐字相同（其本身引用 kuandu-quanzhan-ARCHIVE 冠军三档 + service.py
  EXEC_CONFIGS）：
    - 全A：~/.lei_signal_lab/cache/timing/breadth_cn_all.parquet 的 b200
    - 创业板专属：同目录 breadth_cyb.parquet 的 b200
    - 有效性：b200 非 NaN 且 n200 ≥ 50（AB 同款）
    - 档位线：30+40/3 ≈ 43.33 与 30+80/3 ≈ 56.67（gamma=1.0 三档逆势）
  每个交易日给每条序列一个档位序数 tier ∈ {0,1,2}（searchsorted right）。

二、前瞻收益（forward returns）标的价格（跑前冻结）

  全A腿用中证800指数 000932（cache/timing/000932.parquet close，
  2009-07 起全覆盖重叠窗）——理由：缓存中无中证全指(000985)，中证800
  覆盖约八成五市值，是可得的最接近"全A"的价格代理；创业板腿用创业板指
  399006（cache/timing/399006.parquet close）。
  收益口径：信号日收盘 → h 个交易日后收盘（h ∈ {20, 60, 120}，跑前
  冻结三档）。信号日用收盘价，决策不使用当日盘中信息，无前视。

三、四态分类（跑前冻结）

  仅当两条序列当日都处于非中间档（tier∈{0,2}）时分类，否则记"中间态"
  不进检验：
    同多   tier_cyb=0 且 tier_all=0 （B200 双双低于下档线 = 逆势加仓侧）
    同空   tier_cyb=2 且 tier_all=2 （双双高于上档线 = 逆势减仓侧）
    分歧M  tier_cyb=0 且 tier_all=2 （创业板专属多 · 全A空）
    分歧S  tier_cyb=2 且 tier_all=0 （创业板专属空 · 全A多）

四、主检验样本单位：episode 起点（跑前冻结，防重叠样本虚增显著性）

  日度状态高度自相关（连续多日同态），且前瞻窗口重叠会虚增显著性。
  因此主检验样本单位 = **episode 起点**：每个四态的最大连续段的第一天。
  日度天数只作描述登记（daily_n），不进判定。
  对照组（同多 / 同空）同样取 episode 起点。

五、"增量存在"的判定线（跑前写死）

  核心问题：分歧日市场随后往哪走？若分歧态的前瞻收益显著偏向其中
  一条信号所指的方向（而不仅仅跟随另一条），则分歧携带增量信息。

  定义两个对比（对照 = 全A信号所指方向的同向态）：
    ΔM = mean(分歧M 前瞻收益) − mean(同空 前瞻收益)
      （若创业板宽度有独立信息，分歧M 的市场表现应比"同空"更好，ΔM>0）
    ΔS = mean(分歧S 前瞻收益) − mean(同多 前瞻收益)
      （ΔS<0 表示分歧S 比"同多"更差，创业板信息又对了一次）

  判"增量存在"（PASS）需同时满足：
    (a) 样本：分歧M 与 分歧S 的 episode 数各 ≥ 20（对齐 N 任务"n≥20
        才有方差可检验"下限，也是 AB 报告的同一经验线）；
    (b) 显著性：两个对比（ΔM、ΔS）在 h∈{20,60,120} 三档中至少两档
        |Welch t| ≥ 2 且方向正确（ΔM>0、ΔS<0）；
    (c) 幅度：|Δ| 在 h=60 档 ≥ 1 个百分点；
    (d) 稳定性：把 episode 按时间对半分成前后两半（2012-2019 /
        2020-2026），两个对比在 h=60 档的前后两半符号一致且与全样本
        同号。
  判"无增量"（FAIL）：(a) 满足但 (b)(c)(d) 任一不满足——两态是同一
    信息的两遍复述（或分歧信息不可检出）。
  判"证据不足"（WATCH）：(a) 不满足（任一分歧态 episode < 20）——
    同时报告"需要多少年样本"的粗估（按当前分歧态年发生率外推）。

  简单显著性方法：Welch 双样本 t（不等方差），不做多重比较校正，
  但登记比较总数 = 2 对比 × 3 视野 = 6 次，阈值 2 对应单次约 p≈0.05，
  多重比较风险在报告局限一节如实声明。

六、附带登记（不作判定依据，只登记）

  分歧 episode 后，399006 与 000932 各自的前瞻收益对比（哪条宽度的
  "标的"跟随自己的信号走）。

七、稳健性（跑前冻结）

  - 分半（前半/后半）符号一致性已进判定线 (d)；
  - 另登记 3 年滚动窗内分歧态 episode 年分布与集中度（若分歧挤在
    个别年份，如实呈现 top3yr 集中度）；
  - 敏感性（仅描述）：把样本单位换成"每 20 个交易日最多抽 1 个分歧
    日"的稀疏采样，方向是否不变。

八、红线
  纯统计，不设计仓位规则、不做参数网格、不使用买卖指令词汇。
  双跑：PYTHONHASHSEED=0 / =42 各完整跑一遍，canonical JSON 的
  sha256 必须一致。
==============================================================================
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
CACHE = Path.home() / ".lei_signal_lab/cache/timing"
OUT_JSON = REPO / "scripts/agent_AF/results_p1_increment.json"

# ---------------- 预注册常量（与 docstring 一致，冻结） ----------------
LADDER_EDGES = [30 + 40 * 1 / 3, 30 + 40 * 2 / 3]  # 43.33 / 56.67
MIN_STOCKS = 50
HORIZONS = [20, 60, 120]
LEG_ALL = "000932"   # 中证800，全A价格代理（跑前冻结）
LEG_CYB = "399006"   # 创业板指
PASS_N_EP = 20       # 每个分歧态 episode 下限
T_THRESHOLD = 2.0    # |Welch t| 阈值
MIN_EFFECT_60D = 0.01  # h=60 幅度 ≥1pp
SPLIT_YEAR = 2020    # 前后半分界（2012-2019 vs 2020-2026）


def tier_series(breadth_name: str) -> pd.Series:
    df = pd.read_parquet(CACHE / f"{breadth_name}.parquet")
    ok = df["b200"].notna() & (df["n200"] >= MIN_STOCKS)
    b = df.loc[ok, "b200"].sort_index()
    return pd.Series(
        np.searchsorted(np.array(LADDER_EDGES), b.to_numpy(float), side="right"),
        index=b.index,
    )


def classify(t_cyb: pd.Series, t_all: pd.Series) -> pd.Series:
    """四态 + 中间态，索引为共同交易日。"""
    idx = t_cyb.index.intersection(t_all.index)
    c = t_cyb.reindex(idx)
    a = t_all.reindex(idx)

    def st(cy, al):
        if cy == 0 and al == 0:
            return "同多"
        if cy == 2 and al == 2:
            return "同空"
        if cy == 0 and al == 2:
            return "分歧M"  # 创业板多 · 全A空
        if cy == 2 and al == 0:
            return "分歧S"  # 创业板空 · 全A多
        return "中间"

    return pd.Series([st(x, y) for x, y in zip(c.values, a.values)], index=idx)


def episode_onsets(state: pd.Series) -> pd.Series:
    """每个最大连续同态段的第一天。返回 date -> state。"""
    same = state != state.shift(1)
    return state[same]


def fwd_returns(close: pd.Series, dates: pd.DatetimeIndex, h: int) -> np.ndarray:
    """信号日收盘 → h 交易日后收盘；末尾不足 h 日记 NaN。"""
    pos = close.index.get_indexer(dates)
    out = np.full(len(dates), np.nan)
    for i, p in enumerate(pos):
        if p >= 0 and p + h < len(close):
            out[i] = close.iloc[p + h] / close.iloc[p] - 1.0
    return out


def welch(a: np.ndarray, b: np.ndarray) -> tuple:
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    if len(a) < 2 or len(b) < 2:
        return (float("nan"), float("nan"), len(a), len(b))
    ma, mb = a.mean(), b.mean()
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = np.sqrt(va / len(a) + vb / len(b))
    t = (ma - mb) / se if se > 0 else float("nan")
    return (t, ma - mb, len(a), len(b))


def main() -> int:
    t_all = tier_series("breadth_cn_all")
    t_cyb = tier_series("breadth_cyb")
    state = classify(t_cyb, t_all)

    close_all = pd.read_parquet(CACHE / f"{LEG_ALL}.parquet")["close"].sort_index()
    close_cyb = pd.read_parquet(CACHE / f"{LEG_CYB}.parquet")["close"].sort_index()

    # 前瞻收益矩阵：行=全部分类日，列=h；对两条腿各一份
    dates = state.index
    rets_all = {h: pd.Series(fwd_returns(close_all, dates, h), index=dates) for h in HORIZONS}
    rets_cyb = {h: pd.Series(fwd_returns(close_cyb, dates, h), index=dates) for h in HORIZONS}

    onsets = episode_onsets(state)
    onset_dates = onsets.index

    # ---- 四态样本量（日度 + episode）----
    daily_n = state.value_counts().to_dict()
    ep_n = onsets.value_counts().to_dict()

    # ---- 主对比（episode 起点，全A腿前瞻收益）----
    def contrast(div: str, same: str, sign: float, sub: pd.Series) -> dict:
        d = sub[sub == div].index
        s = sub[sub == same].index
        o = {"n_div": int(len(d)), "n_same": int(len(s))}
        for h in HORIZONS:
            if len(d) >= 2 and len(s) >= 2:
                t, delta, _, _ = welch(rets_all[h][d].to_numpy(), rets_all[h][s].to_numpy())
                o[f"h{h}"] = {
                    "delta": round(float(delta), 5),
                    "mean_div": round(float(np.nanmean(rets_all[h][d])), 5),
                    "mean_same": round(float(np.nanmean(rets_all[h][s])), 5),
                    "t": round(float(t), 3),
                    "sign_ok": bool(np.sign(delta) == sign and abs(t) >= T_THRESHOLD),
                }
            else:
                o[f"h{h}"] = None
        return o

    # 剔除前瞻收益末尾不足 h=120 的天对样本的影响：welch 已自动丢 NaN
    full = contrast("分歧M", "同空", +1, onsets)
    full_S = contrast("分歧S", "同多", -1, onsets)

    # ---- 分半稳定性（h=60）----
    early = onsets[onsets.index.year < SPLIT_YEAR]
    late = onsets[onsets.index.year >= SPLIT_YEAR]

    def half_delta(sub: pd.Series, div: str, same: str) -> float | None:
        d = sub[sub == div].index
        s = sub[sub == same].index
        if len(d) < 2 or len(s) < 2:
            return None
        _, delta, _, _ = welch(rets_all[60][d].to_numpy(), rets_all[60][s].to_numpy())
        return None if np.isnan(delta) else float(delta)

    halves = {
        "early_delta_M": half_delta(early, "分歧M", "同空"),
        "late_delta_M": half_delta(late, "分歧M", "同空"),
        "early_delta_S": half_delta(early, "分歧S", "同多"),
        "late_delta_S": half_delta(late, "分歧S", "同多"),
    }

    # ---- 3 年滚动窗 / 年集中度（分歧态）----
    div_years = {}
    for div in ("分歧M", "分歧S"):
        ys = onsets[onsets == div].index.year
        yc = ys.value_counts().sort_index()
        div_years[div] = {
            "per_year": {int(k): int(v) for k, v in yc.items()},
            "top3yr_share": round(float(yc.sort_values(ascending=False).head(3).sum() / yc.sum()), 4) if len(yc) else None,
            "n_years": int(len(yc)),
        }

    # ---- 附带登记：分歧 episode 后两腿各自前瞻收益（哪条更"对"）----
    ancillary = {}
    for div, leg_same in (("分歧M", "全A"), ("分歧S", "创业板")):
        d = onsets[onsets == div].index
        ancillary[div] = {
            "fwd_cyb_" + ("correct" if div == "分歧M" else "wrong_side") + "_h60": round(float(np.nanmean(rets_cyb[60][d])), 5),
            "fwd_all_" + ("correct" if div == "分歧S" else "wrong_side") + "_h60": round(float(np.nanmean(rets_all[60][d])), 5),
            "n": int(len(d)),
        }

    # ---- 敏感性（仅描述）：稀疏采样，每 20 交易日最多 1 个分歧日 ----
    sparse = {}
    for div, same, sign in (("分歧M", "同空", +1), ("分歧S", "同多", -1)):
        dd = onsets[onsets == div].index
        keep, last = [], None
        for d in dd:
            if last is None or (d - last).days >= 20:
                keep.append(d)
                last = d
        s = onsets[onsets == same].index
        if len(keep) >= 2 and len(s) >= 2:
            _, delta, _, _ = welch(rets_all[60][keep], rets_all[60][s])
            sparse[div] = {"n": len(keep), "delta_h60": None if np.isnan(delta) else round(float(delta), 5)}
        else:
            sparse[div] = {"n": len(keep), "delta_h60": None}

    # ---- 判定（预注册线执行）----
    n_M, n_S = ep_n.get("分歧M", 0), ep_n.get("分歧S", 0)
    if n_M < PASS_N_EP or n_S < PASS_N_EP:
        verdict = "WATCH_证据不足"
        # 粗估还需多少年（按分歧态年发生率）
        need = {}
        for div, n in (("分歧M", n_M), ("分歧S", n_S)):
            per_year = div_years[div]["per_year"]
            avg = np.mean(list(per_year.values())) if per_year else 0
            need[div] = {
                "have": n, "avg_per_year": round(float(avg), 2),
                "years_needed_extra": None if avg <= 0 else round((PASS_N_EP - n) / avg, 1),
            }
    else:
        verdict = "WATCH_证据不足"
        cond_b = all(
            sum(1 for h in HORIZONS if full[f"h{h}"] and full[f"h{h}"]["sign_ok"]) >= 2
            and sum(1 for h in HORIZONS if full_S[f"h{h}"] and full_S[f"h{h}"]["sign_ok"]) >= 2
            for _ in [0]
        )
        d60 = full["h60"]
        cond_c = d60 is not None and abs(d60["delta"]) >= MIN_EFFECT_60D and (
            full_S["h60"] is not None and abs(full_S["h60"]["delta"]) >= MIN_EFFECT_60D
        )
        cond_d = all(
            v is not None and np.sign(v) == sgn
            for v, sgn in (
                (halves["early_delta_M"], 1), (halves["late_delta_M"], 1),
                (halves["early_delta_S"], -1), (halves["late_delta_S"], -1),
            )
        )
        if cond_b and cond_c and cond_d:
            verdict = "PASS_增量存在"
        else:
            verdict = "FAIL_无增量"

    results = {
        "window": [str(state.index.min().date()), str(state.index.max().date())],
        "legs": {"fullA_proxy": LEG_ALL, "cyb": LEG_CYB},
        "daily_state_counts": {k: int(v) for k, v in daily_n.items()},
        "episode_counts": {k: int(v) for k, v in ep_n.items()},
        "contrast_M_vs_同空": full,
        "contrast_S_vs_同多": full_S,
        "half_stability_h60": halves,
        "divergence_year_concentration": div_years,
        "ancillary_which_leg_right": ancillary,
        "sensitivity_sparse20": sparse,
        "verdict": verdict,
        "verdict_detail": locals().get("need"),
        "meta": {
            "breadth": ["breadth_cn_all", "breadth_cyb"],
            "edges": LADDER_EDGES,
            "horizons": HORIZONS,
            "preregistration": "见脚本 docstring（跑前冻结）",
            "source_script": "scripts/agent_AB/run_multi_confirm_frequency.py（口径来源）",
        },
    }

    OUT_JSON.write_text(
        json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )
    canon = json.dumps(results, ensure_ascii=False, sort_keys=True)
    print("sha256=" + hashlib.sha256(canon.encode("utf-8")).hexdigest())
    print("verdict:", verdict)
    print("daily:", daily_n)
    print("episodes:", ep_n)
    print("ΔM(分歧M-同空):", {f"h{h}": (full[f"h{h}"] or {}).get("delta") for h in HORIZONS})
    print("ΔS(分歧S-同多):", {f"h{h}": (full_S[f"h{h}"] or {}).get("delta") for h in HORIZONS})
    return 0


if __name__ == "__main__":
    sys.exit(main())
