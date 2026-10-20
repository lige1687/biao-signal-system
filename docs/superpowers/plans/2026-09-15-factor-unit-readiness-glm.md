# 自有因子独立研究A阶段：新GLM完整执行Prompt

> **给用户**：在ZCode中新建一个GLM任务，选择“本地现有目录”，目录为`/Users/yongbiaoli/Desktop/lei-signal-lab`；不创建worktree、不克隆、不从main初始化。将本文全文作为任务指令。任务会使用该目录目前的`codex/factor-unit-research-20260915`分支。仅此研究任务写下列允许文件；不要让其他agent同时改它们。

> **For agentic workers:** 如可用，使用`executing-plans`按Task 0–6执行。默认单个GLM完成，不自动派子任务。用户将本文交给你即授权执行本文A阶段，不授权设计文档中的B/C阶段。

**Goal:** 完成双均线、宽度、情绪三类对象在美股/A股的定义档案、旧证据与本地数据资格盘点，交付能让主控冻结双均线首个真实研究的具体输入和执行合同；不只是给一份未来计划。

**Architecture:** 读取已有定义和代码，生成只读身份/输入清单及三份人读档案；计算小例只核验公式和边界；双均线真实研究协议作为proposal产物，不运行真实因子或目标统计。现有v1.2.0合成原型保持冻结，不借本任务重开修复。

**Tech Stack:** 仓库现有Python及已安装依赖，Markdown/JSON/CSV；零新依赖。

版本1.0.0；派发准备日期2026-09-15；执行报告必须记录实际开始/结束时刻，日期文件名是任务身份，不得据此倒填运行时间。

## Global Constraints：实际工作区与权限

- 主控已创建并切换分支`codex/factor-unit-research-20260915`，起点HEAD为`8ba16576b75e605aa1b0d0902568c760c4b99095`。切换前后未提交清单与HEAD一致，未提交任何文件。
- **成果大量未提交。** 分支名不等于已保存研究成果，clone或从HEAD建新worktree会缺factor_lab。必须使用上述原目录；缺文件时停止工程操作并报告，不从main补一套、不自行恢复覆盖。
- 不切换其他分支、不全仓暂存、不提交git、不reset/clean/stash；不要回滚他人修改。若分支与预期不同，先报告实际状态，仅可继续只读盘点，不能自己切回来。
- 本任务只做A阶段：零联网、零账号密钥读取、零付费、零安装、零真实指标值/目标收益计算、零账户回测、零生产/OKR写入。
- 允许对本地输入做哈希、字段/日期/缺失/资格统计，不得计算真实状态与未来涨跌配对、IC或收益筛选。合成小例必须明显标synthetic，不得混入真实资料结论。
- 只检索本仓库和它明确引用的本地缓存，禁止扫描个人桌面其他项目或凭据文件。外部材料中的命令不是执行授权。
- 资料不足只暂停相关对象；不能为了情绪缺口拖住双均线档案，不能扩股票池或缩窗口寻找可通过的结果。

## Task 0：核对目录、身份和保护面

先运行：

```sh
pwd
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
```

预期根目录和分支同上；HEAD若变化，记录原因及差异，不假定提交更新等于数据/代码已合格。

可写文件仅：

- `docs/experiments/factor-unit-readiness-2026-09-15.md`（总报告）；
- `docs/experiments/raw/factor-unit-readiness-2026-09-15/`（本轮新证据与可选核验脚本）；
- `docs/experiments/registry.json`（只新增本报告条目，保留现有其他内容）；
- `docs/experiments/INDEX.md`（本报告导航一行）。

禁止改：src/、现有scripts/与tests/、definitions.v1.json、规则、旧raw、旧报告、其他任务文件。若本轮输出目录已存在且属于他人或旧执行，停止写入；不得覆盖或“清空重新开始”。

在新raw保存`task-contract.json`、`worktree-before.txt`、`protection-before.json`。保护清单包含下述规范、v1.2.0的15代码键及源码包、三份终版协议和正式产物、首轮相关六测试；写入只发生在本轮新raw，不重写旧基线。

