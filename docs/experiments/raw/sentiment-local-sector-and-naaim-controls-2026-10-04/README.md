# 本轮恢复与证据入口

先读[完整报告](../../sentiment-local-sector-and-naaim-controls-2026-10-04.md)，再读 definitions.json、protocol.json、qualification.json、run-01/results.json、independent-review.json、local-sector-qualification.json、research-state.json、withheld.json、manifest.json/SHA256SUMS。NAAIM短史有局部关联，组合仍不如简单平均；本地原历史效果尚缺资格。不要凭completed把资料许可、首次发布或完整运行当已具备。

负责人/root原情绪线继续，非接管；work分支task/sentiment-factor-progress，基础fee4dd4d6d8e6196cd763a002eb5157bb6f551f2；范围登记66068173f96a8fcc51d5740adce963ecfadcb597。准确新成果SHA和同步状态读coordination/lei/docs/coordination/tasks/sentiment-factor-research.md。共享脏区不切换、不reset/clean，不同时写同一实验。

## 依赖、路径与最小恢复

已实际用macOS-15.6.1-arm64-arm-64bit、Python3.11.7、numpy2.1.1、pandas2.3.3；没有新安装、服务、密钥、数据库或tokenizer。权威策略原件仅指纹未交，研究可读摘要不能反过来改原文。所有运行资料位置相对项目根，不依赖Air用户名。kernel快照与旧analyze.py逐字相同，只供数学复用，不执行snapshot CLI。旧协议和旧代码需从基础分支保留，不拼共享当前脏src。

```sh
# 已进入准确任务分支的仓库根，核交付SHA
python3 - <<'PYCODE'
from pathlib import Path
import hashlib
r=Path('docs/experiments/raw/sentiment-local-sector-and-naaim-controls-2026-10-04')
for line in (r/'SHA256SUMS').read_text().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256((r/name).read_bytes()).hexdigest()==digest,name
print('delivered bytes match')
PYCODE
# 保存摘要检查：仅标准库，不重新拟合
PYTHONDONTWRITEBYTECODE=1 python3 docs/experiments/raw/sentiment-local-sector-and-naaim-controls-2026-10-04/verify_saved.py
# 人工4边界，需numpy/pandas，0市场拟合
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest docs/experiments/raw/sentiment-local-sector-and-naaim-controls-2026-10-04/test_analysis.py
# 输入检查：纯Git环境缺3原输入，应退出2并列缺件
PYTHONDONTWRITEBYTECODE=1 python3 docs/experiments/raw/sentiment-local-sector-and-naaim-controls-2026-10-04/verify_saved.py --require-inputs
```

可合法恢复并具权限时，准确原输入由用户安全提供于inputs.json列的相对路径并核SHA；无已获数据外部存储授权，不自动重新抓取或构造替代文件。另一台机器若缺依赖，按当地权限建隔离环境安装numpy==2.1.1 pandas==2.3.3；干净安装/跨OS未验证。前三项预期摘要和四人工检查通过，第四项缺原资料是明确阻塞，不称真实研究已可恢复。

独立临时目录验证见validation.json，包含实际命令/退出码/缺件。真实唯一核心命令analysis.py run和数值复核verify_independently.py仅为审计列出，现均封存，不能再次执行；已有输出与state阻止核心重跑。没有活跃实验或checkpoint，复制文件不迁移其他进程/登录态/锁。

## 分工与禁止重复

“基本面指标”负责市场理解图表/参考/指数对照/宏观解读。本线只提供准确因子定义/有效性/限制，不写其web或API；可引用本报告和源码版本，不重复金融实验。旧零售强警报已降级，当前代码文案不是新证明。旧AAII动态/均值/风险、短宽度/NAAIM弱基准、源6/6全部封存，家族累计至少1012市场拟合、至少4Pro。本轮新8拟合、0来源/Pro/付费，没有完整资金或线上收益。

## 接手AI启动提示

这次是现负责人继续的成果共享，不能自动接管。先读最新coordination/lei规则与sentiment-factor-research、investor-observation-map相关记录，核分支/完整commit与manifest/SHA。读取本报告、定义、固定协议、输入资格和封存状态，运行上述摘要/人工/缺件检查；缺输入或许可须明确说明，不能把import/清单complete当真实资格。确认新版是否已修旧流量时间错位/文案问题，再按已有授权选一个改变判断的资格补核或新有界问题。不要重跑旧核心，不因模型增加复杂度追正，不改原E触发/持有/对冲，不改生产、不跨项目取数或扩大预算。准确未交输入、策略原件、其他机器进程仍缺，不假定聊天/登录态随Git提供。共同源/结果优先复用，出现同模块同实验写入先停冲突范围再协调。
