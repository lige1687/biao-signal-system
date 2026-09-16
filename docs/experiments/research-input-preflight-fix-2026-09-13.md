# 验收入口集中收尾：F1–F4 修复交付-2026-09-13

规范版本：`experiment-backtest-principles.md` v1.1；`definition-standard.md` 1.1.0；
`ai-execution-contract.md` 1.0.1；`experiment-report-template.md` 1.1.0

依据：主控复核单（验收 `research-input-preflight-2026-09-13.md`）F1–F4。
基线：`docs/experiments/raw/research-input-preflight-2026-09-13-fix-01/baseline.json`——
执行前已核对与主控被审指纹 6/6 一致。
网络 0 次、新依赖 0、新因子 0、新增账户 0；未运行收益回测；未写 OKR；
未改 data_quality / trading_calendar 等已收口底层、v0、策略、输入、UI、生产。
完整回归本轮跑了 **1 次**（上限 2），真实请求检查 **3 次**（上限 4）。

定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：

| 项 | 状态 |
|---|---|
| 定义清晰程度 | 不适用——未新增或修改任何登记对象 |
| 数据资格 | 有条件（不变；本修复让"核验失败被忽略"的口子被堵上） |
| 实现核验 | **295 项测试全过**（实跑计数）；ruff 干净；896 项保护零改动 |
| 有效性证据 | 不适用——本轮未计算收益 |
| 生产授权 | **无** |

研究状态：探索（修复交付）；**收口条件见 §6，完成即交主控复核。**

---

## 一句话结论（大白话)

**主控发现我上次交付的验收入口有个真漏洞：它发现"登记资料的来源文件被改过"之后，照样盖章"满足"。这次堵上了，顺手把出口合同和交接单也补齐了。**

三件事：

1. **来源核验失败现在真的会拦。** 主控做了个干净的实验：输入数据本身完全合格、
   对象字段也齐，唯独登记表里某个来源文件的指纹对不上——旧版照样退出 0。
   现在：有对象请求时，来源核验不过，**所有对象请求一律拒绝**（标 `blocked_by`），
   不再退出 0；没有对象请求时，如实记录"对象阶段未使用"，独立的数据结论保留。
2. **出口不再含糊。** 区间日期写反、参数打错、磁盘写失败这三种情况，
   以前会混在"正常拒绝"里甚至直接崩掉；现在统一退出 3（输入/运行失败），
   且磁盘写失败会留下 `FAILED.txt` 标记，**不会留下看着像成功的产物**。
3. **交接单能自己站住了。** manifest 现在绑定四份规范的实际哈希、本任务协议哈希、
   每个对象的完整定义卡与递归依赖、字段检查的原始原因；
   Markdown 会把"未知对象""用途不允许"的具体错误写出来，缺口按产品列定位，
   不再只有一行 False。

另外按主控要求纠正了我上一版报告里的三处错误说法（见 §4），
包括"11 只晚上市"和"economic_index 是没有实现的计算"——**这两句都是错的。**

---

## 1. F1：来源核验失败不能只写进"限制"

| 项 | 内容 |
|---|---|
| 主控反例（复现成功） | 合成输入（恒定名义价 + 恒定经济指数列，字段全齐）；把真实登记表复制到隔离目录、仅将 `mixed_code` 来源 SHA 改为 64 个 0（原表与来源文件未动）。旧版：`sources_verified=False`、`errors=[]`、`request_satisfied=True`、**CLI 退出 0** |
| 根因 | `verify_sources` 失败只写 limitations，最终合并不读它 |
| 修复 | `sources_ok=False` 时：有 refs → 每个对象标 `blocked_by="sources_unverified"`，合并检查叠加该条件，request_satisfied=False，CLI 退出 2；无 refs → `registry.objects_stage="skipped_no_refs"`，独立数据结论保留，并写明"此规则不得用于绕过有对象请求的失败"。`sources_error` 的具体文件与原因保留 |
| 测试 | 正确指纹控制组（成功）、错指纹（函数+CLI 拒绝）、错指纹但无 refs（数据路径保留）。隔离副本不是第二份权威登记 |

## 2. F2：失败出口合同

