# 上游 v1.1 文档与本地仓库现状映射（alignment-map）

日期：2026-09-18。执行：ZCode 委派 job a6ac8ecc（stage S1）。
对象：上游 `lige1687/biao-factor` commit `2fddcdc` 两份文档（原件见
`sources/`，SHA256 见 `sources/manifest.json`）。
性质：**只读核对与映射，不含任何采纳决定、不含执行授权**。上游文档
自述「未读取当前完整仓库」（方向稿 §阅读边界），其事实断言一律不直接
采信，下表每条状态都给出本地仓库证据路径。

状态四级含义：**已实现有证据**＝仓库中存在对应实现且经报告/复核留痕；
**部分实现**＝有代码或文档但覆盖不全或未验收；**仅有规划**＝只在路线/
计划文档中出现；**未知**＝仓库中找不到对应物或无法核实。
（2026-09-19 GPT 终审补充）"已实现有证据"只说明实现存在且有留痕，多数
条目的验证范围是**合成例、文档级核对或主控复核**（factor_lab 工作台自述
"仅合成算法验证"），不等于已完成真实数据验证、被 Agent 主调用链接入或
完整满足上游合同；真实输入的历史数值复算先例见 §B P2 行。

## 一句话结论（大白话）

上游两份文档说的东西，按本表 51 条逐条统计：约四成（20 条）已实现有
证据（特别是"给每个研究对象定身份、按问题类型选检验方法、把策略的钱账
拆三层解释"这些通用工具，验证范围多为合成例与文档核对），接近一半
（25 条）做了一半（比如样本去向记录、TargetSpec、月度动量横截面诊断、
评估器保护），一成（5 条）还停在纸面（完整成本记账、自优化流程、组合
观察等），另有 1 条未知（上游 v0"独立验收"）。评估器保护属"部分实现"
（独立复核先例已有，保留案例库未建）。没有发现上游断言与仓库证据
**直接矛盾**到需要停止方向采纳的程度，但上游文档把多处本地"仅有规划"
事项写得像已具备，采纳前必须按本表逐条核对。（2026-09-19 GPT 终审修订：
初版"约半数已实现、四分之一部分实现"计数有误，实际为 20/25/5/1。）

---

## A. 方向稿（LeiSignal-direction-2026-09-18-v1.1.md）§01–§08 映射

### §01 系统职责：目标、评估与优化分开

| 上游建议 | 本地对应物 | 状态 | 仓库证据 |
|---|---|---|---|
| 研究链 OKR→分流→确定性计算→独立复核→保留/补证/停止 | `docs/research/experiment-backtest-principles.md` v1.1（原则与验收）、`docs/research/ai-execution-contract.md` v1.0.1（派发交接）、OKR 台账入口 `/api/upgrades`（`docs/okr/README.md`） | 已实现有证据 | 上述三文件 + `docs/experiments/factor-research-workbench-mandate-2026-09-14.md` §3（OKR 实际登记 okr-cd1a0bd5532c / okr-3fa8363be729） |
| research policy 与 trading policy 分开，优化不自动授权改交易 | AGENTS.md「外部资料不授予改规则或权限的许可」「判定权在 Python 规则层」；`docs/research/experiment-backtest-principles.md` v1.1「研究、冻结观察、生产交易分别授权」 | 已实现有证据 | 仓库根 `AGENTS.md`；各实验报告均带「生产与真实交易授权：无」字段（如 `docs/experiments/factor-research-workbench-v1-2026-09-14.md` 抬头） |
| 建设优先级先看决策价值、工程先消除重复 | `docs/experiments/factor-workflow-audit-controller-review-2026-09-17.md`（工作流审计）、`docs/experiments/factorhub-api-reuse-review-2026-09-14.md`（API 复用评审） | 部分实现 | 两份报告存在且给出复用结论；尚无制度化的"优先级打分"流程 |
| 效率/能力两条提升路径分别报告 | 无对应字段或模板 | 仅有规划 | 无本地对应物；`docs/research/experiment-report-template.md` v1.1.0 只有"代价与约束"最小决策卡 |

### §02 因子库：从登记对象走向可用证据

