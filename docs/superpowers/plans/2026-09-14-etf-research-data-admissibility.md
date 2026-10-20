# 固定 ETF 池资料采用与开工判断 — 执行规格

> **2026-09-14 优先级变更：后置专项，当前不执行。** 用户澄清主线是通用自有因子研究能力，见[当前任务](2026-09-14-factor-research-workbench-v1.md)。本文件正文作为历史提案保留；40次请求/20份资料及真实评估额度不转授给当前任务，不以持有此文件启动补证。

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task if that skill is available. 用户选择一个新的 GLM 串行执行；不自动派发子任务。技能不可用时按本文件执行并注明，不为技能安装依赖或改变权限。

**Goal:** 补有限官方材料，证明哪些既有研究输入在历史决策前可知，交付可复算的逐项判断及真实动量研究开工建议。

**Architecture:** 在现有证据校验和快照检查之外增加研究专用采用评估，保留旧检查的原始发现；新判断与旧消费者分开。资料取得、证据核对、离线评估三个环节分别留痕，不创建第二份对象登记表，不运行预测或收益实验。

**Tech Stack:** 仓库现有 Python 3.11+、pandas、pytest、ruff；标准库 JSON/CSV/hashlib/datetime/zoneinfo/urllib；PDF 提取只用已安装工具。零新增依赖。

版本：1.0.0；2026-09-14。规划已完成，执行未开始；示例接口均为拟实现合同，不是已实现能力。

## 0. 全局约束与授权

- 设计来源：[资料采用设计 v0.1.1](../specs/2026-09-14-etf-research-data-admissibility-design.md)。权威规范及设计时指纹见其 §7，开工时实际复核。
- 2026-09-14 用户要求“一个新的glm可以吗……还需要具体的执行规格……就开始写吧”：本次主控只编写规格，不启动另一个任务、不联网、不修改研究代码。用户把末尾启动 prompt 交给执行者后，执行者在合同中保存该授权；单独发现本计划文件不等于获得执行许可。
- 上一轮 S1–S3 已收口，无必修项。本轮是新政策评估，不是追加返修；旧协议、资料和结果均只读。
- 固定 14 只、2019-09-02 至 2026-06-30；完整月份最后交易日作为观察日，观察截止沿用当地 15:00 的测试约定，不宣称它是真实数据到达时刻。
- 仅引用 `mixed.price.economic@1.0.0`、`mixed.momentum.raw@1.0.0`；公式、252/21 参数、产品池、交易规则不变，不改对象卡。
- 本轮最多 40 次联网请求、20 份新官方材料、1 次真实资料评估、2 次完整回归。失败请求/重定向/重试计入请求；失败真实评估也计次，不自行重跑。没有任何真实动量计算、真实派生、目标收益、排序相关性或账户运行额度。
- 无生产、OKR、依赖、付费、密钥、登录、新行情、外部因子库或自动持续采集权限。不提交 git，不全仓暂存，不新建工作树以遗漏未提交研究文件。
- 涉及新证据语义歧义，保留未知并继续其余项；不得自行解释成通过。完成交主控复核，不自行宣布验收。

## 1. 工作区与交付路径

以下路径均相对仓库根目录。不得从空仓库或仅含 git HEAD 的副本执行，本轮依赖未提交但已有的研究文件。

| 文件 | 权限与职责 |
|---|---|
| `src/lei_signal/research/research_admissibility.py` | 新建；纯研究评估、时间边界及覆盖判定 |
| `scripts/acquire_etf_evidence.py` | 新建；本轮有限 HTTP 请求、计数与来源原件保存，不拉行情 |
| `scripts/check_etf_research_admissibility.py` | 新建；冻结身份检查、旧检查调用、输出与退出码 |
| `tests/unit/test_research_admissibility.py` | 新建；独立小例、证据及时间反例 |
| `tests/unit/test_etf_evidence_acquisition.py` | 新建；假网络响应与持久预算测试 |
| `tests/integration/test_etf_research_admissibility_cli.py` | 新建；合成全流程、旧消费者不变 |
| `docs/experiments/raw/research-etf-admissibility-2026-09-14/` | 新建；本轮合同、协议、获取账、原件、抽取、补充证据、日志和正式输出 |
| `docs/experiments/etf-research-data-admissibility-2026-09-14.md` | 新建；执行报告及最小决策卡 |
| `docs/research/factor-research-roadmap-2026-09-10.md` | 仅追加带日期的当前证据入口、已做/未做及下一步，不重写路线 |
| `docs/experiments/registry.json`、`docs/experiments/INDEX.md` | 仅本报告条目，保留他人新增内容 |

