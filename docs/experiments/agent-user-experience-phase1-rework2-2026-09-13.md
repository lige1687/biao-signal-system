# 标的讨论体验第一期——R1/R2 收口交付（待主控复核）

- 日期：2026-09-13。主控二轮复核单：`agent-user-experience-controller-recheck-2026-09-13`（U1—U3 及 U4 大部已接受，剩余 R1 文案小修 + R2 计划验证）。
- 被审基础：开发副本 `/Users/yongbiaoli/lei-agent-ux-20260913` 提交 `c3cbab9c`；本轮新增提交见文末。运行目录仍未改动。
- 状态：**R1 完成；R2 按验收项部分完成并如实上报既有功能阻点**（见 §3——两处既有缺陷使"补齐后经页面确认生效"在当前代码下无法走通，按主控 §4 指示不擅自扩大开发范围）。

## 一句话结论（大白话）

退出1的说明已改成"收盘**同时**跌破20日指数均线与抵扣价"并配了主控那张四行对照表做测试（证明"同时"和"任一"两种说法在同样数据下结论不同，文案现在与引擎一致）。计划验证补齐了能补的部分：草稿保存有真实计划编号、挂在原问题上、不完整的草稿确认时被系统如实拒绝、刷新后身份和日期都在。但"补齐字段后经页面确认生效"这一步被**两个本轮之前就存在的缺陷**挡住，无法在既有界面里走通：一是详情页建计划的表单把规则集版本写死为 1.3.0（当前实际是 2.1.0），确认时被系统以"版本已变更"拒绝，编辑保存也不会更新这个版本；二是从对话里保存的计划草稿，其系统建议的入场规则编号不被模块规则认账，且没有任何界面入口能打开这份草稿的核对/编辑抽屉。按主控"如实提交、不擅自扩大开发范围"的指示，这两处原样上报待定夺，未动生产、未改数据库充数。

## 1. R1：退出1 文案（完成）

- `EXIT_CN_SIMPLE.a6_1_costbasis` → 「收盘同时跌破20日指数均线与抵扣价时退出（退出1）」；`EXIT_HINT_CN_SIMPLE` → 主控定稿原文（含"下一交易日开盘退出；初始结构止损仍独立生效"）；`SUPPORTED_EXITS_CN` 同步。
- 两入口与依据卡同一来源：名称/解释经 `exitCn`/词典，ATR 拦截文案经 `SUPPORTED_EXITS_CN`，均为单一定义（grep 全仓仅 agentUx.ts 一处定义）。
- **独立对照**（`run-agent-ux-regression.mjs`）：主控四行表入测——先断言 `(close<ema20)&(close<lag20)` 与"任一"语义在第 2/3 行结论不同（[false,false,false,true] vs [false,true,true,true]），再断言文案含"同时跌破/同时低于"、不含"或/任一"；`run-agent-tasks-regression.mjs` 期望值同步。引擎 `engine.py::prepare_frame` 一字未动。

## 2. R2 已完成部分：保存、拒绝边界、历史恢复

预览隔离环境（合成 516220 + 假模型 + 临时库 preview.db；用户真实库 `~/.lei_signal_lab/lab.db` 事前事后只读核对均 0 行计划，未受任何影响）：

| 验收项 | 结果 | 证据 |
|---|---|---|
| 页面保存草稿，记录真实 plan_id 与原问题绑定 | ✅ | `POST /api/plans` → 201；`plan_516220_SS_20260913114346_518bdfa6`（state=draft）；`agent_plan_draft_bindings` 行：question_id=52、session、冻结产物 spa_52；**非 question_id 充数**。第二次流程 question_id=54 同样成立 |
| 不完整草稿不能生效 | ✅ | 点确认 → `POST …/confirm` → **422 CONFORMANCE_HARD_BLOCK**，硬阻断 `ENTRY_RULE_NOT_ENTRY_MODULE`（`ema20_reclaim_rising` 未映射 A/B/C/D）；页面如实显示"草稿已保存但未激活……存在硬阻断项，无法确认"；库内 state 保持 draft |
| 刷新/历史恢复核对 | ✅ | 恢复后卡片仍是"计划草稿 · 516220.SS（保存后仍需确认）· 原问题 #54 · 服务端产物"；全程零成交写入 |
| 请求/响应与只读库核对 | ✅ | `r2_plan_flow.py` 网络日志（201/422 原文）、`R2-EVIDENCE.json`（临时库只读快照，含全部 plan 行） |

