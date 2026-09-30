# 经典因子与研究基准库：首版使用说明

2026-09-28。参考资料仍放在唯一登记表 `docs/research/definitions.v1.json`，新增 `research_references` 是来源/用途附加记录，计算对象仍用 `objects` 的精确 ID 与版本；没有第二套数据库。`model_definition` 保存成员关系，未拟合的模型没有因变量，不冒充现有 `models` 中的已绑定模型卡。

1. 声明问题：资产、市场、频率、币种、目标、n/h、已有信息、新信息和日期切分。
2. 用 `select_baselines(registry, market='CN', frequency='daily', currency='CNY', asset_type='ETF')` 取得可用对照和逐项排除原因。首版选到 `etf.reference.sma20/ema20/return20/volatility20@1.0.0`；金融股票模型、未实现资料和非ETF对象不会静默混入。
3. 本地连续输出用 `local_features(frame[['close']], n=20)`；保存SMA、EMA、价格距离、过去涨幅、波动和状态。输入只接受close，未来收益字段会拒绝。具体试点沿已确认的状态勘误快照；不改变生产双均线。
4. 外部收益用 `load_published_returns(snapshot, root=repo, market='US', frequency='monthly', currency='USD')`。先从 `sources/snapshots.json` 选匹配快照；函数核原件/输出指纹、单位与日期。月频不扩充为日频，已经减过无风险收益的市场列不再减一次。仅用于事后解释，不直接成为预测输入。
5. 从原入口运行：

```sh
PYTHONPATH=src python3 scripts/run_factor_lab.py \
  --benchmark-protocol docs/archive/handoffs-plans/classic-benchmarks-2026-09-28/protocol-complete.json \
  --out docs/experiments/raw/classic-benchmarks-2026-09-28/your-new-run
```

输出目录必须新建；旧结果/代码/来源指纹不同就拒绝。首次新报告可加 `--register-report`，它向既有实验登记簿增加一个条目；已有路径拒绝覆盖。复算不要加这个参数。

旧 `--protocol` 仍进入合成运行器，不因新接入放宽旧合约。旧冻结协议的登记表与代码身份不能被新版本偷偷替换；若要复算旧研究，使用对应归档代码和登记表快照。

机器结果在 `pilot-complete/results.json`；配置、代码与输入指纹在 `protocol-complete.json` 和 `pilot-complete/manifest.json`；逐次失败/修订记录在 `attempt-history-complete.json`。离线测试不需要联网；网络下载只发生在本次来源获取阶段，不进入测试。

首版支持：单ETF随时间的简单涨幅预测误差比较、原始状态描述和已发布官方收益读取。尚不支持：股票横截面排序、概率模型校准、证券级因子组合重构、对外部收益模型的自动拟合。未支持项不能通过换类型或填零获得通过。

更新资料时新建带抓取日期的来源目录和快照；旧原件/解析/测试期望值不覆盖。许可不明确只保留本地研究使用，不推定可任意再分发。历史发布时间未知的官方序列禁止作为同期起点已经知道的预测信息。

研发完成与因子有效分开：固定工程快照核稳定复算，真实探索检验相对此处的对手/模型是否改善；二者都不授权交易。新研究不复用已看历史冒充独立新证据。
