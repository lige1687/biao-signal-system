# 因子研究标准流程导航图（workflow map）

【来源：执行 agent 交付，**待主控复核的提案**】
本文只做既有规范与既有实现的导航与核对，不新建平行规范、不授予任何新权限、
不含新研究计算。日期：2026-09-17；任务：factor-workflow-audit S1。
所有"已验证"均指主控复核报告原文裁决；其余为代码/文件事实（附路径与哈希，见
`sources-and-checks.json`）。

## 一句话结论（大白话）

因子研究的标准流程其实已经有了，只是散在七八份文件里。把它拼起来是八步：
**先想清楚问的是哪类问题 → 查数据有没有资格用 → 把研究方案冻结成协议 →
先用手算的小例子对答案 → 正式运行 → 主控独立复核 → 结果登记归档 →
（另行申请）生产或交易许可**。每一步都已有权威文档和真实可跑的入口；真正的
缺口集中在三处：历史数据"当时是否可知"的逐行核验没实现、正式的"反复尝试后
偶然胜出"风险校正没实现、以及第二只标的/宽度/情绪的资格证据还没积累。

## 0. 定位：这是导航层，不是第九份规范

- 本图每一步只**引用**现行权威文档的章节，不复制其条文；条文以原文为准。
- 权威次序（沿 `definition-standard.md` §1，第 16 行）：根 AGENTS →
  `experiment-backtest-principles.md` v1.1 → `definition-standard.md` v1.1.0 →
  本轮协议 → 完整定义卡及输入版本。
- 本图不改变 `docs/trading-spec-v1.md`（V1.0）、`configs/rules.v1.yaml`
  （ruleset 1.5.0）、OKR、registry/INDEX，也不给任何对象新增有效性结论。

## 1. 八步流程总览

| 步 | 名称 | 权威文档（版本） | 真实入口（已核存在） | 产物 |
|---|---|---|---|---|
| 1 | 定问题与对象类型 | definition-standard §2/§7.1；principles §13 | `definitions.v1.json`（只读）+ `definitions.py::resolve/validate_registry` | 精确 `id@version` 或候选卡草案 |
| 2 | 数据资格 | principles §6；definition-standard §4；factor-unit-usage §2 | `factor_unit/study_contract.py::validate_study_contract`；`scripts/check_factor_unit_readiness.py` | 资格裁定（ok/restricted）、冻结候选包 |
| 3 | 冻结协议 | ai-execution-contract §1；principles §7/§11.1 | 各工具 protocol JSON + 合同校验（见 §1.3） | 不可变协议文件（SHA 绑定） |
| 4 | 手算测试（独立期望） | ai-execution-contract §2；factor-lab-usage §二.5 | `independent-expectations.json`（factor_lab）；factor_evidence 合同常量+测试集 | 独立期望文件、保护基线 |
| 5 | 运行 | 各使用手册 | 四条 CLI（见 §1.5），退出码语义各异 | manifest + values/diagnostics/quality 等 |
| 6 | 独立复核 | ai-execution-contract §4；principles §11.3 | 主控书面复核报告（`docs/experiments/` 日期命名） | 主控复核报告（接受/限定/返修） |
| 7 | 证据登记 | definition-standard §7.2；根 AGENTS 归档规约 | `docs/experiments/registry.json` + `INDEX.md` + 报告一句话结论小节 | 登记条目（category/verdict） |
| 8 | 生产/交易许可 | principles §8（三状态分离）；trading-spec 与规则账本 | 无代码入口——**只能由用户单独授权** | 授权记录；研究结论不自动产生 |

### 1.1 第 1 步：定问题与对象类型

- **先写清问的是哪类问题**（principles §13，第 279 行）：文档/数据计算核验、
  同日资产相对排序、单市场状态研究、完整政策比较、风险执行检查、已发生收益
  解释——**不同问题用不同验证，不统一考试**。
- 对象六类型（definition-standard §2）：`feature` / `state_signal` /
  `factor_return` / `risk_metric` / `benchmark` / `policy/strategy`；
  用途枚举 `description/ranking/research_signal/attribution/comparison/diagnostic`，
  `production_trade` 不在允许用途。
- **需填写**：精确 `id@version`（不写 latest）；新因子先写候选卡草案（先例：
  `docs/experiments/raw/factor-research-workbench-v1-2026-09-14/candidate-card-dual-ma-bull-state-draft-1.md`），
  不进登记表。卡内 `uses` 与 `not_for` 不得相交。
- **登记表现状（本轮独立复核结构）**：81 对象（feature 19 / state_signal 26 /
  factor_return 2 / risk_metric 4 / benchmark 15 / policy/strategy 15），
  2 个 profile，`models=[]`，version 1.2.0——与
  [factor-library-progress-2026-09-16](../../../experiments/factor-library-progress-2026-09-16.md)
  §3.1 的主控已验证计数一致。
