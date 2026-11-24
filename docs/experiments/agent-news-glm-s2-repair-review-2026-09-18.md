# Agent 消息可靠性：最后一次 GLM 返修复核与 GPT 接管评审

## 一句话结论（大白话）

正式公告消失、历史回答丢消息卡等问题已在本地反例中修正，138 项测试通过；但“只查一个来源失败却说其他来源正常”和“空来源参数退回全源”仍可复现。测试还尝试访问真实库和网络，本次均被主控保护拦住，因此目前不能验收或上线。现按用户新指定的编排 skill 引入 GPT 独立评审；原 ZCode 返修次数不清零。

## 任务与边界

用户要求 `lei-gpt-zcode-orchestrato` 完成剩余工作，安装后的实际名称为 `lei-gpt-zcode-orchestrator`，后续又明确“继续用吧可以开整了”。当前只接续消息叙事层工程，不改交易规则、技术判断、阈值、信号排序，不部署、不恢复定时采集、不写生产库、不调用产品模型。

原合同：`docs/archive/handoffs-plans/2026-09-17-agent-news-glm-contract.json`；原复核：`docs/experiments/agent-news-glm-s2-controller-review-2026-09-18.md`。ZCode job `a5ead433-7197-4124-8485-0d26667ff286`，S2 execution 2 repair；GLM 本 job 1/1、加 Ark 全任务累计3/3已使用。本次只读验收及 GPT 评审，不追加派发，不重置合同。

## 本地独立证据（尚非最终验收）

- 主控在 W 重跑原十个后端文件，138 passed / 270.06s。额外保护拒绝全部 socket 连接、拒绝临时目录外 SQLite：记录到 66 次本地代理连接尝试和 11 次 `/Users/yongbiaoli/.lei_signal_lab/lab.db` 打开尝试，均在执行前被拒绝。不能据此说原测试天然隔离，也不把代理尝试冒充已发出的外部请求。
- 前端 evidence-card、news-context、agent-workspace、agent-ux、agent-markdown 与构建通过；保留包体积及 SSR 既有提示。
- 独立原反例复跑：四条普通消息加未评分官方公告，资料块保留全部五条；模型材料保留原文来源；Ops 未评分保持 null；真实流式 replay 出口保留消息快照。来源拼错、已禁用单源及正常单源状态的原反例也得到改正。
- `chat_identity.py` 增量仅透传已保存的 news_context，加注释；不改变请求身份与事务判定。属于修正历史快照所需最小适配，可由主控接受，但不能据此扩展会话逻辑。
- 交付清单 after 哈希全部与当前文件匹配。主控未重跑执行者的 UI 脚本，六张截图和14项 UI结果暂属执行者证据，独立页面验证尚待进行。

## 尚未解决的两处功能反例

1. `scripts/precompute_newsfeed.py`：`--only-sources ''` 仍通过 `if args.only_sources else None` 变成默认全源。主控替换真实采集为记录参数的桩函数，确认 exit 0 且收到 None。要求显式空参数在任何采集前失败，只有参数未提供才代表默认全源。
2. `health.py`：只选 Fed，采集响应含无效条目时，管线得到 partial；health 文案仍是“部分来源失败：fed；其余来源正常”。本次事实上只有 Fed 被尝试，而且未成功；其他来源未检查。要求所有 scoped 状态都保留范围，不能只修成功分支。

两者均为 R7 原要求内残留，不是新增功能。独立输出：`docs/experiments/raw/agent-news-glm-s2-review-2026-09-18/repair-review/scope-edge-results.json`。

## 执行边界与材料的待核事项

- 执行者承认调试时曾利用残留环境变量向真实模型端点发出一次请求（404）；原“真实产品模型调用0”是硬边界，这不能当作允许的公开资讯 HTTP 预算消耗而冲销。没有成功输出不等于没有调用尝试。主控未读取或复制凭据。
- 执行者承认调试脚本曾读取真实 lab.db。暂不能仅凭其“写入0”证明无初始化/其他副作用；主控本次通过拒绝真实库打开避免再发生。需限定可证明的事实，不夸大损害也不承诺从未触及。
- 恢复手册仍将真实库第一条命令写成 `--no-push`（会评分），与“恢复第一步仅采集”总体要求容易混淆；零模型/禁推送顺序应明确。手册中 git apply --3way 会涉及索引，当前禁止暂存/合并，不能直接照做；生产采用本就未授权。
- 原报告有初轮与返修内容并存，前半仍写后端截3条/has_source，后半才修正；最终对外说明需明确历史与当前。归档证据需核对是否覆盖初轮包，不凭执行者一句“未覆盖”认定。

## 给 GPT 的评审问题

请独立读取冻结合同、本报告、旧复核报告、原始反例输出，以及当前源码快照清单 `docs/experiments/raw/agent-news-glm-s2-review-2026-09-18/repair-review/source-snapshot-manifest.json`。快照只为连接器可读，不是运行仓已采用；全部来自 W，哈希可核。不要读凭据、真实数据库或无关任务；不要依据运行仓旧代码推断 W 已修复。

