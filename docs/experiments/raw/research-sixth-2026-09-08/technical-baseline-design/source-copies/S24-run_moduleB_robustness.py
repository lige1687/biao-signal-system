#!/usr/bin/env python3
"""模块B（密集突破）干净数据正期望的稳健性深挖 · 预注册（跑前写死，跑后不得调）。

【被复核结论】（docs/experiments/pollution-recheck-moduleB-csi500-2026-09-03.md §2）
  宽基ETF 7池（510050/510300/510500/512100/159901/159915/588000），
  模块B breakout × b3_dual × vc0，cb=40/cl=8%，深池数据（已核实无跳变污染）：
  N=37, expR=+0.9441, IS=+0.2809, OOS=+2.3257, 胜率 37.84%,
  top1=512100.SS(+15.83R, 占 45.3%)，排除 512100 后平均 R=+0.5457。

【核心问题】N=37 的正期望是分布广泛的，还是被少数几笔 / 某一年 / 某个标的
  撑起来的？

【方法】不新增回测：用 Y 脚本（scripts/run_pollution_recheck.py）同一环境重建
  方式 + 同一参数只跑 RUN-R（深池原样，即干净数据——Y 已核实深池无跳变），
  取全部 37 笔明细（symbol/signal_date/r_net/...），在其上做纯算术稳健性分解。
  已入库 JSON 只含 512100 的两笔明细，缺全量逐笔，故须重跑同一配置补明细——
  参数零改动。

【复现锚（跑前写死）】重跑须满足 N=37 ∧ |ΔexpR|≤0.02 ∧ top1=512100.SS
  ∧ top1 份额∈[40%,50%] ∧ 全部 37 笔中 512100 恰为 2 笔且其 r_net 与已入库
  JSON 逐笔一致（-0.1395 / +15.9697）。不匹配 → 判定只能为"证据不足"。

【预注册稳健性维度与阈值（跑前写死）】
  D1 逐笔集中度：按单笔 r_net 降序。
      - top3_share = 前三笔 r_net 之和 / 全体正 r_net 之和；
      - top5_share 同理前五笔；
      - drop_top3_mean = 剔除 r_net 最高的三笔后剩余笔数的平均 r。
  D2 时间分散：按 signal_date 年份分组。
      - pos_years = 总 r_net>0 的年份数（只计有交易的年份）；
      - max_year_share = 单一年份正贡献占全体正贡献比例。
  D3 标的分散：7 个标的逐一 leave-one-out。
      - loo_min = 各次剔除后剩余平均 r 的最小值；
      - 512100 单列（剔除后平均 r 即已知 ex_512100 口径）。
  D4 胜率结构：r_net>0 笔数占比；正/负笔的平均 r（描述"少数大赢+多数小输"
      结构，不参与判定线）。

【预注册三选一判定线（跑前写死）】
  稳健   iff 复现锚匹配 ∧ drop_top3_mean>0 ∧ loo_min>0 ∧ pos_years≥3；
  脆弱   iff 复现锚匹配 ∧ 整体 expR>0 且上述三条至少一条不成立
          （报告须写明依赖哪个维度）；整体 expR≤0 亦判脆弱；
  证据不足 iff 复现锚不匹配或数据缺字段。
  阈值论证：drop_top3>0 保证"前三笔拿走大头"后仍非负；LOO 全正保证不依赖
  任何单一标的（含已知的 512100 集中）；pos_years≥3 保证不是单一时间段行情
  的产物（数据跨 ~11 年，≥3 个正年份是"时间上至少三处独立出现"的最低要求）。

【红线】不改仓库与缓存任何文件；输出只新增到 docs/experiments/raw/module_b_robustness/；
  不调参、不扩池、不发明变体。
复现：PYTHONHASHSEED=0 / =42 各跑一次，规范化 JSON sha256 须一致。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = REPO / "docs/experiments/raw/module_b_robustness"
OUT = RAW / "moduleB_robustness.json"

POOL_BROAD = ("510050.SS", "510300.SS", "510500.SS", "512100.SS",
              "159901.SZ", "159915.SZ", "588000.SS")
CB, CL = 40, 0.08
ANCHOR = {"N": 37, "expR": 0.9441, "top1": "512100.SS",
          "top1_share": (0.40, 0.50),
          "t512100_r_net": sorted([-0.1395, 15.9697])}

STASH_TRACKED = "a816485"
STASH_UNTRACKED = "1a321ce"


def build_v2_env(env_dir: Path) -> dict:
    """与 run_pollution_recheck.py 完全同一的环境重建（只读 git）。"""
    def rev_ok(rev: str) -> bool:
        return subprocess.run(["git", "-C", str(REPO), "cat-file", "-e",
                               f"{rev}^{{commit}}"]).returncode == 0
    if not (rev_ok(STASH_TRACKED) and rev_ok(STASH_UNTRACKED)):
        raise SystemExit(f"git 悬空对象缺失: {STASH_TRACKED}/{STASH_UNTRACKED}")
    env_dir.mkdir(parents=True, exist_ok=True)
    for rev in (STASH_TRACKED, STASH_UNTRACKED):
        tar = subprocess.run(["git", "-C", str(REPO), "archive", rev, "src", "configs"],
                             capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(env_dir)], input=tar, check=True)
    for p in env_dir.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
    sha = {}
    for rel in ("src/lei_signal/rules/first_ma_pullback.py",
                "src/lei_signal/rules/dense_breakout.py",
                "src/lei_signal/backtest/engine.py",
                "src/lei_signal/backtest/service.py",
                "configs/rules.v2.yaml"):
        sha[rel] = hashlib.sha256((env_dir / rel).read_bytes()).hexdigest()[:16]
    return sha


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    env = tempfile.mkdtemp(prefix="lei_v2env_ai_")
    env_sha = build_v2_env(Path(env))
    sys.path.insert(0, str(Path(env) / "src"))
    sys.path.insert(0, str(REPO / "scripts"))

    from lei_signal.backtest import service as svc
    from lei_signal.backtest.runner import load_pool_frames
    from run_filters_round4 import _summarize

    frames = load_pool_frames()  # 深池原样（干净数据）
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
    s = _summarize(res, "RUN-R_robustness_detail")
    trades = s["trades_detail"]
    ov = s["overview"]
    total_r = ov["total_r"]

    # ---------- 复现锚 ----------
    t512 = sorted(round(t["r_net"], 4) for t in trades if t["symbol"] == "512100.SS")
    anchor_ok = (
        ov["trade_count"] == ANCHOR["N"]
        and abs(ov["expectancy_r"] - ANCHOR["expR"]) <= 0.02
        and s["top1_symbol"] == ANCHOR["top1"]
        and s["top1_total_r"] is not None and total_r
        and ANCHOR["top1_share"][0] <= s["top1_total_r"] / total_r <= ANCHOR["top1_share"][1]
        and t512 == ANCHOR["t512100_r_net"]
    )

    # ---------- D1 逐笔集中度 ----------
    ranked = sorted(trades, key=lambda t: t["r_net"], reverse=True)
    pos_sum = sum(t["r_net"] for t in trades if t["r_net"] > 0)
    top3 = ranked[:3]
    top5 = ranked[:5]
    rest = ranked[3:]
    d1 = {
        "top3": [{"symbol": t["symbol"], "signal_date": t["signal_date"],
                  "r_net": round(t["r_net"], 4)} for t in top3],
        "top5": [{"symbol": t["symbol"], "signal_date": t["signal_date"],
                  "r_net": round(t["r_net"], 4)} for t in top5],
        "top3_share_of_positive": round(sum(t["r_net"] for t in top3) / pos_sum, 4),
        "top5_share_of_positive": round(sum(t["r_net"] for t in top5) / pos_sum, 4),
        "drop_top3_mean_r": round(sum(t["r_net"] for t in rest) / len(rest), 4),
        "drop_top3_n": len(rest),
        "drop_top1_mean_r": round(sum(t["r_net"] for t in ranked[1:]) / (len(ranked) - 1), 4),
    }

    # ---------- D2 时间分散 ----------
    by_year = {}
    for t in trades:
        y = t["signal_date"][:4]
        g = by_year.setdefault(y, {"n": 0, "total_r": 0.0})
        g["n"] += 1
        g["total_r"] += t["r_net"]
    by_year = {y: {"n": g["n"], "total_r": round(g["total_r"], 4),
                   "mean_r": round(g["total_r"] / g["n"], 4)}
               for y, g in sorted(by_year.items())}
    pos_years = sum(1 for g in by_year.values() if g["total_r"] > 0)
    year_pos_contrib = {y: g["total_r"] for y, g in by_year.items() if g["total_r"] > 0}
    d2 = {
        "by_year": by_year,
        "pos_years": pos_years,
        "years_with_trades": len(by_year),
        "max_year_share_of_positive": round(
            max(year_pos_contrib.values()) / pos_sum, 4) if year_pos_contrib else None,
        "max_pos_year": max(year_pos_contrib, key=year_pos_contrib.get) if year_pos_contrib else None,
    }

    # ---------- D3 标的 leave-one-out ----------
    loo = {}
    for sym in POOL_BROAD:
        others = [t["r_net"] for t in trades if t["symbol"] != sym]
        loo[sym] = {"n_removed": len(trades) - len(others),
                    "ex_mean_r": round(sum(others) / len(others), 4) if others else None}
    d3 = {"leave_one_out": loo,
          "loo_min": min(v["ex_mean_r"] for v in loo.values() if v["ex_mean_r"] is not None)}

    # ---------- D4 胜率结构 ----------
    rs = [t["r_net"] for t in trades]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    d4 = {
        "n": len(rs),
        "win_rate": round(len(wins) / len(rs), 4),
        "win_mean_r": round(sum(wins) / len(wins), 4),
        "loss_mean_r": round(sum(losses) / len(losses), 4),
        "median_r": round(sorted(rs)[len(rs) // 2], 4),
    }

    # ---------- 预注册判定 ----------
    cond_top3 = d1["drop_top3_mean_r"] > 0
    cond_loo = d3["loo_min"] > 0
    cond_years = d2["pos_years"] >= 3
    if not anchor_ok:
        verdict = "证据不足"
    elif ov["expectancy_r"] <= 0:
        verdict = "脆弱"
    elif cond_top3 and cond_loo and cond_years:
        verdict = "稳健"
    else:
        verdict = "脆弱"
    failed = [k for k, ok in (("drop_top3>0", cond_top3), ("loo_min>0", cond_loo),
                              ("pos_years>=3", cond_years)) if not ok]

    results = {
        "task": "模块B干净数据正期望稳健性深挖（预注册）",
        "params": {"pool": list(POOL_BROAD), "module": "B", "cb": CB, "cl": CL,
                   "entry": "breakout", "exit": "b3_dual", "volume_confirm": False,
                   "fee": "standard", "limit_guard": True},
        "env_snapshot_sha256_16": env_sha,
        "anchor_ok": anchor_ok,
        "overall": {"N": ov["trade_count"], "expR": round(ov["expectancy_r"], 4),
                    "IS": None if s["is_expectancy"] is None else round(s["is_expectancy"], 4),
                    "OOS": None if s["oos_expectancy"] is None else round(s["oos_expectancy"], 4),
                    "total_r": round(total_r, 4),
                    "top1_symbol": s["top1_symbol"],
                    "top1_share": round(s["top1_total_r"] / total_r, 4) if total_r else None},
        "D1_concentration": d1,
        "D2_time": d2,
        "D3_symbols": d3,
        "D4_win_structure": d4,
        "conditions": {"drop_top3_mean_r>0": cond_top3, "loo_min>0": cond_loo,
                       "pos_years>=3": cond_years},
        "failed_conditions": failed,
        "verdict_pre_registered": verdict,
        "trades_detail": [
            {"symbol": t["symbol"], "signal_date": t["signal_date"],
             "entry_date": t["entry_date"], "exit_reason": t["exit_reason"],
             "r_net": round(t["r_net"], 4), "holding_bars": t["holding_bars"]}
            for t in sorted(trades, key=lambda t: (t["signal_date"], t["symbol"]))
        ],
    }
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    canon = json.dumps(results, sort_keys=True, ensure_ascii=False)
    print(f"复现锚匹配: {anchor_ok}")
    print(f"整体: N={results['overall']['N']} expR={results['overall']['expR']:+.4f} "
          f"top1_share={results['overall']['top1_share']}")
    print(f"D1: top3占正贡献={d1['top3_share_of_positive']:.1%} "
          f"剔前三笔后均值={d1['drop_top3_mean_r']:+.4f} (n={d1['drop_top3_n']})")
    print(f"D2: 正R年份数={pos_years}/{len(by_year)} 最大年份正贡献占比={d2['max_year_share_of_positive']}")
    print(f"D3: LOO最小={d3['loo_min']:+.4f}  各标的: "
          + ", ".join(f"{k}:{v['ex_mean_r']:+.3f}" for k, v in loo.items()))
    print(f"D4: 胜率={d4['win_rate']:.1%} 赢单均={d4['win_mean_r']:+.3f} 输单均={d4['loss_mean_r']:+.3f}")
    print(f"条件: {results['conditions']} 未过: {failed}")
    print(f"判定（预注册）: {verdict}")
    print(f"HASH(规范化JSON): {hashlib.sha256(canon.encode()).hexdigest()}")
    shutil.rmtree(env, ignore_errors=True)


if __name__ == "__main__":
    main()
