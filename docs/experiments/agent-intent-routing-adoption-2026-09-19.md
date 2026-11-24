# Agent 意图路由扩展：生产采用记录（2026-09-19）

## 一句话结论（大白话）

快捷入口现在能听懂三类新问法了：问**定投**（如"现在能定投吗"）直接出定投状态板
卡片（只有数据提示，不代下单）；问**市场情绪**（如"市场情绪怎么样"）直接出情绪
解说卡（只解释、不拦任何信号）；说**心态/认知**（如"最近拿不住怎么办"）系统会
明说"这类内容库还没建"并转回普通聊天，原因在接口回包里可查。线上实测四条全部
符合预期，旧五类指令原样不受影响。本次只装验收过的候选，未做任何新改动。

## 采用内容与过程

- 来源：候选提交 `8ae47dcc`（job 09e2707a，GPT 终审 CONSENSUS；S1 审计纠正了
  "/api/dca 已上线"的假象——该 REST 从未挂载，200 是前端兜底页）。
- 两仓为同一 git 仓库主从工作树：采用前先验 5 个目标文件与候选父提交 5b2fd8a5
  **零漂移**；`git restore --source=8ae47dcc` 恢复 5 文件（intent.py、copilot.py、
  schemas.py + 2 个测试文件）；装后 5/5 逐哈希等于候选版；运行仓独立复跑
  36 passed。前后指纹与复跑输出存
  `raw/agent-intent-routing-adoption-2026-09-19/`。
- 服务重启（launchd com.lei.backend），健康检查 200。
- 线上实测（/api/copilot/dispatch，纯规则+数据服务，零模型调用）：
  "现在能定投吗"→intent=dca 出 dca 卡；"市场情绪怎么样"→intent=sentiment 出卡；
  "最近拿不住怎么办"→chat + chat_fallback=true + fallback_reason=mindset_seed_missing；
  "我昨天买了1万515880"→trade_report 旧路由不受影响。

## 限制与边界

- **"直达"仅指后端分派**：dca/sentiment 卡的 card_type 是新值，前端页面渲染
  未做（页面改版另立任务）；当前页面表现等同既有未知卡的既有处理。
- 认知=识别+显式回落，种子库仍未接入；测试通过不代表具备否定语义理解
  （D4/D5 观察项维持）。
- 情绪/定投只读只叙事，无任何硬过滤；判定权仍在规则层。
- 授权留痕：主控此前告知"装进运行系统仍会先问你"，用户回复"后续你自己推进
  不用管我了"（2026-09-19），据此执行本采用；回退=对 5 文件
  `git restore --source=5b2fd8a5 -- <file>`（哈希见 raw before-hashes.txt）。

## ARCHIVE

分类数据与质量，passed 指生产采用按冻结流程完成且线上分派实测通过；不构成
策略有效性或收益结论。设计细节见 agent-intent-routing-audit-2026-09-19.md
（S1 审计+矩阵冻结）与 agent-intent-routing-2026-09-19.md（S2 实现）。
