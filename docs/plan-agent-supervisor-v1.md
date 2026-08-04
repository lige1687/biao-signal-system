# LEI AI 监督员 v1 · 功能定稿

> 上游：`docs/handoff-agent-supervisor.md`（交接 prompt）。
> 本文是**功能范围定稿**。交接 prompt §6 的四个待决策点、以及本文早期版本 §9 的六项待确认，均已于 2026-08-04 由人类拍板，结论见第 2 节。
> 状态：**范围已冻结，可进入实现**。

## 1. 与交接 prompt 的差异（先说清楚改了什么）

交接 prompt §6.4 建议 v1 = 监督员 + 讲解员，把「计划制定 + 定时提醒」推到 v2+。**这条被推翻了**，理由：

**没有落库的计划，就没有可监督的对象。**

- 拦「亏损后移动失效价」（规格 §14）需要知道**原来的失效价**。DTO 只有今天算出的客观条件，没有「你当初承诺的那个数」。没有台账，这条红线在 v1 无法执行，只能靠对话上文，翻篇即失忆。
- 「退出触发时提醒该出」需要知道**用户是否在持仓**。`exit_signals` 天天 active/inactive，不知道有没有仓，提醒就是噪音。
- 结果：原 v1 实际是**带监督口吻的讲解员**，不是执行系统。

另外两处改动：

- **判定权从 LLM 手里拿走**。交接 prompt §7.3 打算用 system prompt + 后处理校验溯源标签来强制接地生成——那是在校验 LLM 有没有撒谎。本方案改为让它**没机会撒谎**：所有判定移入确定性层。
- **催办进 v1**。原计划「v1 只判定、投递归 v2」不成立：只有你打开才提醒，就不叫每天提醒。待办状态机 + 本地定时投递进 v1，微信归 v2。

## 2. 已确认决策（2026-08-04）

| # | 议题 | 结论 |
|---|---|---|
| — | v1 范围 | 计划台账 + 触发判定 + **待办催办** + agent 作对话录入与讲解 |
| — | 持仓边界 | 记状态机 + 价位，**不记数量、金额、成交价、账户** |
| — | 载体 | 后端 plan API（进现有 SQLite）+ Claude Code skill 前端 |
| — | 取数（交接 §6.1） | **(b) 实时优先，失败回退 fixture**，回退强制打 `DATA_STALE` |
| 1 | 漂移判定基准 | **Python 只管方向，预案只作对照原文**。收紧（多头上移失效价）自动放行；放宽 / 换入场理由 / 跨模块一律进复议。冻结的五项预案在复议时摆给人和 agent 对照，但 Python 不做语义解析。不看浮亏、不需要成本价 |
| 2 | §14 的 provenance | **两层标注**：原则引原文标「规格 §14 原文」，判定逻辑标 `research_proxy` + caveat。同样适用 rr=3 |
| 3 | R/R<3 口径 | **永不拦截，只提示**。文案「建议 >3，2–3 可接受」 |
| 4 | 进场对账 | **待办状态机 + 每日催办**，直到你标记「做了」或「推迟」 |
| 4b | 催办投递 | **launchd 本地定时 + macOS 通知**；微信归 v2 |
| 4c | 推迟复活 | **信号触发，非定时**。推迟必填 `reason_cn` + `resume_on`（结构化谓词，指向确定性层已算出的条件）。monitor 每次验 DTO，条件满足自动回 `open`。不能指定系统算不出的信号 |
| 5 | 多计划并存 | **armed 可多条；entered 同标的同方向只一条** |
| 6 | 计划时效 | **制定时逐计划自填 `valid_until`**，到期发待办让人结论，不自动关 |

决策 1、4、6 有一条共同的设计哲学，是人类在拍板过程中定的调，后续所有扩展都应遵守：

> **能在制定计划时谈定的，就不要留到运行时去判断。**
> 事前预案写得越具体，事后需要「改计划」的场合越少——这本身就是最强的漂移预防。
> 同理，能逐计划自定的，就不要引入全局参数（顺带绕开红线 3）。

## 3. v1 目标与非目标

**一句话目标**：把用户口头的交易计划变成一条**冻结在库里的记录**（含完整交易假设与预案），每次数据更新时由确定性代码把它和当日 `SymbolDetailDTO` 对照，产出带 `rule_id` 溯源的执行待办、每日催办直到你给出结论，并拦下落在预案之外的临时改主意；LLM 只负责把对话变成计划草案、把提醒讲成人话。

