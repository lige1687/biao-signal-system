# 冻结状态

- 仓库：git@github.com:lige1687/biao-signal-system.git。
- 源分支：codex/factor-unit-research-20260915；完整 HEAD：18e64fa632dba5dbad0e5fcae09b4ccc75f119a9。
- 源目录：/Users/yongbiaoli/Desktop/lei-signal-lab；截取：2026-10-03T12:51:08.170699+08:00，Asia/Shanghai。
- 独立交接分支：codex/handoff-external-quant-20261003。源工作区未切换、清理或收走其他修改。
- 工作区索引/未暂存/未跟踪状态见 evidence/worktree-state.json；实际交付字节与相对 HEAD 差异见 source-snapshot.json。仅路径记录其他任务，不带走其文件内容。

## 阶段及证据

|状态|内容|证据（payload 下）|
|---|---|---|
|完成工程、真实调用阻塞|FactorHub 五项只读 GET；缺授权 API key|docs/experiments/factorhub-codex-2026-10-02.md；skill|
|完成限定适配|ML4T 资料时间与预测隔离；有限统计计算、日历与归档桥接|open-finance-skills、quant-resources-adoption/integration/workflow-fit 报告|
|完成工程|Hypothesis 128 个生成边界用例与故意错误反例；未发现新金融有效性|external-increment 报告|
|已结案、不支持当前用途|tsfresh 两项固定表达，4 ETF、4 比较、16 次真实拟合；共同较晚评价 1,268 行/317 日|tsfresh-factor-validation 主报告、数值报告、协议、清单、独立审阅|
|完成工程、没有新拟合|arch8.0.0 共同误差工具；22 回归、独立合成算式、888 行/222 日保存预测检查；退化反例修补|external-multiple-comparison 报告与 raw 小证据|
|已评估、未实施迁移|Parquet 当前规模没有充分迁移理由；DuckDB 未安装/实测|parquet-reading-assessment 报告|
|未开始|下一批新信息候选；仅做了部分去重读取，上一回话中断，未冻结合同或发起拟合|本记录与 NEXT_STEPS|
|本次执行|交接冻结、材料打包、独立恢复、提交与同步检查|evidence/recovery-checks.json、发布收据|
|阻塞|研究补充包未交远端；原供应商资格文件未纳入；台账只保留追加稿，未写仓库外 DB|ARTIFACTS.md|

## 重要成绩与边界

预测误差大小（百分点，越小越好）：简单历史均值 6.804367；既有十项背景 8.221932；加两表达 8.725659；加幅度 8.602305；加相邻联系 8.324057。相对既有背景分别变差 0.503727、0.380373、0.102125。无因子采用结论，也没有完整账户回报。

arch 旧预测辅助区间：B0 6.089249、B1 8.193502、serial 8.325679、amplitude 8.572875、joint 8.740952。共同检查未给改善证据；与完整 tsfresh 评价日期不同，不能混为同一成绩或新研究。

## 进程、checkpoint 与接管

2026-10-03T12:57:54.124163+08:00 本机进程过滤检查未发现本任务 Python 计算进程。已完成的子执行者在同一 Air 共享目录做适配/审阅，不是独立远端任务；本次未派发新实验。无可迁移进程、远端作业 ID、文件锁或未保存数值阶段。

上次继续探索中发生编排 SyntaxError，随后只读批次输出等待被终止，用户中断该轮；未启动拟合/写新候选。不能把中断的去重读取称为已完成，接手须重新核最新任务状态。

已恢复点为两个结案阶段的完整报告/原结果。只有归档读取可从此直接续接；不能承诺迁移实时进程。原负责人到此冻结研究，新负责人在取得包、核材料并登记接管后才开展下一问题。不要两端写同一账本/输出。

发布准备失败留痕：git worktree add 完整检出原基线时退出128，报 No space left on device。基线约1.96GB，随后 df 显示185MiB可用，Git未留下活动工作树登记；创建的handoff分支仍在基线。未重复整仓检出或删除资料。改用新独立索引与commit-tree建立该分支的子提交，原分支/索引不改。具体命令与真实发布状态见发布收据。

## 发布验收（2026-10-03T13:10:58.489219+08:00）

已推送首次代码/文档提交 725478cb15750c4b4f16e409a591b8b55489cad1 到 codex/handoff-external-quant-20261003；从远端fetch后核准确commit和313包文件，全部一致。源分支HEAD及源索引SHA保持原状。此追加记录另作同分支后续元数据提交；代码未改变，不重跑研究/重复测试。所有研究计算已冻结，无待迁移进程。资料完整性仍有 ARTIFACTS 所列远端交付阻塞。
