# 研究输入检查结果

- 快照：`docs/experiments/raw/research-identity-wiring-2026-09-10/canonical-snapshot-v2`
- 用途请求：**description**；refs：['mixed.price.economic@1.0.0', 'mixed.momentum.raw@1.0.0', 'trend.sma200@1.0.0']
- 评价期：2019-09-02 ~ 2026-06-30
- **request_satisfied = False**
- calculation_run = False；production_authorized = False

## 完整性

- verified：True
- 标的：14 只；行数：18916；日期：2019-09-02 ~ 2026-06-30

## 六种用途

| 用途 | 质量裁决 | 产物声明 | 默认接受 | 原因 |
|---|---|---|---|---|
| description | usable | True | ✅ |  |
| ranking | conditional | True | ❌ | starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市 |
| research_signal | conditional | True | ❌ | zero_volume_days: 存在零成交量日（可能停牌或无成交，本轮不区分——无停牌数据源可核）; action_available_at_unknown: 21/21 条行动缺少 available_at（其中 3 条有 announcement_date 可作「不晚于该日已公布」的下界，18 条完全未知）；下界不等于精确到达时刻，一律不写入 available_at。本批只能用于历史重建，不得声称当时可知 |
| attribution | conditional | True | ❌ | zero_volume_days: 存在零成交量日（可能停牌或无成交，本轮不区分——无停牌数据源可核）; action_available_at_unknown: 21/21 条行动缺少 available_at（其中 3 条有 announcement_date 可作「不晚于该日已公布」的下界，18 条完全未知）；下界不等于精确到达时刻，一律不写入 available_at。本批只能用于历史重建，不得声称当时可知 |
| comparison | conditional | True | ❌ | starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市; starts_after_window: 首个报价晚于评价期起点；缺少上市资格证据——不得自动判为晚上市 |
| diagnostic | usable | True | ✅ |  |

## 对象检查

| 对象 | 已解析 | 允许该用途 | 直接可满足 | 缺字段 |
|---|---|---|---|---|
| `mixed.price.economic@1.0.0` | True | True | False | ['economic_index'] |
| `mixed.momentum.raw@1.0.0` | True | True | False | ['economic_index'] |
| `trend.sma200@1.0.0` | True | True | False | ['economic_index'] |

## 限制与未覆盖

- 日历路径与哈希不等于发布时点已获证明；跨所与年度覆盖限制照旧保留
- 既有机器绑定限制：validate_registry 仍要求 standard_version==1.0.0，而正文标准已为 1.1.0；如实保留，不改版本字符串冒充迁移
- 以下对象未满足字段/用途检查：['mixed.price.economic@1.0.0', 'mixed.momentum.raw@1.0.0', 'trend.sma200@1.0.0']；这是已实现的机械字段检查的结论，不是完整公式语义证明
- request_satisfied=true 仅表示本次已实现的输入检查满足，不等于公式实现、历史可得时点、因子有效或交易授权

> request_satisfied=true 仅表示本次已实现的输入检查满足；不等于公式实现、历史可得时点、因子有效或交易授权。
