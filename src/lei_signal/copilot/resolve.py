"""统一入口解析（03B 总控协议 §2，2026-09-08）：服务端确定用户要做什么。

纯规则、零 LLM、零写入：把一句话解析为固定意图/主题/资金用途与澄清需求，
供 `/api/copilot/resolve` 与两个前端入口使用。判定语义：

- **trade_report 只认明确已成交或明确要求报单**；「想买一些 / 打算申购 /
  要不要赎回 / 如果卖出会怎样 / 没买 / 别帮我报单」都是讨论——否定、假设、
  意愿词先于成交词判断，不靠买卖词进成交录入。仅说「报单」打开空预览。
- backtest_request 只认明确的补测/复跑说法；解析不启动回测。
- discovery＝未指定标的的找机会；existing_action＝已有持仓/复盘等独立功能。
- 资金用途 unknown 不阻断讨论；到要给投入方案时问一次（need_clarification）。
"""
from __future__ import annotations

import re
from typing import Any

INTENTS = ("discussion", "trade_report", "discovery",
           "backtest_request", "existing_action")
TOPICS = ("overview", "evidence", "risk", "money", "dca",
          "sentiment", "mindset", "plan")
PURPOSES = ("technical_trade", "income_dca", "spare_cash", "unknown")

#: 否定/假设/意愿先行词：出现即不是已成交录入（任务书 §2 固定例句口径）
_HYPOTHETICAL_RE = re.compile(
    r"如果|假如|假设|要是|要不要|会不会|别(帮我)?|不用|不想|没买|没卖|还没|"
    r"想买|想卖|想申购|想赎回|打算买|打算卖|打算申购|打算赎回|考虑|要是当年"
)
#: 明确已成交 / 明确要求报单
_TRADE_EXPLICIT_RE = re.compile(
    r"已经(买了|卖了|申购|赎回)|我买了|我卖了|买了1|买了2|买了3|买了5|成交了|下单了|"
    "^报单$|^我要报单$|帮我报单|记一笔|记账"
)
_BACKTEST_RE = re.compile(r"补测|回测|测一下|复跑|重新测|再测|跑一次回测")
#: R2：否定与查询语气——「先不要补测」「有没有已有回测」不是启动请求
_BACKTEST_NEGATIVE_RE = re.compile(
    r"先不要|不要补测|不用补测|别补测|不想补测|暂不|先别|"
    r"有没有|是否有|查(一)?下|查查|看看已有|已有回测|已有结果|历史回测结果")
_DISCOVERY_RE = re.compile(
    r"最近机会|看看机会|发掘机会|机会扫描|扫扫机会|有什么机会|今天看什么|"
    "标的雷达|扫一下自选|找点机会")
_EXISTING_RE = re.compile(r"持仓|我的仓位|持仓速览|复盘|周报|这周做得怎么样|成交记录|台账")

_TOPIC_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("plan", re.compile(r"整理成计划|保存草稿|落计划|建计划|生成计划|做个计划")),
    ("money", re.compile(r"资金|投多少|仓位多少|多少预算|金额|投一点|买多少")),
    ("dca", re.compile(r"定投|闲钱|每月|新收入|工资|分批投")),
    ("sentiment", re.compile(r"情绪|冰点|强热|恐慌|热警报|散户")),
    ("mindset", re.compile(r"心态|拿不住|怕跌|慌|睡不着")),
    ("evidence", re.compile(r"胜率|历史成绩|历史如何|依据|赢率|历史怎么样|"
                            "换.*退出|换.*止损|换一种止损|退出会怎样")),
    ("risk", re.compile(r"风险|会不会跌|风险在哪|最坏")),
)

_PURPOSE_DCA_RE = re.compile(r"每月|新收入|工资|定投")
_PURPOSE_SPARE_RE = re.compile(r"闲钱|分批")
_PURPOSE_TECH_RE = re.compile(r"买它|买这个|技术交易|按计划买|(这个|它|该标的).{0,6}(买|加仓|参与)")

# 03B-R3 S2：退出方式的**后端统一识别**（与前端 parseBacktestExit 同一套
# 口径：退出1/抵扣价→a6_1；退出2/关键波动→a6_2；退出3/初始止损→a6_3）。
# 页面、任务创建与讨论证据比较消费同一识别结果，不自造第二套。
_EXIT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("a6_2_top_plus_keywave",
     re.compile(r"退出\s*[②2二]|a6[_\s]?2|关键波|顶部构造.{0,6}退出|换.*关键波")),
    ("a6_3_structure_stop",
     re.compile(r"退出\s*[③3三]|a6[_\s]?3|初始止损|只.{0,4}止损|换.*止损|换一种止损")),
    ("a6_1_costbasis",
     re.compile(r"退出\s*[①1一]|a6[_\s]?1|抵扣价|成本|换.*抵扣")),
)


