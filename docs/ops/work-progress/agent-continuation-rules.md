# 项目 AI 执行与收尾规则

## 当前状态

- 更新时间：2026-10-04（Asia/Shanghai）。
- 范围及授权：用户同意把三条结束检查加入项目级规则，并同步到 GitHub；不修改全局规则，不自动合入 main。
- 当前计划：补充规则 → 读回与文件归置检查 → 仅提交本任务规则和进度 → 推送 codex 工作分支。
- 已完成：AGENTS.md 的“执行与收尾”加入阶段完成、具体阻塞、结束前核对三条；CLAUDE.md 已有 @AGENTS.md 引用。
- 正在做：仅提交本任务规则与进度并推送；规则修改与验证已完成。
- 负责设备：本聊天本地设备，主负责人 Codex；设备主机名未确认。
- 工作分支：codex/project-continuation-rules-20261004；以 origin/main 为基线，仅带入相关执行规则和本进度文件。
- 相关提交：尚未提交；后续可通过 git log -- docs/ops/work-progress/agent-continuation-rules.md 定位包含本记录的提交。
- 生效边界：本地 AI 需加载 AGENTS.md；GitHub 上的 AI 需使用包含规则的分支。尚未合入 main，不能宣称默认分支已生效。
- 下一步：完成检查并推送工作分支；main 合并须用户明确确认。

## 阶段记录

### 2026-10-04：开始与规则补充

检查了共享工作区：已有大量其他任务改动，AGENTS.md 也有既有未提交修改。此次保留这些改动；GitHub 提交只包含“执行与收尾”相关规则及本进度文件，不带入其他研究、代码或数据。

### 2026-10-04：本地验收完成，GitHub 发布准备

三条规则已逐项读回；CLAUDE.md 引用核对通过；python3 scripts/check_repo_hygiene.py 全绿；git diff --check 通过。本次为文档约束变更，不涉及交易规则或程序行为，未运行策略测试。GitHub 提交基于 origin/main，只新增执行与收尾章节和本进度文件；推送后核对远端提交，main 仍须另行批准合并。
