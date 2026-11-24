# 提交交易想法后，系统怎样完成一轮研究

## 可复用的任务交接与恢复（2026-11-02）

多阶段委派、冷上下文执行者或中断恢复使用用户级 `codex-delegate` 的 `references/handoff-workflow.md`；简单单步工作继续用原合同预检。本项目只提供研究上下文适配，不另建预算账本、派发平台或后台服务。

```bash
PYTHONPATH=src python3 -m lei_signal.research.preparation --root . --practice-only \
  --study <原研究目录> --family <原家族> \
  --handoff-contract <本阶段合同.json>
```

将输出保存到本任务新的准备文件。`delegation_context`完整保留原`practice_context`、其他准备字段和合同；通用packet的context可用该文件SHA及pointer `/delegation_context`。合同可声明 `research_controls.required_source_pointers`，每项为指向**原preparation对象中来源绑定对象**的RFC 6901指针，例如 `/source_bindings/0`；必需来源缺失、无指纹、截断或无法核验则阻塞。`required_context`则指向**选中的交接上下文内部**，仅检查字段存在，未知值仍未知。

未知预算、已看历史、未命中、负结论、错误及截断标记均不改写。完整review/关键绑定被截断导致来源身份不可恢复时保守阻塞；其他原始截断信息保留。适配器最多100条来源绑定、单文件1 MiB；通用packet另有限制（每JSON列表256项、嵌套64层），不为通过限制静默删历史。原准备入口退出0仅说明输出成功，必须检查 `delegation_context.status`；独立适配器CLI `python3 -m lei_signal.research.delegation_context --root . --preparation <已存准备.json> --contract <合同.json>` 对blocked退出2。

主控将目标、packet路径和允许产物交给执行者；执行者实际receive并读取后返回回执。主控沿packet绑定的唯一state路径保存实际派发、回调材料及独立复核。中断先核原附件和真实执行者，重复回调不增加观察数；没有派发回执时也不能认定没执行。验收后在既有授权内决定关闭或进入新阶段，累计预算和旧记录不重置。

`ready_with_declared_limits`只表示交接结构可用；`execution_authorized=false`始终保留。源码身份、数值正确、研究有效和生产采用仍分别判断。此流程不保证全局只执行一次，不提供进程退出后的自动接续。可复用范围及实测见[本轮报告](../experiments/reusable-agent-handoff-2026-11-02.md)。

## AI输出的限定诊断（2026-11-02）

只有研究确实使用LLM生成的分数、标签或历史事实，且这些输出会影响研究判断时，才选用本节检查。已有确定性因子、普通资料摘要或纯人工记录不例行加测。

```bash
PYTHONPATH=src python3 -m lei_signal.research.preparation --root . --practice-only \
  --llm-review-file docs/experiments/raw/llm-output-diagnostics-2026-11-02/synthetic-request.json
```

上面是明确标为 `synthetic` 的工程演练，不含真实模型调用。真实使用时在原研究raw中保存原始回答、输入与来源，并建立自己的请求；不要把示例改标为真实。结果位于 `practice_context.llm_output_review`。只检查该附件可使用 `python3 -m lei_signal.research.llm_output_review --root . --request <仓内相对JSON>`；缺件退出2，已完成带限制审查退出0。父准备入口的退出码只说明准备成功，仍须查看每项诊断状态。

请求格式为 `llm-output-review/1`，包含 `perturbation`、`timing` 中至少一项。可复制的完整字段见[合成请求](../experiments/raw/llm-output-diagnostics-2026-11-02/synthetic-request.json)及其指纹绑定的输入；每个引用都需要仓内相对路径、SHA-256、JSON pointer，每份文件不超过1 MiB。

