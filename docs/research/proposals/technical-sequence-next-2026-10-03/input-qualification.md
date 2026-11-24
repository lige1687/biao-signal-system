# 已知抵扣路径候选：无标签输入核查

检查时间：2026-10-03T14:04:25.988221+08:00，Asia/Shanghai。此处只检查历史价格文件是否能提供已知序列，不计算新信号、未来结果、模型或效果；0新标签、0拟合、0市场请求。研究方向、封存用途和历史预算均未改变。

实际读取共同panel，SHA256与原封存值一致。4ETF各1337行，2020-12-21至2026-06-30；无重复日期，无非正/非有限收盘价，按日期排序，4者与此panel日历一致。每个对象有1318个至少含20行历史价格的位置，足以形成 `C[t-19]..C[t-10]` 的已知价格片段。**这不是机会数量、独立样本数或因子有效证据。** 这次没有对候选计算值、筛选方向或检查未来目标。

输入自己标记historical_reconstruction/economic_price；action_known等字段虽然全True，只是已有资格记录的声明，不是本次独立证明。未核交易所完整日历、供应商历史到达、复权/行动完整性或独立新资料；旧数据已被项目研究反复看到。窗口齐全不解除这些限制。

协调：已读取coordination/lei规则及bootstrap、本任务记录；注册同题冲突未发现，未登记任务状态未知。本任务新效果与共享代码修改仍未开始。下一步固定这个候选的独立用途与表达，在最新任务记录明确分工后才能冻结效果合同；不能拿此输入检查当成已完成效果研究。

以下为实际检查回执。文件只交聚合字段与指纹，不上传价格原件。

```json
{
  "phase": "no_label_input_audit",
  "updated_at": "2026-10-03T14:04:25.988221+08:00",
  "input_path": "docs/experiments/raw/volume-information-2026-09-30/execution/panel.json",
  "size": 1582974,
  "sha256": "382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b",
  "data_mode": "historical_reconstruction",
  "price_series": "economic_price",
  "assets": [
    {
      "asset": "510050.SS",
      "rows": 1337,
      "first_date": "2020-12-21",
      "last_date": "2026-06-30",
      "duplicate_dates": 0,
      "input_chronological": true,
      "calendar_matches": true,
      "invalid_close": 0,
      "historical_20_bar_window_available": 1318
    },
    {
      "asset": "510300.SS",
      "rows": 1337,
      "first_date": "2020-12-21",
      "last_date": "2026-06-30",
      "duplicate_dates": 0,
      "input_chronological": true,
      "calendar_matches": true,
      "invalid_close": 0,
      "historical_20_bar_window_available": 1318
    },
    {
      "asset": "510500.SS",
      "rows": 1337,
      "first_date": "2020-12-21",
      "last_date": "2026-06-30",
      "duplicate_dates": 0,
      "input_chronological": true,
      "calendar_matches": true,
      "invalid_close": 0,
      "historical_20_bar_window_available": 1318
    },
    {
      "asset": "588000.SS",
      "rows": 1337,
      "first_date": "2020-12-21",
      "last_date": "2026-06-30",
      "duplicate_dates": 0,
      "input_chronological": true,
      "calendar_matches": true,
      "invalid_close": 0,
      "historical_20_bar_window_available": 1318
    }
  ],
  "status_counts": {
    "quoted": 5348
  },
  "action_known_counts": {
    "True": 5348
  },
  "volume_source_known_counts": {
    "True": 5348
  },
  "source_qualification_fingerprint": "9d150d608a5e8a88d11021b96f5e2ec5443dddf14c1a98b4ddc2fb4b01bee5f2",
  "new_labels": 0,
  "fits": 0,
  "market_requests": 0,
  "limitations": [
    "Row completeness does not verify original price qualification, corporate actions or historical vendor arrival.",
    "The calendar is this sealed panel calendar, not an independently confirmed exchange calendar.",
    "Window availability is input support, not number of independent signals or opportunities.",
    "No candidate value, outcome, test split or effect has been generated."
  ]
}
```
