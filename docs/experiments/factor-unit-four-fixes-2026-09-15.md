# 双均线B0剩余四项限定修复-2026-09-15

```text
【来源：执行agent交付，用户仅转交】
以下完成声明与建议均由执行agent撰写，尚待主控独立核验。
不代表用户意见、主控认可或新增授权。
请主控分别记录：执行者声明 / 主控验证 / 待用户决定。
```

规范版本：`experiment-backtest-principles.md` v1.1 / `definition-standard.md` 1.1.0 /
`ai-execution-contract.md` 1.0.1 / `experiment-report-template.md` 1.1.0。
任务书：`docs/superpowers/plans/2026-09-15-factor-unit-four-fixes-glm.md` v1.0.0；
主控依据：[factor-unit-b0-fix-controller-review-2026-09-15.md](factor-unit-b0-fix-controller-review-2026-09-15.md) v1.0.0（§4 四项暂停项）。
执行目录 `/Users/yongbiaoli/Desktop/lei-signal-lab`；分支 `codex/factor-unit-research-20260915`；
HEAD 全程 `8ba16576b75e605aa1b0d0902568c760c4b99095`（未移动、未提交、未暂存、未切分支）。
登记表 `docs/research/definitions.v1.json` 全程只读，未新建登记对象。

定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：
explicit（对象与公式不变）/ 四真实输入仍为 producer_candidate_only（如实）/
108 项测试 + 主控四反例先行固化 / **无（零真实因子—目标统计）** / **not_authorized**。

## 一句话结论（大白话）

主控上轮挑出的四个口子这次都按任务书堵上了：**资格检查不再认"自己填的声明"**——
没有供应商原件，把合同、证据、来源表一起改成高档位也升不了含分红目标的资格，
而且真实目标这一轮一律保持"不批准、需人工复核"；**稀疏观察不再偷看未来**——
它和主统计用同一批"状态已知、目标合法、已成熟"的样本，截止时间之前的未来收益
不再展示也不再计数；**上游状态列的缺失值（pd.NA）可以直接接进统计**，不再报错，
但字符串 false、数字 0/1/2 照样拒绝；**打包不再漏证据**——合同引用的每份价格证据
原件随包保存，旧真实包另做了补件，恢复演练在临时目录只核对了文件身份，没有重跑
任何真实计算。要强调：这是**研究接口的修复，不是因子有效的证据**；真实目标仍未
批准，B1 未启动，本轮零联网。

## 1. 决策问题与停止条件

- 任务类型：方法论与验证（研究接口纠错），不是收益研究；资金用途/持有周期：不适用。
- 本轮要改变的决策：是否恢复 describe_states 作为可接入研究消费者、终包是否可称
  依赖闭合并归档；不改变任何交易条件、不调参、不扩因子体系。
- 通过条件（任务书给定）：四反例反转且合法合成正例仍可通过；真实资格 0 次运行。
- 停止条件：预算不足或出现四项外新问题即停——未触发；四项外观察见 §7。

## 2. 修前复现（红）→ 修复 → 修后（绿）

修前证据：`raw/factor-unit-four-fixes-2026-09-15/red-before-fix.log`
（新四项测试 16 failed / 3 passed——3 项通过者是"防过度拒绝"的守卫测试，修前本就该过）。
修后证据：同目录 `green-after-fix.log`（19 passed）、`regression-run-01.log`、
`regression-run-02-final.log`（108 passed, 1 skipped；skip 为 close_state 分红消费
未实现的既有跳过）、`ruff-02.log`（All checks passed）。

### Task 1：禁止自填证据升级真实含分红资格

