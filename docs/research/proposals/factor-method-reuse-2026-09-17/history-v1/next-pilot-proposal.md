# 下一步试点建议（最多一项，未实施）

**本文件是提案，不是执行许可；文档中的示例不是已实现的 schema。**

## 建议（唯一一项，且仅此一项）：alphalens-reloaded 固定版本合成输入隔离核验

其余方向（statsmodels HAC、arch 块自助、外部因子定义引入）本轮结论为
**暂缓**：HAC/块自助要等有明确的单序列回归或稳定性问题再启用；外部因子
对照无当前消费场景。Alphalens 适配与短名单 v1.1.0 的"第一优先"建议一致，
本轮已把默认开关核到源码级，具备写输入合同的条件。

- **候选版本**：alphalens-reloaded **0.4.5**（GitHub tag 0.4.5，2025-07-23；
  Apache-2.0，取自 performance.py 页标注）。⚠️ 本轮源码细节读的是 `main`
  分支，**执行时必须改读 tag 0.4.5 的对应文件并复核默认值不变**——这一步
  未做，不许跳过。
- **环境**：隔离环境安装（本轮未安装；依赖与 Python 版本兼容性未验证）。
  不写入 pyproject 主依赖，不进入生产路径。
- **输入合同（拟）**：
  - factor：MultiIndex(date, symbol) 合成分数，日期用本地项目日历的
    plain dates（时区 None，与 prices 一致，避免 `NonMatchingTimezoneError`）；
  - prices：宽表合成价格，必须覆盖最后因子日 + max(periods) 个交易日
    （工具要求 buffer，末端样本不完整是已知缺口来源）；
  - 显式参数：`quantiles=3`（合成池小，不默认 5）、`periods=(1,3)`、
    **`filter_zscore=None`（必须关默认 20——它用未来分布过滤，含前视）**、
    `max_loss=0.0`（让分组异常暴露而非吞掉）、`binning_by_group=False`。
- **输出合同（拟）**：`factor_information_coefficient(factor_data,
  group_adjust=False, by_group=False)` 的逐日 IC；`mean_return_by_quantile(
  by_date=True, demeaned=False)`（**必须显式关 demeaned**——默认 True 是
  多空口径，合成核验阶段不构造任何多空）；`factor_rank_autocorrelation(
  period=1)` 只作名次稳定性描述，**不得**写入任何"换手/交易成本"结论。
- **拟测试手算例与预期（先写期望，退出码 1 不放行——沿 factor_lab 纪律）**：
  1. 完美排序（分数=未来收益名次）：逐日 IC=+1.0；
  2. 反向排序：IC=−1.0；
  3. 常数截面：IC 记缺失（不填 0）；
  4. 并列分数：预期分组不因并列制造假高低差（并列标的应同组或行为可预登记）；
  5. 末端不完整前向收益：末端样本被置 NaN 且损失在 max_loss 报告中单独列示，
     不混入"质量合格"；
  6. 尺度不变性：分数×100 后 IC 不变；
  7. 缺失：某日缺一标的价格——预期该日该标的无资格，不静默填充。
- **成本/许可**：Apache-2.0 代码许可（数据许可不涉及——只用合成输入）；
  安装一次隔离环境；约一轮执行+主控复核。
- **停止条件**：tag 0.4.5 与 main 默认值不一致且差异影响上述开关；任一手算
  例不符且原因定位超出"文档语义"范围；合成验证通过后**不得**直接推广为
  "兼容性已验证"——真实 ETF 数据资格是另一道闸（principles §6）。
- **可写面**：`docs/experiments/raw/<新实验名>-<日期>/`（协议、期望、运行包）
  + `docs/experiments/` 结案报告；不动 src/、configs/、registry（登记按归档
  规约另行完成）。
- **待批准项**：①安装 alphalens-reloaded 0.4.5 到隔离环境；②新建上述实验
  目录与协议；③结案后是否把它列为正式横截面分析实现。三项均需用户/主控
  批准，本提案不构成授权。

## 明确不建议本轮之后立刻做的

- arch/statsmodels 启用：等出现明确的单序列问题（B1 后续或宽度状态均值差）
  再定，避免"先有锤子再找钉子"。
- SPA/多方案检验：无完整尝试史与损失序列，暂缓（红线：不得宣称过拟合已排除）。
- 外部因子数据下载与本地登记：无消费场景，暂缓。
