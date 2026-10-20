# 第四批研究原始材料

本目录对应 `docs/experiments/dca-actual-fund-cash-comparison-2026-09-08.md` 与 `research-fourth-progress-2026-09-08.md`。

- inputs：固定源仓库副本；input-manifest.json列原位置与指纹。
- prices：28段名义报价原响应、合并CSV、分段一致性与日期检查。
- events：510300的13次现金分红原公告；另外三只基金正式报告及逐年覆盖限制。
- study：运行前方案及三份指纹锁、研究账户、12个固定结果、逐笔收支和独立审查。
- evidence-cards.json：沿用现有公共证据契约，研究字段在扩展部分；不表示生产接入。
- registration.json：报告库本批增量；okr-before/after：研究目标进展留痕，长期窗口仍未完成。
- verification.json：归档检查结果；final-manifest.json封存本目录与两份报告（排除自身及临时Python缓存）。

首次12项检查在研究账本未实现时失败，原输出test-red.txt保留；实现后及交付前均通过。独立检查追加无效收盘价反例，当前仅运行入口拦截，本次真实数据未受影响。归档检查曾误用公共契约字段别名，改为已有的source_path/source_hash后通过，未改变实验计算或结果。

复现请先复制本专属目录及所引用第三批qfq价格，随后依次运行study/test_cash_engine.py、study/run_study.py、study/reconcile_results.py；独立核查入口study/reviewer_checks.py与study/reviewer_real_ledgers.py。已有结果不因后续继续研究而覆盖。新实验另存目录与新方案。
