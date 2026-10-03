# 本轮入口：EMA持续性与相邻变色（2026-10-04）

先读 `docs/experiments/technical-persistence-and-color-transition-2026-10-04.md`，再读 brief.json → controller-review.json → 三份 qualification.json → 两份 core-01/contract.json → analysis.json。结论是EMA无稳定新增信息、相邻事件支持不足；非任务接管或原技术方向结束。

实际原始目标是从LEI原文拆出有金融语义、可计算的定义，先审来源/样本，再用不同方法及相同对象日期的增量验证；要看收益、风险、机会、反例和后期证据，不能以工程绿色替代有效。当前两对象固定@1.0.0；原文及公司资料不重写/外传，情绪宽度宏观账户不在范围。

## 可直接运行的最小复核

从本工作分支仓库根目录：

```sh
python3 -S docs/experiments/raw/technical-multimethod-2026-10-03/verify_saved.py --root . --results-only
```

只需本包 analysis.json、verify_saved.py、manifest.json，以及两目标 core-01 的 result.json/contract.json/receipt.json。无行情、无需Air、无需第三方包；预期退出0，报告两目标1268条保存预测、真实旧拟合8、此次新增拟合0及相同误差。**只证明保存结果身份和算术，不重新证明来源资格/公式或供应商许可**。不执行旧市场实验。

源码工程测试（需项目依赖，真实依赖版本在checks.json；未验证全新安装/Linux/Windows）：

```sh
PYTHONPATH=src pytest -q tests/unit/test_technical_persistence_information.py tests/unit/test_alphalens_component.py
```

主控实际12项通过；其中三个合成演练各2次人工模型计算，不是行情拟合。上游组件只加载固定原函数，没有安装完整Alphalens包。实际Python、numpy/pandas/scipy版本见checks.json。新第三方源保留Apache-2.0许可、版权及精确SHA，PROVENANCE记录来源。

## 研究冻结与旧结果

收益正式 freeze-02/risk正式freeze-01，core-01各4真实拟合；accepted-freeze-01/accepted-01仅发布not_supported和重汇总保存结果、各0新增真实拟合。第一次收益冻结因前缀检查失败，日志保留；没有运行真实模型。相邻事件draft被资格审查改为qualification_only，无事件专属冻结统计和结果比较。prepare.py拒绝覆盖已登记对象，不重复运行；analyze.py重新计算辅助描述会读取历史输入，保存核验不需它。

数据panel路径 `docs/experiments/raw/volume-information-2026-09-30/execution/panel.json`，1,582,974字节，SHA382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b；source-manifest精确SHA a0c3b15bc56ac34c4538ac9b11e505a83c0f8bed97175459d7eccb74c2b11c94。名义报价、公司行动PDF、策略原文、旧来源资格附件仍按原位置/指纹，只作来源索引，不随本包上传。到达与全部行动完整性未认证，再分发资格未确认；缺原件不能声称真实市场复现通过。local-only-artifacts.json列本轮没有交付的完整preflight/原始下载/本机核查资料。不要改路径适配而改原锁/封存记录。

## 接续、预算、协作

工作分支task/technical-factor-sequence-progress，基础ae175d3caea2a5bd301cba46c6d2927bf6a50c6f；准确本轮成果commit看本文件Git历史，协调记录同步后引用它。唯一跨任务入口coordination/lei的COORDINATION.md与docs/coordination/tasks/technical-factor-sequence.md；先fetch读取相关负责人和结论，不凭本文件抢研究范围。

真实拟合8/12、行情/付费0、公开源6/6；旧预算不归零。0和1、灰色未知、背景外和未成熟都有记录。封存20/60旧颜色、Q01、斜率、双均线及本轮EMA，禁止重跑追正。未来观察缺取得时间/合法新输入，最早起点未定；相邻变色须新合格资料和成熟支持才重开。D1/D2/D5实例及缺口在完整报告 workflow-fusion-2026-10-04 小节，未接管未来SMA20/宽度的暂停任务。

本轮进程已结束，没有迁移进程、checkpoint、登录态或后台保证。原负责人持续负责；没有接管动作。新AI只能独立核保存结果或经最新协调确认后的不重叠新问题，不与原执行者同时写同一实验。
