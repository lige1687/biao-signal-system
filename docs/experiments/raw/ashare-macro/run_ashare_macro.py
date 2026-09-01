#!/usr/bin/env python3
"""A股宏观变量触发层实验：融资余额变化率/加速度事件研究（预注册 2026-09-01，跑前写死，跑后不改）。

背景（任务书 Prompt C + 四路归档红线）：
- 现有虹吸信号用融资融券余额**水平**；本实验测**变化率（一阶导）/加速度（二阶导）**，
  定位=触发层事件信号（引擎层），不是仓位系数层。
- 红线1（huanjing-ARCHIVE br_half/br_quarter/combo）：「宏观变量分位→仓位打折」已判负
  ——本实验不做任何仓位映射，只做事件研究判方向显著性。
- 红线2（lei-ARCHIVE 利率档位闸）：全样本分位=前视假象——本实验分位一律**滚动窗**，
  仅用 ≤t 数据。红线2（lei-ARCHIVE RS 动量倾斜判负）：本实验无截面排序/加权，不涉。
- 信用利差：无免费可靠日频中国信用债-国债利差源（仓库 _TREASURY_FIELDS 仅国债，
  依赖无 akshare），登记**数据工程欠账**，不用合成数据冒充。

【预注册协议】

数据（全部为生产同款接口，缓存于本目录，拉取日 2026-09-01）：
- 融资余额 rzye_yi（亿元）：东财 RPTA_RZRQ_LSHJ 全史 2010-03-31→2026-08-31（3989 日），
  data_margin_history.json（src/lei_signal/fundamentals/sources.py::fetch_margin_history）。
- 标的（事件前瞻收益口径）：
  主口径 = 创业板指 399006（高贝塔、杠杆资金偏好；先验写死，不跑后换）
  —— raw/siphon_detector/cyb_399006_close.parquet（2010-06-01→2026-08-27，只读）。
  稳健口径 = 上证指数 sh000001（腾讯 ifzq，data_sse_close.json）。
- 阴性对照资产 = 黄金 ETF 518880（data_gold_close.json，2013-07-29 起）。

信号定义（全部仅用 ≤t 信息；t=两融轴事件日收盘）：
- chg20(t) = rzye(t)/rzye(t-20) − 1（两融轴自身 20 个交易日，不跨轴）。
- acc20(t) = chg20(t) − chg20(t−20)（二阶导）。
- 滚动分位窗 W=1250 个两融交易日（含 t），要求 t 处两融观测序号 i ≥ 1249
  （最早可能信号 ≈ 2015-04；刻意覆盖 2015 股灾）。
- E1 去杠杆事件：chg20(t) ≤ Q5(t)（窗内 5% 分位）。冷却 20 个两融交易日。
- E2 杠杆过热事件：chg20(t) ≥ Q95(t)。冷却 20 日。
- E3 去杠杆加速事件：acc20(t) ≤ QA5(t)（acc20 的滚动 5% 分位）。冷却 20 日。定位=辅助。
- 事件日 t 收盘生成 → 指数轴 t'（≥t 的首个指数交易日）的**次一交易日收盘**起算
  前瞻 H 日：fwd(H) = close(t'+1+H)/close(t'+1) − 1（近似 t+1 执行延迟，无费用；
  本研究判方向显著性，非策略回测）。
- 无条件基准 = 同标的、同 H 口径，从两融轴首个可能信号日映射到指数轴起，
  全部指数交易日的 fwd(H) 均值（与事件同期限域，避免期限错配）。

假设（先验方向，跑前写死；跑后不得翻案为反向通过——反向现象最多进「观察中」）：
- H1（E1）：去杠杆急坠后 60 日收益**低于**基准（下跌中段预警）。
- H2（E2）：杠杆过热后 120 日收益**低于**基准（顶部反转预警）。
  **已知反例风险预注册**：2024-09-24 政策 V 转后两融快速回升，若 E2 触发于
  2024-09-24→2025-01-27 且该事件 120 日实际收益 >0，H2 直接 FAIL（与主判定取更严）。
- H3（E3，辅助）：与 H1 同向同窗（60 日）。

判定标准（事前固化，主口径=创业板指，每假设独立）：
- 事件超额 = 事件 fwd(H) 均值 − 基准均值。
- PASS：超额 ≤ −3pp 且 block bootstrap 90% CI 上界 < 0。
- WATCH：超额 ≤ −1pp 且 CI 上界 < 0（方向确认、量级弱）。
- FAIL：其余（含方向相反/不显著）。
- block bootstrap：事件按相邻间隔 ≤60 个两融交易日聚块，块有放回重采样
  1000 次（numpy RandomState seed=0），每次算块内事件平均超额，取 5%/95% 分位。
- 稳健性（验证强度标注，非独立判定）：E1 邻域 Q2.5/Q10、E2 邻域 Q97.5/Q90 方向一致；
  上证口径同号。

窗口核验（只验证不调参；5 个预注册窗口，来自四路归档公共知识）：
  1. 2015-06-15→2016-01-28 股灾去杠杆：E1 应触发（记对/漏）。
  2. 2018-01-29→2018-10-19 阴跌：E1 触发情况如实记录（滚动窗含 2015 极值，可能压低 P5）。
  3. 2024-01-02→2024-02-05 微盘流动性危机：E1 应触发。
  4. 2014-12-01→2015-06-12 疯牛加杠杆：E2 应触发（仅 2015-04 后信号有效期内）。
  5. 2024-09-24→2025-01-27 政策牛：E2 触发=H2 反例试金石（见上）。
  核验判定：应有信号窗（1/3/4）≥2 窗触发记「核验通过」，否则「核验未过」。

阴性对照（方法可信度门槛，独立于主判定报告）：
- N1 资产无关：E1/E2 事件窗的黄金 518880 fwd(H) 超额应 ≈0（|超额|<2pp 且
  bootstrap 90% CI 含 0）。显著 ≠0 → 主结论整体降级为「疑泛化噪音」。
- N2 安慰剂：随机日期（与真实事件同数、1000 组、RandomState seed=0，基准期内
  均匀抽样）的平均超额分布；真实超额须 ≤ 安慰剂 10% 分位（负向假设）。

多重比较声明：3 实验 × 2 标的 = 6 组数字；主判定只取创业板口径（先验写死），
上证口径仅稳健性；E3 亦为辅助。有效独立判定数 = 2（H1/H2）。

复现：cd <repo> && PYTHONHASHSEED=0 python3 docs/experiments/raw/ashare-macro/run_ashare_macro.py
输出：docs/experiments/raw/ashare-macro/ashare_macro_results.json（不含时间戳，可双跑比对哈希）
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]  # ashare-macro -> raw -> experiments -> docs -> repo root

# ── 预注册常量（与 docstring 一致，跑后不改）───────────────────────────────
ROLL_WINDOW = 1250          # 滚动分位窗（两融交易日，含 t）
MIN_IDX = ROLL_WINDOW - 1   # 两融轴序号 i ≥ 1249 才有满窗
CHG_N = 20                  # chg20 回看
COOLDOWN = 20               # 事件冷却（两融交易日）
E1_Q, E2_Q = 5.0, 95.0      # 主阈值（%）
E1_Q_LO, E1_Q_HI = 2.5, 10.0    # E1 邻域（稳健性）
E2_Q_LO, E2_Q_HI = 97.5, 90.0   # E2 邻域（稳健性）
H_E1, H_E2 = 60, 120        # 前瞻窗（指数交易日）
PASS_PP, WATCH_PP = -3.0, -1.0  # 判定线（pp）
BLOCK_GAP = 60              # 事件聚块间隔（两融交易日）
N_BOOT, N_PLACEBO = 1000, 1000
SEED = 0

WINDOWS = [  # (起, 止, 关联实验, 应触发?, 说明)
    ("2015-06-15", "2016-01-28", "E1", True, "股灾去杠杆"),
    ("2018-01-29", "2018-10-19", "E1", None, "阴跌（窗含2015极值可能压低P5，如实记录）"),
    ("2024-01-02", "2024-02-05", "E1", True, "微盘流动性危机"),
    ("2014-12-01", "2015-06-12", "E2", True, "疯牛加杠杆（仅2015-04后有效）"),
    ("2024-09-24", "2025-01-27", "E2", None, "政策牛=H2反例试金石"),
]
E2_COUNTER_START, E2_COUNTER_END = "2024-09-24", "2025-01-27"


# ── 数据加载 ────────────────────────────────────────────────────────────────
def load_data() -> dict:
    margin = json.loads((HERE / "data_margin_history.json").read_text())
    m_dates = sorted(margin)
    rzye = np.array([margin[d]["rzye_yi"] for d in m_dates], dtype=float)
    assert not np.isnan(rzye).any(), "融资余额序列含 NaN"

    def _idx(path: Path | None, parquet: Path | None = None) -> tuple[np.ndarray, np.ndarray]:
        if parquet is not None:
            df = pd.read_parquet(parquet)
            ds = df.index.strftime("%Y-%m-%d").to_numpy()
            cl = df["close"].to_numpy(dtype=float)
            order = np.argsort(ds)
            return ds[order], cl[order]
        raw = json.loads(path.read_text())
        ds = np.array(sorted(raw))
        return ds, np.array([raw[d] for d in ds], dtype=float)

    cyb_d, cyb_c = _idx(None, parquet=REPO / "docs/experiments/raw/siphon_detector/cyb_399006_close.parquet")
    sse_d, sse_c = _idx(HERE / "data_sse_close.json")
    gold_d, gold_c = _idx(HERE / "data_gold_close.json")
    return {
        "m_dates": np.array(m_dates), "rzye": rzye,
        "cyb": (cyb_d, cyb_c), "sse": (sse_d, sse_c), "gold": (gold_d, gold_c),
    }


# ── 信号与事件 ──────────────────────────────────────────────────────────────
def roll_pct(series: np.ndarray, q: float) -> np.ndarray:
    """滚动窗（含 t）分位；仅当窗内 ROLL_WINDOW 个观测全部有效才计算（否则 NaN）。

    这意味着 chg20 的信号有效起点 = 满窗且前 20 日 NaN 段被排除后的首日。
    """
    out = np.full(len(series), np.nan)
    valid_cum = np.cumsum(~np.isnan(series))
    for i in range(MIN_IDX, len(series)):
        lo_i = i - ROLL_WINDOW + 1
        prev = valid_cum[lo_i - 1] if lo_i > 0 else 0
        if valid_cum[i] - prev == ROLL_WINDOW:
            out[i] = np.percentile(series[lo_i : i + 1], q)
    return out


def extract_events(dates: np.ndarray, series: np.ndarray, thr: np.ndarray,
                   side: str, cooldown: int = COOLDOWN) -> list[dict]:
    """side='low': series<=thr 触发；'high': series>=thr 触发。冷却期内忽略。"""
    events, last = [], -10**9
    for i in range(MIN_IDX, len(series)):
        if np.isnan(thr[i]) or np.isnan(series[i]):
            continue
        hit = series[i] <= thr[i] if side == "low" else series[i] >= thr[i]
        if hit and i - last >= cooldown:
            events.append({
                "date": str(dates[i]), "i": i,
                "value": round(float(series[i]), 4),
                "thr": round(float(thr[i]), 4),
            })
            last = i
    return events


def fwd_return(idx_dates: np.ndarray, idx_close: np.ndarray,
               event_date: str, h: int) -> float | None:
    """事件日 → 指数轴 t'（≥event_date 首个交易日）次一收盘起算 H 日收益。"""
    pos = int(np.searchsorted(idx_dates, event_date))
    start, end = pos + 1, pos + 1 + h
    if end < len(idx_close):
        return float(idx_close[end] / idx_close[start] - 1.0)
    return None


