# 因子开工前：研究输入离线验收与交接 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans 按阶段连续执行。Steps use checkbox (`- [ ]`) syntax。用户将本任务书交给执行 agent 后即按此限定范围开展；不是让主控现在代为执行，也不要求重新规划。没有必要不派子 agent，不自动提交代码。

**Goal:** 交付一个能实际运行的离线研究输入检查入口，让后续因子任务知道“是哪批数据、能用于什么、缺什么、哪些旧程序尚未接入”，不再凭一份通过报告或几个标签开工。

**Architecture:** 新增薄编排层，复用现有快照读取、日历、行动核验、用途判定及唯一定义登记表。输入检查与因子计算分开，输出 JSON 及从同一 JSON 生成的 Markdown，不另造质量规则、来源信任平台、因子库或回测引擎。

**Tech Stack:** 项目现有 Python、pandas、pytest、ruff 与标准库；无新依赖、服务、数据库或 UI。

## Global Constraints

- 版本 1.0.0；日期 2026-09-13；研究家族 `research-data-foundation`；任务 ID `research-input-preflight-2026-09-13`。性质：研究输入工程与检查接入，不是预测、政策比较或收益解释。
- 用户本次：“docs/experiments/research-controller-fixes-2026-09-13-02.md 做完了，这次能不能给一个长任务”。本计划延续“不增加新因子、新数据或账户路径”的范围。
- 本任务服务研究可信度层，不改交易规格中的道路、路牌、入场、退出、回补或资金规则。真实交易、生产、OKR 写入、联网、付费、新增依赖均无授权。
- 主控已在[复核报告 §11](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/research-data-foundation-controller-review-2026-09-13.md)确认 R1 剩余修复；R1/R2/R3 不再作为未完成返修。不要恢复已经否决的“合成材料等于真实资格”逻辑。
- 只读既有本地输入与明确引用的文件。不得下载上市资料、公司行动、因子包或行情；不得改产品池、日期窗口、价格口径、填补缺失或捏造 available_at。
- 不安装或运行 Qlib/Alphalens；不做未来收益目标、排序相关性、分组收益、参数搜索或账户模拟。v0、快速回补与过滤政策保持冻结；不修改其运行脚本或登记对象。
- 新输出拒绝覆盖；在全新目录保存每次尝试。不得执行旧脚本 main，不改旧 raw；不使用全仓暂存、强制回滚或大范围文本替换。
- 工程完成不要求全部数据用途放行。只有描述/诊断可用、三个指定对象仍缺 economic_index，是允许的真实结果。

## 0. 本轮真正要交付什么

一个新研究任务不再分别猜五个函数怎么组合，而是运行一次检查，拿到：原文件身份、完整性、质量问题、六种用途的默认结论、指定对象的完整卡与缺项、输入声明和实际字段的差异、真实可得时点的未知项，以及尚未接入的程序清单。

不在本轮修齐所有资料。尤其**不把名义收盘价改名成 economic_index**（按登记规则处理分红拆分后的经济指数），也不因“以后可以计算”就说现在已经提供该字段。

四个独立结果必须保留：

1. 快照是否完整；
2. 该批数据是否满足所请求用途的现有质量与声明检查；
3. 对象是否允许该用途，且实际输入满足其已实现的字段检查；
4. 是否已实际计算、是否有效、是否获准交易——本轮后三项均不获得肯定结论。

## 1. 开工读取与准确绑定

先读根 AGENTS、相关目录 AGENTS（若存在）、交易规格与规则账本、以下规范和最新复核。路径均以仓库根为基准；换机器先定位仓库，不照搬本机路径。

