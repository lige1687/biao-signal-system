# revision-response — round 2 限定返修对照表

job_id=abf62778-7076-4ea5-88fb-2750016ba03a round=2（2026-09-17）。
依据：`docs/experiments/factor-breadth-readiness-controller-review-2026-09-17.md` §3–§7。
round1 六份原字节已排他保存于 `history-round1/`（哈希见下），首轮历史未被覆盖。

## 0. 现场与留存

- round2 现场：分支 `codex/factor-unit-research-20260915`，HEAD
  `84db4e2d10e38ba0dcdafabf84f57fa6f4d2173b`；相对 round1 HEAD 仅一个提交
  （`84db4e2d docs: design staged external agent delegation`，两份设计文档），
  任务输入与实现未动——与主控核实一致。
- round1 六文件开改前哈希（=主控所审版本）：

| 文件 | round1 SHA-256（前 16 位） |
|---|---|
| definition-implementation-map.csv | `13448a1572653c2d` |
| delivery.md | `1c48b9d54e7ffbeb` |
| input-qualification.md | `91e9894d37cef3f5` |
| next-study-request.md | `7a83b5e1978832d7` |
| run-log.md | `cb749e574f68bb6e` |
| sources-manifest.json | `20ee33d9302d3680` |

## 1. R1 → G2/G3：收窄历史身份与资格结论

| 主控要求 | 修改位置 | 修订后表述 |
|---|---|---|
| 删"历史日期逐日查询/一天天查出来/genuinely point-in-time" | input-qualification.md §2、§一句话结论；delivery.md 一句话结论与 G2；CSV 行3/4 membership 列；manifest F4 | 统一改为「20 日探测格 + 变化区间二分 + **每日填充**；272 次查询 ≠ 2,813 天逐日核验」 |
| 682 代码只证明名单不恒定 | 同上 + input-qualification §2 | 「682>300 证明名单不恒定；不证明每一天正确、不证明当时可得」；"直接证明含历史退出成员"句删除 |
| 删"30 个变化日全部半年附近" | input-qualification.md §2 | 改为「30 个变更日=供应商查询结果；含 2015-01-26、2017-02-20、2023-03-20、2025-09-08 等非半年窗日期，原因不解释不补理由；公告逐条核对未做」 |
| B 档=旧实验自评+旧用途限定；不得以 valid 宣布够格 | input-qualification.md §一句话结论、§8 表；delivery.md 一句话结论、G2 | 「事后历史描述」裁定降为**受限的候选材料**：valid 2,378 为旧实现字段非授权；来源/成员/覆盖三重限制未消除；下一次分析须另批 |
| 低覆盖原因不归因；mtime 非抓取证明；1990 起点不单独证明倒算 | input-qualification.md §4、§6、§7 表；CSV 补充线1；manifest F6、inputs 条目、unknowns | 低覆盖「逐产品原因未核实，不统一归因」；「mtime 显示…但 mtime 不是抓取行为的证明，原始输出未归档不能补造」；timing 线「当前成分倒算」降为**相容推断、未证实** |

## 2. R2 → G1/G2：公式等价与价格来源边界

| 主控要求 | 修改位置 | 修订后表述 |
|---|---|---|
| "只差 ×100"改为有前提的公式关系+接口差异 | CSV 行1/行2 design_vs_impl 列、行3/行4 verify 描述；manifest F1；delivery.md 一句话结论与 G1 | 「有前提的公式换算关系（前提=有限正价、同一日历与成员规范，主控已确认）；接口差异：冻结入口排序+zfill6、_valid_quote_sma 仅 dropna/astype；common 入口拒绝乱序、_valid_price 要求正有限价」 |
| 撤回"B200 早年 invalid 更多" | CSV 行2 | 删除；两列共用 E200、缺失均 435 |
| qfq 路径不证明全部列同源 | input-qualification.md §4、§5；manifest F3、backfill_breadth_full 条目；delivery.md G2 | 「已见**一条** qfq 生成路径（带续传跳过）；不证明所有列由该路径/同一日期/同一复权锚产生；矛盾保留，逐列口径未追溯」 |
| 尺度不变性是条件性数学事实 | input-qualification.md §4；CSV 行1；manifest F3 | 「同一序列乘正常数不改变 P>均线，前提成立时为数学事实；**不**证明 qfq≡hfq 逐值等价、**不**证明修订无影响、**不**推出"影响有限"；本轮不追加计算」 |

## 3. R3 → G4：可追溯记录

