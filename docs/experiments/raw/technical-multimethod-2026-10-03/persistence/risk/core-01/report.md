# technical-persistence-risk-2026-10-03（限定范围研究）

## 一句话结论（大白话）

证据不足。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：检验持续程度在当前20/60颜色、EMA方向、涨跌及波动已知后是否提供收益或下探信息
计划对象：510300.SS, 510050.SS, 510500.SS, 588000.SS；实际有报价：510050.SS, 510300.SS, 510500.SS, 588000.SS。
时期：['2022-01-04', '2026-06-30']；评价对象数量：1268条、317个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | MSE | 13.758688 | 百分点² | 1268 | 317 | 4 |
| B0 | RMSE | 3.7092705 | 百分点 | 1268 | 317 | 4 |
| B1 | MSE | 12.430145 | 百分点² | 1268 | 317 | 4 |
| B1 | RMSE | 3.5256411 | 百分点 | 1268 | 317 | 4 |
| B2 | MSE | 12.528153 | 百分点² | 1268 | 317 | 4 |
| B2 | RMSE | 3.5395131 | 百分点 | 1268 | 317 | 4 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 12.430145 | 12.528153 | -0.098008003 | -0.7885% | -0.386573 至 0.186516 | percentage_point_squared |
| B2 相对 B0 | 13.758688 | 12.528153 | 1.2305344 | 8.944% | 0.516949 至 1.87636 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "observations": 4340,
    "ready_252": 4340,
    "eligible": 4256,
    "bull_green": 1049,
    "price_reset_rows": 0,
    "continuous252_or_indicator_missing": 0,
    "outside_bull_green": 0,
    "feature_ready": 4340,
    "per_asset": {
      "510300.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "eligible": 1064,
        "bull_green": 274,
        "feature_ready": 1085,
        "price_reset_rows": 0
      },
      "510050.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "eligible": 1064,
        "bull_green": 248,
        "feature_ready": 1085,
        "price_reset_rows": 0
      },
      "510500.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "eligible": 1064,
        "bull_green": 297,
        "feature_ready": 1085,
        "price_reset_rows": 0
      },
      "588000.SS": {
        "observations": 1085,
        "ready_252": 1085,
        "eligible": 1064,
        "bull_green": 230,
        "feature_ready": 1085,
        "price_reset_rows": 0
      }
    },
    "definition_ref": "research.trend.ema_direction_persistence20@1.0.0",
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
    "event_opportunities": 3802,
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
        "mean": 3.9662095624199045,
        "rows": 454,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      },
      {
        "condition": 1,
        "mean": 3.7249163605061475,
        "rows": 3802,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      }
    ],
    "common_asset_year": [
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2022",
        "weight": 0.0625,
        "rows0": 66,
        "rows1": 176,
        "mean0": 6.4409968039199486,
        "mean1": 4.007850695073919,
        "overall": 4.671435997486472,
        "share1": 0.7272727272727273
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2023",
        "weight": 0.0625,
        "rows0": 34,
        "rows1": 208,
        "mean0": 2.1688028290044428,
        "mean1": 3.425485256492998,
        "overall": 3.2489265683334487,
        "share1": 0.859504132231405
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2024",
        "weight": 0.0625,
        "rows0": 29,
        "rows1": 213,
        "mean0": 1.588939553225202,
        "mean1": 2.8607080478224582,
        "overall": 2.708306038139316,
        "share1": 0.8801652892561983
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2025",
        "weight": 0.0625,
        "rows0": 9,
        "rows1": 234,
        "mean0": 0.23485659047148216,
        "mean1": 1.7002421422823293,
        "overall": 1.6459686033263718,
        "share1": 0.9629629629629629
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2022",
        "weight": 0.05,
        "rows0": 42,
        "rows1": 200,
        "mean0": 3.715422524846192,
        "mean1": 4.765954253010488,
        "overall": 4.583630564651394,
        "share1": 0.8264462809917356
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2023",
        "weight": 0.05,
        "rows0": 23,
        "rows1": 219,
        "mean0": 2.216859193833419,
        "mean1": 3.278062448812123,
        "overall": 3.1772042882149734,
        "share1": 0.9049586776859504
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2024",
        "weight": 0.05,
        "rows0": 10,
        "rows1": 232,
        "mean0": 1.3330756650847344,
        "mean1": 2.395369890741933,
        "overall": 2.351473435136264,
        "share1": 0.9586776859504132
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2025",
        "weight": 0.05,
        "rows0": 1,
        "rows1": 242,
        "mean0": 0.0,
        "mean1": 1.367963707680136,
        "overall": 1.362334227401617,
        "share1": 0.9958847736625515
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2026",
        "weight": 0.05,
        "rows0": 12,
        "rows1": 83,
        "mean0": 0.4252519331417293,
        "mean1": 3.8064961679177394,
        "overall": 3.379391632998664,
        "share1": 0.8736842105263158
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2022",
        "weight": 0.0625,
        "rows0": 35,
        "rows1": 207,
        "mean0": 8.15520582457364,
        "mean1": 4.545432164961927,
        "overall": 5.067506867798331,
        "share1": 0.8553719008264463
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2023",
        "weight": 0.0625,
        "rows0": 22,
        "rows1": 220,
        "mean0": 2.5500229443389886,
        "mean1": 3.414711978443178,
        "overall": 3.3361038844337063,
        "share1": 0.9090909090909091
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2024",
        "weight": 0.0625,
        "rows0": 37,
        "rows1": 205,
        "mean0": 4.140678692760835,
        "mean1": 4.80641834639231,
        "overall": 4.704631705134605,
        "share1": 0.8471074380165289
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2025",
        "weight": 0.0625,
        "rows0": 14,
        "rows1": 229,
        "mean0": 0.357124917228961,
        "mean1": 2.5389726608306145,
        "overall": 2.413269498647803,
        "share1": 0.9423868312757202
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2022",
        "weight": 0.05,
        "rows0": 67,
        "rows1": 175,
        "mean0": 5.84903336592506,
        "mean1": 7.17767337474393,
        "overall": 6.8098267607320935,
        "share1": 0.7231404958677686
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2023",
        "weight": 0.05,
        "rows0": 15,
        "rows1": 227,
        "mean0": 6.967150563331872,
        "mean1": 4.435834759827982,
        "overall": 4.592734499714586,
        "share1": 0.9380165289256198
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2024",
        "weight": 0.05,
        "rows0": 26,
        "rows1": 216,
        "mean0": 1.8871441072958155,
        "mean1": 5.633132991224393,
        "overall": 5.230671375595703,
        "share1": 0.8925619834710744
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2025",
        "weight": 0.05,
        "rows0": 5,
        "rows1": 238,
        "mean0": 2.579926936296395,
        "mean1": 3.6084097885400763,
        "overall": 3.5872475899342393,
        "share1": 0.9794238683127572
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2026",
        "weight": 0.05,
        "rows0": 7,
        "rows1": 88,
        "mean0": 1.0021965950538059,
        "mean1": 6.2968155761988305,
        "overall": 5.9066857565355155,
        "share1": 0.9263157894736842
      }
    ],
    "unsupported_strata": [
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2026",
        "rows0": 0,
        "rows1": 95,
        "reason": "both states not observed"
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2026",
        "rows0": 0,
        "rows1": 95,
        "reason": "both states not observed"
      }
    ],
    "comparison_available": true,
    "common_support_rows": 4066,
    "common_support_assets": 4,
    "fixed_common_means": {
      "condition0": 2.90109230396067,
      "condition1": 3.8445244787036157,
      "difference": 0.9434321747429455,
      "baseline": 3.7863193292520054,
      "identity_error": -8.881784197001252e-16,
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
- 方向比例与相邻变色仅为已知价格表达；排列/变色代理不构成完整交易规则。
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B1
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "四固定国内宽基ETF经济价来源逐行可核；到达和行动完整性有限，不扩大池",
    "source_refs": [
      "docs/experiments/raw/technical-multimethod-2026-10-03/persistence/risk/qualification.json",
      "docs/experiments/raw/technical-multimethod-2026-10-03/brief.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "固定20日方向比例是稳定上行的研究代理；不是原文唯一公式，也不是Q01连续等待年龄",
    "source_refs": [
      "docs/experiments/raw/technical-multimethod-2026-10-03/persistence/risk/qualification.json",
      "docs/experiments/raw/technical-multimethod-2026-10-03/brief.json"
    ]
  },
  "method_fit": {
    "reason": "固定背景加一列，两时间折，不用结果定分组；样本/秩/稀少事件均先审，简单均值防止弱背景误导",
    "source_refs": [
      "docs/experiments/raw/technical-multimethod-2026-10-03/persistence/risk/qualification.json",
      "docs/experiments/raw/technical-multimethod-2026-10-03/brief.json"
    ]
  },
  "conclusion_scope": {
    "reason": "收益或收盘下探的信息用途；全部历史已见；不涉及账户、转黑重置或原文修改",
    "source_refs": [
      "docs/experiments/raw/technical-multimethod-2026-10-03/persistence/risk/qualification.json",
      "docs/experiments/raw/technical-multimethod-2026-10-03/brief.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：insufficient；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
