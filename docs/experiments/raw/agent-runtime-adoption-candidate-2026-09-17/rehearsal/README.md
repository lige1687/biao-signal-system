# 采用包演练记录（S2/G3，2026-09-17）

四幕演练均在 /private/tmp 的独立临时副本执行（mktemp 随机目录，演练后已清理），
副本结构与真实工作区同构：包位于 docs/experiments/raw/.../adoption-package，
24 个目标文件按 manifest before 状态摆放（replace=运行实态捕获，add=不存在）。

- act1-apply-ok.log：正确基线上 apply.sh，exit=0，applied 24/24，
  事后逐文件 sha256 校验全部 == after。
- act2-drift-refused.log：任一目标（agent.py 第100字节翻转）漂移时
  apply.sh 拒绝（exit=1），其余 23 个目标逐一校验保持 before/不存在
  ——零部分写入。
- act3-revert-ok.log：revert.sh，exit=0，14 个 replace 逐字节恢复为
  before（运行实态捕获）、10 个 add 精确删除。
- act4-postedit-refused.log：采用后对 agentUx.ts 追加一行本地改动，
  revert.sh 拒绝（exit=1），该改动原样保留——回退不覆盖之后的新改动。
