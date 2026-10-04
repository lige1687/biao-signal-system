# 黑绿事件与扩大标的资料核查：接续入口

本任务仍由technical-factor-sequence负责；先读取远端coordination/lei的COORDINATION.md与自己的任务记录，避免重开封存题。

总报告：`docs/experiments/color-event-week-context-and-universe-2026-10-04.md`。
四ETF历史新事件问题已完成、未发现稳定增量；行业ETF/个股的效果部分未执行，资格缺口见universe-audit.json。原文买卖条件不修改，不声称完整LEI或线上收益已验证。

阅读顺序：brief.json → universe-audit.json / six-etf-source-audit.json → core四分支qualification.json和core-01/contract.json → core/auxiliary.json → independent-numeric-review.json → registration.json → 综合报告。

## 无行情可复核保存成绩

在仓库根目录：

```sh
python3 -S docs/experiments/raw/color-event-universe-2026-10-04/verify_saved.py
```

只需portable-check.json列出的14个文件（脚本、索引、四题合同/成绩/回执）。成功输出saved_evidence_verified=true、new_fits=0；该核验不证明供应商历史到达或真实盈利。独立目录正常退出0，改坏预测的副本退出1。其他系统及全新环境未测试。

有获准的完整行情时可执行`python3 -S docs/experiments/raw/color-event-universe-2026-10-04/review_numbers.py`，只核直接价格标签、保存系数和简单均值，不重新拟合。首次研究本题及旧实验均已封存，禁止重复运行prepare_contracts.py或核心workflow追求正结果。

## 输入与历史快照

主行情panel为`docs/experiments/raw/volume-information-2026-09-30/execution/panel.json`，SHA256 382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b，1582974字节。来源清单及公司行动原件绑定在合同中。原价、PDF、完整preflight未上传，缺件恢复须按原指纹和授权取得，不能换来源冒充复现。

首green-return20运行后只修正定义卡文案，原数字模型未变；原完整定义登记在core/definition-registry-before-erratum.json，勘误在core/metadata-erratum.json。首分支当前卡会返回stale_proof；主控已在原定义独立快照下验证和通过正式发布，证据historical-snapshot-verification.json。不要改旧receipt/result绑定，也不必重跑4次拟合。其余三题用更正后的freeze-02。源/当前卡差异须保留，不因最新文件存在便声称旧版可直接运行。

## 预算、边界和下一步

四分支合计16真实拟合，回归辅助0新增；ETF/周色历史均值与概率是明确另列的统计估计，不宣称没有估计。失败及勘误见core/execution-ledger.json和controller-record.json，4个现有family ledger路径在各合同。

日20/日60状态、旧周背景、严格相邻黑转绿、EMA持续和本轮事件问题不重跑。下一步只补更大标的集合的真实来源/行动/日历与选择资格；若无新资料，不换参数、模型、日期制造正结果。future-readiness.json复用本核查回答workflow-fusion D5：未来观察仍blocked，取得时间/许可/持续源未闭合；不启动其他负责人暂停的未来SMA20。

没有本题运行中的市场任务、后台采集或待接管进程。本包是成果同步，原负责人责任保持。范围外生产、交易、账户、宽度、情绪不属于本线。
