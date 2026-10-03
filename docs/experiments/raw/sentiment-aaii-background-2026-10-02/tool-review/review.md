# AAII 情绪因子研究的工具复用小审阅（2026-10-02）

结论：**当前最直接可用的是项目已经适配的统计小工具**，用于核对“提前已知的 AAII 情绪条件，是否让这一只 ETF 的后续结果相对已有判断多了一点信息”。提出条件含义、限定当时能看到的数据、选择对照及解释资金意义，仍由本轮研究合同决定。没有理由为此接入另一套完整研究平台。

| 工具 | 对本轮真有用的部分 | 本地状态与不可代替的判断 |
|---|---|---|
| [statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html) / `$lei-quant-tools` | 可考虑连续日期互相影响，估计预先定义的条件收益差有多不稳定；官方文档要求单条等间隔序列。 | 已从 0.15.0 借用两个原函数做窄范围适配，既有报告记录 27 项模拟检查及保留 BSD 许可。还没有替本轮验证真实增量，也不能决定 AAII 的含义或历史可得时间。 |
| [Qlib](https://github.com/microsoft/qlib) | 数据处理、特征表达和研究流程是可拆用的参考组件；官方仓库显示 MIT 许可。 | 已有 Alpha158 定义审阅，未见 AAII 单 ETF 适配。它的多标的排名、模型训练和默认回测不能代替一只 ETF 的历史条件比较；当前没有接入理由。 |
| [RD-Agent](https://github.com/microsoft/RD-Agent) | 将来若有严格冻结的任务，可再评估步骤保存、失败记录和恢复；官方仓库显示 MIT 许可。 | 本地固定版本试跑过已有均线计算，保存与恢复可行；自动提出因子、写代码及模型反馈没运行。试跑还发现步骤上限会多跑一步、停止时有清理警告。官方多股票自动研究的成果不能推成 AAII 的真实收益；本轮不启用。 |
| [Vibe-Trading](https://github.com/hkuds/vibe-trading) | 此次无法确认适合的具体功能。 | 官方仓库可见名称和 MIT 许可，正文未成功显示；本地未适配。不能凭热度或名称推荐其承担语义挖掘或历史检验。 |

这里“增量”指在既有判断相同的情况下，AAII 条件是否还改变未来结果，而不是只看情绪条件单独分组后有没有上涨。多股票同日评分的方法不能直接移到一只 ETF 的时间序列。项目已有 `$lei-data-availability` 和 `$lei-causal-validation` 用来检查消息发布、到达及先后时点；它们是研究边界工具，不是新收益因子。

本次先读[既有工具短名单](../../../research-tool-reuse-shortlist-2026-09-14.md)、[组件采用报告](../../../quant-resources-adoption-2026-10-02.md)和[RD-Agent 试跑复核](../../../rdagent-pilot-controller-review-2026-09-27.md)，然后在三次公开网页请求中查看上述四个官方地址。statsmodels 文档标明 0.15.0；其余网页没有可核定的当前版本。本轮没有安装、下载行情、训练模型或运行新的收益实验；既往明确拒绝访问的 DeanFinancials/deanfi-collectors 涨跌家数资料未再请求。逐项请求结果与限制见同目录 `review.json`。
