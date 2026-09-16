"""连续讨论与简洁回答一轮（2026-09-16）：固定案例的确定性行为锁定。

覆盖（对应 raw/agent-experience-continuity-2026-09-16/inputs-and-acceptance.md）：
- 案例2：板块语境问「对应的ETF」→ 确定性诚实回答，不猜跟踪关系、不自动选产品；
- 案例5：对象已继承时不再追问「想补测哪个标的」（缺信息只问最关键的一项）；
- 案例6：「我已经持有了」→ 持仓语境（stance 进材料 + 降级直出持仓分支）；
- 案例7：「我有一万元，能不能买一点？」→ 资金主题 + 中文数字预算 + 用途澄清；
- 案例8：「和刚才相比有什么变化」→ 同份资料明确没有新数据/日期变了说变化；
- 案例10a：「科创板整体怎么看？」→ resolve 给澄清（gate 不再漏判）；
- 日期口径：当天数据说「截至 X 日」且标明是否收盘未核实，不说「今日收盘」。
"""
from __future__ import annotations

from types import SimpleNamespace

from lei_signal.api.routes.agent import (
    _comparison_reply,
    _degraded_reply,
    _deterministic_reply,
    _sector_product_relation_reply,
)
from lei_signal.copilot import resolve as resolve_mod


# ---------------- 案例7：资金主题与口语金额 ----------------

def test_money_topic_and_cn_budget():
    p = resolve_mod.parse_request("我有一万元，能不能买一点？")
    assert p["topic"] == "money"
    assert p["intent"] == "discussion"          # 讨论，不是报单/成交
    assert p["budget"]["amount"] == 10_000.0
    # 用途不明且要给投入方案 → 只问最关键的一项（用途）
    kinds = [c["kind"] for c in p["need_clarification"]]
    assert kinds == ["purpose"]


def test_loose_budget_variants():
    assert resolve_mod.parse_request("拿1万试试")["budget"]["amount"] == 10_000.0
    assert resolve_mod.parse_request("5千块够不够")["budget"]["amount"] == 5_000.0
    assert resolve_mod.parse_request("我有两万五")["budget"]["amount"] == 25_000.0
    assert resolve_mod.parse_request("十万闲钱")["budget"]["amount"] == 100_000.0
    assert resolve_mod.parse_request("三千元")["budget"]["amount"] == 3_000.0
    # 预算前缀的老路径不变
    assert resolve_mod.parse_request("预算10000元")["budget"]["amount"] == 10_000.0


def test_loose_budget_no_false_positive():
    # 裸数字不猜：代码/年份/无单位数字一律不当地金额
    assert resolve_mod.parse_request("515880 现在怎么看")["budget"] is None
    assert resolve_mod.parse_request("2024年到现在")["budget"] is None
    assert resolve_mod.parse_request("20日线怎么看")["budget"] is None


def test_budget_guards_c3():
    """C3：股数/外币/否定/截断的复杂金额一律不采信。"""
    # 股数不是钱（成交量有一万股、一万股值多少钱）
    assert resolve_mod.parse_request("成交量有一万股")["budget"] is None
    assert resolve_mod.parse_request("一万股值多少钱")["budget"] is None
    # 否定句：我没有一万元预算
    assert resolve_mod.parse_request("我没有一万元预算")["budget"] is None
    assert resolve_mod.parse_request("不用一万块")["budget"] is None
    # 外币不默认折人民币（反例另存）
    assert resolve_mod.parse_request("我有1万美元")["budget"] is None
    assert resolve_mod.parse_request("预算1万美元")["budget"] is None
    assert resolve_mod.parse_request("两万港币")["budget"] is None
    # 复杂中文金额截取部分数字宁可未知
    assert resolve_mod.parse_request("两万三千五")["budget"] is None
    # 正例保留
    assert resolve_mod.parse_request("明确的一万元")["budget"]["amount"] == 10_000.0
    assert resolve_mod.parse_request("两万五")["budget"]["amount"] == 25_000.0
    assert resolve_mod.parse_request("预算10000元")["budget"]["amount"] == 10_000.0


