# 研究输入离线验收入口：主控复核与集中收尾单

版本：1.1.0；日期：2026-09-13；任务家族：research-data-foundation。最新复核见 §10；§1–9 保留初审历史，不代表修复后的状态。

被审报告：[research-input-preflight-2026-09-13.md](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/research-input-preflight-2026-09-13.md)。验收依据：[长任务书 v1.0.0](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/superpowers/plans/2026-09-13-research-input-preflight.md)。沿用研究原则 v1.1、定义标准 1.1.0、执行合同 1.0.1、报告模板 1.1.0；规范、唯一定义登记与冻结 v0 不改。

## 一句话结论（大白话）

**最新复核：来源文件不合格仍放行的问题已修复，295 项回归通过，真实三请求仍为 0/2/2。尚有最终 manifest 写盘失败未处理的遗漏，纳入下一轮开头收尾，不再单开一轮。** 已形成一个已有动量指标研究样板的长任务书：推进计算复算与合成完整示例；真实预测分析仍受资料资格限制，不因接上计算自动获准。详情见 §10，初审发现与修复历史保留。

## 1. 已确认与未确认

| 项目 | 主控结果 |
|---|---|
| 三次真实输入检查 | 在主控独立新目录复跑，退出码 **0 / 2 / 2**；integrity、data_uses、objects、findings、request_satisfied、errors 六组稳定字段逐项与执行产物相等 |
| 真实样本 | 14 只、18,916 行；描述/诊断可用，另外四项默认拒绝；三个指定对象仍缺 economic_index，没有借改字段名放行 |
| 现有回归 | 本次实跑 **281 passed in 31.67s**，退出码 0；本次四个代码/测试文件 ruff 为 `All checks passed!` |
| 冻结保护 | 896 项原基线逐文件哈希无变化；三次交付的 preflight.json / preflight.md 哈希与各自 manifest 一致 |
| 复用与范围 | 新增编排与 CLI 确实调用既有读取/检查/对象绑定；无因子或账户运行。本轮主控不改实现 |
| 当前不可接受项 | F1 来源核验失败未进入最终拒绝；F2 异常退出合同不完整；F3 交接身份与解释输出缺项；F4 报告与测试证据需校正 |
| 定义/数据/实现/有效性/生产 | 不改定义；真实数据仍受限；实现部分确认、待收尾；本轮无有效性证据；无生产授权 |

三次真实复跑属于复现执行者的计算，不是三份独立市场证据；新合成反例另行记录。没有重新构造旧版本验证其失败史，也没有进行全仓库或所有畸形输入的无限审计。

## 2. F1：来源核验失败不能只写进“限制”（必须修，P1）

位置：[input_preflight.py:244](/Users/yongbiaoli/Desktop/lei-signal-lab/src/lei_signal/research/input_preflight.py:244) 捕获 `verify_sources` 失败后，仅设 `sources_verified=False` 并追加 limitations；[最终组合:308](/Users/yongbiaoli/Desktop/lei-signal-lab/src/lei_signal/research/input_preflight.py:308) 不读取该状态，errors 也为空。

主控反例采用两天恒定名义价和实际提供的恒定经济指数列（无行动时首值为 1），仅是合成算法输入，不是真实资料。引用已有 `mixed.price.economic@1.0.0`，不新增或修改对象定义。先用当前真实登记表作控制组，再复制登记表到隔离输出，仅把该卡依赖的 `mixed_code` 来源 SHA-256 改成 64 个 0，原登记表与来源文件不动。

| 条件 | sources_verified | 对象字段满足 | errors | request_satisfied | CLI |
|---|---|---|---|---|---|
| 原来源指纹 | True | True | [] | True | 控制组函数成功 |
| mixed_code 指纹错误 | **False** | True | **[]** | **True** | **退出 0** |

这不是要求新增来源可信认证；已有来源完整性检查已经失败，却被当前编排忽略。实际全池因为另缺 economic_index 而恰好被拒，不能掩盖这个组合缺陷。

**最小修复与验收：**

- 对请求对象所需的来源核验失败，必须影响该对象及最终结果，不得继续返回满足。当前 `verify_sources` 是全登记表检查，可先保守拒绝对象请求，不在本轮实现复杂的来源依赖影响分析。
- 未提供登记表且 refs 为空的数据描述正向路径继续可用。显式传了失败登记表但没有对象时，可报告对象阶段不可用、保留独立数据结论；须写明规则，不能用它绕过有对象请求的失败。
- 保留 sources_error 的具体文件与原因。对“正确指纹控制组 / 错指纹 / 来源缺失”做函数与 CLI 终点断言；修复前错指纹的对象请求必须暴露，修复后不得退出 0。
- 无需更改 `definitions.py` 或 `data_quality.py`，更不需要真实上市材料。只修当前编排如何消费既有失败结果。

