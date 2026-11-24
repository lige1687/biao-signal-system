# D01-future-deduction-box20-10-MAE20-information（限定范围研究）

## 一句话结论（大白话）

证据不足。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：原文条件推演的后续下探风险信息；不形成买卖信号
计划对象：510300.SS, 510050.SS, 510500.SS, 588000.SS；实际有报价：510050.SS, 510300.SS, 510500.SS, 588000.SS。
时期：['2022-01-04', '2026-06-30']；评价对象数量：89条、58个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | MSE | 14.2912 | 百分点² | 89 | 58 | 4 |
| B0 | RMSE | 3.7803704 | 百分点 | 89 | 58 | 4 |
| B1 | MSE | 15.515417 | 百分点² | 89 | 58 | 4 |
| B1 | RMSE | 3.9389614 | 百分点 | 89 | 58 | 4 |
| B2 | MSE | 15.244384 | 百分点² | 89 | 58 | 4 |
| B2 | RMSE | 3.9044057 | 百分点 | 89 | 58 | 4 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 15.515417 | 15.244384 | 0.2710328 | 1.747% | -0.404498 至 1.08568 | percentage_point_squared |
| B2 相对 B0 | 14.2912 | 15.244384 | -0.95318397 | -6.67% | -3.69385 至 1.88133 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "observations": 4340,
    "ready_252": 4340,
    "context": 397,
    "eligible": 388,
    "price_reset_rows": 0,
    "per_asset": {
      "510300.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "context": 92,
        "eligible": 91
      },
      "510050.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "context": 106,
        "eligible": 101
      },
      "510500.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "context": 97,
        "eligible": 95
      },
      "588000.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "context": 102,
        "eligible": 101
      }
    },
    "definition_ref": "research.trend.future_deduction_box20_10@1.0.0",
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
    "evaluation_rows": 89,
    "evaluation_dates": 58
  },
  "descriptions": {
    "available": true,
    "population": "all_evaluable_observations (not restricted to forecast evaluation folds)",
    "raw_rows": 4340,
    "evaluable_rows": 388,
    "common_prediction_rows": 89,
    "event_opportunities": 0,
    "excluded": [
      {
        "id": "510300.SS|2022-01-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-01-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-05-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-07-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-08-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-09-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-10-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-11-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2022-12-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-01-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-03-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-05-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-07-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-08-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-09-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-10-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-11-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2023-12-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-01-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-02-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-04-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-05-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-06-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-07-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-08-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-09-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-10-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-11-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2024-12-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-01-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-04-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-07-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-09-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-10-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2025-12-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-01-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-02-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-02-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-02-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-02-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-02-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-02-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-04-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-24",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510300.SS|2026-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-01-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-05-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-07-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-08-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-09-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-10-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-11-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2022-12-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-01-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-05-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-07-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-08-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-09-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-10-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-11-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2023-12-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-01-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-02-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-03-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-04-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-05-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-06-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-07-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-08-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-09-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-10-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-11-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2024-12-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-01-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-04-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-04-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-04-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-04-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-04-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-04-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-04-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-07-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-09-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-10-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2025-12-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-01-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-02-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-02-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-02-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-02-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-02-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-02-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-04-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-12",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-16",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-17",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-22",
        "reason": "outside_early_ema_context"
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
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510050.SS|2026-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-01-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-02-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-02-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-02-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-02-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-02-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-02-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-02-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-02-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-02-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-02-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-05-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-05-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-05-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-05-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-05-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-05-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-05-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-07-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-08-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-09-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-10-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-10-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-10-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-10-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-10-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-10-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-10-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-10-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-11-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2022-12-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-01-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-01-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-01-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-01-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-01-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-03-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-05-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-07-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-08-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-09-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-10-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-11-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2023-12-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-01-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-02-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-02-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-02-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-02-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-02-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-02-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-02-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-03-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-04-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-05-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-06-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-07-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-09-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-10-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-11-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2024-12-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-01-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-04-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-07-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-09-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-10-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2025-12-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-01-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-04-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-12",
        "reason": "outside_early_ema_context"
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
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "510500.SS|2026-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-01-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-02-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-02-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-02-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-02-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-02-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-02-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-02-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-02-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-02-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-02-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-05-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-07-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-08-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-09-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-10-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-10-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-10-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-10-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-10-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-10-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-10-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-10-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-10-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-10-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-10-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-11-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2022-12-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-01-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-01-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-01-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-01-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-07-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-08-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-09-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-10-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-10-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-10-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-10-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-10-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-10-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-10-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-10-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-10-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-10-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-11-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2023-12-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-01-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-02-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-02-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-02-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-02-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-02-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-02-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-03-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-04-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-05-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-06-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-07-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-08-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-09-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-10-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-11-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2024-12-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-01-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-02-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-05-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-06-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-07-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-08-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-09-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-10-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-11-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2025-12-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-01-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-02-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-02-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-02-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-02-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-02-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-02-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-02-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-02-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-02-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-02-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-03-31",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-16",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-04-30",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-06",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-07",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-13",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-14",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-19",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-20",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-21",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-27",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-28",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-05-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-01",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-02",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-03",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-04",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-05",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-08",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-09",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-10",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-11",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-12",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-15",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-16",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-17",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-18",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-22",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-23",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-24",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-25",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-26",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-29",
        "reason": "outside_early_ema_context"
      },
      {
        "id": "588000.SS|2026-06-30",
        "reason": "outside_early_ema_context"
      }
    ],
    "own_group": [],
    "common_asset_year": [],
    "unsupported_strata": [],
    "comparison_available": false,
    "common_support_reason": "tested_condition unknown"
  }
}
```

## 反例和结论边界

评价期资料没有参与训练或标准化；已有资料是否曾用于挑选方法仍以研究家族记录为准，换名字不成为新验证。预测改善不直接代表投资收益。

- 逐行来源、行动与经济价格按V01来源数学重新核对；成交量不进入D01特征。
- 历史资料到达时间和全部行动完整性未认证；仅作回顾性经济价格研究。
- K10抵扣价盒仅为原文未来方框的固定两周研究代理；不推断买卖。
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B0
- 评价日期只容纳不足三个预定长度的日期段，允许的改善和恶化范围证据有限。
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。
- B2相对B0的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "四只已有来源资格的国内宽基ETF，限定历史池。",
    "source_refs": [
      "docs/experiments/raw/deduction-box-information-2026-09-30/protocol.md",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/qualification.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/input-rank.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/source-manifest.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/definition-card-suggestion.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/deduction-box-information-2026-09-30/describe.py",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution-budget.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/definition-card.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/controller-input-audit.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/adapter-controller-review.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/features.csv"
    ]
  },
  "proxy_fidelity": {
    "reason": "固定十日抵扣价盒顶只对应原文推演的一部分。",
    "source_refs": [
      "docs/experiments/raw/deduction-box-information-2026-09-30/protocol.md",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/qualification.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/input-rank.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/source-manifest.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/definition-card-suggestion.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/deduction-box-information-2026-09-30/describe.py",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution-budget.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/definition-card.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/controller-input-audit.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/adapter-controller-review.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/features.csv"
    ]
  },
  "method_fit": {
    "reason": "已知普通前高距离纳入九字段，先核X秩再比较同一观察。",
    "source_refs": [
      "docs/experiments/raw/deduction-box-information-2026-09-30/protocol.md",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/qualification.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/input-rank.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/source-manifest.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/definition-card-suggestion.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/deduction-box-information-2026-09-30/describe.py",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution-budget.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/definition-card.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/controller-input-audit.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/adapter-controller-review.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/features.csv"
    ]
  },
  "conclusion_scope": {
    "reason": "仅能讨论已见资料的下探预测误差，不能推出交易利润。",
    "source_refs": [
      "docs/experiments/raw/deduction-box-information-2026-09-30/protocol.md",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/qualification.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/input-rank.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/source-manifest.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/definition-card-suggestion.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/deduction-box-information-2026-09-30/describe.py",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution-budget.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/definition-card.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/controller-input-audit.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/adapter-controller-review.json",
      "docs/experiments/raw/deduction-box-information-2026-09-30/execution/features.csv"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：insufficient；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
