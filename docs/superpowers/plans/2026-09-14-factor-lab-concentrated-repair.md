# Factor Lab集中返修 Implementation Plan

> **For agentic workers:** Use `executing-plans` if available to execute task-by-task. 本任务默认一个执行agent串行负责，完成后统一交回，不自行宣布验收。

**Goal:** 一次修完主控R1–R4，使时间资格、协议身份、归因条件与输出证据实际一致。

**Architecture:** 继续使用factor_lab六模块和既有研究函数，仅修接口及消费规则。一个统一排除结果供计数和统计复用；运行前核对冻结合同，运行后记录证据；未知归因条件保持未知。

**Tech Stack:** 当前Python、pandas、pytest、ruff；零新依赖。

版本v1.0.0。开始执行本任务即按下列新额度执行，不能借用上一轮未用额度。

## Global Constraints

- 先读根及相关AGENTS、`docs/trading-spec-v1.md`、`configs/rules.v1.yaml`、MACD和板块规则入口，以及原任务要求的研究规范。
- 权威规范：`docs/research/experiment-backtest-principles.md` v1.1；`definition-standard.md` v1.1.0；`ai-execution-contract.md` v1.0.1；`experiment-report-template.md` v1.1.0。均相对于docs/research。实际版本不同则记录差异，不能猜。
- 定义唯一来源`docs/research/definitions.v1.json`，只读。六对象均@1.0.0：mixed.momentum.raw、mixed.rv20、trend.distance50、trend.distance200、breadth.csi300.b50.common、breadth.csi300.b200.common；候选candidate:lei.dual_ma.bull_state@draft-1只读绑定，不能登记为已验证交易因子。
- 先读原计划`docs/superpowers/plans/2026-09-14-factor-research-workbench-v1.md`和主控`docs/experiments/factor-lab-controller-review-2026-09-14.md`。原任务冻结协议及运行只读，新协议排他保存新版本，不能给旧产物倒填。
- 可改：`src/lei_signal/research/factor_lab/`、`scripts/run_factor_lab.py`、原六份factor_lab测试、使用手册、执行报告和报告registry/INDEX。既有底层消费者、生产规则、定义登记、旧raw和OKR均不改。原报告只追加纠正指针。
- 新证据目录：`docs/experiments/raw/factor-lab-concentrated-repair-2026-09-14/`。新报告：`docs/experiments/factor-lab-concentrated-repair-2026-09-14.md`。
- 不联网、不安装Alphalens、不增加因子/数据/真实账户路径、不改变策略、不提交git、不清理他人修改。
- 单元及临时目录集成测试按需；相关完整回归最多2次。正式合成运行仅一批3个案例，每个1次，失败不自动获得重跑额度。全部预检通过再运行；失败可继续离线修复和测试，但新正式运行先申请。旧额度不累计。

## Task 0：冻结与反例留证

Files：本轮新raw目录、主控reproduce.py只读、原六测试文件。

- [ ] 保存git状态及允许修改面；对原29项保护和408项raw清单逐项哈希建立本轮基线，缺原清单即注明，不制造可比数字。
- [ ] 运行主控reproduce.py，保存实际输出与环境版本。现有错误返回是本轮失败证据，不是期望成功。
- [ ] 将R1–R4反例写为新测试，先在未修代码运行并记录失败；分别断言具体原因，不能只断言非零。

核心测试断言（复用现有夹具构造函数，不能改夹具使反例消失）：

```python
assert unknown_result['periods'][0]['n'] == 0
assert crossing_result['sample_counts']['dev']['n_usable_clean'] == 0
assert future_result['sample_counts']['holdout']['n_usable_clean'] == 0
assert comparison_result['layer2_decision_increment']['status'] != 'attributable_to_declared_action_only'
```

## Task 1：时间资格真正控制统计

Files：contracts.py、diagnostics.py、validation.py、对应三份单测。
Interfaces：保留`evaluate_predictive(batch, targets, protocol=...)`和`audit_validation(pairs, trials, protocol=...)`；共享合法配对判定，返回逐行原因与统一clean集合。

- [ ] 明确每个时间段的评价/拟合截止（带时区）；不得暗猜下一段00:00，也不得把时刻降成日期。冻结协议显式给出截止，且不晚于全局evaluation_cutoff。
- [ ] 先检查标签时间顺序，再处理缺失、未成熟、晚取得、跨段。标签从未来发生是正常定义，只有未成熟/当时不可知/污染时间段时排除，不能把所有未来标签叫泄漏。
- [ ] 特征available_at<=decision_at；标签end<=评价截止且available_at<=评价截止。None/NaT/NaN一致输出未知原因；非法或无时区值是格式错误。
- [ ] clean mask同时供n、IC、状态均值和分组统计使用，不只改变报告计数。示意消费规则：

```python
clean = pairs.loc[pairs['exclusion_reason'].isna()].copy()
assert len(clean) == int(pairs['exclusion_reason'].isna().sum())
```

- [ ] 跨段、同日14/16点、未知、倒挂、完全无目标、无有限值、min_pairs边界逐项测试；合法对照必须有非零统计，防止一律排除。
- [ ] 尝试史加入完整池/目标/输入身份；旧资料未知显式unknown，不伪造之前已冻结。仍输出过拟合风险未排除，不新增统计推断方法。

