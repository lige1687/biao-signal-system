# 意图路由扩展（定投/情绪/认知）S1 只读核实与方案冻结 — 2026-09-19

> 状态：S1 阶段交付（只读核实，**零产品代码改动**）。S2 实现、测试与生产采用
> 另行授权。本文是分派链路审计与用例矩阵冻结；逐条命令与原始输出见同名 raw：
> `docs/experiments/raw/agent-intent-routing-audit-2026-09-19/`。

## 一句话结论（大白话）

把系统现在「听懂用户一句话该干什么」的路由表从头到尾核对了一遍，并按运行中的
服务实测：老的五类快捷指令（报单、机会扫描、推荐、持仓、复盘）都正常；要新增的
三类里，**情绪解说模块是现成的、可以直接接**；**定投的计算和数据都齐了，但对外
的接口从未被接上**（运行中的服务里根本查不到定投接口，此前以为已上线是误报——
一个返回 200 的假象其实是前端页面兜底页，不是接口）；**心态/认知类只有话题骨架、
没有内容库**，本次确认缺位。方案据此冻结：定投直达定投数据服务出卡、情绪直达
情绪解说模块、认知识别后明说「内容库还没建」并转回普通聊天，转回原因可观察。
测试用例矩阵（含旧功能回归、反例、交叉说法、连续对话、名称绑定）已定稿待 S2 实现。

---

## 1. 核对范围与工作区身份（G1 验收项）

- 可写工作区：`/Users/yongbiaoli/lei-agent-runtime-adoption-20260917`，
  分支 `codex/agent-runtime-adoption-20260917`，
  HEAD = `267a7afb62045fb6d1dd279e3f32e0e0bceab4e1`（= 简报声明 267a7afb，一致）。
- 运行仓（只读）：`/Users/yongbiaoli/Desktop/lei-signal-lab`。运行服务进程
  （pid 99297，cwd=运行仓根）命令行为
  `python -m uvicorn lei_signal.api.app:app --host 0.0.0.0 --port 8000`，
  即生产服务就是运行仓的 `create_app` 产物。
- **候选分支=已采用运行实态的核对**：对 10 个关键文件（intent.py、
  routes/copilot.py、resolve.py、routes/dca.py、copilot/sentiment.py、
  routes/sentiment.py、app.py 及三个回归测试文件）做两仓逐字节 `diff`，
  全部 SAME（raw §1）。运行仓工作区另有若干 docs 侧未提交改动，均非产品代码。
  结论：**候选仓源码 = 正在生产运行的代码**，S1 所有行号结论对两者同时成立。

## 2. 分派链路四列表（规则 → 分派点 → 下游 → 就绪度）

先说清这套机制（大白话）：用户在快捷入口说一句话，`parse_intent`
（`src/lei_signal/copilot/intent.py:38-43`）按一张**按顺序匹配的关键词表**
（`_INTENT_RULES`，`intent.py:17-23`）判断意图，命中哪类就走哪条现成流水线出卡片；
一个都不命中就回落到「通用讨论」（`chat`，由前端转 `/api/agent/chat`）。
匹配就是简单的是「包含这个词」判断，没有否定语义——这是该层的既有定位
（`intent.py:1-7` 自述 best-effort 快捷方式），精细的理解归讨论入口的另一套
解析器（`copilot/resolve.py`）。

