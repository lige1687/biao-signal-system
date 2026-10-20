# Agent 真实问答可用性与回答体验（因子接入前的一期）

日期：2026-09-14。任务书：用户转交《给执行 Agent：真实问答可用性与回答体验，因子接入前的一期》v1.0。
实际开发目录：`/Users/yongbiaoli/lei-agent-ux-20260913`（分支 `plan-review-flow-20260913`，基于 `b30ee97e`）。
**未合入运行仓**（`/Users/yongbiaoli/Desktop/lei-signal-lab` 只做了只读诊断，未改任何文件、未重启服务、未写用户业务库）。
关联目标 `okr-8f4f1a5f026f`（执行者只交进度证据，台账由主控更新）。

## 一句话结论（大白话）

这次从「等不到回答」进步到了「有资料先看、能连续讨论」：系统资料一就绪就先亮出来（数据、关键价位、依据边界），AI 解释随后补上；**模型流式路径已修**——原讨论入口对 /api/plan 网关退化为「一口气等全文」、思考型模型会整体读超时，改「边想边传」后同一个模型、同一个配置四轮真实提问全部拿到回答；**数据库失败的可定位性提高**——失败现在会记进服务端日志、能指出聊天在哪条 SQL 等待失败，但具体是哪个后台写者持锁、如何根治仍待真实证据（主控复核 2026-09-15 裁决，持锁根治单列）。回答已经有用，但整体偏长、偏术语，且数值校验通过不等于内容全部正确（第四轮有一处与交易规格直接相悖的表述，见 §4C 反例记录）。主控复核后补修了两个中断边界：①流未正常收尾/被截断不再被当成完成；②未完成回答落库时明确标记，同身份重试会重新生成而非回放半截话（见 §10）。全部改动在开发副本，等主控复核后决定是否合入。

## 1. 改了什么（供主控复核的返拟合入清单）

| 文件 | 改动 | 原因 |
|---|---|---|
| `src/lei_signal/plans/llm.py` | ① `_request_completion_stream` 对 Anthropic 风格网关（/api/coding、/api/plan）改为真流式（SSE 增量产出正文、跳过思考增量、连接 10s+读超时分开）；② 新增 `STREAM_INTERRUPTED` 哨兵——流式中途网络中断时产出，调用方据此标记「未完成」；③ `DISCUSSION_SYSTEM_PROMPT` 补两条固定要求：数据日期非今日须同强度说明「不能直接代表今天」；用户只想观察时给可观察条件、不要求选打法或补测 | 诊断二根因修复 + 任务书§5 表达要求 |
| `src/lei_signal/api/routes/agent.py` | ① 资料就绪后、调模型前发 `prepared` SSE 事件（速览卡/依据卡/下一步，与 done 同名同源）；② 准备段异常与超时补服务端日志（`logger.exception`）——修复「运行版报错服务端零痕迹」的可观测性缺陷；③ 问题落库失败发明确说明、不假装开始回答；④ 流式中断哨兵处理：部分正文保留 + verify_note 标记未完成，不叠加完整模板；⑤ `_degraded_reply` 降级模板按「先回答/日期含义/依据边界/下一步≤3贴题」改写 | 任务书§4 架构 + §5 表达 + 诊断一可观测性 |
| `web/src/pages/AgentWorkspacePage.tsx` | 处理 `prepared` 事件：等待模型期间即渲染资料卡与「系统资料已就绪，AI 解释仍在生成」；失败/中断后资料保留并标注「AI 解释未完成；上面的系统资料仍然可用」 | 任务书§4 |
| `web/src/components/AgentConsole.tsx` | 标的控制台讨论路径从一次性接口改走同一流式协议（复用 `readAgentEvents`），补测准备仍走普通接口；迟到响应按世代丢弃不变 | 验收 D 两入口分阶段 |
| 测试 | 新增 `tests/unit/test_llm_anthropic_stream.py`（6 条）；扩展 `test_agent_stream.py`（prepared 事件、中断哨兵 2 条）；扩展 `test_agent_ux_phase1.py`（降级模板新表达 2 条、日期分支 1 条） | 按修改范围 |

