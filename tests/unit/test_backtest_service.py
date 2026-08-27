"""回测工作台后端测试（service + API 路由）。"""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from lei_signal.backtest import service as svc
from lei_signal.backtest.engine import ENTRY_EARLY, EXIT_COSTBASIS
from lei_signal.backtest.service import BacktestParams


def _geo_frame(shift: float = 0.0) -> pd.DataFrame:
    from lei_signal.features.indicators import compute_features
    from lei_signal.rules.lei_color import classify_colors

    closes = [100.0 * 1.0012**i for i in range(640)]
    base = closes[-1]
    for k in range(8):
        closes.append(base * 1.0012 ** (k + 1) * (1 - 0.05 * (k + 1) / 8))
    closes.append(closes[-1] * 1.006)
    for _ in range(3):
        closes.append(closes[-1] * 1.004)
    close = pd.Series(closes, index=pd.bdate_range("2014-01-01", periods=len(closes)))
    close = close * (1.0 + shift)
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


@pytest.fixture()
def tiny_pool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    frames = {"AAA": _geo_frame(), "BBB": _geo_frame(0.01)}
    monkeypatch.setattr(svc, "_cached_frames", lambda: frames)
    monkeypatch.setattr(svc, "BACKTEST_RUNS_DIR", tmp_path / "runs")
    svc._EVENT_CACHE.clear()
    svc._PIVOT_CACHE.clear()
    svc._GAP_CACHE.clear()
    svc._PROFILE_CACHE.clear()


def test_execute_run_full_chain(tiny_pool: None) -> None:
    params = BacktestParams(rr_min=None, fee_label="none")
    result = svc.execute_run(params)
    assert result["status"] == "done"
    assert result["data_range"]["symbols_count"] == 2
    assert result["funnel"]["touched"] > 0
    overview = result["groups"]["True"]["总览"][0]
    assert overview["trade_count"] > 0
    assert result["trades"], "应产出逐笔明细"
    trade = result["trades"][0]
    for key in (
        "symbol", "signal_date", "entry_date", "entry_price", "stop_price",
        "exit_date", "exit_price", "r_net", "exit_reason",
    ):
        assert key in trade
    # 买卖点日期次序合法
    assert trade["entry_date"] >= trade["signal_date"]
    if trade["exit_date"]:
        assert trade["exit_date"] > trade["entry_date"]


def test_execute_run_symbol_filter(tiny_pool: None) -> None:
    result = svc.execute_run(BacktestParams(symbols=("AAA",), rr_min=None))
    assert result["data_range"]["symbols_count"] == 1
    assert {t["symbol"] for t in result["trades"]} <= {"AAA"}


def test_execute_run_rejects_unknown_symbol(tiny_pool: None) -> None:
    with pytest.raises(ValueError, match="不在回测池"):
        svc.execute_run(BacktestParams(symbols=("NOPE",)))


def test_default_params_filters_off_reproduce_baseline(tiny_pool: None) -> None:
    """默认全关：与不加新字段的既有结论可复现（纪律：过滤器默认关）。"""
    result = svc.execute_run(BacktestParams(rr_min=None, fee_label="none"))
    assert result["funnel"]["filtered_by_volume"] == 0
    assert result["funnel"]["filtered_by_profile"] == 0
    assert result["funnel"]["filtered_by_gap"] == 0
    # trade 明细带 trend_stage（供 §16 分组）
    assert all("trend_stage" in t for t in result["trades"])


def test_execute_run_volume_confirm_changes_trades(tiny_pool: None) -> None:
    """量能确认开启后：要么过滤掉部分信号，要么全部通过（不允许报错）。"""
    base = svc.execute_run(BacktestParams(rr_min=None, fee_label="none"))
    confirm = svc.execute_run(
        BacktestParams(
            rr_min=None,
            fee_label="none",
            volume_confirm=True,
            volume_confirm_window=1,
        )
    )
    assert confirm["funnel"]["filtered_by_volume"] >= 0
    assert len(confirm["trades"]) <= len(base["trades"])


def test_execute_run_trend_stage_group_present(tiny_pool: None) -> None:
    result = svc.execute_run(BacktestParams(rr_min=None, fee_label="none"))
    groups = result["groups"]["True"]
    assert "趋势五步（入场时 stage）" in groups
    stages = [t["trend_stage"] for t in result["trades"]]
    assert all(0 <= s <= 5 for s in stages)


def test_params_validation_new_filters() -> None:
    with pytest.raises(ValueError, match="volume_confirm_window"):
        BacktestParams(volume_confirm_window=0).validate()
    with pytest.raises(ValueError, match="筹码过滤档"):
        BacktestParams(profile_filter="bogus").validate()
    with pytest.raises(ValueError, match="gap_momentum_lookback"):
        BacktestParams(gap_momentum_lookback=0).validate()
    with pytest.raises(ValueError, match="量能过滤档"):
        BacktestParams(volume_filter="surge").validate()
    with pytest.raises(ValueError, match="shrink_recent"):
        BacktestParams(shrink_recent=0).validate()
    with pytest.raises(ValueError, match="volume_filter_vr_max"):
        BacktestParams(volume_filter_vr_max=0.0).validate()
    with pytest.raises(ValueError, match="bias_filter"):
        BacktestParams(bias_filter=0.0).validate()
    BacktestParams(
        volume_confirm=True,
        volume_confirm_window=5,
        profile_filter="both",
        gap_target=True,
        gap_momentum=True,
        gap_momentum_lookback=10,
        volume_filter="shrink",
        shrink_recent=3,
        shrink_prior=3,
        volume_filter_vr_max=0.7,
        bias_filter=-0.15,
    ).validate()


