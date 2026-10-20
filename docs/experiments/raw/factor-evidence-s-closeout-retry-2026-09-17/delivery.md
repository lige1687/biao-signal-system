# S1–S3 收尾交付（factor-evidence，2026-09-17 重派）

执行 agent 声明，待主控复核，不代表用户意见或新增授权。

- 任务：仅完成因子证据可靠性工具 S1–S3 入口、解释和记录收尾（retry
  brief + 主控报告 §9.2–9.5）。旧失败 job `5c5e753f` 未写入任何文件、
  未运行测试，本任务为修好派发器后的新执行。
- 工作区 `/Users/yongbiaoli/Desktop/lei-signal-lab`；分支
  `codex/factor-unit-research-20260915`；起始与结束 HEAD 均为
  `2b05787f746991a90ec33a06736b61cfdeca6119`（未切分支/暂存/提交/reset）。
- 零真实重跑、零联网、零新依赖、零策略参数改动；registry/INDEX/OKR/
  主控报告未动。所有通过均为**合成测试**通过，不称真实结果复跑。

## 一、逐项目标状态

### G1（S1）直接调用不能自填真实身份 —— done

改动：`src/lei_signal/research/factor_evidence/runner.py`

1. 公开 `run_analysis`（runner.py:265）收窄为**仅合成**直接调用入口：
   - `mode == "real"` → 写盘前 `ValueError` 拒绝（runner.py:276-278），
     文案明确"真实身份不能自填（base_dir/sha 不是已验证合同）"；
   - `mode` 缺失或非 synthetic → 拒绝（runner.py:279-281）；
   - 未引入任何可自填 verified/token/approval 旁路。
2. 原分析落盘实现原样移入私有 `_run_analysis_write`（runner.py:286），
   `_resolve_identity` 逻辑未动，仅 docstring 注明"内部辅助函数，不是
   入口，不独立验证来源"。
3. 真实 `main` 校验链未降低：仍为 输出目录检查 → `validate_protocol`
   → `load_b1_observations` → 资料不足出口 2 → 调用
   `_run_analysis_write`（runner.py:469），并在调用处注释说明公开入口
   已收窄。

证据：

- 合成反例测试 `test_run_analysis_fake_real_identity_direct_call_rejected`
  （tests/integration/test_factor_evidence_cli.py:225）：复刻主控反例——
  数据标的改写为 510300（与协议一致）、自填
  `base_dir="does-not-exist"`/`observations_csv_sha256="fake"` 的 real
  直接调用 → 断言 `ValueError` 且输出目录不存在（写盘前拒绝）。通过。
- 合成正例保持：`test_run_analysis_synthetic_complete_manifest`（合法
  合成完整落盘、身份对账）与
  `test_run_analysis_single_group_completes_not_estimable`（单组不可
  估计仍诚实完成）原样通过；原真实模式冲突测试
  `test_run_analysis_real_mode_identity_conflict_rejected` 未改、仍通过。
- 真实 main 校验链合成测试证据：
  `test_main_returns_2_for_not_estimable_real_data`（monkeypatch 装载，
  main 走校验链后出口 2、无输出目录）与 7 条子进程负路由
  （协议缺失/草案/删规范/坏窗口/假版本文件名/输出已存在/导入不写盘，
  均 exit 3 或 0 且不写盘）在定向与回归中通过。
- 手册 `docs/research/factor-evidence-reliability-usage.md` §1 新增
  边界说明：真实入口只有 `main`；直接调用仅限显式合成；私有落盘函数
  不承诺独立验证来源。

### G2（S2）机器解释不再硬编码历史结论 —— done

改动：`runner.py`（两处模板 + 一处括注）、`stability.py`（仅稀疏 note）。
未新增任何阈值、判断分支或统计；统计值计算零改动。

| 位置 | 旧（模板断言） | 新（中性、指向实际数值） |
|---|---|---|
| `_report_md` 留一年句（runner.py:175-178） | "只说明单个年份不使差值反号" | "逐项查看各年份删除后的差值及缺失原因，差值是否随之反号以实际数值为准，不能由此排除单个年份的集中影响，也不据此称不依赖连续行情" |
| 卡片 `qualifications.effectiveness`（runner.py:383） | "无预测有效性证据；逐年方向不一致" | "无预测有效性证明；年度结果见实际输出" |
| `overlap_audit` 稀疏 note（stability.py:325-327） | "可审计格点间标签观察窗口不重叠（区间级）；不重叠不等于统计独立" | "可审计格点间共享区间以 adjacent_shared_max/adjacent_pairs 等实际计数为准；即使为 0 也不证明统计独立" |
| `_report_md` 稀疏行括注（runner.py:194） | "（不重叠不等于独立）" | "（该计数即使为 0 也不证明独立）" |

证据：合成两年反号反例测试
`test_report_two_year_sign_flip_keeps_actual_values`
（tests/integration/test_factor_evidence_cli.py:242），数据与主控反例
一致（2020 真/假 0.1/0、2021 真/假 −0.2/0）：

- 全期差 −0.05、删 2020 后 −0.2、删 2021 后 +0.1（反号）、年度符号
  正 1/负 1——统计值逐项断言不变；
- 报告不再含"不使差值反号"，改含"逐项查看"，并仍展示实际数值
  （−5.0000、−20.0000、+10.0000 个百分点）；
- 卡片不含"逐年方向不一致"，effectiveness 等于新中性文案；
- overlap.json 稀疏 note 不含"观察窗口不重叠"，指向计数与独立边界。

旧真实文件不改：run-01/ 与 freeze/ 原样（见 G3 保护核验）；执行报告
追加 §12 说明 run-01 旧报告中的旧模板句以纠正节为准。

