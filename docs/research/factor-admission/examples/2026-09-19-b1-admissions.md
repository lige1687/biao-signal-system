# B1 批次：问题驱动候选池（2026-09-19）

来源：factor-lib-selfevolution 线 B1 阶段（glm-high）。本文件按
`admission-form.template.json` 纸面填写 5 份准入表单（裁决均为
admit_as_candidate），并附四层缺口扫描。未实际写入 definitions.v1.json，
未运行任何数据。

## 一句话结论（大白话）

我们把交易系统说明书的四层结构（先定方向的道路层、提示路牌层、入场触发层、
过滤纪律层）逐层对照了因子登记表里现有的 81 张卡，找出 5 个"说明书里明确
需要、但登记表里没有任何卡在度量"的信息缺口，各设计了一个候选因子并走完
纸面准入流程，裁决都是"准许登记为候选"（大白话：只登记定义，还没验证过，
将来要验证得另走证据流程）。另有 2 个提案被拒，见
`2026-09-19-b1-rejections.md`。

## 0. 四层缺口扫描（G1）

对照范围：`docs/research/definitions.v1.json` v1.3.0（81 卡全量清单）＋
`docs/trading-spec-v1.md` 各层定义。逐层扫描结论：

| 层 | spec 需要 | 登记表现状 | 缺口 |
|---|---|---|---|
| 道路（§4.1–4.3, §5） | 双均线方向：EMA 预警＋SMA 确认；§4.2 抵扣价判断 SMA 方向是否承压 | `trend.sma50/200`、`trend.distance50/200`、`trend.above50/200`、`trend.cross_up50/200`、`trend.recovered200`：只有 50/200 两条 SMA 的距离/位置/交叉；**无任何抵扣价（cost basis）对象**；无 20/60/120 均线组对象 | 抵扣价距离（SMA 方向承压的直接口径）空白 |
| 路牌（§4.7–4.8, §7–8） | 顶底构造、关键性波动、量能异常三路牌；§4.7 极端乖离（偏离 EMA120，50%+ 为极端区） | `mixed.rv20/rv_percentile/volatility_allowed`（价格波动）、`mixed.momentum.raw`；量能衰减候选已立（fa-20260919-volume-anomaly-decay）；**无任何乖离率（bias）对象** | 价格对 EMA120 的乖离度量空白 |
| 入场触发（§9 A–D） | A2 回调至 20/60/120 均线组附近的"距离"；B 模块均线密集区（§4.6 六均线压缩至约 2%） | `trend.distance50/200` 只覆盖 50/200 均线，**不含 A 模块实际使用的 20/60/120 均线组**；无均线密集宽度对象 | 入场均线组回调距离、密集区宽度空白 |
| 过滤纪律（§10–13） | 盈亏比 ≥3：目标 B 只能用信号时已存在的结构（摆动高低点、缺口、密集区）；无交易条件 9 条 | `risk.*`（账户权重）、`mixed.eligible`（资格开关）；**无任何盈亏比或目标距离对象** | 盈亏比所需的目标/失效距离度量空白 |

以下 5 个候选问题即从上表缺口提炼，每条五要素齐（层、问题、为什么现有
81 卡覆盖不了、候选因子方向、证据要求）。

---

## 表单 1：`fa-20260919-b1-cost-basis-distance`（道路层）

### Stage 1 研究问题
- **question**：当前收盘价距 N 周期 SMA 的抵扣价（N 根 K 线前的价格，即
  决定 SMA 方向的那笔成本）有多远？这个距离是否系统性地区分"SMA 方向
  承压/不承压"的描述状态？
- **spec_anchor**：trading-spec §4.2（抵扣价与 SMA 方向）、§5（SMA 负责确认）
- **spec_layer**：road
- **decision_or_description**：道路层描述需求——度量 SMA 确认方向所依据的
  抵扣价压力，为后续研究"EMA 预警与 SMA 确认一致性"提供输入；不参与判定。
- **plain_language**：SMA 的方向由 N 天前的价格决定（抵扣价），价格离抵扣价
  很近时均线方向就"悬"。现在系统只看均线本身的排列，没人记录这个"悬不悬"。

