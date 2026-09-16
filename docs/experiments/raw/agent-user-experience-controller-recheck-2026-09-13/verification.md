# 二轮主控运行记录

- 22 passed in 72.12s：PYTHONPATH=src python3.11 -m pytest tests/unit/test_agent_ux_phase1.py tests/unit/test_agent_chat.py tests/unit/test_agent_stream.py tests/unit/test_chat_discussion.py -q；开发副本执行，exit 0。
- npm run test:agent-ux && npm run test:agent-tasks && npm run test:evidence-card && npm run build：exit 0。740 modules，built in 2.59s；SSR useLayoutEffect 提示与既有chunk大小提示保留。
- actual-shared-probes.mjs：7个行为PASS，源码检查PASS。基于执行者等价探针，主控以AST提取的实际requestBacktestTask/stableClientId取代内联替身；不冒充全后端验证。
- exit-wording.py：脚本exit 0，行为对照FAIL，四行里两行只跌破一条与“任一跌破”不符。
- CUA真实浏览器复验：用前轮build-browser.cjs重建当前面板至/tmp/lei-ux-controller-browser-20260913；本机5294。选择B→B专用退出→A，摘要恢复退出1，点击创建后真实组件onSubmit输出 {"module":"A","exit":"a6_1_costbasis"}。PASS。该页面无业务后端与模型，未提交真实任务。
- 场景8：读取执行者scene8-history-restore.png，保存草稿可用、确认生效禁用，无plan_id。仅接受草稿历史恢复，保存/确认待证据。
