# 第十四批 A6② 消费方有效期审计

日期：2026-09-08

## 范围

本目录只验证规格 §9 A6② 的回测消费方：顶部构造确认后，消费方能否在每个交易日正确判断该顶部当时是否仍有效。输入是第十一批冻结研究包；生产目录和旧封存目录均未修改。本项不运行收益或真实行情实验，也不判断“顶部确认日与关键波动同日”是否符合最终策略口径。

## 根因与修复

第十一批 `strict_structure.py` 的结构对象同时保留 `confirmed_date` 与 `invalidated_date`，但原 `backtest/engine.py::prepare_frame` 只保存 `confirmed_date`。`simulate_trade` 因而无法知道顶部后来何时失效，已失效顶部会继续参与 A6②。

研究副本仅修这一处数据传递：预计算结果保存 `(confirmed_date, invalidated_date)`；交易日 `t` 的顶部有效条件为 `confirmed_date <= t` 且 `invalidated_date is None or t < invalidated_date`。不能用最终 `is_valid`，否则未来发生的失效会反向删除此前仍有效的顶部。

原有先后规则保持不动：仍排除入场信号日及更早的顶部，允许入场日收盘确认的顶部用于之后的关键波动，也仍允许顶部确认日当天的关键波动触发。规格 §8.3 的“同时出现”与 §9 A6② 的“后，再出现”存在口径差异，留给用户定义，本修复不代答。

## 先失败、后通过

- 原第十一批引擎：`2 failed, 6 passed`，失败恰为“此前已失效仍触发”和“失效当天仍触发”；见 `red-original.log`。
- 修复研究副本：`8 passed`；见 `green-fixed.log`。
- 测试调用真实 `prepare_frame` 和 `simulate_trade`，只用 monkeypatch 给结构检测器注入明确的结构对象，因此验证的是消费方，不宣称复测了严格结构识别器。

覆盖边界：有效顶部；此前失效；关键波动当天失效；未来失效不得抹去过去退出；入场前顶部排除；入场日收盘确认可供后续使用；旧顶部失效后新顶部可用；原有同日确认行为保持。

## 文件与复核

- `test_consumer_audit.py`：8 个消费方边界测试。
- `research-copy/engine.py`：第十一批引擎的最小研究副本及单点修复。
- `engine-consumer-fix.diff`：相对第十一批冻结引擎的完整差异。
- `input-SHA256SUMS`：第十一批引擎、严格结构实现及测试输入指纹。
- `output-SHA256SUMS`：修复副本、差异及红绿日志指纹。

复核命令均使用 `PYTHONDONTWRITEBYTECODE=1 python3 -B` 和 pytest `-p no:cacheprovider`，避免向旧目录写入缓存。
