# 候选定义卡草案：candidate:lei.dual_ma.bull_state@draft-1

> 状态：**本轮源代码绑定候选草案**（2026-09-14，factor-research-workbench-v1）。
> 不是登记表对象，不冒充已登记因子，无任何有效性证据，无生产授权。
> 若实际代码/配置与下述语义冲突，本候选暂停而其余对象继续。

## 身份

- reference：`candidate:lei.dual_ma.bull_state@draft-1`
- type（拟）：state_signal；unit：boolean（0/1/缺失）；entity 轴：instrument（逐产品状态）
- 绑定源代码（冻结 SHA-256，基线见 protection-baseline.json）：
  - `src/lei_signal/rules/dual_ma.py::dual_ma_bull_state`
  - `src/lei_signal/rules/lei_color.py::classify_colors`（signal_color 唯一来源）
  - `src/lei_signal/features/indicators.py::seeded_ema / compute_features`（EMA20/SMA20/close_lag20）

## 语义（与生产函数逐条对应）

逐日布尔，全部条件同时成立才为 1：

1. `Close(t) > EMA20(t)` 且 `Close(t) > SMA20(t)`（SMA 含当日，最后 20 条有效收盘的简单平均；EMA20 由 `seeded_ema` 计算：首窗口 SMA 作种子、alpha=2/21，第 20 根起有效）。
2. `EMA20(t) > EMA20(t-1)` 且 `SMA20(t) > SMA20(t-1)`（两均线相比**前一观察**上升）。
3. `signal_color == "green"`（绿色 = Close>EMA20 且 Close>Close(t-20)，来自 `classify_colors` 严格公式；**不得由调用者任意填 green**）。

**不是**：只看 EMA20/SMA20 交叉；不要求两线同日上穿；不是完整买卖策略。

## 预热与缺失（readiness 另记，不混入有效样本）

- EMA20/SMA20 前 19 根为 NaN；颜色在不足 21 根时为 unknown。`dual_ma_bull_state`
  对未就绪行输出 **False**（布尔列无法表达缺失）。factor_lab 适配层单独计算
  readiness（close/ema20/sma20 非缺失且颜色 ≠ unknown），未就绪行输出
  value=缺失、missing_reason=`warmup_not_ready`，**不计为有效看空样本**。
- 两均线上升条件在前一日均线缺失时为 False：第 20 根（首个 EMA/SMA 有效日）
  即使其余条件满足，也因前一日缺失而 False → 同样记 `warmup_not_ready`。

## 时间与适用

- observation_time：交易日收盘（Asia/Shanghai 15:00）；available_at：收盘后即可知
  （合成案例内成立；真实资料须另行资格核验）。
- 适用实体：由每次实验的卡约束声明；库不写死 14 产品。本候选只表示
  "登记准备 + 合成接入"，不创造成熟收益因子，不改生产规则。

## validation（计划）

- 合成价格逐日核对状态真/假、readiness 边界（第 20/21 根）、颜色 green/gray 分歧
  时的状态压制；3 实体与 5 实体接口一致；追加未来数据不改变历史状态。

## status（五项分列）

| 项 | 状态 |
|---|---|
| definition_clarity | explicit（本卡+源码绑定） |
| data_qualification | synthetic_only（真实资料未检） |
| implementation | bound_to_existing_functions（只读调用，未改生产） |
| effectiveness | no_evidence |
| production | not_authorized |
