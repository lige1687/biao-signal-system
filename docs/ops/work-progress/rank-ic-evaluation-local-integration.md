# Rank IC 评价入口本机接入

更新时间：2026-10-05 UTC。执行目录 `/Users/yongbiaoli/Desktop/lei-signal-lab`；分支 `codex/factor-unit-research-20260915`；HEAD `18e64fa632dba5dbad0e5fcae09b4ccc75f119a9`。父任务 `01a10228-d8a4-73ac-afb1-72b1c8b7003a`，本执行器是本次委派四路径唯一实现者。仅本地，未提交、推送或部署。

目标：让明确的资产排序预测用途通过统一入口评价原始因子和保存的模型分数，继续使用原数学方法；开关、择时和风险排序保留各自用途。本轮只接入独审的四文件补丁并验收人工资料，没有重新计算真实指标、运行模型或改写已封存 PPO 结果。

## 当前结果

精确四文件接入与必需合成回归 completed；完整旧冻结 CLI 兼容验收未通过，不能称全仓或全流程绿色。Rank IC 表示分数顺序与随后结果顺序的吻合程度；本次证明软件按约定工作，不证明因子有效或获得生产资格。

## 验收与证据

证据目录：`data/local-integration/rank-ic-20261005/local-evidence/`。原包、精确补丁及云端回执保留在同级 `package/`；原 ZIP 保留在该任务根目录。以上仅本机交接资料，没有外传或纳入提交。

| 验收项 | 方法和结果 | 状态 |
|---|---|---|
| 指定 Library 原包 | 本机文件可读，ZIP SHA-256 与委派一致；Library 身份与版本 0 保留 | 通过 |
| 精确独审补丁 | patch SHA-256 与独审指定一致，四份包内后像指纹逐一吻合 | 通过 |
| 当前源像和依赖 | 38 份源清单依赖全部匹配；init 原像 `ea269601b6b4fa5f1bb70f2dff555aca5a7afa236babc8005a8b4e7fd2d036c4`，三个新路径不存在 | 通过 |
| 安全接入 | 委派明确四路径写者；非阻塞独占 advisory flock 取得原 init，立即重核原像和不存在条件后正常 `git apply --check`、`git apply`，无强贴、抢锁、reset、stash 或清理 | 通过，协作读取限制见下 |
| 后像和范围 | 四份本机后像再次核对全部一致；21,894 份既有跟踪文件的前后比较只有 init 内容改变 | 通过 |
| 必需合成回归 | 原三组 76 项和新入口 58 项合计 134 项全部通过 | 通过 |
| 相邻单元回归 | validation 29 项、adapters 23 项全部通过；单元总数 186 | 通过 |
| 扩展旧 CLI 回归 | 13 项通过，8 项失败；总调用 207 项中 199 通过、8 失败，无跳过 | 未通过，失败完整保留 |
| 静态和导入 | 三 Python 文件 ruff、语法检查通过；原 6 导出完整保留，全部 18 导出可导入，10 相关子模块实际从当前本机目录导入 | 通过 |
| 调用兼容检查 | src/tests/scripts 排除独立 agents 和 archive 副本，43 份调用/导入文件形成清单；既有函数签名及数学核未改，旧冻结合同兼容限制另列 | 限定通过 |
| 目录归置与差异 | 接入前归置通过；收尾结果见 `hygiene-after.log` 与 `final-receipt.json`；精确代码差异检查通过 | 以实际回执为准 |

测试完整输出 `pytest.log`、JUnit `pytest.xml`，按模块计数 `test-module-counts.json`，失败明细 `test-summary.json`；前后像 `source-check.json`、`post-image-check.json`；原有跟踪文件差异 `tracked-delta.json`；写者记录 `writer-record.json`；接口检查 `public-import.log`；lint `ruff.log`；调用清单 `callers-before.json`。

## 实际四文件

- `src/lei_signal/research/factor_lab/__init__.py`：公开新入口及合同类型，保留所有旧导出。后像 `dfb563ec80d82c7e2c0d5cac4397ba87f5194a1b9bccabd2e1fb0d2ec7e93ba2`。
- `src/lei_signal/research/factor_lab/rank_ic_evaluation.py`：用途、来源可得时点、市场时区、交易日历端点、训练边界和冻结输入资格检查。后像 `049d1076c4c3dd0a98eced31d7503bfc6eb7d441d18b7f04a78bbba6c3f4e25f`。
- `tests/unit/test_rank_ic_evaluation.py`：58 项人工资料断言。后像 `9a0bd80170da2a309fae3ac7972122f18e9aae293b29955a17f40804983acfaf`。
- `docs/research/rank-ic-evaluation-contract.md`：保留独审原文，不改云端交付时“尚未本机接入”的历史描述；当前本机状态由本记录说明。后像 `32d26b3cc9b65a232f39d78d612421d90ec0a6ad2f460abe62ef5c5f92742035`。

`diagnostics.py`、`momentum_prototype.py` 等 38 份清单依赖前后仍完全一致。原 `evaluate_predictive` 的 synthetic-only 合同没有放宽。新入口没有代替旧 caller 的自动分派：调用者须明确传入新冻结合同。

