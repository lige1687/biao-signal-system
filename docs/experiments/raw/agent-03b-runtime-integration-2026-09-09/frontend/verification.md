# 03B 前端定向合入证据

- 日期：2026-09-09
- 工作树：`/Users/yongbiaoli/lei-signal-integration-20260909`
- 共同基线：`6edce25`
- 实际 lab HEAD：`91c720e`
- 研究规范：`docs/research/experiment-backtest-principles.md` v1.0

## 范围

本轮只合入 03B 的讨论、补测和计划链前端能力。它服务于交易系统的展示与操作层：展示后端给出的阶段、依据、补测状态和计划字段，不在前端重新计算道路、路牌、A/B/C/D 触发、失效位或过滤条件，也不改规则阈值。

保留了 lab 已有工作台布局、流式回答、价格链接、`ResultContext`、资料区和升级库路由。没有合入 factor、portfolio、dca、mindset、research、observations 页面或接口，也没有改依赖。

## 改动

- `web/src/components/AgentConsole.tsx`：统一解析分流、补测任务恢复与状态卡、依据卡、服务端计划产物。
- `web/src/pages/AgentWorkspacePage.tsx`：在 lab 新工作台设计内嵌入同一套 03B 能力，保留价格定位和资料区。
- `web/src/components/EvidenceCardView.tsx`：只展示服务端结构化依据，不在前端计算结论。
- `web/src/components/PlanDraftCard.tsx`：服务端计划产物优先，旧文本格式只作兼容；保存草稿与确认生效分开。
- `web/src/utils/resolveRoute.ts`：统一使用服务端解析结果决定讨论、已有功能或补测。
- `web/src/utils/backtestTasks.ts`：补测五种状态、恢复和轮询共用逻辑。
- `web/src/api/client.ts`、`web/src/types.ts`：补齐 03B 请求、响应和结构化产物字段。

## 验证

- `npx tsc --noEmit`：通过。
- `npm run build`：通过；Vite 转换 736 个模块并产出生产包。仅有原有的大包体积提示。
- `npm run test:agent-workspace`：通过；覆盖流式事件、读取器清理、滚动和精确文本预览。
- `npm run test:agent-prices`：通过；覆盖价格来源匹配、歧义、精度、价位角色和图表可视范围。
- `git diff --check -- web/...`：通过。

## 边界与依赖

前端依赖后端提供 `/copilot/resolve`、`/copilot/backtest-requests`、`/agent/chat` 与流式回答中的 `question_id`、`evidence_card`、`plan_artifact` 字段。补测任务实际运行需要后端工作进程；本轮未启动收费模型、未写真实数据库、未执行补测。
