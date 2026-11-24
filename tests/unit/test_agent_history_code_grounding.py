"""S4-2 数值白名单误拦反例（agent-whitelist-fix-2026-09-20）。

场景来自真模型评测 raw/agent-realmodel-eval-2026-09-20 S4-2（B 类归因）：
追问消息带「板块」命中 asks_for_sector → 不继承标的 → 全局路径材料里没有
任何标的代码；模型回显上一轮会话历史里讨论过的 510300，被数值接地校验
当编数字误拦 → 好答案被换成降级模板。

修复口径（冻结）：会话上下文中出现过的**标的代码**视为有据；历史里的
价位数值不进白名单（价位类校验保持严格）；无证据支持的代码/数值仍拒。
"""
from __future__ import annotations

from types import SimpleNamespace

from lei_signal.api.routes.agent import (
    _history_symbol_numbers,
    _payload_symbol_numbers,
)
from lei_signal.plans.grounding import (
    collect_payload_numbers,
    extract_market_numbers,
    verify_numeric_grounding,
)

S4_2_MESSAGE = "那美股大跌一般会传导到 A 股哪些板块？我该避开什么？"
S4_1_HISTORY = [
    SimpleNamespace(
        role="user",
        content="美股科技股最近走弱，我要讨论的标的代码是 510300，"
                "对我持仓有什么影响？"),
    SimpleNamespace(role="assistant", content="好的"),
]
GLOBAL_CTX = {"context_kind": "global", "breadth_cn": None, "margin_cn": None}


def _allowed(ctx, message, history):
    """与 agent.py 讨论管线两处调用点同构的白名单表达式。"""
    return (
        collect_payload_numbers(ctx)
        | frozenset(extract_market_numbers(message))
        | frozenset(_payload_symbol_numbers(ctx))
        | frozenset(_history_symbol_numbers(history))
    )


def test_history_symbol_numbers_extracts_codes_only():
    nums = _history_symbol_numbers(S4_1_HISTORY + [
        SimpleNamespace(role="assistant", content="关键价位 165.7，日期 2026-09-18"),
    ])
    assert 510300.0 in nums
    assert 165.7 not in nums  # 价位类不进白名单：历史只补代码数字段


def test_s42_history_code_echo_passes_grounding():
    """正证：全局追问回显会话历史里的标的代码不再误拦（修复前此断言失败）。"""
    reply = ("美股大跌一般会传导到 A 股，你上一轮问的 510300 属宽基 ETF，"
             "受冲击相对间接；哪些板块受影响更深，材料里没有统计，不编。")
    ok, reason = verify_numeric_grounding(
        reply, _allowed(GLOBAL_CTX, S4_2_MESSAGE, S4_1_HISTORY))
    assert ok, reason


def test_invented_code_still_rejected():
    """反证一：从未出现在材料/消息/历史的代码 512999 仍被拒（保留原拒绝）。"""
    reply = "美股大跌一般会传导到 A 股，512999 这类科技宽基受冲击更直接。"
    ok, reason = verify_numeric_grounding(
        reply, _allowed(GLOBAL_CTX, S4_2_MESSAGE, S4_1_HISTORY))
    assert not ok and "512999" in reason


def test_history_price_echo_still_rejected():
    """反证二：历史里的价位数值 165.7 不因本次修复获得豁免（价位保持严格）。"""
    history = S4_1_HISTORY + [
        SimpleNamespace(role="assistant", content="关键价位 165.7"),
    ]
    ok, reason = verify_numeric_grounding(
        "510300 的关键价位 165.7，跌破即失效",
        _allowed(GLOBAL_CTX, S4_2_MESSAGE, history))
    assert not ok and "165.7" in reason


# ---- R2 收紧（agent-whitelist-fix-r2-2026-09-20）----

def test_history_amount_year_not_whitelisted():
    """P2：历史大额金额/年份（10000 元、2026 年）不入补集。

    修复前 \\d{4,} 会把 10000/2026 当代码段收入白名单（数字长度≠标的
    身份）。负例隔离：这两数值不在 ctx/消息等其他白名单来源中。
    """
    history = S4_1_HISTORY + [
        SimpleNamespace(role="user", content="我成交价 10000 元，2026 年到期"),
    ]
    allowed = _allowed(GLOBAL_CTX, S4_2_MESSAGE, history)
    assert 10000.0 not in allowed
    assert 2026.0 not in allowed
    assert 510300.0 in allowed  # 用户消息里的合法代码仍收（P1 保持）


def test_history_assistant_invented_code_not_whitelisted():
    """P3：仅出现在助手历史正文里的代码（512999）不得因入史自合法化。

    来源分层：历史出现≠来源可信——助手无依据编造的代码进入历史后，
    再引用也不放行（否则形成自增强编造路径）。
    """
    history = S4_1_HISTORY + [
        SimpleNamespace(role="assistant", content="可以关注 512999"),
    ]
    allowed = _allowed(GLOBAL_CTX, S4_2_MESSAGE, history)
    assert 512999.0 not in allowed
    ok, reason = verify_numeric_grounding(
        "512999 这类科技宽基受冲击更直接",
        _allowed(GLOBAL_CTX, S4_2_MESSAGE, history))
    assert not ok and "512999" in reason


