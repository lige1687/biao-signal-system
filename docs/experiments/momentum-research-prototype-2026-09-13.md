# 已有动量指标研究样板：执行报告（momentum-research-prototype-2026-09-13）

任务书：[2026-09-13-momentum-research-prototype.md](../superpowers/plans/2026-09-13-momentum-research-prototype.md) v1.0.0。
冻结协议（现行）：[protocol.json](raw/research-momentum-prototype-2026-09-13/protocol.json) v1.0.3
（sha256 见 §11 修订记录）；历史版本 v1.0.0/v1.0.1/v1.0.2 原件保留于
`raw/research-momentum-prototype-2026-09-13/protocol-v1.0.*.json`。
研究原则 v1.1 / 定义标准 1.1.0 / 执行合同 1.0.1 / 报告模板 1.1.0；
本轮执行前实哈希与协议 `specs` 一致（权威文件哈希见 §8）。
**2026-09-13 两轮集中返修后更新：A–D 见 §11（协议 v1.0.3），R1/R2 见 §12
（现行协议 v1.0.4）；§1–10 保留初版历史，与 §11/§12 冲突之处以后者为准。**

## 一句话结论（大白话）

**这一轮把一个已经在册的 ETF 动量指标做成了"算得对、可复算、缺资料会明说"的
样板：用完全虚构的数据把全部计算从头到尾跑通；用真实冻结数据算出了被允许的
历史动量值（14 只产品、82 个月末观察日、772 个数值），每一个数值都能用两条
独立算法在亿万分之一误差内复算出相同结果；真实数据的"预测研究"按规矩被拒绝，
因为没有资格资料。这不代表这个指标能预测涨跌，也不授权任何真实交易。**

三种结果明确分开：①合成例能算（算法和时间安排正确）；②真实重建能复算
（历史数值诊断通过）；③真实预测被拒绝（资格不够，未运行）。

## 1. 决策问题与停止条件

- 本轮不改变任何交易决策：不动道路/路牌/触发/过滤纪律，不新增因子对象，
  不接账户，不进 OKR。
- 本轮要回答的是工程问题：这个已登记指标的计算、时间安排、缺失处理和
  资格检查能否做到"输入可追溯、数值可复算、资料不足会明确停止"。
- 停止条件（任务书事先指定）：真实资料资格不够就拒绝预测研究并输出原因；
  不删产品、不缩短区间、不用宽松开关绕过。

## 2. 冻结范围与当时可知的信息

| 项目 | 冻结内容 |
|---|---|
| 对象 | `mixed.momentum.raw@1.0.0`（feature，描述数值），依赖 `mixed.price.economic@1.0.0`；完整解析卡与递归依赖见协议 `objects.cards` |
| 公式 | `M(t)=I(t−21)/I(t−252)−1`，偏移按产品自身有效报价位置；首次需 253 条 |
| 观察目标 | `protocol:momentum-next-close-21-session@1.0.0`（协议测量项，非登记表对象）：e 为 t 后第一个交易日、x 为 e 后第 21 个交易日，`Y(t)=I(x)/I(e)−1`；端点须实际有效报价，缺即缺失不顺延 |
| 数据 | 冻结输入：canonical-snapshot-v2 / calendar-merged / publication-evidence / normalized-actions（哈希核对一致；14 只、18,916 行） |
| 评价区间 | 2019-09-02 ~ 2026-06-30；观察日为已核日历中各完整月份最后交易日 |
| 统计口径 | 并列平均名次的 Spearman 等价；少于 3 个配对或名次全同返回缺失；不做分组、不做显著性声明 |
| 时间语义 | 真实行动均无 `available_at`（20 条），全部只能事后重建
（`historical_reconstruction_only=true`），不冒充历史可知输入 |
| 尝试史 | 见 §6 尝试史 |

## 3. 对照设计

本轮是方法论验证，不是收益实验：对照为"同一输入下的独立复算"，不是策略
对照。无资金账户计算，`policy = not_applicable_no_account_policy`，不存在
已运行的政策卡；资金归因/费用/政策增量不适用，也未运行回归凑数。

## 4. 结果（三种结果分开陈述）

### 4.1 合成闭环（synthetic=true）

