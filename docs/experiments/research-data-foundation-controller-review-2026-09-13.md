# 数据基础修复：主控复核与执行 agent 返修单

当前主控报告版本：1.2.0，2026-09-13。最新书面反馈见 §11：R1 剩余修复在本次范围内确认，R1/R2/R3 本轮收口，无新增代码必修项。§1–10 保留历次初审与返修证据，不再作为当前待执行返修单。后续长任务另见 §11.4。

## 一句话结论（大白话）

本次确认 R1 剩余修复：两份人为上市证明经两个入口、两个用途，原先错误放行的 8 个判断全部改为拒绝，日期诊断仍保留；253 项回归通过。R1/R2/R3 在本轮范围内收口，不再要求逐项返修。真实数据仍只有描述和诊断可用。下一步是把已修好的检查接成可复用的离线输入验收入口，不新增因子、数据或账户路径，不宣称数据整体合格。

> 1.1.0 历史结论：当时 R2/R3 已确认，R1 的合成及资格未知 JSON 仍可经两个入口放行，故要求只修来源资格；详见 §10。该旧版问题已由 §11 的新版本复跑确认修复。

> 初审 1.0.0 结论（历史保留）：暂不整体验收。快照入口现在会先检查停牌记录，日历也不再让乱码日期凑数，这两项修复可以保留；但上市证明仍能靠一个假来源字符串加自洽日期获得放行，直接价格检查入口也还会使用混入的账户记录解释停牌。下一步只补这两处可信证据边界，并纠正上市缺口的测试与说明，不新增因子、数据或收益实验。

## 1. 交接身份与采用规范

- 本报告版本：1.0.0；日期：2026-09-13，Asia/Shanghai。
- 被审交付：[research-controller-fixes-2026-09-11-02.md](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/research-controller-fixes-2026-09-11-02.md)。本报告不是 Qlib 文案复核，两条任务不混合。
- 主控结论：部分修复确认，剩余事项返修；不宣布整个数据基础工程完成。
- 本次实际工作：读取实现与测试、独立构造合成反例、运行已有回归、核验已有输入与哈希；没有修复研究代码。本文件是交回执行 agent 的依据，不是已完成返修的证明。
- 研究层定位：研究输入质量与证据使用边界，不改变道路、路牌、入场、退出、回补等交易规则。策略规格与规则账本不变。

权威入口仍使用项目现有文档：

| 文件 | 采用版本与作用 |
|---|---|
| [研究原则](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/research/experiment-backtest-principles.md) | v1.1；证据与验收边界 |
| [定义标准](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/research/definition-standard.md) | 1.1.0；不把数据检查通过写成定义接入或因子有效 |
| [执行与交接合同](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/research/ai-execution-contract.md) | 本次交回采用 1.0.1；新增主控书面复核交付要求，被审旧任务仍保留原 1.0.0 记录 |
| [报告模板](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/research/experiment-report-template.md) | 1.1.0；纯数据检查不要求账户收益与回归 |
| [唯一对象登记表](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/research/definitions.v1.json) | 不修改；本轮未调用因子计算。`mixed.momentum.raw@1.0.0` 仅作为尚未接入的既有对象引用，不声称已满足其输入 |

没有新政策卡或账户冻结协议：本轮不运行策略。被审修复基线为 [baseline.json](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-controller-fixes-2026-09-11-02/baseline.json)。后续执行前记录当前工作区实际指纹，不倒填旧协议。

### 本次被审版本的精确身份

| 文件 | SHA-256 |
|---|---|
| `src/lei_signal/research/data_quality.py` | `fbd3429d0bd9c159bc9f79cc57e5ff91e5d55fa1f9080b035b48b286096fe65a` |
| `src/lei_signal/research/trading_calendar.py` | `4651fa7d0e1e20aeaf3b40d9446f3ea76ec0eac037bbe965c018c3e5ccb6389e` |
| `tests/unit/test_controller_fixes_round2.py` | `b9a70e77f43d093320b32d96d61e5fe9fe9f7e9a34b3d53678d516eebb6c4890` |
| 被审补充报告 | `990004ba3dac1c4da526bf818ec294f3bfeb9516cb981d1518938cf547bef14e` |

若执行时指纹已改变，先核对新差异，不以本报告认定后来的版本仍存在相同问题。

## 2. 已确认成果：保留，不重做

| 被审事项 | 独立复核结论 |
|---|---|
| `check_snapshot` 先校验行动、再解释缺口 | 本次检查成立；混入账户字段的记录在该入口被拒绝。现有测试也覆盖错误身份、冲突 ID、日期非法及合法记录正向路径。结论限定于这个入口。 |
| 冲突 `event_id` 整体排除 | 实现先收集被阻断的记录索引及 ID，再筛出可用停牌记录；不是只排除后出现的重复条目。 |
| 日历按真实日期集合判断完整 | 本次检查成立；既有测试覆盖非法日期替换、合法闰日、部分区间与整月完整性的区分。 |
| 合法真实行动不被误伤 | 现有 21 条行动均未出现 BLOCK 级问题；不等于来源或历史到达时间因此全部合格。 |
| 真实停牌引用 | 512890 的 2021-10-22 缺口仍解释为 `512890-halt-2021-10-22`；解释来源不等于证明当时可交易。 |
| 受保护文件 | 896 项逐文件哈希无变化，聚合哈希与原基线一致。 |