# ---------------- 案例6：持仓语境 ----------------

def test_detect_stance_holding():
    assert resolve_mod.detect_stance("我已经持有了。") == "holding"
    assert resolve_mod.detect_stance("套牢了怎么办") == "holding"
    assert resolve_mod.detect_stance("我手里有这个") == "holding"


def test_detect_stance_negatives():
    assert resolve_mod.detect_stance("我还没买") is None
    assert resolve_mod.detect_stance("没有持有") is None
    assert resolve_mod.detect_stance("如果持有了怎么办") is None
    assert resolve_mod.detect_stance("要不要持有") is None
    assert resolve_mod.detect_stance("持仓速览") is None  # 功能词，非语境声明
    assert resolve_mod.detect_stance("") is None
    # C3 反例：假设与否定里的持有词不是事实
    assert resolve_mod.detect_stance("如果重仓会怎样") is None
    assert resolve_mod.detect_stance("我没有重仓") is None
    assert resolve_mod.detect_stance("担心被套暂时没持仓") is None


def test_detect_fact_correction():
    c = resolve_mod.detect_fact_correction("我没持有了，早卖了")
    assert c["holding_cleared"] is True
    c = resolve_mod.detect_fact_correction("我没有一万元预算")
    assert c["budget_cleared"] is True
    c = resolve_mod.detect_fact_correction("如果清仓会怎样")
    assert c["holding_cleared"] is False          # 假设句不算撤销
    c = resolve_mod.detect_fact_correction("那现在重点看哪里")
    assert c == {"holding_cleared": False, "budget_cleared": False}


def _symbol_ctx(**over) -> dict:
    ctx = {
        "display_name": "通信ETF",
        "as_of": "2026-09-16",
        "assessment": {"color_cn": "绿色", "stage_cn": "-", "risk_state_cn": "-"},
        "buy_point_review": {"candidates": [], "tradability": {
            "tradable": False,
            "blocking_reasons": ["1.无法明确当前趋势类型", "7.多周期杂乱"],
        }},
    }
    ctx.update(over)
    return ctx


def test_degraded_holding_branch():
    ctx = _symbol_ctx(discussion_stance={"kind": "holding", "note_cn": ""})
    text = _degraded_reply("515880.SS", ctx)
    assert "持仓管理" in text
    assert "不按首次买入" in text
    assert "不编" in text                    # 未提供成本/资金不编造
    assert "没有记录任何成交" in text
    assert "不适合讨论开新仓" not in text    # 首次买入框的第一句不出现


def test_degraded_money_branch():
    ctx = _symbol_ctx(question_topic="money",
                      user_budget={"amount": 10_000.0, "currency": "CNY",
                                   "note_cn": "用户本条消息明确提供"})
    text = _degraded_reply("515880.SS", ctx)
    assert "先回答能不能买" in text
    assert "盈亏比不足 3" in text
    assert "新收入" in text and "闲钱" in text  # 只问最关键的一项
    assert "不会替你下单" in text


def test_degraded_money_beats_holding_when_asking_money():
    """C3：持仓者本条明确问钱 → 资金分支优先，不按持仓模板答。"""
    ctx = _symbol_ctx(question_topic="money",
                      discussion_stance={"kind": "holding", "note_cn": ""},
                      user_budget={"amount": 10_000.0, "currency": "CNY",
                                   "note_cn": "用户本条消息明确提供"},
                      user_purpose="spare_cash")
    text = _degraded_reply("515880.SS", ctx)
    assert "先回答能不能买" in text
    assert "从持仓管理角度讲" not in text
    assert "不再追问用途" in text               # 已知闲钱不再追问


