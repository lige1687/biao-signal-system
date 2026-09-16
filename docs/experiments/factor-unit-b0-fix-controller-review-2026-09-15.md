# 双均线 B0 集中修复：主控限定裁决

版本 v1.0.0；2026-09-15。
被审：[执行报告](factor-unit-b0-concentrated-fix-2026-09-15.md)；范围依据：[集中修复任务书](../superpowers/plans/2026-09-15-factor-unit-b0-concentrated-fix-glm.md) v1.0.0；前次依据：[R1–R4主控报告](factor-unit-b0-controller-review-2026-09-15.md)。

## 一句话结论（大白话）

这一轮确实修好了多项旧错误：缺证据、删代码身份会被拒绝，主比较也开始按研究截止时间计算，旧文件保留完整。但还不能宣布整条链可用：稀疏观察仍会展示截止之后的未来收益，虚构供应商引用仍能提升含分红目标的资格，状态计算输出的缺失值也接不进统计。保留已验证部分，暂停真实资格采用与统计接入；按上轮约定不自动再开一轮扩建，不批准 B1 或联网。

## 1. 主控实际执行与身份

- 工作目录 `/Users/yongbiaoli/Desktop/lei-signal-lab`；分支 `codex/factor-unit-research-20260915`；HEAD完整值 `8ba16576b75e605aa1b0d0902568c760c4b99095`，与指定一致。没有切分支、暂存、提交、reset或从main重建。
- 独立执行用户指定测试命令：**87 passed, 1 skipped in 6.39s**。skip为本轮 `test_factor_unit_close_state.py` 分红消费未实现。用户指定ruff命令：**All checks passed!**
- 阅读合同、描述统计、CLI及41项控制器测试，抽查证据矛盾、截止与删键的测试条件，不只看日志。
- 新增主控[独立反例脚本](raw/factor-unit-b0-fix-controller-review-2026-09-15/reproduce.py)和[实际结果](raw/factor-unit-b0-fix-controller-review-2026-09-15/results.json)。统计部分仅用合成资料；资格反例临时改写声明与证据，不改真实输入，不算真实因子/未来收益。临时伪证据已随临时目录清理，原件未改。

复现命令（新输出必须不存在）：

```bash
python3 docs/experiments/raw/factor-unit-b0-fix-controller-review-2026-09-15/reproduce.py /tmp/lei-b0-fix-controller-results-new.json
```

测试命令：

```bash
python3 -m pytest tests/unit/test_factor_unit_close_state.py tests/unit/test_factor_unit_study_contract.py tests/unit/test_factor_unit_state_description.py tests/unit/test_factor_unit_b0_controller_cases.py tests/integration/test_factor_unit_readiness_cli.py tests/unit/test_experiment_reports.py -q
python3 -m ruff check src/lei_signal/research/factor_unit scripts/check_factor_unit_readiness.py tests/unit/test_factor_unit_study_contract.py tests/unit/test_factor_unit_state_description.py tests/unit/test_factor_unit_b0_controller_cases.py tests/integration/test_factor_unit_readiness_cli.py
```

## 2. 已确认、可保留的结果

1. **状态计算保持不动。** `close_state.py` SHA为 `b0efb324a2ef65d1f415c19be4f50b96ebf25f140da0c31b2b759d68ef04db10`，与前轮一致。旧factor_lab七文件在保护表中均一致。
2. **旧证据未覆盖。** task-contract中的B0 raw 123项重算变化0；继承42项仅A阶段报告与更早基线不同，该顶部指针已由前轮认可，不算本轮新漂移。
3. **合同原件与已列产物哈希成立。** 合成正包23项、真实资格包22项，文件集合双向无差、SHA无差；contract.source.json反查contract_sha256一致。包内原文件对当前来源也分别20/19项一致。真实包exit_code=2、restricted，与当前资格函数读回一致；没有真实状态/目标产物。
4. **多项旧反例已实际反转。** 用新版合法合同作正对照可得到ok；在同一新版合同中换成不存在证据后ValueError，删必需代码键后ValueError；字符串false现在拒绝。既有测试还覆盖主比较截止、真假共同集合、空集等，不能因后述缺陷一笔抹掉。
5. **R4撤回方向正确。** 不再把除息日价格变动直接解释为复权混杂；159915对比作废；mtime与skip解释已纠正。