- 5 个明确虚构产品、14 个人工月、约 281 个合成交易日，含现金分红、1拆2、
  同日拆分+分红、月中缺报价、月末缺报价、不足预热（SYN.E 全程缺失）。
- 完整跑通经济指数重建 → 动量 → 未来目标（70 行）→ 逐期排序诊断
  （14 期，其中 2024-12 期末 4 个配对有数值；此后期间因日历末端不足按
  `future_incomplete` 缺失）。
- 修复一处夹具经济含义错误：拆分/分红曾只改事件当日价格（次日假跳空），
  已改为"拆分后所有后续价格按比例缩减、分红后永久降低"；修后各产品动量
  回到同量级（0.16~0.19），证伪路径保留在测试与冒烟记录中。
- 产物：`/tmp` 冒烟目录（不入库）；断网守卫自证、manifest 输出哈希核对由
  集成测试 `test_synthetic_mode_completes_with_full_contract` 等锁定。

### 4.2 真实历史数值诊断（被允许的部分，正式运行一次）

- 运行：`run-04`（[manifest](raw/research-momentum-prototype-2026-09-13/run-04/manifest.json)），
  退出码 0。
- 用途检查（[quality.json](raw/research-momentum-prototype-2026-09-13/run-04/quality.json)）：
  description 可用；ranking / research_signal 不可用（另有四项用途未请求）。
  描述允许不替代预测分析——qualified-research 单独拒绝（§4.3）。
- 数值：772 个动量值（[values.csv](raw/research-momentum-prototype-2026-09-13/run-04/values.csv)）；
  缺失 376 条，原因逐条可查（[missing.csv](raw/research-momentum-prototype-2026-09-13/run-04/missing.csv)）：
  170 条不足预热（该日有效报价不足 253 条）、206 条观察日当日无报价行。
  无报价的具体原因按证据逐条确定：原始行动文件只登记了 1 条停牌，故
  206 条中仅个别可归因停牌，其余与进场时点有关但**缺上市资格证据，不
  定性为"晚上市"**。
- 原始行动记录共 21 条：20 条分红/拆分经逐记录核验后进入经济指数重建，
  1 条停牌只做缺口解释不进入指数；20 条分红/拆分均无 `available_at`，
  如实上报于 manifest `unknown_available_at`，未用本次生成时刻顶替。
- 按协议，历史诊断模式不写真实 targets/rank 结果
  （[skipped-stages.json](raw/research-momentum-prototype-2026-09-13/run-04/skipped-stages.json)）。

### 4.3 真实预测研究：按资格拒绝（退出码 2）

- 运行：`run-05`，退出码 2，未写任何真实 targets/rank 数值。
- 拒绝原因（[skipped-stages.json](raw/research-momentum-prototype-2026-09-13/run-05/skipped-stages.json)）：
  排序与研究信号用途未获允许（多只产品首报价晚于评价期起点、缺上市资格
  证据，`starts_after_window`）；对象字段检查不满足（快照缺
  `economic_index` 字段，[quality.json](raw/research-momentum-prototype-2026-09-13/run-05/quality.json)）。
  未通过把用途改成 description 之类方式绕过。

### 4.4 独立逐值比对（[run-06](raw/research-momentum-prototype-2026-09-13/run-06/summary.json)）

- 全量批量核对：15,388 行有效动量，冻结引擎既有表达式与直接位置公式
  最大绝对差 **0.0**（容差 1e-12）。
- 选类逐值：94 行（普通月末首/中/末、253 边界、273 边界、每个分红/拆分
  行动前后、缺报价前后），80 行核对一致、14 行"类别不存在"（如无 273
  边界月，如实记录）、0 行不一致。每行列出产品、日期、t−21/t−252 两个
  实际端点、区间内行动 ID、原值/两条复算值/差值/结论
  （[comparison.csv](raw/research-momentum-prototype-2026-09-13/run-06/comparison.csv)）。

## 5. 收益、风险与代价解释

不适用：本轮没有计算账户收益或策略表现（动量数值与合成未来目标本身是
价格或经济指数的变化比例，不是钱）；没有账户路径。动量数值是描述性
feature 值，不是可投资的因子收益组合。有效性（`validity`）本轮
未测试；生产（`production`）未授权；不声称任何独特 alpha 或策略改善。

## 6. 尝试史与错误记录（保留失败，不掩饰）

