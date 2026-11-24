"""双入口护栏共享样本（J1/S2，2026-09-19 冻结）。

供「CLI 日扫入口 vs API 扫描入口」一致性护栏与 signal_scan unavailable 验收
共用的冻结样本与注入桩。纪律沿用同目录 test_golden_entry_engines.py：
- 样本预期结果由规则账本 + 实际编排路径**独立核对**后录为冻结值
  （核对记录见各样本 docstring 与 docs/archive/handoffs-plans/
  2026-09-19-arch-j1s2-difference-record.md），不把引擎输出直接当预期；
- 与 S1 golden 的关系：A 系样本**直接 import** S1 的样本构造函数
  （_a_uptrend_frame），不复制不改动；候选样本因 S1 的 B 样本带手工
  指标列（analyze_bars 只收原始 OHLCV，会自行重算指标），无法直传，
  故按 B 样本「横盘密集 + 尾部演化」的同一构造思想给出原始 OHLCV 版，
  判定链路在 docstring 中逐条成文。
- 数据不足样本走生产门槛：analyze_bars 的 MIN_BARS=21 检查自己抛
  DataUnavailableError，测试不自制错误文案。
"""
from __future__ import annotations

import threading

import pandas as pd

from lei_signal.compose.pipeline import AnalysisResult, analyze_bars
from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import validate_bars
from tests.golden.test_golden_entry_engines import _a_uptrend_frame

#: 样本标的（纯测试代码，不落真实自选；走 A 股口径使服务层日历逻辑为生产路径）
SYMBOL_CANDIDATE = "600011.SS"  # 有近期候选 -> verdict=waiting
SYMBOL_NO_SIGNAL = "600012.SS"  # 数据完整、行情不触发 -> verdict=none -> 扫描被过滤
SYMBOL_SHORT_HISTORY = "600013.SS"  # 引擎层数据不足(31根) -> 无候选 -> 扫描被过滤
SYMBOL_UNAVAILABLE = "600014.SS"  # 行情不可用(10根<21) -> 显式错误/unavailable 行

#: CLI/API 两入口共同扫的标的序（即子进程与 HTTP 两侧同一组冻结样本）
ALL_SYMBOLS = [
    SYMBOL_CANDIDATE,
    SYMBOL_NO_SIGNAL,
    SYMBOL_SHORT_HISTORY,
    SYMBOL_UNAVAILABLE,
]

# 2026-09-19 经真实管线（validate_bars -> analyze_bars -> build_review）
# 独立核对后冻结的共同判定字段。核对锚点：
# - SYMBOL_CANDIDATE：最后一根触发 D 空头镜像 watch（trigger=最后一根，
#   recency 窗口内），tradability 通过 -> verdict=waiting；
#   dense_breakout/alignment 的 trigger 都在 recency 窗口外 -> 只进
#   historical_structures，不进 candidates；
# - SYMBOL_NO_SIGNAL / SYMBOL_SHORT_HISTORY：无近期候选 -> verdict=none，
#   被 only_with_candidates=True 过滤（两入口同语义）；
# - SYMBOL_UNAVAILABLE：analyze_bars 抛「只有 10 根日K线，至少需要 21 根」。
EXPECTED_CANDIDATE = {
    "verdict": "waiting",
    "best_scenario_cn": "假突破做空镜像",
    "best_state": "watch",
    "reward_risk_ratio": None,
    "reward_risk_computable": False,
    "blocking_reasons": [],
    "has_active_plan": False,
    "error": None,
}


# ---------------------------------------------------------------------------
# 冻结样本帧构造
# ---------------------------------------------------------------------------


def _waiting_candidate_frame() -> pd.DataFrame:
    """候选样本：400 根横盘 -> 60 根稳定上行 -> 3 根 2%/日加速（原始 OHLCV）。

    判定依据（2026-09-19 实际管线核对，rules.v2.yaml false_breakout_reclaim
    镜像规则 / 规格 §9 D 的空头镜像口径）：
    - 横盘段六线恒 100，密集区寿命、带宽、三类时钟真实成立（与 S1 B 样本
      同思想）；上行段使 SMA 双组多头排列成立（2021-07-15 bullish_start）；
    - 尾部 3 根加速使最后一根收盘向上穿越「此前 20 根最高 high x 1.01」且
      前收未达 -> D 空头镜像的突破观察在**最后一根**（2021-10-11）成立，
      trigger_date 落在 recency（3 交易日）窗口内 -> 近期候选，
      state=watch（加速段直接远离参考位，未满足收回/破坏的后续子态）；
    - dense_breakout（watch 在横盘中段）与 alignment（bullish_start 在
      上行中段）的 trigger 均远于 3 个交易日 -> 只进 historical，不进候选；
    - tradability 门禁通过（趋势类型可判、九条无交易条件无阻断）。
    """
    closes = [100.0] * 400 + [100.0 + (k + 1) * 0.5 for k in range(60)]
    for _ in range(3):
        closes.append(closes[-1] * 1.02)
    n = len(closes)
    index = pd.bdate_range("2020-01-02", periods=n)
    close = pd.Series(closes, index=index)
    return pd.DataFrame(
        {"open": close * 0.999, "high": close * 1.003, "low": close * 0.997,
         "close": close, "volume": pd.Series([1e6] * n, index=index)},
        index=index,
    )


