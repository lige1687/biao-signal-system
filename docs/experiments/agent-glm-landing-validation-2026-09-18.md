# GLM 名称绑定修复落地验证（S2）：运行差异协调与两入口核验

## 一句话结论（大白话）

S1 的名称绑定修复已经打包成一份可直接核对的采用清单（25 个文件，比上一版
多 1 个 `subjects.py`、并把清单里 agent.py 换成 S1 修好的版本），在完全复刻
运行目录状态的独立副本上演练：正常采用 25/25 逐哈希正确、完整回退字节级
还原、六种破坏情况（目标漂移、依赖漂移/缺失、包损坏、重复采用、采用后编辑）
全部拒绝、中断恢复六场景全过；随后用本机 Chrome 真实打开工作台和控制台
两个入口，确认"先问通信ETF再问沪深300/上证指数"在页面上真正随对象切换、
追问正确继承、新对象没行情时不拿旧卡充数。全程零联网、零真实库接触。
**尚未采用到运行系统**——采用与否由主控决定。

## 服务于策略体系的哪一层

解释展示层（同 S1）：讨论对象、资料卡、失效位必须属于用户实际问的标的。
不改交易定义、阈值、判定；不新增部署框架（沿用已验收的采用/回退/恢复工具，
只做清单同步与一处窗口修复）。

## 运行实态复核（只读，不沿用旧 HEAD 假装现状）

- 运行目录 HEAD 重核：`7f8c38c3`（与采集时一致）；在制改动 26 个文件
  **全部在 docs/scripts 层（因子文档、消息面/宽度过程稿等），src/ 与 web/
  零脏改**——采用面即 HEAD 实态。来源 main 目录 `f8638b9f` 不变。
- 三方指纹复算（旧包 before/after × 运行现状 × 本分支现状）：
  - 11 个 replace 行运行态未漂移（仍等于旧 before 指纹）；
  - `agent.py` 运行态未漂移，但其"after 载荷"须更新为 S1 修好的版本
    （旧包载荷是修复前的）；
  - 10 个 add 行运行目录确实不存在（absent 即 add 的正确前置态）；
  - 7 个依赖指纹在运行目录全部仍匹配；
  - **`src/lei_signal/copilot/subjects.py` 是 S1 新增受影响文件**：新增为
    replace 行（before=运行现状指纹，after=分支 HEAD 指纹，二者差异恰为
    S1 的 9 行改动；已验证运行文件与分支 71070885 版逐字节一致，即 S1
    是在同一基线上做的最小修改）。
- **新清单按实际内容为 25 行，不硬凑 24**；依赖表随真实清单同步为 8 行
  （见下）。数量校验脚本 24→25 同步（apply.sh / revert.sh 行数断言与文案）。

## 采用包（新 raw，旧包与旧失败证据全部保留未动）

位置：`docs/experiments/raw/agent-glm-landing-validation-2026-09-18/adoption-package/`
（由已验收的 `agent-runtime-adoption-candidate-2026-09-17` 包复制派生）。

- manifest 25 行（24 原项 + `copilot/subjects.py`），全载荷双向 sha256 校验通过；
- dependencies 8 行：原 7 项（trades.py 幂等 API、client.ts、CopilotCards、
  AnswerText middle 插槽、App.tsx store、AgentMarkdown bpLocatable、
  agent-workspace.css）+ **新增 `configs/rules.v2.yaml`**——演练实测发现
  目标缺规则账本时每个解析对象分析失败退全局（resolved=None），该文件是
  候选行为的硬依赖，且运行与分支当前指纹一致；
- apply.sh / revert.sh：仅同步行数校验与文案；recovery.py：一处窗口修复（见下）。

### 中断窗口最小修复（本轮唯一工具改动，冻结 G2 范围内）

原工具存在"**文件已重命名、恢复计划尚未记账**"的中断窗口：若在 `mv` 之后、
恢复计划写入之前被打断，该文件不在恢复材料里，部分恢复会漏掉它。修复：
apply/revert 写阶段改为"**先记账恢复计划、后原子重命名**"，配 recovery.py
对"已记账但尚未重命名"的中断态做幂等跳过（目标本就在恢复目标态）；其余
拒绝语义不变（后续编辑、备份损坏仍整次拒绝且零写入）。逐文件恢复语义，
**不声称全包原子**（脚本注释保持原声明）。旧包演练证据整体留档于
`rehearsal-v1-pre-windowfix/`，未覆盖。

## 演练结果（隔离副本，从运行目录只读拷出；19/19 通过）

`rehearse_landing_package.sh` 逐幕：

| 幕 | 结果 |
|---|---|
| 正常采用 | 25/25 逐哈希正确；**S1 复现脚本原字节副本对准已采用树跑 fixed 模式全部通过** |
| 重复采用 / 目标漂移 / 依赖漂移 / 依赖缺失 / 包损坏 / 采用后编辑回退 | 全部拒绝，零写入 |
| 完整回退 | 25/25，回退后与运行目录逐文件字节一致（0 差异） |
| 六个中断恢复场景（沿用已验收 recovery_probe，指向新包） | 全过 |
| **重命名窗口探针**（新 `recovery_window_probe.py`：apply 记账未重命名、同态+后续编辑、revert 记账未重命名） | 4 项检查全过：未重命名行被正确跳过、其余文件还原、后续编辑整次拒绝且目标零写入 |
| 前端（已应用树） | `npm run build` 通过 + 6 个 agent 回归脚本（agent-ux/agent-workspace/agent-prices/agent-markdown/evidence-card/agent-tasks）全过 |

