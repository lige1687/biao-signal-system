# DeanFi 均线上方股票占比：公开说明核验（2026-10-02）

## 结论

本次只核对来源说明，不检验交易效果。现有公开文件足以确认：这份历史数据自称来自 Yahoo Finance 的标普 500 股票数据，逐日给出高于 20、50、200 日均线的股票数和占比。它不足以确认每天纳入哪些股票、是否按当日历史成分选股、如何处理缺失价格，以及使用原始收盘价还是调整后收盘价。因此，不能把它称为已经核实历史成分与计算口径的标普 500 市场宽度序列。

## 证据与边界

- 数据仓库根目录 [README](https://github.com/DeanFinancials/deanfi-data/blob/main/README.md) 列出 `advance-decline/ma_percentage_historical.json`，标为盘中每 15 分钟更新，简述为 50/200 日均线宽度；同页说明市场数据来自 Yahoo Finance。保存快照为本目录 `README.md`，SHA-256 为 `f9dda47f019b1badaa21c71769dcf1d6eb4581f275f845be8d14cefc4104e0c3`。
- 已保存的实际数据文件 `docs/experiments/raw/sentiment-short-history-2026-10-02/inputs/ma_percentage_historical.json`，SHA-256 为 `613fa152ee6cf2820df59f5566eb4601bda2f1c71747b7bda96d8128282011c7`。其 `metadata` 自述范围为 S&P 500、股票总数 503、来源 `Yahoo Finance (yfinance)`、周期 2 年、均线周期 20/50/200。`field_descriptions` 定义 `date` 为交易日、`count_above` 为高于均线的股票数、`percentage_above` 为高于均线的股票百分比。实际 404 行日期为 2025-02-24 至 2026-10-01，每行均有 `ma_20`、`ma_50`、`ma_200`。README 的 50/200 简述遗漏了文件中的 20 日字段，以实际文件结构为准。
- 从数值反推，占比与 `count_above / 502` 或 `/ 503` 四舍五入到两位小数相符；例如 2025-02-24 的 50 日值为 `273 / 502 = 54.38%`。这只是算术一致性，不证明分母变化的原因，也不证明成分政策。`metadata.total_stocks=503` 不能当作所有历史日期的固定分母。
- README 没有给出历史成分名单或入选规则，也没有说明均线计算、停牌/缺失值处理、复权/分红调整。该数据文件同样没有这些定义。上述事项均标为**未知**；不从名称或数值变化倒推为既成事实。
- README 的 MIT 说明明确针对**代码**；数据另受原始提供者条款约束。README 虽称可供个人或商业使用，不能据此宣称 Yahoo 原始数据有商业再分发权。本任务仅将快照用于本地来源核验，不作商业授权判断。

## 访问记录

本轮仅进行一次公开网络读取：读取数据仓库根目录 README，HTTP 200，19,046 字节。未读取受限的 `deanfi-collectors/advancedecline` 目录或其算法代码，未换用其他渠道恢复该目录。其余判断来自已保存的本地资料与本地算术核对。详情见 `source-ledger.json` 与 `qualification.json`。
