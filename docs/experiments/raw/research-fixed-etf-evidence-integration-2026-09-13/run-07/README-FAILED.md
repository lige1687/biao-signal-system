# run-07：失败留痕（无 manifest，不构成完成证明）

- 日期：2026-09-13；入口：`scripts/prepare_momentum_qualified_inputs.py`（R1–R4 返修版）
- 协议：`protocol-v1.0.2.json`（8f8d5428…，本轮首版返修协议，保留不覆盖）
- 失败现象：读回核验拒绝——`normalized/*.csv extra=['economic_index.1']`
  （源 CSV 已带 economic_index 列，派生又追加一列，形成双列）。
- 根因：v1.0.2 从 v1.0.1 继承了 `inputs.snapshot_dir`（指向 run-02 派生
  快照——那是 run-05/06 动量 CLI 的**消费**输入）；派生入口的输入必须是
  **原始名义快照**。run-02 当时即以 canonical-snapshot-v2 为输入。
- 处置：协议升 v1.0.3（2c06525e…，snapshot_dir 改回 canonical-snapshot-v2，
  其余冻结输入逐字段相同）；派生以 run-08 重跑一次。本目录产物（部分
  snapshot/ 与 protocol-frozen.json）保留作为失败证据，不作任何完成依据。
