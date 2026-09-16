# 连续讨论补修收口：e461d838 独立复验通过，零产品代码改动结案

> **三轮修订（2026-09-17，同任务 round=2）**：主控复核发现冻结目标内的三处
> 残余并已在本轮修复——G1 概念放行曾覆盖肯定执行要求（已修 `agentUx.ts`）、
> G2 撤销/用途未核本人与肯定陈述（已修 `resolve.py`）、G3 本报告三处文案
> 纠错（本轮已改）。详见 §7 三轮补修；§1–§6 为 round=1 原始记录，按要求
> 原样保留（其中 §6 的两处表述已在 §7 标注作废并以 §7 为准）。
>
> **四轮修订（2026-09-17，同任务 round=3，最后一轮）**：主控第二轮复核发现
> round=2 的修法按**整句**判断否定/人物，一句多事仍误判（先否定比较再肯定
> 回测漏拦、朋友+本人同句撤销失效、否定闲钱仍记闲钱）。本轮按共同根因改为
> **分句**核实，详见 §9；§7 为 round=2 原始记录，原样保留。

## 一句话结论（大白话）

主控点名的两件事，这一轮独立复验全部成立，**本轮没有改任何产品代码，只补了证据**。
① 在通信ETF（515880）的聊天里要求「换成ATR止损比较一下」，系统老实说「这项比较暂未支持」；
点「继续讨论」发出去真的能得到讨论回复（不是把拒绝的话再念一遍），问「ATR止损是什么意思」
也能正常解释，而且整个过程聊天对象始终是通信ETF，没有被「ATR」三个字母拐到一只同名证券上
——工作台和控制台两个入口都实测，有页面截图和后端请求记录，补测任务零新增。
② 聊天记忆不再认错人：假设的钱（「如果我有一万」）、朋友的钱不会再被当成你的预算，
「我手里有一万闲钱」是现金不算持仓，「我已经不持有了」立刻清除旧持仓，
「不是一万，是五千」改口马上生效且前后不矛盾——以上每一条都用临时数据库里的真实消息
编号逐条验证过，回答落库原文与系统准备的材料一致，全程没写任何真实计划或成交。
可以按原样交主控复验合入。

## 0. 范围与方法

- 工作区 `/Users/yongbiaoli/lei-agent-main-consolidation-20260915`，分支
  `codex/agent-experience-continuity-20260916`，被验提交 `e461d838`（派发前HEAD，
  即 cfix2 补修轮成果）。
- 按「先验证、已通过不重写、不为修改而修改」执行：本轮**零产品代码改动**，
  新增文件只有报告、raw 证据与过程交接（归置检查证实本次零新增违规）。
- 浏览器链用隔离服务（临时业务库 + `MODEL_MODE=degraded`：模型路径整体停用，
  连桩模型都不联网，不读密钥、不调用真实模型；业务写入全落临时库）；
  端口 8022/8032，不碰 8000/5173 运行端口，结束已停自己的预览进程。
- 未合并 main、未部署、未重启任何服务、未写真实计划与成交、未动运行目录
  （运行目录只做了只读比对）。

## 1. G1：ATR 拦截诚实、继续讨论可达、指标词不切对象

验收逐条对照（两个入口 = 研究工作台 `/agent` + 个股页 AI 助手抽屉）：

| 验收点 | 工作台 | 控制台 | 证据 |
|---|---|---|---|
| 比较问法诚实拦截 | ✓ | ✓ | 截图 `screens/r3-ws-atr-intercept.png` / `r3-console-atr-intercept.png` |
| 拦截时对象保持通信ETF | ✓（上下文条「当前讨论 通信ETF (515880.SS)」） | ✓ | 同上截图 + 请求载荷 `symbol=515880.SS` |
| 点「继续讨论」发送→得到讨论回复（非拦截复读） | ✓ | ✓ | `screens/r3-atr-chain-notes.json`；截图 `r3-ws-atr-continued.png` / `r3-console-atr-continued.png` |
| 补测任务零新增 | ✓ | ✓ | notes `no_backtest_tasks: true`（两入口） |
| 概念问法正常讨论 | ✓ | ✓（严格复测） | 工作台：notes + 请求记录；控制台：`console-concept-recheck.json`（轮数净增+新请求200+回复无拦截语） |
| 显式比较仍诚实拒绝 | ✓ | （前端同函数拦截） | notes `explicit_compare_still_refused: true` |

