# 利息标签及实际报表行：源口径裁决

2026-10-20。仅审旧固定准入实际使用的197个accession；不取新原件、不看未来结果、不计算OP或收益。唯一依据为此前批准定义、固定资格文件中与营业利润真正处于同一报表的利息行，以及该行的原始金额和展示名称。

**裁决：不能直接恢复四标签通用白名单。197份中185份按现有定义保留，12份净额或混合项目拒绝自动评分；没有需要另行猜测才能决定的剩余项。** 这不是新增定义，而是兑现原定义已经写明的“净利息、利息加其他项目不得静默映射”。

## 输出与范围

[interest-line-adjudication.json](interest-line-adjudication.json)提供完整197行，顶层有 `schema`、`source_filings_sha256`、`rows`；每行包括 `adsh`、`accepted`布尔、`reason`、`tag`、`presentation`。实际配对证据包含营业利润report/line、利息report/line、展示名、标签版本、原金额及匹配事实数量。未用无关报表或不在营业利润之后的展示名判断。

- 本次源文件：固定 `reported-op-qualification-v2/filings.jsonl`，SHA `b323193685ca7727979c8dfa9babacde1fed91683e7e1800186408649d772383`。
- 本次197个adsh集合来自旧固定 `final-admission.json`，SHA `80fa23246136852bc7e3faa21ee8786ba0d8b0c391ff595c75bc53539e489e0d`。
- 旧准入2,083成员月份中，这12份对应116行；其余185份对应1,967行。这是根据已选申报映射的资料计数，不是新准入最终验收或收益统计。
- 其他申报不在本次审阅范围。后续必须同时满足新准入资格及此表 `adsh存在且accepted=true`，不能把185份的接受扩展为同公司其他年份或同标签全部来源接受。

## 12份拒绝：实际展示与同报表位置

下表原金额单位为百万美元，只用于定位源事实。`R`为原PRE报表编号，箭头为营业利润行→所扣项目行。全部位置关系成立；失败的是经济含义，不是行号。

| 发行人／adsh | 实际标签 | 实际展示名 | 原金额 | 同报表位置 |
|---|---|---|---:|---|
| MPC `0001510295-15-000007` | InterestAndDebtExpense | Net interest and other financial income (costs) | 216 | R2：15→16 |
| MPC `0001510295-16-000078` | InterestAndDebtExpense | Net interest and other financial income (costs) | 318 | R2：16→17 |
| NWL `0000814453-20-000078` | InterestAndDebtExpense | Interest expense, net | 303.3 | R2：7→9 |
| BWA `0000908255-22-000009` | InterestAndDebtExpense | Interest expense, net | 93 | R5：7→10 |
| BWA `0000908255-23-000013` | InterestAndDebtExpense | Interest expense, net | 52 | R5：7→10 |
| ESRX `0001532063-14-000006` | InterestExpense | Interest expense and other | 596.1 | R4：5→9 |
| ESRX `0001532063-15-000004` | InterestExpense | Interest expense and other | 582.9 | R4：5→9 |
| HAR `0001193125-14-300900` | InterestExpense | Interest expense, net | 8.026 | R3：5→7 |
| HAR `0001193125-15-283170` | InterestExpense | Interest expense, net | 13.929 | R3：5→7 |
| NWL `0000814453-21-000050` | InterestExpense | Interest expense, net | 274 | R2：7→9 |
| NWL `0000814453-22-000017` | InterestExpense | Interest expense, net | 256 | R3：7→9 |
| NWL `0000814453-23-000026` | InterestExpense | Interest expense, net | 235 | R3：8→10 |

因此需要更正最初概括：五份 `InterestAndDebtExpense`实际是MPC两份、NWL一份、BWA两份，不能称“五份MPC”。此外，187份名为 `InterestExpense` 的事实中也有上述7份问题；标签名本身不能证明是独立利息费用。

拒绝含义是“现有实际行未证明符合已冻结计量”，不宣称这些公司会计披露错误。`net`在没有更具体说明时不能猜成未抵消利息收入；`and other`不能假定其他部分为零。不做绝对值转换、补零或在混合金额中猜分拆。恢复这些具体行需要原申报中可核对的独立费用或组成桥接，而本轮不为恢复它们另开取数。

## 保留项，及不能机械拒绝的“net”

185份保留组成：167份实际配对展示为单独 `Interest expense` 的 `InterestExpense`、13份明确扣除资本化部分的 `InterestExpense`、5份单独利息费用的 `InterestExpenseDebt`。

五份 `InterestExpenseDebt`为：

- WU：`0001365135-14-000014`、`0001365135-15-000008`、`0001365135-16-000062`、`0001365135-17-000008`，均为同R2营业利润行10之后的利息行13，展示 `Interest expense`。
- KDP：`0001418135-22-000005`，同R2营业利润行7之后的利息行8，展示 `Interest expense`。

原定义要求单独列示费用，未限定必须恰好拼写为两个tag之一。这五个准确的申报行可以作为已核映射保留；它们不授予全局 `InterestExpenseDebt` 白名单。

另13份实际展示为 `Interest expense, net of amounts capitalized` 或 `Interest expense, net of interest capitalized`。其明确意思是**扣除计入资产成本部分后，本期确认的利息费用**，与用利息收入抵消利息费用的净额不同。当前定义采用报表当期费用，不应额外把已资本化成本再次扣进当期，故在既有合并期间和报表结构条件下保留。这些13份的逐adsh、原值与同IS行证据均在JSON。不能写成 `contains("net") => reject`。

## 主控的一次修复应怎样落实

1. 保留失败运行器、旧合同、旧资格和旧准入绑定；本表作为源语义纠正附件。之前的准入审阅对这12份不再适用，但其余已通过且未受影响的检查无需重跑。
2. 从旧形成池仅拒绝选择了上述12个adsh的行，理由写 `interest_line_is_net_or_mixed_not_standalone_expense`。不删除公司全部历史、不换更老报表来绕过本次拒绝、不使用未来结果决定去留。
3. 以新的不可变准入绑定执行既定配对。允许读取的来源必须同时匹配本表 `source_filings_sha256`和本表文件指纹；实际扣减事实须与表内tag、version、report、line、金额匹配。新的未知结构拒绝自动评分，不能从“标签在四个名字中”推断接受。
4. 同一次机械修复验收覆盖：独立费用接受；同tag净额拒绝；利息加其他拒绝；明确资本化扣除保留；无关报表标签不影响实际配对；adsh不在本表拒绝。然后核新准入计数及配对规则，不重跑原A/B资料，也不改已经冻结的金融问题。

本裁决在任何效果读取之前完成，不是依据正负结果筛选公司。标签集合不一致暴露了真实语义缺口；修复目标是恢复原已批准定义，不能将四标签全部接受作为“兼容性修复”。