| 场景 | 必须保存的材料 | 怎样解释 |
|---|---|---|
| 输入微调后评分或标签大变 | 原输入、微调输入、原输入重复调用的三个独立回答记录；相同模型版本、模板/设置指纹、时点、对象、期间和输出单位；指定可改字段、数值变化界限和语义审查依据 | 同时展示扰动差与重复差。输入完全不变不算扰动；数值等价的表示变化可以单列。不能由敏感性直接证明记忆、泄漏、预测优劣或收益 |
| 历史事实被提前引用或没有更新 | 模型原答和事实声明；带时区判断时点；精确期间或最新期间的提问模式；复用 `financial-source-versions/1` 的公开/到达时间、版本、原件指纹与覆盖声明 | 区分提前引用、旧期间、同期间旧版本、匹配和未知。目录不完整、同日只有日期或到达时点缺失时保留未知；值/单位不符另列 |

真实与合成材料分开计数，重复片段排除分母。回答片段数、日期分组数均不等于独立样本数；不据此自动计算真实模型错误率。`reviewed`只说明检查已执行，未知项要看 `assessment_complete` 和逐条结果；`matched`仅指时间/版本关系，不保证数值正确。两个检查均不验证结构化声明确实从原答抽取，也不认证独立调用、语义等价或覆盖完整性。模板降级答复、模型身份未知或缺原答不能补作模型证据。实际接入及旧材料拒绝结果见[报告](../experiments/llm-output-diagnostics-2026-11-02.md)。

## 旧结论与单组件诊断进入研究准备（2026-11-01）

新假设先读取同类旧结论、具体用途、已看历史与重开条件。原 `preparation` 成功解析定义后也返回 `practice_context`；只查旧研究时使用以下入口，独立于定义登记解析：

```bash
PYTHONPATH=src python3 -m lei_signal.research.preparation --root . --practice-only \
  --term 动量 --study docs/experiments/raw/existing-factor-strategy-expansion-2026-10-24
```

准确家族可补 `--family <原家族名>`，显示条数用 `--limit`（默认6）。输出复用 `attempt_review` 的账本和白名单研究文件，以及原报告登记的文字线索；不新建历史库，不追读外盘输出。缺结论或重开条件保持未知，执行完成不等于因子成立；来源指纹相同也不代表结论科学有效。读原报告与后续纠正后，将用途、旧结论和重开依据写回当前开题的既有附件。关键词命中仅是相关线索。

只有信号与完整策略/账户评价冲突才使用 `--diagnosis-file <仓库相对JSON路径>`。该附件放在当前研究的既有raw目录，字段见 [`component_diagnosis.py`](../../src/lei_signal/research/component_diagnosis.py) 模块说明；不得为通过检查补造金融结果。诊断引用两层已保存JSON结果的路径、SHA和字段位置，并绑定原评价标准及对象/时期/原机会/信号/基准等身份。已有单组件对照须与原账户基线一致，优先复用；没有则最多提出一个退出或资金/执行对照，费用和其余规则保持相同。缺结果、身份不一致、来源漂移或同时改变多个组件时保留阻塞原因。

返回 `planned_for_manual_review` 只是有界比较建议，尚未运行也未获得新授权；`reused_for_manual_review` 只表示已有比较附件可复核，不认证因果。诊断不是另一个账户引擎。测试示例全部合成，真实历史缺新附件时保持未知。实现与实际检查见[本次报告](../experiments/ai-quant-practice-integration-2026-11-01.md)。

## 新相对超额题的机制附件（2026-10-31）