| 情形 | 修复前 | 修复后 |
|---|---|---|
| 无日历 + 区间倒置（06-30 → 06-01） | 退出 2、errors=[]（把非法请求当正常数据拒绝） | 入口自行校验日期（不依赖日历），errors 明确"属输入错误"，**退出 3** |
| 非法 CLI 参数（argparse 默认） | 退出 2，与"正常检查被拒"混淆 | `_Parser.error` 覆盖为**退出 3**；`--help` 仍为 0 |
| `preflight.md` 写盘失败（json 已写成） | 未捕获异常，无退出 3；留下 `request_satisfied=true` 的 JSON 无 manifest | 输出阶段捕获 OSError：stderr 明确、**退出 3**、能写则留 `FAILED.txt`、**不写 manifest**；目录不可写时直接返回 3 且不碰原内容 |

## 3. F3：可复现交接

| 缺项 | 补齐 |
|---|---|
| 规范只有名称/版本 | manifest 绑定四份规范（原则 v1.1 / 定义标准 1.1.0 / 执行合同 1.0.1 / 报告模板 1.1.0）的**路径 + 实际 SHA-256** |
| 协议/基线未绑定 | 新增 `--protocol` 参数，manifest 记录协议路径与哈希 |
| objects 只有 contract_digest | 每对象导出**完整解析卡与递归依赖**（`_resolve_closure`，生成物不手改）、`binding` 原结果（含 reasons）、`blocked_by` |
| input_times 只有首末日 | 保留快照 `timing`、时间语义说明、逐标的 `fetched_at/first_date/last_date`；`available_at` 继续为 null 并注明 |
| Markdown 不见具体错误 | 对象表显示 `error`/`purpose_error`/`blocked_by`；新增"缺口定位"表（产品 + 说明，长列表指向 preflight.json 的 findings） |

## 4. F4：报告与测试证据校正

### 4.1 纠正我上一版报告的三条错误说法

| 原说法（已纠正） | 实际 |
|---|---|
| "11 只**晚于评价期起点上市**……结构性，补数据改不了" | 只确认 **11 只首报价晚于起点，缺上市资格证据，原因未确认**。程序当前拒绝是对的，但"晚上市"这个解释没有证据，不能恢复 |
| "`economic_index` 是**未做的计算**，是唯一下一门槛" | **错。** 仓库已有 `definitions.economic_index`、`factor_runtime.reconstructed_economic_index` 与 `build_mixed_batch`，v0 已经算过。缺的是这批名义价快照与现有计算/定义的**合规接入及相应证据**，不是从零没有公式。历史重建与当时可知仍须分开；也不能把"三个指定对象缺字段"扩大成"全部 `mixed.*` 不可用" |
| "需要**全市场**停牌/复牌序列" | 超出固定 14 只与评价期。下一资料需求应先对准实际产品、缺口与用途，不预设扩全市场 |

### 4.2 测试证据校正（名称与实测一致）

| 问题 | 处理 |
|---|---|
| `test_same_path_different_fingerprint…` 实际用了 a/b 两个不同目录，名不符实 | 新增真正的同路径测试：同一 `snap` 目录先后改变输入（断言前后字节确实不同），两次检查的 rows 与 input 哈希均不同 |
| `test_counterexample_files_unchanged…` 只查文件存在 | 新增指纹锁：两份主控反例的 SHA-256 必须等于主控公布值（`bdd93488…`、`3b6520db…`） |
| 断网测试没有报告声称的"guard 先自证" | 补上：guard 先尝试建 socket、必须被它自己拒绝并输出 `guard self-check ok`，然后才跑入口 |
| 矩阵缺口：空/全缺失、区间内漏日、写出中断 | 已补：零标的不被当作满足（显式 `empty_instruments`）、区间漏日触发 `quote_on_unknown_calendar_day` 且 `day_incomplete_months` 命中、md 写失败（F2） |
| §6 回归命令有 `<15 个既有回归文件>` 占位；§8 只列截短哈希 | 本报告 §5 给出完整命令、日志路径与完整指纹 |

## 5. 实际命令、日志与完整指纹

