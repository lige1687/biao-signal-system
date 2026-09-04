"""周复盘聚合 + 复盘端点叙事降级。"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.routes import copilot as copilot_routes
from lei_signal.copilot import review, trades
from lei_signal.portfolio.funddata import NavPoint
from lei_signal.storage.sqlite_store import connect


def _nav(*p):
    return lambda code, page_size=40: [NavPoint(date=d, unit_nav=v) for d, v in p]


@pytest.fixture()
def seeded(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    trades.create_trade(c, fund_code="012414", fund_name="T",
                        side="buy", amount=10000.0, trade_date="2026-08-31")
    trades.create_trade(c, fund_code="012414", fund_name="T",
                        side="sell", amount=5000.0, trade_date="2026-09-02")
    trades.price_pending_trades(c, fetch_nav=_nav(
        ("2026-09-02", 1.50), ("2026-08-31", 1.00)))
    c.commit()  # 释放写锁：端点测试会用另一个连接写同一库
    yield c
    c.close()


def test_weekly_groups_trades_in_iso_week(seeded):
    # 2026-09-02 属 ISO 周 2026-W36（2026-08-31 周一起）
    card = review.build_weekly_review(seeded, "2026-W36")
    joined = "\n".join(line for s in card.sections for line in s.lines)
    assert "2 笔" in joined
    # 买10000@1.0=10000份；卖5000@1.5=3333.33份；实现=5000-3333.33*1.0=1666.67
    assert card.realized_pnl == pytest.approx(5000.0 - 5000.0 / 1.5)


def test_weekly_empty_week_is_honest(seeded):
    card = review.build_weekly_review(seeded, "2026-W01")
    joined = "\n".join(line for s in card.sections for line in s.lines)
    assert "本周没有台账成交" in joined


def test_review_endpoint_template_without_llm(seeded, monkeypatch):
    for name in ("GLM_API_KEY", "DEEPSEEK_API_KEY", "ARK_API_KEY",
                 "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    # 双保险：直接断掉 LLM 配置，任何环境下都不允许测试触网
    monkeypatch.setattr(
        copilot_routes.plans_llm, "load_ark_config", lambda: None
    )
    db = seeded  # 复用同一连接背后的库文件路径
    db_path = db.execute("PRAGMA database_list").fetchone()[2]
    a = FastAPI()
    a.state.analysis_service = None
    a.state.plans_db_path = db_path
    a.state.watchlist_db_path = db_path
    a.include_router(copilot_routes.router)
    r = TestClient(a).get("/api/copilot/review/weekly")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "weekly" and body["grounded"] is False
