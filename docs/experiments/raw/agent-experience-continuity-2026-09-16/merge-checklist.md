# 合入清单（主控复验用，2026-09-16）

分支 `codex/agent-experience-continuity-20260916`（基线 main@6c4f233b），3 个提交：

| 提交 | 内容 | 文件 |
|---|---|---|
| 6292b527 | 冻结案例+修前基线 | docs/experiments/raw/agent-experience-continuity-2026-09-16/（inputs-and-acceptance、baseline-degraded.json、baseline-notes.md、screens/before-*、serve_iso.py、run_cases.py、ui_harness.py） |
| d465b558 | 连续讨论修复+因子交接草案+提速采用候选 | src/lei_signal/copilot/resolve.py、src/lei_signal/api/routes/agent.py、src/lei_signal/api/routes/copilot.py、src/lei_signal/plans/llm.py、tests/unit/test_agent_continuity_20260916.py（新）、docs/factor-evidence-handoff-draft-2026-09-16.md（新）、raw/speedup-adoption-candidate.md |
| b1dc3270 | 两个既有 e2e 断言修复 | tests/integration/test_agent_chat_e2e.py（xfail(strict) + 断言锚点更新） |
| （待提交） | 报告+登记+改后证据 | docs/experiments/agent-experience-continuity-2026-09-16.md、registry.json、INDEX.md、raw/（after-degraded.json、real-chain、case9c、screens/after-*、stub_llm.py、ui_case9.py、merge-checklist.md） |

## 代码改动面（src/ 共 4 文件，全部解释/交互层）

- `copilot/resolve.py`：资金口语主题与中文数字预算、detect_stance（持仓语境，逐条不继承）。
- `api/routes/copilot.py`：对象已核实时不再追问补测标的；科创板泛指澄清 gate 修复。
- `api/routes/agent.py`：确定性作答（板块→产品关系/与刚才比较）两路径接入；立场与主题进材料；降级直出持仓/资金分支；日期口径。
- `plans/llm.py`：DISCUSSION_SYSTEM_PROMPT 五条规则（追问不重复四段/截至X日不称收盘/持仓语境/资金纪律/板块→产品诚实）。

不改：判定层规则、资金纪律、模型配置、前端代码、数据库 schema（零 DDL）。

## 复验入口

- 报告：docs/experiments/agent-experience-continuity-2026-09-16.md（一句话结论/逐项/对照/耗时/未覆盖/ARCHIVE）。
- 证据：docs/experiments/raw/agent-experience-continuity-2026-09-16/（真实原文 real-chain-2026-09-16.json、修前修后 JSON 与截图、全周期 9c、服务器日志）。
- 回归：新 17 项 + 73 + 30 项 + e2e 12过1xfail(strict) + 前端 build，全绿（命令见报告 §5）。
- 单列待裁：数值校验器百分比派生放行过宽（报告 §7.1）；factorsApi.lab 悬空引用（因子草案 §6.4）。

## 边界

未部署、未推送远端、未改运行目录与真实业务库、未动因子工作文件；合并与否由主控决定，合并后按 speedup-adoption-candidate.md 另行定向处理运行目录（两批干净文件+两文件人工定向）。
