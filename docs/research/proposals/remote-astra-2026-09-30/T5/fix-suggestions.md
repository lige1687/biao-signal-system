# T5 最小修复建议（未修改任何生产文件，交主负责人决定）

适用基准：`639ad8d`。证据：`docs/experiments/raw/remote-astra-T5-2026-09-30/results.json` 与 `inputs/`。

共同约束（每一条都适用）：
- **不改阈值、不改规则含义**。会改变事件集合的修复（F2、F8、F5 的事件部分）必须给对应规则升一个版本号并登记到规则账本；事件编号由 `make_event_id` 按 `rule_id + rule_version + …` 生成（`domain/canonical.py:151`），版本号一变，新事件就是新编号，不会与研究库里的旧行冲突，也不会覆盖旧行。
- **不回写旧报告、不删研究库旧行、不复活或抹掉已失效结构的历史**。对已经写进库的可疑行，只做“可识别”而不做“修改”。
- 每个修复同时保留一个“旧行为”测试，固定当前版本的输出，作为历史对照；新测试的输入可直接复制本目录 `inputs/*.json` 到 `tests/fixtures/t5/`。

## 按优先级

| # | 问题 | 最小修复 | 是否改变判定/事件 | 需要谁决定 |
|---|---|---|---|---|
| F1a | 可交易性第 9 条写死“不依赖未完成K线” | `rules/tradability_gate.py:262-265`：在完成度守卫接线前，把说明改为“未接入K线完成度判定，无法确认”，`blocked` 暂保持 `False`；接线后由调用方传入完成度，`partial/unknown` 时 `blocked=True` | 第一步只改文字；第二步会改变买点复核结论 | 第二步随 W2-S3 一并授权 |
| F1b | 盘中分析结果永久写进研究库 | `api/services.py::_run`：最后一根K线日期等于交易所当日且抓取时刻早于收盘时，调用 `analyze` 时传 `sqlite_path=None`（看盘照常，只是不入库），并在结果上标 `sqlite_persisted=None` 与原因。正式口径以 W2-S3 的“观测时刻”判定替换这一临时条件；设计稿 §2 的用途映射表补一行“`analyze()` 研究库写入 = 只接受 final” | 不改信号；改变研究库写入范围 | 主负责人（属 W2-S3 范围的补充） |
| F1c | 买点复核没有完成度标注 | `BuyPointReviewDTO` 增加 `is_intraday_forming`（复用 `card_mapper.is_intraday_forming`），前端照详情页样式显示“盘中” | 只加展示字段 | 主负责人 |
| F2 | “放量突破”事件被后来的失效删除/改挂，并引发研究库身份冲突 | `compose/pipeline.py::_build_structure_necklines`：去掉按**最终**状态 `invalidated` 排除（:81）——确认当天结构必然有效，确认日之后才会检查 C；同日多个结构确认时不再让字典覆盖（:85），改为每个结构各发一条（`source_id=f"breakout_volume:{structure_id}"`）。`volume_proxies` 升版本（例如 2.2.0） | 改变事件集合（新版本，旧版本事件保持） | 主负责人；需在规则账本登记版本差异 |
| F8 | 反转底部上的“放量突破”收盘没过颈线 | `rules/volume.py:141-148` 增加 `close > neckline` 条件，与账本 `volume_proxies.formula` 一致；与 F2 同一次升版本，变更说明分两条写 | 改变事件集合 | 同 F2 |
| F3a | 最低/最高/开盘价缺失被静默放行 | `data/validation.py::validate_bars`：对 `open/high/low` 为空的行输出警告（与收盘价缺失同格式，含日期），并让 `ValidationReport.warnings` 透到详情页（已有 `data_warnings` 通道）；`analyze_bars` 把该情况写入 `DailyAssessment.data_status`（不再恒为 `"OK"`）。是否剔除该行、整体报 `DATA_UNAVAILABLE`、或把当天 C 判定记为“未知”，三选一 | 第一步只增加可见性；第二步改变结构是否失效 | 第二步需用户选（涉及止损语义） |
| F3b | 成交量缺失被当 0 | 同处：缺失成交量单独警告，不再与负成交量同样静默置 0；改为保留空值，量比为空时量能标签记“未知”而不是“无” | 改变量能事件 | 主负责人 |
| F4a | 结构状态被直接改写、无痕 | `storage/sqlite_store.py::write_structures`：检测到状态“倒退”（`invalidated→confirmed/candidate`、`confirmed→candidate`）或失效日被清空时，不覆盖旧值也不报错静默；追加一行生命周期 `reason='recomputed_from_changed_input'`，`changed_on`=本次分析最后数据日，并在结构行增加 `last_recomputed_run_id`。是否允许覆盖“当前状态”列由用户选（见下） | 不改信号；改变研究库写法 | 覆盖与否需用户选 |
| F4b | 生命周期 `reason` 全填失效原因 | `sqlite_store.py:1438`：按转换写原因——`candidate`=`detected`，`confirmed`=`neckline_close_break`/`reversal_bar`，`invalidated`=`invalidated_reason`。只影响新写入的行 | 不改信号 | 主负责人 |
| F4c | 回放旧日改写研究库 | `api/signal_replay.py:43-46`：调用 `analyze(..., sqlite_path=None)`。回放设计只声明写 `signal_alerts`/`daily_opportunity_scan` 两表，本改动与设计一致 | 不改信号 | 主负责人 |
| F5 | 未确认候选失效也发硬卖点、且无事件 | 可追溯性（不需选择）：`apply_c_lifecycle` 对候选触 C 也发事件，`sub_rule="bottom_C_touched_in_candidate"`，`bottom_c_lifecycle` 升版本。卖点档位（需选择）：A 保持硬档；B 候选失效降为提醒档 | 新增事件类型；B 改变卖点档位 | 档位需用户选 |
| F6 | 某结构失效当天综合阶段显示“失效” | 仅显示层：`DayState.stage` 在仍有已确认有效结构时显示机会阶段，失效写在风险栏；或保持现状 | 只改显示 | 用户选 |
| F7 | 长周期不足显示“冲突” | `compose/interpreter.py::_build_dimensions`（:594）与 `_build_factors`（:366）：日、周都为 `unknown` 时维度写“数据不足”，因素标题写“长周期数据不足” | 只改显示文字 | 主负责人 |

