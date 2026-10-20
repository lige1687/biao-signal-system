#!/usr/bin/env python3
"""a6_5 三件套实验：结构止损 + ATR 止盈 + 早断亏损（任务 J，2026-09-02）。

任务来源：exit-structural-stop-revival-ARCHIVE-2026-09-01.md 第五节机制层证伪
与第八节下一步方向第 1 条（用户已拍板）。该报告用逐笔数据证明默认出场 a6_1
（抵扣价）的优势来自两个部件——「早断亏损」（B/C 均亏仅 −0.9R/−0.5R）+
「盈利不封顶」（A 均盈 +7.9R）；上一轮（Prompt G，a6_4）只补了止盈部件
（最优臂 3×ATR），止血但离 a6_1 还差一个数量级，诊断「只补一半救不回来」。
本实验补上第三个部件（早断亏损），检验三件套能否达到「不劣于默认 a6_1」。

===========================================================================
一、变体定义（事前固化）
===========================================================================
a6_5 = 三件组合，全部「收盘确认、次根开盘执行」（引擎 §3.3 纪律）：
1) 结构止损（a6_3 逐字保留）：close < stop_price(C) → 次日开盘离场；
2) ATR 止盈（复用 exit_revival_a64 已验证最优的 3×ATR 档）：
   close ≥ entry + 3.0 × ATR20(信号日) → 次日开盘离场；
3) 早断亏损（本实验新设计，不照抄 a6_1 抵扣价公式）：
   入场后 M 个交易日内（含入场日）且 close < entry − X × ATR20(信号日)
   → 视为「未达预期」提前离场。与结构止损的分野：结构止损等「真正跌破
   结构位」才认输（右侧确认），早断在「浮亏超 X×ATR 但结构未破」时即
   认输（左侧预防）——两种不同的早断哲学，测后者能否还原抵扣价的早断
   效果。同根收盘若已跌破结构位，结构止损优先（保守，与 a6_4 同约定）。
预注册参数网格：M ∈ {5, 10, 15} × X ∈ {1.0, 1.5, 2.0}，共 9 臂。
ATR20(信号日) 不可得（NaN/≤0）的笔：早断与止盈均不启用，退化为纯 a6_3
（单独计数披露）。
对照臂（同脚本同 specs）：a6_1 抵扣价（J2 基线）、a6_3 纯结构止损、
a6_4a_atr3（两件套=止损+止盈，无早断，用于分解第三件的边际贡献）。

===========================================================================
二、口径（复现必读——2026-09-02 环境重建披露）
===========================================================================
【环境现状】8-31 出场矩阵与 9-1 两轮出场实验的运行环境已部分灭失：
- 回测深池 ~/.lei_signal_lab/backtest_pool（175 标的，东财 10 年回填，
  数据截至 2026-08-28）从磁盘消失，成分未入 git；
- stash a816485f（v2 检测器富版本）/ stash^3 1a321ce6（rules.v2.yaml）
  对象不存在（本仓库为 fresh clone，reflog 仅 clone/checkout/pull 三条）；
- 工作台历史 run 记录 ~/.lei_signal_lab/backtest_runs/*.json 已删除。
因此 exit_revival_a64 README 的原配方（git archive + stash 叠加 + 8-31 run
反构）不可执行；基线「逐位复现 8-31 矩阵数字」的门槛客观上无法再设。

【本实验的替代锚（幸存 git 归档）】specs 不再由检测器复算，而是从
raw/lifecycle_combo/ 三个 2026-08-27 工作台 run 的全量逐笔行反构
（stop-loss-matrix 同源做法）——当时真实代码产出的 spec 集合：
- A : T2_A_ETF_cm05_shrink.json  early+shrink+cm0.5+a6_1，45 ETF，283 笔
- B': T1_Bp_a61.json             breakout+cb30/cl3%+a6_1，83 个股，101 笔
- C : T2_C_stocks_v3_b15.json    v3+bias−15%+a6_1，       83 个股，177 笔
数据窗 2016-08-24 → 2026-08-25（10 年）。行情用腾讯 qfq 分页回填重建
（东财源本机网络不可达；fetch_pool.py，127 标的并集，落
raw/exit_three_piece/pool/）。已知偏差：参考数据为东财 fqt=1（8-27 抓取），
本池为腾讯 qfq（9-02 抓取），复权因子与抓取日不同 → 模拟层小幅漂移，
由下列锚定门槛量化。引擎/费用/指标全部走 HEAD(52f5cb3) 已提交生产代码；
账本用 stop-loss-matrix 同款重建（rules.v1 + 代码默认条目 + 126 锚点），
仅 fees/strict_structure/clock 三项参与模拟路径，值=代码默认。

【锚定门槛（AG0–AG3，跑前写死；任一不过 → 整份结果标记
environment_valid=false，不得作正面结论，只能归档为环境证伪）】
- AG0：参考逐笔行 100% 可映射（signal_date 在帧内、笔数恰等
  283/101/177），否则中止退出；
- AG1：入场价漂移 —— 已入场笔中 ≥90% 满足 |重放入场价/归档入场价 − 1|
  ≤ 1.0%；
- AG2：出场漂移 —— 已平仓笔中 ≥70% exit_date 逐日一致，且 ≥85%
  exit_reason 一致（重放 a6_1 vs 归档行）；
- AG3：总体漂移 —— 逐模块 |ΔexpR| ≤ 0.40R 且 |ΔPF| ≤ 0.40（重放 a6_1
  的 standard·net 口径 vs 归档行自算口径）。

【与 8-31/9-1 归档数字的可比性】本实验样本（283/101/177 笔，45 ETF+83
个股池）小于出场矩阵（1469/552/224 笔，175 标的全池）；绝对数字不可与
exit-structural-stop-revival 结果矩阵直接对比，J2 的 a6_1 基线一律取
同脚本同 specs 重放值。所有判定只在本实验宇宙内成立；报告须注明
B 模块 101 笔的小样本限制。

===========================================================================
三、判定标准（预注册，跑之前写死，跑完不得调整）
===========================================================================
口径：腾讯 qfq 重建池（127 标的并集）、数据截至 2026-08-25、
rr_min=None（specs 已定）、limit_guard=True、净 R 口径（net=True）、
主判 fee=standard（单边 5bp）、压力档 conservative（10bp，不参与判定）。
- J1 止血（模块级）：expR > 0 且 PF > 1；
- J2 不劣于默认（模块级）：expR ≥ 同模块同脚本重放 a6_1 的 expR 且
  PF ≥ 同模块重放 a6_1 的 PF（严格无容差；沿用 exit_revival 定义）；
- J3 邻域稳健（模块级）：9 臂全部过 J1；
- J4 跨模块：同一 (M, X) 档在 ≥2/3 模块过 J2 → 跨模块复活候选；
  恰 1 模块 → 模块特定候选；0 模块 → 复活失败（J1 通过也只能表述为
  「止血成功但仍逊于默认」）。
- 分解义务（非门，报告必备）：逐模块给出 a6_1 / a6_3 / a6_4a_atr3 /
  各 a6_5 臂的均盈/均亏/持仓天数/胜率，回答「早断部件是否把均亏拉回
  接近 a6_1 水平」，对齐 exit_revival 第五节格式。

【安全约束】只读研究：不改 src/ 任何生产代码（引擎以库方式导入，
a6_4/a6_5 出场循环在本脚本内复刻）；不 push、不删文件；产出仅本脚本 +
raw/exit_three_piece/ 下新文件。

复现：LEI_BACKTEST_POOL_ROOT 无需设置（脚本显式指向重建池目录）。
  /path/to/venv/python scripts/run_exit_three_piece.py
双跑：PYTHONHASHSEED=0 与 =42 各跑一次，结果 JSON sha256 必须一致。
输出：docs/experiments/raw/exit_three_piece/exit_three_piece_results.json
（无时间戳字段，字节确定）。
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import sys
import tempfile
from dataclasses import asdict
from datetime import date
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

# 兼容 shim（与 run_exit_revival_a64.py 同源处理：提交版 first_ma_pullback
# 不再导出引擎 import 的两个常量；值取工作台口径，仅进程内补齐）。
import lei_signal.rules.first_ma_pullback as _fmp  # noqa: E402

if not hasattr(_fmp, "ENTRY_EARLY"):
    _fmp.ENTRY_EARLY = "early"
if not hasattr(_fmp, "ENTRY_CONFIRMED"):
    _fmp.ENTRY_CONFIRMED = "confirmed"

from lei_signal.backtest.engine import (  # noqa: E402
    EXIT_COSTBASIS,
    EXIT_STRUCTURE_STOP,
    EntrySpec,
    FeeModel,
    Trade,
    is_cn_symbol,
    prepare_frame,
    simulate_trade,
)
from lei_signal.backtest.metrics import compute_metrics  # noqa: E402
from lei_signal.backtest.runner import load_pool_frames  # noqa: E402

RAW_DIR = REPO / "docs/experiments/raw/exit_three_piece"
POOL_DIR = RAW_DIR / "pool"
REF_DIR = REPO / "docs/experiments/raw/lifecycle_combo"
OUT_PATH = RAW_DIR / "exit_three_piece_results.json"

#: 参考 run（2026-08-27 工作台归档，specs 逐笔反构源）。
REFERENCE_RUNS = {
    "A": {"file": "T2_A_ETF_cm05_shrink.json", "trades": 283},
    "B": {"file": "T1_Bp_a61.json", "trades": 101},
    "C": {"file": "T2_C_stocks_v3_b15.json", "trades": 177},
}

DATA_CUTOFF = "2026-08-25"  # 参考 run data_range.end

#: 预注册参数（docstring 判定标准的机器可读副本，两边必须一致）。
TP_ATR_MULT = 3.0
CUT_DAYS = (5, 10, 15)
CUT_ATR_MULTS = (1.0, 1.5, 2.0)

#: 锚定门槛（AG1–AG3，docstring 同源）。
GATE_ENTRY_RATIO = 0.90
GATE_ENTRY_TOL = 0.01
GATE_EXITDATE_RATIO = 0.70
GATE_EXITREASON_RATIO = 0.85
GATE_EXPDR_TOL = 0.40
GATE_PF_TOL = 0.40

FEE_LABELS = ("standard", "conservative")


#: 重建账本：提交版文本 + 缺失规则条目（值=代码默认；stop-loss-matrix 同款）。
_EXTRA_RULES = """
  fees_and_slippage:
    provenance: user_config
    note_cn: 2026-09-02 环境重建·脚本进程内重建；值=engine.FeeModel 代码默认（standard 单边 5bp + $0.005/股）
    params:
      stock_fee_bps: 5.0
      stock_per_share_usd: 0.005
  strict_structure:
    provenance: research_proxy
    note_cn: 2026-09-02 环境重建·脚本进程内重建；值=strict_structure.py 代码默认（仅影响 a6_2 出场，本实验不用）
    params:
      containment_merge: true
      min_bars: 3
      min_wave_bars: 6
  clock_classifier:
    provenance: research_proxy
    note_cn: 2026-09-02 环境重建·脚本进程内重建；值=clock_classifier.py 代码默认（不门控入场，仅证据标注）
    params:
      window: 60
      window_s20: 20
      annualization: 252
      type3_max_abs_s60: 0.10
      type2_min_s60: 0.10
      type1_min_s60: 1.00
      type1_s20_multiple: 2.0
      type1_s60_floor: 0.40
  module_d_false_breakout:
    provenance: research_proxy
    note_cn: 2026-09-02 环境重建·脚本进程内重建；值=module_d_false_breakout.py 代码默认（本实验不用）
    params:
      reclaim_window: 5
      zone_exit_bars: 20
  trend_stage:
    provenance: research_proxy
    note_cn: 2026-09-02 环境重建·脚本进程内重建；该规则仅做登记校验、无参数读取
