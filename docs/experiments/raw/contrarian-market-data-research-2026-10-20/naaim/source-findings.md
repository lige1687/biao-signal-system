# NAAIM 来源取得与资格核查（2026-10-20）

本轮只核数据来源、时点与口径，未做收益或交易效果检验。资料原件和解析表存于合同指定外盘 `result/naaim/`，逐文件 SHA-256、请求记录与精确路径见 [source-qualification.json](source-qualification.json)。

| 来源 | 实际取得 | 最新观察 | 时点与限制 |
|---|---|---|---|
| [NAAIM 官网公开工作簿](https://naaim.org/wp-content/uploads/2026/08/USE_Data-since-Inception_2026-08-19.xlsx) | HTTP 200；1,052 行、1,050 个不同日期，2006-07-05—2026-08-19；均值、分位、标准差等 10 列 | 2026-08-19 为 94.49 | 此静态文件直接公开，但官网[主页面](https://naaim.org/programs/naaim-exposure-index/)仍说明公开展示延迟三个月；单个文件不能证明未来会及时更新。 |
| [Winter Research 公开 JSON](https://stock.winterresearch.com/data/metrics-stock.json) | HTTP 200；260 周，2021-10-27—2026-10-14；页面注明 NAAIM 值经 StockCharts | 2026-10-14 为 **74.53**；前周 2026-10-07 为 **86.76** | JSON 自带生成时间 2026-10-20 04:00:07 UTC，本站首页于当日取得；这证明本次可免费读取近周值，未证明每周固定时限或过去首次发布时间。 |

两份新资料重叠的 **252 周均值全部一致**（容差 0.005 个百分点）；Winter Research 与旧封存的官网延迟 CSV 重叠 **131 周全部一致**（容差 0.001）。[ISABELNET 2026-10-16 文章](https://www.isabelnet.com/investor-sentiment-naaim-exposure-index-and-sp-500/)也写 74.53；[OptionsHawk 2026-10-19 周报](https://optionshawk.com/weekly-market-view-10-19-2026/)的搜索摘录写 74.53 和前周 86.76，但直读该页返回 HTTP 403，未重试。ISABELNET 对“两周平均”的描述与官网工作簿单周 `Mean/Average` 字段不一致，口径采用官网字段和逐周重合核验，不依赖其解释句。

官网工作簿的精确下载 URL 来自 Winter Research JSON 的 `naaim.xlsx_url` 字段，随后直接公开 HTTP 读取成功；没有猜测受保护接口。拼接时官网同日值优先，2026-08-26 之后 8 个日期才取公开 JSON，得到 **1,058 个不同日期**。官网原表最早的 2006-07-05、07-12 各重复一次；前者仅精度不同（19.444444 与 19.44），拼接选 19.44。2014-03-18 与 03-19 相隔一天、2015 和 2016 各有一处相隔 14 天，日期异常原样保留并记在输入支持清单；未把敞口裁剪到 0—100%。

只数输入列，不看之后行情：原定 **≤40%** 低敞口有 **155 周、41 段、41 次首次进入**；**≥100%** 高敞口有 **43 周、26 段、26 次首次进入**。连续段按相邻调查日最多相隔 8 天计算，容许早年 6/8 天的周中日期变动；14 天缺口另起一段。逐年支持、缺口日期和口径见 [input-support.json](input-support.json)，逐年 CSV 在合同指定外盘。仅以 2022—2026 为例，低敞口每年分别 19、5、0、1、0 周，高敞口分别 0、2、3、2、1 周；稀疏年份不能靠全历史总数掩盖。

NAAIM 调查周三收盘时主动管理人的股票敞口；[StockCharts 方法说明](https://chartschool.stockcharts.com/table-of-contents/index-and-market-indicator-catalog/decisionpoint-sentiment-indicators)称该序列通常周四或周五更新。旧调查周的实际首次公布时刻、之后的修订版本未知，历史工作簿和当前 JSON 不能冒充当时可得的完整历史。免费读取也不等于取得自动批量采集、再分发或商用授权；本轮仅保存本地研究原件，未部署定时抓取。公开 JSON 的未来可用性及许可仍需核，不能承诺实时数据服务。

本次外部请求共 **25 项**：20 个网页搜索子项、5 个 HTTP GET；4 个 GET 成功，1 个返回 403。403 未再访问同一页。请求明细在 JSON 清单。
