# 统一 Agent 入口 + 多轮记忆 + 用户视角净化 · 设计定稿

> 日期：2026-08-23。人类已批准全部四项决策（见 §0）。
> 上游背景：监督员体系实际使用为 0（trade_plans 0 条），入口分裂、单轮无记忆、
> 工程审计信息平铺是三个根因。本设计不改判定层，只改会话/表达/呈现三层。

## 0. 已拍板决策

| # | 议题 | 结论 |
|---|---|---|
| 1 | 讨论式解释的上下文 | **技术摘要全喂 + 数值接地校验**（措辞自由、数字不许编） |
| 2 | 统一入口 | **全局顶栏 agent 抽屉**，上下文跟随当前页面 |
| 3 | 工程审计信息 | **默认隐藏，小角标可展开**；Web / agent 回答 / 飞书卡三处统一 |
| 4 | 建计划形态 | **对话式引导**（skill 的引导流程搬到 Web；表单保留兜底） |

## 1. 总体架构：新增会话层，判定层一字不动

现有分层 判定(Python) → 表达(LLM) → 投递(通知) 不变，在表达层旁加**会话层**：

```
全局 agent 抽屉（Web） ──► /api/agent/chat（新）
                             1. 会话读写（SQLite migration 011）
                             2. 上下文构建：技术摘要全喂
                             3. 拼最近 10 轮历史
                             4. LLM（SYSTEM_PROMPT 改讨论式）
                             5. 数值接地校验（新）
                             ▼
                       agent_messages 落库（含 trace 元数据）
```

**不变量（红线，全程不得突破）**：
- 判定权仍在 Python：chat 只解释不判定，不从行情自行判断买点/信号。
- 建计划确认门：agent 只能产 draft 卡片；落库与转 armed 仍走既有
  create/confirm 端点，仍需人类点确认。
- 禁用词表（买入/卖出/建议买/该买/加仓/减仓/抄底）照旧强制。
- 数值接地为新增主校验；rule_id 白名单保留（防编造引用）。
- 不记数量/金额/成交价/账户（acceptance gate 持续扫描）。

## 2. 后端

### 2.1 会话存储（migration 011_agent_sessions）

- `agent_sessions`：`session_id` PK / `symbol` TEXT NULL（NULL=全局会话）/
  `title_cn` / `created_at` / `last_active_at`。
- `agent_messages`：`message_id` PK / `session_id` FK / `role`(user|assistant) /
  `content` / `grounded` INT / `meta_json` TEXT（数值校验结果、引用维度、
  plan_draft 引用等）/ `created_at`。
- 会话按标的组织；前端刷新不丢；「开新会话」显式动作；喂 LLM 只取最近
  **10 轮**（user+assistant 各算一条），更早历史不进 payload。

### 2.2 上下文构建器（新 `src/lei_signal/plans/llm_context.py`）

把规格 §7.2「只喂四块」升级为**技术摘要全喂**（仅限 agent 讨论场景；
`daily_nag` 等离线投递仍用原四块裁剪，不动）：

| 维度 | 来源（SymbolDetailDTO / analyze 结果） |
|---|---|
| 五维度判定 | `assessment`（颜色/阶段/风险/趋势/可交易性） |
| 活跃结构 | `live_structures`（顶/底/关键位/密集区 + 生命周期状态） |
| 量能状态 | 量能异常事件/规则输出 |
| 筹码代理 | volume_profile 的 VAH/POC/价值区（标「代理」） |
| MACD 事件 | `macdEvents`（按 macd-reading skill 口径） |
| 近 N 日关键事件 | `recent_events` 裁剪至近 20 条 |
| 双均线数值 | EMA/SMA 当前值与相对位置 |
| 买点审阅 | review 的 candidates（satisfied/missing/state/key_price） |
| 计划与待办 | 该标的 armed/entered 计划 + open 待办 + nag_count |

预算目标 3-5k tokens/次；超出时按行裁剪（事件类先砍最旧的）。

### 2.3 数值接地校验（升级 `plans/grounding.py`）

- 从本次 payload 递归抽取全部数值 → **数值白名单集合**。
- 从 LLM 回答抽取实数（价格/百分比/带单位数字，含中文数字写的价位），
  每个必须在白名单，或为白名单值的四舍五入/百分比换算（±0.5% 容差）。
- **豁免**：量词与序号（「三根K线」「买点②」「第 3 次」）、日期、
  轮次、候选序号——只校验「行情数值类」数字。
- 失败 → 重试一次 → 再失败降级模板直出（与既有降级链一致）。
- `verify_grounding` 的 rule_id 白名单与禁用词逻辑保留不变。

### 2.4 SYSTEM_PROMPT 重写（讨论式）

- 允许自由组织语言解释「为什么这是买点」，依据策略体系（道路/路牌/触发）
  讲因果，不做骨架照抄。
- 数值纪律不变：数字只能来自 payload；日期照抄；禁用词照旧。
- **溯源标注不再让 LLM 写**：由后端从 alerts 元数据生成 trace 字段，
  前端渲染角标（见 §4）。LLM 回答中不再出现「rule_id:」「研究代理」字样。
- 买点场景既有的「数字关联纪律」「对话聚焦」条款并入新 prompt。

### 2.5 端点

- `POST /api/agent/chat`：`{session_id?, context:{kind, symbol?}, message,
  action?}`。服务端：解析/建会话 → 构建上下文 → 拼 10 轮历史 → LLM →
  数值接地 → 落库 → 返回 `{reply, grounded, session_id, trace}`。
