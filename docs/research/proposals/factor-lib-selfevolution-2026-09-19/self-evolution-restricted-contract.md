# 自进化受限起步执行合同（self-evolution-restricted）

状态：**规划草案，待 GPT 评审；零执行**。与 factor-library-build-contract.md
同批、共享底座（状态模型/证据等级/manifest/blocked 语义以该合同 §1 P0 为准）。

## 0. 定位（GPT 2026-09-19 规划采纳）

**不是"建设自进化系统"，是"建设可审计的研究流程改进闭环"。**
自进化层只改进研究方法、实验流程、复核流程；不改变 trading-spec、不改变
评估尺子、不改变交易规则、不进入生产决策层。完整 replay、自主改规则、
自主部署均后置。

最小闭环（最后一步非自动部署）：

问题记录 → 方法变化候选 → 历史案例对照 → **人工批准** → 观察结果 →
是否纳入方法库

## 1. 第一阶段：Evaluator Memory / 案例台账（M1）

起步对象选评估器保护的保留案例库（不选实验流程单点改进——后者易形成
"失败→改方法→重跑成功→误认为改进"的自证循环）。

交付：
1. **案例台账 schema**（落点按 GPT 裁决＝`docs/research/methods/research-method-cases/`
   ——不叫 self-evolution/，防误解为系统已具备自主进化能力）：每条记录含
   ——哪个问题、为什么修改、修改前方法、修改后方法、适用范围、是否违反
   旧规则、是否改变评价标准。**字段不自造**：状态语义引用因子库合同
   F1 的四态（exists/verified/research_ready/production_approved）。
2. **导入既有案例**：从已结案报告中提取首批失败/阻塞/证伪案例（候选源：
   breadth-price50 判负、factor-method-reuse 暂停、S3 target 阻塞、
   v0.1 路线图错误修订等），每条按 schema 落库。
3. **Before/After 双轨模板**：任何方法改进必须同时保留旧方法结果、新方法
   结果与差异解释，不允许只展示新方法。
4. **反例配额（GPT 第 1 轮新增）**：第一阶段至少 1 个成功改进案例＋
   **1 个被拒绝的方法改进案例**——否则案例库天然偏向成功经验、产生
   自证循环。首条案例＝S2/S3 同名模块返修，分类为 `method_change_case`
   （非"失败案例"）：problem=test isolation contamination；old=same
   filename collision；change=rename execution artifacts；effect=test
   isolation restored；scope=testing workflow only；rule_changed=false——
   它证明的是方法改进可提高研究流程可靠性，不是系统自我修复成功。

验收：≥10 条真实历史案例入台账且 schema 字段完整；**含≥1 条被拒绝的
改进案例**；每条均可回溯到仓库报告路径；模板试用一条真实改进记录。

## 2. 防自证循环机制（硬边界）

1. **固定尺子**：trading-spec、评估标准、验收协议不可变。
2. **Before/After 双轨**：缺旧方法结果即不合格记录。
3. **失败案例必须入库**：防止台账变成"成功经验收集器"。
4. **不允许自动部署**：candidate method → review → adopt；禁止
   candidate → auto use。

## 3. 预算、路由与停止条件

- M1：glm-high，1 主派发＋≤1 返修。
- 停止条件：需要改评估标准才能记录"改进"；案例库开始出现第二套规则/
  第二套评估器语义；自动采纳链路；任何触碰 trading-spec 的诉求。
- Day7 联合复审检查点（与因子库线共用）：是否出现第二套规则、第二套
  评估器、自动采纳、因子效果暗示——任一出现即停线复审。

## 4. 后置事项（明确不做）

完整 replay（需稳定实验历史/成本记录/样本版本/评价协议，均未齐）、
自动改规则、自主部署、交易信号自优化。