### Stage 2 信息缺口
- **required_information**：`close[t] / close[t-N] − 1`（N 与 SMA 周期一致）。
- **existing_factors_checked**：
  - `trend.distance50@1.0.0` / `trend.distance200@1.0.0`：收盘价与
    **均线值**的距离，不是与 **N 期前价格**（抵扣价）的距离——两者在均线
    拐点附近差异最大，恰好是道路层最关心的时刻。
  - `trend.cross_up50/200`、`trend.above50/200`：位置与交叉状态，无承压度量。
  - `mixed.momentum.raw`：区间涨跌幅，窗口语义不同，不含"均线方向决定点"锚定。
- **gap_statement**：登记表无任何抵扣价对象；距离类卡量的是价格到均线值的
  距离，替代不了价格到抵扣价的距离。

### Stage 3 候选因子
- **candidate_id**：`trend.cost_basis_distance20`
- **name**：20 日抵扣价距离
- **type**：factor；**profile**：mixed；**uses**：["research_signal", "description"]
- **preliminary_definition**：
  - formula：`close[t] / close[t-20] − 1`
  - parameters：`{"window": 20}`（先登记 20；60/120 变体届时按 F1 版本演进评估，不一次性铺满）
  - input_requirements：日线收盘价（前复权，随登记表 sources），频率日
  - unit：比例（无量纲）；nan_policy：`close[t-20]` 不存在时 NaN，不外推
  - direction_note：无默认好坏评价（正距离是否利好是待研究问题）
- **alternatives_considered**：多窗口向量（20/60/120 三条一起登记）信息更全
  但违反"先最简"；对数收益版本数学等价，不另立。

### Stage 4 定义登记
- form_only: true。本批次不写入 definitions.v1.json（文件逐字节不变，
  开工/收工各记 SHA-256）。实际写入按 F1 字段标准，lifecycle=exists。

### Stage 5 证据要求（F2 七阶段）
- definition：登记卡快照＋registry 版本固定。
- input_manifest：合成价格序列夹具先行，逐输入 SHA-256 冻结；真实数据另按受限模式授权。
- qualification：ranking 用途按闸门裁决；target 用途必须阻断
  （blocked_qualification_target_use），输出 "Evidence complete, Target
  analysis unavailable" 不算失败。
- ranking_reconstruction：若闸门允许，排序重建留痕。
- sample_ledger：逐日行数守恒台账（factor_blocked/ranking_blocked/target_unavailable）。
- blocked_report：target 阻断时出五要素报告。
- independent_check：独立复算脚本，不得 import 被测实现。
- 禁算统计：rank_ic / quantile_groups_q2 / reference_difference。

### Stage 6 裁决
- **verdict**：admit_as_candidate
- **rationale**：问题挂到道路层 §4.2 抵扣价的明确描述需求；登记表无抵扣价
  对象、与 distance50/200 信息不同源（差一个"均线方向决定点"锚定）；定义
  一行可复算、NaN 政策明确、七阶段可安排。
- **lifecycle_target**：exists；**reviewer**：B1 执行 agent（glm-high），主控复核待验收

---

## 表单 2：`fa-20260919-b1-bias-ema120`（路牌层）

### Stage 1 研究问题
- **question**：价格偏离 EMA120 的乖离率达到多少、处于什么历史分位？极端
  乖离（spec 案例 50%+）之后的路牌描述与普通行情是否系统性不同？
- **spec_anchor**：trading-spec §4.7（乖离率；50% 以上为案例中的极端区域，
  不单独构成买卖信号）、§7.4（顶底构造首先是路标）
- **spec_layer**：signpost
- **decision_or_description**：路牌层描述需求——为"极端加速阶段"（无交易
  条件第 6 条的表述基础）提供可度量口径；不参与判定、不做硬过滤。
- **plain_language**：说明书说价格涨得离 EMA120 太远（比如 50% 以上）属于
  要重点留意的极端情况，但现在没有任何一个因子在记录"离得多远"。

### Stage 2 信息缺口
- **required_information**：`close/EMA120 − 1` 及其历史分位。
- **existing_factors_checked**：
  - `mixed.rv20@1.0.0` / `mixed.rv_percentile@1.0.0`：价格波动及其分位，
    量的是波动幅度，不是价格相对特定均线的偏离方向与幅度。
  - `trend.distance200@1.0.0` / `trend.distance50@1.0.0`：SMA 距离，均线类型
    与周期均不同（spec 明确乖离用 EMA120），且无分位、无正负方向语义。
  - `mixed.momentum.raw`：区间动量，无均线锚定。
