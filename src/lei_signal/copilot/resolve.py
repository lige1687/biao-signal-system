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
    # 连续讨论一轮（2026-09-16）：口语资金问法「能不能买一点/能买吗」归入资金主题，
    # 让用途澄清与资金纪律块能接上；「买点」二字单独出现不算资金问题（买点是技术概念）。
    ("money", re.compile(r"资金|投多少|仓位多少|多少预算|金额|投一点|买多少|"
                         r"买一点|能不能买|能买吗|可以买吗|能买不|"
                         r"怎么安排|如何安排")),
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
#: 三轮收口（主控复核 r3）：分句内用途词**紧前方**被否定时不建立该用途
#: （「我没有闲钱」不建闲钱用途；「闲钱」之前 5 字内出现否定词即算）。
_PURPOSE_NEG_TAIL_RE = re.compile(r"(?:不|没|无|未|别|勿|非)[^，。；,.;:;?!？！]{0,4}$")
_PURPOSE_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("spare_cash", _PURPOSE_SPARE_RE),
    ("income_dca", _PURPOSE_DCA_RE),
    ("technical_trade", _PURPOSE_TECH_RE),
)


def _establish_purpose(clause: str) -> str | None:
    """一个本人分句里的肯定用途；被否定的用途词不算（沿用 R2 优先级）。"""
    for name, pat in _PURPOSE_RULES:
        m = pat.search(clause)
        if m and not _PURPOSE_NEG_TAIL_RE.search(clause[:m.start()]):
            return name
    return None

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


_CN_DIGIT = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}
#: 口语金额：阿拉伯带单位 或 中文数字+万/千（可带 元/块 收尾）
_LOOSE_BUDGET_RE = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?)\s*(万|千|w|W|k|K)\s*(?:元|块)?"
    r"|([一二两三四五六七八九]?十?[一二两三四五六七八九半]?)\s*(万|千)"
    r"([一二两三四五六七八九])?\s*(?:元|块)?")


def _cn_head_to_number(head: str) -> float | None:
    """中文小数字头 → 数值：一/十/十二/二十/二十五/两万五的「两五」段。失败 None。"""
    if not head:
        return None
    if head == "半":
        return 0.5
    if "十" in head:
        left, _, right = head.partition("十")
        tens = _CN_DIGIT.get(left, 1) if left else 1
        ones = _CN_DIGIT.get(right, 0) if right else 0
        if (left and left not in _CN_DIGIT) or (right and right not in _CN_DIGIT):
            return None
        return float(tens * 10 + ones)
    if head in _CN_DIGIT:
        return float(_CN_DIGIT[head])
    # 「两万五」的尾段「两五」= 2.5 万（口语省略「十」前的单位）
    if len(head) == 2 and head[0] in _CN_DIGIT and head[1] in _CN_DIGIT:
        return _CN_DIGIT[head[0]] + _CN_DIGIT[head[1]] / 10.0
    return None


#: 金额守卫（C3，2026-09-16 主控复验）：股数/份额不是钱；否定句里的金额
#: 不是用户已给事实；外币不默认折算人民币；复杂中文金额截取部分数字宁可未知。
_BUDGET_NOT_MONEY_AFTER = ("股", "手", "份", "张", "桶", "克", "盎司", "手")
_BUDGET_NEG_BEFORE = ("没", "无", "不", "别", "未")
_BUDGET_FOREIGN_AFTER = ("美元", "美金", "港币", "港元", "欧元", "日元", "英镑", "刀")
_CN_CONT_DIGITS = set("一二两三四五六七八九十百千万亿")
#: 收口二（二轮复验 2026-09-17）：假设与第三人的钱不是用户事实
#: （「如果我有一万元」「朋友有一万元闲钱」）。
_HYPOTHETICAL_RE2 = re.compile(r"如果|假如|假设|要是|会不会|要不要")
_THIRD_PERSON_RE = re.compile(
    r"朋友|同事|家人|亲戚|同学|别人|人家|我妈|我爸|他有|她有|他们|客户|领导")
#: 三轮收口（主控复核 r3 2026-09-17）：整句级否定/人物守卫在一句多事时
#: 互相误伤——统一改为**分句**核实：按标点切分后逐分句判断归属与否定。
_CLAUSE_SPLIT_RE = re.compile(r"[，。；,;.!！?？\n：:]+")


def _clause_spans(text: str) -> list[tuple[int, int, str]]:
    """[(start, end, 分句)]，保留原文位置（空白分句丢弃）。"""
    spans: list[tuple[int, int, str]] = []
    start = 0
    for m in _CLAUSE_SPLIT_RE.finditer(text or ""):
        if m.start() > start:
            spans.append((start, m.start(), text[start:m.start()]))
        start = m.end()
    if text and start < len(text):
        spans.append((start, len(text), text[start:]))
    return spans