## 3. 返修 R1：上市日期自洽不能代替来源核验

优先级：必须处理，影响是否放行研究用途。

位置：[data_quality.py::_validate_listing_evidence](/Users/yongbiaoli/Desktop/lei-signal-lab/src/lei_signal/research/data_quality.py:802)，尤其 source 检查及返回 `structural=True` 的逻辑。

当前实现只验证 `source` 是非空字符串，并检查上市日期与窗口、首报价的关系。主控独立反例：评价期 2026-05-28 至 2026-06-02，晚出现的产品首报价是 2026-06-01，传入：

```json
{"listing_date": "2026-06-01", "source": "dummy"}
```

实际变化：不提供证据时 `structural=False`，`require_use(..., accept_structural=True)` 拒绝；加入上述数据后 `structural=True`，该调用放行。数据仍标为 conditional，但调用方只接受“已确认固有属性”的开关已足以绕过。

### 最小修改要求

1. 把“字段合法且日期自洽”与“来源已核验、确实支持该产品与日期”分开；前者不能单独产生正常研究用途所需的证据资格。
2. 优先复用现有可回查资料与资格记录；引用须绑定实际产品、日期、来源及内容身份。不要仅新增一个由调用方自由填写的 `verified=True`、可信标签或字符串白名单，把同一问题换个名字保留。
3. 本地无合格来源时继续拒绝，不为通过验收下载新资料、编造证明或新增一套平行登记库。合成数据可以验证算法，但不能因为来源写着“合成测试”就升级真实市场资格。
4. 保留诊断输出：让执行者看见“日期自洽，但来源未核验”的具体原因。不要一律抛错或关闭所有合法路径冒充修复。

### 验收要求

- 无来源、空来源、`dummy` 配自洽日期、无法回查的引用均不能凭 `accept_structural=True` 放行正常研究用途。
- 来源对应另一产品或另一上市日期时拒绝；引用内容发生变化时不得继续沿用旧核验结论。
- 日期自洽的合成小例可检查内部算法，但输出必须明确不是真实资格证明。
- 有合法资格证据时应保留正向路径；没有真实材料，就把该真实路径列未验证，不伪造“已接入”。

## 4. 返修 R2：直接价格入口不能消费未核验停牌记录

优先级：必须处理，属于同类保护的既有入口补接；不得因此声称重建整个研究流程。

位置：[check_prices 的日历调用](/Users/yongbiaoli/Desktop/lei-signal-lab/src/lei_signal/research/data_quality.py:310) 仍把原始 `halts` 交给 `_check_against_calendar`。`_halt_index` 的说明要求调用方已核验，但普通序列参数并未保障这一点。

主控使用两只合成产品：第一只有 6 月 1、2、3 日报价，第二只缺 6 月 2 日。给第二只补一条日期正确、但带 `account_id` 和 `amount` 的记录：

| 路径 | 排序裁决 | `accept_structural=True` |
|---|---|---|
| 直接 `check_prices`，不传停牌记录 | conditional | 拒绝 |
| 直接 `check_prices`，传混入账户字段的记录 | usable | 放行，缺口被解释成 halt |
| `check_snapshot`，传同一记录 | conditional | 拒绝，并报告 `events_passed_as_actions` |

### 最小修改要求

统一“验证后才能消费”的责任：可以让两个研究入口复用同一行动验证结果，也可以让直接入口明确拒绝未经验证的原始停牌记录。采用哪一种按当前调用者选择最小改动，不能只补“调用方必须保证”的注释，也不需要新建通用框架。

### 验收要求

- 相同非法记录经过两个入口，均不能解释缺口或升级排序用途。
- 至少覆盖账户字段混入、错误身份、缺 ID、冲突 ID、非法区间；冲突 ID 下全部记录不可信。
- 合法停牌仍能解释具体产品、具体日期，引用保留 `event_id`；不补造 `available_at`。
- 列出本次实际接入和未接入的既有消费者。CLI 等未消费 halts 的路径不因名称相关就强制重构；也不能把本次有限补接写成全仓库迁移完成。

## 5. 返修 R3：先明确上市当天的资格，再修正测试

优先级：必须纠正测试证据；资格起点的含义需要明确，不能为测试通过擅自放宽。

### 5.1 残余缺口测试提前命中了另一条件

[test_listing_with_residual_gap_stays_unconfirmed](/Users/yongbiaoli/Desktop/lei-signal-lab/tests/unit/test_controller_fixes_round2.py:283) 使用上市日期 2026-05-20，评价期从 2026-05-28 开始。主控实际返回原因是“上市日期早于评价期起点”，还未执行残余缺口检查。

请把上市日期放进评价期，确保中间确有已知开市但缺报价的日子，并断言拒绝原因为“残余缺口”，而不只是断言最终 `structural=False`。

主控用于区分分支的合成小例：同样的评价期起点 5 月 28 日、首报价 6 月 1 日：

