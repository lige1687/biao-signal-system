# 计划补齐、确认与历史恢复——交付报告

- 日期：2026-09-13。任务书：`/Users/yongbiaoli/Desktop/lei-signal-lab/docs/prompts/agent-plan-review-and-confirmation-2026-09-13.md`（用户转交即授权）；主控架构裁决：`agent-user-experience-controller-closeout-2026-09-13.md`。
- 开发副本：`/Users/yongbiaoli/lei-agent-ux-20260913`，分支 `plan-review-flow-20260913`，**提交 `4640a5db`**（基于 `4d38e1a5`）。开工核对：13 个依赖文件与任务书 inputs.json 哈希**零漂移**，HEAD 一致（`raw/…/identity.json` 为修后指纹）。
- 状态：**待主控复核**。合成数据 + 本地假模型；未合入运行目录；真实模型/收益/因子边界不变。
- **2026-09-13 追加**：主控三轮复核 C1—C3 补修已交付，见 `agent-plan-review-and-confirmation-cfixes-2026-09-13.md`（持仓版本拦截/保存快照重试/错误代码区分提示，补修验证 13/13）。

## 一句话结论（大白话）

这轮把"从讨论到一张可用计划"的主干打通了：新建计划不再用一个写死的旧规则版本（改为服务端提供的当前版本，读不到就不让建、可重试）；在讨论里保存的计划草稿，现在卡片上就有「补齐并核对」按钮，打开核对抽屉改同一张计划（不会另建一张）、明确点确认才生效；刷新或重开历史时，卡片直接显示这张计划**现在的状态**（草稿/已确认生效），不用再保存一次。系统建议的入场计划也只从真正合法的买点候选里取（早期转强信号不再被冒充成完整 A 计划，转为待补）。六组验收 13/13 通过，含真实页面正例：讨论→保存→补齐→确认 200→状态 armed，恢复时库内计划数与成交数零增加。

## 1. 三组实现

**P1 规则版本服务端权威**
- 后端新增只读端点 `GET /plans/ruleset-version`（plans.py，返回 `domain.rules_config.ruleset_version()`）。
- `CreatePlanDialog`：删除写死 `RULESET = "1.3.0"`；技术入场与持仓监督两条创建路径都改用该端点；版本未读到时提交按钮禁用 + "正在读取/读取失败 + 重新读取"提示，submit() 再兜底拦截（不以空版本提交）。
- `PlanDraftCard` 保存同样改用该端点（原来走 buyPointReview 且失败时退空版本）；保存稳定编号（stableClientId）输入**不含版本**——同一请求不因版本变化变成新业务。确认时仍由服务端现行版本核验（409 语义不变）。

**P2 会话草稿补齐/确认与历史恢复**
- `PlanDraftCard` 新增 `savedPlanId` prop（历史接口 `plan_draft` 绑定）：有绑定时直接 `GET /plans/{plan_id}` 读取**实际状态**，卡片分行显示"当时讨论字段（服务端产物原文）"与"这张计划当前状态：草稿/已确认生效（以服务端为准）"；不再以再次 POST 保存作为恢复。
- 保存后/恢复的草稿出现「补齐并核对」按钮 → 打开既有 `ReviewDrawer`（同一 plan_id：核对报告、编辑计划、明确确认）；确认成功后卡片状态经 `["plan", planId]` 缓存失效自动刷新。
- 确认失败提示改为"可点「补齐并核对」修改本草稿后重试（不需要新建计划）"（ReviewDrawer 同步），替换原来指向找不到草稿页面的提示。
- 工作台 `loadSession` 消费 `m.plan_draft` 并传入卡片；控制台不加载历史（实时会话内保存后同样出现补齐入口）。迟到响应防串扰沿用世代/会话清空语义（验收 G5.2）。

**P3 预填只用合法候选**
- `opportunities.py` 新增纯函数 `_legal_entry_candidate(confirmed)`：按原顺序取第一个"入场规则可映射 A/B/C/D（`module_of`）且映射模块与候选自身模块一致"的候选，规则/模块/方向/生命周期/触发/失效位随同一候选；无 → `suggested_plan=None`（卡片走"待补"提示），`module or "A"` 兜底删除。不扩 `MODULE_MAP`、不改候选列表/排序/信号/收益口径。

## 2. 六组验收结果（13/13 PASS；结构化逐项 `raw/…/RESULTS.json`，日志 `verify-run.log`，VERIFY_EXIT=0）

