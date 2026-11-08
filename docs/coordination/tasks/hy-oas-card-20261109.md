# 高收益债信用利差小卡 · active

- task-id: hy-oas-card-20261109；owner: 本次「高收益债信用利差」卡片重构请求 / root；status: active；scope_released: false；updated_at: 2026-11-09T00:44:26+0800。
- checked_coordination_sha: 30d954db140ffdb8c7cc858d85487341664d4034。已读 COORDINATION 1.1、cross-market-risk-context-20261102、breadth-reading-aid-20261101、erp-observation-clarity-20261107、microstructure-observations-20261108、trae-observation-integration-20261108、research-dispatch-controller；相关旧小卡写者已释放，新阶段文件与本轮精确范围不重叠。
- 目的：市场观察展示层。按用户要求修正市场速览小卡宽度/日期、全宽参考带与越线高亮、bp 与窗口口径、缺值信息按钮。引用现有 ICE BofA / FRED 同源数据及实际覆盖。保留共享脏基线 codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；两份策略权威源指纹与确认值一致。
- root 唯一源码写者：web/src/components/market-style/{CrossMarketObservation.tsx,cross-market-observation.css,HyOasCard.tsx,hyOasReading.ts}；本地临时目录保存前后证据。代理只读核对现有来源、样本覆盖和分位。其他图表、源数据、数据服务和交易规则只读。没有新金融回测、策略升级、部署或数据发布。
- 验收：实际桌面图表几何、标签/参考线/高亮与日期；现有来源的 1 年和更长可用样本分位、20 条有效观测变化、缺测/信息提示、TypeScript 与定向回归。当前已定位根因，尚无本轮源码改动/验收或已推送源码成果。推进路径为验证当前卡，保留有出处的实际覆盖边界。