**非目标（v1 明确不做）**：

- 不下单、不接券商、不记股数/金额/成交价/账户——`tests/integration/test_acceptance_gates.py::test_no_trading_execution_surface_exists` 的禁用符号表一个都不碰。
- 不从行情探测买卖点。只消费 `analyze()` / `_detail_dto` 的既有输出。
- 不调参。阈值一律 `get_rule(rule_id).params` 读取，代码不写死。
- 不输出买/卖指令，不输出总分。
- 不接微信/邮件推送（v2）。
- 不接 B/C 模块（尚未实现）。计划的 `module` 允许填 B/C，但 monitor 对它们只回「该模块规则未实现，无法监督」，不猜。

---

## 4. 架构：判定与表达分层

红线守恒全靠这个分层。

```
用户对话
   │
   ▼
┌─────────────────────────── 表达层（LLM / ark）─────────────────────────┐
│  职责一：对话 → PlanDraft（结构化草案）→ 必须人类确认才落库             │
│         过程中可给建议，但建议必须挂 rule_id，不得自由发挥              │
│  职责二：把 PlanAlert[] / ActionItem[] 渲染成人话 + 挂溯源标签          │
│  无判定权：不决定条件是否成立、不决定该不该拦、不决定待办开关            │
└───────────────────────────────────────────────────────────────────────┘
   │ 写入需人类确认                                ▲ 只读
   ▼                                               │
┌────────────────────── 判定层（Python，纯函数，可测）──────────────────┐
│  plans/store.py       计划台账 CRUD + append-only 修订史              │
│  plans/monitor.py     evaluate_plan(plan, dto) -> list[PlanAlert]     │
│  plans/drift.py       复议判定：方向分类器 + 预案原文对照（不语义解析）    │
│  plans/actions.py     待办状态机 + 催办计数                            │
│  plans/grounding.py   LLM 输出白名单校验 + 禁用词                      │
└───────────────────────────────────────────────────────────────────────┘
   │ 只读
   ▼
既有确定性层：analyze() / SymbolDetailDTO / configs/rules.v1.yaml
```

**为什么这样分**：

1. 拦截是 Python 做的，LLM 幻觉绕不过去。用户就算把 agent 聊服了，`drift.py` 照样返回需复议。
2. 验收测试测判定层 truth table（稳定、可断言），不测 LLM 输出（不可重复）。
3. 将来产品内嵌（v2 的 `/explain` + React 面板）复用同一套判定，不重写。

---

## 5. 数据模型（migration 010）

现有迁移到 `009_market_context_append_only`，新增 `010_trade_plans`。四张表。

### 5.1 `trade_plans`——计划主体

**交易假设（决策 1，制定时冻结，全部必填）**：这五项是「什么逻辑进场就什么逻辑退出」的载体，也是漂移复议时的**对照原文**。Python 不做语义解析，复议判定只靠方向分类器（见 §6.1）。写不出来就说明计划没想清楚——这个门槛是特性不是 bug。

| 字段 | 对应人话 |
|---|---|
| `thesis_cn` | 我进来冲的是啥、博弈的是啥 |
| `invalidation_criteria_cn` | 如果咋了就算失效 |
| `drawdown_playbook_cn` | 下跌了咋办（哪个位置算正常回踩，哪个位置算失效）|
| `take_profit_plan_cn` | 止盈怎么止（目标 B 到了一次出还是分批、移动止盈规则）|
| `stop_plan_cn` | 止损怎么执行 |

**锚点与状态**

