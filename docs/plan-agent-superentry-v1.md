# Agent 超级入口 · 每日操作闭环 v1 · 设计定稿

> 定稿日期：2026-09-05。所有决策当日由用户拍板（见 §2）。
> 上游：`docs/plan-agent-supervisor-v1.md`（监督员 v1）、`docs/plan-buy-point-agent.md`（买点审阅）、
> `docs/plan-web-plan-entry-agent.md`（Web 计划入口 + Agent 抽屉）。
> 本文是**功能范围定稿**，进入实现前需经 writing-plans 拆解。

## 0. 一句话目标（大白话）

打开一个 Agent 页面，点一个按钮（或说一句话），系统就把今天该看什么标的、能不能买、买多少、
什么时候算失效、持仓有什么要处理的全部摆出来；你实际买卖后说一句话报单，系统记账算盈亏，
每笔了结自动复盘、每周日出周报。**所有判定由规则算，AI 只负责讲人话**，按钮零 AI 调用。

## 1. 定位与策略溯源

本系统分层：交易规格（trading-spec-v1）只覆盖「单一标的技术判定」；组合层（portfolio/advisor，
R1–R7）已有先例。本设计属于**执行编排层 + 组合层扩展**：

- 技术判定（买点/失效/盈亏比/可交易性）**全部复用既有规则层**，本文不新增任何技术判定。
- 仓位建议、基金台账、真实盈亏、复盘属于组合/执行层，**超出 trading-spec 范围**
  （spec §范围明确「不包含组合配置及仓位数量计算」），依据是用户 2026-09-05 拍板，
  对齐 advisor.py 的强度分级语言（certified / candidate / observation / management）。
- 基本面/消息面/情绪面在推荐流水线中**只做排序参考与叙事标注，不做硬过滤**
  （AGENTS.md 红线：技术判定独立成立，叙事层永不挡信号）。

## 2. 已确认决策（2026-09-05，用户拍板）

| # | 议题 | 结论 |
|---|---|---|
| D1 | 实际成交记录 | **只做基金**（场外按当日净值、ETF 按当日收盘价定价）；口头/表单报单，落库前必须确认卡确认；个股暂缓；不接券商、不自动下单。计划台账本身仍不存数量金额（边界变更仅限新台账表） |
| D2 | 仓位口径 | 系统给**依据+档位建议**（试仓 ≤5% / 标准 10–15% / 偏重 20–30%，单标的封顶 30%），引回测结果与指标状态；**最终买多少用户定**。参数入 `configs/rules.v1.yaml`，标注来源「2026-09-05 用户拍板」 |
| D3 | 入口形态 | 豆包式**快捷指令**（零 AI 调用）+ 聊天一句话自动路由到流水线；每日操作清单**独立页面**（不塞对话）；对话中标的/板块可点击直达 K 线；看盘要「丝滑、可读性高」——新增整页 Agent 工作台 |
| D4 | 提醒投递 | 飞书 + macOS 双通道（notify 模块两渠道均已实现），分级推送 |
| D5 | 推荐候选池 | 自选 + 板块体系内（含板块页覆盖的行业 ETF）；不做全市场扫描 |
| D6 | 编排架构 | **方案三（混合）**：按钮走确定性流水线；聊天走「规则意图识别 → 流水线 → GLM 讲解」，识别不到再走既有通用讨论 |
| D7 | LLM | GLM API（密钥走环境变量，不进代码库）；省调用：按钮零 AI、清单页零 AI、讲解按需 |
| D8 | 情绪面 | 留插槽（sentiment 未完工），卡片显示「暂未接入」，不影响其他层 |
| D9 | 推荐质量验证 | 建**推荐存证账本**：每日推荐落库，T+N 自动对账打分；深度测试报告按实验归档规约落 `docs/experiments/` 并登记 registry |

## 3. 总架构（三层，延续监督员哲学）