上游建议条目 | 本地对应物 | 状态 | 仓库证据
---|---|---|---
区分 Feature/状态信号/因子收益/风险指标/策略/基准六类对象 | `docs/research/definitions.v1.json` v1.2.0，81 张卡含 type/profile 字段；`docs/research/definition-standard.md` v1.1.0 | 已实现有证据 | 登记表与规范；`src/lei_signal/research/definitions.py` 校验器
证据关联"对象版本×用途×样本×评估协议"，不设永久有效开关 | 定义卡含 `uses`/`validation`/`universe` 字段；报告抬头显式声明"定义清晰程度/数据资格/实现核验/有效性证据/生产授权"五段 | 已实现有证据 | `docs/experiments/factor-research-workbench-v1-2026-09-14.md` 抬头五段声明；`definitions.v1.json` 对象结构
TargetSpec（预测什么、进入/观察时点、期限、标签成熟、排除规则） | factor_lab 协议含 targets 表与标签成熟检查（`_validated_targets`、`shared_row_exclusion`），但无独立命名的 TargetSpec 合同对象 | 部分实现 | `src/lei_signal/research/factor_lab/diagnostics.py`；workbench v1 报告 §2（"t+1→t+22 测量目标，非可成交开盘"）。上游路线图稿 §5.2 的完整字段表（可交易性、缺失与末端、防泄漏分组）本地未成独立合同
"真实接入"最小回归集（手算小例、并列常数截面、预热不足、缺失终止、跨日历、公司行动、标签未成熟） | workbench v1 三类端到端合成例 50 项手算期望 + 94 项测试 + 316 项回归 | 部分实现 | `docs/experiments/factor-research-workbench-v1-2026-09-14.md` 一句话结论与 §8；覆盖含并列/常数/未成熟标签，但**未覆盖公司行动与供应商修订历史快照**（合成输入无此场景） |
时点可选池/数据快照/分红口径/交易日历输入资格 | 数据基础修复线：`docs/experiments/research-data-foundation-controller-review-2026-09-13.md`（R1/R2/R3 收口，真实数据仅描述诊断可用）；`docs/experiments/research-input-preflight-2026-09-13.md` | 部分实现 | 上述报告；四类漏放中人为上市证明已改为拒绝，但"可复用的离线输入验收入口"仍是下一步建议，未建成 |

### §03 研究方法按用途分流

上游建议条目 | 本地对应物 | 状态 | 仓库证据
---|---|---|---
五类任务（库建设/横截面/时间序列状态/政策对照/风险解释）分别验收，不强制全过 IC | factor_lab `evaluate_predictive` 按对象类型分流 IC/状态/宽度诊断，含 `not_applicable(reason)` 机制；roadmap v0.3 导航"共同宽度、二元状态、收益因子和风险指标不能混一类" | 已实现有证据 | `src/lei_signal/research/factor_lab/diagnostics.py`（`_cross_section_ic`/`_state_outcomes`/`_time_series_state`/`not_applicable`）；`docs/research/factor-research-roadmap-2026-09-10.md` 顶部 v0.3 导航段
Pearson IC 与 Spearman Rank IC 命名分开、小池不强制十等分 | `_cross_section_ic` 同一配对集合计算两种 IC；roadmap §1"分几份取决于有效样本量"；method-reuse 提案对 Alphalens `factor_information_coefficient`（Spearman）已逐项核对 | 已实现有证据 | `src/lei_signal/research/factor_lab/diagnostics.py`；`docs/research/proposals/factor-method-reuse-2026-09-17/README.md` §1（Alphalens 0.4.5 源码核对）
方法卡（来源、已读范围、局限、本地差异、唯一主要假设） | `docs/literature-learning/README.md` v1.1.0（文献接入规范）+ method-reuse 提案内的来源核查台账 | 部分实现 | 上述文件；workbench v1 报告只对合成例写卡，真实文献方法卡仅在 method-reuse 调研线出现，未成通用模板
后续因子按缺口推进、暂不引入大型特征库/残差模型 | method-reuse 提案结论"本轮无立即执行建议"；roadmap §2 Value/Size/Quality 明确推迟 | 已实现有证据 | `docs/research/proposals/factor-method-reuse-2026-09-17/README.md` 一分钟说明；roadmap §2 因子族表

