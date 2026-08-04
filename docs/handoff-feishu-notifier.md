# LEI 监督员 · 飞书投递与交互卡回执 · 实现交接 prompt

> 本文件自包含。接手 AI 无需对话上下文。
> **先读这份**，再读两份既有规格（顺序固定）：
> 1. `docs/plan-agent-supervisor-v1.md` — 监督员 v1 功能定稿（10 项决策已冻结，**已实现**）
> 2. `docs/plan-agent-supervisor-v1-execution.md` — v1 执行计划（P0–P5，**已完成**）
>
> **你的任务**：实现监督员的飞书投递器 + 交互卡回执闭环（规格 v2 路线第 1 项）。
> 这是**在已完工的 v1 判定层之上加一个投递器 + 一个回调入口**，不是重做监督员。
> 判定层（`plans/monitor.py` / `actions.py` / `drift.py`）**一个字都不要改**。

## 0. 你的角色与边界

实现者。系统已有完整的确定性监督链（计划台账 → 判定 → 待办催办 → 漂移复议 → 模板渲染），
当前只能投递到 macOS 桌面通知。你要加的是：

1. **飞书投递器**：把待办与 alert 推到飞书（交互卡片）
2. **回执闭环**：卡片按钮「标记已执行 / 推迟」回调后端，驱动既有待办状态机

**最关键的一句话**：判定权在 Python 判定层，投递器只做**渲染 + 传输 + 回调转发**。
你不新增任何判定逻辑、不新增阈值、不碰 LLM。

## 1. 铁律（任何相位都不得突破）

这些是 v1 已建立的红线，**投递到手机后更不能松**——手机消息传播性远强于桌面通知。

1. **禁买卖指令**：推送文案必须过 `plans/grounding.py::verify_grounding`（禁用词表：
   买入/卖出/建议买/该买/加仓/减仓/抄底）。命中即不发，降级为纯 alert code 文案。
2. **溯源标签保留**：每条推送至少带 `rule_id`；evidence 可精简但不可伪造。
   卡片里出现的 `rule_id` 必须 ⊆ 本次 alert 集合（复用 `verify_grounding`）。
3. **两层标注保留**：`principle_source`（如「规格 §14 原文」）+「判定方式为研究代理」
   两层都必须出现在卡片里。§14（失效价纪律）与 §13 第 4 条（R/R）尤其不可省。
4. **DATA_STALE 不推送**：规格已定「陈旧数据不递增 nag_count」，同理**不推催办**。
   用陈旧数据催办是耍流氓。可推一条「数据陈旧，今日未催办」的静默提示，但不催。
5. **不记数量/金额/成交价/账户**：`tests/integration/test_acceptance_gates.py::
   test_no_trading_execution_surface_exists` 持续扫描禁用符号
   （`place_order/submit_order/AccountState/FundID/ProxyID/StrategyEngine/
   CandidateIntent/AggregateResolver/position_size`）。新增卡片字段、回调 payload、
   数据表**都不得出现数量/金额/成交价/账户**。
6. **不改判定层**：`plans/{monitor,actions,drift,store,models}.py` 只读调用，不修改。
   催办节拍绑 `last_bar_date` 前进这条语义不得动。
7. **回执必须验签**：见 §5 安全。未验签的回调一律拒绝。

## 2. 已验证的环境事实（直接用，不要重新发现）

- **项目**：`/Users/yongbiaoli/Desktop/lei-signal-lab`，分支 `recovery/lei-round2`，ruleset `1.3.0`
- **测试**：`/opt/homebrew/bin/python3 -m pytest -q`（当前 729 passed / 1 skipped）
- **Lint / 类型**：`/opt/homebrew/bin/python3 -m ruff check src`；`/opt/homebrew/bin/python3 -m mypy src`（102 files）
- **依赖**：`requests>=2.31` 已是**主依赖**（`pyproject.toml`），可直接用于飞书 HTTP 调用。
  `httpx` 只在 dev extras。**不要引入新的第三方 SDK**（飞书 open API 用 requests 直调即可）。
- **DB**：`src/lei_signal/api/config.py::sqlite_path()` 读 `LEI_SQLITE_PATH`（默认 `lab.db`），
  WAL 已开。迁移在 `src/lei_signal/storage/sqlite_store.py` 的 `MIGRATIONS` 元组，
  当前最大 `010_trade_plans`。新增迁移追加 `011_*`。
