# 动量研究样板运行报告

- 模式：`historical-diagnostic`；协议：`momentum-research-prototype-2026-09-13`
- synthetic = False
- historical_reconstruction_only = False

## 一句话结论（大白话）

用真实冻结数据做了被允许的部分：重建了复权指数并算出动量值 0 个，缺失 0 处都写明了原因。未来目标和排名诊断按协议没有对真实数据运行。这只是历史数值复算，不构成对未来走势的任何预测证据。

## 阶段与数量

- 观察日数：0
- 动量值：0；缺失：0
- 未来目标：0
- 排名诊断期数：0（有值 0）
- 原始行动记录 1 条；其中进入经济指数的分红/拆分以挂接与逐记录核验结果为准，停牌等非经济行动不进入；available_at 已声明 0 条、未知 1 条

## 未运行阶段

- economic-reconstruction：行动记录核验存在 BLOCK 级发现，不得进入重建：[action_bad_amount] 510300.SS 每份现金金额非法：-0.05；510300.SS 行动记录不合法：分红 'SYNTH-DIV' 每份现金非法：-0.05
- targets：协议规定历史诊断不写真实 targets/rank
- rank-diagnostic：协议规定历史诊断不写真实 targets/rank

## 拒绝原因

- 行动记录核验存在 BLOCK 级发现，不得进入重建：[action_bad_amount] 510300.SS 每份现金金额非法：-0.05
- 510300.SS 行动记录不合法：分红 'SYNTH-DIV' 每份现金非法：-0.05

## 状态

- computation_run = False
- research_qualification = rejected
- validity = not_tested_by_this_run
- production = not_authorized
- policy = not_applicable_no_account_policy

> 本运行不证明动量指标有效，不构成交易授权；无资金账户计算，政策卡不适用。
