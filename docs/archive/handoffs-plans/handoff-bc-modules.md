# LEI 信号系统 -- 模块 B/C 实现交接 prompt

> 本文件自包含。接手 AI 无需对话上下文，读完本文件 + 项目内 `docs/trading-spec-v1.md`（交易规格原文）+ `docs/trading-spec-audit.md`（对账与买卖点整理）即可动手。
>
> **你的任务**：实现模块 B（均线密集区突破）和模块 C（2B/破底翻反转）的完整链路：YAML 规则账本 + 前向状态机 + 回测 + API DTO + 单测。不碰前端（v1 不要求）。

## 0. 你的角色与任务

你是 LEI 单一标的技术交易系统的开发者。这是一个**规则型主观趋势交易系统的研究/回测化项目**。系统已有模块 A（首次均线回撤）和模块 D（假突破收回）的实现，你要补齐模块 B 和 C。

**铁律**：先读 `docs/trading-spec-v1.md` 理解交易体系，再读本 prompt 的任务规格。规格第 17 节的参数未经人类确认不得擅自优化数值。

## 1. 系统背景与定位

- **系统性质**：单一标的技术分析 + 入场/失效/止盈/持仓状态的研究系统。**绝不包含下单、仓位、账户资金接口**。
- **核心哲学**（规格第 2 节）：价量时空；先判断道路（均线方向）再观察路牌（顶底构造）；什么逻辑进场就什么逻辑退出。
- **四条红线**：
  1. **无未来泄漏**：第 t 根 K 线收盘后生成的信号，最早 t+1 开盘执行。摆动点/结构必须确认后才能用。
  2. **research_proxy 标注**：源自交易笔记而非作者原话的规则，provenance 必须标 `research_proxy`，界面必须标注「研究代理」。
  3. **不擅自优化参数**：规格第 17 节参数表中的数值，未确认前用合理默认并在规则 note 标注「待确认」。
  4. **模块分别统计**：四个交易模块（A/B/C/D）必须分别回测，趋势跟随与逆势反转不得在同一笔交易中相互改写理由。

## 2. 技术栈与运行方式

- **后端**：Python 3.11 / FastAPI / pandas / Pydantic。包管理 `pip install -e '.[dev,api]'`。
- **测试**：`/opt/homebrew/bin/python3 -m pytest -q`（pyproject 已设 `pythonpath=["src"]`，无需 venv）。
- **lint/类型**：`/opt/homebrew/bin/python3 -m ruff check src`、`/opt/homebrew/bin/python3 -m mypy src`。
- **项目路径**：`/Users/yongbiaoli/Desktop/lei-signal-lab`，git 分支 `recovery/lei-round2`，ruleset `1.3.0`。

## 3. 项目结构（关键路径）

```
lei-signal-lab/
├── configs/rules.v1.yaml          # 规则账本（最高优先级，所有阈值集中于此）
├── docs/
│   ├── trading-spec-v1.md         # 交易规格原文
│   └── trading-spec-audit.md      # 规格↔系统对账 + 买卖点整理 + 参数表
├── src/lei_signal/
│   ├── features/indicators.py     # compute_features：sma/ema/atr14/close_lag{20,60,120}
│   ├── features/pivots.py         # confirmed_pivots：三左三右摆动点
│   ├── domain/
│   │   ├── types.py               # Stage/RiskState/SignalEvent/Direction/Provenance
│   │   ├── canonical.py           # make_event_id（确定性 ID）
│   │   └── rules_config.py        # RuleSpec/get_rule/ruleset_version
│   ├── rules/                     # 各规则的前向状态机 detect_*_events 函数
│   │   ├── first_ma_pullback.py   # ★ 模块A参考实现（最完整）
│   │   ├── false_breakout_reclaim.py  # 模块D做多
│   │   ├── false_breakout_reclaim_short.py  # 模块D做空镜像
│   │   ├── ma_full_alignment.py   # 完整均线排列 + 斜率加速度
│   │   ├── tradability_gate.py    # 趋势类型分类（横盘/趋势/加速衰竭）
│   │   └── ...
│   ├── research/                  # 回测
│   │   ├── scenario_backtest_common.py  # ★ 共用回测工具
│   │   ├── module_backtest.py     # ★ 模块映射 A/B/C/D 分桶统计
│   │   └── *_backtest.py          # 各规则回测
│   ├── compose/pipeline.py        # analyze_bars：编排 feature->规则->事件
│   ├── api/
│   │   ├── schemas.py             # Pydantic DTO
│   │   ├── routes/symbols.py      # 个股详情路由 + _build_*_dto
│   │   ├── explanations.py        # 规则中文解释
│   │   └── labels.py              # rule_id/sub_rule 中文标签
│   └── data/providers.py          # 腾讯日线 fqkline
└── tests/unit/                    # 各规则单测
```

