# 统一因子查询与组合审查：已实现入口

2026-10-24。服务研究资料与策略审查层；原技术规则、交易和前向启动均保持原授权。使用者先沿 `lei-lowfreq-research` 和 `research-closure` 查既有成果，再调用本入口。工作台界面、指标和API继续由原负责人维护。

## 现在能做什么

`src/lei_signal/research/factor_combinations.py` 已提供精确身份查询、四种关系检查和组合资料审查。它直接读取现有 `current-standards.json` 所指登记表；外部目录调用已有 `osap_reference.load_reference`，不另建因子定义库。

- `object:ID@版本`：已登记的计算对象，包含指标、状态、风险、基准和策略，并非全是选股因子。
- `reference:ID@版本`：文献、方法或比较参照，与同名计算对象分别保存。
- `osap:缩写@目录指纹前12位`：某一公开发布版本的原始目录项。目录含对照或弃用项，不能把总数称为有效因子数。
- `factor-combination-profiles.v1.json`：只为精确对象补充经本轮检查的用途属性、来源和少量组合说明；不改公式或代替唯一登记。未知字段保持未知，外部原文描述不自动变成已核金融机制。

首次真实运行索引见 `docs/experiments/raw/factor-combination-workflow-2026-10-24/result-locator.json`。大结果在已核外盘；报告在实验库。完整目录覆盖这次登记范围，未声称已收全未登记历史脚本。

## 查询与审查

在项目根运行（输出到终端，不会回测、联网或交易）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lei_signal.research.factor_combinations catalog \
  --root . --profiles docs/research/factor-combination-profiles.v1.json \
  --osap-manifest docs/experiments/raw/osap-history-revisions-2026-10-20/osap-2025-manifest.json \
  --market US --family profitability --limit 10
```

外盘未连接时，可省略 `--osap-manifest` 查询本地已登记对象及参考；必须注明这次未载入外部目录。不会重新下载或用内盘替代外盘。

`review --root . --profiles <属性文件> --request <本轮组合请求JSON>` 返回规则缺项、元数据问题、证据检查和旧结果绑定。首轮实际请求文件在结果索引对应的 `*-request.json`，可以用它们检验CLI读回。查询、关系计算与候选审查均不自动执行收益实验。

### 新的相对超额研究：先审收益来源与基准（2026-10-31）

新问题沿原候选请求，增加一份 `strategy-mechanism/1` 附件，并显式要求审查：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lei_signal.research.factor_combinations review \
  --root . --profiles docs/research/factor-combination-profiles.v1.json \
  --request docs/experiments/raw/relative-excess-mechanism-implementation-2026-10-31/us_profitability_slow_growth-request.json \
  --mechanism docs/experiments/raw/relative-excess-mechanism-implementation-2026-10-31/us_profitability_slow_growth-mechanism.json \
  --require-mechanism
```

这是现有候选的真实缺件示例，预期返回未完成及非零退出，不是已获准交易的模板。A股示例在同目录 `cn_reversal_lowvol-request.json` / `cn_reversal_lowvol-mechanism.json`。未知保持 `null`，不为通过检查编造卖方、成本或可投资性；本次补写均标为已见历史，不能倒填旧实验事前假说。

只审附件、尚未进入组合目录时，使用同一个检查器：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m lei_signal.research.factor_combinations mechanism-review \
  --root . --request docs/experiments/raw/relative-excess-mechanism-implementation-2026-10-31/cn_reversal_lowvol-mechanism.json
