# 任务合同：factor-research-workbench-v1（执行者副本）

按 `docs/research/experiment-report-template.md` v1.1.0 派发合同段（T1）填写。

## 任务标识

- 任务ID：本轮执行（执行者 ZCode/GLM）；派发 job `edeffe2f-ab54-4b2b-a59c-15cbc4a4a2ba` 已取消，改为手工转交 prompt。
- 研究家族：自有因子与信号研究体系（factor-research-workbench）。
- 任务类型：方法论与验证（工程能力建设，非收益实验）。
- 工作性质：新建（复用既有计算，不重写公式）。
- 主控：当前 Codex 任务（回调后独立复核）；执行：ZCode/GLM（本任务）；独立期望值来源：协议内手算期望表（不用被测输出生成）。
- OKR：方向 `okr-cd1a0bd5532c`、任务 `okr-3fa8363be729` 只读；执行者不写 OKR、不勾完成。

## 规范绑定（实际路径与版本）

| 文件 | 版本 | 说明 |
|---|---|---|
| docs/research/experiment-backtest-principles.md | v1.1 | 研究与验收原则 |
| docs/research/definition-standard.md | 1.1.0 | 类型/目标/证据合同 |
| docs/research/ai-execution-contract.md | 1.0.1 | 执行行为 |
| docs/research/experiment-report-template.md | 1.1.0 | 报告模板 |
| docs/research/definitions.v1.json | v1.2.0 | 唯一对象登记表（只读） |
| docs/superpowers/plans/2026-09-14-factor-research-workbench-v1.md | 1.0.0 | 执行规格 |

## 对象引用（精确 id@version）

- 已登记（本轮接入）：`mixed.momentum.raw@1.0.0`、`mixed.rv20@1.0.0`、`trend.distance50@1.0.0`、`trend.distance200@1.0.0`、`breadth.csi300.b50.common@1.0.0`、`breadth.csi300.b200.common@1.0.0`（合成输入，不冒充真实沪深300证据）。
- 候选（不登记）：`candidate:lei.dual_ma.bull_state@draft-1`（源代码绑定，见候选卡草案）。

## 权限边界

- 可写：`src/lei_signal/research/factor_lab/**`（新建）、`scripts/run_factor_lab.py`（新建）、`tests/unit/test_factor_lab_*.py`、`tests/integration/test_factor_lab_cli.py`（新建）、`docs/research/factor-lab-usage.md`（新建）、`docs/experiments/factor-research-workbench-v1-2026-09-14.md`（新建）、`docs/experiments/raw/factor-research-workbench-v1-2026-09-14/**`（新建）、registry/INDEX 本条目、路线图追加本轮交付入口。
- 禁改：登记表与全部既有定义卡、生产规则、UI/API、数据库、旧测试、旧 raw、价格/成员缓存、账户数据库、`src/lei_signal/ui/**`（冻结）、他人未提交改动。
- 网络 0；新增依赖 0；真实收益/账户/动量/因子检验运行 0；真实资料只读资格检查 ≤1 批（限已有 full14 快照，可不做）。
- 正式合成端到端 3 类，每类初跑 1 + 纠错 1（失败占次数）；完整相关回归 ≤2 次。
- 不提交 git；退出码合同 0/2/3；无跳过核验开关。

## 交付

factor_lab 六模块 + CLI + 六份测试 + 能力盘点/基线冻结/候选卡/协议/独立期望表（raw）+ 使用手册 + 执行报告 + registry/INDEX/路线图条目 + 逐里程碑证据建议（主控写 OKR）。

## 停止条件

政策/时点歧义、需新资料/依赖/生产修改、保护文件意外变化、预算耗尽、新增实际因子定义需判断 → 停受影响分支，其余继续；主控最多 3 轮（初交+2 次限范围返修）。

## 实际执行记录（执行者填写）

- 执行模型：GLM（`builtin:bigmodel-coding-plan/GLM-5.3-Flash`，ZCode agent），2026-09-14。
- 工作区核验：`/Users/yongbiaoli/Desktop/lei-signal-lab`，HEAD `8ba16576`，脏区 338 行（protection-baseline.json）。
- 预算计数：见执行报告 §失败史与运行计数。