不改：共享 SQLite 层（锁机制本身未改——现有 30 秒等待+WAL 设计未被证明需要动）；已接受的计划流程（C1–C3）不重审；因子相关代码不碰。

## 2. 验收 A：两类首问失败，分别有证据、明确归属

### 失败一：运行版首问「database is locked」

- **证据**：上轮案例 raw（浏览器真实首问最终显示「准备阶段失败：database is locked」）；本次只读补充——运行后端 9/11 10:21 启动、聊天路径文件 mtime 均早于启动（代码漂移排除）；9/14 18:49–18:55 有 360.5 秒的 overseas 预热，首问 18:59 发出；err 日志 9/14 当天 0 条 locked 堆栈，原因是 `_work()` 线程把异常吞进 SSE 不打日志（摘录见 `raw/baseline/runtime-log-excerpts.md`）。
- **复现**（临时库，端到端走真实服务与路由）：另开连接持写锁 35 秒（`BEGIN IMMEDIATE` 不提交），发同一首问——31.0 秒后收到与运行版一致的「准备阶段失败：database is locked」；**修复后的服务端日志精确定位出错语句**（`chat_identity.py:278 enter_chat_request → BEGIN IMMEDIATE`）。释放锁后重发：正常走通。失败尝试不落任何记录（`trade_plans=0`、`fund_trades=0`、无会话残留）。见 `raw/acceptance-A-db-lock.json`、`raw/server-A.log`。
- **归属**：产品缺陷①（可观测性）——失败被吞、服务端无痕迹，已修（补日志）。产品缺陷②（展示层）——失败时用户只看到报错、看不到任何能用的东西，已由「资料先显 + 失败保留」缓解（失败发生在资料准备之前时仍只有报错，此时确实无资料可显，如实呈现）。锁竞争本身（后台预热/分析持久化/newsfeed 与聊天共用一库）是**已知并发环境**，本次未改共享库层；9/14 18:59 具体是哪条语句持锁，因当时无日志**不可指认**，如实保留为未知。按主控复核（2026-09-15 §3）明确能力边界：新日志能指出**聊天在哪条 SQL 等待失败**，**不自动指出哪个连接/事务是持锁者**；持锁问题的根治单列，待真实运行日志积累证据后再立项。

### 失败二：隔离版真实模型 180 秒超时

- **证据**：上轮 raw `server-app-config.log`（`ReadTimeout ... read timeout=180.0（model=ark-code-latest）`）；运行 `.env` 身份 = `ANTHROPIC_BASE_URL=…/api/plan`（Anthropic 风格网关）+ `ARK_TIMEOUT=180` + `ARK_MAX_TOKENS=16000`。
- **归属**：产品缺陷——讨论流式入口对 Anthropic 风格网关**退化为一次性非流式请求**（`_request_completion_stream` 旧代码直接转 `_request_completion`），思考型模型长输入 thinking 期间整段无字节 → 读超时。同仓库买点路径已有「流式实测可用」的对照证据但讨论路径未复用。脚手架自身问题（上轮 404/405、迁移冲突）不属产品缺陷，维持上轮结论。
- **修复验证**：改流式后，同配置四轮真实提问全部成功（首轮全过程 184.8 秒）。措辞按主控复核纠正：读超时与全过程耗时是两回事，**不能单靠总耗时大于 180 秒证明「同轮旧实现必死」**；可成立的是——原讨论路径确有非流式分支（代码与上轮 ReadTimeout 日志为证），改流式后同配置四轮成功。单元测试固化（anthropic 风格必须 `stream=True`、增量顺序、非 200/网络失败降级）。

## 3. 验收 B：可控延迟/超时下，资料先显、失败保留、三段时间

