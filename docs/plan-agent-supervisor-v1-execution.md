# LEI AI 监督员 v1 · 执行计划

> 上游规格：`docs/plan-agent-supervisor-v1.md`（功能定稿，10 项决策已冻结）。
> 本文是**实现顺序**：分 6 个相位，每相位有交付物、测试、门禁。前一相位门禁不绿不进下一个。
> 计划经人类确认后才实现。

## 0. 实现原则

1. **判定层先行，表达层最后。** P0–P3 全是纯 Python，无 LLM，可完全测试。P4 才碰 ark。LLM 集成风险最高，放最后，前面地基已稳。
2. **每相位可独立测试、可独立 review。** 不留半成品跨相位。
3. **不碰既有确定性层。** 只追加 `plans/` 包 + migration + 路由，不改 `rules/`、`compose/`、前端。
4. **执行域禁用符号 gate 持续在线。** 每个 PR 跑 `test_no_trading_execution_surface_exists`，新增 schema 不得出现数量/金额字段。

依赖关系：

```
P0 地基 ──▶ P1 monitor ──▶ P2 actions/催办 ──┐
   │                          (evaluate_resume)  ├─▶ P4 表达层/skill ──▶ P5 集成门禁
   └────────▶ P3 drift ────────────────────────┘
```

P3 可与 P2 并行（都只依赖 P0 的 models/store）；P4 汇聚所有判定层后做。

---

## P0 · 地基与数据模型

**目标**：四张表能存能取，必填校验生效，交易日历能推下一天。

**交付物**
- `src/lei_signal/storage/sqlite_store.py` 追加 migration `010_trade_plans`（`trade_plans` / `trade_plan_revisions` / `plan_action_items` / `plan_annotations` 四表，照迁移 7/8 watchlist 的写法）。
- `src/lei_signal/plans/models.py`：`TradePlan` / `PlanRevision` / `PlanAlert` / `ActionItem` / `Annotation` / `ResumePredicate` dataclass（frozen, slots，对齐 `domain/types.py` 风格）。
- `src/lei_signal/plans/store.py`：CRUD + append-only 修订 + 必填校验，照 `api/watchlist.py` 的 connection 模式。
- `src/lei_signal/data/calendar.py`：`TradingCalendar` Protocol 追加 `next_trading_day(day)`；`WeekdayCalendar` 实现。

**测试**
- migration 在空库与已有 009 的库上都能干净 apply。
- store 往返：建 draft -> 确认 armed -> 追加 revision -> 读回字段全对。
- 必填校验：`thesis_cn` / `invalidation_criteria_cn` / `drawdown_playbook_cn` / `take_profit_plan_cn` / `stop_plan_cn` / `reason` / `valid_until` 任一为空 -> 拒绝落库（draft 阶段允许空，armed 必须全填）。
- append-only：任意修订后 `revision_no=0` 的 `invalidation_price` 与五项预案原文逐字不变。
- `next_trading_day(周五)` = 下周一；跨节假日注入集合后正确跳过。

**门禁**：`pytest -q` 新增测试全绿；`ruff`/`mypy` 过。

---

## P1 · 监督判定（纯函数，无 LLM）

**目标**：给定 `plan + SymbolDetailDTO`，确定性产出 `list[PlanAlert]`。这是整个监督员最有价值的地基。

**交付物**
- `src/lei_signal/plans/monitor.py`：`evaluate_plan(plan, dto) -> list[PlanAlert]`，无 IO。
- 12 个 alert code（规格 §6 表）：每个读 DTO 的明确字段，带 `rule_id` + `evidence` + 两层 provenance + `actionable_from`。
- `actionable_from` = `next_trading_day(last_bar_date)`（红线 1，代码算，LLM 不碰）。
- R/R 阈值读 `get_rule("reward_risk_filter").params.rr_min_ideal`，只 hint 不拦（决策 3）。
- `evaluate_resume(predicate, dto) -> bool`：验 `resume_on` 谓词，P2 复用。纯函数。