- **请求证据**：`atr-chain-requests.json` 记录 4 条后端请求（方法/URL/状态码/载荷），
  其中「继续讨论」草稿两条（两入口各一）均到达后端且 `symbol=515880.SS`，
  概念问法两条（工作台链内 1 条 + 控制台严格复测 1 条）均到达后端；
  比较问法本身在前端即拦截（不发请求），与设计一致。
- **「明确真实证券ATR查询保留」**（函数级，`atr-guard-probe.json`）：
  「看看ATR这只股票现在怎么样」「ATR现在怎么看」仍解析出证券 `ATR`（不全局禁用代码）；
  「如果换成ATR止损…」解析结果为空（指标词不认领证券）；
  「515880 参照ATR距离设止损」只解析出 `515880.SS`。服务端双层守卫
  （`_symbol_candidates_from_message` token 层 + 目录层）均在位。
- **拦截区分是真语义判断，不是改草稿躲正则**：`web/src/utils/agentUx.ts` 的
  `ATR_CONCEPT_RE`（是什么意思/聊聊/讨论/思路/不要求回测/不做数值比较…）在
  拦截函数内放行概念问法；比较/换用措辞仍返回「ATR 止损」。草稿与概念问法分别
  走到后端（请求记录），说明放行与对象解析互不依赖。

**G1 = done。**

## 2. G2：用户事实先核语义、再按精确问题归属进记忆

独立探针 `g2-fact-matrix.py`（结果 `g2-fact-matrix.json`，`ALL_OK: true`）：

- **五例反例全关**：假设的钱、朋友的钱不进预算；「手里有一万闲钱」不算持仓；
  「我已经不持有了」进撤销；「朋友持有这个」不算持仓。
- **正例保留**：持有继承（后续回答转持仓管理口吻）、资金用途继承（闲钱）。
- **临时库真实身份**（Part B，`create_session/append_message` + 与路由
  `_append_answer` 同列的直接 SQL，自增 `message_id` 与精确 `question_id`，
  从库读回 `list_messages` 行喂 `_user_background`）：
  - 中断未答（声明无绑定回答）→ 不可继承；相邻位置不猜（同对象也不行）；
  - 下一问换对象（510300 回答绑定问题2）→ 问题1 无主声明不串用到 510300；
  - 同题多回答（两条回答同 `question_id`）→ 绑定一致、事实不丢、不跨对象；
  - 全局（symbol 未知）→ 不收集任何背景；
  - 否定撤销清除；「不是一万，是五千」先清后立（背景 5000，10000 不再出现）。
- **路由级**（Part C，TestClient + 临时库 + 无模型系统直出）：
  五反例回答原文不含金额误写；正例继承、撤销、金额更正、成本措辞
  （不谎称「你没给成本」，含「没有成本提取能力」）全部通过。
- **准备材料与落库回答一致**：回答接口返回的 `reply` 与
  `/api/agent/sessions/{sid}/messages` 落库原文逐字一致（`reply_matches_stored: true`）。
- **不写真实计划成交**：过程临时库 `trade_plans/fund_trades` 等 7 张表计数全 0；
  全部写入只在 `/tmp` 临时库（路径记录在结果 JSON）。
- 既有回归：主控固定矩阵的 34+7 项测试（两套连续讨论测试文件）41 项全绿。

**G2 = done。**

## 3. G3：合入交接与归置

- 单分支提交（本报告与证据为分支上新提交）；只新增报告/raw/交接文件，
  零产品代码改动（`git show --stat` 可复核）。