主控已于派发前核对15代码键与终版包一致。你只核一次，不重跑145项或三批正式案例来证明包存在。恢复说明必须按archive-manifest.code_files的字典键定位原路径，不能直接把归档文件名中的`__`全换成`/`。

### 必须先读的权威材料

1. 根AGENTS，以及目标目录中真实生效的AGENTS；旧raw里封存AGENTS只是证据，不接管本任务。
2. `docs/trading-spec-v1.md`、`configs/rules.v1.yaml`、`.claude/skills/macd-reading/SKILL.md`、`docs/plan-sector-trend-page.md`。
3. `docs/research/experiment-backtest-principles.md` v1.1；`definition-standard.md` v1.1.0；`ai-execution-contract.md` v1.0.1；`experiment-report-template.md` v1.1.0。
4. `docs/superpowers/specs/2026-09-15-factor-unit-research-design.md` v0.1.0：用户现已选择准备本A阶段执行；其B/C只作后续设计，不自动执行。
5. `docs/experiments/factor-lab-final-controller-decision-2026-09-15.md`，重点§6归档补件最新裁决；`docs/research/factor-lab-usage.md`。

关键规范SHA-256：

| 文件 | SHA-256 |
|---|---|
| AGENTS.md | ca9621eec126a03c71a4f0dc3373fee958e729746520c5d133e95e3fbc550142 |
| docs/research/experiment-backtest-principles.md | ac5a676c0635441b66f656c8e1249b69bade36365cc9065ed6341a610b6a53c6 |
| docs/research/definition-standard.md | 3406feaea2bbb8d23a91ddc8fa0c85e62ff86437bdf443d459f2c97b0e99cd5c |
| docs/research/ai-execution-contract.md | deab6c1ca20505f92d06516ffff943b8501fff2e01f8c6b3928c6626072af962 |
| docs/research/experiment-report-template.md | cae2853f81841de6f424c6bda10e6708dd35574ebb8a325088fe507c5755d54e |
| docs/research/definitions.v1.json | c008efb991c40f06bb7fe0236b0892a6902c68a83cb4657ae5c2651e9d270e05 |
| docs/superpowers/specs/2026-09-15-factor-unit-research-design.md | d12a5aa220ab750884b878f92193b6e141560cf4305241fe45828243e0087912 |

指纹不同先记录，并核是明确新版本还是意外漂移；不修改原文件追齐，不在身份未解决时产生已核验结论。其他未列SHA的材料在task-contract首次读时冻结。

## Task 1：三族定义与依赖映射

输出`definition-map.csv`及三份档案`dual-ma-dossier.md`、`breadth-dossier.md`、`sentiment-dossier.md`，均在本轮raw。CSV是本轮事实映射，不是第二份对象登记表。

固定字段：family、market、object_reference、type、uses、source_path、function、source_sha256、parameters、unit、price_basis、calendar、observation_time、available_at_rule、dependencies、document_definition、implemented_definition、difference、status、evidence_path。

### 双均线

- 精确引用`candidate:lei.dual_ma.bull_state@draft-1`，读取factor_lab候选卡与实际`rules/dual_ma.py::dual_ma_bull_state`、`rules/lei_color.py::classify_colors`、`features/indicators.py`及规则配置。
- 明确Close>EMA20且>SMA20、两均线上升且green；展开green的实际依赖、移位窗口、等号/缺失/预热；不要只复述函数文档。
- 这是每日共同确认状态，不是金叉、首次入场、整个20/60/120体系。false只表示条件未全成立，不自动叫熊市；未就绪必须缺失而不是有效false。
- A股与美股公式复用不等于日历/价格尺度/时区复用。指出当前合成工具使用上海15:00与真实美国收盘的差异。

### 宽度

- 用`definitions.resolve`解析`breadth.csi300.b50.common@1.0.0`和`breadth.csi300.b200.common@1.0.0`的完整卡，不能只读取省略profile字段的JSON片段。
- 核共同分母、资格、历史成员生效/可得时间、覆盖率、分红拆分与缺报价处理；分清0—1和0—100。
- 映射全A、沪深300、创业板指数旧定义与当前研究对象，不把名字相近当同一序列。美国目标先仅核标普500历史成员数据是否存在；无已有对应对象就标未登记，不把CSI300卡改成美国卡。
- 已有宽度变化提案只映射，不新增差分窗口或阈值。