| 权威文件 | 版本 | 本次 SHA-256 |
|---|---|---|
| `docs/research/experiment-backtest-principles.md` | 1.1 | `ac5a676c0635441b66f656c8e1249b69bade36365cc9065ed6341a610b6a53c6` |
| `docs/research/definition-standard.md` | 1.1.0 | `3406feaea2bbb8d23a91ddc8fa0c85e62ff86437bdf443d459f2c97b0e99cd5c` |
| `docs/research/ai-execution-contract.md` | 1.0.1 | `deab6c1ca20505f92d06516ffff943b8501fff2e01f8c6b3928c6626072af962` |
| `docs/research/experiment-report-template.md` | 1.1.0 | `cae2853f81841de6f424c6bda10e6708dd35574ebb8a325088fe507c5755d54e` |
| `docs/research/definitions.v1.json` | 每对象精确版本 | `c008efb991c40f06bb7fe0236b0892a6902c68a83cb4657ae5c2651e9d270e05` |

还需读：最新执行报告 `docs/experiments/research-controller-fixes-2026-09-13-02.md`；总报告只用于追踪缺口，不能采用已撤回的“排序数据缺陷清零”；`docs/research/factor-phase0-decision-brief-2026-09-10.md` 的 P1/P2/P3 仍不是本任务替用户拍板的事项。旧 v0 计划只核冻结与禁止改动范围，不重新执行。

首批引用仅三个已有对象（不是新增计算任务），用 `definitions.resolve` 解析完整卡：

| 对象 | 本次读到的用途 | 实际依赖字段 |
|---|---|---|
| `mixed.price.economic@1.0.0` | description / research_signal / attribution | date, symbol, economic_index |
| `mixed.momentum.raw@1.0.0` | ranking / description / research_signal | date, symbol, economic_index |
| `trend.sma200@1.0.0` | description / diagnostic | date, symbol, economic_index |

用途不能统一改成 diagnostic 来避开对象限制。解析卡用于盘点时可不请求用途，但真正的“用途检查”必须传入准确 purpose。递归记录依赖的精确版本，不建立第二张手写对象登记表。

固定真实输入，评价期 **2019-09-02 至 2026-06-30**，冻结全池 14 只、18,916 行；数量须实读核对，不能硬填结果：

| 输入路径 | SHA-256 |
|---|---|
| `docs/experiments/raw/research-identity-wiring-2026-09-10/canonical-snapshot-v2/snapshot.json` | `d4e6518b957d06a50189a574cbd547a98e479bae872a284c0718febff781ce27` |
| `docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json` | `aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1` |
| `docs/experiments/raw/research-calendar-completion-2026-09-10/publication-evidence.json` | `657ef122c62aefcf8d580e5e20e85beac8b1a0979c399f3529ae30d6b245ef02` |
| `docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/action-sources/normalized-actions.json` | `097043b2c622a308b602a961b666129f575a35083a8ede6d7bfa1cf16ea1ce81` |

快照 CSV 的身份逐项从 snapshot/manifest 复核，不能只核上表 JSON。日历路径和哈希不等于发布时点已获证明；保留既有跨所、年度覆盖限制。

## 2. 文件范围与资源上限

新增文件（若已有同职责实现先查，复用并在协议说明，不再新建等价模块）：

| 路径 | 职责 |
|---|---|
| `src/lei_signal/research/input_preflight.py` | 薄编排、合并检查、固定输出结构；不实现新价格公式或来源资格 |
| `scripts/check_research_input.py` | 完全离线命令入口，无 acquire 分支 |
| `tests/unit/test_research_input_preflight.py` | 组合判定、身份与失败边界 |
| `tests/integration/test_research_input_preflight_cli.py` | 真实子进程命令、退出码、文件不覆盖与断网验证 |
| `docs/experiments/research-input-preflight-2026-09-13.md` | 本轮执行报告及后续开工交接 |
| `docs/experiments/raw/research-input-preflight-2026-09-13/` | 仅新建；协议、清单、测试日志、逐次新输出、消费者映射 |

允许更新当前计划复选框、执行报告及其 registry/INDEX 登记。若公共导航被并发修改，交回准确登记建议，由主控合并，不覆盖对方内容。

