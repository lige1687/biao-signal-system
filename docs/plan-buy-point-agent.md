# 买点分析 agent + 一键扫描自选 + 对话内落计划

## 目标（人类 2026-08-05）

现有链路是**被动**的：有计划才监督。缺的是**主动**：我指一个标的（或一键扫全部自选），
agent 用 LEI 系统判定「当前买点如何 / 图什么信号进 / 止损设哪 / 盈亏比多少」，
谈妥后**在对话里直接落计划**。没有买点时说明「到什么情况才算」，并能把这个条件
交给系统跟踪。

已定决策：
- 判定拼装放**后端端点**，skill 与 Web 抽屉共用同一端点（结论必然一致）。
- **同时做批量扫描**（一键扫全部自选）。

## 关键前提（已勘察确认）

判定素材**全部已存在**，Python 已算好，agent 不需要自行判断买卖点：
- `ConditionalScenarioDTO`：`satisfied_conditions` / `missing_conditions` /
  `key_price` / `invalidation_cn` / `reward_risk_ratio` / `reward_risk_computable` /
  `next_step_cn` / `caveat_cn`
- `TradabilityDTO`：`trend_type` + 9 条无交易条件 + `blocking_reasons`
- `TradeOpportunityDTO` / `PullbackOpportunityDTO`：分层机会 + B1 + R/R
- `AnalysisService.get_many`：并发批量取数（批量扫描直接用）
- `_assessment_dto()`：路由已有的拼装函数，复用可避免与看盘界面分叉

因此本期**不新增任何判定逻辑**，只做「汇总既有判定 + 讲解 + 落计划」。

## 红线（全程遵守）

1. **判定权在 Python**：端点只汇总既有 DTO 字段，不新增买点判断、不算新数值。
2. **LLM 只讲解**：输出过 `verify_grounding`（禁用词 + rule_id 白名单），失败降级模板。
3. **不擅自建计划**：agent 只能提议，落库必须人类明确确认（复用既有 create+confirm）。
4. **research_proxy 标注**：场景/可交易性均为研究代理，讲解必须带标注。
5. 不下单、不记数量/金额/账户。

---

## 后端

### B1. 买点审阅端点 `GET /api/symbols/{symbol}/buy-point-review`
新文件 `src/lei_signal/api/routes/opportunities.py`（挂 app）。

Python 侧汇总（**无新判定**）：
- 取 `analysis_service.get(symbol)` -> `_assessment_dto(result)`
- 汇总为 `BuyPointReviewDTO`：
  - `verdict`：`actionable`（有 confirmed 机会且 tradable）/
    `blocked`（有机会但 tradability 阻断）/ `waiting`（只有 watch 机会）/
    `none`（无机会）。**由字段组合派生，不是新判定**
  - `tradability`：直接给 TradabilityDTO
  - `candidates`：list of 每个机会的 `{scenario_cn, rule_id, lifecycle_id, module,
    direction, state, satisfied_conditions, missing_conditions, key_price,
    invalidation_price(=invalidation_cn 对应价), reward_risk_ratio,
    reward_risk_computable, reward_risk_target, next_step_cn, caveat_cn}`
  - `suggested_plan`：**仅当 verdict=actionable** 时给出可直接落计划的预填
    （module/direction/entry_rule_id/entry_lifecycle_id/invalidation_price/
    target_b_price/reward_risk_at_plan）。五项预案留空--必须人写
  - `watch_conditions`：verdict 为 waiting/none 时，把 `missing_conditions` +
    `key_price` 整理成「到什么情况才算买点」，并给出**可跟踪化**的建议：
    `{as_signal_rule_ids: [...], as_resume_predicate: {...}}`（复用既有
    holding_watch 的 watch_signal_rule_ids 与 resume_on 谓词形态）

### B2. 批量扫描端点 `GET /api/opportunities/scan`
- 参数：`symbols`（逗号分隔，缺省取 watchlist 全部）、`state`（默认只回
  有机会的）、`refresh`
- 用 `analysis_service.get_many` 并发；每标的复用 B1 的汇总函数
- 返回 `ScanResponse{generated_at, items: [ScanItemDTO], errors: {...}}`
  - `ScanItemDTO`：`{symbol, display_name, verdict, best_candidate(精简),
    has_active_plan(查 plans 库), reward_risk_ratio, blocking_reasons}`
  - `has_active_plan` 让"已建计划的不用再提"，直接回答你的"哪些还没建计划"
- 单标的失败不影响整体（每标的 error 隔离，照 dashboard 既有做法）

### B3. 买点分析问答 `POST /api/symbols/{symbol}/buy-point-chat`
- 复用 `routes/agent.py` 的模式：Python 给 review 结果，LLM 只讲解
- `llm.py` 新增 `build_buy_point_payload(review)`（裁剪上下文，只喂 review
  的确定性字段）+ 复用 `chat_ark`
