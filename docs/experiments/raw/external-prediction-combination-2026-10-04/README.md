# 固定预测组合的保存证据

原价量/时序预测只读，0新拟合。完整结论见 ../../external-prediction-combination-2026-10-04.md。

先核 SHA256SUMS，再复核保存算术（标准库即可，工作目录为项目根）：

```bash
python3 -S docs/experiments/raw/external-prediction-combination-2026-10-04/verify_saved.py --summary docs/experiments/raw/external-prediction-combination-2026-10-04/core/summary.json
```

预期：exit 0、162项数值核对、original_predictions_checked=false。这只验证保存汇总，不证明原市场数据合格。

拥有原档案且原指纹一致时，加 --root . 可核原1268行，预期239项、true。原件路径/SHA在summary与arithmetic-details；缺原件即不能完整重算，不能用合成资料顶替。

run_probe.py --root . --out 新目录、risk_followup.py --root . --output 新文件、report_details.py --root . --output 新文件提供原算术入口；正常接续只读现成结果，不重跑封存。已有输出会拒绝覆盖。完整桥接运行还依赖项目源码/NumPy，相关原件及运行代码指纹见manifest。Linux/Windows和从零完整市场恢复未验证。

core-process/risk-process/report-process及verification-processes保留命令、返回码和输出；<PROJECT_ROOT>为路径脱敏替换，不是可原样执行的shell变量。没有模型密钥、行情大表或训练权重进入Git。
