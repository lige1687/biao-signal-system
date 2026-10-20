# 两个已封存示例：同一条标准流程如何按问题类型分流

【来源：执行 agent 交付，**待主控复核的提案**】日期：2026-09-17。
本文只用两个**已封存**的实例说明 workflow-map 的走法。**本轮没有重新运行
任何命令**；所有入口表述仅指**路径与参数已静态核查**（哈希见
`sources-and-checks.json`），参数来源指向冻结协议原件。合成例的全部产物是
算法验证，**不是任何真实价值证据**。
v1.1（2026-09-17）：按主控复核 R1–R3 修订——真实/合成入口分开、示例 B 改绑
closeout 目录终版协议与 v2 期望、S1–S3 状态更新为已收口；修订前原字节存
`history-v1/`。

## 例 A：双均线 B1——真实数据上的"单标的二元状态历史描述"（已限定收口）

**问题类型**：单标的、二元状态、时间关系（状态成立/不成立之后一段时期的
价格变化差）→ 走 workflow-map §2 第二行，**不做横截面 IC**（请求 IC 会被
工具判 `not_applicable`）。

| 流程步 | 本例实际走了什么 | 权威绑定 |
|---|---|---|
| 1 定问题/对象 | 候选卡 `candidate:lei.dual_ma.bull_state@draft-1`（未进登记表）；问题合同固定 `theme=trend, type=state_signal, use=historical_description, lookback=20, e_offset=1, x_offset=22` | 候选卡：`docs/experiments/raw/factor-research-workbench-v1-2026-09-14/candidate-card-dual-ma-bull-state-draft-1.md`；factor-unit-usage §2 |
| 2 数据资格 | B0 资格链：510300 共 1,558 交易日原始响应离线复用（缺失 0、非交易日 0）；真实目标闸 `target=blocked` + `manual_target_review_required`（供应商前复权价，含分红等价未核） | `scripts/check_factor_unit_readiness.py --contract PATH --out NEW_DIR`（退出 0/2/3）；主控 T1–T4 关闭：factor-unit-four-fixes-controller-2026-09-15 |
| 3 冻结协议 | `protocol-v1.0.1.json`（SHA `00a16465…`；v1.0.0 `63617173…` 为失败版，源码不可恢复，保留为历史缺口） | `docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/` |
| 4 手算测试 | 单测 40 项（description_core/b1_contract/b1_description/CLI）+ 既有 89+19 项相关测试，主控实跑通过 | b1-closeout §4 实跑记录 |
| 5 运行 | `scripts/run_b1_dual_ma_description.py` → `factor_unit/b1_description.py::describe_b1`（真实历史描述入口；与合成入口 `state_description.describe_states` 共用 `description_core` 纯计算层，但**入口不可互换**——describe_states 自述仅收 synthetic、真实模式拒绝，describe_b1 自述不调用 describe_states、不冒用 synthetic 身份） | run-02 在 raw 目录；路径与参数已静态核查，本轮未执行 |
| 6 独立复核 | 主控从封存观察表**独立重汇总**，主要数字全一致；收口时再核 38 结果文件 + 7 规范原件 | b1-controller-review-2026-09-16；b1-closeout-controller-2026-09-16 |
| 7 证据登记 | 报告与主控复核均落 `docs/experiments/` 并登记 | b1-dual-ma-first-real-description-2026-09-16.md |
| 8 生产许可 | 无；主控裁决明确"未接受预测有效、统计可靠、交易赚钱、含分红已核" | b1-closeout §5 |

**分流后的第二段（可靠性体检）**：同一份封存观察表再走一次第 3–6 步——
新协议 `factor-evidence-reliability@1.0.0`（SHA `769a3501…`）→
`scripts/run_factor_evidence_reliability.py`（真实入口只有 main；直接
`run_analysis` 仅收显式合成）→ 主控独立复算逐年/留一年/等权/重抽四类数字
→ 裁决"证据不足以支持稳定优势，也未证无效"。R1–R4 返修主控接受
（116 项回归 + ruff）；S1–S3 收尾经替代任务完成，主控 §10 限定收口
（2026-09-17：118 项回归 + ruff、158 项独立检查通过；保留快照核验超预算
3/1 的流程违规记录，不称全程合规）。当前 `runner.py`/`stability.py`
工作区 SHA 与 §10 记录的收口后 SHA 逐字一致。此收口不增加因子有效性
证据或真实运行权限（§10.3）。

**本例证明的流程能力**：真实数据可以走完 1–7 步且每一步留痕可核。
**本例没有的结论**：稳定优势、预测能力、交易价值、含分红财富等价。

