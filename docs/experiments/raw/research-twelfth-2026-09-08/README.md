# 第十二批归档导航

## 一句话结论（大白话）

12组日线账户已经跑完并独立核对。A20约23.45万元的增长几乎来自三笔未卖出持仓，C1的15笔已卖出交易全亏，4组没有买入；不能据此决定正式升级。数值边界问题修复后，财务结果完全不变。

主报告：`../../acd-limited-account-comparison-2026-09-08.md`。

- `protocol.md`、`configurations.json`、`initial-lock.json`：开始前固定方案与输入。
- `research-package/`：第十一批副本；adapter实际导入第十一封存副本，指纹可对照，未改生产。
- `adapter/`：2174原事件、891确认的完整候选与两组参照，891全字段当日重算检查。
- `cash-engine/`：新配置接入与旧行为核查；首轮引擎保留。
- `account-results/`：首轮12组全部账户，保留原错误拒绝记录。
- `precision-fix/`：发现错误后另立协议、十进制纠错、边界测试、候选差异和重跑工具。
- **`precision-account-results/`：报告采用的最终12组账户**，所有候选、订单、成交、逐日金额、年度/基金贡献均在此。
- `independent-review/`：首轮全核及发现两例外；`precision-addendum/`另冻修正版再全核。两份封印均保留。
- `interpretation-review/`：另一路只读核对收益集中、已结束/仍持有、首次/非首次、期末等待等解释。
- `okr-*.json`：仅已批准的第十/十一证据更新，版本10、3/4；本批成果未擅自写入。
- `evidence-cards.json`：按既有证据契约记录研究结论与限制。
- `root-verification.json`：负责人封存前指纹、结果、注册和来源检查。
- `final-manifest.json`：本批文件、主报告与学习补充的最终指纹，共享registry/INDEX及实时OKR不纳入不可变封存。

再运行须复制至新输出目录；不要覆盖本目录任何封存结果。启动程序要求新结果目录不存在。原年度现金流及已知行动、交易近似等限制见第八批资料说明。原作者未定义分支和完整策略待完成清单见主报告末尾；不得由账户核对通过推导未来盈利或完整策略通过。

## 后续AI的接入说明

论文学习内容在 `docs/literature-learning/account-comparison-lessons-2026-09-08.{md,json}`，schema沿用`learning-followup/1`，以paper_id和entry.id增量合并。两条索引分别为sullivan1999、cederburg2020。没有新的全文阅读状态或Zotero写入；页面开发时不得覆盖旧阅读记录。本批不承担新的页面开发。

## ARCHIVE

有限对照已结案，mixed。新退出实验和OKR第十二证据更新需按主报告所述具体范围另行确认，当前不默认执行。
