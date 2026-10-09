# D—MAE 原件身份适配，阶段 A

## 一句话结论（大白话）

六份恢复的原件逐字节核对后，76 个案例、84 个原事件和 336 条特征记录能准确对上，包含 8 个双事件案例和 1 个未来观察日期不足的案例。本阶段只确认“这些资料是谁、怎样对应”；没有计算新的风险尺度、未来结果或策略效果。

## 交付与边界

- 新适配器：`src/lei_signal/research/native_risk_d_mae_inputs.py`，唯一公开真实入口 `load_original_identity()`，无路径或预期哈希参数。入口先核外盘 UUID/设备、恢复清单中的六个精确路径与固定 SHA-256，再严格解析 JSON。任何目录越界、链接、重复 JSON 键、非有限数、资料字节改变或身份冲突均拒绝。
- 新人工测试：`tests/unit/test_native_risk_d_mae_inputs.py`。人工变异只调用内部 `_validate_identity`，不能给真实入口替换预期哈希。
- 完整身份明细：外盘本次运行的 `result/identity-audit.json`（路径和指纹见 `verification.json`）。其中逐案例保留原 D、A/C/ATR、事件别名、事件各自 MA 周期、来源指纹和当前研究窗口的日期元数据；另有全部 84 条事件到案例的映射。原 `member_ma_periods` 列表原样保存。

真实原件有一个容易误读的细节：`case:3127bc9f56ebea7d4573` 的 `member_event_ids` 首项事件是 MA120，但 `member_ma_periods` 写作 `[60, 120]`。两个成员周期相同，只是列表顺序不同。最初按位置配对的检查因此失败；现按事件 ID 读取实际 MA，核对保留重复次数的周期集合，同时核代表事件与 `case.ma`。原文件没有修改。

旧 `deduplicated-cases.json` 的自然月字段属于另一个问题，不能决定本轮未来观察窗口。适配器只引用已冻结 `METADATA-ONLY-SUPPORT.json` 中 `all_window_metadata` 的日期及成熟状态：75 个有足够日历、`case:ded0d0c43677a76957f4` 保留为未知。没有读取未来价格。

适配器输出字段供下一阶段单独审查集成：`cases[]` 的 `case_id, asset, signal_date, lifecycle, event_ids, event_ma_period, A, C, ATR20_SMA, D_frozen, price_basis_id, source_sha256, calendar_id, window_metadata`，以及 `event_to_case`。现有原生入口只接受人工数据且会计算 V；本阶段没有接入或放宽它。下一阶段须另行确定真实 X 的权限、代码与绑定，不能把本身份审计当成 X 封存或交易结论。

完整检查、首轮失败和文件指纹见 `verification.json`。本阶段未改规则、原生旧入口、原件、报告登记、生产资料；真实 X/V/Y、拟合和外部请求均为零。
