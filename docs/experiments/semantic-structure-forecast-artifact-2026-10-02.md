# semantic-structure-2026-10-02（限定范围研究）

## 一句话结论（大白话）

证据不足。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：最新顶部失效是否解除后续收益警示
计划对象：510300.SS, 510050.SS, 510500.SS, 588000.SS；实际有报价：510050.SS, 510300.SS, 510500.SS, 588000.SS。
时期：['2022-01-04', '2026-06-30']；评价对象数量：656条、230个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | MSE | 39.701312 | 百分点² | 656 | 230 | 4 |
| B0 | RMSE | 6.3008977 | 百分点 | 656 | 230 | 4 |
| B1 | MSE | 55.431312 | 百分点² | 656 | 230 | 4 |
| B1 | RMSE | 7.4452208 | 百分点 | 656 | 230 | 4 |
| B2 | MSE | 55.016797 | 百分点² | 656 | 230 | 4 |
| B2 | RMSE | 7.4173308 | 百分点 | 656 | 230 | 4 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 55.431312 | 55.016797 | 0.41451553 | 0.7478% | -0.030993 至 0.957973 | percentage_point_squared |
| B2 相对 B0 | 39.701312 | 55.016797 | -15.315485 | -38.58% | -33.8376 至 -0.85221 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "observations": 4340,
    "ready_252": 4340,
    "active_before_today": 2531,
    "first_invalidated": 219,
    "eligible": 2483,
    "price_reset_rows": 0,
    "continuous252_or_indicator_missing": 0,
    "no_previous_active_top": 1809,
    "feature_ready": 2531,
    "per_asset": {
      "510300.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "active_before_today": 637,
        "first_invalidated": 52,
        "eligible": 627,
        "feature_ready": 637,
        "no_previous_active_top": 448,
        "price_reset_rows": 0
      },
      "510050.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "active_before_today": 685,
        "first_invalidated": 59,
        "eligible": 673,
        "feature_ready": 685,
        "no_previous_active_top": 400,
        "price_reset_rows": 0
      },
      "510500.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "active_before_today": 596,
        "first_invalidated": 55,
        "eligible": 582,
        "no_previous_active_top": 489,
        "feature_ready": 596,
        "price_reset_rows": 0
      },
      "588000.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "active_before_today": 613,
        "first_invalidated": 53,
        "eligible": 601,
        "no_previous_active_top": 472,
        "feature_ready": 613,
        "price_reset_rows": 0
      }
    },
    "definition_ref": "research.structure.simple_top3_invalidation@1.0.0",
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
    "evaluation_rows": 656,
    "evaluation_dates": 230
  },
  "descriptions": {
    "available": true,
    "population": "all_evaluable_observations (not restricted to forecast evaluation folds)",
    "raw_rows": 4340,
    "evaluable_rows": 2483,
    "common_prediction_rows": 656,
    "event_opportunities": 213,
    "excluded": [
      {
        "id": "510300.SS|2022-04-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-04-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-04-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-05-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-05-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-05-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-06-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-07-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-07-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-07-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-07-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-07-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-08-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-08-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-08-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-08-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-08-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-08-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-08-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-09-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-09-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-09-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-10-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-10-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-10-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-10-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-11-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2022-12-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-01-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-02-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-03-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-03-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-03-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-03-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-04-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-04-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-04-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-04-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-04-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-04-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-04-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-04-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-04-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-05-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-05-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-06-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-06-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-06-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-06-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-06-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-06-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-06-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-06-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-06-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-06-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-06-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-06-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-07-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-07-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-07-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-07-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-07-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-07-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-07-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-08-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-08-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-08-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-08-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-08-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-09-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-09-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-09-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-09-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-09-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-10-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-11-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-11-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-11-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-11-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-11-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-11-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-11-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-11-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-11-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-12-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-12-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-12-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2023-12-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-01-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-01-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-01-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-01-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-01-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-02-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-02-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-02-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-02-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-02-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-02-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-02-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-02-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-02-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-02-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-02-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-03-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-04-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-04-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-04-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-04-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-04-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-04-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-04-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-04-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-04-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-04-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-04-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-04-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-05-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-06-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-06-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-07-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-07-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-07-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-07-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-07-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-07-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-07-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-07-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-08-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-08-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-08-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-08-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-09-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-09-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-09-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-09-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-09-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-09-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-09-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-09-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-09-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-10-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-10-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-10-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-10-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-10-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-10-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-10-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-10-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-10-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-10-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-10-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-10-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-11-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-11-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-11-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-11-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-11-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-11-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-11-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-11-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-12-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-12-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-12-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-12-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-12-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2024-12-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-01-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-01-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-01-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-01-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-01-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-01-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-01-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-01-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-02-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-03-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-03-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-03-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-03-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-03-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-03-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-05-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-05-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-05-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-05-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-05-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-05-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-05-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-05-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-05-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-06-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-07-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-08-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-09-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-10-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-10-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-10-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-10-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-10-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-10-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-11-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-12-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-12-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-12-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-12-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-12-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-12-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-12-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2025-12-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-01-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-02-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-02-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-02-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-04-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-05-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-05-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-05-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-05-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-05-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-05-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-05-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-05-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-05-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-05-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-05-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-05-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-06-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-06-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-06-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-06-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-06-05",
        "reason": "no_previous_active_top"
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
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-06-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-06-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-06-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-06-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-06-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510300.SS|2026-06-30",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2022-01-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-01-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-01-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-02-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-02-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-02-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-02-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-02-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-02-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-02-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-02-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-02-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-02-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-02-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-03-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-03-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-03-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-03-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-03-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-04-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-04-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-04-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-04-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-04-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-04-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-04-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-05-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-05-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-06-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-07-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-07-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-07-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-07-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-07-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-08-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-08-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-08-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-09-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-09-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-09-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-09-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-09-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-09-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-09-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-09-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-11-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2022-12-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-01-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-02-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-04-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-04-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-04-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-05-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-05-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-05-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-06-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-06-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-06-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-06-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-07-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-07-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-07-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-07-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-07-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-07-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-07-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-08-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-08-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-08-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-08-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-08-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-09-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-09-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-09-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-09-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-09-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-11-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-11-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-11-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-11-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2023-12-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-01-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-01-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-01-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-01-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-01-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-01-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-01-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-02-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-02-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-02-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-02-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-02-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-02-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-02-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-02-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-02-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-03-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-03-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-03-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-03-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-03-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-04-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-04-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-04-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-04-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-04-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-04-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-04-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-04-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-04-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-04-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-04-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-04-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-05-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-07-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-07-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-07-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-07-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-07-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-07-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-08-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-08-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-08-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-08-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-09-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-09-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-09-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-09-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-09-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-09-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-09-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-10-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-11-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-12-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-12-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-12-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-12-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-12-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-12-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-12-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-12-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-12-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2024-12-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-01-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-01-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-02-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-03-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-03-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-03-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-03-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-03-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-03-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-03-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-03-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-03-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-03-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-05-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-05-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-05-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-05-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-05-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-05-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-05-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-05-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-06-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-06-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-06-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-06-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-06-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-07-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-08-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-08-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-08-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-08-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-08-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-08-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-08-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-08-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-08-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-08-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-08-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-08-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-09-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-09-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-09-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-09-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-09-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-10-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-10-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-10-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-10-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-10-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-10-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-10-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-10-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-10-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-11-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-11-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-11-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-11-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-11-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-12-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-12-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-12-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-12-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-12-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-12-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-12-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-12-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-12-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-12-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2025-12-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-01-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-01-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-01-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-01-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-01-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-01-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-01-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-01-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-01-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-02-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-03-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-03-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-04-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-04-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-04-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-04-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-04-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-04-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-04-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-04-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-04-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-04-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-04-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-04-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-04-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-05-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-05-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-05-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-05-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-05-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-05-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-05-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-05-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-05-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-06-01",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-02",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-03",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-04",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-05",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-08",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-09",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-10",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-11",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-12",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-15",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-06-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-06-18",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-06-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-06-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-06-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-06-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-06-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510050.SS|2026-06-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-01-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-01-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-01-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-02-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-02-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-02-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-02-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-02-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-02-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-02-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-02-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-03-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-03-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-03-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-03-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-03-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-03-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-04-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-04-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-04-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-05-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-05-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-05-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-05-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-05-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-05-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-05-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-05-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-05-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-05-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-05-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-05-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-06-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-07-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-07-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-07-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-07-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-07-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-07-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-07-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-07-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-07-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-07-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-08-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-08-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-08-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-08-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-08-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-08-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-08-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-09-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-09-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-09-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-09-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-09-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-09-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-09-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-10-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-10-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-10-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-10-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-10-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-10-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-10-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-10-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-10-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-10-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-10-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-10-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-10-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-11-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-11-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-11-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-11-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-11-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-11-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-11-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-11-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-11-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-11-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-11-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-11-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-11-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-12-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-12-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-12-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-12-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-12-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-12-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-12-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-12-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-12-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2022-12-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-01-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-02-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-02-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-02-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-02-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-02-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-02-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-02-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-02-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-02-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-02-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-02-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-02-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-03-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-03-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-03-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-03-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-03-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-03-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-03-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-03-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-03-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-03-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-03-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-04-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-04-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-04-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-04-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-04-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-04-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-06-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-06-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-06-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-06-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-06-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-06-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-06-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-07-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-07-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-07-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-07-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-07-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-07-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-07-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-07-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-07-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-07-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-07-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-08-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-08-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-08-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-08-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-08-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-08-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-08-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-08-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-09-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-09-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-09-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-09-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-09-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-10-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-11-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-12-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-12-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-12-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-12-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-12-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2023-12-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-01-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-01-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-01-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-01-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-01-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-01-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-02-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-02-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-02-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-02-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-02-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-02-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-02-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-02-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-02-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-02-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-02-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-03-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-04-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-04-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-04-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-04-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-04-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-04-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-04-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-05-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-05-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-05-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-05-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-05-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-05-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-05-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-05-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-05-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-07-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-07-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-07-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-07-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-07-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-07-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-07-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-07-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-08-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-08-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-08-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-08-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-08-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-08-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-08-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-09-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-09-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-09-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-09-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-09-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-09-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-09-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-09-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-09-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-09-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-10-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-10-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-10-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-11-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-11-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-11-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-11-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-11-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-11-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-11-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-12-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-12-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-12-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-12-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-12-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2024-12-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-01-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-01-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-02-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-03-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-04-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-04-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-04-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-04-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-05-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-05-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-05-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-05-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-05-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-05-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-05-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-05-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-06-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-07-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-08-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-09-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-10-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-10-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-10-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-11-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-11-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-11-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-11-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-12-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-12-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-12-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-12-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-12-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-12-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-12-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-12-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-12-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-12-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2025-12-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-01-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-02-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-03-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-03-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-04-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-05-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-05-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-05-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-05-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-05-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-05-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-05-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-05-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-05-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-06-01",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-02",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-03",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-04",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-05",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-08",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-09",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-10",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-11",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-12",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-06-15",
        "reason": "immature_label"
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
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-06-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-06-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-06-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-06-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-06-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-06-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "510500.SS|2026-06-30",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2022-01-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-01-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-01-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-01-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-01-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-01-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-02-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-02-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-02-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-02-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-02-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-02-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-02-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-03-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-03-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-03-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-03-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-03-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-03-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-03-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-03-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-03-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-03-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-03-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-03-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-03-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-04-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-04-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-04-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-05-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-06-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-06-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-06-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-06-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-06-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-06-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-06-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-06-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-06-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-07-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-07-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-07-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-07-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-07-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-07-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-07-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-07-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-08-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-08-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-08-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-08-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-08-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-08-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-08-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-08-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-08-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-09-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-09-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-09-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-09-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-09-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-09-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-09-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-09-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-09-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-09-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-09-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-09-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-10-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-10-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-10-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-10-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-10-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-10-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-10-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-11-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-11-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-11-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-11-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-11-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-11-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-11-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-12-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-12-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-12-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-12-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2022-12-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-01-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-01-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-01-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-01-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-01-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-01-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-01-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-01-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-01-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-01-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-01-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-01-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-01-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-02-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-03-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-04-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-05-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-05-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-05-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-05-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-06-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-06-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-06-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-06-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-06-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-06-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-06-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-06-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-06-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-08-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-08-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-08-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-08-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-08-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-08-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-08-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-08-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-08-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-09-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-09-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-09-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-09-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-09-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-09-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-09-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-09-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-09-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-10-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-10-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-10-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-10-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-10-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-10-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-10-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-11-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-11-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-11-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-11-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-11-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-11-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-11-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-11-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-11-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-11-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-11-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-12-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-12-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-12-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-12-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2023-12-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-01-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-01-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-02-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-02-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-02-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-02-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-02-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-02-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-02-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-02-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-02-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-02-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-02-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-03-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-03-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-03-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-03-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-03-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-03-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-03-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-03-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-03-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-03-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-03-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-03-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-04-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-05-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-05-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-05-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-06-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-07-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-07-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-07-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-07-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-07-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-07-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-07-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-07-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-07-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-07-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-07-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-07-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-08-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-08-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-08-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-09-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-09-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-09-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-09-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-09-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-10-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-11-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-11-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-11-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-11-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-11-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-11-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-11-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-11-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-11-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-11-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-11-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2024-12-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-01-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-01-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-01-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-01-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-01-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-01-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-01-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-01-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-02-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-03-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-05-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-05-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-05-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-05-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-05-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-06-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-06-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-06-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-06-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-06-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-06-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-06-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-06-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-06-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-06-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-06-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-06-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-06-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-04",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-07-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-08-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-09-01",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-09-02",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-09-03",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-09-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-09-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-09-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-09-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-09-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-09-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-09-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-09-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-09-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-09-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-10-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-10-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-10-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-10-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-10-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-10-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-10-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-10-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-12-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2025-12-31",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-05",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-01-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-09",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-10",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-16",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-17",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-04-30",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-06",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-07",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-08",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-11",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-12",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-13",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-14",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-15",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-19",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-20",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-21",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-27",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-28",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-05-29",
        "reason": "no_previous_active_top"
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
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-06-18",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-06-22",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-06-23",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-06-24",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-06-25",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-06-26",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-06-29",
        "reason": "no_previous_active_top"
      },
      {
        "id": "588000.SS|2026-06-30",
        "reason": "no_previous_active_top"
      }
    ],
    "own_group": [
      {
        "condition": 0,
        "mean": 0.5450733790685334,
        "rows": 2270,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      },
      {
        "condition": 1,
        "mean": 0.8699434932665705,
        "rows": 213,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      }
    ],
    "common_asset_year": [
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2022",
        "weight": 0.05,
        "rows0": 150,
        "rows1": 10,
        "mean0": -2.295252170974218,
        "mean1": 0.5688492664314792,
        "overall": -2.1162458311363617,
        "share1": 0.0625
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2023",
        "weight": 0.05,
        "rows0": 157,
        "rows1": 11,
        "mean0": -1.497065405194543,
        "mean1": -1.2799046061294774,
        "overall": -1.482846543350997,
        "share1": 0.06547619047619048
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2024",
        "weight": 0.05,
        "rows0": 118,
        "rows1": 14,
        "mean0": 2.6797154718682274,
        "mean1": 2.9493740651828415,
        "overall": 2.708315625704626,
        "share1": 0.10606060606060606
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2025",
        "weight": 0.05,
        "rows0": 107,
        "rows1": 11,
        "mean0": 1.4317395413168497,
        "mean1": 1.4256278728377192,
        "overall": 1.4311698095094731,
        "share1": 0.09322033898305085
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2026",
        "weight": 0.05,
        "rows0": 44,
        "rows1": 5,
        "mean0": 1.3220842876172079,
        "mean1": 0.2448873309284542,
        "overall": 1.2121662308122332,
        "share1": 0.10204081632653061
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2022",
        "weight": 0.05,
        "rows0": 126,
        "rows1": 12,
        "mean0": -1.0517627725973018,
        "mean1": -0.6837230006047754,
        "overall": -1.0197593141631691,
        "share1": 0.08695652173913043
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2023",
        "weight": 0.05,
        "rows0": 184,
        "rows1": 9,
        "mean0": -1.1697859824955574,
        "mean1": -3.213440796437015,
        "overall": -1.2650859479125165,
        "share1": 0.046632124352331605
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2024",
        "weight": 0.05,
        "rows0": 123,
        "rows1": 14,
        "mean0": 2.9636299730235347,
        "mean1": 0.8542220008182991,
        "overall": 2.7480700342580366,
        "share1": 0.10218978102189781
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2025",
        "weight": 0.05,
        "rows0": 128,
        "rows1": 16,
        "mean0": 2.257423811123125,
        "mean1": 0.9220202744756127,
        "overall": 2.109045640384512,
        "share1": 0.1111111111111111
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2026",
        "weight": 0.05,
        "rows0": 55,
        "rows1": 6,
        "mean0": -1.3944435214170827,
        "mean1": 0.05423670877588638,
        "overall": -1.2519503840210526,
        "share1": 0.09836065573770492
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2022",
        "weight": 0.05,
        "rows0": 117,
        "rows1": 14,
        "mean0": -0.9631295889057934,
        "mean1": 0.6533081280221532,
        "overall": -0.7903805199211271,
        "share1": 0.10687022900763359
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2023",
        "weight": 0.05,
        "rows0": 130,
        "rows1": 14,
        "mean0": -1.2549664238077574,
        "mean1": -3.1529151827502444,
        "overall": -1.4394892198160547,
        "share1": 0.09722222222222222
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2024",
        "weight": 0.05,
        "rows0": 139,
        "rows1": 13,
        "mean0": 1.586544277662678,
        "mean1": 2.827530564932057,
        "overall": 1.6926812627580854,
        "share1": 0.08552631578947369
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2025",
        "weight": 0.05,
        "rows0": 98,
        "rows1": 10,
        "mean0": 3.434134442354879,
        "mean1": 4.555112847937809,
        "overall": 3.537928739168114,
        "share1": 0.09259259259259259
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2026",
        "weight": 0.05,
        "rows0": 45,
        "rows1": 2,
        "mean0": 1.1414738130924102,
        "mean1": 1.50652713329385,
        "overall": 1.1570079969307692,
        "share1": 0.0425531914893617
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2022",
        "weight": 0.05,
        "rows0": 127,
        "rows1": 15,
        "mean0": -1.318585877694966,
        "mean1": -0.5967788222522982,
        "overall": -1.242338653528487,
        "share1": 0.1056338028169014
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2023",
        "weight": 0.05,
        "rows0": 129,
        "rows1": 13,
        "mean0": -1.9634341788012872,
        "mean1": -2.314268314175594,
        "overall": -1.9955527968285127,
        "share1": 0.09154929577464789
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2024",
        "weight": 0.05,
        "rows0": 122,
        "rows1": 14,
        "mean0": 5.943331744049878,
        "mean1": 4.178389732598517,
        "overall": 5.761646536988708,
        "share1": 0.10294117647058823
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2025",
        "weight": 0.05,
        "rows0": 131,
        "rows1": 9,
        "mean0": 2.3477869661372024,
        "mean1": 4.687867813291867,
        "overall": 2.49822073488286,
        "share1": 0.06428571428571428
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2026",
        "weight": 0.05,
        "rows0": 40,
        "rows1": 1,
        "mean0": 2.127762954849638,
        "mean1": 28.339222614840963,
        "overall": 2.767066848995768,
        "share1": 0.024390243902439025
      }
    ],
    "unsupported_strata": [],
    "comparison_available": true,
    "common_support_rows": 2483,
    "common_support_assets": 4,
    "fixed_common_means": {
      "condition0": 0.7163600680603562,
      "condition1": 2.1263072816009054,
      "difference": 1.409947213540549,
      "baseline": 0.7509835124857454,
      "identity_error": 0.0,
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
- 最新最简三根顶部仅为研究代理；失效不是退出或再入场。
- 行动资料历史到达时间及完整性尚未认证。
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B0
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "四ETF全部安排日保留，实际经济OHLC来源够有限回顾性用途，历史到达未知。",
    "source_refs": [
      "docs/experiments/raw/semantic-mining-2026-10-02/structure-adapter/qualification.json",
      "docs/experiments/raw/semantic-mining-2026-10-02/controller/structure-adapter-review.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "原文路标破坏与出现不同；只继承三根形态，最新替换/一次退休明确为窄研究状态。",
    "source_refs": [
      "docs/experiments/raw/semantic-mining-2026-10-02/structure-adapter/qualification.json",
      "docs/experiments/raw/semantic-mining-2026-10-02/controller/structure-adapter-review.json"
    ]
  },
  "method_fit": {
    "reason": "X资格训练/评价支持[{'fold': {'train_end': '2024-12-31', 'eval_start': '2025-01-01', 'eval_end': '2025-12-31'}, 'train': 1728, 'train_true': 148, 'train_false': 1580, 'evaluation': 458, 'evaluation_true': 40, 'evaluation_false': 418}, {'fold': {'train_end': '2025-12-31', 'eval_start': '2026-01-01', 'eval_end': '2026-06-30'}, 'train': 2233, 'train_true': 193, 'train_false': 2040, 'evaluation': 198, 'evaluation_true': 14, 'evaluation_false': 184}]；只两个固定线性模型，简单均值并列。",
    "source_refs": [
      "docs/experiments/raw/semantic-mining-2026-10-02/structure-adapter/qualification.json",
      "docs/experiments/raw/semantic-mining-2026-10-02/controller/structure-adapter-review.json"
    ]
  },
  "conclusion_scope": {
    "reason": "只测试20日未来涨跌，五期限风险/收益分组仅描述；不优化账户或反向改技术规则。",
    "source_refs": [
      "docs/experiments/raw/semantic-mining-2026-10-02/structure-adapter/qualification.json",
      "docs/experiments/raw/semantic-mining-2026-10-02/controller/structure-adapter-review.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：insufficient；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
