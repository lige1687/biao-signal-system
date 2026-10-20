# R1-risk1 收益前静态代码审阅

日期：2026-09-08。审阅范围限本批冻结协议与收益前执行适配；未运行四个真实账户，也未复核未来产生的资金结果。

## 结论

**通过，可以按当前收益前锁运行。** 没有发现会把本批问题改成另一套问题的偏差：新增接口只让指定集合使用1%计划风险确定数量；R1仍走原诊断候选筛选和原道路退出；执行器只生成两只产品、两档费用共四个R1-risk1账户。源文件锁与当前实际文件一致。

## 逐项核对

| 协议要求 | 静态证据 | 结论 |
| --- | --- | --- |
| 新增数量集合独立，默认旧行为不变 | `engine.diff`只新增`risk_sized_config_set`、`uses_risk_sizing`及两处数量判断；空集合时逻辑仍为原P7/显式配置条件。真实沪深300旧R1代表的daily、trades、orders、events、roundtrips五类输出逐项相等。 | 通过 |
| R1-risk1不启用3倍目标筛选 | 内部`config_id='R1'`仍进入诊断分支；`target_unavailable`和`signal_reward_risk_below_3`继续旁路，开盘只要求正失效距离，`risk_sized_config_set`没有改变`is_explicit_config`。缺目标和不足3倍的单元例均通过。 | 通过 |
| 只改买入数量 | 原现金可买整百份与“前日账户财富1%÷开盘风险距离”的整百份取较小值；结构失效优先、EMA20与20根前收盘同时跌破的退出分支没有改动。 | 通过 |
| 使用前日财富 | 每个交易日开始先复制`previous_equity`为`risk_reference`，买入后到日末才更新。新增反例在买入日开盘10、收盘11时仍记录前日财富100000和预算1000，而日末财富为100990。 | 通过 |
| 四个账户与单产品输入 | `run_accounts.py`按2只产品×2档费用循环；每次只传该产品价格、行动、候选、退出观察及限制条件，初始100000、每周追加0。输出标签为R1-risk1，内部身份保持R1。 | 通过 |
| 313条候选不改 | 运行前筛选冻结输入中的R1和两只指定产品并断言313；只读计数为沪深300ETF 158、创业板ETF 155。每个单产品账户收到自己的子集。 | 通过 |
| 费用、现金上限与整百份 | 数量先按含买入费的现金上限取整百份，再与风险数量取小；成交函数再次断言现金足够。费用现金上限和不足一手例通过。 | 通过 |
| 收益前输入冻结 | `source-lock.json`的SHA-256为`be43adaba201acaf205249b748d520930987278965b644931ead45fe214e6dcd`，其中14个运行依赖均与当前文件匹配；runner在建结果目录前、逐账户后和完成前都会复核。 | 通过 |

## 测试与保留记录

`preparation-tests.log`保留了不足一手反例首次写错参数而失败、修正后6项通过，以及补入前日财富反例后的最终7项通过。这是测试本身的修正，没有掩盖执行算法失败。`real-default-regression.log`记录旧R1代表五类表完全一致。

静态审阅没有重新运行真实账户。`execution-report.md`或同等准备说明在审阅时尚不存在；当前仍处于收益前阶段，这不阻断执行，最终执行报告应在运行后记录实际命令、锁指纹、完成状态和任何失败尝试。

## 审阅文件指纹

| 文件 | SHA-256 |
| --- | --- |
| `protocol.md` | `aaced19dd2e6c71228af6c194454410ab52e6874eb13b284c76eef22fbcb1b78` |
| `execution/engine.diff` | `8cc5013b12d72b600d951d4f37a8af4810078567cbff339436725ff464a13766` |
| `execution/engine.py` | `a828d373d86b8547698b61386401829cb05d3616c9272ec0297ad1b801b1e8be` |
| `execution/run_accounts.py` | `5742c699c607ff656a407360a166bcf47a7f8cbb790a7ea81997dbc4260899dc` |
| `execution/test_engine.py` | `fdebe21b7b2e9da3c4031204adedda361537174e962f46b7a9ad6a5b3aeac675` |
| `execution/preparation-tests.log` | `4d3ba3f31c087a55f241b2670cd049d9cc2ef01b0e8d730de73b3da1ee60665b` |
| `execution/real-default-regression.log` | `f6b3f36b4ecf4511430d1f3511fece924adb933f11509f68df26f3a55c4e1983` |
| `execution/source-lock.json` | `be43adaba201acaf205249b748d520930987278965b644931ead45fe214e6dcd` |

文献说明的术语已同步改成大白话；它不属于本次执行代码审阅指纹。