## Task 2：运行前核对协议，而非运行后才记代码

Files：runner.py、contracts.py、adapters.py、CLI及合同/集成测试。
Interfaces：`run_protocol(protocol_path, output_dir)`保持现有返回码；身份失败3、合法不足2、合成完成0、意外错误/期望失败1。

- [ ] 建立不可由协议删减的必需代码键集合，含CLI、六模块及实际复用依赖；直接调用规则配置加载器时纳入身份。冻结准确卡内容/候选卡/规范/登记表版本及指纹；计算前比对实际文件。
- [ ] 目标只支持entry_offset=1、exit_offset=22；其他值立即拒绝，不能协议写10而实际算22。min_pairs、单位、预处理、观察规则同样禁止声明与执行分离。
- [ ] 新协议保存原字节副本，manifest区分文件SHA与规范化内容SHA；current指针不作为运行输入。每个值文件有旁置元数据索引：对象/版本、单位、输入快照、池/日历、价格/币种、时间语义、原因和质量。不能用DataFrame形状代替输入身份。
- [ ] 删一个必需代码键、改CLI预期哈希、改卡、错登记表版本、改目标参数、输入篡改均在计算前拒绝3。正向走真实函数，不patch资格返回值。临时测试可以复制源树后改副本，不改工作区受保护文件。
- [ ] 合成数据也须声明价格尺度/日历/时间；真实资料仍不在本轮开放。缺必要信息按明确格式失败或资料不足分流，不能偷偷填值。

## Task 3：有差额不代表已经解释原因

Files：attribution.py、test_factor_lab_attribution.py。
Interfaces：`explain_strategy(accounts, model_card=..., protocol=...)`保留三层；新增比较合同置于protocol，不用成交记录反推未成交候选池。

- [ ] 明确并核对完整池版本、期间、初始资金、外部资金流、费用表、基准、除声明动作外冻结规则及输入身份。相等指纹只证明材料一致，不证明现实执行正确；合成合同始终标合成。
- [ ] 固定必查集合，`must_match=[]`或删字段不能逃过检查。池不同拒绝归因；缺合同允许显示算术差额但status必须not_attributable或明确条件性，不能出现only。
- [ ] 未核项不记true。费用按规则比较，不能从已成交平均费率证明全费用规则相同。
- [ ] 正向同合同仅退出不同可获限定结论；分别改池、外部入金、基准、费用、规则和删合同得到可定位原因。账户资金贡献与事件映射既有测试全部保留，events与actions不互换。
- [ ] 模型卡校验字段类型、factor_return引用、频率/币种/窗口/对齐合法性；结构非法报错，合法未实现保留not_run。不新增回归，不把宽度水平冒充收益因子。

## Task 4：让验收证据不可空转

Files：runner.py、集成测试、手册和本轮报告。

- [ ] 空期望集合不能all_passed成功；冻结每例必需检查ID与独立期望来源，删检查必须拒绝。容差非负有限且有固定允许值，不能用无穷容差放行。
- [ ] 修复状态案例不同对象检查点覆盖的风险，B50/B200分别用对象ID命名，不让后算覆盖前算。输出JSON拒绝NaN/Infinity，缺失写null与原因。
- [ ] 捕获InsufficientDataError为2并落原因，使用真实缺数据输入验证，不模拟抛异常作为唯一证据。写盘失败不得留下“已完成”的manifest。
- [ ] 统一保存计算批次metadata/findings、协议副本、输入和产物哈希，逐项能追溯；不将每行元数据重复撑大CSV。执行模型如实声明，删除硬编码GLM身份。
- [ ] 全部局部测试及第一次相关回归通过后冻结新代码/协议，再一次运行三个正式合成案例；任何纠错产生新版本，不覆盖原件。

验证命令：

```sh
python3 -m pytest tests/unit/test_factor_lab_contracts.py tests/unit/test_factor_lab_adapters.py tests/unit/test_factor_lab_diagnostics.py tests/unit/test_factor_lab_validation.py tests/unit/test_factor_lab_attribution.py tests/integration/test_factor_lab_cli.py -q
ruff check src/lei_signal/research/factor_lab scripts/run_factor_lab.py tests/unit/test_factor_lab_contracts.py tests/unit/test_factor_lab_adapters.py tests/unit/test_factor_lab_diagnostics.py tests/unit/test_factor_lab_validation.py tests/unit/test_factor_lab_attribution.py tests/integration/test_factor_lab_cli.py
```

完整相关回归沿原报告日志中的准确15文件集合，加本轮新测试；运行前把具体命令冻结在本轮协议，不用测试数量作为通过标准。

## Task 5：统一交付，完成即停

- [ ] 报告R1–R4逐项旧失败/新通过/合法控制结果、每个正式运行实际次数、保护文件逐项差异、文件修改清单、版本指纹和仍未接入项。
- [ ] 原执行报告追加主控纠正指针；registry/INDEX登记新报告mixed，不写“算法全部正确”。OKR只给主控证据建议，不写或勾完成。
- [ ] 提交待复核：回答计算能否复算、时间资格是否实际消费、未知合同是否降级、是否有真实因子有效性、是否有交易授权。后两项仍为无。

本轮不顺带做Alphalens、统计显著性、真实市场试验或新数据获取。返修通过后再另发工具复用任务；不因发现范围外问题无限开工。
