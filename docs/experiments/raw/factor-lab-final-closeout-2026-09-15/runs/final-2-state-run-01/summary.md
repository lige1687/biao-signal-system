# factor-lab-demo-2-state v1.2.0 — 合成算法验证，非真实收益/有效性证据

- 协议：`protocol-2-state.json`（文件SHA前12位 7b3cd8aaa58c），kind=state_diagnostic，资料模式=synthetic（合成）
- 期望核对：28 项，全部通过=True
- 生产授权：无；有效性声明：无（本运行不证明任何因子有效）

## 期望核对明细

- 通过 b200_at_change：期望 0.75，实际 0.75
- 通过 b200_at_first_valid：期望 0.6666666666666666，实际 0.6666666666666666
- 通过 b200_coverage_missing_days：期望 1，实际 1
- 通过 b200_first_valid_date：期望 2018-10-05，实际 2018-10-05
- 通过 b200_valid_days：期望 60，实际 60
- 通过 b50_at_change：期望 0.75，实际 0.75
- 通过 b50_at_first_valid：期望 0.6666666666666666，实际 0.6666666666666666
- 通过 b50_coverage_missing_days：期望 1，实际 1
- 通过 b50_day_before_change：期望 0.6666666666666666，实际 0.6666666666666666
- 通过 b50_first_valid_date：期望 2018-10-05，实际 2018-10-05
- 通过 b50_valid_days：期望 60，实际 60
- 通过 constant_breadth_ic_status：期望 not_applicable，实际 not_applicable
- 通过 dm_a_not_ready_rows：期望 20，实际 20
- 通过 dm_a_state_at_last_row：期望 1，实际 1
- 通过 dm_a_state_at_row21：期望 0，实际 0
- 通过 dm_a_state_at_row25：期望 0，实际 0
- 通过 dm_a_state_false_rows：期望 15，实际 15
- 通过 dm_a_state_true_rows：期望 30，实际 30
- 通过 dm_b_not_ready_rows：期望 20，实际 20
- 通过 dm_b_state_at_last_row：期望 0，实际 0
- 通过 dm_b_state_false_rows：期望 45，实际 45
- 通过 dm_b_state_true_rows：期望 0，实际 0
- 通过 so_dm_a_false_n：期望 15，实际 15
- 通过 so_dm_a_true_n：期望 8，实际 8
- 通过 so_dm_b_false_n：期望 23，实际 23
- 通过 so_dm_b_true_n：期望 0，实际 0
- 通过 ts_m1_n：期望 39，实际 39
- 通过 ts_m1_status：期望 descriptive_only，实际 descriptive_only
