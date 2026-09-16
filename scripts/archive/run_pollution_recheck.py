#!/usr/bin/env python3
"""债务一复核：模块B（密集突破）宽基7池"45%正收益"污染重算 · 预注册（跑前写死）。

【被复核结论】（docs/experiments/b-adaptation-report-2026-08-26.md §0/§2）
  宽基ETF 7池（510050/510300/510500/512100/159901/159915/588000），
  模块B 主轴 breakout × b3_dual × vc0，cb=40/cl=8%：
  N=37, expR=+0.944, IS=+0.281, OOS=+2.326, top1=512100.SS(+15.8R, 45%)。
  债务表述（master-plan 债务一）：该正收益 45% 来自"被污染的中证1000ETF 数据"
  （跳变审计 data-quality-jump-audit-2026-09-02 §5 对技术模块池的影响面推断），
  需在修平数据上重算，确认正收益是否仍成立。

【原始实验环境重建（如实声明）】
  当前分支 HEAD 的 src/ 树因 2026-09-01 回退事故处于新旧混杂状态
  （backtest/engine.py、service.py 为事故后 52f5cb3 保存的新版，但其所依赖的
  first_ma_pullback.py V2 版与 configs/rules.v2.yaml 已丢失，直接 import 报错）。
  本脚本从 git 悬空对象重建 2026-09-01 10:52（= 2026-08-26 原实验的工作台状态）
  的完整代码快照到临时目录后运行，不改动仓库任何文件：
    - 追踪文件（含 first_ma_pullback.py V2、dense_breakout.py、rules_config.py 等）
      取自 WIP stash 提交 a816485；
    - 未追踪文件（backtest/engine.py、service.py 等 + configs/rules.v2.yaml）
      取自 untracked stash 提交 1a321ce；
    - 其中 engine.py/service.py 与当前 HEAD 逐字节一致（已核验）。
  环境等价性由脚本内"复现锚"硬校验（见下），不靠版本声称。

【数据事实核查（预注册，事实认定而非判定）】
  F1 实验所用深池（~/.lei_signal_lab/backtest_pool）7 标的在审计 13 跳变清单
     对应日期的池内单日收益（510500: 2015-04-15 池外、2022-08-29；
     512100: 2022-09-05）——预期无超涨跌停异常；
  F2 深池 7 标的全历史 |单日收益|>12% 扫描（创业板/科创板 ETF ±20% 板内为合法）；
  F3 池文件 mtime 与 meta（provider/fetched_at）——证明 2026-08-25 落盘、
     早于 2026-08-26 原实验、且此后未被改动；
  F4 timing 缓存（~/.lei_signal_lab/cache/timing）同日期单日收益——应复现审计
     跳变（+248.6%/-12.7%/+176.3%），证明"污染存在于 timing 缓存"这一对照事实。

【跑法（原参数原框架，只换数据）】三个数据版本，同一参数同一引擎：
  RUN-R 复现：当前深池原样（即原实验真实数据）——锚定复现；
  RUN-P 污染反事实：把池内 512100/510500 两标的的 OHLC 替换为 timing 缓存的
     未修平序列（池日期范围内，volume 保留池数据）——量化"若当初池数据真被
     污染会怎样"，仅披露不参与判定；
  RUN-F 修平版：替换为 flatten_jumps(timing 序列)——跳变审计 §3 预注册修平法
     原样复用（跳变日起 OHLC 同除跳变比、多跳变按时间序），不重新发明。
  三跑之间清空事件/枢轴/缺口缓存并重建帧缓存，进程内互不污染。

【复现锚（预注册匹配线）】
  RUN-R 须满足：N=37 ∧ |ΔexpR|≤0.02 ∧ |ΔIS|≤0.02 ∧ |ΔOOS|≤0.02
  ∧ top1=512100.SS ∧ top1 份额∈[40%,50%]（对照 spectrum.log /
  b_spectrum_summary.json）。不匹配 → 判定只能为"证据不足"，如实报告差异。

【预注册判定标准（三选一，跑完不得回头调整）】
  分支甲（F1-F3 确认深池无跳变污染，即原实验数据本来干净）：
    判「45%正收益仍成立」 iff RUN-R 复现匹配
        ∧ RUN-F 整体 expR>0
        ∧ RUN-F 排除 512100 后平均 R>0（原实验 ex-top1 绝对正值口径）；
    判「不成立」 iff RUN-F expR≤0
        ∨ RUN-F 排除512100后平均R≤0
        ∨ (RUN-F IS≤0 ∧ RUN-F OOS≤0)；
    其余（含复现失败）→「证据不足」。
  分支乙（F1 发现深池确有跳变——按取证预期不会发生）：
    判「仍成立」 iff RUN-F expR>0 ∧ 排除512100后>0 ∧ IS>0；
    「不成立」/「证据不足」同分支甲。

【红线遵守】不修改 ~/.lei_signal_lab 任何缓存与 src/ 生产代码；只输出统计
对照与判定，不产生买卖点；输出只新增到 docs/experiments/raw/pollution_recheck/。

输出：docs/experiments/raw/pollution_recheck/moduleB_broad_recheck.json
复现：PYTHONHASHSEED=0 / =42 各跑一次，规范化 JSON 的 sha256 须一致。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = REPO / "docs/experiments/raw/pollution_recheck"
OUT = RAW / "moduleB_broad_recheck.json"

# 原实验参数（run_b_spectrum.py 宽基ETF 主轴 + b_spectrum_summary 最优档，原样）
POOL_BROAD = ("510050.SS", "510300.SS", "510500.SS", "512100.SS",
              "159901.SZ", "159915.SZ", "588000.SS")
CB, CL = 40, 0.08
ORIGINAL = {  # spectrum.log 2026-08-26 归档数字（复现锚）
    "N": 37, "expR": 0.944, "IS": 0.281, "OOS": 2.326,
    "top1": "512100.SS", "top1_share": (0.40, 0.50),
}
# 审计 13 跳变清单中落在宽基 7 池的两个标的（data-quality-jump-audit §2）
JUMPS = {"510500.SS": ["2015-04-15", "2022-08-29"], "512100.SS": ["2022-09-05"]}
# 20cm 板（创业板/科创板 ETF）合法大幅日不视为异常
LEGAL_20CM = {"159915.SZ", "588000.SS"}

STASH_TRACKED = "a816485"   # WIP stash：追踪文件（含 first_ma_pullback V2）
STASH_UNTRACKED = "1a321ce"  # untracked stash：backtest/engine|service + rules.v2.yaml


def build_v2_env(env_dir: Path) -> dict:
    """从 git 悬空对象重建原实验代码快照（只读 git，不改仓库）。"""
    def run(*args: str) -> bytes:
        r = subprocess.run(["git", "-C", str(REPO), *args],
                           capture_output=True, check=True)
        return r.stdout

    def rev_ok(rev: str) -> bool:
        return subprocess.run(["git", "-C", str(REPO), "cat-file", "-e",
                               f"{rev}^{{commit}}"]).returncode == 0

    if not (rev_ok(STASH_TRACKED) and rev_ok(STASH_UNTRACKED)):
        raise SystemExit(f"git 悬空对象缺失: {STASH_TRACKED}/{STASH_UNTRACKED}（可能被 gc）")

    env_dir.mkdir(parents=True, exist_ok=True)
    for rev in (STASH_TRACKED, STASH_UNTRACKED):
        tar = subprocess.run(["git", "-C", str(REPO), "archive", rev, "src", "configs"],
                             capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(env_dir)], input=tar, check=True)
    # 清掉归档带入的 pycache
    for p in env_dir.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
    # 等价性核验：重建 env 的 engine/service 与 HEAD 是否一致
    same = {}
    for rel in ("src/lei_signal/backtest/engine.py", "src/lei_signal/backtest/service.py"):
        rebuilt = subprocess.run(
            ["git", "-C", str(REPO), "show", f"{STASH_UNTRACKED}:{rel}"],
            capture_output=True, check=True).stdout
        head = subprocess.run(
            ["git", "-C", str(REPO), "show", f"HEAD:{rel}"],
            capture_output=True, check=True).stdout
        same[rel.split("/")[-1]] = rebuilt == head
    # 关键文件 sha256（归档可审计）
    sha = {}
    for rel in ("src/lei_signal/rules/first_ma_pullback.py",
                "src/lei_signal/rules/dense_breakout.py",
                "src/lei_signal/backtest/engine.py",
                "src/lei_signal/backtest/service.py",
                "configs/rules.v2.yaml"):
        fp = env_dir / rel
        sha[rel] = hashlib.sha256(fp.read_bytes()).hexdigest()[:16]
    return {"engine_service_match_HEAD": same, "snapshot_sha256_16": sha}


def flatten_jumps(bars, dates):
    """审计 §3 预注册修平法原样复用（跳变日起 OHLC 同除跳变比，按时间序）。"""
    df = bars.copy()
    log = []
    for d in sorted(dates):
        ts = pd_Timestamp(d)
        if ts not in df.index:
            log.append({"date": d, "in_pool_range": False})
            continue
        i = df.index.get_loc(ts)
        ratio = float(df["close"].iloc[i] / df["close"].iloc[i - 1])
        mask = df.index >= ts
        for c in ("open", "high", "low", "close"):
            df.loc[mask, c] = df.loc[mask, c] / ratio
        log.append({"date": d, "ratio": round(ratio, 4), "in_pool_range": True})
    return df, log


def pd_Timestamp(s):
    import pandas as pd
    return pd.Timestamp(s)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    env = tempfile.mkdtemp(prefix="lei_v2env_")
    env_info = build_v2_env(Path(env))
    sys.path.insert(0, str(Path(env) / "src"))
    sys.path.insert(0, str(REPO / "scripts"))

    import pandas as pd  # noqa: F401  (V2 env 与本机同 pandas)
    from lei_signal.backtest import service as svc
    from lei_signal.backtest.runner import load_pool_frames
    from lei_signal.data.cache import ParquetCache
    from lei_signal.features.indicators import compute_features
    from lei_signal.features.pivots import confirmed_pivots  # noqa: F401
    from lei_signal.rules.lei_color import classify_colors
    from run_filters_round4 import _summarize  # 与原实验同一汇总口径

    TIMING = Path.home() / ".lei_signal_lab/cache/timing"
    POOL_ROOT = Path.home() / ".lei_signal_lab/backtest_pool"

    # ---------- 数据事实核查 F1-F4 ----------
    cache = ParquetCache(POOL_ROOT)
    pool_raw = {s: cache.read(s) for s in POOL_BROAD}
    forensics = {"F1_jump_dates_in_pool": {}, "F2_pool_absdaily_gt12pct": {},
                 "F3_pool_file_evidence": {}, "F4_timing_same_dates": {}}
    for s in POOL_BROAD:
        bars = pool_raw[s]
        bars = bars[~bars.index.duplicated(keep="last")].sort_index()
        ret = bars["close"].pct_change(fill_method=None)
        forensics["F2_pool_absdaily_gt12pct"][s] = {
            "range": [str(bars.index[0].date()), str(bars.index[-1].date())],
            "big_days": [{"date": str(k.date()), "ret": round(float(v), 4)}
                         for k, v in ret[ret.abs() > 0.12].items()],
            "legal_20cm_board": s in LEGAL_20CM,
        }
        for d in JUMPS.get(s, []):
            ts = pd.Timestamp(d)
            entry = {"date": d, "in_pool_range": bool(ts in bars.index)}
            if entry["in_pool_range"]:
                entry["pool_single_day"] = round(float(ret.loc[ts]), 4)
            forensics["F1_jump_dates_in_pool"].setdefault(s, []).append(entry)
        meta_fp = POOL_ROOT / f"{s}.bars.meta.json"
        meta = json.loads(meta_fp.read_text()) if meta_fp.exists() else {}
        st = (POOL_ROOT / f"{s}.bars.parquet").stat()
        forensics["F3_pool_file_evidence"][s] = {
            "provider": meta.get("provider"),
            "fetched_at_utc": meta.get("fetched_at"),
            "rows": meta.get("rows"),
            "file_mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
        }
    for s, dates in JUMPS.items():
        tf = pd.read_parquet(TIMING / f"{s.split('.')[0]}.parquet")
        tf = tf[~tf.index.duplicated(keep="last")].sort_index()
        tret = tf["close"].pct_change(fill_method=None)
        for d in dates:
            ts = pd.Timestamp(d)
            forensics["F4_timing_same_dates"].setdefault(s, []).append({
                "date": d,
                "timing_single_day": round(float(tret.loc[ts]), 4) if ts in tf.index else None,
            })

    pool_clean = all(
        abs(e.get("pool_single_day", 0.0)) <= 0.12
        for lst in forensics["F1_jump_dates_in_pool"].values() for e in lst
    ) and all(
        (s in LEGAL_20CM) or (not v["big_days"])
        for s, v in forensics["F2_pool_absdaily_gt12pct"].items()
    )

    # ---------- 三跑 ----------
    def load_timing_bars(s):
        tf = pd.read_parquet(TIMING / f"{s.split('.')[0]}.parquet")
        tf = tf[~tf.index.duplicated(keep="last")].sort_index()
        for col in ("high", "low"):
            if col not in tf.columns:
                tf[col] = (tf[["open", "close"]].max(axis=1) if col == "high"
                           else tf[["open", "close"]].min(axis=1))
        return tf[["open", "high", "low", "close"]]

    def transplant(pool_bars, timing_bars):
        """池日期范围内 OHLC 替换为 timing 序列（volume 等其余列保留池数据）。"""
        out = pool_bars.copy()
        common = pool_bars.index.intersection(timing_bars.index)
        assert len(common) == len(pool_bars), \
            f"timing 序列未覆盖池全部交易日: {len(common)}/{len(pool_bars)}"
        out.loc[common, ["open", "high", "low", "close"]] = \
            timing_bars.loc[common, ["open", "high", "low", "close"]]
        return out

    flat_logs = {}
    transplant_specs = {}
    for s, dates in JUMPS.items():
        tb = load_timing_bars(s)
        tf_flat, lg = flatten_jumps(tb, dates)
        flat_logs[s] = lg
        transplant_specs[s] = {"raw": tb, "fixed": tf_flat}

    def run_once(tag, frames_override=None):
        frames = load_pool_frames()  # 深池全量（含基准 000300 时钟）
        for s in POOL_BROAD:
            if frames_override and s in frames_override:
                frames[s] = classify_colors(compute_features(frames_override[s]))
        svc._FRAME_CACHE = frames
        svc._EVENT_CACHE.clear()
        svc._PIVOT_CACHE.clear()
        svc._GAP_CACHE.clear()
        svc._PROFILE_CACHE.clear()
        from lei_signal.backtest.service import BacktestParams, execute_run
        res = execute_run(BacktestParams(
            symbols=POOL_BROAD, module="B", rr_min=None,
            entry_variant="breakout", exit_variant="b3_dual",
            volume_confirm=False, fee_label="standard", limit_guard=True,
            volume_confirm_window=1,
            overrides=(("consolidation_bars", CB), ("cluster_threshold", CL)),
        ))
        s = _summarize(res, tag)
        trades = s["trades_detail"]
        others = [t["r_net"] for t in trades if t["symbol"] != "512100.SS"]
        ov = s["overview"]
        t512100 = [t for t in trades if t["symbol"] == "512100.SS"]
        return {
            "tag": tag,
            "N": ov["trade_count"],
            "expR": round(ov["expectancy_r"], 4),
            "IS": None if s["is_expectancy"] is None else round(s["is_expectancy"], 4),
            "OOS": None if s["oos_expectancy"] is None else round(s["oos_expectancy"], 4),
            "profit_factor": round(ov["profit_factor"], 4),
            "win_rate": round(ov["win_rate"], 4),
            "total_r": round(ov["total_r"], 4),
            "top1_symbol": s["top1_symbol"],
            "top1_total_r": round(s["top1_total_r"] or 0.0, 4),
            "top1_share": (round((s["top1_total_r"] or 0.0) / ov["total_r"], 4)
                           if ov["total_r"] else None),
            "ex_512100_mean_r": (round(sum(others) / len(others), 4) if others else None),
            "by_symbol": [
                {"symbol": b["symbol"], "N": b["trade_count"],
                 "expR": None if b["expectancy_r"] is None else round(b["expectancy_r"], 4),
                 "total_r": round(b["total_r"], 4)} for b in s["by_symbol"]
            ],
            "trades_512100": [
                {"signal_date": t["signal_date"], "entry_date": t["entry_date"],
                 "exit_reason": t["exit_reason"], "r_net": round(t["r_net"], 4)}
                for t in t512100
            ],
        }

    t0 = time.time()
    run_r = run_once("RUN-R_pool_as_is")
    override_p, override_f = {}, {}
    for s, spec in transplant_specs.items():
        pool_bars = pool_raw[s]
        pool_bars = pool_bars[~pool_bars.index.duplicated(keep="last")].sort_index()
        override_p[s] = transplant(pool_bars, spec["raw"])
        override_f[s] = transplant(pool_bars, spec["fixed"])
    run_p = run_once("RUN-P_pollution_counterfactual", override_p)
    run_f = run_once("RUN-F_flattened", override_f)
    print(f"三跑总耗时 {time.time() - t0:.1f}s")

    # ---------- 复现锚校验 ----------
    anchor_ok = (
        run_r["N"] == ORIGINAL["N"]
        and abs(run_r["expR"] - ORIGINAL["expR"]) <= 0.02
        and run_r["IS"] is not None and abs(run_r["IS"] - ORIGINAL["IS"]) <= 0.02
        and run_r["OOS"] is not None and abs(run_r["OOS"] - ORIGINAL["OOS"]) <= 0.02
        and run_r["top1_symbol"] == ORIGINAL["top1"]
        and run_r["top1_share"] is not None
        and ORIGINAL["top1_share"][0] <= run_r["top1_share"] <= ORIGINAL["top1_share"][1]
    )

    # ---------- 预注册判定 ----------
    def judge():
        f_ok = (run_f["expR"] is not None and run_f["expR"] > 0
                and run_f["ex_512100_mean_r"] is not None
                and run_f["ex_512100_mean_r"] > 0)
        dead = ((run_f["expR"] is not None and run_f["expR"] <= 0)
                or (run_f["ex_512100_mean_r"] is not None
                    and run_f["ex_512100_mean_r"] <= 0)
                or (run_f["IS"] is not None and run_f["IS"] <= 0
                    and run_f["OOS"] is not None and run_f["OOS"] <= 0))
        if pool_clean:
            if f_ok and anchor_ok:
                return "45%正收益仍成立"
            if dead:
                return "不成立"
            return "证据不足"
        # 分支乙（池内有跳变，取证预期不发生）
        if f_ok and run_f["IS"] is not None and run_f["IS"] > 0:
            return "45%正收益仍成立"
        if dead:
            return "不成立"
        return "证据不足"

    verdict = judge()
    results = {
        "task": "债务一：模块B宽基7池 cb40/cl8% 污染重算（预注册）",
        "original_archived": {
            "source": "raw/b_adaptation/b_spectrum_summary.json + spectrum.log",
            **ORIGINAL, "top1_share": list(ORIGINAL["top1_share"]),
        },
        "params": {"pool": list(POOL_BROAD), "module": "B",
                   "entry": "breakout", "exit": "b3_dual", "volume_confirm": False,
                   "cb": CB, "cl": CL, "rr_min": None, "fee": "standard",
                   "limit_guard": True, "oos_split": "数据末尾往前2年"},
        "env_rebuild": env_info,
        "forensics": forensics,
        "pool_clean_no_jumps": pool_clean,
        "flatten_logs": flat_logs,
        "runs": {"RUN-R_pool_as_is": run_r,
                 "RUN-P_pollution_counterfactual": run_p,
                 "RUN-F_flattened": run_f},
        "reproduction_anchor_ok": anchor_ok,
        "verdict_pre_registered": verdict,
        "branch": "分支甲（池无跳变）" if pool_clean else "分支乙（池有跳变）",
    }
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    h = hashlib.sha256(json.dumps(results, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    print(f"复现锚匹配: {anchor_ok}（N={run_r['N']} expR={run_r['expR']:+.4f} "
          f"IS={run_r['IS']:+.4f} OOS={run_r['OOS']:+.4f} top1={run_r['top1_symbol']} "
          f"share={run_r['top1_share']:.1%}）")
    print(f"RUN-P(污染反事实): N={run_p['N']} expR={run_p['expR']:+.4f} "
          f"IS={run_p['IS']} OOS={run_p['OOS']} top1={run_p['top1_symbol']} "
          f"share={run_p['top1_share']}")
    print(f"RUN-F(修平版):     N={run_f['N']} expR={run_f['expR']:+.4f} "
          f"IS={run_f['IS']} OOS={run_f['OOS']} top1={run_f['top1_symbol']} "
          f"share={run_f['top1_share']} ex512100={run_f['ex_512100_mean_r']}")
    print(f"深池无跳变(F1/F2): {pool_clean}")
    print(f"判定（预注册）: {verdict}")
    print(f"输出: {OUT}")
    print(f"HASH(规范化JSON): {h}")
    shutil.rmtree(env, ignore_errors=True)


if __name__ == "__main__":
    main()