- **未实现**：`definition-standard` §7.3（第 137–140 行）自述——TargetSpec/
  Evidence 合同**未接入**现有 runner/schema/校验器；规范写了不等于机器会查。

### 1.2 第 2 步：数据资格

- **底线**（principles §6）：只用当时已经知道且已生效的信息；快照取得时刻
  ≠ 历史可得时刻。
- **真实输入的证据链字段**（factor-unit-usage §2）：`price_basis_evidence`
  `{path, sha256}` 逐产品一致；`vendor_response_ref` 结构化且绑定同产品/
  输入哈希/请求参数/价格语义；日历做内容级核验（本地 CN 日历覆盖
  2019-09-01—2026-06-30）；`available_at` 未知写 null。
- **真实目标闸**（B0 四项修复，主控 T1–T4 关闭）：供应商前复权价未经主控
  确认的资料一律 `target=blocked` + `manual_target_review_required`；
  与含分红财富的等价性是"未核"，不是已证不等价。
- **未实现**：逐行真实历史可得时间（point-in-time）核验——B0 对
  `point_in_time_verified=true` 一律拒绝；宽度历史名单的当时可得性同样未核
  （[breadth-readiness 主控复核](../../../experiments/factor-breadth-readiness-controller-review-2026-09-17.md) §9 G2）。

### 1.3 第 3 步：冻结协议

- 协议必须绑定：身份/版本、对象 `id@version`、规范路径+版本+SHA、必需代码键
  全集哈希（不可裁剪）、输入身份（文件 SHA）、容差、固定参数、`no_claims`。
- 三个已冻结先例（本轮核到文件存在）：
  - factor_lab：`docs/experiments/raw/factor-research-workbench-v1-2026-09-14/protocol-{1-numerical,2-state,3-attribution}.json`；
  - B1：`docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/protocol-v1.0.1.json`
    （SHA `00a16465…`，主控记录见 b1-closeout §2）；
  - 证据可靠性：`docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16/protocol-v1.0.0.json`
    （SHA `769a3501…`，身份 `factor-evidence-reliability@1.0.0`）。
- factor_lab 特有纪律（usage §二.5）：协议携带 `required_checks` 字段即被拒；
  容差只允许 {0, 1e-9, 1e-6, 0.01}；期望必须与独立期望产物值级一致。
- **未实现/待协调**：B1 收口缺口 #4——修后代码尚无新正式冻结运行包，
  SPEC_VERSION 仍为 1.0.1，下一版本需另行协调校验器版本常量、任务授权与
  冻结构建（b1-closeout §3）。

### 1.4 第 4 步：手算测试（独立期望）

- 先写独立预期再计算（ai-execution-contract §2）；期望来源必须独立于被测
  输出（复核者不得复制被测输出当期望值，§1）。
- factor_lab：`independent-expectations.json` + `derive_expectations.py`
  （同目录），退出码 1 = 实现与手算期望不一致，不许放行。
- factor_evidence：合同常量（`REQUIRED_CODE_KEYS/REQUIRED_STANDARDS/
  FIXED_PARAMS/FIXED_TOLERANCE/REQUIRED_OUTPUT_FIELDS`，见
  `factor_evidence/contract.py`）+ 主控实跑 116 项回归与 ruff（R1–R4 复核）。
- **边界**：合成小例对得上手算，证明的是"算法在人工可验算的例子上没算错"
  （factor-lab 终版裁决 §1 边界），不是任何因子有效。

### 1.5 第 5 步：运行（四条真实 CLI，本轮均核到文件存在）

| 工具 | 命令（存在性已核，本轮未执行） | 退出码 | 输入限制 |
|---|---|---|---|
| factor_lab | `python3 scripts/run_factor_lab.py --protocol <不可变协议.json> --out <新目录>` | 0 完成 / 1 期望不符 / 2 资料不足 / 3 身份格式失败 | `data_mode` 只接受 synthetic |
| factor_unit 资格 | `python3 scripts/check_factor_unit_readiness.py --contract PATH --out NEW_DIR` | 0 资格齐备 / 2 restricted / 3 合同身份错误 | 只校验与打包，不算真实表现 |
| B1 描述 | `scripts/run_b1_dual_ma_description.py`（协议绑定 510300 固定输入） | 见各轮报告 | 真实输入逐 SHA 绑定 |
| 证据可靠性 | `scripts/run_factor_evidence_reliability.py` | 见 usage §1 | 真实入口只有 main；`run_analysis` 直接调用仅收显式合成（2026-09-17 主控 S1 收窄决定；**对应代码修改尚未完成**，见缺口） |

