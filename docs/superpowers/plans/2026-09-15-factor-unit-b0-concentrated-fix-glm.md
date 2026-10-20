# Factor Unit B0 集中修复 Implementation Plan

> **For agentic workers:** 使用可用的 executing-plans 按任务顺序执行；没有技能则直接依本文，不安装、不另派子agent。用户转交并要求开始后执行本轮范围，完成交主控。

**Goal:** 一次关闭B0主控R1–R4反例，保留已测通的收盘价计算，交出真实小试之前可信的资格、统计和冻结接口。

**Architecture:** 最小修改新建factor_unit模块及CLI，复用既有日历解析，不重写研究平台。状态计算/旧factor_lab/生产保持冻结；真实资料仍只读结构，不计算状态或未来表现。

**Tech Stack:** 现有Python/pandas/numpy/pytest/ruff；零联网、零安装、零新行情、零账户。

版本v1.0.0，2026-09-15；本轮不是B1运行授权。

## Global Constraints

- 原目录 `/Users/yongbiaoli/Desktop/lei-signal-lab`，原分支 `codex/factor-unit-research-20260915`；参考HEAD `8ba16576b75e605aa1b0d0902568c760c4b99095`。先核实际身份及脏工作区，保留所有他人改动，不切分支、不建新工作区、不暂存/提交/reset/clean/stash。
- 必读根/相关AGENTS、`docs/trading-spec-v1.md`、规则v1及实际v2、MACD技能与板块方案；本轮服务双均线道路状态的研究核验，不改变条件。
- 权威：研究原则v1.1、定义标准v1.1.0、执行合同v1.0.1、报告模板v1.1.0、唯一登记表`docs/research/definitions.v1.json`容器1.2.0；保存实际指纹，异常先停受影响项。
- 主控依据 `docs/experiments/factor-unit-b0-controller-review-2026-09-15.md` v1.0.0；先读反例脚本及results.json，再读原B0报告/任务书。本计划覆盖冲突条款，不修改旧证据。
- 对象保持 `candidate:lei.dual_ma.bull_state@draft-1`，仍引用原卡，不升正式登记。20/1/22固定，不加新因子/标的/参数/收益回归。
- 只许合成统计与本地真实结构资格；禁止真实状态/未来目标计算、下载、密钥、生产、UI、交易与OKR写入。

## 允许文件与预算

可修改：

- `src/lei_signal/research/factor_unit/study_contract.py`
- `src/lei_signal/research/factor_unit/state_description.py`
- `scripts/check_factor_unit_readiness.py`
- `tests/unit/test_factor_unit_study_contract.py`
- `tests/unit/test_factor_unit_state_description.py`
- `tests/integration/test_factor_unit_readiness_cli.py`
- `docs/research/factor-unit-usage.md`

可新增：`tests/unit/test_factor_unit_b0_controller_cases.py`、`docs/experiments/factor-unit-b0-concentrated-fix-2026-09-15.md`及同名raw目录。报告registry仅新增本报告/更新被审结论指针，INDEX补导航；B0报告顶部加纠正指针。所有B0旧raw、主控反例原件只读。

`close_state.py`、其测试、factor_lab v1.2.0、生产三函数、规则账本、旧TradingCalendar和唯一对象登记表冻结；本轮发现状态函数新问题只报告，不顺手改。

完整相关回归≤2次；合成正式正/负各1次，确有工程错误可纠错1批；真实资格检查≤1批，不因失败自行重试；所有CLI调试含/tmp均记录。单元测试按需，不能跑步长0的已知可能无限循环入口来制造挂起。

## Task 0：冻结基线与可恢复失败证据

- [ ] 保存允许修改文件开工原字节、实际分支/HEAD、原B0所有raw SHA和42项保护；新输出目录排他创建。
- [ ] 原样复跑主控reproduce.py到本轮新输出，保存当前反例；其正常退出只是“诊断脚本执行完”，不能算实现通过。
- [ ] 将下列反例写成应拒绝/应正确返回的pytest，修前失败留档，再改实现。新夹具不依赖个人真实缓存，不用mock把资格检查强行放行。

## Task 1：R1 真实消费证据与日历

文件：study_contract.py、合同测试、新控制器反例测试。

保持入口 `validate_study_contract(contract: dict) -> dict`，结构/身份错误ValueError，资料不足restricted，逐产品原因明确；不赋予自动运行权限。

