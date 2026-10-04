# 环境资料覆盖核查：恢复入口

先读上两级`sentiment-environment-readiness-2026-10-05.md`，再核protocol.json、manifest.json和SHA256SUMS。本目录只回答输入/环境支持，不计算因子效力。现有clock代码/账本与工作分支基础41fd886cd31d1101609690d2192a331fe47dd93c字节相同；本轮工作提交从分支路径历史与协调记录定位。

必要运行环境：Python 3.11.7、numpy 2.1.1、pandas 2.3.3及PyYAML（实际版本见restore-check.json）。无网络服务、权重、数据库和密钥需要。使用项目已有依赖安装规范，不自动全局安装。

在仓库根目录执行；`CACHE_ROOT`由接手者设为合法取得的两个缓存所在目录，不能默认为另一台机器已有资料。

```sh
# 安装须在用户获准的虚拟环境，版本以pyproject及本次运行记录为依据。
python3 -m pip install numpy==2.1.1 pandas==2.3.3 PyYAML==6.0.3
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/src"
H=docs/experiments/raw/sentiment-environment-readiness-2026-10-05
shasum -a 256 -c "$H/SHA256SUMS"
python3 "$H/check_coverage.py" --self-test --root "$PWD" --output "$H/local-self-test-new.json"
# 仅取得protocol所列相同指纹资料后；保存到新文件，不覆盖result.json。
python3 "$H/check_coverage.py" --root "$PWD" --cache-root "$CACHE_ROOT" --output "$H/local-check-new.json"
python3 "$H/verify_saved.py" --root "$PWD" --cache-root "$CACHE_ROOT" --output "$H/local-verification-new.json"
```

首个自检预期exit0，12斜率边界/4路径/20前缀/1120独立人工点。完整检查预期835美国日期、458国内板块并集、261国内日期、最多142可分组日期；原始资料未交付时应停止并报告缺件，不能取新版覆盖旧输入。完整检查约4秒，无模型重训；虽便宜，已有验证无故不重跑。

4个市场输入仅本地：旧SPY价格和旧AAII保存面板（只读取t列），以及CACHE/sector_trend_history.json、CACHE/tx_sector_flow_pilot.json。准确大小SHA在protocol.json；CACHE路径恢复由--cache-root明确指定。数据许可/历史到达时间/调整版本未自动合格，Git摘要不等于原件已交。

标准入口`docs/research/current-standards.json`在共享工作树采用，本工作分支可能不含其他线最新全局规范；protocol已保存准确路径/版本，另见同仓技术规范来源40ed00f8fa3469fe68bb5255917368d95758da4b。执行新效力研究前核最新版与唯一定义表，不使用本目录另立登记源。完整跨机器市场运行、Linux/Windows均未验证。独立目录自检只证明最低代码关系可恢复。