| 运行/事件 | 结果 | 处置 |
|---|---|---|
| run-03（第一次真实历史诊断） | **作废**：行动记录用裸码（如 `510300`），当时身份映射只认带后缀写法，20 条分红/拆分全部未挂接，经济指数在无调整下错误重建，`unknown_available_at` 被错报为 0 | [INVALID-README](raw/research-momentum-prototype-2026-09-13/run-03/INVALID-README.md) 保留存档；修复后按任务书允许复跑一次（run-04） |
| 协议 v1.0.0 → v1.0.1 | `validate_sessions` 曾静默排序（掩盖乱序输入）；测试参数笔误 | 按协议规则出新版本并记录影响；v1.0.0 原件保留 |
| 协议 v1.0.1 → v1.0.2 | 新增 `adapt_company_events` 字段适配（`cash_per_unit`→`cash`、`ex_date` 回退、停牌不进指数） | v1.0.1 原件保留；影响记录见协议 `revisions` |
| 夹具经济含义缺陷 | 拆分/分红只改当日价格制造假跳空（SYN.C/D 动量虚高至 1.36） | 修正为持续缩减/降低；修前数值不留档（仅冒烟） |

## 7. 真实资金可执行性

不适用。本轮无资金、无交易、无费用模型；`production_authorized=false`；
不构成冻结观察或生产采用建议。旧 v0/生产/UI 均未接入本样板。

## 8. 限制、复核与复现

### 8.1 权威文件与身份

| 文件 | SHA-256 |
|---|---|
| 交易规格 `docs/trading-spec-v1.md` | `dd75d70cd22b103e815d3b314b47c36731230aa268d05e42fa447ba55e639798` |
| 研究原则 v1.1 | `ac5a676c0635441b66f656c8e1249b69bade36365cc9065ed6341a610b6a53c6` |
| 定义标准 1.1.0 | `3406feaea2bbb8d23a91ddc8fa0c85e62ff86437bdf443d459f2c97b0e99cd5c` |
| 执行合同 1.0.1 | `deab6c1ca20505f92d06516ffff943b8501fff2e01f8c6b3928c6626072af962` |
| 报告模板 1.1.0 | `cae2853f81841de6f424c6bda10e6708dd35574ebb8a325088fe507c5755d54e` |
| 唯一定义登记表 | `c008efb991c40f06bb7fe0236b0892a6902c68a83cb4657ae5c2651e9d270e05` |
| 本任务书 v1.0.0 | `230f801b9ce012377f5f945537f08d0a804a6bbcfd79fa83067a268abd3a55c9` |
| 冻结协议 v1.0.2 | `329666ff8b86fc4a58055fdc47a6927325a71ac7b50dc75a2baa7d0c4daa35de` |

git HEAD `8ba16576b75e605aa1b0d0902568c760c4b99095`（分离 HEAD）；Python 3.11.7；
零新增依赖、零网络请求（断网守卫自证拦截后才运行）。

### 8.2 新增/修改文件指纹

| 文件 | SHA-256 |
|---|---|
| `src/lei_signal/research/momentum_prototype.py` | `02366b5c8b683035e431a97c7ade3afbd8520a63f993860b6f953d1c3f0277c8` |
| `scripts/run_momentum_research_prototype.py` | `65b932d662273282cda33268037338ad98772aac95b63a68f6f8d74fba48b0b3` |
| `tests/unit/test_momentum_prototype.py` | `1ae4cde72dcef7580fa5ddca4b9592e3d0f31898e463c142e0053b40fdcf06de` |
| `tests/integration/test_momentum_prototype_cli.py` | `d0f88066423db117ec5ebca182a5201df34697dc0bd3b42da45afbd5b9528351` |
| `tests/unit/test_research_input_preflight_fix.py`（Task 1 增补） | `238ea6e1e082086ae3986665ecdda1b0eeaabddcd2d25777a52361118f4910a1` |
| `scripts/check_research_input.py`（Task 1 收尾） | `6b3f3d480963a15835756933f18b0ce7cc43aa4f116d318d285cc8074003534b` |
| `run-04/values.csv` | `0db2492a11372fae827465debcddf81e25b0016ea4fd219be6f0894cf471a0b5` |
| `run-04/manifest.json` | `7241de4a4f2edbeff6eb0d1a9da92036087d95509ef630b9cd49151b4a602818` |
| `run-06/comparison.csv` | `7d0b27870adc89c37ca8894e737d04046c3ee018358c8d6bb88f24ddbdda5331` |

