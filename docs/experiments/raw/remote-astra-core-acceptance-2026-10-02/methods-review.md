# T7–T10 方法验收辅助意见（2026-10-02）

范围：只读审阅 `4155b4db` 交付的任务书、提案与 Python 校验器；未运行脚本、未联网核对论文或交易所声明、未接触主电脑资料。以下行号均相对该交付 checkout。这里的“满足”指任务书规定的方案或演练交付已写出，不代表真实交易效果或已具备运行资料。

## 需要主负责人处理的发现

1. **T10 的 `complete` 不能解释为“可按旧代码复现”。** `handoff_check.py:56-85` 只核清单中列出的文件和代码 blob；`missing` 项仅加入 findings，不降低 `complete` 状态，也未核 `originals`、`path_map`、依赖版本、预期输出的数值或 `code.commit`。真实示例明写原实验 Python/pandas 版本未知、历史行情到达时间未知（`example_manifest.py:55-66`），却以 `complete` 为自检通过条件（`:69-72`）。任务书要求列出缺项及复查用途（`RESEARCH-DECISIONS-ARCHITECTURE.md:45-53`）；清单格式满足，但“complete”至多是**已列字节与三个已列代码文件匹配**，不能据此开 B 类旧代码复现。建议把此示例的缺项、环境未知及旧锁的独立核验作为复现前置条件，或把状态收窄命名。
2. **T9 记录链只能发现不一致的局部改写，不能保证旧历史不可重写或机会齐全。** `observation_ledger.py:20-40` 的哈希及上一条哈希都在同一可编辑文件内；整体重算链后仍可通过，缺独立保存的冻结指纹、外部时间戳或只追加存储。`validate():42-55` 只检查机会在冻结日之后和结果晚于填报的成熟日，没有验证 `outcome` 对应已有机会、同一对象版本、关联快照和 20 个交易日实际成熟，也没有枚举当月本应出现的全部机会。`T9/README.md:5,11` 的“全部机会”“改历史可被发现”因此超过校验器保证；五个合成状态和三个负例仅证明指定篡改会被抓到。实际启动前需把原始快照与冻结协议指纹独立锚定，并对机会清单、成熟日期、版本关联作人工或程序复核。
3. **T9 草案的“新数据支持/不支持”条件尚未被演练实现。** `T9/observation-contract.md:14-15` 要求去掉任一时期后方向不变、连续 24 个月仍无可比较结果则结束；`observation_ledger.py:102-117` 只计首次/后续数量和平均值，永远给出 `describe_only` 或 `insufficient_no_comparison`，没有时期分组、逐期剔除或 24 个月结束判定。作为合同草案可以有条件接受，不能把 5/5 演练写成“判断更新规则已经可执行”。
4. **T7 当前计数不等于未来可用样本数，且巧合比例不是有效性概率。** `qualification_count.py:30-37,62` 直接使用生产全历史构造识别，代码自己注明可能改写历史；`T7/README.md:31-32` 也承认正式研究须逐日按当时历史识别。`T7/contract.md:23-24` 的 30 次、13 簇仅限两只 ETF、这一识别版本及被截断的一个窗口，不能当六 ETF 后续合同的样本资格。`method_examples.py:94-105` 的 `1/2^G` 要求簇之间可近似独立、零效应下正负号对称；同一市场冲击及分组边界会破坏这些前提，`T7/README.md:31` 已有提示。`contract.md:16` 用它作事前 `describe_only` 判断可以是保守提示，不能称为“排除巧合的概率”或科学充分性门槛。
5. **T7 账户差的剩余项不能直接解释为“资金复用贡献”。** `method_examples.py:183-194` 以账户收益差减去逐次交易收益差之和，标作 `capital_reuse_part_not_condition_effect`；这一差额还会包含复利、仓位、执行顺序和价格路径等因素。`T7/contract.md:17` 已写“资金复用及其余”，应沿用这个较准确的名称；E2 合成例确实能手算出 6%，但它不证明真实账户中可把剩余项归因为资金复用。另 `contract.md:14-15` 的每簇简单平均使大簇与小簇等权，是明确的研究取舍，应报告簇大小及逐簇差，不宜把它解释成每笔交易的平均作用。
6. **T8 的首选路线是有条件的移交决策，不是资料资格验收。** `T8/README.md:11-16,20-26,46` 明确远端缺四只 ETF 的同口径日线、84/84 行动原证、9-27 账户 raw，历史到达时间、部分公司行动覆盖和沪市日历也未证明；`data-contract.json:10-16,21-38` 只列字段、指纹、覆盖和未知标记。即使 R1 移交成功，指纹一致只证明副本相同，不能自动证明各日价格、行动资料当时可知。应保持“有限历史资格”，待实际移交逐项验收后再作 T2/T7 正式研究输入判断；小时数据仍为未接入（`T8/data-contract.json:41-49`）。

