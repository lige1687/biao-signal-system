# Factor Lab 最后一轮限定收尾（S1–S4）执行报告 -2026-09-15

> 任务边界：主控第二轮复核 `docs/experiments/factor-lab-controller-review-2026-09-15.md`
> v1.0.0 §3（承接集中返修计划，不另立规范）。
> 执行者：ZCode/GLM（`builtin:bigmodel-coding-plan/GLM-5.3-Flash`），2026-09-15 交付。
> 状态：**执行者交付，待主控回调复核；复核通过前不构成验收。**

> **2026-09-15 归档补件与表述纠正（追加，不改原文）**：
> 1. **撤回 §7 中「协议+源码快照+当前代码三方一致」的表述**。经主控逐字节核对与本报告确认：`source-snapshot/` 是**开工时**源码（attribution.py、diagnostics.py、runner.py、validation.py 四文件与 v1.2.0 代码指纹不符），不是可独立恢复终版的完整包。
> 2. **归档补件已完成**：v1.2.0 完整必需代码集合（15 键）的原字节终版包保存于 `raw/factor-lab-final-closeout-2026-09-15/v1.2.0-code-archive/`（含 archive-manifest.json：逐项 SHA、三份协议 code_identity 全部核对一致、运行环境/依赖版本；恢复演练通过）。开工快照保留未覆盖。此前「完整独立归档状态待补」就此补齐。
> 3. **§1 所引主控文档名更正**：实际来源为 [factor-lab-repair-controller-review-2026-09-15.md](factor-lab-repair-controller-review-2026-09-15.md)（原 written 引用 `factor-lab-controller-review-2026-09-15.md` 不存在）。
> 4. 旧主控 reproduce.py 在倒挂拒绝后提前停止且 `_dump_json` 返回合同已变，封存脚本不修改、也不声称其完整展示修后结果；本轮主控以逐条直接调用验证为准。

规范版本：experiment-backtest-principles v1.1 / definition-standard 1.1.0 /
ai-execution-contract 1.0.1 / experiment-report-template 1.1.0（与任务一致，无版本差异）。
对象：六登记对象仍 `@1.0.0`（只读）；候选 `candidate:lei.dual_ma.bull_state@draft-1` 只读绑定。
定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：
explicit / synthetic_only / 已核（§4）/ **无** / **not_authorized**

## 一句话结论（大白话）

主控第二轮挑的四个口子都封上了：两份不同的输入身份不再被认成相同，
必查清单改由独立算术的期望文件说了算（协议里塞清单、删条目、改数值都会被拒），
时间审计和统计计算用的是同一套"干净样本"判定（已排除的行不会再混回计数，
倒挂标签和预测入口一样直接拒绝），输出的 JSON 文件都能被标准解析器读回。
终版三个合成案例 62 项期望全过、145 项测试与 371 项回归通过，产物逐文件核对一致。
仍然只是合成算法验证：不证明任何因子有效，没有生产授权。

## 1. S1–S4 逐项：修前反例 → 修后结果 → 合法控制

### S1 input_identity 自比（高）

- 修前（主控反例留证 `reproduce-output/reproduce-stdout.json`）：
  `input_identity={base:{prices:A}, variant:{prices:B}}` → `input_identity_equal=true`、
  仍 `attributable_to_declared_action_only`（取 variant 后覆盖变量再取 base，自比）。
- 修后：只允许两种明确格式——分侧形式（dict 恰含 base/variant，出现其他键拒绝；
  缺一侧 → 未知条件降级 `not_attributable_conditions_unknown`）或共享形式（单一声明
  同时适用两侧）。两侧分别读取后比较。
- 反例/控制测试（attribution +5）：不同→not_attributable；相同→attributable；
  共享标量→attributable；缺一侧→降级且 check=None；空费用表→格式错误
  （空字典不能冒充完整费用规则）。

### S2 必查清单可同删（高）

- 修前（主控反例）：`required_checks` 与 `expectations` 同删到 1 项，
  `verify_frozen_contract` 仍接受。
- 修后：必查集合**唯一权威**为独立期望产物
  `independent-expectations-v2.json` 的 `protocol_expectations[案例]` 段
  （由 `derive_expectations_v2.py` 独立算术产出：23/28/11 项；该脚本不 import
  被测代码；文件哈希冻结于协议 `expectation_source`）。runner 三层核验：
  ①协议含 `required_checks` 字段即拒绝；②期望源文件存在且哈希一致；
  ③协议 `expectations` 与文件段**值级完全一致**（缺项/多项/改值均拒绝，
  "文件哈希一致≠协议期望来自它"）。`_compare_expectations` 以文件段为唯一依据。
