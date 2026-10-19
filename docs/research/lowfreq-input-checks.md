# 原600股研究资料的新检查入口

用途：阻止不合格输入继续进入原历史价格评估器。适配`lowfreq-evaluator-contract/1`、冻结design-v3；不替代通用研究合同、已有source qualification或研究授权，不接受任意设计。

只读检查：

```sh
PYTHONPATH=src python3 -B -m lei_signal.research.lowfreq_input_guard \
  --contract docs/experiments/raw/lowfreq-expanded-discovery-2026-10-19/evaluation-input-contract-v2.json
```

退出3表示阻断；0仅表示当前实现的历史输入检查无阻断，仍为`historical_only_conditional`。原600包现应因sz.001914的1,560行返回复权口径冲突退出3，不能删掉检查或把报错改为通过。

有新的明确研究授权、输入资格、冻结方案、剩余预算、外盘新目录后，才可在同一命令加`--run --out <绑定的新目录>`。该入口先检查，再调用旧`run_study`；没有本轮授权不要重跑已封存实验。实际坏包拦截证据见[检查报告](../experiments/lowfreq-data-integrity-enforcement-2026-10-20.md)。

`--claim`目前只支持`historical_price_diagnostic`。`executable`、`nominal_price_floor`、`size_filtered`、`point_in_time_proven`等一律拒绝，填写布尔声明不能放行。暂无合格资料时，不用自称“已过滤微盘/已验证成交”代替实现。

三个辅助函数的范围：

- `select_available_records`：仅执行已提供时间字段的选择逻辑，要求带时区，分证券/报告期选决策前最新版本。它不验证提供的available_at是否真实；原公告、到达、修订证据仍要单独取得。来源只有日期时不要虚构盘中时刻。
- `historically_listed`：只按历史上市/退出日期判断，不以今天状态删除全部退出者；不证明供应商名单完整。
- `frozen_selection_execution`：保留事先目标及未成交/未知标记，不重排；`filled_weights=None`，不声称实际成交和资金收益。

旧冻结评估器的直接入口仍能绕过这层检查，其他入口未自动覆盖。旧文件及结果保留，恢复者须明确选择新检查入口。该说明是本适配器用法，不另立全局研究标准，也不扩大数据或交易权限。
