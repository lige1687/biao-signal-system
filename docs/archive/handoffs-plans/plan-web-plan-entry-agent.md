# Web 建计划入口 + 监督待办页 + Agent Chat 抽屉

## 目标与已定决策

- **建计划入口**:WorkspacePage(默认落地页)与 DetailPage(独立详情页)的标的 header 右上角都加「建立执行计划」按钮,弹 Modal 表单,从当前 assessment 机会数据**预填**入场字段,人只填五项预案。
- **标的提醒**:新增极简全局顶栏 + `/plans` 监督待办页,跨标的汇总计划/待办/alert,页内「已执行/推迟」走既有 plans 状态机。
- **Agent**:阶段一确定性视图(监督待办页渲染 alert/nag/五项预案)+ 阶段二右侧 chat 抽屉,走后端接地 LLM 端点(复用 `render_alerts`/`verify_grounding`/`make_ark_renderer`)。**非流式 v1**(`call_ark` 同步)。

## 红线(全程遵守)

1. 判定权在 Python:chat 端点 LLM 输出必须过 `verify_grounding`(禁用词 + rule_id 白名单),失败降级 `render_alerts` 模板。
2. 建计划表单只**预填** DTO 已有数值,不许算新数(entry_price_ref/invalidation_price 缺则留空让人填)。
3. 无券商/无金额/无账户:done/defer 复用既有 `/api/plans/.../done`、`/defer`,与飞书回执同源。
4. 对话式 skill 保留,Web chat 是并行入口,不替换。

---

## 后端改动

### B1. Agent chat 端点 `POST /api/plans/{plan_id}/chat`
- 新文件 `src/lei_signal/api/routes/agent.py`(挂到 app),或加进 `routes/plans.py`。建议独立 `agent.py`。
- 请求体 `{"message": str}`(message 可空:空=渲染当前 alert 摘要)。
- 逻辑:
  1. `get_plan` + `analysis_service.get(plan.symbol)` + `context_from_result`。
  2. `alerts = evaluate_plan(plan, ctx)`;`actions = list_action_items(conn, plan_id)`。
  3. 有 ark 凭据:`llm.py` 新增 `chat_ark(context_payload, user_message, config)` -> 调 ark(system prompt 复用 SYSTEM_PROMPT 接地规则 + context + 用户问题)-> `verify_grounding(reply, rule_ids)` -> 过则返回。
  4. 无凭据 / 校验失败:降级 `render_alerts(alerts, llm_render=None)`(模板)。
- 返回 `{"reply": str, "grounded": bool, "alerts": [PlanAlertDTO], "plan_id": str}`。
- 新 schema `PlanChatRequest{message:str}`、`PlanChatReply{reply,grounded,alerts,plan_id}` 在 `schemas.py`。
- `llm.py` 新增 `chat_ark(payload, message, config) -> str | None`(参考 `call_ark` 的双协议 anthropic/openai 分支,把 user message 拼进 messages)。

### B2. 待办计数端点 `GET /api/plans/summary`
- 返回 `{"open_actions": int, "active_plans": int}` 供顶栏红点。
- `store.py` 新增 `count_open_action_items(conn) -> int`(SQL `SELECT COUNT(*) FROM plan_action_items WHERE state='open'`)。
- 路由加进 `routes/plans.py`。

### B3. 测试
- `tests/unit/test_agent_chat.py`:有/无 ark 凭据两条路径;LLM 输出含禁用词->降级模板;rule_id 超集->降级;空 message 返回 alert 摘要。
- `test_plans_store.py`:`count_open_action_items`。
- mock ark(参考 `test_plans_llm.py` 的 mock 范式),不打真实 API。

---

## 前端改动(web/)

### F1. `src/types.ts` — 新增类型
`Plan`、`ActionItem`、`PlanAlert`、`CreatePlanPayload`、`PlanChatReply`、`PlansSummary`(对齐后端 DTO)。

### F2. `src/api/client.ts` — 新增方法
`createPlan`、`confirmPlan`、`listPlans(symbol?,state?)`、`getPlan`、`planAlerts`、`planActions`、`doneAction`、`deferAction`、`planChat`、`plansSummary`。

### F3. `src/components/TopNav.tsx`(新)+ Layout
- 极简顶栏:`看盘(/)` `卡片墙(/grid)` `监督待办(/plans)` + 红点(open_actions)。
- `App.tsx` 用顶栏包裹 `<Routes>`,新增 `/plans` 路由。
- 红点 react-query 轮询 `plansSummary`(refetchInterval 60s)。

