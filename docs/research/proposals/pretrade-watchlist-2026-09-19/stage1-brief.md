# Stage 1 执行简报：WorkspacePage 首屏「买前关注区块」（只读聚合，无新判定）

## 工作区

唯一可写工作区：`/Users/yongbiaoli/Desktop/lei-signal-lab/scripts/agents/watchlist-stage1-20260919`
（git worktree，基线 HEAD 91a93ad2， detached）。主仓 R 其余部分一律只读；
`web/node_modules` 为指向 R 的符号链接（只读复用，勿改勿装新依赖）。

## 任务（GPT-6 Pro 冻结计划 FROZEN-PLAN.md 前段 + 本简报约束）

在工作台首页（`web/src/pages/WorkspacePage.tsx`）增加「买前关注区块」，
把 `/opportunities/scan` 已有的 actionable/waiting/blocked 分组结果组织成
用户 5 秒能看懂的清单；每条展示并只展示以下字段（字段来源权威：
`/Users/yongbiaoli/Desktop/lei-signal-lab/docs/research/proposals/pretrade-watchlist-2026-09-19/stage1-source-mapping.md`，
逐字段照抄来源，禁止自创字段）：

- 为什么关注（best_scenario_cn + module 中文口径 A回调/B密集突破/C 2B/D假突破）
- 当前候选状态（best_state：观察中/已确认/走弱/失效，与扫描 verdict 分别展示）
- 还缺什么（missing_summary_cn；price/state 型照抄原文，无价位不编数字）
- 失效位（invalidation；无则明示「未给出」，不得推算）
- 盈亏比（算不出明说「不可计算」）
- 数据时点（as_of，区块必显）
- 已有计划入口（has_active_plan=true 时直达；false 时点击进入既有
  buy-point-review/计划预填链路——只打开既有 SuggestedPlanDTO 预填，
  保存动作仍走既有确认流程，不新建第二套计划）
- 跨日变化占位：显示「跨日变化待后段」，不接任何消息维度

无候选时直说「当前没有值得关注的候选」，不凑数。

## 硬纪律（违反任一即失败）

1. 后端若需适配，只允许 `src/lei_signal/api/routes/opportunities.py` 的
   只读聚合扩展（新 DTO 字段必须标注 source=引用来源 或 derived=纯格式化，
   禁止任何 decision 类字段）；不碰 `src/lei_signal/rules/`、`storage/`、
   `configs/`、Streamlit 目录、消息面模块。
2. 判定与排序沿用 scan 既有输出，禁止新增买卖评分、推荐分、AI 判断、
   消息驱动信号；blocked 不冒充 invalidated，confirmed 不自动等于可交易。
3. UI 文案用策略体系语言（阶段/路牌/入场方法/失效位），大白话解释为主，
   禁止发明新概念。
4. 全程不动主仓 R（含并行任务「质感精修」的未提交 web 改动），只在 worktree 内工作。
5. 不部署、不起定时任务、不写真实数据库、不联网下载依赖。

## 验证（交付前自跑并留证到 raw 目录）

- `cd web && npm run build` 通过；
- 若改了后端：`PYTHONPATH=src python -m pytest tests/unit/ -q`（用
  /Users/yongbiaoli/.workbuddy/binaries/python/envs/default/bin/python3）
  相关文件全过，且新增聚合路由有测试覆盖（来源字段断言）；
- 自测截图（桌面+窄屏）与场景自评表存 `docs/experiments/raw/watchlist-stage1-2026-09-19/`：
  逐条回答五秒为什么看/三十秒等什么与何时失效/失效位可见/占位正确/动作闭环；
- `python3 scripts/check_repo_hygiene.py` 全绿（worktree 内）。

## 交付

- 改动文件清单+逐文件说明、自测证据路径、场景自评表、未解决问题清单。
- 报告落在 worktree 内 `docs/experiments/watchlist-stage1-2026-09-19.md`
  （含「一句话结论（大白话）」小节，登记 registry/INDEX 留给主控采用时统一做）。