def test_history_code_prefix_gate():
    """身份判别：6 位数字但前缀非法（如 99 开头）不算代码。"""
    nums = _history_symbol_numbers([
        SimpleNamespace(role="user", content="看看 990012 怎么样"),
    ])
    assert nums == set()

# ---- R3 身份标记准入（agent-whitelist-fix-r3-2026-09-20）----

def test_r3_p1_identity_marker_code_whitelisted():
    """P1：「我要讨论的标的代码是 510300」→ 入补集，回显不误拦。"""
    history = [
        SimpleNamespace(role="user", content="我要讨论的标的代码是 510300"),
        SimpleNamespace(role="assistant", content="好的"),
    ]
    allowed = _allowed(GLOBAL_CTX, S4_2_MESSAGE, history)
    assert 510300.0 in allowed
    ok, reason = verify_numeric_grounding(
        "你讨论的 510300 属宽基 ETF，受冲击相对间接", allowed)
    assert ok, reason


def test_r3_p2a_amount_sentence_not_whitelisted():
    """P2a：「账户金额是 510300 元」——6 位、前缀合法、来自用户，但是金额。"""
    history = [
        SimpleNamespace(role="user", content="账户金额是 510300 元"),
    ]
    assert _history_symbol_numbers(history) == set()
    allowed = _allowed(GLOBAL_CTX, S4_2_MESSAGE, history)
    assert 510300.0 not in allowed


def test_r3_p2b_price_decimal_not_whitelisted():
    """P2b：「成交价是 510300.25 元」——小数点不算相邻数字，整数段不算代码。"""
    history = [
        SimpleNamespace(role="user", content="成交价是 510300.25 元"),
    ]
    assert _history_symbol_numbers(history) == set()
    allowed = _allowed(GLOBAL_CTX, S4_2_MESSAGE, history)
    assert 510300.0 not in allowed and 510300.25 not in allowed


def test_r3_p2c_no_other_whitelist_source_covers_amount():
    """P2c 防掩盖：P2a/P2b 数值不在 ctx/消息等其他白名单来源中。"""
    history = [SimpleNamespace(role="user", content="账户金额是 510300 元")]
    ctx_nums = (collect_payload_numbers(GLOBAL_CTX)
                | frozenset(_payload_symbol_numbers(GLOBAL_CTX)))
    msg_nums = frozenset(extract_market_numbers(S4_2_MESSAGE))
    assert 510300.0 not in ctx_nums
    assert 510300.0 not in msg_nums


def test_r3_p3_assistant_history_still_excluded():
    """P3 保持：仅助手历史里的 512999 不放行（R2 来源分层不回退）。"""
    history = [
        SimpleNamespace(role="assistant", content="可以关注 512999"),
    ]
    allowed = _allowed(GLOBAL_CTX, S4_2_MESSAGE, history)
    assert 512999.0 not in allowed


def test_r3_p4_current_message_invented_still_rejected():
    """P4 保持：当前消息编造 512999 仍拒（消息抽取不收纯 6 位数字段）。"""
    history = [
        SimpleNamespace(role="user", content="我要讨论的标的代码是 510300"),
    ]
    ok, reason = verify_numeric_grounding(
        "512999 这类科技宽基受冲击更直接",
        _allowed(GLOBAL_CTX, S4_2_MESSAGE, history))
    assert not ok and "512999" in reason


def test_r3_p6_r2_negatives_hold():
    """P6 保持：R2 负例（10000 元/2026 年/165.7）仍不入补集。"""
    history = [
        SimpleNamespace(role="user",
                        content="我成交价 10000 元，2026 年到期，关注 165.7"),
    ]
    allowed = _allowed(GLOBAL_CTX, S4_2_MESSAGE, history)
    assert 10000.0 not in allowed and 2026.0 not in allowed
    assert 165.7 not in allowed


def test_r3_marker_variants():
    """标记模式集变体：代码：X / 基金代码 X / ETF 代码=X / 标的是 X 均入；
    「无标记裸数字」与「标的成本 510300」不入。
    """
    def nums(text):
        return _history_symbol_numbers(
            [SimpleNamespace(role="user", content=text)])

    assert nums("代码：510300") == {510300.0}
    assert nums("基金代码 510300 怎么样") == {510300.0}
    assert nums("ETF 代码=510300") == {510300.0}
    assert nums("我们讨论的标的是 510300") == {510300.0}
    # 无标记裸数字 / 非指向语境 → 不入（由 chat_fallback 降级承接）
    assert nums("看看 510300 怎么样") == set()
    assert nums("这个标的成本 510300 元") == set()
    # 计量单位紧跟（数量/金额语境）即使带「标的」字样也不入
    assert nums("标的 510300 股") == set()