**测试（truth table，每 code 至少一正一反）**
- `ENTRY_CONDITIONS_MET`：armed + `current_conditions_confirmed=True` -> 触发；False -> 不触发。
- `ENTRY_BLOCKED_BY_TRADABILITY`：`tradability.tradable=False` -> block + 列 `blocking_reasons`。
- `INVALIDATION_BREACHED`：close 击穿 `invalidation_price` -> block；未击穿 -> 不触发。
- `EXIT_TRIGGERED`：entered + 匹配 `exit_signals` active -> remind；armed -> 不触发。
- `PLAN_EXPIRING` / `PLAN_STALE_RULESET` / `PLAN_ORPHANED` / `MODULE_NOT_IMPLEMENTED` / `DATA_STALE` 各正反例。
- 溯源闭环：每条 alert 的 `rule_id` 能被 `get_rule()` 命中，否则 fail。
- 红线 1：`actionable_from > data_as_of` 严格成立。
- 幂等：同 plan+dto 重复调用，alert 列表逐字段相等。
- 两层标注：research_proxy 判定的 alert 同时带 `principle_source`（如「规格 §14 原文」）与 `logic_provenance=research_proxy` + caveat。

**门禁**：全绿，且 `monitor.py` 源码扫描无裸数值阈值（红线 3）。

---

## P2 · 待办与催办

**目标**：监督员会追着你要结果，直到你给结论。launchd 每日跑，通知到桌面。

**交付物**
- `src/lei_signal/plans/actions.py`：待办状态机。`open`/`done`/`deferred`/`expired`；`superseded` 自动关；`valid_until` 到期产 `REVIEW`（决策 6，不改 plan 状态）。
- 催办节拍绑 `last_bar_date` 前进：未前进整体 skip；`DATA_STALE` 不递增 `nag_count`。
- `deferred` 复活：复用 `monitor.evaluate_resume`，满足 -> `open` + `ACTION_RESUMED`（决策 4c）。
- `scripts/daily_nag.py`：launchd 入口。跑 `analyze` -> `evaluate_plan` -> 更新待办 -> 投递。
- `scripts/com.lei.supervisor.plist`：launchd 配置（每交易日收盘后触发；触发时刻是运行配置非交易参数）。
- macOS 通知投递（`terminal-notifier` 或 `osascript`）。

**测试**
- nag 幂等：`last_bar_date` 不变 -> `nag_count` 不变。
- `DATA_STALE` -> 不递增 `nag_count`。
- 信号复活：`resume_on={close>=ema20}` 满足 -> `open` + `ACTION_RESUMED`；不满足 -> 保持 `deferred`。
- `resume_on` 引用不存在的 rule_id/字段 -> 拒绝并报可引用清单。
- superseded：同标的同向第二条转 `entered` -> 第一条 `superseded` + annotation（决策 5）。
- `valid_until` 到期 -> `REVIEW` 待办，plan 状态**不**变（决策 6）。
- `daily_nag` 在 fixture 上 dry-run -> 产出的待办清单与预期一致。

**门禁**：plist 安装 + dry-run 真能弹通知；测试全绿。

---

## P3 · 漂移复议

**目标**：拦下落在预案之外的临时改主意。可与 P2 并行。

**交付物**
- `src/lei_signal/plans/drift.py`：`check_revision(plan, changes) -> Verdict`。
- 方向分类器（确定性）：多头下移失效价/空头上移 = 放宽 -> `needs_review`；反向 = 收紧 -> `within_playbook`（决策 1）。
- 硬规则（不分方向一律 `needs_review`）：entered 后换 `entry_rule_id`（§14）、换 module/跨趋势跟随↔逆势反转（§12）、改 `thesis_cn`/`invalidation_criteria_cn`。
- `needs_review` 时摆出 `revision_no=0` 的冻结五项预案作对照原文（不解析）。
- 复议结论 + 原因写 `plan_annotations`（append-only）。

**测试**
- 收紧（多头上移失效价）-> `within_playbook`，放行。
- 放宽（多头下移失效价）-> `needs_review`。
- entered 后换入场理由 -> `needs_review`。
- 跨模块改理由 -> `needs_review`。
- 改 `thesis_cn` -> `needs_review`。
- `revision_no=0` 任何修订后不变。
- annotation append-only，不覆盖。

**门禁**：drift truth table 全绿。

---

## P4 · 表达层与 skill

**目标**：能聊天建计划，能把 alert 讲成人话，且讲不错。LLM 最低风险接入。

