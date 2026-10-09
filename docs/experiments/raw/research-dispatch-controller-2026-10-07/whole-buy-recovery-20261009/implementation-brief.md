# Goal5 单原始纯买入决策的已提交边界恢复合同

审定者 /root/original_cash_package_review，Astra/high；执行 Sol/medium；root唯一共享记录写者。服务原目标5执行过程可恢复性，既有冻结策略不变。范围不是原部分成交内核集成，更不是生产或真实市场。

仅一个具名人工账户、一个冻结原决策、一个固定串行整笔买单计划。正向只支持P0；P1本轮明确拒绝，不凭归因支持。仅ready、全buy、无卖款来源。无卖出/入出金/支付/公司行动/新周/多批/预占/部分成交/撤单/追单/外部账户变化/并发。原dated_ledger.Ledger唯一资金权威，调用既有SyntheticAccount、decision、plan_p0、begin、opening和attempt_open，旧源不写不改。原订单数量、排序、预算、限价、费用、开盘资格、份额解禁均绑定原输入。不得导入找回ZIP内核，不把其TEST配置变默认。

## 文件与存储

仅新目录的 whole_buy_recovery.py、test_whole_buy_recovery.py、run_recovery_checks.py、frozen-fixtures.json、source-manifest.json、README.md、validation-receipt.json及必要版本化失败记录。root提供output-plan.json绑定本轮新外盘目录；所有运行状态、日志、临时、测试故障产物写该外盘，不回退本机、不删任何失败文件。运行前调用main仓已审定output_storage.recheck_saved_plan核身份和容量再创建唯一目录，之后每次写须核真实设备/位置。旧源PYTHONDONTWRITEBYTECODE=1。小源码和回执本机。禁止commit/push/共享报告registry/INDEX/state写入。

## 方法

新增只创建、恢复、尝试下一固定订单与只读查看。固定具名人工fixture，不开放任意输入/代码/账户/ledger事件平台。冻结初始化输入及外部独立预期hash，每次调用核旧源、外壳、fixture、运行身份；state自己的hash不能自证。修改资金/日历/费用/名称并重算外层hash仍拒绝。

恢复：固定材料重建隔离人工账户/原决策/完整计划；按保存尝试顺序通过原attempt_open重建含拒单的历史，再逐项核各回执及完整状态，吻合才继续。禁把JSON塞旧私有字段、禁pickle/eval。重建是人工内存，报告恢复重建Ledger.apply次数与本次新订单次数分别列，不能说恢复从不调用apply。

单份state.json同时绑定schema/run/输入/codehash、原decision/plan/hash、日历行动身份、稳定请求完整内容及摘要/orderID/回执、下一位置、完整ledger.snapshot与audit、_original_decision_hash/_attempted_keys、batch.expected/receipts/stopped、account._cash_sources/_decisions可比较内容；_sale_results必空。它是核对记录，不独立维护另一套现金。Decimal/时间/集合/tuple显式可逆编码，保留旧hash语义，不放松为只比较余额。

稳定请求身份由run+decision/plan/order+固定opening构成，调用者不能换ID多花钱。先检查完整请求才可重复返回；同ID变日期/价格/数量/费用/计划/证据拒绝。不能依赖原attempt_open按orderID提早返回。完全相同已提交请求返回原回执并独立标本次新增apply=0，不把历史回执apply=1冒充本次。拒单也持久化，重启不能换日/名字追单。格式/身份拒绝在ledger前、权威文件字节不变。

保存临时+flush/fsync+同文件替换后才返回已提交，状态/游标/回执/身份同次写。替换前失败，弃用变化的内存对象，下一调用从最后权威文件恢复；替换后返回失败，恢复必须识别已提交。已有state禁止重新初始化，坏state不清空重置；保留故障文件。只证明单writer已提交边界和可控替换失败，不声称断电/并发/恶意篡改防护。

## 必要测试

1正常两单：410.50，各100份×2元/费5.20，第一后205.30，第二后0.10/总费10.40；不中断与第一后新进程完整状态/回执一致。
2拒单后：首开盘2.001超过限2.000，保存拒单；新进程相同重投只返回旧拒绝，第二可成交最终205.30；预算不挪。
3终态重复、新进程、替换已成功但返回丢失，状态不变不重复扣款。
4替换前一次故障，旧state字节不变；弃内存再恢复处理结果等于无故障。
5对成功和拒绝请求分别核原重放/改日期数量名称均不能新作用；固定计划/开盘输入身份不能换。
6截断/错游标/错回执/错完整状态/矛盾内容即使重算外hash仍拒绝；fixture或旧源漂移拒绝，不能重置。
7P1/await_sale/无可卖整手/行动未知/部分数量/撤单/新决策全部在新作用前拒绝；正向只声明P0。
8实际两个不同Python进程成功后恢复及拒绝后恢复；保留PID、金额、完整差比较；旧源前后hash不变。只跑新测试，不跑旧41/30/13或老套件。repo hygiene用主仓checker，隔离旧缺件不能凑绿。

普通新代码错误保留快照后修复，复验受影响项。出现需改旧源/费用数量/新增策略/范围外状态、不能解释完整重建差、来源hash漂移、磁盘失败、网络或真实数据需求则停相应项报告。允许预算是本合同必要人工工程核验，无新市场运行许可；不重置任何旧预算。

交回准确文件hash、外盘验证位置、真实通过/失败、两条新进程证据、独算金额、旧源不变和限制。主控非作者独审后归档。结论只能是一个原纯买入决策在已提交边界可恢复且不重复扣款，非Goal5全部完成。
