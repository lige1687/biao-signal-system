---
name: trae-delegate
description: 在用户明确要求通过 TRAE 委派时，核独立 CLI 的安装、登录和权限，派发有边界的公开资料核查，并由主控验收真实结果；区分编辑器聊天启动和可追踪的 CLI 完成。
---

# TRAE 有界委派

适用：主控已定义问题、允许材料、输出和验收，用户希望让 TRAE 帮忙执行。研究方法和预算沿项目 `research-closure`、`lei-lowfreq-research` 与当前研究合同；本技能不另造研究体系、不扩大授权。

## 1. 先确认能否执行

运行 `python3 scripts/preflight.py`（本技能目录下）。仅检查版本、实际帮助参数、登录状态；不安装、不登录、不读凭证。退出 0 只代表本机前提检查通过，仍须首次有界任务检验服务权限。退出 2 为阻塞，退出 3 为命令/版本不适配。

2026-10-21 本机实测：独立 `traecli 0.209.1` 安装成功，`login status` 未登录；桌面账号不自动等于 CLI 登录。官方当日说明 CLI 2.0 限企业旗舰套餐：[使用限制](https://docs.trae.cn/cli_about-trae-code-cli-2)。后续以当时官方资料与真实响应为准，不把本次限制写成永久事实。不要复制桌面或 Codex 的令牌，不购买或升级套餐。

需要安装或修改仓外配置时遵守项目授权要求；用户已经针对同一动作授权则不重复询问。只用官方安装方式，不自动迁移、卸载、改全局环境。登录交给用户完成，不在日志保存授权回调或令牌。

## 2. 固定一份最小任务合同

复用既有任务记录，写清：问题、明确不做的研究、允许读取的准确文件与 SHA-256、文件来源、可写路径、输出字段、预算、停止条件、主控验收方法。派发前检查协调分支与其他负责人，不能替代别人的任务。

第一单用独立目录中的公开材料和脱敏方法说明；不发送账户、持仓、凭证、私人数据库。指令里限定只读列出的材料，不下载、不改源、不自行委派或扩样。提示词边界不是操作系统级读取隔离；read-only 也不阻止读取仓外文件。需要敏感材料时，先有具体材料与目的地授权及有效隔离。

## 3. 独立 CLI 路径（本机尚未完成端到端验证）

先核当次 `traecli --help` 与 `traecli exec --help`，不能把编辑器的 `trae-cn` 当作 `traecli`。本机 0.209.1 帮助支持以下模板：

```sh
traecli --no-daemon -a never -s read-only -C "$task_workspace" exec   --json --ephemeral --skip-git-repo-check   --output-schema "$task_schema" -o "$task_final" - < "$task_prompt"
```

路径由主控确定，不照抄未定义变量运行。调用方保存完整 stdout JSONL、stderr、退出码、开始结束时间、版本、输入/输出哈希；长日志按项目外盘计划路由。设置进程时限，超时或中断保存状态，重试前查结果是否已经写成。

不使用 bypass permissions、danger-full-access 或信任未知 hooks。不要自动载入未审配置。该版 `--ignore-user-config` 帮助混用了 CODEX_HOME 文案，其隔离效果未实测，不能据此宣称配置和凭证隔离；先完成无敏感材料试跑再采用。无登录或服务权限就停该渠道，项目其他获准工作照常推进。

## 4. 编辑器路径单独记状态

`trae-cn chat --mode ask --new-window --add-file ...` 只作为人工界面辅助入口。进程退出 0 不能认定问题已发送、模型已执行或答复已完成。必须从真实界面读回同一任务标识与完整答复；界面打不开、只有 Loading 或没有任务时，记 `receipt_unverified`，不得重复发出后当多份独立复核。

## 5. 主控验收

按顺序分开记录 installed → authenticated → dispatched → result_received → accepted。每一步有独立证据；不跳级。

验收至少包含：JSON 可解析且字段齐；来源确为允许材料；随机抽取的关键数字和定义由主控回到原件核对；金融含义、时间、股票池、权重、未知、费用、不能支持的结论都准确。任务运行完不等于因子有效，测试通过不等于研究成功。失败保留，不调参改基准追求正结果。

首个实证记录：`docs/experiments/raw/reversal-method-replication-2026-10-21/trae-pilot/`。当日 CLI 未认证；编辑器 dispatch 退出 0，但结果未确认。此技能已验证前提检查和失败状态，未宣称自动研究回调已打通。