def _frame_for(symbol: str) -> pd.DataFrame:
    """symbol -> 冻结样本帧（无信号/引擎数据不足两样本直接复用 S1 构造函数）。"""
    if symbol == SYMBOL_CANDIDATE:
        return _waiting_candidate_frame()
    if symbol == SYMBOL_NO_SIGNAL:
        # S1 golden A「正常无信号」样本：紧口径健康上行，永不触碰回撤带
        return _a_uptrend_frame(tight=True, dip_len=0, recover_len=0)
    if symbol == SYMBOL_SHORT_HISTORY:
        # S1 golden A「数据不足」样本：31 根，指标未就绪 -> 引擎层零事件
        return _a_uptrend_frame(pre_bars=31, dip_len=0, recover_len=0)
    if symbol == SYMBOL_UNAVAILABLE:
        # 行情不可用：10 根 < analyze_bars 的 MIN_BARS=21 生产门槛
        return _a_uptrend_frame(pre_bars=10, dip_len=0, recover_len=0)
    raise KeyError(f"未知测试样本标的: {symbol}")


# ---------------------------------------------------------------------------
# analyze 替身（两条入口共用同一组样本与同一份结果缓存）
# ---------------------------------------------------------------------------

_LOCK = threading.Lock()
_CACHE: dict[str, AnalysisResult] = {}


def stub_analyze(symbol: str, **_kwargs) -> AnalysisResult:
    """与 compose.pipeline.analyze 同签名的离线替身。

    只替换「抓行情」这一步（改喂冻结样本帧），特征/规则/结构/状态机/
    候选汇总全部走生产管线（analyze_bars）。SYMBOL_UNAVAILABLE 由
    analyze_bars 自己的 MIN_BARS 门槛抛 DataUnavailableError。
    """
    with _LOCK:
        cached = _CACHE.get(symbol)
    if cached is not None:
        return cached
    bars = _frame_for(symbol)
    frame, report = validate_bars(bars, symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    result = analyze_bars(symbol, frame, price_data=PriceData(
        symbol=info.symbol, display_name=info.symbol, bars=frame,
        report=report, info=info,
    ))
    with _LOCK:
        _CACHE.setdefault(symbol, result)
        return _CACHE[symbol]


def install_daily_scan_stub() -> None:
    """把替身装进 services 模块名下，使随后构造的 AnalysisService 采用它。

    scripts/daily_scan.py 的 main() 内部自行 ``AnalysisService(max_workers=8)``，
    构造时按模块全局名解析 analyze；在 runpy 执行 daily_scan 之前替换
    ``lei_signal.api.services.analyze`` 即可让真实 CLI 编排吃离线样本。
    """
    import lei_signal.api.services as services  # noqa: PLC0415

    services.analyze = stub_analyze


def render_cli_runner_script(
    repo_root: str, daily_scan_path: str, cli_args: list[str]
) -> str:
    """生成子进程执行器脚本（写入 tmp_path 运行，不入库）。

    子进程内先装替身再 runpy 执行 daily_scan，使其 main() 的全部真实编排
    （argparse -> 自选解析 -> AnalysisService 构造 -> 串行预热 -> 扫描 ->
    落库计数 -> 汇总打印 -> os._exit）原样走一遍。
    """
    return (
        '"""J1/S2 双入口护栏：daily_scan.py 真实编排路径的子进程执行器（临时产物）。"""\n'
        "import sys\n"
        f"sys.path.insert(0, {repo_root!r})\n"
        "from tests.golden.scan_entry_samples import install_daily_scan_stub\n"
        "install_daily_scan_stub()\n"
        f"sys.argv = ['daily_scan.py'] + {cli_args!r}\n"
        "import runpy\n"
        f"runpy.run_path({daily_scan_path!r}, run_name='__main__')\n"
    )