用桩模型控制时序（`raw/stub_model.py`，固定文本只验交互不算质量），真实构建前端 + 真实 SSE 流（Playwright 驱动，`raw/ui_harness.py`）：

| 场景 | 资料就绪可见 | 首段模型正文 | 完成 | 顺序正确 |
|---|---|---|---|---|
| B1 桩首字延迟 8s | **11.8s**（速览卡+依据卡渲染，截图 `B1-facts-ready.png`） | 20.3s | 23.1s | ✓ 资料先于模型正文 |

三段时间（准备/首次有用内容/模型完成）都有记录；首次有用内容=资料卡先显，不拿加载动画充数。服务端与桩日志交叉校准一致。

| 场景 | 结果 |
|---|---|
| B2 桩中途断流（异常终止） | 部分正文保留 + 「AI 讲解因连接中断未完成」标记（14.7s 出现）+ 资料卡保留（截图 `B2-failed-kept.png`） |

B2 过程中发现并修复一个真缺陷：断流原被当成「正常写完」，半截话会照常落库计为已回答——违反「失败后明确哪些解释未完成」。修复为 `STREAM_INTERRUPTED` 哨兵机制（见 §1），配两条单测。

## 4. 验收 C：同一真实模型四轮案例（510300，恰好 4 次请求，无重试）

配置=应用保存的模型配置（未改文件、未换供应商）；临时业务库；本地已有行情（510300 日线截至 2026-09-04，未联网补）。完整原文：`raw/acceptance-C-full-transcript.json`（权威）与页面截图 `raw/screens/C-round1..4.png`。逐轮概要（每轮资料就绪 ≈11.9–23.5s）：

| 轮 | 问题 | 完成耗时 | 人工评价 |
|---|---|---|---|
| 1 | 最近怎么看？先判断，再机会风险，依据够不够 | 184.8s | 合格。第一句给判断；主动说明「2026-09-04 不是今天的数据，不能直接代表现在」；机会/风险分开、支持与不能说明分界清楚；三个关键价位各带人话解释；主动讲震荡画像与「回调打法吃不到肉」；旧胜率表样本小、配置不全如实说 |
| 2 | 哪些有历史依据，哪些只是观察？能否给胜率 | 156.2s | 优秀。证据分层（回测定案/当日读数/不适用前提）逐句归类；胜率三口径说清：没有信号就谈不上胜率、旧表数字「能报不能用」、现行配置下为空需补测 |
| 3 | 先不买只观察，看哪些变化 | 60.9s | 合格。给三个可观察价位+颜色/量能状态条件，明确「什么情况回来聊、什么情况不用看」；不要求选打法或补测 |
| 4 | 满足条件后进入/失效/退出怎么讨论？缺什么？别替我保存计划 | 126.5s | 优秀。五项假设逐项框架化、只引材料数值；明确最大缺口=信号不存在+数据过期；列出缺项清单；结尾「不保存、不出计划草案」 |

边界如实性核对：全程 `grounded=true`（数值接地校验通过）；没有编造买点、没有给本次胜率、没有保存计划或成交（`trade_plans=0`、`fund_trades=0`）。**但数值校验通过不等于内容正确**——按主控复核（2026-09-15 §6）记录一处直接反例：第四轮正文「系统对盈亏比 3 是只算不强制，低于 3 只提示」与最高溯源 `docs/trading-spec-v1.md` §10（盈亏比不足 3 放弃交易）、§13 无交易条件第 4 条直接不一致；无论源于上下文旧文案还是模型改写，都不能以 `grounded=true` 证明其正确。本轮不追查完整来源、不扩算法修复，仅保留反例；后续因子接入必须区分「材料中的数字 / 研究结论 / 允许的交易用途」。其余已注意的小瑕疵：第 2 轮正文有一处日期笔误「2026-09-004」（模型抄写错误，接地校验未拦截字符串形态）；「平均错开 170~246 天」等引用均出自材料（experience/fit 块），非模型编造，但「回测定案」「退出历史依据最硬」这类表述也不因数字出自材料就完成适用性核验。主控对回答质量的其他意见（整体偏长、偏术语、第三/四轮重复旧统计、首层与折叠内容的配合）记录为后续表达方向：首层直接列最相关的两三项条件和日期限制、历史数字按追问展开；不在本轮追加页面重构。