- **gap_statement**：登记表无 EMA120 乖离对象；波动分位与 SMA 距离都不能
  替代"价格相对 EMA120 的带方向偏离"。

### Stage 3 候选因子
- **candidate_id**：`mixed.bias_ema120_pct`
- **name**：EMA120 乖离率
- **type**：factor；**profile**：mixed；**uses**：["research_signal", "description"]
- **preliminary_definition**：
  - formula：`close[t] / EMA120[t] − 1`
  - parameters：`{"window": 120, "ema_alpha": "标准 EMA 递推，与系统既有 EMA 口径一致"}`
  - input_requirements：日线收盘价（前复权），频率日；EMA 口径沿用系统既有实现
  - unit：比例（正=价格在均线上方）；nan_policy：不足 120 根 K 线时 NaN
  - direction_note：无默认好坏评价；"极端是否预示反转"是待研究问题，不是假设
- **alternatives_considered**：乖离分位（bias 的 rolling percentile）作为第二
  版本届时评估，先登记原始值；SMA120 版本与 spec 口径不符，不立。

### Stage 4 定义登记
- form_only: true（同上）。

### Stage 5 证据要求（F2 七阶段）
- 同表单 1 的七阶段安排（definition 快照 / 合成输入冻结 / qualification
  闸门＋target 阻断 / ranking_reconstruction 留痕 / sample_ledger 行数守恒 /
  blocked_report 五要素 / independent_check 独立复算）。
- 禁算统计：rank_ic / quantile_groups_q2 / reference_difference。
- 特别声明：本因子不做"极端即反转"的规则化，不生成交易规则（禁区自查）。

### Stage 6 裁决
- **verdict**：admit_as_candidate
- **rationale**：挂到 §4.7 路牌描述需求；登记表无 EMA 乖离对象，波动与
  SMA 距离不同源；定义可复算、方向声明留白、七阶段可安排。
- **lifecycle_target**：exists；**reviewer**：B1 执行 agent（glm-high），主控复核待验收

---

## 表单 3：`fa-20260919-b1-pullback-distance`（入场触发层，模块 A）

### Stage 1 研究问题
- **question**：A 模块回调入场中，价格距离 20/60/120 均线组最近的那条均线
  有多远（百分比距离）？"回调到位"的可度量口径在历史样本上如何分布？
- **spec_anchor**：trading-spec §9 模块 A A2（回调到 20/60/120 双均线组或
  密集区；"触及附近"的允许距离是必须配置参数 ma_touch_distance）
- **spec_layer**：entry_trigger
- **decision_or_description**：为 A2 位置条件提供度量基础（回调是否接近
  均线组），服务于触发条件的描述与研究代理设计；不自行判定"可入场"。
- **plain_language**：A 模块要求等价格回调到均线附近再买，但"附近"是多近
  现在没法量化——登记表里只有 50/200 天均线的距离，没有 A 模块真正用的
  20/60/120 这组均线。

### Stage 2 信息缺口
- **required_information**：收盘价到 20/60/120 六均线（EMA+SMA）中最近一条
  的绝对百分比距离。
- **existing_factors_checked**：
  - `trend.distance50@1.0.0` / `trend.distance200@1.0.0`：均线周期与 A2
    条件（20/60/120）不匹配，不能作为模块 A 的位置度量。
  - `trend.above50/above200`：二值位置状态，无距离。
  - `etf.trend.price50.state` 等：ETF 50 线状态卡，同样周期不符。
- **gap_statement**：登记表所有距离/位置对象只覆盖 50/200 周期；模块 A
  实际使用的 20/60/120 均线组距离完全空白。

### Stage 3 候选因子
- **candidate_id**：`mixed.pullback_ma_distance`
- **name**：入场均线组最近距离
- **type**：factor；**profile**：mixed；**uses**：["research_signal", "description"]
- **preliminary_definition**：
  - formula：`min(|close − M| / M)`，M ∈ {EMA20, SMA20, EMA60, SMA60, EMA120, SMA120}
  - parameters：`{"windows": [20, 60, 120], "ma_types": ["ema", "sma"]}`（登记为参数，不硬编码）
  - input_requirements：日线 OHLC 收盘价（前复权），频率日；均线口径同系统既有
  - unit：比例（非负）；nan_policy：任一均线不足窗口时 NaN（不部分计算）
  - direction_note：无默认好坏评价（距离多小算"到位"是待研究参数问题）
