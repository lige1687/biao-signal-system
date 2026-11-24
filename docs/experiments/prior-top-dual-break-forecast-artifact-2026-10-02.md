# prior-top-dual-break-interaction-2026-10-02（限定范围研究）

## 一句话结论（大白话）

本次方法下未得到新增帮助的支持。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：在SMA60最近5日上行背景中，前收盘已有且今天没有被创新高破坏的最新简单顶部，与今天双跌破同时出现，是否在分别知道这两个分量及价格背景后，增加未来20日收盘下探信息
计划对象：510300.SS, 510050.SS, 510500.SS, 588000.SS；实际有报价：510050.SS, 510300.SS, 510500.SS, 588000.SS。
时期：['2022-01-04', '2026-06-30']；评价对象数量：874条、291个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | MSE | 14.516891 | 百分点² | 874 | 291 | 4 |
| B0 | RMSE | 3.8101038 | 百分点 | 874 | 291 | 4 |
| B1 | MSE | 13.702304 | 百分点² | 874 | 291 | 4 |
| B1 | RMSE | 3.7016623 | 百分点 | 874 | 291 | 4 |
| B2 | MSE | 13.716907 | 百分点² | 874 | 291 | 4 |
| B2 | RMSE | 3.7036343 | 百分点 | 874 | 291 | 4 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 13.702304 | 13.716907 | -0.014603168 | -0.1066% | -0.0346375 至 0.00871672 | percentage_point_squared |
| B2 相对 B0 | 14.516891 | 13.716907 | 0.79998387 | 5.511% | 0.114301 至 1.50907 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "scheduled": 4340,
    "ready_252": 4340,
    "trend_up": 2069,
    "eligible": 2009,
    "state_00": 958,
    "state_10": 516,
    "state_01": 88,
    "state_11": 447,
    "reason:continuous252_or_economic_price_missing": 0,
    "reason:sma60_not_rising": 2271,
    "per_asset": {
      "510300.SS": {
        "scheduled": 1085,
        "ready_252": 1085,
        "trend_up": 529,
        "eligible": 508,
        "state_00": 257,
        "state_10": 125,
        "state_01": 21,
        "state_11": 105,
        "reason:continuous252_or_economic_price_missing": 0,
        "reason:sma60_not_rising": 556
      },
      "510050.SS": {
        "scheduled": 1085,
        "ready_252": 1085,
        "trend_up": 550,
        "eligible": 543,
        "state_00": 233,
        "state_10": 170,
        "state_01": 24,
        "state_11": 116,
        "reason:continuous252_or_economic_price_missing": 0,
        "reason:sma60_not_rising": 535
      },
      "510500.SS": {
        "scheduled": 1085,
        "ready_252": 1085,
        "trend_up": 526,
        "eligible": 515,
        "state_00": 249,
        "state_10": 128,
        "state_01": 21,
        "state_11": 117,
        "reason:continuous252_or_economic_price_missing": 0,
        "reason:sma60_not_rising": 559
      },
      "588000.SS": {
        "scheduled": 1085,
        "ready_252": 1085,
        "trend_up": 464,
        "eligible": 443,
        "state_00": 219,
        "state_10": 93,
        "state_01": 22,
        "state_11": 109,
        "reason:continuous252_or_economic_price_missing": 0,
        "reason:sma60_not_rising": 621
      }
    },
    "definition_ref": "research.interaction.prior_top_dual_break20@1.0.0",
    "planned_assets": [
      "510300.SS",
      "510050.SS",
      "510500.SS",
      "588000.SS"
    ],
    "input_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "input_missing_assets": [],
    "actual_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "588000.SS"
    ],
    "missing_assets": [],
    "partial": false,
    "evaluation_rows": 874,
    "evaluation_dates": 291
  },
  "descriptions": {
    "available": true,
    "population": "all_evaluable_observations (not restricted to forecast evaluation folds)",
    "raw_rows": 4340,
    "evaluable_rows": 2009,
    "common_prediction_rows": 874,
    "event_opportunities": 447,
    "excluded": [
      {
        "id": "510300.SS|2022-01-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-01-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-02-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-03-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-04-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-05-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-06-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-06-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-06-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-06-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-06-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-06-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-06-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-06-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-06-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-09-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-10-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-11-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2022-12-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-04-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-04-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-04-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-04-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-04-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-04-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-05-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-06-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-07-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-08-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-08-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-08-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-08-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-08-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-08-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-08-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-08-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-08-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-08-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-08-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-09-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-10-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-11-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2023-12-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-01-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-02-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-03-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-03-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-06-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-06-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-06-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-06-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-06-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-06-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-06-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-06-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-06-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-06-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-06-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-07-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-08-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2024-09-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-01-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-02-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-03-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-03-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-03-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-03-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-03-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-03-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-03-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-03-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-03-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-03-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-04-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-05-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2025-06-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-02-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-03-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-03-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-03-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-03-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-03-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-03-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-04-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510300.SS|2026-06-01",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-02",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-03",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-04",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-05",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-08",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-09",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-10",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-11",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-12",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-15",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-16",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-17",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-18",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-22",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-23",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-24",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-25",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-26",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-29",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-30",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2022-01-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-01-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-02-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-03-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-04-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-05-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-06-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-06-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-06-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-06-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-06-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-06-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-06-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-06-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-06-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-08-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-08-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-08-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-09-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-10-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-11-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2022-12-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-03-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-03-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-03-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-03-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-03-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-03-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-03-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-03-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-03-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-04-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-05-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-06-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-07-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-08-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-08-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-08-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-08-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-08-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-08-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-08-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-10-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-10-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-10-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-10-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-10-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-10-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-10-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-10-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-10-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-10-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-10-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-10-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-11-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2023-12-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-01-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-02-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-02-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-02-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-02-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-02-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-02-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-02-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-02-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-02-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-02-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-02-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-06-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-06-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-06-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-06-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-06-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-06-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-06-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-06-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-06-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-06-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-07-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-07-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-07-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-07-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-07-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-07-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-07-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-07-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-07-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-07-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-07-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-07-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-08-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2024-09-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-01-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-02-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-04-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-04-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-04-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-04-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-04-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-04-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-04-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-04-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-06-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-06-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-06-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-06-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-06-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-06-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2025-06-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-03-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-03-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-03-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-03-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-03-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-03-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-03-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-03-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-03-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-03-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-03-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-03-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-03-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-04-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-05-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510050.SS|2026-06-22",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-23",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-24",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-25",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-26",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-29",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-30",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2022-01-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-01-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-01-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-01-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-02-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-03-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-04-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-05-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-06-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-06-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-06-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-06-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-06-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-06-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-06-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-06-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-06-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-06-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-09-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-09-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-09-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-09-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-09-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-09-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-09-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-09-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-09-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-09-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-09-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-10-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-11-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2022-12-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-04-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-04-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-04-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-05-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-06-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-07-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-08-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-09-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-10-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-11-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2023-12-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-01-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-02-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-03-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-04-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-04-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-04-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-04-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-04-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-04-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-04-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-06-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-07-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-08-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2024-09-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-01-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-02-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-02-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-02-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-02-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-02-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-02-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-02-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-02-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-02-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-02-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-02-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-02-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-02-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-04-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-04-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-04-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-04-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-04-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-04-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-04-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-05-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-06-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-12-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-12-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-12-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2025-12-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-04-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-04-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-04-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-04-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-04-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-04-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-04-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-04-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-04-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-05-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-05-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-06-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-06-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-06-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-06-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-06-05",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-06-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-06-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-06-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-06-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-06-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "510500.SS|2026-06-16",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-17",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-18",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-22",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-23",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-24",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-25",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-26",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-29",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-30",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2022-01-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-01-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-02-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-03-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-04-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-05-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-06-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-08-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-08-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-09-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-10-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-11-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2022-12-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-02-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-03-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-03-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-03-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-03-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-03-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-03-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-03-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-03-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-03-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-03-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-05-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-06-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-06-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-06-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-06-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-07-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-08-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-09-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-10-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-11-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2023-12-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-01-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-02-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-03-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-04-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-05-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-05-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-05-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-05-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-05-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-05-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-05-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-05-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-06-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-07-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-08-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2024-09-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-01-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-01-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-01-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-01-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-01-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-01-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-01-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-01-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-02-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-02-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-02-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-02-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-04-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-04-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-05-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-11",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-12",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-06-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-07-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-07-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-07-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-07-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-07-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-07-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-07-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-07-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-07-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-07-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-07-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-12-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-12-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-12-04",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-12-18",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-12-19",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-12-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-12-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-12-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-12-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-12-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-12-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-12-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2025-12-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-01-05",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-01-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-01-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-01-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-01-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-03-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-03-25",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-03-26",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-03-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-03-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-03-31",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-01",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-02",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-03",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-07",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-08",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-09",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-10",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-13",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-14",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-15",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-16",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-17",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-20",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-21",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-22",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-23",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-24",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-27",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-28",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-29",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-04-30",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-05-06",
        "reason": "sma60_not_rising"
      },
      {
        "id": "588000.SS|2026-06-01",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-02",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-03",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-04",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-05",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-08",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-09",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-10",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-11",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-12",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-15",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-16",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-17",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-18",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-22",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-23",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-24",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-25",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-26",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-29",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-30",
        "reason": "immature_label"
      }
    ],
    "own_group": [
      {
        "condition": 0,
        "mean": 3.7393649654129604,
        "rows": 1562,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      },
      {
        "condition": 1,
        "mean": 3.49959388577204,
        "rows": 447,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      }
    ],
    "common_asset_year": [
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2022",
        "weight": 0.05,
        "rows0": 35,
        "rows1": 25,
        "mean0": 4.322267423389779,
        "mean1": 3.877891261673948,
        "overall": 4.137110689341517,
        "share1": 0.4166666666666667
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2023",
        "weight": 0.05,
        "rows0": 68,
        "rows1": 23,
        "mean0": 3.4925748882182694,
        "mean1": 2.0610860312100683,
        "overall": 3.130770012271142,
        "share1": 0.25274725274725274
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2024",
        "weight": 0.05,
        "rows0": 114,
        "rows1": 23,
        "mean0": 3.2121916010082763,
        "mean1": 2.470752713529022,
        "overall": 3.0877164593146786,
        "share1": 0.1678832116788321
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2025",
        "weight": 0.05,
        "rows0": 126,
        "rows1": 20,
        "mean0": 1.7221511386425716,
        "mean1": 1.3682610403784632,
        "overall": 1.673673042989954,
        "share1": 0.136986301369863
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2026",
        "weight": 0.05,
        "rows0": 60,
        "rows1": 14,
        "mean0": 3.1561562374083088,
        "mean1": 3.5986980552734305,
        "overall": 3.2398803651125205,
        "share1": 0.1891891891891892
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2022",
        "weight": 0.05,
        "rows0": 31,
        "rows1": 27,
        "mean0": 4.396256050464217,
        "mean1": 3.3329193261535517,
        "overall": 3.9012544719058044,
        "share1": 0.46551724137931033
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2023",
        "weight": 0.05,
        "rows0": 70,
        "rows1": 28,
        "mean0": 3.788640443894891,
        "mean1": 3.546587985809429,
        "overall": 3.7194825987276166,
        "share1": 0.2857142857142857
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2024",
        "weight": 0.05,
        "rows0": 123,
        "rows1": 25,
        "mean0": 2.812319261327852,
        "mean1": 1.6045257154466364,
        "overall": 2.608300081280349,
        "share1": 0.16891891891891891
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2025",
        "weight": 0.05,
        "rows0": 176,
        "rows1": 20,
        "mean0": 1.5810222860453313,
        "mean1": 0.42022501336421597,
        "overall": 1.46257358475134,
        "share1": 0.10204081632653061
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2026",
        "weight": 0.05,
        "rows0": 27,
        "rows1": 16,
        "mean0": 3.580133076420438,
        "mean1": 6.242092666106448,
        "overall": 4.570629667931511,
        "share1": 0.37209302325581395
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2022",
        "weight": 0.05,
        "rows0": 59,
        "rows1": 27,
        "mean0": 4.539379251745578,
        "mean1": 5.867606608417284,
        "overall": 4.956380863723905,
        "share1": 0.313953488372093
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2023",
        "weight": 0.05,
        "rows0": 65,
        "rows1": 13,
        "mean0": 2.630030687403781,
        "mean1": 1.3605422998492074,
        "overall": 2.4184492894780187,
        "share1": 0.16666666666666666
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2024",
        "weight": 0.05,
        "rows0": 79,
        "rows1": 22,
        "mean0": 4.942335089091665,
        "mean1": 3.6387328980186613,
        "overall": 4.6583821365807125,
        "share1": 0.21782178217821782
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2025",
        "weight": 0.05,
        "rows0": 129,
        "rows1": 37,
        "mean0": 3.066985959150942,
        "mean1": 3.271548276054945,
        "overall": 3.1125811743644847,
        "share1": 0.22289156626506024
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2026",
        "weight": 0.05,
        "rows0": 66,
        "rows1": 18,
        "mean0": 5.5596884559046496,
        "mean1": 3.60670045992256,
        "overall": 5.141191028194202,
        "share1": 0.21428571428571427
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2022",
        "weight": 0.05,
        "rows0": 37,
        "rows1": 10,
        "mean0": 6.91099164885749,
        "mean1": 5.003228463195206,
        "overall": 6.505084588078281,
        "share1": 0.2127659574468085
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2023",
        "weight": 0.05,
        "rows0": 70,
        "rows1": 16,
        "mean0": 4.414603418920745,
        "mean1": 1.9266442342047065,
        "overall": 3.9517272915317148,
        "share1": 0.18604651162790697
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2024",
        "weight": 0.05,
        "rows0": 71,
        "rows1": 6,
        "mean0": 5.188752788843563,
        "mean1": 2.6191429223848592,
        "overall": 4.988523448600027,
        "share1": 0.07792207792207792
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2025",
        "weight": 0.05,
        "rows0": 116,
        "rows1": 55,
        "mean0": 4.715102197311675,
        "mean1": 4.086217325430881,
        "overall": 4.5128292853032335,
        "share1": 0.3216374269005848
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2026",
        "weight": 0.05,
        "rows0": 40,
        "rows1": 22,
        "mean0": 8.487578447531547,
        "mean1": 8.443050879873105,
        "overall": 8.471778342878553,
        "share1": 0.3548387096774194
      }
    ],
    "unsupported_strata": [],
    "comparison_available": true,
    "common_support_rows": 2009,
    "common_support_assets": 4,
    "fixed_common_means": {
      "condition0": 4.125958017579079,
      "condition1": 3.4173227088148312,
      "difference": -0.7086353087642481,
      "baseline": 4.012415921117979,
      "identity_error": 8.881784197001252e-16,
      "unit": "percentage_point",
      "weighting": "equal supported assets; equal supported years within asset; same strata in both conditions",
      "evidence": "descriptive, not causal"
    }
  }
}
```

## 反例和结论边界

评价期资料没有参与训练或标准化；已有资料是否曾用于挑选方法仍以研究家族记录为准，换名字不成为新验证。预测改善不直接代表投资收益。

- 逐行名义OHLC和行动重建已重新核对；V01量仅在源资格例程内核对，未进入T01特征。
- 行动历史到达时间及完整性仍未知；这些是回顾性经济价格观察。
- T and K are retained separately; their product is only a risk-information expression.
- A prior top broken by today's high is not active today; today's new top enters no earlier than tomorrow.
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B1
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "四国内宽基ETF固定历史，4340安排日全部保留；2069上行背景日及四态均有支持；市场总体及未来独立验证不在此次可推断范围。",
    "source_refs": [
      "docs/experiments/raw/technical-combination-semantics-2026-10-02/qualification/qualification.json",
      "docs/experiments/raw/technical-combination-semantics-2026-10-02/controller/qualification-review.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "原文§4.3有顶部与均线转向位置的组合，但此处仅用昨日已有且今日未破坏的最新简单三根顶部和K01双跌破；极端时钟、严格包含构造、持续恶化和持仓退出均省略。",
    "source_refs": [
      "docs/experiments/raw/technical-combination-semantics-2026-10-02/qualification/qualification.json",
      "docs/experiments/raw/technical-combination-semantics-2026-10-02/controller/qualification-review.json"
    ]
  },
  "method_fit": {
    "reason": "两个训练期983和1678条均有四态；B1同时含T、K与固定价格背景，B2只加乘积；ridge1固定而非优化。2026H1只有4条双跌破但无顶部的可评价日，限制组合分离。",
    "source_refs": [
      "docs/experiments/raw/technical-combination-semantics-2026-10-02/qualification/qualification.json",
      "docs/experiments/raw/technical-combination-semantics-2026-10-02/controller/qualification-review.json"
    ]
  },
  "conclusion_scope": {
    "reason": "只回答未来20日收盘下探的固定模型表示增量；产品项并非新增数据，描述差额并非因果或账户退出效果；原文不变。",
    "source_refs": [
      "docs/experiments/raw/technical-combination-semantics-2026-10-02/qualification/qualification.json",
      "docs/experiments/raw/technical-combination-semantics-2026-10-02/controller/qualification-review.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：not_supported；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。

## ARCHIVE｜自动数表归档

本轮固定组合未获得相对两个单独条件的新增帮助；2025和2026上半年均微恶化。完整原文映射、收益、风险、机会数、反例与限制见 [用户可读报告](prior-top-dual-break-information-2026-10-02.md)。此文件是受控流程自动数表；原生成文件与收据保留在 publication-01，0新增拟合。