## 5. 验收 D：两入口分阶段、切会话迟到响应、刷新恢复、不重复记录

（`raw/ui_harness_d.py`、`raw/acceptance-D-result.json`，截图 `D-*.png`）

- **工作台分阶段**：发问后 11.9–12.9s 资料卡先显（截图 `D-ws-facts.png`、`D-ws-p2-facts.png`）。
- **标的控制台分阶段**：抽屉发问后 12.4s 显示「系统资料已就绪（见下方依据卡），AI 解释仍在生成…」+ 依据卡（截图 `D-console-facts.png`）——此前抽屉只有一句「正在整理」。
- **迟到响应不串入**：工作台「停止接收→新对话」后，等服务端把旧流走完，新视图 0 条迟到内容；控制台流式期间切标的，回来后 0 条旧回答串入。产品事实一并记录：工作台流式期间有意禁用「新对话/历史」按钮（防串扰设计）；「停止接收」=本次回答不落历史（历史只留问题，不落假回答——`p1_stopped_session_history_answers=0`）。
- **刷新恢复**：完整轮次（1问1答）经「新对话→历史载入」与「刷新→历史载入」两次恢复，回答与资料卡完整（`p2_restored_answer_count=1`、`p2_after_reload_restored_count=1`）。
- **不重复记录**：`trade_plans=0`、`fund_trades=0`；仅完整走完的轮次落回答（库内 5 会话=两次失败的 D 尝试各 1 问题 + 停止的 1 问题 + 完整 1 问 1 答 + 控制台切换 1 问题，逐条核对见 raw）。

## 6. 验收 E：同样事实，改前/改后对照

同一份事实（510300，2026-09-04 数据，无买点，被无交易条件 1/7 挡住，无匹配统计）：

**改前**（上轮真实输出）——状态标签开头、日期只当角标、下一步把选择困难交回用户：

> 【510300.SS（510300.SS）】数据日 2026-09-04。AI 讲解暂时不可用……
> 当前状态：黑色 / 关键风险 / 风险关注 有效顶部+黑色……
> 接下来可以：说说你想用哪种打法讨论（趋势回调 / 突破 / 反转），或对这个标的发起一次历史补测。

**改后**（同事实新模板输出，`raw/acceptance-E-before-after.json`）——先回答、日期同强度、依据一句话、下一步贴题：

> 510300.SS（510300.SS）：按系统数据，现在不构成可执行的入场计划——按规则本轮不适合讨论开新仓。
> 系统给出的原因是：1.无法明确当前趋势类型、7.多周期杂乱。
> 注意：AI 讲解暂时不可用。以下是系统按 2026-09-04 数据直接给出的事实——今天是 2026-09-14，这是过去的数据，不能直接代表今天；先用最新数据核实再谈下一步。
> ……历史依据：现在不能给这次判断附上可靠的胜率——现有记录不足以核实是否是同一种做法……
> 接下来可以先核实这个标的的最新数据；想继续讨论的话，说一个你关心的条件或价位，系统有对应事实时再展开。

对照结论：能否直接回答=改前不能（标签罗列）改后能；机会风险解释=改前缺位改后明确；依据边界=改前工程腔改后一句话；下一步贴题=改前让用户选打法改后给可执行动作。真实模型路径的表达改进由提示词两条新规承担，验收 C 四轮已见实效（日期说明、观察型回答）。失败与不确定也如实入报告：模板无法覆盖「有候选且未阻断」之外的全部形态，候选分支文案较简（依赖依据卡补充细节）。

## 7. 因子库衔接（本期只交接，不实施）

**现有讨论上下文适合读入已验收材料的位置**（均为只读挂载先例，缺席不阻断）：