| 主控反例（§4 P1） | 修后行为（执行者声明，待主控核验） |
|---|---|
| 合同/证据/CSV 一致自填 `snapshot_provenance_bound`，无供应商原件 | `status=restricted`、`target=blocked`，reasons 注明 `manual_target_review_required`——快照溯源只证明"能追到供应商调整价的生成过程"，不等于"已核含分红财富构造"（`test_forged_snapshot_provenance_bound_not_qualified`） |
| `price_basis_verified` + `vendor_traceable=true` + 指向不存在文件的 `vendor_response_ref` | ValueError 拒绝：被消费的供应商引用必须结构化 `{path,sha256}`、文件存在、指纹一致（`test_forged_price_basis_verified_fake_vendor_rejected`、`test_structured_vendor_ref_nonexistent_file_rejected`） |
| （新增覆盖）供应商记录错绑输入、缺请求参数/价格语义、证据记录重复、CSV 行重复、sha256_16 前缀 | 全部 ValueError；CSV 必须完整 sha256 精确相等、每 symbol 唯一（`test_vendor_record_*`、`test_conflicting_duplicate_*`、`test_duplicate_source_decision_*`、`test_sha256_16_*`） |
| 合法供应商原件身份一致但含分红构造未核 | 仍 `restricted/blocked`；notes 只写"来源检查完成……目标仍未批准"，不称资格齐备（`test_valid_vendor_material_still_not_total_return_qualified`） |
| 合法合成正例（守卫，不得一律拒绝） | 仍 `status=ok`、全部 `pending_controller_freeze`（`test_legal_synthetic_positive_still_passes`） |

代码位置：`study_contract.py` 真实分支——移除了把 `snapshot_provenance_bound`
直接列为含分红目标合格的旧分支；真实模式（含分红与替代目标）本轮一律
`target=blocked` 并注明 `manual_target_review_required`，**没有新增自行批准真实
目标的开关**。独立期望对账：无供应商原件的真实正向资格数=0 ✓；合法合成正例数>0 ✓；
含分红目标不能仅凭供应商调整价声明通过 ✓。

### Task 2：稀疏结果也遵守同一合法集合

| 主控反例（§4 P1） | 修后行为 |
|---|---|
| 50 日合成递增、截止 2019/资料 2020：`comparison.n=0` 但 `true_slots_up=2`、slots 展示未来变化 | 两者都为 0；三格全部 `skipped=true`、`main/aux=null`、`skipped_reason=not_mature/tail_immature`（`test_sparse_cannot_see_future`，按任务书给定断言原样固化） |

稀疏格点从合同锚点每 23 格取（不动态选锚），每格用与主比较**完全相同**的
"状态已知∧主目标合法∧成熟∧在评价期内"判定，没有第二套放宽条件；不合格格保留
日期与 `skipped_reason`（missing_row/tail_immature/e_missing/x_missing/not_mature/
state_unknown），不计 `true_slots_up/false_slots_down`；辅助路径不全但主目标合法时
主值保留，aux 缺失由稀疏 `aux_n` 独立表达。正向对照（同一夹具截止 2030）：第 0/23
格有效且两个上涨计数保留（0.2079…/0.1694…手算核对），第 46 格 `tail_immature` 跳过
（`test_sparse_positive_control_cutoff_2030`）；未知状态格不展示不计数
（`test_sparse_unknown_state_slot_not_counted`）；0/负/1/24 步长继续拒绝、锚点固定
（既有测试保持绿）。

### Task 3：支持上游 pd.NA，不放宽非法状态

- 上游 `compute_close_state` 的可空布尔列（pd.BooleanDtype）原样接入
  `describe_states`：pd.NA/None/NaN 统一为未知；有效状态仍只接受 bool/np.bool_；
  字符串 false、空串、数字 0/1/2 拒绝（`test_string_and_numeric_states_still_rejected`）。
- 真实接口格式合成对照：close=`[100]*20 + range(101,131)` 50 行，state 列原样传入
  （不人工换 None、不复制公式）。手算期望：第 0—19 行未知（unknown=20）、第 20—27
  行状态 true 且 21 间隔标签完整 → `comparison.n=8`、真假对账 8+0=8、余行标签不足
  （`test_nullable_boolean_pipeline_hand_computed`）。全 pd.NA（unknown=50, n=0）与
  混合 bool/NA/None/NaN（unknown=30）另有独立用例。
