# S2 执行记录：隔离整合与采用包验证（2026-09-17）

执行者：ZCode（委派 job 1b20120c…，stage=S2）。主控材料：controller-S1-review.md（同目录）。

## 候选分支结构（codex/agent-runtime-adoption-20260917）

| 提交 | 内容 |
|---|---|
| 4d241978 | 主控 S1 复核（只含复核材料） |
| d6660f01 | **基线提交**：运行实态捕获（2026-09-17 11:44 快照）13 个文件——基金成交幂等（copilot 路由/trades/sqlite 031 迁移/client/CopilotCards/test_copilot_trades_dedup）+ 因子 evidence runner/stability 及 CLI 测试 + web 工作台页面与样式在制改动。拷贝前后逐文件 sha256 双核对；与 S1 审查快照零漂移 |
| 96a6bf55 | **Agent 增量提交**：S1 清单 24 项（与基线清楚分离） |

## 24 项采用的三类实施方式

1. **整文件替换 9 + 新增 10**：从 main@f8638b9f 提取，逐文件 sha256==main 核对。
   唯一路径适配：`test_agent_continuity_routes_20260916.py` 的
   `tests/000300.SS.bars.parquet` → `tests/fixtures/kline/000300.SS.bars.parquet`（治理后位置）。
2. **三方合并 2（base=运行提交态 cb71cad6，零冲突）**：
   - `copilot.py` = main 增量 + 运行基金成交幂等层（request_id 字段/409/幂等 docstring）。
     合并后与 main 的 diff 仅 17 行，全部为运行层；main 内容零丢失（grep 核对）。
   - `sqlite_store.py` = main 增量 + 031 迁移（含 executescript 中断重跑保护）。
     与 main 的 diff 仅 26 行，全部为运行层。
3. **语义缝合 3（base=cb71cad6，零冲突）**：
   - `AgentConsole.tsx`：main 的 failedRetryable/心跳去重/等待文案 + 运行的外部入口
     草稿注入（storeDraft/draftSeq）与普通文字买点。合并后 vs 运行实态：仅 main 增量，
     运行内容零丢失。
   - `AgentWorkspacePage.tsx`：main 的稳定性 + subjectLabel + 运行 UX 第二轮
     （看图按钮/价位区标签/AnswerText middle 插槽/closeResource）+ 21 行脏改层。
     ATR 执行拦截块（detectUnsupportedExitRequest/“这项比较暂未支持”）两侧同款收敛，合并后完整保留。
   - `test_agent_chat_e2e.py`：main 的 xfail(strict) 数值校验器缺口 + 断言锚点
     "AI 讲解暂时不可用" + 运行侧治理后夹具路径。

**排除项**（按主控裁决#1）：14 个运行领先文件与 4 个仅脏改文件不动；
`configs/dca_evidence.json` 保留运行版（工作区版本即运行版，未触碰）。

## 验证记录（详细数字见报告）

- 后端 pytest（/opt/homebrew/bin/python3.11，PYTHONPATH=src）：批次一 130 passed；
  批次二 140 passed + 1 failed（test_discussion_backtest_03b::test_s13——
  **在基线提交 d6660f01 上复跑同样失败**，属既有基线失败，按裁决不修；该测试会尝试
  真实 LLM 端点（404 放弃），为避免再次真实外呼后续批次跳过它）；
  e2e 14 passed + 1 xfailed（xfail 即 main 钉住的数值校验器缺口，strict=True 符合预期）；
  基线在制 factor CLI 16 passed；反向依赖（plans_actions/intraday_check）含在批次二。
- 前端：`npm run build`（tsc --noEmit + vite）通过，仅既有包体积提醒；
  6 个 agent 回归脚本（ux/workspace/prices/tasks/markdown/evidence-card）全部通过。
- ruff：采用集 Python 文件 35 项告警，与 main 同文件集合逐文件数量一致（全部既有，
  零新增；合并文件未引入新告警）。
- 真实路由冒烟（uvicorn 127.0.0.1:8141 + LEI_SQLITE_PATH 临时库 + 全部模型环境变量
  剥离→无模型降级直出）：降级直出/事实三轮/ATR 两轮共 5 场景，路由与临时库链路可用。
  注：pytest 用 TestClient 走同一真实路由栈，本人事实的细粒度语义
  （第三人/假设/更正/快照与历史一致）由 test_agent_context_contract 等 130 项覆盖。
