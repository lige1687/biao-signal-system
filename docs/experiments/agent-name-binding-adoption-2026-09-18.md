# Agent 指数名称绑定修复：生产采用记录（2026-09-18）

## 一句话结论（大白话）

验收过的修复已经装进正在运行的系统并重启生效：现在直接问"沪深300""上证指数"
这类名字，系统真的能听懂并切换讨论对象了（线上实测"沪深300"正确解析为
000300.SS，修复前这个名字解析不出来）。装之前逐个核对了 25 个目标文件和
8 个依赖与验收时完全一致（零漂移）；装完独立复跑新增单测 10/10 通过。
本次只装不改：所有文件内容与两轮验收过的候选逐字节一致，未做任何新改动。

## 采用内容与边界

- 来源：隔离候选仓验收通过的采用包
  `lei-agent-runtime-adoption-20260917/docs/experiments/raw/agent-glm-landing-validation-2026-09-18/adoption-package/`
  （S1 名称绑定修复 + 此前已验收的 Agent 连续讨论/事实记忆/稳定性 24 项，共 25 项）。
- 采用过程：`apply.sh --target /Users/yongbiaoli/Desktop/lei-signal-lab`，
  五重预校验（清单结构/双向载荷哈希/8 依赖指纹/目标 before 态/行数断言）
  全过后写入，25/25 逐哈希应用成功；任何失败即零写入，本次未触发。
- 装后验证：修复标记在 `copilot/subjects.py`（指纹=分支修复版 99734490…）与
  `api/routes/agent.py` 在位；`tests/unit/test_agent_name_resolve.py` 10/10 通过。
- 服务：launchd `com.lei.backend` 重启（kill -k），健康检查 200；前端为
  vite 开发服务器，源码改动即时生效，无需构建。
- 线上实测：POST /api/agent/chat 问"沪深300收盘价多少？"，回答正确绑定
  000300.SS 并给出数据事实。当次"AI 讲解"走降级文案（模型接口暂不可用），
  属运行环境状况：成功请求前后无新增异常堆栈，与本次装入内容无关；
  最初 3 次 500 为真实库写入锁竞争（`sqlite3.OperationalError: database is
  locked`，进入会话写库时与其他进程瞬时争锁），重试即成功，非代码问题。

## 限制

- 装入文件以工作区改动形式存在，**未单独 git 提交**（运行仓工作区另有其他
  任务线未提交改动混存，提交时机留用户）。
- 回退方式：`revert.sh --target /Users/yongbiaoli/Desktop/lei-signal-lab`
  （同一采用包内置，逐文件还原到采用前状态）。
- 真实模型正文质量延续既有边界：本轮线上问答验证的是对象绑定与降级路径，
  不构成对讲解质量的验收。

## ARCHIVE

分类数据与质量，passed 指生产采用按冻结流程完成且线上对象绑定验证通过；
不改变交易判定，不构成任何策略有效性或收益改善结论。验证细节见候选仓
`docs/experiments/agent-glm-landing-validation-2026-09-18.md` 及其 raw。