既有 `data_quality.py`、`data_snapshot.py`、`trading_calendar.py`、`symbol_identity.py`、`definitions.py`、`factor_runtime.py`、`factor_diagnostics.py`、`factor_account_adapter.py`、旧 CLI 和旧测试本轮只读。发现其问题先由新入口拒绝/隔离并留反例，不借任务扩大到再次重写底层；无法安全隔离则暂停该分支。

保护基线：沿用 `docs/experiments/raw/research-data-provenance-round2-2026-09-10/protected-baseline.json` 的 896 项，另加以上既有代码、当前研究规范及主控两份反例的开工指纹。不把新增输出本身纳入运行前基线，避免循环哈希。

建议集中一轮完成，资源上限：联网 0、新增依赖 0、账户路径 0、真实输入检查最多 8 次（非收益运行）；完整回归最多 3 次，局部测试不限但不得无意义循环。总执行时间上限 6 小时，到限交部分产物与精确阻断，不为了“长任务”刻意耗时。每阶段自验通过后直接下一阶段，不逐项回来要许可。

## 3. Task 1：冻结本轮身份与消费者清单

**Files:** 新输出目录中的 `protocol.json`、`baseline.json`、`consumer-map.md`。JSON 是本任务记录格式，不宣称通用协议校验器已经存在。

**Interfaces:** 消费上述固定路径与当前实际代码；产生后续运行使用的文件指纹、任务版本、固定区间、用途枚举及可写范围。

- [ ] 记录 `git status --short`、HEAD、实际文件 SHA-256、Python/依赖版本。核对本计划指纹，漂移只暂停受影响输入，不覆盖别人修改。目录已存在用新的 attempt-NN，不覆盖旧尝试。
- [ ] 逐文件核对 896 项保护基线，保存算法与结果；保存两份主控反例原字节哈希，不把后来重写的文件冒充原反例。
- [ ] 运行如下只读检索，逐个实际入口记录“读取快照 / 验哈希 / 检查用途 / 传声明 / 绑对象 / 真的计算 / 是否冻结”。函数存在不等于消费者已调用。

```sh
rg -n 'check_prices\(|check_snapshot\(|require_use\(|bind_definitions\(|build_mixed_batch\(' scripts src/lei_signal/research
```

当前已看到：旧 `scripts/run_research_data_snapshot.py::_run_quality` 调用 check_prices；`cmd_verify` 先核 loaded.verified；`cmd_bind` 没有绑定具体快照。`factor_runtime` 是另一条冻结研究计算链。它们本轮只映射 legacy 或未接入，不强制迁移、更不能倒填本任务合规版本。

**阶段验收：** 消费者清单逐项有代码位置和判断依据，协议能明确下一阶段读取哪批资料；没有新增数据或改变政策。

## 4. Task 2：复用现有能力构造薄检查入口

**Files:** 新增 `input_preflight.py` 和对应单元测试。

**拟实现接口（当前尚不存在；执行后才可宣称实现）：**

```python
def inspect_input(*, snapshot_dir, calendar_path, publication_path,
                  actions_path, registry_path, refs: tuple[str, ...],
                  use: str, evaluation_start: str, evaluation_end: str) -> dict:
    """只读检查，返回可JSON序列化的报告；不运行因子或账户。"""

def combine_checks(*, integrity_ok: bool, data_use_ok: bool,
                   object_checks: tuple[bool, ...]) -> bool:
    return integrity_ok and data_use_ok and all(object_checks)
```

`combine_checks` 只是本次请求的合取，不能成为新质量规则或可信标签入口；公开命令不接受调用者传这几个布尔值。

- [ ] 先写独立真值测试再实现小函数，不能用被测输出生成期望值：

```python
def test_combination_requires_every_check():
    from lei_signal.research.input_preflight import combine_checks
    assert combine_checks(integrity_ok=True, data_use_ok=True,
                          object_checks=(True, True)) is True
    assert combine_checks(integrity_ok=False, data_use_ok=True,
                          object_checks=(True,)) is False
    assert combine_checks(integrity_ok=True, data_use_ok=False,
                          object_checks=(True,)) is False
    assert combine_checks(integrity_ok=True, data_use_ok=True,
                          object_checks=(True, False)) is False
```