- `close_state.py` 未改（SHA 复算一致，见 §5）。

### Task 4：补全价格证据依赖，不重跑真实资格

- CLI 新行为：合同直接引用的每份 `price_basis_evidence` 原字节入包（`evidence/`，
  相对路径改名避免同名碰撞）；消费到 `vendor_response_ref` 时同样保存原件；应包含
  依赖集合从合同与实际消费清单**预先推导**，`manifest.dependency_closure` 与实际归档
  双向核对（缺失/错哈希在合同校验阶段拒绝，不默默漏包）。
- 正式合成正包 `raw/.../final-synthetic-positive-01/`：exit 0、`package_completed=true`、
  `qualification_status=ok`、证据原件在包、闭包双向差为空、冻结 CLI 字节=定稿（纠错后
  重打，见 §6 记账）。正式合成负例（必需键哈希清零）exit 3，未产包。
- 旧真实终包保持原样（SHA 复算 219 项保护文件零变化）。补件 `raw/.../supplement/`：
  旧合同副本 + 缺失的 `real-evidence.json` 原件 + 旧包 manifest 副本 + mapping.json +
  README；证据哈希与旧合同引用逐一核对一致（934c84d6…）；README 标明"为旧运行补齐
  证据，不代表新代码重新执行过"；外部输入依赖（4 份真实 parquet、CN 日历、来源裁定
  v2 CSV，路径+哈希）显式列出——恢复级别是"代码/证据包+声明的外部输入"，**不是**
  无任何外部依赖的一包复放。
- 恢复演练 `restore_drill.py`：临时目录布局，旧包 22 项已列文件身份一致、4 产品证据
  补件哈希==旧合同引用、6 项外部输入身份一致、mapping 3 项一致；未调用真实运行入口，
  仓库原件零改动。**真实资格检查本轮 0 次运行**，旧真实包未重跑。

## 3. 对照设计

纯接口核验，账户比较与三层归因不适用（未检验收益）。固定不变：对象
`candidate:lei.dual_ma.bull_state@draft-1`、20/1/22、稀疏步长 23、close_state 公式与
源码、旧 raw/合同/包、四真实输入。本轮只改变：合同校验真实分支、稀疏格合法性判定、
状态缺失表示接入、CLI 证据归档，及以上文件的测试与说明。

## 4—5. 结果与收益解释

不适用：零真实因子/未来收益/账户计算。合成统计只用于验证代码路径（修前红/修后绿），
不构成任何市场结论。

## 6. 调用与预算记账（实际）

| 项目 | 预算 | 实际 |
|---|---|---|
| 全相关回归（任务书指定 pytest 命令） | ≤2 次 | 2 次（run-01：108 passed；run-02 定稿后终跑：108 passed, 1 skipped） |
| ruff（指定命令） | 按需 | 2 次（01：B007×2+F401；02：All checks passed） |
| 正式合成正/负 | 各 1 次 | 各 1 次（exit 0 / exit 3）+ 纠错 1 批后重打正包 1 次（ruff  lint 使首版正包冻结的 CLI 字节≠定稿；半成品目录删除后排他重建，cli-calls.log 逐次记账） |
| 纠错批 | ≤1 批 | 1 批（make_supplement.py 字典推导 NameError + ruff 3 项） |
| 真实资格检查 | 0 次 | 0 次 |
| 联网/新依赖/新资料 | 0 | 0 |
| 新四项测试文件 | 修前红/修后绿 | red 16 failed→green 19 passed |
| pytest 集成测试内 CLI 子进程 | 记账 | 每次集成测试运行 9 次子进程调用（含 /tmp、目录已存在拒绝用例），随 2 次回归共 18 次；手工 CLI 调用见 `cli-calls.log` |

## 7. 限制、反例与四项外观察（登记待决定，未自批扩建）

- `_needed_start` 仍为"评价开始减 25 自然日"近似，不代表精确 20 个交易日预热（沿
  主控 §4 补充范围限制，本轮未改）。