## 3. F2：失败出口与不完整产物（必须修，P2）

位置：[CLI 参数与输出:138](/Users/yongbiaoli/Desktop/lei-signal-lab/scripts/check_research_input.py:138)。协议规定 0 满足 / 2 检查完成但被拒 / 3 输入、参数或运行失败，当前有三个不一致：

1. **模拟写盘失败**：主控在 `preflight.json` 写成后，只令 `preflight.md` 写入抛出 OSError。`main()` 没有返回 3，而是抛出未捕获异常；目录留下 `request_satisfied=true` 的 JSON，无 manifest、无失败状态。未生成 manifest 这一点正确，但不完整产物仍缺明确状态。
2. **无日历且区间倒置**：2026-06-30 → 2026-06-01 实测退出 2、errors=[]。它没有错误放行，但把非法请求当成正常数据拒绝；现有倒置测试传了日历，因此未覆盖此路径。
3. **非法 CLI 参数**：argparse 默认退出 2，与本命令已定义的“正常检查拒绝”混淆。现有禁止覆盖口径测试只断言非零，没有锁定合同中的 3。

**最小修复与验收：** 在新入口校验日期合法性/起止关系，不依赖可选日历触发；参数错误返回 3、`--help` 仍为 0。输出阶段捕获 I/O 错误，stderr 明确失败，能安全记录时保留失败标记；完整写出后再标完成。若磁盘本身不可写，不能要求凭空写成失败文件，返回 3 且无完成标志即可。现存输出目录仍拒绝覆盖。

测试覆盖 JSON、Markdown、manifest 三处写入失败及目录不可写的模拟；不改生产磁盘权限、不删文件。函数和子进程退出均应检查，不能只断言抛异常。已有合法/受限路径保持 0/2。

## 4. F3：可复现交接尚缺关键字段与原因（必须补，P2）

任务书 Task 3 要求实际规范指纹、协议哈希、准确依赖、完整卡和原输入时间。实际三份 manifest 只有三项规范名称/版本，没有规范哈希、报告模板身份或冻结协议哈希；objects 仅有 contract_digest，没有完整卡快照/依赖解析输出；input_times 只保存首末观察日和一条总 available_at=null。执行的 baseline.json 另有部分指纹，但运行 manifest 未绑定这份文件，不能靠读者自行猜其关联。

这不等于全无追溯：当前 snapshot.json / registry 的哈希已间接绑定其中的 CSV 指纹与对象内容，**不要求在每行重复复制这些信息**。补法可复用旁置快照/清单并绑定其路径和哈希，不建第二份手写登记表。

还缺两项直接解释：

- [对象绑定:285](/Users/yongbiaoli/Desktop/lei-signal-lab/src/lei_signal/research/input_preflight.py:285) 只抽 missing_fields / directly_satisfiable，丢掉 binding 的 reasons 等原结果；这与任务书要求保留 binding 原结果不符。
- 生成 Markdown 的对象表不展示 error / purpose_error。主控“未知对象”反例 JSON 有 `unknown exact definition version`，Markdown 仅显示 False/None，加一条泛化限制，读者看不到具体错误。正常用途表也反复铺相同告警而缺产品定位。来源失败原因同样不能只留一个不可点击字段名。

**集中补齐：** manifest 绑定本次采用的规范与协议/基线、实际代码与输入身份；导出完整解析卡及递归依赖（生成物，不手改），保留 binding 原结果、用途不符和未知对象的具体原因。原输入中的 fetched/generated/observation/available 时间按适用字段保留或给精确 JSON 位置引用，未知继续未知，不把本次生成时刻当历史可知时刻。

Markdown 从同一 dict 展示关键原因与异常定位，长列表可指向旁置 JSON，不要求搭 UI。新增测试核规范/协议指纹、完整卡依赖、错误原因可见及输出哈希；已有子文件通过 parent manifest 绑定的地方无需无意义复制。

## 5. F4：报告与测试证据集中校正（不增加研究范围）

### 5.1 纠正三条会误导下一步的事实