```

独立命令不代表与外部候选已核同；它返回 `candidate_consistency=not_checked`。组合 `review` 才把附件的候选ID、组件版本和范围与本次请求核对。两个入口均不联网、回测或改变原资料资格。

| 附件部分 | 写清的内容 |
| --- | --- |
| `identity` | 准确候选与组件ID、市场、股票池、频率、币种和用途；不能只匹配“A股/美股” |
| `claim` / `benchmark` | 相对谁、主张和差额单位；基准角色、选择理由及选择时点、币种、分红与成本、可投资依据 |
| `mechanism` | 收益来源、参与者约束、承担风险或提供服务、持续原因、指标连接、竞争解释、不同预测与反驳条件 |
| `universe` / `timing` | 池的金融理由、历史成员身份与反例池，信息/行动时点、创建时间、旧尝试及已见历史 |
| `controls` | 最强简单对手、风险暴露对照、费用与容量、依赖和不确定性处理 |
| `sources` / `source_refs` | 仓内小材料、SHA、具体位置和实际阅读范围；引用ID必须已绑定，引用内容仍需主控核对 |
| `open_questions` | 尚不知道什么、缺什么证据；不能用解释流畅代替已解决 |

`relative_return`可描述策略与指数、同池对照或市场参照的收益差，必须保留各自口径；`net_relative_return`在本附件中专指相对事前可投资替代、双方按各自适用成本处理后的净回报差。后者缺费用/可投资依据、使用价格或报价代理时不能标附件完整。母指数的身份也不自动证明可投资；检查器不自动改基准或修改主张来凑通过。

这里的净回报需要在 `cost_basis` 说明双方费用处理；指数名称中的 NTR（股息税后口径）本身不证明已扣交易成本。`net_total_return` 只是附件的口径声明，仍须对照实际序列和成本证据。`same_universe_control` 还会核对基准与候选的股票池ID相同；其他角色允许不同池，但理由和可比性仍由人工审阅。

`mechanism_review.status`区分 `not_checked`、`incomplete`、`invalid`、`complete_for_manual_review`。完整仅表示字段及来源身份可供人工审阅，经济机制、alpha与独立验证始终未被该检查器证明。旧调用保留原 `state`，但不代表新机制审查已做；新问题必须看 `mechanism_review` 和 `new_research_status`，原资料缺件也不能被一份完整解释覆盖。`--require-mechanism`是显式检查入口，不是通用运行许可。

附件用于未来新问题时，将其及审查结果纳入已有draft的 `sources:[{path,sha256}]`，在 `controller_review` 的 `source_refs` 引用相应文件。复用原冻结绑定，不新增正式合同字段、不改旧快照。现有runner会核这些文件的指纹，但不会重新理解或认证机制内容；本检查器也不能阻止绕过显式入口的任意脚本。

实施、反例及实际缺件见[相对超额与机制审查落地](../experiments/relative-excess-mechanism-implementation-2026-10-31.md)。

既有严格式研究准备入口仍可用 `context --root . --definition-ref <准确ID@版本>` 调用。若旧登记源结构未通过原验证器，原错误会保留；普通目录可被读取不等于严格式定义检查通过。

## 供工作台或研究脚本调用的函数

| 函数 | 输入与输出 |
| --- | --- |
| `build_catalog(root, profiles_path, osap_manifest)` | 返回全部已声明范围的卡片、原始字段和来源指纹；不扫描其他项目 |
| `query_catalog(catalog, term, market, family, purpose, limit)` | 按属性过滤，返回命中总数及是否截断；未知属性不会自动匹配 |
| `return_relationship(left, right, left_scope, right_scope)` | 日期和值；返回共同期、收益相关、共同亏损与各自亏损、缺日期；无合成账户或权重优化 |
| `score_relationship(...)` | 日期、股票、分数；同日共同股票分别比较排名，正确处理相同分数；不跨日期拼接 |
| `holdings_relationship(...)` | 日期、股票、权重；每月相同股票较小权重之和，现金不重新分配；需自行声明真实/保存报价权重 |
| `assess_candidate(catalog, candidate, evidence)` | 精确对象、金融理由与竞争解释、完整规则、已核证据；返回设计资格与缺口，永不自动前向 |

关系输入的范围必须一致且非空：`market/universe_id/frequency/currency/return_basis/series_kind`。月度只能用 `YYYY-MM`，日度只能用 `YYYY-MM-DD`；月末实际快照日期可另存，调用者须明确形成月与持有月。`expected_dates` 是本轮预定完整日期列表，左右一致、月份连续。没有该列表只检查所见首尾内的缺月，不能声称目标时期完整。缺失不填0，常数序列不给虚假相关。

不同作者股票集合的收益比较只能在明确声明的资金配置问题下处理，需保留双方实际集合说明；不能给它们相同标签后称为逐股同池比较。跨市场配置需另设计币种、日历和交易约束，本入口拒绝未经设计的混合。

## 实际研究流程与边界

1. 从准确目录查来源、金融含义、适用股票范围和既有结果；每次选择一个具体用途。
2. 固定少量有理由的候选及简单对手，检查同类历史是否已回答。已有负结果没有新证据时直接复用。
3. 各关系按真实资料分别计算或明确未评价；公开收益不能代替逐股评分，报价持仓不能证明可成交。
4. 完整规则逐项写出股票范围、信号、判断和成交时间、资金比例、调仓、退出、缺价、费用、基准。未明确的项填null。
5. 历史成员、当时可得资料、价格及退出、持仓、费用、母指数和后续未见资料分别核。声明为true须附实际path+sha核验凭据；文件指纹相同仍只证明来源版本，不能替主控证明科学资格。
6. 能做的新效果检验继续走本项目原研究合同、预算和输出存储。当前辅助工具不执行新收益回测，不宣称适配所有旧入口。结果含单项、组合、强对手、费用、风险与机会代价；新增帮助不足可暂停。
7. 将结论、全部尝试和唯一能改变判断的下一项证据写回原案例。冻结后新观察仍须完整策略资格和原前向模块的明确启动，不由低相关或此工具状态自动触发。

`qualified_for_research_design`仅代表本工具检查的设计字段与声明凭据齐全，仍需主控审阅；`blocked_inputs`列出缺口。两者都返回 `forward_eligible=false`。目前没有通用的语义自动认证、全库两两寻优或生产交易连接。

首次案例、性能与增量表：[统一因子组合流程实测](/library?report=docs%2Fexperiments%2Ffactor-combination-workflow-2026-10-24.md)。

## 保存组合的费用后增量（2026-11-05）

来源先查[买方方法参考卡](buy-side-method-reference.v1.json)及[学习来源集合](../literature-learning/buy-side-learning-sources-2026-11-05.md)。JKP年度/季度口径和Tidy组合统计阶段不能互换；本地采用规则仍有自己的版本，不称上游完整复现。

```sh
PYTHONPATH=src python3 -m lei_signal.research.factor_combinations portfolio-review \
  --request /已核外盘/本轮/request.json