请判断：哪些是实际阻塞，最小纠正是什么；两处机械修正及测试隔离能否在已有授权下由 Codex 完成，还是原三次返修上限要求先停止；如仍建议 ZCode，必须说明预算已用尽，不能推荐新建 job 绕过。请区分采集失败信息、执行越界记录、可证明的后果及生产授权。提出必要验收反例，不扩新架构或策略研究。

## 2026-09-19 凌晨 · GPT-6 Pro 终审结论与阻塞项闭环（终章）

- **终审全文**：`raw/agent-news-glm-s2-review-2026-09-18/controller-scope-fix/gpt-final-review.md`（通道说明：连接器隧道失效期间降级为项目内聊天纯文本投递材料，模型 6 Pro）。
- **裁决**：本地功能验收 **PASS**（两处主控修正被接受、无新问题、144 项测试与程序合规性均认可）；主仓采用暂缓，仅两个最小阻塞项。
- **阻塞项1（UI 独立验证）已闭环**：主控亲自复跑执行者的页面验证脚本，15/15 全过（全局/单ETF/无模型/历史恢复四路径 + 桌面/窄屏），证据在 `controller-scope-fix/ui-independent-verify/`（含主控运行截图与第一次原生库偶发崩溃的如实记录）。
- **阻塞项2（越界事件归档）已闭环**：`controller-scope-fix/boundary-events-2026-09-18.md`（事件记录+影响分析+待用户签署的风险接受声明）。
- **当前状态**：两个阻塞项均已关闭，「本地验收通过、待用户批准采用」条件成立；采用与否、何时采用由用户决定。生产未部署、消息未恢复、推送未启用。

## 当前状态（历史，2026-09-18 晚）

本地复核未通过；GPT 接管评审进行中；未开始新的业务修改或派发。待 GPT 有效回复后，主控逐项核对，不凭外部评审自行创造权限。生产未采用，消息未恢复。

## 2026-09-18 晚·主控直接修正记录（ZCode 新主控接手后补充）

新主控（ZCode/GLM-5.3）按用户指令接管：返修额度 3/3 已用尽，不追加派发；两处残留属主控能直接修的小遗漏，经用户明确授权（「主控能直接修的小遗漏就修并留证据」）由主控直接修正，未新占返修额度、未新建 job、未越冻结范围。逐项状态：

1. **`--only-sources ''` 退回全源**：已修。`scripts/precompute_newsfeed.py` 改为只有「未提供参数」才代表默认全源（`args.only_sources is None` 判定），显式空值/空白逗号列表在采集前报参数错误退出（exit 2，管线零调用）；未知源族仍由 pipeline 校验兜底。新 CLI 回归测试 4 项（`tests/unit/test_newsfeed_cli.py`）。
2. **定向 partial 误称其余来源正常**：已修。`health.py` partial 分支按 `stats.scope` 保留范围说明——「（本次范围仅：美联储官方公告）…其他来源未核实，不代表整套资料状态」；无 scope 的全量 partial 保持原口径（有对照测试防误伤）。新增回归测试 2 项。
3. **测试与证据**：修复前/后主控探针输出、带保护的全量测试留档在 `raw/agent-news-glm-s2-review-2026-09-18/controller-scope-fix/`（probe_scope_edge.py、probe-scope-edge-before.json / -after.json、pytest_guard_zcode.py、pytest-guarded-controller-fix.txt）。带网络/真实库拦截保护重跑后端 11 个测试文件：**144 passed（原 138 + 新增 6）**。
4. **文档同步**（W 内）：S2 报告头部加「主控更正」段并说明初轮历史与现行为分界；恢复手册 §5 拆开「真实库第一条命令」（改 `--no-llm --no-push` 仅采集，评分命令单独标注另批）、§2 注明 `git apply --3way` 会写索引及无索引替代、§3 预期更新为 144；W 登记簿 S2 verdict 由 passed 改为 **mixed**、INDEX 同步。
5. **初轮归档覆盖核查**（上节待核项）：W 内初轮 `changed-files.json`/`implementation.patch`/`new-files.tar.gz` 确被返修版覆盖，但主控此前已把完整初轮快照与 diff 另存于 R `raw/agent-news-glm-s2-review-2026-09-18/initial-snapshot/`（含 executor-raw 与逐文件哈希）与 `full-initial.patch`，失败证据未丢失。
6. **仍未解决、留待终审决策**：执行者调试期曾以残留环境变量向真实模型端点发过一次请求（404）及读取真实 lab.db 的越界记录（无法证明零副作用）；UI 六张截图与 14 项页面结果仍是执行者证据，主控未独立复跑页面验证。这两项不是本轮修正能消化的，交 GPT 终审定处理方式。