### 8.3 实际命令与日志

```sh
# Task 1 局部测试（2026-09-13 下午阶段日志 run-02/task4-tests.log 末次实跑 59 项；
# 该日志不再覆盖，其后新增断言在返修后新日志中单独实报）
python3 -m pytest tests/unit/test_momentum_prototype.py \
  tests/unit/test_research_input_preflight_fix.py \
  tests/integration/test_research_input_preflight_cli.py -q
# 正式真实运行（各一次；<RAW> = docs/experiments/raw/research-momentum-prototype-2026-09-13）
python3 scripts/run_momentum_research_prototype.py \
  --protocol ${RAW}/protocol.json \
  --mode historical-diagnostic --out ${RAW}/run-04            # exit 0
python3 scripts/run_momentum_research_prototype.py \
  --protocol ${RAW}/protocol.json \
  --mode qualified-research --out ${RAW}/run-05               # exit 2（拒绝）
# 独立逐值比对（v1，已被 v2 取代；产物封存于 run-06）
python3 ${RAW}/run-06/compare_values.py
# 完整回归（实跑 346 passed in 41.42s，退出 0；日志 run-02/full-regression.log）
python3 -m pytest tests/unit/test_controller_fixes.py \
  tests/unit/test_controller_fixes_round2.py tests/unit/test_controller_fixes_round3.py \
  tests/unit/test_controller_fixes_round4.py tests/integration/test_controller_fixes_cross_module.py \
  tests/unit/test_research_data_quality.py tests/unit/test_research_data_snapshot.py \
  tests/unit/test_research_calendar_and_identity.py tests/integration/test_research_offline_loop_round2.py \
  tests/integration/test_research_data_snapshot_cli.py tests/unit/test_research_definitions.py \
  tests/unit/test_factor_runtime.py tests/unit/test_factor_diagnostics.py \
  tests/unit/test_factor_account_adapter.py tests/unit/test_experiment_reports.py \
  tests/unit/test_research_input_preflight.py tests/integration/test_research_input_preflight_cli.py \
  tests/unit/test_research_input_preflight_fix.py \
  tests/unit/test_momentum_prototype.py tests/integration/test_momentum_prototype_cli.py -q
```

日志：`raw/research-momentum-prototype-2026-09-13/run-02/full-regression.log`、
`run-02/task4-tests.log`（阶段日志，末次实跑 59 项，保留不覆盖）、
`run-02/ruff.log`。返修轮（§11）的新命令与日志见该节，实际计数单独实报。

### 8.4 保护核对

- 原 896 项受保护基线
  （[protected-baseline.json](raw/research-data-provenance-round2-2026-09-10/protected-baseline.json)）
  逐文件 SHA-256 复算：**变化 0、缺失 0**。
- 完整回归 346 项通过；Task 1 输出失败矩阵（JSON/Markdown/manifest/mkdir
  四类模拟失败 + `--protocol` 缺失/正确正反例）在
  `tests/unit/test_research_input_preflight_fix.py` 固化。
- 未修改：底层质量/快照/日历/身份/定义/因子运行时、账户适配、v0、生产、
  API、UI、规则账本、OKR。工作区内他人未提交改动未触碰、未提交 git。

### 8.5 尚余限制（如实列出）

- 真实预测研究仍被拒：缺上市资格证据（首报价≠上市日）、排序/研究信号用途
  未获允许、快照无 `economic_index` 字段、20 条行动无历史可得时点。
  下一件最能改变判断的资料：各产品的上市公告/成立公告证据与行动可得时点。
- 真实 `unknown_available_at`=20 意味着本轮经济指数只能事后重建；
  即使将来用途放行，预测研究还需逐时点可得性证据。
- 合成例只有 1 期排序诊断有数值（14 个月窗口减去 253 条预热后的算术结果），
  这是窗口长度使然，不是缺陷；延长合成窗口即可多期，但本轮按任务书固定
  14 个月。
- `select_mixed` 的 273 条月选资格属政策层，本轮未使用，未测。

## 9. 已接入 / 未接入消费者