| 意图 kind | 规则（intent.py:行号 → 关键词） | 分派点（routes/copilot.py） | 下游能力 | 就绪度（以运行实况为准） |
|---|---|---|---|---|
| trade_report 报单 | :18 → 买了/卖了/申购/赎回/报单/下单了/成交了 | :242-248 | `parse_trade_report`（intent.py:103-129）→ 报单预览卡 → 用户确认后入 fund_trades 台账 | ✅ 就绪（生产在用） |
| scout 机会扫描 | :19 → 最近机会/看看机会/发掘机会/机会扫描/扫扫机会 | :206-230 | `copilot/scout.py::scout` → 趋势/埋伏/情绪三段机会卡 | ✅ 就绪 |
| recommend 推荐 | :20 → 今天看什么/推荐/有什么机会/扫一下自选/标的雷达 | :231-241 | `_recommend_card`（copilot.py:92）+ 推荐留痕 journal | ✅ 就绪 |
| holdings 持仓 | :21 → 持仓/我的仓位/持仓速览 | :249-279 | 计划表（armed/entered）+ 基金持仓汇总（含净值核算） | ✅ 就绪 |
| review 复盘 | :22 → 复盘/周报/这周做得怎么样 | :280-293 | 周报读取/生成（`copilot/review.py`） | ✅ 就绪 |
| chat 未命中回落 | — | :294-299 | `chat_fallback=true` → 前端转 `/api/agent/chat` | ✅ 就绪 |
| **dca 定投（新增）** | 无 | 无 | **服务层就绪**：`src/lei_signal/dca/{service,state,presets}.py` + `configs/dca_evidence.json`（git 已跟踪）；讨论路径已直连服务出材料（agent.py:1908-1962）。**REST 未挂载**：`routes/dca.py` 定义了 `/api/dca` 前缀 6 路径 7 操作（dca.py:35；174/193/235/249/266/289/301），但 `app.py:114 create_app` 的 22 个 `include_router`（:145-162）里没有它，测试目录也无挂载；dca.py 自入库（1d431137 治理快照）后无挂载动作 | ⚠️ **部分就绪：服务层数据可用；对外 REST 入口未挂载（与简报前提不符，见 §3）** |
| **sentiment 情绪（新增）** | 无（resolve.py:52 话题层有同词表） | 无 | `copilot/sentiment.py` 只叙事标注模块（:3-5 红线原文「永不硬过滤信号、不参与技术判定」；:42 板块热度包 / :95 标的索引 / :122 单标的叙事 / :131 两融环境）；REST `/api/sentiment/*` 7 路径运行中（OpenAPI 实证）；scout 卡已嵌情绪段（scout.py:96-149） | ✅ 就绪（只叙事） |
| **mindset 认知/心态（新增）** | 无（resolve.py:53 话题层有同词表） | 无（agent.py:1998-2001 讨论侧话题块返回 available=False + 引用边界说明） | **种子库缺位**：`configs/mindset_seed.json` 候选仓、运行仓**均不存在**；`src/` 零文件引用，仅有话题骨架（resolve.py:21,53、semantic_states.py:82、agent.py:1904,1998） | ❌ **缺位（本次确认）→ S2 显式回落通用讨论并留回落原因** |

### 2.1 简报提醒项核实

`agent.py` 的 `outcome.kind`（:2476-:3088 出现）取值为
replay/incomplete/resume/proceed，是流式会话的续跑状态，与意图路由无关——
简报「勿混淆」提醒核实无误，本次改动不触碰。

### 2.2 两套解析器边界（S2 红线）

`copilot/resolve.py`（服务 `/api/copilot/resolve`，copilot.py:649，供 agent 讨论入口）
是另一套更细的解析器：意图+主题+资金用途+澄清，带否定/假设/分句守卫。
其 `_TOPIC_RULES`（resolve.py:44-57）已有 dca/sentiment/mindset **话题级**识别。
本次合同**只动 `intent.py` 的 dispatch 快捷层**，不改 resolve.py 及其既有回归
（test_discussion_backtest_03b、test_agent_context_contract、
test_agent_continuity_20260916）。

## 3. 关键发现：DCA REST 入口未挂载（纠正简报前提，待主控裁决）

