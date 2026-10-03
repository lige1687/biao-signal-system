# 保存结果的各ETF历史平均对照接入计划

> 执行方式已由用户授权继续；codex-delegate单实现者，主控独立验收。本计划遵循writing-plans的分步检查，不再向用户重复询问是否执行。

**Goal:** 让后续研究从已有保存结果核对一个合理简单对手，防止仅战胜弱模型就误认为有增量。
**Architecture:** 新增纯核数模块与现有CLI的独立分支，调用原check_publication确认来源，再计算逐ETF成熟训练均值；输出新目录辅助报告。原workflow及研究合同不变，不做第二套准入/账本。
**Tech Stack:** Python 3.11、现有NumPy/Pandas/pytest；不安装依赖。

## Global Constraints

工作树为本task/classic-factor-progress隔离目录，基线cf8d630954257fff441d55a974f8a0fe95eca443。只写executor-contract.json四源码/测试路径及自己的回执/测试临时目录，不提交、推送或编辑主工作区。策略原文、旧报告/raw、workflow.py/evaluation/inputs/question_contract、定义及页面只读。主控负责说明/阶段文档/发布。
研究层依据：经典方法保留简单对照，2026-10-03风险报告显示各ETF历史平均比候选强，现有B0只共同均值。原审计已证明B0/B1/B2保护存在，不重复实现。旧风险/经典研究封存，0新市场拟合/行情请求/付费。
两策略SHA：df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20；85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903。

## 设计与接口

新增`src/lei_signal/research/factor_lab/baseline_review.py`：
- `build_baseline_review(contract, observations, predictions) -> dict`：纯数值函数，无IO/拟合。仅连续目标forward_return/mae/max_drawdown/forward_volatility及既有equal_asset/equal_date权重；不支持事件概率、状态描述或账户。输入未经正式来源核查时明确numeric_inputs_only。
- `review_saved_run(run_dir, output_dir, *, root=None) -> dict`：先检查目标、路径、输出不存在及必要原件齐全，再调用既有workflow.check_publication(run_dir,root)，不能用自写verified标志替代。复用读取contract/preflight/result。核查期间不拟合、不调用execute_workflow、不登记报告、不改journal/原报告。原来源缺失/旧源码不匹配即失败，不能在原锁补新SHA以通过。
- 输出新目录`review.json`和`report.md`，报告以人话说明每个对手、相同对象日期权重、数值局部改善和不确定边界；源码/输入文件SHA、原run_id、原结论、data_mode、0新增拟合、辅助诊断标识。不要复制全部逐行数据。既有登记状态不变。

计算定义（不是伪代码中的自由参数）：
```python
for index, fold in enumerate(contract['split']['folds']):
    train = [r for r in observations if r['eligible'] and r['date'] <= fold['train_end'] and r['label_end'] < fold['eval_start']]
    means = {a: sum(r['y'] for r in train if r['asset'] == a) / sum(r['asset'] == a for r in train) for a in {r['asset'] for r in train}}
    # 每条已保存预测只绑定自身fold和asset，不借评价结果估计均值。
    # 评价中有asset不在means内：明确失败，不能缩池或退回总体均值。
```
所有数值有限，ID/asset/date唯一，prediction身份/target/label_end与eligible observation逐项一致；fold日期和contained规则均沿原合同。必须完整覆盖原来实际可评价行，不能仅对容易的配对算数；无预测则报告资料不足，不计算nan。较晚才能知道的train标签不能混入。
每种方法在同一预测行计算均方错误及开方错误；权重调用既有规则（各ETF总权相同，或各日期总权相同）。各ETF自己的均值在本ETF的成熟训练记录内等权，定义写清不冒充全库统一最优基准。保留B0/B1/B2原值并加入asset_training_mean；输出B2相对每个对手的差额及百分比（对手错误0时百分比为null）。可给逐ETF、逐年摘要；仅点估计辅助，不宣称稳定、因果或交易采用。负结果正常成功。

`scripts/run_factor_lab.py`：互斥模式增加`--review-baselines SAVED_RUN`；使用既有`--out`。增加只在本模式可用的`--review-root ROOT`用于复现临时研究树，默认项目根。拒绝与--register-report/--reuse-predictions混用，其他模式若带--review-root也拒绝。只读失败退出3、合法诊断（含负结果）退出0，错误写stderr；不覆盖原目录、不制造通过。

## 任务1：核心比较与反例

