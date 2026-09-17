# 返修后采用包演练记录（S2 repair，2026-09-17）

全部场景在 /private/tmp 的 mktemp 随机独立副本上执行，进程级隔离、无网络调用；
包一律放在与目标无关的路径、从 / 目录用显式 --target 调用；演练后副本已清理。

返修前四项（保持验收）：
- repair-actE.log（+actF 无目标拒绝）：错误 cwd + 包在目标外的任意位置，--target 显式
  指定 → 只改目标副本，24/24 逐哈希==after。
- repair-actB.log：目标漂移（copilot.py 翻转 1 字节）→ STATE-FAIL 拒绝，零部分写入。
- repair-actC.log：revert → 14 个 replace 逐字节恢复 before、10 个 add 精确删除。
- repair-actD.log：采用后追加本地改动 → revert 拒绝，改动原样保留。

返修新增场景：
- repair-actG.log：晚序损坏（manifest 最后一行 after 载荷追加 1 字节）→
  PAYLOAD-FAIL 预校验拒绝（exit 1），24 目标逐一校验保持 before/不存在——零写入。
- repair-actH.log：before 回退载荷损坏 → revert 预校验拒绝（exit 1），
  目标保持 after 状态——零写入。
- repair-actI.log：写入中途失败（web/src/pages 目录只读）→ WRITE-FAIL 中止，
  KEEPDIR（备份+已写清单+restore-partial.sh）保留，按打印指引实际执行 restore，
  恢复后 24 目标逐一校验全部回到 before/不存在——零部分写入。
- repair-actJ1/J2.log：必要依赖缺失（client.ts 删除）→ revert 拒绝且目标保持 after；
  依赖漂移（trades.py 翻转 1 字节）→ apply 拒绝。正例=完整兼容基线副本
  （24 before + 7 依赖按捕获指纹就位）上的 actE/actA 成功应用。

依赖清单：adoption-package/dependencies.tsv —— 7 个只读前置指纹
（trades.py、client.ts、CopilotCards.tsx、AnswerText.tsx、App.tsx 草稿 store、
AgentMarkdown.tsx、agent-workspace.css），逐项含选择理由；apply/revert 均校验，
缺失或漂移一律拒绝，包不复制、不覆盖它们。
