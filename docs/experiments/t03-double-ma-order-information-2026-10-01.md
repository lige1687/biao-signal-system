# T03-double-order-daily-MAE20-information-20261001（限定范围研究）

## 一句话结论（大白话）

证据不足。结论只涉及本合同的对象、时期和方法。计算与检查完成不等于允许交易。

问题：F=(dS20<dS60<dS120) AND (dE20<dE60<dE120) when C>0; deterministic nonlinear expression of B1, no new raw information.
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
| B1 | MSE | 16.119236 | 百分点² | 1268 | 317 | 4 |
| B1 | RMSE | 4.0148768 | 百分点 | 1268 | 317 | 4 |
| B2 | MSE | 16.093097 | 百分点² | 1268 | 317 | 4 |
| B2 | RMSE | 4.0116203 | 百分点 | 1268 | 317 | 4 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 16.119236 | 16.093097 | 0.026138961 | 0.1622% | -0.405599 至 0.470889 | percentage_point_squared |
| B2 相对 B0 | 13.758688 | 16.093097 | -2.3344093 | -16.97% | -6.04492 至 0.40175 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "observations": 4340,
    "ready_252": 4340,
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
    "event_opportunities": 1140,
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
        "mean": 3.640665859078415,
        "rows": 3116,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      },
      {
        "condition": 1,
        "mean": 4.165134939907814,
        "rows": 1140,
        "assets": 4,
        "weighting": "natural own-group equal_asset; different composition is not net increment"
      }
    ],
    "common_asset_year": [
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2023",
        "weight": 0.0625,
        "rows0": 208,
        "rows1": 34,
        "mean0": 3.245712634328268,
        "mean1": 3.268588282247499,
        "overall": 3.2489265683334487,
        "share1": 0.14049586776859505
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2024",
        "weight": 0.0625,
        "rows0": 170,
        "rows1": 72,
        "mean0": 2.329099879480735,
        "mean1": 3.603653912749855,
        "overall": 2.708306038139316,
        "share1": 0.2975206611570248
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2025",
        "weight": 0.0625,
        "rows0": 122,
        "rows1": 121,
        "mean0": 1.0583872254677575,
        "mean1": 2.2384060256300993,
        "overall": 1.6459686033263718,
        "share1": 0.49794238683127573
      },
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2026",
        "weight": 0.0625,
        "rows0": 27,
        "rows1": 68,
        "mean0": 0.6059742093320689,
        "mean1": 3.4875202632823443,
        "overall": 2.66855454268595,
        "share1": 0.7157894736842105
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2023",
        "weight": 0.0625,
        "rows0": 213,
        "rows1": 29,
        "mean0": 3.10377336458297,
        "mean1": 3.71654176178796,
        "overall": 3.1772042882149734,
        "share1": 0.11983471074380166
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2024",
        "weight": 0.0625,
        "rows0": 160,
        "rows1": 82,
        "mean0": 2.1940324701136094,
        "mean1": 2.658675318107296,
        "overall": 2.351473435136264,
        "share1": 0.33884297520661155
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2025",
        "weight": 0.0625,
        "rows0": 81,
        "rows1": 162,
        "mean0": 1.1928329644114755,
        "mean1": 1.4470848588966878,
        "overall": 1.362334227401617,
        "share1": 0.6666666666666666
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2026",
        "weight": 0.0625,
        "rows0": 56,
        "rows1": 39,
        "mean0": 2.651651240249523,
        "mean1": 4.42435219694615,
        "overall": 3.379391632998664,
        "share1": 0.4105263157894737
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2022",
        "weight": 0.05,
        "rows0": 231,
        "rows1": 11,
        "mean0": 4.916188366723117,
        "mean1": 8.245195390377853,
        "overall": 5.067506867798331,
        "share1": 0.045454545454545456
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2023",
        "weight": 0.05,
        "rows0": 182,
        "rows1": 60,
        "mean0": 3.4528223944819074,
        "mean1": 2.9820577372874975,
        "overall": 3.3361038844337063,
        "share1": 0.24793388429752067
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2024",
        "weight": 0.05,
        "rows0": 202,
        "rows1": 40,
        "mean0": 4.356153497652737,
        "mean1": 6.464446652918049,
        "overall": 4.704631705134605,
        "share1": 0.1652892561983471
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2025",
        "weight": 0.05,
        "rows0": 130,
        "rows1": 113,
        "mean0": 1.173424417349841,
        "mean1": 3.8396399461587336,
        "overall": 2.413269498647803,
        "share1": 0.46502057613168724
      },
      {
        "asset": "510500.SS",
        "stratum": "510500.SS|2026",
        "weight": 0.05,
        "rows0": 25,
        "rows1": 70,
        "mean0": 0.9997309012305955,
        "mean1": 6.0719022266652125,
        "overall": 4.737120298919261,
        "share1": 0.7368421052631579
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2023",
        "weight": 0.0625,
        "rows0": 213,
        "rows1": 29,
        "mean0": 4.37608717347621,
        "mean1": 6.183971757948182,
        "overall": 4.592734499714586,
        "share1": 0.11983471074380166
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2024",
        "weight": 0.0625,
        "rows0": 190,
        "rows1": 52,
        "mean0": 5.306484478869431,
        "mean1": 4.95366195978785,
        "overall": 5.230671375595703,
        "share1": 0.21487603305785125
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2025",
        "weight": 0.0625,
        "rows0": 143,
        "rows1": 100,
        "mean0": 1.5854447791186315,
        "mean1": 6.449825609400559,
        "overall": 3.5872475899342393,
        "share1": 0.411522633744856
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2026",
        "weight": 0.0625,
        "rows0": 37,
        "rows1": 58,
        "mean0": 1.6735391486632551,
        "mean1": 8.607141351212645,
        "overall": 5.9066857565355155,
        "share1": 0.6105263157894737
      }
    ],
    "unsupported_strata": [
      {
        "asset": "510300.SS",
        "stratum": "510300.SS|2022",
        "rows0": 242,
        "rows1": 0,
        "reason": "both states not observed"
      },
      {
        "asset": "510050.SS",
        "stratum": "510050.SS|2022",
        "rows0": 242,
        "rows1": 0,
        "reason": "both states not observed"
      },
      {
        "asset": "588000.SS",
        "stratum": "588000.SS|2022",
        "rows0": 242,
        "rows1": 0,
        "reason": "both states not observed"
      }
    ],
    "comparison_available": true,
    "common_support_rows": 3530,
    "common_support_assets": 4,
    "fixed_common_means": {
      "condition0": 2.577604701877781,
      "condition1": 4.570126053795189,
      "difference": 1.992521351917408,
      "baseline": 3.5041502726227263,
      "identity_error": -4.440892098500626e-16,
      "unit": "percentage_point",
      "weighting": "equal supported assets; equal supported years within asset; same strata in both conditions",
      "evidence": "descriptive, not causal"
    }
  }
}
```

## 反例和结论边界

评价期资料没有参与训练或标准化；已有资料是否曾用于挑选方法仍以研究家族记录为准，换名字不成为新验证。预测改善不直接代表投资收益。

- Retrospective price-math reconstruction only; source action arrival null and Shanghai-specific calendar completeness not certified.
- Seen retrospective deterministic expression; no live PIT/trade certification.
- 加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：B2 underperforms B0
- 不同年份的改善方向相反，不能视作跨年份稳定帮助。
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。
- B2相对B0的范围仍包含改善及恶化，当前不能确认稳定帮助。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "Fixed four domestic broad ETFs fit the authorized domestic broad-index/ETF research scope. Correlated CSI300/SSE50/CSI500 and STAR50 are not four independent market replications; no transfer to all38, all6ETF, individual stocks or foreign indexes.",
    "source_refs": [
      "/Users/yongbiaoli/Documents/Codex/2026-09-30/task/supervision/t03-admission-2026-10-01/controller-scientific-decision.json",
      "/Users/yongbiaoli/Documents/Codex/2026-09-30/task/supervision/t03-admission-2026-10-01/admission/dependence-qualification.json"
    ]
  },
  "proxy_fidelity": {
    "reason": "Strict SMA20>SMA60>SMA120 and EMA20>EMA60>EMA120 exactly retains implementation4.5 boolean ordering. It omits slopes, clock, parallelism, pullback/bottom/hourly/target/execution conditions and covers only the guideT03 narrow ordering subset, not full sorting score/log-gap definitions or entireA/B.",
    "source_refs": [
      "/Users/yongbiaoli/Documents/Codex/2026-09-30/task/supervision/t03-admission-2026-10-01/controller-scientific-decision.json",
      "/Users/yongbiaoli/Documents/Codex/2026-09-30/task/supervision/t03-admission-2026-10-01/admission/dependence-qualification.json"
    ]
  },
  "method_fit": {
    "reason": "Full training X ranks13/14 with intercept and both states allow a bounded fixed-model numerical estimate.4340rows/1085dates are58state runs29true29false, same-date states shared, longesttrue144/false363 and overlapping21-close paths. Fold1 training13true/eval11true runs; fold2 training22true/eval7true5false runs with95mature dates, only1full60dateblock+35remainder. Never infer independent n, precision, stability or usefulness from row count/full rank. No selection of extra model/period when weak.",
    "source_refs": [
      "/Users/yongbiaoli/Documents/Codex/2026-09-30/task/supervision/t03-admission-2026-10-01/controller-scientific-decision.json",
      "/Users/yongbiaoli/Documents/Codex/2026-09-30/task/supervision/t03-admission-2026-10-01/admission/dependence-qualification.json"
    ]
  },
  "conclusion_scope": {
    "reason": "All history seen; saved economic-price/action math recomputed under explicit current replay clock with original action historic availability null. F is fully determined by six existing distances, so tests representation increment in fixed linear model only. Retain B0/B1/B2, asset/period counterexamples and source/calendar limits; no historical tradability, net alpha, production, fullLEI or stable factor claim.",
    "source_refs": [
      "/Users/yongbiaoli/Documents/Codex/2026-09-30/task/supervision/t03-admission-2026-10-01/controller-scientific-decision.json",
      "/Users/yongbiaoli/Documents/Codex/2026-09-30/task/supervision/t03-admission-2026-10-01/admission/dependence-qualification.json"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：insufficient；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。


## T03 主指标RMSE（百分点；MSE区间仅辅助）

0.10pp attention只对应B1 RMSE减B2 RMSE，不是sqrt(deltaMSE)或交易增量。
```json
{
  "primary_rmse": {
    "metric": "RMSE",
    "unit": "percentage_point",
    "B1": 4.0148768345144425,
    "B2": 4.011620250600831,
    "absolute_error_improvement": 0.0032565839136111663,
    "attention_threshold_pp": 0.1,
    "lo": -0.04851697891531781,
    "hi": 0.05895800888331882,
    "valid_draws": 2000,
    "unestimable_draws": 0,
    "dependence": {
      "block_length": 20,
      "draws": 2000,
      "seed": 20261001,
      "axis_scope": "evaluation",
      "secondary_block_length": 60
    },
    "secondary": {
      "metric": "MSE",
      "unit": "percentage_point_squared",
      "B1": 16.11923599632071,
      "B2": 16.093097035030674,
      "absolute_error_improvement": 0.026138961290037344,
      "lo": -0.4055987832493833,
      "hi": 0.4708894917962454
    },
    "scope": "fixed paired OLS expression forecast-error difference only; no account value or strong significance claim"
  },
  "primary_rmse_block60": {
    "metric": "RMSE",
    "unit": "percentage_point",
    "B1": 4.0148768345144425,
    "B2": 4.011620250600831,
    "absolute_error_improvement": 0.0032565839136111663,
    "attention_threshold_pp": 0.1,
    "lo": -0.07227060354273926,
    "hi": 0.08221086232861101,
    "valid_draws": 2000,
    "unestimable_draws": 0,
    "dependence": {
      "block_length": 60,
      "draws": 2000,
      "seed": 20261001,
      "axis_scope": "evaluation",
      "secondary_block_length": 60
    },
    "secondary": {
      "metric": "MSE",
      "unit": "percentage_point_squared",
      "B1": 16.11923599632071,
      "B2": 16.093097035030674,
      "absolute_error_improvement": 0.026138961290037344,
      "lo": -0.6516560209373289,
      "hi": 0.6129932974505286
    },
    "scope": "fixed paired OLS expression forecast-error difference only; no account value or strong significance claim"
  }
}
```