**交付物**
- `src/lei_signal/plans/grounding.py`：`verify_grounding(text, alerts) -> bool` + 禁用词表（买入/卖出/建议买/该买/加仓/减仓/抄底）。
- `src/lei_signal/api/routes/plans.py`：CRUD + `GET /api/plans/alerts` + `GET/POST /api/plans/actions`。
- `src/lei_signal/api/schemas.py` 追加 `PlanDTO` / `PlanAlertDTO` / `ActionItemDTO` / `RevisionRequest`；`app.py` `include_router`。
- `.claude/skills/lei-supervisor/SKILL.md`：指令只渲染 alert、禁买卖词、参数决策点停下、建计划时五项预案逐项问、agent 建议只能引 DTO 已有数值。
- `.claude/skills/lei-supervisor/scripts/plan_cli.py`：HTTP 客户端调 `/api/plans*`，失败回退直连 store 模块（不写两套逻辑）。
- 降级模板渲染：LLM 两次过不了 `verify_grounding` -> 固定模板直出 alert。

**测试**
- `verify_grounding` 拒绝引用了不存在 rule_id 的伪造输出（超集即拒）。
- 禁用词命中即拒。
- 两层标注：research_proxy alert 的渲染结果同时含原文出处与「判定方式为研究代理」。
- 降级路径：两次失败 -> 模板直出，不抛异常。
- 端到端：对话建 draft -> 确认 armed -> 跑 alert -> 产待办 -> skill 讲解，全程溯源标签可校验。

**门禁**：`ruff`/`mypy` 过；skill 端到端跑通。

---

## P5 · 集成与门禁

**目标**：全量门禁绿，真实数据验证，文档定稿。

- `pytest -q`、`ruff check src`、`mypy src` 全绿。
- `test_no_trading_execution_surface_exists` 确认通过：无禁用符号，新增 schema 无数量/金额字段。
- 真实数据验证：在已验证 fixture 标的（000001.SS 趋势可交易、000300/510300 阻断）上建计划、跑 alert、看催办，非退化。
- 更新 `docs/plan-agent-supervisor-v1.md` 状态为已实现，补实际文件路径。

---

## 里程碑

| 里程碑 | 完成相位 | 价值 |
|---|---|---|
| **M1** | P1 | 确定性监督可跑：给定 plan+dto 出 alert，全测试绿。最高价值地基，到这里系统已经「会看」 |
| **M2** | P2 | 能催办：launchd 每日跑，通知到桌面。到这里系统「会追」 |
| **M3** | P3 | 能拦漂移：临时改主意被拦下复议。到这里系统「会管」 |
| **M4** | P4 | 能聊天建计划 + 讲解。完整 v1 |

M1 之后即可单独验证核心价值；M2–M3 可并行推进。

---

## 风险与对策（按相位）

| 相位 | 风险 | 对策 |
|---|---|---|
| P1 | truth table 漏边界 -> 判定错 | 每 code 一正一反是硬门禁；反例比正例重要 |
| P1 | `actionable_from` 跨节假日不准 | 诚实标「最早可执行日（未扣节假日）」；v2 注入节假日表消除 |
| P2 | launchd 在睡眠/关机时不跑 | 通知是 best-effort；下次唤醒 `last_bar_date` 前进会补算待办，不丢 |
| P2 | 催办疲劳 | 只在数据前进催；`DATA_STALE` 不催；推迟必填原因的摩擦筛真假推迟 |
| P3 | 方向分类器遇双向/对冲计划歧义 | v1 只做单向计划（long/short 互斥）；双向留 v2 |
| P4 | LLM 编 rule_id/数值 | `verify_grounding` 白名单；两次失败降级模板；判定权本就不在 LLM |
| P4 | agent 建议变成探测 | SKILL 指令限定建议只能引 DTO 已有数值，不许算新数 |

---

## 开工前待办（非决策，是活儿）

1. `terminal-notifier` 是否已装；未装则 `brew install terminal-notifier` 或退到 `osascript`。
2. `LEI_SQLITE_PATH` 确认（默认 `lab.db`，已开 WAL，launchd 与 API 并发读写安全）。
3. launchd 触发时刻定为收盘后（如 15:30），实际用起来再调。
