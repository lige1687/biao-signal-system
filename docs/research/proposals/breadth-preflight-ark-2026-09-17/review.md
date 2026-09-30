# 宽度开跑前独立核验报告（S1）

实际执行者：**ZCode GLM-5.3-Flash/high**（不是 Ark；目录沿用旧计划命名
`breadth-preflight-ark-2026-09-17`，产物与 Ark 无关）。实际日期 2026-09-18。
job `a45965db-162c-4ab6-bbba-e836318d9ee8`，stage=S1；本文件为
**execution=2（attempt=repair）修订版**：按主控复核
`docs/experiments/breadth-preflight-controller-review-2026-09-18.md` 补齐 R1/R2
证据并收窄结论（R3）。execution=1 时点的本报告原字节已封存于
`checks/archive-pre-repair-2026-09-18/`（含 SHA-256）。分支
`codex/factor-unit-research-20260915`，HEAD
`7f8c38c36981b2d176381181bc6a8bb901df618c`（开工与收工均核对一致，无漂移）。

## 一句话结论（大白话）

我们要在批准任何重跑之前，独立检查那套"宽度高低与 510300 之后 21 个交易日
涨跌关系"的计算工具是否可靠。结论：**在被测的 48 项合成检查覆盖范围内
（纯函数 28 项＋协议身份 14 项＋核验器 6 项），配对、数学、拒绝错误数据的
路径、协议身份校验和独立核验器都与合同一致；已确认的阻断缺陷是已知的文件
路径写错一行（`run_breadth.py:32`）。这不等于"实现只有这一个缺陷"——低危
口径问题（F2）与三项观察（F3–F5）仍未由主控裁定，缺陷清单在这些裁定前不
闭合。修 F1 并按规矩重新冻结版本，才谈得上申请一次补救运行；本报告不批准
运行，也不下任何投资结论。**

术语说明：「宽度」指沪深300 成员中站在自己 200 日均线上方的合格股票比例；
「名次相关」指两列数字各自按大小排名后看排名是否同向（+1 完全同向、-1 完全
反向）。**名次相关为 0 只说明"看不出单调同向/反向的排名关系"，不是一般意义
的"没有关系"**——本合同本来就不检验非单调关系。本文的统计都是对这份历史
快照的描述，不是预测。

## 1. G1 身份与现场（全部闭合）

证据见 `source-manifest.json`（全部 SHA-256 逐字节计算于 2026-09-18）：

- 四份真实输入（宽度 parquet、观察表、价格表、日历）哈希与合同白名单
  （`breadth_description_contract.py:98-123` 钉定值）**逐一命中**；
- 五份研究规范哈希与合同钉定值（`breadth_description_contract.py:125-146`）
  **逐一命中**，即冻结以来规范零漂移；
- 冻结副本 `freeze/v1.0.0/code/` 7 个代码文件与当前 `src/`、`raw/` 对应文件
  **逐字节相同**——run-01 失败后没有人悄悄改过被审代码；
- `run-01/` 现场只有 `rejection.json`（内容为 `docs/docs/experiments/...`
  找不到文件的报错），无任何统计产物——"旧 run 仅拒绝产物"成立；
- 冻结协议 `freeze/v1.0.0/protocol-v1.0.0.json` 的身份常量（家族/用途/标的/
  日期窗/端点偏移/统计口径/质量标签/容差/四输入/8 个代码键）与合同模块常量
  逐项一致（人工比对；运行时由 `validate_protocol` 代码再机械强制）。

## 2. G2 合同逐条对照（文件行号）

合同 = `docs/archive/handoffs-plans/2026-09-17-breadth-first-description-execution.md`
§唯一评价合同/§固定统计（下称"计划"）。被审 = `src/lei_signal/research/
breadth_description.py`（下称 bd）、`breadth_description_contract.py`（下称
contract）、`raw/.../run_breadth.py`（下称 CLI）。

