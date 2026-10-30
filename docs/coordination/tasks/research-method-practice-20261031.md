# 研究方法与实际操作补强

- task-id: research-method-practice-20261031；owner: 01a178be-0af9-7801-b956-dcc39a312850/root；status active；scope_released false。
- checked_coordination_sha: 640a3e896dbb22a223bf6c582ead74dc4c5d41a3；checked_at: 2026-10-31T00:17:31.648605+08:00。
- 用户本轮授权按优先级落实六项研究方法、五项实际操作问题，审计外部工具已有接入；研究不限ETF，股票横截面/行业/母指数/状态均可；多ETF分散降级。无自动交易、参数搜索或批量挖掘授权。
- 已读task-id: research-dispatch-controller, classic-factor-research, market-observation, market-style-observation-20261020, investor-workspace-simplification-20261012, strategy-account-bridge-20261020, lowfreq-strategy-discovery-20261019, research-utility-review-20261012, technical-factor-sequence, investor-observation-map, theory-workflow-system-increment, personal-lowfreq-system-audit-20261018, focus-stock-universe-20261024, portfolio-trends-20261013。
- 基线codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9加共享原修改；仅本地，无已推源码成果，不用HEAD代表新内容。协调元数据单独worktree普通推送，读回后开写。
- 冲突决定：focus-stock最新仅observation-library与MarketStylePanel布局，本方避开；investor-observation-map保持IndexComparison/模型/原图和ETF源，本方只OverlaySection新增两同对象估值选择；market-style旧workbench范围已释放，窄接原比较区；preparation只新增可选独立研究尝试索引，不动原定义/账本/执行器。其他旧研究与预算不重跑。
- 精确写范围：src/lei_signal/research/attempt_review.py、account_input_review.py、preparation.py仅可选只读查询；对应tests/unit/test_research_attempt_review.py、test_account_input_review.py；src/lei_signal/fundamentals/service.py仅overlay_history；tests/unit/test_fundamentals_valuation_overlay.py；web/src/pages/FundamentalsPage.tsx仅OverlaySection；web/src/components/fundamentals/ValuationPriceObservation.tsx、valuationPriceObservation.ts及.test.mjs；web/src/pages/factor-workbench/FactorWorkbench.tsx仅本轮证据卡接线、web/src/pages/factor-workbench/ResearchUseReview.tsx及必要本区样式；docs/archive/handoffs-plans/research-method-practice-20261031/；docs/experiments/research-method-practice-2026-10-31.md及同名raw小证据；docs/ops/work-progress/research-method-practice-20261031.md；research-workflow-usage.md只追加新查询用法；registry仅本报告键/INDEX仅本行（写前重核）。
- 唯一写者按plan.md分工，3位原Sol medium先完成只读审计；root持归档和前端工作台，其他每文件单写。实际成本未知。
- 验收：真实旧尝试只读返回/缺项与已见历史不升级；账户缺字段拒绝推断、同现金不可重复使用；估值同对象配对日期与失效边界；10/24原证据逐数对应；相关单元/CLI/真实页面、归置及源指纹读回。
- 当前完成只读能力盘点；代码未改，未跑新市场试验；0新源请求/拟合/交易。原预算封存。小代码/证据预计<4MiB，存储fresh>5GiB；大结果0。
- 下一步：登记读回后实施上述有限增量，独立验证、原报告归档和剩余依赖记录。仓外OKR DB若位置不在repo则只准备更新内容，不越权写。