- [ ] 接口调用顺序固定：`load_snapshot` → `TradingCalendar.from_file` → `check_snapshot`（传完整行动与固定评价期）→ `require_use`（带 `loaded.declared_uses`）→ `load_registry/validate_registry/verify_sources` → 每个 ref 的 `resolve(..., purpose=use)` 与 `bind_definitions(..., snapshot=loaded.snapshot, purpose=use)`。不把“缺一项就报错退出”作为唯一输出，合法但受限的数据需保留全部原因。
- [ ] 不信任调用者的 `verified=True`、字段列表、币种、quality-report.json 或自填上市证明。本入口从路径重读并核实；跨产品实际字段不一致时逐产品列出，不能用并集掩盖单产品缺项。日期索引如何对应 date 字段要明确记录。
- [ ] 绑定是已有机械字段检查，不是完整公式语义证明。不要向 `provided_fields` 填不存在的 economic_index，不改币种字符串让绑定通过。不自动运行经济指数生成或重解释原价口径。
- [ ] 用途限制分层报告：数据描述可用不意味着某个不允许 description 的对象也可用；对象不允许用途、错版本、缺字段分开记录。refs 为空时只检查数据，不声称因子接入。
- [ ] 默认不启用 `allow_conditional` 或 `accept_structural`，新命令也不暴露这些开关；保持底层 API 原语义不变。若审计显示“启用 accept_structural 后仍拒绝”，那只是额外诊断，不进入默认接受逻辑。
- [ ] 只读原始公司行动 `events` 容器中的记录，内容仍交 `check_actions/check_snapshot` 验证，账户 events 不得混入。记录该容器映射、21 条行动和停牌引用，不调 factor_runtime 的会丢弃停牌的规范化函数来检查缺口。
- [ ] 对文件缺失、非 JSON、JSON 顶层类型错误、日期/身份错误保存明确失败，不能吞异常后返回空 findings/成功。I/O 或解析失败不得进入后续计算；新入口可做最小类型检查，不重写来源资格规则。

运行：`python3 -m pytest tests/unit/test_research_input_preflight.py -q`；先确认新增断言因缺接口或错误结果失败，再实现并保存通过日志。

**阶段验收：** 只使用实际读取的输入得到报告；真假资格不靠调用方自填值，负例不能绕过组合判断；真实对象缺经济指数继续标缺。

## 5. Task 3：命令、机器输出与交接报告使用同一结果

**Files:** 新增 `scripts/check_research_input.py`、CLI 测试；复用 Task 2 返回 dict。

拟定命令参数：`--snapshot --calendar --publication --actions --registry --start --end --use --refs --out`；`--refs` 为零到多个准确引用，其余输入显式传入。无联网、参数优化、覆盖或数据修复选项。

- [ ] 在全新 `--out` 写 `preflight.json`、`preflight.md`、`manifest.json`。已有目录直接拒绝，不覆盖也不隐藏换目录；调用者显式选择新 attempt-NN。先保留临时失败状态，输出不完整时不能留下成功 manifest。
- [ ] `preflight.json` 至少含 `schema_version`、`request`、`integrity`、`data_uses`（六种）、`objects`、`request_satisfied`、`errors`、`limitations`、`calculation_run=false`、`production_authorized=false`。对象逐项含 resolved、purpose_allowed、missing_fields、binding 原结果及完整卡指纹；不能一个总通过掩盖其他层失败。
- [ ] `data_uses` 明确区分质量 verdict、快照声明、默认 require_use 是否接受及原因。生成 Markdown 时只读同一个 dict，不重新猜测或手抄成更乐观的结论。
- [ ] `request_satisfied=true` 仅表示本次已实现的输入检查满足，不等于公式实现、历史可得时点、因子有效或交易授权；未覆盖项始终旁列。三个指定真实对象本轮预计均不能满足字段检查。
- [ ] manifest 记录规范实际版本/哈希、refs/依赖/卡哈希、代码哈希、所有输入哈希、生成时刻和原输入各类时间、评价期、协议哈希、输出文件哈希。`generated_at` 不得代替 `available_at`；未知保持 null/原因。不写自包含 manifest 的循环哈希，不调用旧 make_manifest 后伪称已支持新字段。
- [ ] 退出码约定：0＝请求的检查满足；2＝检查完成但请求被拒；3＝输入/参数/解析或运行失败。退出 2 是有价值的检查结果，不在报告写成崩溃；CLI 非零时也必须保留已可安全保存的原因。输出路径不可写或已存在时 stderr 说明且不碰原内容。