| 主控要求 | 修改位置 | 修订后表述 |
|---|---|---|
| 补缺失当前 SHA（标注补录） | manifest 新增 `supplemental_sha_added_round2`（6 项：definitions.py、verify 脚本、两个 backfill 脚本、两个展示缓存） | 「2026-09-17 round2 返修时补录，非开工身份」；两个动态缓存「round1 内容身份不可追溯，结构统计属当时内容」 |
| 改正 fetch_constituent_prices 归属 | manifest research_engine 条目（删除错误 note）、prepare_data 条目（补 note） | 死代码在 `prepare_data.py`，不在 research_engine.py |
| 删执行者自行裁决措辞 | run-log.md 超支处置段；delivery.md G4 标题与正文 | 「是否接受由主控裁决；历史违规不因返修变合规」；round1 稿中先例引用句删除并注明系执行者越权下裁决 |
| 预算 planned/已执行同步、计数分栏、不称"从严全计" | run-log.md 数据文件账、manifest budget_statement（分 round1/round2） | 「内容/结构深读 8 份 + 仅哈希 2 份 = 触及 10 份」；「原始输出未归档，不能补造」 |
| 保护结论限于可核证据 | delivery.md G4 | 「24 项有 SHA 者逐项一致；未留开工哈希的既有脏文件原字节不变无法由当前 git 状态单独证明，仅记录未触碰操作事实」 |
| 登记用真实枚举 | delivery.md G4 | category 建议 **`数据与质量`**（round1 的 `research_prep` 系误写，更正）；本轮仍不写共享登记 |

## 4. R4 → G3：下一步请求收窄

| 主控要求 | 修改位置 | 修订后表述 |
|---|---|---|
| 一个待批准最小问题；续数/剔年份/多目标/多变化量拆为可选 | next-study-request.md 全文重写（§1 最小问题、§2 可选扩展 E1–E5） | 最小问题=冻结序列有效日上单一宽度对象与已知历史区间的描述性关系（对象由主控批准时指定）；E1 续数、E2 年份敏感性、E3 多窗口、E4 变化量、E5 分档均**独立可选、均非前置**；已有有限窗口即可研究 |
| 不称"÷100 零计算" | next-study-request.md §1；delivery.md G3 | 「一次单位转换，本轮未执行，不属于零计算；执行时须与卡口径核对」 |
| 两数据源不冒充已核等价 | next-study-request.md §3 | 「冻结序列主案 + 按卡现算复核案；两者逐值等价未核验（verify 样本仅 2 个真实交易日，其运行属真实计算本轮禁止）」 |
| 双源一致≠历史可得 | next-study-request.md §4 缺口3；input-qualification.md §6；manifest F5 | 「双源核对一致只证明内容一致，不构成当时可得性证据」 |
| 不冻结窗口/分档/收益目标、不调用真实消费者 | next-study-request.md §1/§5 | 窗口长度、评价价、目标定义留到实验冻结；不调用生产展示消费者；20/60 日、0.2/0.8 均只以"冻结时定/须另批"出现 |

## 5. round2 实际命令与结果

```
git rev-parse HEAD && git branch --show-current
→ 84db4e2d10e38ba0dcdafabf84f57fa6f4d2173b；codex/factor-unit-research-20260915 ✓

git log --oneline <round1_HEAD>..HEAD
→ 仅 84db4e2d docs: design staged external agent delegation ✓

shasum -a 256（六份 round1 文件，开改前）→ 与主控所审哈希逐项一致 ✓
cp 六文件 history-round1/（排他：目录此前不存在）✓

shasum -a 256（R3 补录 6 项）→
  definitions.py            b6d5a35532644c37…
  verify_research_definitions.py 79592e307b91decd…
  backfill_breadth_full.py  3f4805526e4e7792…
  backfill_timing_data.py   15c2cacb334ccce9…
  a_share_ma_breadth_history.json c6940ca95a601ea9…（动态缓存，round1 身份不可追溯）
  timing/breadth_csi300.parquet   0a1fd8b2f9a32c4c…（同上）

综合检查 1 批（JSON 解析/CSV 解析/禁用措辞上下文/本地链接）→
  manifest 17 顶键可解析；CSV 7 行、4 卡行、版本全 1.0.0；md 本地链接 0 条；
  措辞扫描命中 6 处经逐条核对全部为"更正说明中的自我引用"（不称零计算、
  更正从严全计、删除先例句的说明、research_prep 更正），无残留主张 ✓

python3 scripts/check_repo_hygiene.py →
  ✓ 归置自检通过：根层四层均在白名单内，关键配置均已入库。（exit 0）✓
```

## 6. round2 预算账（原预算不重置，不重记 round1）

- 新数据深读：0；结构统计脚本：0；项目回归：0；真实宽度/状态/目标/收益计算：0；
  联网/安装：0；git 写操作：0。
- 本轮新增预算：综合检查 1 批（已用 1/1）+ hygiene 1 次（已用 1/1）。
- round1 遗留违规（结构脚本 3/2）原样保留，待主控裁决。

## 7. 已知限制

- manifest `deliverables` 中五份文件哈希由本轮收尾统一回填（含本文件），
  manifest 自身哈希按构造不内嵌，由最终回报给出。
- 动态缓存的 round1 内容身份不可追溯（当时未留哈希）；本轮按预算不重读其内容。
- 下一步研究仍为草案，未获批不执行；本返修不改变任何数据用途授权。