### §04 探索流程：每次正式研究先形成小合同

上游建议条目 | 本地对应物 | 状态 | 仓库证据
---|---|---|---
研究前小合同（KR、疑问、证据、路线、假设、预算、停止条件、复核人） | `docs/research/ai-execution-contract.md` v1.0.1 + 冻结协议先例（`docs/superpowers/plans/2026-09-14-factor-research-workbench-v1.md` v1.0.0、`docs/experiments/raw/factor-research-workbench-v1-2026-09-14/task-contract.md`） | 已实现有证据 | 上述合同与保护基线 `protection-baseline.json`
停止与结论分开记录、资源停止≠证伪 | `experiment-backtest-principles.md` v1.1；registry.json `verdict` 枚举含 watch/mixed（"证据不足"） | 已实现有证据 | `docs/research/experiment-backtest-principles.md`；`docs/experiments/registry.json` categories/verdict 字段
研究家族尝试史、跨 Agent 尝试归并 | factor_lab `audit_validation` 试验史审计；method-reuse 提案保留四轮 execution 外部访问实账 | 部分实现 | `src/lei_signal/research/factor_lab/validation.py`（`_trial_record`/`audit_validation`）；method-reuse README"外部访问实账"。跨 Agent 自动归并无统一机制，靠人工台账（trial 记录限于单次 lab 运行内；repair 1 重验 `validation.py` 全文无跨任务/跨 Agent 归并入口）
监测用新增事实、未成熟标签不提前计入 | 宽度冻结观察线 `docs/research/observations/breadth-v1/`（config.json `signal_observation_started: false`，input_observation_only 阶段）；factor_evidence 标签区间重叠审计 | 部分实现 | `docs/research/observations/breadth-v1/config.json`；`docs/research/factor-evidence-reliability-usage.md`（年份稳定性、留一年、重叠审计）。仅覆盖二元状态线，无通用监测平台

### §05 工程效率：确定性组件、复用、成本记录

上游建议条目 | 本地对应物 | 状态 | 仓库证据
---|---|---|---
重复计算沉淀为可测试组件 | `src/lei_signal/research/factor_lab/`（contracts/adapters/diagnostics/validation/attribution/runner）+ `scripts/run_factor_lab.py` CLI；`src/lei_signal/research/definitions.py` 唯一公式源 | 已实现有证据 | 目录与 `docs/research/factor-lab-usage.md` v（workbench 交付）
复用数值不继承资格（缓存≠合格） | factor_lab `fingerprint_path`/`protocol_sha256` 输入指纹绑定；定义卡 validation 字段 | 部分实现 | `src/lei_signal/research/factor_lab/contracts.py`。上游的"资格撤回→受影响消费者关联"机制本地无对应物（repair 1 重验：`grep -rn "withdraw\|revoke\|recall\|受影响消费者\|downstream" src/lei_signal/research/` 仅命中"只阻断受影响部分"的 scope 机制（`data_quality.py:24,82`），无撤回状态与消费者关联登记）
最小执行记录五组字段（身份/起点/决策/产物资格/复核成本） | 实验报告模板 v1.1.0 + registry 三件套 + raw manifest | 部分实现 | `docs/research/experiment-report-template.md`；各 raw 目录 manifest.json。成本组（模型调用、人工时间）**未系统记录**，method-reuse 提案仅手工记外部访问次数
模型分工按风险 | AGENTS.md「模型分工与额度节约」节（Astra/Sol/Spark 三层） | 已实现有证据 | 仓库根 `AGENTS.md`（2026-09-08 用户确认）
成本三层次报告（运行差额/建设投入/净节约） | 无对应物 | 仅有规划 | repair 1 重验：`grep -rn "净节约\|建设投入\|运行差额\|cost_baseline\|cumulative_saving" src/ --include="*.py"` 零命中，仓库中无按此口径的成本对照记录

### §06 自提升：改工作方法不改尺子

