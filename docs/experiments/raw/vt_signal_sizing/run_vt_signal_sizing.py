#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务 K：vt 目标波动缩放接入「信号驱动的单标的仓位层」（2026-09-02）。

===========================================================================
研究问题（对应 vt-grid-ARCHIVE 冲突发现③ + huanjing-ARCHIVE 观察中 F2）
===========================================================================
Q1（主检验）：把已验证有效的 vt 机制（基于**波动率**的目标波动缩放，
    组合层唯一 passed 的仓位机制）接到**单次信号触发的单笔头寸大小**上——
    每笔入场按 E = clip(目标/该标的RV20, 0.25, 1) 缩放仓位——是否改善
    同一组信号的风险调整表现（expR/PF 口径，比照 exit-matrix 框架：
    同模块同信号，只是仓位大小不同）？
Q2（F2 缺口）：huanjing 观察中 F2「高波期 A/B/D 入场打折、C 不缩」的
    模块非对称性，在 vt 单笔缩放机制下是否同样成立——即 C 模块（2B 破底
    翻，深跌后反转）是否应排除在 vt 缩放之外，还是同样适用？

红线（先分清，不得混淆）：本实验自变量 = **波动率**（信号日 RV20），
不是宽度分位（b50/b200）、不是利率分位——后者是仓位系数层已判负 8 项的
机制（huanjing 5 + position-mapping-revival 3）。脚本中仓位系数 E 的
计算输入只有 (target, RV20) 两个标量（见 e_of 函数），代码层面不引入
任何宽度/利率变量。

===========================================================================
环境披露（2026-09-02 实测，先于一切计算声明）
===========================================================================
exit-matrix 1469 笔全池基线在本机**已不可复现**：
  - ~/.lei_signal_lab/backtest_pool/（175 标的深池）已不存在；
  - ~/.lei_signal_lab/backtest_runs/（08-31 逐笔 run JSON）已不存在；
  - stash a816485f / 1a321ce6 已非 git 对象（git cat-file 验证）；
  - /tmp/a64-worktree 已不存在；系统 python 无 pandas（本实验用 /tmp/vt_venv）。
因此本实验**不重跑引擎**，改用 git 内已归档的逐笔交易记录（冻结于归档
时点）作为信号本体；每笔的 r_net/entry_price 等直接取归档值，唯一新增
数据 = 重取行情（仅用于计算信号日 RV20 与年代核对）。代价：A 模块主样本
为 641 笔已平仓（wf_a_noshrink 全量），非 1469 笔全池样本——两口径差异
在报告中如实声明；本实验全部对比为**同一逐笔集合内部**（等权 vs vt 加权），
不依赖跨口径对比。

信号本体（全部为 git 内归档，模块冻结配置见各 run params）：
  A_cn        raw/breadth_overlay/wf_a_noshrink.json  655 行→641 已平仓
              （early / a6_1_costbasis / clock_mult0.5 / 无量能过滤，44 ETF 池）
  A_cn_shrink raw/breadth_overlay/wf_a_main.json      283 行→275
              （同上 + volume_filter=shrink，配置稳健性臂）
  B_cn        raw/lifecycle_combo/T1_Bp_a61.json      101 行→100
              （breakout / a6_1 / cb30+cl3%，83 个股池；归档剔除 000300.SS
               基准自身 12 笔——benchmark_own_trades_dropped=12）
  C_cn        raw/lifecycle_combo/T2_C_stocks_v3_b15.json 177 行→176
              （v3 / a6_1 / bias −15%，个股池）
  A_us        raw/stage_b200/A_us.json                 96 行→95
  B_us        raw/stage_b200/B_us.json                 37 行→37
              （XLK/IGV/SOXX；归档均剔除 ^GSPC 基准自身交易，故与各自
               run groups 汇总(n=160/45)不符——结构性差异，不设 G1 门槛）
  D 模块：cn 个股池默认参数十年仅 2 笔（lifecycle_combo 归档），样本不足
  不检验，显式声明。

RV20 估计器（vt-grid 第一节已验证口径，逐字复用）：
  rv20   = rets.rolling(20).std() * sqrt(252)，rets = close.pct_change()
  ewma97 = rets.ewm(alpha=0.03, min_periods=20).std() * sqrt(252)（稳健臂）
取值时点 = 信号日 T 收盘（含 T）——仓位决策在 T 收盘后、T+1 开盘入场前
做出，T+1 数据不可用（无前视；对齐 vt-grid「t 收盘计算、t+1 执行」）。

行情数据（新增抓取，缓存于本目录 bars_cn.parquet / bars_us.parquet，
含 open/close 两列，供 G2 年代核对与 RV20 计算）：
  cn ETF/个股：腾讯 fqkline qfq 日线（2016-01-01 起两年窗分页）——
               与 08-31 深池同源前复权口径（spot check：159611.SZ
               2024-05-28 重取开盘 1.023 == 归档 entry_price 1.023）；
  us XLK/IGV/SOXX：Yahoo v8 chart 日线 **raw quote OHLC**（复刻生产
               YahooV8PriceProvider 口径：引擎用 quote.close/open 原始价，
               adjusted 标记为 True——见 src/lei_signal/data/providers.py）。
  交叉验证 X2：cn 个股与 ~/.lei_signal_lab/cache/a_share_klines.parquet
  （2026-08-19 冻结年代）重叠段收盘比对；X3：ETF 与 raw/etf_breadth/
  *_close.parquet（归档冻结）重叠段收盘比对。

