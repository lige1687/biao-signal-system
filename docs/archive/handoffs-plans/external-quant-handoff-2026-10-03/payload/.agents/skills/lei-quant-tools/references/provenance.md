# 来源与复制边界

- statsmodels 0.15.0：从固定PyPI wheel的 sandwich_covariance.py 原样选择 weights_bartlett 与 S_hac_simple。只调整模块包装与导入，未修改这两个函数；许可和版权通知保留在 scripts/statsmodels-LICENSE.txt。没有安装或验收整个statsmodels。
- exchange_calendars 4.13.2：只提取 XSHG 文件中的2026年休市日期列表，未执行上游代码；提取后与上交所2026年通知逐日核对。Apache-2.0完整许可保留。没有安装或验收整个日历库及其他市场。
- 官方通知只有发布日期，没有日内发布或供应商到达时刻，不能证明盘中历史可用性。
- 具体下载URL、SHA-256、源文件和逐项检查见 docs/experiments/raw/quant-resources-adoption-2026-10-02/manifest.json 与 checks.json。

## 2026-10-02 归档读取适配

新增 `workflow_bridge.py` 和 `workflow-check` / `workflow-hac`：复用本地研究
程序的数据形状与日期验证，核对原产物指纹及只读执行日志；仅在完整日期、
同一资产集合、同一拟合时期下计算辅助误差。两个借用的statsmodels函数
及2026日历快照未改。当前包仍没有安装整个statsmodels或exchange_calendars。

改动前技能及CLI入口快照、失败记录、真实归档调用、独立审阅和检查保存在
`docs/experiments/raw/quant-resources-integration-2026-10-02/`。原接入报告的指纹
代表当时版本，不回填为当前代码。

## 2026-10-02 tsfresh 两个计算核心

- 固定 tsfresh 0.21.2，MIT许可与版权完整保留在 `scripts/tsfresh-LICENSE.txt`。
- 从 [PyPI发布包](https://pypi.org/project/tsfresh/0.21.2/) 的
  `tsfresh/feature_extraction/feature_calculators.py` 选择 `mean_abs_change`
  与 `autocorrelation`；正文原样，仅省去注册属性装饰器并保留所需NumPy/Pandas导入。
- wheel SHA-256：`28dcef148f90f5d5d5176446ff34f360b71c31500fa2b71c4cb2a3090f236318`。
  固定包、完整原文件、来源请求及代码核对证据保存在
  `docs/experiments/raw/tsfresh-adoption-2026-10-02/`。
- `tsfresh_candidates.py` 为本地输入、日期和单位适配；它没有调用整套提取器、
  自动填空或显著性筛选。无需安装完整tsfresh；项目既有NumPy/Pandas足够。
- 网上latest API为开发文档；实际采用依据是上述0.21.2发布包源码，其他版本不冒称已测。
