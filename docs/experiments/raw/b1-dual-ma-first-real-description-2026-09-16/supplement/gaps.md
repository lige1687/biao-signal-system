# 补件缺口与冻结历史登记（2026-09-16T17:09:43.782907+08:00）

## 冻结历史

- src/lei_signal/research/factor_unit/__init__.py: 两版相同，现存原件一致
- src/lei_signal/research/factor_unit/description_core.py: 两版相同，现存原件一致
- src/lei_signal/research/factor_unit/state_description.py: 两版相同，现存原件一致
- src/lei_signal/research/factor_unit/b1_contract.py: v1.0.0原字节不可恢复（声明 f58586153acafe57…）
- src/lei_signal/research/factor_unit/b1_description.py: 两版相同，现存原件一致
- scripts/run_b1_dual_ma_description.py: 两版相同，现存原件一致
- src/lei_signal/research/factor_unit/close_state.py: 两版相同，现存原件一致
- src/lei_signal/research/trading_calendar.py: 两版相同，现存原件一致
- src/lei_signal/features/indicators.py: 两版相同，现存原件一致
- src/lei_signal/rules/dual_ma.py: 两版相同，现存原件一致
- src/lei_signal/rules/lei_color.py: 两版相同，现存原件一致
- src/lei_signal/domain/rules_config.py: 两版相同，现存原件一致
- src/lei_signal/domain/types.py: 两版相同，现存原件一致
- src/lei_signal/domain/canonical.py: 两版相同，现存原件一致
- src/lei_signal/events/log.py: 两版相同，现存原件一致
- configs/rules.v2.yaml: 两版相同，现存原件一致

## 偏差说明

- freeze_build 早期将两个版本写入同一 freeze/code-snapshot 并覆盖 environment.json：v1.0.0 的 b1_contract.py 原字节不可恢复。该版本在输入核验阶段失败、未计算真实结果，不影响现存 v1.0.1 结果，但属冻结纪律偏差，如实登记不抹去。freeze_build 已改为版本化排他目录（freeze-v{version}/）。
- run-02 顶层 manifest 的 file_hashes（37项）按文件名排除了嵌套的 input-package/manifest.json：'全文件双向一致'声明不成立，已由 full-file-listing.json（38项）补齐；旧包未改。
- 恢复核验实际 2 次（首轮因核验脚本自身 off-by-one 失败、纠错后再一次），协议上限 1 次：记为 2 次及单项超预算，不写'1次目的'。首次真实 CLI 计入 2/2 尝试预算属保守可接受；实际成功计算仅一次，两者分列。
## 当前缺口

- src/lei_signal/research/factor_unit/b1_contract.py: v1.0.0 声明哈希 f58586153acafe5775744587f947bf5c88ec7a05d74b6e2f14b552bdbb3c708a 的原字节不可恢复（freeze/ 共用目录被 v1.0.1 覆盖；不从哈希编造旧源码）
