# 数据来源清单 · vix-sentiment（2026-09-01）

全部数据公开可复现（无会员墙、无试用期），下载日 2026-09-01。
sha256 见 `data_sha256.txt`。所有文件只读使用，未改动任何原始 raw 目录。

## CBOE 官方（VIX 家族，免费 CDN CSV）

| 文件 | URL | 覆盖 |
|---|---|---|
| data/VIX9D_History.csv | `https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv` | 2011-01-04 → 2026-08-31 |
| data/VIX_History.csv | 同上目录 `/VIX_History.csv` | 1990-01-02 → 2026-08-31 |
| data/VIX3M_History.csv | 同上目录 `/VIX3M_History.csv` | 2009-09-18 → 2026-08-31 |

说明：CBOE 免责声明为"informational purposes only, possibly preliminary"。

## CBOE 官方（股票 Put/Call 比率，遗留资源文件拼接）

**事实更正（2026-09-01，留痕）**：首版记"1995-09 起 24 年"是错的——
`pcratioarchive.csv` 的 EQUITY 列 2077 行只有 50 个非空值（1995-2003 段
只有 TOTAL/INDEX P/C），且这 50 天与段2 重叠。**股票 P/C 实际起点
2003-10-21，共 16 年**。

| 文件 | URL | 覆盖 | 用途 |
|---|---|---|---|
| data/equitypcarchive.csv | `https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/equitypcarchive.csv` | 2003-10-21 → 2012-06-07 | 段A（只取 ≤2006-11-01） |
| data/equitypc.csv | 同上目录 `/equitypc.csv` | 2006-11-02 → 2019-10-04 | 段B（≥2006-11-02） |
| data/pcratioarchive.csv | 同上目录 `/pcratioarchive.csv` | 1995-09-27 → 2003-12-31（EQUITY 列仅 50 值） | 覆盖校验，不进拼接 |

拼接核查（2026-09-01 实测）：
- 段A∩段B 重叠 1409 天 corr = 0.991，MAE = 0.0104，均值差 +0.002（段A 略高）
  ——疑为初步成交量 vs 清算成交量口径差。拼接缝在 2006-11-01|02，日度噪声
  ~1.5% 量级，对扩张窗口分位（≥90 分位触发）影响有限，已在归档"局限"声明。
- data/totalpc.csv（总 P/C 2006-11→2019-10）备用未用，仅存档。

**数据工程欠账（显式登记）**：
1. 股票 P/C 比率 2019-10-05 → 2026-08-31 无公开可复现通道：CBOE 遗留 CSV
   全族冻结于 2019-10-04；CBOE JSON API（cdn.cboe.com/api/global/market_statistics）
   对脚本取数 403（反爬，与 LEI 组 2026-08-28 记录一致）；Yahoo ^CPCE/^CPC 已
   下架（404）；stooq 启用 JS 工作量证明反爬。不用不可复现通道硬凑。
2. AAII 全史会员墙（无任何本地数据），NAAIM 仅 130 周公开样本——交叉验证
   只能用 NAAIM 重叠窗（2023-11→2026-05），AAII 缺席。

## 仓库内复用（只读拷贝，来源目录未动）

| 文件 | 来源 | 覆盖 |
|---|---|---|
| data/gspc_ohlc.parquet | raw/module_e/us_gspc_ohlc.parquet（yfinance ^GSPC） | 1985-01-02 → 2026-08-26 |
| data/qqq_ohlc.parquet | raw/module_e/us_qqq_ohlc.parquet（yfinance QQQ） | 1999-03-10 → 2026-08-26 |
| data/gold518880_close.parquet | raw/gold_expand/518880_close.parquet（A 股黄金 ETF） | 2013-07-29 → 2026-08-31 |
| data/naaim_hist.json | raw/sentiment/naaim_hist.json（官方嵌入图表解析，130 周） | 2023-11-29 → 2026-05 |

阴性对照资产 = 518880（黄金，与美股恐惧情绪机制无关的资产）。

## PIT 口径

VIX 收盘 16:15 ET 公布、P/C 成交量数据收盘后隔夜才定稿——两者当日收盘时
均不可得。全部信号按"信号日 t 收盘生成 → t+1 收盘可执行"处理，远期收益
从 t+1 收盘起算（不含 t+1 当日收益，防前视）。
