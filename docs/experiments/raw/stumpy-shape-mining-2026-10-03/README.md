# 复现与证据入口

先读protocol.json、sources.json、probe-summary.json、independent-validation.json和final-validation.json。后者记录实际命令、退出码、输出；公开副本将本机仓库绝对路径替换为${ROOT}，未改数字。原本机记录保留在.biao/external-shape-mining-20261003。core-tests.log和followup2-failure.json保留失败。

已测Python3.11.7、NumPy2.1.1、SciPy1.17.1、STUMPY1.14.1、numba0.61.2、llvmlite0.44.0、pytest8.4.2，macOS arm64。sources.json含3个wheel准确下载URL/大小/SHA和完整许可。恢复依赖应先核wheel指纹，再在本机隔离目录安装；其他平台需对应wheel，尚未验证。NumPy/SciPy沿用本机既有版本，未做完整无网络环境恢复。

以下在项目根目录运行，ROOT为项目路径。先确认上述依赖与版本可用。输出必须是新目录。

```sh
export ROOT="$PWD"
export PYTHONPATH="$ROOT/.biao/external-shape-mining-20261003/deps:$ROOT/src"
export NUMBA_CACHE_DIR="$ROOT/.biao/external-shape-mining-20261003/numba-cache"
export NUMBA_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
python3 -m lei_signal.research.shape_mining apply \
  --input docs/experiments/raw/stumpy-shape-mining-2026-10-03/probe/synthetic/input.json \
  --library docs/experiments/raw/stumpy-shape-mining-2026-10-03/probe/synthetic/discover/library.json \
  --output .biao/shape-resume-new
```

预期退出0，输出research_unqualified，240日期、后80日期有距离，结果与probe/synthetic/apply/observations.json相同。这验证应用，不重新发现模板。最小相关测试：python3 -m pytest tests/unit/test_shape_mining.py -q；已实测15通过。独立恢复实际复制单模块到新目录后使用同样apply参数，记录见final-validation.json。

run_probe.py是本次冻结端到端程序，需要本地源panel；不要因恢复而重跑研究。verify_saved_outputs.py保留最后批次的实际执行脚本（含必要回归和恢复），不是日常启动脚本；原运行路径在.biao。真实输入及两输出只在本地probe-real/real，未交付，指纹见probe-summary.json；远端可恢复人工演示，无法仅凭Git恢复真实演示。无模型权重或凭证需求；真实历史再利用仍需合法数据权限。

manifest.json与SHA256SUMS覆盖本目录除自身的文件。大wheel、真实行情/模板/逐日结果不在清单交付范围，见sources和probe-summary中的local-only记录。CLI目前可接受显式window/max_candidates的Python参数，但本题结论只适用于冻结20/3，不能把可调用参数当调参授权。
