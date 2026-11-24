# 公司行动时间链统一框架（A1 / G3，v1.0.0，2026-09-19）

> 大白话一句话：一条基金分红/拆分/停牌消息要问四个时间——事情什么时候发生、
> 公告什么时候发出、我们什么时候能拿到、市场什么时候生效。这份文档把这四个
> 时间连成一条链，并规定哪些检查机器能自动做、哪些必须人来做（比如"这个来源
> 是不是真的官方"、"历史上到底拿不拿得到"），防止回测偷看未来。

- 契约来源：`docs/research/proposals/factor-next-phase-4dir-2026-09-19/qualification-path-contract.md`（A1）
- 上游：`./evidence-model.md`（三层来源）、`./time-field-semantics.md`（四时间字段）
- 已核实例：`docs/experiments/fixed-etf-evidence-integration-2026-09-13.md`
  已核 6 条 515300 分红官方公告（event_id：
  `515300-cash_dividend-2023-12-19 / 2024-06-21 / 2024-09-20 / 2024-12-03 /
  2025-06-17 / 2025-09-18`，`evidence-bundle-v1.2.json` 中
  `time_evidence.kind=in_document_date_bound, bound=not_before`）——本框架的
  Tier1 实例基准。
- 本阶段只定义框架与清单，不改任何资格闸门代码。

## 1. 时间链结构

```
action event（事件发生）
      │
      ├── announcement（对外披露）──► available_at（系统可获得）──► decision_at（决策使用）
      │                                      ▲
      └── effective date（市场生效）──────────┘（无固定先后，分别举证）
```

四个环节与四时间字段的对应（唯一口径，见 time-field-semantics.md）：

| 链上环节 | 字段 | 证据义务 |
|---|---|---|
| action event | `event_time` | Tier1 公告内容字段；可 null |
| announcement | `publication_time` + `publication_bound` | Tier1 官方原文；Tier2 禁止携带 |
| 系统可获得 | `available_at` | Tier1 仅 `bound=exact`+`availability_scope` 覆盖取数渠道时可填；Tier3 用户口径；缺证必须 null |
| 市场生效 | `effective_time` | Tier1 公告内容 或 Tier2 规则推导（`derived_from_rule=true`+规则出处） |

链上硬时序（违反即负向用例 N9/N10）：

- `event_time ≤ publication_time`（结果类公告；预告类可反，须 bound 注明）；
- `publication_time ≤ available_at`（先披露才可能获得）；
- `available_at ≤ decision_at`（决策不得早于可获得——动量协议既有约束）；
- `publication_time（安排公告） ≤ effective_time`；
- `effective_time` 与 `available_at` **无固定大小关系**（停牌可当日盘中才知），
  禁止互推。

## 2. 自动核清单（机器可执行，schema+脚本层）

对应 `available-at-evidence.schema.json` 与
`docs/experiments/raw/factor-a1-2026-09-19/validate_negative_cases.py`：

| # | 检查项 | 拒绝条件 |
|---|---|---|
| A1 | 字段完整 | tier 决定必填集缺失（Tier1 缺 source.sha256/availability_scope 等） |
| A2 | tier 互斥 | 同一行动出现两个 tier 记录（N1） |
| A3 | 时序 | publication_time > available_at、available_at < publication_time、decision_at < available_at（N9/N10） |
| A4 | hash | Tier1 source.sha256 缺失或格式错（非 64 位十六进制）；登记后原文改动导致 hash 失配 |
| A5 | 来源链接 | Tier1 source.locator 非 URL 且非 `docs/` 仓库路径；Tier2 rule.reference 非 URL 且非 `docs/`、`configs/` 路径 |
| A6 | 规则推导 | Tier2 缺 `derived_from_rule=true` 或缺 rule.statement/reference；Tier2 携带 publication_time/available_at（N7） |
| A7 | 语义串扰 | `bound=not_before` 时 available_at 非 null（N5）；effective_time 填入 available_at（N6：生效日不算到达证据） |
| A8 | tier0 纯净 | tier0 记录夹带任何 tier 证据字段（N8） |
| A9 | 时间格式 | 裸本地时间串、无时区语义（N4；默认 Asia/Shanghai） |

## 3. 必须人工清单（机器不能裁决）

| # | 检查项 | 为什么机器不能做 | 责任记录方式 |
|---|---|---|---|
| H1 | 来源真实性 | URL/PDF 是否确为官方一手（交易所/基金公司/法定披露渠道），二手聚合页伪装成官方是最常见风险 | 复核人在 bundle 记录留 `facts_verified` + 复核人标识 |
| H2 | 历史可获得性解释 | 「当时系统/公开渠道是否真的能拿到」取决于历史渠道状态，无机器可查的统一接口 | `historical_availability_verified` 字段（fixed-etf 6 条当前全为 false，即此清单未过） |
| H3 | 无公告裁决 | 行动确无官方公告（如某些停牌），还是"未找到"——两者必须区分，缺证不等于无证 | 人工裁决记录：`explicit_missing`（查过、确无）vs `not_found`（未查到、待查） |
| H4 | Tier3 用户供料受理 | 仅历史缺口+用户主动提供；用户身份与口径确认 | `user_supplied/provided_by/acknowledged_by_user`，A1/A2 验收前下游一律拒绝（N3b） |

## 4. 与盘点结果的衔接

21 条既有行动按本框架盘点（`normalized-actions-inventory-2026-09-19.json`）：
8 条已到 Tier1 且 publication_time 有 not_before 下界（含 6 条已核 515300 分红）、
1 条 Tier1 仅内容层（515880 拆分公告落款缺失）、12 条 tier0；**21/21 的
available_at 均为 null**——即 H2（历史可获得性）是全部行动共同缺的人工环节，
也是 research_signal 停在 conditional 的直接原因。补证路径（A2，另行授权）：
优先对 8 条 Tier1 下界记录补 H2 裁决与到达证据，再逐条处理 tier0 的 Tier1 原文检索。