def test_execute_run_volume_filter_shrink_changes_trades(tiny_pool: None) -> None:
    """缩量过滤开启：funnel 记录被过滤数，交易数不多于基线；默认关时口径不变。"""
    base = svc.execute_run(BacktestParams(rr_min=None, fee_label="none"))
    assert base["funnel"]["filtered_by_shrink"] == 0
    assert base["params"]["volume_filter"] == "none"
    shrink = svc.execute_run(
        BacktestParams(rr_min=None, fee_label="none", volume_filter="shrink")
    )
    assert shrink["params"]["volume_filter"] == "shrink"
    assert shrink["params"]["shrink_recent"] is None  # None = 账本默认
    assert shrink["funnel"]["filtered_by_shrink"] >= 0
    assert len(shrink["trades"]) <= len(base["trades"])


def test_execute_run_bias_filter_changes_trades(tiny_pool: None) -> None:
    """深乖离过滤开启：funnel 记录被过滤数，交易数不多于基线；默认关时口径不变。"""
    base = svc.execute_run(BacktestParams(rr_min=None, fee_label="none"))
    assert base["funnel"]["filtered_by_bias"] == 0
    assert base["params"]["bias_filter"] is None
    deep = svc.execute_run(
        BacktestParams(rr_min=None, fee_label="none", bias_filter=-0.15)
    )
    assert deep["params"]["bias_filter"] == -0.15
    assert deep["funnel"]["filtered_by_bias"] >= 0
    assert len(deep["trades"]) <= len(base["trades"])


def test_start_run_persists_result(tiny_pool: None) -> None:
    run_id = svc.start_run(BacktestParams(rr_min=None))
    for _ in range(600):
        status = svc.run_status(run_id)
        if status and status["status"] != "running":
            break
        import time

        time.sleep(0.05)
    assert status is not None and status["status"] == "done", status
    loaded = svc.load_run(run_id)
    assert loaded is not None and loaded["params"]["rr_min"] is None
    runs = svc.list_runs()
    assert any(r["run_id"] == run_id for r in runs)
    summary = next(r for r in runs if r["run_id"] == run_id)
    assert "expectancy_r" in summary


def test_glossary_has_user_facing_terms() -> None:
    for term in ("rr_min", "win_rate", "expectancy_r", "profit_factor",
                 "max_consecutive_losses", "max_drawdown_1r",
                 "in_sample", "out_of_sample"):
        entry = svc.GLOSSARY[term]
        assert entry["label"] and entry["tip"]


def test_api_routes(tiny_pool: None) -> None:
    from lei_signal.api.app import create_app

    client = TestClient(create_app())
    options = client.get("/api/backtest/options").json()
    assert options["defaults"]["rr_min"] == 3.0
    assert any(o["value"] is None for o in options["rr_levels"])
    assert "glossary" in options and "expectancy_r" in options["glossary"]

    resp = client.post(
        "/api/backtest/runs",
        json={"rr_min": None, "entry_variant": ENTRY_EARLY,
              "exit_variant": EXIT_COSTBASIS, "fee_label": "none"},
    )
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]
    for _ in range(600):
        detail = client.get(f"/api/backtest/runs/{run_id}").json()
        if detail.get("status") != "running":
            break
        import time

        time.sleep(0.05)
    assert detail.get("status") == "done", detail
    assert detail["groups"]["True"]["总览"][0]["trade_count"] > 0

    runs = client.get("/api/backtest/runs").json()
    assert any(r["run_id"] == run_id for r in runs)
    missing = client.get("/api/backtest/runs/does-not-exist")
    assert missing.status_code == 404

    bad = client.post("/api/backtest/runs", json={"entry_variant": "bogus"})
    assert bad.status_code == 422


def test_result_json_serializable(tiny_pool: None) -> None:
    result = svc.execute_run(BacktestParams(rr_min=None))
    text = json.dumps(result, ensure_ascii=False)
    assert len(text) > 1000
    parsed = json.loads(text)
    assert parsed["disclaimer"]


def test_klines_endpoint(tiny_pool: None) -> None:
    from lei_signal.api.app import create_app

    client = TestClient(create_app())
    data = client.get("/api/backtest/klines/AAA").json()
    assert data["symbol"] == "AAA"
    assert len(data["dates"]) == data["count"] > 500
    assert len(data["ohlc"]) == data["count"]
    first = data["ohlc"][0]
    assert len(first) == 4 and first[2] <= first[0] <= first[3]
    missing = client.get("/api/backtest/klines/NOPE")
    assert missing.status_code == 404
