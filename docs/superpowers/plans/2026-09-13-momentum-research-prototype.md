# 已有动量指标研究样板：连续执行任务书

> **For agentic workers:** 使用 `executing-plans` 按任务连续执行；本任务不要求新建用户侧任务或派发子 agent。每阶段完成局部验证后继续，最终一次交回主控。

**Goal:** 把一个已登记的 ETF 动量指标做成“输入可追溯、数值可复算、未来观察目标明确、资料不足会明确停止相关计算”的研究样板，而不是开发更多指标或追求更高历史收益。

**Architecture:** 复用既有快照检查、身份解析、经济指数重建和动量计算，只加研究隔离适配及未来观察目标/排序诊断。合成算法验证、真实历史重建诊断、具备资格的预测研究分别输出，互不冒充。

**Tech Stack:** 仓库已有 Python、pandas、NumPy、pytest、ruff；零新增依赖、零网络请求。下文接口为本任务待实现设计，不代表当前已存在。

版本：1.0.0；日期：2026-09-13。授权背景：用户要求“能不能开一轮大任务开始做啊”，并提交输入检查修复报告。本次开始的是一个已有指标的研究样板，不授权新增因子、数据、账户路径、生产规则或 OKR 修改。

## Global Constraints

- 先读根及相关目录 AGENTS、交易规格、研究原则与下列权威文件。服务研究验证层，不改变道路、路牌、触发和过滤纪律。
- 唯一定义登记为 `docs/research/definitions.v1.json`；不另建库、不改旧卡、不倒填冻结实验版本。
- 研究原则 `docs/research/experiment-backtest-principles.md` v1.1；定义标准 `docs/research/definition-standard.md` v1.1.0；执行合同 `docs/research/ai-execution-contract.md` v1.0.1；模板 `docs/research/experiment-report-template.md` v1.1.0。执行前记录实际字节哈希，有语义漂移只暂停受影响项。
- 先读 `docs/research/factor-phase0-decision-brief-2026-09-10.md` v2、本任务及 `docs/experiments/research-input-preflight-controller-review-2026-09-13.md` §10。旧简报的选择在下文针对本轮明确，不改其历史文本；旧 v0 计划及输出只读。
- 数据限制仍然成立：首报价不等于上市日期；取得时间不等于历史可知时间；补经济指数列不等于取得研究用途资格。
- 不安装 Qlib/Alphalens，不接 Alpha158，不接 vectorbt/Backtrader/LEAN，不做界面或通用回测框架。此前 Qlib 审阅的暂不引入结论不变。
- 不用 `allow_conditional` / `accept_structural` 绕过真实输入限制；不删除有问题的产品、不缩短区间来制造合格样本。已有资料不够就交付算法和精确缺口，不停止全部任务。
- 不调用会运行账户或覆盖旧输出的 v0 主入口；不改持仓、退出、快速回补候选或任何政策结论。无资金账户计算，policy 字段明确 `not_applicable_no_account_policy`，不能伪造一张已运行政策卡。
- 现有工作区有其他人的未提交修改。只用小范围 `apply_patch`，不重置、不覆盖、不把别人的内容一起提交；未经要求不提交 git。

## 1. 本轮固定选择：先写协议再运行

**研究问题：** 在固定混合 ETF 池中，过去较早一段涨幅较大的产品，随后一段是否也相对较强？本轮先证明这项问题的计算和时间安排可以正确实现；真实资料不合格就不回答其预测有效性。

