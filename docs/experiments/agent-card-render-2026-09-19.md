# B 阶段前端三卡渲染：dca / sentiment / mindset（GPT ITERATION:6 冻结契约）

- 日期：2026-09-19
- 分支：`codex/agent-runtime-adoption-20260917`（HEAD 29a8ef42 起步）
- 阶段：S1（三卡渲染实现与验证），委派执行；主控独立复核另行
- 委派任务：fb2024ae-a975-4af3-b52d-b9e92e9ec330

## 一句话结论（大白话）

助手的三个新回答卡片——定投状态板、市场情绪速览、认知/心态卡片——现在能在
网页助手里正常显示了。测试结论：三种卡片都走对了各自的显示分支；有数据时如实
展示（状态、读数、出处都照后端给的原样呈现）；缺数据时明确写「数据不可用」，
绝不编数字凑数；算不出来的状态显示「不可判」，不会误写成「未触发」；三张卡
都是纯展示，没有任何买入、卖出、加仓之类的动作话术。网页构建和原有功能测试
全部通过；另有一个与本次改动完全无关的旧测试（K线结构标记）在改动前就已经
失败，已留证并如实记录。后端与工作台对话管线一行未动。

对用户的实际意义：现在对助手说「定投怎么样了」「现在市场情绪如何」「聊点
心态」，收到的不再是一句「暂不支持展示」，而是能看的卡片；其中定投状态板
只给参考状态、不催你操作，情绪卡只解释「为什么」、不拦任何信号，心态卡只
讲故事带出处、不参与任何买卖判断。

## 改动范围（diff 全量清单）

| 文件 | 性质 | 内容 |
|---|---|---|
| `web/src/components/copilot/CopilotCards.tsx` | 唯一代码改动 | 分发层新增 dca/sentiment/mindset 三分支；三个纯展示组件 + 本地类型 + 中文显示映射 |
| `web/run-copilot-cards-regression.mjs` | 新增测试 | 真实组件静态渲染回归（9 组断言，见下） |
| `web/package.json` | 测试登记 | 新增一行 `"test:copilot-cards"` |
| `docs/experiments/agent-card-render-2026-09-19.md` | 本报告 | |
| `docs/experiments/raw/agent-card-render-2026-09-19/` | raw 证据 | 构建/回归/渲染验证原始输出 |
| `docs/experiments/registry.json`、`docs/experiments/INDEX.md` | 登记 | 按归档规约三件套 |

后端零改动、`/api/agent/chat` 工作台管线零改动（diff 仅上表文件，见 raw
`diff-scope.txt`）。三类卡沿用既有 `cp-card` 布局类与 `details` 折叠交互，
未新增 CSS、未改任何交互流程、未反向改后端契约。

## 冻结契约逐条落实

1. **仅分发层新增三分支**：`CopilotCardDispatcher` 内追加三个 `card_type`
   判断，未知卡兜底文案原样保留；类型与组件照 `ScoutCard` 先例就地定义。
2. **dca 卡**（payload 契约 = `src/lei_signal/api/routes/copilot.py` dca 分支
   实测字段）：证据账本可用性 + 版本；中美宽度读数（值/健康度/口径日期）；
   `states` 逐状态（三色、距年线、两年回撤、宽度档位、深超跌、底部区域）放
   可折叠区。`evidence_available` 非 true → 「证据账本数据不可用…状态无法
   计算」；宽度/字段缺失 → 「数据不可用」；`deep20/bottom_zone` 为 null →
   「数据不可判」（null=无法判定 ≠ 未触发，P1 口径）；措辞只读，无动作语。
3. **sentiment 卡**：过热/冰点板块叙事 + 融资环境 + 可选标的标注；包级不可用
   → 「情绪面数据不可用」+原因；融资环境单独失败 → 该行单独「数据不可用」；
   无任何趋势判断/交易建议/过滤语。
