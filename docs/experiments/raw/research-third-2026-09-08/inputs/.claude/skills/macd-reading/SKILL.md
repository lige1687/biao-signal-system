---
name: macd-reading
description: MACD 解读口径（研究代理）。MACD = 均线扩散/密集 = 乖离率 = 强度，不是转折节点；只能表达「交叉」与「多头排列+乖离率」，「破线」「均线拐头」必须由 LEI 颜色与均线斜率补齐后才能用来观察趋势。禁把金叉/死叉当买点。
---

# MACD 解读 skill

本 skill 定义 LEI 系统里 **MACD 唯一合法的解读口径**。任何时候讲 MACD
（对话、抽屉、审阅、监督讲解），都按这里的口径讲，不得另起一套。

判定权在 Python（`rules/macd_strength.py` + `features/indicators.py`），
你只负责把确定性输出讲成人话。**不得自己算 MACD、不得自己判金叉死叉。**

## 定义（不可改写）

MACD 研究的是**均线的扩散和密集状态**，形容的其实就是一个**乖离率**的问题，
表示的是**强度**，而不是转折趋势节点。

- 两线间距（|DIF|）拉大 = 乖离扩散 = 强度增强；缩小 = 均线密集 = 强度收敛
- DIF 在 0 轴上方/下方 = 多头/空头排列方向（DIF>0 ⟺ EMA12>EMA26）
- 柱体 hist = 2×(DIF−DEA)，符号即 DIF×DEA 交叉状态（加速度量），
  **只用于交叉判读，不作扩散判定**

## 趋势转折 5 步骤：MACD 能交代与不能交代的部分

| 步骤 | MACD | 谁来交代 |
|---|---|---|
| 破线（收盘破均线） | **无法交代** | LEI 三色（close vs EMA20 vs close_lag20），见 `assessment.color_cn` |
| 均线拐头 | **无法表达** | 均线斜率（`ema20_slope` / `sma20_slope` / `sma60_slope` / `sma120_slope`），聚合在维度「长周期」 |
| 交叉 | **可以表达** | DIF 与 DEA 金叉/死叉；DIF 穿越 0 轴（= EMA12 穿越 EMA26，两线排列翻转） |
| 多头排列 + 乖离率 | **可以表达** | DIF 的 0 轴方向（排列）+ \|DIF\| 间距趋势（扩散/收敛） |

**核心结论**：只需要把 MACD 无法交代的部分（破线、均线拐头）用系统既有的
LEI 颜色与均线斜率补齐，就可以用 MACD 去观察趋势。**单独看 MACD 不能观察趋势** ——
讲 MACD 时必须同时给出这两项补齐，否则就是错的讲法。

## 数据从哪里来（只读，不自算）

`GET /api/symbols/{symbol}/detail`：

- `assessment.dimensions["强度(MACD)"]` → 支持 / 冲突 / 中性（唯一的 MACD 维度结论）
- `assessment.supports[] / conflicts[]` 里 `rule_id == "macd_strength"` 的那条 Factor：
  `label_cn`（形如「MACD 多头扩散（研究代理）」）+ `detail_cn`（含盲区补齐说明）
- `chart.macdDif / macdDea / macdHist` → 数值序列（末值即当日 DIF/DEA/hist）
- 盲区补齐：`assessment.color_cn`（破线）、`assessment.dimensions["长周期"]`（均线拐头）

**中性（收敛）不会进 supports/conflicts**，只在 `dimensions` 里 —— 找不到 Factor
不等于没有 MACD 读数，先看维度值。DIF/DEA 为空（预热期，前 `slow-1 + signal-1` 根）时
维度也不会出现，照实说「数据不足，MACD 尚未成形」。

## 八种状态与讲法

| status | 维度 | 讲法 |
|---|---|---|
| 金叉 | 支持 | 强度转向增强（DIF 上穿 DEA）。**不是买点** |
| 死叉 | 冲突 | 强度转向减弱（DIF 下穿 DEA）。**不是卖点** |
| 上穿0轴 | 支持 | DIF 上穿 0 轴 = EMA12 上穿 EMA26，两线排列转多。**不是买点** |
| 下穿0轴 | 冲突 | DIF 下穿 0 轴 = EMA12 下穿 EMA26，两线排列转空。**不是卖点** |
| 多头扩散 | 支持 | DIF 在 0 轴上方，两线间距拉大 = 乖离扩散，多头强度增强 |
| 多头收敛 | 中性 | DIF 在 0 轴上方，两线间距缩小 = 均线趋密集，多头强度衰减 |
| 空头扩散 | 冲突 | DIF 在 0 轴下方，两线间距拉大 = 空头乖离扩散 |
| 空头收敛 | 中性 | DIF 在 0 轴下方，两线间距缩小 = 空头强度衰减 |

照抄 `label_cn` / `detail_cn`，不要自己换词。

## 表达红线（与 lei-supervisor 一致，任何时刻不得突破）

1. **禁把金叉/死叉当买卖点**。金叉/死叉只是强度描述，`macd_strength` 规则
   **不产生任何交易事件**，不构成买点。买点只能来自系统的 review / 买点规则。
2. **禁买卖指令**：不出现 买入/卖出/建议买/该买/加仓/减仓/抄底。用「强度增强/减弱」
   「参考」「系统定义的买点」。
3. **必标研究代理**：MACD 的 `provenance = research_proxy`。讲判定时标
   「判定方式为研究代理」，不得冒充 LEI 原始规则。
4. **必带盲区补齐**：讲 MACD 强度时，同时给出破线（LEI 颜色）与均线拐头（均线斜率/长周期维度）
   的状态。只讲 MACD 就下趋势结论 = 违反口径。
5. **不调参**：12/26/9 由 `configs/rules.v1.yaml` 的 `indicators.macd_*` 读，
   不得建议改参数、不得说「换成 x/y/z 更好」。
6. **不自算不推算**：不得从 K 线自己判断金叉、不得推算 detail 里没有的乖离数值。
   任何结论可追溯到 `rule_id=macd_strength` + 数值。

## 讲解骨架

```
MACD 强度：<label_cn>（判定方式为研究代理，rule_id=macd_strength）
  数值：DIF <x> / DEA <y> / 柱体 <z>
  含义：<按上表讲两线间距的扩散或收敛，只讲强度>
  盲区补齐：破线 -> LEI 颜色为 <color_cn>；均线拐头 -> 长周期维度 <值>
  注意：MACD 只表达强度，不表达转折；金叉/死叉不构成买点。
```

## 不要做的事

- 不用 MACD 判买卖点、不用 MACD 定止损止盈、不把 MACD 写进计划的入场理由
  （入场理由只能引真实交易规则的 `lifecycle_id`）。
- 不讲「MACD 顶背离/底背离」——系统未实现背离判定，讲了就是自创规则。
- 不给 MACD 打分、不和其它维度加权成总分。
- 不在 MACD 上叠加系统没算的周期（周线 MACD 等未实现）。