===========================================================================
判定标准（预注册，跑之前写死，跑完不得调整）
===========================================================================
有效性门槛（任一不通过 → 整份结果作废，不得解读）：
  G1 基线复现：A_cn / A_cn_shrink / C_cn 自算等权基线（n/expR/PF）必须与
     归档 run groups 汇总逐位一致（|Δ|<1e-9）——证明逐笔记录未损坏且
     指标口径与引擎 compute_metrics(net=True) 一致。
  G2 年代核对：每模块 ≥98% 已入场笔满足 |重取开盘(entry_date) −
     归档 entry_price| / entry_price ≤ 0.35%（容差=复权价 2-3 位小数
     舍入；若某标的复权因子在归档后漂移，其全部笔将集体超限并被此门槛
     捕获）。另报中位偏离（应≈舍入量级）。
  G3 RV20 可得：因历史不足 21 根收盘而丢弃的笔 <5%/模块。

主判定 Q1（主样本 = A_cn，主锚点 target=20%，主估计器 = rv20）：
  J1 风险效率改善：ΔexpR = expR_w − expR_0（expR_w = Σ(E·r)/Σ(E)，
     expR_0 = mean(r)，同一已平仓集合）的逐笔配对 bootstrap
     （10000 次，numpy RandomState(20260902)）95% percentile CI 下界 > 0；
  J2 绝对收益保留：retention = Σ(E·r)/Σ(r) ≥ 0.80（Σ(r)≤0 时该条不判
     只记录）——防「砍仓买效率」（vt-grid 单资产层教训的对应条款）；
  J3 PF 不劣化：PF_w ≥ PF_0 − 0.05（加权 PF = Σ_{r>0}E·r/|Σ_{r≤0}E·r|）。
  verdict：passed = J1∧J2∧J3；watch = ΔexpR 点估计>0 但 CI 含 0 且
  J2/J3 成立；falsified = 其余。
  参数稳健（防孤峰，对齐 vt-grid「全档全报」）：target ∈
  {12.5,15,17.5,20,22.5,30,40}%（7 档全报，20/22.5=vt-grid 组合层
  通过带；更宽档位检验单标的层是否需要不同量级）。「方向稳健」=
  ≥5/7 档 ΔexpR>0。估计器稳健：锚点 20% 用 ewma97 复算（含 bootstrap
  CI，仅作敏感性披露，无预注册判定线——rv20 与 ewma97 的分歧本身
  作为诚实发现报告）。

副判定 Q2（F2 的 C 排除问题，锚点 20%/rv20，逐模块
A_cn/A_cn_shrink/A_us/B_cn/B_us/C_cn）：
  报 ΔexpR + bootstrap CI + RV20 三分位组（低/中/高波）mean r_net 与
  高−低差 + Spearman(RV20, r_net)。
  「C 应排除于 vt（非对称成立）」= A_cn 过 J1（CI 下界>0）且 C_cn 的
  ΔexpR CI 上界 ≤ +0.05R（缩放对 C 无有意义正贡献）；
  「C 同样适用」= C_cn CI 下界 > 0；
  其余 = 不确定。D 模块不检验（N=2）。

安全约束：只读研究，不改 src/、不 push、不删文件；产出仅本目录新增。
输出：vt_signal_sizing_results.json（sort_keys、无时间戳字段，
PYTHONHASHSEED=0/42 双跑 md5 一致才入档）。

事后补充（跑后新增，非预注册，透明披露）：首跑后 G2 在 C_cn 失败
（5/173 笔价位年代漂移，集中在多分红标的 000568.SZ/002326.SZ——qfq
分段常数复权基数在归档（东财源）与重取（腾讯源）间的方法论差异；
X2 收益率层交叉验证一致：68 标的中位 |Δret|=0.0bp、最差 3.5bp，
价位漂移不改变收益率即 RV20 的输入）。为此新增两件事且**未改任何
预注册判定线**：① G2 超限笔与 G3 缺失笔逐笔明细落盘；② C_cn 剔除
G2 超限笔的对称稳健臂（基线+锚点格+CI+三分位）。预注册判定
（G2 FAIL → 结果作废条款）如实保留：本实验最终以 gates.all_pass=False
入档，解读层依赖 X2 收益率一致性 + 剔除稳健臂，证据等级在报告中
相应降档声明。

复现：cd docs/experiments/raw/vt_signal_sizing &&
      PYTHONHASHSEED=0 python3 run_vt_signal_sizing.py [--refetch]
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RAW = REPO / "docs" / "experiments" / "raw"

#: ── 预注册参数（docstring 判定标准的机器可读副本，两边必须一致）──────
TARGETS = (0.125, 0.15, 0.175, 0.20, 0.225, 0.30, 0.40)
ANCHOR = 0.20
ESTIMATORS = ("rv20", "ewma97")
E_FLOOR, E_CAP = 0.25, 1.0
BOOT_N = 10_000
BOOT_SEED = 20_260_902
RETENTION_MIN = 0.80
PF_TOLERANCE = 0.05
G2_RATE_TOL, G2_SHARE_MIN = 0.0035, 0.98
G3_MISSING_MAX = 0.05
CI_C_EXCLUSION_UB = 0.05  # Q2：C 排除判定的 CI 上界线