### G3（S3）过程记录诚实、修后源码可恢复、旧结果受保护 —— done

1. **记录纠正（只追加，不回退代码重造日志）**：
   - `repair-r1-r4/repair-log.md` 追加 §7：明确 §1 红批"2 个收集错误
     + 其余新测试失败、旧逻辑反例全部复现"表述过宽——收集失败只能证明
     测试与未新增常量不兼容，不能证明未执行的行为反例逐一复现；行为
     反例证据以主控 review-repair.py 为准；32 次测试原始日志不可恢复
     限制保留，未补造任何日志。
   - 执行报告追加 §12（带日期）：同样区分收集失败与行为复现，并说明
     历史 run-01 仍绑定旧代码字节。
   - 旧 repair-log §1–§6 原文与旧 repair 快照/清单未覆盖。
2. **修后源码可恢复**：本目录 `code-snapshot/`（runner.py、
   stability.py、test_factor_evidence_cli.py 修后原字节）+
   `closeout-manifest.json`（基线 HEAD、新旧 SHA256、绑定声明：旧
   run-01/freeze 绑定旧字节，未来正式真实运行须新版本协议+主控授权）。
   快照核验确认快照字节与工作区实际字节一致（见下）。
3. **旧结果保护核验**（logs/snapshot-verify-3.log，26 项检查 0 失败，
   退出 0）：新快照 3 文件字节一致；run-01 清单 12 文件哈希零漂移；
   protocol-v1.0.0.json SHA 仍为 769a3501…；旧 repair 快照 8 键原件
   未被覆盖、非本轮 5 键 live 哈希仍与 repair-manifest 一致（本轮触碰
   的 runner/stability live 前移为预期）；freeze/ 与 supplement/ 结构
   在。git 层面：run-01/、freeze/、protocol、factor_lab/、factor_unit/、
   configs/、definitions.v1.json、registry、INDEX 零工作区改动。
4. **真实测试次数与失败日志**：见下节，全量如实；快照核验的调用超支
   如实上报（见预算表）。

## 二、改动文件清单

| 文件 | 改动 |
|---|---|
| `src/lei_signal/research/factor_evidence/runner.py` | S1 入口收窄 + 私有落盘函数 + main 改调私有函数；S2 两处模板 + 一处括注；docstring 同步 |
| `src/lei_signal/research/factor_evidence/stability.py` | 仅稀疏 note 改中性（其余零改动） |
| `tests/integration/test_factor_evidence_cli.py` | 新增 2 个主控反例测试（伪 real 身份拒绝、两年反号中性解释）；原有测试零修改 |
| `docs/research/factor-evidence-reliability-usage.md` | §1 追加真实入口边界说明 |
| `docs/experiments/factor-evidence-reliability-v1-2026-09-16.md` | 只追加 §12 带日期纠正 |
| `docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16/repair-r1-r4/repair-log.md` | 只追加 §7 S3 纠正 |
| 本目录（新增） | delivery.md、closeout-manifest.json、code-snapshot/（3 文件）、logs/（5 份命令输出） |

## 三、实际命令与次数（stdout/stderr/退出码存 logs/）

| 命令 | 次数 | 结果 |
|---|---|---|
| `python3 -m py_compile`（3 个改动 py 文件） | 1 | OK，退出 0（预算外静态预检，非 pytest/ruff） |
| `python3 -m pytest tests/integration/test_factor_evidence_cli.py -q` | 1/≤3 | **16 passed in 2.74s**，退出 0（logs/pytest-directed-1.log） |
| 九文件相关回归（§2 同命令） | 1/1 | **118 passed in 6.50s**（原 116+新 2），退出 0（logs/pytest-regression-1.log） |
| `python3 -m ruff check`（仅本轮 3 个改动文件） | 1/1 | **All checks passed!**，退出 0（logs/ruff-1.log） |
| 测试内合成输出 | 1 批 | 即定向 pytest 运行本身（全部写入 pytest tmp_path，无仓库内落盘）；未另跑演示批次 |
| 快照核验脚本 | **3 次调用 / 预算 1 次** | 第 1 次脚本缺陷（把交付目录相对路径拼到仓库根）零结果崩溃；第 2 次旧快照命名映射错误致第 4 节误报 FAIL（第 1/2/3/5 节有效且通过）；第 3 次修正后 **26 项检查 0 失败**，退出 0。三次输出均存 logs/snapshot-verify-{1,2,3}.log，超支如实上报 |
| `python3 scripts/check_repo_hygiene.py` | 1/1 | "归置自检通过"，退出 0（logs/hygiene-1.log） |

预算结论：定向 pytest 1/3、回归 1/1、ruff 1/1、合成输出 1 批、hygiene
1/1，均未超；**快照核验调用次数超预算（3 vs 1）**，原因是我方两次
脚本缺陷而非重复验证需要，全部输出留档可审，请主控裁处。

## 四、未解决 / 留主控

1. 快照核验调用次数超支（见上），由主控裁量是否追认。
2. 真实正向重跑仍未授权也未执行；新正式真实协议仍未创建——修后代码
   （3 文件 SHA 见 closeout-manifest.json）需新版本协议绑定后方可真实
   运行。
3. 工作区存在他人会话的并行内容（会话开始前已修改的 INDEX.md、
   registry.json、factor-library-progress 系列文件，及本次会话期间他
   人新增的 `docs/superpowers/specs/2026-09-17-ark-agent-delegate-design.md`），
   均未触碰，仅报告。
4. 共享 registry/INDEX/OKR 与主控报告的统一更新归主控，本任务未动。