- 上市 5 月 20 日：命中“上市早于评价期”，不是残余缺口。
- 上市 5 月 28 日：当前实现发现中间 5 月 29 日缺报价，拒绝原因确为残余缺口。
- 上市 5 月 29 日：当前实现排除了上市日，残余为空，判为自洽。

### 5.2 “周五上市、周一首报价”不能无条件当作正常

当前实现把上市日与首报价日两个端点排除。合成日历明确 2026-05-29 周五开市，但周五上市、周一首报价仍可被整体解释。本轮没有新增市场资料证明这类情况一律正常。

应先说清 `listing_date` 表示什么，以及何时开始应该有报价。如果上市当天已具备报价资格，不能仅因隔着周末就忽略当天；若确有不同的资格起点或停牌解释，必须有相应证据。资格起点未知则保留未知，不擅自创建交易规则。

被审报告称已补周五上市的正向测试，但目前 18 项测试中的上市正向例实际是“6 月 1 日上市且同日首报价”，未找到该周五案例。修正报告描述；仅在含义和证据明确后补相应正向例，不能先定它必须通过。

## 6. 可直接交给执行 agent 的任务合同

请先读本报告及现有 AGENTS、研究规范，核对被审版本。只处理 R1–R3，不重新规划整个数据基础工程。

### 6.1 范围、资源与文件

- 可改：`src/lei_signal/research/data_quality.py`、对应研究测试，以及必要的研究专用薄适配；如需要改其他研究调用者，先写明具体调用链和必要性，不顺手迁移全仓库。
- `trading_calendar.py` 本轮修复已被确认，不默认重做；若 R3 涉及日历调用，只处理已证明必要的局部变化。
- 文档：新增带日期的返修交付报告和独立输出目录；旧报告可加纠正指针/修订记录，不覆盖历史正文或旧源码证据。
- 保护：冻结 raw 输入/旧结果、对象登记表、策略规格、规则账本、生产消费者、正在运行的 v0、账户路径、真实交易权限、OKR 均不改。
- 网络、付费、新依赖、新因子、新数据源、新产品：均为 0；不运行收益回测，不运行变异工具，不调用可能覆盖封存输出的旧入口。
- 既有授权不清或确需扩项时，只暂停受影响分支并写明待确认事项；本返修单不扩大外部或生产权限。

### 6.2 执行顺序

1. 记录当前代码、输入和受保护文件指纹；如与本报告不同，先核差异。
2. 先用下方独立小例复现 R1/R2；把预期拒绝写成失败测试。旧测试通过不是新问题已修复的证明。
3. 明确证据可信边界与两个入口的职责，完成最小修复；不把真假来源判断简化成禁止 `dummy` 一个字符串。
4. 对 R3 先记录资格起点的定义或缺口，再分别覆盖实际分支。无法确认的来源与资格保持受限，继续完成其他项。
5. 重跑相关测试、静态检查、真实输入只读质量复核和保护哈希；报告实际计数，不追求固定的 233。
6. 更新交付报告、登记与导航前重读共享文件，避免覆盖其他 agent 的修改；本主控报告保持历史证据，新结论写新版本/新小节。

### 6.3 交回格式与停止条件

按 R1/R2/R3 返回：修复前反例、根因、最小改动、修复后正反例、实际命令/退出码/计数、前后代码哈希、影响的真实数据裁决、未接入项、失败史与待确认项。

必须区分：日期与字段合法、来源已核验、用途获准、算法有效、生产授权。这五件事不能合并成一个“通过”。真实数据没有合格来源而保持拒绝，是可以接受的安全结果；但代码仍能接受假证明则不能声称已解决。

R1/R2 的已复现遗漏不再放行、R3 的测试真正覆盖声称分支且语义不靠猜测后，完成即停并交主控复核。没有额外收益或数据扩建任务。主控下一次仍须返回书面复核报告；执行者不得自行宣布最终验收。

## 7. 主控独立反例复跑入口

以下仅构造合成行情与合成日历，在内存中调用现有研究函数；不是真实行情证据，不写文件、不联网、不运行账户。假定 `verified=True` 的对象仅用于合成调用路径对照，不是对真实快照核验的替代。

从仓库根目录运行。当前版本输出的是已发现的问题；返修后应拒绝非法证据，或者直接入口明确拒绝未经核验的 halts，不能为维持旧输出改回错误行为。

