# A 子合同：资格路径建设（qualification-path）

目标句：**不是"打开资格墙"，而是建立 research_signal 从 conditional 到
可判断状态所需的证据链**——是否最终通过由规则决定，不由本线决定。

## A1 证据模型（glm-high，1 主派发＋≤1 返修）

- **available_at 三层来源**（Q1 已选 B 起步）：
  - Tier1 官方披露时间（交易所/基金公司/法定披露）：字段 event_time、
    publication_time、source、source_hash、availability_scope；
  - Tier2 规则化时间（公告发布后第 N 交易日生效类）：必须
    `derived_from_rule=true` ＋规则出处，不得伪造成公告时间；
  - Tier3 用户供料（仅历史缺口、用户主动提供）：`user_supplied=true`，
    不与系统发现混同。
- **四时间字段语义表**（不得混淆）：event_time（事件发生）/
  publication_time（对外披露）/ available_at（系统可获得）/
  effective_time（市场生效）。
- **公司行动时间链**：在 fixed-etf 线已核基础上（6 条分红公告、
  normalized-actions 21 条）统一 action event＋announcement＋effective
  date＋available_at；自动核（字段完整/时序/hash/来源链接/规则推导）与
  必须人工（来源真实性/历史可获得性解释/无公告裁决）分列。
- 交付：`docs/research/qualification-path/` 证据模型＋schema＋既有 21 条
  行动的分层盘点（每条当前缺哪层）；不改资格闸门。
- 验收：时间字段语义零混淆（负向测试）；盘点覆盖 21/21。

## A2 小样本补证（glm-max，1 主派发；A1 验收后另行授权）

- 选 3–5 条历史行动走通完整时间链（Tier1/2 为准）；**不一次补 21 条**；
  每条留来源/hash/推导依据；产出「research_signal 可判断性差距报告」
  （还差什么才能从 conditional 变可判断）。
- 验收：小样本链完整可审计；差距报告逐条对应资格闸门的拒绝原因。

## 边界

不修改 require_use/USES/质量裁决规则；不宣称资格已解除；Tier3 未经用户
提供不得虚构；零真实预测运行。
