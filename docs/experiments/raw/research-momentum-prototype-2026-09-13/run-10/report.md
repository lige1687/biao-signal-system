# 动量研究样板运行报告

- 模式：`synthetic`；协议：`momentum-research-prototype-2026-09-13`
- synthetic = True
- historical_reconstruction_only = False

## 一句话结论（大白话）

用完全虚构的价格数据把整套计算从头到尾跑通了：重建复权指数、算动量、算未来观察目标、算排名一致性，共写出 12 个动量值、70 个未来目标、14 期排名诊断（其中 1 期有数值）。这只能证明算法和时间安排算得对，不能证明这个指标在真实市场上有效。

## 阶段与数量

- 观察日数：14
- 动量值：12；缺失：58
- 未来目标：70
- 排名诊断期数：14（有值 1）

## 合成夹具说明（synthetic=true）

- SYN.A：基准路径：无行动、无缺报价
- SYN.B：现金分红两次 + 月末缺报价（2024-11-29）
- SYN.C：1拆2 + 区间内缺报价（2024-09-10）
- SYN.D：同日拆分+分红（2024-09-02，事件顺序确定性由 event_id 排序决定）
- SYN.E：晚进场：有效报价不足 253 条，动量全程缺失（不足预热）

- 人工交易日历：2024-01-02 ~ 2025-02-28，共 302 个交易日，节假日 ['2024-05-01', '2024-10-08']
- 全部数据为本次生成，不伪装交易所数据或上市材料；合成成功不代表真实资料准入。

## 状态

- computation_run = True
- research_qualification = qualified_synthetic_only
- validity = not_tested_by_this_run
- production = not_authorized
- policy = not_applicable_no_account_policy

> 本运行不证明动量指标有效，不构成交易授权；无资金账户计算，政策卡不适用。