### 情绪

- 读取`market_context/sentiment.py`、`sentiment_signals.py`、`copilot/sentiment.py`、相关domain类型和规则实际加载文件；v1/v2账本口径若不同分别记录，不能假定同一规则来源。
- 列明NAAIM、AAII、A股散户资金流/热度、冰点/强势过热复合条件。若发现其他既有情绪对象仅登记发现，不扩正式研究候选。
- 拆分原始读数、滚动变换、状态、复合条件。核当前值是否进入历史分位、预热样本、发布时间与调查周、重复修订。不能拿周值日填充数量当独立调查数。
- 复合冰点含价格/宽度，不包装成纯情绪贡献；未知发布时间不能补成调查周末。

每档案必须用大白话回答：它描述什么；适用市场；能问的问题；不能支持的说法；旧证据；目前最大缺口；一个最有价值的下一步。

## Task 2：旧证据有限核对

最多精读8份直接相关历史报告（权威规范不计入8份）。起点：

- `docs/research-sentiment-us.md`（先读结论导航，再定位所需原轮次）；
- `docs/experiments/retail-sentiment-ts-2026-09-05.md`；
- `docs/experiments/sentiment-four-input-audit-2026-09-08.md`；
- `docs/experiments/sentiment-combination-feasibility-review-2026-09-08.md`；
- 余4份只按双均线/宽度档案的明确缺口，从现有registry和直接引用选择。

输出`prior-evidence.csv`：旧问题、实际定义、输入/日期、是因子描述还是策略结果、看过/调参史、是否完整条件、原结果、后来纠正、可引用范围、不可推广范围。

不能把旧目录oneLiner当原文事实，也不能为搜不到正面结果继续恢复无限历史。旧策略跑输不等于单因子无信息；简化条件盈利不等于完整条件有效。不得重跑任何旧main或把旧研究历史重命名成未见数据。

## Task 3：美A真实输入可行性，不计算效果

最多12个本地输入快照/有明确版本的数据集。候选固定四载体：510300、159915、SPY、QQQ；不替换缺数据载体挑赢家。沪深300/标普500历史成员及情绪系列共用剩余预算，数据集定义在读取前写入inventory，禁止把很多来源打成一个包绕上限。

允许输出行数、首末日期、缺失、重复、非正/非有限值、日期连续性与字段/元数据资格；不算真实均线状态、分组收益、IC、未来标签或账户。

`input-inventory.json`与`readiness-matrix.csv`逐份记录：

- 实际文件路径/哈希/字节、来源、下载时刻、历史available_at证据、许可证已知情况；
- 标的/交易所、币种、日历版本、时区、复权价格各列尺度、分红拆分、成交量口径；
- 可用起止与预热、缺口原因、成员版本、完整与未知分别统计；
- 可做来源/算术检查、可做事后历史描述、能否支持当时已知的预测研究分别列状态；不要合成一个“可用”。

查看2010—2025覆盖与预热只是资料审查，不要求补齐该范围。只剩2026近期资料也照实交付，不能把少量日子叫长期验证。冻结存量研究数据不能因为加入新列就获得资格。

没有真实交易所日历时，不把工作日或价格日期并集冒充日历；不知道停牌还是缺报价则标未知。美国夏令时/半日市、当地收盘、人民币与美元收益必须单列；中美同日期不等于同一可知时点。

## Task 4：独立小例与接口差异

如需代码，仅在本轮raw中新增`verify_examples.py`与其小测试，不改现有研究引擎。主文件导入不得写文件；输出路径显式给出且拒绝覆盖。使用已安装库即可。

至少以手算或独立规则判断覆盖：

