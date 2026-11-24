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

---

# S1–S3 最小收尾回应（execution 3 / 第二次返修，2026-09-17）

对照主控复核 §8。v2 七文件原字节存 `history-v2/`（不覆盖 history-v1）。
本轮公开访问 3/4、结构+教学算术 1/2（同一命令内完成）、hygiene 1/1。

## S1（精确接口）

1. **optimal_block_length 返回列名**：已按主控给的固定源码亲自核验——
   arch **v8.0.0** `arch/bootstrap/base.py` 返回语句
   `return pd.DataFrame(opt, index=idx, columns=["stationary", "circular"])`。
   CSV A4 与卡2"检查建议"已改为实际列名 `stationary`/`circular`，并注明
   docstring 旧名 b_sb/b_cb 与实现不一致、以源码为准。
2. **statsmodels 版本固定**：钉 **v0.15.0**（GitHub 最新 release tag；文档
   站 stable 页自称 0.15.0，两者一致）。补读 v0.15.0 tag 源码核对
   `cov_hac_simple`（cov_hac 即其别名）签名与 `weights_bartlett`，与文档
   一致。A1 证据改为 tag 源码；A2（get_robustcov_results）如实降级标注
   "仅文档级核对"，不再笼统声称源码级。
3. **A5 收窄为 SPA**：删去 StepM/MCS 的混用接口描述，仅保留 SPA 的输入、
   H0、consistent p 值说明；StepM/MCS 标注为"不同方法不同假设，本轮未核"。

## S2（试点规格）

1. **教学表重写为最小确定例**：factor 只在 d1、prices 完整 d1–d4、
   periods=(1,3)；逐项给出唯一手算值（IC₁=IC₃=+1.0，1期收益 +10%/+5%/−5%，
   3期 +30%/+20%/−15%，有效键数=3/日）。删除"6天表只给4天"的不完整承诺。
2. **特征/目标混用更正**：撤回"本地动量对象窗口 t+1→t+22"——那是 B1 的
   未来目标窗口；`mixed.momentum.raw@1.0.0` 是过去窗口特征
   I(t−21)/I(t−252)−1。试点中特征（过去）与未来目标（t→t+h）分开表述。
3. **并列例改为唯一预期**：4 标的 (4,3,3,1)+quantiles=2，断点 3.0 不与
   箱边界重复 → 唯一预期"正常两组、并列同组不抛异常"；并注明 3 标的
   (3,3,1) 因中位断点与最大值并列必抛异常，两例各自唯一。
4. **缺价例给版本条件与两分支预期**（pandas≥3.x NaN 传播 / <2.1 'pad'
   填充），并明示"未钉版本前为条件规格，不称可直接执行"。
5. **方法卡1** 小写 x 定义为"逐期设计行×当期残差"的向量序列，不再可能
   被误读为只用设计矩阵。**卡2 Stationary 教学例**改为给定前提输入
   （起点、重启判定序列）的完整展开算术，期望索引 [1,2,3,3,4,5] 可独立
   复算；如实声明验证的是展开规则、不声称已复算 arch 的 RNG。
6. 试点维持**暂缓**；"3 标的、分数互不相同"明示为教学例选择，非工具
   通用必要条件。

## S3（同步与实账）

1. **CSV C2 起点冲突**：删去误带的市场因子 1926-07；C2 只写动量详情页
   口径 1927-01（C1 市场因子 1926-07 保留）。
2. **hygiene 实账**：execution 2 实际**调用两次、成功一次**（首次 cwd 在
   提案目录路径不存在；立即换根目录重跑成功）。台账由"1/1"改为"尝试 2、
   成功 1"。结构检查口径改为按实际命令调用描述。
3. **访问时刻撤回**：v2 台账中"~13:35–13:43"为猜测，与派发时间不符，
   已撤回；工具侧无法恢复精确时刻，v2/v3 台账时刻字段一律改"未知
   （会话时钟未记录，无法从工具记录恢复）"。
4. **同步指纹**：README 升 v3 说明、sources-and-checks.json 全量重写
   （含 history-v2 身份、本轮命令实账与五文件新 SHA）。

## 本轮证据命令

- fetch×3：arch v8.0.0 base.py（返回列名）、statsmodels releases（v0.15.0）、
  statsmodels v0.15.0 tag sandwich_covariance.py（签名/权重）。
- 结构+教学算术：**命令 2 次（限额用满，两次均暴露检查脚本自身笔误）**——
  两次 CSV 结构校验均通过（11 行全 9 列）；脚本初稿把卡2例 u₅=0.30 误当
  继续（0.30<0.50 实为重启），先后触发 StopIteration/IndexError。该笔误
  同时存在于卡2初稿，已由检查发现并修正（u₅ 改 0.60，展开唯一
  [1,2,3,3,4,5]）；试点例收益/断点数值为直接手算（10→11 即 +10% 等），
  未再耗命令。
- hygiene 1 次：repo 根目录执行通过。
