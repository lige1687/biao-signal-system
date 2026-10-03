# 最小恢复与证据阅读

阅读顺序：报告→protocol.json→sources.json/component-provenance.json→core/{inputs,results,checks,skill-pack}.json→core-receipt.json/followup1-receipts.json→manifest.json。合成记录不是市场成绩。官方完整许可FactorMiner-LICENSE.txt，SciPy许可另附。来源archive/wheel准确URL、字节/SHA在sources/scipy-wheel。源文件完整清单upstream-files.json，实际导入23模块清单core/loaded-upstream.json。

## 不执行原生组件的保存核验

在项目根执行，Python3.11标准库即可：

```sh
python3 -S docs/experiments/raw/factorminer-experience-actions-2026-10-04/verify_saved.py
```

预期status passed，独立核27值，无第三方包、网络、模型或拟合。manifest不包含自身/SHA256SUMS，最后清单覆盖manifest，避免自指。实际退出0；破坏副本检验见restore-validation.json。仅它证明保存算术，不重新证明原市场资格。

## 实际使用建议入口

需要Python3.12及NumPy2.3.5/SciPy1.17.1；本机3.11不能导入此固定上游。PYTHON312为接手设备已具备的解释器，UPSTREAM为从准确公共URL恢复并核SHA后的源码根目录，DEPS为隔离依赖目录，ROOT为项目根。只有需要重新运行组件时才恢复公共源与依赖；不要完整安装上游GPU/LLM平台。

```sh
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$DEPS:$ROOT/src"
"$PYTHON312" -m lei_signal.research.experience_actions \
 --input "$ROOT/docs/experiments/raw/factorminer-experience-actions-2026-10-04/example-input.json" \
 --upstream "$UPSTREAM" \
 --provenance "$ROOT/docs/experiments/raw/factorminer-experience-actions-2026-10-04/component-provenance.json" \
 --skill-pack "$ROOT/docs/experiments/raw/factorminer-experience-actions-2026-10-04/core/skill-pack.json" \
 --output "$ROOT/.biao/experience-resume-new"
```

预期退出0，status research_unqualified，selected_recipe smooth_3；读取输出recommendation.json，与adapter/recommendation.json一致。没有执行公式、取行情或调用模型。无--skill-pack则四种修改均25%；不同目标/未知变化特性也不迁移经验。不要通过更换seed选择喜欢的结果。

安装恢复依赖示例：在有授权公共下载环境中先核sources/scipy-wheel精确版本；Python3.12可用`-m pip install --target "$DEPS" numpy==2.3.5 scipy==1.17.1`。该从零网络安装命令未实测，本机实际是已有NumPy+核SHA后的原wheel解压。Mac arm64的SciPy wheel不适用于Linux/Windows，须对应发行且先验许可和指纹，不能宣称跨平台通过。

真实研究使用仍需准确native IC含义、父子公式与选择记录、范围和独立来源资格；本项目旧RMSE不能转换冒充。本工具不自动学习自然语言报告，也不负责金融研究定义、资格或交易决策。没有必需密钥、权重/tokenizer或真实行情；合成SQLite本地终态记录不需交付，可从inputs.json恢复，避免把库加入Git。

run_probe.py仅保留冻结核心调用，原生源/旧完整实验不需为验收再执行。本次独立临时目录恢复已经做，不依赖默认项目用户名路径。回执公开副本将本机绝对根替换${ROOT}、解释器替换${PYTHON312}；原字节仅本地.biao。源码和wheel均能从指定公共URL取回，但没有授权网络/依赖的机器只能做标准库保存核验。
