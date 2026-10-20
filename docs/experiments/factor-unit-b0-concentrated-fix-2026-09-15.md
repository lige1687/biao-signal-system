# 双均线B0集中修复：R1–R4反例关闭-2026-09-15

> **后续指针（2026-09-15）：** 主控限定裁决（[factor-unit-b0-fix-controller-review-2026-09-15.md](factor-unit-b0-fix-controller-review-2026-09-15.md)）指出本文交付仍存四项问题（自填证据升级、稀疏截止失效、pd.NA接入断点、证据未随包）；该四项的限定修复交付见 [factor-unit-four-fixes-2026-09-15.md](factor-unit-four-fixes-2026-09-15.md)（执行者声明，待主控独立核验）。本文结论以那两份文件为准。

规范版本：`experiment-backtest-principles.md` v1.1 / `definition-standard.md` 1.1.0 /
`ai-execution-contract.md` 1.0.1 / `experiment-report-template.md` 1.1.0。
任务书：`docs/superpowers/plans/2026-09-15-factor-unit-b0-concentrated-fix-glm.md` v1.0.0；
主控依据：[factor-unit-b0-controller-review-2026-09-15.md](factor-unit-b0-controller-review-2026-09-15.md) v1.0.0。
执行目录 `/Users/yongbiaoli/Desktop/lei-signal-lab`；分支 `codex/factor-unit-research-20260915`；
HEAD 全程 `8ba16576`（未移动、未提交）。执行模型：GLM（`builtin:bigmodel-coding-plan/GLM-5.3-Flash`）。
被审对象：[B0执行报告](factor-unit-close-adapter-2026-09-15.md)（已加纠正指针）。

定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：
explicit（对象与公式不变）/ 四输入仍为 producer_candidate_only（如实）/ 本轮 87 项测试 +
独立反例先行 / **无（零真实因子—目标统计）** / **not_authorized**。

## 一句话结论（大白话）

上一轮主控挑的四个口子都堵上了：**资格检查不再"填上就算"**——证据必须是真实文件、
逐产品对得上哈希和档位，日历要逐天核对（本地 A 股日历实际只覆盖 2019-09 起），
必需代码清单被砍会直接被拒；**统计真正 obey 截止时间**——标签收盘晚于研究截止就不算
成熟样本，主比较只用"状态已知+目标合法+已成熟"的同一批样本并对账；**冻结包**
存了运行合同原件和全部依赖代码；**上一轮"5跌3无"的除息日推理已撤回**（那个推理
在数学上不成立），159915 那笔张冠李戴的比对已作废。四份价格数据仍然没有一份能
证明自己的复权口径，所以真实研究依然不能开算；下一轮只申请 510300 一只、
2019-10-08 起的小试。

## 1. R1：来源、日历与代码身份闭合

| 主控反例 | 修复后行为 |
|---|---|
| 价格证据指向不存在的文件 | ValueError（引用必须 {path,sha256} 且文件存在哈希匹配） |
| 候选卡 Markdown 当日历、删哈希、假称1990覆盖 | 日历内容级核验：真实日历走 TradingCalendar 逐日检查；合成日历须逐日 session/close_at 且日期对应；删哈希拒绝；评价窗1995 → 给出首个缺失日 1994-12-07 |
| available_at=`garbageT`+假来源+PIT=true | 真实解析时刻（无时区拒绝）；真实身份的 point_in_time_verified=true 一律拒绝（本B0不实现逐行真实历史资格） |
| CLI 必需代码键只剩 `__init__.py` | `REQUIRED_CODE_KEYS`（11键：新模块+CLI+均线/颜色/双均线/配置加载器/规则v2/交易日历）为模块常量不可裁剪；缺失/错哈希 → 退出3 |
| 证据与输入/来源表矛盾 | 逐产品解析证据记录与 CSV 行：symbol/input_sha256/档位/data_mode 逐项对照；矛盾拒绝 |
| 合成证据用于真实身份 | 证据 data_mode 与合同 data_mode 必须一致；真实verified缺可回查供应商材料 → 降级 producer_candidate_only 继续 restricted，不编造 |
| 合法对照 | 合成身份全合格 → status=ok、全部 pending_controller_freeze（非一律拒绝） |