- 供应商原件的 JSON 结构（records/request_params/price_semantics）是本模块自定的
  消费合同，尚无真实供应商材料可对照；真实启用需主控任务明确冻结资料与目标。
- 四项外观察（不处理，仅登记）：`docs/experiments/registry.json` 解析方
  `experiment_reports._load_registry` 只接受 dict 形式 entries，与当前文件实际格式
  的兼容性未在本轮核验范围；INDEX/AGENTS 归档约定仍按字符串键 dict 执行。
- 本报告的"关闭"声明均为执行者声明，待主控独立复核；主控后续验收结果未被预写。

## 8. 复核与复现

- 复核性质建议：独立重算（主控 reproduce.py 原脚本未改，可重跑对照）。
- 输入/代码/产物：`src/lei_signal/research/factor_unit/{study_contract,state_description}.py`、
  `scripts/check_factor_unit_readiness.py`、四个测试文件、`docs/research/factor-unit-usage.md`；
  新 raw `docs/experiments/raw/factor-unit-four-fixes-2026-09-15/`（baseline 哈希、
  red/green/回归/ruff 日志、cli-calls.log、正式正负合同与正包、supplement、
  build/make_supplement/restore_drill 三脚本）。
- 复算入口：§2 两条任务书指定命令；`python3 docs/experiments/raw/factor-unit-four-fixes-2026-09-15/restore_drill.py`。

## 9. ARCHIVE

- 结案日期：2026-09-15（执行侧交付结案；主控复核另行记录）
- 最终结论：没有明确增量（接口修复，不声称因子有效）；真实目标仍未批准
- 生产采用：未授权；B1 未启动；零联网
- 原始数据与复现入口：`docs/experiments/raw/factor-unit-four-fixes-2026-09-15/`
- `registry.json`：已登记（category=方法论与验证，verdict=mixed）
- `INDEX.md`：已补导航

## 11. 流程偏差补充说明（2026-09-15 主控文案收尾要求追加）

- **首次成功合成包曾删除重建**：首个 exit 0 正式正包（修 lint 前打出）在 ruff 纠错后
  被删除并以同名目录 `final-synthetic-positive-01` 重建，两次完整运行均记录在
  `raw/factor-unit-four-fixes-2026-09-15/cli-calls.log`。允许纠错一次不等于允许删除
  已成功的正式证据——首次成功包的原字节**不可恢复**（当时未另存副本）；当前可核验的
  是重建后最终包的身份闭合（合同原字节、24 项文件双向哈希、冻结 CLI=定稿）。
  主控已确认不要求为此重跑补历史；下轮起使用全新编号并保留全部成功/失败目录。
- **旧原件可恢复性**：旧真实终包 `final-real-qualification-01` 及其合同、证据原件
  （real-evidence.json 等）全部原样存在且哈希复算一致，经 supplement 补件可恢复到
  「代码/证据包+声明的外部输入」级；被删除重建的只有上述首个合成正包一份。
- **纠错额度边界**：任务书的「纠错 1 批」额度用于修复已定位工程错误，不授予删除
  成功证据、重编历史或扩大修改范围的权限。本说明为事后如实记录，不改写当时日志。

## 10. 最小决策卡

| 必答项 | 本轮答案 |
|---|---|
| 决策与资金用途 | 恢复研究接口可信度（资格闸/稀疏合法集/可空布尔接入/证据闭包）；不涉及资金决策。 |
| 基准与增量 | 对照=主控四个反例+合法合成正例；固定对象/参数/公式/旧包，只改四个限定位置。 |
| 收益解释 | 不适用：零真实收益计算。 |
| 代价与执行 | 真实目标一律 blocked 的代价=真实研究继续暂停；合成链路全绿。 |
| 证据与结论 | 证据不足（对"因子有效"而言）；对"接口缺陷修复"而言四反例已反转（执行者声明，待主控核验）。 |
| 下一步与边界 | 完成即停交主控；不自动进入资料抓取或 B1；四项外问题已登记待决定；本轮用户授权不是无限返修许可。 |
