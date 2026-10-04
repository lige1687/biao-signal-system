# bull-gray-origin-lightgbm-forward_return-2026-10-04（限定范围研究）

## 一句话结论（大白话）

本次方法下未得到新增帮助的支持。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：辅助判断多头灰色等待中未来收益和风险，非完整交易
计划对象：510300.SS, 510050.SS, 510500.SS, 588000.SS；实际有报价：510050.SS, 510300.SS, 510500.SS, 588000.SS。
时期：['2022-01-04', '2026-06-30']；评价对象数量：122条、80个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | MSE | 22.838707 | 百分点² | 122 | 80 | 4 |
| B0 | RMSE | 4.778986 | 百分点 | 122 | 80 | 4 |
| B1 | MSE | 16.847699 | 百分点² | 122 | 80 | 4 |
| B1 | RMSE | 4.1045948 | 百分点 | 122 | 80 | 4 |
| B2 | MSE | 16.847699 | 百分点² | 122 | 80 | 4 |
| B2 | RMSE | 4.1045948 | 百分点 | 122 | 80 | 4 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 16.847699 | 16.847699 | 0 | 0% | 0 至 0 | percentage_point_squared |
| B2 相对 B0 | 22.838707 | 16.847699 | 5.9910085 | 26.23% | -0.552157 至 12.5927 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "scheduled": 4340,
    "eligible": 315,
    "reasons": {
      "gray_origin_unknown": 2,
      "not_gray": 1447,
      "not_bull": 2568,
      "feature_ready": 323
    },
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
    "evaluation_rows": 122,
    "evaluation_dates": 80
  },
  "descriptions": {
    "available": true,
    "population": "all_evaluable_observations (not restricted to forecast evaluation folds)",
    "raw_rows": 4340,
    "evaluable_rows": 315,
    "common_prediction_rows": 122,
    "event_opportunities": 114,
    "excluded": [
      {
        "id": "510050.SS|2022-01-04",
        "reason": "gray_origin_unknown"
      },
      {
        "id": "510050.SS|2022-01-05",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-01-06",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-01-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-01-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-01-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-01-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-01-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-01-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-01-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-01-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-01-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-01-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-01-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-01-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-01-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-01-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-01-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-01-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-02-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-03",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-04",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-03-31",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-04-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-05-31",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-06-24",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-06-27",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-06-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-06-29",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-06-30",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-01",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-04",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-05",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-06",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-08",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-15",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-18",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-19",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-21",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-22",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-25",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-26",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-27",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-07-29",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-08-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-03",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-04",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-08-31",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-09-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-10-31",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-03",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-04",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-11-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-12-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-12-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-12-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-12-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-12-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-12-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2022-12-09",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-12-12",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-12-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-12-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-12-15",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-12-16",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-12-19",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-12-27",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-12-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-12-29",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2022-12-30",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-05",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-06",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-09",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-11",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-12",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-16",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-17",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-18",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-19",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-20",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-30",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-01-31",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-02-01",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-02-02",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-02-03",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-02-09",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-02-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-02-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-02-16",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-02-17",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-02-24",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-02-27",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-02-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-03-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-03-08",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-03-09",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-03-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-03-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-03-31",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-03",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-04",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-04-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-04",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-05-31",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-06-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-03",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-04",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-07-31",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-08-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-08-02",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-08-03",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-08-04",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-08-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-08-08",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-08-09",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-08-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-08-18",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-08-21",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-08-22",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2023-08-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-08-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-08-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-08-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-08-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-08-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-08-31",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-04",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-09-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-10-31",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-03",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-11-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-04",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2023-12-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-03",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-04",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-01-31",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-02-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-02-29",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-01",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-04",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-05",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-06",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-08",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-11",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-12",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-15",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-18",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-19",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-20",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-22",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-26",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-03-29",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-01",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-08",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-09",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-11",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-12",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-17",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-18",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-19",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-22",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-24",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-25",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-26",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-29",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-04-30",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-06",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-08",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-09",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-15",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-16",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-17",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-20",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-21",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-22",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-23",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-27",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-29",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-30",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-05-31",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-06-03",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-06-04",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-06-05",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-06-06",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-06-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-06-11",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-06-12",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-06-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-06-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-06-17",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-06-18",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-06-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-06-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-06-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-06-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-06-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-06-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-06-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-06-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-03",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-04",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-07-31",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-08-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-03",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-04",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-09-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-10-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-10-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-10-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-11",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-15",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-16",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-17",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-18",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-21",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-22",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-23",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-24",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-25",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-29",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-30",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-10-31",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-01",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-06",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-08",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-11",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-12",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-15",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-19",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-20",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-22",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-25",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-26",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-27",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-11-29",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-12-02",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-12-04",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-12-05",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-12-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-12-16",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-12-17",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2024-12-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-12-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-12-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-12-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-12-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-12-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-12-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-12-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2024-12-31",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-03",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-01-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-02-27",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-02-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-06",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-11",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-12",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-17",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-18",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-19",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-20",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-21",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-24",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-25",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-03-27",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-04-03",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-04-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-04-08",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-04-09",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-04-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-04-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-05-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-05-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-05-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-05-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-05-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-05-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-05-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-05-15",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-05-16",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-05-19",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-05-20",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-05-21",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-05-22",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-05-23",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-05-26",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-06",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-09",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-16",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-17",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-18",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-19",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-20",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-24",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-25",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-26",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-27",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-06-30",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-01",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-02",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-03",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-04",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-08",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-09",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-11",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-15",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-16",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-17",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-18",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-21",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-22",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-23",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-24",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-25",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-29",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-30",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-07-31",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-04",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-05",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-06",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-08",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-11",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-12",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-15",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-18",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-19",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-20",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-21",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-22",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-25",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-26",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-27",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-08-29",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-01",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-02",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-03",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-04",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-05",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-08",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-09",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-11",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-12",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-15",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-16",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-17",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-19",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-22",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-23",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-09-24",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-09",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-15",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-16",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-20",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-21",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-22",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-23",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-24",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-27",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-29",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-30",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-10-31",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-03",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-04",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-06",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-11",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-12",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-20",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-21",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-24",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-25",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-26",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-27",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-11-28",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-12-01",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-12-02",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-12-03",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-12-04",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-12-10",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2025-12-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2025-12-31",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-01-05",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-01-06",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-01-07",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-01-08",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-01-09",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-01-12",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-01-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-01-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-01-15",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-01-16",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-01-29",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-02-02",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-02-03",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-02-05",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-02-06",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-02-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-02-24",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-02-25",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-02-26",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-02-27",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-03-03",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-03-04",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-03-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-19",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-03-31",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-03",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-13",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-14",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-20",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-21",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-04-30",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-05-06",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-05-07",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-05-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-05-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-05-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-05-13",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-05-14",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-05-18",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-05-21",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-05-22",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-05-25",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-05-26",
        "reason": "not_gray"
      },
      {
        "id": "510050.SS|2026-05-27",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-05-28",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-05-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-01",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-02",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-03",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-04",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-05",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-08",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-09",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-10",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-11",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-12",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-15",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-16",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-17",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-18",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-22",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-23",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-24",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-25",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-26",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-29",
        "reason": "not_bull"
      },
      {
        "id": "510050.SS|2026-06-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-04",
        "reason": "gray_origin_unknown"
      },
      {
        "id": "510300.SS|2022-01-05",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-01-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-01-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-02-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-03",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-04",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-03-31",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-04-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-05-31",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-06-23",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-06-24",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-06-27",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-06-28",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-06-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-06-30",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-01",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-04",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-05",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-06",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-08",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-19",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-21",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-25",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-27",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-28",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-07-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-08-01",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-08-02",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-08-03",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-08-04",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-08-31",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-09-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-10-31",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-03",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-04",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-11-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-12-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-12-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-12-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-12-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-12-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-12-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-12-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-12-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-12-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-12-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2022-12-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-12-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-12-27",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-12-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2022-12-30",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-05",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-06",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-09",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-10",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-12",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-17",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-19",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-20",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-30",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-01-31",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-01",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-02",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-03",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-09",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-10",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-14",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-17",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-23",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-24",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-27",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-02-28",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-03-06",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-03-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-03-08",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-03-09",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-03-10",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-03-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-03-14",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-03-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-03-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-03-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-03-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-03-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-03-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-03-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-03-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-03-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-03-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-03-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-03-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-03-31",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-03",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-04",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-04-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-04",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-05-31",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-06-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-03",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-04",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-07-31",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-08-01",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-08-02",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-08-03",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-08-04",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-08-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-08-08",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-08-09",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-08-10",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-08-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-08-14",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-08-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-08-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2023-08-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-08-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-08-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-08-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-08-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-08-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-08-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-08-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-08-31",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-04",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-09-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-10-31",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-03",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-11-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-04",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2023-12-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-03",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-04",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-01-31",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-02-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-03-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-03-04",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-03-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-03-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-03-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-03-08",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-03-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-03-12",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-03-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-03-14",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-03-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-03-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-03-19",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-03-20",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-03-21",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-03-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-03-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-01",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-02",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-03",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-09",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-10",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-12",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-23",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-24",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-25",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-04-30",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-06",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-08",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-09",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-10",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-14",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-17",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-20",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-21",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-23",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-27",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-30",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-05-31",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-06-03",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-06-04",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-06-05",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-06-06",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-06-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-06-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-06-12",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-06-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-06-14",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-06-17",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-06-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-06-19",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-06-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-06-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-06-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-06-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-06-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-06-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-06-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-03",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-04",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-07-31",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-08-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-03",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-04",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-09-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-10-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-10-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-10-10",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-14",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-17",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-21",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-23",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-24",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-25",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-28",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-30",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-10-31",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-01",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-06",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-08",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-12",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-14",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-20",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-21",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-25",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-11-28",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-12-04",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-12-05",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-12-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-12-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-12-17",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-12-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-12-19",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-12-24",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2024-12-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-12-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-12-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-12-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2024-12-31",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-01-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-03",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-01-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-02-25",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-02-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-02-27",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-06",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-10",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-12",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-14",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-17",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-19",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-20",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-21",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-24",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-03-27",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-04-02",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-04-03",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-04-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-04-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-06",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-05-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-04",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-05",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-06",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-09",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-17",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-19",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-20",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-24",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-25",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-27",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-06-30",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-01",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-02",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-03",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-04",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-08",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-09",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-10",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-14",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-17",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-21",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-23",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-24",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-25",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-28",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-30",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-07-31",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-04",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-05",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-06",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-08",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-12",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-14",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-19",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-20",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-21",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-25",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-27",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-28",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-08-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-01",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-02",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-03",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-04",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-05",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-08",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-09",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-10",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-12",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-17",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-19",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-23",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-24",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-25",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-09-30",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-09",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-10",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-17",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-21",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-23",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-24",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-27",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-28",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-30",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-10-31",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-03",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-10",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-12",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-20",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-21",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-24",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-25",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-27",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2025-11-28",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-03",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-04",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-05",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-11",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-12",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-29",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2025-12-31",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-01-05",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-06",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-08",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-09",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-12",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-14",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-19",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-20",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-21",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-27",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-28",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-01-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-02-02",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-02-03",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-02-05",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-02-06",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-02-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-02-25",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-02-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-03-02",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-03-03",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-03-04",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-03-05",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-03-06",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-03-09",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-03-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-03-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-03-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-03-18",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-03-19",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-03-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-03-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-03-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-03-25",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-03-26",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-03-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-03-30",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-03-31",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-01",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-02",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-03",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-07",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-08",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-09",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-10",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-13",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-14",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-15",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-16",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-17",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-20",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-21",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-22",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-23",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-24",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-27",
        "reason": "not_bull"
      },
      {
        "id": "510300.SS|2026-04-28",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-04-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-04-30",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-06",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-07",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-08",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-12",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-13",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-14",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-19",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-20",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-25",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-27",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-28",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-05-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-01",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-02",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-03",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-04",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-05",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-08",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-09",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-10",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-11",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-12",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-15",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-16",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-17",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-18",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-22",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-23",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-24",
        "reason": "immature_label"
      },
      {
        "id": "510300.SS|2026-06-25",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-26",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-29",
        "reason": "not_gray"
      },
      {
        "id": "510300.SS|2026-06-30",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-01-04",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-01-06",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-01-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-01-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-01-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-01-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-01-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-01-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-01-17",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-01-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-01-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-01-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-01-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-01-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-01-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-01-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-01-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-01-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-02-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-03",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-03-31",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-04-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-05-31",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-06-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-06-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-06-23",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-06-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-06-27",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-06-28",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-06-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-06-30",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-01",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-04",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-05",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-06",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-08",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-19",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-07-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-02",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-03",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-04",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-08",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-09",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-16",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-17",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-19",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-23",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-08-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-09-01",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-09-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-09-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-10-31",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-03",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-11-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-11-23",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-11-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-11-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-11-30",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-01",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-02",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-05",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-06",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-08",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-09",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-16",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-19",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2022-12-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-12-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-12-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-12-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-12-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-12-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-12-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2022-12-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-03",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-01-31",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-02-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-02-02",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-03",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-06",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-08",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-09",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-16",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-23",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-27",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-02-28",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-01",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-02",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-03",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-06",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-09",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-16",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-17",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-03-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-03",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-04",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-06",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-17",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-19",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2023-04-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-04-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-04-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-05-31",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-06-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-03",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-07-31",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-03",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-08-31",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-09-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-10-31",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-03",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-11-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2023-12-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-03",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-01-31",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-02-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-03-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-03-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-03-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-03-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-03-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-03-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-03-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-03-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-03-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-03-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-03-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-03-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-03-19",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-03-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-03-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-03-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-03-26",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-03-27",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-03-28",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-03-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-01",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-02",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-03",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-16",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-19",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-23",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-26",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-04-30",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-06",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-08",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-09",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-16",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-17",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-30",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-05-31",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-06-03",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-06-04",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-06-05",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-06-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-06-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-03",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-07-31",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-08-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-03",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-09-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-10-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-10-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2024-10-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-16",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-17",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-23",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-28",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-30",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-10-31",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-01",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-04",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-06",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-08",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-26",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-27",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-28",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-11-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-12-02",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-12-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-12-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-12-17",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-12-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-12-19",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-12-30",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2024-12-31",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-01-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-03",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-01-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-02-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-02-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-02-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-02-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-02-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-02-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-02-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-02-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-02-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-02-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-02-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-02-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-02-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-02-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-02-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-02-26",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-02-27",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-04",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-05",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-06",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-17",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-19",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-26",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-27",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-03-31",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-04-01",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-04-02",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-04-03",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-04-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-04-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-04-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-05-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-03",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-06-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-06-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-06-26",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-06-27",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-06-30",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-01",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-02",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-03",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-04",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-08",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-09",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-16",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-17",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-23",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-28",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-30",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-07-31",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-01",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-04",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-05",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-06",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-08",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-19",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-26",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-27",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-28",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-08-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-01",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-02",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-03",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-05",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-08",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-09",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-16",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-17",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-19",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-23",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-26",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-09-30",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-09",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-16",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-17",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-23",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-27",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-28",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-10-30",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-11-03",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-11-04",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-11-05",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-11-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-11-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-11-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-11-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-11-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-11-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-11-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-11-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-11-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-11-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-11-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-03",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-04",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-05",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-11",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-12",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-18",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-19",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2025-12-30",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2025-12-31",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-05",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-06",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-08",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-09",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-16",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-19",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-21",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-23",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-26",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-27",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-28",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-01-30",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-02-03",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-02-04",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-02-09",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-02-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-02-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-02-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-02-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-02-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-02-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-02-26",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-02-27",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-02",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-03",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-04",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-05",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-06",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-09",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-17",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-19",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-23",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-03-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-03-25",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-03-26",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-03-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-03-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-03-31",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-01",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-02",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-03",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-07",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-08",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-09",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-10",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-13",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-14",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-15",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-16",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-17",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-20",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-21",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-22",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-23",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-24",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-27",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-28",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-29",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-04-30",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-05-06",
        "reason": "not_bull"
      },
      {
        "id": "510500.SS|2026-05-07",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-05-08",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-05-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-05-12",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-05-13",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-05-14",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-05-15",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-05-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-05-19",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-05-20",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-05-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-05-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-05-26",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-05-28",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-01",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-02",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-03",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-04",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-05",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-08",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-09",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-10",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-11",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-12",
        "reason": "not_gray"
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
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-18",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-22",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-23",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-24",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-25",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-26",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-29",
        "reason": "not_gray"
      },
      {
        "id": "510500.SS|2026-06-30",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-01-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-01-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-02-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-03-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-04-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-05-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-06-23",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-06-24",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-06-27",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-06-28",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-06-29",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-06-30",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-01",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-07",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-08",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-12",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-13",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-14",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-15",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-19",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-20",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-21",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-25",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-27",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-07-28",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-01",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-02",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-03",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-04",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-05",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-08",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-09",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-10",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-12",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-15",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-16",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-17",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-24",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-25",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-26",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-29",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-08-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-08-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-09-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-10-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-17",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-11-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-11-21",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2022-11-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-11-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2022-12-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-01-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-02-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-02-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-02-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-02-06",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-02-07",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-02-08",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-02-09",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-02-10",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-02-13",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-02-14",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-02-15",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-02-21",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-02-22",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-02-23",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-02-24",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-02-27",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-02-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-03-24",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-03-27",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-03-28",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-03-29",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-03-30",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-03-31",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-03",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-04",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-06",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-07",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-10",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-12",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-13",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-14",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-17",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-19",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-20",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-04-21",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-05-04",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-05-05",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-05-08",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-05-09",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-05-10",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-05-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-05-12",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-05-15",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-05-16",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-05-17",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-05-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2023-05-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-05-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-05-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-05-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-05-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-05-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-05-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-05-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-05-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-06-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-07-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-08-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-09-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-10-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-11-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2023-12-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-01-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-02-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-19",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-03-20",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-03-21",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-03-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-03-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-04-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-05-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-06-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-07-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-08-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-09-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-10-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-10-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2024-10-10",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-14",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-15",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-16",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-17",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-21",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-22",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-23",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-24",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-25",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-28",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-29",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-30",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-10-31",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-01",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-04",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-07",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-08",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-12",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-13",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-14",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-19",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-20",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-21",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-22",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-25",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-26",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-27",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-11-29",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-12-02",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-12-03",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-12-17",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-12-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-12-20",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-12-23",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-12-24",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-12-25",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-12-26",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-12-27",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-12-30",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2024-12-31",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-01-02",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-01-03",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-01-06",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-01-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-01-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-02-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-02-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-02-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-02-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-02-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-02-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-02-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-02-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-02-17",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-02-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-02-19",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-02-20",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-02-21",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-02-24",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-02-25",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-02-26",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-02-27",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-02-28",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-03",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-04",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-05",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-06",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-07",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-10",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-12",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-14",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-17",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-21",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-24",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-25",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-26",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-27",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-28",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-03-31",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-04-01",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-04-02",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-04-03",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-04-07",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-04-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-04-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-05-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-06-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-07-24",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-07-25",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-07-28",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-07-29",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-07-30",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-07-31",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-01",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-04",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-05",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-06",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-07",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-08",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-12",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-13",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-14",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-15",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-19",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-20",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-21",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-22",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-25",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-26",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-27",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-28",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-08-29",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-01",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-02",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-03",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-04",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-05",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-08",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-09",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-10",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-12",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-15",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-16",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-17",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-19",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-22",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-23",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-24",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-25",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-26",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-29",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-09-30",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-09",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-10",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-13",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-14",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-15",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-16",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-21",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-22",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-23",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-24",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-27",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-28",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-29",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-30",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-10-31",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-03",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-04",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-05",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-07",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-10",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-12",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-13",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-14",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-17",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-19",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-20",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2025-11-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-11-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-11-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-11-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-11-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-11-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-04",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-11",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-12",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2025-12-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-01-05",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-01-06",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-01-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-01-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-01-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-01-12",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-13",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-14",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-15",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-16",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-19",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-20",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-21",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-22",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-23",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-26",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-27",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-28",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-29",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-01-30",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-02-05",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-02-06",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-02-09",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-02-10",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-02-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-02-13",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-02-24",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-03-02",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-03-03",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-03-04",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-03-05",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-03-06",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-03-09",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-03-10",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-03-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-03-12",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-03-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-03-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-03-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-03-18",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-03-19",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-03-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-03-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-03-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-03-25",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-03-26",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-03-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-03-30",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-03-31",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-01",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-02",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-03",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-07",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-08",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-09",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-10",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-13",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-14",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-15",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-16",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-17",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-20",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-21",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-22",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-23",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-24",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-27",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-28",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-29",
        "reason": "not_bull"
      },
      {
        "id": "588000.SS|2026-04-30",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-06",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-07",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-08",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-12",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-13",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-14",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-15",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-19",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-20",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-21",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-22",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-25",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-26",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-27",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-28",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-05-29",
        "reason": "not_gray"
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
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-04",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-05",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-08",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-09",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-10",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-11",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-12",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-15",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-16",
        "reason": "immature_label"
      },
      {
        "id": "588000.SS|2026-06-17",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-18",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-22",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-23",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-24",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-25",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-26",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-29",
        "reason": "not_gray"
      },
      {
        "id": "588000.SS|2026-06-30",
        "reason": "not_gray"
      }
    ],
    "own_group": [
      {
        "condition": 0,
        "mean": -0.9471914797615291,
        "rows": 201,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      },
      {
        "condition": 1,
        "mean": -3.333290616170415,
        "rows": 114,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      }
    ],
    "common_asset_year": [
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2022",
        "weight": 0.05,
        "rows0": 9,
        "rows1": 1,
        "mean0": 2.8313698992778895,
        "mean1": -2.679192762700078,
        "overall": 2.2803136330800924,
        "share1": 0.1
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2023",
        "weight": 0.05,
        "rows0": 12,
        "rows1": 8,
        "mean0": -0.7890001498322347,
        "mean1": -3.550613187468871,
        "overall": -1.8936453648868887,
        "share1": 0.4
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2024",
        "weight": 0.05,
        "rows0": 8,
        "rows1": 12,
        "mean0": 0.40949674625049837,
        "mean1": -0.9412975926138193,
        "overall": -0.4009798570680922,
        "share1": 0.6
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2025",
        "weight": 0.05,
        "rows0": 26,
        "rows1": 6,
        "mean0": 1.1722376788467146,
        "mean1": 4.414774827421809,
        "overall": 1.7802133942045448,
        "share1": 0.1875
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2026",
        "weight": 0.05,
        "rows0": 10,
        "rows1": 8,
        "mean0": -1.1132263095845396,
        "mean1": -4.175924031389542,
        "overall": -2.4744252970534286,
        "share1": 0.4444444444444444
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2022",
        "weight": 0.05,
        "rows0": 11,
        "rows1": 1,
        "mean0": 4.258141192848081,
        "mean1": -1.0965935604293042,
        "overall": 3.8119132967416327,
        "share1": 0.08333333333333333
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2023",
        "weight": 0.05,
        "rows0": 5,
        "rows1": 7,
        "mean0": 0.5781774973604792,
        "mean1": -2.0606792759593238,
        "overall": -0.9611556204094059,
        "share1": 0.5833333333333334
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2024",
        "weight": 0.05,
        "rows0": 13,
        "rows1": 15,
        "mean0": -0.6633000102248475,
        "mean1": -1.1374750621738203,
        "overall": -0.9173223594832258,
        "share1": 0.5357142857142857
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2025",
        "weight": 0.05,
        "rows0": 19,
        "rows1": 7,
        "mean0": 1.1029613539328489,
        "mean1": -0.7122406827855746,
        "overall": 0.6142531132778886,
        "share1": 0.2692307692307692
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2026",
        "weight": 0.05,
        "rows0": 5,
        "rows1": 8,
        "mean0": 0.04299859794589356,
        "mean1": -2.347055769899381,
        "overall": -1.4278040899588906,
        "share1": 0.6153846153846154
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2022",
        "weight": 0.0625,
        "rows0": 4,
        "rows1": 10,
        "mean0": -2.8546204883246133,
        "mean1": -1.2932076435277384,
        "overall": -1.7393255991839884,
        "share1": 0.7142857142857143
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2023",
        "weight": 0.0625,
        "rows0": 1,
        "rows1": 8,
        "mean0": -2.768166089965396,
        "mean1": -1.3485058756909818,
        "overall": -1.5062458994992503,
        "share1": 0.8888888888888888
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2024",
        "weight": 0.0625,
        "rows0": 19,
        "rows1": 9,
        "mean0": -4.698402034261186,
        "mean1": -1.6291355084765806,
        "overall": -3.711852079544706,
        "share1": 0.32142857142857145
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2025",
        "weight": 0.0625,
        "rows0": 7,
        "rows1": 7,
        "mean0": -0.2151859679828893,
        "mean1": -0.40066636497291575,
        "overall": -0.30792616647790255,
        "share1": 0.5
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2022",
        "weight": 0.0625,
        "rows0": 12,
        "rows1": 1,
        "mean0": -4.617017657639793,
        "mean1": -2.4411508282475514,
        "overall": -4.449643286148082,
        "share1": 0.07692307692307693
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2024",
        "weight": 0.0625,
        "rows0": 15,
        "rows1": 1,
        "mean0": -2.932357578810726,
        "mean1": -4.037558685446041,
        "overall": -3.0014326479754336,
        "share1": 0.0625
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2025",
        "weight": 0.0625,
        "rows0": 5,
        "rows1": 1,
        "mean0": -3.84588797360965,
        "mean1": -6.254203093476796,
        "overall": -4.247273826920841,
        "share1": 0.16666666666666666
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2026",
        "weight": 0.0625,
        "rows0": 3,
        "rows1": 4,
        "mean0": -4.443825378235174,
        "mean1": -12.970102616107194,
        "overall": -9.31598379987633,
        "share1": 0.5714285714285714
      }
    ],
    "unsupported_strata": [
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2026",
        "rows0": 9,
        "rows1": 0,
        "reason": "both states not observed"
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2023",
        "rows0": 8,
        "rows1": 0,
        "reason": "both states not observed"
      }
    ],
    "comparison_available": true,
    "common_support_rows": 298,
    "common_support_assets": 4,
    "fixed_common_means": {
      "condition0": -1.2569736232108002,
      "condition1": -2.612723018396508,
      "difference": -1.3557493951857076,
      "baseline": -1.746912164179447,
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
- Current bullish gray dates retain open paths; prior direction is historical, not a trading reset rule.
- Color/group segments and overlapping outcomes are not independent opportunities.
- 部分字段在训练时期没有变化，无法提供可学习的差别。
- 部分字段在训练时期没有变化，无法提供可学习的差别。
- 部分字段在训练时期没有变化，无法提供可学习的差别。
- 部分字段在训练时期没有变化，无法提供可学习的差别。
- 部分整段日期的重复抽取缺少固定对象，已剔除并报告次数，没有改换对象比重。
- 部分整段日期的重复抽取缺少固定对象，已剔除并报告次数，没有改换对象比重。
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。
- B2相对B0的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "四ETF有限回顾资料；真实到达/行动完整性未知",
    "source_refs": [
      "docs/experiments/raw/color-gray-path-2026-10-04/brief.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "当前多头灰，保留所有来源明确日期；此前颜色可形成于非多头组，非等待重置交易规则",
    "source_refs": [
      "docs/experiments/raw/color-gray-path-2026-10-04/brief.json"
    ]
  },
  "method_fit": {
    "reason": "两折成熟训练，共同ETF日期权重，固定线性与浅树；来源组小须披露",
    "source_refs": [
      "docs/experiments/raw/color-gray-path-2026-10-04/brief.json"
    ]
  },
  "conclusion_scope": {
    "reason": "历史信息比较，不是独立未来验证或净资金收益",
    "source_refs": [
      "docs/experiments/raw/color-gray-path-2026-10-04/brief.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：not_supported；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