def test_comparison_skips_global_and_other_object_turns():
    """C1：中间隔了全局轮/其他对象轮 → 只与最近一条同对象的冻结事实比。"""
    import json as _json

    global_row = SimpleNamespace(role="assistant", content="…", meta_json=_json.dumps({
        "resolved_symbol": None, "evidence_card": None}))
    hist = [
        _assistant_row("515880.SS", "2026-09-16", "观察中", 1),
        global_row,
    ]
    ctx = _symbol_ctx(as_of="2026-09-16", evidence_card={"facts": {
        "as_of": "2026-09-16", "verdict_cn": "可执行", "buy_point_candidate_n": 1}})
    text = _comparison_reply(hist, "515880.SS", ctx, "和刚才相比有什么变化？")
    # 与 515880 那条比（同日内容有变化），不被全局轮卡成「缺字段不可比」
    assert "有变化" in text
    assert "缺少可对比的字段" not in text


def test_comparison_no_same_object_history():
    """本会话该对象没有可比历史 → 如实说，不拿全局/其他对象冒充。"""
    import json as _json

    global_row = SimpleNamespace(role="assistant", content="…", meta_json=_json.dumps({
        "resolved_symbol": None, "evidence_card": None}))
    ctx = _symbol_ctx()
    text = _comparison_reply([global_row], "515880.SS", ctx, "和刚才相比有什么变化？")
    assert "还没有可比较的之前" in text


def test_degraded_today_date_honesty():
    """主控复验 §3：无完成交易时段来源证明 → 截至该日最新记录，不说当日收盘。"""
    from datetime import datetime

    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    ctx = _symbol_ctx(as_of=today)
    text = _degraded_reply("515880.SS", ctx)
    assert f"截至 {today} 的最新记录" in text
    assert "是否已收盘" in text and "来源证明" in text
    assert "收盘后" not in text


# ---------------- 案例2：板块→产品关系 ----------------

def _sector_ctx() -> dict:
    return {"context_kind": "sector", "display_name": "通信", "as_of": "2026-09-14"}


def test_sector_product_relation_honest_reply():
    text = _sector_product_relation_reply(_sector_ctx(), "有哪些对应的ETF？")
    assert text is not None
    assert "没有可核实" in text
    assert "不" in text and "猜" in text       # 不仅凭名称猜
    assert "不替你选定" in text
    assert "2026-09-14" in text                # 板块资料日期保持


def test_sector_product_relation_guards():
    # 非板块语境不出手
    assert _sector_product_relation_reply(_symbol_ctx(), "有哪些对应的ETF？") is None
    # 板块语境但问的不是产品关系 → None（走正常讨论）
    assert _sector_product_relation_reply(_sector_ctx(), "这个板块怎么看？") is None


# ---------------- 案例8：与刚才比较 ----------------

def _assistant_row(symbol: str, as_of: str, verdict: str, n: int = 0):
    import json as _json

    meta = {"resolved_symbol": symbol, "evidence_card": {"facts": {
        "symbol": symbol, "display_name": "通信ETF", "as_of": as_of,
        "verdict_cn": verdict, "buy_point_candidate_n": n,
    }}}
    return SimpleNamespace(role="assistant", content="…", meta_json=_json.dumps(meta))


def test_comparison_same_fields_no_overclaim():
    """C1：已比较字段全同 → 只说已比较字段相同，不断言系统没变化。"""
    hist = [_assistant_row("515880.SS", "2026-09-16", "按规则本轮不适合讨论开新仓")]
    ctx = _symbol_ctx(as_of="2026-09-16", evidence_card={"facts": {
        "as_of": "2026-09-16", "verdict_cn": "按规则本轮不适合讨论开新仓",
        "buy_point_candidate_n": 0}})
    text = _comparison_reply(hist, "515880.SS", ctx, "和刚才相比有什么变化？")
    assert "已比较的字段" in text and "相同" in text
    assert "2026-09-16" in text
    assert "不能断言" in text                    # 无完整版本快照不得全称
    assert "系统状态没有变化" not in text        # C1 禁句
    assert "没有新数据" not in text              # C1 禁句（同日≠无更新）