# 03B-R3 T1：用户明确给出的比较区间（起止日期）与「采用这次历史运行的窗口」
# 两种可证明来源；识别不到＝未核实，不默认与旧运行相同。
_WINDOW_RANGE_RE = re.compile(
    r"(20\d{2})\s*[-/年.]\s*(\d{1,2})\s*[-/月.]\s*(\d{1,2})\s*日?\s*"
    r"(?:至|到|~|-|—|—)\s*"
    r"(20\d{2})\s*[-/年.]\s*(\d{1,2})\s*[-/月.]\s*(\d{1,2})")
_ADOPT_RUN_WINDOW_RE = re.compile(
    r"(?:采用|用|沿用|使用|按|照)\s*(?:这次|本次|该|此|上次|上一?次|那次|历史)?\s*"
    r"(?:运行|回测|补测)?\s*(?:的)?\s*(?:窗口|区间|时间段|日期|范围)"
    r"|(?:窗口|区间)\s*(?:改?用|采用|沿用)\s*(?:这次|本次|该|上次|历史)"
    r"|(?:同样|一致|相同的)\s*(?:窗口|区间)")

# 运行编号（run_id）真实格式：YYYYMMDD-HHMMSS-<6位hex>（backtest/service.py
# new_run_id）。从「采用…窗口」类消息里抽取用户明确指定的 run_id（d2），使
# 其真正进入选择器，而非只读取 win_choice.run_id 却从不生成该字段。
_RUN_ID_RE = re.compile(
    r"run[_]?id\s*[:=]\s*([0-9]{8}-[0-9]{6}-[0-9a-fA-F]{6})"
    r"|\b([0-9]{8}-[0-9]{6}-[0-9a-fA-F]{6})\b",
    re.IGNORECASE,
)


def _extract_run_id(text: str) -> str | None:
    """从消息中抽取系统真实格式的运行编号（d2）。无则返回 None。"""
    if not text:
        return None
    m = _RUN_ID_RE.search(text)
    if not m:
        return None
    return m.group(1) or m.group(2)


def parse_exit_choice(text: str) -> str | None:
    """从一句话里识别用户明确的退出方式（返回引擎 exit_variant id 或 None）。"""
    t = (text or "").strip()
    if not t:
        return None
    for exit_id, pat in _EXIT_PATTERNS:
        if pat.search(t):
            return exit_id
    return None


def parse_window_choice(text: str) -> dict[str, Any] | None:
    """从一句话里识别用户明确的**比较区间**（03B-R3 T1）。

    只认两种明确表达，其余一律返回 None（＝该维度尚未核实，绝不默认相同）：

    - ``explicit_dates``：「只比较 2024-01-01 至 2024-06-28」这类明确起止；
    - ``adopt_run_window``：「采用这次历史运行的窗口」「用上次回测的区间」
      这类**明确选择**——不强迫用户手填日期，也能形成可证明的区间。
    """
    t = (text or "").strip()
    if not t:
        return None
    m = _WINDOW_RANGE_RE.search(t)
    if m:
        def _d(y: str, mo: str, d: str) -> str | None:
            # 合法日历解析：不存在的日期（如 2024-02-30）、倒序或非法组合直接
            # 判为无明确选择，绝不标 verified 或静默回退旧窗口（03B-R3 边界 w3）。
            from datetime import date as _date

            try:
                _date(int(y), int(mo), int(d))
            except (ValueError, OverflowError):
                return None
            return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"

        start = _d(m.group(1), m.group(2), m.group(3))
        end = _d(m.group(4), m.group(5), m.group(6))
        if start and end and start <= end:
            return {"kind": "explicit_dates", "start": start, "end": end,
                    "source": "message"}
        # 命中日期格式但日历非法/倒序：记为一次明确但无效的选择（边界 w3）。
        # 调用方不应静默回退旧窗口或继承，应判未核实。
        return {"kind": "explicit_dates", "start": None, "end": None,
                "source": "message", "invalid": True}
    if _ADOPT_RUN_WINDOW_RE.search(t):
        # 明确采用历史运行：若消息同时给出 run_id，则把该身份带入选择器
        # （d2）；选择器据 run_id 在本对象/会话候选中定位，多候选无明确身份
        # 时不静默用最新一条。
        return {"kind": "adopt_run_window", "source": "message",
                "run_id": _extract_run_id(t)}
    return None


