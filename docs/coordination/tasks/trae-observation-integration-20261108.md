# Trae观察补齐与首页接入

- task-id: trae-observation-integration-20261108; owner: 01a1ba4c-f7c4-7de2-b51d-9552681be8c4/root; status: active; scope_released=false; updated_at: 2026-11-08T17:34:12.630666+08:00。
- 用户明确批准补齐首页小图并授权布局取舍；此前只读Trae核验已完成。服务于市场环境观察层，四卡VIX期限、SMH/QQQ、RSP/SPY、A股大小盘，不改策略或仓位。
- checked_coordination_sha: 35cffb2cfe0ea59d115397e35da75b8e58cf041e。已读COORDINATION1.1、cross-market-risk-context-20261102、market-increment-map-20261102、erp-observation-clarity-20261107、market-observation、research-dispatch-controller；三项相关前端范围已释放，market-observation当前方向不写本范围。根/web规范与桌面两份策略源已读。
- 基线codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9及共享脏区；仅本地，远端不可复现，无已推成果commit。
- root唯一写：web/src/components/market-observation-alerts/{index.tsx,selection.ts,selection.test.mjs,CandidateShelf.tsx}；web/public/research/relative-market-observations-20261108/**；docs/ops/trae-observation-integration-20261108/**。另仓外本任务implementation证据目录。前端执行者唯一写新增RelativeObservationCards.tsx、relativeObservationData.ts、relative-observation.css（同market-observation-alerts目录）。需要参考线型时允许其精确修改market-style/MarketTrendChart.tsx的可选虚线参数，既有默认不变。不写其他文件，先备份现有字节。
- 保存源数据口径与日期，独立同日配对重算，不复用Trae未来数据清洗/仓位阈值。本地缓存不足时允许只读公共行情补数并留原件。旧快照与研究只读。
- 验收：4组逐点算术/配对/非未来窗口，来源日期；新旧选择持久化与收起恢复；同页放大、时间窗、Escape回焦点；TypeScript和隔离Vite构建；桌面5173实际页面。所有验收当前待执行。
- 当前已做审查、范围核对、源码备份；下一步合同预检后真实派发UI独立子任务，root完成资料及容器接线。无新金融实验/调参/付费/删除/强推/生产交易/定时任务/远端部署。已有负结果见仓外report.md，不重跑。