- 回归：连续讨论两套测试 41 通过；与 cfix2 同口径的 **13 文件相关回归**
  （名称/主题/03B/契约/stream/copilot_ops/稳定性/重试/e2e + 连续讨论）
  **144 通过、1 已知 xfail**（`tests/integration/test_agent_chat_e2e.py`
  校验器百分比派生缺口，xfail(strict) 留痕——保持原边界，不是全绿；
  这是 13 个相关测试文件的范围，**不是全仓测试**）。
- 前端：`npm run test:agent-ux` 通过；`npm run build`（含 tsc）通过。
- 归置检查（只读）：借用运行仓 `scripts/check_repo_hygiene.py` 原函数与白名单，
  将检查根重定向到本工作区（方法记录于
  `raw/agent-continuity-zcode-closeout-2026-09-17/run_hygiene_readonly.py`）。
  结果 **298 项 = 治理前基线 299 项 − 1 项已解决**（因子草案已由 e461d838 迁入
  `docs/archive/handoffs-plans/`），**本次任务新增 0 项**。298 项均为治理前基线
  缺口（根层散文件、tests 夹具、worktree `.git` 识别等），按要求不扩项治理、
  不迁移受保护历史、不称全绿（日志 `hygiene-r3.log`）。

**G3 = done。**

## 4. 残余、未覆盖与本轮发现（原样报告，交主控裁断）

1. **拦截轮「接下来（针对 名称待核实（515880.SS））」标签**
   （`web/src/components/agent/NextStepsBar.tsx` 的 displayName 取自本轮自身卡片，
   拦截轮无卡片）。这是**既有显示残留**：cfix2 的显示名修复范围是「标题/上下文条」
   （本轮实测这两处已正常显示通信ETF），该标签在 e461d838 之前的 r2 拦截截图里
   就是同样表现（`raw/agent-experience-continuity-2026-09-16/screens/r2-ws-atr-intercept.png`）。
   对象符号全程正确（515880.SS）、名称显示是诚实的「不凭代码猜名字」纪律，
   不属于 G1 验收文字；按「不为修改而修改、业务歧义交主控」原样报告，未改。
   隔离环境右侧资料面板同场景显示「名称待核实」同源（r2 一致）。
2. 概念放行后的讨论内容诚实边界（不捏造回测结果）由接地校验与提示词维持，
   本轮未逐字验证每种概念问法；指标词守卫表仍只有 ATR 一个登记项。
3. 治理 298 项基线缺口未处理（交治理任务，与本任务无关）。
4. 控制台入口的显式比较拒绝依赖与工作台同一前端函数（`detectUnsupportedExitRequest`），
   控制台链内未单独重复拍摄显式比较截图（函数级回归与工作台实测覆盖）。

## 5. 精确测试命令与源码指纹

