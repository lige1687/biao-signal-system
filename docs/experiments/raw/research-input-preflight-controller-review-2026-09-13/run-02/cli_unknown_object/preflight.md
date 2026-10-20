# 研究输入检查结果

- 快照：`/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-input-preflight-controller-review-2026-09-13/run-02/synthetic-snapshot`
- 用途请求：**description**；refs：['nosuch.object@1.0.0']
- 评价期：2026-06-01 ~ 2026-06-02
- **request_satisfied = False**
- calculation_run = False；production_authorized = False

## 完整性

- verified：True
- 标的：1 只；行数：2；日期：2026-06-01 ~ 2026-06-02

## 六种用途

| 用途 | 质量裁决 | 产物声明 | 默认接受 | 原因 |
|---|---|---|---|---|
| description | usable | True | ✅ |  |
| ranking | conditional | False | ❌ | not_declared: 产物自身声明的用途不含 ranking |
| research_signal | conditional | False | ❌ | not_declared: 产物自身声明的用途不含 research_signal |
| attribution | usable | False | ❌ | not_declared: 产物自身声明的用途不含 attribution |
| comparison | conditional | False | ❌ | not_declared: 产物自身声明的用途不含 comparison |
| diagnostic | usable | True | ✅ |  |

## 对象检查

| 对象 | 已解析 | 允许该用途 | 直接可满足 | 缺字段/原因 |
|---|---|---|---|---|
| `nosuch.object@1.0.0` | False | None | None | ValueError: unknown exact definition version: nosuch.object@1.0.0 |
> 完整解析卡与递归依赖见 manifest.json 的 `objects.<ref>.resolved_cards_closure`。

## 限制与未覆盖

- 未提供日历：所有依赖日历的检查按无合格日历降级
- 既有机器绑定限制：validate_registry 仍要求 standard_version==1.0.0，而正文标准已为 1.1.0；如实保留，不改版本字符串冒充迁移
- 以下对象未满足字段/用途检查：['nosuch.object@1.0.0']；这是已实现的机械字段检查的结论，不是完整公式语义证明
- request_satisfied=true 仅表示本次已实现的输入检查满足，不等于公式实现、历史可得时点、因子有效或交易授权

> request_satisfied=true 仅表示本次已实现的输入检查满足；不等于公式实现、历史可得时点、因子有效或交易授权。
