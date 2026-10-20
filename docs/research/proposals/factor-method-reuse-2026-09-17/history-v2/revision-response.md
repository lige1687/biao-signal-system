# R1–R4 返修逐项回应（execution 2 / attempt repair）

对照 `docs/experiments/factor-method-reuse-controller-review-2026-09-17.md`
§3–§6。原则：复核事实与源码不符时以固定版本源码为准并说明；v1 原件存
`history-v1/`；返修新增公开访问 7/12、结构检查 1/3、hygiene 1/1。

## R1（表格与现有能力）

1. **CSV 列数**：v1 的 A2（10列）、B1（11列）已修；v2 全部数据行 9 列，
   `python3 csv.reader` 逐行校验通过（见 sources-and-checks 命令实账）。
   逐行重写而非机械删引号，字段语义重新核对（A2 的参数名差异、B1 的
   逐入口默认均保留在"关键默认与差异"列）。
2. **definitions.v1.json SHA 已补**：
   `c008efb991c40f06bb7fe0236b0892a6902c68a83cb4657ae5c2651e9d270e05`
   （registry version 1.2.0）。
3. **A3 撤回"无本地实现"**：capability-reuse.csv A3 改为如实记录
   `factor_evidence/resampling.py` 的 `circular_indices`+`paired_block_deltas`
   （固定块长、绕回开头、PCG64 定种子、同一索引用于三列），已在
   factor-evidence-reliability-v1 真实使用；缺口限定为"外部 Stationary
   （随机重启块长）形式未接入"。
4. **卡2"既有真实结果：无"已限定**：改为"外部 Stationary 形式 0 次；本地
   循环分块形式已真实使用"。
5. **"无本地HAC实现"改为限定表述**："本轮检查范围内未见…；models=[] 只说明
   未登记风险模型，不证明不存在其他能力"（A1/A2）。
6. **Alphalens 推荐理由重构**：不再引用旧短名单排名；next-pilot-proposal
   明确当前**无已冻结的同日多ETF排序问题**，结论降级为**暂缓**并给出触发
   条件。未新增任何执行。

## R2（版本与 Alphalens 语义）

1. **版本钉死 tag 0.4.5**：返修轮直接抓取
   `raw.githubusercontent.com/.../0.4.5/src/alphalens/{utils,performance}.py`
   逐项核对，撤回 main 概括。逐入口默认分列：`get_clean_factor_and_
   forward_returns` filter_zscore=20；`compute_forward_returns` 单独调用
   =None；`get_clean_factor` 无该参数（CSV B1、README 已分列）。
2. **B3 错误因果撤回**：qcut 遇重复边界抛 ValueError（装饰器改写为建议性
   报错）、no_raise 路径返回空 Series——不会把同值硬拆成假高低组。保留
   "同日共同宽度值无横截面离散度"的适用性限制，B3 决定由"禁用"改为
   "暂缓（非整个库永久禁用）"。
3. **demeaned/时区/日历/权重分开描述**（CSV B2 + 试点）：demeaned=True=
   前向收益减同日横截面均值（对比口径）≠完整多空账户；factor_weights 才
   是减均值+绝对值和归一的 dollar-neutral 权重（equal_weight 为±1 各除
   数量）；时区是两输入一致性检查（NonMatchingTimezoneError），不是自动
   猜发布时间；日历推断（infer_trading_calendar）单列。
4. **索引层名 date/asset 如实列出**：工具显式 rename；本地 symbol 须薄适配
   改名并在协议登记（试点输入合同）。
5. **端点语义**：工具 t→t+h（pct_change(h) 后 shift(-h)）vs 本地 t+1→t+22
   行位移，试点中分列。缺报价行为改为"由 pandas 版本决定"：pandas 3.x
   fill_method 固定 None（NaN 传播），更早版本默认 'pad' 前向填充——须钉
   版本后写死，不预设"自动剔除"。
6. **max_loss=0 冲突拆分**：常数/并列负例（预期抛 "Bin edges must be
   unique"）与末端不完整负例（可能整体 MaxLossExceededError）拆成不同
   入口/子样例，撤回"完整流程返回缺失 IC"的矛盾承诺。
7. **手算例补具体数字**：6日×3标的价格/分数表、d1 一期收益 +10%/+5%/−5%、
   IC=+1.0、反向 −1.0、尺度不变 +1.0，均可独立复算；未执行任何库。
8. **合成验证边界**：限定为"0.4.5 在合成小例上的行为一致"，不推广为真实
   数据资格，也不一概否认有限合成兼容性验证的价值。

## R3（方法卡纠错）

1. **书目**：改为 NBER t0055 工作论文 1986-04；正式发表 Econometrica
   **55(3), 1987-05, 703–708**（据 NBER 页，返修新增访问）。未读原文继续
   明示；"作者结论"标注为文档/源码转述。
2. **Bartlett 权重算式纠正**：nlags=4 时权重 = 1−l/5，l=0..4 =
   1、0.8、0.6、0.4、0.2（按 statsmodels 源码 `1 - np.arange(nlags+1)/
   (nlags+1.0)` 核对，返修新增源码访问）。同时纠正"必然低估"表述：方向
   取决于残差自相关结构。
3. **Stationary 段长措辞**：按 arch 8.0.0 源码改为"逐步以概率 1/block_size
   重启 → 几何分布的离散段"；文档页 "expon distributed" 与实现分栏。8.0.0
   签名只有 seed、无 random_state——旧文档页所记 random_state 弃用属更早
   版本，版本差异留痕（卡2）。重启逻辑在编译采样器内，本轮只核到输入
   （候选起点、u、p），采样器本体未逐行读——如实标注。
4. **"完全不能替代"撤回**：改为"不同算法，可作为同一统计问题的两种不确定
   性估计并存报告（如跨日 IC 均值），前提与估计目标分清、结果不相加"。
5. **optimal_block_length 文档符号 vs 返回列名**（c_i 与 b_sb/b_cb）分栏
   记录（CSV A4）。

## R4（外部因子与本地定义）

1. **起点纠正**：Mkt-RF 月度自 **1926-07** 起（f-f_factors 详情页，返修新增
   访问）；入选条件精确化（月初 share code 10/11、期初股价股数良好、当月
   收益良好），不泛称全部美股；RF 来源 2024-05 前 Ibbotson、2024-06 起
   ICE BofA——来源变化如实记录；单位 unknown 保留。
2. **Mom 无风险项**：构造公式即高减低组合，**无额外再减 RF**（从 unknown
   改为明确）；单位与发布时点仍 unknown 另列。
3. **raw/rank/benchmark/宽度分列**：对照表加 mixed.momentum.rank@1.0.0
   独立列；raw 列不再塞排序/并列规则；宽度单位=无量纲 fraction（底层资产
   人民币计价另列，不填"币种=人民币"）；benchmark 点名
   `benchmark.etf.price_sma50_binary_account@1.0.0`，单位写全
   （账户金额与持仓路径 account_path）。
4. **冻结≠静态**：新增第五条线——定义冻结不等于输入历史不可修订，取得日
   不代替当时可知日；跨币种因子解释用途改为"需模型裁定"，不作永久禁用
   宣言。

## 未解决/仍未知（如实）

- alphalens 0.4.5 LICENSE 文件、arch/statsmodels 许可原文未核（unknown）。
- arch 8.0.0 采样器本体（编译代码）未逐行读；statsmodels/arch 发布版号
  未钉（文档站/源码页口径）。
- French 数据使用条款、单位、发布时点：未核/未标注处保留 unknown。
- pandas 版本未钉（执行时再定），缺报价行为因此不预设。