## 4. 核心约定（必须遵守）

### 4.1 规则账本范式
所有规则必须在 `configs/rules.v1.yaml` 注册，包含：`rule_id`、`version`、`provenance`（`research_proxy`）、`formula`、`note_cn`、`params`（阈值字典）、`events`（子规则列表）。代码通过 `get_rule(RULE_ID)` 读取，**不在代码中写死阈值**。

### 4.2 前向状态机范式（参考 first_ma_pullback.py）
每个规则函数签名：`detect_xxx_events(frame: pd.DataFrame, symbol: str) -> list[SignalEvent]`。
- 用 `_Episode`/`_WatchState` 等 dataclass 维护跨日状态。
- 逐日 `for position, timestamp in enumerate(frame.index)` 推进。
- 任何结论只依赖 `position` 及此前数据；参考位用 `series.shift(1)` 严格前移。
- 事件用 `make_event(...)` 构造，`evidence` 保存成立所用数值，`invalidation` 保存客观失效条件。
- 事件 ID 用 `make_event_id(rule_id, rule_version, symbol, timeframe, available_date, source_id)`。

### 4.3 回测范式（参考 scenario_backtest_common.py）
- 重叠事件研究口径，**非单账户资金曲线**。固定周期 5/10/20/60/120 日 + 规则退出。
- `ScenarioBacktestReport` 含 `fixed_horizon_stats` 和 `rule_exit_stats`。
- 未完成/未平仓样本单独计数，**不进收益统计**。
- 必须带 `RESEARCH_DISCLAIMER`。

### 4.4 API/前端范式
- DTO 在 `api/schemas.py` 定义，路由在 `api/routes/symbols.py` 的 `_build_*_dto` 拼装。
- 中文解释在 `api/explanations.py`，标签在 `api/labels.py`。
- **前端不碰**（v1 不要求 React 面板）。

### 4.5 模块映射
`src/lei_signal/research/module_backtest.py` 的 `MODULE_MAP` 已预留 B/C（注释状态）：
```python
# "dense_breakout": ("B", "trend_following", "均线密集区突破"),   # 待实现
# "two_b_reversal": ("C", "reversal", "2B/破底翻"),               # 待实现
```
实现后取消注释，`MODULE_NOT_IMPLEMENTED` 对 B/C 自动消失。

## 5. 任务 1：模块 B -- 均线密集区突破（规格 §9 模块 B）

**规格原文**：
> **B1. 环境条件**：横盘阶段不频繁交易，只等待标志性动作。
> **B2. 多头触发**：均线刚形成多头排列时提前观察；或等待价格向上突破密集区；均线依次拐头向上，三线同向时大趋势确认。【回测代理：保守版】下一根 K 线开盘入场。
> **B3. 失效**：若价格重新跌回密集区，同时 20 均线组向下弯曲，突破逻辑失效。

### 可复用的已有基础

| 组件 | 路径 | 用途 |
|---|---|---|
| 横盘判定 | `tradability_gate.py::classify_trend_type` / `_entanglement_series` | 六线纠缠度 + consolidating 判定 |
| 排列判定 | `ma_full_alignment.py::detect_ma_alignment_events` | 完整多头排列（SMA20>SMA60>SMA120 且三线向上） |
| 密集区参数 | `configs/rules.v1.yaml` 的 `tradability_gate.params.cluster_threshold`（0.02，待确认） | 均线密集最大宽度 |
| 回测工具 | `scenario_backtest_common.py` | fixed_horizon_stats / rule_exit_stats |
| 模块映射 | `module_backtest.py::MODULE_MAP` | 取消注释 dense_breakout 行 |

### 实现要求