### F4. `src/components/CreatePlanDialog.tsx`(新)
- 复用 `modal-overlay`/`modal-card`(参考 `AddSymbolDialog`、`MarketBreadthModal`)。
- Props:`{ symbol, prefill, onClose }`。prefill 来自当前 assessment 的活跃机会。
- 字段:module(select A/B/C/D)、direction、entry_rule_id、lifecycle_id、entry_price_ref、invalidation_price、target_b_price、valid_until、reason + 五项预案 textarea(thesis/invalidation_criteria/drawdown/take_profit/stop)。
- 预填映射(只取 DTO 已有值,缺则空):
  - direction/lifecycle_id/b1_price <- `trade_opportunities[0]` 或 conditional scenario;
  - entry_rule_id <- opportunity.supporting_event.rule_id 或 scenario.scenario_id;
  - entry_price_ref/invalidation_price <- 结构价(有则填,无则空让人填)。
- 提交:`createPlan(payload)` -> `confirmPlan(plan_id)` -> invalidate `["plans"]` -> 关闭。
- 五项预案留空 -> 禁用提交(对齐 skill「想清楚再下单」)。

### F5. 两页 header 加按钮
- `DetailPage.tsx`:`flex:1` spacer 后、刷新按钮前,加「建立执行计划」按钮 -> 开 `CreatePlanDialog`(prefill = `data.assessment`)。
- `WorkspacePage.tsx`:同位置(line 266 `flex:1` 后)加同款按钮 -> prefill = 当前选中标的的 assessment。
- 抽一个共用 `useCreatePlan` 触发器或直接两处各自管理 dialog state(简单起见各自 state)。

### F6. `src/pages/SupervisorPage.tsx`(新,路由 `/plans`)
- `listPlans(state=armed|entered)` -> 按标的分组渲染计划卡:五项预案摘要 + entered_on/exited_on + valid_until。
- 每计划:`planAlerts` + `planActions`。待办行带「已执行 / 推迟」:
  - 已执行 -> `doneAction`。
  - 推迟 -> 展开内联表单(reason + resume_on JSON)-> `deferAction`(422 回显校验错误)。
- 每计划卡有「问 agent」按钮 -> 开 `AgentDrawer`。
- 空态:无计划时引导去标的页建计划。

### F7. `src/components/AgentDrawer.tsx`(新)
- 右侧抽屉(modal-overlay 变体,从右滑入)。Props:`{ planId, onClose }`。
- 打开即 `planChat(planId, "")` 拿当前 alert 接地摘要。
- 底部输入框 -> `planChat(planId, message)` -> 追加对话(非流式,loading 态)。
- 显示 `grounded` 标记(接地/模板降级)。

### F8. `App.tsx`
- 包裹 TopNav;加 `<Route path="/plans" element={<SupervisorPage />} />`。

---

## 交付顺序(增量可验)

1. **后端**:B2 summary + B1 chat 端点 + llm.chat_ark + 测试。门禁:pytest/ruff/mypy。
2. **前端地基**:F1 types + F2 api client。
3. **建计划入口**:F4 CreatePlanDialog + F5 两页按钮。手验:两页能建 draft->confirm,出现在 /plans。
4. **监督待办**:F3 TopNav + F6 SupervisorPage。手验:看计划/待办,页内 done/defer 写回状态机。
5. **Agent 抽屉**:F7 AgentDrawer。手验:接地摘要 + 提问,禁用词降级生效。

## 验收门禁

- 后端:`pytest -q` 全绿、`ruff check src`、`mypy src`。
- 前端:`cd web && npm run build`(tsc 通过)。
- 手验:DetailPage+WorkspacePage 各建一个计划 -> /plans 看到 -> 页内推迟一个(done 走飞书或页内均可)-> AgentDrawer 提问接地。
- 红线:chat 输出含「买入」必降级模板;建计划不预填不出的价格字段。

## 不做(本期)

- chat 流式传输(非流式 v1,后续可加 SSE)。
- Web 端建计划引导式对话(表单已结构化覆盖五项预案,足够)。
- 飞书回执页改为页内(并行保留,不替换)。
- 计划修订(drift)的 Web UI(继续走 skill `plan_cli revise`)。
