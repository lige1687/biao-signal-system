# D—MAE 人工流程 R1/R2 返修局部独审

## 一句话结论（大白话）

**R1、R2 已在指定人工接入版本中闭合。** 正常人工输入仍可走完X、Y两阶段；同一案例重复事件会被拒绝；两阶段累计用时超出已定预算时，在结果与回执发布前暂停，并留下失败记录。真实因子效果仍未测量。

本报告是上次[完整审查](../REVIEW.md)的**增量复验**。上次R1/R2失败反例、证据和审查结论保持原样；旧169项作者测试、1,754项纯计算审查及本线476次数值核对均未重跑。

## 版本与范围

- 任务：`d-mae-workflow-integration-review`。原外部线程 `01a0cd21-07e5-7163-8f4e-72a4d5ebc32e`；仅写本 `revision-b2f45151/` 目录。
- 作者仓库：[biao-signal-system](https://github.com/lige1687/biao-signal-system)，工作分支 `codex/native-workflow-integration-20261007`。
- 上次审查基线 `f0c72d078a97b02ddf21595422747377fd6e09cd`；本次锁定准确提交 **`b2f45151128baa1fe387cda85862d71cb01e1206`**。读回远端该分支ref亦等于此提交。
- 协调分支本轮在线读到 `dcbee1e174a87b685560dfaeb182e61075eaa761`，记录将本task列为active、owner与输出目录相符；其中工作详情尚只写到前一提交，不把协调摘要当新版本证明。
- 作者新回执 `docs/experiments/raw/native-workflow-integration-2026-10-07/repair-r1-r2.json` 声称六项局部自验通过；本报告结论来自下面**独立脚本**，不把作者自验当独审。
- 只核新适配器与两份新测试的变更；三共享入口补丁字节与前轮已核基线相同。49份其他任务持有的本机依赖仍缺于纯Git提交，真实六份原件及真实X/Y授权仍缺。

## 两项返修逐项核验

| 上轮问题 | 准确修复位置 | 本轮独立反例与结果 | 结论 |
|---|---|---|---|
| R1 同案例重复成员漏拦 | `src/lei_signal/research/native_risk_d_mae_workflow.py:144,160–176`，先核本行去重，再核跨行集合，并显式要求成员出现84次 | 76案例、84成员、33组正常通过。把首案例内一个事件别名再写一次后，变为85次记录/84个唯一别名，程序拒绝；跨案例重复也拒绝 | **闭合** |
| R2 两阶段累计预算超限仍发布 | 同文件 `507–509,522–527`，在写result之前以“此前已用＋本阶段已用”检查 | 人工时钟设预算1.5秒、两阶段各0.9秒：X完成，Y在结果与回执前暂停；`failure.json`和失败账本保留，Y再次尝试遭拒。各0.5秒：X/Y均完成，新进程核Y回执通过 | **闭合于计算后、发布前检查点** |

预算数值是注入的确定性时钟，**不是实际耗时**。实际执行未等待1.8秒，也未计算市场数据。此检查不保证操作系统硬实时中断，也没有把发布回执与复查所耗时间计入发布前的阈值；作者源码注释对此有明确限制。本轮只要求不在已记录计算阶段累计超限后发布成功结果，这一项已满足。

同时核六种权限字段严格类型拒绝（布尔与数字、字符串混用），未见此前修复回退。`targeted-results.json` 共29项独立断言，**29通过、0失败**。其中包含正常结构、两种重复、两种预算场景、失败记录、拒绝重试及新进程复查；不是29次市场实验。脚本启动退出0。项目目录归置检查退出0。

## 实际执行与可读证据

从上次本线独立生成的人工 `x.json/y.json` 复制准确输入，在 `source-copy/` 隔离复制作者本次准确源码及少量静态依赖，分别建立 `isolated-over/` 与 `isolated-within/`。独审程序独立调用正式 `freeze_workflow`/`execute_workflow`，没有运行作者测试文件，也未调用旧归档study。新进程复查使用独立Python子进程、设置 `PYTHONDONTWRITEBYTECODE=1`。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B docs/experiments/raw/research-dispatch-controller-2026-10-07/independent-review/native-workflow/revision-b2f45151/targeted_check.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/check_repo_hygiene.py
```

`targeted_check.py` 为一次性证据生成器，遇到已有 `source-copy/` 会拒绝覆盖；本报告交付后的复验应先复制本审查脚本到**新的**专属审查目录，不删除或覆盖本次快照。对每个目标的具体结果在 `targeted-results.json`；`before.json` 与 `after.json` 核六个作者文件及HEAD，审前后未变。三个本次改动文件SHA分别为：

| 文件 | SHA256 |
|---|---|
| `native_risk_d_mae_workflow.py` | `941ab8e495724a1d3f68ce1d15f967d8e994855bc6ae45387f7f81c6529054af` |
| `test_native_risk_d_mae_workflow.py`（unit） | `ee967bba8186946db1da0d72c8aed37b0eebd4b8eab1f8adb7eda7cb15eba41e` |
| `test_native_risk_d_mae_workflow.py`（integration） | `3343cf2d245c5fc026c4c60a94274cb4e405252a6153e98fa4a213f4a04fadd2` |

`targeted-results.json` 记录两场景精确账本：超限完成记录合计X 0.9秒与Y失败耗时0.9秒，合计1.8秒；限内两阶段各0.5秒，合计1.0秒。计时和状态是代码边界的合成验证，真实执行预算、真实研究数据资格与因子增量均未测量。

**范围结论：** 本次两项返修可接受，上次完整人工接入审查的两条阻断可改为已闭合。其他边界仍按上次报告：纯Git提交缺49份准确基线依赖，六份真实原件及历史到达资格、真实X/Y阶段许可没有取得，人工算术通过不授权真实研究或生产交易。本轮没有改作者源码、共享入口、冻结结果、协调文件，也没有推送本独审目录；后续归档和同步由协调端按其职责处理。
