# technical-persistence-return-2026-10-03（限定范围研究）

## 一句话结论（大白话）

本次方法下未得到新增帮助的支持。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：检验持续程度在当前20/60颜色、EMA方向、涨跌及波动已知后是否提供收益或下探信息
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
| B1 | MSE | 51.879304 | 百分点² | 1268 | 317 | 4 |
| B1 | RMSE | 7.202729 | 百分点 | 1268 | 317 | 4 |
| B2 | MSE | 53.172675 | 百分点² | 1268 | 317 | 4 |
| B2 | RMSE | 7.2919596 | 百分点 | 1268 | 317 | 4 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 51.879304 | 53.172675 | -1.2933706 | -2.493% | -3.12333 至 0.285923 | percentage_point_squared |
| B2 相对 B0 | 46.299413 | 53.172675 | -6.8732618 | -14.85% | -16.9867 至 1.27653 | percentage_point_squared |

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
        "mean": 3.151941631030569,
        "rows": 454,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      },
      {
        "condition": 1,
        "mean": 0.25912694619674137,
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
        "mean0": -2.2909082855630944,
        "mean1": -0.46226067952036803,
        "overall": -0.9609827538956569,
        "share1": 0.7272727272727273
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2023",
        "weight": 0.0625,
        "rows0": 34,
        "rows1": 208,
        "mean0": -0.6526403156191298,
        "mean1": -1.7294376895024253,
        "overall": -1.5781521080477472,
        "share1": 0.859504132231405
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2024",
        "weight": 0.0625,
        "rows0": 29,
        "rows1": 213,
        "mean0": 12.769232280383706,
        "mean1": 0.10974302859532604,
        "overall": 1.6267892612476527,
        "share1": 0.8801652892561983
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2025",
        "weight": 0.0625,
        "rows0": 9,
        "rows1": 234,
        "mean0": 2.300664898121152,
        "mean1": 2.0832206648449123,
        "overall": 2.0912741549662544,
        "share1": 0.9629629629629629
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2022",
        "weight": 0.05,
        "rows0": 42,
        "rows1": 200,
        "mean0": -0.04235936738098022,
        "mean1": -0.9435372285757356,
        "overall": -0.7871344592774723,
        "share1": 0.8264462809917356
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2023",
        "weight": 0.05,
        "rows0": 23,
        "rows1": 219,
        "mean0": -0.8215994187158763,
        "mean1": -1.4792163011396726,
        "overall": -1.4167155230580721,
        "share1": 0.9049586776859504
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2024",
        "weight": 0.05,
        "rows0": 10,
        "rows1": 232,
        "mean0": -0.8438275497587833,
        "mean1": 1.6009895010416804,
        "overall": 1.499964003074719,
        "share1": 0.9586776859504132
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2025",
        "weight": 0.05,
        "rows0": 1,
        "rows1": 242,
        "mean0": 2.661169415292375,
        "mean1": 1.7631356565070144,
        "overall": 1.7668312686830858,
        "share1": 0.9958847736625515
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2026",
        "weight": 0.05,
        "rows0": 12,
        "rows1": 83,
        "mean0": 4.569445703492953,
        "mean1": -1.9039678650048477,
        "overall": -1.0862735195103892,
        "share1": 0.8736842105263158
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2022",
        "weight": 0.0625,
        "rows0": 35,
        "rows1": 207,
        "mean0": -0.48542359490178627,
        "mean1": -0.7208900377468063,
        "overall": -0.6868349736989727,
        "share1": 0.8553719008264463
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2023",
        "weight": 0.0625,
        "rows0": 22,
        "rows1": 220,
        "mean0": 1.1918856245542462,
        "mean1": -1.6592684508206819,
        "overall": -1.4000726257865976,
        "share1": 0.9090909090909091
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2024",
        "weight": 0.0625,
        "rows0": 37,
        "rows1": 205,
        "mean0": 0.7742356221900433,
        "mean1": 1.2895063316346327,
        "overall": 1.2107252727526088,
        "share1": 0.8471074380165289
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2025",
        "weight": 0.0625,
        "rows0": 14,
        "rows1": 229,
        "mean0": 3.4736125111237786,
        "mean1": 3.6351527794267082,
        "overall": 3.625845932693207,
        "share1": 0.9423868312757202
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2022",
        "weight": 0.05,
        "rows0": 67,
        "rows1": 175,
        "mean0": 4.174779256342127,
        "mean1": -3.974939203173721,
        "overall": -1.7186121916548707,
        "share1": 0.7231404958677686
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2023",
        "weight": 0.05,
        "rows0": 15,
        "rows1": 227,
        "mean0": -4.849376257204892,
        "mean1": -1.7820848688400488,
        "overall": -1.9722062358874568,
        "share1": 0.9380165289256198
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2024",
        "weight": 0.05,
        "rows0": 26,
        "rows1": 216,
        "mean0": 30.659088288709555,
        "mean1": -0.5687898773638861,
        "overall": 2.7862714132059874,
        "share1": 0.8925619834710744
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2025",
        "weight": 0.05,
        "rows0": 5,
        "rows1": 238,
        "mean0": 1.8194394595620067,
        "mean1": 4.049868393790828,
        "overall": 4.003974794321099,
        "share1": 0.9794238683127572
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2026",
        "weight": 0.05,
        "rows0": 7,
        "rows1": 88,
        "mean0": 25.09558711355168,
        "mean1": 3.4398101238993557,
        "overall": 5.035498954715841,
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
      "condition0": 4.188658503462566,
      "condition1": 0.16917378823900445,
      "difference": -4.0194847152235615,
      "baseline": 0.6511169352450454,
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
- 方向比例与相邻变色仅为已知价格表达；排列/变色代理不构成完整交易规则。
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B1
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B0
- 不同年份的改善方向相反，不能视作跨年份稳定帮助。
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。
- B2相对B0的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "四固定国内宽基ETF经济价来源逐行可核；到达和行动完整性有限，不扩大池",
    "source_refs": [
      "docs/experiments/raw/technical-multimethod-2026-10-03/persistence/return/qualification.json",
      "docs/experiments/raw/technical-multimethod-2026-10-03/brief.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "固定20日方向比例是稳定上行的研究代理；不是原文唯一公式，也不是Q01连续等待年龄",
    "source_refs": [
      "docs/experiments/raw/technical-multimethod-2026-10-03/persistence/return/qualification.json",
      "docs/experiments/raw/technical-multimethod-2026-10-03/brief.json"
    ]
  },
  "method_fit": {
    "reason": "固定背景加一列，两时间折，不用结果定分组；样本/秩/稀少事件均先审，简单均值防止弱背景误导",
    "source_refs": [
      "docs/experiments/raw/technical-multimethod-2026-10-03/persistence/return/qualification.json",
      "docs/experiments/raw/technical-multimethod-2026-10-03/brief.json"
    ]
  },
  "conclusion_scope": {
    "reason": "收益或收盘下探的信息用途；全部历史已见；不涉及账户、转黑重置或原文修改",
    "source_refs": [
      "docs/experiments/raw/technical-multimethod-2026-10-03/persistence/return/qualification.json",
      "docs/experiments/raw/technical-multimethod-2026-10-03/brief.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：not_supported；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