仅允许以上新增源文件；若确需多一个小工具，放本轮 raw 内并列入协议代码清单，不建立通用框架。旧 `data_quality.py`、`qualification_bundle.py`、`definitions.py`、`data_snapshot.py`、`trading_calendar.py`、动量 CLI、派生 CLI 和全部既有测试不修改。

本轮 raw 内固定布局：`contract-v1.0.0.json`、`policy-v1.0.0.json`、`acquisition-plan-v1.0.0.json`、`requests/`、`sources/`、`extracts/`、`evidence-bundle-v1.2.json`、`availability-evidence-v1.0.0.json`、`review-notes.md`、`protocol-v1.0.0.json`、`protection/`、`logs/`、`synthetic/`、`run-01/`。这里列的是预定路径，不代表文件已存在。

新版本文件排他创建；内容变化另存新版本。运行协议必须绑定实际代码和输入，不能执行 current 指针。版本历史不可恢复时如实登记，禁止补造原件。目录已存在则停下核对归属，不自动顺延编号来重复真实运行。

## 2. 必读与固定输入

- 根 `AGENTS.md` 及适用目录规则；`docs/trading-spec-v1.md`、`configs/rules.v1.yaml`、`.claude/skills/macd-reading/SKILL.md`、`docs/plan-sector-trend-page.md`。本轮服务规格 §3.1–3.2 的数据与时点层，不修改策略层。
- `docs/research/experiment-backtest-principles.md` v1.1、`ai-execution-contract.md` v1.0.1、`definition-standard.md` v1.1.0、`experiment-report-template.md` v1.1.0，唯一 `definitions.v1.json` v1.2.0。
- `docs/experiments/momentum-prototype-controller-review-2026-09-13.md` §13；`fixed-etf-evidence-integration-2026-09-13.md` §10。此前长日志按需要读，不恢复整个研究历史。
- 前轮 raw：`docs/experiments/raw/research-fixed-etf-evidence-integration-2026-09-13/` 下的 `protocol-v1.0.4.json`、`evidence-bundle-v1.2.json`、`needs.csv`、`remaining-acquisition-request.md`、`consumer-map.md`。最后两份是旧交接，数字以终版报告和逐条清单为准。
- 价格/指数只读输入：前轮 `run-08/snapshot/`；由该目录自身 `snapshot.json` 验证文件，不把协议中原始名义快照错当派生输入。
- 原始名义输入、日历、日历公布证据和行动路径从前轮 `protocol-v1.0.4.json` 的 `inputs` 精确解析；保留原路径/哈希，目录身份展开为文件清单，不把目录当普通文件求哈希。
- 772 旧值仅是历史核算背景，不作合格数量常量；本轮不重新计算或要求凑齐该数。

固定产品名单：`159652.SZ, 510300.SS, 512400.SS, 512890.SS, 513870.SS, 515050.SS, 515130.SS, 515170.SS, 515300.SS, 515880.SS, 516220.SS, 518850.SS, 562590.SS, 588000.SS`。完整身份不可退化成裸码 join。

## 3. 跨任务接口和裁决语义

### 3.1 不新增一套总规范

`policy-v1.0.0.json` 是本轮冻结政策快照，`policy_id=etf-research-admissibility`、`version=1.0.0`，不是对象卡或永久总纲。固定：时区、池和区间、观察规则、允许用途 `research_input_assessment`、禁止用途、证据种类、未知处理、预算及本计划哈希。参数不开放给调用者任意调整。

合同先冻结范围和预算；获取材料后、真实评估前再冻结运行协议及全部代码/输入哈希。不要在开发中反复覆盖同一个“正式协议”。

### 3.2 现有能力复用

