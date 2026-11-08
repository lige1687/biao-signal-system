# 新阶段：ERP × 宽度 × 趋势增量检验 — active 2026-11-08T20:14:05.616535+08:00

- 稳定task-id erp-breadth-integration-review-20261108；owner 01a1b55e-b30e-7a72-98bc-103222ea9ee5/root；status active；scope_released=false。本阶段研究id erp-breadth-trend-increment-20261108，旧review已完、旧ERP22政策及宽度负结果保持封存。
- 用户新增明确授权“继续把ERP和宽度、趋势结合起来做一下测试验证，缺的数据能补就补，看看有没有实际增量，有用的再接到看板里”，以及不同宽基ERP口径、相对EY补充。主问题固定沪深300ERP×趋势后宽度的资金/风险增量；跨指数先核同口径资料，避免混入主测试。
- checked_coordination_sha=667ae1f54768ee72f92d3b79052125ad4215c0a4；checked_at=2026-11-08T20:14:05.616535+08:00。已读COORDINATION和原self、erp-observation-clarity、breadth-reading-aid、market-increment-map、cross-market-risk-context、trae-observation-integration、microstructure-observations、investor-observation-map、research-dispatch-controller。当前trae/microstructure阶段完成释放；不接管其他数据/布局。
- 基线 codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9 加共享dirty；只保留准确新路径。root写 docs/experiments/erp-breadth-trend-increment-2026-11-08.md、同名raw/**、registry唯一新键、INDEX一行、本协调记录。初期两只读代理各写自己的/tmp/lei-erp-breadth-20261108/*-audit.md。新运行大结果走已核外盘、旧输入不动。
- 未来仅若有明确用途证据，接本轮结果至已存在ErpCrossChart详情/新独立研究摘要；实际共享源码修改前再次登记准确路径。此时无UI写权占用，不改首页布局、生产规则、两份原策略、真实交易、定时采集或其他研究。
- 规范采用current-standards所列现行版本，research-closure+lei-lowfreq-research；政策/account属于独立research runner，非强行套技术ridge。数据先复用已获取清单及冻结ERP/宽度历史；修订史/成员和首发时点缺口明确披露。
- 新问题预算上限核心1批+必要跟进3批（每批1个预登记尝试），来源请求6次含失败，每操作至多1重试；旧研究预算不重置，不搜参。代码/合成验证另记，不充当市场证据。小记录预计5MiB，新数据/结果100MiB走外盘。
- 验收：同期间同资金同成本的嵌套比较与宽度独立对照；投入匹配、费用/滞后、分期/遗漏大行情、相关日期不确定性；关键数字独立重算和来源时间检查，结果足以改变判断才进入观察板。无数据/证据不足为真实边界，不将界面完成当金融效果。
- 当前数据与runner只读审计已真实派发，正式协议待输入可用期确定后冻结；尚未执行市场回测/补数据请求。本阶段代码和产物仅本地，协调元数据已推后读回才算同步。

---

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