- 执行报告 §4 再次写“11 只晚于评价期起点上市”“结构性，补数据改不了”。目前只确认 **11 只首报价晚于起点，缺上市资格证据，原因未确认**。程序当前拒绝是正确的；文字不能恢复已经撤回的解释。
- §5/§9 把 economic_index 描述成“未做的计算”并称唯一下一门槛。仓库已有 `definitions.economic_index`、`factor_runtime.reconstructed_economic_index/build_mixed_batch` 及 v0 计算。**缺的是这批名义价快照与现有计算/定义的合规接入及相应证据，不是从零没有公式实现。** 历史重建与当时可知条件仍须分开，不能说接上计算就解除上市/行动时点限制。只检查三个指定对象，不能扩大为全部 `mixed.*` 不可用。
- “需要全市场停牌/复牌序列”超出固定 14 只和原评价期。下一资料需求应先对准实际产品、缺口与用途，不预设扩全市场；本轮仍不采集。日期公告的“下界”也不要自行写成精确到达时刻，保持已有未确认状态。

### 5.2 不把测试名称当作实测证据

- `test_same_path_different_fingerprint_yields_different_identity` 实际使用 `a/snap` 与 `b/snap`，不是同一路径内容变更。补同一路径先后改变输入的测试，前后字节需确实不同；只动合成临时文件。
- `test_counterexample_files_unchanged_and_no_listing_channel` 仅检查两个文件存在，未断言哈希未变。主控本次另核原反例指纹；该测试应锁定原指纹或报告不能声称它验证未变。
- 断网测试确实在子进程里封锁 socket，但没有报告声称的“guard 先自证有效”步骤。补一次尝试连接必须被该 guard 拒绝的自检，再运行入口；不实际联网。
- 原任务矩阵里的空/全缺失、区间内漏日、写出中断没有对应的新入口终点测试；底层已有测试不能自动代替组合入口覆盖。把有限矩阵补齐即可，不跑无边界变异工具。
- §6 完整回归命令仍有 `<15 个既有回归文件>` 占位；§8 只列截短哈希，测试完整指纹也未提供实际清单路径。下一交付一次补齐真实命令、日志路径、完整文件指纹，修正 §2 表格错位和“七项缺口”与四行表不一致。现有失败史保留，不修改原封存产物。

## 6. 固定复跑材料与实际命令

主控脚本：[reproduce.py](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-input-preflight-controller-review-2026-09-13/reproduce.py)。它只创建全新输出和明确标注的合成夹具；三个真实输入分支只读旧文件，绝不覆盖执行者 attempts。既有对象定义不改，临时错误哈希登记副本不是第二份权威登记表。

```sh
python3 docs/experiments/raw/research-input-preflight-controller-review-2026-09-13/reproduce.py \
  --out docs/experiments/raw/research-input-preflight-controller-review-2026-09-13/run-02
```

主控已实跑 `run-01`，结果见[probe-summary.json](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-input-preflight-controller-review-2026-09-13/run-01/probe-summary.json)。新复跑使用不存在的目录；若 run-02 已存在改新编号。源码无结果断言替代测试，修复后须新增独立期望断言；不能改掉反例输入来使结果变好。

完整回归实际命令：

```sh
python3 -m pytest \
  tests/unit/test_controller_fixes.py \
  tests/unit/test_controller_fixes_round2.py \
  tests/unit/test_controller_fixes_round3.py \
  tests/unit/test_controller_fixes_round4.py \
  tests/integration/test_controller_fixes_cross_module.py \
  tests/unit/test_research_data_quality.py \
  tests/unit/test_research_data_snapshot.py \
  tests/unit/test_research_calendar_and_identity.py \
  tests/integration/test_research_offline_loop_round2.py \
  tests/integration/test_research_data_snapshot_cli.py \
  tests/unit/test_research_definitions.py \
  tests/unit/test_factor_runtime.py \
  tests/unit/test_factor_diagnostics.py \
  tests/unit/test_factor_account_adapter.py \
  tests/unit/test_experiment_reports.py \
  tests/unit/test_research_input_preflight.py \
  tests/integration/test_research_input_preflight_cli.py -q

python3 -m ruff check src/lei_signal/research/input_preflight.py \
  scripts/check_research_input.py tests/unit/test_research_input_preflight.py \
  tests/integration/test_research_input_preflight_cli.py
```

主控记录：281 passed / ruff 通过；不宣称现有测试已经覆盖 F1–F4。F2 倒置区间函数结果也已保存在复跑目录；另实跑 CLI 无日历倒置请求，退出 2、errors=[]；未知参数退出 2。普通坏日期已有拒绝，未发现其错误放行，不把它再报成安全漏洞。

