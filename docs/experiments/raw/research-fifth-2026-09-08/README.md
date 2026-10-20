# 第五批研究：近13年实际基金现金账户

对应主报告：`docs/experiments/dca-long-cash-study-closeout-2026-09-08.md`。
总交接：`docs/experiments/research-05-08-delivery-handoff-2026-09-08.md`。

- `sources/`：三只基金新增15份正式报告，复用4份；每份原文、指定页、下载来源和现金覆盖说明。部分华安报告为正式文档的公开镜像，真实域名保留。
- `study/protocol.md`与`protocol-lock.json`：在新结果前固定最多21次比较。
- `study/qualification.json`：19处PDF原句重新核对、日期覆盖、价格与已知分红/拆分一致性；明确完整份额/停牌事件服务未具备。
- `study/run-lock.json`：最终窗口、成交限制、事件、代码和方案指纹。
- `study/results/`：21账户逐日、逐笔、入金及事件，不删负结果。
- `study/reconciliation.json`：主研究重建21账户70,785日、27,311笔交易。
- `study/independent-long-ledgers-review.md`：另一研究者从原公告和原价重建最长3个账户；不冒称重新生成所有目标买量或21全独立复验。
- `evidence-cards.json`：原公共证据契约加研究扩展，生产未采纳。
- `okr-before/after.json`：06研究由推进中提交待验收；用户未确认完成。
- `registration.json`、`verification.json`、`final-manifest.json`：报告归档与封存检查。

失败与修正留痕：历史限制、迟复牌与坏数据检查先出现失败；独立审查又发现重复经济事件和不存在的日期未拦截，均在新增候选首次运行前修复。现旧12项+新8项通过，旧第四批12账户全部逐日及逐笔不变。

文件边界：只使用本批目录及新报告、学习实例和研究OKR更新；第四批185个封存文件及更早资料保持原样。来源仓库为`/Users/yongbiaoli/lei-signal-sync`，本次复用其此前冻结版本，不借当前并行代码冒充旧研究输入。

复现应先复制本目录及所引用的第三/第四批资料。`study/run_study.py`等会写研究输出，不在原封存目录直接重跑；核对本批应使用`verify_archive.py`只读检查。
