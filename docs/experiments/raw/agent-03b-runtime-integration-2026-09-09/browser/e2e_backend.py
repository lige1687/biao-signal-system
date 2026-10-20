"""03B 合并树浏览器验收后端（隔离库、显式行情、本地固定短解释）。

控制输入 target_b_price=120 只用于验证字段传递，不是真实系统建议或交易建议。
所有生产模块必须从本脚本所在的 integration stage 导入。
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))
TMP = Path(tempfile.mkdtemp(prefix="lei-03b-stage-browser-")).resolve()
SYMBOL = "000001.SS"


def _frame(n: int = 400) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-02", periods=n)
    rng = np.random.default_rng(23)
    close = 100 + np.cumsum(rng.normal(0.15, 1.2, n))
    return pd.DataFrame({"open": np.r_[close[0], close[:-1]], "high": close + 2,
                         "low": close - 2, "close": close, "volume": 1e6}, index=idx)


def build_app():
    from unittest.mock import patch
    from fastapi import FastAPI
    from lei_signal.api import config as api_config
    from lei_signal.api.routes import agent, backtest, copilot, opportunities, plans
    from lei_signal.api.schemas import SuggestedPlanDTO
    from lei_signal.backtest import service as bt_service
    from lei_signal.compose.pipeline import analyze_bars
    from lei_signal.copilot import backtest_requests as br
    from lei_signal.plans import llm

    fixture_path = ROOT / "tests/000001.SS.bars.parquet"
    frame = pd.read_parquet(fixture_path) if fixture_path.exists() else _frame()
    frames = {SYMBOL: frame}
    db = str(TMP / "lab.db")
    runs_dir = TMP / "backtest_runs"
    result = analyze_bars(SYMBOL, frame.copy())

    class Entry:
        error = "fixture absent"
        def __init__(self, value): self.result = value

    class Service:
        def get(self, symbol, *args, **kwargs): return Entry(result if symbol == SYMBOL else None)

    short = "（本地固定短解释）计划字段以服务端产物为准。"
    cfg = llm.ArkConfig(api_key="browser-only", base_url="https://127.0.0.1:9", model="fixed")
    patches = [
        patch.object(Path, "home", return_value=TMP),
        patch.object(api_config, "sqlite_path", return_value=db),
        patch.object(bt_service, "BACKTEST_RUNS_DIR", runs_dir),
        patch.object(br, "_TEST_SOURCE_FRAMES", frames),
        patch.object(llm, "load_ark_config", return_value=cfg),
        patch.object(llm, "chat_discussion", side_effect=lambda *a, **k: short),
        patch.object(llm, "chat_discussion_stream", side_effect=lambda *a, **k: iter(short)),
    ]
    for item in patches: item.start()

    real_review = opportunities.buy_point_review
    def controlled_review(request, symbol):
        review = real_review(request, symbol)
        suggested = SuggestedPlanDTO(
            symbol=symbol, module="A", direction="long", entry_rule_id="a_pullback",
            entry_trigger_cn="控制输入：已知系统建议，仅验证字段传递",
            invalidation_price=90, target_b_price=120,
            target_b_source="controller_fixture")
        return review.model_copy(update={"suggested_plan": suggested})
    opportunities.buy_point_review = controlled_review

    from lei_signal.storage.sqlite_store import connect
    conn = connect(db); conn.close()
    app = FastAPI()
    app.state.plans_db_path = db
    app.state.watchlist_db_path = db
    app.state.analysis_service = Service()
    for router in (copilot.router, agent.router, plans.router, backtest.router):
        app.include_router(router)
    app.state.browser_fixture = {"target_b_price": 120, "real_advice": False,
                                 "sqlite_path": db, "import_root": str(ROOT)}
    return app


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--port-file", required=True)
    args = parser.parse_args(); app = build_app()
    import uvicorn
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
    Path(args.port_file).write_text(str(port), encoding="utf-8")
    print(json.dumps({"port": port, "tmp": str(TMP), "import_root": str(ROOT)}, ensure_ascii=False), flush=True)
    uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")).run()


if __name__ == "__main__": main()
