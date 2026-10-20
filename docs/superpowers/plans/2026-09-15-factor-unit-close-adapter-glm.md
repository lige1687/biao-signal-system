# 双均线独立研究 B0：收盘价适配与真实输入冻结 Implementation Plan

> **For agentic workers:** 使用可用的 `executing-plans` 技能按任务执行；没有该技能时按本文逐项执行，不安装技能。本轮单个 GLM 顺序负责，不派并行修改同文件的 agent。每项先写反例测试，再实现，再验证。

**Goal:** 交付可复用的收盘价状态研究适配、四市场输入的来源裁定，以及不需要重规划便可进入真实历史研究的冻结候选协议。

**Architecture:** 在研究目录新增隔离模块，复用已有均线、颜色和双均线函数；不修改仅供合成研究的 factor_lab v1.2.0。对象仍引用原候选卡，数据/日历/用途资格另列；未知来源的市场只给原因，不假装已经能检验。

**Tech Stack:** 现有 Python/pandas/numpy/pytest/ruff；不新增依赖、网络、市场数据或账户引擎。

版本 v1.0.0，2026-09-15。本文是可转交执行规格，不代表此刻已经派发。用户明确让执行者开始本文，才授权下述 B0 离线范围；B1 真实统计仍需主控确认后另行授权。

## Global Constraints

- 工作目录固定 `/Users/yongbiaoli/Desktop/lei-signal-lab`；分支固定 `codex/factor-unit-research-20260915`。开工先核对 `pwd`、`git branch --show-current`、`git rev-parse HEAD` 和 `git status --short`。主控核对时 HEAD 为 `8ba16576b75e605aa1b0d0902568c760c4b99095`；变化先记录归属，有冲突只暂停受影响项。
- 大量成果未提交，必须用此原目录；不要另开空仓、克隆、从 HEAD 建新工作区。不得切换分支、暂存、提交、stash、reset、clean，不恢复他人文件。
- 先读根及目录 AGENTS；研究原则 v1.1、定义标准 v1.1.0、AI 执行合同 v1.0.1、报告模板 v1.1.0；唯一登记表 `docs/research/definitions.v1.json` 容器版本 1.2.0。运行时核实际版本和指纹，不把本段当免核凭据。
- 策略溯源读 `docs/trading-spec-v1.md` §4.1、`configs/rules.v1.yaml`、实际加载的 `configs/rules.v2.yaml`、`.claude/skills/macd-reading/SKILL.md`、`docs/plan-sector-trend-page.md`。本轮服务“道路/双均线当前状态”的研究层，不改交易规则。
- 读 A 阶段报告与本次主控报告 `docs/experiments/factor-unit-readiness-controller-review-2026-09-15.md` v1.0.0；主控 R1–R6 优先于 A 阶段不可执行提案。原提案不覆盖、不补写成正式协议。
- 对象唯一引用 `candidate:lei.dual_ma.bull_state@draft-1`，卡文件为 `docs/experiments/raw/factor-research-workbench-v1-2026-09-14/candidate-card-dual-ma-bull-state-draft-1.md`。不得称它已进入正式登记表。公式不变；新输入合同单独版本化，不偷换旧卡身份或用途资格。
- 冻结旧 factor_lab 全包、`scripts/run_factor_lab.py`、原测试、原 raw、规则与生产/UI。不修改 `definitions.v1.json`。不为了复用强行把 real 模式塞进旧 runner。
- 零联网、零安装、零密钥、零真实因子—目标统计、零账户/交易/OKR写入。真实输入只做结构、来源、身份、日历对齐、行动边界和资格检查；不能提前看表现再选协议。
- 四个载体仅 `510300 / 159915 / SPY / QQQ`，不是因子库永久标的池。不得增删换赢家；本轮不跑宽度或情绪的新表现、不加窗口网格、不按牛熊筛时期。

## 文件范围与交付

新增（若已存在先核归属，不覆盖）：

- `src/lei_signal/research/factor_unit/__init__.py`
- `src/lei_signal/research/factor_unit/close_state.py`：最小收盘价适配。
- `src/lei_signal/research/factor_unit/study_contract.py`：用途、来源、日历与参数校验。
- `src/lei_signal/research/factor_unit/state_description.py`：仅以合成资料验证的未来目标与描述统计。
- `scripts/check_factor_unit_readiness.py`：离线资格检查与冻结候选包，不自动运行真实统计。
- `tests/unit/test_factor_unit_close_state.py`
- `tests/unit/test_factor_unit_study_contract.py`
- `tests/unit/test_factor_unit_state_description.py`
- `tests/integration/test_factor_unit_readiness_cli.py`
- `docs/research/factor-unit-usage.md`：新消费者手册，引用权威规范，不另写总纲。
- `docs/experiments/factor-unit-close-adapter-2026-09-15.md`
- `docs/experiments/raw/factor-unit-close-adapter-2026-09-15/`：本轮全部快照、日志、来源表、纠正附录、协议候选、代码原字节包。