真实日历事实入档：`calendar-merged/calendar.json` 实际 **2019-09-01—2026-06-30，
2495 天，82 个月，深交所来源**；用 TradingCalendar 逐日核验，声明范围不替代实际 days。

## 2. R2：统计消费完整合同

- 合同必填无默认：`object_ref / data_mode / 20 / 1 / 22 / evaluation_window /
  research_cutoff（带时区）/ sparse_anchor_session（每产品）/ sparse_step=23`
  （0/负/1/24 均拒绝）；
- 主控30日例复核：截止2019 → 成熟主比较 n=0（修复前 n=8）；截止=标签收盘当日
  盘前/正好/盘后 → 未成熟/成熟/成熟边界逐一测试；状态已知∧目标合法∧成熟的
  **共同集合**对账（n_true+n_false=comparison.n）；全资产背景单列 background
  （含未知状态，不混称）；辅助路径缺失独立 aux_n；
- 输入严校：字符串"false"与数字2拒绝（修复前30行全计true）；(symbol,session) 唯一；
  I 只接受正有限或显式缺失；close_at 逐日带时区且日期与 session 对应；
- 全部日期窗外/空输入 → 结构化零计数（修复前 KeyError）；连续状态段按完整日程序列，
  缺整行即断开；稀疏锚点来自合同（不按首个已知状态动态改选），未知/缺格跳过不顺延；
- 成熟判定改用**标签结束格点的逐日 close_at**（半日市13:00收盘场景已测）。

## 3. R3：冻结包闭合

- 运行合同**原字节**随包（contract.source.json），contract_sha256 反查一致；
- 必需代码键在生成任何结果前逐项核哈希；包内含生产函数/颜色/双均线/配置加载器/
  规则v2/交易日历原字节（不再只有新模块）；
- `file_hashes` 用包内相对路径并与实际集合双向核对（本轮正例包 23 文件零差）；
- manifest 区分 `package_completed`（打包完成）/ `qualification_status`
  （ok/restricted）/ `exit_code`；restricted 包可打包完成但不打印"资料齐备"；
- 新合同排他创建：输出目录已存在、JSON错误、缺源文件 → 明确退出码；
  数据被篡改恢复为**身份错误退出3**（纠正B0修复轮把它改称资料不足的做法）。

## 4. R4：撤回过度判断，收窄资料申请

- **撤回**"8除息日5跌3无=非干净名义价"：不复权序列的除息日相邻变化=分红+当日行情，
  市场上涨可抵消除息（手算反例：昨日100、分红2、今日100 → 含现金 +2%）。原始数值
  保留但只作观察；
- **作废** v1 boundary-checks 的 159915 "1651日冻结对比"——实际比的是 510300.SS
  快照（v1 脚本循环内只加载了 510300 快照文件），已验明并记录，不隐藏；
- 日历覆盖修正为实际 2019-09-01—2026-06-30；撤回"A股只差一个条件"与 2012 起点
  建议；mtime 语义纠正（非可靠抓取时刻）；skip 归属纠正（是本轮 close_state 分红例）；
- **新资料申请（b1-request-v2.md）**：仅 510300；观察期 2019-09-02—2025-12-31
  （目标尾部 2026-02-03 在日历内，已核）；预热按固定规则取日历内第 21 个交易日
  **2019-10-08** 起评（前有 20 个已核交易日），不假造 2012 完整日历、不加任意缓冲；
  申请一份独立带声明快照，"供应商调整价格变化"与"含分红财富"证据需求分列；
  联网预算建议 ≤8 请求——**本轮未执行、未授权**。

## 5. 测试、预算与终包

- 反例先行：`test_factor_unit_b0_controller_cases.py` 41 项（R1–R4 全部主控反例+
  合法对照）修前 19 失败留档（red-before-fix.log），修后全绿；
- 本轮命令实跑（regression-run-01.log）：**87 passed, 1 skipped**
  （skip=close_state 分红消费未实现，归属已纠正）；ruff 本轮 7 文件 All checks passed；
- 预算：完整回归 1/2 次；合成正式批次 1/1（正/负各1）；真实资格检查 1/1；
  纠错批次 0；全部 /tmp 调试记录于集成测试临时目录（自动清理，无真实数据）；