- [ ] 价格证据改为结构化引用 `{path, sha256}`，必须存在且内容哈希匹配；解析记录中的symbol/input_sha256/price_basis/data_mode/来源字段，与输入逐项一致。不能仅验证字符串、不能信verified=true；来源裁定CSV同样逐产品/输入哈希对照。证据矛盾则拒绝或降级，不取有利者。
- [ ] 明确证据真实程度：合成来源记录只能证明算法；自造JSON与自己的哈希不能证明市场事实。真实价资格必须绑定可回查的供应商响应/生成参数/已核方法记录；本轮缺材料继续restricted，不编造材料以做正例。
- [ ] 日期/时刻使用真实解析，不用包含T/后缀判断。available_at未知保持null；本B0不实现逐行真实历史资格，故不接受真实`point_in_time_verified=true`。合成时刻可验证解析，但仍输出synthetic，不授予真实资格。
- [ ] 候选卡缺失/错哈希拒绝。必需规范集合、准确版本、指纹不可裁剪为一条带@的字符串。
- [ ] 用只读`TradingCalendar.from_file`和`coverage(start,end)`核CN内容；实际日期完整性由days计算，声明范围不能替代。评价窗+预热使用的日期+目标尾部逐日有定义；缺一天、非法日期、错市场、区间越界均可定位。不得把所有价格数据首日强制当评价首日。
- [ ] US真实日历没有材料继续受限，不能拿Markdown或“普通13点半日收盘声明”冒充逐日日历。合成日历须有逐日session/close_at，时区、交易所、日期与收盘对应；不强行混用CN解析器。
- [ ] 所有文件哈希为必填且在消费前核。数据被篡改属身份错误退出3，恢复B0原任务书合同，不沿用执行者把它改称资料不足退出2的做法。
- [ ] 每产品target只有价格、日历、身份、来源都合格才能pending_controller_freeze；任一阻断不可仍显示目标已齐备。至少有合成合法正例，不允许一律拒绝。

红测例：不存在证据、错产品/输入哈希、来源表与合同矛盾、Markdown当日历、删哈希、伪造1990覆盖、缺一个日期、available_at=`garbageT`、缺卡、规范删至1条、合成证据用于真实身份。

## Task 2：R2 统计真正使用同一个合同和样本集合

文件：state_description.py及对应两份测试。保持 `describe_states(values, schedule, contract)`。

- [ ] 显式必填object_ref/data_mode/20/1/22、评价起止、带时区research_cutoff、每产品预定sparse_anchor_session；禁止用默认参数掩盖漏声明。步长固定23，0/负/1均立即拒绝。
- [ ] 数据键(symbol,session)唯一；state只能真正bool/空，字符串false和数字2拒绝；I只接受正有限或显式缺失；无日期/无时区/时刻与session不匹配拒绝。不能通过填data_mode字符串把真实输入身份转换为合成；合成夹具身份在调用/冻结层绑定，纯内存函数不声称能自动识别数据出处。
- [ ] 标签结束收盘晚于research_cutoff，不计入成熟样本；同日收盘前/正好收盘/收盘后分别测。观察也必须落评价期内且不晚于截止。时区转换使用逐日close_at，夏令时和半日市分别测。
- [ ] 主比较共同集合=状态已知且主目标合法成熟的行；n_true+n_false=n_comparison。额外全资产背景可单列，但不能冒称同一集合；辅助路径缺失独立aux_n，不让主n替代路径n。
- [ ] 预热未知保留；无目标、全未知、空输入、全部日期落日历外必须明确返回零计数/原因或预检查ValueError，不允许KeyError。不得静默丢失日历外行。
- [ ] 连续状态段按完整应有日历序列，缺整日或unknown均断开，不跨缺价连接。稀疏锚点来自合同，不根据第一个已知状态/未来收益改选；未知或缺格跳过该格不顺延。
- [ ] 主目标仍e=t+1、x=t+22；辅助下行含起点0，缺路径不伪造。标准JSON不含NaN/Infinity，逐项计数与原因对账。

独立手算最小例：30日I恒100，前5行未知，余行true；截止覆盖全部日期时合法主比较n=3、真3、假0，额外背景n=8可单列；截止在2019年而资料全2020年时成熟主比较n=0。将state全设字符串false必须报错，不许变成30个true。

```python
def test_string_false_is_not_boolean(valid_fixture):
    values, schedule, contract = valid_fixture
    values['state'] = 'false'
    with pytest.raises(ValueError):
        describe_states(values, schedule, contract)
```

逐年/未知/缺失/辅助样本与稀疏样本分列；仍只描述合成关系，不加显著性、回归、策略收益。

## Task 3：R3 必需身份不能裁剪，冻结包闭合