- 已接入：本轮新 CLI（离线编排）与新测试；无其他消费者。
- 未接入：`factor_runtime.build_mixed_batch`、生产/API/UI、v0 主入口、
  任何策略层。不修改旧消费者的行为。

## 10. 最小决策卡

| 必答项 | 本轮答案 |
|---|---|
| 本轮判断什么 | 已登记动量指标的"输入可追溯、数值可复算、缺失明示、资格 gate"样板是否成立 |
| 基准与增量 | 对照为同输入独立复算（引擎表达式 + 直接位置公式）；最大差 0.0；合成/真实诊断/资格拒绝三种结果分开 |
| 收益解释 | 不适用：无资金、无收益计算；`policy=not_applicable_no_account_policy` |
| 代价与执行 | 无费用/成交约束；未接账户与生产 |
| 证据与结论 | 工程与方法论通过；指标有效性未测试；真实预测按资格拒绝（mixed） |
| 下一步与边界 | 最能改变判断的资料：上市资格证据 + 行动可得时点；未获准冻结观察或生产采用；完成即停，交主控复核 |

## 11. 集中返修记录（2026-09-13，按主控复核单 A–D 一次收尾）

被审与复核：主控[书面复核与集中返修单](momentum-prototype-controller-review-2026-09-13.md)
（隔离证据在其 `raw/momentum-prototype-controller-review-2026-09-13/` 目录）。
本轮只改 `momentum_prototype.py`、`run_momentum_research_prototype.py`、
本轮两份测试；已确认的 run-04 数值与旧产物全部保留。

### 11.1 A–D 对照表

| 项 | 主控发现 | 修复 | 验证证据 |
|---|---|---|---|
| A（P1） | 行动检查发现错误后，新消费者仍拿原记录计算（fee 混入、负分红都退出 0） | ① `adapt_company_events` 严格校验：未登记字段（含账户字段）、同义字段冲突、负/非有限金额、非正比例、重复 event_id、非法日期一律抛错；② CLI 复用 `data_quality.check_actions`，BLOCK 级发现与计算消费绑定；③ 计算前逐产品预检，任何不合法即整体拒绝（退出 2），不留下部分产物 | 新增单测 7 项 + CLI 反例 2 项（fee/负分红 → 退出 2、无 values.csv、报告含 event_id）；合法控制组仍退出 0 |
| B（P1） | 协议身份未与算法绑定：改 `objects.primary`/`target_id` 仍退出 0 且照抄错误身份；codes 未含 CLI；registry 版本误写 v1.0.0 | 新增 `_verify_protocol_identity`：主对象/依赖/目标 ID/目标参数必须等于本实现唯一支持值；两卡快照必须与登记表当前解析逐字一致；动量参数（252/21）必须与算法常量一致；登记表容器版本必须与实际一致（1.2.0）；必需代码键固定（含 CLI 自身），删键免核被拒；协议 v1.0.3 绑定 CLI 哈希并写 `target_parameters` | 新增 CLI 反例 6 项（未知对象/错目标/卡不一致/删代码键/改 CLI 哈希/错登记表版本 → 全部退出 3、无产物） |
| C1（P2） | qualified-research 无完成分支，资格满足会落回历史诊断尾部还可能报成功 | 实现真正的合格分支：资格满足时产出 values/targets/rank 并如实标注可得时点边界；未满足仍拒绝（当前真实资料即如此） | 模拟资格检查的子进程测试：分支产出 targets.csv/rank-diagnostic.csv、`skipped_stages` 无 targets、`historical_reconstruction_only=true`；真实路径 run-05 拒绝结论不变 |
| C2（P2） | "窗口重叠"算的不是相邻目标区间相交（7 期不一致）；合成流程有失败仍退出 0 | 新增 `count_window_overlaps`：逐产品比较相邻两期真实 [e,x] 日期相交（端点接触计入，缺失窗口不参与）；合成流程有产品失败时退出 2 | 手算测试 4 类：完全分离=0、真交叠=1、端点接触=1、缺端点不参与；合成控制组仍退出 0 |
| D1 | run-06 边界核对不成立（253/273 选点类型失配、缺口用工作日推算）；未做正式键集合核对 | 新比对入口 [compare_values_v2.py](raw/research-momentum-prototype-2026-09-13/run-08/compare_values_v2.py)：`--out` 拒绝覆盖；统一日期类型；253/273 按实际第 253/273 个有效报价位置取值（非月末输出标"不适用"并注明）；缺口按已核交易日历定位；新增正式键集合精确核对。旧 run-06 封存不重跑 | [run-08/results/summary.json](raw/research-momentum-prototype-2026-09-13/run-08/results/summary.json)：批量 15,388 行最大差 0.0；**772 正式键与重算预期完全一致（0 缺失/0 多余/0 重复/0 值差）→ 修复不改变合法消费结果，run-04 无需重跑**；选类 125 行：110 一致、15 条"类别不存在"全部附检查依据 |
| D2 | 合成例只有 /tmp 冒烟；quality.json 丢发现定位；报告文案与日志计数不实 | 合成完整示例入库 `run-07`（values/targets/rank/manifest/missing 全套）；quality.json 落盘行动逐条发现（level/code/instrument/message/evidence）、identity_errors、输入时间语义（fetched_at 逐产品 + actions available_at 已声明/未知计数）；报告 §5/§4.2/§8.3 文案与计数已纠正（21 条原始行动、20 条进指数、1 条停牌分列；缺报价原因逐条定性；日志阶段计数实报） | run-07 产物齐备；该新增字段仅由新接口的运行与测试证明（见 §12 时间资格测试与 run-09 的 quality.json）；run-04/run-05 为封存旧产物，其 quality.json 保持原样未改 |