```bash
python3 - <<'PY'
from datetime import date, timedelta
from types import SimpleNamespace
import pandas as pd
from lei_signal.research import data_quality as q
from lei_signal.research.trading_calendar import TradingCalendar

days = {}
d = date(2026, 5, 1)
while d <= date(2026, 6, 30):
    tr = d.weekday() < 5
    days[d.isoformat()] = {
        'is_trading_day': tr, 'source_flag': '1' if tr else '0',
        'source_month': d.isoformat()[:7],
    }
    d += timedelta(days=1)
cal = TradingCalendar({
    'authority': 'exchange_official',
    'publisher': 'SYNTHETIC ALGORITHM TEST ONLY',
    'months_requested': ['2026-05', '2026-06'], 'days': days,
})

def frame(ds):
    return pd.DataFrame({
        'open': [10.] * len(ds), 'high': [11.] * len(ds),
        'low': [9.] * len(ds), 'close': [10.] * len(ds),
        'volume': [100.] * len(ds),
    }, index=pd.to_datetime(ds))

def result(report):
    try:
        q.require_use(report, 'ranking', accept_structural=True)
        gate = 'ALLOWED'
    except q.UseNotPermitted:
        gate = 'REJECTED'
    return report.verdict_for('ranking'), gate

frames = {
    '510300.SS': frame(['2026-05-28', '2026-05-29', '2026-06-01', '2026-06-02']),
    '512890.SS': frame(['2026-06-01', '2026-06-02']),
}
for label, evidence in [
    ('no_evidence', None),
    ('dummy_plus_date', {'listing_date': '2026-06-01', 'source': 'dummy'}),
    ('friday_listing', {'listing_date': '2026-05-29', 'source': 'synthetic'}),
]:
    report = q.check_prices(
        frames, calendar=cal, evaluation_start='2026-05-28',
        evaluation_end='2026-06-02',
        listing_evidence={'512890.SS': evidence} if evidence else None,
    )
    f = next(f for f in report.findings if f.code == 'starts_after_window')
    print(label, result(report), f.structural, f.evidence['evidence_check'])

frames = {
    '510300.SS': frame(['2026-06-01', '2026-06-02', '2026-06-03']),
    '512890.SS': frame(['2026-06-01', '2026-06-03']),
}
action = {
    'event_id': 'synthetic-halt', 'symbol': '512890.SS',
    'type': 'trading_halt', 'effective_date': '2026-06-02',
    'halt': {'start_date': '2026-06-02', 'end_date': '2026-06-02'},
    'account_id': 'test-account', 'amount': 0,
}
kw = dict(calendar=cal, evaluation_start='2026-06-01', evaluation_end='2026-06-03')
loaded = SimpleNamespace(
    frames=frames, verified=True,
    snapshot={'semantics': {'price_basis': 'nominal_close', 'currency': 'CNY'}},
)
for label, report in [
    ('direct_no_halt', q.check_prices(frames, **kw)),
    ('direct_account_event', q.check_prices(frames, halts=[action], **kw)),
    ('snapshot_account_event', q.check_snapshot(loaded, actions=[action], **kw)),
]:
    print(label, result(report), [
        (f.code, f.level, f.evidence.get('cause')) for f in report.findings
        if f.code in ('product_internal_gap', 'events_passed_as_actions')
    ])
PY
```

## 8. 已执行验证及其边界

主控在本次复核过程中实际执行以下已有回归命令，结果 233 passed、退出码 0：

```bash
python3 -m pytest \
  tests/unit/test_controller_fixes.py \
  tests/unit/test_controller_fixes_round2.py \
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
  tests/unit/test_experiment_reports.py -q

python3 -m ruff check \
  src/lei_signal/research/data_quality.py \
  src/lei_signal/research/trading_calendar.py \
  src/lei_signal/research/data_snapshot.py \
  src/lei_signal/research/symbol_identity.py \
  tests/unit/test_controller_fixes_round2.py
```

ruff 返回 `All checks passed!`。这两项只证明现有测试与静态检查通过，不覆盖刚发现的独立反例。未重新执行旧版本来验证执行者所称“修复前 12 个失败”；该数字保留为执行者历史记录，不包装成主控独立重现。

真实输入只读复核使用：

- 快照：`docs/experiments/raw/research-identity-wiring-2026-09-10/canonical-snapshot-v2`，加载结果 `verified=True`。
- 日历：`docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json`；发布时间记录为同研究目录的 `publication-evidence.json`。
- 行动：`docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/action-sources/normalized-actions.json` 中的 `events` 容器；容器名不改变其原始行动内容与身份，账户事件仍不得混入。
- 评价期：2019-09-02 至 2026-06-30。日历 `complete=True`，`invalid_records=0`；21 条行动没有 BLOCK 级发现。
- description、diagnostic 为 usable；ranking、comparison、research_signal、attribution 为 conditional。对后四项调用 `accept_structural=True` 均拒绝；conditional 不等于已准许使用。不得把它们误写成 `unusable` 枚举，也不得以 `allow_conditional=True` 的显式接受行为冒充绕过不可用状态的缺陷。
- 受保护清单：[protected-baseline.json](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-data-provenance-round2-2026-09-10/protected-baseline.json)。896 项无变化；聚合 SHA-256 为 `fbfae8e3bbe735a363c16622737026f721805467fbca87b3eaa909bd8c3a4846`，算法沿该基线，不更换排序或拼接规则。

历史到达时间仍没有因此获得证明。无收益实验、无预测测试、无资金归因；三层归因均不适用。未改动生产权限或 OKR。

## 9. 主控文件交付与 ARCHIVE

本轮补交书面复核产物；返修工作尚未实施。