修改面证据：开工保存的7个允许修改文件当前均有变化，全部在许可面；新增控制器测试、报告/本轮raw及导航符合声明类型。由于没有全仓开工文件字节清单，不把这些证据扩大成“整个脏仓其他文件绝对无人修改”；未将现有无关未提交成果归给执行者。

## 3. 两项主动披露的裁定

### a）旧reproduce.py被新版格式提前拒绝

**替换成新版合法夹具验证的路径可以接受；原脚本提前报错本身不能证明R1–R4修复。** 格式升级拒绝证明旧合同不再受理，不等于进入了证据、时间和统计分支。

本次主控已经补做“新版正对照→只改坏证据/只删必需键”的独立测试，确认这两条原缺陷被关闭；也确认字符串false拒绝。41项测试的相关手算期望有独立依据，例如30日例的主比较3/背景8，并非直接抄被测输出。

但覆盖有缺口：截止测试只检查comparison，没有检查sparse_view；state夹具用None而不是上游实际输出的pd.NA；证据测试没有同时伪造表格与供应商引用。因此不接受“41项全过即可代替所有链路核验”的扩大说法。旧脚本保留，无须改写旧证据或强求旧格式继续成功。

### b）v1 CSV错列，改用v2

**格式修复及保留旧件可以接受。** 主控用标准csv.reader核到：v1表头16列，四行长度为17/16/17/16；v2表头和四行均16列。两版的symbol、文件路径、完整SHA四组逐项一致。

人工对照v1原行、boundary-checks与v2说明：510300的1652重叠日与5/3观察被保留但撤回推断；159915的1651错对象对比被明确作废；SPY的8451/1.54e-6与QQQ的6909/1.46e-6沿用原观察。旧八笔具体除息数值仍在旧JSON，不要求复制进新CSV。这里核的是迁移忠实性，未重新证实旧数值为真实市场事实。

两处说明仍不严谨，后续文档处理时更正即可：v2的“同族一致只证明同源同惯例”应改为“数值接近，与同源假设相容，不能证明来源”；510300 allowed_uses中“状态计算待冻结”不代表未知价格基础已合格。CSV格式正确也不代表当前校验器已经拒绝重复产品或检查所有声明，不能扩大为完整CSV校验器通过。

## 4. 尚存实质问题：暂停项与恢复条件

### P1：含分红财富资格仍可由自填声明升级

位置：`study_contract.py` 真实price_basis处理分支。

主控保留真实510300输入文件/哈希和日历，只在临时材料中一致改写合同、证据JSON、来源CSV：

- 档位=`snapshot_provenance_bound`，没有供应商原件，目标=`total_return_wealth` → **status=ok、target=pending_controller_freeze**。
- 档位=`price_basis_verified`，`vendor_traceable=true`，`vendor_response_ref`指向不存在文件，来源CSV同步同档位 → **同样ok**。

原因明确：前者已被代码列为含分红目标可接受档位；后者只检查布尔值与引用非空，没有消费供应商原件。外部文件哈希都真实一致，仍不能说明自写内容是真实事实。原“不得用供应商调整价替代含分红财富”的目标边界没有落实。

**裁决：真实价格资格结论不可被下游采用。** 当前四真实输入仍restricted这一结果保留，但不能推出更高档位判定已可信。恢复前必须按目标分开资格、实际核供应商原件与构造依据，不能把JSON/CSV一起自填当核验。无需为此新增外部因子。

### P1：截止只约束主比较，稀疏结果仍读取未来

位置：`state_description.py` sparse_slots构造及计数。

独立50日递增合成值，研究截止=2019年、数据全在2020年：主比较n=0正确，但 **true_slots_up=2**，slots仍输出约20.79%、16.94%的未来变化且skipped=false。

它没有使用主比较的mature/状态已知共同集合。此时既不能展示为有效稀疏研究结果，也不能当“另一个时间视角已一致”。未知状态也没有完整参与skipped判定。