def _own_clause(clause: str) -> bool:
    """分句是否可归属本人：含第三人/假设标记的分句不是本人陈述
    （「朋友…」「如果…」）；无标记分句按既有约定视为本人陈述，
    不向更远处猜归属。"""
    return not (_THIRD_PERSON_RE.search(clause) or _HYPOTHETICAL_RE2.search(clause))


def _budget_guard_ok(text: str, m: re.Match[str]) -> bool:
    """一条金额候选是否可采信为人民币预算（C3 四道守卫）。"""
    after = text[m.end():m.end() + 3]
    if after.startswith(_BUDGET_NOT_MONEY_AFTER):
        return False  # 股数/份额/手数：不是金额（成交量有一万股）
    if after.startswith(_BUDGET_FOREIGN_AFTER):
        return False  # 外币：不默认折成人民币，宁可未知（反例另存）
    if after and after[0] in _CN_CONT_DIGITS:
        return False  # 后面还连着中文数字：是更复杂的金额说法，不截取部分
    if after and after[0] in "万千wWkK":
        return False  # 「预算1万美元」：单位在数字后，交给口语分支（外币守卫）
    before = text[max(0, m.start() - 3):m.start()]
    if any(w in before for w in _BUDGET_NEG_BEFORE):
        return False  # 「我没有一万元预算」「不用一万」：否定不是事实
    # 三轮收口：归属按金额所在**分句**核实（「朋友有一万，我五千」里
    # 五千是本人事实，朋友的一万不是）。
    clause = next((t for s, e, t in _clause_spans(text)
                   if s <= m.start() < e), text)
    if not _own_clause(clause):
        return False  # 「朋友有一万元」「如果我有一万元」：非本人事实
    return True


def _parse_loose_budget(text: str) -> dict[str, Any] | None:
    """不带「预算」前缀的口语金额识别（2026-09-16 连续讨论一轮）。

    只在带明确单位时采信：阿拉伯数字必须跟 万/千/w/k；中文数字必须跟 万/千。
    不匹配裸数字（515880 这类代码、2024 这类年份自然出局）；股数/外币/
    否定句/截断的复杂金额一律不采信（C3）。"""
    for m in _LOOSE_BUDGET_RE.finditer(text or ""):
        if not _budget_guard_ok(text, m):
            continue
        if m.group(1) is not None:
            value = float(m.group(1))
            unit = m.group(2)
            if unit in ("万", "w", "W"):
                value *= 10_000.0
            elif unit in ("千", "k", "K"):
                value *= 1_000.0
            return {"amount": value, "currency": "CNY",
                    "note_cn": "用户本条消息明确提供"}
        head, unit_cn, tail = m.group(3), m.group(4), m.group(5)
        if not head:
            continue
        base = _cn_head_to_number(head)
        if base is None:
            continue
        # 「两万五/三千五」口语省略：单位后的尾数 = 十分之一个单位
        if tail:
            base += _CN_DIGIT[tail] / 10.0
        return {"amount": base * (10_000.0 if unit_cn == "万" else 1_000.0),
                "currency": "CNY", "note_cn": "用户本条消息明确提供（中文数字换算）"}
    return None


#: 持仓语境（连续讨论一轮 2026-09-16）：用户声明已持有当前对象。
#: 只识别明确的持有陈述；「持仓速览/我的仓位」是 existing_action 功能词，
#: 不算语境声明；否定/假设先行（没买/如果持有）不算。
_HOLDING_RE = re.compile(r"我已经持有|我已持有|我持有|已经持有|持有着|"
                         r"我手里有|我手上有|被套|套牢|重仓|轻仓")
#: C3（主控复验 2026-09-16）：假设/条件句里的持有词不是事实（「如果重仓
#: 会怎样」）；否定词就近压过持有词（「我没有重仓」「担心被套暂时没持仓」）。
_HOLDING_HYPOTHETICAL_RE = re.compile(
    r"如果|假如|假设|要是|会不会|要不要|考虑|打算|想(要|持)")
_HOLDING_NEG_NEAR_RE = re.compile(
    r"(?:没|未|不|无|别)[^，。；,.;?!？！]{0,6}(?:持有|重仓|轻仓|被套|套牢|持仓|手里有|手上有)")
_HOLDING_FEATURE_RE = re.compile(r"持仓速览|我的仓位|持仓情况|持仓查询")
#: 现金不是持仓（收口二）：「我手里有一万元闲钱」是钱不是证券。
_HOLDING_CASH_RE = re.compile(
    r"(?:手里有|手上有)[^，。；,.;?!？！]{0,8}(?:元|块|万|千|钱|现金|预算|闲钱|资金)")
#: 用户明确纠正（会话背景清除用）：此后不再当作持有/有该笔资金。
_HOLDING_CLEAR_RE = re.compile(
    r"没(有)?持有|没买|未持有|不再持有|不持有了|不持有|已经卖了|已卖出|"
    r"清仓|割肉|止盈离场|暂时没持仓")