上游建议条目 | 本地对应物 | 状态 | 仓库证据
---|---|---|---
Dream-RSI 借鉴"记录→候选→对照→再部署"，不照搬论文倍数 | 无对应物（本地未立项任何 replay/自优化流程） | 仅有规划 | 上游方向稿 §06 自述"当前先做受控工作流程改进；完整 replay 后置"，本地无执行痕迹
评估器保护（复核方管理独立期望值、保留案例答案隔离） | 部分先例：主控独立复核模式（各 controller-review 报告"独立重算/实跑 pytest"），`verification` 独立于执行者 | 部分实现 | 如 `docs/experiments/breadth-preflight-controller-review-2026-09-18.md`（主控实跑 28 项测试、复算 33 项 SHA）；但无"保留案例库+答案隔离"机制
单点改进流程（批次归因→一个改进→新旧对照→复核→绑定） | method-reuse 提案是"调研收口、无立即执行建议"，结构上接近但未进入改进验证 | 仅有规划 | `docs/research/proposals/factor-method-reuse-2026-09-17/next-pilot-proposal.md`（试点规格保留、触发条件未满足）

### §07 首个试点：打通一条因子证据链

上游建议条目 | 本地对应物 | 状态 | 仓库证据
---|---|---|---
已登记排序因子打通"验证目标→标签→诊断→账户对照→条件证据"并记成本 | 现状：workbench v1 只到合成端到端；`factor-lab-final-closeout-2026-09-15.md`/`factor-lab-final-controller-decision-2026-09-15.md` 收口为工具建设，真实输入诊断未跑；B200 首次描述线（`breadth-b200-first-description-2026-09-17.md`）为状态线非排序线 | 部分实现 | 上述报告。排序因子的真实证据链（含账户关联与成本）**本地尚无一次完整执行**
沿用"动量选强×波动过滤"协议、不与快速回补混合 | 因子库 v0 四格已有结论（roadmap §2："整段多赚约59万但回撤加深5pp、分段方向相反"→条件依赖） | 已实现有证据 | `docs/experiments/factor-library-v0-delivery-2026-09-09.md`；roadmap §2 Volatility 行引用

### §08 推进顺序与 OKR

上游建议条目 | 本地对应物 | 状态 | 仓库证据
---|---|---|---
A–E 阶段（核对收口→证据链→成本基线→流程改进→扩展） | 本地对应排序见"合并点与冲突点"§C；OKR 台账已有因子方向条目 | 部分实现 | `/api/upgrades` okr-cd1a0bd5532c（方向）、okr-3fa8363be729（首轮工具）、okr-4f4157e2957e（外部资源，v6）
不建议以因子数量/回测条数/最高年化作 KR | roadmap §2"验收标准是问题被回答，不是曲线好看"；principles v1.1 | 已实现有证据 | `docs/research/factor-research-roadmap-2026-09-10.md` §2；`docs/research/experiment-backtest-principles.md` v1.1

---

## B. 路线图稿（LeiSignal-factor-roadmap-and-direction-metrics-v1.1-2026-09-18.md）§0/§4/§5/§6/§9 映射

### §0 主控先读（执行顺序）

| 上游条目 | 状态 | 仓库证据 |
|---|---|---|
| 先核数据漏放修复是否验收 | 部分实现 | `docs/experiments/research-data-foundation-controller-review-2026-09-13.md`：R1/R2/R3 在该轮范围收口（8 个错误放行改拒绝、253 项回归通过），但"可复用离线输入验收入口"仍是下一步，**不能写成整体已验收** |
| v0 是否完成真实接入 | 未知（上游也未取得验收包） | 本仓库无 v0 独立验收报告的直接对应；`factor-lab-final-controller-decision-2026-09-15.md` 收口对象是 workbench 工具而非上游所指 14 只池 v0 账户接入。两线关系需主控核对（见冲突点 C4） |
| 纯 50 日宽度挑战不再立项 | 已实现有证据 | `docs/experiments/breadth-price50-decision-2026-09-09.md`（判负收口）；roadmap v0.3 导航"已有判负是针对特定定义与接法" |

### §4 分阶段路线 P0–P5

