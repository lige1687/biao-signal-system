# 补充证据清单（应主控审核 F2 要求增补，2026-09-13）

用途：主控审核（qlib-alpha158-controller-review-2026-09-13.md）指出原报告
§5 对 CSZScoreNorm 拟合方式的断言不成立，要求补入同一固定上游引用的
processor.py 依据。本目录是独立补充证据，不覆盖、不改动原五份快照。

仓库：microsoft/qlib
固定提交：79633dd9506ea689e5400dea0197717b5b3d74b7（与原快照清单同一引用）
访问日期：2026-09-13
证据链接：https://github.com/microsoft/qlib/blob/79633dd9506ea689e5400dea0197717b5b3d74b7/qlib/data/dataset/processor.py

| 本目录文件 | 上游路径 | SHA-256 |
|---|---|---|
| upstream-processor.py | qlib/data/dataset/processor.py | 424af44e81c99467171c2d0b7978fb9f95d3b4c8b743a535ff4fe45d708cf517 |

本次确认范围（源码阅读，未运行处理器）：

- `CSZScoreNorm`（processor.py:300-323）：构造参数为 `fields_group/method`，
  **没有** fit_start_time/fit_end_time；`__call__` 按 `datetime` 分组，
  对同一日期不同产品的值应用 zscore（默认）或 robust_zscore。
  未穷尽其调用的标准化函数的全部边界。
- `ZScoreNorm`（processor.py:228-259）：构造参数含 `fit_start_time/fit_end_time`，
  `fit()` 仅取训练区间计算 `nanmean/nanstd` 并保存；属按训练期拟合固定参数。
  RobustZScoreNorm 同理（中位数/MAD 版）。
- 原报告把 CSZScoreNorm 描述成"按 fit_start/end 拟合"属与 ZScoreNorm 混淆，已修订。
