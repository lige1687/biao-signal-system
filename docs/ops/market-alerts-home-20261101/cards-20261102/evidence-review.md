# 首页市场观察小卡：现有模型证据评审（2026-11-02）

范围：只读复核现有目录、数据适配器和冻结报告；没有联网、取新数、做预测或账户效果实验。这里的“默认”只表示首页阅读顺序，不表示信号效力。现有首页已有中国股债利差（ERP-CN）和中美宽度缩略图；以下不再重复显示这些对象。页面实际最新值须以各来源返回的**观测日期**为准，不能用本报告的历史读数冒充今日值。

## 建议默认四张

| 小卡 / 信息维度 | 为什么与宽度、ERP 不同 | 推荐读法与详情 | 数据状态及关键限制 |
|---|---|---|---|
| **A股融资余额与买入** `cn-financing`：杠杆参与 | 宽度来自股价覆盖面，ERP是估值与债息；融资余额是尚未偿还的借款存量，融资买入额是当日交易额 | 小卡显示融资余额、资料日、较前期变化；详情并列融资买入额与口径说明。不要叫“资金净流入” | 使用现有 `/api/fundamentals/observations?market=cn` 的 `margin_balance` 和 `margin_buy`；只有当前观测，**同口径融资余额历史曲线未接通**，不能借用“两融合计”历史。偿还额、同池成交分母和首次可用时间未核。`web/src/components/observation-library/ObservationMetric.tsx:145-193`；`web/src/components/observation-library/catalog.ts:44`；`docs/experiments/market-observation-content-2026-09-30.md:17-18,35-36` |
| **沪深A股成交额集中度** `turnover-concentration`：交易集中 | 与宽度同属参与结构但分母不同：它问成交额是否由少数活跃股票占据，不是上涨家数；与融资存量也不同 | 小卡明确写“月度历史，截至 2026-09”，显示前5%股票成交额占比及上月变化；详情看断线、样本数、缺月和定义。若首页要求每张都是现时值，则它应改为默认折叠，首页只留三张 | **静态历史，不自动更新，无当日读数。** 供应商覆盖沪深A股，不含北交所/B股；129个月中84个月可用，其余保留空值；末月2026-09为42.158%，5224只股票。45%旧参考线口径未对齐，不是风险阈值。`web/public/research/turnover-concentration/observation.v1.json`；`web/src/components/observation-library/concentrationData.ts:1-86`；`web/src/components/observation-library/projectionSources.ts:28,83-85,125-131` |
| **VIX** `vix`：美国期权预期波动 | 不来自中美价格宽度或股债估值差，提供美国期权市场对波动的定价 | 小卡显示指数点与观测日；详情看历史和标普500范围。升高表示预期波动增加，**没有涨跌方向** | 当前观测来自 `fundamentals.observations(us)`，详情历史来自 `fundamentals.ratesHistory`；两个来源失败状态应分开。对应标普500期权，不能称整个美国或A股情绪。`web/src/components/observation-library/ObservationMetric.tsx:143-184`；`web/src/components/observation-library/projectionSources.ts:32,95-97,173-180`；`web/src/components/observation-library/catalog.ts:33` |
| **美国高收益债信用利差** `hy-oas`：信用风险补偿 | 观察债券市场借钱成本，来源和机制不同于价格宽度、ERP和VIX；与VIX同属压力家族，**不可当作独立两票** | 小卡显示利差、资料日；详情看ICE BofA高收益债历史及与VIX的同向/分歧。利差扩大只说明风险补偿要求增加 | 当前观测来自 `fundamentals.observations(us)`；详情历史复用 `fundamentals.usMacro` / FRED，历史可能修订，FRED公开范围有限。不是违约率，也没有固定顶底线。`web/src/components/observation-library/ObservationMetric.tsx:144-184`；`web/src/components/observation-library/projectionSources.ts:33,100-101,185-189`；`web/src/components/observation-library/metricData.ts:110-124`；`docs/experiments/breadth-companion-observation-discovery-2026-10-26.md:37-40,84-95` |

**默认数量判断。** 现有可读材料足以支持三张有现行接口的卡加一张明确标为“历史月度”的结构卡；不支持凑到五、六张。成交集中度不能排在“今日机会/风险”之列。如果产品上无法让“历史月度”在小卡上显眼，默认只放融资、VIX、HY三张，把集中度移入可选。小卡应让数值、单位、范围和观测日一眼可见；点开后看定义、源、历史、缺口。已有报告要求缺失或陈旧显式显示，不把旧值延伸到今天（`docs/experiments/breadth-companion-observation-discovery-2026-10-26.md:101-109`）。

