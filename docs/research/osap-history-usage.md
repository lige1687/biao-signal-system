# OSAP 与历史财报版本读取

这些入口服务研究资料层。公开组合收益用于对照定义和研究结果，不能作为提前知道的选股特征。已登记 `reference.osap.catalog@1.1.0`；旧1.0记录保持。

从已落地的项目根执行（需挂载已登记外盘，旧原件不复制）：

```sh
PYTHONPATH=src python3 -m lei_signal.research.osap_reference --manifest docs/experiments/raw/osap-history-revisions-2026-10-20/osap-2025-manifest.json catalog --signal AssetGrowth
PYTHONPATH=src python3 -m lei_signal.research.osap_reference --manifest docs/experiments/raw/osap-history-revisions-2026-10-20/osap-2025-manifest.json series --signal Mom12m --signal Beta
PYTHONPATH=src python3 -m lei_signal.research.financial_revisions --bundle docs/experiments/raw/osap-history-revisions-2026-10-20/hekang-financial-versions.json --decision-at 2024-06-28T15:00:00+08:00
```

OSAP还支持 `catalog --term` 和 `diff --other-manifest`。manifest把目录、收益文件、指纹和发布版绑在一起；源文件改动即拒绝读取。已有原件可用绝对路径，读取器不下载、不复制、不写缓存。新增大输出先用既有output_storage计划外盘路径，不把全部JSON输出存进Git。

收益的percent保留来源百分数，decimal只除100一次；原Sign表示原始指标的排序方向，不能再乘到发布的多空差额收益上。NA保留；每个因子的有值日期单独核。目录有对照和弃用项，不按全部目录数宣称有效因子数量。

财报bundle以公司、准确指标、描述期间和版本分别保存。`published_at`允许有时区的准确时刻或只有日期；日期在内部表示未知时刻范围，不被补成真实午夜。公布同日不保证在决策前可知；准确时刻等于决策也不当作可执行。`--availability-basis vendor`同时要求供应商可用时间；未知即拒绝该资格。`retrieved_at`只是本次取得资料时间，不能回填历史可用时间。

调用财报CLI前会校验原件SHA、字段、金额、单位和期间。同期间不同指标不会互相覆盖，未知版本顺序会报告不确定。退出2表示所声明资料时间资格未通过，不代表策略无效。这里只选指定期间的版本，未提供自动“最近一期”、累计值转单季、TTM、财报字段提取或全市场覆盖检查。

`qualified_for_declared_time_basis`仅指所提供版本的时间条件；不代表公告取消/替代关系已全核、版本链完整或财务真实性合格。既有600股整理入口`build_financial_panel.py`已经处理原报选择与公告范围，新入口不取代它，也不要求迁移旧冻结合同。新增公告分类应使用原`financial-notice-review/1`结构，绑定原件及全文证据，再由原选择器核输入变化；本轮实例见报告raw中的`notice-review-one.json`与`notice-effect-verification.json`。新注释未写回旧冻结结果。

复用已有`data_snapshot.py`处理行情快照差异；财报版本不是OHLC日线，不强行套入价格格式。原`lowfreq_input_guard.py`精确时刻选择仍保留，旧冻结入口不改。新研究需在原合同显式绑定这次入口和原件；现有直接脚本不会自动强制迁移。

实际报告：[OSAP接入与修订案例](../experiments/osap-history-revisions-2026-10-20.md)。源数据、代码发布版本与独立生成复验分开；保存原件后才能记录新快照，旧证据不覆盖。当前只完成一个真实公开收益版本读取，不能声称已比较两份真实收益发布版。

2026-10-20当前准备导航限制：参照卡已登记，但全局preparation入口受既有green_momentum_methods_20261020来源格式与验证器不匹配阻断；该来源归因子实现对话，未修改。以上两个独立读取入口不依赖该来源卡，已用真实文件核验。来源卡修复后再用preparation查询准确ref，不降低全局验证要求。