可改：实验 registry 只新增本报告，INDEX 只补导航。A 阶段报告只在顶部加本轮纠正指针；A 阶段 raw 不改。不得把计划示例 JSON 宣称为既成接口。

## Task 0：开工身份与六项纠正（独立可验收）

- [ ] 保存工作区状态、允许修改清单、保护文件 SHA。保护至少覆盖 A 阶段 `protection-before.json` 所有明确路径、原三份终版协议/manifest、候选卡、四份价格输入以及旧原型完整源码。
- [ ] 在本轮 `readiness-corrections.md` 逐条回应主控 R1–R6，保留旧值/旧说法与纠正依据，不“修好后当初就正确”。
- [ ] 明确收盘价输入不是删减策略条件：它只剥离无关的 ATR、MACD、成交量计算；完整共同确认仍调用旧函数。
- [ ] 记录 SMA/EMA 条件关系成立的假设及浮点临界限制；状态 false 不是看空，未就绪不是 false。删除“价格缩放已验证分红缩放”的扩大表述。

验收：不改旧 raw；六条有明确处理；旧原型源码零变化。

## Task 1：实现 close-only 薄适配（独立可验收）

接口固定：

```python
def compute_close_state(close: pd.Series) -> pd.DataFrame:
    """返回 close/ema20/sma20/close_lag20/signal_color/state/missing_reason。
    state 使用可空布尔；索引保留；禁止排序、去重或补价后静默计算。
    """
```

实现依赖仅复用 `features.indicators.seeded_ema(close, 20)`、`rules.lei_color.classify_colors(frame)`、`rules.dual_ma.dual_ma_bull_state(frame)`；SMA 用 `rolling(20, min_periods=20).mean()`，lag 用 `shift(20)`。不调用依赖 OHLCV 的 `compute_features`，不复制旧函数公式实现。

- [ ] 先写测试：只有收盘价的 21 行可运行；20 行未就绪；`[100]*20+[105]` 最后 true，恒定和最后99为 false；不需成交量、高低价。
- [ ] 重复/乱序日期、非正值、无穷值报错；NaN 保留。前导 NaN 按旧 seeded_ema 语义；内部 NaN 导致旧 EMA 后续不可用时诚实传播，不擅自跳过/重启。所有当前及前一日均线、lag、颜色准备好才产生有效布尔。
- [ ] 独立手算 EMA 种子和后续递推、SMA 含当日；生产函数只作观察输出，不能拿被测结果当期望。
- [ ] 在合成完整 OHLCV 上与旧调用链逐行比对，记录差异键、值、原因；靠“最后一个状态相同”不能通过。
- [ ] 固定输入前缀不变、仅追加未来资料，既有输出不变；价格同比放大100倍后非临界状态不变，数值归一后容差 `abs(actual-expected)<=1e-10*max(1,abs(expected))`；布尔/键集合精确相同。
- [ ] 含分红小例如果采用目标财富尺度，则将价格和每份现金分红同步缩放；拆分比例不随货币缩放。未实现分红消费就明确该测试不适用，不能谎报覆盖。

示例断言（被测模块新增后生效）：

```python
def test_close_only_has_nullable_warmup():
    idx = pd.date_range('2020-01-01', periods=21, freq='D')  # 合成观察序号，非真实交易日历
    got = compute_close_state(pd.Series([100.0]*20+[105.0], index=idx))
    assert got['state'].iloc[:20].isna().all()
    assert bool(got['state'].iloc[20]) is True
```

运行 `python3 -m pytest tests/unit/test_factor_unit_close_state.py -q`；先失败留档，再最小实现至通过。

## Task 2：四份输入来源追踪，禁止猜复权（独立可验收）

输入只用 A 阶段清单绑定的 `/Users/yongbiaoli/.lei_signal_lab/cache/timing/{510300,159915,SPY,QQQ}.parquet`，先重算完整哈希。变化则本轮标新快照，不静默替换 A 阶段身份。