| 合同条款 | 实现位置 | 对照结果 |
|---|---|---|
| 观察轴先按完整日历推导，再左连接宽度和目标 | bd:217（轴=窗口内全部 session）、bd:225-272（逐日查行） | 一致；缺行保留轴位并给原因（checks 23/24 验证） |
| 端点 t+1 / t+22 交易日 | bd:45、bd:219-221 | 一致（checks 7 断言 e=s[1]、x=s[22]） |
| 标签成熟：x 日 15:00+08 ≤ 截止 | bd:161-163、bd:222 | 一致（checks 19：早截止→label_not_mature，不造目标值） |
| main 应等于 close(x)/close(e)-1，偏差 >1e-12 整体拒绝 | bd:255-268（RATIO_TOLERANCE） | 一致（checks 21：+1e-9 拒绝、+5e-13 通过且保留原值） |
| 输入身份/必需键缺失硬拒绝 | bd:58-61、bd:110 | 一致（checks 11） |
| 重复键（宽度/观察日期）硬拒绝 | bd:90-94 | 一致（checks 12） |
| 每行 valid 须真布尔，禁止非空字符串判真 | bd:117-118 | 一致（checks 13） |
| 计数非整数 / 0≤eligible≤quoted≤pool_total 违反硬拒绝 | bd:97-105、bd:112-116 | 一致（checks 26） |
| 价格非正/非有限硬拒绝 | bd:142-147 | 一致（checks 22） |
| 有效 b200 越界 [0,100] 硬拒绝；非有限拒绝；NaN 不拒绝 | bd:133-139 | 一致（checks 27、17） |
| coverage 越界 [0,1] 硬拒绝；有效行 coverage 与 eligible/pool 在 1e-12 内一致 | bd:119-121、bd:129-132 | 一致；一致性检查仅对 valid 且 pool>0 行（与合同"有效行须有"一致） |
| coverage=0.90 边界有效（不足则 breadth_invalid 排除） | bd:235-237（`< 0.9 - 1e-12` 判invalid） | 一致（checks 16：270/300 纳入、269/300 排除；与 common 卡 quality_gate"等于0.90有效"吻合） |
| 质量不足/缺失按日期保留六类原因，primary 先宽度后目标互斥 | bd:29-36、bd:274-277 | 一致（checks 18：同日双原因 primary=breadth_invalid，全部原因保留在 exclusion_reasons） |
| 无值不填 0、不前填、不顺延 | bd:228-242（缺失留 None/NaN，不改数） | 一致 |
| 过滤不依赖 B1 state/flag_*/in_comparison 等旧字段 | bd:55（_OBS_COLUMNS 仅 4 列）、bd:150-158 | 一致（checks 14：增删改这些列，配对逐列不变） |
| 主指标=并列平均名次名次相关，复用 rank_diagnostic 仅改名 | bd:294-305 → momentum_prototype.py:118-139 | 一致（平均名次、n<3→fewer_than_three_pairs、常数→constant_rank） |
| 全期+2019…2025 逐年，按观察日年份、年内重排名 | bd:343-361（session 前 4 位切年） | 一致（checks 6：2020 rho=1、2021 rho=-1、拼接全期手算 rho=0） |
| 重叠：合法行 (e,x] 21 段相邻区间、按原日历位置、相邻共享 20 段 | bd:364-399 | 一致（checks 9/10：8 行→引用 168、唯一 28、直方图 {20:7}；剔除中间行后区间不压缩，直方图 {20:5, 19:1}——手算一致） |
| 输出协议身份常量逐项相等 + 代码键集双向核对 | contract:208-288（常量相等）；contract:350-364（实际闭包⊆声明且声明文件逐一哈希） | 一致（代码走查；篡改拒绝由既有 47 项测试覆盖，本轮未复跑） |
| 输出目录排他创建、manifest 最后写、拒绝留 rejection.json | contract:367-372、CLI:212-217/296-319、CLI:53-55 | 一致（代码走查；写盘失败注入由既有测试覆盖） |
| 退出码 0/2/3 语义 | CLI:212-270/315-321 | 一致；一处口径观察见 F4 |

## 3. 合成反例结果（checks/，48 项全过）

三个独立检查文件（均本轮新写、位于交付目录内），期望值手算固定、注释给推导，
不读真实输入、不跑 CLI：

