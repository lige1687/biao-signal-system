# 方案取舍

|已采纳/否决|理由与准确依据|
|---|---|
|采纳 FactorHub 项目只读 skill|限定五 GET、不输出交易判断；factorhub-codex 报告和 skill。供应商登录/数据许可不自动继承|
|采纳 ML4T 的资料时间与预测隔离方法|方法有助审查，未整体导入示例模型；open-finance-skills 报告记录上游训练日期边界错误|
|采纳有限统计核心与日历快照|需求小，来源与许可保留；quant-resources-adoption 报告。不能说完整框架安装通过|
|采纳 Hypothesis 有界工程用例|核日期与单位变化；external-increment。故意错误反例不是本项目发现新 bug|
|保留 tsfresh 计算工具；否决这两项当前预测用途采用|两项加入已有信息均恶化，简单历史均值更好；tsfresh-factor-validation 性能与增量表|
|不迁移 DuckDB|当前读取量约 9.84 MB、273,846 行尚无实测瓶颈；parquet-reading-assessment。没做 DuckDB 性能对比|
|采纳 arch8.0.0 有限纯 Python 组件|补同基准多候选共同检查；未安装全库；external-multiple-comparison 报告。使用原单位误差，没有按波动标准化|
|拒绝常量/退化抽取分布|原严格“大于”在完全相等时可能给误导数字；degenerate-probe、repair-regression 与 22 回归|
|拒绝跨多拟合期、缺日期的自动共同比较|不得压缩日历/填尾部/改权重求数；archive-full-period.json 保存不适用原因|
|冻结验证器恢复，不改当前共享代码|旧实验后其他任务改了 EMA 字面量，引起 stale_proof；归档恢复至原 SHA，0 重拟合；frozen-validator-recovery.json|
|本次用 payload 和全新恢复目录|共享工作区混有其他任务；保留准确依赖字节但不把他们的修改作为本任务在根目录提交|

尚需人类输入仅是材料交付与身份许可。下一批具体题目由接手者在最新去重记录和策略范围内设计，遇到新输入变量改变策略或预算需确认；本次不提前选方案或创建生产规则。
