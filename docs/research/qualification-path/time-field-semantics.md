# 四时间字段语义表与负向校验（A1 / G2，v1.0.0，2026-09-19）

> 大白话一句话：四个「时间」各管一件事——事情什么时候发生、消息什么时候公布、
> 我们什么时候能拿到、市场上什么时候生效。任何一个填到另一个的格子里，就是
> 「把还没公布的消息当作已知」，回测会偷看未来，所以混淆一律拒绝。

## 1. 语义表

| 字段 | 含义（唯一口径） | 典型来源 | 允许为 null | 与其他字段的时序约束 |
|---|---|---|---|---|
| `event_time` | 事件本身发生的时点（权益登记、拆分完成等） | 官方公告内容字段 | 是（缺原文时） | `event_time ≤ publication_time`（结果类公告：事件先于公告；预告类可反，需 bound 注明） |
| `publication_time` | 消息**对外披露**的时点；必须带 `publication_bound`（not_before/exact） | 官方公告落款/送出日/交易所披露时刻 | 是 | `publication_time ≤ available_at`（先公布才可能获得） |
| `available_at` | **本系统**可获得该消息的时点 | Tier1 exact+scope 覆盖 / Tier3 用户口径 | **是（缺证必须 null，不伪造）** | `publication_time ≤ available_at`；决策侧 `decision_at ≥ available_at`（动量协议既有约束） |
| `effective_time` | 市场**生效**时点（除息日/拆分日/停牌日） | 公告内容或 Tier2 规则推导 | 是 | `publication_time(安排公告) ≤ effective_time`；与 available_at **无固定大小关系**，禁止互推 |

要点：

- fixed-etf 已核公告的落款/送出日只是 `publication_time` 的**下界**（not_before），
  不是 `available_at`。从「有公告」跳到「系统已知」中间还差 availability_scope
  与到达证据——这正是 research_signal 卡在 conditional 的原因。
- `effective_time` 与 `available_at` 方向都可能（公告先于生效=正常；停牌当日盘中才
  知=available_at 晚于生效起点），所以只能分别举证，不能由一个推另一个。

## 2. 负向校验（混淆即拒绝）

机器可执行部分落在 `available-at-evidence.schema.json`（tier 互斥、Tier2 禁
publication_time/available_at、Tier3 必带 user_supplied 等）；本表是完整规则清单，
编号 N1–N10，其中 N1–N8 已由 schema+校验脚本覆盖（见
`docs/experiments/raw/factor-a1-2026-09-19/validate_negative_cases.py` 与运行日志），
N9–N10 是语义级检查，进入 G3 自动核清单。

| # | 混淆/违规形式 | 拒绝方式 |
|---|---|---|
| N1 | 同一行动出现两个 tier（如 Tier1+Tier2 并存） | schema allOf 互斥拒绝 |
| N2 | Tier1 缺 `source.sha256` 或缺 `availability_scope` | schema required 拒绝 |
| N3a | Tier3 缺 `user_supplied=true` | schema const 拒绝 |
| N3b | A1/A2 验收前出现任何被消费的 tier3 记录 | 下游消费拒绝（闸门侧不动，本阶段记录为待执行规则） |
| N4 | `event_time`/`publication_time` 无时区语义（裸本地串） | schema pattern 要求日期或带时区时间戳；跨日事件按 Asia/Shanghai 登记 |
| N5 | Tier1 记录在 `publication_bound=not_before` 时填非 null 的 `available_at` | schema tier1_official.allOf 强制：bound 非 exact 时禁止非 null available_at（规则 R5 已结构化） |
| N6 | `effective_time`（除息日等）被填进 `available_at` 字段 | 语义规则 R6：available_at 必须有到达证据（Tier1 exact 或 Tier3），生效日不算到达证据 |
| N7 | Tier2 携带 `publication_time`（把规则推导日伪造成公告时间） | schema additionalProperties:false + 显式 not 拒绝 |
| N8 | tier0 记录夹带任何 tier 证据字段 | schema not 拒绝 |
| N9 | 时序倒挂：publication_time > available_at，或 available_at < publication_time | 自动核清单时序项（G3） |
| N10 | decision_at < available_at（决策早于可获得） | 动量协议既有约束，自动核清单继承 |

## 3. 与既有协议的一致性

动量 v1.0.7 协议写明「未知 available_at 保留 null」「decision_at 不得早于
available_at」「除息连接不等于当天分红可花」——本表是其证据层的展开，无冲突；
「除息连接不等于当天分红可花」即 N6 的协议表述。