简报前提「定投=/api/dca/* 六端点已在运行仓」经运行实况核实**不成立**：

1. 运行中服务 OpenAPI 共 121 条路径，**零条** `/api/dca`（对照组：
   `/api/copilot/dispatch`、`/api/copilot/resolve`、`/api/sentiment/*`、
   `/api/agent/chat` 全部在线）——raw §4.1。
2. **易假阳性点**：`GET /api/dca/state` 返回 HTTP 200，但响应体是前端
   `index.html`（app.py:178-187 的 SPA 静态兜底：未命中 API 的 GET 一律回
   首页）。**判定端点就绪必须看 OpenAPI/响应体，不能只看状态码**——raw §4.2。
3. 全仓仅 app.py 一处 `include_router`，其中无 `dca.router`；前端 `web/`
   从未调用 `/api/dca`（grep 零命中）。

**对 S2 的影响与冻结建议**：dca 意图的直达目标不能是调用 `/api/dca/*` REST。
冻结方案：**直达 `lei_signal.dca` 服务层只读适配器出卡**（证据账本可用性 +
宽度状态板，请求带 symbol 则附该标的逐状态；先例 agent.py:1908-1962 已在生产
同路径运行）。「是否补一行挂载把 REST 放出来」超出本合同最小改动边界，
**留主控另行裁决，S2 不自行挂载**。

## 4. S2 实现方案冻结（现有结构内最小改动）

1. **词表追加**（intent.py `_INTENT_RULES` 尾部追加，旧五类原序原词不动）：
   `dca=("定投","分批投")`、`sentiment=("情绪","冰点","强热","恐慌","热警报","散户")`、
   `mindset=("心态","拿不住","怕跌","慌","睡不着")`。
   - 优先级规则：**旧五类在前（追加式扩展，旧行为零回归由构造保证）；
     新三类依次 dca→sentiment→mindset**。sentiment 先于 mindset 与
     resolve.py:52-53 自身顺序一致。
   - dca 词表**刻意窄于** resolve.py:51（不含 闲钱/每月/工资/新收入）：这些是
     资金用途词汇，归讨论入口处理；进 dispatch 粗粒度层会误劫持
     （例：「每月复盘」撞「每月」、「工资到账怎么安排」不是查定投状态板）。
     该偏差写入 intent.py 文档字符串。
   - sentiment/mindset 词表与 resolve.py:52-53 **逐字一致**：同一句话在两个
     入口识别方向相同。
2. **dca 分支**：dispatch 新增分支，调 dca 服务层只读适配器出定投状态卡；
   卡片只读、零下单零记账（实际买卖仍走 trade_report 确认台账）；数据缺席
   如实标注（沿 dca.py/agent.py「缺席如实，不硬凑」先例）。
3. **sentiment 分支**：调 `copilot/sentiment.py` 出只叙事情绪卡
   （板块热度包+两融环境，带 symbol 时加单标的叙事）；note_cn 带只叙事红线
   措辞，**永不硬过滤、不参与技术判定**。
4. **mindset 显式回落**：`Intent` 数据类追加带默认字段
   `fallback_reason: str | None = None`；parse_intent 对 mindset 类返回
   `kind="mindset"` + `fallback_reason="mindset_seed_missing"`；dispatch 回落
   分支（copilot.py:294-299）据此返回 `intent="chat"`、`chat_fallback=true`、
   回显 `fallback_reason`，note_cn 说明「心态内容库尚未建立，已转通用讨论」。
   `CopilotDispatchReply`（schemas.py:1166-1174）同名追加带默认字段（非破坏）。
   **不改语义状态校验任何逻辑**。
5. **文档化**：以上优先级与回落规则写入 intent.py 模块 docstring/注释。

## 5. 用例矩阵（冻结；机读版见 raw/case-matrix.json）

断言层级说明：`unit`=parse_intent 纯函数；`route`=TestClient 打
`/api/copilot/dispatch` 看**回包结构**（intent/chat_fallback/card.card_type/
fallback_reason），**不凭回答正文判定**；`regression`=既有文件全量复跑。
「改前实况」列在 HEAD 267a7afb 实测/由规则表推出。

### 5.1 旧五类回归（期望不变）

| # | 输入样例 | 改前实况 | S2 后期望 | 层级 |
|---|---|---|---|---|
| A1 | 今天看什么 | recommend | recommend | unit+route |
| A2 | 有什么推荐 | recommend | recommend | unit |
| A3 | 看下我的持仓 | holdings | holdings | unit |
| A4 | 持仓速览 | holdings | holdings（card_type=holdings） | unit+route |
| A5 | 我昨天买了1万515880 | trade_report | trade_report（preview.fund_code=515880, amount=10000） | unit+route |
| A6 | 卖了5000块纳斯达克基金 | trade_report | trade_report | unit |
| A7 | 本周复盘 | review | review | unit |
| A8 | 最近机会 | scout | scout | unit |
| A9 | 515880 这个买点为什么是买点 | chat | chat（不带新回落原因） | unit |
| A10 | 市场环境怎么样 | chat | chat，`fallback_reason` 为空（不含新词表词） | unit+route |

### 5.2 新三类正向

| # | 输入样例 | 改前实况 | S2 后期望 | 层级 |
|---|---|---|---|---|
| B1 | 现在能定投吗 | chat | **dca**（简报指定交叉用例；card_type=dca、非回落） | unit+route |
| B2 | 这个ETF适合定投吗 | chat | dca（带 symbol 时卡片含该标的逐状态） | unit |
| B3 | 开始分批投沪深300 | chat | dca | unit |
| B4 | 市场情绪怎么样 | chat | **sentiment**（card_type=sentiment、非回落） | unit+route |
| B5 | 市场恐慌了吗 | chat | sentiment | unit |
| B6 | 现在散户热不热 | chat | sentiment | unit |
| B7 | 最近拿不住怎么办 | chat | 识别 mindset → **显式回落 chat**：chat_fallback=true、`fallback_reason="mindset_seed_missing"`、note_cn 含心态说明 | unit+route |
| B8 | 心态崩了 | chat | 同 B7 | unit+route |
| B9 | 跌得睡不着 | chat | unit 层断言 `kind=="mindset"` 且 fallback_reason 非空（识别成功，回落发生在 dispatch 层——两层职责分开可观察） | unit |

### 5.3 否定用例（不得命中新三类）

| # | 输入样例 | S2 后期望 | 说明 |
|---|---|---|---|
| C1 | 设置提醒 | chat | 无任何词表词 |
| C2 | 今天大盘为什么跌 | chat | 「跌」非词表词 |
| C3 | 换一种止损方式 | chat | 止损属退出方式词汇（resolve.py 层），不入 dispatch 词表 |
| C4 | 每月复盘一次 | review | 「每月」不在 dca 窄词表（冻结设计）；review 前位优先 |
| C5 | 这只基金规模多大 | chat | 「基金」非词表词 |
| C6 | 工资到账了怎么安排 | chat | 「工资」不在 dca 窄词表（资金用途词汇归 agent 入口） |

### 5.4 交叉意图（优先级可观察）

| # | 输入样例 | S2 后期望 | 优先级依据 |
|---|---|---|---|
| D1 | 推荐个适合定投的ETF | recommend | 旧五类前位（追加式扩展构造性质） |
| D2 | 我昨天申购了定投500元515880 | trade_report（preview=515880） | 成交词优先（intent.py:16 既有口径） |
| D3 | 市场情绪恐慌，看下我的持仓 | holdings | 「持仓」旧五类前位 |
| D4 | 情绪不好，睡不着 | sentiment | 已知取舍：sentiment 先于 mindset（与 resolve.py 同序）；「情绪」兼有市场/心情两义，双方落点均只叙事，误向代价低——**列观察项** |
| D5 | 别定投了，风险太大 | dca | **已知局限**：本层无否定处理（与「别买了」今日即命中 trade_report 同一既有局限）；否定/假设精细处理归 resolve.py，本合同不复制（红线：最小改动）——**列观察项** |

### 5.5 连续讨论

| # | 输入序列 | S2 后期望 | 边界 |
|---|---|---|---|
| E1 | 「现在能定投吗」→「515880 呢」→「买了1万515880」 | dca / chat / trade_report 逐条独立 | parse_intent 纯函数无跨消息状态；上下文承接归 agent 入口（resolve.py context_scope）。连发三条逐条断言，证明 dispatch 无隐藏会话态 |

### 5.6 名称绑定回归

| # | 对象 | 基线（2026-09-19 实测） | S2 后期望 |
|---|---|---|---|
| F1 | `tests/unit/test_agent_name_resolve.py` 全文件 | 10 passed | 10 passed（agent 入口名称绑定与 intent.py 无共享代码，不得破坏） |
| F2 | dispatch 新三类对 agent 入口的影响 | 无 | 零影响（不触 resolve.py/agent.py）；如需轨迹证据沿既有禁网隔离 before/after 法（先例 agent-glm-symbol-binding-fix-2026-09-18） |

### 5.7 入口级轨迹断言（route 层最低集合）

S2 测试须含：B1（dca 直达）、B4（sentiment 直达）、B7（mindset 显式回落且
`fallback_reason` 可观察）、A5（旧报单回归）、A10（旧 chat 回归且无回落原因）、
E1（连续三条无状态）。全部断言回包结构字段，不判回答正文。

## 6. 回归基线（S2 前后对照）

```
python3 -m pytest tests/unit/test_copilot_intent.py \
  tests/unit/test_copilot_dispatch.py tests/unit/test_agent_name_resolve.py -v
→ 24 passed in 12.81s（2026-09-19，HEAD 267a7afb，离线临时库，禁网）
```

S2 完成后同命令须保持 24 passed，新增用例另计。

## 7. 已知局限与红线确认

- **无否定语义**（既有层定位）：D5 类输入本层照命中；精细处理归 resolve.py，
  本合同不扩。两处已知取舍（D4 情绪/心态同现、D5 否定）列观察项，主控可改判。
- **只叙事红线**：sentiment/mindset 落点均为叙事标注，永不硬过滤、不参与
  技术判定（AGENTS.md 体系红线；sentiment.py:3-5 模块原文同旨）。
- **不触碰**：resolve.py 及其回归、agent.py（含 outcome.kind、语义状态校验）、
  `/api/dca` 路由挂载与否（留主控）、种子库接入、页面改版、真实模型评测。
- dispatch 快捷层与讨论入口（resolve/agent）词表方向一致性是设计目标；
  两层粒度不同（粗快捷 vs 细守卫），差异已逐条文档化（§4.1）。

## 8. S1 改动清单

新增纯文档三件：本审计、`raw/evidence-2026-09-19.txt`（逐命令原始输出）、
`raw/case-matrix.json`（机读矩阵）；增量登记 `registry.json` +1 条目、
`INDEX.md` §1 +1 行。`src/`、`web/`、`configs/`、`tests/` **零改动**。
未跟踪的 `docs/archive/handoffs-plans/agent-intent-routing-20260919/` 为主控
交接材料，保持原样不入本提交。

---

## ARCHIVE

- 结案时间：2026-09-19（S1 阶段；整体任务待 S2 与主控独立复核）
- 执行：ZCode（GLM-5.3 Flash），job 09e2707a stage=S1 attempt=initial
- 工作区 HEAD：267a7afb（分支 codex/agent-runtime-adoption-20260917）
- raw 对照：`docs/experiments/raw/agent-intent-routing-audit-2026-09-19/`
- 验收对照：G1 三条验收逐项落位——四列表见 §2（行号可对照源码）；
  用例矩阵见 §5（六组覆盖+具体样例+期望）；HEAD 与运行实态核对见 §1；
  本阶段零产品代码改动见 §8。
- 未解决问题（移交 S2/主控）：① DCA REST 未挂载与简报前提不符，挂载与否待
  裁决；② D4/D5 两处词表层已知取舍待主控认可或改判。