1. `src/lei_signal/api/routes/agent.py::_prepare_discussion` —— 可选叙事块的现行挂载点（`experience`/`fit`/`sentiment_signals`/`winrate` 都在此 try/except 挂入 `ctx_payload`）；已验收因子的「辅助解释材料」应走同一模式。
2. `src/lei_signal/plans/llm_context.py::build_discussion_context` —— LLM 实际可见材料的裁剪层；因子摘要要进提示词必须在此有明确槽位与字段边界（现有裁剪原则：给了它就会引用，引用了就要校验）。
3. `src/lei_signal/plans/llm.py::DISCUSSION_SYSTEM_PROMPT` —— 引用纪律入口（因子必须按「是什么/对本标有什么证据/不能说明什么」三段讲，禁止合成胜率）。
4. 前端展示位：`web/src/components/EvidenceCardView`（依据卡已分「判定层事实/历史与范围/解释与假设」区，因子证据属「研究材料」区，不得混入判定层事实区）。

**接入前缺项清单**（缺任何一项都不应接）：

- 因子「已验收」状态的机器可读来源与适用范围（标的/环境/观察期限）——待因子研究工坊交付后才有，任务书示例不算实现；
- 每个值的 `available_at`/缺失状态/来源指纹（展示「当时可知」）；
- 用途边界字段：研究材料展示 / 辅助解释 / 申请改变技术判定——第三种需主控单独裁定，不得由讨论层自动升级；
- 接地校验口径：因子值进 `ctx_payload` 后才会进 `allowed_nums` 白名单，需防「因子数字绕过现行无统计不给胜率」的纪律；
- 与因子负责人的交付物对齐（本期不冻结第二套因子字段、不接研究包）。

未来第一步（建议）：让 Agent 准确回答「这个因子是什么、对本标的有什么证据、不能说明什么」，有增量效果证据后再讨论采用。基本面/消息面仍只解释原因。

## 8. 测试与运行记录

- 后端：`pytest tests/unit/test_llm_anthropic_stream.py tests/unit/test_agent_stream.py tests/unit/test_agent_ux_phase1.py` 19 passed；相关讨论/LLM 契约测试 60 passed（`test_agent_chat/test_chat_discussion/test_discussion_contract_r2/test_plans_llm/test_copilot_llm/test_buy_point_chat`）。日志入 `raw/tests/`。
- 前端：`tsc --noEmit` 通过；`npm run build` 通过；`test:agent-ux`/`test:agent-workspace`/`test:agent-tasks`/`test:evidence-card` 全过。
- 隔离服务：三个阶段（A/B 桩、C 真实模型、D 桩 8022）均为临时库+本机行情+8021/8022 端口，结束后即停；运行版服务（PID 1790/1784）全程未动。模型网络请求仅 C 阶段 4 次（预算 5 次内），无行情外联。
- raw 清单（均新增目录，未覆盖旧 raw）：`environment.json`、`inputs-and-acceptance.md`、`baseline/`、`code-changes.diff`、`serve_iso.py`、`stub_model.py`、`ui_harness.py`、`ui_harness_d.py`、`repro_db_lock.py`、`acceptance-A-db-lock.json`、`acceptance-B1/B2-timings.json`、`acceptance-C-rounds.json`、`acceptance-C-full-transcript.json`、`acceptance-D-result.json`、`acceptance-E-before-after.json`、`screens/`（15 张）、`server-*.log`、`stub-*.log`、`environment-iso-*.json`。

## 9. 未完成与边界