| 阶段 | 上游要点 | 状态 | 仓库证据 |
|---|---|---|---|
| P0 输入资格漏放封堵 | 四类反例（哈希漏放、日历覆盖、单产品缺报价、公司行动身份/时间）修复+正反测试 | 部分实现 | 数据基础线报告（`research-data-foundation-summary-2026-09-10.md` → `research-data-provenance-round2-2026-09-10.md` → `research-data-foundation-controller-review-2026-09-13.md`）。上游引用的 `load_snapshot → check_snapshot → require_use` 调用链**本仓库已实现且已有编排入口**：`src/lei_signal/research/data_snapshot.py:831`（`load_snapshot`，离线读回并逐文件核对 SHA-256）、`src/lei_signal/research/data_quality.py:606`（`check_snapshot`）、`src/lei_signal/research/data_quality.py:381`（`require_use` 用途闸门）、`src/lei_signal/research/input_preflight.py`（薄编排复用三者，即 `research-input-preflight-2026-09-13.md` 交付）。维持"部分实现"的依据是 09-13 复审结论：R1/R2/R3 在该轮范围内收口（8 个错误放行改拒绝、253 项回归通过），但真实数据仍只有描述和诊断可用，"把已修好的检查接成可复用的离线输入验收入口"仍是后续建议，不宣称数据整体合格 |
| P1 v0 真实接入与独立验收 | 14 只池、月度无退出四格、两档费用、≤8 条正式路径 | 部分实现 | 因子库 v0 线：`docs/experiments/factor-library-v0-task-2026-09-09.md`、`factor-library-v0-delivery-2026-09-09.md`（跑通，账目误差 4.66e-10 元，但 roadmap §3 明示"只证明算术一致，不证明输入资料完整"）；**"独立验收"环节是否完成在仓库中未见对应收口报告，状态未知** |
| P2 动量排序诊断（样本去向/逐期诊断/条件结论三类交付） | 一个动量定义、固定池、逐月 Rank IC、同期参考差额 | 部分实现 | 工具侧已备：`mixed.momentum.raw@1.0.0`/`mixed.momentum.rank@1.0.0`（definitions.v1.json）、`_cross_section_ic`/`_quantile_groups_q2`（diagnostics.py）、`momentum_prototype.rank_diagnostic`（真实输入先例＝`docs/experiments/momentum-research-prototype-2026-09-13.md`：冻结输入 14 只、18,916 行，run-04 历史数值诊断复算 772 个动量值一致，真实预测按资格拒绝、历史诊断模式不写真实 targets/rank 结果；roadmap v0.3 导航引用该函数）。**P2 式横截面诊断（逐月 Rank IC＋样本去向＋条件结论三类交付）未发生**——已有的是真实输入的历史数值复算与 workbench v1 合成端到端，二者都不能替代 P2 执行。（2026-09-19 GPT 终审修订：初版把 rank_diagnostic 先例误指到 factor-lab-extension-2026-09-05.md，该文件是 market_context 面板实验区，与 momentum_prototype 无关。） |
| P3 宽度状态验证 | 已有宽度候选选一个解释问题 | 部分实现 | 21 张 breadth 卡 + `policy.breadth.*@1.0.0`；`factor-evidence-reliability-usage.md`（年份稳定性/留一年/重叠审计/成对循环分块重抽）；`breadth-b200-first-description-2026-09-17.md`（首次描述）。条件证据线在推进中 |
| P4 论文/外部参照/小型模型 | 方法卡、只读接入 | 部分实现 | `docs/literature-learning/README.md` v1.1.0；method-reuse 提案完成 statsmodels/arch/Alphalens/French 分层对照（暂缓接入） |
| P5 组合/执行/持续观察 | 影子观察、监控分层 | 仅有规划 | 宽度冻结观察线（observations/breadth-v1）是唯一真实观察实例，处于 input_observation_only 阶段；无组合对照框架 |

### §5 三个最小合同