```
┌─ 表达层（GLM，可选）───────────────────────────────┐
│ 讲解流水线结果、追问答疑、复盘叙事。输出过既有接地   │
│ 校验（数值白名单 + rule_id 白名单 + 禁用词），       │
│ 失败两次降级模板。不可用时全链路仍可用（模板直出）。  │
└──────────────▲──────────────────────────────────┘
               │ 结构化结果（CopilotCard）
┌─ 编排层（Python，新模块 copilot/）────────────────┴─┐
│ intent.py     规则意图识别（chat → 流水线 + 参数）    │
│ pipelines.py  确定性流水线（推荐/仓位/报单/复盘/速览）│
│ cards.py      卡片 DTO（结构化 + 证据链 + 跳转链接）  │
└──────────────▲──────────────────────────────────┘
               │ 只读复用
┌─ 判定层（既有，零改动）──────────────────────────────┐
│ opportunities scan/review · plans monitor/actions    │
│ portfolio advisor/funddata · newsfeed · sectors      │
│ dailybrief · notify(feishu/macos) · agent sessions   │
└─────────────────────────────────────────────────────┘
```

红线：判定权在 Python；GLM 不产生任何新数值/新判定/新日期；所有阈值走 `configs/rules.v1.yaml`。

## 4. 模块设计

### A. 今日推荐流水线 `pipeline_today_recommend`

- **宇宙**：自选（15:00 `daily_scan` 已落 `daily_opportunity_scan`）+ 板块快照覆盖的行业 ETF。
- **资格门（技术）**：verdict ∈ {actionable, waiting} 才可上榜；blocked/none 不进推荐（但清单页保留全量链接）。
- **排序（综合）**：板块阶段（markup 加分）→ 消息面大事（newsfeed 当日 ≥8 分事件标注）→ 基本面面板状态 →
  情绪面插槽（缺省跳过）。排序只影响展示顺序，**不改变任何技术结论**；被排后的标的仍完整保留。
- **输出**：前 5 标的 + 前 3 板块。每条含：推荐理由（rule_id 证据链 + 板块阶段 + 消息标注）｜
  当前状态（可动手 / 还缺什么 / 被什么挡）｜若动手：仓位档位建议（§B）+ 失效位参考 + 盈亏比 |
  跳转链接（DetailPage）。
- 每次运行的完整输出落 `recommendation_journal`（§5 存证账本）。

### B. 仓位建议 `pipeline_position_advice(symbol)`

- 输入：买点审阅候选（或 armed 计划）+ 组合持仓 + 该标的对应模块的历史回测统计（既有
  scenario/timing backtest 输出）。
- 输出：档位（试仓/标准/偏重，上限 30%）+ 依据清单（回测期望、板块阶段、同板块已有敞口、
  入场价到失效位距离、盈亏比）+ 明示「最终由你定」。
- 溯源：档位阈值 = D2 用户拍板入 rules.yaml；依据中每条带证据 ref（回测出处），
  无回测依据的部分标 management/observation（advisor.py 先例）。

### C. 基金交易台账 + 真实盈亏（边界变更核心）

- 新表 `fund_trades`（migration 编号顺延）：`trade_id / fund_code / fund_name / side(buy|sell) /
  amount / priced_nav(系统定价) / user_note / trade_date / source(agent|web) / plan_id? / created_at`。
  **与 trade_plans 分表**，计划台账 schema 不动。
- 报单入口：① Agent 对话（意图路由 → 正则/规则抽取数字 → **确认卡** → 用户确认落库）；
  ② 持仓页与操作清单页表单。
- 定价：场外基金按报单日净值、ETF 按报单日收盘价（报单默认收盘口径，盘中报单也按当日收盘计）；
  净值日更任务已有（funddata）。无价可依时明确提示，**不猜数**。
- 盈亏：买入摊成本、卖出按当日价算已实现盈亏、持仓按最新净值算浮动盈亏。R 倍数仅在
  有关联计划时计算：初始风险额 = 该笔金额 × |参考入场价 − 失效价| ÷ 参考入场价，
  R 倍数 = 实际盈亏 ÷ 初始风险额（大白话：当初这笔准备亏的钱为 1 份，最后赚了几个 1 份）。
- **验收守门更新**：`test_no_trading_execution_surface_exists` 按 D1 更新白名单
  （fund_trades 豁免；个股交易字段仍禁；禁券商 API 符号不变），并在 AGENTS.md 记录边界变更出处。

### D. 复盘 `pipeline_review`

两个问题分开答（监督员 v2 路线第 5 条的落地）：