## 7. 被审文件指纹

| 文件 | SHA-256 |
|---|---|
| `src/lei_signal/research/input_preflight.py` | `37200f4e45adb300b20346ffdafa744d4c55d1d990493b7f6ccbf6d79bca76d3` |
| `scripts/check_research_input.py` | `b884d5c125b3e29db6aa63adfeb24cd1cb625a0c1526140f56f24135fb2cd11d` |
| `tests/unit/test_research_input_preflight.py` | `60b7fe0dceae865c0c4cae0a6604708cff34dded74b7633a5e6a6b3fc501fb2d` |
| `tests/integration/test_research_input_preflight_cli.py` | `d315405f7e1f673a6810cb9300f9731ab78a412ebd367b4b81720ccd1bfdc841` |
| 被审执行报告 | `ebf6940a3eb710e801b7e238111dab7ee23f8138a7656dee36d46c87a898f0be` |
| 被审 protocol.json | `0d1e0021b6630d1046619d9360e7061474a0e0b7d9f05b1a30fd5a63a61e5f51` |

输入身份沿被审 baseline 与本轮独立复跑 manifest 核对，真实输入路径/区间均未变化。主控实际网络 0、依赖 0、账户路径 0、OKR 写入 0；只写主控报告、反例复跑文件及登记导航，未修改被审代码、测试、执行报告和旧 raw。

## 8. 给执行 agent：一轮集中收尾与停止条件

直接按 F1–F4 集中执行，不重新规划长任务、不每修一项就回主控。

1. 先保存当前身份，用 F1 的正确/错误来源控制组锁定失败测试，修当前编排对来源检查结果的使用。
2. 补新 CLI 的参数、日期与输出失败合同，保留正常 0/受限 2，不改底层 API。
3. 从同一结果补齐机器身份、卡依赖与人读错误原因，再完成本任务已有有限测试矩阵；保留既有已确认功能。
4. 一次真实三请求复跑、一轮完整回归，附新日志、指纹、保护核对和修订记录，最后交回主控。

**可写范围：** 本轮两份新实现、两份新测试、带修订记录的本轮执行报告、新编号的修复输出，以及对应 registry/INDEX 导航。被审协议与 attempts 保留，修订协议另存；主控反例与原登记表只读。不得改已收口的 data_quality/trading_calendar 等底层模块、v0、策略、输入、UI、生产或 OKR。网络/新依赖/新因子/新增账户均为 0。

建议最多两次完整回归、最多四次真实请求检查，局部测试按需。遇到必须更改冻结底层才能继续的事项，仅暂停受影响分支并提交独立反例；不越权修底层、不反复扩大审计范围。缺真实资料不是本轮待修缺陷。

收口条件：F1 错误来源请求不能再退出 0；F2 异常按合同终止且不留下完成假象；F3 身份、依赖和原因能从产物独立追溯；F4 报告不再把首报价当上市、不把既有计算说成从零不存在，测试覆盖与名称相符。满足后完成即停，不要求所有用途变为可用，不自行开启经济指数计算或因子第一波。

## 9. 最小决策卡与归档

| 必答项 | 回答 |
|---|---|
| 本轮判断什么 | 新离线入口是否完成任务书；当前部分确认、需集中收尾 |
| 基准与增量 | 原执行产物 0/2/2 可复现；独立来源哈希反例揭示组合遗漏 |
| 收益与代价 | 不适用：没有计算收益；修复仅限新入口与交接 |
| 当前行动 | 按 F1–F4 一次收尾，不扩大旧修复或新数据任务 |
| 权限 | 研究工程交付待复核；生产、真实交易、OKR 无授权 |

归档：本主控复核记录登记为“数据与质量 / mixed”，不是执行修复已完成。后续修订在本报告追加带日期记录，保留本次反例与初审结论。

## 10. 修复后复核与下一轮连续任务（2026-09-13，v1.1.0）

被审交付：[research-input-preflight-fix-2026-09-13.md](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/research-input-preflight-fix-2026-09-13.md)。本节覆盖初审中的当前状态，不删旧发现。

### 10.1 独立确认

