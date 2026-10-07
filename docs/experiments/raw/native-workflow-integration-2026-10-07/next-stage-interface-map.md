# D—MAE20 原生入口接续：准确接口与停写范围

更新时间：2026-10-07 23:32 Asia/Shanghai。状态：**接口定位完成；共享代码未获准修改；真实效果未测量**。本文件只定位现有入口和下一阶段拟触及的准确文件，不是原合同、执行许可或结果回执。

## 可复核的输入与协调基线

- 本轮读到 `coordination/lei` 完整 commit `eb61b3a20737da3c561260434886016b34c57f8f`，规则 `COORDINATION.md` v1.1，并读 `research-dispatch-controller`、`classic-factor-research` 的任务记录。协调检查器 SHA `1426314a0b76a1758f5c5a9a9aa71ed9ff4ce801504b38b74b0e8828581f355e`。在线检查两次：使用旧稳定任务名 `classic-factor-research` 时退出 2（旧记录无机器声明）；使用新范围名 `native-workflow-integration` 时退出 2（下列共享源码路径尚未登记）。`online_verified=true` **不等于准入**，`work_clearance=false`。因此本轮不写共享源码。
- 技术线合成纯函数 `docs/experiments/raw/native-risk-d-mae-2026-10-07/study.py` SHA `84f4fee2a538a918352bca099ec9c9b4a38f6d6a19dab5faa564b668c0bd8745`；交付 `MANIFEST.json`、`REPORT.md`、`synthetic-receipt.json`、`MISSING-INPUTS.json`。独立人工审查 `docs/experiments/raw/research-dispatch-controller-2026-10-07/independent-review/d-mae-synthetic/REVIEW.md` 已给**合成纯运算限定通过**，但审查报告仍仅本机、未推送，不证明真实资料绑定或完整原生入口可用。原设计合同 `immutable-handoff/PROPOSED-CONTRACT.json` SHA `ace132ddb89de3e45951148d9673524fa9fe448f662f2576221d216bbe9717c6`，明确 `native_workflow_contract=false`，真实 X/Y 预算均为零。
- 当前实际源码 SHA：`scripts/run_factor_lab.py` `eb38c3ce70a4331026ab1dc5d8f71eb5f2e1cbffda59ceac4abbaffb15820c52`；`question_contract.py` `ed4a44fbb3fbf6c7b986bd2fb9261f98f15cf33b604f04b84e7ceb4e2fffcb97`；`workflow.py` `967d92adc77a18c42f16fda27c80eb5a136eadd72e4918515302003216a43cb6`；`workflow_inputs.py` `43a0683c13132fa34c73d4ce618d37746b5a8aa8da89e2967d132f59bee777ad`；`workflow_evaluation.py` `508459ca3964a55e1688fef345d6e667acba68141f8be8f04f1ea1c5f0018c1c`。这些是共享脏工作区**实际字节**，不是 HEAD 中的版本。

## 唯一入口与必须保留的调用链

`scripts/run_factor_lab.py --workflow-draft/--workflow-contract/--review-workflow-contract` → `workflow.freeze_workflow/run_workflow` → `question_contract.validate_workflow_contract` → `workflow.preflight` → `input_preflight.inspect_workflow_input` → `workflow_inputs.prepare_observations` → `workflow.execute_workflow` → `workflow_evaluation.evaluate_observations` 或专用无拟合回调 → 同一个研究族 `attempts.jsonl`、`execution.lock`、`receipt.json`、`state.json`、`check_publication`。沿用这个入口、账本、锁、回执，不新增平台或绕过出版复核。

现行真实阻碍：

1. `question_contract.py:257-305,445-525` 不接受 D 的特征种类和同样本有符号排序相关评价；现有评价菜单以预测误差为主，不能伪装成 `prediction_ridge`。原设计 JSON 缺完整原生合同字段，`--review-workflow-contract` 已以退出码 3 拒绝。
2. `workflow_inputs.py:80-157,159-267` 的通用 MAE 可跳过目标路径中的停牌；技术合成实现要求先核 **全部 75 条成熟路径、每条 t+1 至 t+21 共 21 个合法收盘价**，任一条失败就不产生本批标签。不可借通用 `_label` 给 D 计算真实 Y。
3. `workflow.py:564-875,933-1172,1547-1685` 的 `preflight` 会读目标、筛出有标签评价行、要求有成熟训练行；随后才记账并执行。仅靠现有 `calculation_run=false` 字段不能证明“只做 X 不看 Y”。D/V 原件绑定和一次 Y 必须是**两个分开的、有指纹回执的阶段**。已有一次性研究入口不能在 0 真实 Y 许可下被真实数据调用；需要在同一入口增加专用的只核 X 阶段及封存凭证，再另由中控批准 Y。
4. `workflow.py:179-359` 会从现行定义登记表解析对象闭包、核源码与数据 SHA；`check_publication:1323-1405` 当前仅认识预测与等待路径结果。D 描述性结果需以原始 76 案例、84 事件成员、33 生命周期、75/1 标签状态和固定共同资产覆盖逐项复核，不能复用预测结果的 B0/B1/B2 要求。`--register-report` 会写共享 registry，须仍交中控串行登记。

