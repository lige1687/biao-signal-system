# LEI 看盘系统——第一轮开发任务交接 prompt

> 本文件是自包含的任务交接指令。接手 AI 无需任何对话上下文，读完本文件 + 项目内 `docs/trading-spec-v1.md`（交易规格原文）+ `docs/trading-spec-audit.md`（对账与买卖点整理）即可动手。

## 0. 你的角色与任务

你是接手 LEI 单一标的技术交易系统的开发者。这是一个**规则型主观趋势交易系统的研究/回测化项目**，不是自动交易系统。你的任务是按本 prompt 的第一轮任务清单，实现 5 个开发项，每个都遵循"YAML 规则账本 + 前向状态机 + 回测 + API DTO + React 面板 + 单测"的完整链路。

**铁律**：先读 `docs/trading-spec-v1.md` 理解交易体系，再读本 prompt 的任务规格。规格第 17 节的参数未经人类确认不得擅自优化数值。

## 1. 项目背景与定位

- **系统性质**：单一标的技术分析 + 入场/失效/止盈/持仓状态的研究系统。**绝不包含下单、仓位、账户资金接口**（代码中不得出现 place_order/AccountState/position_size 等执行域符号）。
- **核心哲学**（规格第 2 节）：价量时空；先判断道路（均线方向）再观察路牌（顶底构造）；什么逻辑进场就什么逻辑退出。
- **四条红线**：
  1. **无未来泄漏**：第 t 根 K 线收盘后生成的信号，最早 t+1 开盘执行；摆动点/结构/枢轴点必须确认后才能用；周线信号只能当周最后交易日收盘后用。
  2. **research_proxy 标注**：源自交易笔记而非作者原话的规则，provenance 必须标 `research_proxy`，界面必须标注"研究代理"，不得冒充 LEI 原始规则。
  3. **不擅自优化参数**：规格第 17 节参数表中的数值，未确认前用合理默认并在规则 note 标注"待确认"，不得回测调参后宣称是作者标准。
  4. **模块分别统计**：四个交易模块（A/B/C/D）必须分别回测，趋势跟随与逆势反转不得在同一笔交易中相互改写理由（规格第 12 节）。

## 2. 技术栈与运行方式

- **后端**：Python 3.11 / FastAPI / pandas / Pydantic。包管理 `pip install -e '.[dev,api]'`。
- **前端**：React + Vite + TypeScript + React Query + ECharts。在 `web/` 下，`npm install && npm run build`。
- **测试**：`/opt/homebrew/bin/python3 -m pytest -q`（pyproject 已设 `pythonpath=["src"]`，无需 venv）。
- **lint/类型**：`/opt/homebrew/bin/python3 -m ruff check src`、`/opt/homebrew/bin/python3 -m mypy src`。
- **启动**：后端 `PYTHONPATH=src python -m lei_signal.api`（127.0.0.1:8000）；前端 `npm --prefix web run dev`（localhost:5173，代理 /api→8000）。
- **项目路径**：`/Users/yongbiaoli/Desktop/lei-signal-lab`，git 分支 `recovery/lei-round2`。

## 3. 项目结构（关键路径）

