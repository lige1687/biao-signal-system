# 机构宏观与择时公开框架及系统缺口

- task-id: institutional-macro-gap-20261114；owner: 01a1d305-954b-7ed2-9dc6-430491131d6c/root；status: active；scope_released: false；updated_at: 2026-11-14 Asia/Shanghai。
- checked_coordination_sha: c7e990649d7f247768cc6db7199cfdb5278ec513；已读COORDINATION、research-dispatch-controller、cross-market-risk-context-20261102、market-increment-map-20261102、gemini-factor-fit-20261104、market-observation-panel-v2-20261109；旧成果及预算封存不重跑。
- 目标：以机构公开材料对照系统现有宏观、压力、趋势及宽度，判断缺口及已知交易证据；针对已存ALFRED两个金融条件历史发布版本，只做NFCI与ANFCI可观察差异的描述性资格比较。无资金操作和预测回测，已有策略研究只引用。
- 数据与实验合同：2011-05-25—2026-10-21已存两个历史发布版本，单版本选最新共有观察周，同周零线之上/以下及最近4周变化符号比较，0单列，缺历史时排除；日级发布版本，至少次交易日后可得，不认定盘中。四周变化使用同一版本内相差28自然日的历史观察；不读预测标签、不根据结果选阈值。保留年份与连段，相关仅同期描述，非预测增量或交易。先写合同，再一次计算。
- 唯一写者root：docs/experiments/institutional-macro-gap-2026-11-14.md、docs/ops/work-progress/institutional-macro-gap-20261114.md、独立外盘run；不写共享前端、registry、策略、交易或生产。隔离只读本地与公开来源代理已派；所有实际外部检索总计上限6次，含失败；已用6，Gemini独立答复按用户请求。
- 基础 codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9，dirty worktree保留；成果将仅本地，未部署。验收原始指纹、分母、独立抽样与结果解释；资料或时点不足则仅交描述性边界。

## 追加一项可执行的有界增量研究

既有ALFRED历史版本及SPY含分红调整日价均可复用，且用户要求结合系统看择时/宏观；追加检验“美国金融条件ANFCI能否改善下一季度回报判断”，不改原描述合同。已有数据和历史已见，探索性，不是账户回测。预测比较采用公开日级版本后一交易日收盘可得，至随后63个交易日收盘回报；基准固定为历史63/252日回报、63日波动及NFCI；候选再加ANFCI，另列训练均值对手。2015起按年度向前训练，训练标签须在评价年开始前成熟；同一评价样本、每年训练内标准化与固定岭系数0.001。主指标MSE和两模型配对差，按连续26周块重采样给95%经验范围；保存逐期/逐年反例。新合同与输入指纹先行、仅一批、不调参数、不新取数、不改生产/交易；受资料不足或质量不合格则阻断效力结论。