### 11.2 返修轮命令与日志（实际计数实报）

```sh
# 局部测试（本轮两个测试文件）：62 passed in 9.62s
python3 -m pytest tests/unit/test_momentum_prototype.py \
  tests/integration/test_momentum_prototype_cli.py -q
# 完整回归（与初版 §8.3 同一 20 文件命令）：363 passed in 44.69s，退出 0
#   （346 + 返修新增 17 项；日志 run-08/full-regression-revision.log）
# ruff（本轮四文件）：All checks passed!（run-08/ruff-revision.log）
# 合成完整示例入库：
python3 scripts/run_momentum_research_prototype.py \
  --protocol docs/experiments/raw/research-momentum-prototype-2026-09-13/protocol.json \
  --mode synthetic --out docs/experiments/raw/research-momentum-prototype-2026-09-13/run-07
# 独立逐值比对 v2（旧 run-06 封存未重跑）：
python3 docs/experiments/raw/research-momentum-prototype-2026-09-13/run-08/compare_values_v2.py \
  --out docs/experiments/raw/research-momentum-prototype-2026-09-13/run-08/results
```

### 11.3 返修轮指纹

| 文件 | SHA-256 |
|---|---|
| 协议 v1.0.3（现行） | `7d7562f7d350038643ce4d099254d7bcc2c95ffdc137e1707e843b30eca8da1f` |
| 协议 v1.0.2（原件保留） | `329666ff8b86fc4a58055fdc47a6927325a71ac7b50dc75a2baa7d0c4daa35de` |
| `src/lei_signal/research/momentum_prototype.py` | `26f49a57033797231e095d62c7655324736c98156ed336ae77b7957b5f56278c` |
| `scripts/run_momentum_research_prototype.py` | `59c6ffd8cb36ea03b51f556b0ecd9f5cedbfb26244453e65a451277f2c2504e0` |
| `tests/unit/test_momentum_prototype.py` | `1e21ec8ac0aea4008c745752c975375840116d7e90d134fe2975498301d4ec00` |
| `tests/integration/test_momentum_prototype_cli.py` | `27f56f069b7a791aea0ad92eed7eb8ae4ee2153589eaeaead3dfd03ab7cead4a` |
| `run-04/values.csv`（已确认数值，未变） | `0db2492a11372fae827465debcddf81e25b0016ea4fd219be6f0894cf471a0b5` |
| `run-07/manifest.json`（合成完整示例） | `bad02a1f1a6763768c54f502197c7707509eee706798f960e0a01a846dca5485` |
| `run-08/results/summary.json`（比对 v2，终版协议下实跑） | `2e3a5d539fca9e514c6b7a9db235517a2fc63547ecd81bd0e0f17db7f8c6ed53` |

### 11.4 返修后状态

