# available_at 三层来源证据模型（A1 / G1，v1.0.0，2026-09-19）

> 大白话一句话：这份文档定义「一条基金分红/拆分/停牌消息，到底是什么时候能被我们
> 系统正当知道的」，并把「知道的时间」按证据强弱分成三档——官方公告原文（最硬）、
> 按规则推出来的时间（中等，且只推生效日、不推公告日）、用户主动补的料（只许补
> 历史旧账）。没有证据就如实记 unknown，不许编。

- 契约来源：`docs/research/proposals/factor-next-phase-4dir-2026-09-19/qualification-path-contract.md`（A1）
- schema 机器可执行版：`./available-at-evidence.schema.json`（同一对象的两份表达，语义以本文档为准、校验以 schema 为准）
- 本阶段**只建模与盘点，不改任何资格闸门代码，不宣称资格解除**。

## 1. 为什么需要这个模型

动量原型 v1.0.0–v1.0.7 冻结协议已写明：冻结输入缺历史 available_at，21 条公司行动
的 available_at 全部为 unknown（`docs/experiments/raw/research-momentum-prototype-2026-09-13/protocol-v1.0.7.json`）。
research_signal 因此停在 conditional：系统无法证明「这条行动消息在历史上什么时候可被获得」，
也就无法证明历史回看没有偷看未来。本模型是补证的第一步：先把「什么才算证据」定清楚，
再谈补证（A2 小样本补证另行授权）。

## 2. 三层来源（tier）

一条行动的 available_at 证据**必须落到且只落到一个 tier**（schema 用 allOf/if-then 强制互斥）。

### Tier1 官方披露（preferred）

「官方」= 交易所、基金公司、法定信息披露渠道的一手文件（公告 PDF/页面原文）。
二手聚合页（如东方财富 fundf10 行情数据页）**不是 Tier1**。

必填字段（与 schema `tier1_official` 一一对应）：

| 字段 | 含义 | 备注 |
|---|---|---|
| `event_time` | 事件本身发生的时点 | 分红=权益登记日口径的事件；无则填可得的最早官方事件时点 |
| `publication_time` | 对外披露的时点 | 必须同时给 `publication_bound` |
| `publication_bound` | `not_before`（落款/送出日，只是下界）或 `exact`（有发布时刻证据） | fixed-etf 已核 6 条 515300 分红公告均为送出日 ⇒ 目前只有 `not_before` |
| `source` | 官方原文定位（URL 或仓库内路径）+ `sha256` + 可选页码/抓取日期 | |
| `availability_scope` | 该披露在什么渠道/范围可被获得 | 例：「基金公司官网公告栏，公开发布」 |
| `available_at` | 仅当 `publication_bound=exact` 且 `availability_scope` 覆盖系统取数渠道时才可填；否则 **null** | 这是 Tier1 的核心纪律：有原文 ≠ 知道精确到达时间 |

先例实例（G3 引用）：`docs/experiments/fixed-etf-evidence-integration-2026-09-13.md`
已核 6 条 515300 分红官方公告（MO7U/QXY9/SAOV/QVEK/HGW2/NN2J），
`evidence-bundle-v1.2.json` 中 `time_evidence.kind=in_document_date_bound, bound=not_before`，
即 Tier1 已达但 `available_at` 仍为 null（只有下界）。这正是本模型要显式表达的状态。

### Tier2 规则推导

「公告发布后第 N 个交易日生效」类规则化时间。必填：

- `derived_from_rule=true`（schema const，缺失或 false 即拒绝）；
- `rule`：`statement`（规则原文语义）+ `reference`（规则出处：官方规则页 URL 或仓库内
  权威文档路径）+ 可选 `rule_id`；
- `effective_time`：推导出的生效时点；
- `derivation_inputs`：推导输入（如公告落款日、交易日历版本）。

**红线**：Tier2 记录**禁止携带 `publication_time` 与 `available_at`**（schema
`additionalProperties:false` + 显式 `not`）。规则只能推导生效日，不能推出公告何时
发出；把推导日伪造成公告时间是最严重的负向用例（见 G2 语义表 N7）。

### Tier3 用户供料（本阶段只定义不使用）

仅限**历史缺口**且**用户主动提供**。必填：`user_supplied=true`、`provided_by`、
`provided_at`、`scope=historical_gap_only`。不得与系统发现的证据混同；生产使用还需
`acknowledged_by_user=true`（A1 阶段 schema 允许该字段为 false，但任何下游消费方
在 A1/A2 验收前应拒绝一切 tier3——负向用例 N3b）。

### tier0 缺证（如实 unknown）

`tier=0, basis=missing`。21 条行动的当前缺层盘点大量处于此档，这是现状的如实表达，
不是失败状态；伪造任何一层才是失败。

## 3. 字段与三层的关系总表

| 字段 | Tier1 | Tier2 | Tier3 | tier0 |
|---|---|---|---|---|
| event_time | 必填 | — | 可选 | — |
| publication_time(+bound) | 必填 | **禁止** | 可选 | — |
| source+sha256 | 必填 | —（规则出处走 rule.reference） | 可选 | — |
| availability_scope | 必填 | — | 可选 | — |
| derived_from_rule+rule | — | 必填 | — | — |
| user_supplied+provided_by/at/scope | — | — | 必填 | — |
| available_at | 仅 exact+scope 覆盖时可填 | **禁止** | 可填（用户口径） | — |
| effective_time | 独立字段 | 必填 | 可选 | — |

## 4. 升降级规则

- tier 不可叠加：同一条行动同时出现两个 tier 记录即 schema 拒绝。
- 升级（0→1/0→2）必须产生新证据记录并在行动台账中留痕（来源/hash/推导依据），
  不覆盖旧记录。
- 降级（发现原文失配、规则不适用）记入 conflicts，回 tier0，不删历史。
