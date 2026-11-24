# T01-simple-top3-auxiliary-MAE20-forecast（限定范围研究）

## 一句话结论（大白话）

本次方法下未得到新增帮助的支持。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：顶部路标出现后重新评估风险；不构成持仓退出规则
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
| B1 | MSE | 13.779148 | 百分点² | 874 | 291 | 4 |
| B1 | RMSE | 3.7120274 | 百分点 | 874 | 291 | 4 |
| B2 | MSE | 13.784746 | 百分点² | 874 | 291 | 4 |
| B2 | RMSE | 3.7127815 | 百分点 | 874 | 291 | 4 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 13.779148 | 13.784746 | -0.0055987811 | -0.04063% | -0.0163512 至 0.00175409 | percentage_point_squared |
| B2 相对 B0 | 14.516891 | 13.784746 | 0.73214419 | 5.043% | 0.127217 至 1.33932 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "observations": 4340,
    "ready_252": 4340,
    "trend_up": 2069,
    "top_all": 828,
    "top_in_uptrend": 326,
    "eligible": 2009,
    "price_reset_rows": 0,
    "per_asset": {
      "510300.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "trend_up": 529,
        "top_all": 205,
        "top_in_uptrend": 83,
        "eligible": 508
      },
      "510050.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "trend_up": 550,
        "top_all": 190,
        "top_in_uptrend": 80,
        "eligible": 543
      },
      "510500.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "trend_up": 526,
        "top_all": 217,
        "top_in_uptrend": 86,
        "eligible": 515
      },
      "588000.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "trend_up": 464,
        "top_all": 216,
        "top_in_uptrend": 77,
        "eligible": 443
      }
    },
    "definition_ref": "research.structure.simple_top3@1.0.0",
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
    "event_opportunities": 319,
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
        "mean": 3.7419340449519733,
        "rows": 1690,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      },
      {
        "condition": 1,
        "mean": 3.359214601093799,
        "rows": 319,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      }
    ],
    "common_asset_year": [
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2022",
        "weight": 0.05,
        "rows0": 46,
        "rows1": 14,
        "mean0": 4.215447488822297,
        "mean1": 3.87971834819038,
        "overall": 4.137110689341517,
        "share1": 0.23333333333333334
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2023",
        "weight": 0.05,
        "rows0": 75,
        "rows1": 16,
        "mean0": 2.9515041419009362,
        "mean1": 3.97107877963148,
        "overall": 3.130770012271142,
        "share1": 0.17582417582417584
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2024",
        "weight": 0.05,
        "rows0": 111,
        "rows1": 26,
        "mean0": 3.266457763555346,
        "mean1": 2.324628583517986,
        "overall": 3.0877164593146786,
        "share1": 0.1897810218978102
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2025",
        "weight": 0.05,
        "rows0": 131,
        "rows1": 15,
        "mean0": 1.6904459953130253,
        "mean1": 1.527189259368465,
        "overall": 1.673673042989954,
        "share1": 0.10273972602739725
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2026",
        "weight": 0.05,
        "rows0": 65,
        "rows1": 9,
        "mean0": 3.3588939906832933,
        "mean1": 2.3803375137680525,
        "overall": 3.2398803651125205,
        "share1": 0.12162162162162163
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2022",
        "weight": 0.05,
        "rows0": 47,
        "rows1": 11,
        "mean0": 3.9711319833007637,
        "mean1": 3.6026869232182506,
        "overall": 3.9012544719058044,
        "share1": 0.1896551724137931
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2023",
        "weight": 0.05,
        "rows0": 83,
        "rows1": 15,
        "mean0": 3.8101820197642278,
        "mean1": 3.2176124689916987,
        "overall": 3.7194825987276166,
        "share1": 0.15306122448979592
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2024",
        "weight": 0.05,
        "rows0": 125,
        "rows1": 23,
        "mean0": 2.778275578513585,
        "mean1": 1.684520205012765,
        "overall": 2.608300081280349,
        "share1": 0.1554054054054054
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2025",
        "weight": 0.05,
        "rows0": 169,
        "rows1": 27,
        "mean0": 1.4747798230098452,
        "mean1": 1.3861715749110664,
        "overall": 1.46257358475134,
        "share1": 0.1377551020408163
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2026",
        "weight": 0.05,
        "rows0": 39,
        "rows1": 4,
        "mean0": 4.792703082366019,
        "mean1": 2.4054138771950533,
        "overall": 4.570629667931511,
        "share1": 0.09302325581395349
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2022",
        "weight": 0.05,
        "rows0": 72,
        "rows1": 14,
        "mean0": 5.2805781097232245,
        "mean1": 3.2890807414416883,
        "overall": 4.956380863723905,
        "share1": 0.16279069767441862
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2023",
        "weight": 0.05,
        "rows0": 61,
        "rows1": 17,
        "mean0": 2.2115161242785732,
        "mean1": 3.160974176370146,
        "overall": 2.4184492894780187,
        "share1": 0.21794871794871795
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2024",
        "weight": 0.05,
        "rows0": 81,
        "rows1": 20,
        "mean0": 4.9469885399494595,
        "mean1": 3.4895262029372853,
        "overall": 4.6583821365807125,
        "share1": 0.19801980198019803
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2025",
        "weight": 0.05,
        "rows0": 145,
        "rows1": 21,
        "mean0": 3.016693388837976,
        "mean1": 3.7746635029999007,
        "overall": 3.1125811743644847,
        "share1": 0.12650602409638553
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2026",
        "weight": 0.05,
        "rows0": 71,
        "rows1": 13,
        "mean0": 5.241376089422839,
        "mean1": 4.594026463022418,
        "overall": 5.141191028194202,
        "share1": 0.15476190476190477
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2022",
        "weight": 0.05,
        "rows0": 34,
        "rows1": 13,
        "mean0": 6.209425029139226,
        "mean1": 7.278348049918882,
        "overall": 6.505084588078281,
        "share1": 0.2765957446808511
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2023",
        "weight": 0.05,
        "rows0": 71,
        "rows1": 15,
        "mean0": 4.182191141861598,
        "mean1": 2.8608650666369377,
        "overall": 3.9517272915317148,
        "share1": 0.1744186046511628
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2024",
        "weight": 0.05,
        "rows0": 64,
        "rows1": 13,
        "mean0": 5.240299238577348,
        "mean1": 3.7490118671732153,
        "overall": 4.988523448600027,
        "share1": 0.16883116883116883
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2025",
        "weight": 0.05,
        "rows0": 149,
        "rows1": 22,
        "mean0": 4.443066276718168,
        "mean1": 4.985315116174802,
        "overall": 4.5128292853032335,
        "share1": 0.1286549707602339
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2026",
        "weight": 0.05,
        "rows0": 51,
        "rows1": 11,
        "mean0": 9.060552613006593,
        "mean1": 5.742006726830358,
        "overall": 8.471778342878553,
        "share1": 0.1774193548387097
      }
    ],
    "unsupported_strata": [],
    "comparison_available": true,
    "common_support_rows": 2009,
    "common_support_assets": 4,
    "fixed_common_means": {
      "condition0": 4.107125420937217,
      "condition1": 3.465158772365542,
      "difference": -0.6419666485716755,
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
- 严格三日形态仅为原文简单顶部的窄子集；收盘后已知，不代表立即退出。
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B1
- 不同年份的改善方向相反，不能视作跨年份稳定帮助。
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "四国内宽基ETF已有完整经济OHLC；仅该历史池。",
    "source_refs": [
      "docs/experiments/raw/top-structure-information-2026-09-30/protocol.md",
      "docs/experiments/raw/top-structure-information-2026-09-30/source-audit-controller-review.md",
      "docs/experiments/raw/top-structure-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/top-structure-information-2026-09-30/execution/qualification.json",
      "docs/experiments/raw/top-structure-information-2026-09-30/controller-input-audit.json",
      "docs/experiments/raw/top-structure-information-2026-09-30/execution-contract.json",
      "docs/experiments/raw/top-structure-information-2026-09-30/statistics/run_summary.py",
      "docs/experiments/raw/top-structure-information-2026-09-30/statistics/preparation-log.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "严格三日降高降低是原文简单构造的窄子集，非全部顶部。",
    "source_refs": [
      "docs/experiments/raw/top-structure-information-2026-09-30/protocol.md",
      "docs/experiments/raw/top-structure-information-2026-09-30/source-audit-controller-review.md",
      "docs/experiments/raw/top-structure-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/top-structure-information-2026-09-30/execution/qualification.json",
      "docs/experiments/raw/top-structure-information-2026-09-30/controller-input-audit.json",
      "docs/experiments/raw/top-structure-information-2026-09-30/execution-contract.json",
      "docs/experiments/raw/top-structure-information-2026-09-30/statistics/run_summary.py",
      "docs/experiments/raw/top-structure-information-2026-09-30/statistics/preparation-log.json"
    ]
  },
  "method_fit": {
    "reason": "299成熟顶部160可配、139不可配，固定背景与时间评价；不调整参数。",
    "source_refs": [
      "docs/experiments/raw/top-structure-information-2026-09-30/protocol.md",
      "docs/experiments/raw/top-structure-information-2026-09-30/source-audit-controller-review.md",
      "docs/experiments/raw/top-structure-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/top-structure-information-2026-09-30/execution/qualification.json",
      "docs/experiments/raw/top-structure-information-2026-09-30/controller-input-audit.json",
      "docs/experiments/raw/top-structure-information-2026-09-30/execution-contract.json",
      "docs/experiments/raw/top-structure-information-2026-09-30/statistics/run_summary.py",
      "docs/experiments/raw/top-structure-information-2026-09-30/statistics/preparation-log.json"
    ]
  },
  "conclusion_scope": {
    "reason": "条件关联和固定预测误差仅支持历史风险信息，不支持交易或完整顶部判断。",
    "source_refs": [
      "docs/experiments/raw/top-structure-information-2026-09-30/protocol.md",
      "docs/experiments/raw/top-structure-information-2026-09-30/source-audit-controller-review.md",
      "docs/experiments/raw/top-structure-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/top-structure-information-2026-09-30/execution/qualification.json",
      "docs/experiments/raw/top-structure-information-2026-09-30/controller-input-audit.json",
      "docs/experiments/raw/top-structure-information-2026-09-30/execution-contract.json",
      "docs/experiments/raw/top-structure-information-2026-09-30/statistics/run_summary.py",
      "docs/experiments/raw/top-structure-information-2026-09-30/statistics/preparation-log.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：not_supported；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