**裁决：稀疏结果及整套统计接入暂停。** 恢复条件为所有比较输出共用合法集合或明确标注未成熟仅供诊断且绝不计分；截止前不展示成已实现研究结果。只修主n不够。

### P2：上游可空布尔无法直接进入描述函数

主控调用已保留的compute_close_state，在合成50日输入得到前20行pd.NA；原样接入describe_states即抛：`ValueError: state只接受真布尔或空（收到<NA>）`。

这是实际适配接口断点，不是要求新功能。测试使用None绕开了它。恢复需支持上游真实的缺失表示（但字符串false/数字2继续拒绝），并增加完整“close→state→description”合成对照，不复制上游公式。

### P2：终包仍遗漏被引用的价格证据原件

合成和真实终包的合同分别引用 evidence_synthetic.json、real-evidence.json，但两者未列在包内files、实际也未随包保存。23/22个已列文件完整不能证明依赖集合完整；来源CSV不能替代被检查的证据JSON。

**裁决：接受已列代码与合同的存储完整性，不接受单包完全独立恢复的说法。** 原证据仍在本轮raw且可核，未丢失。恢复条件是补件或明确外部依赖清单及保留位置，不必为补件重跑真实资格，更不能重跑真实研究。

补充范围限制：`_needed_start`仍采用评价开始减25自然日，不能代表精确20个交易日预热；当前固定方案应由已核日历逐格列出，不让这一近似自动授予任意市场完整预热资格。此处为源码核查限制，不增加参数研究任务。

## 5. B1申请裁决与执行者交回要求

从现有日历独立定位确认：日历内第21个交易日确为 **2019-10-08**；2025-12-31后的第22个交易日为 **2026-02-03**。单载体、固定区间的方向合理，不应退回四市场齐步建设。

**本轮不批准联网或B1真实计算，也不选择替代目标后偷偷开算。** 网络采样与当前接口修复可分开授权，但本次用户请求是主控复核；不能由“≤8请求建议”自动产生执行权限。

按上一轮“修复后仍有实质缺陷则裁剪/暂停”规则：

- 保留：close_state、R4更正、已通过旧反例、终包已有源码/合同与保护证据。
- 暂停：真实价格资格自动判定的采用、describe_states作为可接入研究消费者、B1。
- **无本轮自动派发的新增返修任务。** 待解决项有上述4类，不能写“无问题”；用户如批准恢复，修改范围限study_contract/state_description/CLI及相应测试、补件与说明，不改公式、不扩依赖、不下载资料，独立复核后再处理资料授权。
- 执行者可直接依据本文确认收到裁决并停止，无须为得到“通过”自行再跑批次。需要补件/修复先获得明确新指令。

过程记录：final-batches-exitcodes.log另披露正式批次后为捕获日志重调CLI，被已有目录检查拒绝。它未覆盖原件，但仍是额外调用，不能把“包只有两份”说成“CLI总共仅三次”。本轮不据此臆测其次数；报告应保持这条偏差可见。

## 最小决策卡

| 问题 | 裁决 |
|---|---|
| 做成了什么？ | 多项旧缺陷关闭，87测试通过，旧123件未动，代码与合同归档改善。 |
| 还差什么？ | 真实证据仍可自填升级；稀疏截止失效；pd.NA接入断点；证据JSON未随包。 |
| 因子有效吗？ | 未计算真实因子表现，没有此证据。 |
| 下一步？ | 保留可信部分、暂停受影响消费者；单510300方案留待明确授权。 |
| 本轮权限？ | 零联网、零实现修改、零OKR写入、零git变更操作；未派发。 |

## ARCHIVE

主控仅新增报告和独立诊断证据，登记与导航保持单一来源。verification-before-completion用于独立验证，不用测试绿替代逐项裁决。本文不抹去上轮已确认成果，也不把剩余问题转成未授权的连续扩建。

交付检查：报告本地链接检查及registry解析另行实跑；87项测试为前述主控本轮实跑，不与文档登记测试重复累加成新的回归数量。修改清单为本文、同名raw下reproduce.py/results.json、registry两个条目与INDEX一行；被审实现、原合同/包均未修改。
