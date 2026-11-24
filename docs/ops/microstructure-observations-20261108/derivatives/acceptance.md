# 衍生品观察包验收（2026-11-08）

入口：`src/lei_signal/market_context/microstructure_derivatives.py` 从保存的原件生成 `web/public/research/microstructure-observations-20261108/derivatives.json`。仅观察，不参与交易判定。

## 本次取得与现值

| 指标 | 最新交易日 | 值 | 历史点数 | 口径 |
|---|---|---:|---:|---|
| 510300期权成交量 PCR | 2026-11-06 | 0.6367倍 | 8 | 当日认沽成交张数/认购成交张数 |
| 510300期权持仓量 PCR | 2026-11-06 | 0.6653倍 | 8 | 日末认沽未平仓张数/认购未平仓张数 |
| 510300近月平值隐含波动代理 | 2026-11-06 | 20.650% | 8 | 2026-11近月、同档认购/认沽有效IV等权平均；Delta最接近±0.5；不是恒定期限QVIX |
| Cboe股票期权成交量 PCR | 2026-11-06 | 0.59倍 | 1 | Equity分类；独立于Total |
| Cboe总体期权成交量 PCR | 2026-11-06 | 0.95倍 | 1 | Total分类；含其他期权产品 |
| Cboe COR3M | 2026-11-06 | 20.47% | 5230 | 官方历史收盘；此前756个完整交易日历史位置82.14%；2006起的早期资料早于2021公开推出 |
| IF2611年化基差 | 2026-11-06 | -9.440% | 5 | 4039.6/4054.28-1，剩14自然日，乘365/14 |
| IC2611年化基差 | 2026-11-06 | -3.458% | 5 | 同日收盘、中证500现货 |
| IH2611年化基差 | 2026-11-06 | -11.046% | 5 | 同日收盘、上证50现货 |
| IM2611年化基差 | 2026-11-06 | -2.144% | 5 | 同日收盘、中证1000现货 |

上述基差值以生成包为准；表中三位小数人工摘录应与JSON核对。期货与指数供应商都只给日K收盘栏，没有逐笔最终成交时间。按相同交易日和共同15:00收市近似对齐，**不能称同步可成交价差**。到期日按中金所[IF](https://www.cffex.com.cn/u/cms/www/202003/27165505w3j5.pdf)、[IC](https://www.cffex.com.cn/u/cms/www/202003/27165958okn6.pdf)、[IH](https://www.cffex.com.cn/u/cms/www/202003/27165822h30l.pdf)、[IM](https://www.cffex.com.cn/u/cms/www/202207/182020307zry.pdf)各合约细则第九条第三个周五规则推得2026-11-20，异常/法定假日顺延；本月逐合约参数XML仍未取得。年化基差未经股息、融资与费用调整，临近到期易放大微小价差，不拼接主力换月。

## 原件与资格

- [上交所每日统计](https://www.sse.com.cn/assortment/options/date/)与[期权风险指标](https://www.sse.com.cn/assortment/options/risk/)：保存2026-10-28至11-06的8个交易日，逐文件与`TRADE_DATE`核对；负分子、零分母、零IV不作有效读数。[上交所股票期权规则第九条](https://www.sse.com.cn/lawandrules/sselawsrules2025/option/c/c_20250610_10781448.shtml)规定到期月份第四个周三，法定假日/休市顺延。近月IV只从当日原件实际列出的合约选取；无顺延公告时按常规第四周三保守排除过期月份。
- [Cboe每日统计](https://www.cboe.com/markets/us/options/market-statistics/daily)：HTML原件内日期为2026-11-06，Equity和Total分别摘取；不是持仓PCR。
- [Cboe COR3M官方CSV](https://cdn.cboe.com/api/global/us_indices/daily_prices/COR3M_History.csv)：按原交易日排序去重；缺失收盘留`null`，不向前填补。756交易日分位严格只用此前完整756个读数，同值按半权并列，即`(低于当值的个数+同值个数/2)/756`；不足或窗内有缺值留空。指标含期权定价的隐含相关，非已实现逐股相关。
- [新浪IF行情](https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_V21052021_4_12=/InnerFuturesNewService.getDailyKLine?symbol=IF2611&type=2021_04_12)及[东方财富沪深300指数日K](https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000300)等四组日K为数据原件；中金所日行情月ZIP及合约参数XML各连接重置1次，未把供应商行情冒充中金所原始行情。

原件在外置盘 `.../microstructure-observations-20261108/derivatives/`，逐件 URL、状态、字节、SHA-256 和路径见 `source-ledger.json`。共29次HTTP请求、2次连接失败、约2.29MB响应；另一次东方财富`2.000300`返回`data:null`，随后用`1.000300`取得有效数据。还剩合同额度1对象，未用于无新判断价值的重复请求。

验证：`PYTHONPATH=src python3 -m pytest -q tests/unit/test_microstructure_derivatives.py`，8项通过；覆盖PCR分母/负数、近月同档/到期、错日/未来日、相关历史缺值/严格历史分位、年化基差零值/时间对齐。生成后读回10张卡、0项不可得。实时刷新、来源再分发条款、期货逐笔时间与新指标预测效果均未验收。
