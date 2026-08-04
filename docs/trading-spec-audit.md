# LEI 交易规格 V1.0 ↔ 现有系统对账与买卖点整理

配套文档：`docs/trading-spec-v1.md`（规格原文）。
对账基线：`configs/rules.v1.yaml` ruleset `1.2.0`（23 条规则）。

## 1. 现有规则清单（1.2.0）

| rule_id | provenance | 对应规格章节 |
|---|---|---|
| lei_color | lei_explicit | 4.3 / 5 颜色预警 |
| ema20_reclaim_rising | lei_explicit | 5 趋势状态 / A4 早期版 |
| dual_ma_bull_confirmed | lei_explicit | 4.5 排列 / A4 确认版 |
| dual_ma_spread | lei_inferred | 4.5 开口 |
| long_trend | lei_inferred | 4.4 长周期 |
| swing_pivots | existing_backtest | 7.3 摆动点代理 |
| bullish_engulfing | research_proxy | 7 底部构造 |
| bullish_outside_reversal | research_proxy | 7 底部构造 |
| bearish_engulfing | research_proxy | 7 顶部构造 |
| bearish_outside_reversal | research_proxy | 7 顶部构造 |
| higher_low_bottom | lei_explicit | 7 底部构造 |
| double_bottom | lei_explicit | 7 底部构造 |
| bullish_reversal_bottom | lei_explicit | 7 底部构造 |
| bottom_c_lifecycle | lei_explicit | 7.2 失效 / A5 |
| top_structure | lei_explicit | 7.1 顶部 / A6 退出 |
| key_wave_black | lei_explicit | 8 关键波动 / A6 退出 |
| volume_proxies | research_proxy | 4.8 量能 |
| volume_profile_proxy | research_proxy | 11 筹码代理 POC/VAL/VAH |
| first_ma_pullback | research_proxy | 模块 A 回撤 |
| false_breakout_reclaim | research_proxy | 模块 D 假突破（做多侧） |
| ma_full_alignment | research_proxy | 4.5 排列 / B2 |
| low_level_confirmation | research_proxy | A3 低级别确认（日线代理） |
| resistance_b1 | lei_explicit | 10 目标 B |

## 2. 四大交易模块对账

### 模块 A：稳定上升趋势回调
| 子项 | 规格 | 系统现状 | 状态 |
|---|---|---|---|
| A1 环境 | 多头趋势平行向上 | ma_full_alignment + long_trend | ✅ |
| A2 位置 | 回撤到 20/60/120 或密集区 | first_ma_pullback（20/60/120） | ⚠️ 密集区回撤未接 |
| A3 结构 | 底部构造/低级别排列/破线重站回/破底翻 | 底部构造✅、low_level_confirmation✅、ema20_reclaim_rising✅ | ⚠️ 破底翻(2B)缺 |
| A4 入场 | 早期(EMA20拐头)/确认(双均线共同向上) | ema20_reclaim_rising + dual_ma_bull_confirmed | ✅ |
| A5 失效 | 结构低点破坏 | bottom_c_lifecycle | ✅ |
| A6 退出 | ①跌破EMA20+20日抵扣价 ②顶构+关键波动 ③结构止损 | ②(top_structure+key_wave_black)✅ ③✅ | ⚠️ ①抵扣价退出缺 |

### 模块 B：均线密集区突破
| 子项 | 规格 | 系统现状 | 状态 |
|---|---|---|---|
| B1 环境 | 横盘不频繁交易 | 无横盘/趋势类型判定 | ❌ |
| B2 多头触发 | 多头排列+突破密集区+三线同向 | ma_full_alignment✅、volume_profile_proxy(代理)✅ | ⚠️ 突破触发逻辑未接 |
| B3 失效 | 跌回密集区+20MA下弯 | — | ❌ |

### 模块 C：2B / 破底翻
| 子项 | 规格 | 系统现状 | 状态 |
|---|---|---|---|
| C1 结构 | 多头 2B（L1/L2） | — | ❌ 完全缺 |
| C2 入场 | 收复L1 + EMA20拐头/双均线共同向上 | 可复用 ema20_reclaim_rising / dual_ma_bull_confirmed | ⚠️ 2B 结构识别缺 |
| C3 失效 | 重新跌破 L2 | — | ❌ |

### 模块 D：假突破反向
| 子项 | 规格 | 系统现状 | 状态 |
|---|---|---|---|
| D1 多头假跌破 | 价格收回+均线方向改变 | false_breakout_reclaim（做多侧） | ✅ |
| D2 空头假突破 | 对称做空 | — | ❌ 缺做空镜像 |
| D3 失效 | 假跌破低点/假突破高点 | 做多侧✅ | ⚠️ 做空侧缺 |

## 3. 卖点 / 退出全景

