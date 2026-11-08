# 观察数据完成、界面集成验收 — active 2026-11-08T23:32:56.362329+08:00

- task-id trae-sector-observation-20261108；owner不变，status active，scope_released=false；checked_coordination_sha de456e4057b4d22e0c7e46d4040055330cf293d1，本次fetch/read自身及既有释放记录（上版列明），无范围冲突。
- 五个源缓存SHA匹配原审计且未修改；四ETF逐日热度、活跃、换手等对原公式差异0；两段前缀无未来数据、缺同日分母拒绝。新金融实验0，原4批预算不重启。静态包1.72MB。
- 分工阶段变更：同任务baseline_review在ready合同integration-ui-contract.json下仅创建4新文件EtfPriceHeatObservation.tsx、etfPriceHeatData.ts、etfPriceHeatData.test.mjs、etf-price-heat.css；原共享文件一直root唯一写。该worker已结束并释放4文件，root现独立接收验收和必要修复，不存在同时同文件写者。
- root已接分类/首页按需/情绪页；代理解析3检查通过。首次主控tsc发现unknown日期类型错误，保留失败并正在修复；实际桌面/内存build尚未验收。来源/复权未全资格，现只观察，不能升级可靠预测信号。
- 根主控唯一继续原登记全部路径。独立可检查产物docs/ops/etf-price-heat-observation-20261108/README.md、data-checks.json、formula-verification.json；源代码仍本地未提交未部署。

---

# ETF量价热度观察接入 — active

- task-id: trae-sector-observation-20261108；owner: 01a1bb25-a628-7242-8a66-504aaf9d08e3/root；status active；scope_released=false。updated_at 2026-11-08T23:27:32.026137+08:00。
- 用户澄清观察用途：可解释、可查看的指标接入系统；有信号证据再升级首页用途。仅本地观察展示，不改策略/仓位/真实交易，不自动置顶，不部署。
- checked_coordination_sha c3b69af47e0feb0acf62b8d695b51673b0a0e74b；已读COORDINATION1.1、trae-observation-integration-20261108、sector-crowding-advice-review-20261102、market-increment-map-20261102、research-dispatch-controller。前三任务最新段已完成释放；首页原owner六类布局与默认核心四项保持；本轮只追加一个ETF观察入口，无其他活跃同写者。
- 基线 codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9，2056条既有脏区保留。最近成果提交无，本轮仅本地，远端不可复现。
- root唯一写路径：web/src/components/market-observation-alerts/EtfPriceHeatObservation.tsx; web/src/components/market-observation-alerts/etfPriceHeatData.ts; web/src/components/market-observation-alerts/etfPriceHeatData.test.mjs; web/src/components/market-observation-alerts/etf-price-heat.css; web/src/components/market-observation-alerts/index.tsx; web/src/components/market-observation-alerts/indicatorCatalog.ts; web/src/components/market-observation-alerts/IndicatorThumbnail.tsx; web/src/pages/SentimentPage.tsx; web/public/research/etf-price-heat-20261108/data.json; docs/ops/etf-price-heat-observation-20261108。子代理仅只读审查并写仓外observation-fit-review.md，无仓内写权。修改前原字节备份。
- 目标：单卡支持512480/515880/159915/510300成交活跃、量价热度、价热分歧事实；分类缩略图、同页详情、加入首页、情绪页入口。来源/日期/历史快照显式；热度不称分位或概率，ETF不冒充行业成分广度或净流入。
- 复用前阶段审计4批和历史结果，不追加金融有效性实验/不换参追正；本阶段只做数据派生与工程检查。输入只读Trae本地4ETF和市场成交缓存，未经完整来源/分红PIT认证，保留限制。无联网采数/付费。小文件预算<10MiB。
- 验收：原缓存SHA一致，派生公式对审计/前缀无未来数据/缺项不伪补，前端解析/日期/缺失，TS及内存build，桌面实际分类小图/切标的/详情/收藏/情绪入口。研究预测结果只引用旧审计。当前检查：已读规范和释放范围，其他待执行。
- 前阶段证据仓外 research-notes/trae-sector-review-2026-11-08/report.md；本次归档 docs/ops/etf-price-heat-observation-20261108/README.md。下一步限定派生与接线。