- 原 896 项保护基线复算：变化 0、缺失 0；run-04 数值哈希未变。
- 真实模式实际执行：本轮返修**未重跑真实历史诊断**——比对 v2 证明修复后
  对 772 个正式键的重建结果与 run-04 逐一相同；真实预测（qualified）分支
  已实现但当前真实资料仍被资格拒绝（run-05 结论不变）。
- 未新增数据、未接账户、未改生产/OKR；他人未提交改动未触碰；未提交 git。
- 完成即停，交主控复核。（A–D 轮）

## 12. R1/R2 返修记录（2026-09-13，按主控复核单 §9 一次收尾）

被审：主控复核单 v1.1.0 §9（[momentum-prototype-controller-review-2026-09-13.md](momentum-prototype-controller-review-2026-09-13.md)）。
A/B/C2/D1 经主控 §9.1 确认收口，本轮不重开；只处理 R1（时间资格）与
R2（终版合成证据与说明）。可写边界不变：本轮两实现、两测试、执行报告、
新协议/新编号产物、登记导航。

### 12.1 R1：时间资格（非空可得时间 ≠ 历史时点合格）

主控 time_probe 反例（合成分红 available_at=2030-01-01，生效 2025-06-16，
研究窗 2025-01-02~2026-02-27）在修复前确实以退出 0 写出 targets 并标
`qualified_for_this_mode`。本轮先以测试复现该失败模式（修复前晚控制/
无时区控制均失败），再实现：

- **信号资格**：qualified 分支在生成任何信号/目标之前，逐事件核对"进入
  t 日信号计算的行动是否不晚于 t 的决策时点（本地 15:00，Asia/Shanghai，
  带时区严格比较）可知"；无法证明（缺失、晚于、无时区）即拒绝研究，
  逐条列产品/event_id/生效日/可得时间/观察日/原因。
- **目标与信号区分**：未来目标是事后评价标签——生效日在所有观察日之后、
  仅落在目标窗内的事件不构成信号泄漏，不拒绝研究；但该标签在 x 决策
  时点尚不可知时，从排序配对中剔除并逐条留痕
  （quality.json `target_label_status`），目标数值本身按事后评价保留。
- **历史诊断**：晚取得（available_at 晚于评价期终点）或未知的行动如实标
  `historical_reconstruction_only=true` 并输出 `late_available_at` 逐条
  清单，不再只数空值。

验证（全部经正式 CLI 与真实检查函数；夹具快照含按合成分红独立计算的
economic_index 列使字段绑定真实通过，无 patch）：

| 控制 | 结果 |
|---|---|
| 早（available 2025-06-15T10:00+08，生效 2025-06-16） | 退出 0；targets/rank 写出；`historical_reconstruction_only=false`；标签全完整 |
| 晚（2030-01-01T10:00+08） | 退出 2；无 values/targets；报告含产品、event_id 与 2030 时点 |
| null | 退出 2（时间资格路径与既有用途闸门双重覆盖）；无 targets |
| 同日边界（生效日=观察日 2025-06-30） | 14:00+08 → 放行；16:00+08 → 拒绝；无时区 14:00 → 拒绝 |
| 目标尚不可知（生效 2026-03-02、可知 2026-04-01、窗至 2026-03-06） | 退出 0；该目标标签剔除出配对（该期 n=1 而非 2）；quality 留痕 product/obs/x/event_id |
| 历史 2030 | 退出 0 但 `historical_reconstruction_only=true`，`late_available_at` 含该行动 |

原 `test_qualified_branch_produces_targets_when_gates_pass`（强制放行、
只测路由）已删除，由上表真实时间条件测试取代；修复前的失败证据保留在
本轮迭代记录与主控 [time-run-01](raw/momentum-prototype-controller-review-2026-09-13/time-run-01/summary.json)。

### 12.2 R2：终版合成证据与三处说明修正

- run-07 确认为中间阶段产物：其绑定的协议（f6e463ed…）与 CLI（204da006…）
  原件**未保留、不可恢复**（当时未按规程另存版本文件即被覆盖），已在
  [run-07/EARLY-STAGE-README.md](raw/research-momentum-prototype-2026-09-13/run-07/EARLY-STAGE-README.md)
  如实注明，不编造重建；终版合成示例为
  [run-09](raw/research-momentum-prototype-2026-09-13/run-09/manifest.json)
  （协议 v1.0.4 + 终版 CLI，manifest 哈希 `cc5e6bc3…`）。
