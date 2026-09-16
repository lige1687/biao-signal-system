"""任务二：A 稳健档在扩池后复核 + 行业分化表。

三个层级：
  Level 1: 4 个大子池（行业 ETF / 宽基 ETF / 海外 ETF / 指数本体）
  Level 2: 每个行业 ETF 单独跑（~33 个新 ETF + 老 ETF）
  Level 3: 排除 top1 / top3 检验（最优行业 ETF 池上）
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "etf_expansion"
OUT_A = RAW / "A_pool"
OUT_EACH = RAW / "A_each_industry"
OUT_A.mkdir(parents=True, exist_ok=True)
OUT_EACH.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "scripts"))
from run_backtest_grid import _summary_one  # type: ignore

# 稳健档（上一轮结论）
PARAMS = dict(
    module="A",
    rr_min=None,
    entry_variant="early",
    exit_variant="a6_1_costbasis",
    fee_label="standard",
    limit_guard=True,
    overrides=(("clock_mult", 0.5), ("touch_atr", 1.0)),
)

POOLS = {
    "行业ETF": [
        "512000.SS", "512010.SS", "512170.SS", "512200.SS", "512400.SS",
        "512480.SS", "512580.SS", "512660.SS", "512690.SS", "512760.SS",
        "512800.SS", "512890.SS", "512980.SS", "515030.SS", "515050.SS",
        "515130.SS", "515170.SS", "515210.SS", "515220.SS", "515300.SS",
        "515790.SS", "515880.SS", "516010.SS", "516220.SS", "516510.SS",
        "518850.SS", "562590.SS", "159611.SZ", "159819.SZ", "159825.SZ",
        "159865.SZ", "159928.SZ", "159992.SZ",
    ],
    "宽基ETF": [
        "510050.SS", "510300.SS", "510500.SS", "512100.SS", "159901.SZ",
        "159915.SZ", "588000.SS",
    ],
    "海外ETF": [
        "159995.SZ", "513030.SS", "513100.SS", "513180.SS", "513500.SS",
        "513520.SS", "513870.SS",
    ],
    "指数本体": [
        "000001.SS", "000001.SZ", "000016.SS", "000300.SS", "000688.SS",
        "000698.SZ", "000905.SS", "399006.SZ",
    ],
}

INDUSTRY_EACH = {
    "512000.SS": "券商",
    "512010.SS": "医药",
    "512170.SS": "医疗器械",
    "512200.SS": "房地产",
    "512400.SS": "有色金属",
    "512480.SS": "半导体(国联安)",
    "512580.SS": "环保",
    "512660.SS": "军工",
    "512690.SS": "酒",
    "512760.SS": "半导体(华夏)",
    "512800.SS": "银行",
    "512890.SS": "科技",
    "512980.SS": "传媒",
    "515030.SS": "新能源车",
    "515050.SS": "5G通信",
    "515130.SS": "医药 ETF",
    "515170.SS": "食品饮料",
    "515210.SS": "钢铁",
    "515220.SS": "煤炭",
    "515300.SS": "红利低波",
    "515790.SS": "光伏",
    "515880.SS": "通信",
    "516010.SS": "游戏",
    "516220.SS": "化工新材料",
    "516510.SS": "云计算",
    "518850.SS": "黄金",
    "562590.SS": "券商(易方达)",
    "159611.SZ": "电力",
    "159819.SZ": "人工智能",
    "159825.SZ": "农业",
    "159865.SZ": "养殖",
    "159928.SZ": "消费",
    "159992.SZ": "创新药",
}


def _run(symbols, tag, out_dir, *, top_exclude=None) -> None:
    from lei_signal.backtest.service import BacktestParams, execute_run

    fp = out_dir / f"{tag}.json"
    if fp.exists():
        print(f"[skip] {tag}")
        return
    t0 = time.time()
    final_syms = symbols
    if top_exclude:
        final_syms = [s for s in symbols if s != top_exclude]
    res = execute_run(BacktestParams(**PARAMS, symbols=tuple(final_syms)))
    s = _summary_one(res)
    if top_exclude:
        s["exclude"] = top_exclude
    fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    ov = s["overview"]
    is_e = s["is_expectancy"] if s["is_expectancy"] is not None else float("nan")
    oos_e = s["oos_expectancy"] if s["oos_expectancy"] is not None else float("nan")
    print(
        f"[done] {tag:<32s}  N={ov['trade_count'] or 0:>4}  expR={ov['expectancy_r'] if ov['expectancy_r'] is not None else float('nan'):+.3f}  "
        f"PF={ov['profit_factor']}  IS={is_e:+.3f}({s['is_trade_count'] or 0})  "
        f"OOS={oos_e:+.3f}({s['oos_trade_count'] or 0})  top1={s['top1_symbol'] or '-'}  "
        f"{time.time()-t0:.1f}s"
    )


def main() -> None:
    print("=== Level 1: 4 大子池 ===")
    for name, syms in POOLS.items():
        _run(syms, name, OUT_A)

    print("\n=== Level 2: 每行业 ETF 单独 ===")
    for sym, label in INDUSTRY_EACH.items():
        tag = f"{sym}__{label}"
        _run([sym], tag, OUT_EACH)

    print("\n=== Level 3: 排除 top1/top3 检验 ===")
    pool_fp = OUT_A / "行业ETF.json"
    if pool_fp.exists():
        c = json.loads(pool_fp.read_text(encoding="utf-8"))
        syms_sorted = sorted(c["by_symbol"], key=lambda s: -(s["total_r"] or 0))
        if syms_sorted:
            top1 = syms_sorted[0]["symbol"]
            _run(POOLS["行业ETF"], "no_top1", OUT_A, top_exclude=top1)
            top3 = [s["symbol"] for s in syms_sorted[:3]]
            from lei_signal.backtest.service import BacktestParams, execute_run
            t0 = time.time()
            syms = [s for s in POOLS["行业ETF"] if s not in top3]
            tag = f"no_top3__{','.join(top3)}"
            fp = OUT_A / "no_top3.json"
            if not fp.exists():
                res = execute_run(BacktestParams(**PARAMS, symbols=tuple(syms)))
                s = _summary_one(res)
                s["exclude"] = top3
                fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
                ov = s["overview"]
                is_e = s["is_expectancy"] if s["is_expectancy"] is not None else float("nan")
                oos_e = s["oos_expectancy"] if s["oos_expectancy"] is not None else float("nan")
                print(
                    f"[done] no_top3 (excl {top3})  N={ov['trade_count'] or 0:>4}  expR={ov['expectancy_r']:+.3f}  "
                    f"PF={ov['profit_factor']}  IS={is_e:+.3f}({s['is_trade_count'] or 0})  "
                    f"OOS={oos_e:+.3f}({s['oos_trade_count'] or 0})  top1={s['top1_symbol'] or '-'}  "
                    f"{time.time()-t0:.1f}s"
                )


if __name__ == "__main__":
    main()