新题在既有开题中回答“相对谁、优势为什么可能存在、适合哪些对象、什么证据会推翻”，按[组合入口的收益来源审查](factor-combination-workflow.md#新的相对超额研究先审收益来源与基准2026-10-31)准备并执行显式检查。可先用独立 `mechanism-review` 检查附件，进入组合候选时用 `review --mechanism <附件> --require-mechanism` 核对象一致性。未知和已见历史保留，不为通过填造经济解释。

本轮复用现有draft的 `sources` 绑定附件与审查结果SHA，`controller_review.*.source_refs`引用对应文件；冻结、执行和报告注册流程保持原样。严格式合同没有新增机制字段，原runner仅核附件字节，不能把sources绑定或检查器的完整状态当因果、alpha、独立验证或交易授权。旧冻结实验不追认新规则；账户、风险和其他用途仍沿自身评价方法，不强迫先证明完整因果。

## 研究前先查已有尝试与账户输入（2026-10-31）

研究对象按问题选择，可以是股票横截面、行业、母指数、市场状态、ETF或完整策略；
不把ETF数量当成独立验证数量。下面两个入口只检查已有记录，不启动回测、取数或交易。

```bash
PYTHONPATH=src python3 -m lei_signal.research.attempt_review --root . \
  --family price-volume-path-eight-etf-2026-10-04
PYTHONPATH=src python3 -m lei_signal.research.attempt_review --root . \
  --study docs/experiments/raw/existing-factor-strategy-expansion-2026-10-24
PYTHONPATH=src python3 -m lei_signal.research.account_input_review confirmed-account.json
```

尝试查询复用原workflow的JSONL账本，或显式指定独立研究目录；不另建登记簿。
精确家族查询保留原预算、计算和机械重试，关键词查询有扫描上限。独立研究只读已支持的
合同、尝试、设计、冻结和完成记录；不会沿外盘结果链接扫描大文件。输出文件SHA、
缺项、坏行、未结束运行与来源漂移；`complete`只涉及本次索引的材料身份，
不能保证所有未登记尝试已被发现，更不代表策略有效。方法字段是声明或证据引用，不是评分。
例如新写的`forward`字段不能把已见历史升级为独立前向结果。

账户检查接受规范化、带确认依据的账户声明，完整字段见
[`account_input_review.py`](../../src/lei_signal/research/account_input_review.py)的模块说明。
也能识别现有持仓估值快照并列出缺口：市值、净值反推份额不等于确认的总份额、
可卖份额与现金。`ready`仅代表字段和声明约束通过，来源真实性仍为`declared_unverified`；
缺`decision_at`时，当时可用性保持`unknown`。同币种资金请求合计审查，卖出回执不重复增加现金。
返回`incomplete/invalid`时CLI退出码为1，仍给出JSON原因；不会生成订单。

价格与估值观察复用已有入口：
[沪深300价格与PE](/fundamentals?observation=hs300-pe#fund-sec-market)、
[标普500价格与CAPE](/fundamentals?observation=sp500-cape#fund-sec-market)。
价格加经营信息的已有比较位于因子工作台“比较与组合增量”，原文指纹不匹配时隐藏摘录数字。
实现、实际记录审查、反例与尚缺部分见
[本轮报告](../experiments/research-method-practice-2026-10-31.md)。

## 因子有效性方法与留痕入口

按本轮问题选择方法、综合判断增量及保存失败记录，见[因子验证操作指引](methods/factor-validation-guide.md)。它整理已有能力和三个价格风险因子的实际例子，不改变本入口、权威规范或旧冻结合同；不是每题都必须做全套检查。具体方法案例继续存入[现有案例库](methods/research-method-cases/README.md)，因子结论和正式报告仍由原定义与实验登记表管理。

## 按本轮问题选择已有工具

宽基与ETF研究仍从“想判断什么、已有信息是什么、能否在当时知道”开始。
主控按下表选择需要的技能，把检查结果放进本轮已有合同或报告；已有记录足够
且未变化时直接引用。不要求每轮加载全部技能或重复运行已完成检查。

| 遇到的问题 | 使用位置和工具 | 交回现有流程的内容 | 适用条件 |
|---|---|---|---|
| 新资料有没有把后来修订的值当成过去已知 | 冻结输入前用 [lei-data-availability](../../.agents/skills/lei-data-availability/SKILL.md)；复用 `input_preflight` 和 `workflow_inputs` | 本轮所用字段的公开/可得时间、版本及未知项，写入已有来源说明 | 来源资格需要补查时使用；仅有当前版本不能推出历史预测可用 |
| 对未来的判断有没有使用后来才知道的资料 | 声称用过去预测后来时用 [lei-causal-validation](../../.agents/skills/lei-causal-validation/SKILL.md)，包括固定规则预测；复用适用的 `workflow.py::preflight` | 预测时点和结果成熟边界；有训练过程再记训练时点、预处理范围及剔除原因，写入已有研究设计 | 核验定义、解释历史或描述状态时不强行建预测模型 |
| 已有预测差额是否适合检查相邻日期的影响 | 原结果验收后，确有额外诊断问题时用 [lei-quant-tools](../../.agents/skills/lei-quant-tools/SKILL.md) 的 `workflow-check` / `workflow-hac` | 是否适用、完整覆盖、差额方向、单位和辅助误差，写入原任务的新附件 | 原评价器已有同用途答案时直接采用；缺日期或权重不一致则保留原因，不强求数字 |
| 想看FactorHub目录或供应商的结果作参考 | 已授权本轮来源、凭据和查询范围时用 [factorhub-readonly](../../.agents/skills/factorhub-readonly/SKILL.md) | 标明来源的目录、净值或摘要，作为候选资料/外部对照 | 安装或主控选源不扩大查询授权；供应商摘要不当逐ETF每日因子值，指数不当可交易ETF；其他来源沿用各自资格 |
| 需要核对上交所2026年度安排 | 日期问题确实涉及该市场与年份时用 `lei-quant-tools` 的 `xshg-date` | 与本轮合格日历的辅助核对记录 | 只覆盖该年度安排，不判海外市场、临时调整或产品能否成交 |
| 核算外部时序候选是否表达不同的价格变化 | 定义前的数学预览用 `lei-quant-tools` 的 `candidate-preview` | 固定20日平均绝对对数变化、相邻变化联系及已有涨跌/波动比较列 | 只用明确日历及已有经济价格，不补报价、不默认筛全库；未登记为正式因子或证明预测增量 |

例如研究“均线斜率能否补充已有价格信息”：先复用本项目精确定义和已合格
行情；来源有新增或未知项才补时间核查，再按未来结果成熟时间划分资料，
交原研究入口完成基准和新增信息比较。原评价器已经回答结果是否稳定时，
不再为使用工具多算一套。若出现具体的平均差额诊断问题，先检查适用性，
再决定是否使用辅助计算。

研究“同一天如何给ETF排序”时则先核对象数量、当日资产集合和本轮定义。
Alphalens、Qlib等既有候选须依相应用途的原评估选择；当前已验证的时间序列
小组件不能自动授予排序、完整回测或账户配置能力。大项目取舍沿用
[资源评估](../experiments/quant-resources-adoption-2026-10-02.md)，本轮没有新增整库验收。

以上是主控的使用指引，只有原程序已实现的检查会实际执行。登记
`ready` 或新增一段技能说明，都不等于新数据、因子或生产交易已获准。
技能不另设研究登记表、完成标准或后台任务；现有合同、预算与发布入口继续负责执行。

### 开发时补充自动生成的边界例子

修改输入处理或百分比计算后，可使用项目的 `property-tests` 可选开发依赖。
新增 `tests/unit/test_research_property_checks.py` 使用 Hypothesis 6.147.0，
限定检查演示适配器：未来报价不能改写过去特征；统一缩放价格不能改变百分比结果。
每条性质最多生成64个通过例，故意偷看未来的隔离错误函数另作工具灵敏度核对。
具体范围和本次证据见[外部增量评估](../experiments/external-increment-2026-10-02.md)。

```bash
HYPOTHESIS_STORAGE_DIRECTORY=logs/research-properties PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/unit/test_research_property_checks.py -p no:cacheprovider
```

没有该可选依赖时会跳过，跳过不能算通过。现有手写反例继续保留；这项开发检查
不代替实际资料资格，也不证明其他已登记因子、真实市场表现或整个系统都正确。
只在相关代码改动或明确需要反例检查时用，不给每轮金融研究附加无关计算。

## 已有归档结果的辅助工具（2026-10-02）

项目技能 `$lei-quant-tools` 可直接读取本入口保存的合同、检查产物和预测结果，
先核文件与原执行日志，再判断能否计算考虑相邻日期联系的平均差额误差。
具体命令与适用范围见
[技能入口](../../.agents/skills/lei-quant-tools/SKILL.md)；
[整合验收](../experiments/quant-resources-integration-2026-10-02.md)记录真实调用与拒绝例。

它只作已有结果的辅助分析；原主指标、全部评价日期、资金口径和结论继续
以原合同及报告为准。缺少计划日期或每日资产集合变化时会拒绝计算，
不能将裁切后的辅助时期冒充原全期结果。该入口不重新拟合或重新发布报告。

## 原研究流程

### 只审查合同声明，不执行研究

需要先核对合同字段时，可使用现有入口：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_factor_lab.py --review-workflow-contract /path/to/contract.json
```

它只读取指定合同，原样交给现有 `validate_workflow_contract`，把 JSON 结果写到
stdout；不导入 `workflow` 或合成协议执行器，不读取合同引用的数据、资格产物、
模型或历史账本，不计算特征和未来结果，不取得锁，不创建输出目录或登记报告。
现有校验器按因子类型可能导入常量或声明检查函数及其 numpy/pandas 依赖；这不
代表执行了研究。审查分支会关闭模块导入的字节码缓存写入；示例中的
`PYTHONDONTWRITEBYTECODE=1` 也从 Python 启动时避免缓存写入。

审查成功退出 0，合同读取/格式/字段失败退出 3，命令参数冲突退出 2。
此模式与其他入口互斥，禁止 `--out`、`--register-report`、`--reuse-predictions`。
正常执行模式仍要求 `--out`。`declaration_valid=true` 只说明声明满足现有机械
规则；实际来源、资格数量、预算和权限尚未核验，`execution_authorized` 始终为
false。额外的 `mode=plan_only` 或预算字段不改变模式；未知目标、已有信息、
时间划分和资格数量保持原样并由原校验器判断，不填默认值，也不把
`qualification_only` 改成预测计算许可。

新研究已经接在现有 `scripts/run_factor_lab.py` 的两个新分支。先检查、演练和冻结，
再计算，最后核对生成的表并登记；旧实验继续按自己的冻结版本运行。
当前规范路径和版本只有一个导航来源：[current-standards.json](current-standards.json)。

你只需要提出交易判断，比如“回调时保持均线上行，是否少一些未来下跌”。主控把它
变成可以计算的定义，确定对象、期限、已有信息、反例、允许的尝试和资料范围。
对象是否对应用途、这个代理是否忠实、方法是否合适、最后结论能说多大，由主控
留下理由；程序不把理由当作“已验证”。技术体系的新增、删除和含义调整仍需你确认。

程序先查看实际文件，保留每个缺口的原因。正常停牌、漏报、尚未上市、行动尺度不明
和未来结果未成熟分别处理；不拿假报价补洞。固定期限的首尾变化、途中最低收盘或
最低价、峰谷回撤、可操作开盘需要不同证据。相邻日期及同日资产一起处理，不能把
重复观察当作很多互相独立的验证。检查前的资料只用于资格，导出的冻结检查不显示
未来结果数字；看过的结果不会因为更换AI、文件名或家族名成为新验证。

接着用人工生成的小样例演练完整流程，冻结本轮数据、相关定义、代码、目标、
频率、权重和有限方法。正式计算前会再次检查。错误的时点、未披露的缩池、没有
反例、旧凭据、超预算或越界用途会停在相应位置。合理的部分覆盖可以完成，但
报告会明确实际比较对象，不能说成全范围已经验证。

结果表由程序生成：简单历史参照、已有信息、加入候选后的误差并列；展示差值、
单位、允许的改善与恶化范围、机会数量及未覆盖部分。预测更准不直接等于投资
收益，途中最有利价格也不等于已经兑现。方法较差、没有新增帮助或证据不足都可以
正常结案；不会自动换参数直到找到正结果。结论的科学解释由主控看完表后确认。

以后换一个技术想法，作者只补特征/事件适配器和研究卡；时点、标签、配对、基准、
统计范围、报告与验收复用。尚未支持的适配器会直接拒绝，不把名称写上就算实现。
目前内置的是演示用SMA相对距离、前一真实报价下跌事件，以及连续预测/二元风险
频率评价器；它们不等价于A01双均线带的完整注册定义。真实A01等作者须先接准确
特征适配器，不能拿这里的演示代理替换原定义。
当前特征用日线真实报价计算，`bar_frequency=daily_quote`与每周/每月取一次观察分开；
按周取观察不等于用周线计算均线。真实资料中的周期完成标记还须符合来源日历。

## 执行者最短调用路径

合同样例和实际两次演示在
`docs/experiments/raw/research-workflow-engineering-2026-09-29/demos-final/`。
最初版本的`demos/`原样保留；最终版本补齐了计算前拒绝尝试的耗时入账，沿用原家族预算。
实验库的报告是生成稿的副本；复现合同、数字和回执保存在实际运行目录，最终演示为
`demos-final/<案例>/run/`。生成稿中的“同目录”指这个运行目录；登记表的
`workflow_receipt`也记录真实回执位置。

```bash
PYTHONPATH=src python3 scripts/run_factor_lab.py --workflow-draft DRAFT.json --out NEW_FREEZE_DIR
PYTHONPATH=src python3 scripts/run_factor_lab.py --workflow-contract NEW_FREEZE_DIR/contract.json --out NEW_RUN_DIR
```

主控核对最终结论后，将相同定义/方法的新合同指向新报告路径，重新冻结；再执行：

```bash
PYTHONPATH=src python3 scripts/run_factor_lab.py --workflow-contract NEW_FREEZE_DIR/contract.json --out NEW_ACCEPTED_DIR --reuse-predictions PREVIOUS_RUN_DIR --register-report
```

只改说明文字不重新拟合；只改汇总比重可重用预测，重算汇总和验收。改特征、标签、
数据、抽样频率、期限切分或评价器会使对应预测缓存失效。改后看过结果须记探索。
家族日志在 `docs/experiments/raw/research-workflow-ledgers-2026-09-29/<family-hash>/`，
它是Experiment Ledger的运行记录，不是第二份因子登记表。同一家族只允许一个
活动运行；改任务名不重置次数、预算或已见资料。日志记录演练、失败、重试及耗时。
计算前拒绝的尝试也消耗同一家族时间预算，但不计为新的科学假设。

## 覆盖边界（不要把入口接入说成全系统已接入）

| 入口/用途 | 当前能力 |
|---|---|
| 新 `--workflow-draft` / `--workflow-contract` | 已接实际计算前检查、合成演练、冻结、两种评价器与覆盖链 |
| 新分支 `--register-report` | 已接实际发布验收；缺凭据、漏基准、改数字/单位、少交预测均不能完整登记 |
| 旧 `--protocol` | 保留自身原有合成协议检查，未迁移到六阶段新合同 |
| 旧 `--benchmark-protocol` | 保留自身原有基准研究检查和登记，未声称受新发布验收约束 |
| 历史 raw脚本、其他独立研究脚本 | 未统一接入；旧快照不改，不由本入口追溯认证 |
| 真实报价 | 先调用原input_preflight，再绑定实际日历、价格、缺价与经济变换；原始名义价加手填action_known不能过关 |
| 经济价格 | 只接受从指纹绑定的名义OHLC及行动清单用现有economic_index函数逐值重算；没有行动记录不证明行动历史完整，完整性未证实只作有限结果 |
| 可操作真实开盘、完整账户政策 | 当前明确不支持；不能用open_actionable=true替代证据，不计算或登记投资收益 |
| 未见资料 | 可检测本入口日志中的同内容/重叠已评价标签；历史未接入脚本的接触史还需主控读取真实交接，不能自动保证所有过去资料未见 |
| 任意程序/操作系统 | 没有禁止任意脚本的权限沙箱；本入口不承担恶意重写代码、凭据和日志的安全认证 |

技术分支拒绝情绪、宽度、宏观和生产用途；公共数学工具的存在不授权本负责人运行这些研究。


## 2026-09-30：先有可核查的研究设计再运行

新建合同使用 `research-workflow/1.1`，旧冻结1.0保持原状。`research_design.claim_mapping` 写原文语句/章节、代理、保留/省略条件、决策用途、观察/行动时点及适用范围；`sample_fit` 写资格产物、其SHA、未用未来结果数值的声明、数量、共同支持、相关性、模型字段数、选择理由与决定。完整字段示例见 `tests/unit/test_workflow_design_review.py`（结构演示，非市场设计）。

资格文件含 `data_sha256`、`outcome_values_used_for_design:false`、`counts`（assets/observations/dates/episodes）及人工审阅的 `scientific_support`。基础计数对应问题期间所有安排观察，包含不合格和反例；它们绝不是独立样本数。有效机会、成熟标签、每期训练/评价、目标组支持另放 `scientific_support` 并在首页披露。无趋势/事件ID支持时episodes为null，不能手填独立事件数。

程序核文件内容与SHA、输入绑定和基本数量，不审判方法科学性。四栏主控理由不得重复。只够资格或描述时保留报告，当前连续预测/二元风险入口不会强跑模型；也不要求为了进入模型而扩大参数/标的。当前真实适配器还包括 A01 N60带距离和A03首次触碰；其实现能力与用途以精确登记版本及实际输入为准。

## 2026-10-02：两个技术语义的限定入口

`slope_change_information` 绑定 `research.trend.slope_change60_20@1.0.0`：当前SMA60年化对数斜率减20日前同斜率。`simple_top_invalidation_information` 绑定 `research.structure.simple_top3_invalidation@1.0.0`：前收盘最新简单三根顶部仍有效的日期，区分首次突破原高和未突破。后者不采用全段复杂包含构造回填。

两者保留全部安排行、252连续真实经济OHLC、无标签资格默认及真实效果许可检查，复用来源核查和两个固定后期20日结果比较。各入口检查精确卡、背景字段、训练成熟和同期开完整结果。数据及模型支持只覆盖合同中四ETF的已见历史，不支持自动改阈值、资金账户、退出或真实交易。代码／规则／标签路径进入缓存指纹，旧冻结合同及快照不迁移。

原文定位、已测用途与仍未回答的语义见 [技术语义证据导航](technical-semantic-evidence-map-2026-10-02.md)。已经接入入口不等于因子有效。

## 2026-10-02：相邻回调均线层级变化

新增 `pullback_layer_change_information`，绑定唯一登记对象 `research.pullback.ma_layer_change@1.0.0`。它比较同一研究上涨段内、左右各3根确认的相邻回调，最深到达20／60／120双均线组的变化，保留未接触、持平、变深及跌破全部档位。走势段起止、配对和零容差接触是已公开的研究选择，不等同完整模块A。

已通过原入口完成资格、合成演练、冻结、真实效果和发布核数；[完整结果](../experiments/pullback-layer-change-information-2026-10-02.md)结论为证据不足。第一评价段训练不足不估计，实际后期只有4条预测；预检查的31条候选不可当成31条预测。主指标为未来20日从次日收盘到途中最低收盘的下探，收益等五期限另作描述。新对象数量、方法和权限必须重新绑定，不能以本次接入代替新研究设计。