- `test_independent_checks.py`（execution=1，原样保留）：28 项，一次通过
  （1/4 命令）。覆盖：三个手算相关值（1、-1、√3/2）、常数/不足 3 对的
  null+原因、跨年重排名（2020 同向 1、2021 反向 -1、拼接全期手算 0）、目标
  0.1 与比例缩放不变、25→0.25 一次转换、0/100 边界、coverage 0.90 边界、
  六类排除原因与优先级、B1 旧状态无关、缺列/重复/字符串布尔/计数违例/价格
  非正非有限/端点错一天/比率超差/宽度越界的硬拒绝、重叠 21/20 段与剔除后
  不压缩轴。其中「顶层无副作用」一项是 **import 之后运行的有限 AST 静态
  检查**（只扫模块顶层语句），不能据此声称"导入前安全"或穷尽全部副作用。
- `test_protocol_identity_checks.py`（R1 返修补件）：14 项。先有合法合成
  协议正例零错误（证明校验链可用、非一律拒绝），再逐项证明删必需身份键
  （object/family/规范条目）、改对象引用（b50）、改用途（prediction）、改
  规范哈希、合成模式缺 fixtures 声明、代码键非 SHA-256、mode 不一致、
  current 指针冒充原件分别**到达预期校验分支**（断言具体错误文本，如
  "protocol object != frozen identity"、"missing or altered spec hash:…"、
  "protocol file must be a version original…"）；另以真实闭包对照合成声明，
  覆盖 `verify_code_manifest` 双向三支路（missing required code key /
  code hash mismatch+declared drifted / declared missing file）。
- `test_verifier_independent_checks.py`（R2 返修补件）：6 项。手造合成
  inputs+run（8 干净行＋22 个缺目标行；宽度 0.1→0.8 严格升、目标严格降、
  无并列 → 手算 rho=-1；重叠手算 168 引用/28 唯一/相邻 20 段），直接调用
  `verify_run`：清洁控制组通过（并证明确实到达键集核对 30=30）；删行、
  额外行、NaN、单位错、目标错五种破坏逐一被抓住（断言各自具体错误文本）。
  全程不 import 被审实现，不拿被审输出当真值。

运行记录：R1/R2 两文件合并为一条命令，首跑 15 过/5 败（失败全是检查文件
自身夹具笔误 `mkdir` 缺 `parents=True`，与被审实现无关），修夹具后重跑
20/20 全过。预算与原始日志见 `checks.log`、`checks/run-02-repair-pytest.log`、
`checks/run-03-repair-pytest.log`。

**已有工程拒绝（run-01 失败、合成 CLI 超支）不等于宽度因子无效；本轮 48 项
通过也不授予任何真实运行权限。**

## 4. 发现清单（按严重程度）

**F1（阻断真实运行，已知缺陷的独立确认）** CLI `run_breadth.py:31-32`：
`_HERE = Path(__file__).resolve()` 是**文件**路径，`_HERE.parents[3]` 落在
`docs/`（应为 `parents[4]` 才是仓库根；`make_protocol.py:18` 用目录推导
`parents[3]` 是对的，两处口径不同步）。真实分支以 `REPO_ROOT / required.path`
找冻结输入（CLI:84），拼出 `docs/docs/...` → OSError → 退出 2，与 run-01
`rejection.json` 完全吻合。合成分支走 `--input-dir` 绝对路径（CLI:94-101），
不经该常量——这正是旧合成测试没抓住它的原因（同类"只被真实分支使用的常量"
风险）。本轮仅做路径解析演示与现场比对，未运行完整 CLI（预算 0 次）。

**F2（低，需主控裁定是否算偏差）** 非交易日报价的拒绝范围不对称：
bd:195-198 对宽度行只在评价窗内拒绝非交易日；bd:200-204 对价格行**全局**拒绝
（文件中任何不在日历上的日期都拒绝）。合同硬拒绝清单写"非交易日报价"未限
窗口。影响：窗外周末日期的宽度行会被静默忽略而非拒绝。四份冻结输入哈希未
变，真实运行会命中同一数据；即使宽文件存在窗外非交易日也只影响"拒不拒绝"
的口径，不影响窗内统计。建议随 v1.0.1 一并收紧或书面接受现状。

