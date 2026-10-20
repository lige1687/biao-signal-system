# 标的讨论使用体验第一期——U1—U4 返修交付报告

- 日期：2026-09-13（主控复核同日返修交付）
- 主控复核单：`/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/agent-user-experience-controller-review-2026-09-13/`（结论：部分通过、暂不合入，返修范围固定 U1—U4 + 补齐验证）
- 上轮交付：`agent-user-experience-phase1-2026-09-13.md`（保留，不覆盖）
- 开发副本：`/Users/yongbiaoli/lei-agent-ux-20260913`；运行目录仍未做任何改动
- 状态：**待主控复核（第二轮）**。不声称策略收益改善；真实模型质量仍未测。

## 一句话结论（大白话）

主控挑出的四类交互问题都修了并验证：现在**直接说"帮我补测一下"也会打开中文选择面板**，不再要求手敲"模块A"；**改选打法时，不属于它的退出方式会被立刻清掉**，提交的就是页面上看到的组合；**切到新会话后，旧问题的迟到任务消息不会再插进新对话**（任务本身还在原问题下可查）；退出方式的中文解释改成了**和引擎实际规则一致**的说法，"查看依据详情"按钮现在**真的会展开依据明细**。主控点名的补测验证也补完了：三种任务结果（完成/没有触发过买卖/失败）都真实产生并界面可见，计划草稿在历史里能按当时的身份和日期恢复，窄屏 390px 下完整走通了回答、展开依据和面板操作。全部证据基于合成数据 + 本地假模型。

## 1. U1：直接提问与按钮操作同一条流程

**修了什么**
- 两入口 `handleBacktest` 重写：仍按原链路先用 `agentChat` 把原问题建档，然后在**原回答上打开中文面板**（绑定 reply.session_id + question_id + resolved_symbol）；"请说明要补测的模块：A/B/C/D…"文字追问从两入口删除。原话已选的方法（`parseBacktestModule`）只作面板预选，未选不代选。
- 面板提交统一走共享函数 `requestBacktestTask`（创建 + 稳定请求身份 `stableClientId` + 登记一处实现，`taskCreatedTextCn` 一份文案），两入口不再各维护一份。
- 控制台与工作台同构：面板挂在回答上（turn.setupPanel）、世代计数统一命名 `generationRef`。
- ATR 拦截草稿重写（`atrDiscussionDraft`）：措辞避开后端 `parse_request` 的触发词（补测｜回测｜测一下｜复跑｜重新测｜再测｜跑一次回测，见 `src/lei_signal/copilot/resolve.py::_BACKTEST_RE`），并在拦截回合挂"继续讨论（不做数值比较）"动作（NextStepsBar 支持带草稿的本地动作），点击放回输入框可改后发送。

**验证（修前→修后）**
- 主控原探针 `controller-probes-original.cjs` 复跑：因结构新增共享函数/同步锁标识无法绑定（`ReferenceError: setupBusyRef is not defined`），原样保留在 `raw/…rework…/controller-probes-original-run.json`（任务书 §9 允许）。
- 等价探针 `rework-probes.mjs`（同一 AST 提取判定方式，env 补透明 mock）**7/7 PASS**：两入口直接提问打开面板且无模块码追问；两入口迟到响应不插入新会话；U2 三场景（无效预选不可提交/加载中无静态替身/结构不符不可提交）。结果存 `rework-probes-run.json`。
- 浏览器（工作台 + 控制台）：直接输入"510300 帮我补测一下"→ 面板直接打开（截图 `u1-atr-continue-discussion.png` 佐证同会话流程）；选择后提交，服务端恰一个新任务且参数与面板一致。
- ATR 闭环浏览器实测：拦截 → 点"继续讨论" → 发送草稿（用户消息历史可见安全措辞）→ 得到讨论回复，补测任务数不变（零任务）。

## 2. U2：面板显示、当前选择与实际提交一致

**修了什么**
- 切打法后用 `resolveExitAfterModuleChange` 校验：当前退出不在新打法的合法清单（`validExitsFor`，b3_dual 仅 B）即清空并回落到该打法下合法默认；提交前再核对，绝不发送隐藏旧选项。
- 能力清单**加载中/失败/为空/结构不符一律不可提交**：加载中显示"正在读取…"；失败显示"选项读取失败，暂不能提交 + 重新读取"按钮；删除了加载期的静态 A/B/C/D 与退出替身（词典只给已加载结果命名）。预选的原话方法不在能力清单时如实提示要求重选。
- 窗口如实显示（`windowLabelFromComparisonConfig`）：读原问题冻结的 `evidence_card.history_and_scope.comparison_config.window`，有则显示"沿用原问题窗口 start ~ end"；`window_state=unverified` 或无窗口则显示"原问题没有可核实的窗口选择（…）"，不再一律写"未指定"。两入口 `openSetupPanel` 均已接通。