| 合同 | 状态 | 仓库证据 |
|---|---|---|
| 5.1 定义合同（ID/版本/公式/单位/方向/依赖/时点/质量/计算绑定） | 已实现有证据 | `docs/research/definition-standard.md` v1.1.0 + `definitions.v1.json` v1.2.0（对象字段含 definition/dependencies/validation/universe）；`src/lei_signal/research/definitions.py` |
| 5.2 TargetSpec 合同 | 部分实现 | 无独立合同对象；factor_lab targets 表 + 标签成熟/重叠检查承担核心子集（见 §02 行）；`audit_validation` 的切分段检查（validation.py `_validate_split`）覆盖时间隔离 |
| 5.3 条件证据合同（证据键×用途×区间，无永久 valid 开关） | 部分实现 | 报告抬头五段声明（清晰度/资格/核验/有效性/授权）+ registry verdict 枚举是等价机制；上游 5.3.1"原因—证据—动作—重新开启条件"四字段无结构化落点（各报告散见，靠 template 最小决策卡近似） |

### §6 最小统计与测试规则

| 上游条目 | 状态 | 仓库证据 |
|---|---|---|
| 6.1.1 逐期 IC 计算单位、样本不足返回缺失不返回 0 | 已实现有证据 | `_cross_section_ic(*, min_pairs=3)` 样本不足走 `not_applicable`；`shared_row_exclusion` 保留排除原因（diagnostics.py） |
| 6.1.2 按日期分组再跨日期汇总、不合并日期×产品行 | 部分实现 | `_universe_pairs`/`_instrument_pairs` 分层配对 + `_quantile_groups_q2` 按日期组；跨期冻结权重汇总的字段化协议未见显式实现 |
| 6.1.3 不完整标签不改变事前排名 | 部分实现 | 排除发生在配对层（`shared_row_exclusion` 在值/标签两侧记录原因），事前排名表与统计配对集合分离的设计与上游一致；"原组已观测部分展示覆盖率"无对应输出 |
| 6.2 时间切分检查实际信息区间、重叠标签非独立 | 已实现有证据 | `audit_validation`（validation.py）：段边界、标签跨段泄漏检查、试验史登记 |
| 6.3 对照覆盖未选/未买/等待 | 部分实现 | attribution.py `_layer2_decision_increment` 决策增量层；"排除原因、替补、现金"字段化记录仅在因子库 v0 报告中人工呈现 |
| 6.4 独立复核独立产生期望 | 已实现有证据 | workbench v1 手算期望表 + 主控 controller-review 系列（如 breadth-preflight 主控实跑测试） |
| 6.5 结论分级由证据限制 | 已实现有证据 | `docs/research/experiment-backtest-principles.md` v1.1 措辞边界条款 + 各报告"不得升级为"列（roadmap §2 表） |
| 6.6 外部分析工具透明清洗 | 部分实现 | method-reuse 提案已逐项核对 Alphalens 0.4.5 清洗默认值并结论"暂缓"；本地未安装、未接入 |

### §9 执行合同与交付

| 上游条目 | 状态 | 仓库证据 |
|---|---|---|
| 9.1 任务最小模板 | 已实现有证据（本地已有等价物） | `docs/research/ai-execution-contract.md` v1.0.1 + 冻结协议/task-contract 先例；上游模板字段更细（P2 专项条目），可作映射参考不必新建 |
| 9.2 完成后交付（一句话结论、命令、退出码、版本、成本） | 部分实现 | 归档三件套（AGENTS.md）+ template v1.1.0；**成本（模型调用/人工时间）系统性缺失** |
| 9.3 合并为现有路线图章节、不建第二套登记表 | 本文件即该合并的第一步 | 本次 G3 导航追加即按此原则执行 |

### 路线图稿 §1–§3、§7–§8 的处理说明（2026-09-19 GPT 终审补）

初版映射只单列了路线图稿 §0/§4/§5/§6/§9，未交代其余章节的去向。核实结果：

- **§1 不变的研究原则（含 §1.1 对象划分、§1.2 弱但互补用法）**：操作性要求
  已由本表既有行承载——"类型/证据/授权分开"与六类对象划分→§A §02 前两行；
  "不是所有研究都先过 IC"的五类分流→§A §03 第一行；"归因并行、不做伪精确
  加法"→§B 6.3 行与三层归因相关行；"控制选择偏差/研究家族留痕"→§A §04
  尝试史行。属原则重申，无未映射的独立要求。
