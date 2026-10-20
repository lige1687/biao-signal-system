# 动量研究样板运行报告

- 模式：`historical-diagnostic`；协议：`fixed-etf-evidence-integration-2026-09-13`
- synthetic = False
- historical_reconstruction_only = True

## 一句话结论（大白话）

用真实冻结数据做了被允许的部分：重建了复权指数并算出动量值 772 个，缺失 376 处都写明了原因。未来目标和排名诊断按协议没有对真实数据运行。这只是历史数值复算，不构成对未来走势的任何预测证据。

## 阶段与数量

- 观察日数：82
- 动量值：772；缺失：376
- 未来目标：0
- 排名诊断期数：0（有值 0）
- 原始行动记录 21 条；其中进入经济指数的分红/拆分以挂接与逐记录核验结果为准，停牌等非经济行动不进入；available_at 已声明 0 条、未知 21 条

## 未运行阶段

- targets：协议规定历史诊断模式不写真实 targets/rank 结果
- rank-diagnostic：协议规定历史诊断模式不写真实 targets/rank 结果

## 未知可得时点的行动（available_at 未知，保持 null）

- `510300.SS` 510300-cash_dividend-2019-01-16
- `510300.SS` 510300-cash_dividend-2019-12-11
- `510300.SS` 510300-cash_dividend-2021-01-18
- `510300.SS` 510300-cash_dividend-2022-01-19
- `510300.SS` 510300-cash_dividend-2023-01-16
- `510300.SS` 510300-cash_dividend-2024-01-18
- `510300.SS` 510300-cash_dividend-2025-06-18
- `510300.SS` 510300-cash_dividend-2026-01-19
- `512400.SS` 512400-cash_dividend-2024-09-18
- `512400.SS` 512400-cash_dividend-2025-09-15
- `512890.SS` 512890-split-2021-10-22
- `515050.SS` 515050-split-2026-05-13
- `515300.SS` 515300-cash_dividend-2023-12-19
- `515300.SS` 515300-cash_dividend-2024-06-21
- `515300.SS` 515300-cash_dividend-2024-09-20
- `515300.SS` 515300-cash_dividend-2024-12-03
- `515300.SS` 515300-cash_dividend-2025-06-17
- `515300.SS` 515300-cash_dividend-2025-09-18
- `515300.SS` 515300-cash_dividend-2025-12-15
- `515880.SS` 515880-split-2026-02-03

## 状态

- computation_run = True
- research_qualification = qualified_for_this_mode
- validity = not_tested_by_this_run
- production = not_authorized
- policy = not_applicable_no_account_policy

> 本运行不证明动量指标有效，不构成交易授权；无资金账户计算，政策卡不适用。