- **单笔复盘卡**：触发 = 卖出成交落库 或 计划进入终态。内容：
  - 纪律面：当初计划五项预案 vs 实际执行；催办次数、推迟原因、复议记录（plans 库已有）。
  - 结果面：实际盈亏金额、R 倍数、与建计划时盈亏比预期对比。
- **周复盘**：每周日晚跑批，本周操作、合计盈亏、按「守纪律/未守纪律」「按模块」分组统计。
- 叙事：GLM 一次调用生成，数值全部来自台账与 plans 库，过接地校验；无 GLM 走模板。
- 新表 `trade_reviews`（独立表，便于页面渲染与增量生成；plans 的注解体系不动）。

### E. 每日操作清单页 `/ops`

- 组装（全确定性，零 AI）：① 持仓要处理的（advisor 建议 + INVALIDATION_BREACHED + 到期 REVIEW）
  ② 今日推荐（§A 输出）③ plans 开放待办 ④ 观察触发（waiting 条件命中）。
- 生成时机：15:00 daily_scan 后由编排脚本组装落库（复用 launchd 节奏）。
- 推送：EXIT/actionable 级 → 飞书 + macOS；纯观察 → 只红点（D4）。

### F. Agent 工作台（整页体验，D3「丝滑」要求）

- 新路由 `/agent`（AgentWorkspacePage）：左栏对话流（含内嵌 CopilotCard 卡片），右栏联动面板
  （当前讨论标的的迷你 K 线 + 买卖点标记，复用 KlineChart；无标的时显示组合速览）。
- 联动机制：后端回复的 `resolved_symbol`（已有）驱动右栏切换；卡片内 symbol 可点击
  → 右栏即切（不跳页）；「开大图」按钮才进 DetailPage。
- 快捷指令条（置顶）：`今天看什么` `持仓速览` `建个计划` `我要报单` `本周复盘`。
  点击 = 直接调流水线端点（零 AI），卡片先出，带「让 AI 讲讲」按钮（此时才一次 GLM 调用）。
- 既有全局 AgentConsole 保留（其他页面快捷入口），新增「展开成工作台」按钮；chips 调整为同一套快捷指令。

### G. 意图路由 `intent.py`（方案三核心）

- 第一层：规则匹配（关键词 + 既有 `_SYMBOL_TOKEN_RE` 标的抽取）：报单（买了/卖了/申购/赎回）、
  推荐（看什么/推荐/机会）、持仓、复盘、建计划、板块。
- 第二层：未命中 → 走既有 `/agent/chat` 通用讨论（一次 GLM 调用，现有接地链路）。
- 规则层零 AI；路由决策可测（truth table）。**不做 LLM 意图分类**（省调用；识别不准时反问一句）。

### H. GLM 接入（`plans/llm.py` 扩展）

- 新增 `GLM_API_KEY / GLM_BASE_URL(默认 https://open.bigmodel.cn/api/paas/v4) / GLM_MODEL`
  环境变量分支，OpenAI 兼容协议，优先级 GLM > DeepSeek > ARK。
- 密钥注入本机环境（launchd plist / .env，均不进库）。
- 上下文预算沿用 <8k 裁剪；讲解类调用结果带 `grounded` 标记。

### I. 情绪面插槽

- 流水线入参含 `sentiment` 槽位：数据缺失时卡片固定显示「情绪面：暂未接入」，不报错不阻塞。

## 5. 推荐质量验证账本（D9「深度测试」）

- `recommendation_journal` 表：每日推荐流水线完整输出 + 当日价格快照。
- T+1 / T+5 / T+20 自动对账：推荐后走势、买点是否兑现、兑现后的 R 表现。
- 月度出「推荐质量报告」→ 按实验归档规约落 `docs/experiments/推荐质量-YYYY-MM-DD.md` +
  登记 registry.json（verdict 按 passed/falsified/mixed 归档）。
- **诚实声明**：历史无逐日扫描数据，不做伪历史回测；用前向存证替代。规则层各模块的
  历史回测证据（scenario backtests）继续作为单标的依据。

## 6. 数据模型变更汇总

