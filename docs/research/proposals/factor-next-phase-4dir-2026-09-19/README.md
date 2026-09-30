# 四方向下一阶段：子合同集（factor-next-phase-4dir-20260919）

授权链：用户 2026-09-19 原话「可以啊，okr先推进吧，下一阶段开始做4个方向
好吧，我认可了，开整」→ GPT（6 Pro）第 0 轮规划
`APPROVE_FOUR_DIRECTION_PLANNING`（结构＝一父线四子线；首批 A1/B1/C1/D1）。

结构：父线＝okr-cd1a0bd5532c（保持 approved）；四个子合同：

| 子线 | 合同 | 首批阶段（executor） |
|---|---|---|
| A 资格路径 | [qualification-path-contract.md](qualification-path-contract.md) | A1 证据模型（glm-high）→ A2 小样本补证（glm-max） |
| B 覆盖扩充 | [factor-coverage-contract.md](factor-coverage-contract.md) | B1 问题驱动候选池（glm-high） |
| C 自进化 M2 | [self-evolution-m2-contract.md](self-evolution-m2-contract.md) | C1 before/after＋失败分类（glm-high） |
| D P1 裁决 | [p1-direction-decision-package-contract.md](p1-direction-decision-package-contract.md) | D1 裁决材料框架（glm-max） |

共享底座（不重复建设）：definitions v1.3.0 lifecycle、Evidence Record 七阶段、
research-method-cases 台账、factor-admission 准入流程。

**用户拍板项（按 GPT 建议先行采纳、可否决）**：
- Q1 available_at 来源策略：**选 B（官方披露＋规则推导）起步**，Tier3 用户
  供料仅在历史缺口时由用户主动提供（标 user_supplied=true）；
- Q3 B 覆盖规模：**第一批 4–8 个候选问题**（4 通过＋2 拒绝为验收）；
- Q2 P1 方向最终选择：**维持待用户**（D1 材料包完成后裁决，GPT 不代裁）。

全局护栏（四线同守）：不改交易规则与评估尺子；不绕过 target 资格；
不做因子有效性宣称；不自动进化；不进生产；零 commit（用户未指示）。