接口壳采用 `main(argv=None) -> int` 与 `if __name__ == '__main__': raise SystemExit(main())`；导入无顶层执行。运行 `python3 scripts/check_research_input.py --help` 应只打印帮助，无网络或输出目录副作用。

**阶段验收：** 子进程输出、退出码、JSON、Markdown 的结论一致；受限状态不冒充成功，无旧路径覆盖。

## 6. Task 4：集中完成组合边界测试，不再只测试单个标签

**Files:** 两个新增测试文件；合成输入在测试 tmp_path，不加入真实来源登记。既有测试只重跑，不改预期来迎合新结果。

- [ ] 按下表逐项写 fixture、独立期望与最终 CLI/函数断言；每项断言到 request_satisfied 或退出码，而非只检查字段存在。允许多个边界共用小夹具，不造大型数据工厂。

| 测试情形 | 最终应观察到 |
|---|---|
| 合法完整快照、只请求数据 description、无 refs | 成功正向路径，不得一律拒绝 |
| 同一快照但产物不声明该用途 | 拒绝且指明 not_declared，质量可用也不能覆盖 |
| CSV 被改、删列或缺文件；旧报告仍显示 verified | 新读取拒绝，旧报告不生效 |
| 价格口径/币种/字段由命令试图覆盖 | 无该参数；不能靠声明改变结果 |
| 单产品缺字段，另一只具有该字段 | 不能用并集宣布全批满足 |
| 两份主控固定上市反例 | 原 8 判断继续拒绝；反例文件指纹不变 |
| 非法账户 events 冒充停牌 actions | 记录污染原因，不能用于消除缺口 |
| 合法停牌 | 仍能追踪到 event_id，不因此证明当时可交易 |
| 缺日历、区间内漏日、非法日期键 | 清楚拒绝/受限，不回退工作日当真日历 |
| 空/全缺失、非法顶层 JSON、非法区间 | 明确失败原因，无空成功 |
| 不存在对象、错版本、禁用用途 | 分别拒绝；不解析 latest 或降级默认用途 |
| 真实名义价绑定三个指定对象 | economic_index 缺失，不能把 close 改名补足 |
| 人为改写已保存的 preflight 结果或 manifest 标签 | 重新运行从原输入读取，不信旧通过结果 |
| 相同请求重复运行 | 稳定结果字段一致；仅生成时刻/输出位置等明确易变字段可不同 |
| 同一路径不同输入指纹 | 新输出明确不同身份，不沿用旧质量判断 |
| 输出目录存在、写出中断、断网运行 | 旧文件不变；无成功假文件；断网仍能完成合法检查 |

断网测试用测试进程封锁 socket/HTTP 调用并执行导入与检查；CLI 子进程必须也覆盖，父进程 monkeypatch 不自动约束子进程。记录真正拦截的方法，不将 `network_calls=0` 自填字段当证明。测试临时文件的构造/破坏后先 assert 新旧字节确实不同，避免篡改测试假通过。

**不强制跑变异工具。** 有限矩阵完成就结束；新发现的无关消费者问题进未接入表，不横向修全仓。

## 7. Task 5：一次真实输入交接批次、完整回归与收口

