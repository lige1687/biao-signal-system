# 执行失败留痕

## attempt-01

- 状态：在生成任何账户结果前失败；目录保留为空。
- 原因：研究副本移除了旧首12门槛，但写运行锁时仍引用已删除的 `gate` 变量，触发 `NameError`。
- 处理：不修改第一次锁定的 `run_accounts.py`、`code-lock.json` 和 `engine-attempt-01.diff`；复制为 `run_accounts_attempt02.py` 后只删除这个失效引用，并改用新的 `attempt-02/` 和 `code-lock-attempt-02.json`。

## attempt-02

- 状态：第一个账户已在内存完成，写 `trades.csv` 时失败；部分目录原样保留，不能作为结果。
- 原因：初始买入行没有 `payment_sources`，再投入买入行有该字段；CSV 写出却只取第一行字段，触发额外字段错误。
- 处理：不修改第二次锁定代码与差异；复制为 `run_accounts_attempt03.py`，CSV 字段改为全部行字段的有序并集，并改用新的 `attempt-03/` 和代码锁。