- **alternatives_considered**：分别登记三条单窗口距离（信息等价但卡数×3，
  违反最简）；到"密集区"的距离依赖表单 4 的密集宽度定义，先不耦合。

### Stage 4 定义登记
- form_only: true（同上）。

### Stage 5 证据要求（F2 七阶段）
- 同表单 1 的七阶段安排；合成夹具需覆盖"均线未满窗口"与"多条均线等距"
  两类边界；ranking 按闸门、target 阻断；禁算统计同前三条。

### Stage 6 裁决
- **verdict**：admit_as_candidate
- **rationale**：挂到 §9-A2 的必须配置参数（ma_touch_distance）背后的一致
  度量需求；现有距离卡周期不匹配、缺口成立；min 口径可复算、边界政策明确。
- **lifecycle_target**：exists；**reviewer**：B1 执行 agent（glm-high），主控复核待验收

---

## 表单 4：`fa-20260919-b1-ma-cluster-width`（入场触发层，模块 B）

### Stage 1 研究问题
- **question**：六条均线（EMA/SMA 20/60/120）的密集程度（最高与最低均线
  的距离百分比）当前处于什么水平？"均线密集区"的可度量口径如何界定？
- **spec_anchor**：trading-spec §4.6（均线密集：整理约不少于 6 个月、六均线
  高度接近、参考压缩至约 2% 以内）、§9 模块 B（密集区突破）
- **spec_layer**：entry_trigger
- **decision_or_description**：为 B 模块环境条件（横盘密集）提供度量基础；
  服务于触发环境描述与 research_proxy 设计；不自行判定"密集成立可交易"。
- **plain_language**：B 模块等的是"六条均线挤在一起"的横盘结束后的突破，
  说明书给了参考值（挤到 2% 以内），但没有任何因子在记录"现在挤得有多紧"。

### Stage 2 信息缺口
- **required_information**：`(max(MAs) − min(MAs)) / min(MAs)`，MAs 为六均线值。
- **existing_factors_checked**：
  - `trend.distance50/200@1.0.0`：价格到单条均线的距离，不含均线之间的相对关系。
  - `mixed.volatility_allowed@1.0.0`：价格波动开关，量的是价格不是均线排布。
  - `breadth.*` 家族：横截面"站上均线比例"，与单一标的均线间密集无关。
- **gap_statement**：登记表无任何"均线间相对距离/密集"对象；密集区是 B 模块
  的环境前提，当前完全不可度量。

### Stage 3 候选因子
- **candidate_id**：`trend.ma_cluster_width`
- **name**：六均线密集宽度
- **type**：factor；**profile**：mixed；**uses**：["research_signal", "description"]
- **preliminary_definition**：
  - formula：`(max(M) − min(M)) / min(M)`，M = {EMA20, SMA20, EMA60, SMA60, EMA120, SMA120}
  - parameters：`{"windows": [20, 60, 120], "ma_types": ["ema", "sma"]}`；2% 阈值不写入因子（属 rules.v1.yaml）
  - input_requirements：日线收盘价（前复权），频率日
  - unit：比例（非负，越小越密集）；nan_policy：任一均线不满窗口时 NaN
  - direction_note：无默认好坏评价
- **alternatives_considered**：标准差版宽度对个别均线离群敏感；逐对距离
  矩阵粒度过碎。极差/最小值是最简可复算口径，先以此登记。
- 注意：整理时长（≥6 个月）不在本因子内，属独立条件，不扩项。

### Stage 4 定义登记
- form_only: true（同上）。

### Stage 5 证据要求（F2 七阶段）
- 同表单 1 的七阶段安排；合成夹具覆盖"全部均线重合（宽度 0）"与"单线
  离群"边界；ranking 按闸门、target 阻断；禁算统计同前。

### Stage 6 裁决
- **verdict**：admit_as_candidate
- **rationale**：挂到 §4.6＋§9-B 的环境度量需求；登记表均线间关系空白；
  极差口径可复算、阈值留给规则账本不夹带。
