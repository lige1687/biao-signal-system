# 外部量化资源：独立接续交接包

## 目标与真实状态

为 LEI 的宽基与 ETF 研究引入能复用、算得对、且有机会提供新信息的外部量化资源，并用已有信息和简单预测作同条件比较。当前资源适配已落盘；两项 tsfresh 固定用途效果研究已结案为“不改善”，arch 多方案共同误差工具已通过限定工程验收。没有线上收益测量、生产采用或下一批已启动实验。

本次只交接、核对与最低恢复测试，不开展新研究。源工作区有其他任务改动，不能用源 HEAD 代表本任务未提交成果。本包 payload 是本任务源码、必要共享依赖及规范的逐文件真实快照；共享组件只是恢复依赖，不宣称是本聊天独立改动。分支根目录仍是原基线，接手应使用恢复后的独立目录。

## 阅读顺序与第一步

1. ORIGINAL_GOALS.md 与 evidence/original-user-requests.json：读人类原文、策略原件及权限。
2. STATUS.md、DECISIONS.md、DO_NOT_REPEAT.md：区分工具可用与因子有效，查封存和预算。
3. ENVIRONMENT.md、ARTIFACTS.md、EVIDENCE.md：核版本、代码快照、资料是否真的已到达。
4. 运行 `python3 tools/restore.py --verify-only`；再按 ENVIRONMENT.md 恢复到全新目录并做最低检查。
5. NEXT_STEPS.md 与 RESUME_PROMPT.md：满足接管条件后登记新负责人；新研究先核其他任务，不重复封存研究。

## 交付边界

- Git 包：代码、项目 skills、许可、策略精确副本、原始需求摘录、报告、协议和小型证据；每个文件见 manifest.json / SHA256SUMS。
- 本地补充包：行情输入、保存预测及完整检查资料，只在忽略的 docs/ops/recovery/external-quant-handoff-20261003/research-materials.tar.gz，尚未向云端交付。准确大小和 SHA 见 ARTIFACTS.md。
- 原供应商文件约 70 MB：指纹清单已交，原件未纳入本包；仅重新核查完整来源资格时需要，不是只读保存预测检查的运行条件。
- 没有权重/tokenizer/向量索引；模型系数在保存结果里。没有数据库、密钥、登录态、全局环境或进程迁移。
- Linux/Windows 未验证；macOS 迁移目录测试实际结果见 evidence/recovery-checks.json，不以文档“完成”代替材料资格或执行授权。

本包自检：manifest 不纳入自身与 SHA256SUMS；SHA256SUMS 纳入 manifest、排除自身，以避免循环哈希。包含本目录的准确交付提交可用 `git log -1 --format=%H -- docs/archive/handoffs-plans/external-quant-handoff-2026-10-03` 定位；最终推送收据不写入自身提交。

最低恢复已实测：新虚拟环境安装成功，56项唯一测试已有通过证据（修补遗漏V2配置后复查5项），迁移目录真实保存预测只读检查通过且原件不变。Linux/Windows、FactorHub真实访问仍未验证；补充包仍未交远端。磁盘空间造成整仓检出失败，记录保留。
