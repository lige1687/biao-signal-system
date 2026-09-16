# LEI 看盘系统 -- AI 监督员 Agent 层 · 计划制定交接 prompt

> 本文件自包含。接手 AI 无需任何对话上下文，读完本文件 + 项目内 `docs/trading-spec-v1.md`（交易规格）、`docs/handoff-prompt-round1.md`（round1 交接）、`docs/trading-spec-audit.md`（对账）即可制定计划。
>
> **你的任务**：为 LEI 系统的 AI 监督员 agent 层制定一份**详细实施计划**（不是直接写代码）。计划要覆盖 v1 最小形态的范围、数据流、红线执行机制、与现有系统的集成方式、验收标准、以及 v2+ 路线。制定过程中可读取项目代码理解现有模式。

## 0. 你的角色

你是 LEI 单一标的技术交易系统的架构师。系统已有一个**确定性的规则引擎**（YAML 规则账本 + 前向状态机 + 回测 + API + React），现在要在其之上加一层 **AI 监督员 agent**。你的产出是一份**计划**，交由人类确认后再实现。

**铁律**：先读 `docs/trading-spec-v1.md` 理解交易体系与四条红线，再读本 prompt 的 agent 边界。规格第 17 节参数未经人类确认不得擅自优化。

## 1. 系统背景与定位

- **系统性质**：单一标的技术分析 + 入场/失效/止盈/持仓状态的研究/回测化系统。**绝不包含下单、仓位、账户资金接口**（代码中不得出现 place_order/AccountState/position_size 等执行域符号）。
- **核心哲学**（规格第 2 节）：价量时空；先判断道路（均线方向）再观察路牌（顶底构造）；什么逻辑进场就什么逻辑退出。
- **项目路径**：`/Users/yongbiaoli/Desktop/lei-signal-lab`，git 分支 `recovery/lei-round2`，ruleset `1.3.0`。

## 2. 四条红线（agent 层必须遵守，不得突破）

1. **无未来泄漏**：第 t 根 K 线收盘后生成的信号最早 t+1 开盘执行；摆动点/结构/枢轴点必须确认后才能用；周线信号只能当周最后交易日收盘后用。
2. **research_proxy 标注**：源自交易笔记而非作者原话的规则，provenance 必须标 `research_proxy`，界面/agent 输出必须标注"研究代理"，不得冒充 LEI 原始规则。
3. **不擅自优化参数**：规格第 17 节参数表中的数值，未确认前用合理默认并在规则 note 标注"待确认"，不得回测调参后宣称是作者标准。
4. **模块分别统计**：四个交易模块（A/B/C/D）必须分别回测，趋势跟随与逆势反转不得在同一笔交易中相互改写理由（规格第 12 节）。

## 3. 系统架构与现有确定性输出（agent 要读这些，不要重算）

技术栈：Python 3.11 / FastAPI / pandas / Pydantic 后端；React + Vite + TS 前端。测试 `/opt/homebrew/bin/python3 -m pytest -q`，lint `ruff check src`、`mypy src`，前端 `npm --prefix web run build`。

关键入口与产物（agent 应基于这些已有确定性输出，**不得自行从行情探测信号**）：

- `src/lei_signal/compose/pipeline.py::analyze(symbol)` / `analyze_bars(...)` → `AnalysisResult`（frame、events、structures、pivots、assessment、b1、profile）。
- `src/lei_signal/api/routes/symbols.py::_detail_dto` → `SymbolDetailDTO`，含：
  - `assessment`：颜色/阶段/风险状态/支持冲突因素/风险提示/`trade_opportunities`/`pullback_opportunities`/`conditional_scenarios`/`exit_signals`/`tradability`
  - `recent_events` / `new_events`：带 `rule_id`、`provenance`、`evidence`、`invalidation` 的客观事件
  - `live_structures` / `closed_structures`：底部/顶部结构（C 点、颈线、失效）
  - `scenario_backtests`：按规则/模块/盈亏比分桶的回测
  - `concepts`：概念术语解释
- 规则账本 `configs/rules.v1.yaml`（所有阈值集中于此，代码不写死）。规则通过 `get_rule(rule_id)` 读取。
- 事件确定性 ID：`make_event_id(rule_id, rule_version, symbol, timeframe, available_date, source_id)`，同数据同规则必产生同 ID。

### Round 1 已交付（ruleset 1.3.0，全门禁通过）

| 模块 | 产物 | 对 agent 的意义 |
|---|---|---|
| 抵扣价退出 `exit_ema20_costbasis`（A6①） | 退出触发事件 + A6 三版本退出回测 | agent 提醒"持仓触发退出，明天该出" |
| 盈亏比 `reward_risk_filter`（只算不强制） | `compute_reward_risk`：目标B优先级(摆动高点>筹码峰>区间)+"目标不可计算" | agent 标注"这笔 R/R=X，<3 提示但不拦" |
| 可交易性门禁 `tradability_gate` | 趋势类型分类(横盘反复/横盘末期/趋势/加速衰竭)+9条无交易条件 | agent 拦"环境阻断，按规则不该开仓" |
| 模块分别统计 `module_backtest` | A/B/C/D 分桶 + 趋势跟随/逆势反转汇总 | agent 不混笔讲理由 |
| 做空镜像骨架 `false_breakout_reclaim_short` | direction=short 事件骨架 | agent 支持双向 |

仍缺：买入模块 B（密集区突破）、C（2B/破底翻）待第二轮实现；`MODULE_MAP` 已预留。

## 4. 用户对 agent 的愿景（这是设计的核心约束）

用户原话："通过和 agent 聊天，agent 帮我制定计划，然后计划通过系统提醒我啥时候买入啥时候卖出，最终实现监督我完成系统规律的事情。agent 解读买点卖点是附带功能。"

