# D—MAE 恢复原件独立审查

审查人：/root/d_mae_recovered_review，GPT-6 Astra/high；2026-10-09 11:42 +08:00。只读，无修改、下载、拟合、标签或效果计算。协调基线af739e1a52b837826be6020d7fdeaebaaad6c69a。

## 一句话结论（大白话）
六份准确原件已补齐，可以继续核对身份和准备格式适配；现有程序只接受人工样例，仍不能直接把真实资料送进去计算结果。

独立重算六SHA均等于ace132原合同；study.py、test_synthetic.py、核源脚本、最终日志及设计元数据也与原回执一致。此前合成计算和局部返修审查可复用，不重跑1754项已验收检查。

准确已审代码提交b2f45151128baa1fe387cda85862d71cb01e1206：src/lei_signal/research/native_risk_d_mae_workflow.py第89–91、111–126、138–140行限定mode=synthetic与artificial_only=true，真实权限为0；第57–67行只接受仓内相对路径且解析不得越界。当前外盘恢复原件不能直接经过此入口；不能给真数据标人工或用越界链接绕过。

原件为76案例、84事件、336特征长表行；需明确date→signal_date、member_event_ids→event_ids、ATR→ATR20_SMA，逐案例核事件别名、33组、价格轴、来源及原D。只选local_contract.opportunity.invalidation_distance及冻结variant，不加其他特征，不重新去重。

deduplicated-cases的anniversary_1_calendar_month是旧B1问题。必须按原METADATA-ONLY-SUPPORT.json的all_window_metadata及合同t+1至t+21、截止2026-06-26接续；未知case:ded0d0c43677a76957f4保留，不能用旧标签窗口。

已验收的非有限V拒绝、重复事件拒绝和两阶段累计时间修复保持，不把旧问题重新报成未修复。下一阶段允许只读身份对照、真实格式适配设计和人工反例；真实X派生/封存仍需单独许可，代码与绑定独审后才执行；Y另给一次许可。指纹、成员、字段、日历、路径冲突须停受影响阶段，不缩分母。原到达时间未知等限制保持。

本次不判断D有效性。原始详细审查由本聊天子代理回调提供，恢复清单同目录recovery-manifest.json。