```
lei-signal-lab/
├── configs/rules.v1.yaml          # 规则账本（最高优先级，所有阈值集中于此，代码不写死）
├── docs/
│   ├── trading-spec-v1.md         # 交易规格原文（规则最高溯源依据）
│   └── trading-spec-audit.md      # 规格↔系统对账 + 买卖点整理 + 参数表 + 路线图
├── src/lei_signal/
│   ├── features/indicators.py     # compute_features：sma/ema/atr14/close_lag{20,60,120}
│   ├── domain/
│   │   ├── types.py               # Stage/RiskState/SignalEvent/Direction/Provenance 等
│   │   ├── canonical.py           # make_event_id（确定性 ID）
│   │   └── rules_config.py        # RuleSpec/get_rule/ruleset_version，读 rules.v1.yaml
│   ├── rules/                     # 各规则的前向状态机 detect_*_events 函数
│   │   ├── lei_color.py           # 颜色（绿灰黑）
│   │   ├── first_ma_pullback.py   # ★ P1 范式：首次回撤均线（最完整的参考实现）
│   │   ├── false_breakout_reclaim.py  # P2：假突破收回
│   │   ├── ma_full_alignment.py   # P2：完整排列+斜率加速度
│   │   ├── low_level_confirmation.py  # P2：低级别日线代理确认
│   │   ├── key_wave.py            # 关键波动
│   │   └── resistance_b1.py       # B1 阻力（目标参考）
│   ├── research/                  # 回测
│   │   ├── scenario_backtest_common.py  # ★ 共用回测工具（ScenarioBacktestReport 等）
│   │   ├── outcomes.py            # 前向收益统计
│   │   └── *_backtest.py          # 各规则回测
│   ├── compose/pipeline.py        # analyze_bars：编排 feature→规则→事件→assessment
│   ├── api/
│   │   ├── app.py                 # FastAPI 工厂 create_app
│   │   ├── schemas.py             # Pydantic DTO（AssessmentDTO/SymbolDetailDTO 等）
│   │   ├── routes/symbols.py      # 个股详情路由 + _build_*_dto
│   │   └── explanations.py        # 规则中文解释（title/definition/formula/usage/invalidation）
│   └── data/providers.py          # 腾讯日线 fqkline（仅日线，无 60min）
└── web/src/
    ├── types.ts                   # 前端类型（与 DTO 对应）
    ├── pages/WorkspacePage.tsx    # 主工作台
    ├── components/
    │   ├── TradeOpportunityPanel.tsx       # 买点状态机卡（生命周期+条件+失效锚+回测）
    │   ├── ConditionalScenarioPanel.tsx    # 条件化场景卡
    │   ├── ScenarioBacktestPanel.tsx       # 回测面板
    │   └── ExplanationPanel.tsx            # 点击解释浮层
    └── styles.css
```

## 4. 核心约定（必须遵守）

### 4.1 规则账本范式
所有规则必须在 `configs/rules.v1.yaml` 注册，包含：`rule_id`、`version`、`provenance`（`lei_explicit`/`lei_inferred`/`research_proxy`/`existing_backtest`）、`formula`、`note_cn`、`params`（阈值字典）、`events`（子规则列表）。代码通过 `get_rule(RULE_ID)` 读取，**不在代码中写死阈值**。新增规则时 `ruleset_version` 递增（当前 1.2.0）。

### 4.2 前向状态机范式（参考 first_ma_pullback.py）
每个规则函数签名：`detect_xxx_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]`。
- 用 `_Episode`/`_WatchState` 等 dataclass 维护跨日状态。
- 逐日 `for position, timestamp in enumerate(frame.index)` 推进。
- 任何结论只依赖 `position` 及此前数据；参考位用 `series.shift(1)` 严格前移。
- 事件用 `make_event(...)` 构造，`evidence` 保存成立所用数值，`invalidation` 保存客观失效条件。
- 事件 ID 用 `make_event_id(rule_id, rule_version, symbol, timeframe, available_date, source_id)`，保证确定性（门禁 11）。

### 4.3 回测范式（参考 scenario_backtest_common.py）
- 重叠事件研究口径，**非单账户资金曲线**。固定周期 5/10/20/60/120 日 + 规则退出。
- `ScenarioBacktestReport` 含 `fixed_horizon_stats`（固定周期）和 `rule_exit_stats`（规则退出）。
- 未完成/未平仓样本单独计数，**不进收益统计**。
- 必须带 `RESEARCH_DISCLAIMER`（不计手续费/滑点/涨跌停/停牌）。

### 4.4 API/前端范式
- DTO 在 `api/schemas.py` 定义，路由在 `api/routes/symbols.py` 的 `_build_*_dto` 拼装。
- 中文解释在 `api/explanations.py`（每个 rule_id/sub_rule 一条 title/definition/formula/usage/invalidation/caveat）。
- 前端类型在 `web/src/types.ts`，面板在 `web/src/components/`，接入 `WorkspacePage.tsx`。
- research_proxy 规则在界面必须可见"研究代理"标注。

### 4.5 其他约定
- 上海 A 股符号用 `.SS` 后缀（如 `600519.SS`），`.SH` 会被数据层拒为非 A 股。
- A 股涨用红色、跌用绿色（中国惯例）。
- 不得输出不透明总分（系统已禁 score/total_score/rating）。

## 5. 现有系统现状（ruleset 1.2.0，23 条规则）