- 9/14 18:59 运行版锁冲突的具体持锁语句不可考（当时无日志）；新日志只定位聊天等待失败的语句，**不指认持锁者**；共享库层的并发设计本身未改，持锁根治单列待真实证据（主控复核裁决）。
- 控制台抽屉在流式期间切标的=放弃本次回答（问题已记录、回答不落历史）——与工作台「停止接收」同一语义，本期如实保留，不扩功能。
- 降级模板的「510300.SS（510300.SS）」重复显示为既有展示瑕疵（ctx 无 display_name 时的兜底），未在本期修。
- 一期原边界「前端历史恢复不展示未完成明细」已在补修二解决（`answer_incomplete` 字段 + 历史标注）。
- 回答整体偏长、偏术语，首层与折叠内容的配合待改进——主控记录为后续表达方向，本轮不追加页面重构。
- 真实回答质量是本轮四轮的人工评价，不构成对模型 generally 质量的结论；固定文本桩仅用于交互验证；数值校验通过不等于内容正确（§4C 反例）。
- 控制台抽屉与工作台在流式期间均不提供第二个问题入口（按钮禁用/忙态守卫）——迟到防护依赖世代/票据丢弃与「停止接收」，维持既有设计。

## 10. 主控复核补修轮（2026-09-15）

主控书面复核：`/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/agent-conversation-controller-review-2026-09-15/`（独立探针 `probe.py`、`results.json`、22 项专项回归）。本轮只实施两项固定补修与报告结论纠正；不重做计划工程、不追加页面重构、不发真实模型请求。

### 10.1 补修一：流未正常收尾不再算完成

- **修前**（主控探针实测）：正文后①连接正常关闭但无 `message_stop`、②服务端 `type=error` 事件，两种结束都只返回半句话且 `interrupted=false`，与正常完成无区别——完成判定依赖「迭代器没抛异常」。
- **修后**：`plans/llm.py` 新增 `StreamInterrupt(reason)`（connection_interrupted / no_completion_marker / server_error_event / max_tokens_truncated）；Anthropic 流核对 `message_stop`、`error` 事件与 `stop_reason=max_tokens`，OpenAI 流核对 `[DONE]` 与 `finish_reason=length`，缺正常终止标记一律产出未完成标记。买点共用包装函数保留原失败降级语义（失败→None；额度截断沿用原行为返回已收正文）。
- **固定矩阵测试**（`tests/unit/test_llm_stream_completion.py`，合成事件、零模型请求）：正常完整流 / 正文后正常 EOF 缺完成标记 / 服务端错误事件 / 网络异常 / 额度截断，Anthropic 与 OpenAI 各自支持的事件按实际协议验证，正常例含真实正常终止。10 条全过。

### 10.2 补修二：未完成回答如实落库，同身份重试再生成

- **修前**（主控探针实测）：中断回答 `answer_state=answered`、`meta_json` 无未完成原因；同 `client_request_id` 重试只回放原半句话（`replayed=true`），模型不再调用——「可重试同一问题」承诺未实现。
- **修后**：
  - `copilot/chat_identity.py`：新增 `mark_incomplete`（状态 `incomplete`，部分原文照常绑定保留）；`_claim_generation` 支持 `incomplete→generating` 原子领取（并发重复重试只有一个胜出）；`incomplete` 状态的重试走既有 `resume` 路径对原问题重新生成，不新增问题。
  - `api/routes/agent.py`：`_append_answer` 新增 `incomplete` 参数（回答插入与状态绑定同一事务）；流中断时 meta 写入 `answer_incomplete={reason, reason_cn}`，done 事件 `answer_state=incomplete`；`verify_note` 带具体原因（连接中断/未正常收尾/服务错误事件/额度截断）。
  - `api/schemas.py` + 消息历史路由：`AgentMessageDTO` 增加可选 `answer_incomplete`（刷新/历史可区分未完成与其他未过校验）。
  - 前端两入口：done 不再都当完整答案（incomplete 按失败态展示）；历史恢复的回答显示未完成标记；未完成回答提供「重试生成」按钮，用同一 `client_request_id` 与原请求快照（会话/对象/上下文一致，`request_hash` 一致不 409）重新生成；控制台讨论请求补带稳定 `client_request_id`。