**验证**
- 浏览器（真实组件+真后端）：选 B → b3_dual → 切回 A：B 专用选项消失、摘要立即回落"跌破 20 日均线或 20 个交易日前价格（抵扣价）时退出（退出1）（默认）"，提交后服务端核验新任务参数为 `A + a6_1_costbasis`（非隐藏的 b3_dual）。窗口显示"原问题没有可核实的窗口选择"（本合成问题确实无冻结窗口）。
- SSR（等价探针）：主控原 U2 场景（能力仅 B/b3_dual、预选 A）提交按钮 disabled；加载中无静态替身且 disabled；结构不符 disabled。
- 纯函数回归：`run-agent-ux-regression.mjs` 覆盖 validExitsFor/resolveExitAfterModuleChange/windowLabelFromComparisonConfig 全部分支。

## 3. U3：旧任务迟到消息不写入新会话

**修了什么**
- 两入口 `submitSetup`：请求发出前冻结 {sessionId, questionId, symbol, generation}；响应、错误、结束处理都先核对世代——不匹配则不向当前视图追加任何消息（面板照常关闭）。任务已由服务端创建并登记（trackTask + 服务端列表），回到原会话时恢复。
- 工作台 `loadSession` 增加按会话的 `recoverActiveTasks(…, sessionId)`：回到原会话时任务卡重新接线。
- 连续点击防重：同步忙锁 `setupBusyRef`（ref，不依赖渲染）+ 共享函数内的稳定 client_request_id（服务端对同 (session_id, client_request_id) 幂等返回原任务）。

**验证**
- 等价探针 U3-late-workspace/console PASS（提交 → 世代变更 → 响应到达 → 新会话零旧任务消息、登记仍发生）。
- 浏览器真实迟到：提交瞬间 `kill -STOP` 预览后端 → 点"开新会话" → `kill -CONT` 放行响应 → 新会话 turns 为空、无"已创建补测任务"；服务端任务 #3 确实创建并完成（`btr_1512d3c801…completed`）。截图 `u3-late-response-clean.png`。
- 正文与资料区同答双渲染：面板状态在 turn 上，两处渲染同一份数据，提交走同一 `submitSetup` + 忙锁，连续点击只产生一次创建请求（服务端任务计数核验）。

## 4. U4：中文解释保持原含义；详情按钮真展开

**修了什么（对照引擎 `engine.py::EXIT_VARIANT_CN` 逐条改写）**
- 退出1：`跌破 20 日均线或 20 个交易日前价格（抵扣价）时退出（退出1）`（原"按 20 日线和成本区退出"易误读为筹码成本）；解释只列两条线，无相对结果承诺。
- 退出2：`先出现顶部构造，再按关键性波动条件退出（退出2）`；解释明确"顶部构造成立是前提"，删除"落袋更早"这类相对收益暗示。
- 退出3：`只按初始结构止损退出（退出3）`。
- B 专用：`B 专用双条件退出（跌回密集区上沿＋20日线组下弯）（退出B）`；解释明确"两条件同时满足才离场；均线排列被破坏是另一个独立的底线条件"（不再写"或"）。
- `SUPPORTED_EXITS_CN` 同步改写；`noteCn` 保持 exact/unknown 不直达用户。
- "查看依据详情"真展开：`EvidenceCardView` 新增 `forceDetailsOpen`；工作台动作展开本回答正文 + 本回答证据卡全部折叠区；控制台抽出 `ConsoleTurnView`（本地展开状态）同行为，并定位到该回答。
- 支持本问题的运行恢复附带说明：`window_note_cn` / `differences_cn` 放回每条支持运行的可展开"查看依据详情（该次运行的附带说明）"（明细后置而非删除，只呈现已有字段）。

**验证**
- 组件 SSR 回归 `run-evidence-card-regression.mjs`：支持卡（含合成附带说明 + R 值）与不匹配卡中文显示正确；默认收起、`forceDetailsOpen` 时 details 带 open。
- 浏览器：点动作条"查看依据详情"→ 折叠区实际展开（展开数 ≥1），零交易运行显示"这段历史里没有触发过买卖"，附带说明可读。截图 `u4-scene7-details-expanded.png`。

## 5. 上轮未测项补完（原任务书场景 6/7/8 与窄屏）

