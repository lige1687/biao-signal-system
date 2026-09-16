# 第九批交付目录

日期：2026-09-08。两组入场纪律诊断、六个既有B事件的区间定义核查及全任务交接；不修改正式策略。

## 一句话结论（大白话）

普通突破从没有买入变成132次，说明此前主要被叠加的目标空间检查挡住；更多参与带来收益、跌幅和费用，不能据此取消纪律。B另需明确区间含义：横盘够久后新建的价格区间，可能只有一天。完整系统与未来验证仍未完成。

## 阅读入口

1. [本轮结果与适用限制](../../entry-discipline-and-b-zone-diagnosis-2026-09-08.md)
2. [全任务已交与未完成清单](../../research-local-phase-closeout-2026-09-08.md)
3. [运行前协议](protocol.md)及[协议指纹](protocol-lock.json)
4. [新账户汇总](account-results/summary.json)、[原配置逐表回归](account-results/original-regression.json)
5. [独立现金重建](reference-account-review/README.md)、[全部候选与最早退出检查](execution-checks.json)
6. [B六事件与原文来源](b-zone-semantics/README.md)、[引擎修正与Spark失败记录](reference-engine/README.md)
7. [学习内容接入交接](../../../literature-learning/research-followups-handoff-2026-09-08.md)、[原契约证据卡](evidence-cards.json)
8. [用户确认的K-baseline实际更新](okr-confirmed-update.json)

## 原始结果

`account-results/`只含两组新账户R0/R1及汇总。各组保存daily.csv、trades.csv、orders.json、events.json、roundtrips.json。1,742个候选继承第八批原始目标和拒绝状态，另附诊断身份。旧P0/P5/P6的输出只作内存回归比较，未覆盖原文件。

`reference-account-review/accepted/`是独立核算冻结的接受快照；核对8,398日、941成交、2,211订单、1,274事件、472持仓记录，其中469已结束、3个末尾未结束。所有金额误差低于预先约定的0.00001容差，最大约0.00000000103。两组在已知拆分日均没有持份，也没有卖后才除息的正应收实例；这类边界仍靠合成用例覆盖，不能冒称本次真实历史验证。

根的`verify_execution.py`不导入引擎，检查全部941成交、1,742原候选去向及472次持仓最早退出。`fill-checks.csv`、`order-checks.csv`、`position-checks.csv`逐项保存。

## 复现约定

`run_references.py`先验证第八批输入指纹和本次协议，再跑P0/P5/P6回归，随后跑R0/R1；拒绝覆盖已经存在的account-results。`verify_execution.py`做执行检查；`reference-account-review/verify_references.py`先冻结接受快照，再独立十进制核算；`check_summary_and_orders.py`核对汇总与订单。

如需复算，复制本批目录到新的隔离位置并明确依赖第八批所在位置，给新输出新目录，不删除或改写封存结果。代码中记录的源路径指向本次工作区，不承诺移动整个项目后不配置路径也能直接执行。禁止在旧原始目录重复写入。

## 失败、范围和状态

Spark首版通过自身测试但未通过独立测试，第二版在额度耗尽时仍未全部完成；审查者最后修复旧输出多余字段及来源身份。首版、二版、独立失败与最终测试均保存。独立汇总检查器首次把跌幅正负口径混用，修正检查器一处符号后通过，主账户未变。

B唯一替代仅检查六个旧日期，未生成新信号或计算收益。全任务清单是资料与交付覆盖盘点，不冒称对所有旧实验重新独立计算。OKR仅按本次已确认范围写入K-baseline进行中3/4，其他目标不随本批成绩改动。

## ARCHIVE

本轮限定的研究工作及交付已完成。最终检查见delivery-checks.json，封存内容与指纹见final-manifest.json；后续定义、工程接入、用户验收及未来观察仍是未完成事项。
