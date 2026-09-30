# 正例：量能异常后的量能衰减（纸面走通到 candidate）

表单 ID：`fa-20260919-volume-anomaly-decay`（对应
`admission-form.template.json` 全部字段，本文为其填写稿）

## 一句话结论（大白话）

我们挑了一个真实的研究问题——「成交量突然放大的路牌信号出现之后，量能是
很快缩回去还是持续放大，对后续走势的含义可能不同，但我们现在没有任何因子
能度量"放出来的量缩回去的速度"」——并为它设计了一个候选因子（量能异常后
N 日成交量回落比例）。整个准入流程在纸面上走通，裁决是**准许登记为
candidate**（大白话：只登记定义、还没验证过，将来要验证得另走证据流程）。
本次没有真正写入登记表，也没有跑任何真实数据。

## Stage 1 研究问题

- **question**：路牌层的「量能异常」出现后，量能在随后 N 日是快速萎缩还是
  持续维持？这个"衰减速度"与路牌的后续描述是否有系统性差异？
- **spec_anchor**：`docs/trading-spec-v1.md` 路牌层「量能异常，只预警不必然
  反向」（体系分层第二层）。规格书里量能异常是路牌之一，但规格只定义了
  异常的识别，没有定义异常之后的量能演化如何度量——这正是描述层缺口。
- **spec_layer**：signpost
- **decision_or_description**：服务于路牌信号的**叙事与描述研究**：解释
  「这次量能异常之后市场承接如何」，为后续（远期）研究路牌质量提供输入；
  不参与判定、不做硬过滤（与基本面/消息面同一边界原则）。
- **plain_language**：现在系统只能告诉你"今天量能异常了"，但异常之后量是
  一天就缩没还是持续放大，目前没人记录。想研究路牌信号的好坏，先得能度量
  这个"后劲"。

## Stage 2 信息缺口

- **required_information**：量能异常事件后 N 日成交量相对异常日成交量的
  比例（衰减速度的可度量口径）。
- **existing_factors_checked**（对照 definitions.v1.json v1.3.0，共 81 卡，
  逐一检索 volume/amount/turnover 类对象）：
  - `mixed.rv20@1.0.0`：价格的 20 期样本波动——量的是**价格**波动，
    不含成交量信息。
  - `mixed.volatility_allowed@1.0.0`：历史波动过滤状态，依赖
    `mixed.rv_percentile`，同样只看价格，且是过滤开关不是事件后演化度量。
  - `breadth.*`（约 25 张卡）：宽度家族全部基于"站上均线的比例"，
    无量能维度。
  - 其余卡（momentum、price、asset、policy、benchmark 等）经逐类检索，
    无任何成交量输入对象。
- **gap_statement**：登记表对**成交量**维度整体空白；价格波动与宽度均无法
  替代"量能异常后衰减速度"这一事件锚定的信息。

## Stage 3 候选因子

- **candidate_id**：`mixed.volume_anomaly_decay`
- **name**：量能异常后 N 日量能衰减比例
- **type**：factor；**profile**：mixed；**uses**：["research_signal", "description"]
- **preliminary_definition**：
  - formula：`mean(volume[t+1..t+N]) / volume[t]`，其中 t 为量能异常
    事件日（异常识别口径沿用路牌层既有定义，不在本因子内重复定义）；
    N 初稿 5，参数登记在 parameters，不硬编码。
  - input_requirements：日线成交量（前复权口径随登记表 sources）、
    事件日序列、N；数据频率日。
  - unit：无量纲比值；nan_policy：事件后不足 N 日或 volume[t] 无效时为
    NaN，不外推。
  - direction_note：无默认好坏评价（快衰减好还是坏是待研究问题，不是假设）。
- **alternatives_considered**：逐日量比序列（volume[t+k]/volume[t] 全序列）
  信息更细但登记粒度过碎；最大量能回落深度（max/min）对异常日选择敏感。
  均值比例是描述"整体后劲"的最简可复算口径，先以最简版本登记。

## Stage 4 定义登记

- form_only: true。本次不实际写入 definitions.v1.json（该文件在本任务中
  逐字节不变，开工/收工各记一次 SHA-256）。实际写入时按 F1 字段标准成卡，
  lifecycle=exists。

## Stage 5 证据要求（引用 F2 七阶段）

- definition：登记卡快照 + registry 版本固定。
- input_manifest：输入为合成夹具先行（成交量序列 + 事件日序列），
  真实数据运行另按受限模式授权；逐输入 SHA-256 冻结。
- qualification：ranking 用途按闸门裁决；target 用途必须阻断
  （blocked_qualification_target_use），输出"Evidence complete, Target
  analysis unavailable"不算失败。
- ranking_reconstruction：作为研究信号可做排序重建留痕（若闸门允许）。
- sample_ledger：事件级台账，行数守恒（factor_blocked + ranking_blocked +
  target_unavailable）。
- blocked_report：target 阻断时出五要素报告。
- independent_check：独立复算脚本，不得 import 被测实现。
- 禁算统计：rank_ic / quantile_groups_q2 / reference_difference。
- 升级路径：到 verified 必须走 F1 证据规则 + F2 完整证据链；
  本准入流程到此为止。

## Stage 6 裁决

- **verdict**：admit_as_candidate
- **rationale**：研究问题挂到路牌层量能异常的具体描述需求；登记表量能维度
  空白、缺口经逐类对照成立；候选定义可复算、NaN 政策明确、七阶段证据路径
  可安排。三项准入条件全部满足，且未触碰任何禁区。
- **lifecycle_target**：exists（candidate）
- **reviewer**：F3 执行 agent（glm-max），主控复核待验收

## 未触碰声明

本正例全程纸面：未写 definitions.v1.json、未运行数据、未生成交易规则、
未按任何收益/IC 口径筛选。
