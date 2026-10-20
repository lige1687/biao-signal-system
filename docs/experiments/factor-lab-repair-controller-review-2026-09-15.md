# Factor Lab集中返修：主控第二轮复核

版本v1.0.0；2026-09-15；分类：方法论与验证；verdict=mixed。
对应执行报告：[集中返修](factor-lab-concentrated-repair-2026-09-14.md)。本报告包含可直接交回执行agent的最后一轮限定收尾规格。

## 一句话结论（大白话）

大部分原反例已修，132项测试复跑通过，保护文件也没有变化。但还不只是补一份运行清单：不同输入仍可能被认成相同，必查清单仍能被同时删减，时间审计的计数与实际使用不完全一致。先集中修完下列四项，再补终版合成证据；不增加因子、不退回固定ETF池、不安装外部工具。

## 1. 主控实际验证

```sh
python3 -m pytest tests/unit/test_factor_lab_contracts.py tests/unit/test_factor_lab_adapters.py tests/unit/test_factor_lab_diagnostics.py tests/unit/test_factor_lab_validation.py tests/unit/test_factor_lab_attribution.py tests/integration/test_factor_lab_cli.py -q
python3 docs/experiments/raw/factor-lab-controller-review-2026-09-15/reproduce.py
```

- 六文件测试：**132 passed in 13.66s**。本轮未重复358项全套相关回归，不把执行者的回归结果写成主控实跑。
- 对本轮protection-baseline逐文件复算：29项保护文件、411项raw全部零变化。411=所述408项目录文件+另外3个单文件，不是执行者少保护了数据。
- 当前v1.1.1数值协议实际通过`verify_frozen_contract`，随后在同一真实函数验证裁剪反例；没有调用正式CLI重跑。
- 三个v1.1.0正式manifest.outputs均为空，和披露一致。其冻结代码与当前代码均只有runner.py不符。因此“当前CLI即可复放v1.1.0”不成立；若旧runner原件有保存，需提供其准确路径/哈希，否则只能保留为旧运行证据，不能从哈希恢复源码。
- `_write_manifest`现已在落盘后逐文件取哈希，修复方向正确；本轮未另行正式运行来证明终版整批闭合。

本次复核脚本只调用合成函数及读取文件。第一次误将测试夹具返回的整个protocol当comparison，按合同正确拒绝；修正为protocol.comparison后才取得下列有效反例，不将夹具误用算成代码缺陷。

## 2. 最后一轮限定必修项

### S1：归因仍可能把不同输入判成相同（高优先级）

位置：`src/lei_signal/research/factor_lab/attribution.py`，`_layer2_decision_increment`的input_identity处理。

主控提供`input_identity={base:{prices:A}, variant:{prices:B}}`，实际输出input_identity_equal=true，仍为attributable_to_declared_action_only。原因：取出variant后覆盖原变量，随后从这个variant对象读取base，最终比较的是同一份东西。

修复要求：分别从原合同读取两侧，或明确只允许一种共享输入格式并拒绝两侧形式；不可悄悄自比。两侧相等、不同、缺一侧、None均需测试。顺带锁定费用表空字典不能冒充完整规则；这属于已有必查条件结构，不增加费用引擎。

### S2：必查清单仍由被检协议自行裁剪（高优先级）

位置：`runner.py::verify_frozen_contract`。

主控把数值案例required_checks与expectations同步由23项缩为1项，保留原独立期望来源及其哈希，入口仍接受。当前只验证两个字段相互包含，没有验证必须检查的集合。

修复要求：每类冻结案例的必需ID集合来自独立、固定的规格（或经校验的独立期望产物），不能同删两个字段即可免检。缺项、多余未知项、重复项及改单项期望必须按明示规则核验。验证源文件存在且哈希一致不等于协议中的期望值来自它。不得另写一套手工重复维护的期望库；复用独立期望脚本的明确输出与固定案例合同。

### S3：时间审计没有复用同一合法集合（高优先级）

位置：`validation.py::audit_validation`，构建excluded_any与clean；以及diagnostics中的时间消费。

主控反例一：一行已标feature_not_available_by_decision_time，审计仍n_usable_clean=1，但segment_ic=null。它没有重新进相关计算，**不能夸大为重新入算**，问题是计数与统计不一致。

反例二：直接审计标签start=1月6日、end=1月4日，仍clean=1且segment_ic.n=1；预测诊断会检查倒挂，直接审计却没有同样检查。当前两个接口并非真正共享逐行合法集合。

修复要求：原排除原因与新增时间排除取并集；时间倒挂、缺失、非有限值在两个入口一致处理；n及所有统计从同一集合产生。每个原因可追溯，不能仅把计数改0而仍使用原行。