1. `configs/rules.v1.yaml` 加规则 `dense_breakout`，provenance=`research_proxy`。params 复用 `cluster_threshold`（或独立声明 + 标注待确认）。formula/note_cn/events 齐备。
2. `src/lei_signal/rules/dense_breakout.py`：`detect_dense_breakout_events(frame, symbol)`。
   - **B1 环境**：识别横盘密集区（纠缠度 <= cluster_threshold 持续 >= minimum_consolidation_bars）。复用 `_entanglement_series` 或独立算。横盘期间产 `watch` 事件。
   - **B2 触发**：横盘期间或之后，价格收盘突破密集区上沿（近期 high 或 VAH），且完整多头排列成立（复用 ma_full_alignment 的判定逻辑）。产 `confirmed` 事件。
   - **B3 失效**：价格跌回密集区 + SMA20 方向向下弯曲。产 `failed` 事件。
   - 每个密集区生命周期内只允许一次突破确认（参考 first_ma_pullback 的 consumed 语义）。
3. 回测 `src/lei_signal/research/dense_breakout_backtest.py`：用 `scenario_backtest_common.py`。
4. `compose/pipeline.py`：接入 `detect_dense_breakout_events`。
5. `api/explanations.py` + `api/labels.py`：加规则解释与标签。
6. `module_backtest.py::MODULE_MAP`：取消注释 dense_breakout 行。
7. 测试：无未来泄漏（追加未来 bars 不改变过去事件）+ 正常突破 + 跌回失效 + 非密集区不触发。

## 6. 任务 2：模块 C -- 2B / 破底翻反转（规格 §9 模块 C）

**规格原文**：
> **C1. 结构**：多头 2B：`[原文未提供具体结构定义]`。周线和日线同时出现 2B，属于更高级别验证；大幅负乖离可以作为增强条件，但不能单独触发交易。
> **C2. 入场**：分别测试：1.收盘重新站上 L1 后下一根开盘入场；2.收复 L1 后再等待 EMA20 拐头向上；3.收复 L1 后再等待 EMA20 与 SMA20 共同向上。"快速收复"允许的最大 K 线数量必须作为参数。
> **C3. 失效**：价格重新跌破 L2，2B 逻辑失效。

### L1/L2 结构定义（研究代理量化口径）

规格未提供 2B 的具体结构定义（`[原文未提供]`），以下为**研究代理量化口径**，必须标 `research_proxy`：

```
2B 多头结构（破底翻）：
  1. 价格创低 L2（确认摆动低点，经三左三右确认）；
  2. 反弹；
  3. 再次下探，形成 L1（L1 > L2，即更高低点，也经确认）；
  4. 价格跌破 L1（假跌破 / 破底），但未跌破 L2；
  5. 在 two_b_reclaim_bars 根 K 线内收回 L1 上方（破底翻）；
  6. -> 2B 确认。L2 为结构失效线（C3：跌破 L2 -> 失效）。
```

**L1/L2 来源**：用 `confirmed_pivots` 的摆动低点。L2 = 更低的确认低点，L1 = 更高的确认低点。两个低点之间至少有一个确认摆动高点（颈线）。

### 可复用的已有基础

| 组件 | 路径 | 用途 |
|---|---|---|
| 摆动点 | `features/pivots.py::confirmed_pivots` | 三左三右确认的 swing low |
| 底部结构 | `rules/bottom_structure.py` | higher_low_bottom / double_bottom（可参考 L1/L2 识别） |
| EMA 转强 | `rules/ema_reclaim_tiers.py` | EMA20 拐头向上（C2 版本 2） |
| 双均线确认 | `rules/dual_ma.py::detect_dual_ma_confirm_events` | EMA20+SMA20 共同向上（C2 版本 3） |
| 回测工具 | `scenario_backtest_common.py` | 同 B |

### 实现要求