- `GET /api/agent/sessions?symbol=`：会话列表（含最近一条摘要）。
- `GET /api/agent/sessions/{id}/messages`：历史消息。
- `POST /api/agent/sessions`：显式开新会话。
- 建计划对话流的落库走既有 `/api/plans` create/confirm，不新增写路径。
- 既有 `/api/plans/{id}/chat`、买点 chat 端点保留（内部收敛到会话层，
  老调用不破），标记 deprecated。

## 3. 前端：全局抽屉 + 能力 chips + 对话式建计划

- **TopNav 常驻 agent 按钮**，有 open 待办时红点；侧滑抽屉全页面可用。
- 上下文跟随：标的详情页=该标的；看盘/监督页=全局。抽屉头部显示当前
  上下文（标的+日期）+「开新会话」。
- **能力 chips 按上下文动态显示**：
  - 标的：`这个买点为什么是买点` · `技术面讨论` · `给这个买点建计划` · `这个标的我的计划`
  - 全局：`扫描自选买点` · `今日待办` · `市场环境怎么样`
  - chips 点击=发送预设消息；「扫描」等结果型动作以结构化卡片内嵌对话
    （复用现有 scan 表格渲染逻辑）。
- **对话式建计划**：agent 基于买点审阅逐项问五项预案（每项给基于策略的
  建议值，挂规则依据）；用户可回「按建议」或自述；问完整理成**计划卡片
  内嵌对话**（五项+失效价+有效期一览）；用户点「确认落库」→ 既有
  create → confirm。中途可「去表单微调」打开 PlanCreateFlow（预填已答项）。
- AgentDrawer/BuyPointDrawer 的对话 UI 合并进全局抽屉后退役；
  SupervisorPage「问 agent」改为打开全局抽屉并定位到该计划会话。

## 4. 审计信息角标化（三处统一）

- 新 `ProvenanceBadge` 组件：`ⓘ` 小角标，点开浮层显示 rule_id /
  研究代理标注 / 证据键值 / 规格引用。
- 应用处：SupervisorPage 的 alert 行、agent 回答尾部（渲染 trace 元数据）、
  BuyPointDrawer。
- **飞书卡**（`notify/render.py`）：正文去掉全部工程标注；卡片底部 note
  一行小字「研究代理判定 · 溯源见系统」；evidence 精简但保留在回调
  可查的日志/DB 中，不伪造。
- 验收口径：默认界面（DOM 文本）grep 不到「rule_id:」「判定方式为研究代理」
  明文；展开角标后完整可见。

## 5. 兼容与迁移

- `daily_nag` / `intraday_check` 等离线链路不接会话层、不改上下文裁剪。
- 老端点保留可用；前端全面切换到统一抽屉后下个大版本再删。
- 会话数据只增不改（append-only，与修订史同一原则）；不含数量/金额。

## 6. 验收标准

1. 数值接地单测：编造数字→拒绝+降级；照抄→通过；量词/序号豁免不误杀。
2. 多轮集成测试：第二轮请求的 payload 含第一轮问答；回答引用上文。
3. 三处角标：默认 DOM 无工程明文；展开后 rule_id/研究代理/证据完整。
4. 建计划对话流：确认前 DB 零写入；确认后 draft→armed 与表单路径行为
   一致（复用既有端点测试）。
5. 禁用词与 rule_id 白名单校验不回归；`test_no_trading_execution_surface_exists`
   继续通过。
6. 既有测试全绿；`ruff check src` / `mypy src` 干净。

## 7. 非目标

- 不改判定层任何阈值/规则；不做微信/邮件推送；不做语音/图片输入。
- 不做多设备会话同步（本地 SQLite 单机为准）。
- 飞书卡不做交互式折叠（平台能力限制，note 小字方案替代）。

---

## 8. 验收记录（2026-08-23，实机）

- 交付：558912f..955577c，17 commits（9 任务 + 6 轮 fix + 终审 2 + nit 1）。
- 门禁：pytest 1147 passed / 1 skipped（feature 净增 51 测试）；触碰文件 ruff/mypy 干净；web tsc --noEmit exit 0。
- 终审：merge-ready（final-review.md §8 复核记录；FR-1/2/3 + R-3 + ReviewDrawer 顺手项闭合）。
- 实机验收（biao restart 后 curl 生产后端，真实 DeepSeek）：
  - 首问「这个买点为什么是买点」→ 讨论式回答（先纠正前提=环境阻断、再讲结构面为何像买点），grounded=True，正文无 rule_id:/研究代理明文；
  - 第二轮「那筹码峰呢」→ 直接切筹码代理维度（POC/价值区/当前价，代理口径），多轮上下文生效，grounded=True；
  - GET messages 4 条按序持久化；GET sessions 列表/标题/摘要正常。
- 实机发现并修复：生产库写事务 >5s 致 agent_chat 撞 `database is locked` → connect busy_timeout 5s→30s（955577c 前一提交）。
- 已知后续（backlog 见 .superpowers/sdd/progress.md Feature 3 段）：R-1 混合阿拉伯+中文单位数值绕过（fail-open 裁定）、全局 chips 数据支撑、会话恢复 UI 未接线、孤儿 draft 无管理面（既有缺口）、AgentDrawer 孤儿组件等，均为防御性/外观/重构类。
