# B1 R1–R3 限定收尾：主控复核

日期：2026-09-16。版本：1.0。裁决：**本轮限定收口；历史描述可保留，流程有偏差，不能称全部无条件通过。**

## 一句话结论（大白话）

双均线第一次真实历史描述及其补件可以收口，不需要再为这轮重新计算。510300 的成立组后续平均价格变化高一些，但七个年份只有两年优于未成立组，不能据此认定稳定赚钱。补件把缺失的文件清单和规范原件补齐了；超预算、早期源码丢失仍作为历史缺口保留。

## 1. 被审对象与权限

- 执行报告：[B1 报告 §12](b1-dual-ma-first-real-description-2026-09-16.md)，以前部旧表述与 §12 冲突时，以带日期纠正为准。
- 上轮要求：[主控 R1–R3](b1-controller-review-2026-09-16.md)。
- 工作目录 `/Users/yongbiaoli/Desktop/lei-signal-lab`；分支 `codex/factor-unit-research-20260915`；HEAD `8ba16576b75e605aa1b0d0902568c760c4b99095`，本轮核对一致。
- 按 `ai-execution-contract.md` v1.0.1 独立复核。未改实现、旧结果、旧协议、OKR；未联网、未安装、未提交。主控真实计算与正式运行均为 0。
- 独立核验脚本与完整指纹：[check.py](raw/b1-closeout-controller-2026-09-16/check.py)、[results.json](raw/b1-closeout-controller-2026-09-16/results.json)。脚本只读旧包，临时构造协议作校验，不调用真实研究计算。

## 2. 执行者声明与主控验证

| 项目 | 主控验证 | 裁决 |
|---|---|---|
| R1：规范与容差必须核验 | 从旧协议构造绑定当前代码的合法校验正例；独立删空 standards、将 float 容差改为 1、清空 output_fields/no_claims，四项均在校验阶段被拒，合法正例通过。40 项新测试另覆盖文件版本、卡、任务书等。 | 限定修复接受；不代表旧运行使用新校验器。 |
| R2：清单和原件补齐 | 旧 manifest 的 37 项逐一哈希一致；补件清单与实际非顶层 manifest 文件集合双向一致，共 38 项；嵌套 manifest 入列。补件自身无未列文件；7 份规范/卡/任务书原件与旧协议逐一匹配；两份 CSV 元数据绑定正确文件哈希。 | 当前补件接受。 |
| R2：写盘失败不冒称完成 | 独立复跑新测试，并阅读三处进程内合成故障注入：首写和中途失败无 manifest，定稿前注入失败只留 completed=False。 | 接受这三种测试范围，不扩称所有磁盘故障均已验证。 |
| R3：结论收窄 | §12 已注明 t+1 收盘到 t+22 收盘，共 21 个价格变化区间；年度均值差严格为 2 正 5 负；稀疏观察不重叠不等于相互独立；组间均值与中位数差都为正，与假组自身均值/中位数异号分开。 | 接受纠正；前部旧措辞不得单独摘录为现行结论。 |

旧协议 SHA：v1.0.0 `636171734bf363b30a0821b19256c5dc16507600b97d1a98a61766802b249477`；v1.0.1 `00a16465e5232d3760cedbe9bccb5332b05e4f777f1732e8911ee586974c3af2`，与上轮记录一致，run-02 协议副本与 v1.0.1 原字节一致。close_state、description_core、state_description、b1_description 指纹与上轮记录一致。本轮未重复全仓保护核验，不把这些局部核对扩大为所有文件均受独立核验。

## 3. 保留的缺口与流程偏差

1. v1.0.0 的 b1_contract.py 原字节不可恢复，不编造；该失败尝试不能宣称完整源码可恢复。现存 v1.0.1 成功结果与此区分。
2. 恢复核验 2/1、补件核验 2/1 均超各自预算。自报错误不构成追加次数许可。closeout-run-log.md 还记录失败补件删除重建，因此不将本轮称为全程排他留档。当前最终补件可核实，不抹去过程偏差。
3. 历史逐轮失败日志及早期 CLI 调用次数无法精确恢复。测试日志支持现有结果，不证明全部历史尝试记录完整。
4. 修后代码没有新正式冻结运行包；SPEC_VERSION 仍为 1.0.1，旧同版本协议绑定旧代码。freeze_build 已改为版本目录，但下一版本仍需另行协调校验器的版本常量、任务授权和冻结构建，不能现在直接指定新版本就声称能正式运行。本轮不为此创建新协议或重跑。
5. CLI 元数据中的“非含分红财富”应按本轮口径理解为“不得未经验证作为含分红财富使用，等价性未核”，不是已证明数学上不等价。此处由本裁决明确解释，后续获准维护时再统一文案，不因此另开返修轮。

## 4. 实际核验

```text
python3 docs/experiments/raw/b1-closeout-controller-2026-09-16/check.py
退出 0；38 项结果文件、7 项规范原件、4 类独立协议反例核验通过。

python3 -m pytest tests/unit/test_factor_unit_description_core.py tests/unit/test_b1_contract.py tests/unit/test_b1_description.py tests/integration/test_b1_description_cli.py -q
40 passed，退出 0。

python3 -m pytest tests/unit/test_factor_unit_close_state.py tests/unit/test_factor_unit_study_contract.py tests/unit/test_factor_unit_state_description.py tests/unit/test_factor_unit_b0_controller_cases.py tests/integration/test_factor_unit_readiness_cli.py tests/unit/test_experiment_reports.py -q
89 passed, 1 skipped，退出 0（此命令不含 four_fixes 文件，不冒报 108）。

python3 -m pytest tests/unit/test_factor_unit_four_fixes.py -q
19 passed，退出 0；与上一命令合计覆盖旧相关 108 项通过、1 项跳过，但不是同一批命令运行。

python3 -m ruff check src/lei_signal/research/factor_unit/b1_contract.py scripts/run_b1_dual_ma_description.py tests/unit/test_b1_contract.py tests/integration/test_b1_description_cli.py
All checks passed，退出 0。
```

## 5. 给执行者的收口指令

**本轮必需返修项：无。完成即停。** 不为消除历史缺口重签旧协议，不覆写 run-02，不追补伪造日志，不新增真实计算。

接受的是：固定快照上的历史描述、已核实补件，以及合成测试范围内的接口修复。未接受的推论是：预测有效、统计上可靠、交易赚钱、含分红财富已核、所有未来运行能力已就绪或生产授权。

下一阶段仍须另立有限任务并授权。建议先确定如何评估结果受连续行情和观察区间重叠影响的不确定性，再决定是否增加一个事先指定的新载体作比较；不要因为总体均值较好就调参数。此段是方向建议，不是联网、跨市场、参数搜索、策略归因或 OKR 写入许可。

## ARCHIVE：最小决策卡

| 问题 | 裁决 |
|---|---|
| 本轮改变什么？ | 收口 B1 接口及归档修复，不改变双均线定义。 |
| 实际增加什么？ | 规范校验、完整文件核对和失败不冒称完成的证据。 |
| 钱从哪里来？ | 本轮没有账户盈亏，不作赚钱归因。 |
| 代价与限制？ | 有预算偏差、失败版本源码缺口；历史时点可得性及稳健推断未核。 |
| 现在怎么办？ | 本轮停止；后续研究另行授权。 |
