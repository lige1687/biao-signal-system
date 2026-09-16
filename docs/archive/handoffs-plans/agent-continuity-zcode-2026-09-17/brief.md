# ZCode执行：Agent连续讨论现有补修收口

你是执行者，Codex是主控。请实际验证和必要修复，不只写建议。
工作区 /Users/yongbiaoli/lei-agent-main-consolidation-20260915；分支 codex/agent-experience-continuity-20260916；派发前HEAD=e461d838，工作区仅可能有本次派发文件。不能改运行目录，也不合main。

第一步读本仓AGENTS.md、CLAUDE.md及规定的四份策略文件：docs/trading-spec-v1.md、configs/rules.v1.yaml、.claude/skills/macd-reading/SKILL.md、docs/plan-sector-trend-page.md。改动属于解释交互层，不是技术判定层。道路/路牌/A-D/盈亏比≥3纪律保持，基本面消息只叙事，MACD只讲强度且补破线/均线方向，不造规则。

最新用户AGENTS补充优先于本开发仓旧文本：新过程文档去docs/archive/handoffs-plans，规范去docs/research，实验报告与raw旧路径禁止迁移。结案跑归置检查；本开发分支未同步治理，前次借运行仓scripts/check_repo_hygiene.py按开发根检查299项，不得为了全绿做整仓治理或隐瞒。无脚本时使用原检查函数指定本工作区只读检查并记录方式。报告要用人话，含一句话结论/ARCHIVE，registry增量watch，INDEX导航；不改其他报告裁决。

先读（无需重看全部历史）：
1. docs/experiments/controller-agent-continuity-cfix-review-2026-09-16.md（主控固定两项）
2. docs/experiments/agent-experience-continuity-cfix2-2026-09-17.md（现有补修，不能重复实现）
3. docs/experiments/raw/controller-agent-continuity-cfix-review-2026-09-16/{probe.py,atr-probe.mjs,background.json,atr.json}
4. git show e461d838；新增归置后的因子草案只读，不扩项。

固定架构：用现成message_id/question_id及冻结对象归属，未知不猜；讨论背景不是交易授权。ATR指标与真实证券身份按语境区分；概念说明与执行比较分开，不能只换草稿文本躲拦截。G1/G2以随附冻结契约为准。

源文件候选：src/lei_signal/api/routes/agent.py、copilot/resolve.py、web/src/utils/agentUx.ts、web/src/pages/AgentWorkspacePage.tsx、web/src/components/AgentConsole.tsx，相关测试。先验证，若现状已通过则只交证据，不为修改而修改。

建议验证：PYTHONPATH=src /opt/homebrew/bin/python3.11 -m pytest -q tests/unit/test_agent_continuity_20260916.py tests/unit/test_agent_continuity_routes_20260916.py；web npm run test:agent-ux、npm run build；若触及身份另跑ask_stability/incomplete_retry。保留原校验器12通过/1已知失败边界，不称全绿。浏览器仅受影响两入口ATR链，用临时库和桩模型；不调用真实模型、不读取或输出密钥，不占8000/5173运行端口，结束停自己的预览进程。

报告 docs/experiments/agent-continuity-zcode-closeout-2026-09-17.md；证据同名raw目录；新过程交接留docs/archive/handoffs-plans。报告逐G列实际证据、失败、未覆盖、源码指纹和精确测试命令；有新缺陷仅修范围内者。末尾给主控可合入提交列表与运行目录只读冲突列表，不部署。台账由主控更新，你不写共享升级库。收到结果后主控会独立复验，不能自行标接受。