## 3. R2 阻点（既有缺陷，如实上报，未扩大开发范围）

"用既有编辑/补齐方式完成必要字段，再通过页面确认一次"在当前代码下无法走通，两条既有路径各被一个**本轮之前就存在**的缺陷挡住：

1. **会话保存的草稿**（ruleset 2.1.0，正确）：确认 422 硬阻断——系统建议的 `entry_rule_id=ema20_reclaim_rising` 不在 A/B/C/D 模块映射表（`research/module_backtest.py::MODULE_MAP`）。即使该字段可改，**也没有任何既有 UI 入口**能打开会话草稿的核对/编辑抽屉（ReviewDrawer 仅在详情页"新建计划"流程内部可达；监督待办页不列 draft）。
2. **详情页既有表单**（`CreatePlanDialog`）：`ruleset_version` 硬编码 `"1.3.0"`（CreatePlanDialog.tsx:41），当前激活规则集为 2.1.0（`rules_config.ruleset_version()` 实测返回 2.1.0）。字段全部填齐（entry_rule_id=first_ma_pullback、五项预案、有效期、失效价 0.521）后经页面确认 → **409 RULESET_VERSION_CHANGED**"计划基于规则集 1.3.0，当前为 2.1.0；请复核后重建草稿"。核对抽屉本身工作正常（列出软建议、可发起确认请求），且编辑态保存不含版本字段，无法自愈——即当前前端创建/补齐的任何计划都无法确认生效。

含义：这不是体验层文案问题，而是"计划保存→确认生效"链路的既有功能缺陷，影响真实用户路径。按主控 §4"先如实提交，不擅自扩大开发范围"，本轮不改创建/确认代码。候选修法（供主控定夺，未实施）：前端 `RULESET` 改为动态读取当前版本；`ema20_reclaim_rising` 的模块归属或 suggested_plan 的 entry_rule_id 供给口径核对；会话草稿增加核对抽屉入口。

## 4. 验证与回归

- `npm run test:agent-ux`（含四行对照）→ PASS；`test:agent-tasks`、`test:evidence-card`、`test:agent-workspace`、`test:agent-prices` 全部 PASS；`tsc --noEmit`、`npm run build` 通过（受 R1 影响面即此，未重跑无关旧审计）。
- 后端零改动，未重跑（U1—U3 已被主控接受）。
- 浏览器/脚本证据：`raw/agent-user-experience-phase1-r2-plan/`（r2_plan_flow.py、r2c_complete_plan_confirm.py、R2-EVIDENCE.json、r2-after-confirm.png、r2-history-restore.png、r2c-run.log、preview-snapshot.db 只读快照）；R1 证据在 `raw/agent-user-experience-phase1-rework-2026-09-13/` 基础上由更新后的回归脚本覆盖。

## 5. 数据与模型性质

- 行情=仓库测试夹具（516220/510300 parquet，真实管线计算）；模型=本地假模型桩；确认/拒绝/保存全部走真实后端与临时库。用户真实台账零写入（只读核对两次）。

## 6. 身份与登记

- 本轮提交：见 git log（R1+R2 一个提交）；关键文件指纹：`raw/agent-user-experience-phase1-r2-plan/identity.json`（agentUx.ts / 两个回归脚本 / PlanDraftCard 未改动说明）。
- registry 新增本报告条目（数据与质量 / watch）；INDEX §1 追加导航；前两轮报告与失败记录原样保留。
- 真实模型质量、数值容差缺陷、因子采用、部署：均保持主控裁定的后续事项，本报告不授权。

---

## ARCHIVE

- 分类：数据与质量；verdict：watch（R1 完成、R2 部分完成+既有缺陷上报，待主控定夺阻点处理）。
- 保留失败史：422/409 原文、无 UI 入口结论、四行对照表。数据库状态未以任何方式伪造；所有确认尝试均为真实请求。