1. 对象仅 `mixed.momentum.raw@1.0.0`，依赖 `mixed.price.economic@1.0.0`。类型仍是 feature（描述数值），不是可投资的因子收益组合。
2. 原始值 `M(t)=I(t−21)/I(t−252)−1`，两个偏移按该产品自身有效报价位置；首次需要 253 条。保留原定义，不偷换为统一交易日偏移。月选资格的 273 条另属政策，本轮不使用取前三、波动过滤和权重规则。
3. 观察日期取已有合格日历中各完整月份的最后交易日，评价区间固定为 2019-09-02 至 2026-06-30。月份不完整不推断月末。产品当日无报价不前填信号；不得按某产品最后报价冒充全市场月末。
4. 唯一未来观察目标：对观察日 t，e 为其后第一个交易日，x 为 e 之后第 21 个交易日；`Y(t)=I(x)/I(e)−1`。e、x 都要求该产品实际有效报价；缺端点或区间末尾不足返回缺失，不能顺延到下一次报价。观察目标不是成交价承诺，不计费用、不报告账户回报。
5. t 收盘数据最早只能在其实际可得后用于决策；不能仅凭标注 15:00 就认定已知。目标在 x 收盘且必要资料可得后才可能成为完整历史标签；未知 `available_at` 保留 null。合成例可声明合成可得时间，不能移植为真实时点证据。
6. 统计诊断只用“当期指标排序与随后变化排序的一致程度”，即 Spearman 相关：两列分别按并列平均名次，再计算名次的 Pearson 相关。它不是 `mixed.momentum.rank` 的按代码打破并列的选股顺序，不引用该卡冒充同一变换。
7. 每次只配对有限且有效的 M/Y；少于 3 个配对或任一列名次全相同返回缺失及原因。3 是算术最低样例标准，不是统计可靠性的保证。列出每期数量、排除原因、均值/中位数和实际观察区间重叠情况；不做五分组/十分组，不做显著性或独特 alpha 声明。
8. 本轮不做政策对照或市场超额基准。旧简报 P3 的账户参照延后，不能把“没有账户”写成“内部政策对照已完成”。不测试第二个观察窗口，不训练、调参或挑结果。

上述目标和变换是本轮协议中的测量方法，不新增交易因子对象。如将来复用成正式对象，再按唯一登记表流程审议；本轮只保存协议版本与哈希。

## 2. 文件范围与产物

仓库根：`/Users/yongbiaoli/Desktop/lei-signal-lab`。下列为相对此根的精确位置。

| 文件 | 职责/权限 |
|---|---|
| `scripts/check_research_input.py` | 仅 Task 1 的输出失败收尾与协议文件校验 |
| `tests/unit/test_research_input_preflight_fix.py` | 追加有限输出失败及协议引用反例，保留原测试 |
| `src/lei_signal/research/momentum_prototype.py` | 新增薄适配、目标与排序计算；不改已有引擎 |
| `scripts/run_momentum_research_prototype.py` | 新增离线编排、权限分支、协议及产物绑定 |
| `tests/unit/test_momentum_prototype.py` | 新增独立算术/时间/缺失/价格尺度测试 |
| `tests/integration/test_momentum_prototype_cli.py` | 新增完整调用、拒绝、断网和输出保护测试 |
| `docs/experiments/momentum-research-prototype-2026-09-13.md` | 执行报告；尚未由本任务书创建 |
| `docs/experiments/raw/research-momentum-prototype-2026-09-13/` | 新协议、基线、合成例、逐值差异、日志、运行快照；每次输出新编号 |
| `docs/experiments/registry.json`、`docs/experiments/INDEX.md` | 只登记本交付及导航，保留并发改动 |

只读：`data_quality.py`、`data_snapshot.py`、`trading_calendar.py`、`symbol_identity.py`、`definitions.py`、`factor_runtime.py`、`factor_diagnostics.py`、账户适配、旧协议与 raw、所有生产/API/UI、规则账本、OKR。主控复核报告和反例只读。确须改只读代码时，给最小反例，只暂停依赖该修改的任务。

## Task 1：输入入口最后一项输出保护，纳入同轮完成

**依据：** 主控 `probe_manifest_failure.py` 实测 manifest 写入失败仍抛出未捕获 OSError，留 `request_satisfied=true` 的部分 JSON，无 FAILED.txt；JSON/Markdown 已修，不能声称全部写出阶段完成。

- [ ] 在已有修复测试追加 JSON、Markdown、manifest 和 mkdir 四个独立模拟失败；至少 manifest 场景先看到失败。使用临时目录和 monkeypatch，不改真实权限。核心断言如下：

```python
assert rc == 3
assert not (out / "manifest.json").exists()
assert "失败" in captured.err
# 目标目录仍可写的模拟故障，必须有 FAILED.txt；mkdir 不可写时不要求文件。
```

