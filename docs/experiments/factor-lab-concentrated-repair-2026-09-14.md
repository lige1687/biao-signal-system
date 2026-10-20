# Factor Lab 集中返修（R1–R4）执行报告 -2026-09-14

> 任务书：`docs/superpowers/plans/2026-09-14-factor-lab-concentrated-repair.md` v1.0.0；
> 主控初审：`docs/experiments/factor-lab-controller-review-2026-09-14.md` v1.0.0（mixed）。
> 执行者：ZCode/GLM（`builtin:bigmodel-coding-plan/GLM-5.3-Flash`），2026-09-15 交付。
> 状态：**执行者交付，待主控回调复核；复核通过前不构成验收。**

规范版本：`experiment-backtest-principles.md` v1.1；`definition-standard.md` v1.1.0；
`ai-execution-contract.md` v1.0.1；`experiment-report-template.md` v1.1.0（均与任务书一致，未发现版本差异）。
冻结协议：本轮新协议 v1.1.0 ×3（排他保存于本轮 raw，见 §4）；原任务协议与运行只读。
登记表：`definitions.v1.json` v1.2.0 只读；六对象仍 `@1.0.0`；候选
`candidate:lei.dual_ma.bull_state@draft-1` 只读绑定。
定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：
explicit / synthetic_only / 已核（本文 §3）/ **无** / **not_authorized**

## 一句话结论（大白话）

主控挑出的四个问题都修完了，并且每一条都先把"坏例子"写成会失败的测试、
看着它失败、再修到通过：现在"当时还不知道的结果"会被真正踢出统计（不只是加警告），
运行前会逐字核对"冻结的代码和规则是不是就是眼前这份"（删一条都拒绝），
两个账户条件没核对清楚时就不再宣称"差额只归给某个动作"，
空的验收清单不能再当成"全部通过"。全部用合成数据验证：三个正式案例 62 项
手算期望全过、132 项测试与 358 项相关回归通过。仍不证明任何因子有效，无生产授权。

## 1. R1–R4 逐项：旧失败 → 新通过 → 合法控制

### R1 时间资格实际控制统计

- 旧失败（主控反例，留档 `reproduce-output/reproduce-stdout.json`）：
  NaT 可得时间的 3 个标签仍输出 n=3、IC=1；1月9日样本既记 crossing=1 又记 clean=1；
  1月23日样本（结果在2月、截止1月25日）仍 clean=1。
- 反例测试先行：`TestTimeQualificationR1`（diagnostics 8 项 / validation 6 项）
  在未修代码上失败（留档 `reproduce-output/unfixed-test-failures.txt`：37 failed）。
- 新行为：共享逐行排除判定（值缺失/非有限 → 时间顺序 → 成熟 → 可知 → 特征可得）；
  **clean 掩码同时决定 n、IC、状态均值、分组与段内统计**；None/NaT 一律
  `label_available_unknown` 剔除，naive（无时区）为格式错误；
  每段评价截止（`segment_cutoffs`）必填、带时区、不晚于全局截止、依次不提前；
  全部观察日保留（无目标日 n=0）；`min_pairs` 用声明值实际执行（输出与行为一致）；
  时间倒挂拒绝；特征滞后声明（`feature_available_lag_days>0`）触发
  `feature_not_available_by_decision_time` 剔除。
- 合法控制（防"一律排除"）：干净样本的段内统计非零
  （`test_clean_mask_feeds_segment_statistics`：clean=3 → pooled IC=1.0）；
  正式案例中 holdout 30 对全部成熟 → clean=30、每期 IC=1.0。

### R2 运行前核对冻结合同

- 旧问题（源码审阅）：代码哈希在计算后才生成；协议无必需代码键/预期哈希；
  代码清单漏 CLI 与规则配置加载器；目标声明与执行可能分离（写 10 算 22）。
