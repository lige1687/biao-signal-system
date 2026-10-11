# 获取信息界面做减法：日常闭环与因子位置

更新时间 2026-10-12T00:15:27.999665+08:00。用户明确授权“你先修完闭环 给我看看效果”及“看看因子的位置”。本轮服务策略的展示、理解、计划核对与复盘层；Python信号/策略文档/真实交易记录不改。

- 验收：三个常用入口；重点摘要可到同一基金、图表、Agent草稿、原确认流程和复盘；因子参考有日期与缺失提示，研究档案可达；桌面及窄屏实际点击、构建、相关回归及归置。效果待用户验收。
- 基线：共享目录HEAD 18e64fa，当前web有历史未提交改动；先建立仅本地隔离快照与SHA清单，保留共享目录全部字节。未推送的新成果不宣称远端可复现。
- 重叠决定：investor-observation-map只维护市场理解/基本面入口小块，本轮保留其页面及所有旧路由；daily-trading-system-audit维护后端接入，本轮不改。因子研究原负责人/冻结结论及旧预算不变。root独写导航/今日页与协调；Sol分写持仓呈现与因子组件，具体子范围互斥。研究原任务保持用户优先级暂停。
- 当前检查：协调读取成功；实时API只读29持仓、28净值、0关联计划、0技术资料；固定外盘身份通过，内盘14.4GB，仅新增小代码和截图，复用已有依赖。尚未跑本批代码验证。
- 最新已推成果：无。本轮仅开工；不部署、不交易、不跑市场实验、不安装大依赖、不删除数据；0新研究计算。
- 系统原条目：okr-4c2ea452d3cc、okr-a4fed76c71c3、okr-266b531f965d已只读定位，复用相应原条目，最终由root追加准确进展；不改原负责人/完成标准。
- 下一步：隔离复用当前web→有界实现→实际读回操作路径→留本机预览与准确成果/验收记录。

<!-- lei-coordination-json:start -->
{
  "task_id": "investor-workspace-simplification-20261012",
  "owner": "01a123fc-553b-7b81-9952-36e1acb11dcc",
  "status": "active",
  "checked_coordination_sha": "4f13b4b38b9482a780ba9e68c22172b4f859d765",
  "checked_at": "2026-10-12T00:15:27.999665+08:00",
  "read_task_ids": [
    "daily-trading-system-audit",
    "investor-observation-map",
    "market-observation",
    "technical-factor-sequence",
    "classic-factor-research",
    "original-eight-continuation-20261010",
    "research-dispatch-controller"
  ],
  "work_branch": "codex/investor-workspace-simplification-20261012",
  "base_commit": "18e64fa632dba5dbad0e5fcae09b4ccc75f119a9",
  "write_paths": [
    "web/src/App.tsx",
    "web/src/components/TopNav.tsx",
    "web/src/components/TodaySignalBanner.tsx",
    "web/src/components/portfolio/PortfolioToday.tsx",
    "web/src/pages/PortfolioPage.tsx",
    "web/src/components/factors/",
    "web/src/pages/TodayPage.tsx",
    "web/src/pages/today.css",
    "web/src/components/portfolio/portfolioWorkspace.css",
    "web/run-investor-workspace-regression.mjs",
    "docs/ops/work-progress/investor-workspace-simplification-20261012.md",
    "docs/archive/handoffs-plans/investor-workspace-simplification-20261012/"
  ],
  "scope_released": false
}
<!-- lei-coordination-json:end -->