| 字段 | 类型 | 说明 |
|---|---|---|
| `plan_id` | TEXT PK | `plan_{symbol}_{created_at}_{短哈希}` |
| `symbol` / `module` / `direction` | TEXT | module 对齐 `MODULE_MAP`；direction ∈ long/short |
| `entry_rule_id` | TEXT | **入场理由锚点**，漂移检测的主对象 |
| `entry_lifecycle_id` | TEXT | 锚到 `TradeOpportunityDTO` / `PullbackOpportunityDTO` 的 `lifecycle_id` |
| `entry_trigger_cn` | TEXT | 入场条件人话（来自 `next_step_cn`） |
| `entry_price_ref` | REAL | 参考入场价（`b1_price` / `ma_value`），**不是成交价** |
| `invalidation_price` | REAL | 失效价。**revision_no=0 里的值永久冻结** |
| `target_b_price` / `target_b_source` | REAL / TEXT | 来自 `compute_reward_risk` |
| `reward_risk_at_plan` | REAL NULL | 建计划时的 R/R 快照；不可计算时 NULL |
| `valid_until` | TEXT NOT NULL | **决策 6**：逐计划自填有效期。到期发 REVIEW 待办，不自动关 |
| `state` | TEXT | 见 5.4 |
| `ruleset_version` | TEXT | 建计划时的规则集版本，用于识别「计划基于旧规则」 |
| `reason` | TEXT NOT NULL | 制定原因必填 |
| `entered_on` / `exited_on` / `exit_reason_rule_id` | TEXT NULL | 只有日期与规则，**没有数量金额** |
| `superseded_by` | TEXT NULL | **决策 5**：被同向 entered 计划顶掉时指向对方 |
| `created_at` / `updated_at` | TEXT | UTC |

**刻意不存在的字段**：股数、金额、成交价、账户、仓位比例、盈亏金额。

### 5.2 `trade_plan_revisions`——append-only 修订史

漂移复议的全部依据。改计划**不覆盖历史**，只追加。

`revision_id` / `plan_id` / `revision_no`（0 = 创建快照，原始失效价与五项预案永远躺在这）/ `changed_field` / `old_value` / `new_value` / `verdict`（`within_playbook` / `needs_review` / `confirmed_override`）/ `verdict_reason_cn` / `changed_at` / `changed_by`（`user` / `system`）。

### 5.3 `plan_action_items` + `plan_annotations`——待办与原因（决策 4）

`plan_action_items`：`action_id` / `plan_id` / `kind`（`ENTER` / `EXIT` / `REVIEW`）/ `source_alert_code` / `state`（`open` / `done` / `deferred` / `expired`）/ `due_from`（= alert 的 `actionable_from`）/ `nag_count` / `last_nagged_bar_date` / `resume_on`（推迟时的复活谓词，见下）/ `closed_on` / `close_kind`。

`nag_count` 是有意留的——「这笔催你 5 天了」本身就是监督信息，也是复盘素材。

**推迟复活（决策 4c，信号触发非定时）**：`state=deferred` 时必填 `resume_on`--一个结构化谓词，指向确定性层已算出的条件。两种形态：

- `{"rule_id": "..."}`：该 rule_id 的事件出现在当日 DTO 的 `new_events` 时复活。
- `{"field": "close", "op": ">=", "ref": "ema20"}`：`field`/`ref` 是 DTO 内的点路径，`op` ∈ `>= <= == != > <`。如 `close >= ema20`、`tradability.tradable == true`。

`monitor.evaluate_plan` 每次顺带验所有 `deferred` 项的 `resume_on`：满足则该项回 `open` 并产 `ACTION_RESUMED` 提醒。**约束**：`resume_on` 必须能被 DTO 验证；用户指定系统算不出的信号时（如「等放量」而无 `volume_anomaly` 规则），skill 拒绝并列出当前可引用的 rule_id / 字段。父计划的 `valid_until` 仍是兜底--到期 REVIEW 会把挂着的 deferred 项一并翻出来。

`plan_annotations`：**一张表收所有「原因」**——推迟原因、放宽原因、收紧原因、复议结论、事后补充的人话解释。字段 `annotation_id` / `plan_id` / `ref_kind`+`ref_id`（指向 revision 或 action item）/ `kind` / `reason_cn` / `created_at` / `author`。**append-only，永不修改已冻结记录。** 这与 Plan Guardian PG-50 的注解模型是同一套设计，两个项目共用思路。

### 5.4 状态机

```
draft ──人类确认──▶ armed ──ENTER 待办被标记 done──▶ entered ──▶ exited
  │                  │                                  │
  │                  ├──失效价击穿 / lifecycle 消失──▶ invalidated ◀┘
  │                  └──同向他计划转 entered──▶ superseded（记原因）
  └──abandoned
```