- 新增本报告，登记到报告库为“数据与质量”／mixed，并在 INDEX 增加主控复核入口；原执行报告正文不覆盖。
- 当前导航不得继续把执行者“三处均已修复”的主张当成主控结论；同一原报告的导航摘要明确标注本次待返修状态，旧主张仍可回查原正文。
- 交接合同 1.0.0 → 1.0.1，只增加每轮主控书面复核交付义务；旧 1.0.0 存入只读历史快照，根 AGENTS 更新简短路由。其他规范、旧实验协议、对象版本不变。
- 本次没有把执行返修要求实际派发给另一个任务；用户可直接把本文件交给原执行 agent。

### 本文件交付检查

- 从本报告 §7 提取并实际执行复跑代码，R1/R2 的错误放行及快照入口正确拒绝均与审核记录一致；这是复核反例仍存在的证明，不是返修通过。
- 本报告 11 个本地文件链接目标均存在；现有报告库扫描可提取结论、识别 category 与 mixed 状态，无待分类标记。
- 新文档登记后重跑 `python3 -m pytest tests/unit/test_experiment_reports.py -q`：4 passed，退出码 0。相关已跟踪文档 `git diff --check` 通过；不代表已审核工作区其他改动。
- 被审报告、两份研究库代码和被审测试文件的哈希保持 §1 原值；交接合同历史快照与旧版逐字节一致。新合同 1.0.1 SHA-256：`deab6c1ca20505f92d06516ffff943b8501fff2e01f8c6b3928c6626072af962`。
- 本次实际修改仅六个文档/导航文件：本报告、registry.json、INDEX.md、AGENTS.md、ai-execution-contract.md 及其 1.0.0 历史快照。无研究代码修复，无 OKR 写入。

### 最小决策卡

| 必答项 | 回答 |
|---|---|
| 本轮改变什么决策？ | 是否接受数据基础三项修复交付；目前部分确认、仍需返修 |
| 比谁好、新增什么？ | 同一合成输入对照两个入口与有/无证据，新增独立反例，不比较收益 |
| 钱从哪里来？ | 不适用，未计算账户损益 |
| 代价与执行条件？ | 仅已有研究代码的有限修复及测试；无新数据、无账户路径、无生产改动 |
| 现在怎么办？ | 执行 agent 按 R1–R3 返回修复证据；有资格语义缺口则保留未知 |
| 证据与授权上限？ | 只能说明输入检查行为；不证明策略/因子有效，不授予交易或 OKR 完成状态 |

## 10. R1/R2/R3 交付后的主控复核与最新返修单（2026-09-13）

### 10.1 当前结论、版本与已确认项

被审交付：[research-controller-fixes-2026-09-13.md](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/research-controller-fixes-2026-09-13.md)。本节为主控书面回执，采用现有执行与交接合同 1.0.1；不修改旧规范、冻结协议或对象版本。

**结论：部分确认，R2/R3 保留，仅 R1 继续返修。** 已经解决的字符串来源、错误哈希、错产品/日期等检查不撤销；但这些检查不能独立证明一份来源可信。

| 事项 | 本次主控判断 |
|---|---|
| R1：来源资格 | 未完成。文件可回查、哈希一致和内容自洽已经检查，但合成/未声明资格资料仍会被当作已确认的晚上市证据 |
| R2：两个研究入口的非法停牌消费 | 本次范围内确认。重跑原 §7 反例后，无停牌记录、直接入口混入账户记录、快照入口混入同一记录均拒绝；非法记录的发现可见。合法停牌正向路径保留。这里不是说两个入口所有用途裁决都完全相同，也不是全仓库迁移完成 |
| R3：测试分支与周五上市假设 | 本次范围内确认。测试已实际区分“早于评价期”和“残余缺口”，并断言残余日；无证据的“周五上市、周一首报价正常”说法撤回。不再要求重做此部分 |
| 已确认的日历修复 | 保留；本轮 trading_calendar.py 哈希未变 |

本次核对的实际文件身份如下。执行报告原哈希栏使用了“已变化（见下）”但未填完整修复后值，本表提供主控实测值；下次交付应填完整指纹，不以占位说明代替。

| 文件 | SHA-256 |
|---|---|
| `src/lei_signal/research/data_quality.py` | `d8f34018a0101fdabccb0d02bffa0e1e608cc642402298813699939228156bb6` |
| `src/lei_signal/research/trading_calendar.py` | `4651fa7d0e1e20aeaf3b40d9446f3ea76ec0eac037bbe965c018c3e5ccb6389e` |
| `tests/unit/test_controller_fixes_round3.py` | `3d1d8def97a7f050644b910e523265b7befc326ff57e7997f41956c9814a98c3` |
| `tests/unit/test_controller_fixes_round2.py` | `f318226057dc2288d68a7701fead8649fd5f4fc09b494986457f8dbfe3e8b0b8` |
| `tests/unit/test_research_data_quality.py` | `11ba81e23a833c9ce6cccd415e477e2647a4c2a8c17dbe88da72dd34a95c5ba7` |
| 被审 9-13 执行报告 | `f9a3b7dd41861b91e3bcec5311f12f24601467ee3c00646635eb79b31e6277f6` |
| 本主控报告更新前 1.0.0 | `212a28bab6b0df6b45a1c8ae89b44459fd8858deb10ccb08a82ea41d41e79904`；本次更新为 1.1.0，旧正文保留 |

