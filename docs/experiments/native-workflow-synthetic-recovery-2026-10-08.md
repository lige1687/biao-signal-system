# D—MAE人工研究流程与Git恢复增量（2026-10-08）

## 一句话结论（大白话）

人工案例验证了研究流程能分阶段保存、重启读回并拒绝重复或篡改；行情资料已找到但本轮没有用于真实计算，六份冻结研究原件仍缺，因此D信号与后续最不利价格变化的真实关系尚未测量，也没有发生买入。

## 本次范围

D是待检验的研究信号；这里的“最大不利价格变化”是以案例的参考收盘价为起点，观察之后20个收盘间隔内最不利的价格路径，用来检查D是否与后续风险有关，不表示有人实际买入。这份增量补充并引用已封存的[10月7日入口核验报告](native-workflow-integration-2026-10-07.md)，不改写它当时的缺口和失败。仅记录后续已验收的D—MAE专用人工流程返修、恢复材料交付，以及一个纯Git人工流程恢复节点。此处的X、Y是流程中的两个阶段代号，不代表已运行真实研究。

专用人工适配和两项测试在工作分支 `codex/native-workflow-integration-20261007`，代码提交 `b2f45151128baa1fe387cda85862d71cb01e1206`。非作者独立复核对R1/R2共29项局部检查通过；该复核只覆盖人工工程边界，不能证明数据正确或因子有效。执行代码没有在本轮改动。

## Git材料与恢复检查

远端基线盘点曾找到49项依赖，其中19项缺少已核远端相同字节。其原字节已在独立分支 `codex/native-workflow-baseline-20261008` 交付：首个快照提交 `ec565b87f794541bfa6518a8675dce941390e3e8`，补齐准确研究命令入口后的提交 `dbd86bccf9ffe9ea9617a484bf8b96825880fb7d`。19份原件共972,036字节；恢复清单逐项记录了大小和SHA-256。入口 `scripts/run_factor_lab.py` 的验收版本为4,889字节，SHA-256 `eb38c3ce70a4331026ab1dc5d8f71eb5f2e1cbffda59ceac4abbaffb15820c52`。原失败记录保留在 `pure-git-recovery/`；其原因是最初取到842字节的旧命令入口，不支持这次测试所需参数。

单项恢复检查在保存的49项来源、已验收实现和三处共享入口补丁装配后，通过：Python 3.11.7、pytest 8.4.2，命令退出码0，结果为 `1 passed in 3.40s`。覆盖人工X输入76行、Y阶段75条成熟结果和1条未知、33组逐项核对、启动新Python进程读回结果，以及拒绝重复运行和篡改回执。完整通过回执为恢复分支 `codex/native-workflow-pure-git-recovery-20261008` 提交 `fe6e51e2c9d767ebd718f77b5de020b372e0a7db`，详见[可复现步骤与范围](raw/native-workflow-integration-2026-10-07/pure-git-recovery-cli50/README.md)和[恢复清单](raw/native-workflow-integration-2026-10-07/pure-git-recovery-cli50/manifest.json)。首次失败的记录仍可在[原失败清单](raw/native-workflow-integration-2026-10-07/pure-git-recovery/manifest.json)核对。

这次证明的是：按多个已记录的Git来源装配后，现有Python环境可运行这个人工流程节点。通过提交本身没有49项装配后的全部路径，不能只检出一个分支就声称完整恢复。原实施记录列出108项文件；另外5个运行时源码和基线版本有差异，其中3个会被加载但相关函数在此节点没有调用，2个没有导入。五项的原始及旧版指纹与静态调用边界见[审计记录](raw/native-workflow-integration-2026-10-07/pure-git-recovery-cli50/five-runtime-static-audit.json)。这不等于108项完整环境已逐字节恢复，也不代表新机器能自动安装依赖。

## 效果、限制与后续条件

本次真实X、V、Y、拟合、行情请求和付费请求均为0。没有发生买入，也没有测量D与后续最不利价格变化的真实关系、资金效果或线上收益。行情资料已经找到，但本轮没有用于真实计算。仍缺六份冻结研究原件：`deduplicated-cases.json`（去重后的案例）、`label-protocol.json`（结果定义）、`native-early-events.json`（原生事件）、`x-panel-long.json`（X阶段数据表）、`validated-input-binding.json`（已核对的输入绑定）和`feature-contract.json`（D信号定义合同）；其准确路径与预期指纹见原资料的`MISSING-INPUTS.json`。还需核实资料当时可知的时间与使用许可，真实阶段预算和授权也未给出。不能根据人工测试通过推断信号有效。

若继续真实研究，须由中控先核对六份真实原件及其来源、版本和许可，再按原研究定义单独批准X阶段；Y阶段需要独立授权。任何真实结果必须与本工程检查分开报告，并记录输入指纹、比较基准、失败案例和适用范围。

## ARCHIVE

本报告封存2026-10-08人工流程返修与单项Git恢复检查事实。它不封存D—MAE真实研究结论，不批准真实行情计算、交易或生产采用。原入口报告 `native-workflow-integration-2026-10-07.md` 及其registry登记保持原样。
