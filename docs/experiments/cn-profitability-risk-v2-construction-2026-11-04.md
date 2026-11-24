# A股盈利组合V2：小行业修正、波动过滤与持仓缓冲

**四项建议已经落实并检验。更值得保留的研究候选是“细行业内过滤＋70／85缓冲”，但尚未证实稳定超额，暂不新增前向账户。** 25bp费用情景下，它相对修正后的盈利基准每月多0.060个百分点，95%描述区间为[-0.109, +0.228]；IR由0.217变成0.339，已观测片段最深相对回撤由12.55%缩小至9.16%。同时超额波动更高、最长相对水下期更长，并非全面改善。

小行业统一比例选股已成为新的研究对照；合并行业则没有自动提高质量，反而带来明显的细行业权重偏离。因此保留旧版可比结果，以**细行业盈利V2**作为后续研究基准；合并门类只保留为对照，不替换生产规则。

范围：2015—2025年，原2014年固定600股样本中的563只合格非金融股票，31,872个股月。132个月保留目标持仓；毛收益共同完整127月，计持仓漂移费用需当月及前月资料完整，共122月。基准是同池等权，沪深300等母指数超额未评价。五个公司行动缺口未填零；这是已看过历史的报价情景研究，行业快照的历史可得性、实际成交及完整公司行动链仍有限制。

## 1. 金融含义与可执行研究规则

盈利使用**毛利润／总资产（GP/assets）**，描述资产产生毛利的能力，不等同于净利润、经营现金流或可直接兑现的股东回报。同细行业比较有助于限制资本密集度差异；波动过滤是假设极端波动股票包含更多投机、脆弱经营或流动性风险，缓冲则检验减少阈值附近反复换股是否有帮助。当前结果只能检验这种结构的收益与代价，尚不能确认“赚的是彩票偏好者的钱”或已经识别错误定价。

新研究规则：每月在原合格池中按财报时点筛资格，细行业内选毛利资产比前20%，数量向上取整，行业资金仍为原股票数占比。过滤版先按过去60日**总波动**排除高端股票，再按盈利排序，选股名额按过滤前行业数量计算。新入候选须在低波前70%，已有目标持仓可放宽至85%，但财报资格、股票池或盈利排名失效仍退出。旧持仓不享受盈利排名豁免。

整数边界按低波排序前 `max(1, floor(比例×组内股票数))` 个处理，并列按代码排序。单股行业保留该股，并明确它没有同行选择能力；因此名义30%不等于每月恰好剔除30%。细行业无缓冲平均实际排除34.81%，加缓冲后32.69%。这是研究目标持仓规则；停牌、涨跌停和未成交的实际持仓状态尚未接入。

缓冲思路借鉴机构指数对新选入和已有成分使用不同保留条件的实践，70／85为本地固定检验值，并非机构保证有效的参数。[MSCI Quality方法，2014版§3.1.1及附录VII](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Quality_Indexes_Meth_Aug14.pdf)

## 2. 先拆开小行业修正与行业合并

下表保留原127个共同完整月，方便与旧报告比较；这里尚未扣费。

| 规则 | 超额月均（百分点） | TE（年化） | IR | 细行业权重绝对偏差合计 |
| --- | --- | --- | --- | --- |
| 旧盈利规则 | 0.075 | 4.20% | 0.215 | 0.00% |
| 细行业盈利V2 | 0.087 | 4.60% | 0.226 | 0.00% |
| 合并门类盈利 | 0.066 | 6.74% | 0.118 | 68.68% |


统一比例只将“不足5股全保留”改为同样的向上取整20%：相对旧盈利每月仅多0.011个百分点，区间[-0.033,+0.098]。原31.32%未筛选权重不能全部叫作坏股票；修正后仍有平均6.82%的资金位于只有1只股票的细行业，其余2—4股组会选1只。不能把定义更一致说成已经获得显著超额。