| 组 | 结果 | 关键证据 |
|---|---|---|
| G1 版本 | PASS×2 | 端点返回 2.1.0（与 rules_config 一致）；Playwright 路由拦截读取失败 → 建立草案按钮禁用 + 提示（不空版本）。版本变化 409：pytest `test_confirm_rejects_after_version_change_and_keeps_draft`（409 后 state=draft、ruleset_version 不被重标；版本恢复后版本门通过） |
| G2 真实正例 | PASS×3 | `TH881272.SECTOR`（完整路由 ACTIONABLE 唯一夹具）：页面讨论→卡片预填 C/two_b_reversal（P3 合法）→保存 `plan_TH881272_SECTOR_20260913144700_8e733d51`→补齐并核对→编辑补失效价/有效期/五项预案→确认→**state=armed**。请求日志 72 条存 RESULTS.json |
| G3 拒绝与修正 | PASS×2+既有 | 未补失效价确认→422 后仍可编辑（G3.1）；516220 早期信号 P3 后无合法预填→卡片"暂不能保存"待补（G3.2）；分析不可用 503 由既有 `test_plan_confirm_guard.py` 覆盖（15 passed，含 ANALYSIS_UNAVAILABLE/state 不变） |
| G4 身份与历史 | PASS×3 | armed 计划刷新+历史恢复显示"已确认生效"且无保存按钮；恢复前后库内计划数=+0、fund_trades=0；同标的两问题→两个不同 plan_id、绑定各自 question_id（q31/q33） |
| G5 两入口与迟到 | PASS×2 | 控制台（/symbol/th881272）保存→补齐并核对可达；工作台保存瞬间 SIGSTOP 后端→切新会话→CONT：新会话零串扰 |
| G6 回归 | PASS | 前端 5 脚本全过、tsc 无错、build 成功；后端 `test_plan_review_flow_p1(3)+test_plan_confirm_guard(15)+test_agent_ux_phase1(9)+test_plans_conformance_routes+test_chat_discussion` = **40 passed** |

合成/真实界限：行情=仓库测试夹具（TH881272/516220 parquet 经真实分析管线）；模型=本地假模型桩（固定合成回复）；保存/拒绝/确认/恢复全部走真实 FastAPI 路由与隔离临时库 preview.db。用户真实库 `~/.lei_signal_lab/lab.db` trade_plans 事后只读核对 0 行（未受影响）。预览栈已禁用预热外联，端口 8014/8015/5174。

## 3. 修前失败记录（保留）

- 修前基线（`4d38e1a5`）上：表单新建计划确认必 409 RULESET_VERSION_CHANGED（写死 1.3.0）；会话草稿确认必 422 ENTRY_RULE_NOT_ENTRY_MODULE 且无核对入口；516220 早期信号被 `module or "A"` 冒充为 A 预填。主控 closeout 报告已记录，本轮逐项对应修复或转待补。
- 验收脚本迭代中的断言问题（旧按钮文案、全角括号正则、历史面板竞态）已在脚本内修正；最终 run 全绿，中间 run 日志不另留档（断言错误非产品缺陷）。

## 4. 边界与未做

- 未改：回测引擎、信号规则、`MODULE_MAP`、风险阈值、确认拒绝纪律、计划/成交数量金额边界、冻结 Streamlit；未做旧计划批量迁移（版本不符按既有 409 提示重建，原计划保留）；未接因子；未测真实模型；未部署/合入。
- 收益口径、候选总体排序、技术信号判定不变；P3 只影响 `suggested_plan` 预填来源。

## 5. OKR 与登记

- 台账 `okr-b1ce64d26449`：已按授权登记本任务（PATCH evidence/next_action，**v2→v3**，status 保持 planned，完成标准未改）；04B 既有目标旧标准未动。
- 本仓 registry 新增本报告条目（数据与质量 / watch）；INDEX §1 追加导航；不改前轮报告与裁决。

## 6. 实际模型与工具

- 当前执行模型（GLM-5.3-Flash 会话）独立完成；未另开子任务，无冒称调用。验证工具：Playwright + 本机 Chrome（既有依赖）、pytest、esbuild/node 回归、隔离预览栈。

---

## ARCHIVE

- 归档：2026-09-13；交"待主控复核"，不自行合入或标全方向完成。
- 证据目录：`raw/agent-plan-review-and-confirmation-2026-09-13/`（verify_all.py、verify-run.log、RESULTS.json 含 72 条计划请求日志、r2c/前轮脚本引用、identity.json）。
- 定向补丁：分支 `plan-review-flow-20260913` 提交 `4640a5db`（相对 `4d38e1a5`：后端 2 文件、前端 6 文件、新增 pytest 与 raw 证据）；合入按文件清单定向 apply。
- 保留失败史：主控 closeout 记录的旧阻点（409/422/无入口）及其本轮修复对应关系见 §1/§2；验收脚本中间迭代的断言修正不属产品缺陷。
