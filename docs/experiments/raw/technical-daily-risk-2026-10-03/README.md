# 两项技术风险研究：成果与恢复入口

先读仓库 `docs/experiments/technical-daily-risk-information-2026-10-03.md`，再读 `numeric-audit-01.json`、两题 `freeze-01/contract.json`、`core-01/result.json` 与 `accepted-01/receipt.json`。最终均为本实验范围内未发现实际增量；不是完整LEI失效或生产授权。

本轮真实拟合8次已经完成。不得因换机器/接续/代码变更而重复拟合或换参数追正结果。原S01/Q01收益、D01风险以及137起点等待代价均保留原负责人及封存结论。没有仍在运行的本轮市场进程，没有需要迁移的checkpoint。

代码基线3e348e6fa49cdd399e9838f252a2c0c1f411c8c1；最终代码与小产物在task/technical-factor-sequence-progress本目录最新成果commit。准确远端SHA及当前归属看coordination/lei:docs/coordination/tasks/technical-factor-sequence.md。接续先读最新COORDINATION.md及其他记录，不凭此文件当锁。

## 无行情的最小结果核验

Python3.11.7、NumPy2.1.1是本次实际版本；没有安装新依赖。

```bash
python3 docs/experiments/raw/technical-daily-risk-2026-10-03/verify_saved.py --output /tmp/lei-risk-verification-NEW.json
```

输出路径必须不存在。预期退出0，核总体/年份/ETF/删一个ETF、固定20/60日相关日期范围，与保存数一致。只读已有预测，0拟合、0网络。独立临时目录实际验证退出0，见portable-check.json；没有在Linux/Windows执行。

`artifact-manifest.json`列必要文件大小/SHA；`SHA256SUMS`核交付文件（不含自指manifest与清单本身）。完整标签核数需要原受限/未交的源资料，已有本机记录1357条值与训练均值独立核准。不要把保存结果检查通过视为完整来源资格/资料许可/金融有效性通过。

## 完整来源资格的缺口

原价格面板、来源文档与行动材料、两份桌面权威原文、较大的逐观察preflight及本地输入链接不随Git上传，准确指纹在manifest/冻结bindings。旧全局登记表依赖的部分证据也仅在Air；完整真实流程的恢复仍须取得对应文件与合法许可，不能悄悄删旧卡或跳过检查。路径适配不得改原封存合同/锁/成绩。

69项既有source映射修复和69个本地lifecycle只读链接分别是登记完整性及本地资料恢复，不是新研究；只上传前者的元数据，没有上传符号链接或原始行情。一个旧名义CSV在独立检出中的字节与旧资格不同，先保存旧字节再恢复精确资格输入；该变化仅本地，不进入提交。

## 验证与失败

17项相关新旧测试、两真实受控流程与发布验收、独立核数及保存结果恢复已完成。扩大回归首轮39失败/33通过，输出截断，只保留可见错误，不假装全面归因/通过。归置检查仅因已有且用户明确指定的docs/progress目录不在旧白名单退出1；未改检查器、未删目录。详见adapter-test-attempts.json、pre-effect-attempts.json、targeted-tests.log、hygiene.log。

定义卡保持冻结前的实现/准备状态以保护缓存身份；最终效果以报告、accepted回执与实验登记为准。旧卡的公式与含义未修改。

本轮无买卖、无账户回测、無生产上线。小时路线仍缺真实60分钟资料，这只阻塞小时比较，不授权用虚拟日线替代。

最新共享归置检查器已明确接纳用户指定的docs/progress。只读调用该版本检查本隔离目录退出0，未复制或修改检查器；旧版本退出1保留，准确源码SHA及检查目标见 `current-hygiene-receipt.json`。
