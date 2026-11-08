# ERP与多指标组合能力复核 — completed 2026-11-08T19:24:32+08:00

- task-id `erp-breadth-integration-review-20261108`; owner `01a1b55e-b30e-7a72-98bc-103222ea9ee5/root`; status `completed`; scope_released=true。checked_coordination_sha=`7f2815d49146005b1a02fb7e6113fb6ad2093689`; checked_at=`2026-11-08T19:24:32+08:00` Asia/Shanghai。
- 目标：回答沪深300 ERP及其“ERP+宽度/趋势/拥挤/信用/跨市场”框架目前打磨到哪一层；逐条审核新提供的阈值和机构实践主张；盘点系统中已有、观察级、缺历史资格、尚未接通的指标，并选出可能互补且可继续验证的少数组合。用途是方法与系统覆盖审查，不是新交易策略。
- 已读协调规则和相关task：`erp-observation-clarity-20261107`（已结案并释放原范围）、`research-dispatch-controller`、`breadth-reading-aid-20261101`、`cross-market-risk-context-20261102`、`market-increment-map-20261102`、`market-observation`、`microstructure-observations-20261108`（他人当前active，仅读）、`trae-observation-integration-20261108`（他人当前active，仅读）、`investor-observation-map`（他人持续任务，仅读）、`sentiment-factor-research`（已存缺口结论）。无接管；不得写上述他人代码/研究范围。
- 基线工作区：`codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9` 加既有大量脏区；不清理、不覆盖。复用 `erp-trend-matrix-2026-11-07.md`、`valuation-portability-review-2026-11-07.md`、`system-indicators-inventory-2026-11-08.md` 及已存宽度/ERP研究，不重跑历史市场回测、不重新挑参。
- 本任务允许写入仅 `docs/experiments/erp-breadth-integration-review-2026-11-08.md`、`docs/experiments/raw/erp-breadth-integration-review-2026-11-08/**`、实验登记新增此报告唯一键及 `INDEX.md` 新增一行，并维护本协调task文件。登记文件含既有共享脏改；写前读当前内容/diff，只增本key、不重排/覆盖。其他实验登记人如出现同路径未解决写入，本任务先完成独立报告、暂缓该两文件并明确记录。
- 只读审查实现：A/美股ERP与轨道、均线趋势、20/50/200日市场宽度、估值/宏观、融资与成交集中度、情绪、VIX/OAS等信用波动观察；检查可用时间、更新频率和point-in-time/覆盖边界。方法对照参考既有报告，必要时复用已核一手来源。
- 验收：给出“已做好/部分做好/未验证”清单；说明各建议组合在金融含义、当前数据链、互补信息/同源重复、样本与实盘边界的判断；至多提出少数证据可达且值得做的增量方向，未支持的阈值保留未验证。无代码、API、权重、交易、生产参数或自动化变更。
- 本轮不加测试、不跑新回测/参数扫描、不新增市场取数；仅完成文献/系统原件/已存证据复核和归档。性能表复用已完成的沪深300 ERP×趋势研究；宽度或其他组合未有合格新绩效结果时明确填未评价。
- 相对上一进度新增：纳入用户2026-11-08关于宽度、拥挤、信用利差、波动率、跨资产流动性及Core-Satellite建议的审核；上一轮ERP×趋势完成结果仍封存。
- 已完成本轮最新用户范围：复核系统ERP口径与阈值/机构主张，评估新增的ERP＋宽度、拥挤、信用/波动及核心卫星建议；沿用已完成的ERP×趋势和ERP/宽度历史证据，不新跑市场回测。
- 结果文件：`docs/experiments/erp-breadth-integration-review-2026-11-08.md`，SHA-256 `47b61888972c9878227bdfc187136c6c58a91f36f887042021ea7cece6e761ff`；原始/归档记录及基线备份在同名raw目录。实验registry仅新增本报告键，INDEX仅新增本报告一行；写后核对原836项registry entries逐项不变，INDEX减去新行逐字还原原本地脏文件。
- 结论：沪深300ERP观察与ERP×MA仓位研究较完整但非同风险优势；完整ERP×宽度/趋势组合未验证，行业估值链不足。推荐分栏展示估值、参与面、趋势、风险背景，ERP显示收益率端与利率端贡献，不产生统一分数或仓位。微观结构任务截至`7f2815d4`仍active，衍生品10项已进可选目录、权益/融资仍补历史；未触碰他人代码。
- 本轮4个公开搜索查询、0行情下载、0新回测、0参数搜索、0软件测试、0交易/生产变更。源代码及其余共享改动没有变更；本地报告未提交到成果分支，未部署。包含本结案状态的协调提交以`git log -- docs/coordination/tasks/erp-breadth-integration-review-20261108.md`定位（不在文件内自指SHA）。
- 本任务问题已答，状态`completed`、scope_released=true。恢复时复用报告/既有证据，不重跑本轮旧窗口；若要做新的策略/资金决策，先登记独立的ERP×宽度问题与合格点时数据。
