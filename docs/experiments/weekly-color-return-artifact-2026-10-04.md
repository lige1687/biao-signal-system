# weekly-color-return-2026-10-04（限定范围研究）

## 一句话结论（大白话）

本次方法下未得到新增帮助的支持。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：判断日周共振是新增帮助、重复表达或不稳定；不引入交易过滤
计划对象：510300.SS, 510050.SS, 510500.SS, 588000.SS；实际有报价：510050.SS, 510300.SS, 510500.SS, 588000.SS。
时期：['2022-01-04', '2026-06-30']；评价对象数量：1268条、317个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | MSE | 44.124881 | 百分点² | 1268 | 317 | 4 |
| B0 | RMSE | 6.6426562 | 百分点 | 1268 | 317 | 4 |
| B1 | MSE | 192.6735 | 百分点² | 1268 | 317 | 4 |
| B1 | RMSE | 13.880688 | 百分点 | 1268 | 317 | 4 |
| B2 | MSE | 192.72225 | 百分点² | 1268 | 317 | 4 |
| B2 | RMSE | 13.882444 | 百分点 | 1268 | 317 | 4 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 192.6735 | 192.72225 | -0.048749619 | -0.0253% | -2.21085 至 2.09274 | percentage_point_squared |
| B2 相对 B0 | 44.124881 | 192.72225 | -148.59737 | -336.8% | -231.143 至 -71.0338 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "observations": 4340,
    "ready_252": 4340,
    "week_ready120": 3060,
    "eligible": 2976,
    "price_reset_rows": 0,
    "continuous252_or_indicator_missing": 0,
    "previous_week_unknown_or_warmup120": 1280,
    "feature_ready": 3060,
    "per_asset": {
      "510300.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "week_ready120": 765,
        "eligible": 744,
        "previous_week_unknown_or_warmup120": 320,
        "feature_ready": 765,
        "price_reset_rows": 0
      },
      "510050.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "week_ready120": 765,
        "eligible": 744,
        "previous_week_unknown_or_warmup120": 320,
        "feature_ready": 765,
        "price_reset_rows": 0
      },
      "510500.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "week_ready120": 765,
        "eligible": 744,
        "previous_week_unknown_or_warmup120": 320,
        "feature_ready": 765,
        "price_reset_rows": 0
      },
      "588000.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "week_ready120": 765,
        "eligible": 744,
        "previous_week_unknown_or_warmup120": 320,
        "feature_ready": 765,
        "price_reset_rows": 0
      }
    },
    "definition_ref": "research.trend.completed_week_color20@1.0.0",
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
    "evaluation_rows": 1268,
    "evaluation_dates": 317
  },
  "descriptions": {
    "available": true,
    "population": "all_evaluable_observations (not restricted to forecast evaluation folds)",
    "raw_rows": 4340,
    "evaluable_rows": 2976,
    "common_prediction_rows": 1268,
    "event_opportunities": 1416,
    "excluded": [
      {
        "id": "510300.SS|2022-01-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-01-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-02-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-03-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-04-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-05-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-06-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-07-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-08-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-09-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-10-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-11-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2022-12-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-01-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-02-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-03-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510300.SS|2023-04-28",
        "reason": "previous_week_unknown_or_warmup120"
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
        "id": "510050.SS|2022-01-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-01-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-02-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-03-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-04-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-05-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-06-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-07-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-08-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-09-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-10-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-11-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2022-12-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-01-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-02-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-03-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510050.SS|2023-04-28",
        "reason": "previous_week_unknown_or_warmup120"
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
        "id": "510500.SS|2022-01-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-01-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-02-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-03-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-04-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-05-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-06-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-07-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-08-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-09-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-10-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-11-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2022-12-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-01-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-02-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-03-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "510500.SS|2023-04-28",
        "reason": "previous_week_unknown_or_warmup120"
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
        "id": "588000.SS|2022-01-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-01-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-02-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-03-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-04-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-05-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-06-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-07-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-08-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-09-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-10-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-11-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2022-12-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-05",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-01-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-02-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-01",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-02",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-08",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-09",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-15",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-16",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-22",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-23",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-28",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-29",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-30",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-03-31",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-03",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-04",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-06",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-07",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-10",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-11",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-12",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-13",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-14",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-17",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-18",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-19",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-20",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-21",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-24",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-25",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-26",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-27",
        "reason": "previous_week_unknown_or_warmup120"
      },
      {
        "id": "588000.SS|2023-04-28",
        "reason": "previous_week_unknown_or_warmup120"
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
        "mean": 1.4568785216165887,
        "rows": 1560,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      },
      {
        "condition": 1,
        "mean": 1.0094842433709983,
        "rows": 1416,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      }
    ],
    "common_asset_year": [
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2023",
        "weight": 0.0625,
        "rows0": 154,
        "rows1": 10,
        "mean0": -1.691710468533584,
        "mean1": -4.324874553371899,
        "overall": -1.8522692541944568,
        "share1": 0.06097560975609756
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2024",
        "weight": 0.0625,
        "rows0": 129,
        "rows1": 113,
        "mean0": 4.1495625989323095,
        "mean1": -1.2531909207109382,
        "overall": 1.6267892612476527,
        "share1": 0.4669421487603306
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2025",
        "weight": 0.0625,
        "rows0": 51,
        "rows1": 192,
        "mean0": 1.9844856569492857,
        "mean1": 2.1196398497520117,
        "overall": 2.0912741549662544,
        "share1": 0.7901234567901234
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2026",
        "weight": 0.0625,
        "rows0": 14,
        "rows1": 81,
        "mean0": 7.566783661274803,
        "mean1": -0.30894446966584427,
        "overall": 0.8516891496306722,
        "share1": 0.8526315789473684
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2023",
        "weight": 0.0625,
        "rows0": 154,
        "rows1": 10,
        "mean0": -1.2813092328513818,
        "mean1": -2.989702385285349,
        "overall": -1.385479547024185,
        "share1": 0.06097560975609756
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2024",
        "weight": 0.0625,
        "rows0": 119,
        "rows1": 123,
        "mean0": 4.0162630310172105,
        "mean1": -0.9345041621704566,
        "overall": 1.499964003074719,
        "share1": 0.5082644628099173
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2025",
        "weight": 0.0625,
        "rows0": 36,
        "rows1": 207,
        "mean0": 1.6492092002427698,
        "mean1": 1.7872872805857491,
        "overall": 1.7668312686830858,
        "share1": 0.8518518518518519
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2026",
        "weight": 0.0625,
        "rows0": 51,
        "rows1": 44,
        "mean0": 0.8946741054757859,
        "mean1": -3.382371903017092,
        "overall": -1.0862735195103892,
        "share1": 0.4631578947368421
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2023",
        "weight": 0.0625,
        "rows0": 157,
        "rows1": 7,
        "mean0": -1.9361100604817996,
        "mean1": -3.263396266032386,
        "overall": -1.9927625204748125,
        "share1": 0.042682926829268296
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2024",
        "weight": 0.0625,
        "rows0": 166,
        "rows1": 76,
        "mean0": 2.438607852837688,
        "mean1": -1.4712287837490112,
        "overall": 1.2107252727526088,
        "share1": 0.3140495867768595
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2025",
        "weight": 0.0625,
        "rows0": 65,
        "rows1": 178,
        "mean0": 3.696371393801076,
        "mean1": 3.600092253075164,
        "overall": 3.625845932693207,
        "share1": 0.7325102880658436
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2026",
        "weight": 0.0625,
        "rows0": 14,
        "rows1": 81,
        "mean0": 10.220953196564864,
        "mean1": -0.7310996999223923,
        "overall": 0.8828870427178349,
        "share1": 0.8526315789473684
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2023",
        "weight": 0.0625,
        "rows0": 154,
        "rows1": 10,
        "mean0": -3.3719686416183663,
        "mean1": -3.2944645539385222,
        "overall": -3.3672427826134976,
        "share1": 0.06097560975609756
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2024",
        "weight": 0.0625,
        "rows0": 181,
        "rows1": 61,
        "mean0": 3.5234339277483193,
        "mean1": 0.5989531323508718,
        "overall": 2.7862714132059874,
        "share1": 0.25206611570247933
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2025",
        "weight": 0.0625,
        "rows0": 81,
        "rows1": 162,
        "mean0": 5.516484275360239,
        "mean1": 3.247720053801528,
        "overall": 4.003974794321099,
        "share1": 0.6666666666666666
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2026",
        "weight": 0.0625,
        "rows0": 34,
        "rows1": 61,
        "mean0": 12.055721661459714,
        "mean1": 1.122587937842208,
        "overall": 5.035498954715841,
        "share1": 0.6421052631578947
      }
    ],
    "unsupported_strata": [
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2022",
        "rows0": 0,
        "rows1": 0,
        "reason": "both states not observed"
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2022",
        "rows0": 0,
        "rows1": 0,
        "reason": "both states not observed"
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2022",
        "rows0": 0,
        "rows1": 0,
        "reason": "both states not observed"
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2022",
        "rows0": 0,
        "rows1": 0,
        "reason": "both states not observed"
      }
    ],
    "comparison_available": true,
    "common_support_rows": 2976,
    "common_support_assets": 4,
    "fixed_common_means": {
      "condition0": 3.0894657598861834,
      "condition1": -0.5923435744035223,
      "difference": -3.6818093342897056,
      "baseline": 0.9811077265119763,
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
- 周色仅用上一已完成ISO周；本周即使周五也不使用。这是保守延迟代理，不构成交易过滤。
- 无交易的日历周不伪造报价；连续周数按有报价的交易周计数。
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B1
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B0
- 不同年份的改善方向相反，不能视作跨年份稳定帮助。
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "固定已有经济四ETF，历史来源实际到达和行动完整性有限，不扩大池",
    "source_refs": [
      "docs/experiments/raw/weekly-color-information-2026-10-04/return/qualification.json",
      "docs/experiments/raw/weekly-color-information-2026-10-04/brief.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "原20周期判据应用于已完成交易周；上一ISO周才使用与120周暖启动为本轮保守代理，非完整共振事件或作者唯一标定",
    "source_refs": [
      "docs/experiments/raw/weekly-color-information-2026-10-04/return/qualification.json",
      "docs/experiments/raw/weekly-color-information-2026-10-04/brief.json"
    ]
  },
  "method_fit": {
    "reason": "分类状态不强排大小；固定共同支持、两历史折/零惩罚OLS及简单均值，周持续与20日重叠按日期核",
    "source_refs": [
      "docs/experiments/raw/weekly-color-information-2026-10-04/return/qualification.json",
      "docs/experiments/raw/weekly-color-information-2026-10-04/brief.json"
    ]
  },
  "conclusion_scope": {
    "reason": "周状态背景表达的信息，不是完整日周变色事件或真实交易增量；全部已见资料",
    "source_refs": [
      "docs/experiments/raw/weekly-color-information-2026-10-04/return/qualification.json",
      "docs/experiments/raw/weekly-color-information-2026-10-04/brief.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：not_supported；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
