# 独立验收证据（2026-10-02）

主报告：`docs/experiments/remote-astra-core-acceptance-2026-10-02.md`。

交付提交固定为 `4155b4db7ccd14674eff2e29dfaf102d2ac3e5f9`，基准 `639ad8dbd3d2aa72f824b626b86149c466c132a4`。这不是主工作区当前分支的验收。运行副本在仓库内 `.biao/remote-astra-acceptance-20261002/checkout`；该副本是可再生的本机工作材料，不提交进 Git。需要复核时从交付提交建立副本，而不是用主工作区正在开发的代码。

本机解释器 `/opt/homebrew/opt/python@3.11/bin/python3.11`，Python 3.11.7 / pandas 2.3.3 / NumPy 2.1.1。所有交付脚本由主负责人执行，两个辅助 agent 只读审阅。

- `preflight-state.json` 保留推送前找不到远端分支的初始检查；不覆盖这个历史。
- `acceptance-state.json` 是本轮恢复后的状态，以它和最终报告为准。
- `delivery-diff.txt`、`source-and-boundary.json` 记录原交付范围及权威策略源指纹。
- `runs/<label>/result.json` 记录实际命令、退出码、耗时、文件指纹及与 Git 交付字节的比较；`run.log` 是真实输出。差异文件另存，未变化文件可从交付提交读取。
- `replay.py` 只在副本中执行指定脚本，禁止生成字节码，临时目录放在本仓库；T5 唯一覆盖的是硬编码临时目录变量，业务源码不变。
- `t5-comparison.json` 区分业务结果和机器环境差异。
- `controller_probes.py` / `controller-probes.json` 是主负责人另核的两个最小合成反例、提交边界和两 ETF 原始价格抽查；不计算新收益。
- `scope-review.md` / `methods-review.md` 是独立辅助意见，不能代替实际运行结果；对应委派合同记录模型、范围和禁止事项。
- `REPAIR-PROMPT.md` 可直接交给远端 Opus 5.5，限定本批返修内容、去重归属和复验条件。
- `population_partition_replay.py` 按原顺序把四个产品分给四个本机进程，仅覆盖原脚本的产品列表和输出目录；生产构造识别、原 `asof_structures`、输入和分类算法全部不变。新结果保存在 `runs/population-asof-partitioned/`，以最终 `result.json` 为完成依据。`partition-source-check.json` 记录原算法及四个直接计算来源均与固定交付字节一致。
- `source-followup.json` 记录第二篇指定 PDF 的有限补查仍未取回，不用另一版本替代未验证的阅读证据。

重跑入口示例（从主仓库根目录）：

```sh
/opt/homebrew/opt/python@3.11/bin/python3.11 -B docs/experiments/raw/remote-astra-core-acceptance-2026-10-02/replay.py NEW_LABEL docs/experiments/raw/remote-astra-T2-2026-09-30/run_cases.py
```

`NEW_LABEL` 必须是不存在的目录名，日志器拒绝覆盖既有验收日志。T5 要保留专用安全运行分支；另一次验收应使用新的验收目录，不覆盖本次记录。`result.json` 枚举同目录 JSON 供完整性比较，不代表每个 JSON 都由那一次脚本重写；实际产出以主报告命令表和脚本写入语句为准。

另一台只有 GitHub 数据的电脑可以在仓库内建立同一固定副本；以下操作不会切换共享工作分支。目录已存在时先核对其提交，不能覆盖别人正在使用的副本。选择安装了项目依赖的 Python，实际环境和运行命令另行留档，不要求另一台机器具有本机解释器的绝对路径。

```sh
git clone --shared --no-checkout . .biao/remote-astra-acceptance-20261002/checkout
git -C .biao/remote-astra-acceptance-20261002/checkout switch --detach 4155b4db7ccd14674eff2e29dfaf102d2ac3e5f9
python3 -B docs/experiments/raw/remote-astra-core-acceptance-2026-10-02/population_partition_replay.py --label UNIQUE_NEW_LABEL
```

分产品原始输出的候选总量/成交总量是同一个全局输入的 504/11，合并时只保留一次；分类计数按原产品顺序相加。合并后的全部 JSON 字节与交付中的完整逐日结果比较，不只比较三个主要数字。此前 `runs/population-asof/` 的人工中断留痕保留，不能以续验完成改写成此前也通过。

本轮没有改生产代码、规则账本、定义登记表、旧实验 raw 或旧报告，没有启动真实观察、采购或新增收益研究。只有报告登记与导航追加自己的报告。