```python
from lei_signal.research.data_snapshot import load_snapshot
from lei_signal.research.data_quality import check_snapshot
from lei_signal.research.definitions import load_registry, resolve
from lei_signal.research.qualification_bundle import validate_evidence_bundle
from lei_signal.research.trading_calendar import TradingCalendar

# 先核实际签名；以下调用均为已存在的接口。
card = resolve(load_registry(), "mixed.momentum.raw@1.0.0", purpose="description")
loaded = load_snapshot(snapshot_dir)
old_quality = check_snapshot(
    loaded, calendar=calendar, actions=actions,
    evaluation_start="2019-09-02", evaluation_end="2026-06-30",
)
checked = validate_evidence_bundle(bundle, root=repo_root, universe=set(symbols))
```

不得导入并执行旧脚本 main；`listing_evidence_from_validated` 会写目录，本轮无需调用它来授予资格。旧包只支持文内日期，**新公开时间证明放补充文件**，不能把精确时间塞回旧包或改旧校验器。

### 3.3 新接口（待实现）

```python
def verify_availability_record(record: dict, *, root: Path,
                               bundle_result: dict, policy: dict) -> dict:
    """验证原件/抽取/事实身份/时间证明绑定；返回状态、原因及派生时间边界。"""

def assess_time(evidence: dict, *, cutoff: str) -> dict:
    """只接收 verify_availability_record 的结果；时刻必须带时区。"""

def assess_inputs(loaded, *, calendar, actions: list[dict],
                  bundle_result: dict, availability: list[dict],
                  old_quality: dict, policy: dict) -> dict:
    """不计算动量/收益；生成事实层、产品层、观察日期层的采用结果。"""
```

公开 CLI 必须从磁盘原件重查，不能让外部 JSON 直接冒充 `verify_availability_record` 的结果。纯函数测试可以使用显式合成结构，但不能成为真实模式旁门。

`verify_availability_record` 返回字段固定为 `verification`（supported/unknown/rejected）、`kind`（从 evidence_kind 映射）、`value`、`synthetic`、`evidence_ids`、`reason_codes`；`assess_time` 返回 `status`、`synthetic`、`upper_bound`（带时区 ISO 或 null）、`evidence_ids`、`reason_codes`。校验未 supported 的记录不能仅因有合法时间字符串而变成 supported。`assess_inputs` 返回 `facts`、`coverage`、`finding_map`、`missing_evidence`、`summary`，供 CLI 分别落盘，不能从报告文本反向生成机器结论。

补充记录逐项包含 `record_id`、`instrument_id`、`event_id`（无事件则 null）、`fact_record_id`、`fact_fingerprint`、`evidence_kind`、`value`、`source_refs`（path/sha256）、`locator`、`extracted_record_ref`、`publication_semantics`、`refers_to_version`、`synthetic`。必需字段由代码固定；补充记录里的时间、所指版本和身份同时与冻结抽取记录比对，删除字段/改后重算本记录指纹不能越过检查。

`evidence_kind` 固定五类：`exact_available_at`、`public_by_date`、`document_date_only`、`fetched_only`、`unknown`。只有前两类有证据支持时可产生“时间条件满足”。`public_by_date` 必须说明官方发布记录如何把 D 日与同一事实版本相连；落款、送出、当前网页、URL 日期不够。取得来源与人工/AI 原文判断分别留痕；程序验证绑定一致，不宣称机器已自动证真。执行者的原文解释交主控独立复核，输出 `review_status=pending_controller_review`，不是不可质疑的可信标志。

时间算法固定如下；调用前已完成证据验证，不允许单靠填 `public_by_date` 触发：

```python
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

def public_date_upper(day: str) -> datetime:
    d = date.fromisoformat(day)
    if d.isoformat() != day:
        raise ValueError("non_canonical_date")
    return datetime.combine(d + timedelta(days=1), time.min,
                            tzinfo=ZoneInfo("Asia/Shanghai"))

# exact_available_at：上界为已核精确时刻。
# public_by_date：上界为 public_date_upper(已核公开日期)。
# 满足条件 iff 上界 <= 带时区的 cutoff；否则 time_after_cutoff。
# 其余三类返回 time_unknown；无时区/非法日期返回 invalid_evidence。
# 不回填原 available_at，不把生效日期替换为公开日期。
```

每项状态：`supported / unknown / rejected / not_applicable`；`reason_codes` 列表、`evidence_ids` 列表另列。`supported` 仅指所标维度，不能单字段代替完整资格。`synthetic=true` 永远不产生真实市场采用结论。