**核心角色 = 纪律监督员 + 计划执行提醒，不是探测器。** agent 监督**用户**去服从确定性系统，不替代系统。它不探测、不调参、不输出不透明总分，只对照确定性层已算出的条件提醒执行、拦临时改主意（规格第 14 节：亏损后不得更换入场理由移动失效价——这正是 agent 该拦的）。

**关键边界**：agent 能否监督好，取决于确定性层能否可靠算出"该监督的条件"。Round 1 已把这些条件铺了一大半（退出/可交易性/盈亏比/模块分桶）。所以现在可以启动 agent 最小形态，B/C 模块之后增量加，agent 覆盖面跟着长。

## 5. agent 的边界（红线可执行化）

- **只读确定性输出，不重算信号**：agent 只消费 `AnalysisResult`/`SymbolDetailDTO`，不得从行情直接探测买卖点。
- **接地生成**：任何结论必须能追溯到 `rule_id` + `evidence` 数值；DTO 里没有的事实一律不准说。每条建议带溯源标签（如 `[rule_id:exit_ema20_costbasis | 证据:close<ema20,close<close_lag20]`）。
- **research_proxy 必须标注"研究代理"**，不得冒充 LEI 原始规则。
- **禁止输出买/卖指令**、禁止调参、禁止给不透明总分（系统已禁 `score/total_score/rating`）。agent 输出"参考/提醒/阻断原因"，不是"买入/卖出"。
- **模块 A/B/C/D 分开讲**，趋势跟随与逆势反转不得互相改写理由（规格 12）。
- **遇到规格第 17 节参数决策点，停下来列待确认表等人类确认**，不擅自定值。
- **拦临时改主意**：持仓亏损后用户想移动失效价/换入场理由时，agent 必须按规格第 14 节拦阻并说明。

## 6. 待你决策/推荐的设计点

1. **数据获取方式**（用户未定，请你推荐）：agent 拿数据的回退策略——
   - (a) 实时调 `analyze(symbol)` 拉腾讯行情（最贴近真实监督，需网络、有延迟）；
   - (b) 实时优先，失败/无网读 `tests/` fixture parquet（离线回放，稳健但数据陈旧）；
   - (c) 只用 fixture（纯离线，快，但不能监督当下）。
   给出推荐与理由。
2. **agent 载体形态**：Claude Code skill（`.claude/skills/...`，用户分析时调）vs 后端 `/explain` 端点（产品内嵌，服务端调 LLM）vs 两者。用户倾向先做 skill（轻、不碰产品代码、先把"接地生成"约束打磨稳）。请评估并推荐 v1 形态。
3. **LLM 运行时**：项目用火山引擎 ark（非 DeepSeek），通过 gitignored `.env`/`.env.local`。若涉及后端 LLM 调用，走 ark。
4. **v1 范围**：最小形态建议 = 监督员+讲解员（给定标的当前确定性状态，输出"该不该动/为什么/失效在哪/下一步观察什么"+拦临时改主意）。计划制定 = 定下 v1 做什么、不做什么；"计划制定+定时提醒"放 v2+。请确认或调整。

## 7. 要求产出的计划内容

计划文档应包含：

1. **v1 目标与非目标**：一句话目标 + 明确不做什么（不下单、不探测、不调参）。
2. **数据流**：agent 如何拿到 `AnalysisResult`/DTO（含数据获取回退策略的最终推荐）、传给 LLM 的上下文结构（哪些字段、如何裁剪避免超 context）、LLM 输出格式。
3. **红线执行机制**：四条红线 + agent 边界如何变成可执行约束（system prompt / skill 指令 / 后处理校验）。重点说明"接地生成"如何强制（溯源标签 + 校验 DTO 里是否存在被引述的 rule_id/evidence）。
4. **与现有系统集成**：复用哪些已有函数/DTO，新增哪些文件（skill 文件 / helper 脚本 / 可选端点），不破坏现有只追加事件日志与确定性不变量。
5. **监督员的核心能力清单**：基于 round1 已有输出，列出 v1 能监督/提醒/拦阻的具体场景（如：可交易性阻断时拦开仓、退出触发时提醒、R/R<3 时提示、用户想移失效价时拦、模块混笔时纠正）。
6. **验收标准**：可验证的红线守恒测试（如：agent 输出每条结论都能在 DTO 找到 rule_id 溯源；research_proxy 规则输出带"研究代理"；不出现买/卖指令字样；参数决策点会停下）。
7. **v2+ 路线**：计划制定+定时提醒、B/C 模块接入后的覆盖扩展、后端 `/explain` 产品化。
8. **风险**：接地生成漂移、LLM 幻觉、延迟/成本、约束绕过，及对策。

## 8. 参考材料

- 交易规格原文：`docs/trading-spec-v1.md`
- 对账与买卖点整理：`docs/trading-spec-audit.md`
- Round 1 交接（完整任务规格与范式）：`docs/handoff-prompt-round1.md`
- 最完整规则参考实现：`src/lei_signal/rules/first_ma_pullback.py`
- API DTO：`src/lei_signal/api/schemas.py`；路由拼装：`src/lei_signal/api/routes/symbols.py`
- 规则账本：`configs/rules.v1.yaml`（ruleset 1.3.0）
- 真实数据验证已跑通（000001.SS 趋势可交易、000300/510300 趋势不明阻断、R/R 多数可计算、模块 A/D 有样本），非退化。

## 9. 交付方式

输出一份 Markdown 计划文档。遇到规格第 17 节参数决策点或与四条红线冲突的设计，**停下来输出待确认表等人类确认**，不要擅自定值。计划经人类确认后才实现。
