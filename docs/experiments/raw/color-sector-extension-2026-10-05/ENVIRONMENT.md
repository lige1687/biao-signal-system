# 本轮运行与恢复范围

实际Python 3.11.7；NumPy 2.1.1；pandas 2.3.3；LightGBM4.6.0。系统 macOS-15.6.1-arm64-i386-64bit。原本仓库局部运行时`docs/experiments/raw/color-gray-path-2026-10-04/.venv.local/bin/python`，没有新安装或全局改动。

LightGBM本机需进程变量`DYLD_LIBRARY_PATH=/opt/homebrew/lib/python3.11/site-packages/torch/lib`，用于既有libomp。此机器路径不是远端恢复前提；远端必须安装本系统匹配的OpenMP并核原运行时指纹，不能照搬路径。其他OS未测试。不需API密钥，不授予行情下载/付费或生产权限。

项目根目录运行，相对路径在本目录脚本中解析。先核manifest/SHA256SUMS及源许可；`workflow-input.local.json`、完整preflight和模型参数本机保留、未上传。清单记录准确大小/SHA及取得位置，接手者拿不到原输入不得声称完整复现。不要重新拟合已封存16次。

- 保存CSV可用标准库独立核算主要误差和高低组表。
- 完整分析重放需恢复原输入及模型参数后，设置`PYTHONPATH=src`，运行`analyze_saved.py`；这是重放、0拟合。
- `ranking_checks.py`需要完整原preflight；`diagnostics.py`需要原价格日历和保存CSV，缺文件应报告而非重训补齐。
- 首次执行设计入口`prepare.py`→`run_stages.py freeze freeze-02`→`run_stages.py execute core-01`已经执行；现在不再运行。
- 正式报告登记使用`publish.py`复用旧预测，4分支0新增真实拟合，已完成。

依赖原源码和科学定义跟随本工作分支，原数据不在Git；冻结合同绑定原件。恢复资料时不能修改旧锁、hash或成绩来匹配新路径。