## 明确满足的原任务要求与边界

- **T7：** 对三种办法的目标、数据与误导点给了表格，并选同一回撤配对、时间重叠分组为主；合同写出机会并集、成交/退出、简单对照、结果、停止条件（`T7/README.md:7-15`、`T7/contract.md:5-19`）。四个人工情形覆盖同机会、机会改变、相邻重叠、极端单笔（`method_examples.py:136-165`）。脚本的 4/4 结果需由主负责人运行核实；例子本身明确是合成且不计费用（`T7/README.md:26`）。
- **T8：** 三条资料路线、每类阻塞的字段/时期/许可/核验条件、下一批三个问题及停止事实都已写出（`T8/README.md:18-44`；`T8/data-contract.json:6-52`）。交易所法律声明的现场真实性由主负责人另核，本次未联网。
- **T9：** 固定对象版本、起点、假设、对照、费用、节奏、停止/暂停、采用边界和五类合成状态均在草案中（`T9/observation-contract.md:3-35`）；报告明说真实观察未启动、A03 原协议不在快照（`T9/README.md:20-35`）。
- **T10：** 区分旧数字核对、冻结代码重算和新合同重算；给出公开/授权边界、机器可读清单和五个合成错误类型（`T10/README.md:7-33,44-52`；`handoff_check.py:122-150`）。原任务只要求四个类型，第五个换行符差异属于有用的补充。校验器尚不能单独保证跨电脑完整复现，见发现 1。

建议整体措辞：T7–T10 的**方法、路线与草案交付可按限定范围接受**；T9/T10 的程序保证要按上述边界收窄，真实观察启动、正式收益比较、旧实验完全复现均仍待资料与关键定义验收。这里不代主负责人决定策略语义、生产修改或用户授权。

## 两个最小复现片段（供主负责人执行；本审阅未运行）

在交付 checkout 根目录运行。片段只调用交付方现有函数，在内存或临时目录中处理合成资料。

**T9：整体重算哈希链后，改写过的结果仍被接受。**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path("docs/experiments/raw/remote-astra-T9-2026-09-30").resolve()))
import observation_ledger as t9

ledger, _ = t9.case_matured()
print("before", t9.validate(ledger))
next(r for r in ledger if r["kind"] == "outcome")["payload"]["values"]["ret20"] = 0.9
for i, record in enumerate(ledger):
    record["prev_hash"] = ledger[i - 1]["hash"] if i else None
    record["hash"] = t9._digest(record)
print("after", t9.validate(ledger))
print("rewritten_first_mean", t9.review(t9.derive(ledger), t9.OBJ)["first_mean"])
```

预期观察：`before []`、`after []`、`rewritten_first_mean 0.9`。解释：`validate()` 能发现**未同步重算哈希的局部改写**；整条链和结果一起重写时，无独立锚点便无法判别原记录。该例不表示记录格式毫无作用。

**T10：清单明列关键缺项仍返回 `complete/proceed`。**

```python
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path("docs/experiments/raw/remote-astra-T10-2026-09-30").resolve()))
import handoff_check as t10

with tempfile.TemporaryDirectory() as tmp:
    package, code, manifest = t10.build_synthetic(Path(tmp))
    manifest["missing"].append({"item": "frozen dependency lock required for replay", "reason": "not transferred"})
    result = t10.check(package, manifest, code_root=code)
    print(result["status"], result["action"])
    print([f for f in result["findings"] if "declared_missing" in f])
```

预期观察：`complete proceed`，同时 findings 含新增的 `declared_missing`。解释：这里的 `complete` 只表示**已枚举文件和代码 blob 的字节检查通过**；它没有证明冻结依赖齐全或能实际复现旧实验。
