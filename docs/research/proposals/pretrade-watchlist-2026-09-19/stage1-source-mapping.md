# Stage 1 关注区块 · 字段来源映射表（前置任务1，2026-09-19）

依据：GPT-6 Pro 冻结要求「模块、字段或规则ID、适用标的、数据时点、版本」。
本表逐项列出关注区块每个展示字段的来源；聚合层只引用，不新增裁决。

| 展示字段 | 来源模块/函数 | 规则锚点 | 数据时点 | 备注 |
|---|---|---|---|---|
| symbol 范围 | api/watchlist.py::list_watchlist | 用户自选 | 实时读库 | 扫描范围=自选 |
| display_name | service 结果 display_name | — | as_of | |
| as_of（数据时点） | BuyPointReviewDTO.as_of | — | 预计算批次时间 | 区块必显 |
| verdict/verdict_cn | opportunities.py::build_review 派生 | 非新判定：confirmed+可交易→actionable；§13阻断→blocked；仅watch→waiting | as_of | docstring 自证「字段组合派生」 |
| best_scenario_cn（为什么关注） | scenario.scenario_id | rules/ 入场模块：first_ma_pullback(A回调)、dense_breakout(B)、two_b_reversal(C 2B)、module_d_false_breakout(D) | as_of | MODULE_MAP 反查 |
| best_state（候选状态） | candidate.state | 机会引擎 lifecycle：watch/confirmed/weakened/invalidated | as_of | 与 verdict 分别展示 |
| 还缺什么条件 | missing_conditions → _watch_conditions() | 规则引擎条件原文照抄 | as_of | price/state 分型不编数字 |
| 条件可跟踪化 | WatchConditionDTO.as_signal_rule_ids | _CONDITION_SIGNAL_HINTS → holding_watch/resume_on 信号 | as_of | 仅提示，不自动建 |
| 失效位 | invalidation_price / invalidation_cn | 场景结构位（C点/密集区下沿等，规则引擎产物） | as_of | 「当前失效可见」限定 |
| 盈亏比 | reward_risk_ratio / computable | rules/reward_risk_filter（阈值 rules.v1.yaml） | as_of | 算不出明说 |
| 阻断原因 | tradability.blocking_reasons | rules/tradability_gate（规格§13九条） | as_of | blocked≠invalidated |
| 已有计划 | has_active_plan / active_plan_ids | trade_plans 存储 | 实时读库 | 直达不重复建 |
| 计划预填 | SuggestedPlanDTO | plans 模块 | as_of | 保存须用户确认 |
| 消息状态位（预留） | 无来源，V1 不接消息 | — | — | 显示「消息维度未接入」 |

## 前置任务2结论：历史状态回查 = 无直接能力

run_opportunity_scan 为实时计算（service.get_many 当前结果），无历史扫描存储表。
按 GPT 冻结规则「历史状态无法回查则阻塞失效可见验收、不准聚合层补判」，Stage 1
验收口径限定为：**当前失效条件可见**（当前 state/invalidation 展示）；跨日失效
追溯明确归 Stage 2 快照，前段 UI 对此显示「跨日变化待后段」而非留白。

## 版本锚点

- 规则账本：configs/rules.v1.yaml（provenance 体系，无 ETF 专用标注——ETF 差异
  按 FROZEN-PLAN 四类映射执行，未规则化项标「ETF差异，尚未规则化」）
- 交易规格：docs/trading-spec-v1.md（§9 入场模块、§10 盈亏比、§13 无交易条件）
