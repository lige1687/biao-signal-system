"""计划台账数据模型（migration 010 对应的领域对象）。

刻意不存在的字段：股数、金额、成交价、账户、仓位比例、盈亏金额--
计划台账只记状态机 + 价位。``tests/integration/test_acceptance_gates.py``
的执行域禁用符号 gate 持续扫描，新增字段不得引入数量/金额。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 计划状态
PLAN_DRAFT = "draft"
PLAN_ARMED = "armed"
PLAN_ENTERED = "entered"
PLAN_EXITED = "exited"
PLAN_INVALIDATED = "invalidated"
PLAN_SUPERSEDED = "superseded"
PLAN_ABANDONED = "abandoned"

PLAN_STATES = (
    PLAN_DRAFT, PLAN_ARMED, PLAN_ENTERED, PLAN_EXITED,
    PLAN_INVALIDATED, PLAN_SUPERSEDED, PLAN_ABANDONED,
)

# 修订裁决
VERDICT_SNAPSHOT = "__snapshot__"          # revision_no=0 创建快照
VERDICT_WITHIN_PLAYBOOK = "within_playbook"
VERDICT_NEEDS_REVIEW = "needs_review"
VERDICT_CONFIRMED_OVERRIDE = "confirmed_override"

# alert 严重级
SEVERITY_BLOCK = "block"
SEVERITY_REMIND = "remind"
SEVERITY_HINT = "hint"

# 五项交易假设字段（制定时冻结，复议对照原文）
PLAYBOOK_FIELDS = (
    "thesis_cn",
    "invalidation_criteria_cn",
    "drawdown_playbook_cn",
    "take_profit_plan_cn",
    "stop_plan_cn",
)

# armed 阶段必填字段（draft 允许空）
REQUIRED_FOR_ARMED = (*PLAYBOOK_FIELDS, "reason", "valid_until")

# 计划种类。entry=完整入场计划（走 draft->armed->entered）；
# holding_watch=持仓盯盘（已在场内，只监督退出，直接落 entered）。
PLAN_KIND_ENTRY = "entry"
PLAN_KIND_HOLDING_WATCH = "holding_watch"
PLAN_KINDS = (PLAN_KIND_ENTRY, PLAN_KIND_HOLDING_WATCH)

# 计划来源 (Step 3, 决策 2, 2026-08-09). 决定 plan 是怎么来的, 用于审计/筛选/报告.
#   user           = 手动建 (默认, create_plan 不传 source 时落此值)
#   watch_promoted = 由 Step 2 提醒命中带出, 用户确认后落计划
#   agent          = 来自 agent 自动生成 (预留, 当前未启用)
PLAN_SOURCE_USER = "user"
PLAN_SOURCE_WATCH_PROMOTED = "watch_promoted"
PLAN_SOURCE_AGENT = "agent"
PLAN_SOURCES = (PLAN_SOURCE_USER, PLAN_SOURCE_WATCH_PROMOTED, PLAN_SOURCE_AGENT)

#: 持仓盯盘必填的退出预案两项（人类 2026-08-05 决定）：
#: 已在场内不必再论证入场理由，但「什么逻辑退出」必须先写下来，
#: 否则价位到了仍会临场改主意--这正是监督员要拦的。
EXIT_PLAYBOOK_FIELDS = ("take_profit_plan_cn", "stop_plan_cn")

#: 持仓盯盘 armed(entered) 必填：两项退出预案 + 有效期。
#: 触发条件（止盈价/止损价/信号）至少一个非空，由 store 单独校验。
REQUIRED_FOR_HOLDING_WATCH = (*EXIT_PLAYBOOK_FIELDS, "valid_until")


@dataclass(frozen=True, slots=True)
class TradePlan:
    """一条交易计划（当前值）。原始冻结值见 revision_no=0。"""

    plan_id: str
    symbol: str
    module: str                      # A/B/C/D
    direction: str                   # long/short
    entry_rule_id: str | None
    entry_lifecycle_id: str | None
    entry_trigger_cn: str | None
    entry_price_ref: float | None
    invalidation_price: float | None
    target_b_price: float | None
    target_b_source: str | None
    reward_risk_at_plan: float | None
    valid_until: str                 # ISO 日期；draft 允许空串
    state: str
    ruleset_version: str
    reason: str                      # draft 允许空串
    thesis_cn: str = ""
    invalidation_criteria_cn: str = ""
    drawdown_playbook_cn: str = ""
    take_profit_plan_cn: str = ""
    stop_plan_cn: str = ""
    entered_on: str | None = None
    exited_on: str | None = None
    exit_reason_rule_id: str | None = None
    superseded_by: str | None = None
    #: entry=完整入场计划；holding_watch=持仓盯盘（只监督退出）
    plan_kind: str = PLAN_KIND_ENTRY
    #: 持仓盯盘的退出触发价位。止盈=达到即提醒；止损=击穿即提醒。
    #: 方向感知：long 时 close>=take_profit / close<=stop；short 反向。
    take_profit_price: float | None = None
    stop_price: float | None = None
    #: 信号型退出触发：这些 rule_id 出现在当日 new_events 即提醒（如灰转绿/转黑）。
    #: 存储为逗号分隔字符串，模型侧暴露为 tuple。
    watch_signal_rule_ids: tuple[str, ...] = ()
    #: 计划来源 (Step 3). user=手动, watch_promoted=来自提醒, agent=预留.
    source: str = PLAN_SOURCE_USER
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True, slots=True)
class PlanRevision:
    """append-only 修订记录。revision_no=0 为创建快照。"""

    revision_id: str
    plan_id: str
    revision_no: int
    changed_field: str               # __snapshot__ / invalidation_price / thesis_cn ...
    old_value: str | None
    new_value: str | None
    verdict: str                     # within_playbook/needs_review/confirmed_override/__snapshot__
    verdict_reason_cn: str | None
    changed_at: str
    changed_by: str                  # user/system


@dataclass(frozen=True, slots=True)
class PlanAlert:
    """监督判定输出。强制带溯源 + 两层 provenance + actionable_from。

    actionable_from 由判定层算（next_trading_day），LLM 永不推算日期（红线 1）。
    """

    code: str
    severity: str                    # block/remind/hint
    rule_id: str | None              # 必须能被 get_rule() 命中（溯源闭环）
    evidence: dict[str, Any] = field(default_factory=dict)
    principle_source: str | None = None    # 原文出处，如「规格 §14 原文」
    logic_provenance: str = "research_proxy"
    caveat_cn: str = ""
    actionable_from: str = ""        # ISO 日期，严格晚于 data_as_of
    data_as_of: str = ""             # ISO 日期 = last_bar_date
    next_step_cn: str = ""
    action_kind: str | None = None   # ENTER/EXIT/REVIEW 产待办；CLOSE_ENTER 关闭 ENTER；None 不产


@dataclass(frozen=True, slots=True)
class ActionItem:
    """待办。催办计数是有意的监督信息。"""

    action_id: str
    plan_id: str
    kind: str                        # ENTER/EXIT/REVIEW
    source_alert_code: str
    state: str                       # open/done/deferred/expired
    due_from: str | None
    nag_count: int = 0
    last_nagged_bar_date: str | None = None
    resume_on: str | None = None     # 推迟复活谓词 JSON
    closed_on: str | None = None
    close_kind: str | None = None
    created_at: str = ""


@dataclass(frozen=True, slots=True)
class Annotation:
    """原因注解（append-only）：推迟/放宽/收紧/复议/事后补充。"""

    annotation_id: str
    plan_id: str
    ref_kind: str                    # revision/action
    ref_id: str | None
    kind: str
    reason_cn: str
    created_at: str
    author: str                      # user/system/agent


#: 推迟复活谓词两种形态（决策 4c）：
#:   {"rule_id": "..."} -- 该 rule_id 事件出现在当日 new_events 时复活
#:   {"field": "close", "op": ">=", "ref": "ema20"} -- DTO 内点路径比较
ResumePredicate = dict[str, Any]


__all__ = [
    "ActionItem",
    "Annotation",
    "EXIT_PLAYBOOK_FIELDS",
    "PLAN_ABANDONED",
    "PLAN_ARMED",
    "PLAN_DRAFT",
    "PLAN_ENTERED",
    "PLAN_EXITED",
    "PLAN_INVALIDATED",
    "PLAN_KIND_ENTRY",
    "PLAN_KIND_HOLDING_WATCH",
    "PLAN_KINDS",
    "PLAN_SOURCES",
    "PLAN_SOURCE_AGENT",
    "PLAN_SOURCE_USER",
    "PLAN_SOURCE_WATCH_PROMOTED",
    "PLAN_STATES",
    "PLAN_SUPERSEDED",
    "PLAYBOOK_FIELDS",
    "PlanAlert",
    "PlanRevision",
    "REQUIRED_FOR_ARMED",
    "REQUIRED_FOR_HOLDING_WATCH",
    "ResumePredicate",
    "SEVERITY_BLOCK",
    "SEVERITY_HINT",
    "SEVERITY_REMIND",
    "TradePlan",
    "VERDICT_CONFIRMED_OVERRIDE",
    "VERDICT_NEEDS_REVIEW",
    "VERDICT_SNAPSHOT",
    "VERDICT_WITHIN_PLAYBOOK",
]
