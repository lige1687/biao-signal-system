# AlphaGen 现成组件复用检查：恢复入口

本目录只交付第一方小型调用脚本、人工输入/输出、来源指纹和核验材料。完整结论见上两级的 `external-mining-reuse-2026-10-03.md`。

## 先核版本和保存结果

工作仓库 https://github.com/lige1687/biao-signal-system ，分支 `task/external-quant-progress`。本轮基础 `ada1fd79d471ae88d7f2cc41a0d0ebd8f0887026`；本目录所在的新提交由 `git log -1 -- docs/experiments/raw/external-mining-reuse-2026-10-03` 查询，协调分支同名任务记录给出实际核实的完整发布提交。

在仓库根目录执行：

```bash
python3 docs/experiments/raw/external-mining-reuse-2026-10-03/verify_saved.py
```

只需 Python 3.11 标准库，不联网、不装依赖、不导入 AlphaGen、不重新拟合。预期退出0，`status=passed`、六组独立数值检查。`SHA256SUMS`包含manifest；manifest列出其余文件大小和SHA256，避免自指。先用平台可用的 SHA256 工具核清单；Mac/Linux有 `shasum -a 256 -c SHA256SUMS` 时在本目录执行。Linux/Windows实际恢复未验证。

## 本轮真实调用（已经完成，不默认重跑）

准确命令和退出码见 `core-invocation.json`。固定上游版本259687e8f316994426416c530a94842a2fe6405e，105文件的原SHA见 `upstream-files.sha256.json`。`sources.json`有准确公开重取URL、压缩包大小277278字节和SHA，源码只在仓库忽略目录，**未随Git交付**。首次两次网页读取没有原始响应副本，该来源留档缺口明确保留。

调用脚本只实现上游要求的 `n_days/evaluate_alpha`，把人工已计算数组交给原生候选池，未运行表达式求值器、原生数据流程或完整强化学习训练；没有假造Qlib、替换上游函数或修改上游源。环境实际为Python3.11.7、PyTorch2.5.1、NumPy2.1.1、pandas2.3.3（Apple Silicon Mac）。没有安装全套上游requirements或降级环境。

AlphaGen核心许可未确认，GitHub许可字段null；不能把第三方子目录许可当作整个核心许可。因此默认恢复只核已交的结果，不下载/安装/再分发核心。未来只有明确许可、新版改变关键前提或必要独立验证才重开，先核最新协调和冻结协议，使用新输出文件，脚本会拒绝覆盖旧结果。

## 结果与停止条件

- 原生组合能合并两组人工互补信息；同向重复被拒，但完全反向重复被收录。组合统计只是代数检查，不是金融预测效果。
- 单ETF与多个ETF共同变化的人工序列，跨日期完全一致，原生按同一天不同产品比较却给0；这是评价问题不同，不应将它解释为趋势信息无效。
- 即使传入预载人工数据，`StockData`仍因缺Qlib而失败。没有冒称完整环境已恢复。
- 没有运行中的本任务进程、模型训练、行情回测或checkpoint。仅归档脚本可读回，复制它不会迁移其他任务或登录态。

## 下一位AI的第一步

先读取 `coordination/lei:COORDINATION.md` 和 `docs/coordination/tasks/external-quant-resources.md`，核准确版本与本目录SHA，再执行保存结果核验。不要从头重做Qlib五公式、RD-Agent执行恢复、QuantaAlpha修订/融合、DEAP试点或这次AlphaGen人工例子。旧报告有部分仅本地，准确路径/大小/指纹及是否在基础提交可读均见sources；本次仅交必要结论索引，不夹带其他任务旧原件。

下一问题优先是复用现有候选生成后、计算前的“已有比较重复/是否有足够正反机会”检查，尚未实施，不认领其他任务的基准CLI或整个验证流程。新增研究合同和实际数据资格未具备前，不把该计划写成在跑。