- **固定矩阵测试**（`tests/unit/test_agent_incomplete_retry.py`，真实路由+临时库+合成流）：正文中断→当时提示→messages API 明确未完成→同 cid 重试确实再调用（模型调用数 2）→原问题不增加（user 消息数 1）、旧部分原文保留+新完整回答、最终结果 `answer_state=answered` 且无未完成标记→再次重试只回放；身份层并发重试 CAS 只领到一次生成权。全过。

### 10.3 补修轮改动文件与验证

- 改动：`src/lei_signal/plans/llm.py`、`src/lei_signal/api/routes/agent.py`、`src/lei_signal/copilot/chat_identity.py`、`src/lei_signal/api/schemas.py`、`web/src/pages/AgentWorkspacePage.tsx`、`web/src/components/AgentConsole.tsx`、`web/src/types.ts`；测试新增 2 文件、更新 1 文件。差异：`raw/agent-conversation-fixes-2026-09-15/code-changes-fixround.diff`；修前/修后 SHA256：`raw/agent-conversation-fixes-2026-09-15/fingerprints.md`（修前与主控 results.json 被审状态同源）。
- 验证：补修矩阵 19 passed；相关回归（agent_chat / chat_discussion / discussion_contract_r2 / agent_ux_phase1）44 passed；`tsc --noEmit`、`npm run build`、`test:agent-ux`、`test:agent-workspace` 通过。未重跑全仓回归与四轮付费案例（按主控指示）。
- 一期四轮真实调用证据继续有效：补修只影响中断边界与持久化状态，正常完成的回答路径行为不变（由「正常完成重试只回放」矩阵覆盖）。

## 11. 主控二轮复验补修（2026-09-15，遗漏一/二）

主控二轮复验确认一轮主路径补修通过（流未正常收尾可识别、同身份重试再生成、旧半截保留、成功后不重复生成、报告过满表述已纠正），同时指出两项遗漏；本轮只补这两处，已通过项锁定，未重跑四轮真实模型或计划工程。主控证据：`/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/agent-conversation-controller-recheck-2026-09-15/`。

### 11.1 遗漏一：OpenAI 风格流内错误事件识别

- **修前**（主控探针反例）：正文后流内 `{"error":{...}}` 事件不被识别——error 后直接 EOF 被归因为 `no_completion_marker`（丢失真实原因）；error 后跟 `[DONE]` 则完全没有中断标记，半句话按正常完成返回。此前我的矩阵表述「5 场景×双协议」不准确：OpenAI 侧实际用 HTTP 非 200 用例替代了流内 error 用例，二者不同。
- **修后**：`_request_completion_stream` OpenAI 分支解析 JSON 后先检查顶层 `error`，识别即以 `server_error_event` 收尾并返回——后续的 `[DONE]`/EOF 不得把已下发的服务错误洗成成功。新增 error→EOF 与 error→[DONE] 两例，保留正常完成与额度截断对照（`test_llm_stream_completion.py` 现 12 条）。

### 11.2 遗漏二：历史恢复提供可核实的重试身份（原问题重试入口）

- **修前**：历史映射只恢复未完成标签，无 `incompleteDone`/`requestBody`/`clientRequestId`——刷新后只有标签、没有原问题重试入口；「可重新提问生成」的普通提问是新问题，不满足「刷新/历史仍未完成→同身份重试」的用户路径。
- **修后**：
  - 服务端：迁移 030（`agent_chat_requests` 增加 `request_message/request_context_kind/request_symbol`，领号时保存原始三输入）；回答行经 029 已有的 `source_request_id` 带回编号（流式/普通两路 `_append_answer` 均传入）；`chat_identity.retry_identity_for` 投影函数——**仅当** claim 处于 `incomplete`、原始输入已存、问题号已回填且消息与绑定部分原文一致时，才在消息历史 API 投影 `retry={client_request_id, message, context_kind, symbol}`；已完成问题与旧记录（无编号/输入不可考）不投影，不伪造字段。
  - 前端：工作台历史恢复按服务端投影还原 `clientRequestId/requestBody/incompleteDone`（不用当前会话或当前标的猜原请求），重试按钮照常出现并可点击；历史标签与重试按钮并存时各司其职（标签说明当时状态，按钮走原问题重试）。控制台抽屉无历史恢复流程，历史重试入口实际在工作台（两入口的流式提问路径同一套协议，前轮证据复用）。