输出分别保留 `source_identity`、`fact_binding`、`time_evidence`、`listing_consistency`、`quote_version`、`calendar_status`、`purpose_fit`、`overall`；原 `old_quality` 完整保存。每个旧发现关联 `original_finding_id` 与新证据解释，不删除、不自动转写旧 verdict。

## Task 0：冻结任务、保护现场和获取清单

**Files:** 本轮 raw 的 contract、policy、acquisition-plan、protection；不改旧文件。

**Consumes:** §0–3、实际仓库、前轮终版。**Produces:** 带哈希的范围合同、政策快照和排序后的资料需求表。

- [ ] 记录 `git status --short`、`git rev-parse HEAD`、实际模型和 Python/依赖版本；不用“GLM”掩盖实际运行模型不同。现有文件缺失或归属不明先停受影响项。
- [ ] 建新 raw 目录并拒绝重用。保存本轮可写文件的原字节；对前轮 raw、既有研究模块/测试、规则账本、登记表及 v0 入口逐文件哈希。原 896 项清单如果可定位则复用；不能据数字编出清单。
- [ ] 按上述路径解析两张准确卡并保存展开卡；固定 14 产品及 82 月末观察日的推导规则，不硬编码数量作为通过条件。
- [ ] 对账 14 个上市需求与 21 条行动，不把“12 份缺原件”写成“12 只实际阻断”。列完整 `need_id/instrument/event/needed_fact/existing_source/actual_impact/priority/reason`。
- [ ] 获取优先顺序：已有 515050/562590 上市来源的公开证据；512890 拆分前安排公告；缺原文行动；实际受阻产品的上市资料；最后是不影响当前阻断的需求。同优先级按完整产品 ID、事件日期、need_id 排序。先查本地再请求。
- [ ] 每个候选 URL 的产品归属和官方域名依据记录在清单；未知不猜。后续发现新链接可追加发现记录，但不改需求优先级、不扩池、不增加预算。

验收：另一个执行者能从合同确定要读什么、能写哪里、最多运行几次。此阶段只读盘点不算真实评估；不得提前全池运行 `assess_inputs`。

## Task 1：实现可计数、可恢复但不可重置的资料获取

**Files:** 新 `scripts/acquire_etf_evidence.py`、`tests/unit/test_etf_evidence_acquisition.py`；raw requests/sources。

**Interfaces:** `request_once(url: str, *, ledger_dir: Path, allowed_hosts: set[str], transport) -> dict`；transport 一次只发一条 HTTP 请求，自动重定向和自动重试关闭。返回状态、最终本次 URL、状态码、来源文件引用或失败原因。

- [ ] 先写下列预算测试和假响应，不访问网络：

```python
def test_budget_survives_restart(tmp_path):
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "acquire", Path("scripts/acquire_etf_evidence.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ledger = tmp_path / "requests"
    ledger.mkdir()
    for n in range(1, 41):
        (ledger / f"{n:03d}.started.json").write_text('{}')
    called = []
    result = mod.request_once("https://example.invalid/a", ledger_dir=ledger,
        allowed_hosts={"example.invalid"}, transport=lambda u: called.append(u))
    assert result["reason"] == "request_budget_exhausted"
    assert called == []
```

- [ ] 执行 `python -m pytest tests/unit/test_etf_evidence_acquisition.py -q`，记录真实失败；不存在模块只是接口未建证据，不声称发现旧系统缺陷。
- [ ] 最小实现：发请求前以独占创建 `NNN.started.json` 占用一个槽，记录 URL、UTC 请求时刻、need_id；返回后另建 result 文件，记录返回时刻、状态、字节数、哈希、重定向目标或异常。进程崩溃留下 started 仍占额度；重启不清零。第 41 次在联网前拒绝。
- [ ] 使用 `urllib` 禁用自动重定向；3xx 目标经域名和需求核验后才能再调用一次，每跳计数。超时 30 秒，无自动重试；响应上限 20 MiB，超过即停止读取并保留失败原因。每次请求失败也占槽。
- [ ] 新原件最多 20 份；相同哈希复用而不重复占“新原件”数，但请求照算。索引 HTML 若保存成证据原件，同样占份数。第 21 份不得取得；先检查剩余额度，已满不再发请求。
- [ ] 增补假网络测试：重定向不暗发请求、跨域拒绝、超时计数、崩溃后重启、篡改/缺失 result 不退回额度、材料上限、同哈希去重、原件不覆盖。通过后才执行获取批次。