- **§2 当前状态表**：五行事实主张分别对应 §0 三行（v0 真实接入、数据基础、
  纯 50 日不再立项）、§A §07 第二行（混合池选强）与 §5/§B P4 行（验证目标、
  证据索引、外部模型无全仓接入证据）——即已按行核对其事实断言（见 §0 与 C5）。
- **§3 两条研究链路**：3.1 五类研究类型表与 §A §03 第一行同旨；3.2 三层
  分析对应本地三层归因（§A §05 组件行、§B 6.3 行）。
- **§7 方向指标（九项）、§7.1 P2 四件事、§7.2 长期复盘**：本地**无对应指标
  台账**（上游亦自述"不要求立即开发仪表盘"）；"结论可追溯、反例闭合、成本
  记录"等思想散见于本地 principles 验收条款与各 controller-review 实践，但
  未成体系，按四级口径属**仅有规划**——初版未单列是覆盖缺口，此处补记。
  §7.1 四件事属 P2 执行期验收口径：P2 未执行，工具侧部分对应（复算/样本
  去向有先例，成本记录缺失）。
- **§8 论文立项办法**：§8.1–8.3 由 §B P4 行与本地 `docs/literature-learning/
  README.md` v1.1.0、`ai-execution-contract.md` v1.0.1 部分承载（方法卡、
  只读接入、预算与停止条件）；**§8.4 有限稳健性补证协议（邻近规格/选择
  变化/尖峰归因/时期依赖/选择偏差五问）本地无对应物**，属仅有规划，补记。

---

## C. 合并点与冲突点

**C1 与 `docs/research/factor-research-roadmap-2026-09-10.md`（v0.2+v0.3）的关系。**
高度同构：两稿都坚持"问题被回答而非曲线好看"、五类方法分流、小池不硬切分组、
无通用 IC 阈值、尝试史防挑选。上游路线图稿的 P0–P5 与本地 §5 Phase 排期
（Phase 0 先做小验证）顺序兼容但粒度不同。**冲突点**：本地 v0.3 已把主线
纠正为"通用研究工具优先、固定 14 只 ETF 资料后置"，上游 P1 仍以"14 只池
月度无退出四格"为执行底座；若采纳上游 P1 需先裁决这一定向差异，本轮不裁决。
（"通用能力优先"的条款依据＝v0.3 导航原文：「用户明确主线是自有因子与信号
研究体系，不是补齐固定14只ETF的所有历史资料」「固定ETF资料采用计划后置，
未启动」；v0.2 旧正文的 Phase 排期不承载该决定。）

**C2 与 09-14 workbench 线（mandate + 首轮规格 + v1 报告）的关系。**
上游方向稿 §07 的"首个试点"与 workbench 线目标几乎相同（复用已有因子、
主交付证据链、辅助交付成本基线）。先后关系：workbench v1 已交付**工具层**
（合成验证收口于 `factor-lab-final-controller-decision-2026-09-15.md`），
上游试点的"真实输入排序因子证据链"是它的自然下一步；本次 G3 导航按
"上游仅方向参考、执行仍走本地 workbench 线"表述。

**C3 与 `factor-method-reuse-2026-09-17` 已收口提案（试点暂停）的衔接。**
该提案结论"本轮无立即执行建议、Alphalens 试点暂缓（触发条件保留）"与上游
§03/§6"暂不同时引入大型特征库、专业工具不替代资格体系"一致，无冲突。
上游统计规则（§6）若未来落地，Alphalens 接入仍受该提案触发条件约束，
不被上游文档自动激活。

**C4 与宽度线现状的衔接。**
宽度线现状：核验收口（`breadth-b200-first-description-controller-review-2026-09-17.md`、
`breadth-preflight-controller-review-2026-09-18.md`：28 项小例通过、
33 项 SHA 复算一致），但**"路径错误未修"**——prelight 复审明示"协议被删
字段能否拒绝、独立检查能否发现被改坏的结果，尚未按本轮任务实际验证"。
上游 P3"宽度按状态研究"与本地 `factor-evidence-reliability-usage.md`
（首版仅二元状态）方向一致；上游要求的"状态覆盖、条件收益/风险"交付
在 preflight 两项补齐前不应开跑。