已实现：颜色(lei_color)、EMA20转强(ema20_reclaim_rising)、双均线共同确认(dual_ma_bull_confirmed)、双均线开口(dual_ma_spread)、长趋势(long_trend)、摆动点(swing_pivots)、阳/阴线反包及外包反转(4条)、高底/双底/反转底部(3条)、C点生命周期(bottom_c_lifecycle)、顶部结构(top_structure)、关键波动+黑(key_wave_black)、量能代理(volume_proxies)、筹码代理POC/VAL/VAH(volume_profile_proxy)、首次回撤均线(first_ma_pullback)、假突破收回做多(false_breakout_reclaim)、完整排列+斜率加速度(ma_full_alignment)、低级别日线代理(low_level_confirmation)、B1阻力(resistance_b1)。

**已跑通**：模块 A（稳定上升趋势回调）+ 模块 D 做多侧。**8 个缺口**见 `docs/trading-spec-audit.md` 第 4 节。

## 6. 第一轮任务（5 项，已确认方向：先补退出+横切层 / 多空双向 / 盈亏比只算不强制）

### 任务 1：抵扣价退出（规格 A6①）
**背景**：`close_lag{20,60,120}` feature 已存在（= N 周期前收盘，即抵扣价），无需新增 feature。
**要做**：
1. `configs/rules.v1.yaml` 加规则 `exit_ema20_costbasis`，provenance=`research_proxy`，对应规格 A6①。formula：`收盘同时跌破 EMA20 且 跌破 20 日抵扣价(close_lag20)`。
2. `src/lei_signal/rules/exit_ema20_costbasis.py`：实现退出判定函数 `detect_exit_ema20_costbasis_events(frame, symbol)`，前向判定 `close < ema20 and close < close_lag20`，产出退出事件。
3. 回测：作为模块 A 的退出方式之一（A6 三版本：①抵扣价 ②顶构+关键波动 ③结构止损），用 `scenario_backtest_common.py` 分别统计。
4. API：`AssessmentDTO` 加 `exit_signals` 字段或复用现有风险结构；前端买点卡"持仓退出"区展示。
5. 测试：无未来泄漏（追加未来 bars 不改变过去退出点）+ 正常退出用例。

### 任务 2：盈亏比计算（规格第 10 节，只算不强制）
**背景**：`resistance_b1` 已有目标参考；摆动点、密集区代理已有。
**要做**：
1. `configs/rules.v1.yaml` 加规则 `reward_risk_filter`，provenance=`research_proxy`。
2. 实现：入场前用信号时已存在的目标计算 R/R。目标 B 来源优先级：摆动高点/低点 → 未回补缺口 → 均线密集区 → 筹码峰 → 区间另一侧。**无法客观确定 B 时标记"目标不可计算"**，不得事后选最优目标。
3. **只计算展示，不做硬过滤**（已确认）。R/R 值透传到 API/前端展示。
4. 回测：分别统计 R/R≥3 和 R/R≥5 两组表现（追加到回测输出）。
5. 测试：目标 B 只用信号时已存在数据（无未来泄漏）+ "目标不可计算"分支。

### 任务 3：可交易性门禁与趋势类型分类（规格第 13 节 + 第 2.2 节）
**背景**：现有 `Stage` 是机会阶段链，无"趋势类型/可交易性"层。
**要做**：
1. `configs/rules.v1.yaml` 加规则 `tradability_gate`，provenance=`research_proxy`。
2. 趋势类型分类：横盘反复 / 横盘末期 / 趋势 / 加速衰竭。量化建议：均线纠缠度（六线最大最小距离）+ 波动压缩（ATR 分位）+ 斜率。`cluster_threshold`/`minimum_consolidation_bars` 等用默认值并标注"待确认"。
3. 9 条无交易条件清单（规格第 13 节逐条实现）：趋势类型不明、模块不明、入场/目标/失效不能定义、盈亏比<3（注意：当前只算不强制，但门禁仍标注）、横盘无标志动作、极端加速无持仓、多周期杂乱、数据不足、依赖未来 K 线。
4. 作为横切层：输出"可交易性"状态 + 阻断原因清单，接入 assessment。
5. 测试：横盘期阻断、趋势期放行、加速无持仓阻断。

