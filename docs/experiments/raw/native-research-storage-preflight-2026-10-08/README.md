# 研究写入前空间检查：限定工程交付

## 一句话结论（大白话）

新增检查能在研究开始写文件之前核对输出位置、磁盘身份和预计总占用；资料缺失或空间不足会直接拒绝。41项新人工检查和6项独立核对通过。这降低执行失败的风险；因子质量和真实收益本轮均未测量。

## 阅读和版本

先读 `implementation-contract.json`、`acceptance.json`、`initial-failures.txt`，再读本文件和自己的进度。基础提交 `dbd86bccf9ffe9ea9617a484bf8b96825880fb7d`，成果分支 `codex/native-storage-preflight-20261008`。包含本清单的准确成果提交用 `git log -1 -- docs/experiments/raw/native-research-storage-preflight-2026-10-08/manifest.json` 定位，不在清单内循环写自身commit。全任务状态仍在 `coordination/lei` 的 `docs/coordination/tasks/classic-factor-research.md`。

## 使用约束与格式

只保护显式传入 `--storage-plan` 的 `--workflow-draft` / `--workflow-contract`，包括后者的 `--reuse-predictions`、`--register-report`。旧不带计划的调用保留，未自动受保护。声明只读审查不得传存储计划。通过存储检查不授予科学计算、发布报告、真实数据或交易权限。

计划必须是 `research-storage-plan/1.0` JSON：

- `binding` 精确包含 `mode`（workflow-draft 或 workflow-contract）、`input`（绝对path与小写sha256）、绝对 `out`、布尔 `register_report`、`reuse_predictions`（null或旧目录path与contract_sha256）。输入和输出路径必须与CLI一致，输出不得已存在。
- `growth_bytes` 必须逐一正整数声明 `output`、`current_journal`、`current_lock`。复用另加 `reuse_journal`、`reuse_lock`；登记另加 `publication_report`、`publication_registry`；无未使用角色。output包含失败文件，账本/锁预算包含新父目录所需空间。相同device上的所有角色累加，不能分别看每项都够。
- `volumes` 是设备清单；每项精确包含 `id`、`kind`（internal/external）、真实 `mount_path`、实际整数 `device`（st_dev）、正整数 `reserve_bytes`。一个device只声明一次。核实际空闲空间是否达到增长总和加保留量，不能拿日常音频阈值作研究预算。
- 外盘另需 `external_policy`（path、sha256）；只能指向该CLI所在仓库的 `configs/storage-policy.v1.json`。必须与真实挂载、UUID、文件系统、可写外置盘身份匹配。配置缺失拒绝。该配置未随此限定代码分支交付；已核远端来源 `codex/gpt-system-integration-20261008@4830bdb8ed11f439d999bf2460d6c044abd00b92`，SHA256 `dbdcc8af8bd5f1d6be7ce5262e10d21177a4c4faae97d4a4d2aeda900877d4dd`。接手者先核版本/设备，不能直接沿用此机器的UUID当自己的授权。

不允许符号链接、特殊文件、双斜杠别名、未知卷或缺盘回退。普通研究合同的数据资格仍由原执行链检查，本模块不核行情许可或所有科学输入。

已具备完整合同、设备、配置及执行授权后，在仓库根按实际路径调用（以下占位路径不是可执行资料）：

```sh
PYTHONPATH=src python3 scripts/run_factor_lab.py --workflow-contract /absolute/contract.json --out /absolute/new-output --storage-plan /absolute/storage-plan.json
```

拒绝退出3，仅stderr说明；不进入原执行失败文件写回。容量只在开始时测量，不是运行中限额。之后其他进程占盘、拔盘或目录改变仍可能失败；不能宣称保护所有入口或修复旧storage_guard四缺陷。

## 最小复核（本轮实际已执行）

现有环境 Python3.11.7 / pytest8.4.2 / Ruff，未安装新依赖。新机安装、Linux/Windows与真实拔盘未验证。以下命令只运行新人工检查，不跑封存研究；给每次basetemp一个新名字，避免pytest清理已有目录。

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3.11 -m pytest -q -p no:cacheprovider --basetemp=docs/experiments/raw/native-research-storage-preflight-2026-10-08/pytest-NEW-UNIQUE tests/unit/test_research_storage_preflight.py tests/integration/test_research_storage_preflight_cli.py
PYTHONDONTWRITEBYTECODE=1 python3.11 docs/experiments/raw/native-research-storage-preflight-2026-10-08/independent-check.py
PYTHONDONTWRITEBYTECODE=1 python3.11 -m ruff check --no-cache scripts/run_factor_lab.py src/lei_signal/research/storage_preflight.py tests/unit/test_research_storage_preflight.py tests/integration/test_research_storage_preflight_cli.py
```

独立脚本在本raw新建随机人工目录，保留不删除。测试目录只在本机，不随Git上传。41项最终测试退出0；6项独立核对退出0。旧只读审查组合84通过、2失败，失败在CLI执行前因缺旧附件而发生，不能算全套兼容通过。准确缺件与失败见acceptance、initial-failures；未补旧材料、未改测试。

分支自带旧归置器把worktree的 `.git` 指针报错；当前主工作区规则支持该形态，加载只读规则并设置REPO为本工作树后退出0。当前规则源码SHA `a661696b29d685c25388441975be6316d33342c3bcc24040cff5c58a377634bb` 仅本地未随此包，不能把这个结果写成远端旧检查器已修复。未修改检查器。

## 已封存和下一步

不重跑旧真实/人工因子研究、不修改冻结协议/预算、不修旧8项指纹失败。0行情请求、0拟合、0真实标签、0封存重跑、0付费操作、0安装。两份策略临时拷贝和第一轮pytest临时目录的仓外写入失误保留于preparation/initial-failures，未上传正文或擅自清理。

接手第一步：fetch协调、核准确分支commit和manifest/SHA256SUMS、核新版是否已处理已知问题。交中控做限定非作者验收；随后只在另行具备原件资格和阶段授权时接续真实研究。不要从工程检查通过推断因子有增量或真实收益。