另外将“特征时间资格已实现”收紧到实际能力：现在只检查调用者声明feature_available_lag_days，默认0，并未逐行比较feature_available_at与decision_at。最后收尾二选一：实现已要求的逐行时间比较，并对同日14点/16点有测试；或在所有接口和文档明确限定为合成即时可得假设，未知/未支持时间语义不得获得已核验结论。不得把补一个滞后开关等同完整历史时点核验。日期级标签成熟必须注明收盘等具体事件时刻；未知不能靠日期相等默许成熟。

### S4：非有限值输出不是合法JSON；终版证据需补齐

位置：`runner.py::_dump_json`。

主控执行`json.loads(_dump_json({value:NaN}))`实际报Extra data。原因是把NaN换成null后在JSON后面追加`// non-finite sanitization`注释。JSON格式不允许这类注释。

修复要求：警告放到结构字段或独立质量文件；所有JSON输出必须经标准json.loads读回。测试NaN/Infinity/-Infinity及嵌套结构，合法有限值仍正常。保留manifest最后写及逐文件哈希修复，不为重跑覆盖旧manifest。

## 3. 可直接交回执行agent的收尾任务

本节承接原集中返修计划及主控初审，不另立规范。先读根/相关AGENTS、原计划与本报告；规范版本、对象ID和只读边界沿原任务，实际版本/指纹仍须记录。

**范围：**仅S1–S4；允许修改factor_lab相关模块、原六测试、使用手册、本轮新报告及报告registry/INDEX。definitions登记表、底层生产函数、旧raw、旧协议、OKR不改，不提交git。不要重开已通过的均线/动量算术或引入Alphalens。

**步骤：**

1. 新建`docs/experiments/raw/factor-lab-final-closeout-2026-09-15/`，保存允许修改面的当前源码原字节及哈希，冻结现有协议/运行哈希。先运行本报告脚本，把上述反例写成失败测试；不要改主控脚本或旧夹具掩盖问题。
2. 按S1→S2→S3→S4修改，每项有明确反例和合法控制。局部测试按需；完整相关回归最多2次，准确文件集合及命令在运行前登记，不能用测试总数当目标。
3. 补旧v1.1.0可复放性说明：提供旧runner原件或明确尚不能证明完整源码可恢复；协议副本不能替代源码。修改报告§4/§6的过强表述。列明此前临时目录调试次数，不把所有完整CLI执行仅因路径在/tmp就从运行史删除；既有任务允许临时集成测试，不在缺证据时追认违规。
4. 完成局部测试及冻结合同检查后再保存新协议，文件名含版本，排他创建，代码/卡/源数据/独立期望/必查集合一致。保存全部执行源码快照，不仅保存哈希。任何冻结后改代码都先出新版本。
5. **终版补证额度：仅一批3个合成案例，每例1次。** 该额度须在S1–S4局部验收全部通过、冻结完成后使用；不建议现在单独重跑v1.1.1。任何正式失败停在该案例，继续离线排错可以，但不得自动获得重跑额度。临时完整CLI调试逐次记录，禁止把完整重复批次藏进/tmp绕过额度；pytest临时目录测试单列，不冒称正式证据。
6. 成功产物逐项检查：标准JSON可解析、manifest.outputs与实际产物集合及SHA一致（排除manifest自身）、协议原字节SHA一致、数值/标签/元数据可追溯、旧29+411保护项无变化。失败不能留下已完成标记。
7. 新报告`docs/experiments/factor-lab-final-closeout-2026-09-15.md`按S1–S4返回：修前反例、修后结果、正控、命令/次数、前后版本/源码存档、输出核对、未实现能力。旧报告仅追加纠正指针，registry/INDEX登记mixed，不写OKR完成。

这是首轮建设的最后一次预定返修机会。若仍有实质缺陷，交回主控裁剪未可信能力或暂停该分支，不自动开展无限下一轮；其余可确认的计算能力保留。完成即停。

## 4. 方向及ARCHIVE

本次不能宣布R1–R4全面收口，也没有必要推倒通用工具。先完成有限收尾；之后另行授权Alphalens-reloaded隔离复用，减少排名诊断重复实现。真实因子研究按各因子适用标的与资料资格分别开展，固定ETF池不作为通用工具的强制前提。

| 决策卡 | 本轮答案 |
|---|---|
| 改变什么 | 暂不单独重跑v1.1.1；先修4个有限问题再补终版证据 |
| 对照 | 冻结任务要求、实际源码与独立合成反例 |
| 资金来源解释 | 无真实收益；归因只审合成账户合同 |
| 代价与授权 | 本次零正式运行、零联网、未改实现；下轮限一批3例 |
| 结论 | mixed；132项测试通过不抵消新反例；无因子有效性/生产授权 |

ARCHIVE：封存主控第二轮发现；后续结果另报告。本轮不更新OKR状态或完成度。
