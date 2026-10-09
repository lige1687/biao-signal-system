# D–MAE 原 D 的真实 Y 入口：Stage C 代码交付

本阶段只完成可运行入口和人工资料检查；**没有读取真实未来价格，也没有执行真实 Y**。外盘 `result/tests/` 存人工测试临时文件和日志；同一计划下唯一 `result/real-y/` 留待主控独立审查、签发许可后使用。现有 X、V 已封存，一次运行的额度不能重用。

入口 [native_risk_d_mae_real_y.py](../../../../../src/lei_signal/research/native_risk_d_mae_real_y.py) 固定读取已接受的 X（76 案例、84 事件成员、33 资产及生命周期组），以冻结交易日历确定每个成熟案例事件后的第 1 至第 21 个收盘价，即 21 个收盘价、20 个间隔。先核全 75 条路径的日期、完整性、正数和有限值，才计算 `Y=max(0,100×(1−21日最低收盘价/首日收盘价))`；最后一个坏价也会阻止全部 Y。第 76 个案例继续标为未知，不延长 2026-06-26 截止日，不从旧自然月字段推出窗口，不使用最低价字段。外部来源、已封存 X、代码、合同、许可、输出盘、唯一账本均按固定路径及 SHA 核验。价格是事后保存的经济价格，来源到达时间未知；上海市场使用深圳日历代理尚未独立证实。因此结果只可作描述性研究，不代表当时可执行报价、交易效果或交易授权。

比较使用原 D、原 V 和这次 Y **三者都有有限数值的同一批案例**。各资产分别算并列名次相关系数及 D 与 V 的有符号差，案例少于 2 个或名次恒定时给空值，2 案例标明退化情况。总体只对原来共同可算的固定资产集合求等资产平均；33 个预定删除对照重复使用同一批 Y，若固定资产中任一项变得不可算便给空值，不改用更小资产集合。`asset_lifecycle_groups` 是该资产全部原案例组数；`complete_asset_lifecycle_groups` 才是 D/V/Y 均完整的组数。该相关差不等于 D 相对 V 的独立增量，更不是收益。

主控独立审查后，需要在本目录写入唯一的 `real-y-grant.json`，并绑定该文件的完整字节哈希。许可必须是 `native-risk-d-mae-real-y-grant/1`、`approved: true`、`stage: "real_y"`，精确包含源码和合同所列字段，不接收额外字段。固定字段及值由入口中的 `GRANT_KEYS`、`_validate_grant` 和 [executor-contract.json](executor-contract.json) 确定，尤其绑定设计、Stage A/X 代码、当前 Y 代码 SHA、X 结果/回执/许可/完成账本、原六来源 SHA、成员 SHA、真实价格和日历 SHA、输出计划与外盘设备。`permissions` 必须是严格整数：`real_Y_passes=1`, `max_label_cases=75`, `max_future_close_observations=1575`, `fits=0`, `searches=0`, `extra_windows=0`, `auto_retries=0`。`original_sha256` 须与冻结 X 逐项相同。仅输出计划或任意调用者替换预期 SHA 不构成许可；当前入口对照写死的已审指纹。

主控在许可获独审后，**只运行一次**：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B /Users/yongbiaoli/Desktop/lei-signal-lab/.codex/worktrees/research-direct-20261008/src/lei_signal/research/native_risk_d_mae_real_y.py
```

命令不接受参数。入口在真正开始前检查准确来源、许可、磁盘 UUID/设备、空间与尚未使用的输出目录；唯一 `real-y-attempt.jsonl` 以排他方式记录 `started` 后即耗尽本轮额度。开始后失败会追加失败记录，不能自动重试或换输出目录。成功时排他写入 `result/real-y/y-result.json` 与 `receipt.json`，逐字读回核 SHA，然后在账本中锁住两份 SHA。主控仍需独立审核这些真实输出，才能解释研究结果。人工测试和验证见 [verification.json](verification.json)。
