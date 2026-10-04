# 连续颜色特征：定义复用核对

本阶段只计算截至当天收盘已知的描述，不计算未来收益、下探或模型。输入沿用 `color_history_information.history_rows` 的四只 ETF 日历、连续有效报价与 252 日预热；缺报价或行动未知后，20 日窗口重新累计。核心策略源文件的 SHA-256 沿用已核对的 `df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20` 与 `85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903`。原文 §2.7 的黑、灰、绿语义和实现 §3.2 的只看截至当日数据是解释边界；连续比例不是原文另一个交易触发。

| 本阶段字段 | 严格计算 | 登记表/现有实现复用结论 |
|---|---|---|
| `green_share20` | 最近 20 个连续合格日 `color20 == green` 数量 / 20 | 颜色逐日判定与 `research.trend.daily20_non_green_to_green_week_context@1.0.0` 的日色定义相同，但该登记对象是**相邻非绿转绿事件**，不是 20 日绿色比例。登记表未找到比例的精确对象 ID，不冒用旧 ID。 |
| `switch_frequency20` | 这 20 个颜色之间的 19 对相邻日变化次数 / 19 | 与现有 `switches20`（20 对计数）窗口及分母不同；登记表未找到精确对象 ID。 |
| `ema_above_share20` | 最近 20 个连续合格日 `close > EMA20` 的次数 / 20，相等记 0 | `research.trend.ema_direction_persistence20@1.0.0` 是 `EMA20[j] > EMA20[j-1]` 的 20 日比例；它比较 EMA 自身相邻两天，**不是**本字段的价格高于 EMA 比例。`research.trend.ema_only_wait_age20@1.0.0` 的单日 `E` 条件与这里的严格大于条件相同，但其对象是连续等待日龄，也不是此比例。无精确比例对象 ID。 |
| `ema20_up_share20` | 直接调用现有 `_segment_features`，逐日重用 `sum(EMA20[j]>EMA20[j-1],j=t-19..t)/20` | **精确复用** `research.trend.ema_direction_persistence20@1.0.0`。EMA 递推使“价格高于 EMA”和“EMA 上行”在数学上几乎同义，但浮点舍入、相等边界及 252 日预热可能让这两个实现不同；比较时使用本字段作为旧控制，不把 `ema_above_share20` 冒充旧定义，也避免同一模型同时放入两个近重复字段。 |
| `distance_to_ema20` | 直接复用历史行的 `100 * (close / EMA20 - 1)`，保留正负号 | 与 `src/lei_signal/research/trend_slope_change_information.py` 的 `ema20_distance` 及登记表里该名称的基准特征公式相同；这在登记表中是基准字段，未发现独立的同名定义对象 ID。相等为 0。 |
| 当前 20/60 颜色与多头组 | 直接复用历史行颜色及 `min(SMA20,EMA20)>max(SMA60,EMA60)` | 20 日严格颜色与上述日色对象一致；60 日颜色和多头组沿用现有 `_segment_features`。不将灰色转成数字排序。 |
| 同日排名 | 每天对合格且数值有限的 ETF 做升序平均并列名次 `(rank-1)/(n-1)` | 新的显示/比较变换，不是登记因子。少于两只 ETF 时未知；同值全体得 0.5，表示该日没有相对区分度。 |

这四只 ETF 可同日一起上涨或下跌。同日排名只表达相对位置，不替代原始绝对距离、比例，也不证明新增预测信息。历史经济价格的实际到达时间仍未认证；任何收益判断留给主控已授权的后续合同。

调用 `same_day_ranks` 时须先传入当天四只 ETF 的全部合格行，再按颜色或多头背景筛选；先筛灰色再排名会改变“同日四只 ETF 相对位置”的定义。缺值仅从该字段当天的排序中剔除，单只有效值时返回未知。