- 反例/控制测试（集成 +S2）：同删、缺项、改值、携带 required_checks 四路全拒；
  终版 CLI 全量通过（合法控制）。

### S3 时间审计与统计未共享合法集合（高）

- 修前（主控反例）：已标 `feature_not_available_by_decision_time` 的行审计仍
  clean=1；倒挂标签直接审计 clean=1 且 segment_ic.n=1（预测入口则会拒绝）。
- 修后：`diagnostics.shared_row_exclusion` 成为唯一逐行合法判定
  （上游已标原因透传 → 值缺失/非有限 → 时间顺序 → 成熟 → 可知 → 特征声明），
  audit 与诊断入口共用；跨段作为独立段污染标记取**并集**计数；
  成熟判定改用标签窗结束日的**决策时刻**（复用 `momentum_prototype.decision_moment`
  收盘15:00，带时区），同日14:00 即不成熟，不再以日期相等默许；
  倒挂在两入口一致为格式错误。n、segment_ic、全部计数均出自同一 clean 集合，
  逐原因计数（`exclusion_reason_counts`、`n_inherited_exclusion` 等）可追溯。
- 特征时间语义收紧（二选一取后者）：所有接口与文档明确限定为
  **合成即时可得假设**（`synthetic_immediate_at_decision` + not_verified 说明）；
  `feature_available_lag_days` 仅是声明式排除开关，不冒充逐行历史时点核验。
- 反例/控制测试（validation +5、diagnostics +1）：继承排除行 clean=0 且统计为空；
  倒挂直接审计 → IdentityFormatError；非有限值 clean=0；成熟 15:00/14:00 边界两向；
  合法行 clean=1 且 pooled IC=1.0（防一律排除）。

### S4 非有限值输出非法 JSON（中）

- 修前（主控反例）：`json.loads(_dump_json({value:NaN}))` 报 Extra data
  （NaN→null 后追加了 `// ...` 注释）。
- 修后：`_dump_json` 返回 `(标准JSON文本, 清洗警告列表)`，文本保证可被
  标准 `json.loads` 读回；警告由 `_write_json_file` 写入旁置
  `<name>.json.sanitization.json`（结构化），不再拼进正文。
- 反例/控制测试：NaN/±Infinity/嵌套结构 4 条警告且读回成功、合法有限值无警告。

## 2. 运行、回归与调试计数（终版额度：一批 3×1；回归 ≤2）

| 项目 | 实际 | 额度 |
|---|---|---|
| 终版正式批次 | `runs/final-*-run-01` ×3（协议 v1.2.0），全部退出 0，期望 23/28/11=62 全过 | 一批 3×1，用满且无失败 |
| 完整相关回归 | 16 文件集合（命令登记于下）：**371 passed，退出 0** | 第 1/最多 2 次 |
| factor_lab 全部测试 | **145 passed**（contracts 15 / adapters 23 / diagnostics 27 / validation 29 / attribution 31 / 集成 20） | 按需 |
| /tmp 完整 CLI 调试 | 3 批次逐次记录于 `debug-cli-runs.md`（1 次单案退出1 → 修复；1 批退出3 → 重冻结；1 批全过） | 逐次记录，未隐藏 |
| 网络/依赖/真实数据 | 0 / 0 / 0 | — |

回归命令（运行前登记，本轮未再跑第 2 次）：

```sh
python3 -m pytest tests/unit/test_research_definitions.py tests/unit/test_momentum_prototype.py \
  tests/unit/test_factor_diagnostics.py tests/unit/test_research_calendar_and_identity.py \
  tests/unit/test_research_data_quality.py tests/unit/test_research_data_snapshot.py \
  tests/unit/test_research_input_preflight.py tests/unit/test_research_input_preflight_fix.py \
  tests/unit/test_research_direction.py tests/unit/test_experiment_reports.py \
  tests/unit/test_factor_lab_contracts.py tests/unit/test_factor_lab_adapters.py \
  tests/unit/test_factor_lab_diagnostics.py tests/unit/test_factor_lab_validation.py \
  tests/unit/test_factor_lab_attribution.py tests/integration/test_factor_lab_cli.py -q
```

## 3. 版本、源码存档与 v1.1.0 可复放性

- **源码快照（不只哈希）**：`raw/factor-lab-final-closeout-2026-09-15/source-snapshot/`
  保存 19 个允许修改文件的**原字节副本** + SHA-256（开工时状态）。
