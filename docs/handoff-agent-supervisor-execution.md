# LEI 监督员 v1 · 实现交接 prompt

> 本文件自包含。接手 AI 无需任何对话上下文。
> **先读这份**，再读两份规格（顺序固定）：
> 1. `docs/plan-agent-supervisor-v1.md` - 功能定稿（架构 + 数据模型 + 红线机制 + 验收），10 项决策已冻结，**不得再改设计**
> 2. `docs/plan-agent-supervisor-v1-execution.md` - 执行计划（6 相位 + 门禁 + 里程碑）
>
> **你的任务**：按执行计划 P0→P5 实现。规格已由人类确认，你不是来重新设计的，是来忠实实现的。遇到设计有歧义，停下来问，不要擅自补造。

## 0. 你的角色

实现者。系统已有一个确定性规则引擎（YAML 规则账本 + 前向状态机 + 回测 + API + React），你要在其之上加一层**计划台账 + 监督判定 + 催办**，外加一个 Claude Code skill 作表达层。

**最关键的一句话**：判定权在 Python，不在 LLM。P0–P3 全程零 LLM 调用；P4 LLM 只负责把 alert 讲成人话，且输出过白名单校验，两次失败降级为模板直出。你写的是确定性代码，不是 prompt 工程。

## 1. 铁律（任何相位都不得突破）

1. **无未来泄漏**：`PlanAlert.actionable_from` = `next_trading_day(last_bar_date)`，由代码算，LLM 永远不推算日期。
2. **research_proxy 两层标注**：每条 alert 带 `principle_source`（如「规格 §14 原文」/「规格 §13 第 4 条」）+ `logic_provenance=research_proxy` + caveat 说明代理了什么。规格 §14 是裸句（无【原系统原则】/【回测代理】标记），「盈亏比小于 3」出自规格 §13 第 4 条原文--两者都是「原则有出处、可执行判定是我们造的」，必须分两层。
3. **不擅自优化参数**：阈值一律 `get_rule(rule_id).params` 读取，`monitor.py` / `drift.py` 源码不得出现裸数值阈值。`valid_until` / `resume_on` 逐计划自填，**不引入全局参数 N**（这是绕开红线 3 的刻意设计）。
4. **模块分别统计**：`plan.module` 单值；跨模块 / 跨趋势跟随↔逆势反转改入场理由 -> 一律 `needs_review`。
5. **执行域禁用符号 gate 持续通过**：`tests/integration/test_acceptance_gates.py::test_no_trading_execution_surface_exists` 扫描 `place_order / submit_order / AccountState / FundID / ProxyID / StrategyEngine / CandidateIntent / AggregateResolver / position_size`。新增代码不得引入这些符号，**且不得出现数量/金额/成交价/账户字段**--计划台账只记状态机 + 价位。
6. **append-only**：`trade_plan_revisions` 与 `plan_annotations` 只追加，`revision_no=0` 的失效价与五项预案原文任何修订后逐字不变。
7. **判定权在 Python**：漂移看方向分类器（收紧放行 / 放宽进复议），**不解析预案文本**；五项预案只在复议时作对照原文摆出来。R/R<3 **永不拦截，只 hint**（决策 3）。

## 2. 已验证的环境事实（直接用，不要重新发现）

- **项目**：`/Users/yongbiaoli/Desktop/lei-signal-lab`，分支 `recovery/lei-round2`，ruleset `1.3.0`。
- **测试**：`/opt/homebrew/bin/python3 -m pytest -q`
- **Lint / 类型**：`ruff check src` ；`mypy src`
- **迁移**：`src/lei_signal/storage/sqlite_store.py` 的 `MIGRATIONS` 元组（约 `:26`），当前最大 `009_market_context_append_only`。追加 `010_trade_plans`（四张表）。迁移 runner 在 `:448`。
- **DB**：`src/lei_signal/api/config.py:57` 读 `LEI_SQLITE_PATH`（默认 `lab.db`），WAL 已开（`sqlite_store.py:402-407`）。launchd 脚本与 API 并发读写安全。
- **store / 路由范式（照抄）**：`src/lei_signal/api/watchlist.py`（frozen dataclass + slots + sqlite CRUD，迁移 7/8 就是它的表）。路由范式 `src/lei_signal/api/routes/watchlist.py`，挂载点 `src/lei_signal/api/app.py:41-43`。
- **交易日历**：`src/lei_signal/data/calendar.py` - `TradingCalendar` Protocol + `WeekdayCalendar` + `DEFAULT_TRADING_CALENDAR`。**默认无节假日表**（刻意的保守选择，别往里塞节假日）。追加 `next_trading_day(day)` 到 Protocol + 实现。
- **DTO**：`src/lei_signal/api/schemas.py`。要读的：`SymbolDetailDTO`(:472) / `AssessmentDTO`(:428) / `TradabilityDTO`(:412) / `ExitSignalDTO`(:378) / `TradeOpportunityDTO`(:347) / `PullbackOpportunityDTO`(:317)。
- **规则读取**：`get_rule(rule_id)` 在 `src/lei_signal/domain/rules_config.py:68`。所有阈值从这里读。
- **既有确定性函数（只读消费，不重算）**：
  - `analyze(symbol)` / `analyze_bars(...)` - `src/lei_signal/compose/pipeline.py:128`
  - `_detail_dto` - `src/lei_signal/api/routes/symbols.py`
  - `compute_reward_risk` - `src/lei_signal/rules/reward_risk_filter.py:120`（`rr_min_ideal=3` 在 `configs/rules.v1.yaml:416`，provenance `research_proxy`）
  - `evaluate_tradability` - `src/lei_signal/rules/tradability_gate.py:204`
  - `make_event_id` - `src/lei_signal/domain/canonical.py:151`
