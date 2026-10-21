# 2025 N-PORT 基金类型来源资格（2026-10-22）

## 当前结论

找到可与 N-PORT 的 `SERIES_ID` 精确连接的官方免费来源：SEC Form N-CEN 季度结构化数据集。官方说明确认 `FUND_REPORTED_INFO` 按 `ACCESSION_NUMBER, SERIES_ID` 记录每只系列基金，并列出 ETF、交易所交易管理基金、指数基金等申报字段。**未取得 2025 年 N-CEN 行数据，因此不能给全体 N-PORT 基金分类或报告覆盖率。** 另用原始 N-PORT 申报的系列编号与 2024／2025 原版招募文件，确认了下列四只**有界的主动管理开放式股票基金候选**，可供共同日期的小规模机制演练；这不是全市场分类，也不是效果证明。已知本机自动请求 SEC 大文件返回 403；本任务没有换身份、凭据或重试下载。

## 四只可复核的有界候选

以下系列编号均直接来自 SEC 对应的 **2024-12-31 N-PORT 申报索引**，不是由基金名称或 accession 前缀猜测。招募文件均为基金自身当年的原始 497K；497K 是 SEC 标为开放式管理投资公司的概要招募文件，正文披露股票投资和经理人主动选择证券。2024 版用于 2024-12-31 至 2025 年新版日期之前；2025 版用于新版日期之后。若中途有补充文件改变分类，仍需单独复核。

