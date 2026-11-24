# synthetic-continuous（合成流程演示）

## 一句话结论（大白话）

本次方法下未得到新增帮助的支持。这里使用人工生成的数据，只证明流程行为，不说明市场规律。计算与检查完成不等于允许交易。

问题：人工示例候选；不声称复现注册A01公式
计划对象：SIM-0, SIM-1；实际有报价：SIM-0, SIM-1。
时期：['2022-01-03', '2022-05-27']；评价对象数量：82条、41个日期。
简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。

## 预测表现（与投资收益分开）

错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。

例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。

| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |
|---|---|---:|---|---:|---:|---:|
| B0 | MSE | 13.584611 | 百分点² | 82 | 41 | 2 |
| B0 | RMSE | 3.6857308 | 百分点 | 82 | 41 | 2 |
| B1 | MSE | 6.4299844 | 百分点² | 82 | 41 | 2 |
| B1 | RMSE | 2.5357414 | 百分点 | 82 | 41 | 2 |
| B2 | MSE | 6.4299844 | 百分点² | 82 | 41 | 2 |
| B2 | RMSE | 2.5357414 | 百分点 | 82 | 41 | 2 |

## 相对已有信息的增量

同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。

| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |
|---|---:|---:|---:|---:|---|---|
| B2 相对 B1 | 6.4299844 | 6.4299844 | 0 | 0% | -3.11062e-17 至 2.33315e-16 | percentage_point_squared |
| B2 相对 B0 | 13.584611 | 6.4299844 | 7.154627 | 52.67% | 6.67369 至 8.15572 | percentage_point_squared |

## 机会数量、风险与覆盖

固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。

描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。

```json
{
  "coverage": {
    "raw": 210,
    "calendar_slots": 210,
    "indicators": 208,
    "observations": 210,
    "feature_qualified": 208,
    "labels_evaluable": 202,
    "eligible": 200,
    "per_asset": {
      "SIM-0": {
        "raw": 105,
        "calendar_slots": 105,
        "indicators": 104,
        "observations": 105,
        "feature_qualified": 104,
        "labels_evaluable": 101,
        "eligible": 100,
        "reasons": {
          "feature_not_ready:quoted": 1,
          "eligible": 100,
          "immature_label": 4
        }
      },
      "SIM-1": {
        "raw": 105,
        "calendar_slots": 105,
        "indicators": 104,
        "observations": 105,
        "feature_qualified": 104,
        "labels_evaluable": 101,
        "eligible": 100,
        "reasons": {
          "feature_not_ready:quoted": 1,
          "eligible": 100,
          "immature_label": 4
        }
      }
    },
    "common_comparison": null,
    "common_comparison_reason": "not evaluated by input builder",
    "planned_assets": [
      "SIM-0",
      "SIM-1"
    ],
    "input_assets": [
      "SIM-0",
      "SIM-1"
    ],
    "input_missing_assets": [],
    "actual_assets": [
      "SIM-0",
      "SIM-1"
    ],
    "missing_assets": [],
    "partial": false,
    "evaluation_rows": 82,
    "evaluation_dates": 41
  },
  "descriptions": {
    "available": true,
    "population": "all_evaluable_observations (not restricted to forecast evaluation folds)",
    "raw_rows": 210,
    "evaluable_rows": 200,
    "common_prediction_rows": 82,
    "event_opportunities": 0,
    "excluded": [
      {
        "id": "SIM-0|2022-01-03",
        "reason": "feature_not_ready:quoted"
      },
      {
        "id": "SIM-0|2022-05-24",
        "reason": "immature_label"
      },
      {
        "id": "SIM-0|2022-05-25",
        "reason": "immature_label"
      },
      {
        "id": "SIM-0|2022-05-26",
        "reason": "immature_label"
      },
      {
        "id": "SIM-0|2022-05-27",
        "reason": "immature_label"
      },
      {
        "id": "SIM-1|2022-01-03",
        "reason": "feature_not_ready:quoted"
      },
      {
        "id": "SIM-1|2022-05-24",
        "reason": "immature_label"
      },
      {
        "id": "SIM-1|2022-05-25",
        "reason": "immature_label"
      },
      {
        "id": "SIM-1|2022-05-26",
        "reason": "immature_label"
      },
      {
        "id": "SIM-1|2022-05-27",
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

- Demonstration proxy only; historical identity, calendar authority and economic action scale require root qualification.
- 部分字段在训练时期没有变化，无法提供可学习的差别。
- B2相对B1的范围仍包含改善及恶化，当前不能确认稳定帮助。
- 预测评价只覆盖一个年份，不能据此确认跨年份重复。

## 主控判断（程序不能替代）

```json
{
  "universe_fit": {
    "reason": "人工样例验证机械行为，不能推断真实市场。登记A01仅用于来源解析演示，公式不等价。",
    "source_refs": [
      "docs/research/lei-factor-research-mission.md"
    ]
  },
  "proxy_fidelity": {
    "reason": "人工样例验证机械行为，不能推断真实市场。登记A01仅用于来源解析演示，公式不等价。",
    "source_refs": [
      "docs/research/lei-factor-research-mission.md"
    ]
  },
  "method_fit": {
    "reason": "人工样例验证机械行为，不能推断真实市场。登记A01仅用于来源解析演示，公式不等价。",
    "source_refs": [
      "docs/research/lei-factor-research-mission.md"
    ]
  },
  "conclusion_scope": {
    "reason": "人工样例验证机械行为，不能推断真实市场。登记A01仅用于来源解析演示，公式不等价。",
    "source_refs": [
      "docs/research/lei-factor-research-mission.md"
    ]
  }
}
```

## ARCHIVE / 最小决策卡

执行：completed；证据：not_supported；覆盖：本合同已声明范围；交易许可：无。
本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。