### 任务 4：回测按 A/B/C/D 模块分别统计（规格第 12 节）
**背景**：现有回测按 rule_id 分，未按交易模块分组。
**要做**：
1. 建立模块映射：A=first_ma_pullback/回调类、B=密集突破(待实现)、C=2B破底翻(待实现)、D=false_breakout_reclaim。
2. 改造回测输出：按模块分组统计 + 趋势跟随(A/B) vs 逆势反转(C/D) 分别统计。
3. 不让普通回调信号与 2B 反转信号在同一笔交易中改写理由。
4. 测试：模块归属正确 + 分别统计输出。

### 任务 5：状态机 direction 双向框架（为做空做准备）
**背景**：已确认多空双向。现有 `Direction` 枚举有 BULLISH/BEARISH/NEUTRAL。
**要做**：
1. 事件/DTO/状态机加 `direction=short` 分支骨架（不立即实现具体做空规则）。
2. `false_breakout_reclaim` 预留做空镜像接口（突破压力位拉回 + sma20_slope<0）。
3. 前端买点卡支持做空方向展示（跌用绿色，中国惯例）。
4. 测试：方向字段正确透传。

## 7. 待确认参数表（规格第 17 节，未确认前用默认 + 标注"待确认"）

| 参数 | 现有值/待定 |
|---|---|
| execution_timeframe | 日线 |
| context_timeframe | 周线 |
| direction | 多空双向（已确认） |
| cluster_threshold | 待定（规格参考 ~2%） |
| minimum_consolidation_bars | 待定（规格参考 ~6 个月≈120 交易日） |
| ma_touch_distance | touch_tolerance_pct/atr（已有） |
| swing_confirmation | 左右确认根数（已有） |
| two_b_reclaim_bars | 待定（第二轮） |
| volume_lookback | 已有 |
| volume_threshold | 已有，待优化 |
| gap_definition | 待定 |
| acceleration_definition | 待定（斜率角度区间，建议 ema20_slope_pct 映射） |
| bias_extreme | 待定（规格参考 50%） |
| break_basis | 收盘为主（部分 low 触发） |
| exit_variant | 待定（A6 三版本分别实现） |
| reward_risk_min | 只算不强制（已确认），回测看 ≥3/≥5 |
| fees_and_slippage | 待定 |

## 8. 验收门禁（全部必须通过）

```bash
cd /Users/yongbiaoli/Desktop/lei-signal-lab
/opt/homebrew/bin/python3 -m pytest -q                    # 全绿，无失败
/opt/homebrew/bin/python3 -m ruff check src               # All checks passed
/opt/homebrew/bin/python3 -m mypy src                     # Success: no issues
git diff --check                                          # 干净
npm --prefix web run build                                # tsc + vite build 通过
```

每个新规则必须有：
- [ ] rules.v1.yaml 注册（含 provenance/formula/note_cn/params/events）
- [ ] 前向状态机规则函数（无未来泄漏，追加未来 bars 测试）
- [ ] 回测（固定周期 + 规则退出，带 disclaimer）
- [ ] API DTO + 路由拼装
- [ ] explanations.py 中文解释
- [ ] 前端类型 + 面板 + 接入 WorkspacePage
- [ ] 单测（正常/失效/无未来泄漏）
- [ ] research_proxy 规则界面可见"研究代理"标注

## 9. 交付顺序建议

1. 任务 1（抵扣价退出）→ 任务 2（盈亏比）→ 任务 3（可交易性门禁）→ 任务 4（模块分别统计）→ 任务 5（双向框架）。
2. 每个任务独立提交，独立跑门禁，不要一次性堆所有改动。
3. 遇到规格第 17 节参数决策点，**停下来输出待确认表等人类确认**，不要擅自定数值。

## 10. 参考材料

- 交易规格原文：`docs/trading-spec-v1.md`
- 对账与买卖点整理：`docs/trading-spec-audit.md`
- 最完整参考实现：`src/lei_signal/rules/first_ma_pullback.py`（前向状态机范式）
- 回测共用工具：`src/lei_signal/research/scenario_backtest_common.py`
- 买点卡片范式：`web/src/components/TradeOpportunityPanel.tsx`
- 原始视频材料：见 `docs/trading-spec-v1.md` 第 19 节