- **项目内无 LLM 客户端**：ark 集成尚未落地（`render_alerts(llm_render=...)` 目前只在测试里 mock）。
  **飞书投递用模板渲染 `plans/grounding.py::template_render`，不依赖 LLM。**
- **secrets**：`.gitignore` 已忽略 `.env` / `.env.*`（`!.env.example` 例外）。
  当前仓库**没有** `.env`。飞书凭据走环境变量，**绝不硬编码、绝不提交**。

### 既有可复用组件（只读消费，不重写）

| 组件 | 路径 | 用途 |
|---|---|---|
| 待办状态机 | `plans/actions.py`：`run_plan_cycle` / `nag_open_items` / `revive_deferred` / `validate_resume_on` | 已实现催办节拍与推迟复活 |
| 判定 | `plans/monitor.py`：`evaluate_plan` → `list[PlanAlert]`（12 code） | alert 唯一来源 |
| 渲染 + 校验 | `plans/grounding.py`：`template_render` / `verify_grounding` / `FORBIDDEN_TERMS` / `RESEARCH_PROXY_MARKER` | 卡片文案必须过校验 |
| 台账 CRUD | `plans/store.py`：`get_plan` / `list_plans` / `list_action_items` / `update_action_item` / `add_annotation` | append-only 语义已实现 |
| 取数 | `scripts/daily_nag.py::fetch_context`（实时优先，失败回退 fixture 标 `cache_fallback_used`） | 复用，别写第二套 |
| 现有投递 | `scripts/daily_nag.py::notify`（terminal-notifier → osascript 回退） | 抽 Protocol 时以它为参考实现 |
| 计划回执动作 | `api/routes/plans.py`：`done_action` / `defer_action` | 回调应复用这两个端点的逻辑，别复制 |

`PlanAlert` 字段（`plans/models.py`）：`code` / `severity`(block/remind/hint) / `rule_id` /
`evidence` / `principle_source` / `logic_provenance` / `caveat_cn` / `actionable_from` /
`data_as_of` / `next_step_cn` / `action_kind`(ENTER/EXIT/REVIEW/CLOSE_ENTER/None)。

`ActionItem` 字段：`action_id` / `plan_id` / `kind` / `source_alert_code` / `state`
(open/done/deferred/expired) / `due_from` / `nag_count` / `last_nagged_bar_date` /
`resume_on` / `closed_on` / `close_kind`。

## 3. 推什么（分级，人类已确认）

**Tier 1 · 即时单独推**
- `EXIT_TRIGGERED` — 持仓退出触发
- `INVALIDATION_BREACHED` — 失效价击穿（§14 最硬那条，必带两层标注）

**Tier 2 · 每日一条汇总卡**
- 开放待办 + `nag_count`（「这笔催你 5 天了」本身就是监督信息）
- `ENTRY_CONDITIONS_MET` 首次成立
- `PLAN_EXPIRING` / REVIEW 类待办

**Tier 3 · 不推，打开才看**
- 全部 hint 级：`ENTRY_RR_BELOW_IDEAL` / `ENTRY_RR_NOT_COMPUTABLE` /
  `MODULE_NOT_IMPLEMENTED` / `PLAN_STALE_RULESET` / `PLAN_ORPHANED`
- 回测、图表、概念解释

**Tier 0 · 绝不推**
- `DATA_STALE` 下的催办（见铁律 4）
- 任何买卖措辞

一条汇总卡，不是每个 alert 一条消息。**推送疲劳是这个功能最大的失败模式。**

## 4. 架构：投递器 Protocol（规格 v2 明文要求「待办层不动，只加投递器」）

```
plans/actions.run_plan_cycle（judgment，不改）
        │ CycleResult(alerts, nagged, revived, superseded, review)
        ▼
notify/render.py      alert/待办 -> 渠道无关的 NotificationPayload（过 verify_grounding）
        │
        ▼
notify/base.py        Notifier Protocol: send(payload) -> bool
        ├── notify/macos.py    MacNotifier（把 daily_nag.notify 搬进来）
        └── notify/feishu.py   FeishuNotifier（交互卡片）
                                   ▲
                                   │ 按钮回调
                        api/routes/feishu.py（验签 -> 复用 done/defer 逻辑）
```

