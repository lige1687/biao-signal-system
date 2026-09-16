# 第十二批现金引擎接口验证

日期：2026-09-08

## 一句话结论（大白话）

现金引擎只增加了一个由本批调用方明确传入配置名单的入口；名单内配置沿用原 P7 的 1% 计划亏损预算、实际开盘风险距离、100 份整手和现金上限，旧配置的计算结果没有变化。

## 服务的策略层

本改动只服务于交易规格 §3.2、§10、§13、§16 的成交时点、盈亏比纪律与账户执行。A/C/D 的信号判定、目标价和初始失效位均由候选数据提供；引擎不新增规则、不调阈值，也不把这些配置当成 B 模块。

## 精确改动

相对第九批已核实引擎 `docs/experiments/raw/research-ninth-2026-09-08/reference-engine/engine.py`，`engine.py` 只有三处语义改动：

1. `simulate` 新增可选参数 `explicit_config_set=None`；默认空集合，因此旧调用接口和旧配置范围不变。
2. 配置编号属于 `explicit_config_set` 时允许运行；未显式传入的新编号仍报 `Unknown configuration`。
3. 显式配置与 P7 共用同一仓位计算：前一日单基金权益乘 1%，除以实际开盘价与初始失效价的距离，向下取整到 100 份，再受现金上限约束。

P4/P7 的 `breakout` 形态锁定条件原样保留，只检查 P4/P7；显式配置不会进入该分支。候选完整副本仍保存在 `candidate_metadata`，订单、成交和持仓继续通过 `candidate_id` 关联。

## 先失败、后通过

首次运行 `python3 -m unittest -v test_twelfth_configs.py`：4 个测试中，未传名单拒绝测试通过，其余 3 个测试共出现 14 个错误，统一原因是 `simulate() got an unexpected keyword argument 'explicit_config_set'`。这证明新接口在改动前不存在。

最小修复后重复同一命令：4 个测试全部通过。覆盖：新配置默认拒绝、12 个显式配置的 1% 预算与份数、非 B 形态不触发 P7 锁定、后续候选不能移动持仓初始失效位。

## 旧路径核对

`run_copied_reference_tests.py` 先把本目录 `engine.py` 以模块名 `engine` 导入，再逐一加载第九批冻结的 `test_baseline.py`、`test_diagnostic.py`、`test_parent_review.py`。这样测试中的 `from engine import simulate` 明确指向本批引擎，同时 `test_parent_review.py` 仍能从第九批自身目录读取冻结基线。结果：41 个测试全部通过。

`verify_eighth_reference_tables.py` 从第八批读取原名义价格、14 个已知公司行动、候选和退出观察，再用本批引擎重算 P0、P5、P6。每组的 `daily`、`trades`、`orders`、`events`、`roundtrips` 五张表均与第八批封存结果逐字节或逐对象完全一致，共 15/15 张表一致。

验证脚本只读取旧批次，本批之外没有写入结果；也没有运行第十二批 12 组的真实收益。