## 例 B：纯合成横截面——factor_lab 的"排名吻合度"算法验证（限定收口为合成原型）

**问题类型**：同日多标的连续分数 vs 后续结果排名 → 走 workflow-map §2
第一行 `cross_section_ic`。**输入是人工编造的合成价格面板**，只回答
"算法算得对不对"，不回答任何市场问题。

| 流程步 | 本例实际走了什么 | 权威绑定 |
|---|---|---|
| 1 定问题/对象 | 直接引用登记对象（如 `trend.distance50@1.0.0`）；协议 `kind=predictive_diagnostic`、`diagnostics.type=cross_section_ic`、`data_mode=synthetic` | definitions.v1.json（本轮核到该卡存在）；factor-lab-usage §一/§二 |
| 2 数据资格 | 走**合成声明**路径：价格尺度/日历/时间/币种在协议里声明；特征时间语义为"合成即时可得假设"，未做逐行历史时点核验 | factor-lab-usage §二.3 返修后语义 |
| 3 冻结协议 | **终版绑定在 closeout 目录**：`docs/experiments/raw/factor-lab-final-closeout-2026-09-15/protocol-{1-numerical,2-state,3-attribution}.json`（本轮逐份静态核查：version 1.2.0、各 15 个 code_identity 键、`data_mode=synthetic`、`expectation_source` 冻结独立期望文件哈希）；R2 纪律：必查集合唯一权威为独立期望产物，协议携带 `required_checks` 即拒，容差 ∈ {0,1e-9,1e-6,0.01} | 历史原件在 `docs/experiments/raw/factor-research-workbench-v1-2026-09-14/`（保留为历史，不与终版代码混配） |
| 4 手算测试 | closeout 目录 `independent-expectations-v2.json` 的 `protocol_expectations[案例]` 段（numerical/state/attribution 三案例，23/28/11 项；由 `derive_expectations_v2.py` 独立算术产出，不 import 被测代码）；期望与实现值级不一致 → 退出 1 不放行 | 终版执行报告 §S2；factor-lab-usage §二.5 |
| 5 运行 | `python3 scripts/run_factor_lab.py --protocol <closeout>/protocol-{1-numerical,2-state,3-attribution}.json --out <新目录>`（终版执行报告第 122–124 行同款三条；脚本路径与协议参数已静态核查，本轮未执行；退出码 0/1/2/3） | 产物：manifest、values_*、diagnostics_*、validation、attribution、quality、summary（标题常驻"合成算法验证…"） |
| 6 独立复核 | 主控实跑 145 项测试通过；直接调用函数验证指定反例；15 个代码键按原字节归档核验；三类正式产物（19+15+5 份）哈希与清单一致 | factor-lab-final-controller-decision-2026-09-15 §1/§6 |
| 7 证据登记 | 执行报告与主控裁决落 `docs/experiments/` | factor-research-workbench-v1-2026-09-14.md 等 |
| 8 生产许可 | 无；裁决保留为"仅供合成研究的通用原型" | 终版裁决 §2 |

## 两例对照：流程相同，分流点在哪

| 分流点 | 例 A（B1 真实状态） | 例 B（合成横截面） |
|---|---|---|
| 问题类型 | 单标的二元状态的时间关系 | 多标的连续分数的排名吻合 |
| 诊断入口 | `b1_description.py::describe_b1`（真实B1，共同合法集合，逐年分列；`describe_states`仅限合成） | `diagnostics.py::evaluate_predictive` 的 `cross_section_ic` |
| 数据资格路径 | 供应商证据链 + 真实目标闸（未过闸只描述价格变化） | 合成声明路径（协议自述合成身份） |
| 结论强度 | 真实历史**描述**，证据不足 | 算法**正确性**，零市场含义 |
| 主要缺口 | 时点逐行核验、稳健推断、第二载体 | 真实输入消费者、一切有效性 |

**共同纪律**（两例一致，是新对象入场时照抄的部分）：协议冻结身份与哈希、
独立期望先于运行、输出目录防覆盖、主控书面复核、报告一句话结论 + registry
登记、研究结论不自动产生生产/交易授权。

**不可照抄的部分**：例 A 的输入绑定 510300 固定快照，换标的必须新建协议版本
与资格链（不能改路径复用，factor-evidence-usage §4 同口径）；例 B 的
`data_mode=synthetic` 不可被字符串改写成真实身份（factor-unit-usage §3 已拒绝
此类旁路）。
