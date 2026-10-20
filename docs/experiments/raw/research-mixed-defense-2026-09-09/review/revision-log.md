# 修订记录

首版在结果生成前首次试运行时有一处无法解析的临时代码，未产生任何判断或收益，原文件保留为 `failed-attempt-01-syntax.py`。修正仅删除无效表达式，审核规则未变。

第二次初稿错误地要求 `signals.weights` 合计为0.75，但执行接口保留的是原名单内部权重（合计1），0.75实际施加在订单目标金额；也按成交月份而非真实月度执行事件清空独立预算状态。原版保留为 `failed-attempt-02-semantic.py`。修订后直接核每组订单目标金额等于开盘权益75%，并用 `reentry_events` 的止损来源、恢复信号、成交及月度取消做双向完整性核查。

诊断初版找“下一次月度执行”时未排除 `signals.csv` 中的每日均线退出行，错误报告6个边界差异；保留为 `failed-attempt-03-diagnostic-filter.py`。加上 `trend_states != daily_below_sma200` 后再核。
