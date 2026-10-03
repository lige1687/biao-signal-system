# 证据索引与版本

所有实际文件大小和SHA256见manifest；原始证据不改写，历史绝对路径只用于说明当时环境。新机器命令使用仓库相对路径。

| 证据 | 准确位置/版本 | 含义 |
|---|---|---|
| 队列目标与去重 | `docs/archive/handoffs-plans/remote-astra-queue-2026-09-30/`@4155b4db | README、OWNERSHIP、TASKS、RESEARCH-DECISIONS-ARCHITECTURE、72文件输入清单 |
| 完整验收要求 | `docs/research/proposals/remote-astra-2026-09-30/ACCEPTANCE-PROMPT.md`@4155b4db | 历史原件；后续授权改变见USER-REQUESTS |
| 交付总报告/母体报告 | `docs/experiments/remote-astra-core-review-2026-09-30.md`、`module-a-population-audit-2026-10-02.md`@4155b4db | 被验对象，不是无条件接受证据 |
| 远端交付状态 | `docs/research/proposals/remote-astra-2026-09-30/task-state.json` | 预算自报约数、T1跳过、逐题输出 |
| 独立验收报告 | `docs/experiments/remote-astra-core-acceptance-2026-10-02.md`@30dca305 | 判定、机械问题、代理、语义、R1—R8与生产立项建议 |
| 独立复现 | `docs/experiments/raw/remote-astra-core-acceptance-2026-10-02/runs/*/result.json`及run.log | 命令、cwd、退出码、耗时、产物SHA与字节比较 |
| 完整逐日摘要 | `.../runs/population-asof-partitioned/population-audit-asof.json` | SHA256 `f3c53471fa97d88fc8470837f141449ed44a7ddb062690eeeaf966a1b42ba4a8`，504/504，非完整逐日构造列表 |
| 运行与源码绑定 | 同raw `partition-source-check.json`、`final-verification.json`、`source-and-boundary.json` | 锁原算法与原报告；不能为新路径改写 |
| 控制器反例 | 同raw `controller-probes.json`及`controller_probes.py` | T9重算链可通过；T10关键缺项仍complete/proceed |
| 返修范围 | 同raw `REPAIR-PROMPT.md` | R1—R8原件，旧“等用户选技术含义”由本包最新授权补充说明覆盖 |
| 来源核查 | 同raw `source-followup.json`、`methods-review.md`、`scope-review.md` | 已核引用范围及第二篇PDF未独立核全限制 |
| 历史依赖与缺口 | T10 `existing-audit.json`、本包`definition-gaps.json` | 旧锁换行差异及定义证据缺失；未伪装闭合 |
| 新方向方法核对 | 本包`research-preflight.json`、DECISIONS | 只读去重/评议，不是效果实验或统计结果 |

本包没有完整远端聊天/第二篇指定PDF原件，不冒称有。不能因日志含旧绝对路径就创建Air用户名目录，也不能用报告数字替造缺失输入。
