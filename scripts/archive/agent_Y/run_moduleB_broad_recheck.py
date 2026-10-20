#!/usr/bin/env python3
"""债务一复核：模块B（密集突破）宽基7池 cb40/cl8% 正收益是否被污染数据撑起。
预注册判定标准（2026-09-03 跑前写死，跑后不得调整）。

【背景】
b-adaptation 报告（2026-08-26）宽基ETF 7 池（510050/510300/510500/512100/
159901/159915/588000）唯一 IS 为正档 cb40/cl8%：N=37、expR=+0.944、IS=+0.281、
OOS=+2.326、排top1后+0.546，top1=512100.SS（+15.8R，占45%）。
跳变审计（data-quality-jump-audit-2026-09-02.md）认定 512100/510500 为污染
标的，要求在修平数据上复核。审计的 13 个跳变全部位于 ~/.lei_signal_lab/cache/
/timing（宽度择时缓存）；而模块B回测读的是 ~/.lei_signal_lab/backtest_pool
（回测深池）——两套存储是否同污，本脚本先用数据说话（不预设结论）。

【修平方法（复用审计预注册函数，不重新发明）】
flatten_jumps：对跳变日 D，ratio=close[D]/close[D-1]，D 及之后全部 OHLC 同除
ratio（等价于跳变日收益置0），多跳变按时间序。与审计脚本逐字一致。

【三个变体（一次全部跑完，无挑选）】
V0 基线复现：backtest_pool 现状数据，原参数原框架重跑（应复现 2026-08-26
    归档数字；池文件自 2026-08-24/25 落盘后未再变更，mtime 已核）。
V1 审计修平处置：对池内 7 标的逐个检查审计 13 个跳变日（涉宽基池的为
    510500 两个、512100 一个）当日实际单日收益；仅当 |单日|>12%（超涨跌停
    物理限制，即审计"必然复权断裂"判据）时执行 flatten。若跳变不存在则
    不做任何修改（机械对无跳变日期除以 ~1.0 的比值会人为扭曲数据，禁止）。
V2 跨存储敏感：把 512100.SS/510500.SS 的 OHLC 整体替换为 timing 缓存
    flatten_jumps 修平版（共同交易日，volume 沿用池数据），其余 5 只不动。
    这是"被污染那套数据修平后的版本"代入模块B框架的字面执行。

【预注册判定标准（对 V1 与 V2 分别适用；量级参照原报告判据体系）】
- 「45% 正收益仍成立」：该变体 expR>0 且 排除512100后剩余交易平均R>0
  （ex-512100>0，与原报告 ex-top1>0 判据同构）；
- 「不成立」：该变体 expR<=0，或 ex-512100<=0（正收益完全由 512100 一只
  撑起，其余标的合起来不能证明池子有效）；
- 「证据不足」：数据无法构建（跳变日不在索引/共同交易日不足/特征计算
  失败）或 N<30（原报告样本下限）。
判定由脚本按上述布尔条件机械输出，跑完不改线。

【红线】只读 ~/.lei_signal_lab 缓存与 src/ 生产代码（运行时注入替换帧，
不落盘不改文件）；不产生买卖点；输出仅新增 JSON。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

POOL_ROOT = Path.home() / ".lei_signal_lab/backtest_pool"
TIMING_ROOT = Path.home() / ".lei_signal_lab/cache/timing"
OUT_DIR = REPO / "docs/experiments/raw/agent_Y_pollution_recheck"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "moduleB_broad_recheck.json"

# 宽基 7 池 + 审计跳变清单中涉池标的（审计 JUMPS 的子集，逐字照抄）
POOL_BROAD = (
    "510050.SS", "510300.SS", "510500.SS", "512100.SS",
    "159901.SZ", "159915.SZ", "588000.SS",
)
AUDIT_JUMPS = {  # data-quality-jump-audit-2026-09-02.md §2 修（13个）全表
    "159928.SZ": ["2021-06-25"],
    "510500.SS": ["2015-04-15", "2022-08-29"],
    "512010.SS": ["2021-06-28"],
    "512100.SS": ["2022-09-05"],
    "512200.SS": ["2024-08-12"],
    "512480.SS": ["2021-03-29", "2026-07-03"],
    "512690.SS": ["2021-05-17", "2021-12-31"],
    "512800.SS": ["2025-07-07"],
    "515880.SS": ["2026-02-03", "2026-07-06"],
}
REPAIR_THRESHOLD = 0.12  # 审计"超涨跌停物理限制"判据：|单日|>12% 才视为断裂

# 原始归档数字（b_spectrum_summary.json 宽基ETF 行，用于复现核对）
ORIGINAL = {"N": 37, "expR": 0.9440623764835745, "IS": 0.28089447203379264,
            "OOS": 2.32566217742062, "ex_top1": 0.5457184526833196,
            "top1": "512100.SS"}


def flatten_jumps(bars: pd.DataFrame, dates: list[str]) -> pd.DataFrame:
    """审计预注册修平函数逐字复刻（多跳变按时间序）。"""
    df = bars.copy()
    for d in sorted(dates):
        ts = pd.Timestamp(d)
        i = df.index.get_loc(ts)
        prev_close = df["close"].iloc[i - 1]
        ratio = float(df["close"].iloc[i] / prev_close)
        mask = df.index >= ts
        for c in ("open", "high", "low", "close"):
            df.loc[mask, c] = df.loc[mask, c] / ratio
    return df


def load_pool_bars(sym: str) -> pd.DataFrame:
    df = pd.read_parquet(POOL_ROOT / f"{sym}.bars.parquet")
    return df[~df.index.duplicated(keep="last")].sort_index()


def load_timing_bars(sym: str) -> pd.DataFrame:
    df = pd.read_parquet(TIMING_ROOT / f"{sym.split('.')[0]}.parquet")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for col in ("high", "low"):
        if col not in df.columns:
            df[col] = (df[["open", "close"]].max(axis=1) if col == "high"
                       else df[["open", "close"]].min(axis=1))
    return df[["open", "high", "low", "close"]]


def audit_jump_presence(bars: pd.DataFrame, dates: list[str]) -> list[dict]:
    """逐跳变日检查池数据当日实际单日收益（>12% 才算断裂存在）。"""
    out = []
    for d in sorted(dates):
        ts = pd.Timestamp(d)
        try:
            i = bars.index.get_loc(ts)
        except KeyError:
            out.append({"date": d, "in_index": False, "single_day": None,
                        "jump_present": False})
            continue
        ret = float(bars["close"].iloc[i] / bars["close"].iloc[i - 1] - 1.0)
        out.append({"date": d, "in_index": True, "single_day": round(ret, 6),
                    "jump_present": bool(abs(ret) > REPAIR_THRESHOLD)})
    return out


def build_v1(bars: pd.DataFrame, presence: list[dict]) -> tuple[pd.DataFrame, list[str]]:
    """仅对池内真实存在的跳变执行审计修平（无跳变则原样返回）。"""
    real = [p["date"] for p in presence if p["jump_present"]]
    if not real:
        return bars, []
    return flatten_jumps(bars, real), real


def build_v2(pool_bars: pd.DataFrame, timing_fixed: pd.DataFrame) -> pd.DataFrame:
    """OHLC 替换为 timing 修平版（共同交易日），volume 等其余列沿用池数据；
    帧裁到共同交易日（保持 7 池共同数据范围可比）。"""
    common = pool_bars.index.intersection(timing_fixed.index)
    out = pool_bars.loc[common].copy()
    out[["open", "high", "low", "close"]] = timing_fixed.loc[
        common, ["open", "high", "low", "close"]].values
    return out


def summarize(result: dict) -> dict:
    """直接读 execute_run 的生产指标分组（与原始报告逐字同口径）+ 512100 归因。"""
    g = result["groups"]["True"]
    ov = g["总览"][0]
    n = ov["trade_count"]
    total_r = ov["total_r"] or 0.0
    exp = ov["expectancy_r"]
    inout = {s["label"]: s for s in g["样本内外"]}
    is_row = inout.get("样本内（<= 切分日）")
    oos_row = inout.get("样本外（> 切分日）")
    by_sym = {s["label"]: s for s in g["按标的"]}
    sym = by_sym.get("512100.SS")
    n512 = sym["trade_count"] if sym else 0
    r512 = sym["total_r"] or 0.0 if sym else 0.0
    ex_n = n - n512
    ex_exp = ((total_r - r512) / ex_n) if ex_n else None
    share = (r512 / total_r) if total_r else None
    # 512100 逐笔（生产 closed 口径：非开放且非无效风险/涨停跳过）
    t512 = [
        {"signal_date": t["signal_date"], "entry_date": t["entry_date"],
         "exit_date": t["exit_date"], "exit_reason": t["exit_reason"],
         "r_net": round(t["r_net"], 4)}
        for t in result["trades"]
        if t["symbol"] == "512100.SS" and t["exit_date"] is not None
        and t["exit_reason"] not in ("invalid_nonpositive_risk",
                                     "skipped_limit_up_at_entry")
    ]
    # 预注册判定（跑前写死的布尔条件，机械输出）
    if n < 30:
        verdict = "证据不足(N<30)"
    elif exp is not None and exp > 0 and ex_exp is not None and ex_exp > 0:
        verdict = "45%正收益仍成立"
    else:
        verdict = "不成立"
    return {
        "N": n,
        "open_count": ov["open_count"],
        "expR": round(exp, 6) if exp is not None else None,
        "total_R": round(total_r, 4),
        "win_rate": ov["win_rate"],
        "profit_factor": ov["profit_factor"],
        "IS_expR": is_row["expectancy_r"],
        "IS_n": is_row["trade_count"] if is_row else 0,
        "OOS_expR": oos_row["expectancy_r"],
        "OOS_n": oos_row["trade_count"] if oos_row else 0,
        "ex_512100_expR": round(ex_exp, 6) if ex_exp is not None else None,
        "ex_512100_n": ex_n,
        "by_symbol": {
            s["label"]: {"n": s["trade_count"],
                         "total_r": round(s["total_r"] or 0.0, 4),
                         "expR": s["expectancy_r"]}
            for s in sorted(g["按标的"], key=lambda x: -(x["total_r"] or 0))
        },
        "trades_512100": t512,
        "r512100_share": round(share, 4) if share is not None else None,
        "data_range": result["data_range"],
        "funnel": result["funnel"],
        "pre_registered_verdict": verdict,
    }


def install_pre_revert_modules() -> list[str]:
    """2026-09-01 回退事故后，src 树的规则模块是旧版（v1 纠缠度口径，
    缺 _bandwidth_condition、ENTRY_* 常量、compute_reward_risk 的 gaps 形参，
    engine 无法导入/调用）。把归档时代的工作区版注册进 sys.modules：
    来源 stash@{0}（已原样提取到 scripts/agent_Y/pre_revert_rules/，并与其
    独立保存副本 stop_loss_matrix/pre_revert_modules 逐字节核对一致）。
    只改本进程内存，不改仓库任何文件；如实记入输出 JSON。"""
    import importlib.util

    base = REPO / "scripts/agent_Y/pre_revert_rules"
    installed = []
    for name in ("first_ma_pullback", "dense_breakout", "reward_risk_filter",
                 "tradability_gate", "two_b_reversal", "volume", "lei_color"):
        modname = f"lei_signal.rules.{name}"
        if modname in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(modname, base / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[modname] = mod
        spec.loader.exec_module(mod)
        installed.append(modname)
    return installed


def patch_ledger_to_archive_v2() -> None:
    """把规则账本指回归档时代的 configs/rules.v2.yaml（提交 1a321ce 版，
    已原样存为 scripts/agent_Y/rules.v2.archive-1a321ce.yaml）。
    当前树的 configs/rules.v1.yaml 是回退事故前的旧账本（cb 默认 120），
    service 的参数覆盖锚点（cb: 126 / cl: 0.02）在 v1 上不存在。归档运行
    用 v2 账本 + 原始 overrides 机制（文本替换→临时账本→跑完恢复），
    与 run_b_spectrum.py 当时的执行路径逐字一致。"""
    from lei_signal.domain import rules_config as rc

    v2 = REPO / "scripts/agent_Y/rules.v2.archive-1a321ce.yaml"
    if not v2.exists():
        raise FileNotFoundError(f"归档账本缺失: {v2}")
    rc._default_config_path = lambda: v2  # type: ignore[assignment]
    rc.load_ruleset.cache_clear()


def run_variant(frames_bars: dict[str, pd.DataFrame], tag: str) -> dict:
    """注入帧后调用生产 execute_run（原框架），随后清理模块级缓存防串扰。"""
    from lei_signal.backtest import service as svc
    from lei_signal.features.indicators import compute_features
    from lei_signal.rules.lei_color import classify_colors

    frames = {}
    for sym, bars in sorted(frames_bars.items()):
        frames[sym] = classify_colors(compute_features(bars))
    svc._FRAME_CACHE = frames
    svc._EVENT_CACHE = {}
    svc._PIVOT_CACHE = {}
    svc._GAP_CACHE = {}
    patch_ledger_to_archive_v2()
    params = svc.BacktestParams(
        symbols=tuple(sorted(frames_bars)),
        module="B",
        rr_min=None,
        entry_variant="breakout",
        exit_variant="b3_dual",
        fee_label="standard",
        limit_guard=True,
        volume_confirm=False,
        volume_confirm_window=1,
        overrides=(("consolidation_bars", 40), ("cluster_threshold", 0.08)),
    )
    result = svc.execute_run(params)
    summary = summarize(result)
    summary["variant"] = tag
    return summary


def main() -> None:
    installed = install_pre_revert_modules()
    pool_bars = {s: load_pool_bars(s) for s in POOL_BROAD}
    results: dict = {
        "pre_registered_criteria": {
            "成立": "expR>0 且 ex-512100 平均R>0",
            "不成立": "expR<=0 或 ex-512100<=0",
            "证据不足": "数据无法构建或 N<30",
            "repair_threshold": REPAIR_THRESHOLD,
            "framework": "execute_run 原框架: B/breakout/b3_dual/vc0/rrNone/"
                         "fee standard/limit_guard, cb=40 cl=8% (b-adaptation 原参数)",
        },
        "engine_code_note": (
            "src 树规则模块为 2026-09-01 回退事故后的旧版（v1 纠缠度口径），"
            "且 configs 只有 rules.v1.yaml（cb 默认 120，覆盖锚点不存在）。"
            "本复核的最小工程处置：①从 stash@{0} 提取归档时代规则模块注册进"
            "本进程（scripts/agent_Y/pre_revert_rules/，与 "
            "stop_loss_matrix/pre_revert_modules 独立副本逐字节一致）；"
            "②账本指回提交 1a321ce 的 configs/rules.v2.yaml（原样复制到 "
            "scripts/agent_Y/）。处置模块: " + ", ".join(installed)
        ),
        "original_archive": ORIGINAL,
        "variants": {},
    }

    # ── 跳变在池内的存在性核查（先于一切修平）──
    presence = {}
    for sym in POOL_BROAD:
        dates = AUDIT_JUMPS.get(sym, [])
        presence[sym] = audit_jump_presence(pool_bars[sym], dates) if dates else []
        # 附：全序列 |单日|>12% 扫描（不论是否在审计清单内）
        r = pool_bars[sym]["close"].pct_change(fill_method=None)
        extra = [
            {"date": str(ts.date()), "single_day": round(float(v), 6)}
            for ts, v in r[r.abs() > REPAIR_THRESHOLD].items()
            if str(ts.date()) not in dates
        ]
        for e in extra:
            e["in_audit_list"] = False
            e["note"] = "创业板/科创板ETF ±20% 合法清单核对见报告"
        presence[sym] = presence[sym] + extra
    results["pool_jump_presence"] = presence

    # ── V0 基线复现 ──
    results["variants"]["V0_pool_as_is"] = run_variant(pool_bars, "V0")

    # ── V1 审计修平处置（条件执行）──
    v1_bars, repaired_log = {}, []
    for sym in POOL_BROAD:
        dates = AUDIT_JUMPS.get(sym, [])
        if not dates:
            v1_bars[sym] = pool_bars[sym]
            continue
        pres = [p for p in presence[sym] if p.get("in_audit_list", True)]
        fixed, real = build_v1(pool_bars[sym], pres)
        v1_bars[sym] = fixed
        if real:
            repaired_log.append({"symbol": sym, "repaired_dates": real})
    results["variants"]["V1_audit_repair"] = run_variant(v1_bars, "V1")
    results["variants"]["V1_audit_repair"]["repaired"] = repaired_log

    # ── V2 跨存储敏感（timing 修平版代入）──
    v2_bars = dict(pool_bars)
    v2_meta = {}
    for sym in ("512100.SS", "510500.SS"):
        tc = load_timing_bars(sym)
        tcf = flatten_jumps(tc, AUDIT_JUMPS[sym])
        common = pool_bars[sym].index.intersection(tcf.index)
        v2_bars[sym] = build_v2(pool_bars[sym], tcf)
        # 共同交易日上收益相关性（量级披露）
        r1 = pool_bars[sym]["close"].pct_change().reindex(common)
        r2 = v2_bars[sym]["close"].pct_change().reindex(common)
        v2_meta[sym] = {
            "common_days": int(len(common)),
            "first": str(common[0].date()), "last": str(common[-1].date()),
            "returns_corr": round(float(r1.corr(r2)), 6),
        }
    results["variants"]["V2_timing_fixed_ohlc"] = run_variant(v2_bars, "V2")
    results["variants"]["V2_timing_fixed_ohlc"]["store_swap"] = v2_meta

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    h = hashlib.sha256(
        json.dumps(results, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    print(f"输出: {OUT}")
    print(f"HASH(规范化JSON): {h}")
    for tag, s in results["variants"].items():
        print(f"[{tag}] N={s['N']} expR={s['expR']:+.4f} IS={s['IS_expR']} "
              f"OOS={s['OOS_expR']} ex512100={s['ex_512100_expR']} "
              f"share512100={s['r512100_share']} -> {s['pre_registered_verdict']}")


if __name__ == "__main__":
    main()