- **lifecycle_target**：exists；**reviewer**：B1 执行 agent（glm-high），主控复核待验收

---

## 表单 5：`fa-20260919-b1-rr-distance`（过滤纪律层）

### Stage 1 研究问题
- **question**：在信号可度量时点，到最近一个**已确认**摆动高点的上行距离
  与到最近一个**已确认**摆动低点的下行距离之比是多少？这个"距离比"的分布
  能否为盈亏比 ≥3 过滤的描述研究提供口径？
- **spec_anchor**：trading-spec §10（盈亏比过滤：目标 B 只能用信号时已存在
  的结构——前期确认的摆动高低点等；无法客观确定 B 时标记"目标不可计算"）
- **spec_layer**：filter_discipline
- **decision_or_description**：为盈亏比过滤提供纯距离度量的描述基础
  （距离比 ≠ 盈亏比，盈亏比需入场价/失效价上下文，那是规则层职责）；
  不生成交易规则、不做硬过滤。
- **plain_language**：说明书要求"预计赚的空间至少是可能亏的空间的 3 倍才
  交易"，赚的空间要用信号时已经存在的前期高点来量。现在登记表里没有
  任何一张卡在量"到前期高点和前期低点各有多远"。

### Stage 2 信息缺口
- **required_information**：`(swing_high − close) / (close − swing_low)`，
  两端摆动点均为信号时已确认（避免未来函数）。
- **existing_factors_checked**：
  - `risk.*`（4 张）：账户权重与方向占比，与距离度量无关。
  - `mixed.eligible@1.0.0` / `mixed.volatility_allowed@1.0.0`：资格与波动
    开关，不含目标/失效结构距离。
  - `trend.*` 全部：均线距离/位置，不含摆动点结构。
- **gap_statement**：登记表过滤类只有开关与权重，目标—失效距离比这一
  §10 核心度量为零覆盖。

### Stage 3 候选因子
- **candidate_id**：`mixed.swing_rr_distance`
- **name**：已确认摆动点距离比
- **type**：factor；**profile**：mixed；**uses**：["research_signal", "description"]
- **preliminary_definition**：
  - formula：`(H_conf − close[t]) / (close[t] − L_conf)`；H_conf/L_conf 为
    t 时点最近已完成确认的摆动高/低点（确认根数沿用系统既有 swing 口径，
    不在本因子内重复定义）
  - parameters：`{"swing_confirmation": "沿用系统既有 swing 实现，登记时钉版本"}`
  - input_requirements：日线 OHLC（前复权）＋摆动点序列，频率日
  - unit：无量纲比值（正）；nan_policy：close ≤ L_conf 或无已确认摆动点时
    NaN（对应 spec"目标不可计算"标记，不事后选点）
  - direction_note：无默认好坏评价；距离比不等于盈亏比，不承载"≥3 可交易"语义
- **alternatives_considered**：到最近前高/前低的单边距离分别登记（信息可
  组合但比值语义要冻结）；含缺口/密集区目标的完整盈亏比属规则层组合逻辑，
  超出因子边界，不立。

### Stage 4 定义登记
- form_only: true（同上）。

### Stage 5 证据要求（F2 七阶段）
- 同表单 1 的七阶段安排；合成夹具须包含"无已确认摆动点""close 跌破 L_conf"
  两类 NaN 分支；ranking 按闸门、target 阻断；禁算统计同前。

### Stage 6 裁决
- **verdict**：admit_as_candidate
- **rationale**：挂到 §10 的距离度量基础；登记表过滤类零覆盖；比值口径
  严格只用已确认结构、NaN 对应"目标不可计算"，符合防未来函数要求；
  明确与交易规则划界。
- **lifecycle_target**：exists；**reviewer**：B1 执行 agent（glm-high），主控复核待验收

---

## G3 边界自查（本文件）

- 全文无因子比较、排名、IC、收益/有效性表述；五张卡均为定义级候选。
- definitions.v1.json 未写入、未修改（前后 SHA-256 见
  `docs/experiments/raw/factor-b1-2026-09-19/README.md`）。
- 未触碰禁区：不按表现筛选、不淘汰因子、不生成交易规则、不改 trading-spec。