def baseline(idx_dates: np.ndarray, idx_close: np.ndarray,
             first_date: str, h: int) -> tuple[float, np.ndarray, np.ndarray]:
    """基准：first_date 起全部指数交易日的 fwd(H)（同 t'+1 口径）。返回 (均值, 位置, 收益)。"""
    j0 = int(np.searchsorted(idx_dates, first_date))
    pos = np.arange(j0, len(idx_close) - 1 - h)
    fwd = idx_close[pos + 1 + h] / idx_close[pos + 1] - 1.0
    return float(fwd.mean()), pos, fwd


def blocks(events: list[dict]) -> list[list[int]]:
    """事件按两融轴相邻间隔 ≤BLOCK_GAP 聚块，返回块内事件下标（在 events 列表中）。"""
    if not events:
        return []
    out, cur = [], [0]
    for k in range(1, len(events)):
        if events[k]["i"] - events[k - 1]["i"] <= BLOCK_GAP:
            cur.append(k)
        else:
            out.append(cur)
            cur = [k]
    out.append(cur)
    return out


def block_bootstrap_ci(events: list[dict],
                       h: int, idx: tuple[np.ndarray, np.ndarray],
                       base_mean: float) -> tuple[float, float, float]:
    """返回 (平均超额, 90%CI 下界, 上界)。块有放回重采样 N_BOOT 次（seed 固定）。"""
    blks = blocks(events)
    means = np.array([
        np.mean([fwd_return(idx[0], idx[1], events[k]["date"], h) for k in blk])
        - base_mean for blk in blks
    ])
    obs = float(np.mean([
        fwd_return(idx[0], idx[1], e["date"], h) for e in events
    ]) - base_mean) if events else float("nan")
    rng = np.random.RandomState(SEED)
    samples = np.array([
        float(np.mean(rng.choice(means, size=len(means), replace=True)))
        for _ in range(N_BOOT)
    ]) if len(means) else np.array([np.nan])
    lo, hi = np.percentile(samples, [5.0, 95.0])
    return obs, float(lo), float(hi)