4. **mindset 卡**：`text` 必展示（缺失显示降级文案不占位）；`quote` 仅非空
   才渲染（实测仅 3/26 有值，回归里断言空 quote 不出「」占位）；`source`
   显示出处；`items` 空用回落说明；卡片标题保留「只作叙事与教育用途，不参与
   判断」。`count` 展示为「N 条」；`sha256` 是完整性指纹、对用户是乱码噪音，
   决定不上屏（契约四条渲染要求不含它，特此留痕供复核）。
5. **缺字段降级总原则**：所有字段按「缺了就如实说不可用」处理，全组件无一处
   补猜、无默认值冒充数据。

## 验证证据（原始输出见同名 raw 目录）

| 验证 | 命令 | 结果 | 证据文件 |
|---|---|---|---|
| 新增三卡回归 | `node run-copilot-cards-regression.mjs` | 通过 | `copilot-cards-regression-output.txt` |
| 既有回归 9 项 | `npm run test:*`（逐项） | 8 过 1 既有失败（见下） | `existing-regressions-output.txt` |
| web 构建 | `npm run build`（tsc --noEmit + vite build） | 通过（2.83s） | `build-output.txt`（df 构建前后各留一行） |
| 渲染分支验证 | 同新增回归脚本（真实组件静态渲染） | 三类 card_type 均进对应分支；正常与缺字段 payload 都验证 | 同上 |
| diff 范围 | `git diff --stat` + `git status` | 仅上表文件 | `diff-scope.txt` |

新增回归 9 组断言覆盖：① 三类 card_type 经 `CopilotCardDispatcher` 进入对应
分支 + 未知类型保持既有兜底；② dca 正常 payload 逐字段；③ dca 降级（账本
不可用 / 数据不足标的 / null 三态 / 缺 breadth 与 hint）；④ sentiment 正常；
⑤ sentiment 降级（包不可用 / 空对象 / 融资环境单独失败）；⑥ mindset 正常
（quote 条件渲染计数断言）；⑦ mindset 降级（空 items / 缺 text / 库不可用）；
⑧ 六份渲染 HTML 无「建议买/加仓/清仓/止损/止盈/立即执行」类动作语；
⑨ 既有 recommend/scout 卡渲染零退化。

磁盘留痕：构建前 `/` 可用 637Mi、构建后 638Mi（vite dist 原地重建，净变化约 0）。

## 既有失败（与本次无关，未修复）

`test:structure-controls`（K线结构标记回归，`run-structure-regression.mjs`）
在**未含本次改动的干净 HEAD 上同样失败**（`git stash` 前后各跑一次对照，
exit 均=1，报 `invalidatedMarks 单独开启失败：无标记`）。该脚本与 copilot
卡片无关，修复会越出本阶段冻结的 diff 范围，故只留证不处理，交主控定夺。

## 限制与交接

- 三类卡是**纯展示**：无按钮、无二次请求；dca 不做任何新计算（宽度健康度、
  不可判语义都直接读 payload）。
- dca 无 symbol 请求时后端返回整个跟踪池（11 个标的）逐状态，前端用折叠区
  收纳（≤3 个自动展开）；若后续后端想改为「无 symbol 不带 states」，属契约
  变更，前端无需再动。
- 候选提交未合并、未部署；线上生效与否待主控验收与合并授权。

## ARCHIVE

- 冻结契约来源：委派简报 G1（GPT ITERATION:6 计划，2026-09-19）。
- payload 契约核对基准：本仓 `src/lei_signal/api/routes/copilot.py:294-398`
  （dca/sentiment/mindset 三分支 data 字典）+ `lei_signal/dca/state.py`
  （TargetState/breadth meta）+ `lei_signal/copilot/sentiment.py`、
  `mindset.py`（数据包结构与降级路径）。
- 复现：`cd web && npm run test:copilot-cards && npm run build`；回归脚本
  `web/run-copilot-cards-regression.mjs`（esbuild 打包真实组件 +
  react-dom/server 静态渲染，全程离线，payload 全为合成测试数据）。
- 前端显示映射（纯展示层，不影响判定）：三色 green/gray/black 与档位
  low/mid/high 的中文说法、健康度 fresh/stale/incomplete/missing/unknown
  中文说法，未知值一律回「数据不可判/未核实」。