| `SERIES_ID`／基金 | SEC 原始系列映射 | 2024 原版 | 2025 原版 | 资格判断 |
|---|---|---|---|---|
| `S000000856` Parnassus Core Equity Fund（PRBLX、PRILX） | [N-PORT 索引](https://www.sec.gov/Archives/edgar/data/866256/000175272425024370/0001752724-25-024370-index.htm)，第 40–47 行，注册人 CIK `0000866256` | [2024-05-01 概要招募书](https://www.sec.gov/Archives/edgar/data/866256/000119312524121889/d777314d497k.htm)，第 10–16、85–101、229–233 行 | [2025-04-28 概要招募书](https://www.sec.gov/Archives/edgar/data/866256/000119312525100238/d897910d497k.htm)，第 20–22、83–101、117–131 行 | 两版均写明主要投股票，顾问按财报、估值、企业质量自主选股；开放申购与赎回。 |
| `S000006037` Fidelity Contrafund（FCNTX、FCNKX） | [N-PORT 索引](https://www.sec.gov/Archives/edgar/data/24238/000175272425037255/0001752724-25-037255-index.htm)，第 36–42 行，CIK `0000024238` | [2024-03-01 概要招募书](https://www.sec.gov/Archives/edgar/data/24238/000002423824000021/filing7318.htm)，第 214–227、97–102、188–191 行 | [2025-03-01 概要招募书](https://www.sec.gov/Archives/edgar/data/24238/000002423825000021/filing8433.htm)，第 204–217、285–290 行 | 两版均写明主要投普通股，以基本面分析选择个股；FCNTX 与 K 为同一基金的份额类别，支持按系列而非份额类别计数。 |
| `S000007112` Fidelity Magellan Fund（FMAGX 等） | [N-PORT 索引](https://www.sec.gov/Archives/edgar/data/61397/000175272425037331/0001752724-25-037331-index.html)，第 41–52 行，CIK `0000061397` | [2024-05-30 概要招募书](https://www.sec.gov/Archives/edgar/data/61397/000006139724000078/filing7534.htm)，第 8–22、97–102、168–194 行；[申报索引](https://www.sec.gov/Archives/edgar/data/61397/000006139724000078/0000061397-24-000078-index.htm)第 14–32、43–49 行同时给出 497K 类型、日期和系列编号 | [2025-05-30 概要招募书](https://www.sec.gov/Archives/edgar/data/61397/000006139725000066/filing8713.htm)，第 8–22、92–97 行 | 两版均写明主要投普通股，以基本面分析主动选择证券；2024 版写明交易所开市日可按基金净值申购／赎回。 |
| `S000011202` Dodge & Cox Stock Fund（DODGX、DOXGX） | [N-PORT 索引](https://www.sec.gov/Archives/edgar/data/29440/0001145549-25-011411-index.htm)，第 36–42 行，CIK `0000029440` | [2024-05-01 概要招募书](https://www.sec.gov/Archives/edgar/data/29440/000119312524118329/d718181d497k.htm)，第 8–12、73–81、91–97、180–190 行 | [2025-05-01 概要招募书](https://www.sec.gov/Archives/edgar/data/29440/000119312525097621/d815578d497k.htm)，第 12–16、76–82、98–99 行 | 两版均写明主要投股票，经理人基于个别企业价值判断买卖；开放申购与赎回。 |

四只在本试点本地 N-PORT 清单中均有 2024-12-31、2025-03-31、2025-06-30、2025-09-30 共同报告端点（清单核对由主控承担；本文件只核类型来源），故可限定 2025 年三段共同区间。招募书的**文件发布日期不等于持仓公开日**；任何使用当时可知信息的统计，还须分别核 N-PORT 披露日期。`0001752724`、`0001145549` 等 accession 前缀不是基金 CIK，上表 CIK 来自 SEC 索引。此四只为按已知名称挑出的候选，不能推论整个主动基金总体，更不能直接与 ETF／指数整体比较。

## 原始来源与确切用途

1. [SEC N-CEN 数据集索引](https://www.sec.gov/data-research/sec-markets-data/form-n-cen-data-sets)，本轮读取页面正文（2026-10-22；页面标记最后更新 2026-09-30）。其 2025 提交季度文件为：[Q1](https://www.sec.gov/files/dera/data/form-n-cen-data-sets/2025q1_ncen_0.zip)、[Q2](https://www.sec.gov/files/dera/data/form-n-cen-data-sets/2025q2_ncen_0.zip)、[Q3](https://www.sec.gov/files/dera/data/form-n-cen-data-sets/2025q3_ncen.zip)、[Q4](https://www.sec.gov/files/dera/data/form-n-cen-data-sets/2025q4_ncen.zip)。这些 URL 从页面链接读取；未下载。SEC 称数据按提交季度发布，来自申报人原始 XML，并注明当前数据集**尚未纳入 EDGAR 25.2 引入的 N-CEN 3.1 版本申报**。因此缺行不能直接解释为没有基金，不能只读某一个提交季度当作全年覆盖。
2. [SEC N-CEN 数据集说明](https://www.sec.gov/files/ncen_readme.pdf)，本轮读取第 1–4、11、23 页。`SUBMISSION` 有 `ACCESSION_NUMBER`、`FILING_DATE` 和 `REPORT_ENDING_PERIOD`；`REGISTRANT` 有注册人层 `INVESTMENT_COMPANY_TYPE`；`FUND_REPORTED_INFO` 以 `ACCESSION_NUMBER, SERIES_ID` 为键，含 `IS_ETF`、`IS_ETMF`、`IS_INDEX`、`IS_MULTI_INVERSE_INDEX`、`IS_INTERVAL`、`IS_FUND_OF_FUND`、`IS_MASTER_FEEDER`、`IS_MONEY_MARKET`、`IS_TARGET_DATE`、`IS_UNDERLYING_FUND`、`IS_FUND_TYPE_NA`。`ETF` 表也有 `SERIES_ID` 和 `FUND_ID`。精确位置：PDF 文本第 149–158、199–200、401–425、843–850 行。
3. [SEC Form N-CEN 原始表格](https://www.sec.gov/files/formn-cen.pdf)，本轮读取第 1–6 页。B.6.a 是注册人“开放式管理投资公司”分类；C 部分须按系列分别填，ETF/交易所交易管理基金还须填 E 部分。第 36–45、180–187 行支撑这一区分。注册人类型不能代替系列层 ETF/指数判定。
4. [SEC 开发者说明](https://www.sec.gov/about/developer-resources)与[站务 FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions)，本轮只读。SEC 允许适度脚本访问，但要求声明真实用户代理；FAQ 给出的样例包含真实联系邮箱（FAQ 第 317–331 行）。本任务不编造联系信息，也不把更换身份当作 403 的修复。

## 可复核连接规则及剩余缺口

- 实际取得文件后，以 `SERIES_ID` 接 N-PORT；同一 `SERIES_ID` 若跨注册人、时期或修订出现冲突，连同 `ACCESSION_NUMBER`、CIK、`REPORT_ENDING_PERIOD` 与 `FILING_DATE` 留痕核实。先按报告期关联 2025 年资料，再明确该信息何时公开；若用于当时可知的判断，只能使用当时已提交版本。2025 提交季度不等于 2025 报告期，2025 年末申报可能在 2026 年才提交。
- `IS_ETF=Y`、`IS_ETMF=Y` 或 `IS_INDEX=Y` 可分别确认申报者报告了相应类型；`N`、空值或缺失**不能单独证明“主动”**。一个指数 ETF 可同时有 ETF 与指数属性，不能用互斥单标签硬归类。筛出“开放式且非 ETF/指数”只产生待核候选；主动管理与股票投资范围仍需对应 2025 版基金原始招募说明书或同等原件，并核精确系列身份。
- 目前没有可读的 2025 N-CEN 类型原值，所以**全体**分类人数、覆盖率及主动与 ETF／指数分组比较尚未评价；上表仅是四只原件支持的小子集。Hugging Face 精确搜 `n-cen` / `sec-ncen` 未找到相关公开数据；GitHub 上发现的 `bensacc/nport-mcp` 仅公布摄取代码及 2026 Q2 数据说明，没有可用 2025 分类文件。第三方代码仅帮助定位官方结构，不作为基金类型事实。
- 恢复全样本比较的条件：通过符合 SEC 要求的真实联系方式取得官方 N-CEN 原始行，或获得可校验原始 SEC 文件及指纹的公开镜像，并按报告期／披露时间联结。四只小子集可先作机制演练，但在缺 ETF／指数同口径类型原值时，不得宣称已完成类型对照。任何路径都不能由数据集目录或基金名称替代实际原件。

本任务只做资料资格；市场收益、持仓变化、资金压力及交易适用性均未评价。