## 待远端登记的准确写入清单

本负责人（流程线）拟成为下列**共享入口适配**唯一写者；技术线仍是原 `study.py` 和同题合成/来源材料唯一写者。实际动手前先由协调负责人在同一 `native-workflow-integration` 记录登记并推送，在线复核无冲突，再核中控对限定独审的接续意见。本清单是待确认范围，不是目录排他权。

| 路径 | 精确改动目的 | 是否必要 |
|---|---|---|
| `src/lei_signal/research/native_risk_d_mae_workflow.py`（新） | 正式研究层适配：从**已核冻结原件**绑定 76 个案例、84 成员及 33 生命周期；引入经独审的纯数学算法而非从归档 raw 动态导入；分开 X 封存、全路径预检和 Y 一次计算；输出每案例/每资产/固定资产集/33 删除的审计结构。 | 必要，待独审确认其算法与接口 |
| `src/lei_signal/research/question_contract.py` | 只为 D—MAE 描述性问题增有限种类和精确字段/单位/预算/日期/比较边界；原模型和旧合同不改变。 | 必要 |
| `src/lei_signal/research/workflow_inputs.py` | 在 `prepare_observations` 接正式专用适配；不修改通用 `_label` 的旧行为。 | 必要 |
| `src/lei_signal/research/workflow.py` | 在现有审查、冻结、账本/锁、回执/出版链挂专用 X 与 Y 阶段、绑定专用源码 SHA，并明确 Y 禁令；保留现有合同路径和失败账本。 | 必要 |
| `tests/unit/test_native_risk_d_mae_workflow.py`（新） | 人工样例检验 21 根、不连续/停牌失败、并列秩、固定共同资产、全部 33 删除及 X 不读 Y。 | 必要 |
| `tests/integration/test_native_risk_d_mae_workflow.py`（新） | 通过原 CLI 做 76 案例合成端到端：先 X 回执后 Y 回执、预算/锁/出版复核、坏路径 0 标签、旧入口不变。只用测试隔离目录。 | 必要 |
| `scripts/run_factor_lab.py` | 现有 `--workflow-draft/--workflow-contract` 可用时不改；若 X 阶段无法通过原入口表达，限在原 CLI 增**明确阶段参数**，禁止默默切换。 | 条件性，实施前复核 |
| `docs/research/definitions.v1.json`、`docs/experiments/registry.json`、`docs/experiments/INDEX.md` | D 对象及实验登记若需要，交中控安排统一写者。流程线只提交候选，不在本范围直接写。 | 中控串行 |

`workflow_evaluation.py` 当前不列为写路径：专用无拟合相关性计算留在新适配，由 `workflow.py` 显式分流，并在 `check_publication` 复算。`input_preflight.py` 只通过 `inspect_workflow_input` 分发到 `prepare_observations`，当前不需修改。实施发现必须改其中任何文件，应先修订协调范围并读回，不顺手扩张。

## 最小验收与停止条件

- 先通过最新远端范围登记、中控对合成限定独审的接续确认。核原六份缺件的**准确 SHA 和成员身份**；原件仍缺时仅合成端到端，不运行真实 X/Y，不填造 76 个案例的字段。已定位原行情 ZIP 不等于原 D/案例/绑定文件齐全。
- 合成阶段以项目隔离根目录验证 CLI 实际产生 X-only 回执，X 阶段没有任何 Y 值或统计；模拟 Y 的 75 条必须全路径预检、1 条按原截断未知，坏路径全批拒绝；复核报告、回执和研究族账本。独立人工复核在 `docs/experiments/raw/research-dispatch-controller-2026-10-07/independent-review/d-mae-synthetic/verification.json` 已记录 1,754 项断言通过、0 失败，同时指出纯函数接受 `action_known=null/0/"false"` 且极端正有限输入可能使 V 溢出为无穷大。**正式输入适配必须拒绝非布尔行动状态，重新核对 V 结果有限性，并逐项测试**；纯函数通过不表示原件资格通过。现有已通过的 45/10 项只在改动影响后做必要回归；旧冻结协议 8 项源码指纹失败保留，不改原锁或成绩凑绿。
- 真实 X 只在中控单独授权并绑定六份原件及最终源码/合同 SHA 后执行；真实 Y 还需**另一次**许可与封存回执。一次 Y 最多 75 案例，0 拟合、0 搜参、0 新窗口、0 自动重试；不把排序相关差称条件增量或线上收益。
- 若范围远端未登记、独审未通过、原件/权限不足、严格路径任一失败，相关阶段标 blocked，保留错误证据；不缩样本、不重算旧结果、不启动付费/生产/交易。
