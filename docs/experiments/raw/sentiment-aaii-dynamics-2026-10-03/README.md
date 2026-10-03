# AAII情绪动态：本轮恢复与核验入口

先读[完整报告](../../sentiment-aaii-dynamics-2026-10-03.md)，再读definitions、protocol、controller-review、research-state、withheld和manifest。三项动态对SPY约半年涨幅未确认稳定新增帮助；完整交易收益未测。不要再跑封存拟合、换窗口追正结果。

代码/小型汇总已准备同步到task/sentiment-factor-progress，确切发布状态与commit以coordination/lei分支docs/coordination/tasks/sentiment-factor-research.md为准。原负责人继续；范围登记commit b2bcdb6d11d43835a474400f985bbd2acaa38d9b，基础成果69688860b30c1f4fdb1d06e40e0d8e75c50e85db。

## 依赖与文件关系

从仓库根目录执行。已验证macOS 15.6.1 ARM、Python3.11.7、NumPy2.1.1、pandas2.3.3。没有新安装、外部服务、环境变量、密钥、模型权重或数据库要求。Linux/Windows未测试，不保证跨平台通过。已有环境可直接使用；若需安装，先在接手环境遵循其权限，用隔离虚拟环境安装`numpy==2.1.1 pandas==2.3.3`，不擅自改全局环境。标准库的verify_saved不需要这两个库。

analysis.py固定从相邻snapshots/workflow_evaluation.py读取原项目数值核心，SHA与原src完全一致；不依赖Air桌面用户名、全局LEI包或共享脏代码。snapshot只是冻结数学来源，不能作为改原工具的入口。authority-manifest的全局definitions哈希只记录当时背景，候选具体定义在本地研究卡，非运行依赖；八份规范远端准确版本见standards-remote-bindings。

## 准确命令及预期

```sh
# 已进入仓库根目录；只核交付文件
python3 - <<'PYCODE'
from pathlib import Path
import hashlib
base=Path('docs/experiments/raw/sentiment-aaii-dynamics-2026-10-03')
for line in (base/'SHA256SUMS').read_text().splitlines():
    expected, name=line.split('  ',1)
    assert hashlib.sha256((base/name).read_bytes()).hexdigest()==expected, name
print('all delivered hashes match')
PYCODE

# 只核保存摘要、公式锁和拟合次数，不重新研究
PYTHONDONTWRITEBYTECODE=1 python3 docs/experiments/raw/sentiment-aaii-dynamics-2026-10-03/verify_saved.py

# 人工边界；会保留本目录synthetic-fixtures内小型测试物，无市场研究
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest docs/experiments/raw/sentiment-aaii-dynamics-2026-10-03/test_analysis.py

# 检查完整输入资格：缺件应退出2，不冒称完整可运行
PYTHONDONTWRITEBYTECODE=1 python3 docs/experiments/raw/sentiment-aaii-dynamics-2026-10-03/verify_saved.py --require-inputs
```

前三项预期指纹相同、保存汇总通过、8个边界测试通过。第四项在仅Git材料环境预期缺4项必需输入；withheld逐件有大小/SHA/恢复方式。输入有资格且合法移交后才可能检查真实资料；仅import或--help不代表市场研究可恢复。本轮实际隔离验证见validation.json，缺件按预期阻止运行不是数据已交。

原实际命令：`python3 .../analysis.py --prepare-only --output .../qualification.json`（0拟合），之后`python3 .../analysis.py --fit`（153次，仅执行一次），`python3 .../verify_independently.py`（27次，已用）。这些命令只为审计列出；run-01/账本已存在会拒绝再拟合。恢复不删除目录绕过保护；独立复核也不能重新运行来重置27次计数。先读取已保存结果。运行过程不随Git迁移，当前无科学进程需恢复。

## 状态与失败的阅读方法

implementation-review是实现者交回时的历史状态，其源码SHA在之后由主控做便携路径修正；最终字节以execution-freeze为准。definitions中的pending同样是冻结时状态，实际核验见controller-review，不覆写冻结卡制造事前通过。preexecution-metadata-correction、preflight-failure、kernel-packaging-correction保留修正原因，旧原文/锁/成绩未改。

源码、报告、保存汇总、参数账和独立复核已提供。原始调查/行情、逐日期观察/预测、系数及部分临时记录未公开；没有其他已授权存储，云端完整真实重算仍缺件。不要把本轮阴性归档当全情绪方向失败，也不要把公开小包检查当生产/金融有效性通过。
