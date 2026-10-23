# 美国机构申赎与持仓：已保存输入盘点（2026-10-23）

**结论。** 已有 N-PORT 申报、逐项持仓、基金申赎及一份较长的美股价格候选资料；目前还不能把基金持股变化可靠地接到同一证券的未来季度收益，也不能计算相对动量的选股增量。关键缺口是有生效区间的 CUSIP→证券/价格身份映射、公司行动与退市收益核对、申报实际公开时点，以及覆盖更多经济季度且含流入/流出对照的合格主动权益基金。以下是输入资格盘点，收益、风险和排序相关性均**未评价**；没有重跑四基金试点或按已知结果选样本。

## 已取得的输入及适用边界

| 输入 | 精确位置、版本和本轮读回 | 能用来做什么；目前不能做什么 |
|---|---|---|
| N-PORT 四表 | `docs/experiments/raw/institutional-flow-holdings-pilot-2026-10-21/mirror-qualification/request-manifest.json` 指向外盘 `.../mechanism-rebalancing-review-20261020/mechanism-rebalancing-review-20261020-20261021T235746-99163d862723/result/mirror-trader298/`，固定 `trader298/sec-nport@d8db5addd8261a422aa2df269b764d746b7ceb54`；SUBMISSION、FUND_REPORTED_INFO、FUND_REPORTED_HOLDING、MONTHLY_TOTAL_RETURN 各四个**2025申报季度**，共16 parquet。本轮逐路径核存在与大小，合计约937 MB；没有重新计算全部 SHA。固定 SHA 在 manifest。 | SUBMISSION 有 `ACCESSION_NUMBER/FILING_DATE/REPORT_DATE/SUB_TYPE`，持仓有 `ISSUER_CUSIP/ISSUER_LEI/BALANCE/UNIT/...`，基金信息有 `SERIES_ID`、资产及三个月申购/赎回；可按申报编号先连行为。`MONTHLY_TOTAL_RETURN` 是基金**份额类别**月收益，不能充当所持股票的未来收益。FILING_DATE 是日期，尚无逐申报接受时分和公众可见时点核验。 |
| N-PORT 结构审计 | `docs/experiments/raw/institutional-flow-holdings-pilot-2026-10-21/mirror-qualification/schema-coverage.json`；2025四个申报季度共52,795申报、22,489,592持仓，申报日期 2025-01-03 至 2025-12-31，但报告日期含历史补报。 | 36,464 对相邻89–92天同 series 申报只是结构候选；主动/被动分类、修订版本和证券身份未核，不能据此宣称有36,464个可用独立季度。申报季度不等于经济季度。 |
| 冻结四基金行为样本 | `docs/experiments/institutional-flow-holdings-pilot-2026-10-21.md` 与同名 raw；S000000856、S000006037、S000007112、S000011202。经济端点 2024-12-31→2025-03-31→06-30→09-30，共12个基金季度；四基金均有净流出。 | 只可复用为资料和行为测量样例。四基金互作同股参照，三段时间且缺净流入对照；373条持仓比较不是373次独立事件。不能在这12行拟合收益、阈值或“机构被迫卖出”故事。 |
| 美股逐日价格候选 | `docs/experiments/raw/momentum-three-universe-increment-2026-10-22/source-inventory.json` 指向外盘 `.../us-op-common-history-20261020/us-op-common-history-20261020-20261020T191922-92db83e55b32/result/sources/prices.parquet`，SHA `31193f4a6bb0885ccba6ced1e5956f968a8a81e5c2959b1fe535637a743a0563`。本轮核文件存在、235,241,029字节；先前 parquet 读回12,286,868行，1968-01-02至2026-10-16，字段为日期、**ticker**、OHLC、`adj_close`、`dividends`、`stock_splits`、来源。 | 有价格、分红与拆股候选，可以研究披露后季度收益；但标识只有 ticker，且来源调整和退市末值未全部合格。原取得路线为历史标普500成员及其价格，并不覆盖所有基金持股。不能按基金 CUSIP 直接连接，不能把当前能找到价格的股票当历史全体。 |
| 历史成员及其他身份线索 | 同一外盘 `sources/members.parquet`（日期、ticker，先前读回1,523,200行）、`membership_intervals.parquet`（ticker、start、end，1,801区间）、`fja-history.csv`、`renames.csv`、`exit_gaps.csv`；具体 SHA 见上述 `source-inventory.json`。本轮核 `members.parquet` 存在。`full_check_permno_map.csv` 本轮读到列 `label,year,month,permno,corr,n,match`。 | 是**候选**历史 S&P 500 成员/代码变化资料，不是经官方核实的所有美股或基金所持股票。`full_check_permno_map.csv` 没有 CUSIP；不能用文件名中的 PERMNO 假称完成 N-PORT 对价映射。既有审计仍有729个成员月无候选、218项退出缺口中102项无可观察报价，须保留未知。 |
| 较窄的其他价格与发表组收益 | `docs/experiments/raw/us-op-common-history-2026-10-20/saved-input-inventory.json`：2026-10-13现有IVV持股504只、502只取到价格，为存活者回看；`docs/experiments/raw/us-long-only-factor-evaluation-2026-10-20/saved-input-inventory.json`：OSAP/French 已发表组收益是组合层结果；`docs/experiments/raw/contrarian-market-data-research-2026-10-20/controller/price-input-reuse.json` 为单一 SPY 路径。 | 都不能提供同一证券的 N-PORT CUSIP、动量排名与未来收益共同分布。SPY可作另行定义的市场背景，不能替代个股标签。 |

