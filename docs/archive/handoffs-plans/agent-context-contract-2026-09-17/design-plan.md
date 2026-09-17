# 本人事实与讨论意图 Implementation Plan

**Goal:** 能讨论假设与别人，但不会把它们记为用户事实；概念解释不启动补测。
**Architecture:** 保留原始消息；先确定分句继承的主语与事实/假设范围，再产生带原文的字段更新事件；当前材料与历史恢复使用同一个应用函数。无法确定归属的内容继续作为问题讨论，不写入本人背景。
**Tech Stack:** Python纯函数、既有消息绑定、React工具函数、pytest与前端脚本；不引入模型调用。

用户2026-09-17“可以的，开干”批准前述设计并执行。策略层归属：讨论解释与资金背景，技术判定规则、资金纪律、真实成交确认不变。

## 选择与约束
继续补句子词表会重复返工；全量模型提取带来费用与不确定性。本期采用确定性、保守的事实事件：本人、肯定实际陈述才更新。没有主语的独立金额仍可在本轮问题中解析，但不自动长期继承；明确金额更正只有已有预算时才替换。本人主语在分句间继承；朋友/假设也继承，显式本人切换可改变主语，但不能自行消除假设范围。
预算/用途/持仓按原话顺序更新；否定用途清除用途；未知不覆盖。事实来源保留原文、消息绑定由既有question_id负责。没有精确对象或冲突绑定不继承。

## 执行项
- [x] 后台先写失败测试：朋友延续、假设延续、显式本人切换、纠正与未知、真实历史绑定；日志保存raw。
- [x] 新增纯分句范围模块；resolve新增事实事件提取与应用入口；route当前准备与历史使用同一入口。断言如 apply(parse('朋友操作了，已清仓')) 不改变holding。
- [x] 前端Sol仅agentUx与回归脚本及共享JSON；后台按共享例句保证概念不进backtest_request。两入口既有共享调用保持。
- [x] 运行新测试、50项连续讨论、相关resolve与身份测试、前端回归及build。无付费模型；归置基线单列。
- [x] 保存报告/登记/提交，同一开发分支。验收后再判断本地主分支合入条件；不修改运行仓、因子、真实交易库。

验证命令：PYTHONPATH=src /opt/homebrew/bin/python3.11 -m pytest -q tests/unit/test_agent_context_contract.py tests/unit/test_agent_continuity_20260916.py tests/unit/test_agent_continuity_routes_20260916.py；npm --prefix web run test:agent-ux；npm --prefix web run build。