- 新增 `BUY_POINT_SYSTEM_PROMPT`：在既有铁律外，明确要求
  「不得自行判断买点，只解释 candidates 里给定的 satisfied/missing/R-R；
    禁止推荐买入；止损只能引 invalidation_price；盈亏比只能照抄 ratio」
- 输出过 `verify_grounding`（rule_id 白名单 = review 内出现的 rule_id），
  两次失败降级模板（模板直出 review 的结构化文本）

### B4. 测试
- `tests/unit/test_buy_point_review.py`：verdict 四态派生正确；tradability
  阻断时不给 suggested_plan；无机会时给 watch_conditions；R/R 不可计算时
  不编数值
- `tests/unit/test_opportunities_scan.py`：批量并发、单标的失败隔离、
  has_active_plan 正确、watchlist 缺省
- `tests/unit/test_buy_point_chat.py`：接地通过 / 禁用词降级 / 伪造 rule_id
  降级 / 无凭据降级（mock ark，不打真实 API）

---

## skill 侧（对话内闭环）

### S1. `plan_cli.py` 新增命令
- `review <symbol>` -> GET buy-point-review
- `scan [--symbols ...]` -> GET opportunities/scan
- `create-holding-watch ...` -> POST plans/holding-watch（补上，当前缺）
- 已有 `create` / `confirm` 直接复用于"对话里落计划"

### S2. SKILL.md 扩展（关键：铁律 1 需精确改写，不是放开）
现铁律 1 写「只读 plans 输出，不得从行情自行判断买卖点」。改为：

> 1. **只读确定性输出，不探测**：你消费 `plan_cli` 取回的 alert / 待办 / 计划 /
>    **买点审阅（review/scan）**。买点结论必须来自 review 的 `candidates`
>    字段（satisfied/missing/key_price/reward_risk），**不得自行从行情判断买点**，
>    不得推算 review 未给出的价位或盈亏比。

新增工作流「买点分析 -> 协商落计划」：
1. `plan_cli review <symbol>`
2. 按 verdict 分支讲解：
   - `actionable`：摆出 图什么信号进（entry_rule_id + satisfied_conditions）、
     止损（invalidation_price，引 invalidation_cn）、盈亏比（照抄 ratio，
     不可计算就说不可计算）、可交易性
   - `blocked`：先讲阻断（规格 §13），明确按规则不开新仓
   - `waiting` / `none`：讲「到什么情况才算」（missing_conditions + key_price），
     并提议把它变成跟踪（见 3b）
3. 协商落计划：
   a. actionable -> 逐项问五项预案 -> `plan_cli create` + `confirm`
      （**预填只用 suggested_plan 给的值**，不自己算）
   b. waiting/none -> 提议建**持仓盯盘式跟踪**或 armed 计划，把
      `watch_conditions.as_signal_rule_ids` 作为盯盘信号，系统自动跟踪
4. 落库前必须人类明确确认（沿用既有纪律）

---

## Web 侧（可选，与 skill 等价入口）

### W1. 标的详情/看盘页 header 加「买点分析」按钮
- 开 `BuyPointDrawer`（复用 AgentDrawer 的抽屉样式）
- 打开即 `buyPointReview(symbol)` 展示结构化审阅（verdict 徽章 + candidates +
  阻断原因 + R/R + 「到什么情况才算」）
- 底部可提问（走 buy-point-chat），显示接地/降级标记
- 有 `suggested_plan` 时给「据此建计划」按钮 -> 打开 CreatePlanDialog 并预填

### W2. `/plans` 页加「扫描自选」区
- 调 `opportunities/scan`，表格列出：标的 / verdict / 最佳机会 / R/R /
  是否已有计划 / 「建计划」按钮
- 默认折叠，点开才扫（避免每次进页面就并发拉全部自选）

### W3. types + api client
`BuyPointReview` / `ScanItem` / `buyPointReview` / `opportunityScan` /
`buyPointChat`。

---

## 交付顺序

1. **B1 review 端点 + 测试**（核心，skill/Web 都依赖）
2. **B2 scan 端点 + 测试**
3. **B3 chat 端点 + 测试**
4. **S1/S2 skill**（对话闭环即可用，先于 Web 交付）
5. **W1–W3 Web**（等价入口）

## 验收门禁

- `pytest -q` 全绿、`ruff check src`、`mypy src`
- `cd web && npm run build`
- 交易执行禁区 15/15，无数量/金额/账户字段
- 端到端实测：review 四态 / scan 批量 / chat 接地与降级
- 红线抽查：LLM 输出含「买入」必降级；review 不含 DTO 之外的新数值

## 不做（本期）

- 不新增任何买点判定规则（B/C/A/D 已实现的机会即全部来源）
- 不做自动建计划（必须人类确认）
- chat 不做流式
- 不做「无计划标的自动日推」（上一轮讨论的 Tier2 汇总，与本期主动分析正交，
  可下一轮）
