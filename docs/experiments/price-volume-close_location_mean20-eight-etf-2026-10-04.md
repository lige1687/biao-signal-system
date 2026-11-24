# price-volume-close_location_mean20-eight-etf-2026-10-04（限定范围研究）

## 一句话结论（大白话）

对固定的4只宽基和4只行业ETF，close_location_mean20让已有价格模型的平均平方错误少0.041，但加入后错误15.458，高于逐只ETF较早已成熟历史平均的14.058。六项一起核对后的改善范围仍容许变差，因此这项已见历史研究不支持新增技术规则，也不是实际交易收益。六项完整比较与反例见[综合报告](price-only-path-six-factor-eight-etf-2026-10-04.md)。

问题：过去20天收盘在日内高低区间的位置能否补充未来21个收盘节点的下探风险判断
计划对象：510300.SS, 510050.SS, 510500.SS, 588000.SS, 512480.SS, 512400.SS, 512800.SS, 512170.SS；实际有报价：510050.SS, 510300.SS, 510500.SS, 512170.SS, 512400.SS, 512480.SS, 512800.SS, 588000.SS。
时期：['2022-01-04', '2026-06-30']；评价对象数量：6072条、759个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | MSE | 15.084605 | 百分点² | 6072 | 759 | 8 |
| B0 | RMSE | 3.8838905 | 百分点 | 6072 | 759 | 8 |
| B1 | MSE | 15.498706 | 百分点² | 6072 | 759 | 8 |
| B1 | RMSE | 3.9368396 | 百分点 | 6072 | 759 | 8 |
| B2 | MSE | 15.457678 | 百分点² | 6072 | 759 | 8 |
| B2 | RMSE | 3.9316254 | 百分点 | 6072 | 759 | 8 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 15.498706 | 15.457678 | 0.041027777 | 0.2647% | -0.0302873 至 0.113153 | percentage_point_squared |
| B2 相对 B0 | 15.084605 | 15.457678 | -0.37307298 | -2.473% | -1.48309 至 0.589002 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "scheduled": 8680,
    "feature_ready": 8576,
    "eligible": 8408,
    "per_asset": {
      "510300.SS": {
        "scheduled": 1085,
        "feature_ready": 1085,
        "eligible": 1064
      },
      "510050.SS": {
        "scheduled": 1085,
        "feature_ready": 1085,
        "eligible": 1064
      },
      "510500.SS": {
        "scheduled": 1085,
        "feature_ready": 1085,
        "eligible": 1064
      },
      "588000.SS": {
        "scheduled": 1085,
        "feature_ready": 1085,
        "eligible": 1064
      },
      "512480.SS": {
        "scheduled": 1085,
        "feature_ready": 1022,
        "eligible": 1001
      },
      "512400.SS": {
        "scheduled": 1085,
        "feature_ready": 1085,
        "eligible": 1064
      },
      "512800.SS": {
        "scheduled": 1085,
        "feature_ready": 1085,
        "eligible": 1064
      },
      "512170.SS": {
        "scheduled": 1085,
        "feature_ready": 1044,
        "eligible": 1023
      }
    },
    "planned_assets": [
      "510300.SS",
      "510050.SS",
      "510500.SS",
      "588000.SS",
      "512480.SS",
      "512400.SS",
      "512800.SS",
      "512170.SS"
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
    "evaluation_rows": 6072,
    "evaluation_dates": 759
  },
  "descriptions": {
    "available": true,
    "population": "all_evaluable_observations (not restricted to forecast evaluation folds)",
    "raw_rows": 8680,
    "evaluable_rows": 8408,
    "common_prediction_rows": 6072,
    "event_opportunities": 0,
    "excluded": [
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
      },
      {
        "id": "512480.SS|2022-01-04",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-05",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-06",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-07",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-10",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-11",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-12",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-13",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-14",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-17",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-18",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-19",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-20",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-21",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-24",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-25",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-26",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-27",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-01-28",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-07",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-08",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-09",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-10",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-11",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-14",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-15",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-16",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-17",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-18",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-21",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-22",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-23",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-24",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-25",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-02-28",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-01",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-02",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-03",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-04",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-07",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-08",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-09",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-10",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-11",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-14",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-15",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-16",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-17",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-18",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-21",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-22",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-23",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-24",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-25",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-28",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-29",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-30",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-03-31",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-04-01",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-04-06",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-04-07",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-04-08",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512480.SS|2022-04-11",
        "reason": "background_or_window_unavailable"
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
        "id": "512170.SS|2022-01-04",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-05",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-06",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-07",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-10",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-11",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-12",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-13",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-14",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-17",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-18",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-19",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-20",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-21",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-24",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-25",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-26",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-27",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-01-28",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-07",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-08",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-09",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-10",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-11",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-14",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-15",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-16",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-17",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-18",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-21",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-22",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-23",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-24",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-25",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-02-28",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-03-01",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-03-02",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-03-03",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-03-04",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-03-07",
        "reason": "background_or_window_unavailable"
      },
      {
        "id": "512170.SS|2022-03-08",
        "reason": "background_or_window_unavailable"
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

- 回溯经济价与官方日线只证明固定源内计算；历史到达、完整个股覆盖和全部成交量单位变化未知。
- 回溯经济价与官方日线只证明固定源内计算；历史到达、完整个股覆盖和全部成交量单位变化未知。
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B0
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。
- B2相对B0的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "宽基及四个不同板块分开解释，样本是固定存续ETF，不把个股后验池混作代表样本。",
    "source_refs": [
      "docs/experiments/raw/price-volume-universe-qualification-2026-10-04/qualification.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "close_location_mean20仅描述过去20日价格路径，不充当LEI原始触发、过滤或交易规则。",
    "source_refs": [
      "configs/strategy-documents.v1.json"
    ]
  },
  "method_fit": {
    "reason": "用相同ETF、日期和未来风险目标，固定已有价格背景后只增加close_location_mean20；再比较逐ETF已成熟历史平均。",
    "source_refs": [
      "docs/archive/handoffs-plans/etf-price-volume-large-validation-2026-10-04.md"
    ]
  },
  "conclusion_scope": {
    "reason": "所有历史评价年份已见，历史到达及行动完整性未证，结果只能是回溯探索。",
    "source_refs": [
      "docs/experiments/raw/price-volume-universe-qualification-2026-10-04/qualification.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：insufficient；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