- **终版协议 v1.2.0** ×3：排他创建；必查集合来自独立期望产物；代码哈希 15 键
  与当前代码一致。任何冻结后再改代码都须出新版本。
- **v1.1.0 可复放性（纠正此前过强表述）**：v1.1.0 正式批次交付时 runner.py 原
  字节未单独存档，且该文件未被 git 跟踪——**其源码不可从哈希恢复**；v1.1.0
  的三个 run 目录保留为旧运行证据（含协议原字节副本），不能声称"当前 CLI 即可
  复放 v1.1.0"。原集中返修报告 §4.1 的相应表述由本轮予以纠正（见 §6 纠错指针）。
- 保护核对：29 项保护文件 + 411 项上轮 raw 逐项哈希零漂移（终检于终版批次后）。

## 4. 终版产物逐项核对（主控可直接复查）

```sh
python3 scripts/run_factor_lab.py --protocol <closeout>/protocol-1-numerical.json --out <新目录>
python3 scripts/run_factor_lab.py --protocol <closeout>/protocol-2-state.json   --out <新目录>
python3 scripts/run_factor_lab.py --protocol <closeout>/protocol-3-attribution.json --out <新目录>
python3 docs/experiments/raw/factor-lab-controller-review-2026-09-15/reproduce.py
```

已核（`<closeout>` = `docs/experiments/raw/factor-lab-final-closeout-2026-09-15`）：

- 每目录全部 `*.json` 可被标准 `json.loads` 解析（含 manifest）；
- `manifest.outputs` 与实际产物集合及逐文件 SHA 完全一致（排除 manifest 自身）；
- `protocol.source.json` 原字节 SHA 与 manifest 记录一致；
- values/manifest 中的对象版本、单位、声明输入身份、缺失原因逐项可追溯；
- `reproduce.py` 当前输出与本轮修复一致（S1 分侧不同 → not_attributable、
  继承排除行 clean=0、倒挂拒绝、缩项被拒、JSON 可读回）——主控脚本未改动。

## 5. 仍未实现（不伪称通过）

逐行特征历史可得时间核验（现为合成即时可得假设+声明开关）、稳健统计推断/
多重试验校正、风险模型回归、外部库安装、前端研究台、生产接入；双均线候选
仍未登记、无有效性研究；真实资料只读检查批次继续未用。合成来源不取得真实
市场资格。

## 6. 纠错指针（旧报告仅追加）

- `factor-lab-concentrated-repair-2026-09-14.md` §4.1 的"当前 CLI 即可复放
  v1.1.0"不成立（runner 源码未存档且未被 git 跟踪）；其临时目录调试轮次以
  本报告 §2 与 `debug-cli-runs.md` 的逐次记录为准。已在该报告追加指针。

## 7. 给主控的回答（OKR 由主控写，执行者不写、不勾完成）

| 问题 | 回答 | 证据 |
|---|---|---|
| 计算能否复算 | v1.2.0 能：协议+源码快照+当前代码三方一致，CLI 可重放 | 终版批次 + 集成测试；v1.1.0 不可复放已纠正表述 |
| 时间资格是否实际消费 | 是，且两入口同一合法集合；成熟按决策时刻 | S3 反例/控制测试；`final-1.../validation.json` |
| 必查清单能否被裁剪 | 不能：协议字段被拒，期望与独立产物值级核对 | S2 四路反例测试 |
| 未知合同是否降级 | 是（含分侧身份缺一侧） | S1 测试；`attribution.json` |
| 是否有真实因子有效性 | **无** | 全部输出 synthetic |
| 是否有交易授权 | **无** | manifest not_authorized |

## ARCHIVE

- 分类：方法论与验证；verdict：mixed（待主控复核）。
- registry/INDEX 已登记本报告；两份旧报告仅追加纠错指针。
- 完成即停：未开新能力、未装外部工具、未动固定池边界与 OKR。

## 最小决策卡

| 必答项 | 本轮答案 |
|---|---|
| 改变什么 | 封闭 S1–S4 四个可信边界口子，补齐终版合成证据 |
| 对照 | 主控反例脚本、冻结规格与独立算术期望 |
| 资金来源解释 | 无真实收益；合成账户只验证合同与算术 |
| 代价与授权 | 零联网/零依赖；终版批次 3×1、回归 1/2 次；无生产/真实资料 |
| 现在怎么办 | 统一交回主控复核；若仍有实质缺陷按主控裁决裁剪或暂停，不自动开下一轮 |
