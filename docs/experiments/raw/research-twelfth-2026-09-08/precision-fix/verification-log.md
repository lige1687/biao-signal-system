# 第十二批盈亏比边界修复验证记录

日期：2026-09-08

## 一句话结论（大白话）

价格数字按十进制看恰好达到“潜在收益是风险的 3 倍”时，现在会正常放行；真正少于 3 倍时仍会拒绝，而且旧配置的行为没有变化。

## 改动范围

`engine.py` 从同批 `cash-engine/engine.py` 复制。唯一功能差异是：仅当 `config_id` 属于调用方传入的 `explicit_config_set` 时，信号收盘和次日实际开盘的盈亏比用 `Decimal(str(价格))` 计算并与 3 精确比较。输出字段仍转回普通数值，P0–P7/R0/R1 继续使用原有计算和比较。

## 红灯记录

修复前运行：

`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest -v test_precision.py`

结果为 4 项测试中 2 项失败：

- `test_signal_ratio_exactly_three_is_accepted`：没有成交，证明信号时的 3 倍边界被误拒绝。
- `test_open_ratio_exactly_three_is_accepted`：没有成交，证明实际开盘时的 3 倍边界被误拒绝。

两个“真正略低于 3”的测试在修复前均已通过。

## 绿灯记录

修复后再次运行同一命令：4/4 通过。测试价格覆盖审阅发现的 `ref=4.591, stop=4.563, target=4.675`，以及目标价或开盘价仅低一个十进制小单位的反例。

随后运行：

`PYTHONDONTWRITEBYTECODE=1 python3 -B run_legacy_tests.py`

结果：第九批冻结的 `test_baseline.py`、`test_diagnostic.py`、`test_parent_review.py` 共 41/41 通过。导入方法是先把本目录 `engine.py` 注册为 `engine`，再加载三套冻结测试，因此测试明确执行本修复引擎。

所有命令均禁止写 Python 缓存，本目录没有生成 `__pycache__`。