获取 CLI 合同：`python scripts/acquire_etf_evidence.py --plan <冻结计划> --ledger <requests目录> --sources <sources目录>`。每次选择清单下一需求，未找到就记缺口；没有可追溯 URL 不伪造。浏览器/Web 搜索若无法准确计数每个网络请求，不作为绕开预算的路径。

## Task 2：核原文，形成事实包和时间补充证据

**Files:** raw extracts、evidence-bundle、availability-evidence、review-notes；可新增 raw `extract_selected_evidence.py` 并绑定代码哈希。旧抽取脚本只读。

**Consumes:** Task 0 需求和 Task 1 原件。**Produces:** 兼容旧 v1.2 schema 的新事实包，以及单独的时间证明文件。

- [ ] 先对已有材料去重、核哈希，按需求逐份看原文；读取 PDF 时使用执行环境可用的 PDF 技能，抽取工具未安装则保留受影响缺口，不安装依赖。
- [ ] 逐事实记录页码/原文位置、原始值、换算式、完整身份及公告类型。每 10 份分红金额转每份必须独立除以 10；拆分比例方向不能凭文件名推断。
- [ ] 原 v1.2 的固定字段沿用，不往旧 schema 塞精确时间。可用以下已存在接口独立检查新事实包：

```python
checked = validate_evidence_bundle(new_bundle, root=repo_root, universe=set(symbols))
assert set(checked) == {"validated", "rejected", "conflicts", "unresolved"}
# 拒绝和未核记录全部输出；不能过滤后只报成功数。
```

- [ ] 时间补充文件严格按 §3.3 绑定抽取证据。每次判断同时写“证明什么”和“不能证明什么”。512890 后发结果公告不得证明原事实在生效前可知；引用先前公告仅算定位线索，需原件。
- [ ] `review-notes.md` 每条引用 raw 页面与抽取值，签明执行者/模型、日期、判断理由及待主控复核状态。未判断、只见落款、来源版本不明，分别保留 unknown，不能用自填可信值解决。
- [ ] 生成操作无导入写文件；使用稳定排序、UTF-8、`allow_nan=False`。同字节只报告复现不覆盖，异字节拒绝；测试临时目录运行两次生成比对，不能反复覆盖正式包。

验收：每项已核字段和时间结论能回到同一事实版本原文；材料多并不自动增加合格输入数。

## Task 3：实现独立时间评估，不改旧消费者

**Files:** 新 research_admissibility.py、test_research_admissibility.py。

**Consumes:** Task 2 事实校验结果、原件、补充证据、policy。**Produces:** §3.3 三个函数中的前两个。

- [ ] 先添加可手算测试：

```python
def test_public_day_boundary():
    from lei_signal.research.research_admissibility import assess_time
    proof = {"verification": "supported", "synthetic": True,
             "kind": "public_by_date", "value": "2026-05-29",
             "evidence_ids": ["synthetic-proof-1"]}
    early = assess_time(proof, cutoff="2026-05-29T15:00:00+08:00")
    equal = assess_time(proof, cutoff="2026-05-30T00:00:00+08:00")
    assert early["status"] == "rejected"
    assert early["reason_codes"] == ["time_after_cutoff"]
    assert equal["status"] == "supported"
    assert equal["synthetic"] is True
```

- [ ] 运行 `python -m pytest tests/unit/test_research_admissibility.py -q` 留下失败；按 §3.3 时间算法实现，无截点平移。
- [ ] `verify_availability_record` 重算所有来源和抽取哈希，逐字段比较身份、时间、所指版本；事实包内找不到引用或被拒绝则不能 supported。同事实存在互斥版本而不能解释时，全部相关记录 rejected。
- [ ] 补测试并分别断言原因：精确14:00可用/16:00晚于截止、等于截止、UTC等价、无时区、非法日期、闰日、仅落款/仅取得时刻/空值、错产品/事件/版本、删绑定字段、篡改时间并重算本记录指纹、来源字节变动、重复冲突、合法控制组。
- [ ] 用假的公开记录或自填 `verified=true` 直接调用 CLI，必须无法通过原件绑定。结构核对和原文语义判断的范围分别输出，不能承诺“所有原文事实机器证真”。

