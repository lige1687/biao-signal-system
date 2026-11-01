# 宽度读图辅助与上下轨 — active

- task-id breadth-reading-aid-20261101；owner 01a19564-4987-7ed3-a08e-efa86bf7e4b7/root；status active；scope_released false，仅以下准确路径。
- 用户在本聊天2026-11-01明确批准上一轮探索方案落实：“可以搞一下…帮助我们阅读…直观的看到…趋势在延伸，还是形成顶底…上下轨…也可以做”。用途仅描述性读图，不变更技术交易规则/仓位/旧冻结研究。
- checked_coordination_sha bcc414935db0c0529b3d1525f96c3b3556c42ab3；checked_at 2026-11-01T12:50:39.076902+08:00；已读COORDINATION、research-dispatch-controller、market-style-observation-20261020、investor-observation-map、sentiment-factor-research、focus-stock-universe-20261024最新相关段。
- 重叠决定：focus-stock-universe-20261024当前独占observation-library ERP与projection及其资料包；本方只读复用入口，不写该目录、不接手其ERP工作。market-style旧前端修复已释放；本方仅BreadthComparison及自身新组件/CSS。老情绪效力研究、策略原件/阈值、冻结实验只读，不重跑。
- 基线共享工作区codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9加已有脏区；保留他人全部改动。源码暂仅本地，未推成果；独立coord元数据提交，不提交共享源码。
- Python agent独占新增src/lei_signal/market_context/breadth_observation.py、tests/unit/test_breadth_observation.py、tests/unit/test_breadth_observation_route.py，及src/lei_signal/api/routes/symbols.py中market_context_breadth_history函数的最小可选扩展。
- root独占web/src/components/market-style/BreadthComparison.tsx、breadth-comparison.css、新BreadthReading.tsx、breadthReadingTypes.ts及必要同区展示测试；web/src/types.ts仅BreadthHistoryResponse可选observation字段。计划docs/superpowers/plans/2026-11-01-breadth-reading-aid.md；进度docs/ops/work-progress/breadth-reading-aid-20261101.md；小验收docs/ops/breadth-reading-aid-20261101/。其他共享模块无写入。
- 方法：保留原20/50/200值；Python纯函数只读生成历史分位轨道、5条记录变化、进入/持续/离开极端与多周期参与状态。前端仅展示，不给已确认顶底/胜率/交易指令。复用1260/252历史分位口径；固定线和动态轨道语义分清，空值/滞后显式。
- 验收：合成边界/无未来变化/缺值/准确5条差/旧history不变测试；同屏上下图、周期/轨道切换、历史悬停状态、A/美切换、390px与桌面真实页面；TS/build、归置、diff与读回。新行情实验0、下载0、付费0；本机可用约17GiB，小代码/报告预算<5MiB，不动外盘/仓外文件。
- 下一步：登记读回后按唯一写者分工实现，完成上述验收，实际问题留痕后更新本记录。本次无后台任务或交易授权。