- `draft` 未确认不参与监督，不产 alert、不产待办。
- `armed` 盯入场类 alert；`entered` 盯退出类。
- `superseded`（决策 5）：同标的同方向只允许一条 `entered`。原因——不记数量，两条 entered 在现实里指向同一个仓位，退出信号触发时无法区分该退哪一笔。armed 阶段无此问题，多个候选计划盯不同条件互不干涉，正合规格 §12「分别统计」。

---

## 6. PlanAlert：v1 能监督的场景

`evaluate_plan(plan, dto) -> list[PlanAlert]` 是纯函数，无 IO。每条 alert 强制携带：`code` / `severity`（block / remind / hint）/ `rule_id` / `evidence`（DTO 原始数值）/ `provenance` 两层标注 / `actionable_from` / `data_as_of`。

| code | 触发条件（读 DTO 哪个字段） | severity | 产待办 |
|---|---|---|---|
| `ENTRY_CONDITIONS_MET` | armed 且对应 lifecycle `current_conditions_confirmed=True` | remind | **ENTER** |
| `ENTRY_BLOCKED_BY_TRADABILITY` | `tradability.tradable=False` | **block** | — |
| `ENTRY_RR_BELOW_IDEAL` | `reward_risk_ratio < rr_min_ideal` | hint | — |
| `ENTRY_RR_NOT_COMPUTABLE` | `reward_risk_computable=False` | hint | — |
| `ENTRY_CONDITIONS_LOST` | 曾成立后转 False，或 state=weakened | remind | 关闭 ENTER 待办 |
| `INVALIDATION_BREACHED` | close 击穿 `invalidation_price` 或 lifecycle 已 closed | **block** | **EXIT**（若 entered）|
| `EXIT_TRIGGERED` | entered 且 `exit_signals` 中匹配规则 `state=active` | remind | **EXIT** |
| `PLAN_EXPIRING` | 今日 ≥ `valid_until` | hint | **REVIEW** |
| `PLAN_STALE_RULESET` | `plan.ruleset_version != 当前 ruleset` | hint | **REVIEW** |
| `PLAN_ORPHANED` | `entry_lifecycle_id` 在当日 DTO 里找不到 | hint | **REVIEW** |
| `MODULE_NOT_IMPLEMENTED` | `module` ∈ {B, C} | hint | — |
| `DATA_STALE` | `meta.cache_fallback_used` 或 `last_bar_date` 落后 | hint | — |

`DATA_STALE` 存在时，所有 alert 降级标注「数据陈旧，仅供参考」，且**不递增 `nag_count`**——用陈旧数据催办是耍流氓。

**R/R 口径说明（决策 3）**：规格 §13 把「盈亏比小于 3」列为无交易条件（不开新仓），round1 实现为「只算不强制」。人类 2026-08-04 明确定为**只提示、永不拦截**，文案表述为「建议 >3，2–3 可接受」。此差异必须写入 `configs/rules.v1.yaml` 的 note，标明是人类决定而非实现漂移——红线 3 禁的是擅自更改，人类拍板则必须留下出处。回测层 2–3 的敏感性扫描归回测层（对齐规格 §15 第四轮），不进 v1 监督员。

### 6.1 漂移复议（规格 §14，决策 1）

这是监督员区别于讲解员的唯一硬功能。**判定基准不是浮亏，是方向分类器（决策 1）**：Python 只判移动方向，不解析预案文本。冻结的五项预案在复议时作为对照原文摆给人看，但代码不读它。

```
check_revision(plan, changes, dto):
  方向分类器（确定性，可测）：
    多头下移失效价 / 空头上移 = 放宽风险 -> verdict = needs_review
    多头上移失效价 / 空头下移 = 收紧（移动止盈）-> verdict = within_playbook，放行
  硬规则（不分方向，一律 needs_review）：
    换 entry_rule_id 且 state=entered        -> §14 正条
    换 module / 跨趋势跟随↔逆势反转          -> §12
    改 thesis_cn / invalidation_criteria_cn   -> 改的就是假设本身
```

`within_playbook` 直接放行（收紧是正常计划推进）；`needs_review` 进复议流程。预案文本不参与判定，只在复议时摆出来给人和 agent 对照--这样判定权完整留在 Python，不自相矛盾。

**复议流程不是二值 block/allow**：

