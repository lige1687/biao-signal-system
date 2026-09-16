# 连续讨论补修收口：e461d838 独立复验通过，零产品代码改动结案

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
- 回归：连续讨论两套测试 41 通过；与 cfix2 同口径全量回归（名称/主题/03B/契约/
  stream/copilot_ops/稳定性/重试/e2e + 连续讨论）**144 通过、1 已知 xfail**
  （`tests/integration/test_agent_chat_e2e.py` 校验器百分比派生缺口，
  xfail(strict) 留痕——保持原边界，不是全绿，不隐瞒）。
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
# 全量回归（144 通过、1 已知 xfail）
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
  - `0e5cba80` C1–C3 补修；`ba16af38` docs；`e461d838` 二轮补修（本轮被验对象）
  - `25926877` 本轮收口提交（报告+raw 证据+registry/INDEX 登记+交接归档，
    29 文件纯新增，零产品代码改动）
- **运行目录只读差异清单**
  （`raw/agent-continuity-zcode-closeout-2026-09-17/runtime-dir-readonly-diff.json`，
  运行目录未被写入）：与本分支 11 个关键文件对应的运行目录文件中，
  9 个内容不同（运行目录落后于本分支，采用即以本分支为准）、2 个测试文件运行目录
  不存在（新增）；`configs/`、`src/lei_signal/ui/`、`.env*` 本分支未触碰。
- 台账（升级库）由主控更新，本轮未写共享升级库。

## ARCHIVE

category：数据与质量；verdict：watch（e461d838 两项固定收口经独立复验成立：
两入口 ATR 链页面+请求证据、真实库身份矩阵、41+144 项测试与 1 项已知 xfail
边界一致；整包合入待主控复验裁决）。本轮零产品代码改动；未改判定层、
资金纪律、模型配置；未新增交易/因子能力；不代表收益提升；未部署、未合 main、
未写真实库与运行目录。