def parse_request(message: str) -> dict[str, Any]:
    """一句话 → 固定意图/主题/用途/澄清。纯函数。"""
    text = (message or "").strip()
    if not text:
        return {"intent": "discussion", "topic": "overview", "purpose": "unknown",
                "need_clarification": [], "subject_hint": None,
                "trade_preview_requested": False, "is_hypothetical": False}

    hypothetical = bool(_HYPOTHETICAL_RE.search(text))
    topic = next((t for t, pat in _TOPIC_RULES if pat.search(text)), None)

    # ---- 意图（顺序即优先级：补测 > 已有功能 > 发现 > 成交 > 讨论）----
    # R2：否定/查询语气先于启动判断——「先不要补测」「有没有已有回测」是讨论
    if _BACKTEST_RE.search(text) and not _BACKTEST_NEGATIVE_RE.search(text):
        intent = "backtest_request"
    elif _EXISTING_RE.search(text):
        intent = "existing_action"
    elif _DISCOVERY_RE.search(text):
        intent = "discovery"
    elif _TRADE_EXPLICIT_RE.search(text) and not hypothetical:
        intent = "trade_report"
    elif _TRADE_EXPLICIT_RE.search(text) and hypothetical:
        intent = "discussion"  # 「要不要赎回/如果卖出」＝讨论
    elif re.search(r"报单|申购|赎回", text) and not hypothetical and len(text) <= 6:
        # 仅说「报单/申购/赎回」：打开空预览（不补造金额）
        intent = "trade_report"
    else:
        intent = "discussion"
    if intent == "discovery":
        topic = topic or "overview"
    if _BACKTEST_NEGATIVE_RE.search(text) and _BACKTEST_RE.search(text):
        topic = "evidence"  # 「有没有已有回测」＝查历史，不是启动

    # ---- R2/R3：用户明确选择的方法与预算（来源=本条消息；存入快照）----
    method_choice = None
    m = re.search(r"模块\s*([A-Da-d])", text)
    exit_choice = parse_exit_choice(text)
    if m or exit_choice:
        method_choice = {"module": (m.group(1).upper() if m else None),
                         "exit_variant": exit_choice, "source": "message"}
        if not m:
            method_choice["module_source"] = "unspecified"
    budget = None
    bm = re.search(r"预算\s*([0-9][0-9,，.]*)\s*(?:元|块)?", text)
    if bm:
        amount = float(bm.group(1).replace(",", "").replace("，", ""))
        budget = {"amount": amount, "currency": "CNY",
                  "note_cn": "用户本条消息明确提供"}

    # ---- 资金用途（R2：按钱的来源区分——闲钱优先于定投动词）----
    if _PURPOSE_SPARE_RE.search(text):
        purpose = "spare_cash"
    elif _PURPOSE_DCA_RE.search(text):
        purpose = "income_dca"
    elif _PURPOSE_TECH_RE.search(text):
        purpose = "technical_trade"
    else:
        purpose = "unknown"

    # ---- 澄清：用途不明且本次要给投入方案（钱怎么用）----
    need_clarification: list[dict[str, str]] = []
    if purpose == "unknown" and topic in ("money", "dca") and intent == "discussion":
        need_clarification.append({
            "kind": "purpose",
            "question_cn": "这笔钱是持续投入的新收入，还是已有的闲钱分批？",
        })
    if intent == "backtest_request" and not re.search(r"标的|代码|\d{6}|这个|该", text):
        need_clarification.append({
            "kind": "backtest_symbol",
            "question_cn": "想补测哪个标的？（补测一次只跑一个标的、一套明确的方法）",
        })

    return {
        "intent": intent,
        "topic": topic or "overview",
        "purpose": purpose,
        "need_clarification": need_clarification,
        "subject_hint": None,  # 标的解析由路由层结合上下文完成
        "method_choice": method_choice,
        "budget": budget,
        "trade_preview_requested": intent == "trade_report",
        "is_hypothetical": hypothetical,
    }


__all__ = ["parse_request", "INTENTS", "TOPICS", "PURPOSES"]
