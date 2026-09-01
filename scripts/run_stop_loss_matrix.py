#!/usr/bin/env python3
"""止损方式跨模块统一测试·矩阵（2026-09-01，九任务拆分 Prompt I）。

【研究问题】是否存在一种止损方式（ATR 倍数 / 时间 / 追踪），叠加在
现行默认出场（初始结构止损 C + A6① 抵扣价出场）之上，能跨 A/B'/C/D
四个入场模块普遍改善 expR/PF——即「止损方式」作为独立于入场模块的
维度是否成立。四路归档中唯一沾边的是 exit-matrix-2026-08-31（整套
出场变体的移植测试），「止损方式本身跨模块」从未被系统性问过。

【机制边界（不重复已判负实验）】a6_3（纯结构止损、无止盈）三模块全
灾难已被 exit-matrix 判负，其诊断是「止盈不可省」；本实验因此不测
「止损替代全部出场」的变体，只测「附加止损触发叠加在默认出场之上
（先触发先出）」——这隔离的正是止损维度本身。

【设计（事前固化）】
- 基准 = a6_1 抵扣价（结构止损 C + 抵扣价出场）。模块冻结配置与
  exit-matrix 一致：A=early+volume_filter=shrink+clock_mult0.5；
  B'=breakout+cb30/cl3%；C=v3+深乖离-0.15；D=默认单版本（无历史
  冻结配置，用工作台默认：无过滤、无参数覆盖）。公共：全池
  （工作台同源池，基准 run 记录 175 标的）、数据截至 2026-08-28
  （与基准 run 同窗）、rr_min=None、fee=standard（单边 5bp）、
  limit_guard=True、净 R 口径（net=True，与工作台总览一致）。
- 候选止损（收盘确认、次根开盘执行，与引擎执行纪律一致）：
  1) ATR 止损：close < 入场价 − k × ATR20(信号日)，k ∈ {1.5, 2.0, 2.5}。
     ATR20 取信号日值（入场决策时已知，无泄漏）；ATR 不可得（NaN）
     时该触发不生效。
  2) 时间止损：持仓满 N 根 K 线（含入场日）且入场以来最高收盘
     ≤ 入场价（「无进展」= 从未有过收盘浮盈）→ 强制离场，
     N ∈ {10, 20, 40}。
  3) 追踪止损：peak = 入场以来最高收盘 > 入场价 且
     close < 入场价 + p × (peak − 入场价)（锁定峰值浮盈比例 p），
     p ∈ {0.5, 0.7, 0.9}。
- 矩阵：4 模块 ×（1 基准 + 9 候选）= 40 格。

【判定标准（事前固化，跑前写死，不得事后调整）】
1. 有效性前提：A/B'/C 的 specs 从工作台 08-31 基准 run 的逐笔交易清单
   反构（20260831-231254 / 231715 / 231944，见 raw/exit_matrix），重放的
   a6_1 基准必须同时满足：指标一致（笔数相等、|ΔexpR|<0.005、
   |ΔPF|<0.01）且逐笔锚定零失配（exit_date/exit_reason/r_net 全对上
   归档行），且「无附加止损」复刻路径与引擎 simulate_trade(a6_1)
   逐笔零失配——任一不满足则整份结果作废，不得解读。反构的原因：
   stash 版 two_b_reversal 检测器与 08-31 运行版本漂移（检测器复算
   C=201 笔≠归档 224 笔；A/B 检测器复算已逐位一致，反构为对称加固）。
   D 模块无全池历史对照，用检测器复算 specs，仅同脚本内自比较。
2. 「不劣于」：ΔexpR ≥ −0.10R 且 ΔPF ≥ −0.10（点估计）。
3. 「显著改善」：在基准已平仓笔集合上做逐笔配对 bootstrap
   （10000 次重采样，固定种子 numpy RandomState(20260901)），
   ΔexpR 的 95% percentile CI 下界 > 0。
4. 跨模块普适候选：同一候选类存在至少一个参数点在 ≥3/4 模块
   「不劣于」且 ≥1 模块「显著改善」。
5. 模块特定候选：未达第 4 条，但某模块某参数点「显著改善」且该类
   参数的邻域点（同类其余参数）中至少一个同向改善（防单点噪音）。
6. 其余归档为证伪。
7. 时间止损专项义务（heiti-ARCHIVE 右尾事实：41+ 天长持单 55 笔
   占三流合并利润 164%）：逐模块量化基准下 41+ 天长持单的
   笔数/累计净 R/占全部净 R 之比，以及各 N 值把基准 41+ 天单
   提前截断的笔数与其 ΔR 合计——此代价必须与止损收益同表呈现。

【安全约束】只读研究：不改 src/ 任何生产代码（引擎以库方式导入，
出场循环在本脚本内复刻并加附加触发）、不 push、不删文件；
新增产出仅本脚本 + docs/experiments/raw/stop_loss_matrix/。

【账本与检测器重建披露（数据工程欠账，必读）】2026-09-01 上午工作区
被回退：configs/rules.v1.yaml 回到已提交版（丢失 backtest 包依赖的
fees_and_slippage / strict_structure / clock_classifier / trend_stage /
module_d_false_breakout 条目与 tradability_gate 126 锚点），且提交版
检测器（first_ma_pullback 等）证据字段过旧（无 stop_price/entry_variant
等引擎契约字段），富版本只存活于 stash@{0}。本脚本两步重建，全部
只读、进程内完成，不改 src/ 与 configs/ 任何文件：
① 账本：提交版文本 + 缺失条目（参数=代码默认/文档口径：fees 5bp+
$0.005/股、shrink 3/3、strict_structure 3/6/true、clock 代码默认、
module_d 5/20、consolidation 120→126）；
② 检测器：git show stash@{0} 读 6 个 pre-revert 规则模块源码 exec
覆盖进进程内模块对象（快照落 raw/stop_loss_matrix/pre_revert_modules/
供复现）。
重建忠实性由判定标准第 1 条的基准复现门槛验证（A/B'/C 的 expR/PF/
笔数与工作台 08-31 历史 run 完全一致才算数）；strict_structure 参数
仅影响 a6_2 出场（本实验不用），clock 分类不门控任何入场（仅证据
标注）。D 模块无历史对照，其绝对数字受重建影响，但矩阵内部为同
脚本自比较（候选 vs 同脚本基准），相对结论不受影响——引用 D 数字
时必须注明此局限。

复现：PYTHONHASHSEED=0 python3 scripts/run_stop_loss_matrix.py
双跑：PYTHONHASHSEED=0 / 42 各跑 --dump-hash，两次 md5 一致才入档。
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

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# 兼容 shim（与 scripts/run_exit_revival_a64.py 同源处理：2026-09-01 工作区
# 规则文件被回退到已提交版本，丢掉未跟踪 backtest 包依赖的两个常量；
# 值取自运行中工作台服务口径，仅在本脚本进程内补齐，不改 src/ 任何文件）。
import lei_signal.rules.first_ma_pullback as _fmp  # noqa: E402

if not hasattr(_fmp, "ENTRY_EARLY"):
    _fmp.ENTRY_EARLY = "early"
if not hasattr(_fmp, "ENTRY_CONFIRMED"):
    _fmp.ENTRY_CONFIRMED = "confirmed"

from lei_signal.backtest import service  # noqa: E402
from lei_signal.backtest.engine import (  # noqa: E402
    EXIT_COSTBASIS,
    FeeModel,
    Trade,
    entry_specs_from_events,
    prepare_frame,
    simulate_trade,
)
from lei_signal.backtest.entry_filters import (  # noqa: E402
    filter_specs_by_bias,
    filter_specs_by_shrink,
)
from lei_signal.backtest.metrics import compute_metrics  # noqa: E402
from lei_signal.backtest.runner import load_pool_frames  # noqa: E402

DATA_CUTOFF = "2026-08-28"  # 与基准 run（20260831-*）同窗
BOOT_N = 10_000
BOOT_SEED = 20_260_901

#: 基准 run（工作台历史，raw/exit_matrix/exit_matrix_results.json 同源）。
#: A/B/C 的 specs 从这些 run 的逐笔交易清单反构（08-31 真实代码产出的
#: spec 集合，逐笔锚定——因 stash 版 two_b_reversal 与 08-31 运行版本
#: 存在漂移，检测器复算的 C specs 为 201 笔≠归档 224 笔；A/B 检测器
#: 复算已逐位一致，反构为对称加固）。
REFERENCE = {
    "A": {"run_id": "20260831-231254-88cb12", "trades": 1469,
          "expR": 1.1792278030442684, "pf": 1.9663033302762718},
    "B": {"run_id": "20260831-231715-1bb6f2", "trades": 552,
          "expR": 0.3585329893728971, "pf": 1.5782903349521902},
    "C": {"run_id": "20260831-231944-b87a6b", "trades": 224,
          "expR": 0.1277477082902095, "pf": 1.382214463867003},
}
RUNS_DIR = Path.home() / ".lei_signal_lab" / "backtest_runs"

MODULE_CONFIGS = {
    "A": {"module": "A", "entry_variant": "early", "volume_filter": "shrink",
          "bias_filter": None,
          "overrides": (("clock_mult", 0.5),)},
    "B": {"module": "B", "entry_variant": "breakout", "volume_filter": "none",
          "bias_filter": None,
          "overrides": (("consolidation_bars", 30.0), ("cluster_threshold", 0.03))},
    "C": {"module": "C", "entry_variant": "v3", "volume_filter": "none",
          "bias_filter": -0.15, "overrides": ()},
    "D": {"module": "D", "entry_variant": None, "volume_filter": "none",
          "bias_filter": None, "overrides": ()},
}

#: 候选止损：(kind, param)；param 含义见 docstring。
STOP_CANDIDATES = (
    ("atr", 1.5), ("atr", 2.0), ("atr", 2.5),
    ("time", 10), ("time", 20), ("time", 40),
    ("trail", 0.5), ("trail", 0.7), ("trail", 0.9),
)


#: 重建账本：提交版文本 + 缺失规则条目（值=代码默认/文档口径，见 docstring 披露）。
_EXTRA_RULES = """
  fees_and_slippage:
    provenance: user_config
    note_cn: 2026-09-01 账本回退事故·脚本进程内重建；值=engine.FeeModel 代码默认（standard 单边 5bp + $0.005/股）
    params:
      stock_fee_bps: 5.0
      stock_per_share_usd: 0.005
  strict_structure:
    provenance: research_proxy
    note_cn: 2026-09-01 账本回退事故·脚本进程内重建；值=strict_structure.py 代码默认（仅影响 a6_2 出场，本实验不用）
    params:
      containment_merge: true
      min_bars: 3
      min_wave_bars: 6
  clock_classifier:
    provenance: research_proxy
    note_cn: 2026-09-01 账本回退事故·脚本进程内重建；值=clock_classifier.py 代码默认（含 clock_mult 覆盖锚点字面值）
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
    note_cn: 2026-09-01 账本回退事故·脚本进程内重建；值=module_d_false_breakout.py 代码默认
    params:
      reclaim_window: 5
      zone_exit_bars: 20
  trend_stage:
    provenance: research_proxy
    note_cn: 2026-09-01 账本回退事故·脚本进程内重建；该规则仅做登记校验、无参数读取（trend_stage.py）
