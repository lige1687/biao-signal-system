# semantic-trend-2026-10-02（限定范围研究）

## 一句话结论（大白话）

本次方法下未得到新增帮助的支持。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：当前斜率及价格背景已知后，斜率相对20日前变化是否改善未来20间隔涨跌说明？
计划对象：510300.SS, 510050.SS, 510500.SS, 588000.SS；实际有报价：510050.SS, 510300.SS, 510500.SS, 588000.SS。
时期：['2022-01-04', '2026-06-30']；评价对象数量：1268条、317个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | MSE | 46.299413 | 百分点² | 1268 | 317 | 4 |
| B0 | RMSE | 6.8043672 | 百分点 | 1268 | 317 | 4 |
| B1 | MSE | 67.600164 | 百分点² | 1268 | 317 | 4 |
| B1 | RMSE | 8.2219319 | 百分点 | 1268 | 317 | 4 |
| B2 | MSE | 68.533994 | 百分点² | 1268 | 317 | 4 |
| B2 | RMSE | 8.2785261 | 百分点 | 1268 | 317 | 4 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 67.600164 | 68.533994 | -0.93383072 | -1.381% | -2.8633 至 0.411692 | percentage_point_squared |
| B2 相对 B0 | 46.299413 | 68.533994 | -22.234581 | -48.02% | -37.0834 至 -8.60349 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "observations": 4340,
    "ready_252": 4340,
    "eligible": 4256,
    "price_reset_rows": 0,
    "continuous252_or_indicator_missing": 0,
    "feature_ready": 4340,
    "per_asset": {
      "510300.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "eligible": 1064,
        "feature_ready": 1085,
        "price_reset_rows": 0
      },
      "510050.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "eligible": 1064,
        "feature_ready": 1085,
        "price_reset_rows": 0
      },
      "510500.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "eligible": 1064,
        "feature_ready": 1085,
        "price_reset_rows": 0
      },
      "588000.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "eligible": 1064,
        "feature_ready": 1085,
        "price_reset_rows": 0
      }
    },
    "definition_ref": "research.trend.slope_change60_20@1.0.0",
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
    "evaluable_rows": 4256,
    "common_prediction_rows": 1268,
    "event_opportunities": 2015,
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
      }
    ],
    "own_group": [
      {
        "condition": 0,
        "mean": 1.2493055322638498,
        "rows": 2241,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      },
      {
        "condition": 1,
        "mean": -0.11454162268444434,
        "rows": 2015,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      }
    ],
    "common_asset_year": [
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2022",
        "weight": 0.05,
        "rows0": 149,
        "rows1": 93,
        "mean0": 0.2375798360115421,
        "mean1": -2.881260451703966,
        "overall": -0.9609827538956569,
        "share1": 0.384297520661157
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2023",
        "weight": 0.05,
        "rows0": 122,
        "rows1": 120,
        "mean0": -1.7496518716878497,
        "mean1": -1.403794015013643,
        "overall": -1.5781521080477472,
        "share1": 0.49586776859504134
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2024",
        "weight": 0.05,
        "rows0": 95,
        "rows1": 147,
        "mean0": 4.315337569591075,
        "mean1": -0.11070794482462763,
        "overall": 1.6267892612476527,
        "share1": 0.6074380165289256
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2025",
        "weight": 0.05,
        "rows0": 111,
        "rows1": 132,
        "mean0": 1.6310347811307822,
        "mean1": 2.478293628418811,
        "overall": 2.0912741549662544,
        "share1": 0.5432098765432098
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2026",
        "weight": 0.05,
        "rows0": 79,
        "rows1": 16,
        "mean0": 0.46395672197685645,
        "mean1": 2.7661180111713866,
        "overall": 0.8516891496306722,
        "share1": 0.16842105263157894
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2022",
        "weight": 0.0625,
        "rows0": 151,
        "rows1": 91,
        "mean0": 0.3248065539813371,
        "mean1": -2.6322233933662655,
        "overall": -0.7871344592774723,
        "share1": 0.3760330578512397
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2023",
        "weight": 0.0625,
        "rows0": 118,
        "rows1": 124,
        "mean0": -1.303426420867353,
        "mean1": -1.5245228944976275,
        "overall": -1.4167155230580721,
        "share1": 0.512396694214876
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2024",
        "weight": 0.0625,
        "rows0": 101,
        "rows1": 141,
        "mean0": 4.224266846136801,
        "mean1": -0.4514869696151411,
        "overall": 1.499964003074719,
        "share1": 0.5826446280991735
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2025",
        "weight": 0.0625,
        "rows0": 103,
        "rows1": 140,
        "mean0": 1.8677747926161112,
        "mean1": 1.692565676075217,
        "overall": 1.7668312686830858,
        "share1": 0.5761316872427984
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2022",
        "weight": 0.05,
        "rows0": 167,
        "rows1": 75,
        "mean0": -0.4094503035283962,
        "mean1": -1.3044781726121226,
        "overall": -0.6868349736989727,
        "share1": 0.30991735537190085
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2023",
        "weight": 0.05,
        "rows0": 136,
        "rows1": 106,
        "mean0": -1.7518549384171251,
        "mean1": -0.948729281279506,
        "overall": -1.4000726257865976,
        "share1": 0.4380165289256198
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2024",
        "weight": 0.05,
        "rows0": 108,
        "rows1": 134,
        "mean0": 3.599731974341037,
        "mean1": -0.714742815094781,
        "overall": 1.2107252727526088,
        "share1": 0.5537190082644629
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2025",
        "weight": 0.05,
        "rows0": 126,
        "rows1": 117,
        "mean0": 4.032504436340498,
        "mean1": 3.187906005688431,
        "overall": 3.625845932693207,
        "share1": 0.48148148148148145
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2026",
        "weight": 0.05,
        "rows0": 56,
        "rows1": 39,
        "mean0": 0.5432169987619231,
        "mean1": 1.3706183878852978,
        "overall": 0.8828870427178349,
        "share1": 0.4105263157894737
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2022",
        "weight": 0.05,
        "rows0": 129,
        "rows1": 113,
        "mean0": -0.40753311897604594,
        "mean1": -3.2153307790492813,
        "overall": -1.7186121916548707,
        "share1": 0.4669421487603306
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2023",
        "weight": 0.05,
        "rows0": 82,
        "rows1": 160,
        "mean0": -2.5878246809184406,
        "mean1": -1.656701782809078,
        "overall": -1.9722062358874568,
        "share1": 0.6611570247933884
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2024",
        "weight": 0.05,
        "rows0": 102,
        "rows1": 140,
        "mean0": 8.218806806614955,
        "mean1": -1.171718659134832,
        "overall": 2.7862714132059874,
        "share1": 0.5785123966942148
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2025",
        "weight": 0.05,
        "rows0": 145,
        "rows1": 98,
        "mean0": 4.863505555099778,
        "mean1": 2.7322200972506026,
        "overall": 4.003974794321099,
        "share1": 0.40329218106995884
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2026",
        "weight": 0.05,
        "rows0": 66,
        "rows1": 29,
        "mean0": -0.17576729086963855,
        "mean1": 16.895622134324178,
        "overall": 5.035498954715841,
        "share1": 0.30526315789473685
      }
    ],
    "unsupported_strata": [
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2026",
        "rows0": 95,
        "rows1": 0,
        "reason": "both states not observed"
      }
    ],
    "comparison_available": true,
    "common_support_rows": 4161,
    "common_support_assets": 4,
    "fixed_common_means": {
      "condition0": 1.3607684845152286,
      "condition1": 0.618936494323105,
      "difference": -0.7418319901921235,
      "baseline": 0.7563388349528841,
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
- 斜率变化只是已知价格的固定研究表达；行动资料历史到达时间仍未知。
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B1
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B0
- 不同年份的改善方向相反，不能视作跨年份稳定帮助。
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "四ETF全部安排日保留，实际经济OHLC来源够有限回顾性用途，历史到达未知。",
    "source_refs": [
      "docs/experiments/raw/semantic-mining-2026-10-02/trend-adapter/qualification.json",
      "docs/experiments/raw/semantic-mining-2026-10-02/controller/trend-qualification-review.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "原文当前斜率与变化方向分开，20日前差是固定研究表达。",
    "source_refs": [
      "docs/experiments/raw/semantic-mining-2026-10-02/trend-adapter/qualification.json",
      "docs/experiments/raw/semantic-mining-2026-10-02/controller/trend-qualification-review.json"
    ]
  },
  "method_fit": {
    "reason": "X资格训练/评价支持[{'fold': {'train_end': '2024-12-31', 'eval_start': '2025-01-01', 'eval_end': '2025-12-31'}, 'train': 2820, 'evaluation': 888, 'train_dates': 705, 'evaluation_dates': 222}, {'fold': {'train_end': '2025-12-31', 'eval_start': '2026-01-01', 'eval_end': '2026-06-30'}, 'train': 3792, 'evaluation': 380, 'train_dates': 948, 'evaluation_dates': 95}]；只两个固定线性模型，简单均值并列。",
    "source_refs": [
      "docs/experiments/raw/semantic-mining-2026-10-02/trend-adapter/qualification.json",
      "docs/experiments/raw/semantic-mining-2026-10-02/controller/trend-qualification-review.json"
    ]
  },
  "conclusion_scope": {
    "reason": "只测试20日未来涨跌，五期限风险/收益分组仅描述；不优化账户或反向改技术规则。",
    "source_refs": [
      "docs/experiments/raw/semantic-mining-2026-10-02/trend-adapter/qualification.json",
      "docs/experiments/raw/semantic-mining-2026-10-02/controller/trend-qualification-review.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：not_supported；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