1. 摆出 `revision_no=0` 的冻结原文（你当初怎么说的）；
2. 指出改动与原假设的冲突点；
3. agent 按系统策略给判断（这是计划内的收紧，还是事后合理化），判断必须挂 `rule_id`；
4. 人类明确确认才落库，`verdict=confirmed_override`；
5. 全程写入 `plan_annotations`，**必填原因**。

**留痕优先于阻止**。被复议过的记录本身就是最好的复盘素材——你能看见自己在哪些位置想放宽。

### 6.2 催办（决策 4 / 4b）

```
每个交易日数据更新后：
  if 数据未前进（last_bar_date 未变）: 整体 skip        # 不重复催
  for item in deferred_items:                          # 先验复活条件（决策 4c）
      if evaluate_resume(item.resume_on, dto): item -> open, 产 ACTION_RESUMED
  for item in open_action_items:
      if DATA_STALE: 记 hint 但不递增 nag_count         # 陈旧数据不催
      else: nag_count += 1; 投递 macOS 通知 + 写今日待办
  until -> done（标记做了，plan 状态推进）
        -> deferred（必填 reason_cn + resume_on，写 plan_annotations）
        -> expired（计划已 invalidated/superseded，自动关）
```

**「每交易日」的定义是 `last_bar_date` 前进了一格，不是日历日推进。**

理由：`data/calendar.py` 的默认 `WeekdayCalendar` **不含任何节假日表**（该模块文档明确说明这是刻意的保守选择--写错节假日表会让周线提前完成，比延迟严重得多）。若按日历日催办，国庆春节长假会连续 8 天弹通知催你买入，而数据根本没更新。改用「数据前进」作为节拍，靠数据本身判断市场开没开，既不需要维护节假日表，也不会误催。

投递（决策 4b）：`launchd` 每交易日收盘后触发一次，跑判定 -> 弹 macOS 通知 + 落地今日待办清单。触发时刻是运行配置项，不是规格 §17 交易参数，可自由调整。微信推送归 v2--届时只是多一个投递器，待办层不动。

---

## 7. 数据流与上下文裁剪

### 7.1 取数（交接 §6.1 = 方案 b）

```
plan_alerts(symbol):
  try:    dto = _detail_dto(analyze(symbol))            # 实时腾讯行情
  except: dto = _detail_dto(analyze_bars(fixture_bars)) # 回退 tests/*.parquet
          mark meta.cache_fallback_used = True
```

选 b 而非 a：监督员发提醒必须能发，网络抖动不该让监督链断。选 b 而非 c：纯 fixture 监督不了当下。**代价必须显式**——回退后所有 alert 强制带 `DATA_STALE`，文案写明 `last_bar_date` 与 provider，且不递增催办计数。用陈旧数据静默发提醒比不发更危险。

### 7.2 喂给 LLM 的上下文（目标 < 8k tokens）

**只喂四块**，其余 DTO 字段一律不给——给了它就会引用，引用了就要校验，不如不给：

1. `plan`（主表当前值 + `revision_no=0` 的冻结预案五项与原始失效价）
2. `alerts`（判定层输出的完整列表，含 evidence）
3. `action_items`（open 待办 + `nag_count`）
4. `context_min`：`symbol` / `display_name` / `meta.{last_bar_date, provider, cache_fallback_used}` / `assessment.{color_cn, stage_cn, risk_state_cn}` / `tradability.{trend_type_cn, blocking_reasons}`

**不喂**：`chart`（最大）、`concepts`、全部 backtest、`recent_events` 全量（只在 alert 的 evidence 里带相关的那几条）。

### 7.3 LLM 输出格式

固定骨架，逐条对应 alert / 待办，不许自由发挥：

```
【计划】{symbol} 模块{module} · {entry_rule_cn} · 状态 {state_cn} · 有效期至 {valid_until}
【数据】{last_bar_date}（{provider}）{陈旧警示}

▶ 待办（催办第 {nag_count} 次）
  {kind_cn}：{要你做什么}
  可执行日：{due_from}
  → 你可以：标记已执行 / 推迟（需说明原因）

■ 阻断 / ■ 提醒 / □ 提示
  {人话说明}
  [rule_id:{rule_id} | 证据:{evidence 键值}]
  {规格 §X 原文 | 判定方式为研究代理}

【下一步观察】{来自 alert 的 next_step，不是 LLM 自创}
```

