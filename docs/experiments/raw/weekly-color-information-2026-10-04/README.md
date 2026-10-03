# 上一已完成周20周黑绿状态：证据与接续

负责人仍为 `technical-factor-sequence`，这是成果共享，不是接管授权。先 fetch
`coordination/lei` 并读取根规则与本任务、risk-shape、external、classic 的最新记录。
本轮代码发布在 `codex/technical-factor-sequence-progress-20261004`，旧 `task/technical-factor-sequence-progress` 保留历史；本地有修改的工作区未切换；准确版本由本目录所在 commit 和协调记录核对。

本题登记前即固定：从技术体系§2.7的日周颜色语义出发，只检验**周线背景部分**。
上一ISO周的20周颜色，在日线颜色、日/周涨跌、波动及ETF身份之后，有没有新增判断帮助？
不等价于日周同时变绿的入场事件、不等价于完整原策略。颜色不是可任意排序的数值。

阅读顺序：`brief.json` → `input-audit.json` → `registration.json` →
`return/qualification.json`（风险题亦单独保存）→ 两个 `core-01/contract.json` →
`analysis.json` → 仓库报告 `docs/experiments/weekly-color-state-information-2026-10-04.md` →
`checks.json`、`manifest.json`、`SHA256SUMS`。文件是否确实存在及校验相符，以实际内容为准。

## 可独立进行的只读核验

在仓库根目录、无需行情或第三方统计包：

```sh
python3 -S docs/experiments/raw/weekly-color-information-2026-10-04/verify_saved.py --root . --results-only
```

输入为本目录 `analysis.json`、两题 `core-01/{contract,result,receipt}.json`、清单。
核对保存结果的内容指纹、日期边界、共同对象和误差数字；正常输出
`saved_evidence_verified=true`、`new_fits=0`。它不能重新证明历史行情来源资格或交易有效。
不带 `--results-only` 时核对整个交付清单；任何缺文件或字节变化都拒绝。

最小相关工程检查，在具备当前依赖的仓库根目录：

```sh
PYTHONPATH=src python3 -m pytest -q tests/unit/test_weekly_color_information.py
```

测试使用人工资料，结果不代表因子有效。环境以 `input-audit.json` 和 `checks.json`
实际版本为准；未在Linux/Windows或全新依赖安装验证，不能宣称跨平台已通过。

## 完整输入及禁止重复

日线panel在 `docs/experiments/raw/volume-information-2026-09-30/execution/panel.json`，
1,582,974字节，SHA256 `382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b`。
来源manifest SHA256 `a0c3b15bc56ac34c4538ac9b11e505a83c0f8bed97175459d7eccb74c2b11c94`。
两份原文SHA在brief和合同中；已有仓库原文快照绑定原SHA，桌面文档不修改。
四只固定国内宽基ETF为510300、510050、510500、588000。完整安排4340行、1085日；
暖启动筛出的日期、成熟标签和后期共同集由qualification与analysis分别明确。

价格原件、行动PDF、行级来源、完整preflight未随本次Git交付；逐项必需路径和指纹在
冻结合同的 sources/data/绑定中。接手环境缺文件时先由用户在获准位置提供相同指纹的
合法材料，不能自动跨项目取数、重抓替代或假定商业资料许可继承。历史供应商实际到达
时间与全部行动记录完整性尚未认证，只能有限回顾研究。

本题最多8次真实OLS计算、0行情/付费；辅助整体/ETF/颜色组历史均值只用较早已成熟
标签估计，明确另列，不偷读后期来构造预测。预定5/10/20/60/120日分组、两后期、
四ETF/去单ETF与20/60日连续日期检查不是参数搜索。全部历史已见，后期不能称盲验证。
已封存日20/日60黑绿、EMA持续、等待日龄、相邻黑转绿等研究不重跑。只允许新合法输入、
明确口径缺陷或新的已授权用途下另冻新问题；不能改本题周数、颜色、基准或日期追正。
`prepare.py`的注册拒绝覆盖已有对象；研究结束后不需要重注册或再跑核心市场计算。

没有后台采集/自动交易/市场PID/checkpoint；复制文件不会迁移进程、凭据或锁。
独立核保存结果不争用本任务实验输出。任何重开市场实验先核协调、授权和原输入指纹。
