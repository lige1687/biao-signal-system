# green-black-state60-risk-2026-10-03（限定范围研究）

## 一句话结论（大白话）

证据不足。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：验证趋势状态的有限信息用途，不制定买卖、结束趋势或仓位规则
计划对象：510300.SS, 510050.SS, 510500.SS, 588000.SS；实际有报价：510050.SS, 510300.SS, 510500.SS, 588000.SS。
时期：['2022-01-04', '2026-06-30']；评价对象数量：948条、237个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | MSE | 33.644506 | 百分点² | 948 | 237 | 4 |
| B0 | RMSE | 5.8003884 | 百分点 | 948 | 237 | 4 |
| B1 | MSE | 37.533367 | 百分点² | 948 | 237 | 4 |
| B1 | RMSE | 6.1264482 | 百分点 | 948 | 237 | 4 |
| B2 | MSE | 39.994406 | 百分点² | 948 | 237 | 4 |
| B2 | RMSE | 6.3241131 | 百分点 | 948 | 237 | 4 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 37.533367 | 39.994406 | -2.461039 | -6.557% | -6.68629 至 0.188115 | percentage_point_squared |
| B2 相对 B0 | 33.644506 | 39.994406 | -6.3499005 | -18.87% | -14.1078 至 -1.07994 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "observations": 4340,
    "ready_252": 4340,
    "eligible": 4096,
    "price_reset_rows": 0,
    "continuous252_or_indicator_missing": 0,
    "feature_ready": 4340,
    "per_asset": {
      "510300.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "eligible": 1024,
        "feature_ready": 1085,
        "price_reset_rows": 0
      },
      "510050.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "eligible": 1024,
        "feature_ready": 1085,
        "price_reset_rows": 0
      },
      "510500.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "eligible": 1024,
        "feature_ready": 1085,
        "price_reset_rows": 0
      },
      "588000.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "eligible": 1024,
        "feature_ready": 1085,
        "price_reset_rows": 0
      }
    },
    "definition_ref": "research.trend.green_black60_state@1.0.0",
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
    "evaluation_rows": 948,
    "evaluation_dates": 237
  },
  "descriptions": {
    "available": true,
    "population": "all_evaluable_observations (not restricted to forecast evaluation folds)",
    "raw_rows": 4340,
    "evaluable_rows": 4096,
    "common_prediction_rows": 948,
    "event_opportunities": 1571,
    "excluded": [
      {
        "id": "510300.SS|2026-03-31",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-01",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-02",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-03",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-07",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-08",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-09",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-10",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-13",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-14",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-15",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-16",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-17",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-20",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-21",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-22",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-23",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-24",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-27",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-28",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-29",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-04-30",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-06",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-07",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-08",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-11",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-12",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-13",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-14",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-15",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-18",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-19",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-20",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-21",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-22",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-25",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-26",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-27",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-28",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-05-29",
        "reason": "immature_label"
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
        "id": "510050.SS|2026-03-31",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-01",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-02",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-03",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-07",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-08",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-09",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-10",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-13",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-14",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-15",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-16",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-17",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-20",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-21",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-22",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-23",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-24",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-27",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-28",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-29",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-04-30",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-06",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-07",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-08",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-11",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-12",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-13",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-14",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-15",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-18",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-19",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-20",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-21",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-22",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-25",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-26",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-27",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-28",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-05-29",
        "reason": "immature_label"
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
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-17",
        "reason": "immature_label"
      },
      {
        "id": "510050.SS|2026-06-18",
        "reason": "immature_label"
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
        "id": "510500.SS|2026-03-31",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-01",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-02",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-03",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-07",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-08",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-09",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-10",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-13",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-14",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-15",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-16",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-17",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-20",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-21",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-22",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-23",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-24",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-27",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-28",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-29",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-04-30",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-06",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-07",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-08",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-11",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-12",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-13",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-14",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-15",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-18",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-19",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-20",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-21",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-22",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-25",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-26",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-27",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-28",
        "reason": "immature_label"
      },
      {
        "id": "510500.SS|2026-05-29",
        "reason": "immature_label"
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
        "id": "588000.SS|2026-03-31",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-01",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-02",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-03",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-07",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-08",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-09",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-10",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-13",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-14",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-15",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-16",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-17",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-20",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-21",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-22",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-23",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-24",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-27",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-28",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-29",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-04-30",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-06",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-07",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-08",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-11",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-12",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-13",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-14",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-15",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-18",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-19",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-20",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-21",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-22",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-25",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-26",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-27",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-28",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-05-29",
        "reason": "immature_label"
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
        "mean": 7.342490825955762,
        "rows": 2525,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      },
      {
        "condition": 1,
        "mean": 6.462097929133037,
        "rows": 1571,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      }
    ],
    "common_asset_year": [
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2022",
        "weight": 0.05,
        "rows0": 210,
        "rows1": 32,
        "mean0": 8.680961111814216,
        "mean1": 10.129172382639942,
        "overall": 8.872460122832495,
        "share1": 0.1322314049586777
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2023",
        "weight": 0.05,
        "rows0": 173,
        "rows1": 69,
        "mean0": 6.718983856782581,
        "mean1": 6.4293570826280355,
        "overall": 6.63640432200298,
        "share1": 0.28512396694214875
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2024",
        "weight": 0.05,
        "rows0": 112,
        "rows1": 130,
        "mean0": 4.080582681708557,
        "mean1": 5.025767124633829,
        "overall": 4.5883263907180005,
        "share1": 0.5371900826446281
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2025",
        "weight": 0.05,
        "rows0": 100,
        "rows1": 143,
        "mean0": 3.2984744713560916,
        "mean1": 2.600801322894282,
        "overall": 2.8879096144423517,
        "share1": 0.588477366255144
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2026",
        "weight": 0.05,
        "rows0": 16,
        "rows1": 39,
        "mean0": 3.1754829203947788,
        "mean1": 6.043623444271187,
        "overall": 5.209255291870776,
        "share1": 0.7090909090909091
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2022",
        "weight": 0.05,
        "rows0": 214,
        "rows1": 28,
        "mean0": 8.541820626747176,
        "mean1": 9.012183143632507,
        "overall": 8.596242736138867,
        "share1": 0.11570247933884298
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2023",
        "weight": 0.05,
        "rows0": 186,
        "rows1": 56,
        "mean0": 5.8021924490864585,
        "mean1": 7.110870096128963,
        "overall": 6.1050269459227415,
        "share1": 0.23140495867768596
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2024",
        "weight": 0.05,
        "rows0": 99,
        "rows1": 143,
        "mean0": 3.6245625710102223,
        "mean1": 3.8761133571863855,
        "overall": 3.773206217387046,
        "share1": 0.5909090909090909
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2025",
        "weight": 0.05,
        "rows0": 57,
        "rows1": 186,
        "mean0": 2.73067095703448,
        "mean1": 2.073565224794822,
        "overall": 2.2277011372954827,
        "share1": 0.7654320987654321
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2026",
        "weight": 0.05,
        "rows0": 25,
        "rows1": 30,
        "mean0": 4.623042119605092,
        "mean1": 9.11332234005865,
        "overall": 7.072285876216124,
        "share1": 0.5454545454545454
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2022",
        "weight": 0.05,
        "rows0": 179,
        "rows1": 63,
        "mean0": 9.03866641865728,
        "mean1": 9.512848441725396,
        "overall": 9.16211049904278,
        "share1": 0.2603305785123967
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2023",
        "weight": 0.05,
        "rows0": 178,
        "rows1": 64,
        "mean0": 9.546797432442977,
        "mean1": 5.019134022838864,
        "overall": 8.34939884477908,
        "share1": 0.2644628099173554
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2024",
        "weight": 0.05,
        "rows0": 150,
        "rows1": 92,
        "mean0": 6.850881352132437,
        "mean1": 9.280238860408826,
        "overall": 7.774438751973048,
        "share1": 0.38016528925619836
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2025",
        "weight": 0.05,
        "rows0": 101,
        "rows1": 142,
        "mean0": 2.67288579089622,
        "mean1": 4.679128824514951,
        "overall": 3.8452582632166306,
        "share1": 0.5843621399176955
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2026",
        "weight": 0.05,
        "rows0": 9,
        "rows1": 46,
        "mean0": 2.5378095219199883,
        "mean1": 10.171630433136896,
        "overall": 8.922459738574128,
        "share1": 0.8363636363636363
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2022",
        "weight": 0.05,
        "rows0": 207,
        "rows1": 35,
        "mean0": 12.590099410550149,
        "mean1": 18.619731105904407,
        "overall": 13.462153581365849,
        "share1": 0.1446280991735537
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2023",
        "weight": 0.05,
        "rows0": 193,
        "rows1": 49,
        "mean0": 11.176510930730705,
        "mean1": 8.897151992427737,
        "overall": 10.714987839917296,
        "share1": 0.2024793388429752
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2024",
        "weight": 0.05,
        "rows0": 175,
        "rows1": 67,
        "mean0": 8.211820155622728,
        "mean1": 6.2499086549699445,
        "overall": 7.668646310400677,
        "share1": 0.2768595041322314
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2025",
        "weight": 0.05,
        "rows0": 118,
        "rows1": 125,
        "mean0": 3.7079521837552467,
        "mean1": 7.634917227196939,
        "overall": 5.727995930381632,
        "share1": 0.51440329218107
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2026",
        "weight": 0.05,
        "rows0": 23,
        "rows1": 32,
        "mean0": 7.394726598169134,
        "mean1": 15.377084926054787,
        "overall": 12.03900780712079,
        "share1": 0.5818181818181818
      }
    ],
    "unsupported_strata": [],
    "comparison_available": true,
    "common_support_rows": 4096,
    "common_support_assets": 4,
    "fixed_common_means": {
      "condition0": 6.250246178020828,
      "condition1": 7.842827500402367,
      "difference": 1.5925813223815393,
      "baseline": 7.181763811079939,
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
- 绿黑状态仅表示已知价格关系，不代表交易触发；行动资料历史到达时间仍未知。
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B1
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B0
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "四固定国内ETF身份与经济OHLC可逐行核；历史到达和行动完整性有限，不扩大范围",
    "source_refs": [
      "docs/experiments/raw/green-black-state-information-2026-10-03/risk/qualification.json",
      "docs/experiments/raw/green-black-state-information-2026-10-03/brief.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "60严格方向是20原判据的同周期研究尺度代理，保留灰未知；不含全系统判断，不改原文",
    "source_refs": [
      "docs/experiments/raw/green-black-state-information-2026-10-03/risk/qualification.json",
      "docs/experiments/raw/green-black-state-information-2026-10-03/brief.json"
    ]
  },
  "method_fit": {
    "reason": "分类指标而非连续排序；固定背景和两候选列，训练只用先成熟资料，简单平均并列，样本秩和支持已审",
    "source_refs": [
      "docs/experiments/raw/green-black-state-information-2026-10-03/risk/qualification.json",
      "docs/experiments/raw/green-black-state-information-2026-10-03/brief.json"
    ]
  },
  "conclusion_scope": {
    "reason": "较晚年份全已见，只能有限历史证据；预测和分组不等于资金增量，不接管转黑重置趋势研究",
    "source_refs": [
      "docs/experiments/raw/green-black-state-information-2026-10-03/risk/qualification.json",
      "docs/experiments/raw/green-black-state-information-2026-10-03/brief.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：insufficient；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
