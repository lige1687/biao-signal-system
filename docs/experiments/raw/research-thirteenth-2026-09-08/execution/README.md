# 第十三批账户执行说明

本目录只实现锁定协议中的 A 持仓退出比较。`run_accounts.py` 复用第十二批修正版
`precision-fix/engine.py`，没有修改引擎；S 回调不增加退出，T 回调在结构失效未触发时，
检查收盘严格低于 EMA20 且严格低于 20 根前收盘。

正式结果在 `account-results/`。S 与 T 各自保留六配置的 daily、trades、orders、events、
roundtrips，以及候选、汇总、年度和基金贡献。`candidate-status-comparison.csv` 记录同一
504 条候选在两账户中的状态变化。

`fixed-17-paths.json` 是固定原买入日期、价格和数量的 17 笔比较，共 34 条 S/T 路径。
每条含退出信号、逐日尝试、公司行动事件、费用、分红、期末估值和净结果；
`fixed-17-reconciliation.json` 记录 S 与原账的对齐。

观察值的独立重算由同批 `independent-review/observation-results.json` 完成；执行器核对
其 passed 状态、11,158 行零差异、输入锁和源文件指纹后接受，记录见
`accepted-observation-review.json`，没有冒充本执行器再次独立重算。

失败/重跑留痕：

- `failed-attempt-01-account-results/`：首次启动在读取独立观察输入锁时，把列表误当成
  字典，账户尚未运行，目录为空；错误日志保存在 `failed-attempt-01-account-run.log`。
- `failed-attempt-02/`：12 账户与 17 笔均已成功，但随后新增了公司行动边界测试，导致
  已锁测试源码指纹过时，因此整体重跑并封存。这不是策略或数据失败。

`tests.log` 为最终 6 项边界测试结果。`run-lock.json` 锁定最终执行源码、协议、候选、
引擎、价格、行动、观察独立核查及其输入；`completion.json` 记录运行后指纹不变。
