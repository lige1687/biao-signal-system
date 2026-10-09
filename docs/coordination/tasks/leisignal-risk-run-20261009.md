## 并发登记事实纠正，开写前重新核对

checked_coordination_sha=22762d6f031c98fd2ac03c89aa25ea499064d9f1；checked_at=2026-10-09T20:07:46.387237+08:00；已读该SHA的A记录 leisignal-risk-input-20261009（owner 01a1208c-8a1b-7b22-8802-1a5f23f57f5a，active只核输入）、自己的记录，以及9af57eb2以来仅A/B两个任务增量；COORDINATION和中控正文未变。C文件此SHA尚不存在。

首次登记期间共享远端引用由另一工作区fetch推进到58f74e60，首次记录将A文件写为不存在的说法失效；保留旧记录并以本段纠正，不用未经阅读的SHA冒充核验。当前A inputs/B implementation没有重叠，A manifest仍未交付，B仅准备人工演练。远端本段读回核同后开写。

---

# 月度风险对照：B 实现与唯一执行

- task-id：leisignal-risk-run-20261009；状态 active / preparing_only；负责人 B，会话 01a1208c-d559-72f0-ba6e-980a4337fa2c，本机 Mac。
- checked_coordination_sha=58f74e60fc3cfc8ab914fa73672e3ad3d21d7da8；checked_at=2026-10-09T20:07:03.803466+08:00。
- 已读 COORDINATION.md、research-dispatch-controller 最近交接/释放记录、risk-shape-information 当前段；本 task 与 A/C 的 task 文件在此 SHA 尚不存在，不能视作已接手或 inputs_ready。
- 冲突决定：旧中控已释放本批职责；B 只实现及运行，不覆盖旧 raw，不写 A inputs、C review、registry/INDEX/catalog。记录不是锁，未登记写者未知。
- 工作分支 codex/leisignal-risk-run-20261009；基线 a2f977455b5395f5a02de901d4b50075a615f8dd；独立工作区 /Users/yongbiaoli/.codex/worktrees/leisignal-risk-run-20261009/lei-signal-lab。目前无成果提交，不用基线冒充成果。
- 共用交接及唯一提案：docs/archive/handoffs-plans/research-dispatch-controller-2026-10-07/three-chat-handoff-2026-10-09.md、next-risk-comparison-2026-10-09.md。
- 问题/用途：月末过去63共同交易日分别计算原基础费 A_ALL、A_SMA/B0 完整账户日收益标准差比例，上限1，次月首次允许开盘调一次；510300 / 2026上半年 / 两参照×两费用，供 C 判断日波动是否相近，属于已见历史探索。
- 唯一写入：docs/experiments/raw/monthly-risk-comparison-2026-10-09/implementation/、自己的 docs/ops/work-progress/leisignal-risk-run-20261009.md、自己的本协调文件，以及核盘绑定的新外盘结果目录。
- 验证目标：人工资料的时点/63共同日/完整自然日日收益、100份整手、费用现金限制、分红应收到账、交易限制延迟/跨月替代/一次订单；源码输入合同预算绑定与一次许可；最终交 C 独审，不自我验收。
- 执行顺序：准备/人工演练 → A准确manifest绑定 → C代码独审 → 用户明确4路径授权 → 各一次真实执行 → C实际结果核验。
- 当前授权：仅准备与人工演练。4条新真实路径尚未批准，预算 permitted=0 / proposed=4 / attempted=0；原2路径已耗尽封存不可转借；原A重放/新信号标签/下载/拟合/扫描均0。
- 已检查：远端获取成功；独立干净工作区建立；桌面两源 SHA 与已确认指纹一致。尚未运行：新账户与C验收。
- 下一依赖：A的准确manifest与来源闭包；C审查确切代码/合成证据；用户批准这批额外4路径。不会用猜测输入代替A，不创建定时器，不依赖中控回调。
- 本轮增量：首次登记唯一B写者、分支、问题、范围及零真实预算。

<!-- lei-coordination-json:start -->
{
  "task_id": "leisignal-risk-run-20261009",
  "owner": "01a1208c-d559-72f0-ba6e-980a4337fa2c",
  "status": "active",
  "scope_released": false,
  "write_paths": [
    "docs/experiments/raw/monthly-risk-comparison-2026-10-09/implementation/",
    "docs/ops/work-progress/leisignal-risk-run-20261009.md",
    "docs/coordination/tasks/leisignal-risk-run-20261009.md"
  ],
  "dependencies": [],
  "dependency_notes": "A/C尚未登记；依赖其未来准确交付，不将未知状态写成ready。"
}
<!-- lei-coordination-json:end -->
