# 双均线 B0 剩余四项限定修复 Implementation Plan

> **For agentic workers:** 使用可用的 executing-plans 技能顺序执行；无该技能则直接遵循本文，不安装技能、不另派子agent。使用小步apply_patch，不用批量文本重写器。

**Goal:** 修复自填证据升级、稀疏截止、可空布尔接入和证据漏归档四项问题；不扩建因子体系。

**Architecture:** 只修现有factor_unit合同/描述模块和资格CLI，保留close_state及旧factor_lab。所有统计验证用合成资料，真实资料仅检查身份与结构，仍不授予B1资格。

**Tech Stack:** 现有Python、pandas、numpy、pytest、ruff；零新依赖、零联网。

版本v1.0.0；2026-09-15。

## 0. 消息来源、授权和交接（强制）

**用户直接决定：** 在主控提出“集中修剩余四项，不联网、不新增因子、不跑真实收益”的建议后，用户回复“可以”。本授权仅覆盖本文限定修复，不覆盖资料获取、目标变更、真实研究、生产或OKR。

**主控已有裁决：** [限定复核报告](../../experiments/factor-unit-b0-fix-controller-review-2026-09-15.md) v1.0.0；此次用户明确授权恢复四项修复，不抹去该报告的暂停历史。真实资格采用与B1仍暂停。

**执行者自述：** 旧执行报告和新交付中的“我”“我们”“建议”“申请”都指执行agent，不代表用户意见或新增授权。引用“主控要求”必须给实际文档/条款，不能自己补写。

最终聊天及报告顶部必须原样包含：

```text
【来源：执行agent交付，用户仅转交】
以下完成声明与建议均由执行agent撰写，尚待主控独立核验。
不代表用户意见、主控认可或新增授权。
请主控分别记录：执行者声明 / 主控验证 / 待用户决定。
```

## Global Constraints

- 目录 `/Users/yongbiaoli/Desktop/lei-signal-lab`，分支 `codex/factor-unit-research-20260915`，核对时HEAD应为 `8ba16576b75e605aa1b0d0902568c760c4b99095`。开工核pwd/branch/HEAD/status；有差异先判断归属，不回滚。
- 大量成果未提交，不从main重建、不建新worktree，不切分支、不暂存/提交/stash/reset/clean。
- 先读根及相关AGENTS、研究原则v1.1、定义标准v1.1.0、执行合同v1.0.1、报告模板v1.1.0；唯一登记表`docs/research/definitions.v1.json`容器1.2.0只读。绑定实际版本与哈希，不补造新版登记对象。
- 策略溯源仍为`docs/trading-spec-v1.md`、规则v1与实际v2、MACD技能及板块方案；本轮只服务道路层的双均线状态研究，不改交易条件。
- 对象固定 `candidate:lei.dual_ma.bull_state@draft-1`，读原候选卡；20/1/22、稀疏步长23不变。保留close_state源码SHA `b0efb324a2ef65d1f415c19be4f50b96ebf25f140da0c31b2b759d68ef04db10`。
- 零联网、零安装、零新资料、零真实因子/未来收益/账户计算、零生产/UI/OKR改动。不得启动b1-request-v2的8请求建议。

## 1. 文件范围

可修改：

- `src/lei_signal/research/factor_unit/study_contract.py`
- `src/lei_signal/research/factor_unit/state_description.py`
- `scripts/check_factor_unit_readiness.py`
- `tests/unit/test_factor_unit_study_contract.py`
- `tests/unit/test_factor_unit_state_description.py`
- `tests/unit/test_factor_unit_b0_controller_cases.py`
- `tests/integration/test_factor_unit_readiness_cli.py`
- `docs/research/factor-unit-usage.md`

新增：`tests/unit/test_factor_unit_four_fixes.py`；`docs/experiments/factor-unit-four-fixes-2026-09-15.md`；`docs/experiments/raw/factor-unit-four-fixes-2026-09-15/`。

仅导航可改：registry新增本报告并给被审报告加纠正结论，INDEX补一行；上轮执行报告顶部加指针。所有旧raw/合同/包/主控反例原件只读，close_state及其测试、factor_lab、生产函数、规则、旧日历模块、对象登记表冻结。