- [ ] 将规范/输入/输出哈希读取、manifest 构造和写入纳入同一失败处理；仅完整写出有效 manifest 才算完成。清楚区分失败标记与正常拒绝，保留正常 0/2、参数错误 3。部分 manifest 不得被消费方当完成；新任务消费前验证 JSON 可解析、输出指纹匹配及无 FAILED.txt。
- [ ] 显式提供 `--protocol` 时要求文件存在、可读、可解析且记录实际哈希；错误路径退出 3，不能记录 null 哈希后当已绑定。兼容旧命令省略该参数，但本轮所有正式运行强制传入新冻结协议。追加缺文件和正确文件的反向/正向测试。
- [ ] 运行 `python3 -m pytest tests/unit/test_research_input_preflight_fix.py tests/integration/test_research_input_preflight_cli.py -q`，保存日志；不重开底层质量修复。

## Task 2：冻结协议与只读接入，复用已有计算

**接口设计：** 新模块 `compute_momentum(index: pd.Series) -> pd.Series` 调用 `definitions.quote_features(index)["momentum"]`，仅暴露本轮列。输入经济指数唯一递增日期、不重复，非缺失值必须有限且大于零；原定义中的报价缺失规则保留。

```python
def compute_momentum(index):
    if not index.index.is_unique or not index.index.is_monotonic_increasing:
        raise ValueError("unique increasing dates required")
    values = index.dropna().to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("finite positive index required")
    return quote_features(index)["momentum"]
```

- [ ] 先写协议 `protocol.json`，锁定 §1、规范指纹、两个对象完整解析卡及递归依赖、代码版本、输入位置/指纹、时间语义、模式边界与容差。冻结后参数不得更改；纠错需新协议版本及影响记录。
- [ ] 输入位置直接读取旧 `docs/experiments/raw/research-input-preflight-2026-09-13/protocol.json` 的 `fixed_inputs`：canonical-snapshot-v2、calendar-merged、publication-evidence、normalized-actions；复制引用到新协议并核哈希，不复制/改写旧输入。全池预期 14 只 / 18,916 行只是核对值，不能硬造结果。
- [ ] 运行前保存旧 896 项受保护基线和本轮额外只读文件的逐文件指纹，记录 git HEAD、相关未提交源码 SHA、Python/依赖版本。先核 `verify_sources`，不允许错源计算。
- [ ] 身份用已有解析器建立一对一映射表；.SH/.SS/裸码只按已有明确映射转换并保留原值，冲突/未知拒绝。原始行动先用既有质量核验，不得直接交给重建函数。停牌只做缺口解释，分红/拆分才进入经济指数；账户 events/actions 不参与此次输入。
- [ ] 优先复用 `factor_runtime.reconstructed_economic_index(series, events)`，输出未知可得时点的行动 ID。若需字段适配，隔离于新模块，用合法身份和实际字段逐项映射；不得改其旧消费者。无时间证据的真实结果必须 `historical_reconstruction_only=true`，不能冒充严格 `definitions.economic_index` 的历史可知输入。
- [ ] 手算 `I=1..253`：前 252 个结果缺失，第 253 个值为 `232/1-1=231`；追加第 254 个值核两个端点。独立手算而非被测函数产生期望。测试不改窗口为 5 来冒充原对象。
- [ ] 运行 `python3 -m pytest tests/unit/test_momentum_prototype.py -q`；对可比真实数值仅做 Task 5 的历史算术诊断。全量 `build_mixed_batch` 若会增加不相关计算，不必调用；直接复用上述经济指数与 quote_features 足够。

## Task 3：一个精确未来目标和并列排序诊断

**待实现接口：**

