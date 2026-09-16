# 第十一批：隔离修复与复测

主报告 ../../acd-repair-validation-2026-09-08.md。服务于规格§3.2/§7/§9A/C/D。仅修改研究包4个规则文件，参数、生产和旧批次不变。

history-diagnostic是同一17段122日期×3模块；continuous-results是两个已知问题日期附近42日期×4类记录。两组全部一致，不是534次独立交易。complete-regression-tests.txt为64项合并检查；旧失败和一项输入契约变更记录均保留。

原始版本差异见old-new-event-comparison.json与压缩完整差异；四个旧问题确认保留，但513100引用底部日纠正为实际首次确认日12月30日，调查保留。输入和运行锁定见initial-lock、repair-lock、run-lock与运行中补记runtime-audit-lock，后者不可冒称启动前新增登记。

本目录封存后复制到新目录再复现，勿在原目录执行会覆写输出的脚本。源代码修复不等于生产采用或证明盈利。学习增补在docs/literature-learning/repair-validation-lessons-2026-09-08.*。