```

这是现有组合审查入口的新子命令，内部调用`incremental_portfolio_review.review(payload)`。请求`schema=incremental-portfolio-review/1`；`scope`须有universe_id、benchmark_id、currency、return_basis、cost_model、source_artifact_sha256，以及frequency=monthly、unit=decimal_return、history_status=previously_seen/unseen_holdout/forward。这些范围和指纹是声明，调用者须核原件；工具不读取它们指向的外部资料。

`rows`按连续YYYY-MM列出全月历，每行的candidate/baseline/benchmark均有gross/net（小数收益，未知null）；可选traded_fraction为本月买入加卖出金额／期初资产，不是单边换手。费用须非负且已经包含在net中；不替调用者模拟成交。返回毛收益可用月、三方毛净共同月、共同片段、月均主动收益、TE/IR、毛/净增量、费用差及总/主动收益相关。成本影响=同月净差−毛差；它是保存结果的算术拆分，不证明因果。

默认不拼缺月CAGR/全期回撤，不计算置信区间，不认证来源、PIT、历史未见性或策略有效性。既有`research_account_evidence_review`负责其独立声明型账户证据结构；本入口只增加保存收益比较。因子分数重复关系仍用`score_relationship`，持仓交集用`holdings_relationship`；主动收益相关不能替代这两者或暴露回归。具体样例与9个真实保存结果对照见[接入报告](../experiments/buy-side-method-increment-2026-11-05.md)。
