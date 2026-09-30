"""Agent 因子只读材料模块：全部使用人工快照，零行情与研究计算。"""
from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import unquote

import pytest

from lei_signal.api.experiment_reports import read_report
from lei_signal.copilot import factor_readonly as fr

NOW = datetime.fromisoformat("2026-09-22T16:00:00+08:00")


def _panel(*, as_of: str = "2026-09-20", value: float = 0.125) -> dict:
    return {
        "generated_at": "2026-09-22 15:30:00",  # legacy：刻意无时区
        "data_as_of": as_of,
        "provenance": "research_proxy",
        "factors": {"mom_121": {"label": "12-1动量"}},
        "symbols": [
            {
                "code": "510300.SS",
                "as_of": as_of,
                "mom_121": value,
                "notes": [],
            }
        ],
        "sectors": [],
    }


def _call(message: str, symbol: str | None = "510300", **kwargs) -> dict:
    return fr.build_factor_reply(
        message,
        symbol,
        panel_loader=kwargs.pop("panel_loader", lambda: _panel()),
        now=NOW,
        **kwargs,
    )


@pytest.mark.parametrize(
    "message, expected",
    [
        ("什么是12-1动量？", True),
        ("mixed.momentum.raw@1.0.0怎么定义？", True),
        ("高点位置因子值得研究吗？", True),
        ("510300这只ETF当前动量如何？", True),
        ("trend.distance50@1.0.0怎么定义？", True),
        ("trend.price.above_ma_200@latest", True),
        ("mixed.momentum.raw 是什么", True),
        ("帮我报单", False),
        ("MACD现在怎么看", False),
        ("成交量放大了吗", False),
    ],
)
def test_is_factor_question_is_narrow(message, expected):
    assert fr.is_factor_question(message) is expected


def test_plain_momentum_resolves_exact_full_card_without_loading_panel():
    called = False

    def forbidden_panel():
        nonlocal called
        called = True
        raise AssertionError("定义查询不得读取面板")

    out = _call("普通动量怎么定义？", None, panel_loader=forbidden_panel)

    assert out["status"] == "ok"
    assert out["intent"] == "definition"
    assert out["definition_refs"] == ["mixed.momentum.raw@1.0.0"]
    assert "252" in out["reply"] and "21" in out["reply"]
    assert "第253条" in out["reply"]
    assert "计算核验" in out["reply"] and "不等于" in out["reply"]
    assert called is False
    assert set(out) == {
        "reply", "status", "intent", "symbol", "definition_refs", "sources", "metadata"
    }


def test_explicit_unknown_version_never_falls_back_to_latest():
    out = _call("mixed.momentum.raw@9.9.9怎么定义？", None)
    assert out["status"] == "unsupported"
    assert out["definition_refs"] == ["mixed.momentum.raw@9.9.9"]
    assert "没有找到这个精确版本" in out["reply"]
    assert "1.0.0" not in out["reply"]


def test_rank_evidence_is_limited_to_algorithm_and_not_effectiveness():
    out = _call("完整动量排序已有证据能证明有效吗？", None)
    assert out["status"] == "limited"
    assert out["intent"] == "evidence"
    assert "mixed.momentum.rank@1.0.0" in out["definition_refs"]
    assert "人工数据" in out["reply"]
    assert "不能证明" in out["reply"]
    assert any(
        s["path"].endswith("factor-momentum-rank-reuse-2026-09-22.md")
        for s in out["sources"]
    )


def test_natural_rank_definition_binds_rank_card_not_raw_momentum():
    out = _call("完整动量排序怎么定义？", None)
    assert out["intent"] == "definition"
    assert out["definition_refs"][0] == "mixed.momentum.rank@1.0.0"
    assert "完整有序名单" in out["reply"]


def test_natural_rank_current_readout_is_rejected_without_formal_observation():
    out = _call("510300当前动量排名是多少？", None)
    assert out["status"] == "unavailable"
    assert out["definition_refs"] == ["mixed.momentum.rank@1.0.0"]
    assert "没有绑定" in out["reply"]


