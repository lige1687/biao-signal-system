# 多方案共同比较只读适配：工程执行记录

## 一句话结论（大白话）

已做出一个只读取保存预测误差的窄工具：它先确保所有候选在同一批完整日期、同一组标的和同一个预测目标上比较，再一起估计“多个方案里挑出最好者”可能受到的历史偶然性影响。21个合成边界测试通过；尚未运行任何真实归档演示，不产生新的因子有效性或交易结论。

## 交付与输入合同

代码为 `.agents/skills/lei-quant-tools/scripts/multiple_comparison.py`，合成测试为 `tests/unit/test_multiple_comparison.py`。脚本支持：

- `compare-losses INPUT.json`：直接读同单位逐日损失，不训练模型。
- `compare-workflows RUN_DIRS... --start YYYY-MM-DD --end YYYY-MM-DD --baseline B0|B1 --block-size N --reps N --seed N`：逐目录调用现有 `workflow_bridge.read_archived_run` 核归档收据、哈希和运行登记，再调用 `prepare_workflow_input` 核资格，才从已保存预测计算逐日平方误差；不改归档文件。

直接输入格式 `lei-multiple-losses/1.0`：顶层必须提供 `schema_version`、`unit`（`percentage_point_squared` 或 `probability_squared`）、`frequency="qualified_session"`、严格递增且至少3日的 `calendar`、`benchmark_id`、不重复的 `candidate_ids`（1至64个）、`block_size`、`reps`、`seed` 和 `rows`。`rows` 必须逐项对应完整日历，每项恰好为 `{date, benchmark_loss, models}`；`models` 的键要与全部候选身份精确一致。每个损失是非负、有限的数字，布尔值拒绝。抽取长度为1至日期数，次数为1至10,000，种子为非负整数；这些是资源与算术边界，不是金融有效性门槛。

归档多运行入口要求所有运行的所选基准逐行完全一致，逐行 `asset/date/id/fold/y/label_end` 完全一致，日期池、损失单位和原主指标一致，且选定区间只含一个完整的已拟合评价期。任何运行的资格为 `not_applicable` 时整体返回同状态。候选身份使用唯一归档路径，不从文件名推断因子定义；每份来源指纹和资格摘要随结果带回。每天同一组ETF的误差先取均值，每个日期作为共同抽取单位。区间有缺日或标的不完整时由现有桥接层拒绝，不把日期压缩或把缺失误差当零。

实际统计只调用限定保留的 arch 8.0.0 `SPA`，指定 `bootstrap="circular"`、`studentize=False`、`nested=False`，并只报告 `upper` 的共同检查数值及各候选平均误差差额。若不同身份候选的逐日损失完全相同，或某候选与基准的逐日差额恒定（包括完全相同、恒定改善或恒定恶化），直接拒绝，防止该实现的严格大于比较在全零或恒定差额时给出误导数值。当前“恒定”采用逐日浮点差额**严格相等**；极微小的数值噪声不归入恒定，若以后要设容差，应另行冻结并测试。还检查差额有限且不超过算术安全范围，以免抽取方差的平方发生溢出；这不是效果阈值。

## 一次工程测试与未做事项

一次合成测试批的真实命令、退出码和完整输出在 `engineering-test-1.json`：`21 passed in 1.41s`，退出码0，没有第二次运行。用例覆盖可重复输出、改善与恶化同时存在、重复身份/同值候选、基准恒差、缺日期、日期错位、候选缺项、布尔/负数/非有限/溢出损失、参数上限、归档资格不适用，以及跨运行身份、目标、日期和基准不一致。归档接口在测试中使用合成替身，不伪称已核真实市场文件。

本执行者没有联网、安装依赖、拟合、新因子研究或读取 tsfresh 真实未来结果。主控负责独立数学核验、实际归档只读演示和技能文档。输出数值只适用于声明的候选、基准、日期及同单位损失；不能推断完整历史尝试已覆盖、后续市场有效、交易收益改善或策略规则需要修改。