- §11.1 D2 的"run-04/run-05 新版 quality.json 含 evidence"表述不实，已改为
  "新增字段仅由新接口运行与测试证明；封存旧产物原样未改"。
- quality.json 新增 `price_findings`（排序拒绝等价格检查发现的逐条
  产品/证据定位）与 `time_violations` 清单；由时间资格测试的产物实证。
- §11 开头坏链接已改指主控 Markdown；协议版本引用统一用
  `protocol-v1.0.*.json` 版本文件（v1.0.3 已补存原件），不再以移动的
  protocol.json 路径冒充历史原件。

### 12.3 命令、日志与指纹

```sh
# 局部测试：67 passed in 16.05s（run-08/local-tests-r1r2.log）
python3 -m pytest tests/unit/test_momentum_prototype.py \
  tests/integration/test_momentum_prototype_cli.py -q
# 完整回归（同一 20 文件命令）：368 passed in 53.83s，退出 0
#   （run-08/full-regression-r1r2.log；363 − 删除 1 项路由式模拟 + 新增 6 项时间资格）
# ruff（本轮四文件）：All checks passed!（run-08/ruff-r1r2.log）
# 终版合成示例：
python3 scripts/run_momentum_research_prototype.py \
  --protocol docs/experiments/raw/research-momentum-prototype-2026-09-13/protocol.json \
  --mode synthetic --out docs/experiments/raw/research-momentum-prototype-2026-09-13/run-09
```

| 文件 | SHA-256 |
|---|---|
| 协议 v1.0.4（现行） | `9b05212dc6ebecfc9c1157bead981700b9778d86f461edb54ccd048276dc480e` |
| 协议 v1.0.3（本轮补存原件） | `1c8d99c1c72cd71ac0cd4dd030c4fe6de86cfc03fb94fc1136131833b8fe108f` |
| `src/lei_signal/research/momentum_prototype.py` | `dd0f12c614bb2b4f8a177763535965003e51556e62a113297e4da236306ccb40` |
| `scripts/run_momentum_research_prototype.py` | `e70b440fe39c26819861810bb3c69fae922db651988b3a0a8a18392dd729dfec` |
| `tests/unit/test_momentum_prototype.py` | `1e21ec8ac0aea4008c745752c975375840116d7e90d134fe2975498301d4ec00` |
| `tests/integration/test_momentum_prototype_cli.py` | `20b1daa5f6cc3d389deb89105ab1d28215e4b54fa9a1db64acdf10c0bed3a420` |
| `run-09/manifest.json`（终版合成示例） | `cc5e6bc32d30d44b0320933a6ea46ba51a78d4d59c7709c7bdc2cbc642f66d92` |
| `run-04/values.csv`（已确认真实值，未变） | `0db2492a11372fae827465debcddf81e25b0016ea4fd219be6f0894cf471a0b5` |

### 12.4 交回问答（按主控 §9.4 要求分别回答）

- **算法及数值是否可复算**：是。run-04 的 772 个真实值封存未动；
  run-08 比对 v2（v1.0.3 下）已证 772 键零差异；R1 只改资格判定与标注，
  不触及算术路径。
- **历史资料何时可用**：逐事件如实标注——20 条分红/拆分均无
  available_at（历史重建）；晚于评价期的行动在 qualified 拒绝、在
  historical 标晚取得；不再把非空可得时间当成历史可知。
- **模式是否已实现**：synthetic、historical-diagnostic、qualified-research
  三模式均已实现且状态诚实；qualified 的真实放行以时间资格为准（当前
  真实资料仍被资格拒绝，run-05 结论不变）。
- **是否有预测有效性证据**：无。本轮全部为工程与方法论收尾。
- **是否获准生产**：无。production=not_authorized，
  policy=not_applicable_no_account_policy。

保护核对：原 896 项基线复算变化 0、缺失 0；run-04 值哈希未变；
旧 run-03～run-08 与主控反例目录未覆盖（run-07 仅新增说明文件）；
未新增数据/账户，未动生产/OKR；他人未提交改动未触碰；未提交 git。
完成即停，交主控复核。（R1/R2 轮）