验收：合成正向说明时间算法可运行；不作为真实来源合格证据。

## Task 4：逐产品、逐日期评估与旧发现映射

**Files:** research_admissibility.py、其单测；不修改 data_quality.py。

**Consumes:** Task 3 结果、LoadedSnapshot、日历、全部行动、old_quality。**Produces:** `assess_inputs` 的 JSON 可序列化结果。

- [ ] 测试先证明“仅时间通过不能令总体通过”：

```python
def test_quote_version_unknown_prevents_overall_support(synthetic_assessment):
    # fixture 必须经过真实新接口；报价无历史版本证据，公告时间满足。
    row = synthetic_assessment["coverage"][0]
    assert row["time_evidence"] == "supported"
    assert row["quote_version"] == "unknown"
    assert row["overall"] != "supported"
    assert "quote_vintage_unproven" in row["reason_codes"]
```

- [ ] 合成 fixture 使用两产品、一个已完成月和手列观察日期；上市/缺报价/未来行动各单独变更一次，期望表手工写出，不调用被测函数生成期望。
- [ ] 从日历实际完整月份推导观察日，全14×观察日都保留，包括预热不足、无报价和未上市；这些行标原因不删除。可计算性只数有效报价位置，不运行 economic_index、momentum 或 rank；不得用固定772当依据。
- [ ] 对每个观察输入记录其所需价格行及相关事件范围。v1 采用保守完整输入链核验：现有累计经济指数在观察日前消费的所有已生效行动都检查，不假设历史行动会在比值中抵消；窗口简化/代数抵消优化不在本轮。
- [ ] 行动生效日在观察日之后的，不作为该日信号输入；未来标签仅输出 `not_evaluated_this_round`，不生成或计算。行动当日是否已可知依冻结截止判断，提前公开不提前入指数。
- [ ] 上市事实、上市至首报价一致性、内部缺口、日历历史可知性、报价版本/可得性、用途逐项检查；缺证返回明确 unknown，不用一般常识代替来源。复用旧检查已经给出的真实日历/停牌发现，不重写旧引擎。
- [ ] 每个旧发现生成稳定 ID（由完整 finding 的规范化 JSON 哈希），原内容保存；旁列 `no_new_evidence / evidence_addresses_fact_only / evidence_supports_new_policy / still_blocked` 和理由。新政策不能覆盖原发现或修改旧卡的用途。
- [ ] 增补测试：未来数据追加不改变过去已有评估；新增历史证据是版本修订，不能冒称未来追加不变；全缺失、预热、未上市、停牌未证、同产品相互冲突、虚假来源、完整合法合成正向、集合完整性以及非有限价格可见。

总体结果只有在所有必需维度均 supported 或有固定规则支持的 not_applicable 时才 supported；synthetic 标志始终传递，真实报告不能引用合成正向宣称市场资料采用成功。

## Task 5：冻结入口身份及可审计输出

**Files:** 新 check_etf_research_admissibility.py、集成测试；raw synthetic。

**Interfaces:** `python scripts/check_etf_research_admissibility.py --protocol <不可变版本文件> --out <新目录>`。不提供 `--force`、`--allow-conditional`、`--accept-structural` 或跳过核验开关。