---

## 8. 红线执行机制

| 红线 | 执行点 | 可测吗 |
|---|---|---|
| 1 无未来泄漏 | `actionable_from` 由判定层计算，LLM 不参与推算日期 | ✅ 断言 `actionable_from > data_as_of` |
| 2 research_proxy 标注 | **两层标注（决策 2）**：`PlanAlert.principle_source`（如「规格 §14 原文」）+ `PlanAlert.logic_provenance=research_proxy` + caveat 说明代理了什么 | ✅ 断言两层都出现在渲染结果里 |
| 3 不擅自优化参数 | 阈值全部 `get_rule().params` 读取；判定层无字面量阈值；时效逐计划自填不设全局 N | ✅ 源码扫描：判定层不得出现裸数值阈值 |
| 4 模块分别统计 | `plan.module` 单值；跨模块改理由一律 `needs_review` | ✅ truth table |
| 接地生成 | **判定权在 Python**；LLM 输出经 `verify_grounding(text, alerts)`：抽取所有 `rule_id:` 标签必须 ⊆ 本次喂入的集合，超集即拒绝重生成（最多 1 次，再失败降级为模板直出） | ✅ 喂伪造输出，断言拒绝 |
| 禁买卖指令 | 禁用词表（买入/卖出/建议买/该买/加仓/减仓/抄底），命中即拒绝 | ✅ |
| 参数决策点停下 | 判定层遇未确认参数 → 产 `PARAM_UNCONFIRMED`，skill 要求列待确认表 | ✅ |

**两层标注的意义（决策 2）**：§14 在规格里是裸句（全文 15 处标【原系统原则】、5 处标【回测代理】，§14 两者皆无），而「盈亏比小于 3」出自 §13 第 4 条原文。这两条都是**原则有原文出处、可执行判定是我们造的**。整条标 research_proxy 会让这条纪律看起来像 AI 编的，削弱它的权威——而它恰恰是整个监督员最硬的一条；完全不标又违反红线 2 的精神。分两层标注是唯一诚实的做法。

**降级路径**：LLM 两次都过不了校验，直接用固定模板渲染 alert。监督员宁可说话生硬，不可说错。

---

## 9. 新增文件清单

**新增**（判定层，纯 Python）
```
src/lei_signal/plans/__init__.py
src/lei_signal/plans/models.py      TradePlan / PlanRevision / PlanAlert / ActionItem / Annotation
src/lei_signal/plans/store.py       SQLite CRUD，照 api/watchlist.py 的模式
src/lei_signal/plans/monitor.py     evaluate_plan(plan, dto) -> list[PlanAlert]，无 IO
src/lei_signal/plans/drift.py       check_revision(plan, changes, dto) -> Verdict
src/lei_signal/plans/actions.py     待办状态机 + 催办节拍（按 last_bar_date 前进）
src/lei_signal/plans/grounding.py   verify_grounding + 禁用词表
src/lei_signal/api/routes/plans.py  CRUD + /api/plans/alerts + /api/plans/actions
scripts/daily_nag.py                launchd 入口：跑判定 → macOS 通知 + 今日待办清单
scripts/com.lei.supervisor.plist    launchd 配置
```

**修改**（只追加，不改既有行为）
```
src/lei_signal/storage/sqlite_store.py   追加 migration 010_trade_plans（四张表）
src/lei_signal/data/calendar.py          Protocol 追加 next_trading_day()
src/lei_signal/api/schemas.py            追加 PlanDTO / PlanAlertDTO / ActionItemDTO / RevisionRequest
src/lei_signal/api/app.py                include_router(plans.router)
configs/rules.v1.yaml                    追加 plan_discipline_guard（承载 §14 两层标注与文案）
                                         reward_risk_filter.note 记录 R/R 口径的人类决定与出处
```

**skill 侧**
```
.claude/skills/lei-supervisor/SKILL.md             指令：只渲染 alert、禁买卖词、参数决策点停下
.claude/skills/lei-supervisor/scripts/plan_cli.py  HTTP 客户端，调 /api/plans*
```

**不动**：`rules/` 下既有规则、`compose/pipeline.py`、前端。v1 完全不碰 React。

---

## 10. 验收标准

**判定层（必须全绿，不依赖 LLM）**