```python
def build_targets(index, sessions, observations):
    # index: 同一产品经济指数；sessions: 已核完整、有序、唯一的交易日期。
    # 返回 DataFrame: observation_date, entry_date, exit_date, target, reason。
    rows = []
    positions = {day: k for k, day in enumerate(sessions)}
    for day in observations:
        if day not in positions:
            rows.append((day, None, None, np.nan, "observation_not_session"))
            continue
        e, x = positions[day] + 1, positions[day] + 22
        if x >= len(sessions):
            rows.append((day, None, None, np.nan, "future_incomplete"))
            continue
        first, last = sessions[e], sessions[x]
        a, b = index.get(first, np.nan), index.get(last, np.nan)
        if not np.isfinite([a, b]).all() or a <= 0 or b <= 0:
            rows.append((day, first, last, np.nan, "endpoint_missing_or_invalid"))
        else:
            rows.append((day, first, last, b / a - 1, None))
    return pd.DataFrame(rows, columns=["observation_date", "entry_date", "exit_date", "target", "reason"])

def rank_diagnostic(frame):
    paired = frame.loc[np.isfinite(frame["momentum"]) & np.isfinite(frame["target"])]
    n = len(paired)
    if n < 3:
        return {"n": n, "value": None, "reason": "fewer_than_three_pairs"}
    ranks = paired[["momentum", "target"]].rank(method="average")
    if (ranks.nunique() <= 1).any():
        return {"n": n, "value": None, "reason": "constant_rank"}
    return {"n": n, "value": float(ranks["momentum"].corr(ranks["target"])), "reason": None}
```

以上是算法核心；调用前校验 sessions 不重复、不倒序、日历覆盖真实完整区间，index 身份不混合。输出统一标注观察目标 ID `protocol:momentum-next-close-21-session@1.0.0`，明确它是协议测量项，不是登记表对象。

- [ ] 先写失败测试：合成观察日期位置 300，进入位置 301、结束 322；I(301)=100、I(322)=110 时为 0.1。删除任一端点必须缺失，不能顺延；结束数据不足必须缺失。
- [ ] 测试两列 `[1,2,3] / [3,2,1]` 得 -1；`[1,1,3] / [1,2,3]` 得 `sqrt(3)/2`；常数、2 对数据、NaN/inf 配对处理与输出原因。容差绝对/相对各 `1e-12`，日期/身份/缺失原因精确相等。
- [ ] 实现上述核心与输入校验；不复制生产面板的名次算法，不引用账户诊断模块来冒充预测测试。
- [ ] 加未来信息测试：只追加 t 之后的报价和之后生效的行动，M(t) 不变；Y(t) 可由缺失变为可计算，但不回写 M。历史行动修订导致变化另记 `historical_revision`，不能称为同一合法输入的未来泄漏。
- [ ] 同一时期的目标窗口可能重叠：按实际 [e,x] 统计，禁止因“月频”就写独立。不要把相关产品数乘以月份数称为独立成功次数。

## Task 4：合成闭环与失败出口，先完整跑通算法

**CLI 新设计：** `python3 scripts/run_momentum_research_prototype.py --protocol <本轮冻结协议> --mode synthetic|historical-diagnostic|qualified-research --out <不存在目录>`。输出不带金额/交易/账户；0 表示该模式完整完成，2 表示质量限制导致研究拒绝，3 表示参数/输入/运行失败。正常历史诊断成功不表示 qualified-research 也成功。

- [ ] 合成夹具至少 4 个明确虚构产品、跨 14 个月的人工交易日历，含分红、拆分、同日事件顺序、缺报价、月末缺报价和不足预热。标 `synthetic=true`；不能伪装交易所数据或上市材料。算法直接调用与正式数据资格检查分开，不把合成成功当真实准入。
- [ ] 价格缩放同时缩放 OHLC 及每份现金分红，比例拆分系数不缩放。10→9 加分红1，与100→90加分红10的连接均为1；仅缩放价格不缩放现金是错误输入，应在测试中显示其经济含义确已改变。
- [ ] 全缺失、重复身份/日期、负价/无穷、非法行动、冲突 ID 均有失败或精确缺失输出。完整合成流程同时有正常输出，防止以一律拒绝假通过。
- [ ] CLI 只消费完整检查产物；篡改哈希、来源核验失败、错对象版本、错误协议、已存在目录、输出写盘失败必须按合同停止。断网守卫先自证拦截再跑全命令，不实际请求网络。
- [ ] 产物至少：`values.csv`、`missing.csv`、`targets.csv`、`rank-diagnostic.csv`（合成或真正合格模式才有后两者）、`quality.json`、`report.md`、最后写出的 `manifest.json`。历史诊断模式不得写真实 targets/rank 结果；以 `skipped-stages.json` 列出未运行及原因。
- [ ] manifest 保存模式、synthetic、historical_reconstruction_only、对象/协议/源码/输入指纹、实际观测与未知可得时点、各输出哈希、计算/研究资格/有效性/生产分别状态。每行只留对象身份引用、日期、产品、单位/缺失原因，不复制整张卡。
- [ ] 执行 `python3 -m pytest tests/unit/test_momentum_prototype.py tests/integration/test_momentum_prototype_cli.py -q`，保存日志与实际数量。

