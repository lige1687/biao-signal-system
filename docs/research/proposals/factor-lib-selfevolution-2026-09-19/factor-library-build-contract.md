# 因子库建设执行合同（factor-library-build）

状态：**规划草案，待 GPT 评审；除已授权的规划动作外零执行**。
任务线：`factor-lib-selfevolution-20260919`（衔接已收口的 factor-upstream-alignment
线与受限试点 PASS_RESTRICTED_PILOT）。

## 0. 目标与授权链

**总目标句（GPT 2026-09-19 第 0 轮规划采纳）**：在 trading-spec-v1 约束下，
建设可追溯因子库与受限自进化研究流程：让因子定义、证据链、实验过程和
方法改进均可登记、复核和回放；自进化只优化研究工作方法，不修改评价
标准、交易规则和生产决策。

服务层：trading-spec 规则层＝保护不修改；研究工具层/因子知识层/实验流程层
＝建设；生产交易层＝不进入。

授权链：用户 2026-09-19 原话「继续继续，跟chat一起 根据我们的文档为目标，
建设因子库和资金号好吧」＋澄清「说错了，是自进化就值钱文档里边写的」→
GPT `ACCEPT_NEW_TASK_INTERPRETATION_WITH_SCOPE_ADJUSTMENT`（本轮规划）。
三项边界确认按 GPT 推荐采纳（用户可否决）：Q1 第一阶段只建知识与证据库，
不做因子优选/收益比较/自动淘汰；Q2 自进化只建研究流程改进闭环；Q3 两线
并行共享底座（选 B）。

## 1. 范围（P0–P3）与非目标

**非目标（资格墙未解锁前禁止）**：因子排名竞争、IC 筛选、收益比较、自动
淘汰、参数优化、任何 target 依赖统计、broker/生产/交易自动化。

| 优先 | 内容 | 说明 |
|---|---|---|
| P0 | 因子定义合同完善（F1） | 81 张卡从"登记"变"可研究对象"：补齐 factor_id/version/formula/input requirement/frequency/availability requirement/target dependency/validation status/evidence level 字段标准与状态语义（**定义存在≠已验证≠可研究≠可生产** 四态分离） |
| P1 | 因子证据链模板推广（F2） | 复用 S3 受限模式推广为 Evidence Record：factor→input manifest→qualification→ranking reconstruction→sample ledger→blocked reason；每因子状态＝ranking_verified / target_blocked / historical_only / production_unapproved |
| P2 | 先问题后因子准入（F3） | 新入口：研究问题→需要什么信息→候选因子→定义登记→证据验证；含不符合问题定义的拒绝案例 |
| P3 | 账本与模板沉淀 | manifest 模板、blocked 模板、experiment record、cost record（不建完整成本系统） |

## 2. 阶段、验收与路由

| 阶段 | 目标 | 验收 | executor | 预算 |
|---|---|---|---|---|
| F1 卡片硬化 | 卡片字段标准＋状态语义＋证据等级落地 definitions.v1.json 及校验器（存量卡逐张补齐或加注） | 抽样审核：无一张卡能被误读为"存在=验证"；校验器拒绝缺字段 | glm-high | 1 主派发＋≤1 返修 |
| F2 证据链模板 | Evidence Record 模板＋迁移样例：抽 3–5 个已有因子生成一致格式报告（含 ≥1 个 target_blocked 样例） | 不依赖 target 也能形成完整报告；样例报告经独立复算（沿用 S3 reference-check 模式） | glm-high | 1 主派发＋≤1 返修 |
| F3 问题驱动准入 | 新因子准入流程文档＋审批点＋拒绝案例 | 试用一个真实候选走完全流程（纸面） | glm-max | 1 主派发 |

**待 GPT 评审裁决项**：F2 样例因子的真实输入运行口径——每个样例因子按
S3 受限模式（BLOCK_AWARE）各 1 正式＋1 复算？还是先只做 1 个样例的完整
真实运行、其余 2–4 个用合成输入演示模板？主控倾向后者（真实额度节约、
模板验证已足够），请 GPT 定。

## 3. 共享底座（两合同共用，Day1–2 冻结）

状态模型（四态分离）、证据等级、manifest 模板、blocked 语义——以本合同
§1 P0 的字段标准为准，自进化合同的案例库 schema 引用同一套语义，不另建。

## 4. 预算与停止条件

- 总预算：主派发≤3（F1/F2/F3 各 1）＋返修≤2；无真实预测运行；无真实
  交易；无 broker；F2 真实受限运行额度按 §2 裁决项执行。
- 停止条件：需要 target 统计才能交付；需要改 trading-spec/评估尺子/资格
  闸门；出现第二套登记表或第二套评估器；额度耗尽。

## 5. 2026-09-19 GPT 第 1 轮裁决登记

- **F1 授权 GRANTED**（scope＝registry semantics only）：四态分离
  exists→verified→research_ready→production_approved；禁止因子评分/排名/
  删除低质量因子/按历史表现淘汰（防提前进入因子选择）。
- **F2 设计批准、执行未授权**：口径收窄为"**单因子真实受限证据链样例＋
  多因子合成覆盖验证**"（合成侧覆盖：正常因子/输入缺失/target 依赖/定义
  版本变化四型；不选'表现最好'的因子；真实样例遇 target 阻塞不算失败，
  阻塞状态正确＋模板完整＋证据链闭环即可验收）。
- **F3 未启动**。
- **完成不代表升级**（本阶段完成表示基础设施和流程具备审计能力，不表示
  因子验证完成、自进化能力完成或生产授权获得）——本条同时写入
  self-evolution-restricted-contract.md。

## 6. 2026-09-19 GPT 第 2 轮裁决登记（F1/M1 评审 + F2 授权）

- **F1 评审 PASS**（无返工）：四态分离成立、verified 保守口径正确、
  production 结构性禁止通过、校验器使 lifecycle 成为约束而非标签。建议：
  F2 的 Evidence Record 直接消费 lifecycle，不另造状态（lifecycle＝因子
  状态；evidence record＝该状态为何成立）。
- **M1 评审 PASS**（无返工）：四硬边界机械落实、状态四值优于成败二元、
  反例配额满足。建议：README 注明"当前校验器为项目内审计辅助，不等同
  通用 schema 标准验证器"（已落实）。
- **F2 授权 GRANTED_WITH_SCOPE**（executor＝glm-high，主派发 1＋返修≤1，
  真实额度＝1 正式受限运行＋1 独立复算，返修不追加、不换因子重跑）：
  - 允许：一个真实受限样例（复用 S3 模式：definition→manifest→
    qualification→ranking reconstruction（若允许）→sample ledger→blocked
    report→independent check；遇 target BLOCKED 输出"Evidence complete,
    Target analysis unavailable"，不是失败）＋2–4 个合成因子覆盖四型
    （正常完整链/输入缺失 blocking/target 依赖 qualification 阻断/
    版本变化 lifecycle 校验）。
  - 验收：G1 模板一致性（同一字段结构覆盖真实＋四型）；G2 状态正确性
    （报告生成不改变任何卡 lifecycle）；G3 阻塞正确性（≥2 个 BLOCK）；
    G4 独立复算（不得 import 被测实现）。
  - 禁止：因子比较/排名/打分/推荐；有效性宣称（"有效因子/优质因子/
    最佳候选"）；自动升级 lifecycle（跑通模板不等于卡片升级，仍守 F1
    证据规则）；与 M1 联动（不出现"因子证据→自动改研究方法"）。
- **F3 维持未授权**（待 F2 完成后再决定）。下一控制门＝F2 终审。
