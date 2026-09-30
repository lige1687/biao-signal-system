# 四项候选计算与入库阶段收口（B11，2026-09-21）

## 一句话结论（大白话）

原来计划建设的四种价格描述，都已有登记定义、可调用的计算和人工数据核对证据，可以完成“计算验证与定义入库”这一项。两项漏价含义不清的旧版由明确的新版本承接，旧版没有被改成通过。真实行情资料仍不足，不能据此判断投资效果或开始交易。

## 主控决定与授权依据

用户本轮“继续继续，开整！”，此前明确把阶段规划交给当前主控，并指定清晰执行任务优先使用Sol中等思考。本批实际使用一位内部 `gpt-5.6-sol / medium` 执行者；主控独立核关键数据、版本与完成标准。不是网页Pro决定。

原数据库标准原文为“四项已准入候选的计算验证与定义入库完成”，未写必须锁死旧1.0.0。旧B3合并记录证明四个候选ID；历史交流文档只保留第12轮摘要，本报告不冒充拥有逐字完整原裁决。主控依据当前用户授权及已核准的B9/B10版本决定，接受以下四个明确版本完成原候选交付，**不改变标准文字，也不使用自动latest别名**。

| 原候选 | 本次接受的精确版本 | 对用户意味着什么 |
|---|---|---|
| 20期抵扣价距离 | trend.cost_basis_distance20@2.0.0 | 当前价格相对20个原始输入行之前价格的位置；不是持仓成本 |
| 回调均线距离 | mixed.pullback_ma_distance@2.0.0 | 价格离六条均线最近有多远；不表示回调买点成立 |
| 六均线宽度 | trend.ma_cluster_width@1.0.0 | 六条均线分散还是靠拢；不替代突破规则 |
| 已确认摆动点距离比 | mixed.swing_rr_distance@1.0.0 | 价格相对已确认高低点的位置；不是可交易的盈亏比判定 |

前两项2.0.0是经明确缺价政策取舍的新主版本，不是1.0.0的同义改名；两张旧1.0.0仍exists。四项均仅有人工数据上的计算证据，未接真实研究runner的事实保留。原B3标准没有要求真实行情运行，该要求在B4另列；本次不把B4提前算作完成。

## 独立复核

- 118项相关单元测试通过：旧新B3-a、B3-b以及登记校验。
- B10实际精确新版本只读重演：2606行、62项边界、追加未来价格不改过去结果2606行、整体乘7不改比例2606行，全部通过。
- B3-b旧两份独立脚本的12及13个观察点重新计算，整个报告JSON与原件一致；捕获报告写入到内存，磁盘原件未写入，原指纹不变。
- 额外从旧原始夹具逐行对比实际实现与独立算法：均线宽度440行、摆动点距离80行，数值及适用的缺失原因一致；最大绝对差分别4.440892098500626e-16和0。
- 执行者只读audit通过：四项当前精确版本及旧版状态、证据路径、实现/测试/合同和历史来源哈希相符，B5原十项状态逐条相符。
- 56个受保护的既有脏源码、测试、前端、脚本及登记表文件哈希未变。登记维持1.4.1，SHA `d967e22f7f93726e1f14a5dfba84897e596d59eaa4f22574e8bccc0888bfc7e2`，86对象88版本、74 exists/14 verified；本批没有新增因子或升级卡状态。

这里的独立数值依据来自原始人工价格、明确结构输入及另一套计算，不是把被测输出当预期值。重跑旧实现/原报告只验证可复现性，另做了实际实现逐行对照；两类检查不混称新增市场证据。

## 历史引用纠错与过程记录

B5机器清单里，bias误指摆动点实现/证据，pullback误指cost证据。执行者新增纠错表，原清单保持不动；主控核实实际路径存在。伴随输入文字也应按正确卡理解：bias需要close与EMA120，不需要摆动点；pullback需要六条EMA/SMA 20/60/120，不是20行滞后。未来派发必须解析完整精确卡，不能继续消费那两条错配文字。

B5原10个精确旧引用中，目前6个verified、4个exists；四个exists包括两张被明确新版本承接但本身未通过的旧v1，以及B200宽度、200期均线距离。后两项可另立本地补证批次，不能由这份清单自动启动。

冻结前审查发现执行者初稿曾把旧v1的exists带入新v2状态，已在首次冻结前改正，audit增加精确版本状态断言。主控自己的额外核对脚本首次误以为旧pivots夹具有date字段，实际只有index/confirmed_index，产生KeyError；失败脚本保留，v2仅从同一bars对应行读日期，不改价格、确认时点或算法，随后520行全过。详见主控目录勘误。无正式返修项；后续不要用失败辅助脚本代替v2。

## 证据与复查

- 冻结合同：`docs/archive/handoffs-plans/2026-09-21-factor-b11-closure-contract.json`（研究原则v1.1、执行合同v1.0.1、定义标准v1.1.0）。
- 执行者目录：`docs/experiments/raw/factor-b11-four-candidate-closure-2026-09-21/`，含baseline、四候选对应表、B5引用纠错、下一步条件与只读audit。
- 主控目录：`docs/experiments/raw/factor-b11-controller-2026-09-21/`，含内存重演、实际520行对照、失败脚本与勘误，原件未覆盖。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 docs/experiments/raw/factor-b11-four-candidate-closure-2026-09-21/audit.py
PYTHONDONTWRITEBYTECODE=1 python3 docs/experiments/raw/factor-b11-controller-2026-09-21/replay_legacy.py
PYTHONDONTWRITEBYTECODE=1 python3 docs/experiments/raw/factor-b11-controller-2026-09-21/check_values_v2.py
PYTHONDONTWRITEBYTECODE=1 python3 docs/experiments/raw/factor-b10-v2-registration-2026-09-21/replay.py --check
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/unit/test_b3b_ma_cluster_width.py tests/unit/test_b3b_swing_rr_distance.py tests/unit/test_factor_lab_b3a_registered_v2.py tests/unit/test_factor_lab_b3a_registered.py tests/unit/test_factor_lab_b3a_factors.py tests/unit/test_research_definitions.py -q -p no:cacheprovider
python3 scripts/check_repo_hygiene.py
git diff --check
```

## ARCHIVE：完成的和没有完成的

接收执行者审计，主控决定原B3完成项可勾选；不新增“审计完成”里程碑，不把整个目标结案。台账先在v34上保留原scope追加B11 authorize为v35，独立验收后仅勾B3，实际回读v36、approved、授权有效、9/10完成。B4/R2仍暂停：以后若采用新版本，须重新明确精确卡、价格资料与运行协议，不替换旧冻结合同、输入或擅自挪用预算。

零生产代码变更、联网、真实行情新运行、预测target/IC/收益差、交易、部署或commit。自进化在本批只落到可执行检查：矩阵状态必须对精确版本、历史报告重演不得写回原件；没有自动调参、自动采纳或模型训练。

下一批优先处理已有B200宽度和200期均线距离的独立本地证据缺口，另冻结小合同；真实资料问题保留为独立尚未完成项，不因本次收口消失。