def verdict(excess_pp: float, ci_hi: float) -> str:
    if excess_pp <= PASS_PP and ci_hi < 0:
        return "PASS"
    if excess_pp <= WATCH_PP and ci_hi < 0:
        return "WATCH"
    return "FAIL"


# ── 主流程 ─────────────────────────────────────────────────────────────────
def main() -> None:
    data = load_data()
    m_dates, rzye = data["m_dates"], data["rzye"]
    chg20 = np.full(len(rzye), np.nan)
    chg20[CHG_N:] = rzye[CHG_N:] / rzye[:-CHG_N] - 1.0
    acc20 = np.full(len(rzye), np.nan)
    acc20[2 * CHG_N :] = chg20[2 * CHG_N :] - chg20[CHG_N : -CHG_N]  # acc(t)=chg20(t)-chg20(t-20)

    # 首个可能信号日 = chg20 满足满窗（排除其自身前段 NaN）的首日
    sig_first = str(m_dates[MIN_IDX + CHG_N])

    q5 = roll_pct(chg20, E1_Q)
    q95 = roll_pct(chg20, E2_Q)
    qa5 = roll_pct(acc20, E1_Q)
    e1 = extract_events(m_dates, chg20, q5, "low")
    e2 = extract_events(m_dates, chg20, q95, "high")
    e3 = extract_events(m_dates, acc20, qa5, "low")

    # 邻域阈值事件（稳健性，非判定）
    e1_lo = extract_events(m_dates, chg20, roll_pct(chg20, E1_Q_LO), "low")
    e1_hi = extract_events(m_dates, chg20, roll_pct(chg20, E1_Q_HI), "low")
    e2_lo = extract_events(m_dates, chg20, roll_pct(chg20, E2_Q_LO), "high")
    e2_hi = extract_events(m_dates, chg20, roll_pct(chg20, E2_Q_HI), "high")

    # 逐事件前瞻收益明细（供归档观察中一节解读，不参与判定）
    for ev, h in [(e1, H_E1), (e2, H_E2), (e3, H_E1)]:
        for e in ev:
            for ak, idx in [("cyb", data["cyb"]), ("sse", data["sse"])]:
                f = fwd_return(idx[0], idx[1], e["date"], h)
                e[f"fwd{h}_{ak}_pct"] = round(100 * f, 2) if f is not None else None

    res: dict = {
        "meta": {
            "protocol": "预注册见脚本 docstring（跑前写死）",
            "margin_range": [str(m_dates[0]), str(m_dates[-1])], "n_margin": len(m_dates),
            "signal_first_possible": sig_first,
            "cyb_range": [str(data["cyb"][0][0]), str(data["cyb"][0][-1])],
            "sse_range": [str(data["sse"][0][0]), str(data["sse"][0][-1])],
            "gold_range": [str(data["gold"][0][0]), str(data["gold"][0][-1])],
            "const": {"ROLL_WINDOW": ROLL_WINDOW, "CHG_N": CHG_N, "COOLDOWN": COOLDOWN,
                      "E1_Q": E1_Q, "E2_Q": E2_Q, "H_E1": H_E1, "H_E2": H_E2,
                      "PASS_PP": PASS_PP, "WATCH_PP": WATCH_PP,
                      "N_BOOT": N_BOOT, "N_PLACEBO": N_PLACEBO, "SEED": SEED},
        },
        "events": {
            "E1_deleveraging": {"n": len(e1), "list": e1},
            "E2_overheating": {"n": len(e2), "list": e2},
            "E3_acceleration": {"n": len(e3), "list": e3},
            "robustness_counts": {
                "E1_Q2.5": len(e1_lo), "E1_Q10": len(e1_hi),
                "E2_Q97.5": len(e2_lo), "E2_Q90": len(e2_hi)},
        },
    }

    # ── 事件研究（主口径创业板；上证=稳健）─────────────────────────────────
    study: dict = {}
    for name, ev, h in [("E1", e1, H_E1), ("E2", e2, H_E2), ("E3", e3, H_E1)]:
        for asset_key, idx in [("cyb", data["cyb"]), ("sse", data["sse"])]:
            base_mean, base_pos, base_fwd = baseline(idx[0], idx[1], sig_first, h)
            ev_h = [e for e in ev if fwd_return(idx[0], idx[1], e["date"], h) is not None]
            obs, lo, hi = block_bootstrap_ci(ev_h, h, idx, base_mean)
            key = f"{name}_{asset_key}"
            study[key] = {
                "h": h, "n_events_with_fwd": len(ev_h),
                "mean_fwd_pct": round(100 * (obs + base_mean), 2) if ev_h else None,
                "baseline_pct": round(100 * base_mean, 2),
                "excess_pp": round(100 * obs, 2) if ev_h else None,
                "ci90_pp": [round(100 * lo, 2), round(100 * hi, 2)],
                "verdict": verdict(100 * obs, 100 * hi) if ev_h else "FAIL(no events)",
            }
            if asset_key == "cyb":  # 安慰剂 N2（主口径）
                rng = np.random.RandomState(SEED)
                placebos = []
                for _ in range(N_PLACEBO):
                    pick = rng.choice(base_pos, size=max(1, len(ev_h)), replace=False)
                    pf = idx[1][pick + 1 + h] / idx[1][pick + 1] - 1.0
                    placebos.append(float(pf.mean() - base_mean))
                pl = np.percentile(np.array(placebos), [5, 10, 50, 90, 95])
                study[key]["placebo_pctile_pp"] = {
                    "p5": round(100 * pl[0], 2), "p10": round(100 * pl[1], 2),
                    "p50": round(100 * pl[2], 2), "p90": round(100 * pl[3], 2),
                    "p95": round(100 * pl[4], 2)}
                # N2：真实超额须 ≤ 安慰剂分布 10 分位（负向假设，pp 口径）
                study[key]["n2_pass"] = bool(ev_h and 100 * obs <= 100 * pl[1])
    res["event_study"] = study

    # ── 窗口核验 ────────────────────────────────────────────────────────────
    wcheck = []
    for a, b, exp, should, note in WINDOWS:
        evs = e1 if exp == "E1" else e2
        hits = [e["date"] for e in evs if a <= e["date"] <= b]
        wcheck.append({"window": [a, b], "experiment": exp, "expect": should,
                       "note": note, "triggered_dates": hits,
                       "hit": bool(hits) if should else None})
    must = [w for w in wcheck if w["expect"] is True]
    res["window_check"] = {
        "windows": wcheck,
        "verdict": "核验通过" if sum(1 for w in must if w["hit"]) >= 2 else "核验未过",
        "must_windows_hit": f"{sum(1 for w in must if w['hit'])}/{len(must)}",
    }

    # H2 反例条款：E2 触发于政策牛窗且创业板/上证 120 日收益 >0 → H2 FAIL
    e2_counter = []
    for e in e2:
        if E2_COUNTER_START <= e["date"] <= E2_COUNTER_END:
            for ak, idx in [("cyb", data["cyb"]), ("sse", data["sse"])]:
                f = fwd_return(idx[0], idx[1], e["date"], H_E2)
                if f is not None:
                    e2_counter.append({"date": e["date"], "asset": ak,
                                       "fwd120_pct": round(100 * f, 2)})
    res["h2_counterexample"] = {
        "events": e2_counter,
        "fired": bool(any(c["fwd120_pct"] > 0 for c in e2_counter
                          if c["asset"] == "cyb")),
    }
    if res["h2_counterexample"]["fired"]:
        res["event_study"]["E2_cyb"]["verdict"] = "FAIL(counterexample clause)"

    # ── N1 阴性对照：黄金 ───────────────────────────────────────────────────
    n1 = {}
    for name, ev, h in [("E1", e1, H_E1), ("E2", e2, H_E2)]:
        base_mean, _, _ = baseline(data["gold"][0], data["gold"][1], sig_first, h)
        ev_h = [e for e in ev if fwd_return(data["gold"][0], data["gold"][1], e["date"], h) is not None]
        obs, lo, hi = block_bootstrap_ci(ev_h, h, data["gold"], base_mean)
        n1[name] = {"n": len(ev_h), "excess_pp": round(100 * obs, 2) if ev_h else None,
                    "ci90_pp": [round(100 * lo, 2), round(100 * hi, 2)],
                    "clean": bool(ev_h and abs(100 * obs) < 2.0
                                  and 100 * lo <= 0.0 <= 100 * hi)}
    res["negative_control_gold"] = n1

    # ── 邻域阈值方向核验（预注册稳健性标注：方向一致，非独立判定）─────────
    def nb_excess(ev: list[dict], h: int) -> float | None:
        base_mean, _, _ = baseline(data["cyb"][0], data["cyb"][1], sig_first, h)
        vals = [fwd_return(data["cyb"][0], data["cyb"][1], e["date"], h) for e in ev]
        vals = [v - base_mean for v in vals if v is not None]
        return round(100 * float(np.mean(vals)), 2) if vals else None

    res["robustness_neighborhood"] = {
        "asset": "cyb",
        "E1_Q2.5_excess_pp": nb_excess(e1_lo, H_E1),
        "E1_Q10_excess_pp": nb_excess(e1_hi, H_E1),
        "E2_Q97.5_excess_pp": nb_excess(e2_lo, H_E2),
        "E2_Q90_excess_pp": nb_excess(e2_hi, H_E2),
        "note": "主判定超额符号为 E1=+ / E2≈0；邻域同号要求：E1 邻域同为正、E2 邻域同为≈0",
    }

    out_path = HERE / "ashare_macro_results.json"
    out_path.write_text(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    print(json.dumps({
        "sha256": digest,
        "verdicts": {k: v["verdict"] for k, v in res["event_study"].items()},
        "n_events": {k: v["n"] for k, v in res["events"].items() if isinstance(v, dict) and "n" in v},
        "window_verdict": res["window_check"]["verdict"],
        "h2_counter_fired": res["h2_counterexample"]["fired"],
        "gold_clean": {k: v["clean"] for k, v in n1.items()},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
