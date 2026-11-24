# 用户要求分类浏览与精简首页 — active 2026-11-08T19:01:41.421648+08:00

- 原task-id trae-observation-integration-20261108；owner 01a1ba4c-f7c4-7de2-b51d-9552681be8c4/root；scope_released=false；用户明确要求首页只放常看ERP/宽度，其他指标按用途分类，按需加入首页。属于市场环境展示组织，不做金融实验/规则调整。
- checked_coordination_sha cd4004a827dd50e8963f9ab163c1dcdef736361d；本轮fetch/read COORDINATION1.1、self、cross-market-risk-context、erp-observation-clarity、research-dispatch-controller；相关前端已释放，复用本会话已读策略源/根web规范。原四卡数据与审查结论保持。
- root唯一写 web/src/components/market-observation-alerts/index.tsx, web/src/components/market-observation-alerts/style.css, web/src/components/market-observation-alerts/selection.ts, web/src/components/market-observation-alerts/useSelection.ts, web/src/components/market-observation-alerts/selection.test.mjs 及 docs/ops/trae-observation-integration-20261108/classification/**；worker唯一写 web/src/components/market-observation-alerts/IndicatorBrowser.tsx, web/src/components/market-observation-alerts/indicator-browser.css, web/src/components/market-observation-alerts/indicatorCatalog.ts, web/src/components/market-observation-alerts/indicatorCatalog.test.mjs。不修改observation-library原catalog及他人组件；从既有catalog读取含义/可查看状态，补本首页独有项与行业结构入口。先按实际字节备份，保留共享脏区。
- 目标：首页默认四张ERP/宽度；已知旧自动默认集迁移为四张并保留显式额外选择，自定义子集与收起意图保留，v1原值不覆盖；六类按用途浏览可预览原卡/大图、按市场筛选和搜索、加入/移出首页/恢复核心四项。行业结构改为可选。未接资料项可查看缺项，不能加入空卡。
- 验收：分类完整且唯一/市场和宽度别名；新旧存储/空选择/损坏存储/跨标签/加入后刷新/移出恢复；原数据日期口径/旧弹窗；桌面实际核心四卡/分类/预览/勾选和布局，TypeScript、内存build和归置。当前待执行。
- 当前基线codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；前阶段源码仅本地，远端不可复现；本轮无新成果commit。仅协调元数据正常同步。0金融实验/取数/付费/策略/删除/强推/远端部署；下一步合同预检后真实派发独立分类组件，root做首页集成与存储。

---

# 首页四项观察接入已完成 — 2026-11-08T17:46:27.265650+08:00

- task-id trae-observation-integration-20261108；owner 01a1ba4c-f7c4-7de2-b51d-9552681be8c4/root；status completed；scope_released=true。
- checked_coordination_sha 06c7ea44d5825a8e110726d4a1604ed0cfa8a76a；交付前fetch/read自身原范围，前轮相关任务无变化。root验收后释放全部本轮准确源码和资料路径，无并行写者或后台任务。
- 新增A股512100/510300、美股SMH/QQQ与RSP/SPY、VIX/VIX3M四张小图，同页120/252/全部大图、收起摘要恢复、原卡片选择保持。资料截至11月6日，明确静态未自动按日更新。读数0.6426/0.7071/0.2938/1.042倍，20共同交易日变化-3.14/-11.95/+7.38/+24.81%。
- A股两端重新取得同源新浪原始收盘，其他6系列复用已审Trae缓存；4组2836点独立与原输入核同，60日仅向后，同日内连接。无Trae未来清洗、价格填充、仓位阈值。股债/宽度/真实交易不变，不声称金融收益增量。
- 前端代理gpt-6.1-sol/medium按预检合同完成4路径并释放，root独审差异与实际fixture，追加标的身份和未来日期校验。实际17定向检查、tsc、内存Vite构建、归置通过；HTTP源SHA相符。桌面1710x947四卡/四详情、历史窗口、A股收起刷新恢复、美股收起恢复、Escape回焦点/无溢出/最终无浏览器error已验收。
- 证据 docs/ops/trae-observation-integration-20261108/README.md、manifest.json、data-acceptance.json、acceptance.json、scoped-changes.patch及3张实页图。public快照SHA 1da2f06102a43eb8721ea376cefa724960b0786561f6f94b2daf1b80b85e9c64；输入8条SHA在manifest。仓外原audit/contract/源码写前备份继续保留。
- 失败保留：初次新浪接口名无效，依项目已有provider改正确接口成功；UI组件写入前临时导入失败，待代理就绪再接入；root日期校验一次TS闭包窄化错误，修正后最终全通过。没有降低检查标准。
- 本轮3次公共行情HTTP请求（含失败1）、0金融实验/调参/付费/删除/强推。快照不自动更新，其他ATR/QVIX/流动性候选维持原审阅分级。现有已保存选择不强改，可在添加其他卡加入；本次Chrome实际入口四卡已默认出现。
- 共享codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；仅本地，远端不可复现；无源提交/远端部署/8000dist替换，5173当前入口已生效。仅此协调元数据正常推送。恢复先读README与当前manifest，核源新日期后再确定是否刷新。

---

# Trae观察补齐与首页接入

- task-id: trae-observation-integration-20261108; owner: 01a1ba4c-f7c4-7de2-b51d-9552681be8c4/root; status: active; scope_released=false; updated_at: 2026-11-08T17:34:12.630666+08:00。
- 用户明确批准补齐首页小图并授权布局取舍；此前只读Trae核验已完成。服务于市场环境观察层，四卡VIX期限、SMH/QQQ、RSP/SPY、A股大小盘，不改策略或仓位。
- checked_coordination_sha: 35cffb2cfe0ea59d115397e35da75b8e58cf041e。已读COORDINATION1.1、cross-market-risk-context-20261102、market-increment-map-20261102、erp-observation-clarity-20261107、market-observation、research-dispatch-controller；三项相关前端范围已释放，market-observation当前方向不写本范围。根/web规范与桌面两份策略源已读。
- 基线codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9及共享脏区；仅本地，远端不可复现，无已推成果commit。
- root唯一写：web/src/components/market-observation-alerts/{index.tsx,selection.ts,selection.test.mjs,CandidateShelf.tsx}；web/public/research/relative-market-observations-20261108/**；docs/ops/trae-observation-integration-20261108/**。另仓外本任务implementation证据目录。前端执行者唯一写新增RelativeObservationCards.tsx、relativeObservationData.ts、relative-observation.css（同market-observation-alerts目录）。需要参考线型时允许其精确修改market-style/MarketTrendChart.tsx的可选虚线参数，既有默认不变。不写其他文件，先备份现有字节。
- 保存源数据口径与日期，独立同日配对重算，不复用Trae未来数据清洗/仓位阈值。本地缓存不足时允许只读公共行情补数并留原件。旧快照与研究只读。
- 验收：4组逐点算术/配对/非未来窗口，来源日期；新旧选择持久化与收起恢复；同页放大、时间窗、Escape回焦点；TypeScript和隔离Vite构建；桌面5173实际页面。所有验收当前待执行。
- 当前已做审查、范围核对、源码备份；下一步合同预检后真实派发UI独立子任务，root完成资料及容器接线。无新金融实验/调参/付费/删除/强推/生产交易/定时任务/远端部署。已有负结果见仓外report.md，不重跑。
