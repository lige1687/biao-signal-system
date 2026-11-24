# docs 导航与目录地图


当前权威来源（新任务适用，2026-09-29）：
- `~/Desktop/lei signal doc/LEI 技术交易体系.md`：技术思想与交易语义的最高来源。
- `~/Desktop/lei signal doc/LEI 技术实现.md`：当前计算、回测与输出定义的实现依据。
- `configs/strategy-documents.v1.json`：固定来源与用户已确认指纹，不保存正文。

新研究先读两份桌面文档并记录实际 SHA-256；`docs/trading-spec-v1.md` 只在复现
冻结 V1 实验或明确标注“历史对照”时使用。研究规范管理“如何检验”，不改写权威源。
两份源文件只读；指纹变化不得据此扩大或缩小因子范围。新增、删除或改变技术含义，
须先说明受影响的策略层、因子对象及历史实验可比性，等待用户确认；不自动更新确认指纹。
冲突须先区分策略语义、实现形式和阈值版本；规则账本不能反向改写体系含义。

> 2026-09-16 目录治理后重写：导航 + 归置入口。新文档放哪、什么做完要删，
> 权威规约见根目录 AGENTS.md「文件归置规约」；本页是它的展开地图。

## 日常先看这几个入口

| 你要解决的问题 | 当前入口 |
|---|---|
| 现在有哪些任务，谁负责，做到哪里 | [阶段交接入口](ops/work-progress/README.md)；[实时进展](progress/) 有部分任务较新的续写，按任务名核对时间和负责人 |
| 新研究采用哪套规范 | [当前规范索引](research/current-standards.json)，再按其中路径读取 |
| 已经研究过什么，结论是什么 | [实验报告索引](experiments/INDEX.md)；分类以 `experiments/registry.json` 为准 |
| 已经取得哪些金融/universe数据，外盘在哪里 | [已获取数据清单](ops/acquired-data-catalog.md)；[机器位置索引](ops/acquired-data-catalog.json)，先复用再补缺 |
| 想学已有方法 | [文献学习入口](literature-learning/README.md) |
| 系统还有哪些改进目标 | [系统待升级说明](okr/README.md)，实际进度以服务端台账为准 |
| 历史资料怎么保留，哪些可考虑清理 | [本次整理清单](ops/repository-housekeeping-2026-10-03.md) |

旧计划、交接提示词、传输副本不作为当前任务入口。需要复现或交接时，再从具体任务记录进入。

## 两处进度文档怎么读

`ops/work-progress/` 是阶段交接记录，`progress/` 是部分任务的实时续写。两处同名不代表前一份已经无用：阶段记录保留了设备、分支和验证历史，实时记录可能有较新的状态。查当前任务时，先看相同任务名的两份文件，按更新时间和来源分支确认；不要直接把较旧阶段报告当成今天的结论。跨分支状态还应核对对应分支的发布记录。

文档里多份内容相同的策略源、研究规范和实验报告，大多是交接包的定版副本、冻结实验的证据或网页按路径读取的报告。本次没有把它们折叠成单份，以免破坏校验清单、旧实验可复现性或正在进行的交接。

## 顶层速查（什么内容放哪）

| 想放/想找的东西 | 去处 |
|---|---|
| 实验结案报告（主题-YYYY-MM-DD.md） | `experiments/`（按归档规约三件套：报告+登记+INDEX） |
| 实验原始数据 / 复现产物 | `experiments/raw/<实验名>-<日期>/` |
| 研究规范（原则/契约/定义/模板） | `research/` |
| 专项研究计划书 | `superpowers/plans/`（日期前缀命名） |
| 交接/计划类过程文档（新写的少见，多为历史） | `archive/handoffs-plans/`（验收后不再新增到 docs 根层） |
| 历史交付报告（ROUND2~5 等） | `archive/rounds/` |
| 运维文档 | `ops/`（运维手册） |
| 文献学习流程与登记 | `literature-learning/` |
| OKR/系统待升级台账说明 | `okr/` |
| 择时扫频历史档案 | `timing-sweep/` |

## 研究资料入口

- `research/experiment-backtest-principles.md` — 系统级实验、回测、归因与实盘验收原则
- [AI执行与交接合同](research/ai-execution-contract.md) — 新任务身份、边界与验收
- [文献与外部方法流程](literature-learning/README.md) — 真实阅读范围、许可与本地适配
- `research/definition-standard.md` — 因子、信号、风险与基准的定义管理细则
- `research/definitions.v1.json` — 唯一机器登记表与定义卡；按精确版本解析，不静默替换旧实验
- `research/experiment-report-template.md` — 新收益实验报告模板与最小决策卡
- `research-playbook.md` — 从既往实验中沉淀的经验法则（受上位验收规范约束）
- `experiments/INDEX.md` — 实验归档总索引（任务编号账 + 主题分组 + raw 对照）
- `next-steps-master-plan-2026-09-02.md` — 早期方向总纲（历史导航；当前选题先核主战场专项计划及最新冻结协议）
- `timing-sweep/` — 8-27 时代 31 轮择时实验档案

## 规格与约束

- `trading-spec-v1.md` — 历史 V1 快照，仅供旧实验复现与历史对照
- `trading-spec-audit.md` — 规格审计
- `system-architecture-and-decisions-2026-09-04.md` — 系统架构与决策台账
- `research-round5/6/7-*.md`、`research-sentiment-us.md` 等 — 各轮研究总纲（实验报告库页面消费）

## 应用线（data-sync）历史文档

- `archive/handoffs-plans/handoff-*.md` / `plan-*.md` — 各轮交接与方案（agent-supervisor、买入点、板块页等）
- `archive/handoffs-plans/PROJECT-HANDOFF-2026-08-27-v2.md` / `SYSTEM-VALUE-SUMMARY-2026-08-31.md`
- `archive/handoffs-plans/broad-index-summary-plain-2026-09-02.md` — 宽基结论大白话版
- `archive/rounds/` — ROUND2~5 交付报告与实施计划

## 归档区说明

`archive/` 主要保存历史留痕，但其中也存在近期交接包，不能仅凭目录名判定任务结束。当前任务状态先查 `ops/work-progress/`；研究结论以对应登记报告为准，
复现命令的路径映射见各归档子目录的 README。研究历史（含失败与证伪）
按 AGENTS.md 要求保留，不删除。

---

看不懂某份文档在讲什么，先查 `experiments/INDEX.md` 对应行的一句话摘要，
再决定要不要读原文。新文件放哪不确定时，跑
`python3 scripts/check_repo_hygiene.py`，它会对放错位置的内容报警。
