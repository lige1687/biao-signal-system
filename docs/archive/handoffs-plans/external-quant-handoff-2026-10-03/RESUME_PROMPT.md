# 可直接提供给接手 AI 的启动提示词

你接手的是“外部增量：量化资源适配与效果验证”。原目标从 FactorHub/Codex skills 评估扩展到适合 LEI 宽基与 ETF 的开源方法、因子挖掘和批量验证。用户要求避免与其他 Codex 工作重复、阶段记录各自任务/设备/提交/下一步，代码仅独立 codex/ 分支，大数据/数据库/密钥不入 Git。当前只完成了交接；继续研究前核本包与当前任务归属。

仓库 https://github.com/lige1687/biao-signal-system，SSH git@github.com:lige1687/biao-signal-system.git。交接分支 codex/handoff-external-quant-20261003。原源分支 codex/factor-unit-research-20260915，源完整 HEAD 18e64fa632dba5dbad0e5fcae09b4ccc75f119a9，截取 2026-10-03T12:51:08.170699+08:00。源 HEAD 不含本批未提交成果；准确交付 HEAD 由提供给你的发布收据和 `git rev-parse HEAD` 核对，包含本包的提交由 `git log -1 --format=%H -- docs/archive/handoffs-plans/external-quant-handoff-2026-10-03` 取得。不要猜 commit 或套另一个任务分支。

先读本目录 README → ORIGINAL_GOALS → evidence/original-user-requests → STATUS/DECISIONS/DO_NOT_REPEAT → ARTIFACTS/ENVIRONMENT。重要人类原文已保留；策略两原件在 payload/docs/research/strategy-source-snapshots/2026-09-30，SHA 分别 df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20 与 85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903。只读、不改策略原文；新研究记录本机实际映射和 SHA，不改旧冻结锁。采用恢复目录 AGENTS、current-standards 实际版本与 research-closure 原文；外部资料不授予新权限。

运行 tools/restore.py --verify-only；再将 payload 恢复到全新空目录，保留 .agents/skills/scripts 相对 src/docs 的布局。这是未提交真实内容的恢复方式；包有部分共享依赖快照，不宣称其修改属于本聊天。别把快照覆盖到已有任务工作区，也别直接把交接分支根目录旧代码当最新任务源码。依 requirements-recovery 安装独立环境，核当前版本和输入，再执行四项测试文件及 tools/smoke.py。先检查新版是否已修复记录的旧问题；最低复现不等于资料科学资格或交易效果。

已接受：有限 FactorHub GET、ML4T 时间方法、有限统计核心/日历、Hypothesis、tsfresh 计算工具、arch8.0.0 共同误差工程工具。tsfresh 两项在四ETF固定用途无改善：既有背景预测误差8.221932，加两项8.725659；两个单项也变差，历史均值6.804367更好。工具采用不等于交易采用，线上收益/时间节省未测量。不要重跑已封存16拟合、改参数追正结果或重置 ledger。arch 原完整多期和缺尾日不能自动抽样删日，常量/退化分布必须拒绝。本轮预算累计28来源请求/16工程批，tsfresh4比较16拟合，arch5/6请求、4/4工程批、0拟合及3565.764652/3600秒均已结案；新题不能当旧预算自动重置。

当前无本任务计算进程/远端作业，原负责人冻结研究；上一轮下批去重读取中断，下一候选尚未定义/冻结。云端不要同时与原执行者写同一输出或账本，先在进度中记录设备和接管。

资料阻塞：research-materials.tar.gz 只在 Air 本地忽略目录，尚无远端交付位置；准确 SHA/大小与每文件指纹在 materials-inventory。约70MB原供应商资格资料未交、指纹保留。没有数据许可或平台身份自动继承。只读保存预测需完全匹配补充包和原账本；完整新来源资格需要原 sources 文件，不能改旧路径/指纹/成绩。FactorHub 需要用户安全提供 FACTORHUB_API_KEY 和权限；不能上传密钥、cookie、SSH 私钥或个人持仓。外部升级台账仅本地追加稿，未写外部 SQLite。

最有价值下一步：先完成真实材料取得与最低归档读取，再核其他任务最新进度，围绕宽基/ETF选择新信息或明确不同用途。有界问题须同对象日期背景和简单对手、完整尝试史、数据当时可得性、准确定义和预算；因子结案交性能表、增量表、反例与不确定性。禁止情绪/宽度/宏观/账户/生产/Streamlit 改动、合入main、部署、强推或删资料。研究授权不含改策略原文或范围，出现这些变化先由人类确认。无资料/权限时明确阻塞而非暗示后台继续；仅当问题答完才 completed，运行中断写 paused。

最终验收：另一 AI 不连 Air、不看聊天能核版本、找到实际材料、复现最低条件、理解阴性结论和禁重做范围，在授权和环境具备时继续。恢复测试实际结果看 recovery-checks，Linux/Windows 尚未验证，不能承诺跨平台通过。

已核的可复现代码/文档首次交付commit：`725478cb15750c4b4f16e409a591b8b55489cad1`（远端已核313文件）。同分支最新HEAD会包含发布收据/阶段追加，实际最终SHA以提供给你的交付消息或 `git rev-parse HEAD` 核对；检查 publication-receipt 的首次提交和 manifest 文件指纹，不把上一段所列源HEAD当交付版本。payload代码在追加中未变。