- 浏览器整页检查：本会话浏览器后端不可用（browser control unavailable），
  **未执行**，如实记录；前端行为以 build + 6 个确定性回归脚本为证据。

## 采用包与演练（G3）

包：raw/agent-runtime-adoption-candidate-2026-09-17/adoption-package/
（manifest.tsv 24 行 before/after sha256 + after/ 全部候选文件 + before/ 全部运行实态
捕获 + apply.sh + revert.sh）。before 含 13 文件基线脏改（以 2026-09-17 11:44 捕获为准）。

演练（/private/tmp 独立副本，演练后已清理，日志在 raw/rehearsal/）：
- Act1 正确基线 apply → exit 0，24/24==after 逐哈希验证；
- Act2 agent.py 翻转 1 字节模拟漂移 → apply 拒绝，其余 23 目标逐一校验保持
  before/不存在（零部分写入）；
- Act3 revert → 14 个逐字节恢复 before、10 个精确删除；
- Act4 采用后追加本地改动 → revert 拒绝，改动原样保留（不覆盖之后的新改动）。

## 过程教训（供后续 agent 参考）

1. zsh 中 `path` 是绑定 PATH 的特殊数组，shell 循环变量禁用该名（S1 已踩）。
2. 本机环境 `echo '-'` 输出空串——哨兵用 `printf -- '-'` 或直接比较空串。
3. 手写 `../` 序列肉眼数错 4 次：脚本里路径上溯一律用 `while` 循环 `cd ..` 计数。
4. `read -r a b c` 对 4 字段 TSV 会把最后两个字段并进 c——列数必须与变量数一致。
5. python `pathlib.read_text()` 不带 encoding 参数会按 locale 读——重写含中文的
   文件必须显式 `encoding="utf-8"`，否则 mojibake 破坏脚本引号结构。
6. 演练必须以 python（csv 模块）组装副本——shell 的 IFS/read 组合在多轮排查中
   反复产生"随机缺文件"的假象，实为解析错误。

## 边界声明

来源仓库与运行仓库全程只读；未改运行代码、未重启服务、未写真实业务库；
未调用付费/真实模型（唯一一次真实外呼来自既有失败测试对 LLM 端点的 404 探测，
随后被跳过）。浏览器检查未执行（后端不可用），已用 build+确定性回归脚本与真实
HTTP 合成流替代并如实区分。

## 返修补记（S2 repair，主控复验 mixed 后）

主控独立复验 G3 未过（verdict=mixed），三项固定返修全部落实，**未改任何已通过
产品代码与运行目录**：

1. `apply.sh`/`revert.sh` 改为 `--target <绝对路径>` 必填（显式目标，打印解析路径、
   验证布局）；包位置与调用 cwd 不再影响目标。
2. 预校验扩为四重：manifest 结构（24 行/列数/op 枚举/哈希格式）、**全载荷双向哈希**
   （apply 验 after+before，revert 验 before+after）、必要依赖指纹、目标状态；
   写入失败不再 trap 删备份——KEEPDIR（备份+已写清单+生成的 restore-partial.sh）
   保留并打印可执行恢复指引；不宣称跨 24 文件原子事务。
3. 新增 `dependencies.tsv`：7 个只读前置指纹（trades.py/client.ts/CopilotCards.tsx/
   AnswerText.tsx/App.tsx 草稿 store/AgentMarkdown.tsx/agent-workspace.css，逐项
   理由），apply/revert 均校验，缺失/漂移拒绝；包不复制不覆盖。

十幕演练（/private/tmp 独立副本、进程级隔离、无网络、未对运行目录安装）：
保持四项（显式目标应用/漂移拒绝零写入/精确回退/回退后修改保护）+ 新增四类
（晚序 payload 损坏拒绝/before 损坏拒绝/写入失败恢复实测/依赖缺失与漂移拒绝），
日志在 raw/rehearsal/repair-act*.log，汇总见 raw/rehearsal/README-repair.md。

报告数字更正：后端通过项 300（130+140+14+16），初版误写 301；"每问省约 12 秒"
为来源侧旧测量、本次候选未重新计时。

返修过程新增教训：多轮修补脚本后演练副本必须重新组装（copytree 快照不会跟随
源变化）；shell 变量不跨工具调用保留，演练驱动改用 python 全程管理状态；
`rm -rf` 的变量兜底值绝不能指向系统目录。