合成测试实际覆盖：至少三对资产、并列平均、常数/缺失返回未定义；原始因子与模型分数类型分开，风险标签须明确 risk 用途，择时/入场条件不强制 IC；当地周界及有指纹日历精确跨度；严格到达时点与有限收盘后回顾分开，未知不补造；封存结果须独立附加冻结研究与合法 SHA。云端独审 10 项额外反例回执复用，包内没有独立反例执行脚本，本机未声称另重跑这 10 项。

## 失败与兼容限制

1. 旧 CLI 测试首先因 `scripts/run_factor_lab.py` 不符合 2026-09-15 原冻结合同而退出 3：合同 `17a7bc63bc97893f24ee72861836d64e65298b18b4d53c67041ef999cc4613d5`，当前及本次接入前均为 `a8542f48980a52edb6f59b276ef64dacf801aa48cf751fbd39165f9d30497476`。每份旧协议共四处代码身份不符：CLI、definitions.py、adapters.py 三处接入前就存在，本次更新 init 新增第四处。精确位置与前后指纹在三个 `protocol-*.json.mismatches.json`。这些拒绝证明冻结检查保持生效，不能视为旧成功路径通过，也不能覆盖旧合同让测试变绿。
2. 为检查当前源码能否复用原人工期望，尝试准备独立临时 synthetic-only CLI 合同；在写新合同和任何计算前发现 `mixed.momentum.raw@1.0.0` 的定义卡指纹也与旧期望来源绑定不同，主动停止，未自动更换定义身份或期待数字。记录 `synthetic-smoke/blocked.json`：旧卡 `bfd8b4703709b92339bb92eb4c9ec77ab3e80f732da304153ce63fa1d6ecb2b2`，当前卡 `14c39a48f8afd5c21b776153cce98ab31cd7195da6b5d13642815c03fd512ade`。该补充路径没有完成新 CLI 计算；没有删除失败项或修改现有测试。
3. 恢复完整 CLI 兼容验收需原负责人另行核对上述定义变化、冻结一个使用当前源码及认可定义的独立人工合同和独立期望；保持旧协议、原结果与失败不变。本任务只能写独审四文件，无法在现有授权内修订共享 CLI/定义或封存协议。新入口本机合成与公开接口验收不依赖这个旧合同恢复。
4. 协调 Git 的 SSH 只读刷新长期无响应，临时 HTTPS 并发尝试因本执行器先前 fetch 的 `shallow.lock` 退出；没有删除锁。另一个独立临时目录、限定 40 秒的 HTTPS 读取也超时。已停止自己的未完成 fetch，不动其他进程；未修改共享 Git refs/index。随后补读当前公开 COORDINATION.md 和 classic/technical/external/remote-core 四个相关任务页面，没有发现四目标的已登记写入重叠。公开页读取不能冒称成功 fetch 或排除未登记活动。当前委派明确实施者，未推协调记录遵守本轮禁止 push 的指令；本记录和写者证据供父任务接续。
5. 完整真实因子/模型训练调用、Qlib 引擎、实时到达资格、运行进程切换、全仓测试及生产效果均未验证。本次无真实 Rank IC、新模型拟合、行情下载、PPO 重新汇总、提交、push 或部署。整个生产流程并未自动采用新入口。

## 来源与接续

Library `libfile_d54ef8bbc1708191842ba7f707577acf`，版本 0；ZIP SHA-256 `5ea2c93fac22b1529b430312492d94bf1829caeab0ebee3805b13fc750a93292`；独审 patch SHA-256 `ebeb4088469f8c40c292911d865d262d7d8b0c644e1c437845608638496e18b0`。正常 Library 技能下载助手取得本机字节；受限网络第一次下载失败后，经自动审查允许同一指定下载，成功并核元数据与指纹。未返回云端工作路径，没有触发云端路径的本机目录重试。

两份桌面策略源实际 SHA-256 与已确认一致：技术体系 `df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20`，技术实现 `85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903`。本次服务研究评价层，不改变原策略语义或阈值。采用当前索引作边界核对，不迁移旧冻结协议。

父任务可直接核 `final-receipt.json`、四后像和 134 必需项结果后验收本机精确接入；若要完整旧 CLI 绿色，先按上述定义/源码差异恢复条件安排独立合同，不能继续硬贴或覆盖封存。无后台研究或测试待收。本次没有另派子 agent，实际模型费用未知。

## 父任务要求的八项失败窄对照（2026-10-05 UTC）

已按后续委派，仅在独立临时原像/后像副本运行原八项失败：原像8失败，后像8失败；八对完整运行日志逐字节相同，均先因既有 `scripts/run_factor_lab.py` 与旧冻结合同指纹不一致退出3。没有改旧合同、测试期待值或共享代码。前结构修复的实际指纹记录进一步证明该CLI、definitions.py、adapters.py差异在结构修复前已经存在；不是结构修复新增的首个错误。本次RankIC改变init指纹，确实增加第四处旧合同身份差异，但这八项均未到达它，不能视为已证实功能回归，也不放行旧冻结合同。

完整八名称、逐项期待/实际/前后差异、方法和恢复建议在 `data/local-integration/rank-ic-20261005/local-evidence/cli-before-after/report.md`；两次原始测试输出、JUnit及完整run.log均保留。原134通过记录和原8失败记录不覆盖，不把本轮16次失败重复计算成新增独立问题。本轮问题已回答，未追加真实计算或修改源文件；仍不声称全仓/成功CLI完整路径通过。