```bash
# 连续讨论两套（41 通过）
PYTHONPATH=src /opt/homebrew/bin/python3.11 -m pytest -q \
  tests/unit/test_agent_continuity_20260916.py \
  tests/unit/test_agent_continuity_routes_20260916.py
# 连续讨论 13 文件相关回归（144 通过、1 已知 xfail；非全仓测试）
PYTHONPATH=src /opt/homebrew/bin/python3.11 -m pytest -q \
  tests/unit/test_agent_continuity_20260916.py tests/unit/test_agent_continuity_routes_20260916.py \
  tests/unit/test_agent_name_resolve.py tests/unit/test_agent_subject_names.py \
  tests/unit/test_chat_discussion.py tests/unit/test_discussion_backtest_03b.py \
  tests/unit/test_discussion_contract_r2.py tests/unit/test_discussion_identifier_spans.py \
  tests/unit/test_agent_stream.py tests/unit/test_copilot_ops.py \
  tests/unit/test_agent_ask_stability.py tests/unit/test_agent_incomplete_retry.py \
  tests/integration/test_agent_chat_e2e.py
# 前端
cd web && npm run test:agent-ux && npm run build
# 浏览器链（先起隔离服务：MODEL_MODE=degraded ISO_PORT=8022 python3 serve_iso_r3.py）
PYTHONPATH=src /opt/homebrew/bin/python3.11 docs/experiments/raw/agent-continuity-zcode-closeout-2026-09-17/ui_atr_chain_r3.py
PYTHONPATH=src /opt/homebrew/bin/python3.11 docs/experiments/raw/agent-continuity-zcode-closeout-2026-09-17/console_concept_recheck.py
# 独立探针（G2 / ATR守卫 / 归置）
PYTHONPATH=src /opt/homebrew/bin/python3.11 docs/experiments/raw/agent-continuity-zcode-closeout-2026-09-17/g2-fact-matrix.py
PYTHONPATH=src /opt/homebrew/bin/python3.11 docs/experiments/raw/agent-continuity-zcode-closeout-2026-09-17/atr_guard_probe.py
/opt/homebrew/bin/python3.11 docs/experiments/raw/agent-continuity-zcode-closeout-2026-09-17/run_hygiene_readonly.py
```

源码指纹（被验时点，SHA256 全表见
`raw/agent-continuity-zcode-closeout-2026-09-17/source-fingerprints.json`）：
`agent.py`、`resolve.py`、`agentUx.ts`、`AgentWorkspacePage.tsx`、`AgentConsole.tsx`
等 11 个关键文件；本轮零改动，指纹即 e461d838 状态，可直接与主控复验时比对。

## 6. 给主控：可合入提交列表与运行目录只读差异

- **可合入提交列表**（单一分支 `codex/agent-experience-continuity-20260916`，
  线性历史，接受与否由主控复验裁决）：
  - `d465b558` 连续讨论四处修复（基线轮）
  - `6292b527` / `ecb6fdb4` / `143d1c1e` 冻结案例、基线与报告（docs）
  - `b1dc3270` 两处陈旧 e2e 断言修复（既有基线失败）
  - `0e5cba80` C1–C3 补修；`ba16af38` docs；`e461d838` **实施提交**（两项
    固定收口的产品实现，本轮被验对象）
  - 交付提交（纯文档与证据，无产品代码）：round=1 交付为 `f4e8c960`；
    round=2 按主控复核补修后以分支**顶提交为准**（以 `git log` 现查，
    本报告不引用自身哈希——round=1 曾自引 `25926877`，因 amend 漂移作废，
    此处记录该教训：交付提交区分「实施」与「交付」，交付哈希只作当时点记录）。
- **运行目录只读差异清单**
  （`raw/agent-continuity-zcode-closeout-2026-09-17/runtime-dir-readonly-diff.json`，
  运行目录未被写入）：与本分支 11 个关键文件对应的运行目录文件中，
  9 个内容不同、2 个测试文件运行目录不存在（新增）。**这只是差异记录——
  运行目录存在并行因子改动，不能据此判定运行仓落后或本分支可直接覆盖；
  差异待主控与并行因子负责人定向核对后再定采用方式。**
  `configs/`、`src/lei_signal/ui/`、`.env*` 本分支未触碰。
- 台账（升级库）由主控更新，本轮未写共享升级库。

## 7. 三轮补修（主控复核 round=2，同任务同一冻结目标）

主控独立复核（`docs/experiments/controller-zcode-continuity-2026-09-17.md`，
失败证据 `raw/controller-zcode-continuity-2026-09-17/`，原样保留未覆盖）发现
冻结目标内三处残余；本轮只修这三处，不扩项。

### G1 修复：概念放行不再覆盖肯定的执行要求

