# 高收益债信用利差小卡 · completed

- task-id: hy-oas-card-20261109；owner: 本次「高收益债信用利差」卡片重构请求 / root；status: completed；scope_released: true；updated_at: 2026-11-09T00:52:39+0800。
- checked_coordination_sha: ad820ea704b6ba9c06135b24085449038a6d4666。沿用开工所读 COORDINATION 1.1 与同模块任务，交付前读回本记录、行业换手已完成、离散度新范围及集中度历史回填新范围；四个本地精确源文件与活动登记无重叠，全部释放。
- 交付：高收益债卡片折线首尾、日期、两条虚线共用全宽绘图区；右侧独立标签栏、浅绿参考区、超上轨橙色、基点变动及信息按钮。保留原约三年参考带；近一年状态独立按同源第20／80分位，较长窗口报告实际同源历史覆盖，5／10年不报缺失分位。只改展示，不改源数据、策略、交易或生产。
- 源码仅本地、未提交、未部署；远端无法复现改动。共享工作基线 codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；准确源路径 web/src/components/market-style/{CrossMarketObservation.tsx,cross-market-observation.css,HyOasCard.tsx,hyOasReading.ts}。证据在本地 /tmp/lei-hy-oas-card-20261109，含原文件、前后截图、浏览器几何和窗口复核脚本。
- 两种桌面宽度实页几何、交互、开关大图和无溢出通过；定向既有回归、同源数据复算和缺值/下降/无足够历史分支通过；TypeScript 与 Vite 内存构建通过。基线对齐失败已复现。初次提示验证需失焦后再聚焦，邻卡即时计数需等渲染，修正测试前提后通过。无新金融研究、源数据发布、交易或部署。可在本地开发首页查看。

---

# 高收益债信用利差小卡 · active

- task-id: hy-oas-card-20261109；owner: 本次「高收益债信用利差」卡片重构请求 / root；status: active；scope_released: false；updated_at: 2026-11-09T00:44:26+0800。
- checked_coordination_sha: 30d954db140ffdb8c7cc858d85487341664d4034。已读 COORDINATION 1.1、cross-market-risk-context-20261102、breadth-reading-aid-20261101、erp-observation-clarity-20261107、microstructure-observations-20261108、trae-observation-integration-20261108、research-dispatch-controller；相关旧小卡写者已释放，新阶段文件与本轮精确范围不重叠。
- 目的：市场观察展示层。按用户要求修正市场速览小卡宽度/日期、全宽参考带与越线高亮、bp 与窗口口径、缺值信息按钮。引用现有 ICE BofA / FRED 同源数据及实际覆盖。保留共享脏基线 codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；两份策略权威源指纹与确认值一致。
- root 唯一源码写者：web/src/components/market-style/{CrossMarketObservation.tsx,cross-market-observation.css,HyOasCard.tsx,hyOasReading.ts}；本地临时目录保存前后证据。代理只读核对现有来源、样本覆盖和分位。其他图表、源数据、数据服务和交易规则只读。没有新金融回测、策略升级、部署或数据发布。
- 验收：实际桌面图表几何、标签/参考线/高亮与日期；现有来源的 1 年和更长可用样本分位、20 条有效观测变化、缺测/信息提示、TypeScript 与定向回归。当前已定位根因，尚无本轮源码改动/验收或已推送源码成果。推进路径为验证当前卡，保留有出处的实际覆盖边界。