开工保存本轮可修改文件原字节、原raw清单及保护哈希；主控已确认的123旧raw加上上一轮新raw均纳入保护。新输出排他创建。

## 2. 验证流程与预算

- 先读主控 `docs/experiments/raw/factor-unit-b0-fix-controller-review-2026-09-15/reproduce.py` 与results.json；原脚本不改。在本轮目录新增对应pytest，修前应失败，修后应通过；新版夹具必须先有合法正对照，不用格式提前报错充当底层缺陷已修复。
- 单元测试按需；全相关回归最多2次。正式合成正/负各1次；如已定位工程错误可纠错1批。真实资格检查本轮**0次**，不为补证据包重跑真实入口。
- 补归档可从原合同与原件只读生成新补件，不运行真实计算/资格。所有CLI调试（含/tmp、目录已存在拒绝）逐次记账；失败也算调用。
- 预算不足或出现四项外新问题：记录、停受影响分支，不能自批重试或扩建。

## Task 1：禁止自填证据升级真实含分红资格

文件：study_contract.py、合同测试、新四项测试。

保持`validate_study_contract(contract)`入口，不另建供应商平台。

- [ ] 复现主控两个反例：真实510300身份不变，仅同步改合同/证据/CSV为snapshot_provenance_bound或price_basis_verified，并给不存在的vendor_response_ref；两者不得得到真实目标资格齐备。
- [ ] 区分“能追到供应商调整价的生成过程”与“已核含分红财富构造”。前者不能满足total_return_wealth，移除当前把snapshot_provenance_bound直接列为含分红目标合格的分支。
- [ ] 被消费的供应商引用必须结构化path/sha256且存在、指纹一致；记录必须绑定同产品、输入哈希、请求参数和价格语义。空字符串、假路径、错产品/输入、冲突重复记录全部拒绝；不能只检查vendor_traceable布尔。
- [ ] 文件相符只证明完整性，不证明自写事实真实。**本轮真实目标没有经过主控确认的资料，保持restricted/target=blocked，并注明manual_target_review_required。** 不为造正例伪造市场核验。合法合成目标仍可通过以验证代码，不是把所有用途一律拒绝。
- [ ] 若声明真实来源已绑定但尚未核财富构造，可展示“来源检查完成/目标仍未批准”，不得称“含分红目标资格齐备”。本轮不实现自行批准真实目标的新开关，未来由明确冻结资料与目标的主控任务另行启用。
- [ ] 真实CSV每symbol唯一，使用完整SHA精确相等，不用sha256_16前缀；重复冲突不得选首条/末条。模式、档位、输入身份必须一致。仅校验本任务必需字段，不全面重做登记库。

独立期望：无供应商原件的真实正向资格数=0；具有完整合成证据的合成正例数>0；目标为含分红财富不能仅凭供应商调整价声明通过。

## Task 2：稀疏结果也遵守同一合法集合

文件：state_description.py、描述测试、新四项测试。

- [ ] 复现50日合成递增I、截止2019/资料2020：目前comparison.n=0而true_slots_up=2。修后两者都为0。
- [ ] 稀疏格点从合同锚点每23格取，不动态选锚。每格使用主比较相同的“状态已知/主目标合法/成熟/在评价期内”判定，不能另写一套放宽条件。
- [ ] 不合格格仍可保留日期与skipped_reason，但main/aux置null、skipped=true，不展示成已可观察结果，不计true_slots_up/false_slots_down。辅助路径不全但主目标合法时，主值可以保留，aux缺失与aux_n独立表达。
- [ ] 合成覆盖截止前、标签正好收盘、之后；未知状态、缺格、路径缺失各有原因。0/负/1/24步长继续拒绝，锚点继续固定。
- [ ] 正向对照：同一50日夹具截止2030，有效稀疏格为第0/23日，两个上涨计数均保留；第46日目标不足跳过。不能靠取消稀疏输出蒙混通过。

```python
def test_sparse_cannot_see_future(synthetic_50_day_fixture):
    values, schedule, contract = synthetic_50_day_fixture
    contract['research_cutoff'] = '2019-01-01T15:00:00+08:00'
    row = describe_states(values, schedule, contract)['symbols']['SYN']
    assert row['comparison']['n'] == 0
    assert row['sparse_view']['true_slots_up'] == 0
    assert all(s['skipped'] and s['main'] is None and s['aux'] is None
               for s in row['sparse_view']['slots'])
```

