# 成员日收益离散度、宽度及行业观察 · active

- task-id member-dispersion-20261109；owner 本次离散度升级用户请求/root；status active；scope_released=false；updated_at 2026-11-09T00:49:54+0800。
- checked_coordination_sha=3b0fd796a36a21fa7feb677bdc63393d41825fe8。已读 COORDINATION、microstructure-observations-20261108、trae-observation-integration-20261108、erp-breadth-integration-review-20261108、index-valuation-windows-20261108、market-observation、research-dispatch-controller 相关段。
- 基线 18e64fa632dba5dbad0e5fcae09b4ccc75f119a9 与现有本地未提交卡片。独立快照联调，保留原行业换手正在修改的 equity.json、microstructure_equity.py、目录和缩略图源文件。入口只改已经释放的 IndicatorBrowser.tsx 和 MicrostructureObservations.tsx 的离散度分支。新增 member_dispersion.py、test_member_dispersion.py、prepare_member_dispersion_inputs.py、MemberDispersion.tsx、memberDispersionData.ts、member-dispersion.css、research/member-dispersion/v1.json。与其他指标的共用计算、数据和策略均隔离。三位执行者各有独立文件，root负责集成和验收。
- 用户最新授权：沪深300/标普500当前成员离散度接历史动态分位、市场宽度、指数波动和行业轮动观察。MA5 对历史 MA5，252交易日上限且至少60个有效观测，阈值及数据同日读回。验收分类和首页正常入口、抽屉三图、宽度背离区、降级及状态优先顺序。已登记未验收；无收益回测、生产策略或OKR写入。
- 工作成果当前仅本地，代码远端复现尚未提供。冻结源、其他工作者的文件和既有快照只读。