def test_comparison_same_date_content_changed():
    """C1 核心反例：同日、结论与候选数都变 → 必须报变化，不得说没变化。"""
    hist = [_assistant_row("515880.SS", "2026-09-16", "观察中", 0)]
    ctx = _symbol_ctx(as_of="2026-09-16", evidence_card={"facts": {
        "as_of": "2026-09-16", "verdict_cn": "可执行", "buy_point_candidate_n": 1}})
    text = _comparison_reply(hist, "515880.SS", ctx, "和刚才相比有什么变化？")
    assert "有变化" in text
    assert "同一数据日" in text
    assert "观察中" in text and "可执行" in text
    assert "没有新数据" not in text


def test_comparison_date_regression_is_honest():
    """C1：日期倒退（16→15）→ 退回较旧资料，不得写成「资料有更新」。"""
    hist = [_assistant_row("515880.SS", "2026-09-16", "可执行", 1)]
    ctx = _symbol_ctx(as_of="2026-09-15", evidence_card={"facts": {
        "as_of": "2026-09-15", "verdict_cn": "可执行", "buy_point_candidate_n": 1}})
    text = _comparison_reply(hist, "515880.SS", ctx, "和刚才相比有什么变化？")
    assert "更旧" in text and "退回较旧" in text
    assert "更新" not in text.replace("不是新数据", "")  # 不得宣称更新


def test_comparison_missing_fields_unverifiable():
    """C1：旧卡缺字段 → 该字段诚实不可比。"""
    import json as _json

    row = SimpleNamespace(role="assistant", content="…", meta_json=_json.dumps({
        "resolved_symbol": "515880.SS",
        "evidence_card": {"facts": {"symbol": "515880.SS", "as_of": "2026-09-15"}},
    }))
    ctx = _symbol_ctx(as_of="2026-09-16", evidence_card={"facts": {
        "as_of": "2026-09-16", "verdict_cn": "观察中", "buy_point_candidate_n": 1}})
    text = _comparison_reply([row], "515880.SS", ctx, "和刚才相比有什么变化？")
    assert "无法核实对比" in text
    assert "不能断言" in text


def test_comparison_newer_date_states_change():
    """跨日向前：日期与内容都变 → 报日期与新结论（正例保留）。"""
    hist = [_assistant_row("515880.SS", "2026-09-15", "观察中", 1)]
    ctx = _symbol_ctx(as_of="2026-09-16", evidence_card={"facts": {
        "as_of": "2026-09-16", "verdict_cn": "按规则本轮不适合讨论开新仓",
        "buy_point_candidate_n": 0}})
    text = _comparison_reply(hist, "515880.SS", ctx, "和刚才相比有什么变化？")
    assert "有变化" in text
    assert "2026-09-15" in text and "2026-09-16" in text
    assert "观察中" in text                      # 旧结论带进对比


def test_comparison_route_narrow_matching():
    """C2：方法/资金/回测口径的「变化」问题不被资料比较抢答。"""
    ctx = _symbol_ctx()
    hist = [_assistant_row("515880.SS", "2026-09-15", "观察中", 1)]
    assert _comparison_reply(hist, "515880.SS", ctx,
                             "如果换成ATR止损，胜率会有什么变化？") is None
    assert _comparison_reply(hist, "515880.SS", ctx,
                             "止盈方法换一个，结果会变吗？") is None
    assert _comparison_reply(hist, "515880.SS", ctx,
                             "多投一万块会有什么变化？") is None
    assert _comparison_reply(hist, "515880.SS", ctx,
                             "与上次回测相比有什么变化？") is None
    # 正例保留
    assert _comparison_reply(hist, "515880.SS", ctx, "和刚才相比有什么变化？") is not None
    assert _comparison_reply(hist, "515880.SS", ctx, "有什么变化？") is not None


def test_comparison_object_switched():
    hist = [_assistant_row("BK1215.SECTOR", "2026-09-14", "板块阶段：派发")]
    ctx = _symbol_ctx(as_of="2026-09-16", evidence_card={"facts": {
        "as_of": "2026-09-16", "verdict_cn": "按规则本轮不适合讨论开新仓"}})
    text = _comparison_reply(hist, "515880.SS", ctx, "和刚才相比有什么变化？")
    assert "两个对象" in text


