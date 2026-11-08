# 成员日收益离散度、宽度及行业观察 · 本地验收完成

- task-id member-dispersion-20261109；owner 本次离散度升级用户请求/root；status completed；scope_released=true；updated_at 2026-11-09T00:59:20+0800。
- checked_coordination_sha=aafe87ad58306b73a3b34f8ab0abf4be0de3a970。重核自身、trae-observation-integration-20261108、microstructure-observations-20261108 及变更索引，沿用已读 COORDINATION 和中控。两个集成文件对照隔离前字节；保留原集中度、行业换手、目录及原股票快照。
- 现有指标库和首页已接沪深300与标普500。固定成员单日离散、MA5/20、历史 MA5 分位和滚动 P20/50/80、MA20/60 宽度、RV20/分位、六状态诊断、行业比值及三层联动图。标普500行业比值至10月30日，11月6日离散与诊断可读、行业比值留空。沪深300成员止于10月23日，指数行情11月6日。两地均有252个历史 MA5。未新增交易或回测。
- 数据快照 SHA256 60f4d0f784df39e61fefa5523f1b06ab3321035c1a3bc41358fbaa8f5680f6a8。来源与覆盖、按需重建和验收见 docs/ops/member-dispersion-20261109/README.md；手工快照原件整理器已移入 scripts/archive/prepare_member_dispersion_inputs.py。
- 本地5173实页核两个市场的指标库和首页、阈值、两开关与区间、弹窗焦点和缺包回退；独立 NumPy 对两地复算。定向 Python 36、Web 28、TS、Vite 内存构建、归置均通过。沪深300 2.44百分点/P31.3，标普500 2.78百分点/P99.6。三位协作者返回，验收释放。
- 工作基线 18e64fa632dba5dbad0e5fcae09b4ccc75f119a9，源码与资料仅本地未提交，未部署。远端只同步本协调记录，远端不含本地应用改动。

# 成员日收益离散度、宽度及行业观察 · active

- task-id member-dispersion-20261109；owner 本次离散度升级用户请求/root；status active；scope_released=false；updated_at 2026-11-09T00:49:54+0800。
- checked_coordination_sha=3b0fd796a36a21fa7feb677bdc63393d41825fe8。已读 COORDINATION、microstructure-observations-20261108、trae-observation-integration-20261108、erp-breadth-integration-review-20261108、index-valuation-windows-20261108、market-observation、research-dispatch-controller 相关段。
- 基线 18e64fa632dba5dbad0e5fcae09b4ccc75f119a9 与现有本地未提交卡片。独立快照联调，保留原行业换手正在修改的 equity.json、microstructure_equity.py、目录和缩略图源文件。入口只改已经释放的 IndicatorBrowser.tsx 和 MicrostructureObservations.tsx 的离散度分支。新增 member_dispersion.py、test_member_dispersion.py、prepare_member_dispersion_inputs.py、MemberDispersion.tsx、memberDispersionData.ts、member-dispersion.css、research/member-dispersion/v1.json。与其他指标的共用计算、数据和策略均隔离。三位执行者各有独立文件，root负责集成和验收。
- 用户最新授权：沪深300/标普500当前成员离散度接历史动态分位、市场宽度、指数波动和行业轮动观察。MA5 对历史 MA5，252交易日上限且至少60个有效观测，阈值及数据同日读回。验收分类和首页正常入口、抽屉三图、宽度背离区、降级及状态优先顺序。已登记未验收；无收益回测、生产策略或OKR写入。
- 工作成果当前仅本地，代码远端复现尚未提供。冻结源、其他工作者的文件和既有快照只读。
