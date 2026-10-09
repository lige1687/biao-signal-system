# D—MAE 真实 X 一次封存入口，阶段 B

## 一句话结论（大白话）

已写好只允许执行一次的真实资料封存入口，人工边界检查通过；**尚未运行真实 X**。之后只有负责人完成独审并写入绑定最终代码和六份原件的单独许可，程序才会把原有 D 和新算的 V 写到固定外盘目录。这里的 V 是“原信号波动幅度占收盘价的百分比”，不会用到未来价格。

## 固定入口与许可

- 源码：`src/lei_signal/research/native_risk_d_mae_real_x.py`，SHA-256：`1a716db72ee4ba760926fd5a7734e0deaa0cf4dd6a3d0f32543c8c0ce9e4c00b`。不接受命令行路径或其他覆盖参数。
- 阶段 A 源码 SHA-256 固定为 `5404b52f1e9ca2dc103eff37cabf51e52656d2737a8244bbb11fc2aeb63decb7`；生产入口只调用其中的公开 `load_original_identity()`，不接受任意字典或已保存审计 JSON 冒充原件。
- 设计合同 SHA-256 固定为 `ace132ddb89de3e45951148d9673524fa9fe448f662f2576221d216bbe9717c6`；本阶段执行合同 SHA-256 为 `c1d1689c8657707ad63f1127d9cab0250cf8a6d33cc3e2eec544c4ed03e3c7d2`；输出计划 SHA-256 为 `91d788d14f38a75350d2bafb6b9154fd6b9f4a9d3fef1128dab590e72fb21dc8`。
- 负责人须另在本目录创建唯一 `real-x-grant.json`。它必须恰有源码中 `GRANT_KEYS` 的字段：`schema=native-risk-d-mae-real-x-grant/1`、`approved=true`、`stage=real_x`、上述三份代码／合同／计划 SHA、六份原件 SHA 字典、按已核 76 个案例和 84 个事件成员形成的 `membership_sha256`、精确 `output`、`real_x_directory`、外盘挂载点／设备号／UUID、固定 `ledger_path`，以及 `permissions={real_X_passes:1,V_passes:1,real_Y_passes:0,fits:0,future_price_reads:0,external_requests:0}`。成员摘要按源码 `_membership_sha` 的固定字段和排序计算；正式入口会从六份原件重新核算后比较。输出计划的 `execution_authorized=false` 只说明它不是科研许可，不代替这份单独许可。
- 固定本机账本是本目录 `real-x-attempt.jsonl`。全部路径、资料、许可和容量检查通过后才独占创建第一条 `started`；**创建即消耗唯一运行次数**。之后即使派生或写盘失败，也保留账本和部分现场，不重试、不换输出目录。完成时追加 X 文件和回执的两个 SHA；读回失败也不能算完成。

负责人在最终独审并创建许可后，使用下面的固定调用；调用时不得附加参数：

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR='/Volumes/win+mac通用/LeiSignal-新实验结果/research-dispatch-controller/research-dispatch-controller-20261009T121052-8c15af8c4cb6/result/tests' python3 -B '/Users/yongbiaoli/Desktop/lei-signal-lab/.codex/worktrees/research-direct-20261008/src/lei_signal/research/native_risk_d_mae_real_x.py'
```

固定真实输出目录为外盘本次计划的 `result/real-x/`，只允许写 `x-rows.json` 和 `receipt.json`；人工测试资料在同一计划的 `result/tests/`，不会占用真实输出目录。真实目录已经存在会在消耗次数前拒绝；不能把一次失败改用另一个目录重跑。

X 行保留 76 个原案例、84 个成员别名、33 个资产生命周期组、原 D 值、价格轴、来源和窗口元数据。只派生一次 `V=100×ATR20_SMA/A`，核正数和有限值，并检查 D 与原 A/C/ATR 的算式身份，但不替换 D。原自然月字段不作为本轮窗口；日历未知案例继续保留。X 文件和回执会绑定设计、六原件、最终代码、许可及成员摘要，分别落盘读回后才记完成。

人工测试、首次失败与所有指纹见 `verification.json`。本阶段真实 X/V/Y、拟合、未来价格读取和外部请求均为 0；没有改旧原生入口、阶段 A 文件、冻结原件、规则或交易系统。真实 Y 需之后另订许可。