def test_comparison_first_question_and_guards():
    ctx = _symbol_ctx()
    assert "第一份资料" in _comparison_reply([], "515880.SS", ctx, "和刚才相比有什么变化？")
    # 非比较问法不出手
    assert _comparison_reply([], "515880.SS", ctx, "现在怎么看？") is None


def test_deterministic_dispatch():
    assert _deterministic_reply([], None, _sector_ctx(), "有哪些对应的ETF？") is not None
    assert _deterministic_reply([], "515880.SS", _symbol_ctx(), "现在怎么看？") is None
    # C2：ATR 变化问题连 _deterministic_reply 整体都不出手
    hist = [_assistant_row("515880.SS", "2026-09-15", "观察中", 1)]
    assert _deterministic_reply(hist, "515880.SS", _symbol_ctx(),
                                "如果换成ATR止损，胜率会有什么变化？") is None


# ---------------- C3：会话背景记忆（同会话同对象） ----------------

def _user_row(text: str):
    return SimpleNamespace(role="user", content=text, meta_json=None)


def test_user_background_collects_same_object_facts():
    from lei_signal.api.routes.agent import _user_background

    hist = [
        _user_row("我已经持有了"),
        _assistant_row("515880.SS", "2026-09-16", "观察中", 0),
        _user_row("我有一万闲钱"),
        _assistant_row("515880.SS", "2026-09-16", "观察中", 0),
    ]
    bg = _user_background(hist, "515880.SS")
    assert bg["holding"] is True
    assert bg["budget"]["amount"] == 10_000.0
    assert bg["purpose"] == "spare_cash"


def test_user_background_not_cross_object_and_correction():
    from lei_signal.api.routes.agent import _user_background

    # 别的对象的声明不串用
    hist = [
        _user_row("我已经持有了"),
        _assistant_row("510300.SS", "2026-09-16", "观察中", 0),
    ]
    assert _user_background(hist, "515880.SS") == {}
    # 用户明确纠正后不再当作持有
    hist2 = [
        _user_row("我已经持有了"),
        _assistant_row("515880.SS", "2026-09-16", "观察中", 0),
        _user_row("我已经卖了"),
        _assistant_row("515880.SS", "2026-09-16", "观察中", 0),
    ]
    bg2 = _user_background(hist2, "515880.SS")
    assert bg2.get("holding") in (None, False)


# ---------------- 案例5/10a：resolve 澄清 ----------------

def _resolve_client(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from lei_signal.api.routes import copilot as copilot_routes
    from lei_signal.storage.sqlite_store import connect

    db = str(tmp_path / "t.db")
    connect(db).close()
    app = FastAPI()
    app.state.plans_db_path = db
    app.state.watchlist_db_path = db
    app.include_router(copilot_routes.router)
    return TestClient(app)


def test_resolve_no_redundant_backtest_symbol_question(tmp_path):
    """案例5：对象已明确（页面/消息可核实）时，不再追问「想补测哪个标的」。"""
    client = _resolve_client(tmp_path)
    r = client.post("/api/copilot/resolve", json={
        "message": "刚才那个依据够吗，不够补测。", "client_request_id": "cr-c5-1",
        "session_id": None, "selected_symbol": "515880.SS",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["intent"] == "backtest_request"
    kinds = [c["kind"] for c in data["clarification"]]
    assert "backtest_symbol" not in kinds


def test_resolve_star_market_area_clarified(tmp_path):
    """案例10a：「科创板整体」是板块泛指（不含连续「板块」二字），也给澄清。"""
    client = _resolve_client(tmp_path)
    r = client.post("/api/copilot/resolve", json={
        "message": "科创板整体怎么看？", "client_request_id": "cr-c10a-1",
        "session_id": None, "selected_symbol": None,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["resolved_symbol"] is None
    hits = [c for c in data["clarification"]
            if c["kind"] == "sector_ambiguous_index_reference"]
    assert hits, data["clarification"]
    assert "科创50" in hits[0]["question_cn"]
    assert "不代表整个板块" in hits[0]["question_cn"]