- 三类终包（final-*，代码定稿后生成）：
  - 合成正例：退出0，package_completed=true，23 文件哈希双向零差，合同原字节入包；
  - 合成负例（删必需键）：退出3，无输出目录=无成功标记；
  - 真实资格：退出2 restricted——510300/159915 日历 qualified 但价格档位不足 →
    blocked；SPY/QQQ 另缺美区日历 → blocked；**包内无任何真实状态/目标值**。

## 6. 事故史（本轮）

1. 集成测试 `env` 夹具未把 `fx` 声明为参数导致拿到夹具对象而非字典（两轮报错定位）；
2. 旧版 source-decision.csv（v1）含未加引号的 ASCII 逗号，机器解析列错位——旧 raw
   只读不改，v2 来源表改用引号规范+全量哈希，验证器以 v2 为准；
3. 夹具首轮四只合成 parquet 字节完全相同，导致"证据矛盾"测试检不出差异——
   改为每只唯一价格后反例生效（这条本身就是"哈希相同则矛盾不可检"的现场教材）。

## 7. 未完成与边界

- 四载体价格档位仍是 producer_candidate_only（诚实现状）；真实价资格需要
  带可回查供应商材料的独立快照（b1-request-v2，未授权）；
- 美股逐日日历缺失；CN 日历仅覆盖 2019-09 起——159915/SPY/QQQ 本轮不申请资料；
- 逐行真实历史 available_at 未实现：真实身份的 PIT=true 仍一律拒绝；
- close_state、factor_lab v1.2.0、生产三函数、规则账本、旧 TradingCalendar、
  唯一登记表零改动；本轮发现的新问题（无）已如实记录。

## 8. 复核与复现

```sh
python3 -m pytest tests/unit/test_factor_unit_close_state.py tests/unit/test_factor_unit_study_contract.py \
  tests/unit/test_factor_unit_state_description.py tests/unit/test_factor_unit_b0_controller_cases.py \
  tests/integration/test_factor_unit_readiness_cli.py tests/unit/test_experiment_reports.py -q
python3 -m ruff check src/lei_signal/research/factor_unit scripts/check_factor_unit_readiness.py \
  tests/unit/test_factor_unit_study_contract.py tests/unit/test_factor_unit_state_description.py \
  tests/unit/test_factor_unit_b0_controller_cases.py tests/integration/test_factor_unit_readiness_cli.py
python3 docs/experiments/raw/factor-unit-b0-controller-review-2026-09-15/reproduce.py <新输出>
# 修复后对该脚本的实测：其锚定的旧版B0合同（standards 为 path@version 字符串）
# 在新校验下被直接拒绝（ValueError，见 reproduce-after-fix.log）——旧合同格式
# 已不被接受，这正是"必需规范不可裁剪"的现场证据。R1–R4 反例的实现正确性
# 以 tests/unit/test_factor_unit_b0_controller_cases.py（41项，新结构夹具）与
# 三类终包为准；reproduce.py 的"正常退出"依旧只代表诊断脚本执行完。
```

## 最小决策卡

| 必答项 | 本轮答案 |
|---|---|
| 决策与资金用途 | 关闭R1–R4，让"资格→统计→冻结包"链条可信，服务510300首个真实历史描述 |
| 基准与增量 | 主控反例逐一先红后绿；87项测试；三类终包；无新因子/参数/标的 |
| 收益解释 | 无真实收益计算；撤回不可靠的口径推断，价格档位如实为 producer_candidate_only |
| 代价与执行 | 真实资格退出2：价格档位+美区日历是真实成本；已给出最小授权路径（仅510300） |
| 证据与结论 | 全部证据落盘可复现；不宣称因子有效、不宣称资料合格 |
| 下一步与边界 | 主控审阅 b1-request-v2（仅510300、2019-10-08起评）；B1 仍未授权，本轮未联网 |

## ARCHIVE

- 结案日期：2026-09-15
- 最终结论：mixed——R1–R4 反例全部关闭（工程通过）；真实资料资格仍不足（如实）
- 生产采用：未授权；B1 未启动；OKR 未写
- 原始数据与复现入口：`docs/experiments/raw/factor-unit-b0-concentrated-fix-2026-09-15/`
- registry.json：已登记（方法论与验证 / mixed）；INDEX：已补导航