#: 三轮收口（主控复核 2026-09-17）：**否定清仓动作**不是撤销——
#: 「我没有清仓/还没卖出」= 仍在持有，不得清除既有持仓事实。
_CLEAR_ACTION_NEG_RE = re.compile(
    r"(?:没|无|未|别|不|勿)[^，。；,.;?!？！]{0,4}(?:清仓|割肉|止盈离场|卖)")
_BUDGET_CLEAR_RE = re.compile(
    r"没(有)?[^，。；,.;?!？！]{0,8}(预算|闲钱|资金|那么多钱|这个钱)|"
    r"不(是|要)[^，。；,.;?!？！]{0,6}(万|千|元|块)")


def detect_stance(message: str) -> str | None:
    """用户本条消息声明的讨论立场。当前只有 ``holding``（已持有）。

    立场只影响**解释口径**（持仓管理视角而非首次买入视角），不改变技术规则、
    不写真实计划或成交；按消息逐条识别——恢复历史时不把旧意图当成今天的
    新授权；同会话同对象的背景记忆由路由层按对象范围另行维护（C3）。"""
    text = (message or "").strip()
    if not text:
        return None
    if _HOLDING_FEATURE_RE.search(text):
        return None  # 功能词：持仓速览/我的仓位，不是语境声明
    if _HOLDING_HYPOTHETICAL_RE.search(text):
        return None  # 假设/意愿句里的持有词不是事实
    if _THIRD_PERSON_RE.search(text):
        return None  # 第三人的持仓不是用户事实（收口二）
    if _HOLDING_CASH_RE.search(text):
        return None  # 「手里有一万元闲钱」是现金不是证券持仓（收口二）
    if _HOLDING_NEG_NEAR_RE.search(text):
        return None  # 否定就近压过持有词
    if _HOLDING_RE.search(text):
        return "holding"
    return None


def detect_fact_correction(message: str) -> dict[str, bool]:
    """用户本条消息是否明确**撤销**自己此前声明的事实（C3 背景记忆清除用）。

    ``holding_cleared``：说了没持有/已卖出/清仓等；
    ``budget_cleared``：说了没有预算/没有那笔钱等。只认明确撤销，沉默不算。
    三轮收口（主控复核 r3 2026-09-17）：判断单位从整句改为**分句**——只从
    本人、肯定的分句提取撤销；第三人分句既不清本人，也不阻止同句其他分句
    的本人更新（「朋友还持有，但我已经清仓了」→ 撤销生效）；否定清仓动作
    的分句（「我没清仓」）不撤销，也不影响其他分句；假设/意愿分句不撤销。"""
    text = (message or "").strip()
    if not text:
        return {"holding_cleared": False, "budget_cleared": False}
    holding_cleared = False
    budget_cleared = False
    for _s, _e, clause in _clause_spans(text):
        if not _own_clause(clause):
            continue
        if (not holding_cleared and _HOLDING_CLEAR_RE.search(clause)
                and not _HOLDING_HYPOTHETICAL_RE.search(clause)
                and not _CLEAR_ACTION_NEG_RE.search(clause)):
            holding_cleared = True
        if not budget_cleared and _BUDGET_CLEAR_RE.search(clause):
            budget_cleared = True
    return {"holding_cleared": holding_cleared, "budget_cleared": budget_cleared}


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
    if bm and _budget_guard_ok(text, bm):
        amount = float(bm.group(1).replace(",", "").replace("，", ""))
        budget = {"amount": amount, "currency": "CNY",
                  "note_cn": "用户本条消息明确提供"}
    if budget is None:
        # 连续讨论一轮（2026-09-16）：不带「预算」前缀的口语金额也识别——
        # 阿拉伯数字必须带单位（1万/5千/3w/5k，裸数字不猜，避免误吃代码/日期）；
        # 中文数字（一万/两万五/十万/一千块）按字面换算。
        budget = _parse_loose_budget(text)

    # ---- 资金用途（R2：按钱的来源区分——闲钱优先于定投动词）----
    # 三轮收口（主控复核 r3 2026-09-17）：用途按**分句**提取——被否定的
    # 用途词不建立该用途（「我没有闲钱」），第三人/假设分句不提取
    # （「朋友有闲钱」），本人肯定分句可更新（「…这是每月工资定投」）；
    # 含糊无归属不猜。与撤销共用同一套分句/归属判断，不各建一套整句守卫。
    purpose = "unknown"
    for _s, _e, clause in _clause_spans(text):
        if not _own_clause(clause):
            continue
        established = _establish_purpose(clause)
        if established:
            purpose = established
            break

    # ---- 澄清：用途不明且本次要给投入方案（钱怎么用）----
    # 三轮收口：第三人/假设的钱不追问用途（不能让用户替朋友或假设情形分类）。
    need_clarification: list[dict[str, str]] = []
    if (purpose == "unknown" and topic in ("money", "dca") and intent == "discussion"
            and not _HYPOTHETICAL_RE2.search(text)
            and not _THIRD_PERSON_RE.search(text)):
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


__all__ = ["parse_request", "detect_stance", "detect_fact_correction",
           "INTENTS", "TOPICS", "PURPOSES"]