- 反例： 「请解释一下用ATR止损回测，比较收益」「先聊聊，再帮我用ATR止损补测」
  修前均放行（null）。修复（`web/src/utils/agentUx.ts`）：新增肯定执行动作词表
  `ATR_EXEC_RE`（补测/回测/测一下/复跑/重新测/再测/比较）+ 就近否定表
  `ATR_EXEC_NEGATED_RE`——执行动作未被否定时，概念词（解释/聊聊）不再放行；
  纯概念与明确否定执行（「是什么意思？我不要求回测」「不想做比较」）继续放行。
  只收**动作词**：胜率/收益是话题词不是执行要求，不进表（「对收益的意义」须放行）。
- 保留：原继续讨论草稿、真实证券 ATR 识别、两入口共用函数，均未动。
- 证据：主控 `atr-probe.mjs` 同逻辑修后复跑三例全过
  （`raw/agent-continuity-zcode-closeout-r2-2026-09-17/atr_probe_rerun.mjs`
  + `atr-rerun-results.json`；主控目录原始失败结果未覆盖）；
  前端回归新增 4 断言后 `npm run test:agent-ux` 通过。
- 两入口浏览器链（隔离服务，临时库，无模型；
  `ui_atr_mixed_chain.py` + `atr-mixed-notes.json` + `atr-mixed-requests.json`
  + 截图 5 张）：两例混合问法均诚实拦截、**无任何非 GET backtest 流量**
  （唯一 backtest 请求是面板配置 `GET /api/backtest/options`，非任务创建）、
  页面无补测任务卡、工作台上下文保持通信ETF；纯概念在两入口均正常讨论
  （工作台新答案卡+后端请求证据；控制台轮数净增+新请求 200）。
- 开发过程记录：首轮浏览器脚本两次假阳性/假阴性（等待条件被旧卡提前满足、
  一次漏发 Enter），修正断言后全绿；这些脚本迭代只发生在本轮 raw 目录内。

### G2 修复：撤销须本人肯定陈述，用途与金额同界

- 反例修复（`src/lei_signal/copilot/resolve.py`）：
  1. 「我没有清仓/还没卖出」——否定清仓动作＝仍在持有，不清除
     （新增 `_CLEAR_ACTION_NEG_RE` 就近否定守卫）；
  2. 「朋友清仓了/朋友已经卖了」——第三人主语不清除本人背景
     （`detect_fact_correction` 增加 `_THIRD_PERSON_RE` 守卫，
     `budget_cleared` 同界）;
  3. 「朋友有一万元闲钱」——用途不再入本人背景（`parse_request` 用途提取
     加假设/第三人守卫），且不再追问用途（澄清条件同界）。
- 正例保留：本人肯定清仓（我清仓了/我已经卖了/我已经不持有了）仍清除；
  本人闲钱用途、金额更正（不是一万是五千）不变；r1 全部既有正反例不回退。
- 证据：主控 G2 探针同逻辑修后复跑三查全过
  （`controller_probe_rerun.py/json`，主控原件未动）；
  新增单测 `test_r3_correction_needs_own_affirmative_statement`、
  `test_r3_background_preserved_against_foreign_or_negated_clear`，
  新增路由测试 3 例（真实临时库+精确 question_id，均核对接口回答与
  **落库回答逐字一致**）；连续讨论两套测试 **46 passed**。

### G3 纠错（本报告文案）

1. §6 提交清单：区分**实施提交**（`e461d838`，产品实现）与**交付提交**
   （纯文档证据；round=1 实际交付 `f4e8c960`，曾误写 `25926877`——amend
   漂移，已作废并记录教训：交付哈希以分支顶 `git log` 现查为准）。
2. §6 运行目录差异：删去「运行目录落后于本分支、采用即以本分支为准」的
   可覆盖推论，改为「差异待定向核对（运行目录存在并行因子改动）」。
3. §3/§5 「144 项全量回归」改为「13 文件相关回归（非全仓测试）」。

## 9. 四轮补修（主控二轮复核 round=3，本轮为最后一次执行轮）