- **固定验收（隔离服务+模型桩端到端，`ui_harness_r2.py`）**：中断（部分正文+未完成标记）→刷新→打开历史→未完成标注与「重试生成」按钮真实可见→点击重试→桩累计恰好 2 次调用（第 1 次按设计断流、第 2 次正常完成）→原问题数仍 1（user 消息 1 条）→再次刷新恢复显示最终回答，旧部分原文保留（共 2 条回答）；已完成问题恢复后不再出现任何重试入口（`final_restore_retry_buttons=0`）；`trade_plans=0`、`fund_trades=0`。截图 `screens/R2-*.png`，结果 `acceptance-R2-history-retry.json`。
- **单元矩阵**：OpenAI 流内 error 两例 + 投影三例（incomplete 投影含 cid 与原消息 / 已完成不投影 / 旧记录不可考不投影）全过；相关回归（agent_chat / discussion_contract_r2 / chat_discussion）33 passed；`tsc --noEmit` 与 `npm run build` 通过。未发任何真实模型请求。

## 12. 主控收口（2026-09-15）：两项固定补修通过

主控收口报告：`/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/agent-conversation-controller-closeout-2026-09-15/`（独立重放 OpenAI 正文→error→EOF 与正文→error→[DONE]，均返回 `server_error_event`；独立临时库走真实 FastAPI——从 messages API **实际读取** retry 身份完成重试，累计模型调用 2 次、原问题身份不变、旧部分回答保留、终态 answered 且历史重试投影数 0、再发原请求只回放；迁移 030 仅增三输入列；两文件专项回归 16 passed）。裁决：**passed，仅指本轮两个固定补修通过**；本轮剩余返修无。

下一阶段（合入准备与运行验收，另行安排，非本报告执行范围）：
1. 核对开发副本相对运行仓的完整差异与依赖（含前期 UX/计划成果，不能只拷本轮文件）；保留运行仓并行修改，整理合入清单与回退材料；沿用先前计划流程的小文案补丁（`save-error-wording.patch`）与登记收尾项。
2. 合入/重启/真实库迁移须在既有授权范围内另行安排；真实库先备份，核对迁移 030，前后端版本同步。
3. 更新后在实际运行入口验证真实首问、资料先显、历史恢复，核对迁移与锁日志；**实际运行首问必须再验证**（锁只是加了定位日志，持锁者未查明），若仍发生按运行问题处理，不得称稳定上线。
4. 边界保持：盈亏比文案冲突等真实性事项、回答偏长与整段耗时、四轮旧资料案例的局限，均沿上轮意见在实际试用中观察改进；锁竞争根治与全部回答真实性不在本次通过结论内。

## ARCHIVE

分类：数据与质量；verdict：mixed（按主控复核 2026-09-15 更正）。真实讨论可用性与资料先显有实际进步，模型流式路径已修（原讨论路径确有非流式分支，改流式后同配置四轮成功）；数据库只提高了失败可定位性，具体持锁者与根治未闭合、单列待真实证据；中断完整性与恢复的两个实测缺口已按固定矩阵补修（§10）。未生产合入；不声称收益、因子有效或全部回答真实性通过（第四轮盈亏比表述与交易规格相悖已记录反例）。四轮真实调用证据继续有效。二轮复验（2026-09-15）两遗漏已补：OpenAI 流内错误事件识别（error 不得被后续结束标记洗成成功）、历史恢复投影可核实的原问题重试身份（旧记录/已完成不投影）；端到端验收中断→刷新→历史→真实点击重试全链通过。测试进程已停，临时库随临时目录销毁。