"""


def build_reconstructed_ledger(repo: Path) -> Path:
    text = (repo / "configs" / "rules.v1.yaml").read_text(encoding="utf-8")
    if "minimum_consolidation_bars: 126" not in text:
        if "minimum_consolidation_bars: 120" not in text:
            raise RuntimeError("tradability_gate 锚点既非 120 也非 126，重建中止")
        text = text.replace(
            "minimum_consolidation_bars: 120",
            "minimum_consolidation_bars: 126", 1,
        )
    lines = text.splitlines(keepends=True)
    rules_idx = next(
        i for i, ln in enumerate(lines) if ln.startswith("rules:")
    )
    end_idx = len(lines)
    for i in range(rules_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped and not lines[i][0].isspace() and not lines[i].startswith("#"):
            end_idx = i
            break
    merged = "".join(lines[:end_idx]) + _EXTRA_RULES + "".join(lines[end_idx:])
    tmp_dir = Path(tempfile.mkdtemp(prefix="lei_rules_rebuild_"))
    path = tmp_dir / "rules.v1.yaml"
    path.write_text(merged, encoding="utf-8")
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for rid in ("fees_and_slippage", "strict_structure", "clock_classifier",
                "module_d_false_breakout", "tradability_gate", "volume_proxies"):
        assert rid in data["rules"], f"重建账本缺 {rid}"
    assert "minimum_consolidation_bars: 126" in merged
    return path


@contextlib.contextmanager
def reconstructed_ledger(repo: Path):
    """把 _default_config_path 指到进程内重建账本（跑完全程，不改文件）。"""
    from lei_signal.domain import rules_config as rc

    tmp = build_reconstructed_ledger(repo)
    rc.load_ruleset.cache_clear()
    orig_path = rc._default_config_path
    rc._default_config_path = lambda: tmp  # type: ignore[assignment]
    try:
        yield
    finally:
        rc.load_ruleset.cache_clear()
        rc._default_config_path = orig_path  # type: ignore[assignment]


REPO = Path(__file__).resolve().parents[1]

#: pre-revert 富版本检测器所在 stash（2026-09-01 回退事故；git show 只读提取）。
_STASH_REF = "stash@{0}"
_PRE_REVERT_MODULES = (
    "src/lei_signal/rules/tradability_gate.py",
    "src/lei_signal/rules/volume.py",
    "src/lei_signal/rules/reward_risk_filter.py",
    "src/lei_signal/rules/dense_breakout.py",
    "src/lei_signal/rules/first_ma_pullback.py",
    "src/lei_signal/rules/two_b_reversal.py",
)


def overlay_pre_revert_modules() -> dict[str, int]:
    """把 stash@{0} 的 pre-revert 规则模块 exec 覆盖进已导入的模块对象。

    背景与合法性（docstring「账本重建披露」同源事故）：backtest 包依赖的
    富版本检测器（evidence 带 stop_price/entry_variant/clock_type 等契约
    字段）只存在于 stash@{0}；提交版检测器证据字段缺失，specs 恒为空。
    本函数用 git show 读 stash 源码（只读），exec 到当前进程的模块对象，
    不写 src/ 任何文件。stash 源码快照落 raw/stop_loss_matrix/
    pre_revert_modules/（首次运行生成，之后优先读快照），保证 stash 被
    清理后实验仍可复现。engine 在 import 时绑定的 compute_reward_risk
    同步补丁到新版本。
    """
    import importlib
    import subprocess

    snap_dir = (REPO / "docs/experiments/raw/stop_loss_matrix"
                / "pre_revert_modules")
    snap_dir.mkdir(parents=True, exist_ok=True)
    patched: dict[str, int] = {}
    for rel in _PRE_REVERT_MODULES:
        snap = snap_dir / Path(rel).name
        if snap.exists():
            text = snap.read_text(encoding="utf-8")
        else:
            text = subprocess.run(
                ["git", "show", f"{_STASH_REF}:{rel}"], cwd=REPO,
                capture_output=True, text=True, check=True,
            ).stdout
            snap.write_text(text, encoding="utf-8")
        mod_name = (
            "lei_signal.rules." + Path(rel).stem
        )
        mod = importlib.import_module(mod_name)
        exec(compile(text, str(snap), "exec"), mod.__dict__)  # noqa: S102
        patched[mod_name] = len(text.splitlines())
    import lei_signal.backtest.engine as _engine_mod

    _engine_mod.compute_reward_risk = importlib.import_module(
        "lei_signal.rules.reward_risk_filter"
    ).compute_reward_risk
    return patched


_OVERLAY_INFO = overlay_pre_revert_modules()


def _detector(module: str):
    if module == "A":
        from lei_signal.rules.first_ma_pullback import (
            detect_first_ma_pullback_events,
        )
        return detect_first_ma_pullback_events
    if module == "B":
        from lei_signal.rules.dense_breakout import detect_dense_breakout_events
        return detect_dense_breakout_events
    if module == "C":
        from lei_signal.rules.two_b_reversal import detect_two_b_reversal_events
        return detect_two_b_reversal_events
    from lei_signal.rules.module_d_false_breakout import detect_module_d_events
    return detect_module_d_events


@contextlib.contextmanager
def patched_ledger(overrides: tuple[tuple[str, float], ...]):
    """复刻 service.execute_run 的账本参数覆盖（只读使用，不改 src/）。"""
    text = service._overrides_yaml(overrides)
    if text is None:
        yield
        return
    from lei_signal.domain import rules_config as rc

    tmp = Path(tempfile.mkdtemp()) / "rules.yaml"
    tmp.write_text(text, encoding="utf-8")
    rc.load_ruleset.cache_clear()
    orig_path = rc._default_config_path
    rc._default_config_path = lambda: tmp  # type: ignore[assignment]
    try:
        yield
    finally:
        rc.load_ruleset.cache_clear()
        rc._default_config_path = orig_path  # type: ignore[assignment]


def simulate_with_stop(
    frame: pd.DataFrame,
    spec,
    *,
    fee: FeeModel,
    prepared: dict,
    limit_guard: bool,
    stop_kind: str | None = None,
    stop_param: float | None = None,
) -> Trade:
    """复刻 engine.simulate_trade(exit_variant=a6_1) 的全部语义，仅在其
    出场检查链中插入一个附加止损触发（先触发先出）。

    stop_kind=None 时必须与引擎逐笔零失配（判定标准第 1 条的对照）。
    附加触发定义（docstring 事前固化）：
    - atr:  close < entry − k × ATR20(信号日)（NaN 不触发）
    - time: elapsed(含入场日) ≥ N 且入场以来最高收盘 ≤ entry
    - trail: peak(入场以来最高收盘) > entry 且 close < entry + p×(peak−entry)
    """
    entry_position = spec.signal_position + 1
    common = dict(
        symbol=spec.symbol, entry_variant=spec.entry_variant,
        is_first_touch=spec.is_first_touch, ma_period=spec.ma_period,
        clock_type=spec.clock_type, weekly_bull_env=spec.weekly_bull_env,
        trend_stage=spec.trend_stage, signal_date=spec.signal_date,
        stop_price=spec.stop_price, target_price=spec.target_price,
        reward_risk=spec.reward_risk,
    )
    if (
        limit_guard
        and engine_is_cn(spec.symbol)
        and entry_position < len(frame)
        and entry_position >= 1
    ):
        prev_close = float(frame["close"].iloc[entry_position - 1])
        open_price = float(frame["open"].iloc[entry_position])
        if prev_close > 0 and open_price >= prev_close * 1.095:
            return Trade(
                exit_variant=EXIT_COSTBASIS,
                entry_date=frame.index[entry_position].date(),
                entry_price=open_price,
                exit_reason="skipped_limit_up_at_entry", **common,
            )
    if entry_position >= len(frame):
        return Trade(
            exit_variant=EXIT_COSTBASIS,
            entry_date=spec.signal_date,
            entry_price=spec.entry_ref_price,
            exit_reason="signal_at_end_not_entered", **common,
        )
    trade = Trade(
        exit_variant=EXIT_COSTBASIS,
        entry_date=frame.index[entry_position].date(),
        entry_price=float(frame["open"].iloc[entry_position]),
        meta={"entry_reason": spec.entry_reason}, **common,
    )
    risk = trade.entry_price - spec.stop_price
    if risk <= 0:
        trade.exit_reason = "invalid_nonpositive_risk"
        trade.exit_date = trade.entry_date
        trade.exit_price = trade.entry_price
        trade.r_gross = 0.0
        trade.r_net = 0.0
        return trade

    costbasis = prepared["costbasis_cond"]
    atr_signal = prepared["atr20"].iloc[spec.signal_position]
    atr_stop = (
        float(stop_param) * float(atr_signal)
        if stop_kind == "atr" and pd.notna(atr_signal)
        else None
    )

    def close_at(position: int, reason: str) -> Trade:
        exit_position = position + 1
        while (
            limit_guard
            and engine_is_cn(spec.symbol)
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

    peak = float("-inf")
    for position in range(entry_position, len(frame)):
        close = float(frame["close"].iloc[position])
        if close > peak:
            peak = close
        if close < spec.stop_price:
            return close_at(position, "structure_stop_C")
        if atr_stop is not None and close < trade.entry_price - atr_stop:
            return close_at(position, f"stop_atr_k{stop_param}")
        if (
            stop_kind == "time"
            and position - entry_position + 1 >= int(stop_param)
            and peak <= trade.entry_price
        ):
            return close_at(position, f"stop_time_N{stop_param}")
        if (
            stop_kind == "trail"
            and peak > trade.entry_price
            and close < trade.entry_price
            + float(stop_param) * (peak - trade.entry_price)
        ):
            return close_at(position, f"stop_trail_p{stop_param}")
        if bool(costbasis.iloc[position]):
            return close_at(position, "exit_a6_1_costbasis")
    trade.holding_bars = len(frame) - 1 - entry_position
    trade.exit_reason = "open_at_end"
    return trade


def engine_is_cn(symbol: str) -> bool:
    from lei_signal.backtest.engine import is_cn_symbol

    return is_cn_symbol(symbol)


def specs_from_reference_run(
    mkey: str, frames: dict[str, pd.DataFrame]
) -> tuple[dict[str, list], list[dict]]:
    """从基准 run JSON 的逐笔清单反构 specs（08-31 真实代码的 spec 集合）。

    返回 (symbol -> specs, 参考 trade 行原序)。trade 行供逐笔锚定校验
    （重放的 a6_1 基准必须与参考行 exit_date/exit_reason/r_net 一致）。
    clock_type/weekly_bull_env 两个纯标注字段不在 run JSON 里，取默认值
    （不参与模拟与判定）。
    """
    from lei_signal.backtest.engine import EntrySpec

    data = json.loads(
        (RUNS_DIR / f"{REFERENCE[mkey]['run_id']}.json").read_text(
            encoding="utf-8"
        )
    )
    by_symbol: dict[str, list] = {}
    rows: list[dict] = []
    for row in data["trades"]:
        symbol = row["symbol"]
        frame = frames.get(symbol)
        if frame is None:
            raise RuntimeError(f"基准 run 标的不在池中: {symbol}")
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


def collect_module(mkey: str, frames: dict[str, pd.DataFrame]) -> dict[str, list]:
    """单模块全池 specs 收集 + 全部出场格的交易模拟（账本覆盖段内完成）。

    specs 来源：A/B/C = 基准 run 逐笔反构（锚定 08-31 真实 spec 集合，
    因 stash 版 two_b_reversal 检测器漂移，检测器复算 C 为 201 笔≠归档
    224 笔，反构后需通过逐笔锚定校验）；D = 检测器复算（无全池历史
    对照，见 docstring 披露）。
    """
    mcfg = MODULE_CONFIGS[mkey]
    use_reference = mkey in REFERENCE
    if not use_reference:
        detector = _detector(mcfg["module"])
        from lei_signal.features.pivots import confirmed_pivots

    cells: dict[str, list[Trade]] = {"baseline": []}
    for kind, param in STOP_CANDIDATES:
        cells[f"{kind}_{param}"] = []
    equivalence_mismatches = 0
    anchor_mismatches: int | None = None
    ref_rows: list[dict] = []
    repo = Path(__file__).resolve().parents[1]

    with reconstructed_ledger(repo), patched_ledger(mcfg["overrides"]):
        fee = FeeModel.from_ledger("standard")
        if use_reference:
            ref_specs_map, ref_rows = specs_from_reference_run(mkey, frames)
        for symbol, frame in sorted(frames.items()):
            prepared = prepare_frame(frame)
            if use_reference:
                specs = ref_specs_map.get(symbol, [])
            else:
                events = detector(frame, symbol)
                specs, _f_rr, _f_nt = entry_specs_from_events(
                    frame, events, symbol,
                    module=mcfg["module"],
                    entry_variant=mcfg["entry_variant"],
                    rr_min=None,
                    pivots=confirmed_pivots(frame),
                )
                if mcfg["volume_filter"] == "shrink":
                    specs, _dropped = filter_specs_by_shrink(frame, specs)
                if mcfg["bias_filter"] is not None:
                    specs, _dropped = filter_specs_by_bias(
                        frame, specs, bias_max=mcfg["bias_filter"]
                    )
            for spec in specs:
                engine_trade = simulate_trade(
                    frame, spec, exit_variant=EXIT_COSTBASIS, fee=fee,
                    prepared=prepared, limit_guard=True,
                )
                cells["baseline"].append(engine_trade)
                replica = simulate_with_stop(
                    frame, spec, fee=fee, prepared=prepared, limit_guard=True,
                )
                if (
                    replica.exit_date != engine_trade.exit_date
                    or replica.exit_price != engine_trade.exit_price
                    or replica.exit_reason != engine_trade.exit_reason
                    or replica.r_net != engine_trade.r_net
                ):
                    equivalence_mismatches += 1
                for kind, param in STOP_CANDIDATES:
                    cells[f"{kind}_{param}"].append(simulate_with_stop(
                        frame, spec, fee=fee, prepared=prepared, limit_guard=True,
                        stop_kind=kind, stop_param=param,
                    ))
    if use_reference:
        anchor_mismatches = 0
        if len(cells["baseline"]) != len(ref_rows):
            anchor_mismatches = abs(len(cells["baseline"]) - len(ref_rows))
        for trade, row in zip(cells["baseline"], ref_rows):
            if (
                (trade.exit_date.isoformat() if trade.exit_date else None)
                != row["exit_date"]
                or trade.exit_reason != row["exit_reason"]
                or (trade.r_net is None) != (row["r_net"] is None)
                or (
                    trade.r_net is not None
                    and row["r_net"] is not None
                    and abs(trade.r_net - row["r_net"]) > 1e-9
                )
            ):
                anchor_mismatches += 1
    return {
        "cells": cells,
        "equivalence_mismatches": equivalence_mismatches,
        "anchor_mismatches": anchor_mismatches,
        "specs_source": "reference_run" if use_reference else "detector",
    }


def metrics_of(trades: list[Trade]) -> dict:
    m = compute_metrics(trades, label="all", net=True)
    d = asdict(m)
    d.pop("label", None)
    return d


def paired_bootstrap_delta(
    base_vals: np.ndarray, var_vals: np.ndarray
) -> tuple[float, float]:
    rng = np.random.RandomState(BOOT_SEED)
    n = len(base_vals)
    deltas = np.empty(BOOT_N)
    for b in range(BOOT_N):
        idx = rng.randint(0, n, n)
        deltas[b] = var_vals[idx].mean() - base_vals[idx].mean()
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return float(lo), float(hi)


def exit_reason_counts(trades: list[Trade]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in trades:
        if t.is_open or t.exit_reason in (
            "invalid_nonpositive_risk", "skipped_limit_up_at_entry"
        ):
            continue
        key = t.exit_reason.split("(")[0]
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def analyze_module(mkey: str, bundle: dict) -> dict:
    cells: dict[str, list[Trade]] = bundle["cells"]
    base_m = metrics_of(cells["baseline"])
    base_closed_idx = [
        i for i, t in enumerate(cells["baseline"])
        if not t.is_open
        and t.exit_reason not in ("invalid_nonpositive_risk",
                                  "skipped_limit_up_at_entry")
    ]
    base_vals = np.array(
        [cells["baseline"][i].r_net or 0.0 for i in base_closed_idx]
    )

    rows = []
    for cell_key in [f"{k}_{p}" for k, p in STOP_CANDIDATES]:
        trades = cells[cell_key]
        m = metrics_of(trades)
        paired_base = []
        paired_var = []
        for i in base_closed_idx:
            t = trades[i]
            assert t is not None
            paired_base.append(cells["baseline"][i].r_net or 0.0)
            paired_var.append(
                (t.r_net or 0.0)
                if (not t.is_open and t.exit_reason not in (
                    "invalid_nonpositive_risk", "skipped_limit_up_at_entry"))
                else 0.0
            )
        lo, hi = paired_bootstrap_delta(
            np.array(paired_base), np.array(paired_var)
        )
        d_expR = (m["expectancy_r"] or 0.0) - (base_m["expectancy_r"] or 0.0)
        d_pf = (m["profit_factor"] or 0.0) - (base_m["profit_factor"] or 0.0)
        kind, param = cell_key.rsplit("_", 1)
        rows.append({
            "module": mkey, "stop_kind": kind,
            "stop_param": float(param) if kind in ("atr", "trail") else int(param),
            **m,
            "delta_expR": d_expR, "delta_pf": d_pf,
            "boot_ci_lo": lo, "boot_ci_hi": hi,
            "significant": lo > 0,
            "noninferior": d_expR >= -0.10 and d_pf >= -0.10,
            "exit_reasons": exit_reason_counts(trades),
        })

    # 判定标准第 7 条：右尾长持单（41+ 天）与时间止损代价。
    base_trades = cells["baseline"]
    closed = [t for t in base_trades if not t.is_open and t.exit_reason not in
              ("invalid_nonpositive_risk", "skipped_limit_up_at_entry")]
    total_r = sum(t.r_net or 0.0 for t in closed)
    long_holds = [t for t in closed if t.holding_bars >= 41]
    long_r = sum(t.r_net or 0.0 for t in long_holds)
    time_costs = {}
    for kind, param in STOP_CANDIDATES:
        if kind != "time":
            continue
        trades = cells[f"{kind}_{param}"]
        cut_long, cut_long_dr = 0, 0.0
        cut_all, cut_all_dr = 0, 0.0
        for i, bt in enumerate(base_closed_idx):
            base_t = cells["baseline"][bt]
            var_t = trades[bt]
            base_exit = base_t.exit_date
            var_exit = var_t.exit_date
            cut = (
                var_exit is not None and base_exit is not None
                and var_exit < base_exit
                and str(var_t.exit_reason or "").startswith("stop_time")
            )
            if not cut:
                continue
            dr = (var_t.r_net or 0.0) - (base_t.r_net or 0.0)
            cut_all += 1
            cut_all_dr += dr
            if base_t.holding_bars >= 41:
                cut_long += 1
                cut_long_dr += dr
        time_costs[f"N{param}"] = {
            "cut_trades_total": cut_all, "cut_deltaR_total": cut_all_dr,
            "cut_41d_trades": cut_long, "cut_41d_deltaR": cut_long_dr,
        }
    right_tail = {
        "closed_trades": len(closed), "total_r": total_r,
        "hold_41d_count": len(long_holds), "hold_41d_r": long_r,
        "hold_41d_share_of_total_r": (long_r / total_r) if total_r else None,
        "time_stop_cost": time_costs,
    }
    return {
        "baseline": {"module": mkey, **base_m,
                     "exit_reasons": exit_reason_counts(base_trades)},
        "cells": rows,
        "right_tail": right_tail,
        "equivalence_mismatches": bundle["equivalence_mismatches"],
        "anchor_mismatches": bundle["anchor_mismatches"],
        "specs_source": bundle["specs_source"],
    }


def classify_verdicts(results: dict) -> dict:
    """判定标准第 4/5/6 条的机械归档（不掺入事后判断）。"""
    verdicts = {}
    kinds = ("atr", "time", "trail")
    for kind in kinds:
        kind_cells = [c for mod in results["modules"].values()
                      for c in mod["cells"] if c["stop_kind"] == kind]
        universal_points = []
        module_specific = []
        for param in sorted({c["stop_param"] for c in kind_cells}):
            pts = [c for c in kind_cells if c["stop_param"] == param]
            n_noninf = sum(1 for c in pts if c["noninferior"])
            n_sig = sum(1 for c in pts if c["significant"])
            entry = {"param": param, "noninferior_modules": n_noninf,
                     "significant_modules": n_sig,
                     "modules": {c["module"]: {
                         "delta_expR": c["delta_expR"],
                         "sig": c["significant"], "noninf": c["noninferior"],
                     } for c in pts}}
            if n_noninf >= 3 and n_sig >= 1:
                universal_points.append(entry)
        for c in kind_cells:
            if c["significant"]:
                module_specific.append({
                    "module": c["module"], "param": c["stop_param"],
                    "delta_expR": c["delta_expR"],
                })
        if universal_points:
            verdicts[kind] = "跨模块普适候选", universal_points
        elif module_specific:
            verdicts[kind] = "模块特定候选（未达普适）", module_specific
        else:
            verdicts[kind] = "证伪", []
    return {k: {"verdict": v[0], "detail": v[1]} for k, v in verdicts.items()}


def main() -> None:
    frames_full = load_pool_frames()
    frames = {s: f.loc[:DATA_CUTOFF] for s, f in frames_full.items()}
    print(f"池载入 {len(frames)} 标的（截至 {DATA_CUTOFF}）", flush=True)

    results: dict = {
        "data_cutoff": DATA_CUTOFF,
        "symbols_count": len(frames),
        "reference": REFERENCE,
        "pre_revert_overlay": _OVERLAY_INFO,
        "modules": {},
    }
    for mkey in MODULE_CONFIGS:
        print(f"[{mkey}] 收集 specs + 模拟 10 格 ...", flush=True)
        bundle = collect_module(mkey, frames)
        results["modules"][mkey] = analyze_module(mkey, bundle)
        bm = results["modules"][mkey]["baseline"]
        print(f"[{mkey}] 基准 n={bm['trade_count']} "
              f"expR={bm['expectancy_r']:.4f} pf={bm['profit_factor']:.4f} "
              f"失配={results['modules'][mkey]['equivalence_mismatches']}",
              flush=True)

    # 判定标准第 1 条：基准对照（A/B/C）= 指标一致 + 反构 specs 逐笔锚定
    # 零失配（exit_date/exit_reason/r_net 全对上 08-31 归档 run）。
    ref_check = {}
    for mkey, ref in REFERENCE.items():
        bm = results["modules"][mkey]["baseline"]
        ok = (
            bm["trade_count"] == ref["trades"]
            and abs((bm["expectancy_r"] or 0) - ref["expR"]) < 0.005
            and abs((bm["profit_factor"] or 0) - ref["pf"]) < 0.01
            and results["modules"][mkey]["anchor_mismatches"] == 0
        )
        ref_check[mkey] = {
            "pass": ok,
            "ours": {"trades": bm["trade_count"],
                     "expR": bm["expectancy_r"], "pf": bm["profit_factor"]},
            "anchor_mismatches": results["modules"][mkey]["anchor_mismatches"],
            "specs_source": results["modules"][mkey]["specs_source"],
        }
    results["reference_check"] = ref_check
    mism = {m: results["modules"][m]["equivalence_mismatches"]
            for m in MODULE_CONFIGS}
    results["equivalence_check"] = mism
    results["valid"] = (
        all(v["pass"] for v in ref_check.values())
        and all(v == 0 for v in mism.values())
    )
    results["verdicts"] = classify_verdicts(results)

    out_dir = (Path(__file__).resolve().parents[1]
               / "docs/experiments/raw/stop_loss_matrix")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "stop_loss_matrix_results.json"
    out_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print("落盘:", out_path, flush=True)

    if "--dump-hash" in sys.argv:
        payload = json.dumps(
            {k: v for k, v in results.items() if k != "valid"},
            sort_keys=True,
        ).encode()
        print("HASH", hashlib.md5(payload).hexdigest())

    print("\nvalid =", results["valid"])
    for kind, v in results["verdicts"].items():
        print(f"{kind}: {v['verdict']}")


if __name__ == "__main__":
    main()