**F3（信息）** bd:191 `pd.Timestamp(cutoff)` 若被传入无时区时间戳，bd:222
的比较会抛 TypeError；CLI 配对段的异常捕获（CLI:267）只接 DataError/ValueError，
此时会以裸 traceback 退出（非 0/2/3）。CLI 自身恒传带时区的冻结 CUTOFF，
仅库的直调方可触发；v1.0.1 可顺手把 cutoff 归一化或改抛 DataError。

**F4（信息）** 数学核 rank_diagnostic（momentum_prototype.py:128）在排名前
静默丢弃非有限值行。在宽度管线里 clean 行已被排除规则保证有限，不可达；
但若有人绕过 build_pairs 直接喂 rank_summary，n 可能小于行数而无告警。本轮
不改旧接口（约束），仅留记录。

**F5（信息，核验脚本缺口）** `verify_result.py` 独立性成立（见 §5），但：
(a) 不核对 pairs.meta.json 的 object/symbol/family 是否被调包（只查 offsets/
unit_conversion/common_calculate_called，verify:382-388）——协议身份由 CLI
的 validate_protocol 把守，核验脚本此为第二道未设的闸；(b) 布尔解析只认
"True"/"False" 首字母大写（verify:73-79），小写会保守报错（方向安全）；
(c) 截止时间/窗口为脚本内手抄冻结值（verify:24-32、112），若将来重冻结协议
必须同步更新，否则核验整体失效——v1.0.1 重冻结时的必改清单项。

## 5. 工作项4：独立核验脚本是否真的独立

`verify_result.py` 的独立性**成立**，按代码证据：

- 不 import 两个被审模块、不调用 rank_diagnostic（文件头声明 verify:5-8，
  import 仅 argparse/json/math/sys/pathlib/pandas，verify:15-21）；
- 名次相关用自写平均名次 + 标准 Pearson（verify:35-66），与被审实现零共享
  代码路径；轴/端点/成熟/排除从 calendar.json 独立推导（verify:82-155）；
- 键集双向检查（缺行/多行/重复都拒，verify:298-309）；逐行单位核对
  （fraction 必须=percent/100，verify:336-338）；summary 全期+7 年逐字段
  严格比对（整数/键集/null 理由严格相等、浮点 1e-12，verify:229-266）；
  重叠从日历位置独立重算（verify:198-220）。

能否抓住删行/多行/NaN/单位错/错目标：删行→缺行错误；多行→多余键错误；
NaN→写盘为空串→与期望 None 双 None 一致，若被改成字符串 "nan" 则浮点比对
必失败；单位错/错目标→逐行核对抓出。**R2 返修已用合成数据直接验证这一
结论**（见 §3 第三个文件）：清洁控制组通过，五种破坏逐一被抓住并断言了各自
错误文本——不再只是代码走查转引旧测试。局限：核验脚本与被审实现共享对合同
的**同一种解读**（如 coverage 边界减 1e-12），两边同错时互相发现不了——这
正是本轮"手算期望独立于两方"的合成检查存在的意义。

## 6. 已检查范围与未核项

已检查：§1 身份闭合、§2 合同逐条对照、§3 合成反例 48 项（纯函数/协议身份/
核验器三组）、§5 核验脚本独立性（走查＋本轮合成实测）、CLI 控制流与退出码
走查、预算台账与主控复审报告交叉阅读。

未核项（如实列出，不记通过）：

1. 四份真实输入的**数据内容**（只算了哈希与身份，未读任何真实行）：观察表
   是否含 x 越出日历轴的尾部行、宽度文件日期是否全为交易日、parquet 列的
   实际 dtype 等只能在真实运行时由合同自动判定；
2. 完整 CLI 端到端（真实或合成）均未运行——预算明令 0 次；
3. 既有 47 项测试与旧回归未复跑（不重复消耗历史口径）；
4. TradingCalendar/definitions/factor_runtime 等冻结旧模块的内部实现只确认
   哈希一致与顶层无副作用，未重审逻辑；
5. 输出包写盘失败路径、manifest 并发/写一半场景只做代码走查。

## 7. 最小补救规格（G3，不自我批准）

范围以主控复审 R1/R2/R3 为基（controller-review §4），本轮独立复核后维持并
细化：

