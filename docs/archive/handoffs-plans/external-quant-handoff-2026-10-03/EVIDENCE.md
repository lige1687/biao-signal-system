# 可定位证据与版本

全部准确文件路径/大小/原源指纹/版本/是否交付在 evidence/source-snapshot.json 和 materials-inventory.json。payload 中保持原相对路径，旧数据和成绩没有适配性改写。

## 结案报告

`payload/docs/experiments/`：factorhub-codex、open-finance-skills、quant-resources-adoption、quant-resources-integration、quant-resources-workflow-fit、external-increment、tsfresh-adoption、parquet-reading-assessment、tsfresh-factor-validation、external-multiple-comparison，均为 2026-10-02.md；另有四份 tsfresh-*-forecast-artifact 同日数值报告。原报告含性能表、增量表或工程用途边界。experiment-registry-snapshot.json 只保留相应登记，原 full registry 内容不作为本任务修改提交。

## 数值、协议、反例及失败

`payload/docs/experiments/raw/external-multiple-comparison-2026-10-02/`：protocol、manifest、controller-review、final-review、independent-core-check、archive-demo-check、degenerate-probe、repair-protocol/repair-regression、final-archive-recheck；源码来源 sources.json 与模块 provenance。22 项回归和 3×1000 合成对照属于旧验收，本次不再跑该大批统计。

`payload/docs/experiments/raw/tsfresh-factor-validation-2026-10-02/`：protocol、manifest、qualification、独立数值审阅、saved-prediction-analysis、controller-terminal-review、冻结源码漂移及恢复记录；原冻结合约/大 preflight/results/ledger 在补充包。独立核数 5,072 个目标与 10,144 个基准字段、共同 1,268 对象，最大差 1.56e-13；不代表未知历史或账户收益。

旧 manifest 内 absolute Air 路径、输出收据和 source 哈希属于原证据；不能替换成远端路径后声称原指纹通过。恢复只读 adapter 依相对目录读原件；科学重资格必须另行核原 bindings。

## 本次交接核验

- 原需求摘录与完整当前交接要求：original-user-requests.json，带时间和逐段 SHA。
- 源目录 dirty 状态：worktree-state.json；实际被快照文件与相对 HEAD 差异：source-snapshot.json。
- 最小环境版本：environment.json；任务未交资料：materials-inventory/source-qualification-inputs。
- 命令、退出码、日志与恢复结果：recovery-checks.json 与其指向的日志。缺少的检查标未验证。
- 包和上传安全检查：delivery-safety.json。它只说明本次候选文件，不能保证 Git 全历史无敏感内容。
- Git 可见提交与远端文件核验由交付末尾准确 SHA / 发布收据说明；不能把源 HEAD 或本地分支存在写成已推送。