## 两入口真实浏览器核验（本机 Chrome，非 HTTP 冒充）

隔离设置：后端为**已应用树**（browser-target），uvicorn 只绑 127.0.0.1:18765，
进程级审计护栏（禁 DNS/外连、沙箱外写入、真实 .env/业务库、非临时 SQLite）；
vite 前端 18766；临时库 + 合成行情 + 双路模型桩；上证指数 000001.SS 刻意
无行情用于"缺数据"腿。检查脚本 `browser/check_two_entries.py`，**7/7 通过**：

- 工作台 `/agent`：问 515880 → 快捷卡"通信ETF"；再问"沪深300…" → 页面回答、
  快捷卡、依据卡、右侧图表、当前讨论芯片**全部切到 沪深300（000300.SS）**；
  追问"那失效位呢" → 芯片与卡片正确继承沪深300；
- 控制台（顶栏"AI 助手"）：问 515880 → 通信ETF 卡；问"上证指数…"（无行情）
  → **无上证指数卡、无 000001.SS、不附旧通信ETF 新卡**（"上证指数"仅出现在
  用户问题回显中 1 次）；问"000300.SS" → 沪深300 卡（代码切换）。
- 截图 6 张存 `browser/*.png`（ws-step1..3、console-step1..3）。

### 重要发现（如实披露，S1 raw 不覆盖）

1. **S1 复现脚本的 SQLite 护栏存在 URI 漏报**：产品代码
   `copilot/breadth.py::us_breadth`（美股宽度叙事层）每轮标的讨论都会以
   `file:…?mode=ro` 只读打开 `~/.lei_signal_lab/lab.db`（生产环境本就读运行库
   自身数据）。S1 护栏把该 URI 字符串当普通路径解析，拼上 cwd 后恰好落进
   允许目录而静默放行——即 **S1 报告的"非法 SQLite=0"实际漏报了这次只读
   打开**（真实库未被写入，数据只读性质未变，但"零接触"表述不成立）。
   本轮浏览器护栏因 cwd 不同正确拦截到 5 次并暴露此问题。处置：启动器
   护栏改为 URI 感知（剥前缀与查询串再核对），并在隔离桩里直接替换
   `us_breadth/us_breadth_cn`，重跑后**四类计数真正全零**。S1 raw 与脚本
   按规约未改，本段为该证据的边界更正。
2. **`configs/rules.v2.yaml` 缺失会让解析对象全部退全局**（演练实测），
   已转为第 8 项依赖指纹，采用前置检查会拒绝缺账本的目标。
3. 与前轮区分：上一轮 `test_s13` 外呼真实 API 得 404，**不属于合格零网络
   测试**；本轮浏览器护栏为进程级审计钩子、四类计数全零、服务端零错误，
   二者口径不同，不得混用。

## 限制与边界

- **尚未实际合入**：全部改动在本任务分支与 raw 工具/证据，运行目录、服务、
  main、真实数据库零写入；实际采用由主控执行（apply.sh --target 运行目录
  即可，回退用 revert.sh --target）。
- 真实模型正文质量未测（模型桩固定回复）；浏览器为 headless Chrome，
  截图与 DOM 断言为证，未覆盖移动端与中断恢复的页面表现。
- 中断恢复为逐文件语义：部分恢复能还原已写入文件并保护其后编辑，
  但不是全包原子事务（工具注释与脚本输出均如此声明）。
- 前端回归与构建在已应用树上通过；web 载荷与旧包逐字节一致，未引入新页面改动。

## ARCHIVE：复现与证据

- raw 目录：`docs/experiments/raw/agent-glm-landing-validation-2026-09-18/`
  - `adoption-package/` — 25 行清单、8 依赖、before/after 载荷、apply/revert/
    recovery（含窗口修复）
  - `rehearse_landing_package.sh` — 19 幕演练驱动；`rehearsal/` — 全部幕日志、
    act1b 应用树复现 matrix、窗口探针日志（`act11-window-probes.probe-bug-run.log`
    为探针自身缺陷的失败留痕，修复后全过）。演练用的目标副本（act*-target、
    browser-target、reprodock 等，约 180MB，可由驱动脚本完整重建）与人为损坏
    的 scratch-package 副本已按目录规约在结案时清理，只留日志与 JSON 证据；
    `rehearsal-v1-pre-windowfix/` 同口径处理
  - `rehearsal-v1-pre-windowfix/` — 窗口修复前整轮证据（18/18），保留未覆盖
  - `recovery_window_probe.py` + `recovery-window-results.json` — 窗口探针与结果
  - `recovery_probe_new_package.py` + `recovery-probe-results-new-package.json` —
    六个恢复场景指向新包
  - `browser/` — `serve_browser_candidate.py`（隔离启动器：URI 感知护栏、
    合成行情、双路模型桩、上证指数刻意无行情）、`check_two_entries.py`、
    `browser-checks.json`（7 项断言）、6 张截图、`browser-guard-report.json`
    （护栏四类全零）
- 复现命令：`python3 recovery_window_probe.py`；`bash rehearse_landing_package.sh`；
  浏览器：先起 launcher 再 `python3 browser/check_two_entries.py`（需临时前端，
  见报告上文端口与代理说明）。
- 被测代码：分支 `codex/agent-runtime-adoption-20260917`；运行目录 HEAD
  `7f8c38c3`（只读重核）；来源 main `f8638b9f`。