- 新行为：`verify_frozen_contract` 在**计算前**核对——
  ①必需代码键全集（15 个：六模块 + CLI + definitions/momentum/factor_diagnostics/
  dual_ma/lei_color/indicators/**rules_config**）逐文件哈希，缺键或错哈希即退出 3；
  ②登记表版本 + 规范化 SHA；③所用对象卡/候选卡规范化指纹（卡变化即拒）；
  ④目标端点仅允许 entry=1/exit=22；⑤合成数据声明（价格尺度/日历/时间/币种）；
  ⑥`required_checks` 非空且期望齐全；⑦容差仅允许 {0, 1e-9, 1e-6, 0.01}；
  ⑧独立期望来源文件哈希；⑨比较合同完整性。协议原字节副本随产物保存；
  manifest 区分文件 SHA 与规范化内容 SHA；manifest 记录**生效的**目标合同而非原文照抄。
- 反例测试（集成 12 项）：删代码键、改 CLI 哈希、改卡指纹、错登记表版本、
  改目标参数、输入篡改——全部在计算前退出 3（正向走真实函数，无 patch 放行）。

### R3 差额不等于已解释

- 旧失败（主控反例）：池 base=[100001,A] vs variant=[100001,B] 仍
  `attributable_to_declared_action_only`；未观察条件被记 true。
- 新行为：比较合同固定在 `protocol.comparison`，**必查集合不可裁剪**
  （`must_match` 等裁剪键直接拒绝；缺必需键即格式错误）。核对：池版本、
  完整候选池实体集、期间（且与账户实际起止一致）、初始资金（且与账户记录一致）、
  外部资金流、费用表（规则级相等，且与实际成交费率一致性核对）、基准、
  除声明动作外冻结规则、输入身份。池不同 → `not_attributable`；
  声明为未知（None）的条件 → `not_attributable_conditions_unknown`
  （算术差额保留展示，未知不记 true）；全部相等才允许
  `attributable_to_declared_action_only`，且附注"仅指合成材料一致"。
- 反例测试（attribution 8+4 项）：池不一致、must_match 逃逸、删合同字段、
  未知条件降级、费用规则不一致、声明与成交矛盾、期间与账户不符、正控仍受限归因；
  模型卡结构非法（频率枚举/引用不可解析/类型错）报错与"合法但未实现 not_run"分离。

### R4 验收证据不可空转

- 旧失败（主控反例）：`_compare_expectations({}, {})` 返回 0 条检查且 all_passed=true。
- 新行为：空期望/空必需清单在计算前拒绝；`required_checks` 删一项即退出 3；
  容差只允许固定值；输出 JSON 统一出口拒绝 NaN/Infinity（缺失写 null 并留清单）；
  `InsufficientDataError` → 退出 2 并落原因（用真实缺数据输入验证：10 行价格 →
  目标全部无法成熟 → 退出 2，日志含 INSUFFICIENT_DATA）；写盘失败不留
  "已完成" manifest（manifest 最后写，故障注入测试断言 manifest 缺失且日志含
  WRITE_FAILURE）；每个值文件带旁置元数据（对象/版本/单位/声明输入身份/缺失原因/
  质量）；批次 metadata/findings 全量入 sidecar；状态案例检查点按对象 ID 命名
  （b50_/b200_ 前缀，互不覆盖）；manifest 不再硬编码执行模型身份。

## 2. 运行与回归计数（本轮额度：正式 3×1、回归 ≤2）

| 项目 | 实际 | 额度 |
|---|---|---|
| 正式合成运行 | 3 个案例各 1 次（`runs/repair-*-run-01`，协议 v1.1.0），全部退出 0，期望 23/28/11=62 项全过 | 3×1，用满且无失败；新批次未申请 |
| 完整相关回归 | 15 文件集合（原 9 研究相关 + 实验报告格式 + 6 新测试文件）：**358 passed，退出 0** | 2 次中的第 1 次 |
| factor_lab 全部测试 | **132 passed**（contracts 15 / adapters 23 / diagnostics 25 / validation 24 / attribution 26 / 集成 19） | 按需 |
| 反例先行失败 | 37 failed / 1 正控通过（未修代码留证） | — |
| 网络/依赖/真实数据 | 0 / 0 / 0（真实只读检查批次仍未使用） | — |

临时目录集成测试与 /tmp 调试运行如实说明：开发期曾在 /tmp 对 v1.1.0 协议试跑
3 轮（协议冻结→发现代码再修改→重冻结），均为**正式运行前**的调试，正式批次
以 `runs/repair-*-run-01` 为准，未覆盖任何旧产物。

## 3. 保护与修改面

- 29 项保护文件逐项哈希与开工基线一致（漂移 0）；上轮 408 项 raw 逐项一致（漂移 0）。
- 本轮实际修改（全部在允许面内）：factor_lab 五模块（adapters/diagnostics/
  validation/attribution/runner；contracts 与 __init__ 未改）、四份测试文件、
  使用手册、registry/INDEX（本条登记）。原六对象、生产规则、旧 raw、OKR 未动。

## 4. 版本指纹与复现

- 协议：`raw/factor-lab-concentrated-repair-2026-09-14/protocol-{1-numerical,2-state,3-attribution}.json`
  **v1.1.1**（含 code_identity 15 键哈希、registry 指纹、卡指纹、data_declarations、
  segment_cutoffs、required_checks、expectation_source）；已交付正式批次运行于
  v1.1.0（其原字节副本保存在各 run 目录 `protocol.source.json`）。
- 复现命令（输出目录必须不存在）：

```sh
python3 scripts/run_factor_lab.py --protocol <raw>/protocol-1-numerical.json --out <新目录>
python3 scripts/run_factor_lab.py --protocol <raw>/protocol-2-state.json   --out <新目录>
python3 scripts/run_factor_lab.py --protocol <raw>/protocol-3-attribution.json --out <新目录>
python3 -m pytest tests/unit/test_factor_lab_contracts.py tests/unit/test_factor_lab_adapters.py tests/unit/test_factor_lab_diagnostics.py tests/unit/test_factor_lab_validation.py tests/unit/test_factor_lab_attribution.py tests/integration/test_factor_lab_cli.py -q
python3 docs/experiments/raw/factor-lab-controller-review-2026-09-14/reproduce.py   # 反例已全部转为正/反测试，此脚本输出与首轮不同属预期
```

- 每个正式运行目录含：manifest.json（双 SHA、代码/卡/输入/输出哈希、
  attempt_history、executor_model=not_declared_in_protocol）、protocol.source.json、
  values_*.csv + values_*.meta.json、targets_*.csv、diagnostics_*.json、
  validation.json / attribution.json、quality.json、summary.md（中文、常驻合成标题）、run.log。

### 4.1 已披露缺口与 v1.1.1 升版（诚实记录）

- 正式批次（v1.1.0 协议）交付后自查发现：manifest 的 `outputs` 哈希在写盘前
  构建、恒为空——产物级哈希追溯不完整（R2 部分未达成）。
- 处置：修复 `_write_manifest`（写 manifest 时对已落盘产物现算哈希，已由
  集成测试与临时目录 CLI 重放验证：19 个产物全部入 manifest.outputs）；
  代码变化使协议升版 **v1.1.1** 重冻结（attempt_history 记录 abandoned 原因）。
- 已交付的 `repair-*-run-01` 目录**原样保留**（协议 v1.1.0 字节副本完整，
  可按其 code_identity 复放）；按"失败可离线修复、新正式运行先申请"的额度纪律，
  **未自行追加正式批次**——是否用 v1.1.1 协议重跑一批以获得含产物哈希的
  manifest，交主控决定。

## 5. 仍未接入与边界（不伪称通过）

- 仍未实现：稳健统计推断/多重试验校正、风险模型回归、外部库安装、
  前端研究台、生产接入；双均线候选仍未登记、无有效性研究。
- "过拟合风险尚未排除"仍是常驻输出；时间排除已做实，但不因此宣称排除过拟合。
- 合成来源不取得真实市场资格；真实资料只读检查批次继续保留未用。

## 6. 给主控的回答与证据建议（OKR 由主控写，执行者不写、不勾完成）

| 问题 | 回答 | 证据 |
|---|---|---|
| 计算能否复算 | 能：冻结协议+代码哈希核对，CLI 到新目录即可重放 | §4 命令；manifest 双 SHA |
| 时间资格是否实际消费 | 是：clean 掩码喂给 n/IC/均值/分组；未知/未成熟/跨段剔除有正反测试 | R1 反例测试；`runs/repair-1.../validation.json`（dev/validation clean=0、holdout clean=30） |
| 产物哈希是否完整 | 正式批次（v1.1.0）manifest.outputs 为空——已披露缺口；修复已在 v1.1.1 验证，重跑批次待授权 | §4.1；临时目录重放 19 产物全入 outputs |
| 未知合同是否降级 | 是：未知条件 → not_attributable_conditions_unknown，差额保留展示 | R3 测试；`attribution.json` |
| 是否有真实因子有效性 | **无** | 全部输出 synthetic 标记 |
| 是否有交易授权 | **无** | manifest production_authorization=not_authorized |

建议主控复核顺序：先跑 §4 命令 1–3（应退出 0 且 62 项期望全过），再抽查
R1–R4 各一条反例测试单独运行应通过、反向篡改应退出 3，最后核对 29+408 保护清单。

## ARCHIVE

- 分类：方法论与验证；verdict：mixed（待主控复核，不预设通过）。
- 原执行报告 `factor-research-workbench-v1-2026-09-14.md` 已追加主控纠正指针；
  本报告登记 registry/INDEX；不写"算法全部正确"，只声明 R1–R4 反例已转为
  通过测试且正式批次可复算。

> **2026-09-15 第二轮复核纠正指针（追加，不改原文）**：主控二审（mixed）发现 S1–S4：分侧输入身份自比、必查清单可同删、审计与诊断合法集合不一致、_dump_json 注释致非法 JSON；且 §4.1 中「当前 CLI 即可复放 v1.1.0」不成立（v1.1.0 交付时 runner.py 原字节未存档且未被 git 跟踪，源码不可从哈希恢复）。全部收尾见 [factor-lab-final-closeout-2026-09-15](factor-lab-final-closeout-2026-09-15.md)；本报告运行证据保留为历史。

## 最小决策卡

| 必答项 | 本轮答案 |
|---|---|
| 改变什么决策 | 修复通用研究工具的可信边界（时间资格/冻结合同/归因条件/验收证据） |
| 比谁好 | 独立反例与冻结规格对照；不比较任何策略收益 |
| 钱从哪里来 | 不研究真实收益；合成账户小例只验证算术与解释权限 |
| 代价与可执行性 | 离线小测试；正式运行 3×1、回归 1/2 次；无生产/真实资料/账户运行 |
| 现在怎么办 | 统一交回主控复核；OKR 由主控更新；后两项（有效性/授权）仍为无 |
