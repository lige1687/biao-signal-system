# green-black-state60-return-2026-10-03（限定范围研究）

## 一句话结论（大白话）

本次方法下未得到新增帮助的支持。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：验证趋势状态的有限信息用途，不制定买卖、结束趋势或仓位规则
计划对象：510300.SS, 510050.SS, 510500.SS, 588000.SS；实际有报价：510050.SS, 510300.SS, 510500.SS, 588000.SS。
时期：['2022-01-04', '2026-06-30']；评价对象数量：948条、237个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | MSE | 198.84054 | 百分点² | 948 | 237 | 4 |
| B0 | RMSE | 14.101083 | 百分点 | 948 | 237 | 4 |
| B1 | MSE | 260.06332 | 百分点² | 948 | 237 | 4 |
| B1 | RMSE | 16.126479 | 百分点 | 948 | 237 | 4 |
| B2 | MSE | 261.44174 | 百分点² | 948 | 237 | 4 |
| B2 | RMSE | 16.16916 | 百分点 | 948 | 237 | 4 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 260.06332 | 261.44174 | -1.3784182 | -0.53% | -9.20479 至 8.38211 | percentage_point_squared |
| B2 相对 B0 | 198.84054 | 261.44174 | -62.6012 | -31.48% | -138.676 至 -2.23804 | percentage_point_squared |

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
        "mean": 2.5054617872000016,
        "rows": 2525,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      },
      {
        "condition": 1,
        "mean": 0.7733219544929602,
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
        "mean0": -0.6367296456512559,
        "mean1": -8.845287005868315,
        "overall": -1.7221587180766518,
        "share1": 0.1322314049586777
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2023",
        "weight": 0.05,
        "rows0": 173,
        "rows1": 69,
        "mean0": -3.3659333391370088,
        "mean1": -4.304944278425126,
        "overall": -3.63366786314891,
        "share1": 0.28512396694214875
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2024",
        "weight": 0.05,
        "rows0": 112,
        "rows1": 130,
        "mean0": 11.440641050190537,
        "mean1": -1.858793469345968,
        "overall": 4.296316721513904,
        "share1": 0.5371900826446281
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2025",
        "weight": 0.05,
        "rows0": 100,
        "rows1": 143,
        "mean0": 6.170500285382928,
        "mean1": 4.953226197847678,
        "overall": 5.45416203633955,
        "share1": 0.588477366255144
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2026",
        "weight": 0.05,
        "rows0": 16,
        "rows1": 39,
        "mean0": 8.083331228740441,
        "mean1": 2.3805492869747344,
        "overall": 4.0395403973065775,
        "share1": 0.7090909090909091
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2022",
        "weight": 0.05,
        "rows0": 214,
        "rows1": 28,
        "mean0": -1.0146492459522876,
        "mean1": -8.248258607576059,
        "overall": -1.851595783660823,
        "share1": 0.11570247933884298
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2023",
        "weight": 0.05,
        "rows0": 186,
        "rows1": 56,
        "mean0": -2.059343396960658,
        "mean1": -5.47127871228186,
        "overall": -2.848882147613498,
        "share1": 0.23140495867768596
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2024",
        "weight": 0.05,
        "rows0": 99,
        "rows1": 143,
        "mean0": 9.902860561822738,
        "mean1": -0.2419194498955801,
        "overall": 3.9082178276255504,
        "share1": 0.5909090909090909
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2025",
        "weight": 0.05,
        "rows0": 57,
        "rows1": 186,
        "mean0": 3.951659038484934,
        "mean1": 4.126735852733204,
        "overall": 4.085668451860153,
        "share1": 0.7654320987654321
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2026",
        "weight": 0.05,
        "rows0": 25,
        "rows1": 30,
        "mean0": -0.2870425018789535,
        "mean1": -4.15515678044149,
        "overall": -2.3969230174585183,
        "share1": 0.5454545454545454
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2022",
        "weight": 0.05,
        "rows0": 179,
        "rows1": 63,
        "mean0": 0.5259210695588209,
        "mean1": -4.233361560393659,
        "overall": -0.7130657308007088,
        "share1": 0.2603305785123967
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2023",
        "weight": 0.05,
        "rows0": 178,
        "rows1": 64,
        "mean0": -4.493094391620101,
        "mean1": -3.288964135030734,
        "overall": -4.1746467204559705,
        "share1": 0.2644628099173554
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2024",
        "weight": 0.05,
        "rows0": 150,
        "rows1": 92,
        "mean0": 9.110611657835234,
        "mean1": -3.8066636281938564,
        "overall": 4.199911962320042,
        "share1": 0.38016528925619836
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2025",
        "weight": 0.05,
        "rows0": 101,
        "rows1": 142,
        "mean0": 11.287941690891756,
        "mean1": 8.282107434632723,
        "overall": 9.531445952666314,
        "share1": 0.5843621399176955
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2026",
        "weight": 0.05,
        "rows0": 9,
        "rows1": 46,
        "mean0": 14.972295021629687,
        "mean1": 1.164054116695875,
        "overall": 3.423584446594135,
        "share1": 0.8363636363636363
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2022",
        "weight": 0.05,
        "rows0": 207,
        "rows1": 35,
        "mean0": -2.2981193217192453,
        "mean1": -9.959903736279845,
        "overall": -3.4062286378747038,
        "share1": 0.1446280991735537
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2023",
        "weight": 0.05,
        "rows0": 193,
        "rows1": 49,
        "mean0": -6.154035418763795,
        "mean1": -5.837786665619561,
        "overall": -6.090001580317236,
        "share1": 0.2024793388429752
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2024",
        "weight": 0.05,
        "rows0": 175,
        "rows1": 67,
        "mean0": 11.004858998048629,
        "mean1": 4.553612447106033,
        "overall": 9.218770076919894,
        "share1": 0.2768595041322314
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2025",
        "weight": 0.05,
        "rows0": 118,
        "rows1": 125,
        "mean0": 14.190395549229166,
        "mean1": 4.971442697295531,
        "overall": 9.44813585173244,
        "share1": 0.51440329218107
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2026",
        "weight": 0.05,
        "rows0": 23,
        "rows1": 32,
        "mean0": 31.214752286918092,
        "mean1": 10.077850867611799,
        "overall": 18.916918733867156,
        "share1": 0.5818181818181818
      }
    ],
    "unsupported_strata": [],
    "comparison_available": true,
    "common_support_rows": 4096,
    "common_support_assets": 4,
    "fixed_common_means": {
      "condition0": 5.5773410588524825,
      "condition1": -0.9871369564227236,
      "difference": -6.564478015275206,
      "baseline": 2.4842751129669347,
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
- 不同年份的改善方向相反，不能视作跨年份稳定帮助。
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "四固定国内ETF身份与经济OHLC可逐行核；历史到达和行动完整性有限，不扩大范围",
    "source_refs": [
      "docs/experiments/raw/green-black-state-information-2026-10-03/return/qualification.json",
      "docs/experiments/raw/green-black-state-information-2026-10-03/brief.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "60严格方向是20原判据的同周期研究尺度代理，保留灰未知；不含全系统判断，不改原文",
    "source_refs": [
      "docs/experiments/raw/green-black-state-information-2026-10-03/return/qualification.json",
      "docs/experiments/raw/green-black-state-information-2026-10-03/brief.json"
    ]
  },
  "method_fit": {
    "reason": "分类指标而非连续排序；固定背景和两候选列，训练只用先成熟资料，简单平均并列，样本秩和支持已审",
    "source_refs": [
      "docs/experiments/raw/green-black-state-information-2026-10-03/return/qualification.json",
      "docs/experiments/raw/green-black-state-information-2026-10-03/brief.json"
    ]
  },
  "conclusion_scope": {
    "reason": "较晚年份全已见，只能有限历史证据；预测和分组不等于资金增量，不接管转黑重置趋势研究",
    "source_refs": [
      "docs/experiments/raw/green-black-state-information-2026-10-03/return/qualification.json",
      "docs/experiments/raw/green-black-state-information-2026-10-03/brief.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：not_supported；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