- **R1（必须）** 新建 v1.0.1 版本修复路径层级：`run_breadth.py` 的
  `REPO_ROOT` 改为与 `_HERE` 为文件路径匹配的 `parents[4]`（或统一改用
  `Path(__file__).resolve().parent.parents[3]` 的目录口径，与 make_protocol
  对齐）。**不改 v1.0.0 任何原件**（协议、代码副本、run-01 原样保留）。
  因 canonical 路径与代码哈希都进协议，v1.0.1 需同步：contract 模块的
  `PROTOCOL_VERSION`/`CANONICAL_RELATIVE_PATH` 指向 freeze/v1.0.1/，重新
  计算 import 闭包并重冻结协议与代码副本；身份常量（对象/标的/窗口/统计/
  容差/质量标签）除版本与路径外**一律不变**。CLI:41 的旧 job 号
  `DELEGATED_JOB_ID` 亦应在 v1.0.1 更新为真实执行 job，避免新产物冒旧溯源。
- **R2（必须）** 新增一个只查路径解析、不碰真实数据、不跑完整 CLI 的回归
  检查：断言 run_breadth 模块的 REPO_ROOT 下存在 `src/lei_signal`（本轮
  checks 文件开头的路径护栏即现成范式），防止下次重蹈"只被真实分支执行的
  常量漏测"。
- **R3（已完成）** 预算口径更正与超支留痕已由执行者台账如实记录、主控已裁
  定流程超支，本轮无追加动作。
- F2/F3/F5 是否随 v1.0.1 顺手收紧，由主控裁定；不裁定则维持原样重冻结。

**一次真实补救运行的前置条件（建议，均需主控/用户明示批准，本报告不批）**：
R1+R2 完成且新版本冻结自检通过；身份常量与 v1.0.0 逐项相等（版本号与路径
除外）；明示授权恰好 1 次真实尝试、任何阶段失败即停；不调对象、参数、日期
窗、指标；verify_result.py 若随窗口/截止变化同步更新其手抄冻结值。

## 8. 决策卡（最小）

- **测的是什么**：现有宽度描述工具链是否值得批准补救运行（只审实现与合同，
  不出统计）。
- **结果是什么**：48 项合成检查覆盖范围内实现与合同一致；已确认缺陷 F1
  （路径一行）；F2 低危口径不对称与 F3–F5 观察仍未裁定——**缺陷清单在主控
  裁定前不闭合，本报告不再使用"唯一缺陷"表述**。
- **对你的实际意义**：修复成本是"一行路径 + 按规矩重冻结版本"；修好后是否
  真的跑那一次补救计算，由你或主控决定，本报告不批准、也不预测结果好坏。
  另提醒：名次相关为 0 只是没有看出单调的排名关系，不是"证明没关系"。

## 9. 返修记录（execution=2，2026-09-18）

- 封存：execution=1 的 review.md 与 test_independent_checks.py 原字节存于
  `checks/archive-pre-repair-2026-09-18/`（SHA 见该目录 README）。原 28 项
  通过内容未改动、未重跑。
- R1 闭合：新增 `checks/test_protocol_identity_checks.py` 14 项（合法正例＋
  删必需身份键/改对象/改用途/规范键哈希/代码键格式/mode 不一致/指针冒充
  原件反例＋代码清单双向三支路），每例断言到达的校验函数与错误文本。
- R2 闭合：新增 `checks/test_verifier_independent_checks.py` 6 项（手造
  合成 run 清洁组＋删行/额外行/NaN/单位错/目标错五破坏，直调 `verify_run`，
  期望手算固定、不依赖被审输出）。未发现核验器漏抓——无新增实质问题。
- R3 闭合：一句话结论、§3、§8 收窄为实际覆盖范围；明确 ρ=0 的含义与 AST
  检查为 import 后有限静态检查。
- 预算：新增合成检查 2/3（首跑 15 过/5 败为检查文件自身夹具笔误，修后
  20/20）；ruff 追加 1/1（失败：1 处 F401，删该导入后按预算不再复验，
  见 checks.log）；hygiene 追加 1/1 通过。被审实现、冻结协议、旧 raw、
  registry/INDEX/OKR 零改动。