- **最佳规则参考实现**：`src/lei_signal/rules/first_ma_pullback.py`（代码风格、provenance 写法照它）。
- **fixture**：`tests/*.bars.parquet` - `000001.SS`（趋势可交易）、`000300.SS` / `510300.SS`（趋势不明阻断）。P1 truth table 与 P5 真实数据验证用这些。
- **LLM 运行时**：火山引擎 ark（非 DeepSeek），通过 gitignored `.env` / `.env.local`。**P0–P3 完全不碰 LLM。**

## 3. 执行顺序与门禁

严格按 P0→P5。**前一相位门禁（pytest + ruff + mypy）不绿，不进下一个相位。** 每相位单独 commit。

### P0 地基与数据模型
migration `010_trade_plans`（四表）+ `plans/models.py` + `plans/store.py` + `calendar.next_trading_day`。
门禁：migration 在空库与已有 009 的库都干净 apply；store 往返；必填校验（五项预案 + `reason` + `valid_until`，draft 允许空、armed 必填）；`revision_no=0` 修订后不变；`next_trading_day` 跨周末正确。

### P1 监督判定（纯函数，无 IO 无 LLM）
`plans/monitor.py::evaluate_plan(plan, dto) -> list[PlanAlert]`，12 个 alert code。`actionable_from` 走日历。R/R 只 hint。附 `evaluate_resume(predicate, dto)`（P2 复用）。
门禁：每个 alert code 一正一反 truth table；溯源闭环（每条 `rule_id` 能被 `get_rule()` 命中）；红线 1（`actionable_from > data_as_of`）；幂等；两层标注；`monitor.py` 无裸数值。

### P2 待办与催办
`plans/actions.py` 状态机 + `scripts/daily_nag.py` + `scripts/com.lei.supervisor.plist`。催办节拍绑 `last_bar_date` 前进；`DATA_STALE` 不递增 `nag_count`；`deferred` 经 `resume_on` 信号复活。
门禁：nag 幂等；`DATA_STALE` 不催；信号复活（满足回 `open` + `ACTION_RESUMED`，不满足保持 `deferred`，引用不存在的 rule_id/字段要拒绝并报清单）；`superseded` 自动关 + annotation；`valid_until` 到期产 `REVIEW` 但**不改 plan 状态**；`daily_nag` fixture dry-run 产出正确。

### P3 漂移复议（可与 P2 并行）
`plans/drift.py::check_revision(plan, changes) -> Verdict`。方向分类器 + 硬规则。`needs_review` 时摆 `revision_no=0` 冻结预案作对照（不解析）。结论写 `plan_annotations`。
门禁：收紧 -> `within_playbook`；放宽 / entered 后换入场理由 / 跨模块 / 改 `thesis_cn`/`invalidation_criteria_cn` -> `needs_review`；`revision_no=0` 不变；annotation append-only。

### P4 表达层与 skill
`plans/grounding.py`（`verify_grounding` 白名单 + 禁用词表）+ `api/routes/plans.py` + `api/schemas.py` 追加 DTO + `app.py` 挂载 + `.claude/skills/lei-supervisor/`（SKILL.md + plan_cli.py）。降级模板渲染。
门禁：`verify_grounding` 拒绝超集 `rule_id`；禁用词命中拒绝；两层标注渲染；两次失败降级模板不抛异常；端到端（建 draft -> armed -> alert -> 待办 -> 讲解）溯源可校验。

### P5 集成与门禁
全量 `pytest -q` / `ruff check src` / `mypy src` 绿；`test_no_trading_execution_surface_exists` 过；真实数据验证（000001.SS 建计划跑 alert 看催办，非退化）；更新规格文档状态。

## 4. 工作纪律

- **TDD for 判定层**：P1 / P3 先写 truth table 测试（反例比正例重要），再写实现。
- **照抄既有范式**：store 抄 `api/watchlist.py`，规则风格抄 `first_ma_pullback.py`，路由抄 `routes/watchlist.py`。别发明新风格。
- **只追加，不改既有行为**：`rules/` / `compose/pipeline.py` / `market_context/` / `web/`（前端）**一个字都不改**。`sqlite_store.py` / `schemas.py` / `app.py` / `calendar.py` / `rules.v1.yaml` 只追加。
- **每相位 commit**，commit message 写清相位与门禁结果。
- **遇到歧义停下来问**，不要擅自补造参数 / 补造规则 / 改设计。规格 §17 类参数决策点尤其要停。

## 5. 不要做的事

- 不下单、不接券商、不记股数/金额/成交价/账户。
- 不从行情探测买卖点（只消费 `analyze` / `_detail_dto` 既有输出）。
- 不调参（阈值走 `get_rule`）。
- 不输出买/卖指令、不输出总分。
- 不接微信/邮件（v2）。
- 不接 B/C 模块（未实现；`module` 填 B/C 时 monitor 回「该模块规则未实现，无法监督」，不猜）。
- P0–P3 不碰 LLM。
- 不碰前端。

## 6. 开工

从 P0 开始。每相位完成、门禁绿、commit 后，简报：做了什么 / 门禁结果 / 下一相位。门禁红了就停在红的地方报错，不要带着失败的测试往下走。