**为什么这样分**：将来接微信/邮件只是再加一个 `Notifier` 实现，渲染与判定都不动。
`daily_nag.py` 只依赖 Protocol，不认识飞书。

## 5. 安全（回执 = 写操作暴露到公网，必须做对）

回执按钮会推进 plan 状态（armed→entered）、清掉催办。这意味着一个**可写端点**要能被
飞书回调到。伪造回执污染不了钱（schema 层没有资金字段），但会让**监督记录失真**——
而监督记录正是复盘素材。

必做：
1. **验签**：飞书回调签名校验（`X-Lark-Signature` / `timestamp` + `nonce` + `Encrypt Key`）。
   校验失败 → 401，不执行任何写操作。
2. **时间戳窗口**：拒绝超过 ±5 分钟的请求（防重放）。
3. **幂等**：同一 `action_id` + 同一动作重复回调只生效一次（`ActionItem.state` 已是终态则直接返回成功）。
4. **凭据只走环境变量**：`FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_ENCRYPT_KEY` /
   `FEISHU_VERIFICATION_TOKEN` / `FEISHU_RECEIVE_ID`（chat_id 或 open_id）。
   **写 `.env.example` 占位，不写真值；`.env` 已被 gitignore。**
5. **回调只暴露必要端点**：`POST /api/feishu/callback` 一个入口。
   不要顺手把 plan CRUD 也开到公网。
6. **公网暴露方式由人类决定**：内网穿透（cloudflared/ngrok）还是部署。
   **你不要自行决定并写死任何公网域名**——做成配置项，默认关闭。

> 若人类选择「先不开公网」：`FeishuNotifier` 仍可单向发（出站 HTTPS 即可），
> 卡片按钮改为**深链回本地**（`http://127.0.0.1:8000/...`）。
> 实现时把「交互回执」做成可开关的 feature flag（`FEISHU_ENABLE_CALLBACK`，默认 false）。

## 6. 交付相位与门禁

严格按 F0→F3。**前一相位门禁（pytest + ruff + mypy）不绿，不进下一个。** 每相位单独 commit。

### F0 · 投递器抽象与渲染（无网络，纯可测）
- `src/lei_signal/notify/__init__.py`
- `src/lei_signal/notify/base.py`：`Notifier` Protocol（`send(payload) -> bool`）+
  `NotificationPayload` dataclass（`title` / `body_md` / `tier` / `plan_id` /
  `action_id` / `buttons`(kind list) / `rule_ids`(供校验)）
- `src/lei_signal/notify/render.py`：`CycleResult` → `list[NotificationPayload]`。
  按 §3 分级；文案过 `verify_grounding`，不过则降级为纯 code + rule_id 文案。
  两层标注必须进 body。
- `src/lei_signal/notify/macos.py`：把 `scripts/daily_nag.py::notify` 搬进来实现 Protocol。
- `scripts/daily_nag.py`：改为依赖 `Notifier`（默认 `MacNotifier`），行为不变。

**门禁**：Tier 分级 truth table（Tier1 单推 / Tier2 汇总 / Tier3 不推 / DATA_STALE 不推）；
渲染结果过 `verify_grounding`；两层标注出现在 body；禁用词不出现；
`daily_nag` 回归（既有 P2 测试全绿，行为未变）。

### F1 · 飞书出站（单向推送）
- `src/lei_signal/notify/feishu.py`：`FeishuNotifier`。
  - `tenant_access_token` 获取 + 缓存（有效期内不重复取）
  - `POST /open-apis/im/v1/messages` 发交互卡片（`msg_type=interactive`）
  - 凭据缺失时 `send()` 返回 False 并打印可读原因，**不抛异常**（投递是 best-effort）
  - 失败重试 1 次，仍失败则降级：不阻断 `daily_nag` 后续计划
- `.env.example`：飞书环境变量占位 + 注释说明
- `scripts/daily_nag.py`：`--notifier feishu|macos|both` 参数

**门禁**：token 获取与发送**全部 mock**（不打真网络）；凭据缺失时优雅失败；
卡片 JSON 结构快照测试；`requests` 调用被正确构造（URL/headers/body）；
**测试不得包含任何真实凭据**。

