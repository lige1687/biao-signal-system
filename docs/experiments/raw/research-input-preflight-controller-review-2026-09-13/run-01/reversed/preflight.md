# 研究输入检查结果

- 快照：`docs/experiments/raw/research-input-preflight-controller-review-2026-09-13/run-01/synthetic-snapshot`
- 用途请求：**description**；refs：（无）
- 评价期：2026-06-30 ~ 2026-06-01
- **request_satisfied = False**
- calculation_run = False；production_authorized = False

## 完整性

- verified：True
- 标的：1 只；行数：2；日期：2026-06-01 ~ 2026-06-02

## 六种用途

| 用途 | 质量裁决 | 产物声明 | 默认接受 | 原因 |
|---|---|---|---|---|
| description | unusable | True | ❌ | evaluation_window_empty: 评价期内没有任何报价 |
| ranking | unusable | False | ❌ | not_declared: 产物自身声明的用途不含 ranking |
| research_signal | unusable | False | ❌ | not_declared: 产物自身声明的用途不含 research_signal |
| attribution | unusable | False | ❌ | not_declared: 产物自身声明的用途不含 attribution |
| comparison | unusable | False | ❌ | not_declared: 产物自身声明的用途不含 comparison |
| diagnostic | unusable | True | ❌ | evaluation_window_empty: 评价期内没有任何报价 |

## 限制与未覆盖

- 未提供日历：所有依赖日历的检查按无合格日历降级
- request_satisfied=true 仅表示本次已实现的输入检查满足，不等于公式实现、历史可得时点、因子有效或交易授权

> request_satisfied=true 仅表示本次已实现的输入检查满足；不等于公式实现、历史可得时点、因子有效或交易授权。