- [ ] 读取 `scripts/backfill_timing_data.py` 和 `src/lei_signal/timing_backtest/data.py`。A 股存在前复权优先/不复权回退；美股 auto_adjust 的代码存在不等于文件来源已证。
- [ ] 最多追踪 8 份直接相关本地日志/manifest/生成记录；可搜索文件路径与哈希，不能无限恢复旧历史。记录检索命中与未找到；不要运行生成脚本的 main。
- [ ] 产出 `source-decision.csv`，逐载体包含：文件哈希、实际绑定的生成代码/日志、供应商、调整口径、公司行动边界、币种、资料覆盖、许可所知、fetched_at证据、available_at证据、允许用途和拒绝原因。
- [ ] 必须区别 `producer_candidate_only`、`snapshot_provenance_bound`、`price_basis_verified`；自填 verified=true、文件名、mtime、存在官方网页都不是来源绑定。
- [ ] 可以查现有原始行动/同源冻结价的少量边界是否吻合，但只说明“此边界吻合”；不外推整段总回报资格。
- [ ] 价格尺度不清时，最多输出结构质量，不能降级名称后计算有投资含义的涨跌。不得将 qfq/auto_adjust 直接改名为已独立复核的分红再投资财富指数。

验收不要求四只都合格；要求知道证据在哪里、缺什么和为什么。禁止为了交付而重抓或换标的。

## Task 3：研究坐标与时间/目标合同（独立可验收）

接口：`validate_study_contract(contract: dict) -> dict`，返回 `status/reasons/allowed_uses`；结构、身份、参数非法抛 ValueError，资料不足返回受限状态，不伪造可执行资格。

- [ ] 合同记录：`object_ref`、候选卡路径/哈希、theme/type、use、market、universe_id、成员快照、属性标签、lookback、horizon、target_basis、regime、data_identity、calendar_identity、code_identity、规范版本、研究截止。
- [ ] 本轮固定 theme=trend、type=state_signal、use=historical_description、lookback=20、e_offset=1、x_offset=22、regime=none。510300/159915/SPY/QQQ 分别统计，不把4只当稳定横截面样本。成长/宽基等标签允许重叠，不组成可加总归因账。
- [ ] session_close、available_at、fetched_at分列；未知 available_at 明确保留 null，`point_in_time_verified=false`。历史描述资格不要求假造当时毫秒；它也不授予预测资格。
- [ ] 日历必须说明来源、覆盖区间、逐日交易状态和半日市收盘；不从报价日期或周一至周五反推完整日历。只使用本地可核材料，NYSE/Nasdaq挂牌市场差异明示，不能假定同表永远一致。
- [ ] 没有可靠日历的市场，交易日目标状态保持 blocked；可以用合成时刻测夏令时/半日市算法，不能当真实日历证据。
- [ ] 主候选目标保持已提案的含分红财富变化 `I(x)/I(e)-1`；e/x由当地日历精确定位。若只能证明供应商调整价格，记录替代目标提案 `vendor_adjusted_price_change`，等待主控确认，不自行替代后开算。两者不可混榜。
- [ ] 辅助下行目标固定 `min(0, min(I(s)/I(e)-1 for s in (e,x]))`；中间缺价就该路径目标缺失。主目标端点缺失不顺延；预热不再加未来22根；尾部未成熟独立记录。可观察起点不叫上市日期证明。

最少反例：收盘时刻冒充可得时间、无时区、半日市用16点、夏令时偏一小时、日期冲突、日历缺一天、未知价格尺度、修改20/1/22参数、伪造对象引用、空源码键集合、自填可信标记。每项有合法对照，不能用“一律拒绝”冒充修复。

## Task 4：用合成资料打通状态—未来目标描述（独立可验收）

接口：`describe_states(values: pd.DataFrame, schedule: pd.DataFrame, contract: dict) -> dict`。本轮测试仅用明确 synthetic=True 的夹具；真实来源身份不能靠传 synthetic=True 改写。