## 留在可选/折叠区

| 项目 | 位置与理由 |
|---|---|
| `aaii`、`naaim` | 每周补充。AAII是受访个人的看涨减看跌意见，NAAIM是受访主动管理人的**自报**风险敞口；两者样本与含义不同，但都不是全部投资者仓位或短期顶底。现有观测接口可读，历史横轴是调查周，逐期首发时间未核。2026-10-26报告中的NAAIM仍停在2026-05-11，不能因为接口存在就默认显示为“本周”。`web/src/components/observation-library/ObservationMetric.tsx:147-182`；`web/src/components/observation-library/projectionSources.ts:37-38,102-105,190-193`；`docs/experiments/observation-library-baker-2026-10-26.md:42-49`；`docs/experiments/market-observation-content-2026-09-30.md:22-25,39-40,52-60` |
| `ofr-fsi`、`vxn`、`nfci` | 压力家族备选。OFR跨市场压力对VIX有明显描述性重复：冻结报告同日月度比较，水平相关0.802、月差相关0.777；其静态副本仅到2026-10-21，约两工作日滞后且可修订。VXN是纳指100期权波动，可在关注该指数时切换，不必与VIX并列常驻。NFCI仅有2026-09-11—10-09五周静态快照。`docs/experiments/breadth-companion-observation-discovery-2026-10-26.md:39-40,84-95`；`web/public/research/observation-library-20261026/reused-series.json`；`web/src/components/observation-library/catalog.ts:34-39` |
| `erp-us`、`hs300-pe`、`sp500-cape` | 估值背景备选。ERP-CN已常驻；沪深300 PE 与其盈利收益率输入高度重合，别算新增维度。ERP-US是标普500的另一市场估值背景，但盈利端月频，不等于每日新增盈利信息；CAPE更慢且对应Shiller美国市场，月初标签不是公布日。`web/src/components/observation-library/catalog.ts:60-64`；`web/src/components/observation-library/metricData.ts:67-108` |
| `finra-margin`、`baker-wurgler`、`pmi-cn`、`wei` | 慢周期背景。FINRA月报通常次月公布，本地静态副本到2026-09；Baker月度静态副本到2025-12，2025-10的SENT_ORTH缺值，且作者不支持以相邻月差判断情绪变化；PMI月度，WEI周度。可点开看经济或美国融资背景，不挤占每日主要观察位置。`web/public/research/observation-library-20261026/reused-series.json`；`web/public/research/observation-library-20261026/baker.json`；`web/src/components/observation-library/projectionSources.ts:35-42,98-101,132-172`；`docs/experiments/observation-library-baker-2026-10-26.md:55-61` |
| `focus-momentum`、`downside-price-impact`、`salience-str`、`smallcap-turnover` | 历史/快照。焦点股是固定300股、截至2025-12-31，不是原视频公式或当前全A；价格冲击和凸显收益偏向历史到2026-10-23；小盘换手仅2026-10-30同日快照。不能当今日连续模型。`web/src/components/observation-library/catalog.ts:26-30,91-94`；`web/src/components/observation-library/projectionSources.ts:25-30,112-124` |
| 其余 `readable=false` 候选 | 只保留定义及待接入状态。包括盈利广度/盈利修正、等权相对市值权、行业扩散和ETF份额等；缺同池历史成员、财报/预测发布时间或连续份额等，不能用代理序列补成首页数值。`web/src/components/observation-library/catalog.ts:23-80`；`docs/experiments/breadth-companion-observation-discovery-2026-10-26.md:32-55,93-109` |

## 使用边界

这份选择只判断**观察信息的区分度与已有展示资料资格**；没有证明它们可提前识别机会、风险、市场顶底或改善账户。VIX/HY/OFR有压力重叠，集中度/宽度有参与结构重叠；方向不一致时先检查范围、频率和日期，不合成统一分数。现有目录的 `readable=true` 只表示适配器能显示数值，不保证资料新鲜，`projectionSources.ts` 也明确把历史显示与今日可用分开。预测/交易阈值、效用、独立增量均未在本次评审评价。`web/src/components/observation-library/catalog.ts:82-111`；`web/src/components/observation-library/projectionSources.ts:45-52`；`docs/experiments/breadth-companion-observation-discovery-2026-10-26.md:78-109`。