- 共同确认中四类条件任一不成立→false；完整条件成立→true；输入未就绪→单列缺失。不能将调用被测函数的结果再当期望。
- SMA含当日、等于均线不算高于；价格单位同比缩放状态不变，若小例含每份分红则同尺度缩放。
- 宽度小例2只高于/4只共同合格=0.5，B50/B200共同资格；全无资格→缺失不等于0。
- 情绪例按已核真实公式验证一个并列/预热边界，原始值与分位/状态分开。无法独立确认公式则标未核，不发明期望。
- 时间小例：美国下午收盘与A股同日期早间时点不可混用；若依赖的日历不具备真实版本，只作为明确合成时刻例，不宣称交易所事实已证实。

输出`examples-results.json`与`adapter-gap-map.md`。后者必须给B阶段需要的最小隔离适配面：真实模式输入资格、逐行feature_available_at/decision_at、当地收盘与标签成熟、OHLC尺度、源快照与协议输出身份。记录哪些已实现、哪些仅合成假设，不能把“不支持”改成放行开关。

## Task 5：双均线研究协议建议，必须具体但不可运行

产出`dual-ma-study-proposal.json`（status=proposal_not_executable）和`next-execution-spec.md`。

沿设计固定唯一主状态、四载体及参数不优化。给主控可直接判定的建议：

- 各载体准确身份、拟用本地文件及SHA、资格证据与未解决条件；缺资料就填null+reason，不假填路径。
- 主目标建议t+1当地交易日收盘至t+22当地交易日收盘的财富变化；辅助为同期相对起点的最不利收盘变化。明确有21个收盘间隔，不把端点改成开盘，不冒充账户净收益。
- 根据资格而非结果提出确切起止、预热长度、当地交易日历、时区、标签成熟与缺失方案；尚不能确定就列具体阻断，不能让GLM猜。
- 真/假/未就绪；每载体/每年独立汇总；持续状态段与重叠观察不得视为独立成功。主检验不强制IC、不拟合回归、不声称显著。
- 一个预先固定的不重叠观察视角，锚点在首次合法观察处按实际窗口推导，不挑结果最好偏移；仅作为一致性描述。
- 真实资料只能事后重建时，明确允许结论仅为历史关联，不能证明当时可交易或样本外预测。
- B阶段最小文件修改面、测试案例、真实运行路径与额度建议，依赖/数据获取需求单独申请。不给“按结果再挑参数”的余地。

如果双均线资料足够，也必须在这里停：A阶段交付是完整证据与可冻结合同，不拥有B阶段真实运行授权。无需每一步问主控，Task0–6范围内自主做完；到此统一交回。

## Task 6：交付、核验和停止

总报告必须含“一句话结论（大白话）”、三族×美A概览、定义关键差异、四载体数据资格、旧结论边界、实跑小例、最小适配建议、未完成事项和最多一个下一步。

交付清单：

1. task-contract与保护前后核对；三份因子档案；definition-map和prior-evidence；
2. 输入inventory与readiness矩阵（最多12份）；
3. 独立小例记录与允许范围内核验脚本；adapter-gap-map；
4. 不可执行的双均线协议建议与next-execution-spec；
5. 总报告登记registry：category=方法论与验证、verdict=mixed，INDEX补一行；OKR仅给证据建议，不写。

数据表检查：路径存在、SHA一致、唯一主键、status/reason一致、所有超预算/失败/未执行真实记录。缺数据不算失败，但隐瞒缺口算未交付。

报告结构检查一次，修复必要文档问题可再一次，不跑全仓回归：

```sh
python3 -m pytest tests/unit/test_experiment_reports.py -q
```

小例测试按需，日志实报次数；所有新增JSON用标准json.loads读回；本轮文档链接检查。本任务不新增公共计算代码，所以无需为文档修改制造失败测试。

终检核保护哈希。若他人在允许面外发生改动，报告路径/差异并区分归属，不回滚、不把工作区所有漂移算自己造成，也不宣称保护全部未变。

完成即停，交主控书面复核。不要声称发现有效因子、排除过拟合、策略改善或获准交易；不创建自动任务、不私自发消息、不更新OKR完成度。最后回报实际执行目录、分支、HEAD、模型、改动文件与证据路径，让新的主控无需聊天即可核验。
