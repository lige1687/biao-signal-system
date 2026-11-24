# V01-volume-abnormal20-auxiliary-risk-forecast（限定范围研究）

## 一句话结论（大白话）

证据不足。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：既有价格/趋势背景中的下一段下跌风险提醒，不构成交易规则
计划对象：510300.SS, 510050.SS, 510500.SS, 588000.SS；实际有报价：510050.SS, 510300.SS, 510500.SS, 588000.SS。
时期：['2022-01-04', '2026-06-30']；评价对象数量：1268条、317个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | Brier | 0.093203671 | 0到1的平方评分 | 1268 | 317 | 4 |
| B1 | Brier | 0.09019434 | 0到1的平方评分 | 1268 | 317 | 4 |
| B2 | Brier | 0.093786916 | 0到1的平方评分 | 1268 | 317 | 4 |
| B50 | Brier | 0.25 | 0到1的平方评分 | 1268 | 317 | 4 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 0.09019434 | 0.093786916 | -0.0035925762 | -3.983% | -0.00882725 至 -0.000205471 | probability_squared |
| B2 相对 B0 | 0.093203671 | 0.093786916 | -0.00058324485 | -0.6258% | -0.00750004 至 0.00597581 | probability_squared |
| B2 相对 B50 | 0.25 | 0.093786916 | 0.15621308 | 62.49% | 0.10336 至 0.197075 | probability_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "observations": 4340,
    "ready_252": 4340,
    "abnormal": 158,
    "ordinary": 4163,
    "unknown": 19,
    "eligible": 4237,
    "price_reset_rows": 0,
    "volume_reset_rows": 1,
    "per_asset": {
      "510300.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "abnormal": 52,
        "ordinary": 1033,
        "unknown": 0,
        "eligible": 1064
      },
      "510050.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "abnormal": 40,
        "ordinary": 1045,
        "unknown": 0,
        "eligible": 1064
      },
      "510500.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "abnormal": 42,
        "ordinary": 1024,
        "unknown": 19,
        "eligible": 1045,
        "volume_reset_rows": 1
      },
      "588000.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "abnormal": 24,
        "ordinary": 1061,
        "unknown": 0,
        "eligible": 1064
      }
    },
    "definition_ref": "research.volume.abnormal20@1.0.0",
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
    "evaluable_rows": 4237,
    "common_prediction_rows": 1268,
    "event_opportunities": 154,
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
        "id": "510500.SS|2022-08-29",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-08-30",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-08-31",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-01",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-02",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-05",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-06",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-07",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-08",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-09",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-13",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-14",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-15",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-16",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-19",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-20",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-21",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-22",
        "reason": "volume_unknown"
      },
      {
        "id": "510500.SS|2022-09-23",
        "reason": "volume_unknown"
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
        "mean": 0.15463662159578576,
        "rows": 4083,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      },
      {
        "condition": 1,
        "mean": 0.1348214285714286,
        "rows": 154,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      }
    ],
    "common_asset_year": [
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2022",
        "weight": 0.05,
        "rows0": 232,
        "rows1": 10,
        "mean0": 0.27586206896551724,
        "mean1": 0.2,
        "overall": 0.2727272727272727,
        "share1": 0.04132231404958678
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2023",
        "weight": 0.05,
        "rows0": 233,
        "rows1": 9,
        "mean0": 0.12017167381974249,
        "mean1": 0.3333333333333333,
        "overall": 0.128099173553719,
        "share1": 0.0371900826446281
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2024",
        "weight": 0.05,
        "rows0": 229,
        "rows1": 13,
        "mean0": 0.043668122270742356,
        "mean1": 0.07692307692307693,
        "overall": 0.045454545454545456,
        "share1": 0.05371900826446281
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2025",
        "weight": 0.05,
        "rows0": 240,
        "rows1": 3,
        "mean0": 0.03333333333333333,
        "mean1": 0.0,
        "overall": 0.03292181069958848,
        "share1": 0.012345679012345678
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2026",
        "weight": 0.05,
        "rows0": 82,
        "rows1": 13,
        "mean0": 0.04878048780487805,
        "mean1": 0.0,
        "overall": 0.042105263157894736,
        "share1": 0.1368421052631579
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2022",
        "weight": 0.05,
        "rows0": 236,
        "rows1": 6,
        "mean0": 0.2542372881355932,
        "mean1": 0.16666666666666666,
        "overall": 0.25206611570247933,
        "share1": 0.024793388429752067
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2023",
        "weight": 0.05,
        "rows0": 234,
        "rows1": 8,
        "mean0": 0.10256410256410256,
        "mean1": 0.25,
        "overall": 0.10743801652892562,
        "share1": 0.03305785123966942
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2024",
        "weight": 0.05,
        "rows0": 232,
        "rows1": 10,
        "mean0": 0.034482758620689655,
        "mean1": 0.0,
        "overall": 0.03305785123966942,
        "share1": 0.04132231404958678
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2025",
        "weight": 0.05,
        "rows0": 239,
        "rows1": 4,
        "mean0": 0.0041841004184100415,
        "mean1": 0.0,
        "overall": 0.00411522633744856,
        "share1": 0.01646090534979424
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2026",
        "weight": 0.05,
        "rows0": 83,
        "rows1": 12,
        "mean0": 0.1566265060240964,
        "mean1": 0.0,
        "overall": 0.1368421052631579,
        "share1": 0.12631578947368421
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2022",
        "weight": 0.05,
        "rows0": 215,
        "rows1": 8,
        "mean0": 0.22790697674418606,
        "mean1": 0.125,
        "overall": 0.2242152466367713,
        "share1": 0.03587443946188341
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2023",
        "weight": 0.05,
        "rows0": 238,
        "rows1": 4,
        "mean0": 0.1134453781512605,
        "mean1": 0.25,
        "overall": 0.11570247933884298,
        "share1": 0.01652892561983471
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2024",
        "weight": 0.05,
        "rows0": 226,
        "rows1": 16,
        "mean0": 0.19911504424778761,
        "mean1": 0.0,
        "overall": 0.1859504132231405,
        "share1": 0.06611570247933884
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2025",
        "weight": 0.05,
        "rows0": 236,
        "rows1": 7,
        "mean0": 0.08898305084745763,
        "mean1": 0.0,
        "overall": 0.08641975308641975,
        "share1": 0.02880658436213992
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2026",
        "weight": 0.05,
        "rows0": 88,
        "rows1": 7,
        "mean0": 0.2159090909090909,
        "mean1": 0.0,
        "overall": 0.2,
        "share1": 0.07368421052631578
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2022",
        "weight": 0.0625,
        "rows0": 238,
        "rows1": 4,
        "mean0": 0.36554621848739494,
        "mean1": 0.5,
        "overall": 0.3677685950413223,
        "share1": 0.01652892561983471
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2023",
        "weight": 0.0625,
        "rows0": 238,
        "rows1": 4,
        "mean0": 0.226890756302521,
        "mean1": 0.75,
        "overall": 0.23553719008264462,
        "share1": 0.01652892561983471
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2024",
        "weight": 0.0625,
        "rows0": 231,
        "rows1": 11,
        "mean0": 0.24675324675324675,
        "mean1": 0.09090909090909091,
        "overall": 0.2396694214876033,
        "share1": 0.045454545454545456
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2025",
        "weight": 0.0625,
        "rows0": 238,
        "rows1": 5,
        "mean0": 0.13025210084033614,
        "mean1": 0.2,
        "overall": 0.13168724279835392,
        "share1": 0.0205761316872428
      }
    ],
    "unsupported_strata": [
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2026",
        "rows0": 95,
        "rows1": 0,
        "reason": "both states not observed"
      }
    ],
    "comparison_available": true,
    "common_support_rows": 4142,
    "common_support_assets": 4,
    "fixed_common_means": {
      "condition0": 0.1565536442918131,
      "condition1": 0.16640297202797205,
      "difference": 0.009849327736158958,
      "baseline": 0.15427216673561403,
      "identity_error": 0.0,
      "unit": "probability",
      "weighting": "equal supported assets; equal supported years within asset; same strata in both conditions",
      "evidence": "descriptive, not causal"
    }
  }
}
```

## 反例和结论边界

评价期资料没有参与训练或标准化；已有资料是否曾用于挑选方法仍以研究家族记录为准，换名字不成为新验证。预测改善不直接代表投资收益。

- 逐行原响应与名义报价/行动重算只支持回顾性经济价格和单ETF量比；行动历史到达时间与绝对成交量单位未认证。
- 全天成交量仅收盘后已知；未知量比保留为未知。背景含同ETF、当天涨跌四组、20日波动和60日均线方向。
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B1
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B0
- B2相对B0的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "国内宽基ETF为主应用；四只预选产品全日记录并无趋势筛选。固定池只支持这些历史，不能外推全ETF、个股或独立市场。",
    "source_refs": [
      "docs/experiments/raw/volume-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/volume-information-2026-09-30/controller-qualification.json",
      "docs/experiments/raw/volume-information-2026-09-30/controller-economic-audit.json",
      "docs/experiments/raw/volume-information-2026-09-30/independent-audit/audit.json",
      "docs/experiments/raw/volume-information-2026-09-30/independent-audit/match-audit.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics-preparation-contract.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics-contract.json",
      "docs/experiments/raw/volume-information-2026-09-30/execution/features.csv",
      "docs/experiments/raw/volume-information-2026-09-30/execution/delivery.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics/preparation-log.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics/run_summary.py"
    ]
  },
  "proxy_fidelity": {
    "reason": "保留原文异常量提醒并单列研究代理；含当日20日/2倍未获作者标准确认。源量逐日核对，行动仅回顾性数学重建；未测试持续大量、成交额或完整交易。",
    "source_refs": [
      "docs/experiments/raw/volume-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/volume-information-2026-09-30/controller-qualification.json",
      "docs/experiments/raw/volume-information-2026-09-30/controller-economic-audit.json",
      "docs/experiments/raw/volume-information-2026-09-30/independent-audit/audit.json",
      "docs/experiments/raw/volume-information-2026-09-30/independent-audit/match-audit.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics-preparation-contract.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics-contract.json",
      "docs/experiments/raw/volume-information-2026-09-30/execution/features.csv",
      "docs/experiments/raw/volume-information-2026-09-30/execution/delivery.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics/preparation-log.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics/run_summary.py"
    ]
  },
  "method_fit": {
    "reason": "主相近背景98/153异常有匹配，55未覆盖；辅助B1各组有历史，B2几乎所有后期异常所用训练组少于5例。允许固定有限诊断，不通过模型复杂度或平滑参数救效果。",
    "source_refs": [
      "docs/experiments/raw/volume-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/volume-information-2026-09-30/controller-qualification.json",
      "docs/experiments/raw/volume-information-2026-09-30/controller-economic-audit.json",
      "docs/experiments/raw/volume-information-2026-09-30/independent-audit/audit.json",
      "docs/experiments/raw/volume-information-2026-09-30/independent-audit/match-audit.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics-preparation-contract.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics-contract.json",
      "docs/experiments/raw/volume-information-2026-09-30/execution/features.csv",
      "docs/experiments/raw/volume-information-2026-09-30/execution/delivery.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics/preparation-log.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics/run_summary.py"
    ]
  },
  "conclusion_scope": {
    "reason": "主匹配只回答相近当日价格/趋势下的条件关联；辅助后期预测只比较同日B0/B1/B2错误。所有历史已见且机会相关，误差不等于账户收益，不能确认稳定或生产采用。",
    "source_refs": [
      "docs/experiments/raw/volume-information-2026-09-30/method-decision.md",
      "docs/experiments/raw/volume-information-2026-09-30/controller-qualification.json",
      "docs/experiments/raw/volume-information-2026-09-30/controller-economic-audit.json",
      "docs/experiments/raw/volume-information-2026-09-30/independent-audit/audit.json",
      "docs/experiments/raw/volume-information-2026-09-30/independent-audit/match-audit.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics-preparation-contract.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics-contract.json",
      "docs/experiments/raw/volume-information-2026-09-30/execution/features.csv",
      "docs/experiments/raw/volume-information-2026-09-30/execution/delivery.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics/preparation-log.json",
      "docs/experiments/raw/volume-information-2026-09-30/statistics/run_summary.py"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：insufficient；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