def test_natural_momentum_effectiveness_question_checks_all_three_bound_reports():
    out = _call("这个动量因子过去真的有用吗？", None)
    assert out["status"] == "limited"
    assert out["intent"] == "evidence"
    report_sources = [s for s in out["sources"] if s["path"].startswith("docs/experiments/")]
    assert len(report_sources) == 3
    assert all(len(s["sha256"]) == 64 for s in report_sources)
    assert "首批绑定" in out["reply"] and "不能证明" in out["reply"]


@pytest.mark.parametrize(
    "message",
    ["解释动量已有回测结果", "当前这个动量因子有用吗"],
)
def test_explicit_evidence_wording_wins_over_backtest_or_current_words(message):
    out = _call(message, None)
    assert out["intent"] == "evidence"
    assert out["status"] == "limited"


def test_mixed_value_and_evidence_question_asks_for_one_question_at_a_time():
    out = _call("510300当前动量数值是多少，这个因子有用吗？", None)
    assert out["status"] == "needs_clarification"
    assert "读数" in out["reply"] and "效果证据" in out["reply"]


def test_candidate_is_document_only_and_never_sent_to_resolve():
    out = _call("高点位置因子怎么定义？", None)
    assert out["status"] == "proposal_only"
    assert out["definition_refs"] == ["candidate:mixed.high52.proximity@draft-2"]
    assert "候选草案" in out["reply"] and "未登记" in out["reply"]
    assert "此前252个有效收盘" in out["reply"]


def test_candidate_current_readout_refuses_because_candidate_was_not_computed():
    out = _call("510300当前高点位置读数是多少？", None)
    assert out["status"] == "unavailable"
    assert out["intent"] == "current_observation"
    assert "尚未接入可查询的计算结果" in out["reply"]


def test_new_experiment_request_returns_text_proposal_only():
    out = _call("给高点位置和12-1动量设计一个新实验", None)
    assert out["status"] == "proposal_only"
    assert out["intent"] == "experiment_proposal"
    assert "文本提案" in out["reply"]
    assert "不会创建任务" in out["reply"]
    assert out["metadata"]["executed"] is False
    assert out["metadata"]["created_task"] is False


def test_historical_panel_readout_uses_symbol_row_date_and_calls_loader_once():
    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        return _panel(as_of="2026-09-20", value=0.125)

    out = _call("510300已有的12-1动量读数是多少？", None, panel_loader=loader)
    assert calls == 1
    assert out["status"] == "historical_only"
    assert out["symbol"] == "510300.SS"
    assert "2026-09-20" in out["reply"]
    assert "12.50%" in out["reply"]
    assert "历史参考" in out["reply"]
    assert out["metadata"]["observation_as_of"] == "2026-09-20"


def test_current_readout_refuses_legacy_schema_even_when_row_is_today():
    out = _call(
        "510300今天最新的12-1动量是多少？",
        None,
        panel_loader=lambda: _panel(as_of="2026-09-22", value=0.333),
    )
    assert out["status"] == "unqualified_current"
    assert "没有合格的当前值来源" in out["reply"]
    assert "正式定义身份" in out["reply"]
    assert "价格口径" in out["reply"]
    assert "输入指纹" in out["reply"]
    assert "33.30%" not in out["reply"]


def test_explicit_raw_reference_with_current_intent_reads_panel_policy_first():
    out = _call("510300当前mixed.momentum.raw@1.0.0读数如何？", None)
    assert out["status"] == "unqualified_current"
    assert out["intent"] == "current_observation"


def test_high_point_and_momentum_comparison_explains_both_without_claiming_effectiveness():
    out = _call("比较高点位置与普通动量", None)
    assert out["intent"] == "comparison"
    assert out["status"] == "proposal_only"
    assert "此前252个有效收盘" in out["reply"]
    assert "t-21" in out["reply"] and "t-252" in out["reply"]
    assert "不能证明" in out["reply"]


def test_current_readout_reports_stale_symbol_date_without_fake_value():
    out = _call("510300现在的动量是多少？", None)
    assert out["status"] == "unqualified_current"
    assert "2026-09-20" in out["reply"]
    assert "尚未核实是否覆盖最近完成交易日" in out["reply"]
    assert "已过期" not in out["reply"]
    assert "12.50%" not in out["reply"]
    assert out["metadata"]["freshness"] == "unknown"
    assert out["metadata"]["calendar"] == "unknown"