夹具定义固定：2020-01-01起50个合成日、15:00+08收盘、state全true、I=100..149，评价期全50日，锚点第一日。它不是实际交易所日历。

## Task 3：支持上游pd.NA，不放宽非法状态

文件：state_description.py、对应测试、新四项测试；不得改close_state。

- [ ] 接受上游可空布尔中的pd.NA及显式None/NaN作为未知；只接受bool/np.bool_为有效状态。字符串false、字符串空、数字0/1/2不自动转布尔。
- [ ] 在数值/布尔转换前识别标量缺失；不能对pd.NA直接做真假判断。内部统一未知表示，不改变已知状态含义。
- [ ] 用现有compute_close_state生成50行真实接口格式：close=`[100]*20 + list(range(101,131))`；原样把可空state列交describe_states，不人工换None，不复制公式。
- [ ] 合成共同样本期望：第0—19行未知，第20—27行状态true且21间隔标签完整，共comparison.n=8；余行标签不足。I独立取正的合成尺度，截止2030。真假对账/unknown=20均需成立。
- [ ] 另测全pd.NA、混合bool/NA、字符串false与数字2拒绝。独立期望写成上述手算常数，不能import被测函数生成期望。

## Task 4：补全价格证据依赖，不重跑真实资格

文件：CLI、集成测试；新raw内补件生成脚本与原件映射表。

- [ ] 新合成包将合同直接引用的每份price_basis_evidence原字节纳入归档，若消费其vendor_response_ref，同样记录并保存所需原件。缺失/错哈希拒绝，不能默默漏包。
- [ ] 预先从合同和实际消费清单推导“应包含的依赖集合”，与实际归档集合双向核对。不能先把已写文件全列出来，就声称完整依赖核验通过。相对路径避免同名碰撞。
- [ ] 旧真实终包保持原样。另建supplement目录：复制其原合同、缺少的real-evidence.json、原包manifest及对应SHA，标明“为旧运行补齐证据，不代表新代码重新执行过”。核对证据文件与旧合同引用哈希一致；否则报不可恢复，不改旧合同。
- [ ] 原价格输入如不随包复制，列出明确外部输入依赖路径/哈希；恢复说明必须说是“代码/证据包+声明的外部输入”，不能称无任何外部依赖的一包复放。
- [ ] 新合成正式正包保存定稿代码/合同/全部消费证据；manifest分清package_completed、qualification_status、exit_code。严格JSON、最后写manifest、排他目录和写盘故障测试继续通过。
- [ ] 补件恢复演练在临时目录进行，只核文件身份/映射，不覆盖仓库，不调用真实运行入口。

## Task 5：交付与停止

- [ ] 运行并记录实际结果，不追87这个旧计数：

```bash
python3 -m pytest tests/unit/test_factor_unit_close_state.py tests/unit/test_factor_unit_study_contract.py tests/unit/test_factor_unit_state_description.py tests/unit/test_factor_unit_b0_controller_cases.py tests/unit/test_factor_unit_four_fixes.py tests/integration/test_factor_unit_readiness_cli.py tests/unit/test_experiment_reports.py -q
python3 -m ruff check src/lei_signal/research/factor_unit scripts/check_factor_unit_readiness.py tests/unit/test_factor_unit_study_contract.py tests/unit/test_factor_unit_state_description.py tests/unit/test_factor_unit_b0_controller_cases.py tests/unit/test_factor_unit_four_fixes.py tests/integration/test_factor_unit_readiness_cli.py
```

- [ ] 逐项对照四个原反例、新正例、测试日志、代码原字节与冻结协议；保护哈希复算。失败、修前/修后及未运行分开。
- [ ] 报告按模板含来源标识、中文一句话结论、决策卡；category=方法论与验证/verdict=mixed。研究接口修复不是因子有效；真实目标仍未批准。不要把主控的后续独立验收预写成“通过”。
- [ ] 最终只回答：四项是否关闭？合法合成链路是否实际走通？真实资格为何仍受限？旧包补件可恢复到哪一级？本轮调用/预算用了多少？

完成即停交主控，不自动进入资料抓取或B1。四项外问题登记待决定；本轮用户授权不是无限返修许可。