**C5 上游断言与仓库证据的差异清单（不构成停止条件，但采纳前须知）。**
1. （2026-09-18 repair 1 修订）上游 P0 引用的
   `load_snapshot → check_snapshot → require_use` 调用链与本地实现**同名同链**
   且已由 `src/lei_signal/research/input_preflight.py` 编排（函数定义见
   `data_snapshot.py:831`、`data_quality.py:606`、`data_quality.py:381`）。
   本表初版误写为"本仓库未检索到同名函数"，经主控复核与本轮逐条重验纠正。
   与上游的真实差异不在实现，而在**验收范围**：09-13 复审仅在该轮范围内
   收口 R1/R2/R3，"可复用的离线输入验收入口"仍列为下一步建议，真实数据
   只解锁描述与诊断用途。
2. 上游多处把"已有定义登记、v0 计划、四格核验"表述为背景事实；本地核实：
   定义登记与四格确实存在（见 §02/§07 行），但 v0 的"独立验收"环节在
   本仓库未见对应收口报告，维持"未知"。
3. 上游 §0 称"宽度研究……纯50日对照、日期统计纠正、部分名单阻断范围和
   持仓差额核对已完成"；本地证据（`breadth-price50-decision-2026-09-09.md`
   判负、broad-breadth-cash-reconciliation-2026-09-08）与之一致，无矛盾。
4. 上游建议合并路径 `docs/research/factor-roadmap.md`（§9.3）本地不存在，
   实际权威路线图为 `docs/research/factor-research-roadmap-2026-09-10.md`，
   本次按本地路径处理。

**C6 采纳层级。**
本轮结论：两份上游文档定位为**方向参考，未授权执行**。任何条目进入执行
（尤其 P1 固定池四格、成本记账、评估器保护改造）须另立合同并获用户授权。

## 复现与核对

- 上游原件与 SHA256：`sources/`、`sources/manifest.json`（commit `2fddcdc`）。
- 本表引用的对象 id@version 均可由 `python3 -c "import json; ..."` 解析
  `docs/research/definitions.v1.json`（v1.2.0，81 张卡）复核。
- 本表引用的代码符号可在 `src/lei_signal/research/factor_lab/{contracts,diagnostics,validation,attribution}.py` 中 grep 复核。
- **repair 1（2026-09-18，execution 2）**：按主控返修单修正 §4 P0 行与 C5.1——
  `load_snapshot → check_snapshot → require_use` 调用链已实现且 `input_preflight.py`
  已编排（初版误判为"未检索到同名函数"）。同轮对本表全部否定性断言用
  `grep -rn` 在 `src/` 全目录重验：资格撤回/消费者关联、成本三层次、跨 Agent
  归并、自优化 replay、`docs/research/factor-roadmap.md` 五项均确认无对应物
  （replay 命中项为 `factor_account_adapter.py` 的冻结账户只读重放，与
  Dream-RSI 流程回放无关），已在对应行注明检索命令与范围。
- **GPT 终审修订（2026-09-19）**：按 GPT REVIEW_WITH_RESERVATIONS 意见逐条
  核实后修正四处——①状态比例改为精确计数（51 条：已实现 20／部分 25／仅
  规划 5／未知 1，初版"约半数/四分之一"量级说反）；②P2 行 rank_diagnostic
  先例改指 `momentum-research-prototype-2026-09-13.md` 并补真实输入历史复算
  先例（初版误指 factor-lab-extension-2026-09-05.md）；③补"§1–§3、§7–§8
  处理说明"（§7 方向指标与 §8.4 稳健性补证本地无对应物，属仅有规划）；
  ④状态图例补验证范围限定（合成例/文档核对≠真实数据验证或生产接入）。
  逐条核实结果与未采纳意见的理由见结案报告「GPT 终审」小节；往返全文见
  `records/2026-09-19-gpt-final-review-exchange.md`。
