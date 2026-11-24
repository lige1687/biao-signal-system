# M01-ma-cluster-mae（限定范围研究）

## 一句话结论（大白话）

证据不足。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：检验原文均线聚散能否帮助候选入场的未来收益/下行风险判断；不定义密集区目标、触发或交易
计划对象：sh000300, sz399006；实际有报价：sh000300, sz399006。
时期：['2023-01-01', '2026-06-30']；评价对象数量：81条、43个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | MSE | 8.1749071 | 百分点² | 81 | 43 | 2 |
| B0 | RMSE | 2.8591794 | 百分点 | 81 | 43 | 2 |
| B1 | MSE | 9.7373223 | 百分点² | 81 | 43 | 2 |
| B1 | RMSE | 3.1204683 | 百分点 | 81 | 43 | 2 |
| B2 | MSE | 10.104431 | 百分点² | 81 | 43 | 2 |
| B2 | RMSE | 3.1787467 | 百分点 | 81 | 43 | 2 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 9.7373223 | 10.104431 | -0.36710854 | -3.77% | -0.874745 至 0.18834 | percentage_point_squared |
| B2 相对 B0 | 8.1749071 | 10.104431 | -1.9295237 | -23.6% | -5.87351 至 0.890379 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "observations": 356,
    "ready_252": 356,
    "trend_qualified": 173,
    "eligible": 165,
    "reset_rows": 0,
    "per_asset": {
      "sh000300": {
        "observations": 178,
        "ready_252": 178,
        "trend_qualified": 89,
        "eligible": 85
      },
      "sz399006": {
        "observations": 178,
        "ready_252": 178,
        "trend_qualified": 84,
        "eligible": 80
      }
    },
    "definition_ref": "research.trend.ma_cluster_width@1.0.0",
    "planned_assets": [
      "sh000300",
      "sz399006"
    ],
    "input_assets": [
      "sh000300",
      "sz399006"
    ],
    "input_missing_assets": [],
    "actual_assets": [
      "sh000300",
      "sz399006"
    ],
    "missing_assets": [],
    "partial": false,
    "evaluation_rows": 81,
    "evaluation_dates": 43
  },
  "descriptions": {
    "available": true,
    "population": "all_evaluable_observations (not restricted to forecast evaluation folds)",
    "raw_rows": 356,
    "evaluable_rows": 165,
    "common_prediction_rows": 81,
    "event_opportunities": 0,
    "excluded": [
      {
        "id": "sh000300|2023-04-21",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-04-28",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-05-05",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-05-12",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-05-19",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-05-26",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-06-02",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-06-09",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-06-16",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-06-21",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-06-30",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-07-07",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-07-14",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-07-21",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-07-28",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-08-04",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-08-11",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-08-18",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-08-25",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-09-01",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-09-08",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-09-15",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-09-22",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-09-28",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-10-13",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-10-20",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-10-27",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-11-03",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-11-10",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-11-17",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-11-24",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-12-01",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-12-08",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-12-15",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-12-22",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2023-12-29",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-01-05",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-01-12",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-01-19",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-01-26",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-02-02",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-02-08",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-02-23",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-03-01",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-06-14",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-06-21",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-06-28",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-07-05",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-07-12",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-07-19",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-07-26",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-08-02",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-08-09",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-08-16",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-08-23",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-08-30",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-09-06",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-09-13",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-09-20",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2024-09-27",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-01-03",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-01-10",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-01-17",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-01-24",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-01-27",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-02-07",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-02-14",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-02-21",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-03-07",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-03-14",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-03-28",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-04-03",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-04-11",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-04-18",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-04-25",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-04-30",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-05-09",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-05-16",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-05-23",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-05-30",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-06-06",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-06-13",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-06-20",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2025-06-27",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2026-02-06",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2026-03-27",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2026-04-03",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2026-04-10",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2026-04-17",
        "reason": "sma60_not_up"
      },
      {
        "id": "sh000300|2026-06-05",
        "reason": "immature_label"
      },
      {
        "id": "sh000300|2026-06-12",
        "reason": "immature_label"
      },
      {
        "id": "sh000300|2026-06-18",
        "reason": "immature_label"
      },
      {
        "id": "sh000300|2026-06-26",
        "reason": "immature_label"
      },
      {
        "id": "sz399006|2023-03-10",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-03-17",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-04-14",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-04-21",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-04-28",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-05-05",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-05-12",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-05-19",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-05-26",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-06-02",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-06-09",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-06-16",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-06-21",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-06-30",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-07-07",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-07-14",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-07-21",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-07-28",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-08-04",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-08-11",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-08-18",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-08-25",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-09-01",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-09-08",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-09-15",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-09-22",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-09-28",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-10-13",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-10-20",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-10-27",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-11-03",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-11-10",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-11-17",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-11-24",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-12-01",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-12-08",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-12-15",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-12-22",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2023-12-29",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-01-05",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-01-12",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-01-19",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-01-26",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-02-02",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-02-08",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-02-23",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-03-01",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-03-08",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-03-15",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-03-29",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-04-03",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-06-07",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-06-14",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-06-21",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-06-28",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-07-05",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-07-12",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-07-19",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-07-26",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-08-02",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-08-09",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-08-16",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-08-23",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-08-30",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-09-06",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-09-13",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-09-20",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2024-09-27",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-01-03",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-01-10",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-01-17",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-01-24",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-01-27",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-02-07",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-02-14",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-02-21",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-03-07",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-03-14",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-03-21",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-03-28",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-04-03",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-04-11",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-04-18",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-04-25",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-04-30",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-05-09",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-05-16",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-05-23",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-05-30",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-06-06",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-06-13",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-06-20",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2025-06-27",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2026-04-03",
        "reason": "sma60_not_up"
      },
      {
        "id": "sz399006|2026-06-05",
        "reason": "immature_label"
      },
      {
        "id": "sz399006|2026-06-12",
        "reason": "immature_label"
      },
      {
        "id": "sz399006|2026-06-18",
        "reason": "immature_label"
      },
      {
        "id": "sz399006|2026-06-26",
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

- 仅限腾讯历史指数价格代理；不是官方全收益、可成交资产或账户收益。
- 日期绑定现存深交所日历；未独立认证沪市日历与历史到达时点。
- 供应商指数点位只用于历史信息研究；六线宽度不是完整密集区，也不是交易触发。
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B1
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B0
- 不同年份的改善方向相反，不能视作跨年份稳定帮助。
- 评价日期只容纳不足三个预定长度的日期段，允许的改善和恶化范围证据有限。
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。
- B2相对B0的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "两宽指有限点位历史适合诊断技术趋势信息，不能代替ETF可交易财富或个股，相关来源不能当独立复现。",
    "source_refs": [
      "docs/experiments/raw/ma-cluster-information-2026-09-30/protocol.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/protocol-v2.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/source-audit.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/source-fingerprints.json",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/execution/qualification.json",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/execution/features.csv"
    ]
  },
  "proxy_fidelity": {
    "reason": "只保留当时六线聚散原公式；旧卡禁止comparison故另立新卡，六个月整理/历史目标边界未补造，不称完整密集区。",
    "source_refs": [
      "docs/experiments/raw/ma-cluster-information-2026-09-30/protocol.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/protocol-v2.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/source-audit.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/source-fingerprints.json",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/execution/qualification.json",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/execution/features.csv"
    ]
  },
  "method_fit": {
    "reason": "连续宽度173上行观察、16趋势段；66/121训练与47/34评价允许有限六字段固定比较；低于2%仅2例不拟合阈值，相关结构使证据有限。",
    "source_refs": [
      "docs/experiments/raw/ma-cluster-information-2026-09-30/protocol.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/protocol-v2.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/source-audit.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/source-fingerprints.json",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/execution/qualification.json",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/execution/features.csv"
    ]
  },
  "conclusion_scope": {
    "reason": "同期比B0/B1/B2，只判断特定模型中收益和下跌信息；全部历史已见，后期时间评价不是未见验证，也不直接推导真实交易收益。",
    "source_refs": [
      "docs/experiments/raw/ma-cluster-information-2026-09-30/protocol.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/protocol-v2.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/source-audit.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/source-fingerprints.json",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/execution/qualification.json",
      "docs/experiments/raw/ma-cluster-information-2026-09-30/execution/features.csv"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：insufficient；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