| 表 | 类型 | 说明 |
|---|---|---|
| `fund_trades` | 新增 | 基金成交台账（D1） |
| `trade_reviews` | 新增 | 单笔/周复盘记录 |
| `recommendation_journal` | 新增 | 每日推荐存证（D9） |
| `trade_plans` 等四张 | **不动** | 监督员 v1 台账保持原样 |

migration 顺延编号，SQLite。

## 7. API 端点（新增，前缀 /api）

```
GET  /copilot/recommend                 今日推荐（流水线输出 + 存证）
POST /copilot/recommend/explain         推荐讲解（GLM，一次）
GET  /copilot/position-advice/{symbol}  仓位档位建议
POST /copilot/trades                    报单（确认后落库）
POST /copilot/trades/preview            报单预解析 → 确认卡（零 AI）
GET  /copilot/trades                    台账 + 盈亏
GET  /copilot/review/{trade_id}         单笔复盘卡
GET  /copilot/review/weekly?week=...    周复盘
POST /copilot/dispatch                  意图路由入口（chat 复用）
GET  /ops/today                         每日操作清单（页面读）
```

## 8. 前端变更汇总（web/，不动 Streamlit）

- 新页面：`/agent`（AgentWorkspacePage，§F）、`/ops`（OpsPage，§E）。
- AgentConsole：chips 替换为快捷指令集 + 「展开工作台」。
- CopilotCard 组件族：推荐卡 / 仓位卡 / 报单确认卡 / 复盘卡 / 持仓速览卡，内嵌于对话流
  与 /ops 页，卡片内 symbol 点击联动（工作台内切右栏，其他页跳 DetailPage）。
- types + api client 同步扩展。

## 9. 分期交付

| 期 | 内容 | 用户可感知 |
|---|---|---|
| P1 | GLM 接入 + 意图路由 + 快捷指令 + 今日推荐流水线（含初步档位）+ 推荐存证账本 | 点按钮出推荐；聊天一句话办事 |
| P2 | 基金台账 + 报单确认卡 + 真实盈亏 + 守门测试更新 | 说一句「我买了XX」就记账；持仓页见真盈亏 |
| P3 | 复盘（单笔 + 周报 + 叙事） | 了结自动复盘；周日晚飞书收周报 |
| P4 | `/ops` 清单页 + 双通道推送编排 + Agent 工作台整页（K 线联动） | 每天一页一条飞书；对话旁边丝滑看 K 线 |

（工作台整页放 P4 是因为前三期先把数据与流水线做实；若前端工期允许可与 P1 并行出骨架。）

## 10. 验收门禁

- `pytest -q` / `ruff check src` / `mypy src` 全绿；`cd web && npm run build` 通过。
- 意图路由 truth table：每类意图正例 + 未命中反例（回落通用讨论）。
- 报单：未经确认卡确认的报单**不落库**（测试断言）；无净值日期明确报错不猜数。
- 接地：GLM 输出含禁用词/编造数值必降级模板（沿用既有测试范式，mock 不打真实 API）。
- 守门：更新后的 `test_no_trading_execution_surface_exists` 绿（fund_trades 豁免、个股仍禁、无券商符号）。
- 幂等：同一交易日重复跑推荐/清单组装，输出与存证不重复。
- 说人话：所有新卡片文案过 AGENTS.md 白话约束（首现概念带解释）。

## 11. 风险与对策

| 风险 | 对策 |
|---|---|
| 推荐排序被当成「新信号」 | 卡片明示「排序仅影响展示顺序，不构成判定」；判定字段全部引 rule_id |
| 报单数字抽取错（金额/份额混淆） | 确认卡必须人工确认；歧义时反问；抽取规则可测 |
| 基金净值延迟/缺失 | 无价不落账，标「待定价」次日补（funddata 日更后自动补） |
| GLM 密钥泄露 | 只走环境变量；文档不出现明文；.gitignore 校验 |
| 意图识别覆盖不了的说法 | 二层回落通用讨论 + 反问；路由表可持续补充（规则文件非硬编码） |
| AI 调用超预算 | 按钮零 AI、清单零 AI、讲解按需；GLM 失败自动降级模板，功能不缺 |
| 复盘变成马后炮安慰 | 复盘卡先摆当初预案原文（revision_no=0），再摆实际；纪律与结果分开陈述 |