### F2 · 交互卡回执（feature flag，默认关）
- `src/lei_signal/api/routes/feishu.py`：`POST /api/feishu/callback`
  - 验签 + 时间戳窗口 + URL 验证挑战（`type=url_verification` 回 `challenge`）
  - 解析 `action.value`（含 `plan_id` / `action_id` / `op`(done|defer)）
  - `op=done` → 复用 `api/routes/plans.py::done_action` 的逻辑
  - `op=defer` → **必须带 `reason_cn` + `resume_on`**（决策 4c）。飞书卡片按钮无法填复杂
    表单时，defer 按钮改为**回一条追问消息**要求用户在 skill/网页补原因，
    或用飞书表单卡片；**不得允许无原因推迟**（推迟必填原因这个摩擦是特性）
  - 幂等：终态重复回调直接成功
- `api/app.py`：`include_router(feishu.router)`（受 `FEISHU_ENABLE_CALLBACK` 控制）
- migration `011_feishu_deliveries`（可选）：投递与回执审计（`delivery_id` / `plan_id` /
  `action_id` / `channel` / `sent_at` / `callback_at` / `op` / `raw_signature_ok`）。
  **不得含数量/金额字段。**

**门禁**：验签失败 → 401 且无写操作；时间戳超窗 → 拒绝；URL 验证挑战正确回应；
`op=done` 驱动状态机（ENTER done → plan entered）；`op=defer` 缺 `reason_cn`/`resume_on` → 拒绝；
幂等（重复回调不重复推进）；`resume_on` 引用系统算不出的信号 → 拒绝并回可引用清单
（复用 `actions.validate_resume_on`）。

### F3 · 集成与门禁
- 全量 `pytest -q` / `ruff check src` / `mypy src` 绿
- `test_no_trading_execution_surface_exists` 通过；新增 schema/payload 无数量/金额字段
- 端到端（mock 飞书）：`run_plan_cycle` → render → FeishuNotifier.send → 模拟回调 → 待办状态推进
- 更新 `docs/plan-agent-supervisor-v1.md` 的 v2 路线第 1 项状态
- **人类手动验收步骤写进 README 或本文件附录**（创建飞书自建应用、填环境变量、
  内网穿透、发一条测试卡）——你不要代替人类创建应用或填真值

## 7. 工作纪律

- **TDD for 渲染与验签**：F0 分级 + F2 验签先写测试（反例比正例重要），再写实现
- **照抄既有范式**：路由抄 `api/routes/plans.py`；store 抄 `plans/store.py`；
  迁移抄 `sqlite_store.py` 的 `010_trade_plans`
- **只追加，不改既有行为**：`plans/{monitor,actions,drift}.py`、`rules/`、
  `compose/pipeline.py`、`web/`（前端）**一个字都不改**。
  `daily_nag.py` 只做「改依赖 Protocol」这一处重构，行为不变
- **不打真网络**：所有飞书调用在测试里 mock
- **每相位 commit**，message 写清相位与门禁结果
- **遇到歧义停下来问**：尤其「是否开公网回调」「defer 如何收原因」这两处涉及安全与
  产品语义的决策，不要擅自定

## 8. 不要做的事

- 不下单、不接券商、不记股数/金额/成交价/账户
- 不改判定层、不新增判定逻辑、不新增阈值
- 不碰 LLM（模板渲染足够；ark 集成是另一条独立任务）
- 不碰前端（React 面板归 v2 第 3 项）
- 不引入新第三方 SDK（用 `requests`）
- 不硬编码凭据、不提交 `.env`、不在测试里放真实 token
- 不自行决定公网暴露方式、不写死公网域名
- 不允许无原因推迟（决策 4c：`reason_cn` + `resume_on` 必填）
- 不推 `DATA_STALE` 催办

## 9. 开工

从 F0 开始。每相位完成、门禁绿、commit 后，简报：做了什么 / 门禁结果 / 下一相位。
门禁红了就停在红的地方报错，不要带着失败的测试往下走。

**开工前需人类确认的两点**（先问，不要猜）：
1. 飞书用**自建应用**（可发交互卡 + 收回调，需 app_id/secret）还是**自定义机器人 webhook**
   （只能单向发）？→ 决定 F2 能否做
2. 是否开公网回调？不开则 F2 做成深链 + feature flag 默认关
