# 来源与证据清单（510300 获取方案核实）

版本 v1.0.0；2026-09-15。配套：[调研结论](review.md)、[获取规格](acquisition-spec.md)。

## 1. 外部公开页面访问记录（预算 8 次，实用 3 次）

| # | 日期 | 链接 | 结果 |
|---|---|---|---|
| 1 | 2026-09-15 | https://akshare.akfamily.xyz/data/fund/fund.html | HTTP 404（旧路径失效，未获取内容） |
| 2 | 2026-09-15 | 站内检索（akshare.akfamily.xyz，关键词 fund_etf_hist_em） | 定位到现行文档页 fund_public.html |
| 3 | 2026-09-15 | https://akshare.akfamily.xyz/data/fund/fund_public.html | 成功（检索结果标题显示文档版本 AKShare 1.18.91） |

未请求任何行情数据接口、未登录、未取密钥、未安装依赖。

### 页面 3 的关键依据（akshare 官方文档，公募基金数据页）

- `fund_etf_hist_em`：数据源东方财富；`adjust` 参数「默认返回不复权的数据；
  qfq: 返回前复权后的数据；hfq: 返回后复权后的数据」。
- 文档「数据复权」说明：前复权「保持当前价格不变，将历史价格进行增减」；
  「每次股票除权除息，均需要重新调整历史价格，因此其历史价格是时变的」，
  「不同时点看到的历史前复权价可能出现差异」；持续分红标的前复权价可能为负；
  后复权「可以被看作投资者的长期财富增长曲线，反映投资者的真实收益率情况」。
- `fund_etf_hist_sina`：无 `adjust` 参数，文档未声明复权口径（本地代码注释
  称其为不复权，此点无官方文档依据）。
- 注意：以上为 akshare 项目文档对其封装语义的描述，**不是**东方财富或腾讯的
  官方接口文档；后复权「财富增长曲线」表述不等于真实账户含分红财富
  （不含真实现金流、整数份额、费用与到账时滞）。

## 2. 本地证据清单（只读核对）

### 数据获取代码

- `src/lei_signal/data/providers.py`：`TencentPriceProvider`（fqkline/get，
  attempts=3；ETF 缺 qfqday 时回退 day 并标 adjusted=False——本规格禁用该回退）、
  `EastmoneyPriceProvider`（fqt=1 前复权，attempts=3，四主机轮询，lmt=6000）、
  `SinaPriceProvider`（不复权，已退出默认链路）、`ChainedPriceProvider`
  （A 股顺序 tencent→eastmoney）。
- `src/lei_signal/data/cache.py`：缓存来源标记机制（无 meta 或不可信来源视为
  未命中）——新快照不得写入该缓存目录。
- `scripts/backfill_timing_data.py::fetch_a_etf`：akshare 东财 qfq 优先、失败自动
  退新浪不复权——现有候选文件「分支未证」的根源；本方案禁止此回退。
- 已安装依赖（读源码核实）：akshare 1.18.49（`fund_etf_hist_em` 正常路径恰好
  1 次 HTTP 请求，`get_market_id` 为本地判断；无 `lmt` 参数）、yfinance 1.5.2、
  pandas 2.3.3、Python 3.11.7。

### 现有 510300 数据资产（均不得覆盖）

- `~/.lei_signal_lab/cache/timing/510300.parquet`：3465 行，2012-05-28→2026-08-27，
  SHA-256 `a6d518e02313f03cb98ebd69a3e459c9382bd85864f5b1d86771c3c04665fcb4`；
  档位 `producer_candidate_only`（生产分支与价格口径未证）。
- `tests/510300.SS.bars.parquet`：tencent，641 行，2023-12-11→2026-08-04
  （冻结测试快照，覆盖不足本次窗口）。
- `~/.lei_signal_lab/cache/510300.SS.bars.parquet`：tencent，641 行，
  2024-01-23→2026-09-15（生产缓存，覆盖不足）。
- 第三轮冻结原始响应：`docs/experiments/raw/research-third-2026-09-08/06/`
  `sh510300-20{13,15,17,19,21,23,25}.json`，腾讯 qfqday，逐文件 URL/抓取时刻
  （2026-09-08T03:34Z）/SHA-256/行数齐全（`fetch-manifest.json`），拼装
  `sh510300-qfq.csv`（3322 行，2013-01-04→2026-09-07，覆盖本次所需全部区间）。
  **是否钉指纹复用或作交叉核对，属主控待决事项。**

### 分红与公司行动证据（目标 B2 的本地基础）

- `docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12/inputs/actions.json`：
  13 笔 510300 现金分红官方公告记录（公告/除息/登记/支付日、金额、来源 PDF
  及 SHA-256）；评价窗内 6 笔，目标尾部 1 笔（2026-01-19，0.123 元）。
- 同目录 `action-coverage.json`：现金事件「两份公开名单一致，**非连续官方无事件
  证明**」；拆分正式覆盖不完整（2015—2026 全区间未知）。
- `docs/experiments/raw/research-third-2026-09-08/06/510300-official-dividend.pdf`
  及 `dividend-daily-ledger.csv`、`dividend-results.json`（2025-06 窗口实测：
  qfq 比例收益 2.6057% vs 名义+现金 2.4673%，差 0.138 个百分点）。
- `docs/experiments/etf-dividend-reinvestment-reference-2026-09-09.md`：分红再投入
  构造协议与独立复核先例（金额零差异）。

### 日历与合同

- CN 日历：`docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json`，
  SHA-256 `aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1`；
  本轮独立复算：第 21 个交易日=2019-10-08；其前 20 个已核交易日=
  2019-09-02—2019-09-30；2025-12-31 后第 22 个交易日=2026-02-03。
- `src/lei_signal/research/factor_unit/study_contract.py:424-428`：真实模式
  `total_return_wealth` 接受 `snapshot_provenance_bound`/`price_basis_verified`；
  `vendor_adjusted_price_change` 要求 `snapshot_provenance_bound`；`price_basis_verified`
  另需 `vendor_traceable=true` 且 `vendor_response_ref` 非空（:407-410）。
- 主控裁决指出的 P1：上述档位目前可被自填声明升级，代码层未修；本规格以归档
  原始供应商响应作为真实 `vendor_response_ref` 素材，但不替代合同修复。

### 数据质量背景

- `docs/experiments/data-quality-jump-audit-2026-09-02.md`：timing 缓存 9 标的 13 处
  复权断裂跳变（未修）；**510300 不在受影响清单**（该报告注明 510300 相关性
  观察干净）。候选文件所在缓存族存在未修污染史，是「旧缓存不可直接采信」的
  背景证据之一。

## 3. 标未知的部分（无文档依据，不得写成已知）

1. 腾讯 fqkline、东财 push2his 两端点均无供应商官方文档：字段语义、限流策略、
   服务稳定性、历史数据可修订性均未知。
2. 前复权精确调整公式（是否等价于除息日按除息价再投入）未公开。
3. 腾讯 `count>640` 的可靠性；东财不带 `lmt` 时是否截断。
4. 任意历史行的真实 `available_at`（逐行可得时间）。
5. 510300 分红事件的连续官方完整性；拆分事件覆盖（2015—2026 未知区间）。
6. 第三轮冻结快照与本次拟抓快照的数值一致性（未对账，属主控待决的观察项）。
