# factor-lab-demo-1-numerical v1.0.0 — 合成算法验证，非真实收益/有效性证据

- 协议：`protocol-1-numerical.json`（sha256 前12位 209325671605），kind=predictive_diagnostic，资料模式=synthetic（合成）
- 期望核对：16 项，全部通过=True
- 生产授权：无；有效性声明：无（本运行不证明任何因子有效）

## 期望核对明细

- 通过 momentum_first_valid_row：期望 253，实际 253
- 通过 momentum_alpha_row252：期望 8.95949559，实际 8.95949559
- 通过 rv20_alpha_row252：期望 5.923488742023525e-09，实际 5.923488742023525e-09
- 通过 distance50_alpha_row252：期望 0.2630064816900779，实际 0.2630064816900779
- 通过 distance200_alpha_row252：期望 1.2937180362899454，实际 1.2937180362899454
- 通过 ic_mean_3：期望 1.0，实际 1.0
- 通过 n_periods_3：期望 26，实际 26
- 通过 min_n_3：期望 3，实际 3
- 通过 ic_mean_5：期望 1.0，实际 1.0
- 通过 min_n_5：期望 4，实际 4
- 通过 max_n_5：期望 5，实际 5
- 通过 scale_invariance_max_diff：期望 0.0，实际 0.0
- 通过 append_invariance_max_diff：期望 0.0，实际 0.0
- 通过 dev_label_crossing_n：期望 24，实际 24
- 通过 validation_label_crossing_n：期望 24，实际 24
- 通过 trial_history_status：期望 provided，实际 provided
