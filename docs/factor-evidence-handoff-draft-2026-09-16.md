# 因子证据交接约定（草案，待双方核实）

> 2026-09-16 · Agent 体验连续讨论一轮 · 交付物 3
> **本文是待因子负责人与 Agent 侧双方核实的约定草案，不是已经上线的接口。**
> 当前不创建空 API、不假返回、不固定 mock 生产结果、不建因子新面板或打分权重；
> 文中样例只作说明且明确未实现。因子进入生产判定、过滤、排序或资金建议必须另行主控裁决；
> 基本面/消息面保持叙事层。

## 0. 口径（先说清，不混淆）

因子是用于描述或区分市场情况的一项测量。**因子值、模型预测、历史交易胜率是三样不同的
东西；因子读数高不直接等于胜率高。** 交接字段设计必须让这三者无法被混装。

## 1. 现有内容（只读勘察，2026-09-16；证据：文件:行号）

- 唯一接口 `GET /api/factors/panel`（`src/lei_signal/api/routes/factors.py:21-27`，27 行）：
  只读磁盘冻结快照 `$LEI_CACHE_ROOT/factor_panel_snapshot.json`，不重算；未预计算 404。
  服务层 `src/lei_signal/api/factor_service.py:41-49`（300s TTL，标 research_proxy）。
- 产出方 `scripts/precompute_factor_panel.py` → `src/lei_signal/market_context/factor_panel.py`
  （原子写 443-448 行；扫描缓存全部 `*.bars.parquet` 345 行）。
- 因子元信息 `FACTOR_META`（factor_panel.py:54-153）：6 因子各带 label/formula/verdict/
  verdict_level(pass|weak|inverse|fail)/evidence(实证留痕)/usage(用法与禁区)。评级是
  2026-08-27 本地实证**静态留痕**，前端与调用方不得另造评级。
- 缓存实物：`factor_panel_snapshot.json`（2026-09-04 生成，33 标的+20 板块）；
  `factor_lab_snapshot.json`（2026-09-06，因子实验台：组合回测+难度分级+估值分位，
  均 research_proxy）——**注意：开发仓后端没有 /factors/lab 路由，`web/src/api/client.ts:633`
  的 `factorsApi.lab` 是悬空引用**（疑似合并时后端未并入，需澄清是补路由还是删死代码）。
- 单测 `tests/unit/test_factor_panel.py`（23 用例）。
- **因子数据目前不进入 Agent 讨论链路**：`plans/llm_context.py::build_discussion_context`
  无任何 factor 字段；routes/agent.py 中 factor 仅指回测指标 profit_factor。

## 2. 缺失内容（相对「Agent 讨论时可引用经过核实的因子证据」）

1. 因子读数无证据卡：快照行只有裸数值+as_of+notes 字符串，无出处/哈希/健康度结构；
2. 评级无版本化引用：evidence 是自由文本，未绑定 source_path+source_hash+source_version；
3. 无按对象+因子的只读证据端点（只有整面板一个端点）；
4. 无「当时可获得时间」available_at（契约里此字段存在但当前全为空）；
5. 历史统计只有散文，无结构化事件定义/入场退出/评价期限/样本量字段；
6. factor_lab_snapshot 前后端断层（见上）。

## 3. 因子负责人当前进度与需补充内容

运行仓库分支 `codex/factor-unit-research-20260915`（工作全部未跟踪新文件，不污染既有代码）：

- 已有：factor_lab 通用研究引擎（合成数据原型收口）；factor_unit 模块（study_contract
  的 {path, sha256} 结构化证据、session_close/available_at 时点区分、METADATA_REQUIRED
  21 键）；**2026-09-16 B1 双均线首次真实历史描述收口**（510300，1516 有效观察，
  真组 590 次后续 21 收盘间隔均值 +1.04%，假组 926 次 +0.34%；逐年方向不稳定 2 正 5 负；
  已声明「历史关联描述，不是预测能力证明，不构成买卖依据」）。
- 阶段判断：研究工具链+首个候选因子单标的历史描述完成；**尚无任何因子获得有效性认证
  或生产授权**；尚不存在面向 Agent 讨论链路的证据交接约定（factor_lab METADATA 与
  data_provenance 契约两套字段未对齐——正是本文要解决的）。
- 负责人需补充：①候选因子定义卡路径与哈希；②B1 类研究产出到 §5 字段的映射确认；
  ③available_at/交易日历等「当时可获得性」的登记责任；④factor_lab_snapshot 断层的处理意见。

## 4. 证据契约真实字段（`src/lei_signal/data_provenance.py`，SCHEMA_VERSION="provenance/1.2"，逐字）