- [ ] 先写 CLI 反例测试：未知对象、卡快照漂移、删代码键、改 policy 参数、篡改原件、current 指针、已有输出目录，全部在评估前拒绝；合法合成控制组仍成功。
- [ ] 输入协议必需键由代码固定，包括本入口、新评估模块、获取脚本、抽取脚本（若有）及实际调用的旧模块；删键不能免核。读取两张卡并逐字典比较冻结卡，用途用 description 解析数学身份，不谎称新用途已登记。
- [ ] 输出协议冻结副本、`summary.json`、`facts.csv`、`coverage.csv`、`finding-map.json`、`old-quality.json`、`missing-evidence.csv`、`manifest.json`。公共对象/单位/代码身份放 manifest，行中只留对象引用、产品、观察日期、状态与原因引用。
- [ ] 退出码：0=评估完成且所声明真实范围满足本政策（或合成例完成，明确 synthetic）；2=评估完整但真实条件不足；3=身份、格式、预算或执行失败。2 允许完整评估 manifest，必须 `assessment_completed=true/research_start_recommended=false`；3 只写故障记录，不写成功 manifest。manifest 永远 `production_authorized=false/controller_acceptance=pending`。
- [ ] JSON 统一拒绝 NaN；CSV 键重复和缺键导致退出3，不把缺行默默排除。coverage 数量从冻结日历与池独立校对；每项汇总能与逐行理由对账。
- [ ] 给集成测试禁止真实网络的 fixture；所有新正向在真实函数和 CLI 中通过，不 patch 资格检查。旧消费者兼容仅用合成例和旧文件哈希，不偷偷调用旧真实研究入口。

## Task 6：一次正式资料评估及回归

**Files:** raw protocol、run-01、logs；只读固定真实输入。

- [ ] 开跑前检查新局部测试已通过、证据包与原件哈希一致、网络计数未超、旧保护清单无异常、实际输入为 run-08/snapshot。把所有代码/输入、卡、政策、任务范围和预算绑定到不可变 protocol 文件并读回校验。
- [ ] 在 CLI 内、身份预检完成后且第一次真实评估前，排他写本轮 raw 的 `real-assessment-attempt-01.json`，记录授权/命令/协议哈希/开始时间；执行者不要手工提前占位。进程失败也占用唯一额度。再次启动见该文件即拒绝，不允许换输出目录或删除记录重新取得额度。合成协议必须明确 synthetic 且全部输入来自合成目录，不能借合成模式检查真实池逃避计次。
- [ ] 正式只运行一次以下入口（命令中的文件必须已由前项排他生成）：

```bash
python scripts/check_etf_research_admissibility.py --protocol docs/experiments/raw/research-etf-admissibility-2026-09-14/protocol-v1.0.0.json --out docs/experiments/raw/research-etf-admissibility-2026-09-14/run-01
```

- [ ] 退出2是合法交付；退出3保留失败并交主控，不修完自行重跑真实资料。日志保存 stdout、stderr、退出码，不能通过管道丢失真实退出码。
- [ ] 完整回归在前轮22文件基础上加本轮3个测试文件。以下名单已核对前轮报告 §9 命令，执行前核存在，保存到 logs/regression-files.json；不用整个 tests 目录。实际运行次数最多2：

```bash
python -m pytest tests/unit/test_controller_fixes.py \
  tests/unit/test_controller_fixes_round2.py tests/unit/test_controller_fixes_round3.py \
  tests/unit/test_controller_fixes_round4.py tests/integration/test_controller_fixes_cross_module.py \
  tests/unit/test_research_data_quality.py tests/unit/test_research_data_snapshot.py \
  tests/unit/test_research_calendar_and_identity.py tests/integration/test_research_offline_loop_round2.py \
  tests/integration/test_research_data_snapshot_cli.py tests/unit/test_research_definitions.py \
  tests/unit/test_factor_runtime.py tests/unit/test_factor_diagnostics.py \
  tests/unit/test_factor_account_adapter.py tests/unit/test_experiment_reports.py \
  tests/unit/test_research_input_preflight.py tests/integration/test_research_input_preflight_cli.py \
  tests/unit/test_research_input_preflight_fix.py \
  tests/unit/test_momentum_prototype.py tests/integration/test_momentum_prototype_cli.py \
  tests/unit/test_qualification_bundle.py tests/integration/test_momentum_qualified_inputs.py \
  tests/unit/test_research_admissibility.py tests/unit/test_etf_evidence_acquisition.py \
  tests/integration/test_etf_research_admissibility_cli.py -q
```
- [ ] 固定新局部命令：

```bash
python -m pytest tests/unit/test_research_admissibility.py tests/unit/test_etf_evidence_acquisition.py tests/integration/test_etf_research_admissibility_cli.py -q
python -m ruff check src/lei_signal/research/research_admissibility.py scripts/acquire_etf_evidence.py scripts/check_etf_research_admissibility.py tests/unit/test_research_admissibility.py tests/unit/test_etf_evidence_acquisition.py tests/integration/test_etf_research_admissibility_cli.py
```