1. `configs/rules.v1.yaml` 加规则 `two_b_reversal`，provenance=`research_proxy`。params 含 `two_b_reclaim_bars`（**待确认**，默认 3）。formula/note_cn/events 齐备。
2. `src/lei_signal/rules/two_b_reversal.py`：`detect_two_b_reversal_events(frame, symbol)`。
   - **C1 结构**：用 confirmed_pivots 识别 L2（更低确认低点）和 L1（更高确认低点）。两低点之间需有确认摆动高点。记录 L1/L2 价格。
   - **C2 入场**：三个版本分别产事件（`two_b_reversal_v1_confirmed` / `v2_confirmed` / `v3_confirmed`）：
     - v1：收盘站上 L1（下一根开盘入场，信号在站上当日生成）；
     - v2：站上 L1 + EMA20 拐头向上（复用 ema_reclaim 逻辑）；
     - v3：站上 L1 + EMA20 与 SMA20 共同向上（复用 dual_ma_confirm 逻辑）。
   - "快速收复"窗口：从跌破 L1 到收回 L1 上方，最多 `two_b_reclaim_bars` 根 K 线。超时则本轮 2B 消耗。
   - **C3 失效**：价格收盘跌破 L2 -> `failed` 事件。L2 是结构最低点，跌破即 2B 彻底失效。
   - 每个 L1/L2 结构只允许一次 2B 确认（consumed 语义）。
3. 回测 `src/lei_signal/research/two_b_reversal_backtest.py`：三个版本分别统计。
4. `compose/pipeline.py`：接入 `detect_two_b_reversal_events`。
5. `api/explanations.py` + `api/labels.py`：加规则解释与标签。
6. `module_backtest.py::MODULE_MAP`：取消注释 two_b_reversal 行。
7. 测试：无未来泄漏 + L1/L2 识别正确 + 三版本入场 + 跌破 L2 失效 + 窗口超时消耗 + 大幅负乖离作为增强但不单独触发。

## 7. 待确认参数表（规格第 17 节，未确认前用默认 + 标注「待确认」）

| 参数 | 含义 | 默认值 | 出处 |
|---|---|---|---|
| `cluster_threshold` | 均线密集最大宽度 | 0.02（~2%） | 规格 §4.6 / tradability_gate 已有 |
| `minimum_consolidation_bars` | 横盘最短时间 | 120（~6 月） | 规格 §4.6 / tradability_gate 已有 |
| `two_b_reclaim_bars` | 2B 快速收复最大 K 线数 | **3**（待确认） | 规格 §17 待定 / 本任务新增 |
| `break_basis` | 盘中/收盘确认 | `close` | 规格 §17 / exit_ema20_costbasis 已有 |

## 8. 验收门禁（全部必须通过）

```bash
cd /Users/yongbiaoli/Desktop/lei-signal-lab
/opt/homebrew/bin/python3 -m pytest -q                    # 全绿
/opt/homebrew/bin/python3 -m ruff check src               # All checks passed
/opt/homebrew/bin/python3 -m mypy src                     # Success: no issues
git diff --check                                          # 干净
```

每个新规则必须有：
- [ ] rules.v1.yaml 注册（含 provenance/formula/note_cn/params/events）
- [ ] 前向状态机规则函数（无未来泄漏，追加未来 bars 测试）
- [ ] 回测（固定周期 + 规则退出，带 disclaimer）
- [ ] pipeline 接入
- [ ] explanations.py 中文解释
- [ ] labels.py 中文标签
- [ ] module_backtest MODULE_MAP 取消注释
- [ ] 单测（正常/失效/无未来泄漏）
- [ ] research_proxy 规则界面可见「研究代理」标注

## 9. 交付顺序建议

1. **模块 B 先**（依赖已有基础，相对简单）-> 独立提交 -> 跑门禁。
2. **模块 C 后**（L1/L2 识别是全新的）-> 独立提交 -> 跑门禁。
3. 两个都完成后，在 fixture（000001.SS / 000300.SS）上验证：B/C 各产出多少事件、`module_backtest` 的 B/C 分桶是否有样本、监督员 `MODULE_NOT_IMPLEMENTED` 对 B/C 是否消失。

## 10. 参考材料

- 交易规格原文：`docs/trading-spec-v1.md`（§9 模块 B/C）
- 对账与买卖点整理：`docs/trading-spec-audit.md`（§2 模块对账）
- 最完整参考实现：`src/lei_signal/rules/first_ma_pullback.py`
- 回测共用工具：`src/lei_signal/research/scenario_backtest_common.py`
- 模块映射：`src/lei_signal/research/module_backtest.py::MODULE_MAP`
- 横盘判定参考：`src/lei_signal/rules/tradability_gate.py`
- 排列判定参考：`src/lei_signal/rules/ma_full_alignment.py`
- 底部结构参考：`src/lei_signal/rules/bottom_structure.py`（higher_low_bottom / double_bottom）
- 摆动点：`src/lei_signal/features/pivots.py::confirmed_pivots`