### 10.2 R1 的剩余反例：合成标签没有进入放行判断

证据文件均由主控人为构造，明确不是真实市场资料，没有下载新数据：

- [显式合成文件](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-data-foundation-controller-review-2026-09-13/listing-explicit-synthetic.json)：SHA-256 `bdd9348897f388dd573b5cd097579f60ae7448d4627812ca4523bdb15579b1f1`。
- [未声明资格文件](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-data-foundation-controller-review-2026-09-13/listing-qualification-omitted.json)：SHA-256 `3b6520db7cc550dc322c5c603604522a029c1b9fa8cad23820fd75e355f2e9cc`。省略 qualification 是刻意测试，不代表文件真实。

两份文件都写同一产品 `512890` 与日期 `2026-06-01`，匹配合成价格的首次报价。调用者为文件计算正确哈希并传入两个正常研究入口，主控实测：

| 人为构造的来源 | 入口 | 输出 synthetic | 输出 structural | ranking | `accept_structural=True` |
|---|---|---|---|---|---|
| 明确写 `synthetic_algorithm_test` | check_prices | True | True | conditional | **放行** |
| 明确写 `synthetic_algorithm_test` | check_snapshot | True | True | conditional | **放行** |
| 不提供 qualification | check_prices | False | True | conditional | **放行** |
| 不提供 qualification | check_snapshot | False | True | conditional | **放行** |

这里没有把 `allow_conditional=True` 的显式接受行为当成缺陷；测试未启用该选项。问题是：本来只接受已确认固有属性的 `accept_structural=True`，已足以接受一份明知是人为编写的上市证明。

原因定位：

- [data_quality.py:937](/Users/yongbiaoli/Desktop/lei-signal-lab/src/lei_signal/research/data_quality.py:937) 只判断 qualification 是否恰好等于合成字符串。省略或换成其他值就得到 `synthetic=False`，但“没有合成标签”不等于“真实来源已经核验”。
- [data_quality.py:974](/Users/yongbiaoli/Desktop/lei-signal-lab/src/lei_signal/research/data_quality.py:974) 在日期自洽后无条件返回 `structural=True`，synthetic 只作为附带说明；下游将该值直接转成可接受的固有属性。
- [round3 正向测试](/Users/yongbiaoli/Desktop/lei-signal-lab/tests/unit/test_controller_fixes_round3.py:120) 只检查 structural 与 synthetic 标签，没有继续调用 `require_use` 验证“合成记录不得成为正常研究资格”。因此现有测试通过不能覆盖这次遗漏。

文件哈希证明的是“读取的字节与所引用的字节一致”，不是“文件里的事实是真的”。同一个调用方能写文件、算哈希、填上市日期时，这三件事相互一致仍不足以建立独立可信来源。

### 10.3 给执行 agent 的唯一剩余返修要求

本轮不要再扩展真实来源格式、增加可信标签或搭建新认证体系。真实资料准入标准尚未建立、也没有合格本地材料时，最小安全结果就是：**这类合成/自述 JSON 可用于诊断日期算法，不能成为真实研究的上市资格。**

1. **分开两种结果。** 保留“日期与窗口是否自洽”的独立算法结果，但它不能自动驱动普通研究报告中的 `structural=True`。合成、资格未知、未核验的来源在正常入口保持 `cause=unconfirmed` 或等价的未核验状态。
2. **未知不能默认真实。** qualification 缺失、未识别、自填 `official/verified` 等值，不得因“不等于 synthetic”就获得真实资料资格。也不能新增一个调用方随意填的 `trusted=True` 来放行。
3. **两入口均作最终用途验证。** 用本节两份固定反例，经 `check_prices` 与 `check_snapshot` 后，再对 ranking、comparison 调用 `require_use(..., accept_structural=True)`，必须拒绝。这一检查不能只停在函数返回的 synthetic 标签。
4. **保留算法正向例。** 同日上市/首报价、早于评价期、残余缺口等计算仍可用合成记录检查，分别断言实际原因；但要在测试中区分“算法计算成立”和“正常研究资格被接受”。不要为保持旧测试的 `structural=True` 断言而保留错误放行。
5. **不更改已有显式授权语义。** 本次不要求改写 `allow_conditional` 的定义，也不把所有 conditional 一律改为 BLOCK。只修复“未经核验的来源被当成已确认固有属性”的错误；真实数据继续受限即可。
6. **收窄报告结论。** 把“假的进不来”限定到实测通过的检查；旧测试因接口变化失败只证明原用例不再满足接口，不能单凭四项失败宣布来源可信已实现。下次填写最终代码哈希，保留失败史。

可写范围沿 §6，但进一步收窄为 `data_quality.py` 的 R1 资格使用逻辑、相关测试与本次返修交付文档。R2/R3 与日历已确认部分只跑回归，不要求重做；若拆出纯研究日期辅助函数是隔离算法与资格所必需，可采用最小实现并记录调用者。不得改生产、对象登记、冻结输入、策略、账户路径或 OKR；网络、新依赖、新数据源均为 0。