1. `evaluate_plan` truth table：第 6 节每个 alert code 至少一个正例 + 一个反例。
2. 红线 1：所有 alert 断言 `actionable_from` 严格晚于 `data_as_of`。
3. 溯源闭环：每条 alert 的 `rule_id` 必须能被 `get_rule()` 命中，否则测试失败。
4. 漂移复议：预案内的改动 → `within_playbook`；预案外放宽 → `needs_review`；entered 后换入场理由 → `needs_review`；跨模块 → `needs_review`；收紧止盈 → `within_playbook`。
5. append-only：任何修订后 `revision_no=0` 的 `invalidation_price` 与五项预案原文不变。
6. 待办节拍：`last_bar_date` 未前进时重复运行，`nag_count` 不变（幂等）；`DATA_STALE` 时不递增。
7. 决策 5：同标的同方向第二条计划转 `entered` 时，前一条自动 `superseded` 且写入 annotation。
8. 决策 6：今日 ≥ `valid_until` 产 `PLAN_EXPIRING` + REVIEW 待办，且计划状态**不**自动改变。
9. 必填校验：五项预案 + `reason` + `valid_until` 任一为空则拒绝落库（draft 阶段允许空）。
10. `test_no_trading_execution_surface_exists` 继续通过；新增 schema 不得出现数量/金额字段。
11. 幂等：同数据同计划重复调用 `evaluate_plan`，alert 列表逐字段相等。

**表达层**

12. `verify_grounding` 拒绝引用了不存在 rule_id 的伪造输出。
13. 禁用词表命中即拒绝。
14. 两层标注：research_proxy 判定的 alert，渲染结果必须同时含原文出处与「判定方式为研究代理」。
15. 校验失败两次 → 降级模板渲染，不抛异常给用户。

**门禁**：`pytest -q`、`ruff check src`、`mypy src` 全过。前端未改。

---

## 11. v2+ 路线

1. **微信投递**：待办层不动，只加一个投递器（server酱 / 企微机器人 / 文件传输助手）。
2. **B/C 模块接入**：`false_breakout_reclaim`（2B/破底翻）、密集区突破实现后，`MODULE_NOT_IMPLEMENTED` 自动消失，监督覆盖面跟着长。
3. **产品化**：后端 `/explain` 端点 + React 计划面板（计划卡 + 待办 + 修订史时间线）。复用 v1 判定层。
4. **交易所节假日表注入**：`calendar.py` 已支持 `holidays` 注入，接入后 `actionable_from` 可扣除长假，不再是「未扣节假日的最早可执行日」。
5. **复盘闭环**：终态计划（含 `nag_count`、推迟原因、复议记录）对比 `scenario_backtests`，分别回答「我照系统做了吗」和「系统本身对不对」——这两个问题必须分开答。

---

## 12. 风险与对策

| 风险 | 对策 |
|---|---|
| 接地生成漂移（LLM 编 rule_id / 编数值） | 判定权在 Python；白名单校验；两次失败降级模板 |
| 你把 agent 聊服，让它同意放宽失效价 | 聊服了也没用——`drift.py` 照样判 `needs_review`，且必须人类明确确认 + 填原因才落库，全程留痕 |
| 预案写得太笼统，什么改动都算「预案内」 | 复议 verdict 逐条记录；复盘时能看出哪些计划的预案形同虚设 |
| 建计划门槛太高，你懒得建 | 五项预案由 agent 对话引导逐项问出来，不是让你对着空表格填；agent 可依 `rule_id` 给建议 |
| 催办疲劳，你对通知脱敏 | 只在数据前进时催；`DATA_STALE` 不催；推迟必填原因这个摩擦本身就在筛真假推迟 |
| 长假期间误催 | 节拍绑 `last_bar_date` 而非日历日，数据不动不催 |
| `actionable_from` 落在节假日里 | 诚实标注为「最早可执行日（未扣节假日）」；v2 注入节假日表后消除 |
| 台账长草 | 逐计划 `valid_until` 到期发 REVIEW 待办；列表按 state 分区 |
| 计划台账被当成持仓管理来用 | schema 层就没有数量/金额字段；acceptance gate 持续扫描 |
| LLM 延迟/成本 | alert 与待办判定不过 LLM，可完全离线跑；LLM 只在你要人话解释时调 |