- **EvidenceRef**（357 行）：`id, source_path, source_hash, source_version, status, window,
  statistic_kind, strategy_scope, limitations, compatibility, note`；compatibility 枚举
  exact/reference/unknown/incompatible；工厂 `evidence_ref()`（441 行）、
  `winrate_evidence_ref()`（595 行）；使用例 `dca/service.py:89-97`。
- **MarketDataRef**（481 行）：`source_id, instrument_id, market, observed_at, available_at,
  generated_at, last_valid_at, health, reason, calendar_ref, as_of_cutoff, source_policy_ref,
  reference_lag_trading_days, extra`；health 枚举 fresh/stale/incomplete/missing/unknown
  （unknown 永不当作当前）；使用例 `dca/state.py:198-214`。
- **RuleRef**（531 行）：`rule_id, version, config_path, config_hash, definition_ref,
  fallback_note`；使用例 `dca/service.py:99-102`、`copilot/backtest_requests.py:281`
  （规则账本整本冻结+sha256+副本）。
- 配套：`FreshnessAssessment`/`assess_freshness()`（245/266 行）、`file_source_hash()`（82 行）。

## 5. 建议的证据交接字段（组合 §4 真实字段；一条 = 一个因子在一个对象上的一次读数）

| 交接需求 | 字段（真实名字） | 取值来源 |
|---|---|---|
| 对象身份与类型 | `instrument_id`、`market`（MarketDataRef） | 快照行 code/group 映射 |
| 因子定义及版本 | `id`（EvidenceRef，形如 `factor:rv_pct`）、`source_version`、`definition_ref`（RuleRef） | FACTOR_META 键 + STUDY_DATE；factor_unit 用 `candidate:lei.dual_ma.bull_state@draft-1` 这类对象引用 |
| 数据来源 | `source_id`、`source_path`、`source_hash` | 快照文件路径 + `file_source_hash()` |
| 数据截止日 | `last_valid_at` | 快照行 as_of |
| 当时可获得时间 | `available_at`（无依据 = null + reason，**不猜**） | 负责人补登记 |
| 计算时间与窗口 | `generated_at`、`window` | 快照 generated_at；FACTOR_META formula 参数 |
| 数值/单位/方向含义 | 数值走 `extra`（先例 dca/state.py:212）；单位方向沿用 FACTOR_META label/formula/usage；统计类型 `statistic_kind` | 快照行 |
| 缺失/过期状态 | `health`、`reason`、`as_of_cutoff`、`reference_lag_trading_days`（经 `assess_freshness()`） | 现 notes[] 迁移为结构化 |
| 验证材料与研究状态 | `status`（照抄账本不推断）、`limitations`、`compatibility`（默认 unknown） | FACTOR_META verdict 映射 status；evidence 文本入 limitations 或挂报告哈希 |
| 适用对象/市场环境 | `strategy_scope`（现有 STRATEGY_* 枚举） | FACTOR_META usage 解析 |
| 已知限制 | `limitations`、`note` | FACTOR_META usage 禁区（如「ADX 禁用于过滤排序」） |
| 历史统计（如有） | 不单独立类：`window + statistic_kind + limitations`；事件定义/入场退出/评价期限/样本量/研究来源作为 limitations 结构化子段，或 source_path 指报告 + source_hash | 例：B1（510300，e=t+1 收盘，x=t+22 收盘，真组 n=590/假组 n=926） |

纪律沿用现有契约：compatibility 默认 unknown；available_at 无依据 = null；快照序列化即冻结、
历史不重读。**没有事件定义+入场退出+评价期限+样本量+研究来源五件套的统计，不称胜率。**

## 6. 未来读取方式（建议，待核实）

1. Agent 只经现有后端只读服务取**组装好的证据**（在 `/api/factors` 路由族下按
   instrument_id + factor id 出只读端点，由 FactorPanelService 层组装成 §5 结构）；
   讨论链路（llm_context）只注入证据摘要，不读原始 parquet、不 import factor_panel 计算函数。
2. 前端不直连因子计算器；维持「重算需跑 scripts/precompute_factor_panel.py」的人工/定时
   离线触发；新端点同样只读冻结快照。
3. 聊天不默认启动昂贵全量计算；factor_lab/factor_unit 研究引擎只在研究任务内运行，
   不进聊天路径。
4. 顺手项：`factorsApi.lab` 悬空引用要么补只读路由、要么删前端死代码（主控定）。

## 7. 下一步

首批真实输出（候选因子定义卡 + B1 类描述的研究边界）经因子负责人确认后，再提出具体
适配任务（端点形状、摘要进讨论材料的字段子集、降级文案）。本文随
`docs/experiments/agent-experience-continuity-2026-09-16.md` 一并交主控复验。