如果想引入真实上市资料或建立新的来源审核流程，另列后续待授权事项，**不是本轮收口条件**。不能因为缺资料就继续允许自述文件取得资格。

### 10.4 可复跑的当前反例

从仓库根目录执行。使用上面已经保存的两份合成文件，代码只读文件、在内存中计算，不写价格或运行账户。`verified=True` 的简化对象仅表示合成调用路径夹具，不能代替真实快照校验。

```bash
python3 - <<'PY'
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
import hashlib
import pandas as pd
from lei_signal.research import data_quality as q
from lei_signal.research.trading_calendar import TradingCalendar

days = {}
d = date(2026, 5, 1)
while d <= date(2026, 6, 30):
    tr = d.weekday() < 5
    days[str(d)] = {'is_trading_day': tr, 'source_flag': str(int(tr)),
                    'source_month': str(d)[:7]}
    d += timedelta(days=1)
cal = TradingCalendar({'authority': 'exchange_official',
    'publisher': 'SYNTHETIC ONLY', 'months_requested': ['2026-05', '2026-06'],
    'days': days})
def frame(ds):
    return pd.DataFrame({'open': [10.] * len(ds), 'high': [11.] * len(ds),
        'low': [9.] * len(ds), 'close': [10.] * len(ds),
        'volume': [100.] * len(ds)}, index=pd.to_datetime(ds))
frames = {'510300.SS': frame(['2026-05-28', '2026-05-29', '2026-06-01', '2026-06-02']),
          '512890.SS': frame(['2026-06-01', '2026-06-02'])}
kw = dict(calendar=cal, evaluation_start='2026-05-28', evaluation_end='2026-06-02')
base = Path('docs/experiments/raw/research-data-foundation-controller-review-2026-09-13')
for filename in ('listing-explicit-synthetic.json', 'listing-qualification-omitted.json'):
    p = base / filename
    evidence = {'512890.SS': {'listing_date': '2026-06-01', 'source': {
        'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}}}
    loaded = SimpleNamespace(verified=True, frames=frames,
        snapshot={'semantics': {'price_basis': 'nominal_close', 'currency': 'CNY'}})
    reports = {
        'check_prices': q.check_prices(frames, listing_evidence=evidence, **kw),
        'check_snapshot': q.check_snapshot(loaded, listing_evidence=evidence, **kw),
    }
    for entry, report in reports.items():
        f = next(f for f in report.findings if f.code == 'starts_after_window')
        outcomes = {}
        for use in ('ranking', 'comparison'):
            try:
                q.require_use(report, use, accept_structural=True)
                outcomes[use] = 'ALLOWED'
            except q.UseNotPermitted:
                outcomes[use] = 'REJECTED'
        print(filename, entry, 'structural=', f.structural,
              'synthetic=', f.evidence['evidence_check'].get('synthetic'), outcomes)
PY
```

修复前输出的 ALLOWED 是反例，不是通过条件。返修后两份文件、两个入口、两个用途都应 REJECTED，同时日期算法仍能给出自洽/残余等诊断。不得修改或删除这两份反例来使验证通过。

### 10.5 本次主控实际验证记录

- 运行被审报告列出的完整回归命令（§8 的 13 个文件另加 `tests/unit/test_controller_fixes_round3.py`）：**245 passed，退出码 0**；运行本次七个代码/测试文件的 ruff 检查：`All checks passed!`。未重跑旧版来独立验证“修复前 6 个失败”的历史计数。
- 从旧 §7 实际提取代码并重跑：字符串假来源被拒；直接账户事件、快照账户事件路径均拒绝且报告可见。旧反例被修复，但本节新增的结构化假来源仍能放行。
- 按 §8 相同路径、评价期和参数只读复核真实输入：`verified=True`；description/diagnostic 为 usable，其余四项为 conditional；对后四项启用 `accept_structural=True` 仍拒绝。512890 的停牌引用仍是 `512890-halt-2021-10-22`。
- 896 个受保护文件逐一核对无变化；聚合哈希仍为 `fbfae8e3bbe735a363c16622737026f721805467fbca87b3eaa909bd8c3a4846`。
- 主控没有修改研究代码、执行报告、旧快照或规则；本次只更新本书面报告及登记导航，新增两份明确标注的人为反例文件。网络 0 次，未改 OKR，未跑收益回测或变异工具。
- 交付前直接执行本报告 §10.4：两份文件 × 两个入口 × ranking/comparison，八个用途判断均为 ALLOWED，确认剩余问题。登记修改后报告库测试 **4 passed**；实际 `scan_reports` 中两份报告均为“数据与质量 / mixed”，无待分类状态；17 个本地链接存在，登记 JSON 无重复键，8 个代码/执行报告/反例文件指纹一致，导航差异与报告格式检查通过。

### 10.6 交回与停止条件

交回执行 agent：仅处理 §10.3 的 R1 剩余问题，R2/R3 无新增必修项。返回两个入口的最终用途断言、独立日期算法正反例、实际回归计数、完整文件哈希和未确认的真实资料路径；把“资料尚无合格来源但被准确拒绝”作为合法交付结果。

