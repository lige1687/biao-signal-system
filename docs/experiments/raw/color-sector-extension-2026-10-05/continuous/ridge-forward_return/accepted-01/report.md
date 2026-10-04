# color-sector-ridge-forward_return-2026-10-05（限定范围研究）

## 一句话结论（大白话）

证据不足。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：检验连续颜色表达的同日排序及额外预测帮助，非账户收益
计划对象：510300.SS, 510050.SS, 510500.SS, 588000.SS, 512170.SS, 512400.SS, 512480.SS, 512800.SS；实际有报价：510050.SS, 510300.SS, 510500.SS, 512170.SS, 512400.SS, 512480.SS, 512800.SS, 588000.SS。
时期：['2022-01-04', '2026-06-30']；评价对象数量：2536条、317个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | MSE | 60.399471 | 百分点² | 2536 | 317 | 8 |
| B0 | RMSE | 7.7717096 | 百分点 | 2536 | 317 | 8 |
| B1 | MSE | 65.533465 | 百分点² | 2536 | 317 | 8 |
| B1 | RMSE | 8.0952742 | 百分点 | 2536 | 317 | 8 |
| B2 | MSE | 64.901437 | 百分点² | 2536 | 317 | 8 |
| B2 | RMSE | 8.0561428 | 百分点 | 2536 | 317 | 8 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 65.533465 | 64.901437 | 0.63202761 | 0.9644% | -0.315266 至 1.60488 | percentage_point_squared |
| B2 相对 B0 | 60.399471 | 64.901437 | -4.5019668 | -7.454% | -12.5665 至 2.07371 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "scheduled": 8680,
    "eligible": 8262,
    "reasons": {
      "continuous20_unknown": 250,
      "feature_ready": 8430
    },
    "planned_assets": [
      "510300.SS",
      "510050.SS",
      "510500.SS",
      "588000.SS",
      "512170.SS",
      "512400.SS",
      "512480.SS",
      "512800.SS"
    ],
    "input_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "512170.SS",
      "512400.SS",
      "512480.SS",
      "512800.SS",
      "588000.SS"
    ],
    "input_missing_assets": [],
    "actual_assets": [
      "510050.SS",
      "510300.SS",
      "510500.SS",
      "512170.SS",
      "512400.SS",
      "512480.SS",
      "512800.SS",
      "588000.SS"
    ],
    "missing_assets": [],
    "partial": false,
    "evaluation_rows": 2536,
    "evaluation_dates": 317
  },
  "descriptions": {
    "available": true,
    "population": "all_evaluable_observations (not restricted to forecast evaluation folds)",
    "raw_rows": 8680,
    "evaluable_rows": 8262,
    "common_prediction_rows": 2536,
    "event_opportunities": 0,
    "excluded": [
      {
        "id": "510050.SS|2022-01-04",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-05",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-06",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-07",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-10",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-12",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-13",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-14",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-17",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-18",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-19",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-20",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-21",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-24",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-25",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-26",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510050.SS|2022-01-27",
        "reason": "continuous20_unknown"
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
        "id": "510300.SS|2022-01-04",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-05",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-06",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-07",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-10",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-12",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-13",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-14",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-17",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-18",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-19",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-20",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-21",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-24",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-25",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-26",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510300.SS|2022-01-27",
        "reason": "continuous20_unknown"
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
        "id": "510500.SS|2022-01-04",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-05",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-06",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-07",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-10",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-12",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-13",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-14",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-17",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-18",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-19",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-20",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-21",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-24",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-25",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-26",
        "reason": "continuous20_unknown"
      },
      {
        "id": "510500.SS|2022-01-27",
        "reason": "continuous20_unknown"
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
        "id": "512170.SS|2022-01-04",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-05",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-06",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-07",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-10",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-12",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-13",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-14",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-17",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-18",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-19",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-20",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-21",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-24",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-25",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-26",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-27",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-01-28",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-07",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-08",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-09",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-10",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-14",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-15",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-16",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-17",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-18",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-21",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-22",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-23",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-24",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-25",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-02-28",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-01",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-02",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-03",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-04",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-07",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-08",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-09",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-10",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-14",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-15",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-16",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-17",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-18",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-21",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-22",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-23",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-24",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-25",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-28",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-29",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-30",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-03-31",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-04-01",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2022-04-06",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512170.SS|2026-06-01",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-02",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-03",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-04",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-05",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-08",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-09",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-10",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-11",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-12",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-15",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-16",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-17",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-18",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-22",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-23",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-24",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-25",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-26",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-29",
        "reason": "immature_label"
      },
      {
        "id": "512170.SS|2026-06-30",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2022-01-04",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-05",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-06",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-07",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-10",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-12",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-13",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-14",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-17",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-18",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-19",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-20",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-21",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-24",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-25",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-26",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2022-01-27",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512400.SS|2026-06-01",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-02",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-03",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-04",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-05",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-08",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-09",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-10",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-11",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-12",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-15",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-16",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-17",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-18",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-22",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-23",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-24",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-25",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-26",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-29",
        "reason": "immature_label"
      },
      {
        "id": "512400.SS|2026-06-30",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2022-01-04",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-05",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-06",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-07",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-10",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-12",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-13",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-14",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-17",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-18",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-19",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-20",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-21",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-24",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-25",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-26",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-27",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-01-28",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-07",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-08",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-09",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-10",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-14",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-15",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-16",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-17",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-18",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-21",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-22",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-23",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-24",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-25",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-02-28",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-01",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-02",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-03",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-04",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-07",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-08",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-09",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-10",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-14",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-15",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-16",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-17",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-18",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-21",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-22",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-23",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-24",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-25",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-28",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-29",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-30",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-03-31",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-01",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-06",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-07",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-08",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-12",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-13",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-14",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-15",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-18",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-19",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-20",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-21",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-22",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-25",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-26",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-27",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-28",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-04-29",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-05-05",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-05-06",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-05-09",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-05-10",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2022-05-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512480.SS|2026-06-01",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-02",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-03",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-04",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-05",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-08",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-09",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-10",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-11",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-12",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-15",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-16",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-17",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-18",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-22",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-23",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-24",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-25",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-26",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-29",
        "reason": "immature_label"
      },
      {
        "id": "512480.SS|2026-06-30",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2022-01-04",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-05",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-06",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-07",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-10",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-12",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-13",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-14",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-17",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-18",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-19",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-20",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-21",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-24",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-25",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-26",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2022-01-27",
        "reason": "continuous20_unknown"
      },
      {
        "id": "512800.SS|2026-06-01",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-02",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-03",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-04",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-05",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-08",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-09",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-10",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-11",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-12",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-15",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-16",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-17",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-18",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-22",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-23",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-24",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-25",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-26",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-29",
        "reason": "immature_label"
      },
      {
        "id": "512800.SS|2026-06-30",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2022-01-04",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-05",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-06",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-07",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-10",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-11",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-12",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-13",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-14",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-17",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-18",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-19",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-20",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-21",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-24",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-25",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-26",
        "reason": "continuous20_unknown"
      },
      {
        "id": "588000.SS|2022-01-27",
        "reason": "continuous20_unknown"
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

- Source and owner qualification are hash-bound; economic prices are retrospective.
- In-memory OHLC roundoff correction: 13 rows, maximum 1.1102230246251565e-16; closes and source files unchanged.
- Historical action arrival and tradable results are not certified.
- Eight-ETF colors describe past states, not trade signals.
- Overlapping daily outcomes and sector ETFs are dependent observations.
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B0
- 不同年份的改善方向相反，不能视作跨年份稳定帮助。
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。
- B2相对B0的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "8fixedETFs; broad/sector and gaps explicitly qualified; evidence not whole ETF population",
    "source_refs": [
      "docs/experiments/raw/color-sector-extension-2026-10-05/brief.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "全日三色保留；绿色占比不等于旧EMA占比，价格距离复用旧公式；排名不新增信息",
    "source_refs": [
      "docs/experiments/raw/color-sector-extension-2026-10-05/brief.json"
    ]
  },
  "method_fit": {
    "reason": "两折成熟训练，共同ETF日期权重，固定线性与浅树；来源组小须披露",
    "source_refs": [
      "docs/experiments/raw/color-sector-extension-2026-10-05/brief.json"
    ]
  },
  "conclusion_scope": {
    "reason": "历史同条件预测比较；报告证据不足或本范围未发现增量。小改善不等于赢过更强简单基线；完整账户/真正未见证据未覆盖",
    "source_refs": [
      "docs/experiments/raw/color-sector-extension-2026-10-05/brief.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：insufficient；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