- [ ] 明确值表最小字段 symbol/session/state/I，schedule含session/close_at。执行前验证完整合同，目标由t+1和t+22而不是按数据删行后的第几行计算。
- [ ] 输出每日期有效/未就绪/目标缺失原因；每产品真/假两组样本数、均值、中位数、上涨比例、辅助下行目标，并给同一可评价日期全集的无条件参照。state未知不混入false。空组输出null与n=0，不崩溃，不输出NaN/Infinity。
- [ ] 按观察年份分列；连续状态段计数；每天滚动的21日未来窗口有重叠，不能当独立多次成功。固定稀疏观察视角为每载体预定评价起点起每23个当地交易日一格，缺失该格跳过不补选、不改锚点。
- [ ] 不产生策略收益、年化、IC排行榜、统计显著性、过拟合已排除、风险调整α；状态真假差异是历史关联，不是因果或可成交利润。
- [ ] 独立期望脚本禁止 import 被测模块；至少覆盖 e/x端点手算、全上涨下行值0、缺中间价、尾部不足、全false、全未知、空年份、窗口重叠与固定稀疏锚点。

## Task 5：资格 CLI 与可移交冻结包（独立可验收）

新命令接口：

```bash
python3 scripts/check_factor_unit_readiness.py --contract PATH --out NEW_DIRECTORY
```

该 CLI **只能校验与冻结候选包，不计算真实因子表现**。退出0=本轮声明用途资料齐备、2=资料不足、3=合同/身份错误。资格齐备也不自动启动 B1。

- [ ] 输入合同引用四份价格清单与来源裁定；先验哈希后消费。旧 current 指针不能作为冻结身份。
- [ ] 把最终代码原字节、依赖列表/解释器版本、卡原字节、规范指纹、来源表和日历证据装入新输出；读取未提交源码，不能只记git HEAD。
- [ ] 协议版本排他保存，输出拒绝覆盖；manifest最后写、逐项输出哈希非空、标准JSON读回。失败不写 completed；原件不可靠时标不可恢复，不靠新版本号洗白。
- [ ] 合成正负完整 CLI 各跑，核验被改输入、删代码键、目标错参数、写盘失败、目录存在、全缺资料；每次/tmp调试也记录。
- [ ] 本轮真实资格检查最多1批四市场；不运行 `compute_close_state` 于四市场全史，不生成真实状态/未来目标值。最终生成 `b1-run-request.md`：逐市场可用/不可用、主目标是否有证据、建议准确评价日期、所需最小授权；四只不必齐步走。

## Task 6：交付、计数与停止

- [ ] 局部测试按需；全相关回归最多2次，用下面命令运行并记录实际文件与项数，不追目标计数：

```bash
python3 -m pytest tests/unit/test_factor_unit_close_state.py tests/unit/test_factor_unit_study_contract.py tests/unit/test_factor_unit_state_description.py tests/integration/test_factor_unit_readiness_cli.py tests/unit/test_factor_lab_contracts.py tests/unit/test_factor_lab_adapters.py tests/unit/test_factor_lab_diagnostics.py tests/unit/test_factor_lab_validation.py tests/unit/test_factor_lab_attribution.py tests/integration/test_factor_lab_cli.py tests/unit/test_experiment_reports.py -q
python3 -m ruff check src/lei_signal/research/factor_unit scripts/check_factor_unit_readiness.py tests/unit/test_factor_unit_close_state.py tests/unit/test_factor_unit_study_contract.py tests/unit/test_factor_unit_state_description.py tests/integration/test_factor_unit_readiness_cli.py
```

- [ ] 合成端到端正式最多1批（正/负各1），纠错最多1批且须是已定位工程错误；真实资格检查1批；零真实表现统计。任何失败都计次数，超限停受影响分支。
- [ ] 完整读回输出哈希、实际代码包与协议一致；重算保护清单，区分他人修改，不回滚。
- [ ] 报告按模板包含一句话结论、决策卡、R1–R6纠正、源码/输入来源证据、测试失败史、实际命令/环境/计数、能力已实现与未实现、逐市场下一步。旧主张只引用不冒称复核。
- [ ] 登记本报告 category=方法论与验证、verdict=mixed，INDEX导航。OKR交主控更新，执行者不写。

完成即停。输出直接回答：“能不能使用只有收盘价的资料？四份输入各缺什么？给主控哪份冻结包就能批准第一批历史描述？”若无市场合格，交确切缺口和最小下一授权，不另开泛化平台建设。

## 后续 B1（本轮禁止启动）

主控确认输入/价格口径/日历及冻结协议后，首轮只比较固定20日双均线状态后的21个收盘间隔表现，逐市场、逐年、连续状态段与稀疏观察并列；不优化参数。含分红目标不足时，由主控明确是否批准调整价格目标，不由执行者降级。

之后才按证据决定宽度/情绪下一位候选或外部工具适配。通用库建设目标不变：先把单个对象的含义、适用范围和证据边界研究清楚，再决定它是否值得进入过滤、仓位或策略归因。