本节两份反例不再凭 `accept_structural=True` 获得 ranking/comparison 放行，算法诊断与既有 R2/R3 正向路径保持后，完成即停并再次交主控书面复核。无需为本轮取得真实上市资料，不自行宣布整体数据基础、因子、策略或交易验收完成。

## 11. R1 剩余修复收口与后续长任务（2026-09-13）

### 11.1 书面结论

被审报告：[research-controller-fixes-2026-09-13-02.md](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/research-controller-fixes-2026-09-13-02.md)。**本轮修复在限定范围内确认，代码必修项：无。** 不要求再取得真实上市材料，也不要求重做 R2/R3、日历或 Qlib 审阅。

`_check_listing_dates` 保留日期诊断，`_verify_listing_source` 当前不向自述文件授予真实来源资格，最终 `starts_after_window` 保持未确认。这正是 §10.3 要求的安全结果，不把“真实来源尚未建立”再次当作本轮未完成。

这不是全仓库安全审计或数据整体合格证明；例如来源解析器的所有异常文件类型、旧 CLI 与各消费者的整条组合调用，并未因这次 R1 检查获得全面核验。后续任务按实际依赖补测，不以不断扩大反例范围让本次修复永不结束。

### 11.2 主控实际复核

- 直接提取并执行本报告 §10.4 的原代码，没有修改固定反例：两份文件 × 两个入口 × ranking/comparison，**8 个判断全部 REJECTED**，`structural=False`；明确合成的标记仍保留。
- 重跑执行报告 §4 所列 15 个测试文件：**253 passed in 25.39s，退出码 0**。日期同日、早于评价期、残余日、周五上市、假官方声明与旧 R2/R3 正向例均包含在该回归范围；这是重跑既有测试，与上一条独立固定反例分别记证据。
- 执行报告 §4 的六文件 ruff 检查：`All checks passed!`。未重建旧代码验证历史失败计数。
- 按 §8 的同一真实快照、日历、行动和评价期只读重算：`verified=True`；description/diagnostic 为 usable，另外四项为 conditional，启用 `accept_structural=True` 后仍拒绝。512890 停牌解释仍引用 `512890-halt-2021-10-22`。
- 896 个保护文件逐一复核无变化，聚合 SHA-256 仍为 `fbfae8e3bbe735a363c16622737026f721805467fbca87b3eaa909bd8c3a4846`。

被审身份（完整 SHA-256）：

| 文件 | 本次实测 |
|---|---|
| `data_quality.py` | `ddad2ecfd676e0c1c9dbc3787afcc29024c53581f3eb664a97167f2e9fc8f783` |
| `trading_calendar.py` | `4651fa7d0e1e20aeaf3b40d9446f3ea76ec0eac037bbe965c018c3e5ccb6389e` |
| `test_controller_fixes_round4.py` | `6bfc96a54dd47c4d159b20a0f3c401d648f2eccb7e6d14b073a0eac080d46ca6` |
| `test_controller_fixes_round3.py` | `5621dd9d2cb5ec872275e45aa9c354ef386b3833f597f02b54c56fc678cfb55b` |
| `test_controller_fixes_round2.py` | `7450340f7dc89b52aa19ff6846765fc1f5f204a278f9a75a5c1c9230ef713d6f` |
| `test_research_data_quality.py` | `b9d05bdc088e528371e631c6b9bbe54cda0d1d5086bcaacf9677f8a3d0e031a9` |
| 被审 `research-controller-fixes-2026-09-13-02.md` | `1567dbe24f81f003e9cc208b1e8ebe8b6a853cd446eedddf25d533bc7873042d` |

### 11.3 非阻断说明与剩余边界

执行报告虽然标题写“完整哈希”，三个修改过的测试仍是“已变化”占位；本主控记录已补齐，**不为这项文案再开一轮返修**，下一轮交付直接生成完整文件清单。报告“任何输入不再产生 structural=True”仅适用于上市证据判断，不能推广到所有风险发现；合法停牌等其他解释仍有独立语义。

仍未完成：真实上市来源资格、公司行动历史可得时点、定义所需 `economic_index` 与名义价快照的接入、消费者组合检查。缺失资料不补造，来源哈希不能替代历史时点证据。

### 11.4 交给执行 agent 的长任务

用户本次要求“这次能不能给一个长任务”。任务书为[研究输入离线验收与因子开工交接计划](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/superpowers/plans/2026-09-13-research-input-preflight.md) v1.0.0。这是新任务，旧 v0 仍保持原冻结协议；主控本次只交计划，没有执行其中开发。

目标不是再造来源认证系统，而是把既有快照、质量检查、用途声明与定义绑定串成一个真正可运行的离线检查入口；同时交清未接入消费者与下一步数据需求。真实对象仍因缺输入而被拒绝，允许作为正确结果收口。阶段通过后可连续推进，不必每修一个测试就回主控；越出文件、资源或方法范围才暂停受影响项。

本次主控仅改书面报告、计划与登记导航；未改研究代码、执行报告、旧输入、生产或 OKR，无联网和收益回测。