## 对已在研究库里的旧行怎么办

- 不删、不改。F1b 生效前写入的盘中行，事后无法与收盘行区分（`run_id` 只到日期）；在研究库使用说明里写明：`run_id` 形如 `api-YYYY-MM-DD` 且 `available_date` 等于该日期的事件，可能来自盘中数据。
- F2 修复后旧版本 `volume_proxies` 事件保留原编号；用新版本做研究时按版本过滤，不与旧行合并统计。
- 已经出现 `EventIdentityConflictError` 的标的：升版本后新事件编号不同，冲突自然停止；旧冲突行保留作为证据，不清理。

## 已知问题（只引用，不在本文件重复建议）

- K1 周五盘中当周周线被标完成：交 T4 的时点字段合同；`bar-completeness-wiring-design-2026-09-20.md` §5 第 6 条需注明周线也要吃日线完成度结论。
- K2 日历未传到模块 A 周线环境：见 T2 `condition-map.md` 第 7 行；修法是 `weekly_env_series(daily, calendar=None)` 加参数并由 `analyze_bars` 一路传入，生产默认不注入日历，因此生产行为不变。
- K3 严格构造包含合并改写过去：按第十批 `repair-acceptance-handoff.md` 第 1 行执行，本次 `inputs/H10_inner_bar.json`、`H10_outer_bar.json` 可作为补充回归输入。

## 建议新增的回归测试（放 `tests/`，由主负责人加入）

1. 门禁 1 加强：多截断日比较 `structure_id`、`lifecycle_id`、`evidence`（本次 H11 的比较逻辑可直接移植），并加入 `inputs/H01_base.json`。
2. 研究库：盘中→收盘同日两次写库（H05）、修订最低价（H09a）、回补缺日（H09b）、回放（H09c），断言不出现“倒退且无记录”的状态变化。
3. 缺价：`inputs/H08a_missing_low.json` 必须产生可见警告且 `data_status != "OK"`。
4. 同一根K线触 C 与突破（`inputs/H03a_same_bar_touch_and_break.json`）：失效且不确认（当前已通过，补成测试防回退）。
5. `test_bar_completeness.py::test_signal_scan_calling_contract_gates_before_scan` 改名或补真正的接线测试——现名暗示已接线，实际只测守卫函数本身。
