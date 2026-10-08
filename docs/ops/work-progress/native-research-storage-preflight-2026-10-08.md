# 研究执行前路径与空间核查

更新时间：2026-10-08T18:55:59.370628+08:00（Asia/Shanghai）。稳定task-id `classic-factor-research` / 子范围 `native-storage-preflight`。目标：研究首次写文件前核对全部输出、磁盘身份和预计增长，拒绝不产生研究输出；本轮未测量因子效果或真实收益。

当前：实现和限定人工检查完成，等待中控独立验收。基础commit `dbd86bccf9ffe9ea9617a484bf8b96825880fb7d`；成果分支 `codex/native-storage-preflight-20261008`。含本进度的完整发布commit用 `git log -1 -- docs/ops/work-progress/native-research-storage-preflight-2026-10-08.md` 定位；推送与读回由协调任务记录保存，不循环写自身SHA。协调入口 `coordination/lei:docs/coordination/tasks/classic-factor-research.md`。本轮checked_coordination_sha `7f871d54ef8c6b929bdbb30f9908e0681d168829`，已读规则1.1、本任务、中控、daily、theory；仅原CLI owner改明确四路径，无同文件冲突，记录不是锁。

已完成：显式--storage-plan保护draft/contract及reuse/register；独立推导当前/旧研究账本和锁、报告/登记路径，按同device累加正增长和reserve；未知盘、缺盘、错误身份、低容量、路径别名/链接/特殊文件拒绝，研究模块导入前禁pyc。通过才进入旧执行链。保护只在带计划时启用。

证据：`docs/experiments/raw/native-research-storage-preflight-2026-10-08/README.md` 为完整用法与边界；implementation-contract/preparation保留原授权和失误；acceptance/manifest/SHA256SUMS绑定源与回执。最终41项新测试通过；6项主负责人独立核对通过；Ruff退出0；当前主工作区归置规则加载到本树通过（旧分支规则对.git指针失败，未修改）；旧审查组合84通过、2因旧附件缺失失败，不能报全套兼容通过。

仅触及合同六范围：CLI、新storage_preflight、两个新测试、本进度、本专属raw。workflow.py/question_contract.py与原冻结账本指纹不变；daily、旧storage_guard和全局登记均未写。代码和小回执拟准确提交；人工测试临时目录仍仅本地，不交Git。外盘配置不在本基线：另有已核安全来源4830bdb8，但本任务不代daily提交配置。真实新机/其他操作系统、真实拔盘、运行中竞态及真实效果未验证。

正在做：发布准确成果并交中控非作者验收。下一步：接收限定审查反馈，只修本范围；原真实D—MAE六原件/资格及阶段权限仍blocked。其他AI暂避CLI及本新增模块/测试同写，不圈占其他研究主题。

准备失误：完整worktree检出21,919历史文件、表观1.9GiB（不是实际新增占盘）；两策略检查误重定向正文到仓外/tmp；第一轮pytest也使用仓外临时目录；首次进度写入缺父目录退出1。准确路径/大小/指纹与失败见preparation/initial-failures；未外传正文，未删改/清理。后续写入只在仓内。

实际科学预算：0行情、0拟合、0真实标签、0封存重跑、0付费操作、0安装；模型成本未知。实现者请求gpt-6.1-sol/high，机械测试不冒称实际计费。没有本轮运行中科学进程；其他任务保持原状态。已封存研究、旧8项指纹失败、cloud storage_guard四缺陷不重复、不改成绩。