- [ ] 先写test_classic_baseline_review.py，用手算固定两ETF：A较早目标0、B较早目标10；评价真值分别0/10；B0=5、B1=4/6、B2=2/8，得到MSE25/16/4/0，B2胜B1但输asset_training_mean。
- [ ] 运行红测并记录（无行情）。实现纯函数；测试日期成熟边界、修改评价y不改变训练均值、某ETF无成熟训练行、缺行/重复ID/目标不匹配、非有限数、两种权重、零分母、不支持目标。
- [ ] 所有拟合函数mock为抛错，辅助函数仍通过；没有新增拟合。

## 任务2：真实入口验证与原件不变

- [ ] 新test_classic_baseline_review_entry.py用现有test_research_workflow_entry.setup_case/frozen_path构造临时人工研究。只执行必要一次原流程以产生真的receipt；核心研究步骤属于合成工程检查，记录人工拟合数。不可伪造receipt证明集成通过。
- [ ] 用subprocess真实调用CLI及--review-root生成独立辅助目录；核表格和模型值；运行前后原目录、原journal/registry文件SHA保持。
- [ ] 篡改结果/漏必要原件、输出已存在、输出位于原运行目录内、禁止参数混用返回非0，不能删除旧目录绕过。保留失败在测试专属临时目录。
- [ ] 运行新增两文件及必要既有相关回归；不运行整个库。命令示例：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/unit/test_classic_baseline_review.py tests/integration/test_classic_baseline_review_entry.py -p no:cacheprovider --basetemp docs/experiments/raw/classic-baseline-adoption-2026-10-03/executor-tests/round-01`，每次新round，禁止复用会删除旧目录的basetemp。

## 主控验收与提交

主控另手算固定反例、审查入口调用/源码差异、核SHA和测试回执；只在有具体风险时补一项必要核对，不重复绿测。更新已有workflow用法、自己进度与协调记录，保留原封存预算和失败。代码独立分支提交推送，不合main、不部署；用户已授权该范围同步。

## 当前进度

范围与设计已登记85a5a28aafcfa0b25f51efedf9590cca47c51766并读回。实现尚未派发；主控收到执行回执后记录实际检查，不将此清单视为运行状态。

## 实施中明确的验收修订（保留原计划）

- 第二批真实入口在原定义库的lifecycle附件处提前停止；发布树49个缺失basis中48未在HEAD交付，不伪造或复制未授权原件。旧A01/A02两项归档回归也缺原件，保留未验证。新入口改用独立synthetic/test ID的最小合成定义目录，仍通过完整原schema、冻结、执行与出版检查；测试目录不冒充真实A01资格。该改动仅限新测试输入，不改正式定义/流程。
- wrapper先确认已有journal，避免原锁函数在缺账本时创建空文件；读取前后核原5文件、journal、registry、实际输入指纹。对核查中变化拒绝输出。
- --review-root不仅核目标文件，还核原CODE_PATHS与当前导入实现的字节一致；当前代码不得套旧目录指纹通过。
- 这项补充诊断的新比较不倒填原预注册，不升级原结论。公开旧研究可复现缺口继续存在，学习页面不实施。

## 实际收尾（2026-10-03 12:56:36 UTC；UTC，用户时区Asia/Shanghai）

四文件实现由Sol6.1 medium完成，最终36 passed / 2 deselected；两项旧归档测试缺原件，不假称全库通过。主控独立两种权重算例、真实保存结果重核及原件指纹检查通过，新增模型拟合0。实际CLI由执行者运行通过；主控新增CLI输出因本地ENOSPC未执行，改为只读独立核数，记录见controller/acceptance.json。上方“尚未派发”是计划写成时状态，已被本段替代。

本地Git新提交受磁盘写入失败阻断；获准小代码/文档使用GitHub API在现有任务分支原HEAD上原子追加。远端与本地HEAD暂时不同，不得reset或切换脏工作区。准确同步SHA由协调记录和本提交路径历史定位。未清理任何资料、未扩大研究预算、未实现学习页。

### 容量恢复后的最终验收

可用空间随后从约108MiB恢复到1.1GiB，原因未确认、本任务没有删除文件。小文件写入恢复，补做唯一一次主控真实CLI验收exit0、0新增拟合、原件SHA不变。拟议GitHub tree/ref直接提交并未执行，改回本地准确路径提交和普通push；上段阻塞/替代计划是故障当时状态。无需重跑绿色模型测试。