```sh
# 三次真实请求（输出目录见下；退出码 0/2/2）
python3 scripts/check_research_input.py \
  --snapshot docs/experiments/raw/research-identity-wiring-2026-09-10/canonical-snapshot-v2 \
  --calendar docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json \
  --publication docs/experiments/raw/research-calendar-completion-2026-09-10/publication-evidence.json \
  --actions docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/action-sources/normalized-actions.json \
  --registry docs/research/definitions.v1.json \
  --start 2019-09-02 --end 2026-06-30 --use description \
  --protocol docs/experiments/raw/research-input-preflight-2026-09-13/protocol.json \
  --out docs/experiments/raw/research-input-preflight-2026-09-13/attempt-01-04
# attempt-02-03：同上 + --refs mixed.price.economic@1.0.0 mixed.momentum.raw@1.0.0 trend.sma200@1.0.0（退出 2）
# attempt-03-03：--use ranking --refs mixed.momentum.raw@1.0.0（退出 2）

# 完整回归（一次，295 passed，日志 /tmp 已不保留；可按此行复跑）
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
  tests/integration/test_research_input_preflight_cli.py \
  tests/unit/test_research_input_preflight_fix.py -q
# → 295 passed（退出码 0）

python3 -m ruff check src/lei_signal/research/input_preflight.py \
  scripts/check_research_input.py \
  tests/unit/test_research_input_preflight.py \
  tests/integration/test_research_input_preflight_cli.py \
  tests/unit/test_research_input_preflight_fix.py
# → All checks passed!
```

完整指纹（同时存于 `raw/research-input-preflight-2026-09-13-fix-01/final-fingerprints.json`）：

| 文件 | SHA-256 |
|---|---|
| `src/lei_signal/research/input_preflight.py` | `c4ed39dbde5d54624f727b6aaffe716650773c773de501b8d1ad3cfccf5a2dde` |
| `scripts/check_research_input.py` | `e20917ea673242820787b16b1b8f00e9951cba8944d301c7ae63767b42bf802e` |
| `tests/unit/test_research_input_preflight_fix.py` | `9ffb620e767dd475f62b3d5328a8d99befe923cefe2a20e7a9515be16beef59a` |
| attempt-01-04 preflight.json | `a1f5086aece8c74679636181ff6f9a9025611e21944a97427608d3117458178a` |
| attempt-02-03 preflight.json | `9675d0b66d7722b57c994f6a239646196553379e0b3c3a1d42daba1bfd293837` |
| attempt-03-03 preflight.json | `b4753c0095ba40c36b7f5a08675bcca8874b8888726007d8720d3b7e15d19670` |

既有两个测试文件（`test_research_input_preflight.py`、`test_research_input_preflight_cli.py`）本轮未改；896 项保护基线零改动；主控两份反例与真实登记表只读。

## 6. 收口条件核对（主控 §8）

| 条件 | 状态 |
|---|---|
| F1 错误来源请求不能再退出 0 | ✅ 函数与 CLI 均有断言（错指纹 → 退出 2、`blocked_by` 可见） |
| F2 异常按合同终止且不留下完成假象 | ✅ 倒置/参数错误 → 3；写盘失败 → 3 + `FAILED.txt` + 无 manifest |
| F3 身份、依赖和原因能从产物独立追溯 | ✅ manifest 绑定规范/协议/输入/代码哈希、完整卡闭包、binding 原因；Markdown 显示具体错误 |
| F4 报告不再把首报价当上市、不把既有计算说成从零不存在；测试覆盖与名称相符 | ✅ §4 已逐条纠正；同路径/指纹锁/guard 自检/矩阵缺口已补 |

**真实数据裁决不变**：描述/诊断可用；ranking、comparison、research_signal、
attribution 继续受限；三个指定对象仍缺 `economic_index`。
没有要求所有用途变为可用；**不自行开启经济指数计算或因子第一波。**

## 7. 失败史（本轮自己的错误）

1. F2 的 manifest 里 `input_times` 被我加成两处（新块 + 旧块），ruff F601 抓到；
   删除旧块。
2. F4 补丁中 `shutil` 导入多余、两处格式问题，ruff `--fix` 处理。
3. 空快照最初会"成功"——零标的既没有 finding 也不报错，是我自己矩阵里的
   "空/全缺失"案例逼出来的：`empty_instruments` 显式拦截。
4. 一处 CLI 里 try/except/pass 被 SIM105 提示，改 `contextlib.suppress`。

## 8. 给主控的交接

- 收口条件四条已全部落实并可复跑（§5 命令）。
- F1 的拒绝策略是**保守**的：任一来源失败即拒绝全部对象请求，
  未做"该来源究竟影响哪些对象"的依赖影响分析——那是后续可选项，本轮按要求不做。
- `attempt-01-04` 是 description 无 refs 的正向路径（退出 0）；四个受限用途与
  三对象缺 `economic_index` 在产物中依然可见，未被本轮修复掩盖。
- 待确认事项：无新增。真实资料缺口（行动到达时间、停牌源、上市资格、
  `economic_index` 合规接入）均为另行授权事项，不是本轮待修缺陷。

**完成即停，交主控复核。不宣布策略有效、因子有效、OKR 完成或获准交易。**