- 本次完整回归实跑 **295 passed in 36.28s**，退出 0。命令为 §6 的原回归集合再加 `tests/unit/test_research_input_preflight_fix.py`，本次未修改被测实现。测试通过不证明所有异常已覆盖。
- 原独立复现脚本本次写入 [run-02/probe-summary.json](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-input-preflight-controller-review-2026-09-13/run-02/probe-summary.json)。正确来源合成控制组仍满足，错误来源对象请求改为拒绝，CLI 返回 2；未知对象返回 2。无日历的非法/倒置日期现有具体 evaluation 错误；Markdown 写盘失败返回 3，未生成 manifest。
- 三次真实请求 0/2/2，14 只 / 18,916 行。与执行者最新 `attempt-01-04`、`attempt-02-03`、`attempt-03-03` 的 integrity、data_uses、objects、findings、request_satisfied、errors 六组字段逐项相等。旧复现脚本的 `stable_fields_equal=false` 比较的是修复前产物，含本次新增元数据差异，不能当成本轮裁决退化。
- 原 896 项保护基线本次逐文件 SHA-256 复算，变化 0。未修改原反例、旧输入、对象登记、底层质量模块、生产或 OKR。
- 来源失败传递、完整卡/依赖与 binding 原因、规范指纹和错误说明已有实质补充。F4 关于首报价、既有经济指数计算和资料范围的纠正方向正确；不能把“已有代码”理解为真实输入资格已经合格。

### 10.2 未收口项：manifest 写出仍可未捕获失败

新独立证据：[probe_manifest_failure.py](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-input-preflight-controller-review-2026-09-13/probe_manifest_failure.py)，结果 [manifest-failure-summary.json](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-input-preflight-controller-review-2026-09-13/run-02/manifest-failure-summary.json)。仅在新合成输出中让 `_write_json(manifest.json)` 抛出 OSError，不改源码或真实磁盘权限。

实测：未捕获异常 `SYNTHETIC manifest disk failure`；main 未返回 3；manifest 不存在、FAILED.txt 不存在；部分 preflight.json 仍含 `request_satisfied=true`。脚本自身退出 0 表示成功记录了反例，不表示被测 main 成功。

原因是 manifest 构造、哈希读取与最终写入仍位于现有输出 try/except 之外。**不接受“全部写盘失败统一处理”的交付表述。** 下一轮 Task 1 将该阶段纳入同一异常出口，并补 JSON/Markdown/manifest/mkdir 有限矩阵，不重开全仓审计。

另据源码，显式 `--protocol` 指向不存在的文件时可写入 null 哈希。新任务正式运行必须绑定实际可读协议，因此同在 Task 1 补显式错误路径拒绝；省略参数的旧诊断兼容性保留。此项为源码检查发现，不冒称本轮已做动态反例。

本轮没有独立复验每一种元数据的全部边界，也没有安装 Qlib 或验证真实历史可知性；不把局部确认包装成整仓验收。

### 10.3 给执行 agent 的连续长任务

权威任务书：[已有动量指标研究样板 v1.0.0](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/superpowers/plans/2026-09-13-momentum-research-prototype.md)。按用户本次希望推进大任务，开始一个已登记指标的研究样板建设；这不是扩大为新因子/新数据/新账户。

1. 合并上述输出保护小修复，不单独消耗一轮交接。
2. 冻结 `mixed.momentum.raw@1.0.0`、经济指数依赖与唯一未来观察目标，复用已有计算。
3. 完成合成输入到动量、未来目标、排序诊断的完整可复算调用，验证价格和现金分红同步缩放等边界。
4. 固定真实输入只做允许的历史数值诊断；预测研究单独检查资格，当前受限就记录拒绝，不绕过。
5. 一次交付代码、测试、日志、指纹、已接入/未接入与缺口，交主控复核。

本次主控仅新增任务书、复核记录和隔离反例证据及导航，**没有执行该新研究任务**。任务书采用计划编写技能，把文件边界、接口、独立算例和阶段停止条件放在同一份计划；不增加第二套规范或登记表。

### 10.4 最新决策卡

| 必答项 | 当前结论 |
|---|---|
| 已确认什么 | 来源失败不再放行；295 项回归、真实三请求及保护核验已复跑 |
| 尚缺什么 | 最终输出失败处理；真实资料资格限制仍在 |
| 下一步 | 按新任务书连续执行：小收尾＋已有动量研究样板 |
| 不意味着什么 | 没有证明动量预测有效、没有新策略/账户，也没有生产或 OKR 授权 |

版本记录：1.0.0 为初审；1.1.0 新增修复后独立复核、manifest 反例及连续任务导航。归档类别/结论仍为“数据与质量 / mixed”。