@pytest.mark.parametrize(
    "panel, phrase",
    [
        (None, "没有可读的历史面板"),
        ({"symbols": "bad"}, "结构不合格"),
        ({"symbols": []}, "没有这个标的"),
    ],
)
def test_missing_or_bad_panel_is_explicit(panel, phrase):
    out = _call("510300已有动量读数是多少？", None, panel_loader=lambda: panel)
    assert out["status"] == "unavailable"
    assert phrase in out["reply"]


def test_multiple_symbols_are_rejected_instead_of_silently_picking_one():
    out = _call("比较510300和159915的动量", None)
    assert out["status"] == "needs_clarification"
    assert out["symbol"] is None
    assert "一次只支持一个标的" in out["reply"]


def test_old_date_request_is_not_silently_mapped_to_current_snapshot():
    out = _call("查510300在2025-01-02的动量", None)
    assert out["status"] == "unsupported"
    assert "不支持按历史日期回查" in out["reply"]


@pytest.mark.parametrize("when", ["昨天", "2025/01/02", "2025年1月2日"])
def test_unsupported_explicit_date_words_do_not_read_current_snapshot(when):
    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        return _panel()

    out = _call(f"{when}510300的动量读数是多少？", None, panel_loader=loader)
    assert out["status"] == "unsupported"
    assert "不支持" in out["reply"]
    assert calls == 0


def test_unknown_use_is_rejected_without_borrowing_research_evidence():
    out = _call("把12-1动量直接用于实盘买卖", None)
    assert out["status"] == "unsupported_use"
    assert "不能用于实盘买卖" in out["reply"]


def test_report_hash_drift_refuses_only_bound_explanation(tmp_path):
    report = tmp_path / "docs/experiments/factor-momentum-rank-reuse-2026-09-22.md"
    report.parent.mkdir(parents=True)
    report.write_text("# 漂移内容", encoding="utf-8")
    index = json.loads((fr._ROOT / "configs/factor-access.v1.json").read_text())
    path = tmp_path / "configs/factor-access.v1.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(index, ensure_ascii=False))
    registry = tmp_path / "docs/research/definitions.v1.json"
    registry.parent.mkdir(parents=True)
    registry.write_bytes((fr._ROOT / "docs/research/definitions.v1.json").read_bytes())
    out = _call("完整动量排序已有证据能证明有效吗？", None, root=tmp_path,
                registry_path=registry)
    assert out["status"] == "source_drift"
    assert "内容指纹不一致" in out["reply"]
    assert "人工数据测试通过" not in out["reply"]


def test_generated_at_without_timezone_is_never_upgraded_to_qualified_time():
    out = _call("510300已有动量读数是多少？", None)
    assert out["metadata"]["generated_at"] == "2026-09-22 15:30:00"
    assert out["metadata"]["generated_at_qualified"] is False
    assert "不带时区" in out["reply"]
    assert len(out["metadata"]["observation_copy_sha256"]) == 64
    assert out["metadata"]["observation_source"]["api"] == "GET /api/factors/panel"


@pytest.mark.parametrize(
    "reference",
    [
        "mixed.momentum.raw",
        "mixed.momentum.raw@latest",
        "mixed.momentum.raw@1.0",
        "candidate:mixed.high52.proximity@draft-999",
    ],
)
def test_malformed_or_unapproved_explicit_reference_is_not_defaulted(reference):
    out = _call(f"{reference}怎么定义？", None)
    assert out["status"] == "unsupported"
    assert out["definition_refs"] == [reference]
    assert "精确版本" in out["reply"]


def test_success_metadata_binds_assembly_registry_and_definition_card():
    out = _call("普通动量怎么定义？", None)
    meta = out["metadata"]
    assert meta["assembled_at"].endswith("+08:00")
    assert meta["assembled_at_role"] == "response_assembly_not_factor_calculation"
    assert len(meta["registry_sha256"]) == 64
    assert meta["definition_cards"][0]["reference"] == "mixed.momentum.raw@1.0.0"
    assert len(meta["definition_cards"][0]["card_sha256"]) == 64
    assert "计算定义核验通过（verified）" in out["reply"]


