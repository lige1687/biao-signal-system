# 环境与准确恢复入口

## 架构和范围

Python 研究工具与规则层 + React web 展示；本任务只恢复研究 CLI 和项目 skills，不启动 web、Streamlit、broker、定时服务或生产 API。判断仍属 Python 原规则，不迁移前端交易逻辑。workflow_bridge 的 ROOT 使用脚本向上第4级，所以必须保持 `.agents/skills/.../scripts` 与根下 `src/`、`docs/` 的关系。本包 restore.py 就按原相对关系放置。

精确源运行环境见 evidence/environment.json。Python3.11.7/macOS15.6.1 arm64；最小版本已记录在 requirements-recovery.txt。这是任务最低环境，不是全项目依赖锁；不需要安装完整 arch/statsmodels/tsfresh/DuckDB。源码有 fcntl，所以不能承诺 Windows。

## 获取与核包（从交接分支克隆，根目录自定义）

```bash
git clone --filter=blob:none --sparse --depth 1 --branch codex/handoff-external-quant-20261003 --single-branch git@github.com:lige1687/biao-signal-system.git lei-handoff
cd lei-handoff
git sparse-checkout set docs/archive/handoffs-plans/external-quant-handoff-2026-10-03
# 先将提交号与发布收据/用户提供的准确 SHA 核对，不能只看分支名。
git rev-parse HEAD
cd docs/archive/handoffs-plans/external-quant-handoff-2026-10-03
python3 tools/restore.py --verify-only
```

上面的 SSH 身份、GitHub 权限需由用户安全提供，不在包中。若没推送成功，使用已交付的同目录文件并核 SHA256SUMS，不能假定链接已有包。

## 空目录恢复与最小依赖

在交接包目录执行；`WORK_ROOT` 是本任务变量，必须选新目录，不覆盖共享仓库。纯代码恢复不用补充包：

```bash
WORK_ROOT="$PWD/recovered-external-quant"
python3 tools/restore.py --output "$WORK_ROOT"
python3 -m venv "$WORK_ROOT/.venv"
"$WORK_ROOT/.venv/bin/python" -m pip install -r requirements-recovery.txt
cd "$WORK_ROOT"
PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/unit/test_multiple_comparison.py tests/unit/test_tsfresh_candidates.py tests/unit/test_tsfresh_price_information.py tests/unit/test_research_property_checks.py
```

供应商原件和任何密钥都不是这四个合成测试的输入。期待 56 个测试通过（本次实际记录若不同，以 recovery-checks 为准）。不自动运行全项目测试或拟合入口。

## 保存预测的真实只读检查

需要先取得 ARTIFACTS 所列完全匹配的补充包，并由用户确认资料可在该环境使用。选择另一空目录：

```bash
WORK_ROOT="$PWD/recovered-with-research"
# SUPPLEMENT_PATH 指向已授权取得的 research-materials.tar.gz，不含凭据。
python3 tools/restore.py --output "$WORK_ROOT" --supplement "$SUPPLEMENT_PATH"
cd "$WORK_ROOT"
PYTHONPATH=src "$PYTHON_BIN" "$PACKET_PATH/tools/smoke.py" --root "$WORK_ROOT" --with-archives
```

`PYTHON_BIN` 明确指向已按 requirements 安装的解释器，`PACKET_PATH` 为实际交接包绝对路径。smoke.py 做固定合成运算与收据/账本核查，并准备已有 2025-01-02..2025-12-02 的 222 日材料；不做重抽统计或拟合、不重跑已封存研究。完整多期请求应返回不适用/缺失尾部，不能改输入求通过。

没有补充包时去掉 `--with-archives`，只能证明纯代码合成最低条件，不能说真实任务复现了。本次实际检查、输入/输出哈希、命令与退出码在 evidence/recovery-checks.json。环境安装失败须先定位版本/OS/网络，不重复原样重试或用全局现成环境冒充新安装。

## 下一问题入口

恢复后现有研究入口是 `scripts/run_factor_lab.py --workflow-draft` → `--workflow-contract` → `--register-report`，完整限定见 docs/research/research-workflow-usage.md。这只是后续入口，不是本次执行命令；真实新研究还需核数据资格、策略原路径映射、定义、ledger、预算和最新代码。Frozen 验证器恢复脚本仅供旧封存资格读取，勿自动运行可能发布/写账本的旧 raw 脚本。

## 变量模板与服务

configuration.env.template 仅列 FACTORHUB_API_KEY 空值。纯恢复无需任何凭据/数据库/API。可选 FactorHub 的独立 requirements.lock 已保留；其依赖安装与平台真实访问本次未验证，不纳入最低恢复通过。不要把空环境模板整个注入生产。

实际当前规则默认来自 `configs/rules.v2.yaml`，已补入准确原件（feb2c51dce704c95eea54fe3a3b6df73b6abf66f1c3e1618c99806ed5c1651c5）；V1 同时保留为旧比较依据。原报告/合同的阈值和指纹不修改，恢复默认配置不代表重新认可旧实验科学资格。初次恢复3项因缺V2失败，补齐后的最低复查见 recovery-checks。

仓库旧基线跟踪约1.96GB文件。本次完整隔离检出因磁盘空间不足失败，失败由Git回滚，未清理源资料；发布使用独立Git索引，只新提交本任务包和进度。上述远端稀疏克隆避免检出旧研究大文件，命令尚未在Linux执行；遇不支持partial clone的服务器先核容量，不改文件求通过。