文件：CLI、study_contract.py、集成测试。

- [ ] 固定必需代码键至少含4个factor_unit文件、CLI、seeded_ema所在文件、颜色/双均线所在文件、规则配置加载器、实际规则v2；若调用TradingCalendar加其文件。枚举直接依赖后冻结，不能由待核合同自己缩小集合。
- [ ] 在生成资格或冻结结果前核每个必需键及哈希；仅剩`__init__.py`、漏CLI、漏生产函数、错任一哈希均退出3。保留合法对照。
- [ ] 最终运行合同原字节随包保存，不把增加_repo_root的运行内存对象冒充原件；反查contract_sha256。保留源码原字节、候选卡、实际采用规范、环境版本、两个市场各自被引用证据；漏任一依赖不能称完整恢复包。
- [ ] file_hashes用包内相对路径，不只文件名；所有条目与实际集合双向核对，不能漏文件。manifest最后写，字段区分package_completed、qualification_status、exit_code；restricted也可打包完成，不能打印资料齐备。
- [ ] 新合同有独立新版本、排他创建，旧current或旧合同不能覆盖。JSON格式错误、缺源文件、输出已存在返回明确退出码，无未捕获FileNotFoundError。
- [ ] 合成CLI实际覆盖坏来源/假日历/删必需键/输入篡改/目录存在/写盘故障，失败包不含成功标记。新正例从真实校验路径通过，不patch检查函数。

## Task 4：R4 撤回过度判断，收窄下次资料申请

文件：新报告、新raw内source-decision-v2.csv/b1-request-v2.md，旧报告顶部指针及手册。旧CSV/JSON不改。

- [ ] 撤回“8次除息日5跌3不跌证明混杂/非名义价”，用100→100加分红2的手算反例解释为何不能判断；保留原始数值和它们能证明的有限范围。
- [ ] 查明159915的1651日对比到底引用何产品；无相同产品来源证据则明确作废此项比对，不能仅从正文隐藏。局部结构/身份核实不运行真实因子统计。
- [ ] 修正日历覆盖至真实days区间，撤回A股只差一个条件和不准确起点；修正skip归属和mtime语义。
- [ ] 新的资料请求只优先510300，候选观察期2019-09-02至2025-12-31，现有日历覆盖目标尾部。列出真实可用预热范围，不假造2012完整日历。若预热不足，按固定规则选择首个可准备日并在看结果前冻结，不加任意缓冲。
- [ ] 申请下一阶段一份独立带声明快照，分别提出“供应商调整价格变化”与“含分红财富”证据需要；不宣称一次重抓天然解决总回报。联网预算建议≤8请求含失败、仅510300、明确源与参数、不自动回退、不覆盖缓存；**此处只是请求，本轮不执行**。

## Task 5：终版验收与停止

- [ ] 独立期望脚本不import被测统计函数；每个R项反例先败后过、正例非空有效。只用小步apply_patch，不再写批量文本换行器；若重写文件，重新核所有功能与期望，不能只凭语法检查说等价。
- [ ] 执行并保存实际日志，不追既有193计数：

```bash
python3 -m pytest tests/unit/test_factor_unit_close_state.py tests/unit/test_factor_unit_study_contract.py tests/unit/test_factor_unit_state_description.py tests/unit/test_factor_unit_b0_controller_cases.py tests/integration/test_factor_unit_readiness_cli.py tests/unit/test_experiment_reports.py -q
python3 -m ruff check src/lei_signal/research/factor_unit scripts/check_factor_unit_readiness.py tests/unit/test_factor_unit_study_contract.py tests/unit/test_factor_unit_state_description.py tests/unit/test_factor_unit_b0_controller_cases.py tests/integration/test_factor_unit_readiness_cli.py
```

- [ ] 三类最终包（合成正、合成负、真实资格）在代码定稿后生成，真实仍不得含任何状态/目标值。需重跑即计预算；不得把调试称只读而不记账。
- [ ] 报告category=方法论与验证/verdict=mixed；逐项说明通过、失败、未运行、数据仍缺、授权仍无，保留事故史，交回主控。
- [ ] 全部旧raw、close_state、factor_lab和生产保护核对；本轮新包可按原路径恢复并比对完整必需文件/合同，不覆盖仓库来演练。

完成即停，不联网、不启动B1、不写OKR。若仍有实质缺陷，主控裁剪或暂停不可信消费者，不自动开启又一轮扩建。下一步目标始终是让一个明确因子得到可信的首份真实历史描述，不是不断增加测试数量。
