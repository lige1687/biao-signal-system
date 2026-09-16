# -*- coding: utf-8 -*-
"""Prompt AA：语义一"主从关系"前置验证——只做事件研究，不搭主从组合回测。

预注册判定标准（2026-09-03 跑前写死，跑完不得回头改线）
=====================================================

信号规则（复用已验证规则，不发明新信号）
--------------------------------------
来源：docs/timing-sweep/execution_playbook_20260827.md（终版三轮王）
      + docs/experiments/kuandu-quanzhan-ARCHIVE-2026-09-01.md。
规则：全A宽度 B200（cn_all 口径，市场个股收盘>MA200 占比，0-100）三档逆势
      ladder：n_bands=3, contrarian, low_edge=30, high_edge=70, gamma=1.0
      → 档位线 43.333/56.667（30-70 三等分）：
        B200 < 43.333 → 目标仓位 1.0（满仓档，信号最强）
        43.333 ≤ B200 < 56.667 → 0.5（半仓档）
        B200 ≥ 56.667 → 0.0（清仓档，信号最弱）
主 = 创业板指 399006（行情缓存 2010-06-01 起）；
从 = 中证1000ETF 512100（行情缓存 2016-11-04 起）。
playbook 明文：A股进攻组（159915 主，588000/512100 可选）共用同一档位线
43.3/56.7 与同一全A B200 宽度（data.py INSTRUMENTS：两者 breadth=cn_all）。

数据预处理（预注册）
------------------
512100 存在已审计的复权断裂跳变 2022-09-05（单日 +176.3%，物理不可能为
市场事件，见 docs/experiments/data-quality-jump-audit-2026-09-02.md §2/§3）。
修平方法照抄该审计 §3：ratio = close[D]/close[D-1 交易日]，D 及之后全部
open/high/low/close 同除 ratio（跳变日收益置 0，价格向后连续化）。
399006 的历史大波动均为合法市场事件（该审计"不修"清单），不动。
共同窗口 = 两标行情日期交集。

主强弱定义（预注册，主定义）
--------------------------
主"强" = 主目标仓位 = 1.0（满仓档）；
主"弱" = 主目标仓位 < 1.0（半仓档或清仓档）。
敏感性次级定义（仅作参考展示，不用于判定线）：主"弱" = 清仓档（0.0）。

从信号事件定义（预注册）
----------------------
事件日 T = 从（512100）目标仓位相对前一交易日上升的日子（升档信号），
包括 0→0.5、0→1、0.5→1。T 日收盘出信号，入场价 = T+1 交易日开盘价，
事件后 N 日收益 = close[T+1+N] / open[T+1] - 1，N ∈ {5, 20, 60, 120}。
窗口末端不足 N 日的样本在对应 N 下剔除并如实报笔数。
按事件日主档位分组：主强组 / 主弱组。
统计：笔数、各 N 平均收益、各 N 胜率（收益>0 占比）。
对照（仅供方向论证，不进判定线）：同事件日主标的 399006 的同样收益。

主从依赖判定线（预注册：三条同时满足才判"存在"）
----------------------------------------------
(a) 主弱组事件 ≥ 10 笔；若 = 0 笔 → 依赖不可检验（同步性吞没），
    1-9 笔 → 该分支"样本不足"；
(b) 主强组 120 日平均收益 − 主弱组 120 日平均收益 ≥ 5 个百分点
    （方向：主弱时从的信号更差才支持主从门）；
(c) 差异经置换检验（事件组标签随机重排 10000 次，固定种子 12345）
    单侧 p < 0.05。声明：事件窗口可能重叠，置换检验 p 值在此场景偏乐观，
    只作辅助，(a)(b) 为主。
三条任一不满足 → 判"不存在主从依赖"（或如实记录原因）。

同步性判定线（预注册）
--------------------
- 档位一致率 = 共同窗口内主从档位（1.0/0.5/0.0 三态）相同的天数占比；
- 主弱日中从也弱的比例（主弱定义同上）；
- "主从而非同步的实际可操作时段占比" = 档位不一致天数 / 共同窗口总天数；
  < 10% 即判"门无实际操作空间"。
敏感性：严格定义（主弱=清仓档）下的同口径数字一并输出。

方向机制（第四步，无判定线，如实报告）
------------------------------------
- 若依赖不存在且可操作时段 <10%：方向问题无数据基础，如实记录；
- 补充数据：同一升档事件后两标的 120 日收益对比（谁对同一宽度信号更敏感）；
  事件日完全同日 → 拐点先后无从谈起（同源信号，同一根 B200 序列）。
- 旁证（非已验证规则，仅作机制参考，不进判定）：若改用创业板专属宽度
  breadth_cyb（该口径在 playbook 已判负：创业板超额 -0.2%）映射同一三档，
  其档位与全A口径档位的不一致率——衡量"假设换宽度，主从状态才会有差异"
  这一假设路径的空间。中证1000 专属宽度无数据（BREADTH_FILES 不含），
  如实记为数据缺口。

产出
----
- docs/experiments/raw/agent_AA/master_slave_precheck_results.json（全部数字）
- stdout 打印规范化 JSON 的 sha256（双跑 PYTHONHASHSEED=0/42 须一致）
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(REPO / "src"))

from lei_signal.timing_backtest.data import (  # noqa: E402
    TIMING_CACHE_DIR,
    load_breadth,
    load_index_bars,
)
from lei_signal.timing_backtest.strategies import LadderParams, ladder_target  # noqa: E402

# ---------------- 预注册参数（写死） ----------------
LADDER = LadderParams(
    indicator="b200", n_bands=3, direction="contrarian",
    low_edge=30.0, high_edge=70.0, gamma=1.0,
)
MASTER, SLAVE = "399006", "512100"
HORIZONS = [5, 20, 60, 120]
JUMP_DATE = "2022-09-05"          # 512100 复权断裂（jump audit §2）
PERMUTE_SEED = 12345
N_PERMUTE = 10000
MIN_EVENTS_SLAVE_WEAK = 10         # 判定线 (a)
MIN_DIFF_PP = 5.0                  # 判定线 (b)：120日均值差 ≥ 5pp
P_ALPHA = 0.05                     # 判定线 (c)
OPERABLE_MAX = 10.0                # 同步性：可操作时段占比 < 10% 即无空间

OUT_JSON = REPO / "docs/experiments/raw/agent_AA/master_slave_precheck_results.json"


def flatten_jump(df: pd.DataFrame, jump_date: str) -> tuple[pd.DataFrame, dict]:
    """jump audit §3 修平：D 及之后 OHLC 同除 close[D]/close[D-1]。"""
    d = df.copy()
    dates = d.index
    pos = dates.get_indexer([pd.Timestamp(jump_date)])
    pos = int(pos[0])
    if pos <= 0:
        raise ValueError(f"跳变日 {jump_date} 不在数据中")
    ratio = float(d["close"].iloc[pos] / d["close"].iloc[pos - 1])
    d.iloc[pos:, :] = d.iloc[pos:, :].div(ratio)
    info = {
        "jump_date": jump_date,
        "ratio": round(ratio, 6),
        "pre_close": round(float(df["close"].iloc[pos - 1]), 4),
        "jump_close_raw": round(float(df["close"].iloc[pos]), 4),
        "jump_close_fixed": round(float(d["close"].iloc[pos]), 4),
        "method": "D及之后OHLC同除ratio（jump audit §3，收益置0向后连续化）",
    }
    return d, info


def build_target(bars: pd.DataFrame, breadth: pd.DataFrame) -> pd.Series:
    aligned = bars.join(breadth[["b200"]], how="inner").sort_index()
    return ladder_target(aligned["b200"], LADDER), aligned


def band(v: float) -> float:
    """档位三态归并（1.0/0.5/0.0）。"""
    if np.isnan(v):
        return float("nan")
    return 1.0 if v >= 0.999 else (0.5 if v >= 0.499 else 0.0)


def event_study(
    events: pd.DatetimeIndex, price: pd.DataFrame, horizons=HORIZONS
) -> dict:
    """T+1 开盘入场，事件后 N 日收益（close[T+1+N]/open[T+1]-1）。"""
    dates = price.index
    out = {}
    for n in horizons:
        rets, used = [], []
        for t in events:
            i = dates.get_loc(t)
            i_entry = i + 1
            i_exit = i + 1 + n
            if i_entry >= len(dates) or i_exit >= len(dates):
                continue  # 窗口不足，剔除并如实报笔数
            r = float(price["close"].iloc[i_exit] / price["open"].iloc[i_entry] - 1.0)
            rets.append(r)
            used.append(str(t.date()))
        rets_a = np.asarray(rets, dtype=float)
        out[f"n{n}"] = {
            "count": int(rets_a.size),
            "mean_ret": round(float(rets_a.mean()), 6) if rets_a.size else None,
            "win_rate": round(float((rets_a > 0).mean()), 6) if rets_a.size else None,
            "event_dates": used,
            "rets": [round(float(x), 6) for x in rets_a],
        }
    return out


def permutation_test(a: np.ndarray, b: np.ndarray, seed=PERMUTE_SEED, n_perm=N_PERMUTE):
    """单侧置换检验：观测差 obs = mean(a)-mean(b)；H0 两组同分布。"""
    if a.size < 3 or b.size < 3:
        return {"stat": None, "p": None, "reason": "任一组<3笔，不可检验"}
    obs = float(a.mean() - b.mean())
    rng = np.random.default_rng(seed)
    pool = np.concatenate([a, b])
    nb = b.size
    cnt = 0
    for _ in range(n_perm):
        perm = rng.permutation(pool)
        d = perm[:-nb].mean() - perm[-nb:].mean()
        if d >= obs:
            cnt += 1
    return {"stat": round(obs, 6), "p": round(cnt / n_perm, 6),
            "reason": None, "n_perm": n_perm}


def main() -> None:
    breadth_all = load_breadth("cn_all")
    bars_m = load_index_bars(MASTER)
    bars_s_raw = load_index_bars(SLAVE)
    bars_s, jump_info = flatten_jump(bars_s_raw, JUMP_DATE)

    tgt_m_full, ali_m_full = build_target(bars_m, breadth_all)
    tgt_s_full, ali_s_full = build_target(bars_s, breadth_all)

    # 共同窗口对齐（档位三态）
    common = ali_m_full.index.intersection(ali_s_full.index)
    band_m = tgt_m_full.loc[common].map(band)
    band_s = tgt_s_full.loc[common].map(band)

    # ---------- 第三步：同步性 ----------
    valid = band_m.notna() & band_s.notna()
    band_m_v, band_s_v = band_m[valid], band_s[valid]
    n_common = int(valid.sum())
    agree = int((band_m_v == band_s_v).sum())
    master_weak = band_m_v < 1.0
    master_strong = band_m_v >= 1.0
    n_master_weak = int(master_weak.sum())
    n_master_strong = int(master_strong.sum())
    slave_also_weak = int((band_s_v[master_weak] < 1.0).sum())
    # 严格敏感性：主弱 = 清仓档
    master_weak_strict = band_m_v <= 0.0
    n_mw_strict = int(master_weak_strict.sum())
    slave_weak_strict = int((band_s_v[master_weak_strict] <= 0.0).sum())
    disagree_days = [str(d.date()) for d in common[valid][band_m_v != band_s_v]]

    sync = {
        "common_days": n_common,
        "common_start": str(common.min().date()),
        "common_end": str(common.max().date()),
        "band_agree_days": agree,
        "band_agree_rate": round(agree / n_common, 6),
        "master_strong_days": n_master_strong,
        "master_weak_days": n_master_weak,
        "master_weak_share": round(n_master_weak / n_common, 6),
        "slave_also_weak_given_master_weak": round(
            slave_also_weak / n_master_weak, 6) if n_master_weak else None,
        "operable_days": n_common - agree,
        "operable_share_pct": round((n_common - agree) / n_common * 100, 4),
        "disagree_dates": disagree_days,
        "sensitive_strict_masterweak_eq0_days": n_mw_strict,
        "sensitive_strict_slave_eq0_share": round(
            slave_weak_strict / n_mw_strict, 6) if n_mw_strict else None,
        "sync_verdict_line": "可操作时段占比 <10% 即判门无实际操作空间",
        "sync_pass": bool((n_common - agree) / n_common * 100 < OPERABLE_MAX),
    }

    # ---------- 第二步：主从依赖事件研究 ----------
    # 从（512100）升档事件：目标档位三态相对前一日上升
    s_band_full = tgt_s_full.map(band).dropna()
    up_events = s_band_full[s_band_full > s_band_full.shift(1)].index
    # 主档位在事件日的状态
    m_at_event = tgt_m_full.reindex(up_events).map(band)
    ev_strong = m_at_event[m_at_event >= 1.0].index   # 主强组事件
    m_at_event = m_at_event.dropna()
    ev_weak = m_at_event[m_at_event < 1.0].index      # 主弱组事件

    study_strong = event_study(ev_strong, bars_s)
    study_weak = event_study(ev_weak, bars_s)
    study_master_ref = event_study(up_events, bars_m)  # 方向论证对照

    perm = permutation_test(
        np.array(study_strong["n120"]["rets"], dtype=float),
        np.array(study_weak["n120"]["rets"], dtype=float),
    ) if study_weak["n120"]["count"] >= 3 else {"stat": None, "p": None,
                                                "reason": "主弱组事件不足3笔"}

    n_weak = study_weak["n120"]["count"]
    mean_s120 = study_strong["n120"]["mean_ret"]
    mean_w120 = study_weak["n120"]["mean_ret"]
    diff_pp = (round((mean_s120 - mean_w120) * 100, 4)
               if (mean_s120 is not None and mean_w120 is not None) else None)
    dep = {
        "slave_upshift_events_total": int(len(up_events)),
        "master_strong_group": study_strong,
        "master_weak_group": study_weak,
        "master_120d_same_events": study_master_ref,
        "perm_test_120d": perm,
        "criteria": {
            "a_min_events": MIN_EVENTS_SLAVE_WEAK,
            "a_met": bool(n_weak >= MIN_EVENTS_SLAVE_WEAK),
            "a_n_weak": n_weak,
            "b_min_diff_pp": MIN_DIFF_PP,
            "b_diff_pp": diff_pp,
            "b_met": bool(diff_pp is not None and diff_pp >= MIN_DIFF_PP),
            "c_alpha": P_ALPHA,
            "c_p": perm.get("p"),
            "c_met": bool(perm.get("p") is not None and perm["p"] < P_ALPHA),
        },
        "dependency_exists": bool(
            n_weak >= MIN_EVENTS_SLAVE_WEAK
            and diff_pp is not None and diff_pp >= MIN_DIFF_PP
            and perm.get("p") is not None and perm["p"] < P_ALPHA
        ),
        "note_unverifiable_reason": (
            "从升档事件当日主档位与从完全一致（同一B200序列）→ 主弱组事件=0，"
            "依赖不可检验" if n_weak == 0 else None),
    }

    # ---------- 第四步：方向机制 ----------
    # 主全历史档位天数分布（2010-06 起）
    m_band_hist = tgt_m_full.map(band).dropna()
    direction = {
        "master_band_hist_days": {
            "full": round(float(m_band_hist.mean()), 6),
            "1.0": int((m_band_hist >= 1.0).sum()),
            "0.5": int(((m_band_hist >= 0.499) & (m_band_hist < 0.999)).sum()),
            "0.0": int((m_band_hist <= 0.0).sum()),
            "start": str(m_band_hist.index.min().date()),
            "end": str(m_band_hist.index.max().date()),
        },
        "same_day_same_signal": bool(n_common > 0 and agree == n_common),
        "who_leads": "无先后可言：两标的档位由同一全A B200 序列映射，事件同日发生",
        "master_vs_slave_120d_after_same_events": {
            "master_399006": study_master_ref["n120"]["mean_ret"],
            "slave_512100_fixed": study_strong["n120"]["mean_ret"],
        },
        "cyb_breadth_sidecheck": _cyb_sidecheck(breadth_all),
    }

    results = {
        "task": "Prompt AA master-slave precheck",
        "date": "2026-09-03",
        "signal_rule": {
            "indicator": "cn_all b200", "strategy": "ladder contrarian 3-band",
            "edges": [43.333333, 56.666667], "levels": [1.0, 0.5, 0.0],
            "source": "execution_playbook_20260827.md 终版三轮王 + kuandu-quanzhan ARCHIVE",
            "master": "399006 创业板指", "slave": "512100 中证1000ETF（修平后）",
        },
        "jump_fix_512100": jump_info,
        "step2_dependency": dep,
        "step3_synchronicity": sync,
        "step4_direction": direction,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )
    digest = hashlib.sha256(
        json.dumps(results, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    print(json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True))
    print("SHA256:", digest)


def _cyb_sidecheck(breadth_all: pd.DataFrame) -> dict:
    """旁证：创业板专属宽度（已判负口径）与全A宽度档位不一致率。仅机制参考。"""
    try:
        cyb = load_breadth("cn_cyb")
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": str(e)}
    both = breadth_all[["b200"]].join(cyb[["b200"]], how="inner", rsuffix="_cyb")
    both = both.dropna()
    t_all = ladder_target(both["b200"], LADDER).map(band)
    t_cyb = ladder_target(both["b200_cyb"], LADDER).map(band)
    ok = t_all.notna() & t_cyb.notna()
    n = int(ok.sum())
    dis = int((t_all[ok] != t_cyb[ok]).sum())
    return {
        "available": True,
        "days": n,
        "band_disagree_days": dis,
        "band_disagree_rate": round(dis / n, 6) if n else None,
        "note": ("非已验证规则（创业板专属宽度在 playbook 判负 -0.2%），"
                 "仅衡量'若换宽度口径主从状态才有差异'的假设空间；"
                 "中证1000 专属宽度无数据（BREADTH_FILES 不含），记为数据缺口"),
    }


if __name__ == "__main__":
    main()
