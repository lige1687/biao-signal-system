# 基线文件恢复入口

既有基线快照首批按原路径交付19份文件，供人工恢复和后续核验。先从 `baseline-delivery-manifest.json` 读取这19项的路径、字节数与SHA-256，再逐项核对。原始交付资格记录保存在 `baseline-delivery-qualification.json`，保持原字节；第3项的中控决定见 `central-review-decision.json`。

这19项及后续获批的第50项入口按核定的原路径和原字节进入此分支。19项与第50项的原作者均未确认，快照整理人不是原作者；本包不证明纯Git研究流程可运行、不构成生产采用，也不启动或授权任何市场研究。

## 第50项入口来源补记

原49项依赖清单漏列了已跟踪的命令行入口 `scripts/run_factor_lab.py`。纯Git恢复时找到的基础提交版本为842字节（SHA-256 `17a7bc63bc97893f24ee72861836d64e65298b18b4d53c67041ef999cc4613d5`），不能执行当前恢复节点需要的参数。经中控批准，本分支现在把该路径补为准确的4889字节原版本（SHA-256 `eb38c3ce70a4331026ab1dc5d8f71eb5f2e1cbffda59ceac4abbaffb15820c52`）。版本指纹由 `implementation-start.json` 与 `controller-receipt.json` 的记录支持；单文件资格和批准分别见 `cli-entry-delivery-qualification.json`、`cli-entry-central-review-decision.json`。

这项补记不改此前19项原件、19项资格历史或原19项清单；脚本原作者未确认，本次只整理原字节。此提交不验证恢复节点，也不表示新增功能或研究完成。