## Task 5：一次真实资料闭环，只做被允许的部分

- [ ] 对固定输入分别检查描述用途、排序用途和研究信号用途，保存完整结果。用途检查结果不得互相替代；描述允许不意味着预测分析允许。
- [ ] 若完整性、来源与真实描述用途允许，运行 `historical-diagnostic`：重建经济指数及本轮动量值、报告未知行动时点与 missing；用合法行动原始记录保留来源映射。若某记录身份或算术有致命错误，停止受影响产品计算并列错误，不删记录后宣称完整。
- [ ] 独立逐值比对：本轮结果对 `quote_features` 的既有表达式与直接位置公式；同一函数两次调用不算独立复算。普通月末、253/273边界、分红/拆分前后、缺报价前后按预定规则选取，每类不存在即记录不存在；列出日期、两个实际端点、行动ID、原值/复算值/差值/原因。全有效动量行也用独立 shift 表达式批量核对。
- [ ] 真实预测诊断仅当排序与研究信号两种用途都明确允许、对象与源通过、经济价格和公司行动历史可知证据完整、评价池/日历合格时运行 `qualified-research`。当前预期达不到；输出拒绝报告和阶段跳过原因即可。不得通过把 use 改成 description 来输出真实排序相关性。
- [ ] 不拉资料、不制造上市证明，不重新解释首报价。缺口清单必须到“对象/产品/日期/所缺来源/受限用途”，不写泛泛“重建整个数据层”，不要求无关全市场资料。
- [ ] 正式真实计算最多一次；若实现错误修复后允许一次新编号复跑，保留失败。禁止扫描窗口或全历史账户路径。输入检查不算策略实验。

## Task 6：一次交付，不自行宣布策略有效

- [ ] 运行新测试和原主控复核报告 §10 所指完整 295 项回归命令（增加本轮测试文件，实际数量实报，不把295当目标）。最多两次完整回归，局部测试不限但须相关；ruff 只检查本轮代码/测试并保存完整日志。
- [ ] 重算受保护基线、输入与旧反例哈希；零改动方可声明保护未变。检查所有 manifest/输出指纹、相对链接、协议和对象依赖；不以文件存在代替内容核验。
- [ ] 执行报告沿用模板，带“一句话结论（大白话）”与最小决策卡。明确合成例能算、真实重建能复算、真实预测是否拒绝三种结果；无账户故资金归因/费用/政策增量标不适用，不运行回归来凑三层归因。
- [ ] 附真实命令、日志路径、全指纹清单、错误与修复史、已接入/未接入消费者。登记报告“方法论与验证 / mixed”，不把工程通过写为因子有效；INDEX 链接本计划。旧 v0/生产/UI 仍未接入，OKR 不写。
- [ ] 完成即停，交主控复核。只有必须新增资料、改变已冻结定义或动只读代码的分支请求授权；其余任务继续。不要每修完一个小测试就重新请求下一轮。

## 完成标准与交回格式

第三个 AI 用相同合法输入，可在 `atol=rtol=1e-12` 内复算相同 M/Y/排序值，日期、ID 和缺失原因完全一致；能准确区分合成数据、事后重建和历史可知资料。不要求得到正相关，更不要求真实预测分支放行。

交回：一句话实际进展；Task 1–6 完成/受限表；新增与修改文件；命令/测试数/日志；真实模式实际执行与拒绝原因；保护指纹；下一件最能改变判断的资料或决策。不声称已拥有独特 alpha、策略有效、OKR 完成或获准交易。