"""


def build_reconstructed_ledger() -> Path:
    text = (REPO / "configs" / "rules.v1.yaml").read_text(encoding="utf-8")
    if "minimum_consolidation_bars: 126" not in text:
        if "minimum_consolidation_bars: 120" not in text:
            raise RuntimeError("tradability_gate 锚点既非 120 也非 126，重建中止")
        text = text.replace(
            "minimum_consolidation_bars: 120",
            "minimum_consolidation_bars: 126", 1,
        )
    lines = text.splitlines(keepends=True)
    rules_idx = next(i for i, ln in enumerate(lines) if ln.startswith("rules:"))
    end_idx = len(lines)
    for i in range(rules_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped and not lines[i][0].isspace() and not lines[i].startswith("#"):
            end_idx = i
            break
    merged = "".join(lines[:end_idx]) + _EXTRA_RULES + "".join(lines[end_idx:])
    tmp_dir = Path(tempfile.mkdtemp(prefix="lei_rules_rebuild_j_"))
    path = tmp_dir / "rules.v1.yaml"
    path.write_text(merged, encoding="utf-8")
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for rid in ("fees_and_slippage", "strict_structure", "clock_classifier",
                "tradability_gate", "volume_proxies"):
        assert rid in data["rules"], f"重建账本缺 {rid}"
    return path


@contextlib.contextmanager
def reconstructed_ledger():
    from lei_signal.domain import rules_config as rc

    tmp = build_reconstructed_ledger()
    rc.load_ruleset.cache_clear()
    orig_path = rc._default_config_path
    rc._default_config_path = lambda: tmp  # type: ignore[assignment]
    try:
        yield
    finally:
        rc.load_ruleset.cache_clear()
        rc._default_config_path = orig_path  # type: ignore[assignment]


def specs_from_reference_run(
    mkey: str, frames: dict[str, pd.DataFrame]
) -> tuple[dict[str, list[EntrySpec]], list[dict]]:
    """从参考 run JSON 的逐笔行反构 specs（stop-loss-matrix 同源做法）。

    clock_type/weekly_bull_env 纯标注字段不在 run JSON 里，取默认值
    （不参与模拟与判定）。
    """
    data = json.loads(
        (REF_DIR / REFERENCE_RUNS[mkey]["file"]).read_text(encoding="utf-8")
    )
    by_symbol: dict[str, list[EntrySpec]] = {}
    rows: list[dict] = []
    for row in data["trades"]:
        symbol = row["symbol"]
        frame = frames.get(symbol)
        if frame is None:
            raise RuntimeError(f"参考 run 标的不在重建池中: {symbol}")
        signal_date = date.fromisoformat(row["signal_date"])
        ts = pd.Timestamp(signal_date)
        if ts not in frame.index:
            raise RuntimeError(f"{symbol} 信号日 {signal_date} 不在帧内")
        position = int(frame.index.get_loc(ts))
        close = float(frame["close"].iloc[position])
        specs = by_symbol.setdefault(symbol, [])
        specs.append(EntrySpec(
            symbol=symbol,
            signal_date=signal_date,
            signal_position=position,
            entry_ref_price=(
                float(row["entry_price"])
                if row["exit_reason"] == "signal_at_end_not_entered"
                else close
            ),
            stop_price=float(row["stop_price"]),
            target_price=(
                None if row["target_price"] is None
                else float(row["target_price"])
            ),
            target_source="ref_run",
            reward_risk=(
                None if row["reward_risk"] is None
                else float(row["reward_risk"])
            ),
            entry_variant=str(row["entry_variant"]),
            is_first_touch=bool(row.get("is_first_touch", False)),
            ma_period=int(row.get("ma_period", 0)),
            clock_type=0,
            weekly_bull_env=False,
            trend_stage=int(row.get("trend_stage", 0)),
            event_id=f"ref:{symbol}:{row['signal_date']}:{len(specs)}",
            entry_reason=str(row.get("entry_reason", "")),
            breakout_reference=None,
        ))
        rows.append(row)
    return by_symbol, rows


def simulate_trade_a65(
    frame: pd.DataFrame,
    spec: EntrySpec,
    *,
    tp_mult: float | None,
    cut_days: int | None,
    cut_atr_mult: float | None,
    fee: FeeModel,
    prepared: dict,
    limit_guard: bool = False,
) -> Trade:
    """a6_4/a6_5 出场循环：engine.simulate_trade 的逐行副本 + 止盈/早断分支。

    tp_mult=None 且 cut_days=None 即纯 a6_3；仅 tp_mult 给值为两件套 a6_4a；
    三者齐给为三件套 a6_5。执行纪律：结构止损 > 早断 > 止盈（同根收盘
    同时满足时保守者优先）；全部收盘确认、次根开盘执行；A 股跌停顺延
    （limit_guard 与引擎同一实现）。
    """
    exit_variant = (
        f"a6_5_M{cut_days}_X{cut_atr_mult:g}_tp{tp_mult:g}"
        if cut_days is not None
        else (f"a6_4a_tp{tp_mult:g}" if tp_mult is not None else "a6_3_replica")
    )
    entry_position = spec.signal_position + 1
    if (
        limit_guard
        and is_cn_symbol(spec.symbol)
        and entry_position < len(frame)
        and entry_position >= 1
    ):
        prev_close = float(frame["close"].iloc[entry_position - 1])
        open_price = float(frame["open"].iloc[entry_position])
        if prev_close > 0 and open_price >= prev_close * 1.095:
            return Trade(
                symbol=spec.symbol, entry_variant=spec.entry_variant,
                exit_variant=exit_variant, is_first_touch=spec.is_first_touch,
                ma_period=spec.ma_period, clock_type=spec.clock_type,
                weekly_bull_env=spec.weekly_bull_env, trend_stage=spec.trend_stage,
                signal_date=spec.signal_date,
                entry_date=frame.index[entry_position].date(),
                entry_price=open_price, stop_price=spec.stop_price,
                target_price=spec.target_price, reward_risk=spec.reward_risk,
                exit_reason="skipped_limit_up_at_entry",
            )
    if entry_position >= len(frame):
        return Trade(
            symbol=spec.symbol, entry_variant=spec.entry_variant,
            exit_variant=exit_variant, is_first_touch=spec.is_first_touch,
            ma_period=spec.ma_period, clock_type=spec.clock_type,
            weekly_bull_env=spec.weekly_bull_env, trend_stage=spec.trend_stage,
            signal_date=spec.signal_date,
            entry_date=spec.signal_date,
            entry_price=spec.entry_ref_price, stop_price=spec.stop_price,
            target_price=spec.target_price, reward_risk=spec.reward_risk,
            exit_reason="signal_at_end_not_entered",
        )
    trade = Trade(
        symbol=spec.symbol, entry_variant=spec.entry_variant,
        exit_variant=exit_variant, is_first_touch=spec.is_first_touch,
        ma_period=spec.ma_period, clock_type=spec.clock_type,
        weekly_bull_env=spec.weekly_bull_env, trend_stage=spec.trend_stage,
        signal_date=spec.signal_date,
        entry_date=frame.index[entry_position].date(),
        entry_price=float(frame["open"].iloc[entry_position]),
        stop_price=spec.stop_price, target_price=spec.target_price,
        reward_risk=spec.reward_risk,
        meta={"entry_reason": spec.entry_reason},
    )
    risk = trade.entry_price - spec.stop_price
    if risk <= 0:
        trade.exit_reason = "invalid_nonpositive_risk"
        trade.exit_date = trade.entry_date
        trade.exit_price = trade.entry_price
        trade.r_gross = 0.0
        trade.r_net = 0.0
        return trade

    atr_signal = float(prepared["atr20"].iloc[spec.signal_position])
    atr_ok = pd.notna(atr_signal) and atr_signal > 0
    tp_price = (
        trade.entry_price + tp_mult * atr_signal
        if tp_mult is not None and atr_ok else None
    )
    cut_level = (
        trade.entry_price - cut_atr_mult * atr_signal
        if cut_days is not None and atr_ok else None
    )

    def close_at(position: int, reason: str) -> Trade:
        exit_position = position + 1
        while (
            limit_guard
            and is_cn_symbol(spec.symbol)
            and exit_position < len(frame)
            and exit_position >= 1
            and float(frame["close"].iloc[exit_position - 1]) > 0
            and float(frame["open"].iloc[exit_position])
            <= float(frame["close"].iloc[exit_position - 1]) * 0.905
        ):
            exit_position += 1
        if exit_position >= len(frame):
            trade.exit_reason = f"{reason}(数据末尾未执行)"
            trade.holding_bars = position - entry_position
            return trade
        trade.exit_date = frame.index[exit_position].date()
        trade.exit_price = float(frame["open"].iloc[exit_position])
        trade.exit_reason = reason
        trade.holding_bars = exit_position - entry_position
        gross = (trade.exit_price - trade.entry_price) / risk
        fees = fee.round_trip_fraction(trade.entry_price)
        trade.r_gross = gross
        trade.r_net = ((trade.exit_price / trade.entry_price - 1.0) - fees) * (
            trade.entry_price / risk
        )
        return trade

    for position in range(entry_position, len(frame)):
        close = float(frame["close"].iloc[position])
        if close < spec.stop_price:
            return close_at(position, "structure_stop_C")
        days_held = position - entry_position + 1  # 入场日记第 1 日（含入场日）
        if (
            cut_level is not None
            and days_held <= int(cut_days)
            and close < cut_level
        ):
            return close_at(position, f"early_cut_M{cut_days}_X{cut_atr_mult:g}")
        if tp_price is not None and close >= tp_price:
            return close_at(position, f"tp_atr{tp_mult:g}")
    trade.holding_bars = len(frame) - 1 - entry_position
    trade.exit_reason = "open_at_end"
    return trade


def exit_reason_counts(trades: list[Trade]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in trades:
        key = t.exit_reason or "(none)"
        if key.endswith("(数据末尾未执行)"):
            key = key[: -len("(数据末尾未执行)")] + "@数据末尾"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def metrics_of(trades: list[Trade]) -> dict:
    d = asdict(compute_metrics(trades, label="全部", net=True))
    d.pop("label", None)
    return d


def anchor_stats(trades: list[Trade], ref_rows: list[dict]) -> dict:
    """重放 a6_1 vs 参考行的锚定统计（AG1/AG2/AG3 素材）。

    匹配键 (symbol, signal_date, is_first_touch)；参考侧行数应与重放逐笔
    一一对应（specs 即由参考行反构）。
    """
    pool: dict[tuple, list[dict]] = {}
    for row in ref_rows:
        pool.setdefault(
            (row["symbol"], row["signal_date"],
             bool(row.get("is_first_touch", False))), []
        ).append(row)
    n_entered = n_entry_ok = 0
    n_closed = n_exitdate_ok = n_exitreason_ok = 0
    dr_list: list[float] = []
    matched_pairs = 0
    for t in trades:
        key = (t.symbol, t.signal_date.isoformat(), t.is_first_touch)
        rows = pool.get(key)
        if not rows:
            continue
        row = rows.pop(0)
        matched_pairs += 1
        if t.exit_reason in ("signal_at_end_not_entered",
                             "skipped_limit_up_at_entry"):
            continue
        n_entered += 1
        arch_entry = float(row["entry_price"])
        if arch_entry > 0 and abs(t.entry_price / arch_entry - 1.0) <= GATE_ENTRY_TOL:
            n_entry_ok += 1
        if t.exit_date is not None and row.get("exit_date"):
            n_closed += 1
            if t.exit_date.isoformat() == row["exit_date"]:
                n_exitdate_ok += 1
            if t.exit_reason == row["exit_reason"]:
                n_exitreason_ok += 1
            arch_r = row.get("r_net")
            if arch_r is not None and t.r_net is not None:
                dr_list.append(t.r_net - float(arch_r))
    # AG3：总体 expR/PF 对照（参考行自算，同 compute_metrics 排除口径）
    closed_ref = [
        r for r in ref_rows
        if r.get("exit_date")
        and r.get("exit_reason") not in
        ("invalid_nonpositive_risk", "skipped_limit_up_at_entry")
    ]
    ref_vals = [float(r["r_net"]) for r in closed_ref if r.get("r_net") is not None]
    ref_expR = sum(ref_vals) / len(ref_vals) if ref_vals else None
    wins = sum(v for v in ref_vals if v > 0)
    losses = abs(sum(v for v in ref_vals if v <= 0))
    ref_pf = (wins / losses) if losses > 0 else None
    return {
        "matched_pairs": matched_pairs,
        "unmatched_ref_rows": sum(len(v) for v in pool.values()),
        "ag1": {"entered": n_entered, "entry_within_tol": n_entry_ok,
                "ratio": (n_entry_ok / n_entered) if n_entered else None},
        "ag2": {"closed": n_closed, "exit_date_equal": n_exitdate_ok,
                "exit_reason_equal": n_exitreason_ok,
                "ratio_date": (n_exitdate_ok / n_closed) if n_closed else None,
                "ratio_reason": (n_exitreason_ok / n_closed) if n_closed else None},
        "ag3_ref": {"expR": ref_expR, "pf": ref_pf, "n": len(ref_vals)},
    }


def judge(mod_results: dict) -> dict:
    """J1–J4 判定（standard·net；严格无容差）。"""
    out: dict = {"J1": {}, "J2": {}, "J3": {}, "J4": {}}
    for m, mods in mod_results.items():
        a61 = mods["variants"]["a6_1_costbasis"]["standard"]["metrics"]
        j2_count = 0
        for vname, vdata in mods["variants"].items():
            if vname == "a6_1_costbasis":
                continue
            mtr = vdata["standard"]["metrics"]
            j1 = (mtr["expectancy_r"] or 0) > 0 and (mtr["profit_factor"] or 0) > 1
            out["J1"].setdefault(m, {})[vname] = bool(j1)
            j2 = (
                (mtr["expectancy_r"] or 0) >= (a61["expectancy_r"] or 0)
                and (mtr["profit_factor"] or 0) >= (a61["profit_factor"] or 0)
            )
            out["J2"].setdefault(m, {})[vname] = bool(j2)
            if vname.startswith("a6_5_"):
                j2_count += 1 if j2 else 0
        a65_names = [v for v in mods["variants"] if v.startswith("a6_5_")]
        out["J3"][m] = all(out["J1"][m][v] for v in a65_names)
    # J4：同一 (M, X) 档跨模块（"a6_5_M10_X1" → split[2:4] = ("M10","X1")）
    arms = sorted({
        tuple(v.split("_")[2:4]) for m in mod_results
        for v in mod_results[m]["variants"] if v.startswith("a6_5_")
    })
    for arm in arms:
        mid = f"a6_5_{arm[0]}_{arm[1]}"
        hits = sum(
            1 for m in mod_results if out["J2"][m].get(mid)
        )
        out["J4"][mid] = {
            "j2_modules": hits,
            "verdict": (
                "cross_module_candidate" if hits >= 2
                else ("module_specific_candidate" if hits == 1 else "fail")
            ),
        }
    return out


def main() -> None:
    print("加载重建池（腾讯 qfq，127 标的并集）...", flush=True)
    frames_full = load_pool_frames(str(POOL_DIR))
    frames = {s: f.loc[:DATA_CUTOFF] for s, f in frames_full.items()}
    print(f"池载入 {len(frames)} 标的（截至 {DATA_CUTOFF}）", flush=True)

    results: dict = {
        "meta": {
            "experiment": "exit_three_piece_a6_5",
            "date": "2026-09-02",
            "pool_symbols": len(frames),
            "data_cutoff": DATA_CUTOFF,
            "reference_runs": {
                m: f"raw/lifecycle_combo/{REFERENCE_RUNS[m]['file']}"
                for m in REFERENCE_RUNS
            },
            "tp_atr_mult": TP_ATR_MULT,
            "cut_days": list(CUT_DAYS),
            "cut_atr_mults": list(CUT_ATR_MULTS),
            "engine_commit": "52f5cb3",
        },
        "modules": {},
        "anchor_gate": {},
    }

    with reconstructed_ledger():
        fees = {label: FeeModel.from_ledger(label) for label in FEE_LABELS}
        for mkey in REFERENCE_RUNS:
            print(f"\n===== 模块 {mkey} =====", flush=True)
            by_symbol, ref_rows = specs_from_reference_run(mkey, frames)
            if len(ref_rows) != REFERENCE_RUNS[mkey]["trades"]:
                print(
                    f"[AG0 FAIL] 参考 {REFERENCE_RUNS[mkey]['trades']} 笔 != "
                    f"反构 {len(ref_rows)} 笔，中止", flush=True,
                )
                results["anchor_gate"]["AG0"] = "FAIL"
                payload = json.dumps(
                    results, ensure_ascii=False, indent=1, sort_keys=True
                )
                OUT_PATH.write_text(payload, encoding="utf-8")
                sys.exit(2)
            results["anchor_gate"].setdefault("AG0", "OK")

            symbol_specs: list[tuple] = []
            for symbol in sorted(by_symbol):
                frame = frames[symbol]
                prepared = prepare_frame(frame)
                for spec in by_symbol[symbol]:
                    symbol_specs.append((frame, prepared, spec))
            print(f"specs {len(symbol_specs)} 笔（AG0 OK）", flush=True)

            variants: dict = {}

            def run(name: str, sim_fn) -> None:
                out = {}
                for label, fee in fees.items():
                    trades = [
                        sim_fn(frame, spec, fee=fee, prepared=prepared,
                               limit_guard=True)
                        for frame, prepared, spec in symbol_specs
                    ]
                    out[label] = {
                        "metrics": metrics_of(trades),
                        "exit_reasons": exit_reason_counts(trades),
                    }
                m0 = out["standard"]["metrics"]
                print(f"  [{mkey}/{name}] {m0['trade_count']}笔 "
                      f"expR {m0['expectancy_r']:.3f} "
                      f"PF {m0['profit_factor']:.3f}", flush=True)
                variants[name] = out

            def base_sim(exit_variant):
                def _sim(frame, spec, *, fee, prepared, limit_guard):
                    return simulate_trade(
                        frame, spec, exit_variant=exit_variant, fee=fee,
                        prepared=prepared, limit_guard=limit_guard,
                    )
                return _sim

            def a65_sim(tp_mult, cut_days, cut_atr_mult):
                def _sim(frame, spec, *, fee, prepared, limit_guard):
                    return simulate_trade_a65(
                        frame, spec, tp_mult=tp_mult, cut_days=cut_days,
                        cut_atr_mult=cut_atr_mult, fee=fee,
                        prepared=prepared, limit_guard=limit_guard,
                    )
                return _sim

            run("a6_1_costbasis", base_sim(EXIT_COSTBASIS))
            run("a6_3_structure_stop", base_sim(EXIT_STRUCTURE_STOP))
            run("a6_4a_tp3", a65_sim(TP_ATR_MULT, None, None))
            for m in CUT_DAYS:
                for x in CUT_ATR_MULTS:
                    run(f"a6_5_M{m}_X{x:g}", a65_sim(TP_ATR_MULT, m, x))

            # 锚定统计（重放 a6_1 vs 参考行）
            a61_trades = [
                simulate_trade(frame, spec, exit_variant=EXIT_COSTBASIS,
                               fee=fees["standard"], prepared=prepared,
                               limit_guard=True)
                for frame, prepared, spec in symbol_specs
            ]
            anchor = anchor_stats(a61_trades, ref_rows)
            replay = metrics_of(a61_trades)
            ref_exp = anchor["ag3_ref"]["expR"]
            ref_pf = anchor["ag3_ref"]["pf"]
            anchor["ag3_replay"] = {
                "expR": replay["expectancy_r"], "pf": replay["profit_factor"],
                "d_expR": (
                    (replay["expectancy_r"] or 0) - ref_exp
                    if ref_exp is not None else None
                ),
                "d_pf": (
                    (replay["profit_factor"] or 0) - ref_pf
                    if ref_pf is not None else None
                ),
            }
            ag1_ratio = anchor["ag1"]["ratio"]
            ag2_date = anchor["ag2"]["ratio_date"]
            ag2_reason = anchor["ag2"]["ratio_reason"]
            d_expR = anchor["ag3_replay"]["d_expR"]
            d_pf = anchor["ag3_replay"]["d_pf"]
            ag1_ok = ag1_ratio is not None and ag1_ratio >= GATE_ENTRY_RATIO
            ag2_ok = (
                ag2_date is not None and ag2_date >= GATE_EXITDATE_RATIO
                and ag2_reason is not None
                and ag2_reason >= GATE_EXITREASON_RATIO
            )
            ag3_ok = (
                d_expR is not None and abs(d_expR) <= GATE_EXPDR_TOL
                and d_pf is not None and abs(d_pf) <= GATE_PF_TOL
            )
            anchor["verdict"] = {
                "AG1": bool(ag1_ok), "AG2": bool(ag2_ok), "AG3": bool(ag3_ok),
            }
            print(f"  锚定: AG1 {anchor['ag1']['ratio']:.3f} "
                  f"AG2 {anchor['ag2']['ratio_date']:.3f}/"
                  f"{anchor['ag2']['ratio_reason']:.3f} "
                  f"AG3 ΔexpR {anchor['ag3_replay']['d_expR']:+.3f} "
                  f"ΔPF {anchor['ag3_replay']['d_pf']:+.3f}", flush=True)

            # ATR 不可得笔（早断/止盈退化计数）
            no_atr = sum(
                1 for _f, p, spec in symbol_specs
                if not (pd.notna(p["atr20"].iloc[spec.signal_position])
                        and float(p["atr20"].iloc[spec.signal_position]) > 0)
            )

            results["modules"][mkey] = {
                "specs": len(symbol_specs),
                "no_atr_degenerated": no_atr,
                "anchor": anchor,
                "variants": variants,
            }

    results["judgments"] = judge(results["modules"])
    results["anchor_gate"]["overall"] = (
        "VALID"
        if all(
            all(results["modules"][m]["anchor"]["verdict"].values())
            for m in results["modules"]
        ) else "INVALID"
    )

    payload = json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True)
    OUT_PATH.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    print(f"\n锚定门槛: {results['anchor_gate']['overall']}")
    print(f"J4: " + json.dumps(
        {k: v["verdict"] for k, v in results["judgments"]["J4"].items()},
        ensure_ascii=False))
    print(f"落盘: {OUT_PATH}")
    print(f"sha256(canonical json) = {digest}")


if __name__ == "__main__":
    main()
