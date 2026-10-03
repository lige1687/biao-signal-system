# 经典因子增量：完成交接（2026-10-02）

## 结果与范围

用户要求深度探索已有经典因子对系统增量，制定计划并落地，指定Sol6.1可负责实现。限定任务已完成：库存/重复公式核对、旧预测零重训汇总、六ETF月频CH3同期解释、独立核数、学习内容和报告归档。科学结果见 `docs/experiments/classic-factor-increment-2026-10-02.md`；结论有条件，不是因子普遍有效或获准交易。

## 实际模型分工

- `classic_inventory`：gpt-6.1-sol / medium，完成只读库存。
- `classic_design`：gpt-6-astra / high，完成方法设计与运行后的关键风险只读复核。
- `classic_implementation`：gpt-6.1-sol / medium，写出20个合成测试与协议例子，19失败/1通过确认实现缺失后遇额度限制，中断；没有冒称由Sol完成实现。
- 主控沿用户“继续”授权，检查已有产物后补齐研究模块、CLI分支、合成验证、真实运行、独立数学核数、学习内容、归档及本轮目标记录。未为绕额度创建新聊天或购买额度。

## 文件与入口

- `src/lei_signal/research/factor_lab/classic_attribution.py`：本次限定研究模块，拒绝不匹配用途、月端、资料和代码身份；所有资格检查先于估计。
- `scripts/run_factor_lab.py --attribution-protocol`：显式同期解释分支，拒绝预测/交易用途及复用预测/自动登记标志。
- `tests/unit/test_classic_attribution.py`：20个可移植合成测试，不依赖机器桌面文件。
- 现有 `factor_lab/attribution.py` 属于基金账户解释，未修改；没有从归档raw脚本导入正式实现。
- `docs/research/classic-benchmarks-usage.md`：明确新入口和旧冻结规范指纹限制。
- `docs/literature-learning/classic-factor-usage-2026-10-02.md`：用户/AI使用卡；seed增加1份本地资料和2条内容，原classic-process路线7条变9条，原资料/条目保留。
- `web/src/pages/LearningLibraryPage.tsx`：补显式共享阅读样式及选中时阅读状态，修复窄窗口只显示选中卡片而正文隐藏；浏览器实测与构建通过。
- 主报告与书面复核均在实验库登记；原父目标 `okr-4f4157e2957e` 仅增加本轮成果记录，不替用户验收整个方向。

## 验收清单

冻结 `implementation-plan.md` 不事后打勾改指纹；本文件记录完成情况。计划7项均有产物：合成测试、两函数、CLI、协议冻结与两项运行、独立核数、报告/学习交付。

市场预算3/4次尝试（含旧合同在估计前拒绝）、资料3/6次请求（含2失败），合计6/10。E2为18次线性关系估计+6个均值，E1为0次；另有2次预定独立系数核算，没有参数搜索。合成测试不计市场尝试。

工程20项新测试通过；相关扩展78通过、1旧规范指纹拒绝，未放宽旧检查。独立核数初次在两次系数核算完成后因manifest字段差异失败，仅恢复资料读取及确定性算术，未重复拟合。最终学习服务、页面、链接、原内容保留、代码差异与仓库检查见raw下 `delivery-checks.json`。

## 接续规则

先读主报告、书面复核、`research-state.json` 与 `attempts.json`；这是已完成有限问题，不自动重跑。未检验独立新资料、完整账户或作者股票组合重建。以后明确新问题时读取当前规范，不能以本次资格文件替代新资料资格或放宽生产授权。当前工作树有大量其他任务改动，初始状态已保存，本轮未提交Git、未删数据、未修改仓库外文档。