ARCHIVES = {
    "A_cn": ("breadth_overlay", "wf_a_noshrink.json"),
    "A_cn_shrink": ("breadth_overlay", "wf_a_main.json"),
    "B_cn": ("lifecycle_combo", "T1_Bp_a61.json"),
    "C_cn": ("lifecycle_combo", "T2_C_stocks_v3_b15.json"),
    "A_us": ("stage_b200", "A_us.json"),
    "B_us": ("stage_b200", "B_us.json"),
}
#: G1 门槛：归档 run groups 汇总 net=True 口径（r_net 统计；groups 键
#: "True"=net 含费用——首跑烟雾测试已验证 groups['True'] 与 r_net 自算一致）。
G1_EXPECT = {
    "A_cn": (641, 0.15589154785869716, 1.094338469072902),
    "A_cn_shrink": (275, 0.816191178200635, 1.6215921991069062),
    "C_cn": (176, 0.20092916881417097, 1.6880665437951334),
}
#: 非 G1 样本的归档 net 汇总（含基准自身交易，仅披露用，不作门槛）。
GROUPS_NET_DISCLOSE = {
    "B_cn": (112, 1.0564718225667649, 3.2381449092111225),
    "A_us": (160, 0.46215601786026095, 1.4418213070962855),
    "B_us": (45, 0.19706997337834103, 1.4449479767011348),
}
EXCLUDED_REASONS = ("invalid_nonpositive_risk", "skipped_limit_up_at_entry")

WINDOWS = (
    ("2016-01-01", "2017-12-31"),
    ("2018-01-01", "2019-12-31"),
    ("2020-01-01", "2021-12-31"),
    ("2022-01-01", "2023-12-31"),
    ("2024-01-01", "2026-12-31"),
)
#: 腾讯 fqkline 主机：主用 ifzq.gtimg.cn（实测 web.ifzq 子域在连续请求
#: ~30 次后返回 501，裸域不受影响；抓取层带双主机重试）。
TENCENT_HOSTS = ("https://ifzq.gtimg.cn/appstock/app/fqkline/get",
                 "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get")
SLEEP = 0.5
US_SYMBOLS = ("IGV", "SOXX", "XLK")
US_P1, US_P2 = 1420070400, 1800000000  # 2015-01-01 → 2027-01-15（固定，勿改）
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def tencent_code(symbol: str) -> str:
    body = symbol.split(".")[0]
    return ("sh" if symbol.endswith(".SS") else "sz") + body


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def _wide(cols: dict[tuple[str, str], pd.Series]) -> pd.DataFrame:
    """{(symbol, field): Series} → MultiIndex 宽表 (symbol, field)。"""
    frame = pd.DataFrame(cols).sort_index()
    frame.columns = pd.MultiIndex.from_tuples(frame.columns)
    return frame


def _tencent_window(code: str, start: str, end: str) -> list:
    """单窗口抓取：双主机各试 2 次；code!=0（如 param error）视为空。"""
    for attempt in range(2):
        for host in TENCENT_HOSTS:
            url = host + "?" + urllib.parse.urlencode(
                {"param": f"{code},day,{start},{end},800,qfq"})
            try:
                payload = json.loads(http_get(url))
            except Exception:  # noqa: BLE001
                time.sleep(SLEEP)
                continue
            if payload.get("code") != 0:
                time.sleep(SLEEP)
                continue
            node = (payload.get("data") or {}).get(code, {})
            bars = node.get("qfqday") or node.get("day") or []
            if bars:
                return bars
            time.sleep(SLEEP)
    return []


def fetch_cn_bars(symbols: list[str],
                  existing: pd.DataFrame | None = None) -> pd.DataFrame:
    """腾讯 qfq 日线 → (symbol, open/close) 宽表，两年窗分页拼接。

    existing：已抓取的部分宽表（断点续传——只补缺失标的，逐列并入）。
    """
    have: set[str] = set()
    if existing is not None and not existing.empty:
        have = set(existing.columns.get_level_values(0))
        print(f"  （续传：已有 {len(have)} 标的）", flush=True)
    cols: dict[tuple[str, str], pd.Series] = {}
    if existing is not None and not existing.empty:
        for sym in sorted(have):
            cols[(sym, "open")] = existing[(sym, "open")]
            cols[(sym, "close")] = existing[(sym, "close")]
    for sym in symbols:
        if sym in have:
            continue
        code = tencent_code(sym)
        opens: dict[str, float] = {}
        closes: dict[str, float] = {}
        for start, end in WINDOWS:
            for bar in _tencent_window(code, start, end):
                opens[bar[0]] = float(bar[1])
                closes[bar[0]] = float(bar[2])
            time.sleep(SLEEP)
        if opens:
            days = sorted(opens)
            idx = pd.to_datetime(days)
            cols[(sym, "open")] = pd.Series(
                [opens[d] for d in days], index=idx)
            cols[(sym, "close")] = pd.Series(
                [closes[d] for d in days], index=idx)
            print(f"  {sym}: {len(days)} 根 ({days[0]}..{days[-1]})", flush=True)
        else:
            print(f"  ! {sym} 无数据", flush=True)
    return _wide(cols)


