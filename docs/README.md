# docs 导航与目录地图

> 2026-09-16 目录治理后重写：导航 + 归置入口。新文档放哪、什么做完要删，
> 权威规约见根目录 AGENTS.md「文件归置规约」；本页是它的展开地图。

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

## 研究线（recovery/lei-round2 的主战场）

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

- `trading-spec-v1.md` — 交易系统规格，最高溯源依据（见根目录 AGENTS.md 第零步）
- `trading-spec-audit.md` — 规格审计
- `system-architecture-and-decisions-2026-09-04.md` — 系统架构与决策台账
- `research-round5/6/7-*.md`、`research-sentiment-us.md` 等 — 各轮研究总纲（实验报告库页面消费）

## 应用线（data-sync）历史文档

- `archive/handoffs-plans/handoff-*.md` / `plan-*.md` — 各轮交接与方案（agent-supervisor、买入点、板块页等）
- `archive/handoffs-plans/PROJECT-HANDOFF-2026-08-27-v2.md` / `SYSTEM-VALUE-SUMMARY-2026-08-31.md`
- `archive/handoffs-plans/broad-index-summary-plain-2026-09-02.md` — 宽基结论大白话版
- `archive/rounds/` — ROUND2~5 交付报告与实施计划

## 归档区说明

`archive/` 下的内容是**历史留痕，不再维护**：结论以对应登记报告为准，
复现命令的路径映射见各归档子目录的 README。研究历史（含失败与证伪）
按 AGENTS.md 要求保留，不删除。

---

看不懂某份文档在讲什么，先查 `experiments/INDEX.md` 对应行的一句话摘要，
再决定要不要读原文。新文件放哪不确定时，跑
`python3 scripts/check_repo_hygiene.py`，它会对放错位置的内容报警。