- 产物共同纪律：输出目录必须不存在（防覆盖）；manifest 记录规范/对象/代码/
  输入/协议哈希；`summary.md` 标题常驻"合成算法验证，非真实收益/有效性证据"
  （factor_lab）。

### 1.6 第 6 步：独立复核

- 主控必须交付可交回执行者的**书面**复核报告（ai-execution-contract §4），
  写明被审身份、已确认项、剩余问题与反例、最小返修范围、验收与停止条件；
  无返修项也须写"无"。
- 已接受的复核方式实例：独立重汇总封存观察表（b1-controller-review）、
  独立复算主要数字 + 实跑回归（factor-evidence-controller-review §9：
  116 项 + ruff）、逐字节哈希核验归档包（factor-lab 终版 §6：15/15 代码键）。
- 复核深度必须声明：独立重算、局部核查还是仅重跑同一实现（principles §11.3）——
  同一实现再跑一遍不算完全独立验证。

### 1.7 第 7 步：证据登记

- 结案报告落 `docs/experiments/主题-YYYY-MM-DD.md`，含"一句话结论（大白话）"
  小节，登记 `registry.json`（category 用固定枚举，verdict：
  passed/falsified/mixed/watch），INDEX.md 补导航行。
- 证据记录字段（definition-standard §7.2）：问题/研究家族、对象及依赖版本、
  目标合同或不适用理由、输入/代码/协议、独立复核范围、结论/反例/限制；
  不用新证据覆盖旧证据，不写永久 valid=true。
- **探索提案不登记**：本目录这类提案按
  [direction-exploration 先例](../factor-library-direction-exploration-2026-09-16/README.md)
  不进 registry/INDEX/OKR。

### 1.8 第 8 步：生产/交易许可（永远单独授权）

- 三状态分离（principles §8，第 197–204 行）：历史回测通过 / 冻结观察 /
  生产采用；研究验收不授权真实交易。
- 现状：本主线无任何生产交付与交易授权（progress §3.8；历轮主控裁决均重申）。

## 2. 按问题类型分流（不统一强制回归或 IC）

| 问题类型 | 适用对象 | 正确入口 | 明确不做 |
|---|---|---|---|
| 横截面排序吻合度（同日多标的分数 vs 后续结果排名） | 连续分数 `feature` | `factor_lab/diagnostics.py::evaluate_predictive` 的 `cross_section_ic` | 不当作赚钱证明；常数截面记缺失不填 0 |
| 单标的二元状态的时间关系（状态成立/不成立之后的平均结果差） | `state_signal`（如双均线候选） | `factor_unit/state_description.py::describe_states`；factor_lab 侧 `state_outcomes`（请求 IC 会得 `not_applicable`） | false 不是看空；未就绪不混成有效样本 |
| universe 轴状态/宽度（同日全池共用一个值） | 宽度类（B50/B200） | `time_series_state` 对**点名目标实体**跨日期诊断 | 复制成横截面会被拒绝；0–1 fraction 不套 20/80 分档 |
| 收益解释（钱从哪来） | `policy/strategy`、`factor_return` | `factor_lab/attribution.py` 三层：资金贡献对账 / 受控决策差额 / 风险模型解释 | 三层不相加；无模型卡时第三层 `not_run`；未解释收益不叫 alpha 或运气 |

分流的权威依据：principles §13"按研究问题选择验证"、definition-standard
§7.1（IC/RankIC 约定与状态/政策/风险另选检查）。**核验不要求盈利；政策对照
不要求先生成预测标签；状态可以有非单调关系。**

## 3. 当前各步状态速查（事实与建议分列见 capability-evidence.csv）

- 已接通（合成范围主控已验证）：第 1/3/4/5/6 步的 factor_lab 链；factor_unit
  B0 资格链；factor_evidence 体检算法。
- 已接通一次真实数据：B1（510300 双均线状态历史描述，数字主控接受，证据
  不足以支持稳定优势）。
- 未接通：逐行历史时点核验（第 2 步）、正式过拟合风险校正（第 4 步外侧）、
  风险模型回归（登记表 `models=[]`）、第二载体与宽度/情绪统一标准证据、
  生产接入（第 8 步）。
- 在途：证据可靠性 S1–S3 限定收尾（代码尚未改，ZCode 派发受阻，等用户选择
  执行方式）；宽度首轮历史描述（ZCode 独占任务，未交付，本任务未读其结果）。

## 4. 本图不做的事

- 不给任何对象新增有效性、收益或排名结论；
- 不把"规范已写"说成"机器已自动校验"（§7.3 合同未接 runner 是明文事实）；
- 不把 8 步串成每个对象都必须全走的关卡——缺口按用途分列
  （progress §5 的既定口径：外推用途要跨载体证据，解释用途要适配模型，
  交易采用另要账户/成本/执行检验）。