| 退出方式 | 规格 | 系统现状 | 状态 |
|---|---|---|---|
| 结构止损（入场结构破坏） | A5/各模块 | bottom_c_lifecycle | ✅ |
| 顶部构造 + 反向关键波动 | A6② | top_structure + key_wave_black | ✅ |
| 跌破 EMA20 + 20 日抵扣价 | A6① | 抵扣价 cost_basis 未计算 | ❌ |
| 关键波动单独退出（研究） | 8.3 | key_wave_black 可独立统计 | ✅ |
| 盈亏比目标止盈 | 10 | resistance_b1 作目标参考，无 R/R 过滤 | ❌ |
| 周期扩散升级观察 | 6 | weekly_trend 有，60min 无 | ⚠️ |

## 4. 横切层缺口（影响所有模块）

| 横切层 | 规格 | 系统现状 | 状态 |
|---|---|---|---|
| 趋势类型分类 | 2.2 道路 / 13 无交易 | Stage 是机会阶段链，无趋势类型 | ❌ |
| 可交易性门禁 | 13 无交易条件 | 无 | ❌ |
| 盈亏比过滤 | 10 | 无 | ❌ |
| 抵扣价 | 4.2 | 未计算 | ❌ |
| 趋势五步状态机 | 5 | EMA/SMA 方向有，五步未显式化 | ⚠️ |
| 多周期（60min） | 6 | 仅日线+周线 | ⚠️ 代理 |
| 信号冲突 / 模块分别统计 | 12 | 事件按 rule_id 分，未按交易模块分组统计 | ⚠️ |

## 5. 待确认参数表（规格第 17 节，标注现有值）

> 规格要求：写代码前先确认，不得擅自优化。下表"现有值"来自 rules.v1.yaml 或代码默认，"待定"=需彪哥拍板。

| 参数 | 含义 | 现有值 / 待定 |
|---|---|---|
| execution_timeframe | 执行周期 | 日线（日线为主） |
| context_timeframe | 背景周期 | 周线（weekly_trend） |
| direction | 方向 | 仅做多（待定是否开做空） |
| cluster_threshold | 均线密集最大宽度 | 待定（规格参考 ~2%） |
| minimum_consolidation_bars | 横盘最短时间 | 待定（规格参考 ~6 个月） |
| ma_touch_distance | 回撤到均线距离 | touch_tolerance_pct/atr（已有） |
| swing_confirmation | 顶底构造确认方式 | swing 左右确认根数（已有） |
| two_b_reclaim_bars | 2B 快速收复最大 K 线数 | 待定 |
| volume_lookback | 成交量基准窗口 | 已有（volume_proxies） |
| volume_threshold | 异常量阈值 | 已有，待优化 |
| gap_definition | 缺口最小标准 | 待定 |
| acceleration_definition | 加速趋势定义 | 待定（斜率角度区间） |
| bias_extreme | 极端乖离阈值 | 待定（规格参考 50%） |
| break_basis | 盘中/收盘确认 | 收盘为主（部分 low 触发） |
| exit_variant | 退出方式 | 待定（A6 三版本） |
| reward_risk_min | 最低盈亏比 | 待定（规格 3） |
| fees_and_slippage | 费用滑点 | 待定 |

## 6. 落地路线图（分阶段，遵循规格第 15 节回测顺序）

### 第一轮：补齐退出 + 横切层（基础最小系统）
1. **抵扣价 cost_basis_N**（4.2）：计算 SMA20/60/120 抵扣价，落地 A6① 退出（收盘跌破 EMA20 + 20 日抵扣价）。
2. **盈亏比过滤**（10）：入场前用 resistance_b1/摆动点/密集区算目标 B，R/R<3 标记"目标不可计算/放弃"。
3. **可交易性门禁**（13）：趋势类型分类（横盘/趋势/加速）+ 无交易条件清单。
4. **模块分别统计**（12）：回测按 A/B/C/D 模块分组输出，不混算。

### 第二轮：补齐缺失买入模块
5. **模块 D 做空镜像**（D2）：false_breakout_reclaim 加 direction=short + sma20_slope<0。
6. **模块 C 2B/破底翻**（C1-C3）：L1/L2 结构识别 + 快速收复窗口 + 失效。
7. **模块 B 密集区突破**（B1-B3）：横盘判定 + 突破触发 + 跌回失效。

### 第三轮：附加过滤器（规格第 15 节第四轮）
8. 斜率加速参与度（acceleration_definition）。
9. 缺口（gap_definition）。
10. 筹码分布增量过滤（volume_profile_proxy 已有代理，接增量比较）。
11. 多周期共振（60min 接入后）。
12. 极端乖离过滤（bias_extreme）。

## 7. 买卖点卡片映射（前端状态机卡）

规格四个模块的入场点，统一映射到买点状态机卡的"当前档"：
- 模块 A → "首次回撤确认"档（first_ma_pullback_confirmed）
- 模块 B → "密集区突破"档（新增）
- 模块 C → "2B 破底翻"档（新增）
- 模块 D → "假突破收回"档（false_breakout_reclaim_confirmed）

卖点/退出映射到卡的"失效边界"层 + 独立"持仓退出"区：
- 结构止损 / 顶构+关键波动 / EMA20+抵扣价 / 盈亏比目标，四种退出方式分别可回测、可展示。