def fetch_us_bars(symbols: tuple[str, ...]) -> pd.DataFrame:
    """Yahoo v8 raw quote OHLC → (symbol, open/close) 宽表（复刻引擎口径）。"""
    cols: dict[tuple[str, str], pd.Series] = {}
    for sym in symbols:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
               f"?period1={US_P1}&period2={US_P2}&interval=1d&events=div%7Csplit")
        payload = json.loads(http_get(url))
        result = payload["chart"]["result"][0]
        ts = result["timestamp"]
        q = result["indicators"]["quote"][0]
        rows = {}
        for t, o, c in zip(ts, q["open"], q["close"]):
            if o is None or c is None:
                continue
            day = pd.Timestamp(t, unit="s", tz="America/New_York").date()
            rows[day] = (float(o), float(c))
        days = sorted(rows)
        idx = pd.to_datetime(days)
        cols[(sym, "open")] = pd.Series([rows[d][0] for d in days], index=idx)
        cols[(sym, "close")] = pd.Series([rows[d][1] for d in days], index=idx)
        print(f"  {sym}: {len(days)} 根 ({days[0]}..{days[-1]})", flush=True)
    return _wide(cols)


_TRADE_CACHE: dict[str, dict] = {}


def load_run(key: str) -> dict:
    if key not in _TRADE_CACHE:
        sub, fname = ARCHIVES[key]
        _TRADE_CACHE[key] = json.loads(
            (RAW / sub / fname).read_text(encoding="utf-8"))
    return _TRADE_CACHE[key]


def closed_trades(key: str) -> list[dict]:
    """已平仓集合：镜像 compute_metrics 的 closed 口径
    （r_net 非空、exit_date 非空、exit_reason 非剔除项）。"""
    return [
        t for t in load_run(key)["trades"]
        if t.get("r_net") is not None
        and t.get("exit_date") is not None
        and t.get("exit_reason") not in EXCLUDED_REASONS
    ]