**Files:** 新输出 attempt 目录、执行报告、登记导航。只跑检查，不计算新的因子值或收益。

- [ ] 执行第一条请求，生成六用途清单，同时检查数据 description（无 refs）：

```sh
python3 scripts/check_research_input.py \
  --snapshot docs/experiments/raw/research-identity-wiring-2026-09-10/canonical-snapshot-v2 \
  --calendar docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json \
  --publication docs/experiments/raw/research-calendar-completion-2026-09-10/publication-evidence.json \
  --actions docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/action-sources/normalized-actions.json \
  --registry docs/research/definitions.v1.json \
  --start 2019-09-02 --end 2026-06-30 --use description \
  --out docs/experiments/raw/research-input-preflight-2026-09-13/attempt-01
```

预计退出 0，仅表示数据描述请求满足；六用途中的四项受限不能隐藏。随后保持所有输入/区间相同，仅在新 `attempt-02` 添加 `--refs mixed.price.economic@1.0.0 mixed.momentum.raw@1.0.0 trend.sma200@1.0.0`：预计退出 2，三个对象缺 economic_index。第三次 `attempt-03` 请求 `--use ranking --refs mixed.momentum.raw@1.0.0`，应分别暴露数据限制及输入字段缺失。参数变更不是新策略试验，不选择更好看的窗口。

- [ ] 若实际与预计不同，先核输入与实现，保存首个差异；不可通过改输入、删产品或填字段追齐结果。因新入口发现过去未纳入的来源限制而更保守，须说明依据，不默认它错了。
- [ ] 重跑全部现有 15 个回归文件（命令见被审报告 §4），另加本次两个测试文件，记录实际总数、退出码、日志、失败史；不把 253 作为必须凑齐的目标。
- [ ] 运行 `python3 -m ruff check src/lei_signal/research/input_preflight.py scripts/check_research_input.py tests/unit/test_research_input_preflight.py tests/integration/test_research_input_preflight_cli.py`，并核保护基线和全部改动清单。
- [ ] 最终报告写五项独立状态、实际接入调用链、消费者已接入/legacy 表、每项数据缺口影响哪个用途。资金贡献、政策增量、风险因子解释均写“不适用：本轮未计算收益”。
- [ ] 交出“下一阶段最小资料需求表”：现有本地证据、缺哪条原始事实、影响哪项判断、为何不能由哈希/自填标记代替、建议验收方式。上市资格、公司行动到达时间、economic_index 生成与绑定分别列出；只做需求，不采集、不自动选供应商、不建信任白名单。
- [ ] 将新报告登记“数据与质量 / mixed”，INDEX 指向本次真实产物；旧总报告仅加最新状态指针，保留历史正文。这里允许的旧文档补充仅限 `research-data-foundation-summary-2026-09-10.md` 顶部指针，不改旧结果。
- [ ] 补齐所有改动文件的完整 SHA-256，包括测试；检查报告链接及实际报告库抽取。生成完整交接后停止，交主控复核，不自行宣布因子第一波可以开工。

## 8. 完成、暂停与交付给主控

完成标准：另一个 AI 只凭协议和相同本地输入，能运行同一命令，得到同样的稳定判定字段、对象缺项与拒绝原因；也能看见哪些功能并未实现。真实对象仍受限不妨碍本次工程交付。

阶段 1–5 连续完成；只有代码/输入漂移、无权写入、无法隔离的底层错误、资源超限或涉及新交易/数据定义时暂停受影响项。其余独立文档、映射与测试继续交付。暂停不代表可以改冻结协议或开展新实验。

主控期望收到：一个简短结论、执行报告路径、三次真实输入检查目录、独立反例与正向测试、完整命令/计数/指纹、已接入和未接入表、原始证据需求表，以及确切的待确认事项（没有就写无）。

**本计划不是已经实现的接口。主控本轮只完成计划与 R1 复核；执行者下一轮提交代码、测试和产物后，才评价上述入口是否建成。**