def test_reply_report_links_point_only_to_report_library_entries():
    out = _call("这个动量因子过去真的有用吗？", None)
    encoded = re.findall(r"/library\?report=([^\)]+)", out["reply"])
    assert len(encoded) == 3
    for item in encoded:
        rel = unquote(item)
        assert rel.startswith("docs/experiments/")
        assert read_report(rel, base=fr._ROOT) is not None
    assert "candidate-definitions.md" not in out["reply"]


def test_observation_reply_shows_dates_and_assembly_role_in_plain_text():
    out = _call("510300已有动量读数是多少？", None)
    assert "数据截止：2026-09-20" in out["reply"]
    assert "计算时间：未记录" in out["reply"]
    assert "回复组装时间：2026-09-22T16:00:00+08:00" in out["reply"]


def test_weekend_does_not_turn_friday_observation_into_stale_policy():
    saturday = datetime.fromisoformat("2026-09-26T12:00:00+08:00")
    out = fr.build_factor_reply(
        "510300现在的动量是多少？",
        None,
        panel_loader=lambda: _panel(as_of="2026-09-25"),
        now=saturday,
    )
    assert out["status"] == "unqualified_current"
    assert "已过期" not in out["reply"]
    assert out["metadata"]["freshness"] == "unknown"


def test_explicit_market_suffix_must_match_panel_row():
    out = _call("510300.SZ已有动量读数是多少？", None)
    assert out["symbol"] == "510300.SZ"
    assert out["status"] == "unavailable"
    assert "没有这个标的" in out["reply"]


@pytest.mark.parametrize("lead", ["那开始回测吧", "帮我回测一下", "回测看看"])
def test_backtest_followup_returns_text_proposal_without_execution(lead):
    out = _call(f"{lead}；沿用刚才的因子问题：mixed.momentum.raw@1.0.0", None)
    assert out["status"] == "proposal_only"
    assert out["intent"] == "experiment_proposal"
    assert out["metadata"]["executed"] is False
    assert out["metadata"]["created_task"] is False
    assert "不会创建任务" in out["reply"]


def test_other_formal_object_reads_own_description_without_momentum_evidence():
    out = _call("mixed.rv20@1.0.0怎么定义？", None)
    assert out["status"] in {"ok", "limited"}
    assert out["definition_refs"] == ["mixed.rv20@1.0.0"]
    assert "20" in out["reply"]
    assert "动量排序" not in out["reply"]


def test_other_formal_object_effectiveness_has_no_bound_evidence_index():
    out = _call("mixed.rv20@1.0.0有效吗？", None)
    assert out["status"] == "evidence_not_bound"
    assert "尚未接入对应的效果证据索引" in out["reply"]
    assert "全库" not in out["reply"]


def test_future_symbol_date_is_rejected():
    out = _call(
        "510300已有动量读数是多少？",
        None,
        panel_loader=lambda: _panel(as_of="2026-09-23"),
    )
    assert out["status"] == "unavailable"
    assert "未来日期" in out["reply"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_panel_value_is_rejected(value):
    out = _call(
        "510300已有动量读数是多少？",
        None,
        panel_loader=lambda: _panel(value=value),
    )
    assert out["status"] == "unavailable"
    assert "有限数值" in out["reply"]


def test_timezone_aware_generated_at_is_not_called_timezone_missing():
    panel = _panel()
    panel["generated_at"] = "2026-09-22T15:30:00+08:00"
    out = _call("510300已有动量读数是多少？", None, panel_loader=lambda: panel)
    assert out["metadata"]["generated_at_qualified"] is True
    assert "不带时区" not in out["reply"]


def test_invalid_symbol_row_date_is_rejected():
    out = _call(
        "510300已有动量读数是多少？",
        None,
        panel_loader=lambda: _panel(as_of="2026-02-30"),
    )
    assert out["status"] == "unavailable"
    assert "日期无效" in out["reply"]
