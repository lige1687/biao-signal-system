# 执行说明

本目录是宽基ETF技术方法的资金安排扩展实验。它复用已冻结候选，不改变A/C/D定义，也不把R0/R1称为正式策略。

方法编号为A20E、A20J、A60E、A60J、A120E、A120J、C1、C2、C3、D、R0、R1。每个账户输出到`account-results/{symbol}-{method}-fee{10|20}bp/`，包含完整每日账、成交、订单、行动事件和完整持仓回合；总表在`account-results/summary.json`和`summary.csv`。
