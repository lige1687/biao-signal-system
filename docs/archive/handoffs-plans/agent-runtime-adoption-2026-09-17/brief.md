# Agent运行采用准备：执行说明

用户授权“可以啊，你可以delegate给zcode做”，承接已验收代码定向采用准备。不是重新修旧三轮任务，不改变已验收语义。你是执行者，主控负责架构冲突和最终采用。

只执行当前stage。S1只读审查结束后回报，等待主控；S2经阶段推进后才整合。

工作区是新建隔离worktree，29b150f5运行已提交版本，**不是当前运行工作区的完整状态**。运行存在未提交因子runner/stability、AnswerText、AgentWorkspacePage与样式改动。切勿把新worktree当实时运行态；必须对纳入清单的实际文件逐字核对，并记录HEAD+dirty指纹。

已验收来源固定 f8638b9f（实施a098939a），源码及报告从/Users/yongbiaoli/lei-agent-main-consolidation-20260915读取；不要重新检验整个历史。优先读docs/experiments/agent-context-contract-2026-09-17.md及其中设计与原始日志；追溯此前未采用稳定性：controller-ask-stability-closeout-2026-09-16.md、agent-experience-continuity-2026-09-16.md与后续主控裁决。文件若已归档，用rg定位，不能猜路径。别把主控旧失败裁决当最新源码仍失败。

先读本工作区AGENTS.md、CLAUDE.md、docs/trading-spec-v1.md、configs/rules.v1.yaml、.claude/skills/macd-reading/SKILL.md、docs/plan-sector-trend-page.md。技术层判定权不变，基本面消息只解释，MACD强度非转折，Streamlit冻结。UI仅web。所有新过程文档放docs/archive/handoffs-plans，报告/raw按AGENTS登记，scripts根不新增一次性工具。

S1按功能来源追最小代码与测试依赖，尤其稳定性（回执/断流/重试/缓存）、名称与板块、用户事实context_scope+resolve+agent、前端agentUx与两个入口；不要仅搬最后a098939a而漏前置依赖。用共同祖先/提交差异/工作区差异三者判断，双方不同不代表运行落后。测试夹具在治理后可能移位，S2可适配测试路径，不能改回旧目录。

S2采用包必须以实际运行文件快照作before、候选作after；避免git diff直接把开发分支旧内容覆盖运行的新功能。只读拷贝必要源/夹具到隔离副本，不复制.env、个人数据、密钥。运行库只能只读核对路径，不打开生产应用测试。测试用临时库和假模型；预览禁非本机网络，不能预热下载或读取真实模型配置。可复用已安装依赖，无须联网安装。建议Python /opt/homebrew/bin/python3.11、PYTHONPATH=src。浏览器限隔离端口，8000/5173不能占用。

交付必须中文说明“用户得到什么、哪些仍未投入使用”，标清未测真实模型。失败基线与修复后结果分开保存。最终只提交候选分支，不合main，不部署，不改台账；主控负责台账更新。
