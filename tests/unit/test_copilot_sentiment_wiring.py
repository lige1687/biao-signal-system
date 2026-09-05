"""情绪面接入 truth table（handoff-sentiment §6 验收建议）。"""
from __future__ import annotations

from lei_signal.api.schemas import ScanItemDTO
from lei_signal.copilot.recommend import build_recommendation


def _scan(symbol: str) -> ScanItemDTO:
    return ScanItemDTO(symbol=symbol, verdict="waiting", verdict_cn="等待")


def test_unavailable_does_not_block_and_marks_accumulating():
    card = build_recommendation(
        [_scan("515880")], run_date="2026-09-05",
        sentiment_index={}, sentiment_available=False,
    )
    assert len(card.items) == 1                      # 不阻塞推荐
    assert card.items[0].sentiment_cn is None        # 未覆盖/无数据 → None
    assert "累积" in card.sentiment_status or "20" in card.sentiment_status


def test_covered_symbol_gets_annotation_without_score_change():
    idx = {"515880": {"name": "通信设备", "state_cn": "偏热", "heat_pctile": 80}}
    base = build_recommendation([_scan("515880")], run_date="2026-09-05")
    with_s = build_recommendation(
        [_scan("515880")], run_date="2026-09-05",
        sentiment_index=idx, sentiment_available=True,
    )
    assert with_s.items[0].sentiment_cn is not None  # 标注出现
    assert "通信设备" in with_s.items[0].sentiment_cn
    # 红线：只标注，评分不许变
    assert with_s.items[0].score == base.items[0].score
    assert with_s.sentiment_status == "已接入（只标注不评分）"


def test_uncovered_symbol_returns_none():
    idx = {"600519": {"name": "白酒", "state_cn": "冰点", "heat_pctile": 5}}
    card = build_recommendation(
        [_scan("515880")], run_date="2026-09-05",
        sentiment_index=idx, sentiment_available=True,
    )
    assert card.items[0].sentiment_cn is None