- [ ] 检查保护哈希和输出清单。由独立手列小例核3条实际代表结论的时间边界与原因映射，不再完整运行真实 `assess_inputs`。旧值/旧 manifest 不变只核哈希，不重算772值。

## Task 7：报告、导航与交主控

**Files:** 执行报告、registry/INDEX 本条、路线图日期追加；不改旧 raw 导航。

- [ ] 按现有模板写“一句话结论”和最小决策卡：本轮解决什么、比原来多知道什么、还差哪些材料、下一步和授权边界。不是收益研究，资金归因/收益对照列“不适用：本轮未运行账户”，不要伪造表格。
- [ ] 报告分列实际新材料数、已核事实数、时间条件满足数、完整输入合格数、旧消费者是否接入、是否已有预测证据；不得把它们互换。
- [ ] `research_start_recommended` 为主控复核前建议，不是授权。即使资料评估全满足，新政策到预测消费者的接入和新实验冻结仍是未完成项，不启动 IC/分组收益/账户。
- [ ] 记录全部失败、预算消耗、未执行项和源文件修改清单；前轮版本事故只引用，不抹平。本轮的新版本从创建起保留原件，不能声称引用哈希存在就等于旧原件可恢复。
- [ ] registry 使用现有分类“数据与质量”，verdict 初交 mixed；INDEX 和路线图只增本轮入口。若别人同期修改，重新读文件后合并本条，不覆盖整份。
- [ ] 检查本地链接、代码语法/测试结果和保护清单，交回报告绝对路径及待主控问题。完成即停，不提交 git。

## 4. 主控复核重点与止步条件

主控独立检查：实际来源是否支持同一事实版本的公开日期；时间边界是否保守；未知报价版本有没有被藏起来；旧发现是否完整保留；合成与真实是否分列；预算/版本是否守住。源码结构与测试数不是最终采用依据。

立即暂停受影响项：规则或输入指纹漂移、证据语义无法确定、需要额外数据/依赖、请求无法计数、预算已满、真实评估失败、受保护文件变化。其他离线文档和已授权测试可继续。发现旧范围新问题只登记，不开启新一轮修复。

## 5. 可直接转交新 GLM 的启动 prompt

```text
请在 LeiSignal 当前完整工作区执行：
docs/superpowers/plans/2026-09-14-etf-research-data-admissibility.md v1.0.0。

这是新一轮“固定ETF池资料采用与开工判断”，不是重开上一轮S1–S3返修。
先读根AGENTS、该执行规格、它链接的设计和必读规范，再按Task 0–7串行完成。
本 prompt 授权规格内的新研究专用代码、测试、有限官方资料取得和独立资料评估：
最多40次联网请求/20份新官方材料/1次真实资料评估/2次完整回归。
失败和重定向计入请求；失败真实评估也计次，不自行追加运行。

固定14只ETF、已有行情和对象定义不变；旧代码/卡/协议/输入/封存结果只读。
新规则仅独立评估，不强行放行旧动量消费者。原available_at未知仍为null，
只采用有原文支持的最晚公开边界，文内日期或今天取得时间不能假扮历史可得。
无新因子、新行情、账户、收益检验、生产、OKR、付费或依赖安装权限，不提交git。

写明实际模型、授权、输入与代码指纹；完成离线反例和合法控制组后再用正式额度。
资料仍不足是合法结果，不为通过改标准或删产品。语义歧义保留未知，继续其他项；
需要超范围时停受影响分支交主控，不自己扩项。
交付文件、执行命令/退出码/日志、证据与缺口对照、保护核对及开工建议。
完成即停，交回主控复核，不自行宣布验收、因子有效或获准交易。
```

## 6. 计划自查（主控编写时）

- 设计 §1–3 → Task 0、2–4；§4 兼容 → Task 3–5；§5 预算 → Task 0、1、6；§6 交付 → Task 7；§7 身份 → Task 0、5、6。
- 仅新增本计划并给设计补交接状态；本轮没有实现上述接口、运行测试或取得官方资料。
- 一个新 GLM 可按明确合同执行；证据语义争议与最终验收交回主控。本次未调用或派发 GLM。