| 项 | 结果 | 证据 |
|---|---|---|
| 场景6（切标的不串） | **通过** | U3 的 SIGSTOP 迟到响应测试即其严格形态（提交→切会话→返回）；另有草稿带标的的探针断言。连续点击：忙锁+幂等键，服务端任务计数核验仅一次创建 |
| 场景7（完成/无交易/失败） | **通过** | 完成：`btr_90fb…completed` 任务卡+运行编号；无交易：`rr_min=30` 任务完成且运行 summary `zero_trades=true`，界面显示"没有触发过买卖"（合成造数已标注：测试说明列于 §6）；失败：`D + data_cutoff=2015-01-01` → `failed`，错误"数据截止早于全部行情：无可用输入（不伪造 K 线）"——系统诚实失败，非人为断言 |
| 场景8（计划链+历史身份） | **通过** | 第二合成标的 `516220.SS`（仓库既有测试夹具，真实管线对其产出 2 个买点候选与 suggested_plan）："帮我把当前的买点整理成计划"→ 服务端计划卡（"计划草稿 · 516220.SS（保存后仍需确认）· 原问题 #43"）；刷新后从历史恢复，计划身份与当时日期保留、出现当时/现在区分文案；全程无成交写入。截图 `scene8-plan-draft.png`、`scene8-history-restore.png` |
| 双合成标的 | **通过** | 510300（无候选）与 516220.SS（有候选）均走通（预览服务器按标的取各自夹具 parquet，真实管线计算） |
| 窄屏 390×844 完整流程 | **通过（4/4）** | Playwright（本机已有 Chrome 通道）真浏览器：实际回答、点"查看依据详情"展开依据、打开中文面板并选择打法后可提交、无横向溢出（≤2px）。截图 `narrow-390-answer-expanded.png`、`narrow-390-panel.png`；脚本与判定 `narrow_flow.py`。窄屏资料区自动展开盖住动作条为既有设计（先收资料区再操作），未做视觉重设计 |

首屏仍为一段较长文字：本轮按主控要求未设硬性字数、未重做页面；四要素以段落区分（`AnswerText` 首段拆分）。

## 6. 数据与模型性质（如实）

- 全部行情为仓库测试夹具 parquet（合成/夹具数据）；全部模型回答为本地假模型桩固定文本（510300 事实版 / 516220 通用版两套，均已标注）；**真实模型质量仍未测**。
- 场景7 的"无交易"通过 `rr_min=30`（盈亏比门槛提到 30）经公开 API 造出，属真实引擎在合成数据上的诚实结果；"失败"由 `data_cutoff` 早于数据起点触发，同为真实失败路径。两者在报告中标注为"测试造数"，不冒充自然发生。
- 预览栈零外部请求（预热已在脚手架禁用）；端口 8014/8015/5174，不占 8000/5173。

## 7. 验证命令与结果汇总

- 等价探针：`node rework-probes.mjs` → 7/7 PASS + source-integrity PASS（`rework-probes-run.json`）；主控原探针复跑失败态已存档（`controller-probes-original-run.json`，原因：新增共享函数标识不在原 env——任务书 §9 预案）。
- 后端：`pytest tests/unit/test_agent_ux_phase1.py test_agent_chat.py test_agent_stream.py test_chat_discussion.py` → **22 passed**（后端本轮零改动，sanity 复跑）。
- 前端：`tsc --noEmit` 无错误；`npm run build` 成功；`test:agent-workspace / test:agent-prices / test:agent-ux / test:agent-tasks / test:evidence-card` 全部通过。
- 基线既有失败 `test_invented_number_degrades` 按主控裁定列为后续真实性事项，本轮未触碰。

## 8. 修改清单与身份

- 相对上轮交付（HEAD `78d65ee5`）的 diff：12 文件 +554/−305，集中在两入口、面板、`agentUx.ts`、`backtestTasks.ts`、证据卡；后端零改动。新增 `web/run-evidence-card-regression.mjs` 与 raw 目录（探针、截图、narrow_flow.py、identity.json）。
- 关键源码指纹（修后）：`raw/agent-user-experience-phase1-rework-2026-09-13/identity.json`。
- 未合入运行目录；未自行部署；方向 OKR `okr-8f4f1a5f026f` 未标完成（本轮成果仍为"待复核"）。

## 9. 登记与边界

- 本仓 registry 新增本报告条目（数据与质量 / watch）；INDEX §1 加导航行；原上轮条目保留原状。合入运行目录时增量登记。
- 边界不变：判定权在 Python 规则层；本轮未改规则、计划确认、窗口算法、证据匹配、数值接地；因子接入与真实性审计不在本轮。

---

## ARCHIVE

- 归档：2026-09-13；执行者第二轮交付，待主控按 U1—U4 固定清单复核。
- 证据目录：`raw/agent-user-experience-phase1-rework-2026-09-13/`（等价探针与运行结果、原探针复跑存档、浏览器截图、窄屏脚本与截图、identity.json）。
- 保留失败史：主控原探针在返修后结构下无法直接绑定（已在 §7 说明并以等价探针覆盖）；IAB/截图自动化通道在本环境间歇故障（改用 Playwright+Chrome 通道完成窄屏验证）。