合并到CSRC首字母门类使单股门类权重降至1.14%，却放开了门类内部的细行业配置：权重绝对偏差合计68.68%，对应半和口径34.34%。TE从细行业版4.60%升到6.74%，毛IR下降。制造业内部企业的资本强度差异仍然存在，合并并不等于更精确的盈利比较。首字母门类映射依据2012分类规则；年度快照代理的时点限制继续保留。[证监会2012行业分类指引§3.1、§6](https://www.csrc.gov.cn/csrc/c100024/c1492226/1492226/files/5f2288e304bf41bc9238c19bcfbdd0af.pdf)

因此在预先登记的门类比较之外，增加了一次同30%、同70／85、保持细行业资金比例的补充对照。该补充是在观察到行业合并混杂之后设计，明确属于事后诊断；没有新增阈值或把旧历史称为新样本。

## 3. 同一122个月，比较费用后的策略表现

月度主动收益＝策略费用情景收益−同池费用情景收益；TE是主动收益标准差乘√12，IR是主动月均／主动月波动乘√12。频率缩放不是复利年化，也未消除月度自相关；主动收益仍可能包含Beta、规模或风格偏离，不能直接称独立Alpha。

25bp＝每1元买入或卖出金额收0.0025元，买卖合计计费。逐股持仓先随上月涨跌漂移，包含退出股票和现金；费用从组合资金支付，再计算本月报价回报。策略和基准均按自己的交易量收费，初始建仓计费，末期不另假设清仓。未模拟实际税费、最低佣金、价差、冲击和成交失败，所以表中是**费用假设情景**，不是个人账户实得净收益。

| 方法 | 费用后超额月均（百分点） | 费前IR（同122月） | 25bp IR | 50bp IR | 25bp TE |
| --- | --- | --- | --- | --- | --- |
| 细行业盈利V2 | 0.083 | 0.291 | 0.217 | 0.143 | 4.62% |
| 全池过滤30% | 0.082 | 0.369 | 0.181 | -0.007 | 5.40% |
| 全池过滤＋缓冲 | 0.075 | 0.287 | 0.170 | 0.052 | 5.30% |
| 细行业过滤30% | -0.003 | 0.212 | -0.008 | -0.226 | 5.04% |
| 细行业过滤＋缓冲 | 0.144 | 0.499 | 0.339 | 0.179 | 5.09% |
| 相同过滤资格内行业等权 | 0.037 | 0.385 | 0.157 | -0.069 | 2.84% |


**硬过滤并非越细越好。** 无缓冲的细行业过滤比盈利基准差，25bp情景下IR约为零；加入缓冲后才出现更好的样本表现。全池过滤加缓冲虽然也减少交易，费后IR却没有提高。不能把缓冲当作普遍保住收益的保证。

核心批中，合并门类后的全池过滤／全池缓冲／门类过滤／门类缓冲，25bp IR分别为0.242／0.229／0.191／0.256，TE分别为6.82%／7.05%／6.72%／6.99%。行业内过滤没有把TE压到4%以下。

## 4. 相对已有方法到底增加了多少

| 增量问题 | 费用后月均差（百分点） | 95%描述区间 | IR差 |
| --- | --- | --- | --- |
| 组合相对盈利基准 | 0.060 | [-0.109, 0.228] | 0.122 |
| 细行业过滤加入缓冲 | 0.147 | [0.001, 0.290] | 0.346 |
| 无缓冲：细行业替代全池排序 | -0.085 | [-0.238, -0.005] | -0.189 |
| 全池过滤加入缓冲 | -0.007 | [-0.159, 0.105] | -0.011 |
| 过滤后再用盈利排序 | 0.106 | [-0.022, 0.345] | 0.181 |


区间使用12个月日历分块、2,000次配对重采样，保留缺月位置；没有校正全部历史尝试。细行业缓冲相对无缓冲的均值区间刚高于零，但IR差区间[-0.043,+0.634]仍跨零，且补充方案是事后选择，不能据此宣布发现稳定Alpha。最关键的“组合相对盈利基准”区间仍包含损害和改善。

细行业盈利与缓冲组合的25bp总收益相关为0.993，主动收益相关为0.754。总收益相关继续只描述共同市场涨跌；主动相关显示这两者仍高度共享选股优势，不能把改良版算成一套全新、低相关的收益来源。

## 5. 缓冲节省了什么，又付出了什么

| 方法 | 月均买卖金额／期初资产（含漂移） | 波动资格失效退出次数 | 盈利排序退出次数 | 共享持仓目标再平衡 |
| --- | --- | --- | --- | --- |
| 全池过滤30% | 55.93% | 842 | 727 | 6.67% |
| 全池过滤＋缓冲 | 42.94% | 340 | 609 | 7.17% |
| 细行业过滤30% | 58.81% | 1063 | 622 | 6.53% |
| 细行业过滤＋缓冲 | 49.19% | 679 | 596 | 6.98% |


细行业加入缓冲后，含漂移交易量从58.81%降到49.19%，相对减少16.4%；但仍高于纯盈利的33.63%。同一122月，收益差中约0.123个百分点来自持仓选择变化，约0.024个百分点来自费用影响变化；改善主要不只是省费用。退出次数基于132个月的目标持仓事件，不能当作独立样本或实际成交次数；盈利退出指排名／名额失去资格，不代表企业基本面一定恶化。共享持仓变动不含漂移，不能与左列直接相加。

| 风险与账户表现 | 细行业盈利V2 | 细行业过滤＋缓冲 |
| --- | --- | --- |
| 月均费用后报价收益 | 1.287% | 1.347% |
| 年化总波动 | 29.71% | 29.12% |
| Sharpe（无风险利率假设0） | 0.520 | 0.555 |
| 年化超额波动TE | 4.62% | 5.09% |
| 片段内最深相对回撤 | -12.55% | -9.16% |
| 片段内最深绝对回撤 | -46.09% | -48.71% |
| 最长已观测相对水下期 | 23个月 | 34个月 |
| 最高单股目标权重 | 3.50% | 3.50% |


相对回撤用 `∏(1+策略收益)/∏(1+同池收益)` 的峰谷跌幅，未将主动收益连乘。费用资料可核的五个连续片段分别独立起算；上述回撤和水下期都不是完整十一年指标。缓冲组合最深相对回撤发生于2023-08—2025-12片段，2024-12见峰、截至2025-12未恢复，已观察12个月；更长的34个月相对水下期发生在早期片段。它在绝对回撤和恢复等待上没有同时获胜。

## 6. 七档参数曲线：30%没有独特跃升

以下是**预先固定的门类内、无缓冲版本**，七档全部保留，同用122个月；不能移作细行业缓冲版的参数稳定性证明。

| 名义剔除 | 实际排除均值 | 费前IR | 25bp IR | 50bp IR | 月均买卖金额占比 |
| --- | --- | --- | --- | --- | --- |
| 10% | 12.71% | 0.351 | 0.280 | 0.208 | 38.66% |
| 15% | 17.45% | 0.334 | 0.250 | 0.166 | 41.42% |
| 20% | 21.84% | 0.326 | 0.232 | 0.139 | 43.87% |
| 25% | 26.73% | 0.300 | 0.199 | 0.099 | 45.94% |
| 30% | 32.23% | 0.313 | 0.191 | 0.070 | 49.22% |
| 35% | 37.42% | 0.317 | 0.186 | 0.056 | 51.79% |
| 40% | 41.60% | 0.364 | 0.224 | 0.083 | 54.00% |


取整使实际排除比例偏离名义阈值；七档平均入选数都约55.13只，选择名额保持一致，换的是名字。30%没有形成独有的高点，费用会明显改变曲线；不据样本中最高IR转用10%或40%。多次比较增加偶然胜出的机会，历史参数曲线无法代替独立证据。[Bailey等：The Probability of Backtest Overfitting，2015](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)

<svg style="max-width:100%;height:auto" xmlns:xlink="http://www.w3.org/1999/xlink" width="864" height="432" viewBox="0 0 720 360" xmlns="http://www.w3.org/2000/svg" version="1.1">
 <metadata>
  <rdf:RDF xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:cc="http://creativecommons.org/ns#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
   <cc:Work>
    <dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage"/>
    <dc:date>2026-11-04T00:53:50.647809</dc:date>
    <dc:format>image/svg+xml</dc:format>
    <dc:creator>
     <cc:Agent>
      <dc:title>Matplotlib v3.11.2, https://matplotlib.org/</dc:title>
     </cc:Agent>
    </dc:creator>
   </cc:Work>
  </rdf:RDF>
 </metadata>
 <defs>
  <style type="text/css">*{stroke-linejoin: round; stroke-linecap: butt}</style>
 </defs>
 <g id="figure_1">
  <g id="patch_1">
   <path d="M 0 360 
L 720 360 
L 720 0 
L 0 0 
z
" style="fill: #ffffff"/>
  </g>
  <g id="axes_1">
   <g id="patch_2">
    <path d="M 58.40125 296.955 
L 708.12 296.955 
L 708.12 29.496 
L 58.40125 29.496 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_1">
    <g id="xtick_1">
     <g id="line2d_1">
      <defs>
       <path id="mda637afcf0" d="M 0 0 
L 0 3.5 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#mda637afcf0" x="87.93392" y="296.955" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_1">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: middle" x="87.93392" y="313.635" transform="rotate(-0 87.93392 313.635)">10</text>
     </g>
    </g>
    <g id="xtick_2">
     <g id="line2d_2">
      <g>
       <use xlink:href="#mda637afcf0" x="186.376155" y="296.955" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_2">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: middle" x="186.376155" y="313.635" transform="rotate(-0 186.376155 313.635)">15</text>
     </g>
    </g>
    <g id="xtick_3">
     <g id="line2d_3">
      <g>
       <use xlink:href="#mda637afcf0" x="284.81839" y="296.955" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_3">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: middle" x="284.81839" y="313.635" transform="rotate(-0 284.81839 313.635)">20</text>
     </g>
    </g>
    <g id="xtick_4">
     <g id="line2d_4">
      <g>
       <use xlink:href="#mda637afcf0" x="383.260625" y="296.955" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_4">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: middle" x="383.260625" y="313.635" transform="rotate(-0 383.260625 313.635)">25</text>
     </g>
    </g>
    <g id="xtick_5">
     <g id="line2d_5">
      <g>
       <use xlink:href="#mda637afcf0" x="481.70286" y="296.955" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_5">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: middle" x="481.70286" y="313.635" transform="rotate(-0 481.70286 313.635)">30</text>
     </g>
    </g>
    <g id="xtick_6">
     <g id="line2d_6">
      <g>
       <use xlink:href="#mda637afcf0" x="580.145095" y="296.955" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_6">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: middle" x="580.145095" y="313.635" transform="rotate(-0 580.145095 313.635)">35</text>
     </g>
    </g>
    <g id="xtick_7">
     <g id="line2d_7">
      <g>
       <use xlink:href="#mda637afcf0" x="678.58733" y="296.955" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_7">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: middle" x="678.58733" y="313.635" transform="rotate(-0 678.58733 313.635)">40</text>
     </g>
    </g>
    <g id="text_8">
     <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: middle" x="383.260625" y="328.635" transform="rotate(-0 383.260625 328.635)">名义高波剔除比例（%）</text>
    </g>
   </g>
   <g id="matplotlib.axis_2">
    <g id="ytick_1">
     <g id="line2d_8">
      <path d="M 58.40125 289.244029 
L 708.12 289.244029 
" clip-path="url(#p053c36b571)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_9">
      <defs>
       <path id="m9849aa6027" d="M 0 0 
L -3.5 0 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#m9849aa6027" x="58.40125" y="289.244029" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_9">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="51.40125" y="294.084029" transform="rotate(-0 51.40125 294.084029)">0.05</text>
     </g>
    </g>
    <g id="ytick_2">
     <g id="line2d_10">
      <path d="M 58.40125 249.846683 
L 708.12 249.846683 
" clip-path="url(#p053c36b571)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_11">
      <g>
       <use xlink:href="#m9849aa6027" x="58.40125" y="249.846683" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_10">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="51.40125" y="254.686683" transform="rotate(-0 51.40125 254.686683)">0.10</text>
     </g>
    </g>
    <g id="ytick_3">
     <g id="line2d_12">
      <path d="M 58.40125 210.449337 
L 708.12 210.449337 
" clip-path="url(#p053c36b571)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_13">
      <g>
       <use xlink:href="#m9849aa6027" x="58.40125" y="210.449337" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_11">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="51.40125" y="215.289337" transform="rotate(-0 51.40125 215.289337)">0.15</text>
     </g>
    </g>
    <g id="ytick_4">
     <g id="line2d_14">
      <path d="M 58.40125 171.05199 
L 708.12 171.05199 
" clip-path="url(#p053c36b571)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_15">
      <g>
       <use xlink:href="#m9849aa6027" x="58.40125" y="171.05199" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_12">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="51.40125" y="175.89199" transform="rotate(-0 51.40125 175.89199)">0.20</text>
     </g>
    </g>
    <g id="ytick_5">
     <g id="line2d_16">
      <path d="M 58.40125 131.654644 
L 708.12 131.654644 
" clip-path="url(#p053c36b571)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_17">
      <g>
       <use xlink:href="#m9849aa6027" x="58.40125" y="131.654644" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_13">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="51.40125" y="136.494644" transform="rotate(-0 51.40125 136.494644)">0.25</text>
     </g>
    </g>
    <g id="ytick_6">
     <g id="line2d_18">
      <path d="M 58.40125 92.257298 
L 708.12 92.257298 
" clip-path="url(#p053c36b571)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_19">
      <g>
       <use xlink:href="#m9849aa6027" x="58.40125" y="92.257298" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_14">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="51.40125" y="97.097298" transform="rotate(-0 51.40125 97.097298)">0.30</text>
     </g>
    </g>
    <g id="ytick_7">
     <g id="line2d_20">
      <path d="M 58.40125 52.859952 
L 708.12 52.859952 
" clip-path="url(#p053c36b571)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="line2d_21">
      <g>
       <use xlink:href="#m9849aa6027" x="58.40125" y="52.859952" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_15">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="51.40125" y="57.699952" transform="rotate(-0 51.40125 57.699952)">0.35</text>
     </g>
    </g>
    <g id="text_16">
     <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: middle" x="21.759219" y="163.2255" transform="rotate(-90 21.759219 163.2255)">信息比率 IR</text>
    </g>
   </g>
   <g id="line2d_22">
    <path d="M 87.93392 52.132933 
L 186.376155 65.212056 
L 284.81839 71.967038 
L 383.260625 92.594607 
L 481.70286 82.289815 
L 580.145095 79.013452 
L 678.58733 41.653227 
" clip-path="url(#p053c36b571)" style="fill: none; stroke: #2563eb; stroke-width: 2; stroke-linecap: square"/>
    <defs>
     <path id="m727890cc96" d="M 0 3 
C 0.795609 3 1.55874 2.683901 2.12132 2.12132 
C 2.683901 1.55874 3 0.795609 3 0 
C 3 -0.795609 2.683901 -1.55874 2.12132 -2.12132 
C 1.55874 -2.683901 0.795609 -3 0 -3 
C -0.795609 -3 -1.55874 -2.683901 -2.12132 -2.12132 
C -2.683901 -1.55874 -3 -0.795609 -3 0 
C -3 0.795609 -2.683901 1.55874 -2.12132 2.12132 
C -1.55874 2.683901 -0.795609 3 0 3 
z
" style="stroke: #2563eb"/>
    </defs>
    <g clip-path="url(#p053c36b571)">
     <use xlink:href="#m727890cc96" x="87.93392" y="52.132933" style="fill: #2563eb; stroke: #2563eb"/>
     <use xlink:href="#m727890cc96" x="186.376155" y="65.212056" style="fill: #2563eb; stroke: #2563eb"/>
     <use xlink:href="#m727890cc96" x="284.81839" y="71.967038" style="fill: #2563eb; stroke: #2563eb"/>
     <use xlink:href="#m727890cc96" x="383.260625" y="92.594607" style="fill: #2563eb; stroke: #2563eb"/>
     <use xlink:href="#m727890cc96" x="481.70286" y="82.289815" style="fill: #2563eb; stroke: #2563eb"/>
     <use xlink:href="#m727890cc96" x="580.145095" y="79.013452" style="fill: #2563eb; stroke: #2563eb"/>
     <use xlink:href="#m727890cc96" x="678.58733" y="41.653227" style="fill: #2563eb; stroke: #2563eb"/>
    </g>
   </g>
   <g id="line2d_23">
    <path d="M 87.93392 108.210065 
L 186.376155 131.660446 
L 284.81839 145.45577 
L 383.260625 171.685679 
L 481.70286 178.26942 
L 580.145095 182.112575 
L 678.58733 152.492395 
" clip-path="url(#p053c36b571)" style="fill: none; stroke: #047857; stroke-width: 2; stroke-linecap: square"/>
    <defs>
     <path id="mf78124e122" d="M 0 3 
C 0.795609 3 1.55874 2.683901 2.12132 2.12132 
C 2.683901 1.55874 3 0.795609 3 0 
C 3 -0.795609 2.683901 -1.55874 2.12132 -2.12132 
C 1.55874 -2.683901 0.795609 -3 0 -3 
C -0.795609 -3 -1.55874 -2.683901 -2.12132 -2.12132 
C -2.683901 -1.55874 -3 -0.795609 -3 0 
C -3 0.795609 -2.683901 1.55874 -2.12132 2.12132 
C -1.55874 2.683901 -0.795609 3 0 3 
z
" style="stroke: #047857"/>
    </defs>
    <g clip-path="url(#p053c36b571)">
     <use xlink:href="#mf78124e122" x="87.93392" y="108.210065" style="fill: #047857; stroke: #047857"/>
     <use xlink:href="#mf78124e122" x="186.376155" y="131.660446" style="fill: #047857; stroke: #047857"/>
     <use xlink:href="#mf78124e122" x="284.81839" y="145.45577" style="fill: #047857; stroke: #047857"/>
     <use xlink:href="#mf78124e122" x="383.260625" y="171.685679" style="fill: #047857; stroke: #047857"/>
     <use xlink:href="#mf78124e122" x="481.70286" y="178.26942" style="fill: #047857; stroke: #047857"/>
     <use xlink:href="#mf78124e122" x="580.145095" y="182.112575" style="fill: #047857; stroke: #047857"/>
     <use xlink:href="#mf78124e122" x="678.58733" y="152.492395" style="fill: #047857; stroke: #047857"/>
    </g>
   </g>
   <g id="line2d_24">
    <path d="M 87.93392 164.39959 
L 186.376155 198.198684 
L 284.81839 218.906624 
L 383.260625 250.537942 
L 481.70286 273.718269 
L 580.145095 284.797773 
L 678.58733 262.853799 
" clip-path="url(#p053c36b571)" style="fill: none; stroke: #b45309; stroke-width: 2; stroke-linecap: square"/>
    <defs>
     <path id="m95af9a57fc" d="M 0 3 
C 0.795609 3 1.55874 2.683901 2.12132 2.12132 
C 2.683901 1.55874 3 0.795609 3 0 
C 3 -0.795609 2.683901 -1.55874 2.12132 -2.12132 
C 1.55874 -2.683901 0.795609 -3 0 -3 
C -0.795609 -3 -1.55874 -2.683901 -2.12132 -2.12132 
C -2.683901 -1.55874 -3 -0.795609 -3 0 
C -3 0.795609 -2.683901 1.55874 -2.12132 2.12132 
C -1.55874 2.683901 -0.795609 3 0 3 
z
" style="stroke: #b45309"/>
    </defs>
    <g clip-path="url(#p053c36b571)">
     <use xlink:href="#m95af9a57fc" x="87.93392" y="164.39959" style="fill: #b45309; stroke: #b45309"/>
     <use xlink:href="#m95af9a57fc" x="186.376155" y="198.198684" style="fill: #b45309; stroke: #b45309"/>
     <use xlink:href="#m95af9a57fc" x="284.81839" y="218.906624" style="fill: #b45309; stroke: #b45309"/>
     <use xlink:href="#m95af9a57fc" x="383.260625" y="250.537942" style="fill: #b45309; stroke: #b45309"/>
     <use xlink:href="#m95af9a57fc" x="481.70286" y="273.718269" style="fill: #b45309; stroke: #b45309"/>
     <use xlink:href="#m95af9a57fc" x="580.145095" y="284.797773" style="fill: #b45309; stroke: #b45309"/>
     <use xlink:href="#m95af9a57fc" x="678.58733" y="262.853799" style="fill: #b45309; stroke: #b45309"/>
    </g>
   </g>
   <g id="line2d_25">
    <path d="M 58.40125 192.865955 
L 708.12 192.865955 
" clip-path="url(#p053c36b571)" style="fill: none; stroke-dasharray: 5.55,2.4; stroke-dashoffset: 0; stroke: #64748b; stroke-width: 1.5"/>
   </g>
   <g id="patch_3">
    <path d="M 58.40125 296.955 
L 58.40125 29.496 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_4">
    <path d="M 58.40125 296.955 
L 708.12 296.955 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_17">
    <text style="font-weight: 700; font-size: 13.2px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="58.40125" y="23.496" transform="rotate(-0 58.40125 23.496)">七档固定阈值｜门类内过滤、无缓冲</text>
   </g>
   <g id="legend_1">
    <g id="line2d_26">
     <path d="M 68.30125 263.535625 
L 79.30125 263.535625 
L 90.30125 263.535625 
" style="fill: none; stroke: #2563eb; stroke-width: 2; stroke-linecap: square"/>
     <g>
      <use xlink:href="#m727890cc96" x="79.30125" y="263.535625" style="fill: #2563eb; stroke: #2563eb"/>
     </g>
    </g>
    <g id="text_18">
     <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="99.10125" y="267.385625" transform="rotate(-0 99.10125 267.385625)">费前</text>
    </g>
    <g id="line2d_27">
     <path d="M 68.30125 280.035625 
L 79.30125 280.035625 
L 90.30125 280.035625 
" style="fill: none; stroke: #047857; stroke-width: 2; stroke-linecap: square"/>
     <g>
      <use xlink:href="#mf78124e122" x="79.30125" y="280.035625" style="fill: #047857; stroke: #047857"/>
     </g>
    </g>
    <g id="text_19">
     <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="99.10125" y="283.885625" transform="rotate(-0 99.10125 283.885625)">25bp费用情景</text>
    </g>
    <g id="line2d_28">
     <path d="M 193.778594 263.535625 
L 204.778594 263.535625 
L 215.778594 263.535625 
" style="fill: none; stroke: #b45309; stroke-width: 2; stroke-linecap: square"/>
     <g>
      <use xlink:href="#m95af9a57fc" x="204.778594" y="263.535625" style="fill: #b45309; stroke: #b45309"/>
     </g>
    </g>
    <g id="text_20">
     <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="224.578594" y="267.385625" transform="rotate(-0 224.578594 267.385625)">50bp费用情景</text>
    </g>
    <g id="line2d_29">
     <path d="M 193.778594 280.960312 
L 204.778594 280.960312 
L 215.778594 280.960312 
" style="fill: none; stroke-dasharray: 5.55,2.4; stroke-dashoffset: 0; stroke: #64748b; stroke-width: 1.5"/>
    </g>
    <g id="text_21">
     <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="224.578594" y="284.810313" transform="rotate(-0 224.578594 284.810313)">门类盈利基准：25bp</text>
    </g>
   </g>
  </g>
  <g id="text_22">
   <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: start; fill: #475569" x="57.6" y="354.6" transform="rotate(-0 57.6 354.6)">全部曲线使用相同122个月；已看历史的敏感性检查，不据最高值选参数。</text>
  </g>
 </g>
 <defs>
  <clipPath id="p053c36b571">
   <rect x="58.40125" y="29.496" width="649.71875" height="267.459"/>
  </clipPath>
 </defs>
</svg>


## 7. 分年胜率与收益曲线

细行业缓冲相对细行业盈利V2，25bp费用情景。月胜率＝当年有效月份中收益更高的月份比例；全年收益差只有12个月都完整时才计算，单位为百分点。年份按原持有月份分组，持有至下一年首个开盘的最后一期仍属原年；不把不完整年份年化。

| 年份 | 完整费用月份 | 相对V2月均差（百分点） | 月胜率 | 全年收益差（百分点） |
| --- | --- | --- | --- | --- |
| 2015 | 12/12 | -0.350 | 58.3% | -7.88 |
| 2016 | 12/12 | -0.135 | 41.7% | -1.54 |
| 2017 | 12/12 | -0.138 | 41.7% | -1.46 |
| 2018 | 12/12 | 0.421 | 50.0% | 3.47 |
| 2019 | 12/12 | 0.031 | 58.3% | 0.64 |
| 2020 | 10/12 | -0.291 | 30.0% | 不完整，不计算 |
| 2021 | 6/12 | 0.039 | 50.0% | 不完整，不计算 |
| 2022 | 12/12 | 0.288 | 58.3% | 3.82 |
| 2023 | 10/12 | 0.243 | 40.0% | 不完整，不计算 |
| 2024 | 12/12 | 0.410 | 66.7% | 6.14 |
| 2025 | 12/12 | 0.106 | 58.3% | 1.74 |


八个完整年份中五年胜出、三年落后；2015—2017连续落后，不能只说胜率较高。2015—2020和2021—2025两段相对盈利基准的费用后月均差分别约−0.071与+0.237个百分点，方向相反。在同池涨幅最高的13个月中，组合比盈利基准每月少赚0.647个百分点；同池下跌的56个月中每月多0.202个百分点。相对少亏与漏掉上涨同时存在。

下面展示费用资料完整的最长两个片段，每段重新从1起算，点位使用实际开盘日期。相对曲线的0线表示与同池等权持平，原策略、两个修正规则和基准同资金对照。五个缺口没有连线，没有生成完整十一年复利年化。

<svg style="max-width:100%;height:auto" xmlns:xlink="http://www.w3.org/1999/xlink" width="864" height="532" viewBox="0 0 936 576" xmlns="http://www.w3.org/2000/svg" version="1.1">
 <metadata>
  <rdf:RDF xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:cc="http://creativecommons.org/ns#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
   <cc:Work>
    <dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage"/>
    <dc:date>2026-11-04T00:53:50.878355</dc:date>
    <dc:format>image/svg+xml</dc:format>
    <dc:creator>
     <cc:Agent>
      <dc:title>Matplotlib v3.11.2, https://matplotlib.org/</dc:title>
     </cc:Agent>
    </dc:creator>
   </cc:Work>
  </rdf:RDF>
 </metadata>
 <defs>
  <style type="text/css">*{stroke-linejoin: round; stroke-linecap: butt}</style>
 </defs>
 <g id="figure_1">
  <g id="patch_1">
   <path d="M 0 576 
L 936 576 
L 936 0 
L 0 0 
z
" style="fill: #ffffff"/>
  </g>
  <g id="axes_1">
   <g id="patch_2">
    <path d="M 51.16 254.67502 
L 454.06292 254.67502 
L 454.06292 64.0725 
L 51.16 64.0725 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_1">
    <g id="xtick_1">
     <g id="line2d_1">
      <defs>
       <path id="mfeed484c3a" d="M 0 0 
L 0 3.5 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#mfeed484c3a" x="68.754524" y="254.67502" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_1">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(56.601205 280.658833) rotate(-20)">2015</text>
     </g>
    </g>
    <g id="xtick_2">
     <g id="line2d_2">
      <g>
       <use xlink:href="#mfeed484c3a" x="134.385606" y="254.67502" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_2">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(122.232287 280.658833) rotate(-20)">2016</text>
     </g>
    </g>
    <g id="xtick_3">
     <g id="line2d_3">
      <g>
       <use xlink:href="#mfeed484c3a" x="200.1965" y="254.67502" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_3">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(188.043181 280.658833) rotate(-20)">2017</text>
     </g>
    </g>
    <g id="xtick_4">
     <g id="line2d_4">
      <g>
       <use xlink:href="#mfeed484c3a" x="265.827582" y="254.67502" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_4">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(253.674263 280.658833) rotate(-20)">2018</text>
     </g>
    </g>
    <g id="xtick_5">
     <g id="line2d_5">
      <g>
       <use xlink:href="#mfeed484c3a" x="331.458664" y="254.67502" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_5">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(319.305345 280.658833) rotate(-20)">2019</text>
     </g>
    </g>
    <g id="xtick_6">
     <g id="line2d_6">
      <g>
       <use xlink:href="#mfeed484c3a" x="397.089746" y="254.67502" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_6">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(384.936427 280.658833) rotate(-20)">2020</text>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_2">
    <g id="ytick_1">
     <g id="line2d_7">
      <path d="M 51.16 246.011269 
L 454.06292 246.011269 
" clip-path="url(#pe8ef39e075)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_8">
      <defs>
       <path id="mdb1169e9cd" d="M 0 0 
L -3.5 0 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="246.011269" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_7">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="250.851269" transform="rotate(-0 44.16 250.851269)">1.0</text>
     </g>
    </g>
    <g id="ytick_2">
     <g id="line2d_9">
      <path d="M 51.16 222.106559 
L 454.06292 222.106559 
" clip-path="url(#pe8ef39e075)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_10">
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="222.106559" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_8">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="226.946559" transform="rotate(-0 44.16 226.946559)">1.2</text>
     </g>
    </g>
    <g id="ytick_3">
     <g id="line2d_11">
      <path d="M 51.16 198.201849 
L 454.06292 198.201849 
" clip-path="url(#pe8ef39e075)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_12">
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="198.201849" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_9">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="203.041849" transform="rotate(-0 44.16 203.041849)">1.4</text>
     </g>
    </g>
    <g id="ytick_4">
     <g id="line2d_13">
      <path d="M 51.16 174.297139 
L 454.06292 174.297139 
" clip-path="url(#pe8ef39e075)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_14">
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="174.297139" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_10">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="179.137139" transform="rotate(-0 44.16 179.137139)">1.6</text>
     </g>
    </g>
    <g id="ytick_5">
     <g id="line2d_15">
      <path d="M 51.16 150.39243 
L 454.06292 150.39243 
" clip-path="url(#pe8ef39e075)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_16">
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="150.39243" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_11">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="155.23243" transform="rotate(-0 44.16 155.23243)">1.8</text>
     </g>
    </g>
    <g id="ytick_6">
     <g id="line2d_17">
      <path d="M 51.16 126.48772 
L 454.06292 126.48772 
" clip-path="url(#pe8ef39e075)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_18">
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="126.48772" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_12">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="131.32772" transform="rotate(-0 44.16 131.32772)">2.0</text>
     </g>
    </g>
    <g id="ytick_7">
     <g id="line2d_19">
      <path d="M 51.16 102.58301 
L 454.06292 102.58301 
" clip-path="url(#pe8ef39e075)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_20">
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="102.58301" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_13">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="107.42301" transform="rotate(-0 44.16 107.42301)">2.2</text>
     </g>
    </g>
    <g id="ytick_8">
     <g id="line2d_21">
      <path d="M 51.16 78.6783 
L 454.06292 78.6783 
" clip-path="url(#pe8ef39e075)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_22">
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="78.6783" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_14">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="83.5183" transform="rotate(-0 44.16 83.5183)">2.4</text>
     </g>
    </g>
    <g id="text_15">
     <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: middle" x="21.702344" y="159.37376" transform="rotate(-90 21.702344 159.37376)">片段起点＝1</text>
    </g>
   </g>
   <g id="line2d_23">
    <path d="M 69.473769 246.011269 
L 74.508482 238.925621 
L 79.543195 223.728332 
L 84.937531 189.600807 
L 90.8713 165.306979 
L 95.906013 106.61927 
L 101.300349 157.82322 
L 107.234118 193.608538 
L 112.448642 217.973631 
L 119.101656 203.262298 
L 123.596935 181.066106 
L 128.81146 157.031 
L 134.92504 164.817696 
L 139.959753 211.71992 
L 145.174277 207.437676 
L 150.748424 180.629468 
L 156.502382 174.057717 
L 161.716906 181.269614 
L 167.111242 171.396959 
L 172.685389 175.370984 
L 178.259535 164.408165 
L 185.272171 159.729595 
L 189.228018 155.884667 
L 194.622353 151.997489 
L 200.556122 162.65875 
L 206.130269 168.360113 
L 210.80536 158.399086 
L 217.098751 158.382139 
L 221.953653 175.442731 
L 227.347989 193.24061 
L 233.101946 178.906219 
L 238.316471 179.884471 
L 243.890617 172.505426 
L 250.723442 169.281801 
L 254.8591 174.54986 
L 260.253435 184.56524 
L 266.007393 187.714316 
L 271.401729 200.379584 
L 276.436442 198.42369 
L 282.1904 193.212137 
L 287.584735 202.004447 
L 292.979071 204.010481 
L 298.553217 222.449399 
L 303.947553 220.340942 
L 309.881322 229.191717 
L 316.174713 232.752912 
L 320.490182 241.824762 
L 326.24414 230.899024 
L 331.638475 240.758872 
L 337.032811 238.576969 
L 342.067524 213.943134 
L 347.641671 193.254531 
L 353.935062 215.596701 
L 358.969775 213.315128 
L 364.004488 205.165567 
L 369.578635 213.225217 
L 375.332593 210.870147 
L 381.805795 213.109836 
L 386.121264 212.500345 
L 391.695411 217.085039 
L 397.269557 202.480079 
L 403.023515 219.560143 
L 408.058228 196.995414 
L 413.452564 209.11328 
L 419.745955 202.028789 
L 424.421046 195.542986 
L 429.815382 189.264583 
L 435.749151 158.04026 
" clip-path="url(#pe8ef39e075)" style="fill: none; stroke-dasharray: 6.66,2.88; stroke-dashoffset: 0; stroke: #94a3b8; stroke-width: 1.8"/>
   </g>
   <g id="line2d_24">
    <path d="M 69.473769 246.011269 
L 74.508482 238.553359 
L 79.543195 224.004877 
L 84.937531 190.558515 
L 90.8713 166.078441 
L 95.906013 105.478932 
L 101.300349 154.603919 
L 107.234118 189.707594 
L 112.448642 215.209445 
L 119.101656 203.338378 
L 123.596935 180.767594 
L 128.81146 156.63385 
L 134.92504 164.259391 
L 139.959753 212.07793 
L 145.174277 209.27616 
L 150.748424 182.376095 
L 156.502382 175.754825 
L 161.716906 185.359498 
L 167.111242 174.067781 
L 172.685389 174.220199 
L 178.259535 164.003191 
L 185.272171 159.450057 
L 189.228018 156.860673 
L 194.622353 152.541672 
L 200.556122 163.367664 
L 206.130269 169.022089 
L 210.80536 160.554263 
L 217.098751 158.988229 
L 221.953653 175.351062 
L 227.347989 189.569977 
L 233.101946 172.452567 
L 238.316471 172.519385 
L 243.890617 164.065669 
L 250.723442 157.664571 
L 254.8591 160.616905 
L 260.253435 171.157968 
L 266.007393 173.695787 
L 271.401729 181.230807 
L 276.436442 179.394846 
L 282.1904 175.074371 
L 287.584735 184.902555 
L 292.979071 184.711037 
L 298.553217 202.363324 
L 303.947553 201.663695 
L 309.881322 210.852686 
L 316.174713 214.819397 
L 320.490182 226.39302 
L 326.24414 216.146752 
L 331.638475 228.101405 
L 337.032811 223.464689 
L 342.067524 200.120155 
L 347.641671 180.26706 
L 353.935062 200.687695 
L 358.969775 199.190419 
L 364.004488 190.530311 
L 369.578635 197.153644 
L 375.332593 194.555767 
L 381.805795 196.378441 
L 386.121264 195.239434 
L 391.695411 200.696719 
L 397.269557 184.862552 
L 403.023515 203.489441 
L 408.058228 179.792901 
L 413.452564 194.296273 
L 419.745955 185.674406 
L 424.421046 176.026338 
L 429.815382 164.79458 
L 435.749151 127.811378 
" clip-path="url(#pe8ef39e075)" style="fill: none; stroke-dasharray: 1.8,2.97; stroke-dashoffset: 0; stroke: #334155; stroke-width: 1.8"/>
   </g>
   <g id="line2d_25">
    <path d="M 69.473769 246.011269 
L 74.508482 238.673652 
L 79.543195 225.029355 
L 84.937531 192.011627 
L 90.8713 167.932071 
L 95.906013 109.599136 
L 101.300349 157.536851 
L 107.234118 192.759681 
L 112.448642 216.619273 
L 119.101656 205.527339 
L 123.596935 182.668169 
L 128.81146 157.400207 
L 134.92504 164.587255 
L 139.959753 210.892737 
L 145.174277 208.709671 
L 150.748424 180.891933 
L 156.502382 174.139069 
L 161.716906 183.534352 
L 167.111242 171.501914 
L 172.685389 170.807239 
L 178.259535 161.143668 
L 185.272171 157.364153 
L 189.228018 155.283864 
L 194.622353 151.7642 
L 200.556122 162.795919 
L 206.130269 168.61618 
L 210.80536 159.158133 
L 217.098751 158.327668 
L 221.953653 173.56426 
L 227.347989 188.153276 
L 233.101946 170.896778 
L 238.316471 170.82677 
L 243.890617 161.708529 
L 250.723442 155.821091 
L 254.8591 158.186371 
L 260.253435 169.298304 
L 266.007393 170.518796 
L 271.401729 177.211755 
L 276.436442 175.602222 
L 282.1904 173.348644 
L 287.584735 182.911412 
L 292.979071 182.845839 
L 298.553217 201.034274 
L 303.947553 200.889609 
L 309.881322 211.077128 
L 316.174713 213.811867 
L 320.490182 226.821097 
L 326.24414 216.355348 
L 331.638475 227.561203 
L 337.032811 222.715876 
L 342.067524 200.167773 
L 347.641671 179.113863 
L 353.935062 198.86737 
L 358.969775 197.891532 
L 364.004488 189.563761 
L 369.578635 196.509345 
L 375.332593 193.827435 
L 381.805795 195.477602 
L 386.121264 194.477703 
L 391.695411 200.344183 
L 397.269557 184.222645 
L 403.023515 202.007775 
L 408.058228 177.708084 
L 413.452564 192.487649 
L 419.745955 183.351191 
L 424.421046 173.246083 
L 429.815382 162.181106 
L 435.749151 124.848919 
" clip-path="url(#pe8ef39e075)" style="fill: none; stroke: #2563eb; stroke-width: 1.8; stroke-linecap: square"/>
   </g>
   <g id="line2d_26">
    <path d="M 69.473769 246.011269 
L 74.508482 237.317989 
L 79.543195 222.506732 
L 84.937531 192.105524 
L 90.8713 163.401589 
L 95.906013 101.226677 
L 101.300349 149.456943 
L 107.234118 182.983722 
L 112.448642 211.792512 
L 119.101656 197.28356 
L 123.596935 177.164444 
L 128.81146 151.614033 
L 134.92504 159.419183 
L 139.959753 201.271272 
L 145.174277 197.812654 
L 150.748424 170.943118 
L 156.502382 164.266755 
L 161.716906 171.517819 
L 167.111242 160.157013 
L 172.685389 155.639323 
L 178.259535 147.283644 
L 185.272171 143.552412 
L 189.228018 140.53051 
L 194.622353 135.881357 
L 200.556122 150.158719 
L 206.130269 155.577346 
L 210.80536 144.530479 
L 217.098751 141.524388 
L 221.953653 155.386161 
L 227.347989 169.9634 
L 233.101946 151.048338 
L 238.316471 157.339864 
L 243.890617 149.855813 
L 250.723442 141.617197 
L 254.8591 143.022652 
L 260.253435 154.67312 
L 266.007393 152.973803 
L 271.401729 163.459672 
L 276.436442 162.46925 
L 282.1904 155.65563 
L 287.584735 160.402211 
L 292.979071 158.725147 
L 298.553217 180.398833 
L 303.947553 178.528799 
L 309.881322 191.003482 
L 316.174713 195.995111 
L 320.490182 207.199061 
L 326.24414 190.152821 
L 331.638475 202.815695 
L 337.032811 196.853599 
L 342.067524 172.428646 
L 347.641671 149.404873 
L 353.935062 171.369713 
L 358.969775 169.676682 
L 364.004488 156.14106 
L 369.578635 164.547492 
L 375.332593 160.082621 
L 381.805795 163.768669 
L 386.121264 161.338676 
L 391.695411 168.92163 
L 397.269557 148.92595 
L 403.023515 164.336249 
L 408.058228 137.984633 
L 413.452564 153.237172 
L 419.745955 143.733018 
L 424.421046 130.043659 
L 429.815382 114.832535 
L 435.749151 72.736251 
" clip-path="url(#pe8ef39e075)" style="fill: none; stroke-dasharray: 11.52,2.88,1.8,2.88; stroke-dashoffset: 0; stroke: #9333ea; stroke-width: 1.8"/>
   </g>
   <g id="line2d_27">
    <path d="M 69.473769 246.011269 
L 74.508482 237.805537 
L 79.543195 223.289205 
L 84.937531 192.876955 
L 90.8713 167.769327 
L 95.906013 108.905852 
L 101.300349 158.916406 
L 107.234118 192.619495 
L 112.448642 222.4238 
L 119.101656 208.920765 
L 123.596935 185.397263 
L 128.81146 164.472566 
L 134.92504 174.003084 
L 139.959753 219.28642 
L 145.174277 216.846285 
L 150.748424 192.592876 
L 156.502382 186.793578 
L 161.716906 194.698924 
L 167.111242 184.794973 
L 172.685389 182.531534 
L 178.259535 173.663899 
L 185.272171 171.373162 
L 189.228018 169.046808 
L 194.622353 164.332937 
L 200.556122 175.252228 
L 206.130269 180.051513 
L 210.80536 171.328467 
L 217.098751 170.640484 
L 221.953653 184.47888 
L 227.347989 198.102152 
L 233.101946 182.754204 
L 238.316471 183.401944 
L 243.890617 175.305809 
L 250.723442 171.604613 
L 254.8591 176.318344 
L 260.253435 185.434631 
L 266.007393 185.282057 
L 271.401729 194.620932 
L 276.436442 193.453198 
L 282.1904 189.413549 
L 287.584735 197.423484 
L 292.979071 197.787171 
L 298.553217 215.263888 
L 303.947553 211.63874 
L 309.881322 219.915882 
L 316.174713 223.464591 
L 320.490182 233.898859 
L 326.24414 220.377267 
L 331.638475 231.758381 
L 337.032811 226.71078 
L 342.067524 206.214843 
L 347.641671 186.789618 
L 353.935062 206.369522 
L 358.969775 204.292557 
L 364.004488 194.426186 
L 369.578635 201.09785 
L 375.332593 198.694402 
L 381.805795 200.247916 
L 386.121264 199.151597 
L 391.695411 204.186733 
L 397.269557 188.881995 
L 403.023515 205.242052 
L 408.058228 182.537742 
L 413.452564 193.82737 
L 419.745955 186.239565 
L 424.421046 177.433526 
L 429.815382 168.240892 
L 435.749151 134.645173 
" clip-path="url(#pe8ef39e075)" style="fill: none; stroke: #047857; stroke-width: 1.8; stroke-linecap: square"/>
   </g>
   <g id="patch_3">
    <path d="M 51.16 254.67502 
L 51.16 64.0725 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_4">
    <path d="M 51.16 254.67502 
L 454.06292 254.67502 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_16">
    <text style="font-weight: 700; font-size: 13.2px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="51.16" y="58.0725" transform="rotate(-0 51.16 58.0725)">2015-01—2020-07｜费用情景财富</text>
   </g>
  </g>
  <g id="axes_2">
   <g id="patch_5">
    <path d="M 513.685 254.67502 
L 916.58792 254.67502 
L 916.58792 64.0725 
L 513.685 64.0725 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_3">
    <g id="xtick_7">
     <g id="line2d_28">
      <g>
       <use xlink:href="#mfeed484c3a" x="531.279524" y="254.67502" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_17">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(519.126205 280.658833) rotate(-20)">2015</text>
     </g>
    </g>
    <g id="xtick_8">
     <g id="line2d_29">
      <g>
       <use xlink:href="#mfeed484c3a" x="596.910606" y="254.67502" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_18">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(584.757287 280.658833) rotate(-20)">2016</text>
     </g>
    </g>
    <g id="xtick_9">
     <g id="line2d_30">
      <g>
       <use xlink:href="#mfeed484c3a" x="662.7215" y="254.67502" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_19">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(650.568181 280.658833) rotate(-20)">2017</text>
     </g>
    </g>
    <g id="xtick_10">
     <g id="line2d_31">
      <g>
       <use xlink:href="#mfeed484c3a" x="728.352582" y="254.67502" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_20">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(716.199263 280.658833) rotate(-20)">2018</text>
     </g>
    </g>
    <g id="xtick_11">
     <g id="line2d_32">
      <g>
       <use xlink:href="#mfeed484c3a" x="793.983664" y="254.67502" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_21">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(781.830345 280.658833) rotate(-20)">2019</text>
     </g>
    </g>
    <g id="xtick_12">
     <g id="line2d_33">
      <g>
       <use xlink:href="#mfeed484c3a" x="859.614746" y="254.67502" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_22">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(847.461427 280.658833) rotate(-20)">2020</text>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_4">
    <g id="ytick_9">
     <g id="line2d_34">
      <path d="M 513.685 220.50675 
L 916.58792 220.50675 
" clip-path="url(#p87212ff3d3)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_35">
      <g>
       <use xlink:href="#mdb1169e9cd" x="513.685" y="220.50675" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_23">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="506.685" y="225.34675" transform="rotate(-0 506.685 225.34675)">0</text>
     </g>
    </g>
    <g id="ytick_10">
     <g id="line2d_36">
      <path d="M 513.685 185.511689 
L 916.58792 185.511689 
" clip-path="url(#p87212ff3d3)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_37">
      <g>
       <use xlink:href="#mdb1169e9cd" x="513.685" y="185.511689" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_24">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="506.685" y="190.351689" transform="rotate(-0 506.685 190.351689)">10</text>
     </g>
    </g>
    <g id="ytick_11">
     <g id="line2d_38">
      <path d="M 513.685 150.516628 
L 916.58792 150.516628 
" clip-path="url(#p87212ff3d3)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_39">
      <g>
       <use xlink:href="#mdb1169e9cd" x="513.685" y="150.516628" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_25">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="506.685" y="155.356628" transform="rotate(-0 506.685 155.356628)">20</text>
     </g>
    </g>
    <g id="ytick_12">
     <g id="line2d_40">
      <path d="M 513.685 115.521567 
L 916.58792 115.521567 
" clip-path="url(#p87212ff3d3)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_41">
      <g>
       <use xlink:href="#mdb1169e9cd" x="513.685" y="115.521567" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_26">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="506.685" y="120.361567" transform="rotate(-0 506.685 120.361567)">30</text>
     </g>
    </g>
    <g id="ytick_13">
     <g id="line2d_42">
      <path d="M 513.685 80.526506 
L 916.58792 80.526506 
" clip-path="url(#p87212ff3d3)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_43">
      <g>
       <use xlink:href="#mdb1169e9cd" x="513.685" y="80.526506" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_27">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="506.685" y="85.366506" transform="rotate(-0 506.685 85.366506)">40</text>
     </g>
    </g>
    <g id="text_28">
     <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: middle" x="486.867344" y="159.37376" transform="rotate(-90 486.867344 159.37376)">相对财富变化（%）</text>
    </g>
   </g>
   <g id="line2d_44">
    <path d="M 531.998769 220.50675 
L 537.033482 219.47781 
L 542.068195 221.189209 
L 547.462531 222.411729 
L 553.3963 221.85508 
L 558.431013 218.965468 
L 563.825349 215.082901 
L 569.759118 212.566499 
L 574.973642 213.951309 
L 581.626656 220.67082 
L 586.121935 219.940452 
L 591.33646 219.840179 
L 597.45004 219.533344 
L 602.484753 221.321274 
L 607.699277 224.576266 
L 613.273424 223.812404 
L 619.027382 223.608448 
L 624.241906 228.274128 
L 629.636242 225.321142 
L 635.210389 218.389007 
L 640.784535 219.802115 
L 647.797171 220.031424 
L 651.753018 222.135911 
L 657.147353 221.398572 
L 663.081122 221.72959 
L 668.655269 221.681641 
L 673.33036 224.147867 
L 679.623751 221.53064 
L 684.478653 220.337993 
L 689.872989 213.051246 
L 695.626946 208.405391 
L 700.841471 206.623575 
L 706.415617 205.205981 
L 713.248442 199.791365 
L 717.3841 194.97675 
L 722.778435 194.580386 
L 728.532393 192.918296 
L 733.926729 179.932035 
L 738.961442 180.658084 
L 744.7154 183.672814 
L 750.109735 183.909159 
L 755.504071 178.693532 
L 761.078217 171.381309 
L 766.472553 175.490292 
L 772.406322 173.436125 
L 778.699713 173.242444 
L 783.015182 176.853487 
L 788.76914 182.16207 
L 794.163475 185.007212 
L 799.557811 178.850786 
L 804.592524 188.596291 
L 810.166671 194.125476 
L 816.460062 185.709622 
L 821.494775 188.034271 
L 826.529488 188.570349 
L 832.103635 183.580275 
L 837.857593 183.593166 
L 844.330795 182.093349 
L 848.646264 181.035471 
L 854.220411 181.873463 
L 859.794557 182.695741 
L 865.548515 181.979848 
L 870.583228 184.787923 
L 875.977564 187.357731 
L 882.270955 185.503598 
L 886.946046 180.329156 
L 892.340382 171.926271 
L 898.274151 169.524133 
" clip-path="url(#p87212ff3d3)" style="fill: none; stroke-dasharray: 1.8,2.97; stroke-dashoffset: 0; stroke: #334155; stroke-width: 1.8"/>
   </g>
   <g id="line2d_45">
    <path d="M 531.998769 220.50675 
L 537.033482 219.810303 
L 542.068195 223.71742 
L 547.462531 225.302116 
L 553.3963 225.094786 
L 558.431013 224.534341 
L 563.825349 220.024278 
L 569.759118 218.778926 
L 574.973642 217.294805 
L 581.626656 225.391449 
L 586.121935 223.545981 
L 591.33646 221.126423 
L 597.45004 220.104975 
L 602.484753 218.624792 
L 607.699277 223.322332 
L 613.273424 221.003488 
L 619.027382 220.655433 
L 624.241906 224.807869 
L 629.636242 220.69594 
L 635.210389 212.108278 
L 640.784535 214.826684 
L 647.797171 216.484558 
L 651.753018 219.503881 
L 657.147353 220.124431 
L 663.081122 220.743359 
L 668.655269 220.961223 
L 673.33036 221.789141 
L 679.623751 220.41473 
L 684.478653 217.048573 
L 689.872989 210.173752 
L 695.626946 205.488104 
L 700.841471 203.432999 
L 706.415617 200.932628 
L 713.248442 196.504144 
L 717.3841 190.523169 
L 722.778435 190.984254 
L 728.532393 186.665981 
L 733.926729 171.415989 
L 738.961442 172.715876 
L 744.7154 180.168233 
L 750.109735 179.648167 
L 755.504071 174.652487 
L 761.078217 168.130791 
L 766.472553 173.624568 
L 772.406322 174.012197 
L 778.699713 170.587069 
L 783.015182 178.06443 
L 788.76914 182.704259 
L 794.163475 183.492145 
L 799.557811 176.786734 
L 804.592524 188.706219 
L 810.166671 191.783003 
L 816.460062 181.461042 
L 821.494775 185.048149 
L 826.529488 186.461187 
L 832.103635 182.099915 
L 837.857593 181.945213 
L 844.330795 180.025123 
L 848.646264 179.293588 
L 854.220411 181.042408 
L 859.794557 181.322362 
L 865.548515 178.427795 
L 870.583228 180.459065 
L 875.977564 183.311427 
L 882.270955 180.531241 
L 886.946046 174.605634 
L 892.340382 166.737723 
L 898.274151 164.527788 
" clip-path="url(#p87212ff3d3)" style="fill: none; stroke: #2563eb; stroke-width: 1.8; stroke-linecap: square"/>
   </g>
   <g id="line2d_46">
    <path d="M 531.998769 220.50675 
L 537.033482 216.063219 
L 542.068195 217.492081 
L 547.462531 225.488886 
L 553.3963 217.176581 
L 558.431013 213.218114 
L 563.825349 206.411322 
L 569.759118 198.880267 
L 574.973642 205.847838 
L 581.626656 207.613235 
L 586.121935 213.105013 
L 591.33646 211.41497 
L 597.45004 211.094434 
L 602.484753 196.734601 
L 607.699277 199.201607 
L 613.273424 202.174429 
L 619.027382 202.612428 
L 624.241906 201.986452 
L 629.636242 200.245756 
L 635.210389 184.195392 
L 640.784535 190.710914 
L 647.797171 192.999114 
L 651.753018 194.877401 
L 657.147353 194.095208 
L 663.081122 198.944849 
L 668.655269 197.819573 
L 673.33036 197.076086 
L 679.623751 192.028333 
L 684.478653 183.583547 
L 689.872989 173.227889 
L 695.626946 168.269941 
L 700.841471 178.010201 
L 706.415617 179.444372 
L 713.248442 171.176324 
L 717.3841 162.737984 
L 722.778435 162.702749 
L 728.532393 152.137448 
L 733.926729 142.276435 
L 738.961442 145.213869 
L 744.7154 144.237493 
L 750.109735 131.47908 
L 755.504071 122.393793 
L 761.078217 117.66174 
L 766.472553 119.729875 
L 772.406322 122.48935 
L 778.699713 123.630486 
L 783.015182 122.557676 
L 788.76914 114.59763 
L 794.163475 114.090101 
L 799.557811 105.49914 
L 804.592524 124.670221 
L 810.166671 131.435533 
L 816.460062 117.282421 
L 821.494775 120.182665 
L 826.529488 113.527663 
L 832.103635 108.663507 
L 837.857593 105.592816 
L 844.330795 107.22498 
L 848.646264 103.513127 
L 854.220411 106.967917 
L 859.794557 105.568047 
L 865.548515 88.116422 
L 870.583228 97.978378 
L 875.977564 95.499169 
L 882.270955 95.736791 
L 886.946046 85.667745 
L 892.340382 72.736251 
L 898.274151 76.637001 
" clip-path="url(#p87212ff3d3)" style="fill: none; stroke-dasharray: 11.52,2.88,1.8,2.88; stroke-dashoffset: 0; stroke: #9333ea; stroke-width: 1.8"/>
   </g>
   <g id="line2d_47">
    <path d="M 531.998769 220.50675 
L 537.033482 217.410813 
L 542.068195 219.42307 
L 547.462531 227.02334 
L 553.3963 224.810348 
L 558.431013 223.597297 
L 563.825349 222.34854 
L 569.759118 218.493582 
L 574.973642 231.060605 
L 581.626656 232.709579 
L 586.121935 228.723272 
L 591.33646 232.996596 
L 597.45004 236.521487 
L 602.484753 237.721607 
L 607.699277 241.33286 
L 613.273424 243.148614 
L 619.027382 243.78328 
L 624.241906 246.011269 
L 629.636242 244.657851 
L 635.210389 233.684013 
L 640.784535 236.611277 
L 647.797171 240.305438 
L 651.753018 242.477158 
L 657.147353 240.722408 
L 663.081122 242.229841 
L 668.655269 241.256939 
L 673.33036 242.350614 
L 679.623751 241.215221 
L 684.478653 237.141876 
L 689.872989 230.381136 
L 695.626946 227.722175 
L 700.841471 227.137181 
L 706.415617 225.583675 
L 713.248442 224.648696 
L 717.3841 223.747226 
L 722.778435 222.187939 
L 728.532393 215.720066 
L 733.926729 208.304631 
L 738.961442 210.097947 
L 744.7154 212.792627 
L 750.109735 210.703612 
L 755.504071 207.023634 
L 761.078217 202.932813 
L 766.472553 199.532443 
L 772.406322 196.698547 
L 778.699713 196.027108 
L 783.015182 198.085979 
L 788.76914 193.15819 
L 794.163475 195.263683 
L 799.557811 187.798413 
L 804.592524 202.665928 
L 810.166671 207.374659 
L 816.460062 198.970819 
L 821.494775 199.764002 
L 826.529488 197.071753 
L 832.103635 192.642587 
L 837.857593 192.957411 
L 844.330795 190.977228 
L 848.646264 189.981585 
L 854.220411 190.100708 
L 859.794557 191.322331 
L 865.548515 186.181449 
L 870.583228 190.487235 
L 875.977564 186.308688 
L 882.270955 186.713203 
L 886.946046 183.226037 
L 892.340382 178.76826 
L 898.274151 181.049692 
" clip-path="url(#p87212ff3d3)" style="fill: none; stroke: #047857; stroke-width: 1.8; stroke-linecap: square"/>
   </g>
   <g id="line2d_48">
    <path d="M 513.685 220.50675 
L 916.58792 220.50675 
" clip-path="url(#p87212ff3d3)" style="fill: none; stroke: #94a3b8; stroke-width: 0.8; stroke-linecap: square"/>
   </g>
   <g id="patch_6">
    <path d="M 513.685 254.67502 
L 513.685 64.0725 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_7">
    <path d="M 513.685 254.67502 
L 916.58792 254.67502 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_29">
    <text style="font-weight: 700; font-size: 13.2px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="513.685" y="58.0725" transform="rotate(-0 513.685 58.0725)">2015-01—2020-07｜相对同池等权</text>
   </g>
  </g>
  <g id="axes_3">
   <g id="patch_8">
    <path d="M 51.16 501.976838 
L 454.06292 501.976838 
L 454.06292 311.374319 
L 51.16 311.374319 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_5">
    <g id="xtick_13">
     <g id="line2d_49">
      <g>
       <use xlink:href="#mfeed484c3a" x="56.687129" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_30">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(35.892235 534.251204) rotate(-20)">2023-07</text>
     </g>
    </g>
    <g id="xtick_14">
     <g id="line2d_50">
      <g>
       <use xlink:href="#mfeed484c3a" x="94.634578" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_31">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(73.839684 534.251204) rotate(-20)">2023-10</text>
     </g>
    </g>
    <g id="xtick_15">
     <g id="line2d_51">
      <g>
       <use xlink:href="#mfeed484c3a" x="132.582027" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_32">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(111.766945 534.2659) rotate(-20)">2024-01</text>
     </g>
    </g>
    <g id="xtick_16">
     <g id="line2d_52">
      <g>
       <use xlink:href="#mfeed484c3a" x="170.117005" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_33">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(149.281733 534.280596) rotate(-20)">2024-04</text>
     </g>
    </g>
    <g id="xtick_17">
     <g id="line2d_53">
      <g>
       <use xlink:href="#mfeed484c3a" x="207.651982" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_34">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(186.836899 534.2659) rotate(-20)">2024-07</text>
     </g>
    </g>
    <g id="xtick_18">
     <g id="line2d_54">
      <g>
       <use xlink:href="#mfeed484c3a" x="245.599431" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_35">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(224.784349 534.2659) rotate(-20)">2024-10</text>
     </g>
    </g>
    <g id="xtick_19">
     <g id="line2d_55">
      <g>
       <use xlink:href="#mfeed484c3a" x="283.546881" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_36">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(262.751987 534.251204) rotate(-20)">2025-01</text>
     </g>
    </g>
    <g id="xtick_20">
     <g id="line2d_56">
      <g>
       <use xlink:href="#mfeed484c3a" x="320.669385" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_37">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(299.854303 534.2659) rotate(-20)">2025-04</text>
     </g>
    </g>
    <g id="xtick_21">
     <g id="line2d_57">
      <g>
       <use xlink:href="#mfeed484c3a" x="358.204363" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_38">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(337.409469 534.251204) rotate(-20)">2025-07</text>
     </g>
    </g>
    <g id="xtick_22">
     <g id="line2d_58">
      <g>
       <use xlink:href="#mfeed484c3a" x="396.151812" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_39">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(375.356918 534.251204) rotate(-20)">2025-10</text>
     </g>
    </g>
    <g id="xtick_23">
     <g id="line2d_59">
      <g>
       <use xlink:href="#mfeed484c3a" x="434.099262" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_40">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(413.304368 534.251204) rotate(-20)">2026-01</text>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_6">
    <g id="ytick_14">
     <g id="line2d_60">
      <path d="M 51.16 476.35148 
L 454.06292 476.35148 
" clip-path="url(#p6c2b4ecff0)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_61">
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="476.35148" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_41">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="481.19148" transform="rotate(-0 44.16 481.19148)">0.8</text>
     </g>
    </g>
    <g id="ytick_15">
     <g id="line2d_62">
      <path d="M 51.16 447.722186 
L 454.06292 447.722186 
" clip-path="url(#p6c2b4ecff0)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_63">
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="447.722186" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_42">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="452.562186" transform="rotate(-0 44.16 452.562186)">0.9</text>
     </g>
    </g>
    <g id="ytick_16">
     <g id="line2d_64">
      <path d="M 51.16 419.092893 
L 454.06292 419.092893 
" clip-path="url(#p6c2b4ecff0)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_65">
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="419.092893" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_43">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="423.932893" transform="rotate(-0 44.16 423.932893)">1.0</text>
     </g>
    </g>
    <g id="ytick_17">
     <g id="line2d_66">
      <path d="M 51.16 390.4636 
L 454.06292 390.4636 
" clip-path="url(#p6c2b4ecff0)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_67">
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="390.4636" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_44">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="395.3036" transform="rotate(-0 44.16 395.3036)">1.1</text>
     </g>
    </g>
    <g id="ytick_18">
     <g id="line2d_68">
      <path d="M 51.16 361.834306 
L 454.06292 361.834306 
" clip-path="url(#p6c2b4ecff0)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_69">
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="361.834306" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_45">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="366.674306" transform="rotate(-0 44.16 366.674306)">1.2</text>
     </g>
    </g>
    <g id="ytick_19">
     <g id="line2d_70">
      <path d="M 51.16 333.205013 
L 454.06292 333.205013 
" clip-path="url(#p6c2b4ecff0)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_71">
      <g>
       <use xlink:href="#mdb1169e9cd" x="51.16" y="333.205013" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_46">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="44.16" y="338.045013" transform="rotate(-0 44.16 338.045013)">1.3</text>
     </g>
    </g>
    <g id="text_47">
     <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: middle" x="21.745313" y="406.675579" transform="rotate(-90 21.745313 406.675579)">片段起点＝1</text>
    </g>
   </g>
   <g id="line2d_72">
    <path d="M 69.473769 419.092893 
L 82.26041 434.048491 
L 97.934356 435.033865 
L 107.421219 435.139209 
L 119.795387 425.831314 
L 132.9945 432.413939 
L 145.368668 480.296121 
L 157.330364 460.095839 
L 170.117005 447.595428 
L 184.553534 449.351668 
L 196.102758 462.994375 
L 207.651982 478.087695 
L 220.438622 478.221673 
L 233.637735 488.696442 
L 248.486737 419.12008 
L 258.386072 419.772018 
L 271.172712 397.281098 
L 283.959353 421.680933 
L 297.98341 421.398413 
L 308.707689 407.165796 
L 320.669385 405.300854 
L 335.105915 409.280562 
L 346.655139 400.526793 
L 358.204363 383.725399 
L 370.991003 373.240384 
L 383.777644 346.131622 
L 399.45159 347.025956 
L 409.763397 337.989482 
L 421.312621 334.10988 
L 435.749151 320.03807 
" clip-path="url(#p6c2b4ecff0)" style="fill: none; stroke-dasharray: 6.66,2.88; stroke-dashoffset: 0; stroke: #94a3b8; stroke-width: 1.8"/>
   </g>
   <g id="line2d_73">
    <path d="M 69.473769 419.092893 
L 82.26041 433.306547 
L 97.934356 435.558577 
L 107.421219 439.395114 
L 119.795387 429.900467 
L 132.9945 437.924075 
L 145.368668 480.002482 
L 157.330364 458.66089 
L 170.117005 447.182769 
L 184.553534 445.121514 
L 196.102758 458.689993 
L 207.651982 475.123627 
L 220.438622 482.420734 
L 233.637735 493.313088 
L 248.486737 424.906312 
L 258.386072 423.655367 
L 271.172712 404.258505 
L 283.959353 424.212514 
L 297.98341 428.199491 
L 308.707689 417.022241 
L 320.669385 414.543224 
L 335.105915 422.282729 
L 346.655139 417.667842 
L 358.204363 405.665727 
L 370.991003 394.853374 
L 383.777644 367.151114 
L 399.45159 371.619641 
L 409.763397 365.008324 
L 421.312621 363.065746 
L 435.749151 358.292703 
" clip-path="url(#p6c2b4ecff0)" style="fill: none; stroke-dasharray: 1.8,2.97; stroke-dashoffset: 0; stroke: #334155; stroke-width: 1.8"/>
   </g>
   <g id="line2d_74">
    <path d="M 69.473769 419.092893 
L 82.26041 432.592951 
L 97.934356 434.242125 
L 107.421219 437.864973 
L 119.795387 427.456741 
L 132.9945 436.019099 
L 145.368668 477.368736 
L 157.330364 454.540774 
L 170.117005 441.495167 
L 184.553534 438.579412 
L 196.102758 452.171179 
L 207.651982 467.820905 
L 220.438622 474.918221 
L 233.637735 485.688013 
L 248.486737 416.576577 
L 258.386072 416.025248 
L 271.172712 396.595691 
L 283.959353 415.854658 
L 297.98341 420.426858 
L 308.707689 409.26988 
L 320.669385 406.79747 
L 335.105915 414.776122 
L 346.655139 409.804836 
L 358.204363 397.823592 
L 370.991003 386.888526 
L 383.777644 358.24802 
L 399.45159 362.476362 
L 409.763397 357.594691 
L 421.312621 356.243937 
L 435.749151 353.173845 
" clip-path="url(#p6c2b4ecff0)" style="fill: none; stroke: #2563eb; stroke-width: 1.8; stroke-linecap: square"/>
   </g>
   <g id="line2d_75">
    <path d="M 69.473769 419.092893 
L 82.26041 429.844665 
L 97.934356 429.66296 
L 107.421219 434.008328 
L 119.795387 428.408916 
L 132.9945 434.724364 
L 145.368668 472.830069 
L 157.330364 449.340287 
L 170.117005 443.141469 
L 184.553534 438.038352 
L 196.102758 449.678653 
L 207.651982 463.898929 
L 220.438622 471.71493 
L 233.637735 481.37278 
L 248.486737 415.476186 
L 258.386072 429.72043 
L 271.172712 420.166552 
L 283.959353 431.142855 
L 297.98341 434.774833 
L 308.707689 427.456185 
L 320.669385 420.196277 
L 335.105915 429.747138 
L 346.655139 422.321875 
L 358.204363 416.825041 
L 370.991003 404.726308 
L 383.777644 387.938612 
L 399.45159 389.374907 
L 409.763397 383.856757 
L 421.312621 380.577248 
L 435.749151 384.525397 
" clip-path="url(#p6c2b4ecff0)" style="fill: none; stroke-dasharray: 11.52,2.88,1.8,2.88; stroke-dashoffset: 0; stroke: #9333ea; stroke-width: 1.8"/>
   </g>
   <g id="line2d_76">
    <path d="M 69.473769 419.092893 
L 82.26041 430.118245 
L 97.934356 431.843978 
L 107.421219 435.74366 
L 119.795387 426.710033 
L 132.9945 432.607367 
L 145.368668 470.318169 
L 157.330364 446.771412 
L 170.117005 435.336654 
L 184.553534 427.59837 
L 196.102758 440.833377 
L 207.651982 457.315112 
L 220.438622 464.048094 
L 233.637735 475.155542 
L 248.486737 405.441797 
L 258.386072 399.379488 
L 271.172712 379.240818 
L 283.959353 395.442374 
L 297.98341 397.896264 
L 308.707689 388.369917 
L 320.669385 384.651769 
L 335.105915 392.056708 
L 346.655139 387.615634 
L 358.204363 376.455139 
L 370.991003 363.170604 
L 383.777644 336.653365 
L 399.45159 336.609265 
L 409.763397 330.509224 
L 421.312621 324.542755 
L 435.749151 322.961548 
" clip-path="url(#p6c2b4ecff0)" style="fill: none; stroke: #047857; stroke-width: 1.8; stroke-linecap: square"/>
   </g>
   <g id="patch_9">
    <path d="M 51.16 501.976838 
L 51.16 311.374319 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_10">
    <path d="M 51.16 501.976838 
L 454.06292 501.976838 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_48">
    <text style="font-weight: 700; font-size: 13.2px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="51.16" y="305.374319" transform="rotate(-0 51.16 305.374319)">2023-08—2025-12｜费用情景财富</text>
   </g>
  </g>
  <g id="axes_4">
   <g id="patch_11">
    <path d="M 513.685 501.976838 
L 916.58792 501.976838 
L 916.58792 311.374319 
L 513.685 311.374319 
z
" style="fill: #ffffff"/>
   </g>
   <g id="matplotlib.axis_7">
    <g id="xtick_24">
     <g id="line2d_77">
      <g>
       <use xlink:href="#mfeed484c3a" x="519.212129" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_49">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(498.417235 534.251204) rotate(-20)">2023-07</text>
     </g>
    </g>
    <g id="xtick_25">
     <g id="line2d_78">
      <g>
       <use xlink:href="#mfeed484c3a" x="557.159578" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_50">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(536.364684 534.251204) rotate(-20)">2023-10</text>
     </g>
    </g>
    <g id="xtick_26">
     <g id="line2d_79">
      <g>
       <use xlink:href="#mfeed484c3a" x="595.107027" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_51">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(574.291945 534.2659) rotate(-20)">2024-01</text>
     </g>
    </g>
    <g id="xtick_27">
     <g id="line2d_80">
      <g>
       <use xlink:href="#mfeed484c3a" x="632.642005" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_52">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(611.806733 534.280596) rotate(-20)">2024-04</text>
     </g>
    </g>
    <g id="xtick_28">
     <g id="line2d_81">
      <g>
       <use xlink:href="#mfeed484c3a" x="670.176982" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_53">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(649.361899 534.2659) rotate(-20)">2024-07</text>
     </g>
    </g>
    <g id="xtick_29">
     <g id="line2d_82">
      <g>
       <use xlink:href="#mfeed484c3a" x="708.124431" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_54">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(687.309349 534.2659) rotate(-20)">2024-10</text>
     </g>
    </g>
    <g id="xtick_30">
     <g id="line2d_83">
      <g>
       <use xlink:href="#mfeed484c3a" x="746.071881" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_55">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(725.276987 534.251204) rotate(-20)">2025-01</text>
     </g>
    </g>
    <g id="xtick_31">
     <g id="line2d_84">
      <g>
       <use xlink:href="#mfeed484c3a" x="783.194385" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_56">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(762.379303 534.2659) rotate(-20)">2025-04</text>
     </g>
    </g>
    <g id="xtick_32">
     <g id="line2d_85">
      <g>
       <use xlink:href="#mfeed484c3a" x="820.729363" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_57">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(799.934469 534.251204) rotate(-20)">2025-07</text>
     </g>
    </g>
    <g id="xtick_33">
     <g id="line2d_86">
      <g>
       <use xlink:href="#mfeed484c3a" x="858.676812" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_58">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(837.881918 534.251204) rotate(-20)">2025-10</text>
     </g>
    </g>
    <g id="xtick_34">
     <g id="line2d_87">
      <g>
       <use xlink:href="#mfeed484c3a" x="896.624262" y="501.976838" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_59">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'" transform="translate(875.829368 534.251204) rotate(-20)">2026-01</text>
     </g>
    </g>
   </g>
   <g id="matplotlib.axis_8">
    <g id="ytick_20">
     <g id="line2d_88">
      <path d="M 513.685 481.743988 
L 916.58792 481.743988 
" clip-path="url(#pb8aaa9a068)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_89">
      <g>
       <use xlink:href="#mdb1169e9cd" x="513.685" y="481.743988" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_60">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="506.685" y="486.583988" transform="rotate(-0 506.685 486.583988)">-15</text>
     </g>
    </g>
    <g id="ytick_21">
     <g id="line2d_90">
      <path d="M 513.685 448.400554 
L 916.58792 448.400554 
" clip-path="url(#pb8aaa9a068)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_91">
      <g>
       <use xlink:href="#mdb1169e9cd" x="513.685" y="448.400554" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_61">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="506.685" y="453.240554" transform="rotate(-0 506.685 453.240554)">-10</text>
     </g>
    </g>
    <g id="ytick_22">
     <g id="line2d_92">
      <path d="M 513.685 415.057119 
L 916.58792 415.057119 
" clip-path="url(#pb8aaa9a068)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_93">
      <g>
       <use xlink:href="#mdb1169e9cd" x="513.685" y="415.057119" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_62">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="506.685" y="419.897119" transform="rotate(-0 506.685 419.897119)">-5</text>
     </g>
    </g>
    <g id="ytick_23">
     <g id="line2d_94">
      <path d="M 513.685 381.713685 
L 916.58792 381.713685 
" clip-path="url(#pb8aaa9a068)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_95">
      <g>
       <use xlink:href="#mdb1169e9cd" x="513.685" y="381.713685" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_63">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="506.685" y="386.553685" transform="rotate(-0 506.685 386.553685)">0</text>
     </g>
    </g>
    <g id="ytick_24">
     <g id="line2d_96">
      <path d="M 513.685 348.37025 
L 916.58792 348.37025 
" clip-path="url(#pb8aaa9a068)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_97">
      <g>
       <use xlink:href="#mdb1169e9cd" x="513.685" y="348.37025" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_64">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="506.685" y="353.21025" transform="rotate(-0 506.685 353.21025)">5</text>
     </g>
    </g>
    <g id="ytick_25">
     <g id="line2d_98">
      <path d="M 513.685 315.026816 
L 916.58792 315.026816 
" clip-path="url(#pb8aaa9a068)" style="fill: none; stroke: #e2e8f0; stroke-width: 0.7; stroke-linecap: square"/>
     </g>
     <g id="line2d_99">
      <g>
       <use xlink:href="#mdb1169e9cd" x="513.685" y="315.026816" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="text_65">
      <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: end" x="506.685" y="319.866816" transform="rotate(-0 506.685 319.866816)">10</text>
     </g>
    </g>
    <g id="text_66">
     <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: middle" x="482.972656" y="406.675579" transform="rotate(-90 482.972656 406.675579)">相对财富变化（%）</text>
    </g>
   </g>
   <g id="line2d_100">
    <path d="M 531.998769 381.713685 
L 544.78541 379.8902 
L 560.459356 383.007976 
L 569.946219 392.215685 
L 582.320387 391.420524 
L 595.5195 395.174914 
L 607.893668 380.843726 
L 619.855364 377.812497 
L 632.642005 380.64619 
L 647.078534 370.69579 
L 658.627758 369.871445 
L 670.176982 373.017424 
L 682.963622 394.040554 
L 696.162735 395.921563 
L 711.011737 395.192968 
L 720.911072 390.780767 
L 733.697712 396.815737 
L 746.484353 387.664346 
L 760.50841 397.684201 
L 771.232689 403.754305 
L 783.194385 402.25269 
L 797.630915 410.996304 
L 809.180139 419.209142 
L 820.729363 427.200528 
L 833.516003 425.107404 
L 846.302644 420.731296 
L 861.97659 427.479854 
L 872.288397 430.756143 
L 883.837621 433.722873 
L 898.274151 447.915749 
" clip-path="url(#pb8aaa9a068)" style="fill: none; stroke-dasharray: 1.8,2.97; stroke-dashoffset: 0; stroke: #334155; stroke-width: 1.8"/>
   </g>
   <g id="line2d_101">
    <path d="M 531.998769 381.713685 
L 544.78541 378.136386 
L 560.459356 379.760726 
L 569.946219 388.439862 
L 582.320387 385.591092 
L 595.5195 390.521068 
L 607.893668 373.040778 
L 619.855364 366.611156 
L 632.642005 365.933138 
L 647.078534 353.656177 
L 658.627758 351.93685 
L 670.176982 351.592009 
L 682.963622 372.01599 
L 696.162735 372.455145 
L 711.011737 375.788482 
L 720.911072 372.965496 
L 733.697712 380.230174 
L 746.484353 368.018607 
L 760.50841 379.432246 
L 771.232689 386.418759 
L 783.194385 385.039565 
L 797.630915 394.090422 
L 809.180139 402.009086 
L 820.729363 410.942158 
L 833.516003 409.115892 
L 846.302644 404.204853 
L 861.97659 410.465207 
L 872.288397 417.299504 
L 883.837621 421.469856 
L 898.274151 439.057242 
" clip-path="url(#pb8aaa9a068)" style="fill: none; stroke: #2563eb; stroke-width: 1.8; stroke-linecap: square"/>
   </g>
   <g id="line2d_102">
    <path d="M 531.998769 381.713685 
L 544.78541 371.381895 
L 560.459356 368.465443 
L 569.946219 378.923088 
L 582.320387 387.862477 
L 595.5195 387.358038 
L 607.893668 359.594163 
L 619.855364 352.472617 
L 632.642005 370.191898 
L 647.078534 352.246929 
L 658.627758 345.079398 
L 670.176982 340.085346 
L 682.963622 362.61233 
L 696.162735 359.174874 
L 711.011737 373.225072 
L 720.911072 404.94185 
L 733.697712 431.247466 
L 746.484353 403.95461 
L 760.50841 413.124638 
L 771.232689 427.086309 
L 783.194385 414.81528 
L 797.630915 427.807152 
L 809.180139 429.389679 
L 820.729363 450.336096 
L 833.516003 444.929897 
L 846.302644 459.318267 
L 861.97659 460.52047 
L 872.288397 464.968323 
L 883.837621 465.176224 
L 898.274151 493.313088 
" clip-path="url(#pb8aaa9a068)" style="fill: none; stroke-dasharray: 11.52,2.88,1.8,2.88; stroke-dashoffset: 0; stroke: #9333ea; stroke-width: 1.8"/>
   </g>
   <g id="line2d_103">
    <path d="M 531.998769 381.713685 
L 544.78541 372.054276 
L 560.459356 373.845291 
L 569.946219 383.205247 
L 582.320387 383.809842 
L 595.5195 382.186229 
L 607.893668 352.15221 
L 619.855364 345.488631 
L 632.642005 350.001903 
L 647.078534 325.054863 
L 658.627758 320.744225 
L 670.176982 320.769124 
L 682.963622 340.105379 
L 696.162735 340.041122 
L 711.011737 349.84952 
L 720.911072 334.099952 
L 733.697712 342.666904 
L 746.484353 320.03807 
L 760.50841 326.525156 
L 771.232689 339.68303 
L 783.194385 335.825922 
L 797.630915 342.92326 
L 809.180139 353.470967 
L 820.729363 366.640929 
L 833.516003 361.495973 
L 846.302644 364.119589 
L 861.97659 362.329357 
L 872.288397 368.136115 
L 883.837621 364.529659 
L 898.274151 386.772949 
" clip-path="url(#pb8aaa9a068)" style="fill: none; stroke: #047857; stroke-width: 1.8; stroke-linecap: square"/>
   </g>
   <g id="line2d_104">
    <path d="M 513.685 381.713685 
L 916.58792 381.713685 
" clip-path="url(#pb8aaa9a068)" style="fill: none; stroke: #94a3b8; stroke-width: 0.8; stroke-linecap: square"/>
   </g>
   <g id="patch_12">
    <path d="M 513.685 501.976838 
L 513.685 311.374319 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="patch_13">
    <path d="M 513.685 501.976838 
L 916.58792 501.976838 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="text_67">
    <text style="font-weight: 700; font-size: 13.2px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="513.685" y="305.374319" transform="rotate(-0 513.685 305.374319)">2023-08—2025-12｜相对同池等权</text>
   </g>
  </g>
  <g id="text_68">
   <text style="font-size: 10px; font-family: 'Hiragino Sans GB'; text-anchor: start; fill: #475569" x="65.52" y="565.632" transform="rotate(-0 65.52 565.632)">25bp费用情景、计持仓漂移。标题按持有月份，点位按实际开盘日期；最长两段分别起算，缺口不连接，非实盘净值。</text>
  </g>
  <g id="legend_1">
   <g id="line2d_105">
    <path d="M 190.942656 15.73 
L 201.942656 15.73 
L 212.942656 15.73 
" style="fill: none; stroke-dasharray: 6.66,2.88; stroke-dashoffset: 0; stroke: #94a3b8; stroke-width: 1.8"/>
   </g>
   <g id="text_69">
    <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="221.742656" y="19.58" transform="rotate(-0 221.742656 19.58)">同池等权</text>
   </g>
   <g id="line2d_106">
    <path d="M 287.742656 15.73 
L 298.742656 15.73 
L 309.742656 15.73 
" style="fill: none; stroke-dasharray: 1.8,2.97; stroke-dashoffset: 0; stroke: #334155; stroke-width: 1.8"/>
   </g>
   <g id="text_70">
    <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="318.542656" y="19.58" transform="rotate(-0 318.542656 19.58)">旧盈利</text>
   </g>
   <g id="line2d_107">
    <path d="M 373.542656 15.73 
L 384.542656 15.73 
L 395.542656 15.73 
" style="fill: none; stroke: #2563eb; stroke-width: 1.8; stroke-linecap: square"/>
   </g>
   <g id="text_71">
    <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="404.342656" y="19.58" transform="rotate(-0 404.342656 19.58)">细行业盈利V2</text>
   </g>
   <g id="line2d_108">
    <path d="M 496.457344 15.73 
L 507.457344 15.73 
L 518.457344 15.73 
" style="fill: none; stroke-dasharray: 11.52,2.88,1.8,2.88; stroke-dashoffset: 0; stroke: #9333ea; stroke-width: 1.8"/>
   </g>
   <g id="text_72">
    <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="527.257344" y="19.58" transform="rotate(-0 527.257344 19.58)">门类过滤＋缓冲</text>
   </g>
   <g id="line2d_109">
    <path d="M 626.257344 15.73 
L 637.257344 15.73 
L 648.257344 15.73 
" style="fill: none; stroke: #047857; stroke-width: 1.8; stroke-linecap: square"/>
   </g>
   <g id="text_73">
    <text style="font-size: 11px; font-family: 'Hiragino Sans GB'; text-anchor: start" x="657.057344" y="19.58" transform="rotate(-0 657.057344 19.58)">细行业过滤＋缓冲</text>
   </g>
  </g>
 </g>
 <defs>
  <clipPath id="pe8ef39e075">
   <rect x="51.16" y="64.0725" width="402.90292" height="190.60252"/>
  </clipPath>
  <clipPath id="p87212ff3d3">
   <rect x="513.685" y="64.0725" width="402.90292" height="190.60252"/>
  </clipPath>
  <clipPath id="p6c2b4ecff0">
   <rect x="51.16" y="311.374319" width="402.90292" height="190.60252"/>
  </clipPath>
  <clipPath id="pb8aaa9a068">
   <rect x="513.685" y="311.374319" width="402.90292" height="190.60252"/>
  </clipPath>
 </defs>
</svg>


## 8. 本轮吸收与保留的边界

- **吸收为研究默认方法：** 小行业统一比例而非全部保留；主动收益相关、TE／IR、相对与绝对回撤及恢复等待并列；持仓漂移后的费用、相同日期对照、筛后等权和同仓现金对手进入评价。旧冻结结果保留可复现。

- **保留为候选：** 细行业内过滤＋70／85缓冲。样本中费用后IR和相对回撤较好，两个时期相对同池均为正，但相对盈利增量早负晚正，置信区间宽，主动风险仍升高。下一阶段若重新启动，应验证这条固定规则，而非再寻找更高历史IR的阈值。

- **不直接采用的主张：** 31.32%全是拖累股；低波过滤必能把TE降到4%；缓冲普遍保住Alpha；合并行业天然更好；该变体是一条独立低相关赚钱来源。本轮数据都不支持这些保证。

- **仍未完成：** 真正IVOL及市值中性；完整退市／换股和可成交收益链；独立新样本及真实行情模拟账户。当前没有修改已有前向账户、成交规则或LEI技术判定。

当前有界问题已回答：修正方法可用，细行业缓冲值得保留为待验证候选，稳定超额与完整账户效果仍未证实。现有历史上再调阈值不能解决这些缺口，因此本轮收尾。

## 归档与复核范围

| 项目 | 状态 |
| --- | --- |
| 定义、时间、规则 | 完成；三层基准、固定30%四格比较及七档预登记，细行业补充标事后 |
| 实现、数据与数值 | 完成；逐月逐股权重、毛收益、漂移自融资费用及关键配对区间独立复核 |
| 性能、强对手与风险 | 完成；相同日期、费用、筛后等权、同仓现金、片段回撤、机会损失 |
| 稳定性与选择历史 | 完成本次描述；分年／两时期反例保留，全部参数公开，未宣称样本外 |
| 连续账户与生产采用 | 证据边界；缺公司行动和真实成交资格，未启用新前向 |


研究附件保留两次核心运行尝试（首次仅保存诊断表失败，修复数值序列化后按同规则重跑）及一次细行业补充；原家族尝试不重置。来源、输入版本、全部36个方法输出（含重复基准与控制）、费用情景、失败日志和独立复核存于本次原始附件。独立图表、全量表格和临时文件保存在已核验外盘；报告内仅保留轻量展示。