主控第二轮复核（失败证据 `raw/controller-zcode-continuity-r2-2026-09-17/`，
原样保留）证实 round=2 的三处整句级守卫在**一句多事**时互相误伤。本轮不改
关键词表、不扩功能，只把判断单位从整句改为**分句**（`resolve.py` 新增
`_clause_spans`/`_own_clause` 共用结构；`agentUx.ts` 逐动作核实所在分句）：

| 主控点名输入 | 修前错误 | 修后行为 | 证据 |
|---|---|---|---|
| 先解释ATR止损，不用比较，直接帮我回测 | 放行 | 拦截「ATR 止损」 | 前端回归 + 两入口浏览器链 |
| 朋友还持有，但我已经清仓了 | holding 仍 true | 本人清仓生效 | 单测+路由测试+主控探针复跑 |
| 我没有闲钱，这是每月工资定投 | purpose 仍 spare_cash | income_dca，旧闲钱撤销 | 单测+路由测试+主控探针复跑 |
| 我没清仓，朋友清仓了 | —（矩阵要求保持） | 保留本人持仓 | 单测 |
| 朋友有闲钱，我每月工资定投 | —（矩阵要求） | income_dca（第三人闲钱不提取） | 单测 |
| 不用比较，也不回测，ATR止损是什么意思 | —（矩阵要求） | 纯概念放行 | 前端回归 |

- **G1**（`web/src/utils/agentUx.ts`）：`hasAffirmativeExec` 对每个执行动作
  匹配项取其**所在分句**，仅在分句内紧邻否定时视为否定；任一动作未否定即
  拦截。概念词只保护「全部动作被否定/纯概念」的问法。草稿、真实证券 ATR
  识别、两入口共用函数未动。
- **G2**（`src/lei_signal/copilot/resolve.py`）：撤销（`detect_fact_correction`）
  与用途（`parse_request` 用途段）改为逐分句——只从本人、肯定的分句提取；
  第三人/假设分句不清本人、也不阻止同句其他分句的本人更新；被否定的用途词
  不建立该用途（`_establish_purpose` + `_PURPOSE_NEG_TAIL_RE`）；金额守卫
  （`_budget_guard_ok`）同样改按金额所在分句核归属（「朋友有一万，我五千」
  的五千是本人事实）。同一套分句/归属结构供当前请求与历史背景
  （`_user_background` 逐条重新推导）消费，不再各用一套整句守卫。
- **验证**：连续讨论两套测试 **50 passed**（46+4 新增：分句矩阵单测、
  真实绑定链背景单测、2 个路由级组合场景含材料/落库一致性）；
  主控 mixed 探针修后复跑两查全过（`controller_mixed_rerun.py/json`）、
  ATR 混合复跑 4 例全过（`atr_mixed_rerun.mjs` + `atr-mixed-rerun-results.json`，
  含两动作都否定的概念问法）——主控原件未动。
- **两入口浏览器链**（`ui_atr_clause_chain.py` + notes/requests + 截图 4 张）：
  分句混合问法两入口均拦截、零非 GET backtest 流量、无补测任务卡、工作台
  上下文保持通信ETF；纯概念两入口正常讨论（工作台新答案卡+后端请求，
  控制台轮数净增+新请求 200）。

## ARCHIVE

category：数据与质量；verdict：mixed（round=1 复验 e461d838 两项收口成立；
round=2 修概念放行/本人肯定边界/文案；round=3（最后一轮）按主控二轮复核的
共同根因把否定与归属判断改为**分句级**：一句多事不再互相误伤——先否定比较
再肯定回测仍拦截、同句第三人描述不挡本人清仓、否定闲钱后本人定投用途生效；
50 项连续讨论测试+13 文件相关回归与 1 项已知 xfail 边界一致，两入口浏览器
链页面+请求证据齐全；合入仍待主控复验裁决）。判定层、资金纪律、模型配置
未动；未新增交易/因子能力；不代表收益提升；未部署、未合 main、未写真实库
与运行目录；主控两轮失败证据均原样保留。局部测试通过不代表冻结目标整体
关闭，最终以主控独立复核为准。
