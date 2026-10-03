# 环境与可复制恢复命令

本任务处于研究证据层：`src/lei_signal`是生产规则/特征，`docs/experiments/raw/remote-astra-*`是被验研究草案，旧宽基raw为冻结输入和记账实现。本交接工具只读校验及最小检查，不是新的生产入口。不启动Web、API、Streamlit、数据库、定时服务或模型服务。

源环境：macOS arm64，Python3.11.7、NumPy2.1.1、pandas2.3.3、PyYAML6.0.3、pytest8.4.2。原交付脚本Python/NumPy版本不同，会影响T5环境元数据。最低核心依赖钉在requirements-minimal.txt，成功安装的全部依赖锁在requirements-tested.txt；完整项目依赖见pyproject.toml，区间约束不是精确全环境锁。Linux/Windows未验证，不能承诺跨系统结果字节一致。

## 从Git恢复（工作目录由你选择，不是Air桌面）

先检查磁盘空间。整仓库已有大量无关历史；默认推荐下文稀疏恢复，不要在空间不足时重复完整检出。完整clone失败记录见RESTORE-FAILURE.md。

```sh
git clone --branch codex/remote-core-handoff-20261003 https://github.com/lige1687/biao-signal-system.git remote-core-task
cd remote-core-task
git rev-parse HEAD
git ls-remote origin refs/heads/codex/remote-core-handoff-20261003
python3 docs/archive/handoffs-plans/remote-core-handoff-2026-10-03/tools/verify_handoff.py --root .
python3 -m venv .biao/remote-core-handoff-20261003/venv
.biao/remote-core-handoff-20261003/venv/bin/python -m pip install -r docs/archive/handoffs-plans/remote-core-handoff-2026-10-03/requirements-tested.txt
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" .biao/remote-core-handoff-20261003/venv/bin/python -B docs/archive/handoffs-plans/remote-core-handoff-2026-10-03/tools/smoke.py --root .
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" .biao/remote-core-handoff-20261003/venv/bin/python -B -m pytest -q -p no:cacheprovider tests/unit/test_first_ma_pullback.py::test_appending_future_bars_does_not_change_past_events tests/unit/test_first_ma_pullback.py::test_event_ids_deterministic
python3 scripts/check_repo_hygiene.py
```

Windows使用venv/Scripts/python路径；该命令改写未实测，不宣称通过。Git或包索引不可访问时，缺Git凭据/已许可离线wheel位置，不能尝试导出Air凭据。requirements恢复需要公共包索引和能满足Python3.11的wheel；当前未提供离线wheel包。

校验预期：全部交付文件SHA一致；摘要504/504等保存数字对上；最小规则运行产生事件、真实CSV可读且有限值特征正常；1个smoke内合成规则检查及2个独立单元测试通过。严格完整研究准入检查：

```sh
python3 docs/archive/handoffs-plans/remote-core-handoff-2026-10-03/tools/verify_handoff.py --root . --require-full-research
```

预期退出2并列出定义证据、小时/六ETF正式资料等缺口。这是阻止不合格材料准入的检查，**不是完整研究通过**。

## 后续执行入口

先NEXT_STEPS处理返修差异；有正式新合同且材料闭合后才运行已有 `scripts/run_factor_lab.py --workflow-draft`/`--workflow-contract`。本包没有批准可直接执行的收益合同。

历史验收控制器 `replay.py` 与 `population_partition_replay.py`依赖仓库相对隔离副本 `.biao/remote-astra-acceptance-20261002/checkout`。只有返修或实质变化要求重验时才建立该副本，并固定原交付提交；历史文件和锁不改路径、不重写：

```sh
git clone --no-checkout https://github.com/lige1687/biao-signal-system.git .biao/remote-astra-acceptance-20261002/checkout
git -C .biao/remote-astra-acceptance-20261002/checkout checkout --detach 4155b4db7ccd14674eff2e29dfaf102d2ac3e5f9
```

不要用已存在的runs标签覆盖结果；旧T5脚本会清理 `/tmp/t5-work`，不得直接运行，若必要重验用已交付控制器的独立路径适配。完整T5运行所需API依赖不在最低环境，先按原pyproject安装并核版本，当前没有重跑其完整环境。

## 配置与服务

最小检查实际默认依赖 `configs/rules.v2.yaml`，同时保留历史 `configs/rules.v1.yaml`、策略指纹index和manifest指定输入；均在Git。必要环境名称：`PYTHONPATH`、`PYTHONDONTWRITEBYTECODE`；必要重验可用`TMPDIR`指向独立仓库内scratch。不需要API密钥、cookie、代理、VPN或数据库。私有供应商小时资料/其他平台只会在获准后产生额外依赖；本包不提供凭据，不假定商业许可。

没有模型训练，所以权重/tokenizer/向量索引不适用。没有活跃任务数据库备份需要；证据JSON是冻结文件，不把直接复制数据库当一致性导出。

## 只取本任务材料的稀疏恢复

```sh
git clone --filter=blob:none --no-checkout --branch codex/remote-core-handoff-20261003 https://github.com/lige1687/biao-signal-system.git remote-core-minimum
cd remote-core-minimum
git show HEAD:docs/archive/handoffs-plans/remote-core-handoff-2026-10-03/manifest.json > .git/handoff-manifest.json
python3 -c 'import json; m=json.load(open(".git/handoff-manifest.json")); paths=[x["path"] for x in m["files"]]+["docs/archive/handoffs-plans/remote-core-handoff-2026-10-03/manifest.json","docs/archive/handoffs-plans/remote-core-handoff-2026-10-03/SHA256SUMS","docs/archive/handoffs-plans/remote-core-handoff-publication-2026-10-03.json"]; assert all(not p.startswith("/") and ".." not in p.split("/") and not any(c in p for c in "*?[]\n") for p in paths); print("\n".join("/"+p for p in paths))' > .git/handoff-sparse-patterns
git sparse-checkout init --no-cone
git sparse-checkout set --no-cone --stdin < .git/handoff-sparse-patterns
git checkout
python3 docs/archive/handoffs-plans/remote-core-handoff-2026-10-03/tools/verify_handoff.py --root .
```

过滤clone命令跨机器未实测；GitHub服务支持情况由接收端实际验证，失败不能假称已恢复。完整验收冻结依赖在Git已有约136MB文件，本任务新交接文档约1MB；实际Git下载压缩量和完整仓库空间不同，另核实际磁盘。稀疏检出未包含其他任务目录不是其不存在的证明。本包最小检查不依赖这些目录。
