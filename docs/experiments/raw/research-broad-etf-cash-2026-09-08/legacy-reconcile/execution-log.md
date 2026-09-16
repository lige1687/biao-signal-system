# 执行记录

日期：2026-09-08

所有历史计算均使用 `python3 -B`，未运行旧脚本主入口。

## 首次历史执行

命令：

```text
python3 -B docs/experiments/raw/research-broad-etf-cash-2026-09-08/legacy-reconcile/run_reconcile.py
```

当时只用 `input-hashes-before.sha256` 锁定了 13 个旧源码和数据文件。协议已经写好，但本次脚本和旧日曲线尚未纳入锁定清单；最小例在历史计算之后才执行。因此首次执行不算完整的“先边界检查、再锁定运行”。首次生成的整份结果没有另存副本，随后被完整锁定重跑覆盖。

从会话命令输出可保留的首次关键数值为：

```text
A_true_buy_once_hold: end 0.9471601028400451, ann -0.5024286681007739, maxdd -53.90245671642505
A_5pp_equal_weight_rebalance: end 0.9691525262232901, ann -0.2902989114026866, maxdd -46.917790099076925
B_breadth_3tier_5pp_rebalance: end 3.3786970199967508, ann 11.95905101400989, maxdd -32.953003108537345
```

精确缺失：首次 `summary.json`、`daily.csv`、`trades.csv` 和输入后哈希没有独立保留，不能逐字节复核第一次与最终文件完全相同。

## 完整锁定重跑

在 `run-lock-before.sha256` 纳入旧源码/数据、协议、当前脚本和旧 A/B 日曲线后，程序先执行最小例，全部通过才加载历史输入。随后运行同一命令，最终关键数值为：

```text
A_true_buy_once_hold: end 0.9471601028400451, ann -0.5024286681007739, maxdd -53.90245671642505
A_5pp_equal_weight_rebalance: end 0.9691525262232901, ann -0.2902989114026866, maxdd -46.917790099076925
B_breadth_3tier_5pp_rebalance: end 3.3786970199967548, ann 11.95905101400989, maxdd -32.95300310853744
```

两次命令输出的 A 数值相同；B 期末仅差约 `4e-15`、最深下跌仅差约 `1e-13`，属于把接近零的卖空份额钳为零后的浮点尾数变化。资金规则和可读结论未变。完整重跑的前后清单用 `cmp` 检查返回 0。

## 核验命令中的一次失败

首次把分组结果写入 `verification.json` 时，字典使用了 `(account, side)` 复合键，JSON 库拒绝序列化并退出。改为 `account|side` 字符串键后核验通过。该失败发生在结果核验输出，不在资金计算中。