本轮用 `PYTHONPATH=src python3 -m lei_signal.integrations.gpt_context --view storage` 核到外盘 UUID `DEBA1C85-6059-3865-B50A-A8EE1F80E4D9`、`identity_ok=true`；上述外盘位置可读。该检查与文件存在/大小不等于逐字节重验指纹。外盘资料已有固定 SHA，后续真正计算前仍要按 manifest 复核。没有下载或访问网络。

价格的现有资格边界还包括 `docs/experiments/raw/us-op-common-history-2026-10-20/price-source-comparison-receipt.json`：2020–2024年同代码同日的616,628组日涨跌比较中有18组调整价差异超过1个百分点，而且新旧来源均为 Yahoo，故一致处也不算独立供应商验证。`exit-outcome-qualification-receipt-v2.json` 的退出缺口只有报价候选，并未核实卖出所得或终止价值。这些问题须在实际收益标签阶段逐例处理。

## 要解锁原问题，最少还需什么

1. **先补连接身份和公开时间。** 针对预先界定的主动权益基金、经济季度和股票，取得当时有效的 CUSIP→稳定证券身份→价格 ticker 区间表，记录代码更名、并购、拆分、退市和无法匹配者。固定镜像可能另有 `IDENTIFIERS` 表，可先检查是否能以 `HOLDING_ID` 连接历史 ticker；截至本文件本轮只核了已保存四表，**尚未读取该表或验证映射**。只用发行人 LEI 会混淆同一公司的不同证券类别。N-PORT 每次申报应核修订链、SEC 接受时间与实际公众可见时间；信号最早形成于资料公开之后，收益从其后可执行价格算，不能从报告期末倒起。
2. **扩大且固定基金与时间范围，然后再碰效果。** 复用四只已核类型基金作为锚点；新增年份/基金要在看未来收益前按原版招募文件或历史 N-CEN 分类固定主动权益资格，覆盖更多互不相同的经济季度，实际保留净流入、净流出、无同股参照、退出和不匹配者。现有2025四个申报季可为资料审计起点，不能凭数万结构候选或四基金12行宣布样本充分。若仍只有单一流出状态，只能描述持仓与流量，不能检验流入/流出压力差。
3. **冻结同股未来季度比较。** 单位建议为**公开申报后、同一形成日的发行人证券×未来季度**；同一证券同日来自多个基金时先聚合或明确群组，不能把基金×证券多行当独立收益事件。主指标可选同日横截面的排名相关性（IC，即机构指标排序与之后股票收益排序是否同向），并报告分组收益及下行风险、覆盖和缺失；简单对手为同股同日的过去价格动量和不加机构信息的合格股票组。对动量相近股票分层或使用事前冻结的同池模型比较，保持日期、股票池、资金和成本一致，才可问“新增信息”。收益须含分红、拆股、退市/并购末值；无法确认者记未知，不当零收益或自动剔除。按经济季度/发行人聚合不确定性，避免重叠持仓和同季市场冲击造成虚假精度。

**较小的替代问题：** 已存 `MONTHLY_TOTAL_RETURN` 或另行核实基金份额净值后，可比较公开申赎与基金下一期份额收益。这是基金层的另一个问题，不能替代“机构持仓对发行人股票未来季度收益是否比动量多提供信息”。如果后续只做基金层，须另立目标和基准，不静默改题。

输入盘点完成；原问题的收益与相对动量增量仍因上述身份、时间和结果资料资格缺口而**未评价**。本轮新效果计算、网络请求、付费和生产变更均为0。
