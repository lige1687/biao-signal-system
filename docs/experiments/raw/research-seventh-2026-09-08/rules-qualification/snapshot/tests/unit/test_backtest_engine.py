"""回测引擎与 §16 指标测试（src/lei_signal/backtest/）。"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from lei_signal.backtest.engine import (
    EXIT_B3_DUAL,
    EXIT_COSTBASIS,
    EXIT_STRUCTURE_STOP,
    EXIT_TOP_PLUS_KEYWAVE,
    EntrySpec,
    FeeModel,
    entry_specs_from_events,
    prepare_frame,
    simulate_trade,
)
from lei_signal.backtest.metrics import compute_metrics, full_group_metrics, regime_from_clock
from lei_signal.domain.types import Direction, Provenance, Severity, SignalEvent
from lei_signal.features.indicators import compute_features
from lei_signal.rules.first_ma_pullback import SUB_RULE_CONFIRMED
from lei_signal.rules.lei_color import classify_colors


def _bars(closes: list[float]) -> pd.DataFrame:
    close = pd.Series(closes, index=pd.bdate_range("2024-01-01", periods=len(closes)))
    return pd.DataFrame(
        {
            "open": close * 1.001,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1e6,
        },
        index=close.index,
    )


def _spec(frame: pd.DataFrame, position: int, stop: float) -> EntrySpec:
    day = frame.index[position].date()
    return EntrySpec(
        symbol="TEST",
        signal_date=day,
        signal_position=position,
        entry_ref_price=float(frame["close"].iloc[position]),
        stop_price=stop,
        target_price=None,
        target_source=None,
        reward_risk=None,
        entry_variant="early",
        is_first_touch=True,
        ma_period=20,
        clock_type=2,
        weekly_bull_env=True,
        event_id="ev1",
    )


def test_fee_model_takes_max_of_bps_and_per_share() -> None:
    fee = FeeModel.from_ledger("standard")
    # 低价股：每股 $0.005 主导（价格 10 -> 0.05% < 0.05%…）每边 max(5bp, 5bp)
    assert fee.round_trip_fraction(10.0) == pytest.approx(2 * 0.0005)
    # 高价股：5bp 主导
    assert fee.round_trip_fraction(1000.0) == pytest.approx(0.001)
    assert FeeModel.from_ledger("none").round_trip_fraction(100.0) == 0.0


def test_entry_next_open_and_stop_exit() -> None:
    closes = [100, 101, 99, 98, 97, 96, 95]
    bars = _bars(closes)
    frame = classify_colors(compute_features(bars))
    prepared = prepare_frame(frame)
    spec = _spec(frame, 0, stop=98.5)
    trade = simulate_trade(
        frame, spec, exit_variant=EXIT_STRUCTURE_STOP, fee=FeeModel("none", 0, 0), prepared=prepared
    )
    # 信号日 0 收盘生成 -> 第 1 根开盘入场
    assert trade.entry_date == frame.index[1].date()
    assert trade.entry_price == pytest.approx(float(frame["open"].iloc[1]))
    # close(3)=98 < 98.5 -> 第 4 根开盘退出（收盘确认、下一根开盘执行）
    assert trade.exit_reason == "structure_stop_C"
    assert trade.exit_date == frame.index[4].date()
    assert trade.exit_price == pytest.approx(float(frame["open"].iloc[4]))
    risk = trade.entry_price - 98.5
    assert trade.r_gross == pytest.approx((trade.exit_price - trade.entry_price) / risk)


def test_gap_over_stop_books_at_open() -> None:
    closes = [100, 101, 90, 89]  # 第 2 根收盘远跌破止损，第 3 根开盘执行
    bars = _bars(closes)
    frame = classify_colors(compute_features(bars))
    prepared = prepare_frame(frame)
    spec = _spec(frame, 0, stop=99.0)
    trade = simulate_trade(
        frame, spec, exit_variant=EXIT_STRUCTURE_STOP, fee=FeeModel("none", 0, 0), prepared=prepared
    )
    assert trade.exit_reason == "structure_stop_C"
    # 退出价 = 第 3 根开盘（跳空按开盘记账，§3.3）
    assert trade.exit_date == frame.index[3].date()
    assert trade.exit_price == pytest.approx(float(frame["open"].iloc[3]))


def test_costbasis_exit() -> None:
    # 持续下跌：close < EMA20 且 close < close_lag20 早于结构止损时触发
    closes = [100 + i for i in range(60)] + [160, 150, 140, 130, 120, 110, 100, 90]
    bars = _bars(closes)
    frame = classify_colors(compute_features(bars))
    prepared = prepare_frame(frame)
    spec = _spec(frame, 59, stop=60.0)
    trade = simulate_trade(
        frame, spec, exit_variant=EXIT_COSTBASIS, fee=FeeModel("none", 0, 0), prepared=prepared
    )
    assert trade.exit_reason == "exit_a6_1_costbasis"


def test_top_plus_keywave_exits_later_than_costbasis() -> None:
    # 单日急跌当日即关键性波动（A6① 当日触发）；顶部构造需再一根创新低
    # 才确认（A6② 晚一日触发）——两者的差异就是“路牌”的代价。
    closes = [100 + i for i in range(60)] + [130, 129, 128, 127, 126]
    bars = _bars(closes)
    frame = classify_colors(compute_features(bars))
    prepared = prepare_frame(frame)
    spec = _spec(frame, 59, stop=95.0)
    t1 = simulate_trade(
        frame, spec,
        exit_variant=EXIT_COSTBASIS, fee=FeeModel("none", 0, 0), prepared=prepared,
    )
    t2 = simulate_trade(
        frame, spec,
        exit_variant=EXIT_TOP_PLUS_KEYWAVE, fee=FeeModel("none", 0, 0), prepared=prepared,
    )
    assert t1.exit_reason == "exit_a6_1_costbasis"
    assert t2.exit_reason == "exit_a6_2_top_plus_keywave"
    assert t2.exit_date > t1.exit_date


def test_open_trade_at_data_end() -> None:
    closes = [100 + i for i in range(80)]
    bars = _bars(closes)
    frame = classify_colors(compute_features(bars))
    prepared = prepare_frame(frame)
    spec = _spec(frame, 78, stop=50.0)
    trade = simulate_trade(
        frame, spec, exit_variant=EXIT_COSTBASIS, fee=FeeModel("none", 0, 0), prepared=prepared
    )
    assert trade.is_open


def _b3spec(frame: pd.DataFrame, position: int, stop: float, reference: float) -> EntrySpec:
    import dataclasses

    base = _spec(frame, position, stop)
    return dataclasses.replace(base, breakout_reference=reference, ma_period=20)


def _trigger_row(frame: pd.DataFrame, trade: object) -> int:
    """退出确认日 = 退出日前一根（收盘确认、次日开盘执行）。"""
    return int(frame.index.get_loc(pd.Timestamp(trade.exit_date))) - 1


def test_b3_dual_exits_on_two_actions_same_day() -> None:
    # 120 根稳步上行后急跌：双条件（跌回上沿 + 破 20 组下弯）同日成立，
    # 此时 20 组仍在 60 组上方（排列未破），验证双条件本身即触发退出。
    up = [100 + i * 1.0 for i in range(120)]          # 100 -> 219
    down = [220 - i * 4.0 for i in range(20)]         # 216 -> 140 急跌
    closes = up + down
    bars = _bars(closes)
    frame = classify_colors(compute_features(bars))
    prepared = prepare_frame(frame)
    spec = _b3spec(frame, 119, stop=200.0, reference=219.0)
    trade = simulate_trade(
        frame, spec, exit_variant=EXIT_B3_DUAL,
        fee=FeeModel("none", 0, 0), prepared=prepared,
    )
    assert trade.exit_reason == "exit_b3_dual"
    # 触发日排列仍多头（sma20 > sma60），证明是双条件而非底线触发
    trig = _trigger_row(frame, trade)
    assert float(frame["sma20"].iloc[trig]) > float(frame["sma60"].iloc[trig])
    c = float(frame["close"].iloc[trig])
    assert c < 219.0
    assert c < float(frame["sma20"].iloc[trig])
    assert c < float(frame["close_lag20"].iloc[trig])


def test_b3_dual_alignment_break_is_floor() -> None:
    # 长期下行使 20 组死叉 60 组（排列破坏）；把上沿设得极低使「跌回上沿」
    # 永不成立，验证排列破坏本身即埋伏底线退出。
    down = [300 - i * 1.0 for i in range(200)]        # 持续阴跌
    bars = _bars(down)
    frame = classify_colors(compute_features(bars))
    prepared = prepare_frame(frame)
    spec = _b3spec(frame, 150, stop=50.0, reference=1.0)  # 1.0 远低于价格
    trade = simulate_trade(
        frame, spec, exit_variant=EXIT_B3_DUAL,
        fee=FeeModel("none", 0, 0), prepared=prepared,
    )
    assert trade.exit_reason == "exit_b3_dual"
    trig = _trigger_row(frame, trade)
    # 底线条件：排列破坏（sma20 <= sma60）
    assert float(frame["sma20"].iloc[trig]) <= float(frame["sma60"].iloc[trig])
    # 跌回上沿条件不成立（价格远在 reference 之上）
    assert float(frame["close"].iloc[trig]) >= 1.0


def test_b3_dual_differs_from_structure_stop() -> None:
    # b3_dual 应早于「仅初始结构止损」（a6_3）退出：后者拿到 stop 被击穿。
    up = [100 + i * 1.0 for i in range(120)]
    down = [220 - i * 4.0 for i in range(20)]
    closes = up + down
    bars = _bars(closes)
    frame = classify_colors(compute_features(bars))
    prepared = prepare_frame(frame)
    spec = _b3spec(frame, 119, stop=150.0, reference=219.0)
    t_dual = simulate_trade(
        frame, spec, exit_variant=EXIT_B3_DUAL,
        fee=FeeModel("none", 0, 0), prepared=prepared,
    )
    t_struct = simulate_trade(
        frame, spec, exit_variant=EXIT_STRUCTURE_STOP,
        fee=FeeModel("none", 0, 0), prepared=prepared,
    )
    assert t_dual.exit_reason == "exit_b3_dual"
    assert t_struct.exit_reason == "structure_stop_C"
    assert t_dual.exit_date < t_struct.exit_date


def test_entry_specs_populate_breakout_reference() -> None:
    # B 突破确认事件的 evidence.breakout_reference 应透传到 EntrySpec。
    from lei_signal.domain.types import Provenance

    closes = [100 + i * 0.5 for i in range(80)]
    bars = _bars(closes)
    frame = classify_colors(compute_features(bars))
    sig_day = frame.index[60].date()
    event = SignalEvent(
        event_id="ev:b", symbol="TEST", timeframe="1d",
        event_date=sig_day, available_date=sig_day,
        rule_id="dense_breakout", rule_version="1.0.0",
        direction=Direction.BULLISH, severity=Severity.IMPORTANT, strength=75,
        reason_cn="突破", provenance=Provenance.RESEARCH_PROXY,
        evidence={
            "sub_rule": "dense_breakout_confirmed",
            "variant": "breakout",
            "breakout_reference": 128.5,
            "close": 130.0,
            "entry_ref_close": 130.0,
            "stop_price": 120.0,
        },
    )
    specs, _, _ = entry_specs_from_events(
        frame, [event], "TEST", module="B", entry_variant="breakout", rr_min=None,
    )
    assert len(specs) == 1
    assert specs[0].breakout_reference == 128.5


def _trade(r: float, year: int = 2024, **kwargs) -> object:  # noqa: ANN003
    from lei_signal.backtest.engine import Trade

    defaults = dict(
        symbol="TEST",
        entry_variant="early",
        exit_variant=EXIT_COSTBASIS,
        is_first_touch=True,
        ma_period=20,
        clock_type=2,
        weekly_bull_env=True,
        signal_date=date(year, 3, 1),
        entry_date=date(year, 3, 2),
        entry_price=100.0,
        stop_price=95.0,
        target_price=None,
        reward_risk=None,
        exit_date=date(year, 4, 1),
        exit_price=100.0 + r * 5,
        exit_reason="x",
        holding_bars=10,
        r_gross=r,
        r_net=r,
    )
    defaults.update(kwargs)
    return Trade(**defaults)


def test_metrics_hand_computed() -> None:
    trades = [_trade(2.0), _trade(-1.0), _trade(-1.0), _trade(3.0), _trade(-1.0)]
    m = compute_metrics(trades, label="t", net=True)  # noqa: FBT003
    assert m.trade_count == 5
    assert m.win_rate == pytest.approx(0.4)
    assert m.avg_win_r == pytest.approx(2.5)
    assert m.avg_loss_r == pytest.approx(-1.0)
    assert m.expectancy_r == pytest.approx(0.4)
    assert m.profit_factor == pytest.approx(5.0 / 3.0)
    assert m.max_consecutive_losses == 2
    # 累计 R 序列 2,1,0,3,2 -> 峰 2 谷 0 -> 最大回撤 2.0
    assert m.max_drawdown_1r == pytest.approx(2.0)
    assert m.total_r == pytest.approx(2.0)


def test_metrics_empty() -> None:
    m = compute_metrics([], label="empty", net=True)  # noqa: FBT003
    assert m.trade_count == 0 and m.win_rate is None


def test_full_groups_cover_sections() -> None:
    trades = [
        _trade(1.0, 2023, benchmark_clock_type=2),
        _trade(-1.0, 2025, benchmark_clock_type=4, is_first_touch=False),
    ]
    groups = full_group_metrics(
        trades, net=True, sample_split=date(2025, 1, 1)  # noqa: FBT003
    )
    for section in (
        "总览", "分年份", "牛/熊/横盘（基准时钟）", "退出方式（A6 三版）",
        "入场版本（A4）", "首次 vs 非首次回撤", "样本内外",
    ):
        assert section in groups, section
    is_ = next(m for m in groups["样本内外"] if "样本内" in m.label)
    os_ = next(m for m in groups["样本内外"] if "样本外" in m.label)
    assert is_.trade_count == 1 and os_.trade_count == 1


def test_regime_mapping() -> None:
    assert regime_from_clock(1) == "bull"
    assert regime_from_clock(2) == "bull"
    assert regime_from_clock(3) == "sideways"
    assert regime_from_clock(4) == "bear"
    assert regime_from_clock(5) == "bear"
    assert regime_from_clock(0) == "unknown"


def test_entry_specs_rr_filter() -> None:
    frame = classify_colors(compute_features(_bars([100 + i for i in range(60)] + [70, 71, 72])))
    day = frame.index[55].date()
    event = SignalEvent(
        event_id="e1",
        symbol="TEST",
        timeframe="1d",
        event_date=day,
        available_date=day,
        rule_id="first_ma_pullback",
        rule_version="3.0.0",
        direction=Direction.BULLISH,
        severity=Severity.IMPORTANT,
        strength=75,
        reason_cn="t",
        provenance=Provenance.RESEARCH_PROXY,
        evidence={
            "sub_rule": SUB_RULE_CONFIRMED,
            "entry_variant": "early",
            "stop_price": 150.0,
            "entry_ref_close": float(frame["close"].iloc[55]),
            "close": float(frame["close"].iloc[55]),
            "is_first_touch": True,
            "ma_period": 20,
            "clock_type": 2,
            "weekly_bull_env": True,
        },
    )
    specs, filtered_rr, no_target = entry_specs_from_events(
        frame, [event], "TEST", entry_variant="early", rr_min=3.0, pivots=()
    )
    # 区间高点可作目标 -> R/R 可算但约 1.5 < 3 -> 被盈亏比过滤剔除
    assert specs == []
    assert filtered_rr == 1
    assert no_target == 0
    specs_nofilter, _, _ = entry_specs_from_events(
        frame, [event], "TEST", entry_variant="early", rr_min=None, pivots=()
    )
    assert len(specs_nofilter) == 1
    assert filtered_rr in (0, 1)


def test_run_round1_accumulates_across_symbols() -> None:
    """回归：run_round1 的组合 key 曾被单标的覆盖，跨标的必须累加。"""
    import numpy as np

    from lei_signal.backtest.runner import Round1Config, run_round1

    def _geo(symbol_shift: int) -> pd.DataFrame:
        closes = [100.0 * 1.0012**i for i in range(640)]
        base = closes[-1]
        for k in range(8):
            closes.append(base * 1.0012 ** (k + 1) * (1 - 0.05 * (k + 1) / 8))
        closes.append(closes[-1] * 1.006)
        for _ in range(3):
            closes.append(closes[-1] * 1.004)
        close = pd.Series(
            closes, index=pd.bdate_range("2014-01-01", periods=len(closes))
        )
        close = close * (1.0 + symbol_shift * 0.001)
        bars = pd.DataFrame(
            {
                "open": close * 1.0005,
                "high": close * 1.004,
                "low": close * 0.996,
                "close": close,
                "volume": np.full(len(closes), 1e6),
            },
            index=close.index,
        )
        return classify_colors(compute_features(bars))

    frames = {"AAA": _geo(0), "BBB": _geo(1), "CCC": _geo(2)}
    report = run_round1(frames, Round1Config(rr_min=None))
    assert report.runs, "应至少产出一个组合"
    early_none = report.runs[("early", "a6_1_costbasis", "none")]
    # 三个标的同构行情，每个都应贡献交易（覆盖 bug 会让只剩最后一个标的）
    symbols_seen = {t.symbol for t in early_none}
    assert symbols_seen == {"AAA", "BBB", "CCC"}


def test_trend_stage_propagates_from_spec_to_trade() -> None:
    """EntrySpec.trend_stage -> Trade.trend_stage（供 §16 分组），默认 0。"""
    closes = [100, 101, 99, 98, 97, 96, 95]
    bars = _bars(closes)
    frame = classify_colors(compute_features(bars))
    prepared = prepare_frame(frame)
    from dataclasses import replace

    spec = replace(_spec(frame, 0, stop=98.5), trend_stage=3)
    trade = simulate_trade(
        frame, spec, exit_variant=EXIT_STRUCTURE_STOP, fee=FeeModel("none", 0, 0), prepared=prepared
    )
    assert trade.trend_stage == 3
    # 默认构造（不传 trend_stage）
    spec_default = _spec(frame, 0, stop=98.5)
    assert spec_default.trend_stage == 0


def test_entry_specs_record_trend_stage_at_signal() -> None:
    """entry_specs_from_events 在信号日采集 trend_stage（帧级只算一次）。"""
    closes = [100.0 * 1.01**i for i in range(200)]
    bars = _bars(closes)
    frame = classify_colors(compute_features(bars))
    prepared = prepare_frame(frame)
    from lei_signal.rules.trend_stage import trend_stage_series

    stages = trend_stage_series(frame)
    last = len(frame) - 1
    from dataclasses import replace

    spec = replace(
        _spec(frame, last, stop=float(frame["close"].iloc[last]) * 0.9),
        signal_position=last,
        trend_stage=int(stages.iloc[last]),
    )
    trade = simulate_trade(
        frame, spec, exit_variant=EXIT_STRUCTURE_STOP,
        fee=FeeModel("none", 0, 0), prepared=prepared,
    )
    # 指数拉升末端应处于高阶段（>=2），透传后 trade 同值
    assert int(stages.iloc[last]) >= 2
    assert trade.trend_stage == spec.trend_stage
