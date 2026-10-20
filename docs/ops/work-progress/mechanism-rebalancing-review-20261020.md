# 机制研究与月末股债再平衡审阅

- 2026-10-20：已完成现有流程与代码、原始资料有界审阅。报告：`docs/experiments/mechanism-rebalancing-review-2026-10-20.md`。
- 范围：report_only；0新市场运行，核心规范/源码/技能/原策略保持。
- checked_coordination_sha：0022cc2f296009c66d7d32b8253aeb54c0930946；已读相关task-id与无冲突决定见协调同名任务。
- 独立核对：Sol/medium只读；主控核关键代码、来源、66/106算术、报告API逐字与登记旧721项。归置和diff检查通过。
- 新候选：okr-1439df888f5b，planned，全部后续里程碑未勾；报告链接已读回，未改授权或完成状态。
- 外部来源16请求项/6直接访问失败，工具发现失败1；边界和来源SHA在同名raw。全文与本地实证未完成。
- 主树保留；成果已发布到codex/mechanism-rebalancing-review-20261020@99e7fd1ef64502cd79cd4b6e58ce5629a65af9c4，10个准确文件远端与逐字核验成功；仅本报告/raw/进度与自身登记项。
- 下一动作：本轮已答；新研究须先核固定原方法、产品/时点/成本资料，再冻结一个比较。不重复旧账户再平衡或其他owner实验。

## 月末股债低频适用性检验完成 2026-10-20T18:52:25.254332+08:00

- 用户已授权探索/实践/测试；本轮限定问题completed，候选实际账户用途暂不采用。checked_coordination_sha=c3aced7add992f7768bebae94e0d4c875ec851c4，已读self/dispatch/personal-lowfreq-system-audit-20261018/research-utility-review-20261012/strategy-account-bridge-20261020；后者新个股前向不接管，不与本SPY/IEF重复。
- 报告 docs/experiments/month-end-rebalancing-pilot-2026-10-20.md，raw同名；2003-01—2026-09共285月，方向差+0.5035pp/次，下一开盘+0.4463，剔除2008/2020仍+0.3635。2026九月1正8负、-0.7332pp；日历交互估计范围跨零；225月过去训练预测对相对涨幅误差少0.4955%，不是独立新价格信息。完整账户/净费用/中国ETF未评价，停止本版政策扩展有证据，不是预算中断。
- 新研究模块month_end_rebalancing.py由Sol/medium实现及6合成检查；Astra/medium冻前方法审查补日历控制，后审同意有限结论；另Sol/medium从原JSON独立核285事件、900预测值/675固定斜率，root独核主要区间，最大误差1.43e-14。无参数搜索或旧研究重跑。
- 现有单资产技术入口不支持该外部机制研究，不声称原生workflow通过；独立合同明确采用当前规范及两策略实际SHA。共享主表3个French源格式错误，首轮严格校验失败保留；未改他人字段/校验器。以自身发布分支cd2b634476bad2a2cc67a605aeaee860b9ce2b28中的有效canonical定义表为基线仅加本卡，执行快照82卡严格通过；主表198卡未改。
- 报告registry新增一键、INDEX一行，原723登记值不变；API全文SHA核同，归置/diff通过。目标okr-1439df888f5b v9 paused表示候选用途搁置，前2核查完成，第3实际账户保持false，未代验收。一次purpose进展写入触发接口撤授权，读回v6后恢复原purpose/原授权范围并保留错误历史，详见goal-and-report-receipt；未扩大范围或重复执行。
- 核心1；预定调整价敏感性1；本轮28外部请求项含原文审阅/官方核对，新增1下载失败，前审阅16次累计44；实际token费用未知。原价/分红/PDF/逐月结果在固定外盘，source/manifest完整；小记录本机。
- 大资料与仓外策略原件不进Git；成果分支旧基线没有output_storage，不能声称干净clone可自动重新取数。当前环境可核保存结果，所有26冻结绑定保持。发布本题准确路径与分支定义增量，不推main，不改服务/生产/交易/通知。
- 当前源码/报告已在本机核验，准确Git发布回执下一条追加；恢复先读design/freeze/results-summary/independent-audit，不重跑追正。新的独立时期或具体可核执行问题才重开。