def load_bars(refetch: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    cn_path, us_path = HERE / "bars_cn.parquet", HERE / "bars_us.parquet"
    need_cn = sorted({t["symbol"] for key in ARCHIVES
                      if not key.endswith("_us")
                      for t in load_run(key)["trades"]})
    if refetch or not cn_path.exists():
        cn = fetch_cn_bars(need_cn)
        cn.to_parquet(cn_path)
    else:
        cn0 = pd.read_parquet(cn_path)
        have = set(cn0.columns.get_level_values(0))
        missing = [s for s in need_cn if s not in have]
        if missing:
            print(f"补抓 cn 缺失标的 {len(missing)} 个 ...", flush=True)
            cn = fetch_cn_bars(missing, existing=cn0)
            cn.to_parquet(cn_path)
        else:
            cn = cn0
    if refetch or not us_path.exists():
        print("抓取 us 行情 ...", flush=True)
        us = fetch_us_bars(US_SYMBOLS)
        us.to_parquet(us_path)
    else:
        us = pd.read_parquet(us_path)
    return cn, us


def equal_metrics(rs: np.ndarray) -> dict:
    n = int(rs.size)
    wins, losses = rs[rs > 0], rs[rs <= 0]
    return {
        "n": n,
        "expR": float(rs.mean()) if n else None,
        "PF": (float(wins.sum() / abs(losses.sum()))
               if n and losses.sum() != 0 else None),
        "total_r": float(rs.sum()) if n else None,
        "win_rate": float((rs > 0).mean()) if n else None,
    }


def sized_metrics(rs: np.ndarray, es: np.ndarray) -> dict:
    wr = rs * es
    n = int(rs.size)
    wins, losses = wr[wr > 0], wr[wr <= 0]
    return {
        "expR_w": float(wr.sum() / es.sum()) if n else None,
        "PF_w": (float(wins.sum() / abs(losses.sum()))
                 if n and losses.sum() != 0 else None),
        "total_r_w": float(wr.sum()) if n else None,
        "mean_E": float(es.mean()) if n else None,
        "median_E": float(np.median(es)) if n else None,
        "share_E_floor": float((es <= E_FLOOR + 1e-12).mean()) if n else None,
        "share_E_cap": float((es >= E_CAP - 1e-12).mean()) if n else None,
    }


def e_of(rv20: np.ndarray, target: float) -> np.ndarray:
    """红线函数：仓位系数只依赖 (RV20, target)——波动率自变量。
    与已判负 8 项（宽度/利率分位→仓位系数）无共享变量。"""
    return np.clip(target / rv20, E_FLOOR, E_CAP)


def paired_bootstrap(rs: np.ndarray, es: np.ndarray) -> tuple[float, float]:
    """逐笔配对 bootstrap：ΔexpR = Σ(E·r)/Σ(E) − mean(r) 的 95% CI。"""
    rng = np.random.RandomState(BOOT_SEED)
    n = rs.size
    deltas = np.empty(BOOT_N)
    for b in range(BOOT_N):
        idx = rng.randint(0, n, n)
        r, e = rs[idx], es[idx]
        deltas[b] = (r * e).sum() / e.sum() - r.mean()
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return float(lo), float(hi)


def vol_at(closes: pd.Series, signal_date: str, estimator: str) -> float | None:
    """信号日 T（含）收盘口径的年化波动估计（vt-grid 公式逐字复用）。"""
    rets = closes.pct_change(fill_method=None)
    if estimator == "rv20":
        vol = rets.rolling(20).std() * np.sqrt(252.0)
    elif estimator == "ewma97":
        vol = rets.ewm(alpha=0.03, min_periods=20).std() * np.sqrt(252.0)
    else:
        raise ValueError(estimator)
    ts = pd.Timestamp(signal_date)
    if ts not in vol.index:
        return None
    v = float(vol.loc[ts])
    return v if np.isfinite(v) else None


def main() -> None:
    refetch = "--refetch" in sys.argv

    # ── G1 基线复现门槛 ─────────────────────────────────────────────
    print("== G1 基线复现门槛（自算等权 vs 归档 groups）==", flush=True)
    g1: dict = {}
    for key, (n_e, expr_e, pf_e) in G1_EXPECT.items():
        rs = np.array([t["r_net"] for t in closed_trades(key)])
        m = equal_metrics(rs)
        ok = (m["n"] == n_e and abs(m["expR"] - expr_e) < 1e-9
              and abs(m["PF"] - pf_e) < 1e-9)
        g1[key] = {"pass": bool(ok), "ours": m,
                   "expect": {"n": n_e, "expR": expr_e, "PF": pf_e}}
        print(f"  {key}: n={m['n']} expR={m['expR']:.9f} PF={m['PF']:.9f}"
              f" -> {'OK' if ok else 'FAIL'}", flush=True)
    g1_all = all(v["pass"] for v in g1.values())

    # ── 行情抓取（含缓存） ─────────────────────────────────────────
    cn, us = load_bars(refetch)

    # ── G2 年代核对：逐笔入场价 vs 重取开盘价 ──────────────────────
    print("== G2 年代核对（归档 entry_price vs 重取开盘）==", flush=True)
    g2: dict = {}
    g2_mismatch: dict[str, list] = {}
    for key in ARCHIVES:
        market = "us" if key.endswith("_us") else "cn"
        frame = us if market == "us" else cn
        devs, checked = [], 0
        bad: list[dict] = []
        for t in load_run(key)["trades"]:
            sym, ed = t["symbol"], t.get("entry_date")
            ep = t.get("entry_price")
            if sym not in frame.columns.get_level_values(0) or not ed or not ep:
                continue
            ts = pd.Timestamp(ed)
            if ts not in frame.index:
                continue
            o = frame.at[ts, (sym, "open")]
            if np.isfinite(o) and o > 0 and ep > 0:
                dev = abs(o / float(ep) - 1.0)
                devs.append(dev)
                checked += 1
                if dev > G2_RATE_TOL:
                    bad.append({"symbol": sym, "entry_date": ed,
                                "signal_date": t.get("signal_date"),
                                "archived_entry_price": float(ep),
                                "fetched_open": float(o),
                                "dev": float(dev),
                                "r_net": t.get("r_net")})
        g2_mismatch[key] = bad
        devs_a = np.array(devs)
        share_ok = float((devs_a <= G2_RATE_TOL).mean()) if checked else 0.0
        g2[key] = {
            "checked": checked,
            "median_dev": float(np.median(devs_a)) if checked else None,
            "max_dev": float(devs_a.max()) if checked else None,
            "share_within_tol": share_ok,
            "pass": bool(checked > 0 and share_ok >= G2_SHARE_MIN),
        }
        med = g2[key]["median_dev"]
        med_s = f"{med:.5%}" if med is not None else "NA"
        mx = g2[key]["max_dev"]
        mx_s = f"{mx:.3%}" if mx is not None else "NA"
        print(f"  {key}: 核对 {checked} 笔，|开盘/入场价−1| 中位 "
              f"{med_s} 最大 {mx_s}，"
              f"≤{G2_RATE_TOL:.2%} 占比 {share_ok:.1%} -> "
              f"{'OK' if g2[key]['pass'] else 'FAIL'}", flush=True)
    g2_all = all(v["pass"] for v in g2.values())

    # ── X2/X3 交叉验证（收盘 vs 冻结年代源） ───────────────────────
    cross: dict = {}
    kl_path = Path.home() / ".lei_signal_lab/cache/a_share_klines.parquet"
    if kl_path.exists():
        kl = pd.read_parquet(kl_path)
        kl_pv = kl.pivot_table(index="date", columns="symbol", values="close")
        kl_pv.index = pd.to_datetime(kl_pv.index)
        stats = []
        for sym in sorted(set(cn.columns.get_level_values(0))):
            code = tencent_code(sym)
            if code not in kl_pv.columns:
                continue
            a = cn[(sym, "close")].dropna()
            b = kl_pv[code].reindex(a.index)
            mask = a.notna() & b.notna()
            if int(mask.sum()) < 60:
                continue
            ratio = a[mask] / b[mask]
            stats.append({
                "symbol": sym, "overlap_days": int(mask.sum()),
                "median_abs_ret_diff": float(
                    (a[mask].pct_change() - b[mask].pct_change()).abs().median()),
                "level_ratio_cv": float(ratio.std() / ratio.mean()),
            })
        cross["vs_a_share_klines"] = {
            "n_symbols": len(stats),
            "median_ratio_cv": (float(np.median([s["level_ratio_cv"]
                                                 for s in stats]))
                                if stats else None),
            "median_abs_ret_diff": (float(np.median(
                [s["median_abs_ret_diff"] for s in stats])) if stats else None),
            "worst_by_ratio_cv": sorted(
                stats, key=lambda s: -s["level_ratio_cv"])[:5],
        }
    etf_stats = []
    for pq in sorted((RAW / "etf_breadth").glob("*_close.parquet")):
        code = pq.name.replace("_close.parquet", "")
        sym = code[2:] + (".SS" if code.startswith("sh") else ".SZ")
        if sym not in set(cn.columns.get_level_values(0)):
            continue
        b = pd.read_parquet(pq)["close"]
        a = cn[(sym, "close")].dropna()
        b = b.reindex(a.index)
        mask = a.notna() & b.notna()
        if int(mask.sum()) < 60:
            continue
        ratio = a[mask] / b[mask]
        etf_stats.append({
            "symbol": sym, "overlap_days": int(mask.sum()),
            "level_ratio_cv": float(ratio.std() / ratio.mean()),
        })
    cross["vs_etf_breadth_frozen"] = {
        "n_symbols": len(etf_stats),
        "median_ratio_cv": (float(np.median([s["level_ratio_cv"]
                                             for s in etf_stats]))
                            if etf_stats else None),
        "worst_by_ratio_cv": sorted(
            etf_stats, key=lambda s: -s["level_ratio_cv"])[:5],
    }

    # ── RV20 标注（主估计器 rv20 + 稳健臂 ewma97） ─────────────────
    print("== RV20 标注 ==", flush=True)
    samples: dict[str, dict] = {}
    g3: dict = {}
    g3_missing_detail: dict[str, list] = {}
    for key in ARCHIVES:
        market = "us" if key.endswith("_us") else "cn"
        frame = us if market == "us" else cn
        rows = closed_trades(key)
        recs = []
        missing = 0
        g3_missing_detail[key] = []
        for t in rows:
            sym, sd = t["symbol"], t["signal_date"]
            if sym not in frame.columns.get_level_values(0):
                missing += 1
                g3_missing_detail[key].append(
                    {"symbol": sym, "signal_date": sd,
                     "cause": "symbol_not_in_fetched_bars"})
                continue
            s = frame[(sym, "close")].dropna()
            r20 = vol_at(s, sd, "rv20")
            e97 = vol_at(s, sd, "ewma97")
            if r20 is None or e97 is None:
                missing += 1
                g3_missing_detail[key].append(
                    {"symbol": sym, "signal_date": sd,
                     "cause": "signal_date_not_in_series_or_vol_nan"})
                continue
            recs.append({"symbol": sym, "signal_date": sd,
                         "r_net": float(t["r_net"]), "rv20": r20,
                         "ewma97": e97, "market": market})
        miss_rate = missing / max(len(rows), 1)
        g3[key] = {"closed": len(rows), "rv20_missing": missing,
                   "missing_rate": miss_rate,
                   "pass": bool(miss_rate < G3_MISSING_MAX)}
        samples[key] = {
            "recs": recs,
            "rs": np.array([x["r_net"] for x in recs]),
            "rv": np.array([x["rv20"] for x in recs]),
            "ewma97": np.array([x["ewma97"] for x in recs]),
        }
        n_valid = len(recs)
        med = float(np.median(samples[key]["rv"])) if n_valid else float("nan")
        print(f"  {key}: 已平仓 {len(rows)}，RV20 可得 {n_valid}"
              f"（缺 {missing}，{miss_rate:.1%}），RV20 中位 {med:.1%}",
              flush=True)
    g3_all = all(v["pass"] for v in g3.values())

    # ── 主检验：网格（6 样本 × 7 目标 × 2 估计器，全报） ───────────
    print("== 主检验网格 ==", flush=True)
    grid: dict = {}
    for key in sorted(samples):
        s = samples[key]
        if not s["rs"].size:
            continue
        base = equal_metrics(s["rs"])
        grid[key] = {"baseline": base, "cells": {}}
        for est in ESTIMATORS:
            rv = s["rv"] if est == "rv20" else s["ewma97"]
            for tgt in TARGETS:
                es = e_of(rv, tgt)
                sm = sized_metrics(s["rs"], es)
                d_expR = sm["expR_w"] - base["expR"]
                retention = (sm["total_r_w"] / base["total_r"]
                             if base["total_r"] and base["total_r"] > 0 else None)
                pf_ok = (bool(sm["PF_w"] >= base["PF"] - PF_TOLERANCE)
                         if sm["PF_w"] is not None and base["PF"] is not None
                         else None)
                ret_ok = (None if retention is None
                          else bool(retention >= RETENTION_MIN))
                lo = hi = None
                if est == "rv20" or (est == "ewma97" and tgt == ANCHOR):
                    lo, hi = paired_bootstrap(s["rs"], es)
                j1 = bool(lo is not None and lo > 0)
                verdict = None
                if est == "rv20":
                    if j1 and ret_ok is not False and pf_ok is not False:
                        verdict = "passed"
                    elif d_expR > 0 and ret_ok is not False and pf_ok is not False:
                        verdict = "watch"
                    else:
                        verdict = "falsified"
                grid[key]["cells"][f"{est}|{tgt:g}"] = {
                    **sm, "delta_expR": d_expR, "retention": retention,
                    "pf_ok": pf_ok, "ret_ok": ret_ok,
                    "boot_ci_lo": lo, "boot_ci_hi": hi, "verdict": verdict,
                }
        n_pos = sum(1 for tgt in TARGETS
                    if grid[key]["cells"][f"rv20|{tgt:g}"]["delta_expR"] > 0)
        grid[key]["n_pos_targets"] = int(n_pos)
        grid[key]["direction_robust_5of7"] = bool(n_pos >= 5)
        c20 = grid[key]["cells"][f"rv20|{ANCHOR:g}"]
        print(f"  {key}: 基线 expR={base['expR']:.3f} PF={base['PF']:.2f} | "
              f"20%档 ΔexpR={c20['delta_expR']:+.4f} "
              f"CI[{c20['boot_ci_lo']:+.4f},{c20['boot_ci_hi']:+.4f}] "
              f"E均值{c20['mean_E']:.2f} 地板率{c20['share_E_floor']:.0%} "
              f"ret={c20['retention']} verdict={c20['verdict']}", flush=True)

    # ── Q2：F2 的 C 排除问题（锚点 20%/rv20 + 三分位视图） ─────────
    print("== Q2 模块非对称（F2）==", flush=True)
    f2: dict = {}
    for key in sorted(samples):
        s = samples[key]
        if not s["rs"].size:
            continue
        rv, rs = s["rv"], s["rs"]
        order = np.argsort(rv, kind="stable")
        n = order.size
        t1, t2, t3 = order[: n // 3], order[n // 3: 2 * n // 3], order[2 * n // 3:]
        terciles = {
            "n_low_mid_high": [int(t1.size), int(t2.size), int(t3.size)],
            "low_vol_mean_r": float(rs[t1].mean()),
            "mid_vol_mean_r": float(rs[t2].mean()),
            "high_vol_mean_r": float(rs[t3].mean()),
            "high_minus_low": float(rs[t3].mean() - rs[t1].mean()),
        }
        cell = grid[key]["cells"][f"rv20|{ANCHOR:g}"]
        try:
            from scipy.stats import spearmanr
            rho, pval = spearmanr(rv, rs)
            rho, pval = float(rho), float(pval)
        except Exception:  # noqa: BLE001
            rho = pval = None
        f2[key] = {
            "terciles": terciles,
            "spearman_rv20_r": rho, "spearman_p": pval,
            "median_rv20": float(np.median(rv)),
            "delta_expR": cell["delta_expR"],
            "boot_ci": [cell["boot_ci_lo"], cell["boot_ci_hi"]],
        }
        rho_s = "NA" if rho is None else f"{rho:+.3f}"
        print(f"  {key}: 高−低波组 Δr={terciles['high_minus_low']:+.3f}R "
              f"rho={rho_s} ΔexpR={cell['delta_expR']:+.4f} "
              f"CI[{cell['boot_ci_lo']:+.4f},{cell['boot_ci_hi']:+.4f}]",
              flush=True)

    # Q2 预注册判定（机械执行，不掺事后判断）
    a_cn_cell = grid["A_cn"]["cells"][f"rv20|{ANCHOR:g}"]
    c_cn_cell = grid["C_cn"]["cells"][f"rv20|{ANCHOR:g}"]
    a_j1 = bool(a_cn_cell["boot_ci_lo"] is not None
                and a_cn_cell["boot_ci_lo"] > 0)
    if a_j1 and c_cn_cell["boot_ci_hi"] is not None \
            and c_cn_cell["boot_ci_hi"] <= CI_C_EXCLUSION_UB:
        f2_verdict = "C 应排除于 vt（非对称成立）"
    elif c_cn_cell["boot_ci_lo"] is not None and c_cn_cell["boot_ci_lo"] > 0:
        f2_verdict = "C 同样适用 vt"
    else:
        f2_verdict = "不确定（CI 不支持任一方向）"

    # ── 事后补充臂（post-hoc，非预注册；因 G2 在 C_cn 失败而加，透明披露）──
    # 内容：① G2 超限笔明细（已在 g2_mismatch）；② 剔除 G2 超限笔后的
    # C_cn 稳健臂（基线 + 锚点格 + bootstrap CI + F2 三分位，两臂对称剔除，
    # 逐笔剔除键 = symbol+signal_date+entry_date）；③ G3 缺 RV20 笔明细。
    # 未改任何预注册判定线的数值或方向。
    print("== 事后补充：C_cn 剔除 G2 超限笔稳健臂 ==", flush=True)
    bad_keys = {(b["symbol"], b["signal_date"]) for b in g2_mismatch["C_cn"]}
    s = samples["C_cn"]
    keep = [x for x in s["recs"] if (x["symbol"], x["signal_date"]) not in bad_keys]
    # symbol+signal_date 定位；002326.SZ 同日两笔对称剔除，无偏
    rs_x = np.array([x["r_net"] for x in keep])
    rv_x = np.array([x["rv20"] for x in keep])
    base_x = equal_metrics(rs_x)
    es_x = e_of(rv_x, ANCHOR)
    sm_x = sized_metrics(rs_x, es_x)
    d_x = sm_x["expR_w"] - base_x["expR"]
    lo_x, hi_x = paired_bootstrap(rs_x, es_x)
    order_x = np.argsort(rv_x, kind="stable")
    nx = order_x.size
    t1x, t3x = order_x[: nx // 3], order_x[2 * nx // 3:]
    try:
        from scipy.stats import spearmanr as _sr
        rho_x = float(_sr(rv_x, rs_x)[0])
    except Exception:  # noqa: BLE001
        rho_x = None
    posthoc = {
        "declared_posthoc": True,
        "reason": ("G2 在 C_cn 失败（5/173 笔价位年代漂移，集中在多分红"
                   "标的 000568.SZ/002326.SZ 的 qfq 方法论差异）；X2 收益率"
                   "层交叉验证一致（68 标的中位 |Δret|=0.0bp、最差 3.5bp），"
                   "价位漂移来自分段常数复权基数差，收益率（RV20 的输入）"
                   "基本不受影响；仍按透明原则做剔除稳健臂"),
        "g2_mismatch_trades": g2_mismatch,
        "C_cn_excl_g2mismatch": {
            "n": int(rs_x.size), "excluded": int(s["rs"].size - rs_x.size),
            "baseline": base_x,
            "anchor_cell_rv20_20pct": {
                **sm_x, "delta_expR": d_x,
                "retention": (sm_x["total_r_w"] / base_x["total_r"]
                              if base_x["total_r"] > 0 else None),
                "boot_ci_lo": lo_x, "boot_ci_hi": hi_x,
            },
            "terciles_high_minus_low": float(
                rs_x[t3x].mean() - rs_x[t1x].mean()),
            "spearman_rv20_r": rho_x,
        },
    }
    print(f"  C_cn_excl: n={rs_x.size} 剔除 {s['rs'].size - rs_x.size} 笔，"
          f"ΔexpR={d_x:+.4f} CI[{lo_x:+.4f},{hi_x:+.4f}] "
          f"高−低波组 Δr={posthoc['C_cn_excl_g2mismatch']['terciles_high_minus_low']:+.3f}R",
          flush=True)

    results = {
        "protocol": {
            "targets": list(TARGETS), "anchor": ANCHOR,
            "estimators": list(ESTIMATORS),
            "E_formula": "clip(target/RV20_signal_date_close, 0.25, 1)",
            "boot": {"n": BOOT_N, "seed": BOOT_SEED},
            "retention_min": RETENTION_MIN, "pf_tolerance": PF_TOLERANCE,
            "g2": {"rate_tol": G2_RATE_TOL, "share_min": G2_SHARE_MIN},
            "g3_missing_max": G3_MISSING_MAX,
            "ci_c_exclusion_ub": CI_C_EXCLUSION_UB,
        },
        "gates": {"G1_baseline": g1, "G1_pass": bool(g1_all),
                  "G2_vintage": g2, "G2_pass": bool(g2_all),
                  "G3_rv20": g3, "G3_pass": bool(g3_all),
                  "all_pass": bool(g1_all and g2_all and g3_all)},
        "groups_net_disclose": {
            "note": ("非 G1 样本的归档 net 汇总（含被归档剔除的基准自身"
                     "交易，与逐笔子集不可直接对比，仅披露）"),
            **{k: {"n": v[0], "expR": v[1], "PF": v[2]}
               for k, v in GROUPS_NET_DISCLOSE.items()},
        },
        "cross_checks": cross,
        "g3_missing_trades": {
            "note": ("缺 RV20 笔明细（退市/长期停牌标的，腾讯 qfq 无该段"
                     "数据；两臂对称剔除）"),
            "detail": g3_missing_detail,
        },
        "grid": grid,
        "f2": f2,
        "f2_verdict": f2_verdict,
        "posthoc": posthoc,
        "d_module": {"n_cn": 2, "tested": False,
                     "note": "cn 个股池默认参数十年 2 笔，样本不足不检验"},
        "red_line_self_check": (
            "仓位系数 E 的输入仅 (target, RV20)；全程未使用 b50/b200/宽度/"
            "利率分位——与已判负 8 项（宽度/利率→仓位系数）自变量不同类。"),
    }
    payload = json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True,
                         default=float)
    out_path = HERE / "vt_signal_sizing_results.json"
    out_path.write_text(payload, encoding="utf-8")
    digest = hashlib.md5(payload.encode("utf-8")).hexdigest()
    print(f"\n落盘: {out_path}")
    print(f"md5(canonical json) = {digest}")
    print(f"门槛: G1={g1_all} G2={g2_all} G3={g3_all}")
    print(f"F2 判定: {f2_verdict}")


if __name__ == "__main__":
    main()
