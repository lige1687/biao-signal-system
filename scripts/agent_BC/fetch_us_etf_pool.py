#!/usr/bin/env python3
"""任务 BC（第一步）：模块B 美股核心 ETF 池数据抓取 · 协议跑前写死，跑后不得调。

【池（跑前写死）】8 只美股核心 ETF：QQQ、SPY、DIA、IWM、XLK、XLF、XLV、XLE。
全史（上市起）。数据客观不可得的标的剔除并逐只记录（唯一合法剔除理由，
禁止删标的洗结果）。

【数据】复用仓库现有 provider 先例（agent_AD/prep_data.py 同一入口）：
src/lei_signal/data/providers.py::YahooPriceProvider（HEAD 只读 import，不改仓库）
= yfinance Ticker.history(period="max", interval="1d", auto_adjust=True,
actions=False) + validate_bars（OHLC 合法性/非正价格/去重排序，违反即抛错）。
落盘到本任务自己的目录 docs/experiments/raw/agent_BC/pool/
（{SYM}.bars.parquet + {SYM}.bars.meta.json），不动 ~/.lei_signal_lab 共享缓存。
额外把 b20 标签源 breadth_sp500.parquet 复制进本任务目录（回测脚本只读自己的
副本，隔离外部会话并发修改共享缓存的哈希风险）。

【交叉校验（跑前写死，照抄 agent_AD/run_precheck.py::data_crosscheck 方法：
重叠段日收益相关系数 + 平均绝对差）】
  - 管线校验（必须过）：^GSPC 用同一 provider 抓，与
    ~/.lei_signal_lab/cache/^GSPC.bars.parquet（yahoo_v8+tencent_rt，
    2024-09-04~2026-09-03，502 根）重叠段比对。
  - 池内标的独立参照（各有本地独立源的必须过）：
      SPY ↔ ~/.lei_signal_lab/cache/timing/SPY.parquet（1993-01-29~2026-08-26）
      QQQ ↔ ~/.lei_signal_lab/cache/timing/QQQ.parquet（1999-03-10~2026-08-26）
      XLK ↔ ~/.lei_signal_lab/backtest_pool/XLK.bars.parquet（yahoo_v8，
             2016-08-24~2026-08-24）
    DIA/IWM/XLF/XLV/XLE 无独立本地参照，登记"依赖管线校验"（管线由 ^GSPC +
    3 只池内标的共同验证）。
  - 通过线（写死）：重叠 ≥200 天 ∧ 日收益 corr ≥ 0.995 ∧ 平均绝对差 ≤0.15 个
    百分点。任何"必须过"项失败 → SystemExit（回测不跑，判定只能是
    样本/数据不足），不修数、不重抓洗结果。
  - 已知口径差登记：auto_adjust 复权基准随抓取时点漂移（新分红发生后历史
    复权价整体平移），重叠段日收益在除权日附近可有微小差异——这正是用
    日收益相关而非价格水平比对的原因。

【跳变扫描（AK 机械规则原样执行，登记 + 兜底停机）】隔夜收盘比 close[t]/
close[t-1] > 1.5 或 < 1/1.5 视为复权断裂（AQ 任务先例）。auto_adjust 数据
预期为 0；若任何池内标的检出 → 登记并 SystemExit（不静默修平）。

【OHLC 包络线微修复（首跑失败后、任何结果产生前预注册的机械规则）】
首跑实测：SPY 等 7 只在 auto_adjust 长历史上被 validate_bars 拒收，逐行核验
违规量级全部为浮点机器精度（SPY 最大绝对违规 1.42e-14，相对 1.6e-16）——
原始数据里 high/low 与 open/close 相等的日子，复权除法在两次乘除链上产生
1 个 ulp 差。机械修复规则（写死）：逐行计算包络违规（env_hi-high 与
low-env_lo），全部违规绝对量 ≤ 0.01 美元的行执行 high=max(high,open,close)、
low=min(low,open,close)；任何违规 > 0.01 美元（真实数据错误量级）→ 登记
并 SystemExit。逐只记录修复行数与最大违规量级，进入 manifest。

【网络重试】Yahoo 间歇性限流（"possibly delisted; no price data found"
瞬时错误）非数据问题，两层应对（写死）：
  a) 主路 period=max 失败 → 兜底 history(start=1990-01-01)（实测限流时
     仍可用；ETF 全部 1990 年后上市，覆盖等价；同一 auto_adjust 口径与
     validate_bars 校验）；
  b) 标的间 sleep 60s（实测限流按静默期恢复，快节奏重试反而加剧限流），
     仍失败的标的整轮重试最多 4 轮（轮间 240s）；
  c) 断点续跑：池目录已有本任务落盘副本（parquet+meta 成对）的标的直接
     复用磁盘数据、不发网络请求；池内标的 4 轮后仍失败才记"数据客观
     不可得"（任务书唯一合法剔除理由，逐只记录错误原文）；管线校验标的
     ^GSPC 失败则整体停机。不编造数据。

【大幅日扫描（仅登记不判失败）】|单日收益|>12% 的日期逐只列出。美股 ETF
无涨跌停制度，2008-10/2020-03 等时段大幅日合法存在，与 A 股池的 20cm 板
"合法大幅日"同一登记性质。

【红线】参数零改动（本脚本只管数据）；不改任何现有文件与共享缓存；
不编造数据（网络失败即报错退出）；输出只新增 docs/experiments/raw/agent_BC/。
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(REPO / "src"))

from lei_signal.data.providers import YahooPriceProvider  # noqa: E402

RAW = REPO / "docs/experiments/raw/agent_BC"
POOL_DIR = RAW / "pool"
MANIFEST = RAW / "pool_manifest.json"

POOL = ("QQQ", "SPY", "DIA", "IWM", "XLK", "XLF", "XLV", "XLE")

CACHE = Path.home() / ".lei_signal_lab/cache"
CROSS_REFS = {
    "SPY": CACHE / "timing/SPY.parquet",
    "QQQ": CACHE / "timing/QQQ.parquet",
    "XLK": Path.home() / ".lei_signal_lab/backtest_pool/XLK.bars.parquet",
}
PIPELINE_REF = CACHE / "^GSPC.bars.parquet"
BREADTH_SRC = CACHE / "timing/breadth_sp500.parquet"

XCHECK_MIN_OVERLAP = 200
XCHECK_MIN_CORR = 0.995
XCHECK_MAX_MAD_PP = 0.15

JUMP_HI = 1.5          # 隔夜收盘比上界
JUMP_LO = 1.0 / 1.5    # 下界
BIG_DAY = 0.12         # 大幅日 |单日收益| 阈值（登记性质）

ENV_REPAIR_MAX_USD = 0.01   # 包络微修复上限（绝对美元）；超过即硬失败
NET_RETRY_ROUNDS = 4        # Yahoo 瞬时限流整轮重试
NET_SYMBOL_SLEEP = 60.0     # 标的间隔（实测限流按静默期恢复，拉长间隔）
NET_ROUND_SLEEP = 240.0     # 轮间隔


def fetch(provider: YahooPriceProvider, symbol: str) -> pd.DataFrame:
    """provider 主路（period=max）+ 等价兜底（start=1990，实测限流时仍可用）。

    实测（2026-09-04）：Yahoo chart 端点 period=max 间歇性返回空（"possibly
    delisted"假错误，实为限流），同一时刻 history(start=1990-01-01) 正常返回
    与 period=max 逐日一致的全史（ETF 全部 1990 后上市，覆盖等价）。
    """
    try:
        data = provider.fetch(symbol, min_rows=300)
    except Exception:
        import yfinance as yf

        raw = yf.Ticker(symbol).history(start="1990-01-01", interval="1d",
                                         auto_adjust=True, actions=False)
        if raw is None or len(raw) == 0:
            raise
        from lei_signal.data.validation import validate_bars

        raw = raw.rename(columns=str.lower)
        raw, _report = validate_bars(raw, symbol=symbol, provider="yahoo_v8_fallback",
                                     adjusted=True, min_rows=300)
        data = type("D", (), {"bars": raw[["open", "high", "low", "close", "volume"]]})()
    bars = data.bars[["open", "high", "low", "close", "volume"]].copy()
    bars = bars[~bars.index.duplicated(keep="last")].sort_index()
    return bars


def crosscheck(mine: pd.Series, ref_path: Path) -> dict:
    """AD 方法：重叠段日收益 corr + 平均绝对差（百分点）。"""
    ref = pd.read_parquet(ref_path)["close"].sort_index()
    joined = pd.concat([mine.sort_index(), ref], axis=1, keys=["mine", "ref"]).dropna()
    r_m = joined["mine"].pct_change(fill_method=None)
    r_r = joined["ref"].pct_change(fill_method=None)
    mask = r_m.notna() & r_r.notna()
    n = int(mask.sum())
    if n == 0:
        return {"ref": str(ref_path), "overlap_days": 0, "passed": False,
                "reason": "无重叠"}
    corr = float(np.corrcoef(r_m[mask], r_r[mask])[0, 1])
    mad = float(np.mean(np.abs(r_m[mask] - r_r[mask])) * 100)
    passed = bool(n >= XCHECK_MIN_OVERLAP and corr >= XCHECK_MIN_CORR
                  and mad <= XCHECK_MAX_MAD_PP)
    return {"ref": str(ref_path), "overlap_days": n,
            "daily_return_corr": round(corr, 6),
            "mean_abs_diff_pp": round(mad, 5), "passed": passed}


def scans(bars: pd.DataFrame) -> dict:
    ret = bars["close"].pct_change(fill_method=None)
    # AK 规则原口径：隔夜比 = close[t]/close[t-1]（= 1 + 单日收益）
    jumps = [{"date": str(k.date()), "ret": round(float(v), 4)}
             for k, v in ret.items() if pd.notna(v) and (v >= JUMP_HI - 1 or v <= JUMP_LO - 1)]
    big = [{"date": str(k.date()), "ret": round(float(v), 4)}
           for k, v in ret.items() if pd.notna(v) and abs(v) > BIG_DAY]
    return {"corp_action_jumps": jumps, "big_days_gt12pct": big}


def repair_envelope(bars: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """预注册 OHLC 包络微修复：仅修 ≤0.01 美元的浮点 ulp 级违规，>0.01 即硬失败。"""
    df = bars.copy()
    env_hi = df[["open", "close"]].max(axis=1)
    env_lo = df[["open", "close"]].min(axis=1)
    viol_hi = (env_hi - df["high"]).clip(lower=0.0)
    viol_lo = (df["low"] - env_lo).clip(lower=0.0)
    viol = pd.concat([viol_hi, viol_lo], axis=1).max(axis=1)
    n_bad = int((viol > 0).sum())
    if n_bad == 0:
        return df, {"repaired_rows": 0, "max_abs_violation_usd": 0.0}
    mx = float(viol.max())
    if mx > ENV_REPAIR_MAX_USD:
        raise SystemExit(f"包络违规 {mx:.4f} 美元超过修复上限 "
                         f"{ENV_REPAIR_MAX_USD}（真实数据错误，不修复）")
    mask = viol > 0
    df.loc[mask, "high"] = df.loc[mask, ["high", "open", "close"]].max(axis=1)
    df.loc[mask, "low"] = df.loc[mask, ["low", "open", "close"]].min(axis=1)
    return df, {"repaired_rows": n_bad, "max_abs_violation_usd": float(f"{mx:.3e}")}


def fetch_all(provider: YahooPriceProvider,
              symbols: list[str]) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """带整轮重试的批量抓取（Yahoo 瞬时限流非数据问题）+ 断点续跑。

    续跑规则：池目录已有本任务落盘副本（parquet+meta 成对存在）的标的直接
    复用磁盘数据，不发网络请求（分钟级窗口内行情不可变）；缺的才抓。
    """
    fetched: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}
    pending = list(symbols)
    for round_no in range(1, NET_RETRY_ROUNDS + 1):
        still: list[str] = []
        for sym in pending:
            cache_fp = POOL_DIR / f"{sym}.bars.parquet"
            meta_fp = POOL_DIR / f"{sym}.bars.meta.json"
            if cache_fp.exists() and meta_fp.exists():
                fetched[sym] = pd.read_parquet(cache_fp)
                print(f"[resume] {sym} 复用磁盘副本", flush=True)
                continue
            try:
                fetched[sym] = fetch(provider, sym)
            except Exception as exc:
                errors[sym] = str(exc)[:300]
                still.append(sym)
            time.sleep(NET_SYMBOL_SLEEP)
        pending = still
        if not pending:
            break
        print(f"[retry] 第 {round_no} 轮后仍失败: {pending}", flush=True)
        if pending and round_no < NET_RETRY_ROUNDS:
            time.sleep(NET_ROUND_SLEEP)
    return fetched, errors


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    POOL_DIR.mkdir(parents=True, exist_ok=True)
    provider = YahooPriceProvider()

    failures: list[str] = []
    manifest: dict = {
        "task": "模块B 美股核心 ETF 池数据（任务 BC 第一步）",
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "YahooPriceProvider (yfinance period=max 1d auto_adjust actions=False)",
        "pool_preregistered": list(POOL),
        "symbols": [],
        "pipeline_check": None,
    }

    # ---------- 管线校验 + 池内标的：同一批量抓取 ----------
    got, errors = fetch_all(provider, ["^GSPC", *POOL])
    if "^GSPC" not in got:
        raise SystemExit(f"管线校验标的 ^GSPC 抓取失败: {errors.get('^GSPC', '')}")

    gspc = got["^GSPC"]
    gspc.to_parquet(POOL_DIR / "^GSPC.bars.parquet")
    (POOL_DIR / "^GSPC.bars.meta.json").write_text(json.dumps({
        "symbol": "^GSPC", "kind": "bars", "provider": "yahoo_v8(auto_adjust)",
        "rows": len(gspc), "note": "管线校验用（非池内标的）",
        "first_date": str(gspc.index[0]), "last_date": str(gspc.index[-1]),
    }, ensure_ascii=False, indent=1))
    manifest["pipeline_check"] = {
        "symbol": "^GSPC", "rows": len(gspc),
        "range": [str(gspc.index[0].date()), str(gspc.index[-1].date())],
        **crosscheck(gspc["close"], PIPELINE_REF),
    }
    if not manifest["pipeline_check"]["passed"]:
        failures.append(f"管线校验未过: {manifest['pipeline_check']}")

    for sym in POOL:
        if sym not in got:
            # 数据客观不可得：登记后剔除（任务书唯一合法剔除理由）
            manifest["symbols"].append({"symbol": sym, "ok": False,
                                        "error": errors.get(sym, "unknown")})
            continue
        bars, repair_meta = repair_envelope(got[sym])
        sc = scans(bars)
        entry = {
            "symbol": sym, "ok": True, "rows": len(bars),
            "start": str(bars.index[0].date()), "end": str(bars.index[-1].date()),
            "adjusted": True, "crosscheck": None, "crosscheck_note": None,
            "envelope_repair": repair_meta, **sc,
        }
        if sym in CROSS_REFS:
            entry["crosscheck"] = crosscheck(bars["close"], CROSS_REFS[sym])
            if not entry["crosscheck"]["passed"]:
                failures.append(f"{sym} 交叉校验未过: {entry['crosscheck']}")
        else:
            entry["crosscheck_note"] = "无独立本地参照，依赖管线校验"
        if sc["corp_action_jumps"]:
            failures.append(f"{sym} 检出复权断裂跳变 {len(sc['corp_action_jumps'])} 处")
        manifest["symbols"].append(entry)
        bars.to_parquet(POOL_DIR / f"{sym}.bars.parquet")
        (POOL_DIR / f"{sym}.bars.meta.json").write_text(json.dumps({
            "symbol": sym, "kind": "bars", "provider": "yahoo_v8(auto_adjust)",
            "rows": len(bars),
            "fetched_at": manifest["fetched_at_utc"],
            "first_date": str(bars.index[0]), "last_date": str(bars.index[-1]),
        }, ensure_ascii=False, indent=1))
        print(f"[{sym}] {entry['start']}~{entry['end']} rows={len(bars)} "
              f"jumps={len(sc['corp_action_jumps'])} "
              f"bigdays={len(sc['big_days_gt12pct'])} "
              f"xcheck={'-' if not entry['crosscheck'] else entry['crosscheck']['passed']}",
              flush=True)

    # ---------- b20 标签源副本（隔离并发修改） ----------
    breadth = pd.read_parquet(BREADTH_SRC)
    b20 = breadth[["b20"]].dropna()
    b20.to_parquet(POOL_DIR / "breadth_sp500_b20.parquet")
    manifest["b20_label_source"] = {
        "file": "pool/breadth_sp500_b20.parquet",
        "origin": str(BREADTH_SRC),
        "range": [str(b20.index[0].date()), str(b20.index[-1].date())],
        "rows": len(b20),
    }

    n_ok = sum(1 for s in manifest["symbols"] if s["ok"])
    manifest["n_ok"] = n_ok
    manifest["failures"] = failures
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1))

    print(f"\n池内可得 {n_ok}/{len(POOL)}；管线校验 "
          f"{'过' if manifest['pipeline_check']['passed'] else '未过'}")
    if failures:
        print("失败项:")
        for f in failures:
            print("  -", f)
        raise SystemExit(1)
    print(f"manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
