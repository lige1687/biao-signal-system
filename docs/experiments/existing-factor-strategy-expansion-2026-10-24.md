# 现有因子再组合：A 股三信息选股与美股盈利低扩张加动量（2026-10-24）

## 一句话结论（大白话）

**这次实际测了两项新组合：A 股三项一起选有小幅收益线索，但对简单混合只多约0.05个百分点/月、最差月更差；美股加入低扩张条件有部分历史优势，但再配动量并未稳定胜过强单项。保留研究线索，暂不新增前向策略。**

本轮回答“现有因子还能怎样有依据地组合”，没有增加因子、调权重寻找好结果，或重做其他负责人正在补的股票池。金融理由、两项问题和对照在本轮结果计算前固定。A 股看2015—2025年，美股主要看2015—2024年，另保留更早历史和最近20个月反例。**都是已经看过的历史；报价和公开分组收益均未扣个人交易费用。**

| 本轮问题 | 实际比较 | 改善与代价 | 结论 |
| --- | --- | --- | --- |
| A 股把动量、毛利润、经营现金流一起评分，是否比原方法好 | 同一共同股票池，127个报价完整月份 | 比动量月均多0.142个百分点；比简单混合仅多0.049个百分点，最差月少赚/多亏约1.00个百分点 | 保留有限线索；尚未证明复杂做法值得采用 |
| 美股盈利低扩张股票组与动量各用一半资金，是否更好 | 两种规模，三段历史；同源盈利＋动量及强单项对照 | 大盘主期年化15.26%，比盈利＋动量多1.56个百分点，但比盈利低扩张单项少2.00个百分点 | 低扩张条件值得保留；各半搭配暂不作为通用分散方案 |
| 能否穿越牛熊、胜过母指数 | 目前资料不足以回答 | A股无连续可执行账户；美股为公开组合、缺逐股持仓和个人成本 | 母指数净优势、真实费用和前向效果均未评价 |

## 1. 这两项为什么值得测，以及做到哪里收尾

动量指前一段时间表现较强的股票是否继续较强。A 股把它与企业经营情况一起看：毛利润相对总资产反映经营获利，经营现金流相对总资产提供另一种现金表现。两项财务指标共用资产分母，现金流也受存货、应收款和税费影响，**不能直接解释成“现金证实利润质量”**。

美股先沿用盈利较高、总资产增长较低的股票组，再加入过去第12至第2个月涨幅较高的股票组。年报信息和月度价格信息更新节奏不同，可能互补；资产增长低也可能来自收缩、出售资产或困难，并不天然等于好公司。原文方法见[French盈利与资产增长分组](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/32_ports_me_op_inv.html)和[French动量分组](https://mba.tuck.dartmouth.edu/pages/Faculty/ken.french/Data_Library/det_6_port_form_sz_pr_12_2.html)。

目标是判断是否值得将这些具体搭配继续做成完整策略。本轮完成固定比较、强单项反例、被替换机会和数据限制即可收尾；没有依据设“必赚多少”或用结果反选市场环境。弱结果不再换比例重试。

## 2. 规则、股票范围与当时可知的信息

| 项目 | A 股 | 美股 |
| --- | --- | --- |
| 实际研究范围 | 既有2014年固定600股抽样框架中，财务共同池累计562只，每月142—329只；不代表历史全A股 | French来源合格NYSE/AMEX/NASDAQ股票动态分组；不是标普500或本机当前名单 |
| 日期 | 2015-01—2025-12，共132个月；主比较127个月 | 1963-07—2014-12共618月；2015-01—2024-12共120月；2025-01—2026-08共20月 |
| 新规则 | 行业内动量评分50%、毛利润评分25%、现金流评分25%，选最高20%；这是评分比例 | 初始资金50%盈利低扩张组、50%动量组；之后两部分之间不转钱，每个时期重新从100单位起算 |
| 原规则保留 | 同分按代码；选股数向上取整；行业少于5只全部保留；行业资金按该行业在共同池的股票数分配 | 来源财务格每年6月形成，动量格每月更新；组内市值加权，不能当作不换股持有 |
| 简单关键对手 | 原“动量＋毛利润”和“动量＋现金流”各用一半资金，重复持股合并权重；另外比较动量、低波动、全池、75%动量＋现金 | 从同一32格资料取四个高盈利格，按月各四分之一资金形成单盈利参照，再与动量初始各半；另有强单项和初始半现金 |
| 观察与成交假设 | 旧年报公布日期严格早于决策日；次月既定进出报价；保持原报表版本、陈旧限制与价格修正；无真实撮合 | 公开历史月收益，来源当前重建版本；不能证明每个历史下载或修订时点均可得，也不虚构次日成交 |
| 行业、分红与时点限制 | 原年度行业快照代理，年内变化与完整历史可知性仍有限；使用旧已修正报价，未重建公司行动与可成交资金 | 202608 CRSP/CIZ来源版本，沿用其收益口径；包含金融和公用事业；无逐股行业控制、重叠或交易成本 |

中国毛利润/资产、经营现金流/资产与美国经营利润/账面权益是不同定义，不能合并成同一个因子效果。A股新增三项组合由2026-10-24新合同授权并在计算前固定；旧财务实验原来明确不做这项组合，本轮没有改写旧冻结合同。

## 3. A 股：性能和相对已有信息的增量

下面全部用**相同的127个报价完整月份**。月平均是每个月结果的平均，不是年化；最差月不是完整账户最大回撤。全池对手也被要求完整，因此缺价月份不会暗中保留给某个候选。

| 方法 | 月平均报价收益 | 最差单月 | 下跌月份占比 |
| --- | --- | --- | --- |
| 共同池全部股票均分资金 | 1.213% | -23.50% | 45.7% |
| 只看动量 | 1.200% | -21.10% | 44.9% |
| 动量＋毛利润 | 1.288% | -21.24% | 44.1% |
| 动量＋经营现金流 | 1.298% | -19.57% | 43.3% |
| 新：三项一起评分选股 | 1.343% | -21.41% | 44.1% |
| 两套旧方法各用一半资金 | 1.293% | -20.41% | 44.1% |
| 只选较低波动 | 1.164% | -23.70% | 44.9% |
| 75%动量＋25%零息现金 | 0.900% | -15.82% | 44.9% |

真正关键的增量如下。描述范围通过保持相邻12个月结构的重复抽取估计，帮助观察历史结果有多不稳定；这是已见历史上的探索，**不代表独立验证成功或未来赚钱概率**。最后一列统一取全池下跌的58个月，避免各方法各挑不同的下跌月份。

| 三项新组合相对谁 | 每月平均差额 | 描述范围：仍可能波动多少 | 同池下跌月的平均差额 |
| --- | --- | --- | --- |
| 共同池全部股票均分资金 | +0.129 个百分点 | [-0.100, +0.367] | +0.563 个百分点 |
| 只看动量 | +0.142 个百分点 | [+0.040, +0.378] | +0.377 个百分点 |
| 动量＋毛利润 | +0.054 个百分点 | [-0.058, +0.176] | +0.045 个百分点 |
| 动量＋经营现金流 | +0.044 个百分点 | [-0.084, +0.256] | +0.097 个百分点 |
| 两套旧方法各用一半资金 | +0.049 个百分点 | [-0.035, +0.181] | +0.071 个百分点 |
| 只选较低波动 | +0.179 个百分点 | [-0.123, +0.395] | +0.059 个百分点 |
| 75%动量＋25%零息现金 | +0.443 个百分点 | [+0.187, +0.603] | -1.003 个百分点 |

三项组合相对单动量有正向线索，但换成更强的简单混合后，约0.05个百分点/月的差距仍可能是历史波动。相对简单混合的最差月为−21.41%对−20.41%；相对“动量＋现金流”也未同时改善收益和最差月。75%动量投入的下跌保护更强，不能把新组合多投入股票得到的收益全算成信息价值。

不同历史阶段的月均结果也不一致：

| 时期/共同月份 | 新三项 | 只看动量 | 简单混合 | 低波动 |
| --- | --- | --- | --- | --- |
| 2015—2020 / 71 | 1.481% | 1.293% | 1.460% | 1.113% |
| 2021—2025 / 56 | 1.167% | 1.082% | 1.082% | 1.229% |

2021—2025年新组合比低波动月均少0.062个百分点，最差月−16.64%对−15.38%，下跌月占50%对42.9%。这反驳“组合能普遍改善防守”。不能在看完这张表以后，倒过来声称当时就能知道该切换策略。

### 替换股票实际带来什么

以下是127个共同月份中，各类变化对每月平均收益差额的贡献，单位都是**百分点**；移除一只上涨股票会是负贡献，移除下跌股票会是正贡献。三项相加逐月核对。

| 对手 | 新增持股贡献 | 放弃原持股贡献 | 共同持股调整贡献 | 合计 |
| --- | --- | --- | --- | --- |
| 只看动量 | +0.404 | -0.262 | +0.000 | +0.142 |
| 简单混合 | +0.021 | -0.187 | +0.215 | +0.049 |

相对动量，每月平均换入/换出约13.8只股票，新进股票带来约+0.404，放弃旧持股约−0.262，合计+0.142个百分点。相对简单混合，新组合主要减少持股并重新分配原来共有股票：每月真正新进仅约0.76只，移除约15.63只，共有持股调整约14.30只。这更接近相似信息的再取舍。

相对动量最有利的三个月：2021-12（+5.56个百分点）、2024-12（+2.43）、2021-11（+2.14）；不利的三个月：2025-02（−3.21）、2025-12（−3.04）、2019-03（−2.02）。被放弃的大涨机会没有从结果中删去。

月度目标权重变化约25.31%，简单混合24.34%，动量27.02%。这些只是目标名单变化，未扣除旧持仓涨跌后的权重漂移，**不能当真实换手率或费用**。

### 相关性与缺失资料

相关程度越接近1，表示两者越倾向同方向变化。行业内因子评分的平均相关：毛利润与动量0.174、现金流与动量0.188、两种财务信息0.492。但三项新组合和动量的收益相关为0.992，和简单混合更达0.997；评分较低相关没有自动变成账户分散。

缺报价月份为2020-08、2021-03、2021-07、2021-09、2023-06，最大单月未知持股权重0.518%。全部132个月都保留在明细：缺失收益按0的情景下，新组合月均1.317%，动量1.230%，简单混合1.279%；按−100%的情景下，分别1.303%、1.216%、1.266%。它们只是压力假设，不是真实收益上下界，也不能替代主比较。全132月情景中新组合比动量约+0.087个百分点/月，比127完整月份的+0.142更小，说明缺失月份处理会影响量级。

还有停牌报价估值：新组合进出端标记停牌的平均目标权重约1.13%。完整报价不等于当时能成交。故不将这些月份拼成中国账户净值、累计净超额或年化。

<svg style="display:block;max-width:100%;height:auto" xmlns:xlink="http://www.w3.org/1999/xlink" width="100%" height="auto" viewBox="0 0 604.8 417.6" xmlns="http://www.w3.org/2000/svg" version="1.1">
 <metadata>
  <rdf:RDF xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:cc="http://creativecommons.org/ns#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
   <cc:Work>
    <dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage"/>
    <dc:date>2026-10-24T13:56:20.989278</dc:date>
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
 <g id="cn-monthly-increment-figure_1">
  <g id="cn-monthly-increment-patch_1">
   <path d="M 0 417.6 
L 604.8 417.6 
L 604.8 0 
L 0 0 
z
" style="fill: #fbfaf7"/>
  </g>
  <g id="cn-monthly-increment-axes_1">
   <g id="cn-monthly-increment-patch_2">
    <path d="M 41.899609 200.296391 
L 594 200.296391 
L 594 74.680664 
L 41.899609 74.680664 
z
" style="fill: #fbfaf7"/>
   </g>
   <g id="cn-monthly-increment-patch_3">
    <path d="M 66.995082 152.787943 
L 69.873864 152.787943 
L 69.873864 166.750952 
L 66.995082 166.750952 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_4">
    <path d="M 70.87518 152.787943 
L 73.753962 152.787943 
L 73.753962 165.426254 
L 70.87518 165.426254 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_5">
    <path d="M 74.379784 152.787943 
L 77.258567 152.787943 
L 77.258567 147.178772 
L 74.379784 147.178772 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_6">
    <path d="M 78.259882 152.787943 
L 81.138665 152.787943 
L 81.138665 138.614176 
L 78.259882 138.614176 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_7">
    <path d="M 82.014816 152.787943 
L 84.893598 152.787943 
L 84.893598 175.476102 
L 82.014816 175.476102 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_8">
    <path d="M 85.894914 152.787943 
L 88.773696 152.787943 
L 88.773696 135.131542 
L 85.894914 135.131542 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_9">
    <path d="M 89.649847 152.787943 
L 92.52863 152.787943 
L 92.52863 169.962007 
L 89.649847 169.962007 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_10">
    <path d="M 93.529945 152.787943 
L 96.408728 152.787943 
L 96.408728 143.570903 
L 93.529945 143.570903 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_11">
    <path d="M 97.410043 152.787943 
L 100.288825 152.787943 
L 100.288825 167.387948 
L 97.410043 167.387948 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_12">
    <path d="M 101.164977 152.787943 
L 104.043759 152.787943 
L 104.043759 138.052667 
L 101.164977 138.052667 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_13">
    <path d="M 105.045075 152.787943 
L 107.923857 152.787943 
L 107.923857 141.598549 
L 105.045075 141.598549 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_14">
    <path d="M 108.800008 152.787943 
L 111.67879 152.787943 
L 111.67879 134.948833 
L 108.800008 134.948833 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_15">
    <path d="M 112.680106 152.787943 
L 115.558888 152.787943 
L 115.558888 160.309667 
L 112.680106 160.309667 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_16">
    <path d="M 116.560204 152.787943 
L 119.438986 152.787943 
L 119.438986 154.511415 
L 116.560204 154.511415 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_17">
    <path d="M 120.189973 152.787943 
L 123.068755 152.787943 
L 123.068755 153.869443 
L 120.189973 153.869443 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_18">
    <path d="M 124.070071 152.787943 
L 126.948853 152.787943 
L 126.948853 141.865368 
L 124.070071 141.865368 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_19">
    <path d="M 127.825005 152.787943 
L 130.703787 152.787943 
L 130.703787 144.860719 
L 127.825005 144.860719 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_20">
    <path d="M 131.705103 152.787943 
L 134.583885 152.787943 
L 134.583885 140.796188 
L 131.705103 140.796188 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_21">
    <path d="M 135.460036 152.787943 
L 138.338818 152.787943 
L 138.338818 141.245614 
L 135.460036 141.245614 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_22">
    <path d="M 139.340134 152.787943 
L 142.218916 152.787943 
L 142.218916 149.645801 
L 139.340134 149.645801 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_23">
    <path d="M 143.220232 152.787943 
L 146.099014 152.787943 
L 146.099014 164.264669 
L 143.220232 164.264669 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_24">
    <path d="M 146.975165 152.787943 
L 149.853948 152.787943 
L 149.853948 170.329486 
L 146.975165 170.329486 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_25">
    <path d="M 150.855263 152.787943 
L 153.734046 152.787943 
L 153.734046 147.56121 
L 150.855263 147.56121 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_26">
    <path d="M 154.610197 152.787943 
L 157.488979 152.787943 
L 157.488979 131.950777 
L 154.610197 131.950777 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_27">
    <path d="M 158.490295 152.787943 
L 161.369077 152.787943 
L 161.369077 142.265708 
L 158.490295 142.265708 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_28">
    <path d="M 162.370393 152.787943 
L 165.249175 152.787943 
L 165.249175 147.247254 
L 162.370393 147.247254 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_29">
    <path d="M 165.874997 152.787943 
L 168.75378 152.787943 
L 168.75378 138.580779 
L 165.874997 138.580779 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_30">
    <path d="M 169.755095 152.787943 
L 172.633878 152.787943 
L 172.633878 157.945971 
L 169.755095 157.945971 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_31">
    <path d="M 173.510029 152.787943 
L 176.388811 152.787943 
L 176.388811 135.598121 
L 173.510029 135.598121 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_32">
    <path d="M 177.390127 152.787943 
L 180.268909 152.787943 
L 180.268909 142.921089 
L 177.390127 142.921089 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_33">
    <path d="M 181.14506 152.787943 
L 184.023843 152.787943 
L 184.023843 134.018128 
L 181.14506 134.018128 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_34">
    <path d="M 185.025158 152.787943 
L 187.903941 152.787943 
L 187.903941 177.358172 
L 185.025158 177.358172 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_35">
    <path d="M 188.905256 152.787943 
L 191.784039 152.787943 
L 191.784039 136.035294 
L 188.905256 136.035294 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_36">
    <path d="M 192.66019 152.787943 
L 195.538972 152.787943 
L 195.538972 149.932684 
L 192.66019 149.932684 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_37">
    <path d="M 196.540288 152.787943 
L 199.41907 152.787943 
L 199.41907 163.397925 
L 196.540288 163.397925 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_38">
    <path d="M 200.295221 152.787943 
L 203.174004 152.787943 
L 203.174004 139.452392 
L 200.295221 139.452392 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_39">
    <path d="M 204.175319 152.787943 
L 207.054102 152.787943 
L 207.054102 145.452636 
L 204.175319 145.452636 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_40">
    <path d="M 208.055417 152.787943 
L 210.9342 152.787943 
L 210.9342 158.972503 
L 208.055417 158.972503 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_41">
    <path d="M 211.560022 152.787943 
L 214.438804 152.787943 
L 214.438804 144.675184 
L 211.560022 144.675184 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_42">
    <path d="M 215.44012 152.787943 
L 218.318902 152.787943 
L 218.318902 131.951141 
L 215.44012 131.951141 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_43">
    <path d="M 219.195053 152.787943 
L 222.073836 152.787943 
L 222.073836 137.685269 
L 219.195053 137.685269 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_44">
    <path d="M 223.075151 152.787943 
L 225.953934 152.787943 
L 225.953934 164.003651 
L 223.075151 164.003651 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_45">
    <path d="M 226.830085 152.787943 
L 229.708867 152.787943 
L 229.708867 151.843907 
L 226.830085 151.843907 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_46">
    <path d="M 230.710183 152.787943 
L 233.588965 152.787943 
L 233.588965 147.419477 
L 230.710183 147.419477 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_47">
    <path d="M 234.590281 152.787943 
L 237.469063 152.787943 
L 237.469063 147.087437 
L 234.590281 147.087437 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_48">
    <path d="M 238.345214 152.787943 
L 241.223997 152.787943 
L 241.223997 149.646808 
L 238.345214 149.646808 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_49">
    <path d="M 242.225312 152.787943 
L 245.104095 152.787943 
L 245.104095 148.407117 
L 242.225312 148.407117 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_50">
    <path d="M 245.980246 152.787943 
L 248.859028 152.787943 
L 248.859028 149.534644 
L 245.980246 149.534644 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_51">
    <path d="M 249.860344 152.787943 
L 252.739126 152.787943 
L 252.739126 147.07388 
L 249.860344 147.07388 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_52">
    <path d="M 253.740442 152.787943 
L 256.619224 152.787943 
L 256.619224 161.787535 
L 253.740442 161.787535 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_53">
    <path d="M 257.245046 152.787943 
L 260.123829 152.787943 
L 260.123829 179.090132 
L 257.245046 179.090132 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_54">
    <path d="M 261.125144 152.787943 
L 264.003927 152.787943 
L 264.003927 139.468385 
L 261.125144 139.468385 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_55">
    <path d="M 264.880078 152.787943 
L 267.75886 152.787943 
L 267.75886 149.310546 
L 264.880078 149.310546 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_56">
    <path d="M 268.760176 152.787943 
L 271.638958 152.787943 
L 271.638958 140.350289 
L 268.760176 140.350289 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_57">
    <path d="M 272.515109 152.787943 
L 275.393892 152.787943 
L 275.393892 143.217487 
L 272.515109 143.217487 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_58">
    <path d="M 276.395207 152.787943 
L 279.27399 152.787943 
L 279.27399 164.171477 
L 276.395207 164.171477 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_59">
    <path d="M 280.275305 152.787943 
L 283.154087 152.787943 
L 283.154087 144.6374 
L 280.275305 144.6374 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_60">
    <path d="M 284.030239 152.787943 
L 286.909021 152.787943 
L 286.909021 152.543697 
L 284.030239 152.543697 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_61">
    <path d="M 287.910337 152.787943 
L 290.789119 152.787943 
L 290.789119 170.697629 
L 287.910337 170.697629 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_62">
    <path d="M 291.66527 152.787943 
L 294.544052 152.787943 
L 294.544052 164.079087 
L 291.66527 164.079087 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_63">
    <path d="M 295.545368 152.787943 
L 298.42415 152.787943 
L 298.42415 162.619477 
L 295.545368 162.619477 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_64">
    <path d="M 299.425466 152.787943 
L 302.304248 152.787943 
L 302.304248 136.626016 
L 299.425466 136.626016 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_65">
    <path d="M 303.055235 152.787943 
L 305.934017 152.787943 
L 305.934017 149.117281 
L 303.055235 149.117281 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_66">
    <path d="M 306.935333 152.787943 
L 309.814115 152.787943 
L 309.814115 148.239465 
L 306.935333 148.239465 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_67">
    <path d="M 310.690267 152.787943 
L 313.569049 152.787943 
L 313.569049 158.649012 
L 310.690267 158.649012 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_68">
    <path d="M 314.570365 152.787943 
L 317.449147 152.787943 
L 317.449147 149.710254 
L 314.570365 149.710254 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_69">
    <path d="M 318.325298 152.787943 
L 321.20408 152.787943 
L 321.20408 152.517877 
L 318.325298 152.517877 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_70">
    <path d="M 0 0 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_71">
    <path d="M 326.085494 152.787943 
L 328.964276 152.787943 
L 328.964276 138.51192 
L 326.085494 138.51192 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_72">
    <path d="M 329.840427 152.787943 
L 332.71921 152.787943 
L 332.71921 152.987814 
L 329.840427 152.987814 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_73">
    <path d="M 333.720525 152.787943 
L 336.599308 152.787943 
L 336.599308 146.101445 
L 333.720525 146.101445 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_74">
    <path d="M 337.475459 152.787943 
L 340.354241 152.787943 
L 340.354241 155.786156 
L 337.475459 155.786156 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_75">
    <path d="M 341.355557 152.787943 
L 344.234339 152.787943 
L 344.234339 167.439628 
L 341.355557 167.439628 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_76">
    <path d="M 345.235655 152.787943 
L 348.114437 152.787943 
L 348.114437 157.775593 
L 345.235655 157.775593 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_77">
    <path d="M 0 0 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_78">
    <path d="M 352.620357 152.787943 
L 355.49914 152.787943 
L 355.49914 157.363487 
L 352.620357 157.363487 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_79">
    <path d="M 356.375291 152.787943 
L 359.254073 152.787943 
L 359.254073 157.667553 
L 356.375291 157.667553 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_80">
    <path d="M 360.255389 152.787943 
L 363.134171 152.787943 
L 363.134171 144.460426 
L 360.255389 144.460426 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_81">
    <path d="M 0 0 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_82">
    <path d="M 367.89042 152.787943 
L 370.769203 152.787943 
L 370.769203 129.190838 
L 367.89042 129.190838 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_83">
    <path d="M 0 0 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_84">
    <path d="M 375.525452 152.787943 
L 378.404234 152.787943 
L 378.404234 178.436985 
L 375.525452 178.436985 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_85">
    <path d="M 379.40555 152.787943 
L 382.284332 152.787943 
L 382.284332 124.958305 
L 379.40555 124.958305 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_86">
    <path d="M 383.160483 152.787943 
L 386.039266 152.787943 
L 386.039266 80.39047 
L 383.160483 80.39047 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_87">
    <path d="M 387.040581 152.787943 
L 389.919364 152.787943 
L 389.919364 138.316941 
L 387.040581 138.316941 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_88">
    <path d="M 390.920679 152.787943 
L 393.799462 152.787943 
L 393.799462 170.838321 
L 390.920679 170.838321 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_89">
    <path d="M 394.425284 152.787943 
L 397.304066 152.787943 
L 397.304066 154.496543 
L 394.425284 154.496543 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_90">
    <path d="M 398.305382 152.787943 
L 401.184164 152.787943 
L 401.184164 150.043552 
L 398.305382 150.043552 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_91">
    <path d="M 402.060315 152.787943 
L 404.939098 152.787943 
L 404.939098 173.147104 
L 402.060315 173.147104 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_92">
    <path d="M 405.940413 152.787943 
L 408.819196 152.787943 
L 408.819196 126.806447 
L 405.940413 126.806447 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_93">
    <path d="M 409.695347 152.787943 
L 412.574129 152.787943 
L 412.574129 161.948677 
L 409.695347 161.948677 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_94">
    <path d="M 413.575445 152.787943 
L 416.454227 152.787943 
L 416.454227 142.851439 
L 413.575445 142.851439 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_95">
    <path d="M 417.455543 152.787943 
L 420.334325 152.787943 
L 420.334325 147.474883 
L 417.455543 147.474883 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_96">
    <path d="M 421.210476 152.787943 
L 424.089259 152.787943 
L 424.089259 158.822382 
L 421.210476 158.822382 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_97">
    <path d="M 425.090574 152.787943 
L 427.969357 152.787943 
L 427.969357 150.502472 
L 425.090574 150.502472 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_98">
    <path d="M 428.845508 152.787943 
L 431.72429 152.787943 
L 431.72429 156.404595 
L 428.845508 156.404595 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_99">
    <path d="M 432.725606 152.787943 
L 435.604388 152.787943 
L 435.604388 167.575731 
L 432.725606 167.575731 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_100">
    <path d="M 436.605704 152.787943 
L 439.484486 152.787943 
L 439.484486 139.959414 
L 436.605704 139.959414 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_101">
    <path d="M 440.110308 152.787943 
L 442.989091 152.787943 
L 442.989091 137.122856 
L 440.110308 137.122856 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_102">
    <path d="M 443.990406 152.787943 
L 446.869189 152.787943 
L 446.869189 135.62455 
L 443.990406 135.62455 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_103">
    <path d="M 447.74534 152.787943 
L 450.624122 152.787943 
L 450.624122 157.120656 
L 447.74534 157.120656 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_104">
    <path d="M 0 0 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_105">
    <path d="M 455.380371 152.787943 
L 458.259154 152.787943 
L 458.259154 139.56914 
L 455.380371 139.56914 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_106">
    <path d="M 459.260469 152.787943 
L 462.139252 152.787943 
L 462.139252 148.074125 
L 459.260469 148.074125 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_107">
    <path d="M 463.140567 152.787943 
L 466.019349 152.787943 
L 466.019349 149.542659 
L 463.140567 149.542659 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_108">
    <path d="M 466.895501 152.787943 
L 469.774283 152.787943 
L 469.774283 154.120915 
L 466.895501 154.120915 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_109">
    <path d="M 470.775599 152.787943 
L 473.654381 152.787943 
L 473.654381 146.173942 
L 470.775599 146.173942 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_110">
    <path d="M 474.530532 152.787943 
L 477.409314 152.787943 
L 477.409314 143.787949 
L 474.530532 143.787949 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_111">
    <path d="M 478.41063 152.787943 
L 481.289412 152.787943 
L 481.289412 133.642689 
L 478.41063 133.642689 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_112">
    <path d="M 482.290728 152.787943 
L 485.16951 152.787943 
L 485.16951 154.542751 
L 482.290728 154.542751 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_113">
    <path d="M 485.920497 152.787943 
L 488.799279 152.787943 
L 488.799279 159.811009 
L 485.920497 159.811009 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_114">
    <path d="M 489.800595 152.787943 
L 492.679377 152.787943 
L 492.679377 140.383527 
L 489.800595 140.383527 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_115">
    <path d="M 493.555529 152.787943 
L 496.434311 152.787943 
L 496.434311 143.532245 
L 493.555529 143.532245 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_116">
    <path d="M 497.435627 152.787943 
L 500.314409 152.787943 
L 500.314409 149.249077 
L 497.435627 149.249077 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_117">
    <path d="M 501.19056 152.787943 
L 504.069342 152.787943 
L 504.069342 151.677696 
L 501.19056 151.677696 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_118">
    <path d="M 505.070658 152.787943 
L 507.94944 152.787943 
L 507.94944 143.456101 
L 505.070658 143.456101 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_119">
    <path d="M 508.950756 152.787943 
L 511.829538 152.787943 
L 511.829538 153.304318 
L 508.950756 153.304318 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_120">
    <path d="M 512.705689 152.787943 
L 515.584472 152.787943 
L 515.584472 158.634988 
L 512.705689 158.634988 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_121">
    <path d="M 516.585787 152.787943 
L 519.46457 152.787943 
L 519.46457 153.604926 
L 516.585787 153.604926 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_122">
    <path d="M 520.340721 152.787943 
L 523.219503 152.787943 
L 523.219503 121.184919 
L 520.340721 121.184919 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_123">
    <path d="M 524.220819 152.787943 
L 527.099601 152.787943 
L 527.099601 155.11581 
L 524.220819 155.11581 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_124">
    <path d="M 528.100917 152.787943 
L 530.979699 152.787943 
L 530.979699 194.586585 
L 528.100917 194.586585 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_125">
    <path d="M 531.605521 152.787943 
L 534.484304 152.787943 
L 534.484304 169.279034 
L 531.605521 169.279034 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_126">
    <path d="M 535.485619 152.787943 
L 538.364402 152.787943 
L 538.364402 154.711412 
L 535.485619 154.711412 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_127">
    <path d="M 539.240553 152.787943 
L 542.119335 152.787943 
L 542.119335 165.612203 
L 539.240553 165.612203 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_128">
    <path d="M 543.120651 152.787943 
L 545.999433 152.787943 
L 545.999433 167.91973 
L 543.120651 167.91973 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_129">
    <path d="M 546.875584 152.787943 
L 549.754367 152.787943 
L 549.754367 134.898026 
L 546.875584 134.898026 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_130">
    <path d="M 550.755682 152.787943 
L 553.634465 152.787943 
L 553.634465 166.446734 
L 550.755682 166.446734 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_131">
    <path d="M 554.63578 152.787943 
L 557.514563 152.787943 
L 557.514563 155.236836 
L 554.63578 155.236836 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_132">
    <path d="M 558.390714 152.787943 
L 561.269496 152.787943 
L 561.269496 168.298109 
L 558.390714 168.298109 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_133">
    <path d="M 562.270812 152.787943 
L 565.149594 152.787943 
L 565.149594 159.018617 
L 562.270812 159.018617 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_134">
    <path d="M 566.025745 152.787943 
L 568.904528 152.787943 
L 568.904528 192.402765 
L 566.025745 192.402765 
z
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-matplotlib.axis_1">
    <g id="cn-monthly-increment-xtick_1">
     <g id="cn-monthly-increment-line2d_1">
      <path d="M 114.119497 200.296391 
L 114.119497 74.680664 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_2">
      <defs>
       <path id="cn-monthly-increment-meee8b6f55d" d="M 0 0 
L 0 3.5 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#cn-monthly-increment-meee8b6f55d" x="114.119497" y="200.296391" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-xtick_2">
     <g id="cn-monthly-increment-line2d_3">
      <path d="M 205.61471 200.296391 
L 205.61471 74.680664 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_4">
      <g>
       <use xlink:href="#cn-monthly-increment-meee8b6f55d" x="205.61471" y="200.296391" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-xtick_3">
     <g id="cn-monthly-increment-line2d_5">
      <path d="M 296.984759 200.296391 
L 296.984759 74.680664 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_6">
      <g>
       <use xlink:href="#cn-monthly-increment-meee8b6f55d" x="296.984759" y="200.296391" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-xtick_4">
     <g id="cn-monthly-increment-line2d_7">
      <path d="M 388.479972 200.296391 
L 388.479972 74.680664 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_8">
      <g>
       <use xlink:href="#cn-monthly-increment-meee8b6f55d" x="388.479972" y="200.296391" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-xtick_5">
     <g id="cn-monthly-increment-line2d_9">
      <path d="M 479.850021 200.296391 
L 479.850021 74.680664 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_10">
      <g>
       <use xlink:href="#cn-monthly-increment-meee8b6f55d" x="479.850021" y="200.296391" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-xtick_6">
     <g id="cn-monthly-increment-line2d_11">
      <path d="M 571.345234 200.296391 
L 571.345234 74.680664 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_12">
      <g>
       <use xlink:href="#cn-monthly-increment-meee8b6f55d" x="571.345234" y="200.296391" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
   </g>
   <g id="cn-monthly-increment-matplotlib.axis_2">
    <g id="cn-monthly-increment-ytick_1">
     <g id="cn-monthly-increment-line2d_13">
      <path d="M 41.899609 178.814547 
L 594 178.814547 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_14">
      <defs>
       <path id="cn-monthly-increment-m5da8443694" d="M 0 0 
L -3.5 0 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#cn-monthly-increment-m5da8443694" x="41.899609" y="178.814547" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_1">
      <!-- -2 -->
      <g transform="translate(26.008984 182.454683) scale(0.1 -0.1)">
       <defs>
        <path id="cn-monthly-increment-ArialUnicodeMS-10" d="M 1925 1375 
L 206 1375 
L 206 1941 
L 1925 1941 
L 1925 1375 
z
" transform="scale(0.015625)"/>
        <path id="cn-monthly-increment-ArialUnicodeMS-15" d="M 3231 0 
L 197 0 
Q 197 388 467 784 
Q 738 1181 1478 1778 
Q 1931 2141 2287 2539 
Q 2644 2938 2644 3341 
Q 2644 3688 2398 3914 
Q 2153 4141 1778 4141 
Q 1400 4141 1144 3908 
Q 888 3675 884 3213 
L 306 3278 
Q 359 3922 764 4262 
Q 1169 4603 1791 4603 
Q 2466 4603 2842 4229 
Q 3219 3856 3219 3328 
Q 3219 2888 2901 2436 
Q 2584 1984 1638 1228 
Q 1141 831 978 544 
L 3231 544 
L 3231 0 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-10"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15" transform="translate(33.296875 0)"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-ytick_2">
     <g id="cn-monthly-increment-line2d_15">
      <path d="M 41.899609 152.787943 
L 594 152.787943 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_16">
      <g>
       <use xlink:href="#cn-monthly-increment-m5da8443694" x="41.899609" y="152.787943" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_2">
      <!-- 0 -->
      <g transform="translate(29.338672 156.42808) scale(0.1 -0.1)">
       <defs>
        <path id="cn-monthly-increment-ArialUnicodeMS-13" d="M 1778 4603 
Q 3272 4603 3272 2259 
Q 3272 1075 2886 498 
Q 2500 -78 1778 -78 
Q 288 -78 288 2259 
Q 288 3444 673 4023 
Q 1059 4603 1778 4603 
z
M 1778 384 
Q 2231 384 2462 823 
Q 2694 1263 2694 2259 
Q 2694 2953 2592 3351 
Q 2491 3750 2286 3945 
Q 2081 4141 1772 4141 
Q 1319 4141 1091 3694 
Q 863 3247 863 2259 
Q 863 1575 966 1175 
Q 1069 775 1272 579 
Q 1475 384 1778 384 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-13"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-ytick_3">
     <g id="cn-monthly-increment-line2d_17">
      <path d="M 41.899609 126.76134 
L 594 126.76134 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_18">
      <g>
       <use xlink:href="#cn-monthly-increment-m5da8443694" x="41.899609" y="126.76134" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_3">
      <!-- 2 -->
      <g transform="translate(29.338672 130.401476) scale(0.1 -0.1)">
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-ytick_4">
     <g id="cn-monthly-increment-line2d_19">
      <path d="M 41.899609 100.734736 
L 594 100.734736 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_20">
      <g>
       <use xlink:href="#cn-monthly-increment-m5da8443694" x="41.899609" y="100.734736" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_4">
      <!-- 4 -->
      <g transform="translate(29.338672 104.374873) scale(0.1 -0.1)">
       <defs>
        <path id="cn-monthly-increment-ArialUnicodeMS-17" d="M 3263 1094 
L 2644 1094 
L 2644 0 
L 2081 0 
L 2081 1094 
L 97 1094 
L 97 1613 
L 2181 4581 
L 2644 4581 
L 2644 1613 
L 3263 1613 
L 3263 1094 
z
M 2081 1613 
L 2081 3681 
L 2069 3681 
L 647 1613 
L 2081 1613 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-17"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-ytick_5">
     <g id="cn-monthly-increment-line2d_21">
      <path d="M 41.899609 74.708132 
L 594 74.708132 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_22">
      <g>
       <use xlink:href="#cn-monthly-increment-m5da8443694" x="41.899609" y="74.708132" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_5">
      <!-- 6 -->
      <g transform="translate(29.338672 78.348269) scale(0.1 -0.1)">
       <defs>
        <path id="cn-monthly-increment-ArialUnicodeMS-19" d="M 838 2363 
Q 1225 2969 1941 2969 
Q 2503 2969 2897 2553 
Q 3291 2138 3291 1491 
Q 3291 838 2898 380 
Q 2506 -78 1856 -78 
Q 1197 -78 733 409 
Q 269 897 269 2144 
Q 269 3369 689 3986 
Q 1109 4603 1906 4603 
Q 2422 4603 2778 4315 
Q 3134 4028 3213 3463 
L 2650 3413 
Q 2497 4141 1875 4141 
Q 1444 4141 1134 3712 
Q 825 3284 825 2363 
L 838 2363 
z
M 1844 384 
Q 2231 384 2472 696 
Q 2713 1009 2713 1453 
Q 2713 1897 2472 2187 
Q 2231 2478 1825 2478 
Q 1453 2478 1184 2204 
Q 916 1931 916 1484 
Q 916 1028 1180 706 
Q 1444 384 1844 384 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-19"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-text_6">
     <!-- 当月收益差：百分点 -->
     <g transform="translate(19.909375 182.488527) rotate(-90) scale(0.1 -0.1)">
      <defs>
       <path id="cn-monthly-increment-ArialUnicodeMS-31e2" d="M 5422 -384 
L 4959 -384 
L 4959 -19 
L 788 -19 
L 788 422 
L 4959 422 
L 4959 1363 
L 1147 1363 
L 1147 1806 
L 4959 1806 
L 4959 2669 
L 831 2669 
L 831 3109 
L 3091 3109 
L 3091 5313 
L 3578 5313 
L 3578 3109 
L 5422 3109 
L 5422 -384 
z
M 5619 4716 
Q 5097 3884 4409 3284 
L 3988 3628 
Q 4675 4163 5209 4972 
L 5619 4716 
z
M 2675 3597 
L 2241 3272 
Q 1669 4072 909 4634 
L 1253 4959 
Q 2041 4366 2675 3597 
z
" transform="scale(0.015625)"/>
       <path id="cn-monthly-increment-ArialUnicodeMS-3997" d="M 5044 206 
Q 5044 -19 4897 -150 
Q 4750 -281 4500 -281 
L 3725 -281 
L 3531 231 
L 4359 206 
Q 4519 197 4519 341 
L 4519 1594 
L 2363 1594 
Q 2119 463 941 -488 
L 550 -91 
Q 1172 356 1520 920 
Q 1869 1484 1869 2053 
L 1869 5013 
L 5044 5013 
L 5044 206 
z
M 4519 3541 
L 4519 4544 
L 2375 4544 
L 2375 3541 
L 4519 3541 
z
M 4519 2059 
L 4519 3072 
L 2388 3072 
L 2375 2059 
L 4519 2059 
z
" transform="scale(0.015625)"/>
       <path id="cn-monthly-increment-ArialUnicodeMS-37c5" d="M 6088 -13 
L 5728 -391 
Q 5000 -66 4391 716 
Q 3878 91 2938 -447 
L 2584 -116 
L 2584 -434 
L 2100 -434 
L 2100 1313 
L 647 825 
L 428 1247 
Q 509 1284 621 1318 
Q 734 1353 763 1369 
L 763 4641 
L 1247 4641 
L 1247 1528 
L 2100 1838 
L 2100 5247 
L 2584 5247 
L 2584 -56 
Q 3647 494 4147 1147 
Q 3669 1850 3463 2719 
Q 3253 2297 2975 1925 
L 2613 2272 
Q 3469 3409 3525 5313 
L 4006 5159 
Q 4006 4703 3916 4166 
L 5813 4166 
L 5813 3700 
L 5422 3700 
Q 5363 2247 4697 1147 
Q 5272 319 6088 -13 
z
M 4947 3700 
L 3816 3700 
L 3763 3500 
Q 3975 2297 4416 1588 
Q 4878 2472 4947 3700 
z
" transform="scale(0.015625)"/>
       <path id="cn-monthly-increment-ArialUnicodeMS-4959" d="M 5191 5063 
Q 4775 4500 4072 4000 
L 3706 4341 
Q 4428 4822 4788 5375 
L 5191 5063 
z
M 2675 4306 
L 2259 3994 
Q 1838 4713 1197 5075 
L 1631 5350 
Q 2178 5041 2675 4306 
z
M 5869 3506 
L 531 3506 
L 531 3975 
L 5869 3975 
L 5869 3506 
z
M 6144 2150 
L 5831 1753 
Q 5544 1859 5209 2034 
L 5209 353 
L 5984 353 
L 5984 -116 
L 403 -116 
L 403 353 
L 1203 353 
L 1203 2113 
Q 906 1969 609 1875 
L 288 2284 
Q 1559 2691 2322 3463 
L 2688 3116 
Q 2044 2509 1313 2150 
L 5006 2150 
Q 4272 2588 3738 3169 
L 4128 3481 
Q 4856 2681 6144 2150 
z
M 4691 366 
L 4691 1709 
L 4044 1709 
L 4044 366 
L 4691 366 
z
M 3547 366 
L 3547 1709 
L 2847 1709 
L 2847 366 
L 3547 366 
z
M 2350 353 
L 2350 1684 
L 1703 1684 
L 1703 353 
L 2350 353 
z
" transform="scale(0.015625)"/>
       <path id="cn-monthly-increment-ArialUnicodeMS-307d" d="M 5991 -122 
L 1209 -122 
L 1209 347 
L 3284 347 
L 3284 1178 
L 1863 1178 
Q 1419 619 588 159 
L 300 581 
Q 1531 1266 1888 2169 
L 697 2169 
L 697 2631 
L 2981 2631 
L 2981 3188 
L 1319 3188 
L 1319 3634 
L 2981 3634 
L 2981 4122 
L 947 4122 
L 947 4581 
L 2291 4581 
Q 2069 4831 1563 5088 
L 2069 5350 
Q 2581 5003 2822 4588 
L 3647 4588 
Q 4069 4869 4313 5375 
L 4781 5147 
Q 4534 4741 4347 4603 
L 4347 4588 
L 5581 4588 
L 5575 4122 
L 3463 4122 
L 3463 3634 
L 5209 3634 
L 5209 3188 
L 3463 3188 
L 3463 2631 
L 5838 2631 
L 5838 2169 
L 2413 2169 
Q 2375 2000 2150 1644 
L 5497 1644 
L 5497 1178 
L 3763 1178 
L 3763 347 
L 5991 347 
L 5991 -122 
z
" transform="scale(0.015625)"/>
       <path id="cn-monthly-increment-ArialUnicodeMS-19f6" d="M 3516 2675 
L 2875 2675 
L 2875 3316 
L 3516 3316 
L 3516 2675 
z
M 3516 0 
L 2875 0 
L 2875 641 
L 3516 641 
L 3516 0 
z
" transform="scale(0.015625)"/>
       <path id="cn-monthly-increment-ArialUnicodeMS-490d" d="M 5850 4506 
L 3572 4506 
Q 3538 4184 3372 3725 
L 5088 3725 
L 5088 -409 
L 4581 -409 
L 4581 91 
L 1941 91 
L 1941 -428 
L 1434 -428 
L 1434 3725 
L 2822 3725 
Q 3000 4009 3066 4506 
L 628 4506 
L 628 4991 
L 5850 4991 
L 5850 4506 
z
M 4581 2175 
L 4581 3238 
L 1941 3238 
L 1941 2175 
L 4581 2175 
z
M 4581 575 
L 4581 1691 
L 1941 1691 
L 1941 575 
L 4581 575 
z
" transform="scale(0.015625)"/>
       <path id="cn-monthly-increment-ArialUnicodeMS-2495" d="M 5991 3003 
L 5684 2553 
Q 4856 3041 4451 3534 
Q 4047 4028 3781 4831 
L 4319 4984 
Q 4375 4356 4829 3825 
Q 5284 3294 5991 3003 
z
M 2613 4697 
Q 2169 3484 800 2547 
L 416 2919 
Q 1731 3741 2188 4934 
L 2613 4697 
z
M 4872 2931 
Q 4844 1956 4730 1092 
Q 4616 228 4430 7 
Q 4244 -213 3847 -213 
Q 3469 -213 2894 -78 
L 2747 481 
Q 3503 269 3834 269 
Q 4013 269 4128 639 
Q 4244 1009 4341 2463 
L 3138 2463 
Q 2869 263 831 -441 
L 525 -31 
Q 2372 478 2631 2463 
L 1556 2463 
L 1556 2931 
L 4872 2931 
z
" transform="scale(0.015625)"/>
       <path id="cn-monthly-increment-ArialUnicodeMS-4348" d="M 5522 4225 
L 3213 4225 
L 3213 3597 
L 4972 3597 
L 4972 1459 
L 1338 1459 
L 1338 3597 
L 2725 3597 
L 2725 5313 
L 3213 5313 
L 3213 4666 
L 5522 4666 
L 5522 4225 
z
M 4513 1900 
L 4513 3156 
L 1825 3156 
L 1825 1900 
L 4513 1900 
z
M 6081 -56 
L 5619 -325 
Q 5188 509 4544 1031 
L 4922 1288 
Q 5672 631 6081 -56 
z
M 1856 1044 
Q 1550 141 763 -453 
L 319 -91 
Q 1059 356 1447 1247 
L 1850 1044 
L 1856 1044 
z
M 4538 -109 
L 4072 -288 
Q 3759 481 3272 997 
L 3681 1197 
Q 4216 653 4538 -109 
z
M 3200 -134 
L 2700 -275 
Q 2519 444 2047 1013 
L 2463 1184 
Q 2925 600 3200 -134 
z
" transform="scale(0.015625)"/>
      </defs>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-31e2"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3997" transform="translate(100 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-37c5" transform="translate(200 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-4959" transform="translate(300 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-307d" transform="translate(400 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-19f6" transform="translate(500 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-490d" transform="translate(600 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2495" transform="translate(700 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-4348" transform="translate(800 0)"/>
     </g>
    </g>
   </g>
   <g id="cn-monthly-increment-line2d_23">
    <path d="M 41.899609 152.787943 
L 594 152.787943 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #777777; stroke-width: 0.7; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-line2d_24">
    <path d="M 323.644787 200.296391 
L 323.644787 74.680664 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #c59f70; stroke-opacity: 0.7; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-line2d_25">
    <path d="M 350.179651 200.296391 
L 350.179651 74.680664 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #c59f70; stroke-opacity: 0.7; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-line2d_26">
    <path d="M 365.449714 200.296391 
L 365.449714 74.680664 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #c59f70; stroke-opacity: 0.7; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-line2d_27">
    <path d="M 373.20991 200.296391 
L 373.20991 74.680664 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #c59f70; stroke-opacity: 0.7; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-line2d_28">
    <path d="M 453.064829 200.296391 
L 453.064829 74.680664 
" clip-path="url(#cn-monthly-increment-p8441f1c113)" style="fill: none; stroke: #c59f70; stroke-opacity: 0.7; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-patch_135">
    <path d="M 41.899609 200.296391 
L 41.899609 74.680664 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-patch_136">
    <path d="M 41.899609 200.296391 
L 594 200.296391 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-text_7">
    <!-- 相对只看动量 -->
    <g transform="translate(41.899609 68.680664) scale(0.12 -0.12)">
     <defs>
      <path id="cn-monthly-increment-ArialUnicodeMS-4987" d="M 3009 1791 
L 2566 1503 
Q 2322 1975 2003 2406 
L 2003 -416 
L 1509 -416 
L 1509 2094 
Q 1313 1497 659 678 
L 275 972 
Q 1053 1969 1459 3603 
L 519 3603 
L 519 4072 
L 1516 4072 
L 1516 5300 
L 2003 5300 
L 2003 4072 
L 2881 4072 
L 2881 3603 
L 2003 3603 
L 2003 2900 
L 2131 2975 
Q 2681 2434 3009 1791 
z
M 5691 -416 
L 5178 -416 
L 5178 38 
L 3659 38 
L 3659 -416 
L 3150 -416 
L 3150 4966 
L 5691 4966 
L 5691 -416 
z
M 5178 3547 
L 5178 4500 
L 3659 4500 
L 3659 3547 
L 5178 3547 
z
M 5178 2059 
L 5178 3078 
L 3659 3078 
L 3659 2059 
L 5178 2059 
z
M 5178 506 
L 5178 1594 
L 3659 1594 
L 3659 506 
L 5178 506 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-2e88" d="M 5856 3616 
L 5247 3616 
L 5247 38 
Q 5206 -163 5042 -273 
Q 4878 -384 4806 -384 
L 4103 -384 
L 3944 103 
Q 4438 63 4678 63 
Q 4716 63 4763 134 
L 4763 3616 
L 2988 3616 
L 2988 4084 
L 4763 4084 
L 4763 5306 
L 5247 5306 
L 5247 4084 
L 5856 4084 
L 5856 3616 
z
M 3175 366 
L 2694 153 
Q 2422 1059 2100 1538 
Q 1609 353 525 -384 
L 153 -13 
Q 1288 719 1813 1984 
Q 1306 2706 628 3256 
L 984 3541 
Q 1794 2828 2009 2497 
Q 2341 3403 2381 4116 
L 359 4116 
L 359 4556 
L 2869 4556 
Q 2844 3303 2328 2028 
Q 2866 1222 3175 366 
z
M 4441 1453 
L 3988 1178 
Q 3663 2072 3091 2700 
L 3444 2950 
Q 4084 2334 4441 1453 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-2679" d="M 5100 2081 
L 1375 2081 
L 1375 4941 
L 5100 4941 
L 5100 2081 
z
M 4588 2566 
L 4588 4453 
L 1869 4453 
L 1869 2566 
L 4588 2566 
z
M 2816 1594 
Q 2166 563 703 -219 
L 372 213 
Q 1778 919 2400 1894 
L 2816 1594 
z
M 5941 109 
L 5563 -256 
Q 4828 866 3622 1522 
L 3981 1869 
Q 5125 1297 5941 109 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-499a" d="M 5838 3041 
L 2713 3041 
L 2484 2753 
L 5044 2753 
L 5044 -403 
L 4556 -403 
L 4556 -63 
L 2247 -63 
L 2247 -428 
L 1759 -428 
L 1759 2028 
Q 1181 1575 794 1350 
L 453 1759 
Q 1453 2284 2069 3041 
L 703 3041 
L 703 3475 
L 2381 3475 
Q 2466 3591 2547 3803 
L 1241 3803 
L 1241 4238 
L 2719 4238 
Q 2769 4369 2791 4481 
Q 1438 4403 1119 4403 
L 903 4856 
Q 3616 4878 5141 5234 
L 5350 4856 
Q 4363 4597 3297 4519 
Q 3259 4334 3213 4238 
L 5197 4238 
L 5197 3803 
L 3091 3803 
Q 3025 3591 2963 3475 
L 5838 3475 
L 5838 3041 
z
M 4556 1978 
L 4556 2284 
L 2247 2284 
L 2247 1978 
L 4556 1978 
z
M 4556 1216 
L 4556 1544 
L 2247 1544 
L 2247 1216 
L 4556 1216 
z
M 4556 409 
L 4556 781 
L 2247 781 
L 2247 409 
L 4556 409 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-2537" d="M 5678 3834 
Q 5613 2631 5508 1595 
Q 5403 559 5328 262 
Q 5253 -34 5048 -161 
Q 4844 -288 4591 -288 
Q 4416 -288 4097 -256 
Q 4016 25 3944 238 
Q 4550 172 4644 172 
Q 4703 172 4812 456 
Q 4922 741 5023 1741 
Q 5125 2741 5159 3391 
L 4359 3391 
Q 4366 1738 3883 889 
Q 3400 41 2528 -384 
L 2156 25 
Q 2716 300 3009 634 
Q 2913 850 2719 1075 
Q 1478 731 763 475 
L 428 959 
Q 678 1172 1014 1786 
Q 1350 2400 1503 2906 
L 353 2906 
L 353 3372 
L 3144 3372 
L 3144 2906 
L 2041 2906 
Q 1500 1597 1125 1125 
L 1141 1113 
L 2444 1484 
Q 2397 1556 2125 1797 
L 2478 2047 
Q 3131 1475 3359 997 
Q 3528 1178 3697 1742 
Q 3866 2306 3866 2888 
L 3866 3391 
L 3194 3391 
L 3194 3834 
L 3866 3834 
L 3866 5319 
L 4353 5325 
L 4353 3834 
L 5678 3834 
z
M 2881 4219 
L 603 4219 
L 603 4659 
L 2881 4659 
L 2881 4219 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-645e" d="M 5056 3378 
L 1313 3378 
L 1313 5050 
L 5056 5050 
L 5056 3378 
z
M 4569 4403 
L 4569 4609 
L 1797 4609 
L 1797 4403 
L 4569 4403 
z
M 4569 3794 
L 4569 4031 
L 1797 4031 
L 1797 3794 
L 4569 3794 
z
M 5797 2816 
L 581 2816 
L 581 3231 
L 5797 3231 
L 5797 2816 
z
M 6059 -191 
L 341 -191 
L 341 275 
L 2950 275 
L 2950 459 
L 897 459 
L 897 878 
L 2950 878 
L 2950 1044 
L 1125 1044 
L 1125 2669 
L 5269 2669 
L 5269 1044 
L 3438 1044 
L 3438 878 
L 5509 878 
L 5509 459 
L 3438 459 
L 3438 275 
L 6059 275 
L 6059 -191 
z
M 4781 2053 
L 4781 2253 
L 3438 2253 
L 3438 2053 
L 4781 2053 
z
M 2950 2053 
L 2950 2253 
L 1613 2253 
L 1613 2053 
L 2950 2053 
z
M 4781 1459 
L 4781 1697 
L 3438 1697 
L 3438 1459 
L 4781 1459 
z
M 2950 1459 
L 2950 1697 
L 1613 1697 
L 1613 1459 
L 2950 1459 
z
" transform="scale(0.015625)"/>
     </defs>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-4987"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2e88" transform="translate(100 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2679" transform="translate(200 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-499a" transform="translate(300 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2537" transform="translate(400 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-645e" transform="translate(500 0)"/>
    </g>
   </g>
  </g>
  <g id="cn-monthly-increment-axes_2">
   <g id="cn-monthly-increment-patch_137">
    <path d="M 41.899609 357.012117 
L 594 357.012117 
L 594 231.396391 
L 41.899609 231.396391 
z
" style="fill: #fbfaf7"/>
   </g>
   <g id="cn-monthly-increment-patch_138">
    <path d="M 66.995082 292.302253 
L 69.873864 292.302253 
L 69.873864 297.966435 
L 66.995082 297.966435 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_139">
    <path d="M 70.87518 292.302253 
L 73.753962 292.302253 
L 73.753962 299.526735 
L 70.87518 299.526735 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_140">
    <path d="M 74.379784 292.302253 
L 77.258567 292.302253 
L 77.258567 283.189676 
L 74.379784 283.189676 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_141">
    <path d="M 78.259882 292.302253 
L 81.138665 292.302253 
L 81.138665 298.127502 
L 78.259882 298.127502 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_142">
    <path d="M 82.014816 292.302253 
L 84.893598 292.302253 
L 84.893598 266.483761 
L 82.014816 266.483761 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_143">
    <path d="M 85.894914 292.302253 
L 88.773696 292.302253 
L 88.773696 298.768538 
L 85.894914 298.768538 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_144">
    <path d="M 89.649847 292.302253 
L 92.52863 292.302253 
L 92.52863 335.44924 
L 89.649847 335.44924 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_145">
    <path d="M 93.529945 292.302253 
L 96.408728 292.302253 
L 96.408728 346.40319 
L 93.529945 346.40319 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_146">
    <path d="M 97.410043 292.302253 
L 100.288825 292.302253 
L 100.288825 237.106196 
L 97.410043 237.106196 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_147">
    <path d="M 101.164977 292.302253 
L 104.043759 292.302253 
L 104.043759 311.767452 
L 101.164977 311.767452 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_148">
    <path d="M 105.045075 292.302253 
L 107.923857 292.302253 
L 107.923857 261.176739 
L 105.045075 261.176739 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_149">
    <path d="M 108.800008 292.302253 
L 111.67879 292.302253 
L 111.67879 282.021452 
L 108.800008 282.021452 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_150">
    <path d="M 112.680106 292.302253 
L 115.558888 292.302253 
L 115.558888 328.049438 
L 112.680106 328.049438 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_151">
    <path d="M 116.560204 292.302253 
L 119.438986 292.302253 
L 119.438986 294.86356 
L 116.560204 294.86356 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_152">
    <path d="M 120.189973 292.302253 
L 123.068755 292.302253 
L 123.068755 351.302311 
L 120.189973 351.302311 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_153">
    <path d="M 124.070071 292.302253 
L 126.948853 292.302253 
L 126.948853 302.523054 
L 124.070071 302.523054 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_154">
    <path d="M 127.825005 292.302253 
L 130.703787 292.302253 
L 130.703787 271.668665 
L 127.825005 271.668665 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_155">
    <path d="M 131.705103 292.302253 
L 134.583885 292.302253 
L 134.583885 277.396593 
L 131.705103 277.396593 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_156">
    <path d="M 135.460036 292.302253 
L 138.338818 292.302253 
L 138.338818 287.540868 
L 135.460036 287.540868 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_157">
    <path d="M 139.340134 292.302253 
L 142.218916 292.302253 
L 142.218916 281.589133 
L 139.340134 281.589133 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_158">
    <path d="M 143.220232 292.302253 
L 146.099014 292.302253 
L 146.099014 317.191054 
L 143.220232 317.191054 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_159">
    <path d="M 146.975165 292.302253 
L 149.853948 292.302253 
L 149.853948 279.750348 
L 146.975165 279.750348 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_160">
    <path d="M 150.855263 292.302253 
L 153.734046 292.302253 
L 153.734046 306.125653 
L 150.855263 306.125653 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_161">
    <path d="M 154.610197 292.302253 
L 157.488979 292.302253 
L 157.488979 275.687679 
L 154.610197 275.687679 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_162">
    <path d="M 158.490295 292.302253 
L 161.369077 292.302253 
L 161.369077 307.86749 
L 158.490295 307.86749 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_163">
    <path d="M 162.370393 292.302253 
L 165.249175 292.302253 
L 165.249175 276.887338 
L 162.370393 276.887338 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_164">
    <path d="M 165.874997 292.302253 
L 168.75378 292.302253 
L 168.75378 256.252531 
L 165.874997 256.252531 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_165">
    <path d="M 169.755095 292.302253 
L 172.633878 292.302253 
L 172.633878 317.852483 
L 169.755095 317.852483 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_166">
    <path d="M 173.510029 292.302253 
L 176.388811 292.302253 
L 176.388811 274.720408 
L 173.510029 274.720408 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_167">
    <path d="M 177.390127 292.302253 
L 180.268909 292.302253 
L 180.268909 298.571941 
L 177.390127 298.571941 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_168">
    <path d="M 181.14506 292.302253 
L 184.023843 292.302253 
L 184.023843 299.937577 
L 181.14506 299.937577 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_169">
    <path d="M 185.025158 292.302253 
L 187.903941 292.302253 
L 187.903941 337.490706 
L 185.025158 337.490706 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_170">
    <path d="M 188.905256 292.302253 
L 191.784039 292.302253 
L 191.784039 296.602693 
L 188.905256 296.602693 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_171">
    <path d="M 192.66019 292.302253 
L 195.538972 292.302253 
L 195.538972 300.442077 
L 192.66019 300.442077 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_172">
    <path d="M 196.540288 292.302253 
L 199.41907 292.302253 
L 199.41907 272.214455 
L 196.540288 272.214455 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_173">
    <path d="M 200.295221 292.302253 
L 203.174004 292.302253 
L 203.174004 281.788671 
L 200.295221 281.788671 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_174">
    <path d="M 204.175319 292.302253 
L 207.054102 292.302253 
L 207.054102 298.570201 
L 204.175319 298.570201 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_175">
    <path d="M 208.055417 292.302253 
L 210.9342 292.302253 
L 210.9342 275.98651 
L 208.055417 275.98651 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_176">
    <path d="M 211.560022 292.302253 
L 214.438804 292.302253 
L 214.438804 250.784021 
L 211.560022 250.784021 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_177">
    <path d="M 215.44012 292.302253 
L 218.318902 292.302253 
L 218.318902 295.612797 
L 215.44012 295.612797 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_178">
    <path d="M 219.195053 292.302253 
L 222.073836 292.302253 
L 222.073836 288.088826 
L 219.195053 288.088826 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_179">
    <path d="M 223.075151 292.302253 
L 225.953934 292.302253 
L 225.953934 298.385654 
L 223.075151 298.385654 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_180">
    <path d="M 226.830085 292.302253 
L 229.708867 292.302253 
L 229.708867 283.626673 
L 226.830085 283.626673 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_181">
    <path d="M 230.710183 292.302253 
L 233.588965 292.302253 
L 233.588965 281.108165 
L 230.710183 281.108165 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_182">
    <path d="M 234.590281 292.302253 
L 237.469063 292.302253 
L 237.469063 293.371874 
L 234.590281 293.371874 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_183">
    <path d="M 238.345214 292.302253 
L 241.223997 292.302253 
L 241.223997 285.60462 
L 238.345214 285.60462 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_184">
    <path d="M 242.225312 292.302253 
L 245.104095 292.302253 
L 245.104095 299.432249 
L 242.225312 299.432249 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_185">
    <path d="M 245.980246 292.302253 
L 248.859028 292.302253 
L 248.859028 293.365906 
L 245.980246 293.365906 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_186">
    <path d="M 249.860344 292.302253 
L 252.739126 292.302253 
L 252.739126 309.519498 
L 249.860344 309.519498 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_187">
    <path d="M 253.740442 292.302253 
L 256.619224 292.302253 
L 256.619224 296.207288 
L 253.740442 296.207288 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_188">
    <path d="M 257.245046 292.302253 
L 260.123829 292.302253 
L 260.123829 320.666941 
L 257.245046 320.666941 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_189">
    <path d="M 261.125144 292.302253 
L 264.003927 292.302253 
L 264.003927 270.621583 
L 261.125144 270.621583 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_190">
    <path d="M 264.880078 292.302253 
L 267.75886 292.302253 
L 267.75886 300.240896 
L 264.880078 300.240896 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_191">
    <path d="M 268.760176 292.302253 
L 271.638958 292.302253 
L 271.638958 271.835628 
L 268.760176 271.835628 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_192">
    <path d="M 272.515109 292.302253 
L 275.393892 292.302253 
L 275.393892 279.422319 
L 272.515109 279.422319 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_193">
    <path d="M 276.395207 292.302253 
L 279.27399 292.302253 
L 279.27399 286.262717 
L 276.395207 286.262717 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_194">
    <path d="M 280.275305 292.302253 
L 283.154087 292.302253 
L 283.154087 255.776639 
L 280.275305 255.776639 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_195">
    <path d="M 284.030239 292.302253 
L 286.909021 292.302253 
L 286.909021 297.454671 
L 284.030239 297.454671 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_196">
    <path d="M 287.910337 292.302253 
L 290.789119 292.302253 
L 290.789119 303.890678 
L 287.910337 303.890678 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_197">
    <path d="M 291.66527 292.302253 
L 294.544052 292.302253 
L 294.544052 257.848582 
L 291.66527 257.848582 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_198">
    <path d="M 295.545368 292.302253 
L 298.42415 292.302253 
L 298.42415 276.961396 
L 295.545368 276.961396 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_199">
    <path d="M 299.425466 292.302253 
L 302.304248 292.302253 
L 302.304248 308.714486 
L 299.425466 308.714486 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_200">
    <path d="M 303.055235 292.302253 
L 305.934017 292.302253 
L 305.934017 326.565047 
L 303.055235 326.565047 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_201">
    <path d="M 306.935333 292.302253 
L 309.814115 292.302253 
L 309.814115 259.343352 
L 306.935333 259.343352 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_202">
    <path d="M 310.690267 292.302253 
L 313.569049 292.302253 
L 313.569049 289.038332 
L 310.690267 289.038332 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_203">
    <path d="M 314.570365 292.302253 
L 317.449147 292.302253 
L 317.449147 289.296042 
L 314.570365 289.296042 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_204">
    <path d="M 318.325298 292.302253 
L 321.20408 292.302253 
L 321.20408 315.515351 
L 318.325298 315.515351 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_205">
    <path d="M 0 0 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_206">
    <path d="M 326.085494 292.302253 
L 328.964276 292.302253 
L 328.964276 295.356485 
L 326.085494 295.356485 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_207">
    <path d="M 329.840427 292.302253 
L 332.71921 292.302253 
L 332.71921 277.031584 
L 329.840427 277.031584 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_208">
    <path d="M 333.720525 292.302253 
L 336.599308 292.302253 
L 336.599308 303.263273 
L 333.720525 303.263273 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_209">
    <path d="M 337.475459 292.302253 
L 340.354241 292.302253 
L 340.354241 251.988728 
L 337.475459 251.988728 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_210">
    <path d="M 341.355557 292.302253 
L 344.234339 292.302253 
L 344.234339 283.131755 
L 341.355557 283.131755 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_211">
    <path d="M 345.235655 292.302253 
L 348.114437 292.302253 
L 348.114437 316.072215 
L 345.235655 316.072215 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_212">
    <path d="M 0 0 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_213">
    <path d="M 352.620357 292.302253 
L 355.49914 292.302253 
L 355.49914 260.333833 
L 352.620357 260.333833 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_214">
    <path d="M 356.375291 292.302253 
L 359.254073 292.302253 
L 359.254073 251.885055 
L 356.375291 251.885055 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_215">
    <path d="M 360.255389 292.302253 
L 363.134171 292.302253 
L 363.134171 300.024512 
L 360.255389 300.024512 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_216">
    <path d="M 0 0 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_217">
    <path d="M 367.89042 292.302253 
L 370.769203 292.302253 
L 370.769203 262.598698 
L 367.89042 262.598698 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_218">
    <path d="M 0 0 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_219">
    <path d="M 375.525452 292.302253 
L 378.404234 292.302253 
L 378.404234 304.783051 
L 375.525452 304.783051 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_220">
    <path d="M 379.40555 292.302253 
L 382.284332 292.302253 
L 382.284332 247.188516 
L 379.40555 247.188516 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_221">
    <path d="M 383.160483 292.302253 
L 386.039266 292.302253 
L 386.039266 253.13584 
L 383.160483 253.13584 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_222">
    <path d="M 387.040581 292.302253 
L 389.919364 292.302253 
L 389.919364 274.702851 
L 387.040581 274.702851 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_223">
    <path d="M 390.920679 292.302253 
L 393.799462 292.302253 
L 393.799462 287.668285 
L 390.920679 287.668285 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_224">
    <path d="M 394.425284 292.302253 
L 397.304066 292.302253 
L 397.304066 290.832018 
L 394.425284 290.832018 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_225">
    <path d="M 398.305382 292.302253 
L 401.184164 292.302253 
L 401.184164 286.356476 
L 398.305382 286.356476 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_226">
    <path d="M 402.060315 292.302253 
L 404.939098 292.302253 
L 404.939098 291.384508 
L 402.060315 291.384508 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_227">
    <path d="M 405.940413 292.302253 
L 408.819196 292.302253 
L 408.819196 272.709059 
L 405.940413 272.709059 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_228">
    <path d="M 409.695347 292.302253 
L 412.574129 292.302253 
L 412.574129 297.362989 
L 409.695347 297.362989 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_229">
    <path d="M 413.575445 292.302253 
L 416.454227 292.302253 
L 416.454227 289.710146 
L 413.575445 289.710146 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_230">
    <path d="M 417.455543 292.302253 
L 420.334325 292.302253 
L 420.334325 283.751395 
L 417.455543 283.751395 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_231">
    <path d="M 421.210476 292.302253 
L 424.089259 292.302253 
L 424.089259 271.262785 
L 421.210476 271.262785 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_232">
    <path d="M 425.090574 292.302253 
L 427.969357 292.302253 
L 427.969357 297.049719 
L 425.090574 297.049719 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_233">
    <path d="M 428.845508 292.302253 
L 431.72429 292.302253 
L 431.72429 301.096733 
L 428.845508 301.096733 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_234">
    <path d="M 432.725606 292.302253 
L 435.604388 292.302253 
L 435.604388 305.275861 
L 432.725606 305.275861 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_235">
    <path d="M 436.605704 292.302253 
L 439.484486 292.302253 
L 439.484486 297.233735 
L 436.605704 297.233735 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_236">
    <path d="M 440.110308 292.302253 
L 442.989091 292.302253 
L 442.989091 284.066409 
L 440.110308 284.066409 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_237">
    <path d="M 443.990406 292.302253 
L 446.869189 292.302253 
L 446.869189 285.954396 
L 443.990406 285.954396 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_238">
    <path d="M 447.74534 292.302253 
L 450.624122 292.302253 
L 450.624122 291.605319 
L 447.74534 291.605319 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_239">
    <path d="M 0 0 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_240">
    <path d="M 455.380371 292.302253 
L 458.259154 292.302253 
L 458.259154 303.72087 
L 455.380371 303.72087 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_241">
    <path d="M 459.260469 292.302253 
L 462.139252 292.302253 
L 462.139252 280.679824 
L 459.260469 280.679824 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_242">
    <path d="M 463.140567 292.302253 
L 466.019349 292.302253 
L 466.019349 281.021231 
L 463.140567 281.021231 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_243">
    <path d="M 466.895501 292.302253 
L 469.774283 292.302253 
L 469.774283 284.360674 
L 466.895501 284.360674 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_244">
    <path d="M 470.775599 292.302253 
L 473.654381 292.302253 
L 473.654381 275.907957 
L 470.775599 275.907957 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_245">
    <path d="M 474.530532 292.302253 
L 477.409314 292.302253 
L 477.409314 276.679274 
L 474.530532 276.679274 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_246">
    <path d="M 478.41063 292.302253 
L 481.289412 292.302253 
L 481.289412 297.626008 
L 478.41063 297.626008 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_247">
    <path d="M 482.290728 292.302253 
L 485.16951 292.302253 
L 485.16951 293.307195 
L 482.290728 293.307195 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_248">
    <path d="M 485.920497 292.302253 
L 488.799279 292.302253 
L 488.799279 300.890691 
L 485.920497 300.890691 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_249">
    <path d="M 489.800595 292.302253 
L 492.679377 292.302253 
L 492.679377 281.36557 
L 489.800595 281.36557 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_250">
    <path d="M 493.555529 292.302253 
L 496.434311 292.302253 
L 496.434311 270.73731 
L 493.555529 270.73731 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_251">
    <path d="M 497.435627 292.302253 
L 500.314409 292.302253 
L 500.314409 291.700935 
L 497.435627 291.700935 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_252">
    <path d="M 501.19056 292.302253 
L 504.069342 292.302253 
L 504.069342 326.743086 
L 501.19056 326.743086 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_253">
    <path d="M 505.070658 292.302253 
L 507.94944 292.302253 
L 507.94944 277.152982 
L 505.070658 277.152982 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_254">
    <path d="M 508.950756 292.302253 
L 511.829538 292.302253 
L 511.829538 273.016769 
L 508.950756 273.016769 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_255">
    <path d="M 512.705689 292.302253 
L 515.584472 292.302253 
L 515.584472 273.524438 
L 512.705689 273.524438 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_256">
    <path d="M 516.585787 292.302253 
L 519.46457 292.302253 
L 519.46457 298.395964 
L 516.585787 298.395964 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_257">
    <path d="M 520.340721 292.302253 
L 523.219503 292.302253 
L 523.219503 279.942373 
L 520.340721 279.942373 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_258">
    <path d="M 524.220819 292.302253 
L 527.099601 292.302253 
L 527.099601 303.478598 
L 524.220819 303.478598 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_259">
    <path d="M 528.100917 292.302253 
L 530.979699 292.302253 
L 530.979699 302.064517 
L 528.100917 302.064517 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_260">
    <path d="M 531.605521 292.302253 
L 534.484304 292.302253 
L 534.484304 323.702305 
L 531.605521 323.702305 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_261">
    <path d="M 535.485619 292.302253 
L 538.364402 292.302253 
L 538.364402 285.686789 
L 535.485619 285.686789 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_262">
    <path d="M 539.240553 292.302253 
L 542.119335 292.302253 
L 542.119335 343.603888 
L 539.240553 343.603888 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_263">
    <path d="M 543.120651 292.302253 
L 545.999433 292.302253 
L 545.999433 327.195652 
L 543.120651 327.195652 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_264">
    <path d="M 546.875584 292.302253 
L 549.754367 292.302253 
L 549.754367 269.834064 
L 546.875584 269.834064 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_265">
    <path d="M 550.755682 292.302253 
L 553.634465 292.302253 
L 553.634465 265.700738 
L 550.755682 265.700738 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-patch_266">
    <path d="M 554.63578 292.302253 
L 557.514563 292.302253 
L 557.514563 338.151635 
L 554.63578 338.151635 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_267">
    <path d="M 558.390714 292.302253 
L 561.269496 292.302253 
L 561.269496 324.489886 
L 558.390714 324.489886 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_268">
    <path d="M 562.270812 292.302253 
L 565.149594 292.302253 
L 565.149594 301.827601 
L 562.270812 301.827601 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #b86358"/>
   </g>
   <g id="cn-monthly-increment-patch_269">
    <path d="M 566.025745 292.302253 
L 568.904528 292.302253 
L 568.904528 260.257408 
L 566.025745 260.257408 
z
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: #007f7b"/>
   </g>
   <g id="cn-monthly-increment-matplotlib.axis_3">
    <g id="cn-monthly-increment-xtick_7">
     <g id="cn-monthly-increment-line2d_29">
      <path d="M 114.119497 357.012117 
L 114.119497 231.396391 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_30">
      <g>
       <use xlink:href="#cn-monthly-increment-meee8b6f55d" x="114.119497" y="357.012117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_8">
      <!-- 2016 -->
      <g transform="translate(102.997622 371.292391) scale(0.1 -0.1)">
       <defs>
        <path id="cn-monthly-increment-ArialUnicodeMS-14" d="M 2400 0 
L 1838 0 
L 1838 3584 
Q 1416 3184 709 2906 
L 709 3450 
Q 1681 3916 2034 4603 
L 2400 4603 
L 2400 0 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-14" transform="translate(111.21875 0)"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-19" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-xtick_8">
     <g id="cn-monthly-increment-line2d_31">
      <path d="M 205.61471 357.012117 
L 205.61471 231.396391 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_32">
      <g>
       <use xlink:href="#cn-monthly-increment-meee8b6f55d" x="205.61471" y="357.012117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_9">
      <!-- 2018 -->
      <g transform="translate(194.492835 371.292391) scale(0.1 -0.1)">
       <defs>
        <path id="cn-monthly-increment-ArialUnicodeMS-1b" d="M 2425 2478 
Q 3284 2203 3284 1306 
Q 3284 716 2862 319 
Q 2441 -78 1778 -78 
Q 1109 -78 689 322 
Q 269 722 269 1325 
Q 269 1759 505 2084 
Q 741 2409 1141 2478 
L 1141 2491 
Q 453 2703 453 3419 
Q 453 3925 815 4264 
Q 1178 4603 1766 4603 
Q 2363 4603 2730 4253 
Q 3097 3903 3097 3406 
Q 3097 2731 2425 2491 
L 2425 2478 
z
M 1778 2700 
Q 2094 2700 2308 2901 
Q 2522 3103 2522 3406 
Q 2522 3716 2305 3928 
Q 2088 4141 1772 4141 
Q 1450 4141 1240 3931 
Q 1031 3722 1031 3438 
Q 1031 3097 1247 2898 
Q 1463 2700 1778 2700 
z
M 1778 384 
Q 2175 384 2440 640 
Q 2706 897 2706 1306 
Q 2706 1716 2432 1978 
Q 2159 2241 1766 2241 
Q 1356 2241 1100 1970 
Q 844 1700 844 1319 
Q 844 922 1108 653 
Q 1372 384 1778 384 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-14" transform="translate(111.21875 0)"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-1b" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-xtick_9">
     <g id="cn-monthly-increment-line2d_33">
      <path d="M 296.984759 357.012117 
L 296.984759 231.396391 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_34">
      <g>
       <use xlink:href="#cn-monthly-increment-meee8b6f55d" x="296.984759" y="357.012117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_10">
      <!-- 2020 -->
      <g transform="translate(285.862884 371.292391) scale(0.1 -0.1)">
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15" transform="translate(111.21875 0)"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-13" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-xtick_10">
     <g id="cn-monthly-increment-line2d_35">
      <path d="M 388.479972 357.012117 
L 388.479972 231.396391 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_36">
      <g>
       <use xlink:href="#cn-monthly-increment-meee8b6f55d" x="388.479972" y="357.012117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_11">
      <!-- 2022 -->
      <g transform="translate(377.358097 371.292391) scale(0.1 -0.1)">
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15" transform="translate(111.21875 0)"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-xtick_11">
     <g id="cn-monthly-increment-line2d_37">
      <path d="M 479.850021 357.012117 
L 479.850021 231.396391 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_38">
      <g>
       <use xlink:href="#cn-monthly-increment-meee8b6f55d" x="479.850021" y="357.012117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_12">
      <!-- 2024 -->
      <g transform="translate(468.728146 371.292391) scale(0.1 -0.1)">
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15" transform="translate(111.21875 0)"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-17" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-xtick_12">
     <g id="cn-monthly-increment-line2d_39">
      <path d="M 571.345234 357.012117 
L 571.345234 231.396391 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_40">
      <g>
       <use xlink:href="#cn-monthly-increment-meee8b6f55d" x="571.345234" y="357.012117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_13">
      <!-- 2026 -->
      <g transform="translate(560.223359 371.292391) scale(0.1 -0.1)">
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15" transform="translate(111.21875 0)"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-19" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
   </g>
   <g id="cn-monthly-increment-matplotlib.axis_4">
    <g id="cn-monthly-increment-ytick_6">
     <g id="cn-monthly-increment-line2d_41">
      <path d="M 41.899609 327.921206 
L 594 327.921206 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_42">
      <g>
       <use xlink:href="#cn-monthly-increment-m5da8443694" x="41.899609" y="327.921206" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_14">
      <!-- -1 -->
      <g transform="translate(26.008984 331.561342) scale(0.1 -0.1)">
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-10"/>
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-14" transform="translate(33.296875 0)"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-ytick_7">
     <g id="cn-monthly-increment-line2d_43">
      <path d="M 41.899609 292.302253 
L 594 292.302253 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_44">
      <g>
       <use xlink:href="#cn-monthly-increment-m5da8443694" x="41.899609" y="292.302253" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_15">
      <!-- 0 -->
      <g transform="translate(29.338672 295.94239) scale(0.1 -0.1)">
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-13"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-ytick_8">
     <g id="cn-monthly-increment-line2d_45">
      <path d="M 41.899609 256.6833 
L 594 256.6833 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="cn-monthly-increment-line2d_46">
      <g>
       <use xlink:href="#cn-monthly-increment-m5da8443694" x="41.899609" y="256.6833" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="cn-monthly-increment-text_16">
      <!-- 1 -->
      <g transform="translate(29.338672 260.323437) scale(0.1 -0.1)">
       <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-14"/>
      </g>
     </g>
    </g>
    <g id="cn-monthly-increment-text_17">
     <!-- 当月收益差：百分点 -->
     <g transform="translate(19.909375 339.204254) rotate(-90) scale(0.1 -0.1)">
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-31e2"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3997" transform="translate(100 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-37c5" transform="translate(200 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-4959" transform="translate(300 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-307d" transform="translate(400 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-19f6" transform="translate(500 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-490d" transform="translate(600 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2495" transform="translate(700 0)"/>
      <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-4348" transform="translate(800 0)"/>
     </g>
    </g>
   </g>
   <g id="cn-monthly-increment-line2d_47">
    <path d="M 41.899609 292.302253 
L 594 292.302253 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #777777; stroke-width: 0.7; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-line2d_48">
    <path d="M 323.644787 357.012117 
L 323.644787 231.396391 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #c59f70; stroke-opacity: 0.7; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-line2d_49">
    <path d="M 350.179651 357.012117 
L 350.179651 231.396391 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #c59f70; stroke-opacity: 0.7; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-line2d_50">
    <path d="M 365.449714 357.012117 
L 365.449714 231.396391 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #c59f70; stroke-opacity: 0.7; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-line2d_51">
    <path d="M 373.20991 357.012117 
L 373.20991 231.396391 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #c59f70; stroke-opacity: 0.7; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-line2d_52">
    <path d="M 453.064829 357.012117 
L 453.064829 231.396391 
" clip-path="url(#cn-monthly-increment-pab1dc66e22)" style="fill: none; stroke: #c59f70; stroke-opacity: 0.7; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-patch_270">
    <path d="M 41.899609 357.012117 
L 41.899609 231.396391 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-patch_271">
    <path d="M 41.899609 357.012117 
L 594 357.012117 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="cn-monthly-increment-text_18">
    <!-- 相对两套原方法各用一半资金 -->
    <g transform="translate(41.899609 225.396391) scale(0.12 -0.12)">
     <defs>
      <path id="cn-monthly-increment-ArialUnicodeMS-20b3" d="M 5831 4525 
L 4091 4525 
L 4091 3706 
L 5472 3706 
L 5472 122 
Q 5472 -88 5315 -213 
Q 5159 -338 4866 -338 
Q 4722 -338 4459 -306 
L 4294 159 
Q 4644 106 4844 106 
Q 5013 106 5013 238 
L 5013 3263 
L 4063 3263 
L 4019 2747 
Q 4647 2319 4953 1797 
L 4569 1447 
Q 4322 1950 3944 2272 
Q 3663 1159 2975 494 
L 2572 813 
Q 3581 1788 3616 3263 
L 2713 3263 
L 2650 2766 
Q 3050 2519 3347 2119 
L 3009 1772 
Q 2784 2128 2572 2266 
Q 2313 1238 1663 666 
L 1300 984 
Q 2144 1728 2209 3263 
L 1247 3263 
L 1247 -391 
L 763 -391 
L 763 3706 
L 2216 3706 
L 2216 4525 
L 397 4525 
L 397 4991 
L 5831 4991 
L 5831 4525 
z
M 3628 3706 
L 3628 4525 
L 2700 4525 
L 2700 3706 
L 3628 3706 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-2be6" d="M 6181 3138 
L 5888 2675 
Q 5219 2872 4647 3250 
L 2228 3250 
L 2228 2988 
L 4819 2988 
L 4819 2522 
L 2228 2522 
L 2228 2247 
L 4819 2247 
L 4819 1778 
L 2228 1778 
L 2228 1472 
L 5831 1472 
L 5831 1006 
L 2963 1006 
Q 2638 488 2375 263 
Q 3453 281 4538 359 
Q 4341 491 3841 738 
L 4288 991 
Q 5297 522 5716 -147 
L 5294 -416 
Q 5034 -56 4991 -25 
L 2994 -141 
Q 1750 -206 1191 -263 
L 997 238 
L 1784 263 
Q 2141 616 2375 1006 
L 622 1006 
L 622 1472 
L 1741 1472 
L 1741 3181 
Q 1269 2869 622 2619 
L 275 3066 
Q 1519 3491 2228 4256 
L 622 4256 
L 622 4722 
L 2619 4722 
Q 2822 5044 2900 5403 
L 3378 5197 
Q 3253 4878 3181 4722 
L 5856 4722 
L 5856 4256 
L 4256 4256 
Q 4953 3447 6181 3138 
z
M 4097 3719 
Q 3888 3947 3725 4256 
L 2881 4256 
Q 2650 3947 2413 3719 
L 4097 3719 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-262e" d="M 5888 4569 
L 4063 4569 
Q 4006 4288 3909 4063 
L 5269 4078 
L 5269 1797 
L 3969 1797 
L 3969 38 
Q 3944 -213 3717 -316 
Q 3491 -419 3309 -409 
L 2853 -391 
L 2700 84 
Q 2906 56 3103 56 
Q 3481 56 3481 219 
L 3481 1797 
L 2088 1797 
L 2088 4063 
L 3366 4078 
Q 3463 4225 3572 4569 
L 1600 4569 
L 1600 2328 
Q 1600 1400 1454 812 
Q 1309 225 831 -391 
L 378 -116 
Q 753 359 933 850 
Q 1113 1341 1113 2209 
L 1113 5038 
L 5888 5038 
L 5888 4569 
z
M 4781 3175 
L 4781 3609 
L 2572 3609 
L 2572 3175 
L 4781 3175 
z
M 4781 2266 
L 4781 2706 
L 2572 2706 
L 2572 2266 
L 4781 2266 
z
M 5966 403 
L 5613 56 
Q 5028 850 4238 1306 
L 4569 1613 
Q 5275 1303 5966 403 
z
M 3034 1331 
Q 2700 581 1734 0 
L 1403 341 
Q 2328 903 2669 1594 
L 3034 1331 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-3848" d="M 5991 3803 
L 2772 3803 
Q 2772 3413 2731 2747 
L 5141 2747 
Q 5119 1750 4973 931 
Q 4828 113 4617 -62 
Q 4406 -238 4166 -238 
Q 3847 -238 3003 -25 
L 2906 544 
Q 3750 238 4056 238 
Q 4178 238 4267 336 
Q 4356 434 4456 970 
Q 4556 1506 4575 2278 
L 2694 2278 
Q 2472 1097 1965 481 
Q 1459 -134 666 -428 
L 331 31 
Q 1184 341 1559 805 
Q 1934 1269 2090 1803 
Q 2247 2338 2247 3803 
L 647 3803 
L 647 4269 
L 2956 4269 
L 2956 5259 
L 3444 5259 
L 3444 4269 
L 5991 4269 
L 5991 3803 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-3f64" d="M 6047 -103 
L 5600 -366 
Q 5428 69 5288 244 
L 2266 -31 
L 2041 475 
L 2772 506 
Q 3134 1244 3456 2188 
L 2041 2188 
L 2041 2656 
L 3719 2656 
L 3719 3738 
L 2394 3738 
L 2394 4206 
L 3719 4206 
L 3719 5253 
L 4206 5253 
L 4206 4206 
L 5538 4206 
L 5538 3738 
L 4206 3738 
L 4206 2656 
L 5894 2656 
L 5894 2188 
L 3975 2188 
Q 3681 1241 3291 531 
L 5013 653 
Q 4669 1025 4325 1228 
L 4738 1472 
Q 5541 953 6047 -103 
z
M 2284 4166 
L 1941 3822 
Q 1597 4384 838 4703 
L 1141 5031 
Q 1869 4756 2284 4166 
z
M 1888 2772 
L 1550 2425 
Q 1203 3003 409 3291 
L 738 3609 
Q 1547 3316 1888 2772 
z
M 2169 1753 
Q 1872 553 978 -378 
L 544 -84 
Q 1469 878 1753 1925 
L 2169 1753 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-2693" d="M 6088 2247 
L 5797 1772 
Q 4028 2241 3238 2753 
Q 2069 2156 666 1791 
L 366 2222 
Q 1991 2641 2797 3059 
Q 2259 3491 1953 3963 
Q 1500 3394 1019 3072 
L 594 3397 
Q 1075 3650 1547 4219 
Q 2019 4788 2272 5350 
L 2753 5222 
Q 2666 4966 2491 4728 
L 4916 4728 
L 4916 4313 
Q 4403 3541 3700 3047 
Q 4050 2813 4815 2561 
Q 5581 2309 6088 2247 
z
M 4288 4263 
L 2344 4263 
Q 2656 3803 3244 3309 
Q 3941 3797 4288 4263 
z
M 4788 -403 
L 4281 -403 
L 4281 -31 
L 2181 -31 
L 2181 -416 
L 1678 -416 
L 1678 2009 
L 4788 2009 
L 4788 -403 
z
M 4281 434 
L 4281 1544 
L 2181 1544 
L 2181 434 
L 4281 434 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-47b7" d="M 5472 159 
Q 5472 -66 5340 -219 
Q 5209 -372 5013 -372 
L 4347 -372 
L 4191 128 
L 4722 113 
Q 4966 113 4966 256 
L 4966 1722 
L 3572 1722 
L 3572 13 
L 3084 13 
L 3084 1722 
L 1678 1722 
Q 1584 466 744 -469 
L 331 -159 
Q 794 394 1001 936 
Q 1209 1478 1209 2194 
L 1209 5044 
L 5472 5044 
L 5472 159 
z
M 4966 3641 
L 4966 4575 
L 3572 4575 
L 3572 3641 
L 4966 3641 
z
M 3084 3641 
L 3084 4575 
L 1697 4575 
L 1697 3641 
L 3084 3641 
z
M 4966 2188 
L 4966 3175 
L 3572 3175 
L 3572 2188 
L 4966 2188 
z
M 3084 2188 
L 3084 3175 
L 1697 3175 
L 1697 2188 
L 3084 2188 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-208f" d="M 5734 2278 
L 775 2278 
L 775 2809 
L 5734 2809 
L 5734 2278 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-25d9" d="M 5819 1288 
L 3406 1288 
L 3406 -428 
L 2913 -428 
L 2913 1281 
L 494 1281 
L 488 1753 
L 2913 1753 
L 2913 2491 
L 903 2491 
L 903 2950 
L 2913 2950 
L 2913 5275 
L 3406 5275 
L 3406 2950 
L 5403 2950 
L 5403 2491 
L 3413 2491 
L 3406 1753 
L 5819 1753 
L 5819 1288 
z
M 5478 4775 
Q 5206 3997 4300 3238 
L 3872 3578 
Q 4756 4178 5050 5056 
L 5478 4775 
z
M 2309 3456 
L 1888 3156 
Q 1463 4272 738 4684 
L 1166 4984 
Q 1819 4591 2309 3456 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-5fd3" d="M 5522 4863 
Q 5541 4597 5477 4328 
Q 5413 4059 5131 3622 
L 4697 3859 
Q 4913 4106 5013 4397 
L 3144 4397 
Q 2878 3913 2203 3444 
L 1875 3822 
Q 2672 4297 3003 5306 
L 3431 5153 
Q 3403 5059 3322 4863 
L 5522 4863 
z
M 1766 4550 
L 1409 4172 
Q 1103 4628 594 4941 
L 891 5234 
Q 1459 4978 1766 4550 
z
M 6009 2778 
L 5678 2369 
Q 4472 2688 3788 3481 
Q 3591 3172 3142 2912 
Q 2694 2653 2222 2578 
L 2222 2572 
L 4813 2572 
L 4813 575 
L 4325 575 
L 4325 2106 
L 2119 2106 
L 2119 575 
L 1631 575 
L 1631 2572 
L 1913 2572 
L 1716 2847 
Q 2591 3081 3020 3382 
Q 3450 3684 3641 4250 
L 4091 4147 
L 4006 3897 
Q 4269 3525 4686 3267 
Q 5103 3009 6009 2778 
z
M 1806 3688 
Q 1628 3134 831 2369 
L 453 2713 
Q 1106 3253 1453 3922 
L 1806 3688 
z
M 3450 1906 
Q 3453 572 2761 120 
Q 2069 -331 819 -384 
L 594 84 
Q 1419 134 1742 186 
Q 2066 238 2409 461 
Q 2753 684 2848 979 
Q 2944 1275 2988 1906 
L 3450 1906 
z
M 5503 0 
L 5259 -447 
Q 4506 47 3272 306 
L 3494 722 
Q 4728 478 5503 0 
z
" transform="scale(0.015625)"/>
      <path id="cn-monthly-increment-ArialUnicodeMS-6460" d="M 6144 3163 
L 5753 2766 
Q 5238 2934 4647 3328 
L 4647 3072 
L 3488 3072 
L 3488 2328 
L 5228 2328 
L 5228 1869 
L 3488 1869 
L 3488 325 
L 5778 325 
L 5778 -134 
L 709 -134 
L 709 325 
L 3003 325 
L 3003 1869 
L 1234 1869 
L 1234 2328 
L 3003 2328 
L 3003 3072 
L 1838 3072 
L 1838 3341 
Q 1266 2969 672 2700 
L 347 3103 
Q 2378 4019 3225 5478 
L 3622 5209 
L 3531 5044 
Q 4700 3588 6144 3163 
z
M 4378 3525 
Q 3634 4109 3244 4647 
Q 2638 3903 2113 3547 
L 2113 3525 
L 4378 3525 
z
M 5025 1522 
Q 4675 769 4141 359 
L 3706 659 
Q 4281 1072 4634 1806 
L 5025 1522 
z
M 2644 628 
L 2175 428 
Q 1897 1125 1441 1544 
L 1875 1747 
Q 2356 1334 2644 628 
z
" transform="scale(0.015625)"/>
     </defs>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-4987"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2e88" transform="translate(100 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-20b3" transform="translate(200 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2be6" transform="translate(300 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-262e" transform="translate(400 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3848" transform="translate(500 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3f64" transform="translate(600 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2693" transform="translate(700 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-47b7" transform="translate(800 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-208f" transform="translate(900 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-25d9" transform="translate(1000 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-5fd3" transform="translate(1100 0)"/>
     <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-6460" transform="translate(1200 0)"/>
    </g>
   </g>
  </g>
  <g id="cn-monthly-increment-text_19">
   <!-- A 股：新三信息选股每月多赚或少赚多少 -->
   <g transform="translate(48.384 21.087938) scale(0.15 -0.15)">
    <defs>
     <path id="cn-monthly-increment-ArialUnicodeMS-24" d="M 4275 0 
L 3591 0 
L 3053 1394 
L 1141 1394 
L 634 0 
L -6 0 
L 1753 4581 
L 2406 4581 
L 4275 0 
z
M 2869 1875 
Q 2306 3363 2234 3564 
Q 2163 3766 2075 4103 
L 2059 4103 
Q 1972 3641 1825 3247 
L 1313 1875 
L 2869 1875 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-3" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-5330" d="M 6041 3725 
Q 5884 2956 5484 2956 
L 5038 2956 
Q 4569 2956 4569 3431 
L 4569 4575 
L 3681 4575 
Q 3672 3913 3630 3656 
Q 3588 3400 3377 3129 
Q 3166 2859 2944 2719 
L 2578 3078 
Q 3188 3506 3188 4019 
L 3188 5044 
L 5050 5044 
L 5050 3559 
Q 5050 3425 5178 3425 
L 5375 3425 
Q 5556 3425 5588 3969 
L 6041 3725 
z
M 2528 206 
Q 2528 -22 2406 -151 
Q 2284 -281 2075 -281 
L 1606 -281 
L 1447 213 
Q 1763 159 1850 159 
Q 2041 159 2041 294 
L 2041 1947 
L 1275 1947 
Q 1284 366 744 -384 
L 325 -56 
Q 794 578 794 1925 
L 794 5031 
L 2528 5031 
L 2528 206 
z
M 2041 3725 
L 2041 4550 
L 1281 4550 
L 1281 3725 
L 2041 3725 
z
M 2041 2413 
L 2041 3256 
L 1281 3256 
L 1281 2413 
L 2041 2413 
z
M 6022 6 
L 5703 -416 
Q 4931 -222 4244 453 
Q 3625 -78 2847 -391 
L 2553 38 
Q 3375 328 3909 825 
Q 3500 1369 3256 2272 
L 2981 2272 
L 2981 2741 
L 5350 2741 
Q 5150 1569 4563 813 
Q 5172 216 6022 6 
z
M 4763 2272 
L 3738 2272 
Q 4003 1503 4238 1153 
Q 4569 1625 4763 2272 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-383f" d="M 6041 2938 
L 5300 2938 
L 5300 -397 
L 4813 -397 
L 4813 2938 
L 4109 2938 
L 4109 2216 
Q 4109 700 3334 -359 
L 2906 -72 
Q 3622 853 3622 2456 
L 3622 4709 
Q 4644 4825 5544 5313 
L 5850 4916 
Q 5141 4503 4109 4319 
L 4109 3406 
L 6041 3406 
L 6041 2938 
z
M 3353 4184 
L 525 4184 
L 525 4653 
L 1716 4653 
L 1716 5281 
L 2222 5281 
L 2222 4653 
L 3353 4653 
L 3353 4184 
z
M 3406 2719 
L 2203 2719 
L 2203 2144 
L 3250 2144 
L 3250 1678 
L 2203 1678 
L 2203 1428 
L 2456 1619 
Q 2981 1281 3309 744 
L 2950 416 
Q 2672 931 2203 1281 
L 2203 -397 
L 1716 -397 
L 1716 1253 
Q 1316 625 703 178 
L 347 550 
Q 1003 959 1409 1678 
L 628 1678 
L 628 2144 
L 1716 2144 
L 1716 2719 
L 453 2719 
L 453 3188 
L 1325 3188 
Q 1147 3659 884 3975 
L 1306 4147 
Q 1631 3813 1806 3188 
L 2228 3188 
Q 2422 3559 2584 4147 
L 3047 3969 
Q 2906 3544 2719 3188 
L 3406 3188 
L 3406 2719 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-2098" d="M 5459 4056 
L 978 4056 
L 978 4563 
L 5459 4563 
L 5459 4056 
z
M 5088 2216 
L 1344 2216 
L 1344 2700 
L 5088 2700 
L 5088 2216 
z
M 5831 206 
L 634 206 
L 634 691 
L 5831 691 
L 5831 206 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-2270" d="M 2113 5100 
Q 1991 4697 1822 4250 
L 1650 3834 
L 1650 -434 
L 1166 -434 
L 1166 2969 
Q 969 2606 609 2181 
L 206 2503 
Q 1144 3613 1656 5281 
L 2113 5100 
z
M 5594 4728 
L 2363 4728 
L 2363 5197 
L 5594 5197 
L 5594 4728 
z
M 6022 3872 
L 2003 3872 
L 2003 4341 
L 6022 4341 
L 6022 3872 
z
M 5588 2938 
L 2356 2938 
L 2356 3406 
L 5588 3406 
L 5588 2938 
z
M 5588 2022 
L 2356 2022 
L 2356 2491 
L 5588 2491 
L 5588 2022 
z
M 5509 -434 
L 5044 -434 
L 5044 -56 
L 2894 -56 
L 2894 -434 
L 2425 -434 
L 2425 1528 
L 5509 1528 
L 5509 -434 
z
M 5044 359 
L 5044 1113 
L 2894 1113 
L 2894 359 
L 5044 359 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-32fe" d="M 4959 1759 
L 1338 1759 
L 1338 4756 
L 2753 4756 
Q 3038 5041 3219 5394 
L 3653 5159 
Q 3509 4919 3347 4756 
L 4959 4756 
L 4959 1759 
z
M 4475 3938 
L 4475 4288 
L 1825 4288 
L 1825 3938 
L 4475 3938 
z
M 4475 3084 
L 4475 3469 
L 1825 3469 
L 1825 3084 
L 4475 3084 
z
M 4475 2228 
L 4475 2644 
L 1825 2644 
L 1825 2228 
L 4475 2228 
z
M 3916 928 
L 3591 594 
Q 3144 1119 2497 1350 
L 2809 1697 
Q 3447 1484 3916 928 
z
M 4703 844 
Q 4519 194 4395 17 
Q 4272 -159 4025 -159 
L 2456 -159 
Q 1925 -159 1925 269 
L 1925 1409 
L 2413 1409 
L 2413 500 
Q 2413 306 2566 306 
L 3928 306 
Q 4038 306 4097 475 
L 4250 903 
L 4703 844 
z
M 6075 353 
L 5663 72 
Q 5256 788 4506 1081 
L 4884 1375 
Q 5578 1100 6075 353 
z
M 1766 1088 
Q 1378 425 616 0 
L 275 359 
Q 1034 734 1403 1350 
L 1766 1088 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-6298" d="M 6028 366 
L 5831 -153 
L 2822 -153 
Q 1966 -59 1403 428 
L 544 -275 
L 178 97 
Q 622 359 1241 897 
L 1241 2656 
L 403 2656 
L 403 3122 
L 1728 3122 
L 1728 769 
Q 1872 588 2259 422 
L 2272 434 
L 2081 744 
Q 2669 1016 2937 1397 
Q 3206 1778 3231 2516 
L 2216 2516 
L 2216 2981 
L 2375 2981 
L 2375 3003 
L 2081 3200 
Q 2638 3778 2766 5081 
L 3200 4947 
Q 3181 4578 3122 4306 
L 3725 4306 
L 3725 5166 
L 4213 5166 
L 4213 4306 
L 5234 4306 
L 5234 3841 
L 4213 3841 
L 4213 2981 
L 5716 2981 
L 5716 2516 
L 4641 2516 
L 4641 1113 
Q 4650 1084 4698 1057 
Q 4747 1031 4756 1031 
L 5281 1031 
Q 5372 1031 5388 1131 
L 5459 1600 
L 5894 1409 
Q 5759 563 5441 563 
L 4556 563 
Q 4428 563 4290 692 
Q 4153 822 4153 941 
L 4153 2516 
L 3706 2516 
Q 3706 1772 3397 1206 
Q 3088 641 2522 391 
Q 2719 313 3084 313 
L 5350 313 
Q 5769 313 6028 366 
z
M 3725 2981 
L 3725 3841 
L 3009 3841 
Q 2844 3297 2559 2981 
L 3725 2981 
z
M 1959 4122 
Q 1694 3903 1544 3816 
Q 1341 4378 722 4884 
L 1119 5153 
Q 1619 4750 1959 4122 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-3e5e" d="M 5838 4372 
L 1906 4372 
Q 1556 3769 825 3047 
L 428 3347 
Q 1447 4247 1838 5394 
L 2303 5241 
Q 2272 5134 2119 4838 
L 5838 4838 
L 5838 4372 
z
M 6009 1941 
L 5228 1941 
L 5100 884 
L 5697 884 
L 5697 416 
L 5044 416 
Q 4956 -403 4203 -403 
Q 3819 -403 3309 -331 
L 3138 159 
Q 3741 44 4072 44 
Q 4506 44 4506 416 
L 1613 416 
L 1544 116 
L 1038 213 
Q 1172 644 1363 1941 
L 409 1941 
L 409 2413 
L 1434 2413 
Q 1497 2772 1600 3866 
L 5394 3866 
L 5281 2413 
L 6009 2413 
L 6009 1941 
z
M 4850 3397 
L 2053 3397 
Q 1984 2681 1941 2413 
L 4775 2413 
Q 4850 3094 4850 3397 
z
M 4166 2784 
L 3822 2431 
Q 3269 2881 2394 3016 
L 2725 3366 
Q 3719 3213 4166 2784 
z
M 4716 1941 
L 2675 1941 
Q 3525 1750 4122 1234 
L 3781 903 
Q 3309 1316 2278 1594 
L 2547 1941 
L 1875 1941 
L 1691 884 
L 4594 884 
Q 4656 1278 4716 1941 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-2ba9" d="M 5831 2253 
Q 5831 2169 5545 1786 
Q 5259 1403 4934 1120 
Q 4609 838 4125 556 
Q 3641 275 2842 20 
Q 2044 -234 891 -434 
L 569 6 
Q 2425 319 3438 763 
Q 3250 1059 2731 1403 
L 3194 1663 
Q 3663 1334 3853 966 
Q 4875 1516 5241 2194 
L 3603 2194 
Q 2994 1644 1581 1044 
L 1209 1453 
Q 3113 2131 3938 3244 
Q 2553 2428 884 2094 
L 575 2522 
Q 1969 2838 2572 3097 
Q 2394 3341 1856 3634 
L 2303 3922 
Q 2700 3694 3022 3291 
Q 3731 3653 4294 4197 
L 2534 4197 
Q 1941 3794 1131 3488 
L 709 3884 
Q 2303 4356 3181 5434 
L 3628 5197 
Q 3503 5025 3163 4684 
L 4966 4684 
L 4966 4256 
Q 4559 3725 4063 3347 
L 4441 3144 
Q 4294 2894 4103 2681 
L 5831 2681 
L 5831 2253 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-5fe9" d="M 6088 213 
L 5753 -134 
Q 4816 569 4716 1728 
L 4703 1728 
L 4703 -416 
L 4219 -416 
L 4219 1728 
L 3859 1728 
L 3859 -416 
L 3372 -416 
L 3372 1728 
L 3359 1728 
Q 3222 656 2272 -122 
L 2119 31 
L 1813 -63 
Q 1847 500 1581 903 
L 1972 1088 
Q 2172 816 2216 488 
Q 2756 894 2981 1728 
L 2644 1728 
L 2644 2194 
L 3372 2194 
L 3372 2597 
L 2444 2597 
L 2444 3066 
L 3372 3066 
L 3372 3419 
L 2644 3419 
L 2644 3884 
L 3372 3884 
L 3372 4269 
L 2463 4269 
L 2463 4738 
L 3284 4738 
Q 3119 4981 2791 5184 
L 3263 5434 
Q 3678 5075 3822 4738 
L 4353 4738 
Q 4700 5044 4863 5416 
L 5331 5222 
Q 5184 4934 4984 4738 
L 5919 4738 
L 5919 4269 
L 4703 4269 
L 4703 3884 
L 5563 3884 
L 5563 3066 
L 6003 3066 
L 6003 2597 
L 5563 2597 
L 5563 1728 
L 5088 1728 
Q 5225 922 6088 213 
z
M 4219 3884 
L 4219 4269 
L 3859 4269 
L 3859 3884 
L 4219 3884 
z
M 5075 3066 
L 5075 3419 
L 4703 3419 
L 4703 3066 
L 5075 3066 
z
M 4219 3066 
L 4219 3419 
L 3859 3419 
L 3859 3066 
L 4219 3066 
z
M 5075 2194 
L 5075 2597 
L 4703 2597 
L 4703 2194 
L 5075 2194 
z
M 4219 2194 
L 4219 2597 
L 3859 2597 
L 3859 2194 
L 4219 2194 
z
M 2272 1375 
L 1900 1375 
L 1900 4525 
L 997 4525 
L 997 1403 
L 628 1403 
L 628 4991 
L 2272 4991 
L 2272 1375 
z
M 1697 2322 
Q 1697 1078 1372 484 
Q 1047 -109 575 -416 
L 263 -50 
Q 691 219 962 733 
Q 1234 1247 1234 2338 
L 1234 4178 
L 1697 4178 
L 1697 2322 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-34a5" d="M 6119 922 
Q 5831 -372 5394 -372 
Q 5150 -372 4840 -44 
Q 4531 284 4325 641 
Q 3850 153 3231 -341 
L 2772 -13 
Q 3619 556 4063 1131 
Q 3656 2034 3531 3725 
L 447 3725 
L 447 4184 
L 3481 4184 
L 3463 5363 
L 3969 5363 
Q 3969 4575 4000 4184 
L 5031 4184 
Q 4716 4597 4103 4788 
L 4447 5141 
Q 4994 5034 5569 4384 
L 5300 4178 
L 5797 4184 
L 5797 3725 
L 4038 3725 
Q 4125 2434 4403 1638 
Q 4891 2409 5063 3322 
L 5544 3163 
Q 5266 1919 4666 1088 
Q 4884 684 5081 475 
Q 5278 266 5347 266 
Q 5481 266 5650 1300 
L 6119 922 
z
M 3213 1338 
L 1038 1338 
L 1038 3175 
L 3213 3175 
L 3213 1338 
z
M 2725 1797 
L 2725 2694 
L 1522 2694 
L 1522 1797 
L 2725 1797 
z
M 3572 697 
L 806 91 
L 506 525 
Q 1769 759 3547 1172 
L 3572 697 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-2ea0" d="M 3541 2009 
Q 3541 1816 3430 1647 
Q 3319 1478 3156 1463 
L 2253 1388 
Q 2206 1466 2132 1641 
Q 2059 1816 2009 1906 
Q 2403 1891 2625 1891 
Q 2881 1891 2951 1930 
Q 3022 1969 3022 2075 
L 3022 5234 
L 3541 5234 
L 3541 2009 
z
M 6041 2631 
L 5613 2356 
Q 4966 3475 4122 3994 
L 4531 4313 
Q 5444 3672 6041 2631 
z
M 2356 4050 
Q 1841 2894 959 2113 
L 556 2444 
Q 1441 3197 1900 4238 
L 2356 4050 
z
M 5313 2322 
Q 4675 1356 3973 828 
Q 3272 300 2601 75 
Q 1931 -150 672 -428 
L 331 31 
Q 2184 291 3203 897 
Q 4222 1503 4903 2606 
L 5313 2322 
z
" transform="scale(0.015625)"/>
    </defs>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-24"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3" transform="translate(66.703125 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-5330" transform="translate(94.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-19f6" transform="translate(194.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-383f" transform="translate(294.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2098" transform="translate(394.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2270" transform="translate(494.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-32fe" transform="translate(594.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-6298" transform="translate(694.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-5330" transform="translate(794.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3e5e" transform="translate(894.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3997" transform="translate(994.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2ba9" transform="translate(1094.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-5fe9" transform="translate(1194.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-34a5" transform="translate(1294.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2ea0" transform="translate(1394.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-5fe9" transform="translate(1494.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2ba9" transform="translate(1594.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2ea0" transform="translate(1694.484375 0)"/>
   </g>
  </g>
  <g id="cn-monthly-increment-text_20">
   <!-- 2015—2025 年，127 个共同报价完整月份；金线为缺价月份。 -->
   <g style="fill: #555555" transform="translate(48.384 399.382341) scale(0.09 -0.09)">
    <defs>
     <path id="cn-monthly-increment-ArialUnicodeMS-18" d="M 1013 2753 
Q 1431 3041 1881 3041 
Q 2453 3041 2878 2636 
Q 3303 2231 3303 1556 
Q 3303 875 2872 398 
Q 2441 -78 1741 -78 
Q 1169 -78 750 245 
Q 331 569 269 1203 
L 856 1247 
Q 928 813 1162 598 
Q 1397 384 1741 384 
Q 2169 384 2434 707 
Q 2700 1031 2700 1503 
Q 2700 1984 2428 2262 
Q 2156 2541 1728 2541 
Q 1188 2541 897 2100 
L 366 2163 
L 813 4519 
L 3084 4519 
L 3084 3975 
L 1259 3975 
L 1013 2753 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-ca7" d="M 6438 1428 
L -38 1428 
L -38 1888 
L 6438 1888 
L 6438 1428 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-3103" d="M 5869 1409 
L 3659 1409 
L 3659 -434 
L 3156 -434 
L 3156 1409 
L 659 1409 
L 659 1875 
L 1459 1875 
L 1459 3384 
L 3156 3384 
L 3156 4219 
L 1838 4219 
Q 1425 3363 953 2931 
L 550 3256 
Q 1381 3994 1734 5381 
L 2144 5184 
Q 2122 4997 2022 4684 
L 5606 4684 
L 5606 4219 
L 3659 4219 
L 3659 3384 
L 5294 3384 
L 5294 2919 
L 3659 2919 
L 3659 1875 
L 5869 1875 
L 5869 1409 
z
M 3156 1875 
L 3156 2919 
L 1947 2919 
L 1947 1875 
L 3156 1875 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-19e8" d="M 3541 0 
Q 3541 -397 3389 -606 
Q 3238 -816 3016 -903 
L 2863 -666 
Q 3213 -516 3216 0 
L 2900 0 
L 2900 641 
L 3541 641 
L 3541 0 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-1a" d="M 3272 4084 
Q 2597 3344 2103 2253 
Q 1609 1163 1522 0 
L 947 0 
Q 969 934 1408 2051 
Q 1847 3169 2547 3975 
L 306 3975 
L 306 4519 
L 3272 4519 
L 3272 4084 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-20b9" d="M 6113 2503 
L 5728 2163 
Q 3956 3153 3200 4469 
Q 2788 3750 2070 3109 
Q 1353 2469 609 2156 
L 191 2491 
Q 2191 3438 3116 5325 
L 3547 5125 
L 3463 4947 
Q 4066 3694 6113 2503 
z
M 3406 -447 
L 2919 -447 
L 2919 3531 
L 3406 3531 
L 3406 -447 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-2400" d="M 5813 2125 
L 5797 1638 
L 581 1638 
L 581 2125 
L 1888 2125 
L 1875 3591 
L 953 3591 
L 953 4078 
L 1900 4078 
L 1900 5306 
L 2388 5306 
L 2388 4078 
L 3988 4078 
L 3988 5306 
L 4494 5306 
L 4494 4078 
L 5422 4078 
L 5422 3591 
L 4494 3591 
L 4494 2125 
L 5813 2125 
z
M 3988 2125 
L 3988 3591 
L 2388 3591 
L 2388 2125 
L 3988 2125 
z
M 5919 -109 
L 5550 -409 
Q 4909 409 3647 1153 
L 3994 1509 
Q 5288 731 5919 -109 
z
M 2778 1191 
Q 1847 119 756 -447 
L 481 -38 
Q 1556 497 2363 1509 
L 2778 1191 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-269b" d="M 5644 441 
Q 5644 13 5467 -157 
Q 5291 -328 4663 -328 
Q 4519 -328 4347 -319 
L 4172 206 
Q 4822 206 4981 250 
Q 5141 294 5141 544 
L 5141 4569 
L 1259 4569 
L 1259 -481 
L 756 -481 
L 756 5038 
L 5644 5038 
L 5644 441 
z
M 4941 3406 
L 1569 3406 
L 1569 3872 
L 4941 3872 
L 4941 3406 
z
M 4422 781 
L 1984 781 
L 1984 2700 
L 4422 2700 
L 4422 781 
z
M 3938 1247 
L 3938 2234 
L 2472 2234 
L 2472 1247 
L 3938 1247 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-3534" d="M 2828 3603 
L 1959 3603 
L 1959 2425 
L 2784 2713 
L 2784 2228 
L 1959 1931 
L 1959 219 
Q 1959 -106 1829 -232 
Q 1700 -359 1416 -359 
Q 1181 -359 775 -288 
L 616 213 
Q 1197 109 1334 109 
Q 1453 109 1453 288 
L 1453 1753 
L 550 1428 
L 313 1919 
L 1453 2284 
L 1453 3603 
L 453 3603 
L 453 4072 
L 1453 4072 
L 1453 5247 
L 1959 5247 
L 1959 4072 
L 2828 4072 
L 2828 3603 
z
M 6053 -31 
L 5716 -403 
Q 5125 -69 4716 416 
Q 4522 78 3872 -422 
L 3609 -159 
L 3609 -441 
L 3103 -441 
L 3103 5019 
L 5491 5019 
Q 5463 4247 5355 3901 
Q 5247 3556 5087 3437 
Q 4928 3319 4609 3319 
Q 4359 3319 4078 3391 
L 3956 3884 
Q 4338 3788 4641 3788 
Q 4744 3788 4794 3839 
Q 4844 3891 4900 4087 
Q 4956 4284 4966 4550 
L 3609 4550 
L 3609 3041 
L 5544 3041 
Q 5519 1894 4978 863 
Q 5256 463 6053 -31 
z
M 5038 2572 
L 4353 2572 
Q 4441 1913 4709 1319 
Q 4997 1922 5038 2572 
z
M 4422 856 
Q 4019 1619 3878 2572 
L 3609 2572 
L 3609 31 
Q 4144 369 4422 856 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-2186" d="M 6284 2975 
L 5900 2572 
Q 4847 3084 3928 4519 
Q 3178 3188 2041 2584 
L 1697 2981 
Q 3113 3628 3859 5422 
L 4281 5184 
L 4206 4997 
Q 5038 3547 6284 2975 
z
M 2241 5172 
Q 2156 4775 1913 4147 
L 1672 3531 
L 1672 -428 
L 1184 -428 
L 1184 2663 
Q 1113 2534 659 2041 
L 213 2322 
Q 1372 3522 1784 5344 
L 2241 5172 
z
M 4984 -409 
L 4500 -409 
L 4500 3116 
L 4984 3116 
L 4984 -409 
z
M 3397 1791 
Q 3397 1034 3097 531 
Q 2797 28 2059 -475 
L 1697 -72 
Q 2209 191 2561 647 
Q 2913 1103 2913 1528 
L 2913 3116 
L 3397 3116 
L 3397 1791 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-2e1b" d="M 5722 3469 
L 5247 3469 
L 5247 4166 
L 1159 4166 
L 1159 3469 
L 678 3469 
L 678 4634 
L 2956 4634 
L 2956 5369 
L 3444 5369 
L 3444 4634 
L 5722 4634 
L 5722 3469 
z
M 4831 3053 
L 1550 3053 
L 1550 3519 
L 4831 3519 
L 4831 3053 
z
M 6053 878 
Q 5925 116 5762 -76 
Q 5600 -269 5363 -269 
L 4031 -269 
Q 3566 -269 3566 256 
L 3566 1931 
L 2797 1931 
Q 2659 -34 678 -397 
L 384 72 
Q 2272 297 2284 1931 
L 831 1931 
L 831 2400 
L 5619 2400 
L 5619 1931 
L 4050 1931 
L 4050 422 
Q 4050 197 4244 197 
L 5141 197 
Q 5378 197 5451 369 
Q 5525 541 5575 1131 
L 6053 878 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-3803" d="M 6053 2322 
L 5825 1953 
Q 5019 2141 4575 2553 
Q 4088 2206 3519 1953 
L 3278 2316 
Q 3838 2544 4269 2900 
Q 4088 3169 3963 3494 
L 3725 3128 
L 3384 3322 
L 3384 3003 
L 2541 3003 
Q 2988 2866 3406 2516 
L 3103 2156 
Q 2831 2428 2344 2631 
L 2344 1984 
L 1856 1984 
L 1856 2919 
Q 1572 2306 609 1913 
L 384 2309 
Q 1103 2569 1422 3003 
L 763 3003 
L 763 4219 
L 1856 4219 
L 1856 4416 
L 488 4416 
L 488 4884 
L 1856 4884 
L 1856 5331 
L 2344 5331 
L 2344 4884 
L 3688 4884 
L 3688 4416 
L 2344 4416 
L 2344 4219 
L 3384 4219 
L 3384 3444 
Q 3919 4209 4109 5375 
L 4603 5234 
Q 4491 4816 4409 4569 
L 5875 4569 
L 5875 4103 
L 5509 4103 
Q 5241 3209 4916 2875 
Q 5272 2506 6053 2322 
z
M 5031 4103 
L 4256 4103 
L 4225 3994 
Q 4453 3388 4594 3219 
Q 4916 3619 5031 4103 
z
M 2900 3444 
L 2900 3775 
L 2344 3775 
L 2344 3444 
L 2900 3444 
z
M 1856 3444 
L 1856 3775 
L 1222 3775 
L 1222 3444 
L 1856 3444 
z
M 2413 3003 
L 2344 3003 
L 2344 2900 
L 2413 3003 
z
M 6047 -116 
L 325 -116 
L 325 325 
L 1369 325 
L 1369 1197 
L 1856 1197 
L 1856 325 
L 2900 325 
L 2900 1466 
L 716 1466 
L 716 1931 
L 5684 1931 
L 5684 1466 
L 3384 1466 
L 3384 1159 
L 5381 1159 
L 5381 716 
L 3384 716 
L 3384 325 
L 6047 325 
L 6047 -116 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-218c" d="M 6194 2875 
L 5778 2553 
Q 5528 2697 5294 2969 
Q 5269 1894 5181 1111 
Q 5094 328 4944 25 
Q 4794 -278 4372 -278 
Q 4047 -278 3609 -166 
L 3456 372 
Q 4003 178 4359 178 
Q 4475 178 4525 333 
Q 4575 488 4667 1075 
Q 4759 1663 4781 2559 
L 3916 2559 
Q 3822 219 2234 -447 
L 1888 -78 
Q 3416 516 3444 2559 
L 2625 2559 
L 2625 2975 
Q 2409 2722 2150 2484 
L 1813 2759 
L 1813 -475 
L 1325 -475 
L 1325 2816 
L 1319 2828 
Q 1319 2813 1131 2617 
Q 944 2422 738 2253 
L 319 2534 
Q 1466 3466 2009 5300 
L 2450 5094 
Q 2328 4681 2069 4116 
L 1813 3572 
L 1813 2834 
Q 2794 3716 3103 4897 
L 3475 4678 
Q 3244 3744 2669 3028 
L 5241 3028 
Q 4750 3606 4459 4494 
L 3506 4494 
L 3500 4953 
L 4825 4953 
Q 5241 3419 6194 2875 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-19f7" d="M 3541 2675 
L 2900 2675 
L 2900 3316 
L 3541 3316 
L 3541 2675 
z
M 3541 0 
Q 3541 -397 3389 -606 
Q 3238 -816 3016 -903 
L 2863 -666 
Q 3213 -516 3216 0 
L 2900 0 
L 2900 641 
L 3541 641 
L 3541 0 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-514e" d="M 2503 3981 
Q 1903 2625 1141 1947 
L 1153 1931 
L 2444 2144 
L 2456 1709 
Q 1428 1534 575 1313 
L 341 1772 
Q 934 2234 1344 2919 
L 563 2725 
L 347 3206 
Q 1059 4156 1325 5319 
Q 1403 5288 1551 5209 
Q 1700 5131 1791 5100 
Q 1441 3947 959 3316 
Q 1597 3375 1650 3397 
Q 1944 3938 2059 4225 
L 2503 3981 
z
M 5997 481 
Q 5925 44 5808 -170 
Q 5691 -384 5497 -384 
Q 5319 -384 4869 -115 
Q 4419 153 4031 666 
Q 3594 188 2388 -341 
L 2088 72 
Q 3097 466 3763 1088 
Q 3503 1550 3406 2419 
L 2484 2272 
L 2406 2725 
L 3378 2900 
L 3378 3397 
L 2606 3278 
L 2522 3731 
L 3378 3891 
L 3378 5209 
Q 3763 5288 3866 5294 
L 3866 3975 
L 5409 4231 
L 5497 3781 
Q 4550 3622 3866 3481 
L 3866 2994 
L 5772 3341 
Q 5825 3150 5856 2875 
L 3884 2516 
Q 3988 1794 4147 1466 
Q 4731 1991 5075 2484 
L 5453 2222 
Q 4731 1353 4372 1025 
Q 4753 456 5403 153 
Q 5494 378 5509 750 
L 5997 481 
z
M 5166 4544 
L 4831 4225 
Q 4478 4656 4019 4856 
L 4306 5178 
Q 4784 4956 5166 4544 
z
M 2578 872 
L 531 134 
Q 500 197 412 347 
Q 325 497 281 603 
L 2578 1369 
L 2578 872 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-20c9" d="M 5350 3828 
L 5306 2566 
Q 5281 1881 5236 1293 
Q 5191 706 5117 340 
Q 5044 -25 4945 -145 
Q 4847 -266 4720 -327 
Q 4594 -388 4428 -388 
Q 4206 -388 3700 -275 
L 3622 225 
Q 3725 206 3978 145 
Q 4231 84 4384 84 
Q 4459 84 4545 143 
Q 4631 203 4731 1045 
Q 4831 1888 4863 3359 
L 3181 3359 
Q 3169 2088 2673 1128 
Q 2178 169 953 -416 
L 622 13 
Q 1219 216 1762 723 
Q 2306 1231 2511 2029 
Q 2716 2828 2694 3359 
L 525 3359 
L 525 3828 
L 2694 3828 
L 2694 5294 
Q 3047 5306 3181 5306 
L 3181 3828 
L 5350 3828 
z
M 2284 4231 
L 1869 3903 
Q 1706 4347 1056 4781 
L 1453 5081 
Q 2041 4650 2284 4231 
z
M 4500 1350 
L 4063 1081 
Q 3913 1684 3219 2419 
L 3622 2656 
Q 4219 2072 4500 1350 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-51c9" d="M 6081 -31 
L 5716 -403 
Q 5094 128 4805 642 
Q 4516 1156 4319 1978 
Q 4172 1084 3815 556 
Q 3459 28 2847 -434 
L 2431 -91 
Q 3616 672 3809 1966 
L 3059 1966 
L 3059 2431 
L 3859 2431 
Q 3913 2963 3922 3781 
L 3244 3781 
L 3244 4250 
L 3916 4250 
L 3916 5350 
L 4403 5350 
L 4403 4250 
L 5509 4250 
L 5509 2431 
L 5931 2431 
L 5931 1966 
L 4794 1966 
Q 5138 669 6081 -31 
z
M 5025 2431 
L 5025 3781 
L 4422 3781 
Q 4431 3403 4366 2431 
L 5025 2431 
z
M 3213 2681 
L 2081 2681 
L 2081 831 
L 2450 831 
L 2450 2338 
L 2938 2338 
L 2938 366 
L 1203 366 
L 1203 -50 
L 716 -50 
L 716 2338 
L 1203 2338 
L 1203 831 
L 1594 831 
L 1594 2681 
L 397 2681 
L 397 3150 
L 1594 3150 
L 1594 4038 
L 1228 4038 
Q 1053 3678 813 3322 
L 378 3622 
Q 966 4275 1141 5313 
L 1575 5094 
Q 1534 4838 1422 4506 
L 2894 4506 
L 2894 4038 
L 2081 4038 
L 2081 3150 
L 3213 3150 
L 3213 2681 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-11ed" d="M 1466 1503 
Q 1847 1503 2117 1231 
Q 2388 959 2388 575 
Q 2388 194 2119 -76 
Q 1850 -347 1472 -347 
Q 1091 -347 820 -76 
Q 550 194 550 575 
Q 550 959 819 1231 
Q 1088 1503 1466 1503 
z
M 1469 44 
Q 1691 44 1845 201 
Q 2000 359 2000 581 
Q 2000 803 1844 958 
Q 1688 1113 1469 1113 
Q 1250 1113 1094 958 
Q 938 803 938 581 
Q 938 359 1092 201 
Q 1247 44 1469 44 
z
" transform="scale(0.015625)"/>
    </defs>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-14" transform="translate(111.21875 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-18" transform="translate(166.828125 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-ca7" transform="translate(222.4375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15" transform="translate(322.4375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-13" transform="translate(378.046875 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15" transform="translate(433.65625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-18" transform="translate(489.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3" transform="translate(544.875 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3103" transform="translate(572.65625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-19e8" transform="translate(672.65625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-14" transform="translate(772.65625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-15" transform="translate(828.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-1a" transform="translate(883.875 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3" transform="translate(939.484375 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-20b9" transform="translate(967.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2400" transform="translate(1067.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-269b" transform="translate(1167.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3534" transform="translate(1267.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2186" transform="translate(1367.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2e1b" transform="translate(1467.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3803" transform="translate(1567.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3997" transform="translate(1667.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-218c" transform="translate(1767.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-19f7" transform="translate(1867.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-6460" transform="translate(1967.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-514e" transform="translate(2067.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-20c9" transform="translate(2167.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-51c9" transform="translate(2267.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2186" transform="translate(2367.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3997" transform="translate(2467.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-218c" transform="translate(2567.265625 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-11ed" transform="translate(2667.265625 0)"/>
   </g>
   <!-- 仅展示月度选择差额，不把断月报价拼成账户净值。 -->
   <g style="fill: #555555" transform="translate(48.384 410.0832) scale(0.09 -0.09)">
    <defs>
     <path id="cn-monthly-increment-ArialUnicodeMS-2154" d="M 2322 5100 
Q 2216 4741 2009 4219 
L 1806 3725 
L 1806 -366 
L 1344 -366 
L 1344 2772 
L 1325 2772 
Q 956 2147 494 1772 
L 147 2119 
Q 566 2444 948 3084 
Q 1331 3725 1919 5325 
L 2322 5100 
z
M 5991 13 
L 5716 -397 
Q 4781 109 4050 1063 
Q 3244 106 2175 -366 
L 1881 44 
Q 2994 575 3763 1459 
Q 2981 2631 2766 4231 
L 2297 4231 
L 2297 4691 
L 5428 4691 
L 5428 4263 
Q 5356 3691 5065 2866 
Q 4775 2041 4372 1472 
Q 5056 522 5991 13 
z
M 4916 4231 
L 3263 4231 
Q 3353 3044 4063 1894 
Q 4741 2897 4916 4231 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-2ee4" d="M 5422 3506 
L 1388 3506 
L 1388 1991 
Q 1388 681 728 -469 
L 294 -184 
Q 903 772 903 2075 
L 903 4984 
L 5422 4984 
L 5422 3506 
z
M 4934 3975 
L 4934 4519 
L 1388 4519 
L 1388 3975 
L 4934 3975 
z
M 6034 38 
L 5716 -416 
Q 3913 -53 3406 1472 
L 2700 1472 
L 2700 191 
L 3822 384 
L 3822 -103 
L 1753 -469 
L 1478 6 
L 2216 109 
L 2216 1472 
L 1503 1472 
L 1503 1941 
L 2528 1941 
L 2528 2534 
L 1638 2534 
L 1638 3003 
L 2528 3003 
L 2528 3419 
L 3016 3419 
L 3016 3003 
L 4091 3003 
L 4091 3419 
L 4575 3419 
L 4575 3003 
L 5491 3003 
L 5491 2534 
L 4575 2534 
L 4575 1941 
L 5741 1941 
L 5741 1472 
L 3909 1472 
Q 4081 1016 4384 744 
Q 4694 953 4984 1416 
L 5375 1119 
Q 5063 713 4728 469 
Q 5138 175 6034 38 
z
M 4091 1941 
L 4091 2534 
L 3016 2534 
L 3016 1941 
L 4091 1941 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-4bc9" d="M 5253 4378 
L 1269 4378 
L 1269 4844 
L 5253 4844 
L 5253 4378 
z
M 5663 2988 
L 3525 2988 
L 3525 72 
Q 3525 -188 3342 -311 
Q 3159 -434 2876 -425 
Q 2594 -416 2259 -422 
L 2069 128 
Q 2475 81 2756 81 
Q 3022 81 3022 275 
L 3022 2988 
L 831 2988 
L 831 3456 
L 5663 3456 
L 5663 2988 
z
M 2369 2344 
Q 1934 1300 922 366 
L 581 716 
Q 984 1047 1406 1620 
Q 1828 2194 1959 2613 
L 2369 2344 
z
M 5966 697 
L 5569 366 
Q 4938 1575 4019 2253 
L 4397 2584 
Q 5231 2019 5966 697 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-3135" d="M 5913 4269 
L 1363 4269 
L 1363 2278 
Q 1363 1144 1180 528 
Q 997 -88 684 -434 
L 294 -147 
Q 669 378 773 940 
Q 878 1503 878 2350 
L 878 4738 
L 3200 4738 
L 3200 5288 
L 3706 5288 
L 3706 4738 
L 5913 4738 
L 5913 4269 
z
M 5778 3194 
L 4728 3194 
L 4728 2303 
L 2350 2303 
L 2350 3194 
L 1472 3194 
L 1472 3659 
L 2350 3659 
L 2350 4147 
L 2828 4147 
L 2828 3659 
L 4244 3659 
L 4244 4147 
L 4728 4147 
L 4728 3659 
L 5778 3659 
L 5778 3194 
z
M 4244 2747 
L 4244 3194 
L 2834 3194 
L 2834 2747 
L 4244 2747 
z
M 6081 72 
L 5819 -397 
Q 4484 -216 3531 263 
Q 2494 -234 1388 -397 
L 1088 44 
Q 2078 134 3034 550 
Q 2509 934 2113 1528 
L 1625 1528 
L 1625 1972 
L 5159 1972 
L 5159 1544 
Q 4819 1025 4044 538 
Q 4963 166 6081 72 
z
M 4544 1528 
L 2700 1528 
Q 3125 1038 3531 781 
Q 4194 1159 4544 1528 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-3578" d="M 2450 3469 
L 1656 3469 
L 1656 2356 
Q 1825 2431 2194 2572 
L 2194 2088 
Q 2091 2025 1905 1942 
Q 1719 1859 1656 1825 
L 1656 13 
Q 1656 -156 1534 -282 
Q 1413 -409 1253 -409 
L 659 -409 
L 481 97 
L 1069 78 
Q 1172 78 1172 159 
L 1172 1588 
Q 1028 1519 513 1306 
L 191 1709 
Q 622 1863 1172 2113 
L 1172 3469 
L 384 3469 
L 384 3938 
L 1172 3938 
L 1172 5288 
L 1656 5288 
L 1656 3938 
L 2450 3938 
L 2450 3469 
z
M 6028 2828 
L 5753 2381 
Q 4759 2531 4000 3091 
Q 3291 2669 2444 2497 
L 2138 2956 
Q 3091 3159 3584 3406 
Q 3081 3831 2713 4556 
L 2328 4556 
L 2328 5025 
L 5472 5025 
L 5472 4616 
Q 5028 3819 4441 3378 
Q 5141 2991 6028 2828 
z
M 4884 4556 
L 3225 4556 
Q 3597 3934 4006 3659 
Q 4431 3909 4884 4556 
z
M 5844 922 
L 4206 922 
L 4206 -409 
L 3750 -409 
L 3750 922 
L 2081 922 
L 2081 1388 
L 3750 1388 
L 3750 1831 
L 2394 1831 
L 2394 2297 
L 3750 2297 
L 3750 2731 
L 4206 2731 
L 4206 2297 
L 5600 2297 
L 5600 1831 
L 4206 1831 
L 4206 1388 
L 5844 1388 
L 5844 922 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-6b2c" d="M 3003 3719 
L 2541 3719 
L 2541 4147 
L 959 4147 
L 959 3688 
L 475 3688 
L 475 4588 
L 1575 4588 
Q 1516 4728 1119 5119 
L 1484 5363 
Q 1803 5097 2075 4575 
L 3003 4588 
L 3003 3719 
z
M 5797 4563 
L 4678 4563 
Q 4638 4416 4453 3988 
L 5550 3988 
L 5550 972 
L 5088 972 
L 5088 3519 
L 3622 3519 
L 3622 872 
L 3163 872 
L 3163 3988 
L 3928 3988 
Q 4125 4294 4191 4563 
L 3059 4563 
L 3059 5031 
L 5797 5031 
L 5797 4563 
z
M 3047 2163 
L 2791 1759 
Q 2556 1934 2264 2045 
Q 1972 2156 1875 2203 
Q 1431 1825 1141 1697 
L 2791 1697 
L 2791 172 
L 1331 172 
L 1331 -244 
L 844 -244 
L 844 1522 
Q 822 1519 538 1381 
L 231 1766 
Q 897 2016 1394 2413 
Q 1075 2503 872 2534 
L 1106 2906 
Q 1406 2856 1791 2725 
Q 2063 2978 2194 3188 
L 1294 3188 
Q 897 2788 519 2509 
L 197 2875 
Q 1072 3459 1403 4078 
L 1734 3847 
Q 1700 3747 1563 3628 
L 2759 3628 
L 2759 3219 
Q 2381 2666 2234 2541 
Q 2694 2381 3047 2163 
z
M 2303 641 
L 2303 1228 
L 1331 1228 
L 1331 641 
L 2303 641 
z
M 4609 3328 
Q 4609 1725 4459 1134 
Q 4309 544 3995 240 
Q 3681 -63 2869 -403 
L 2559 31 
Q 3131 181 3511 484 
Q 3891 788 4028 1370 
Q 4166 1953 4141 3328 
L 4609 3328 
z
M 6022 134 
L 5650 -238 
Q 5075 409 4416 697 
L 4684 1050 
Q 5494 656 6022 134 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-209c" d="M 5900 4434 
L 3834 4434 
Q 3700 4209 3425 3816 
L 3425 -416 
L 2900 -416 
L 2900 3194 
Q 2281 2363 775 1528 
L 453 1947 
Q 1431 2419 2047 2975 
Q 2663 3531 3219 4434 
L 550 4434 
L 550 4922 
L 5900 4922 
L 5900 4434 
z
M 5941 1838 
L 5550 1503 
Q 4619 2634 3597 3078 
L 3938 3419 
Q 4969 2953 5941 1838 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-3519" d="M 2472 3603 
L 1778 3603 
L 1778 2406 
Q 1916 2444 2438 2669 
L 2438 2188 
L 1778 1925 
L 1778 72 
Q 1703 -397 1350 -397 
L 678 -397 
L 538 84 
L 1172 84 
Q 1206 84 1250 162 
Q 1294 241 1294 281 
L 1294 1766 
L 588 1509 
L 256 1894 
Q 1063 2163 1294 2259 
L 1294 3603 
L 434 3603 
L 434 4072 
L 1294 4072 
L 1294 5331 
L 1778 5331 
L 1778 4072 
L 2472 4072 
L 2472 3603 
z
M 6022 1088 
Q 5906 216 5698 -17 
Q 5491 -250 5228 -250 
L 3334 -250 
Q 3131 -250 2893 -84 
Q 2656 81 2656 269 
L 2656 4934 
L 5600 4934 
L 5600 2081 
L 3144 2081 
L 3144 422 
Q 3144 219 3397 219 
L 5113 219 
Q 5250 219 5354 381 
Q 5459 544 5569 1203 
L 6022 1088 
z
M 5113 2547 
L 5113 4469 
L 4372 4469 
L 4372 2547 
L 5113 2547 
z
M 3884 2547 
L 3884 4469 
L 3144 4469 
L 3144 2547 
L 3884 2547 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-383c" d="M 6053 2950 
L 5428 2950 
L 5428 -422 
L 4966 -422 
L 4966 2950 
L 4256 2950 
L 4256 1984 
Q 4291 478 3628 -347 
L 3206 -78 
Q 3247 -47 3309 38 
L 1094 38 
L 1094 -331 
L 634 -331 
L 634 4850 
L 1094 4850 
L 1094 1619 
Q 1578 2044 1869 2766 
L 1191 2766 
L 1191 3231 
L 2203 3231 
L 2203 5216 
L 2663 5216 
L 2663 3231 
L 3609 3231 
L 3609 2766 
L 2663 2766 
L 2663 581 
L 2203 581 
L 2203 2522 
Q 2038 1850 1259 1044 
L 1094 1209 
L 1094 506 
L 3506 506 
Q 3781 931 3781 1953 
L 3781 4819 
Q 4656 4888 5516 5275 
L 5819 4897 
Q 4984 4559 4269 4453 
L 4269 3419 
L 6053 3419 
L 6053 2950 
z
M 3653 4488 
Q 3491 3709 3175 3366 
L 2791 3616 
Q 3122 4016 3263 4659 
L 3653 4488 
z
M 2113 3603 
L 1691 3378 
Q 1506 4072 1228 4434 
L 1600 4653 
Q 1931 4206 2113 3603 
z
M 3700 1528 
L 3250 1319 
Q 3131 1847 2747 2381 
L 3078 2584 
Q 3438 2153 3700 1528 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-358b" d="M 6075 2266 
L 6069 1772 
L 5159 1772 
L 5159 -447 
L 4653 -447 
L 4653 1772 
L 3769 1772 
Q 3775 447 2247 -391 
L 1875 -25 
Q 2722 488 2994 914 
Q 3266 1341 3272 1766 
L 2316 1766 
L 2309 2266 
L 3256 2266 
L 3256 3572 
L 2650 3572 
L 2650 4072 
L 3547 4072 
Q 3378 4641 2713 5081 
L 3144 5350 
Q 3844 4838 4031 4206 
L 3853 4084 
L 3853 4072 
L 4359 4072 
Q 4909 4697 5050 5369 
L 5528 5166 
Q 5391 4644 4966 4072 
L 5825 4072 
L 5831 3572 
L 5159 3572 
L 5159 2266 
L 6075 2266 
z
M 4653 2266 
L 4653 3572 
L 3763 3572 
L 3763 2266 
L 4653 2266 
z
M 2559 2394 
L 1791 2059 
L 1791 25 
Q 1763 -134 1616 -282 
Q 1469 -431 1186 -423 
Q 903 -416 781 -422 
L 575 91 
Q 844 50 1072 50 
Q 1216 50 1258 100 
Q 1300 150 1300 238 
L 1300 1838 
L 575 1544 
L 306 1947 
L 1294 2356 
L 1294 3572 
L 475 3572 
L 469 4044 
L 1294 4044 
L 1294 5269 
L 1791 5269 
L 1791 4044 
L 2522 4044 
L 2522 3572 
L 1791 3572 
L 1791 2541 
Q 2466 2853 2559 2888 
L 2559 2394 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-349f" d="M 6047 806 
Q 6053 666 5929 261 
Q 5806 -144 5709 -276 
Q 5613 -409 5428 -409 
Q 5159 -409 4751 47 
Q 4344 503 4153 947 
Q 3516 272 2859 -128 
L 2419 213 
Q 3338 709 3922 1409 
Q 3591 2216 3438 3769 
L 1516 3769 
L 1516 2900 
L 3225 2900 
Q 3181 1622 3020 1140 
Q 2859 659 2338 659 
Q 2150 659 1819 709 
L 1606 1241 
Q 2009 1119 2363 1119 
Q 2584 1119 2648 1505 
Q 2713 1891 2725 2431 
L 1509 2431 
Q 1481 1084 1270 496 
Q 1059 -91 728 -459 
L 319 -153 
Q 1000 541 1013 2009 
L 1031 4238 
L 3391 4238 
Q 3359 4997 3359 5319 
L 3841 5319 
Q 3850 4619 3878 4238 
L 5747 4238 
L 5747 3769 
L 3909 3769 
Q 4025 2497 4288 1838 
Q 4734 2413 5106 3431 
L 5550 3284 
Q 5113 2075 4500 1325 
Q 4738 869 5008 498 
Q 5278 128 5409 128 
Q 5450 128 5509 462 
Q 5569 797 5575 1081 
L 6047 806 
z
M 5650 4659 
L 5306 4359 
Q 4688 4859 4063 4928 
L 4447 5275 
Q 5144 5119 5650 4659 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-5fb5" d="M 6131 -78 
L 5772 -459 
Q 4466 463 4191 2363 
L 3781 2363 
L 3781 172 
L 4641 506 
L 4641 6 
L 3366 -434 
L 3128 -25 
Q 3297 47 3297 191 
L 3297 2363 
L 2931 2363 
L 2931 2828 
L 3297 2828 
L 3297 5191 
L 3781 5191 
L 3781 3431 
Q 4778 3975 5294 4856 
L 5691 4550 
Q 5413 4056 4864 3604 
Q 4316 3153 3781 2944 
L 3781 2828 
L 5863 2828 
L 5863 2363 
L 4628 2363 
Q 4678 1766 5104 1027 
Q 5531 288 6131 -78 
z
M 2759 1044 
L 2272 1044 
L 2272 4416 
L 1100 4416 
L 1100 1044 
L 641 1044 
L 641 4884 
L 2759 4884 
L 2759 1044 
z
M 1959 1766 
Q 1959 1150 1590 567 
Q 1222 -16 556 -434 
L 206 -44 
Q 806 303 1139 779 
Q 1472 1256 1472 2009 
L 1472 4050 
L 1959 3994 
L 1959 1766 
z
M 3053 63 
L 2681 -319 
Q 2384 313 1753 622 
L 2022 966 
Q 2659 703 3053 63 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-34c6" d="M 5434 2291 
L 4947 2291 
L 4947 2553 
L 1684 2553 
Q 1700 1378 1490 734 
Q 1281 91 781 -422 
L 341 -78 
Q 1191 647 1191 2003 
L 1191 4341 
L 3244 4341 
Q 3000 4744 2456 5075 
L 2816 5388 
Q 3384 5044 3769 4506 
L 3559 4359 
L 3559 4341 
L 5434 4341 
L 5434 2291 
z
M 4947 3016 
L 4947 3878 
L 1678 3878 
L 1678 3016 
L 4947 3016 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-244f" d="M 5900 2234 
L 5409 2234 
L 5409 1088 
L 4013 1088 
L 4013 103 
Q 4013 -28 3914 -167 
Q 3816 -306 3684 -322 
L 3072 -391 
L 2853 116 
L 3469 97 
Q 3497 106 3525 134 
L 3525 1088 
L 2259 1088 
L 2259 1556 
L 3525 1556 
L 3525 2234 
L 1900 2234 
L 1900 2700 
L 3525 2700 
L 3525 3263 
L 2503 3263 
L 2503 3488 
L 2491 3488 
Q 2313 3253 2059 3097 
L 1678 3438 
Q 2606 4022 3128 5369 
L 3541 5178 
Q 3447 4884 3353 4697 
L 4794 4697 
L 4794 4294 
Q 4481 3772 4447 3731 
L 5409 3731 
L 5409 2700 
L 5900 2700 
L 5900 2234 
z
M 4191 4231 
L 3109 4231 
Q 2978 4000 2759 3731 
L 3853 3731 
Q 3991 3897 4191 4231 
z
M 4922 2700 
L 4922 3263 
L 4013 3263 
L 4013 2700 
L 4922 2700 
z
M 4922 1556 
L 4922 2234 
L 4013 2234 
L 4013 1556 
L 4922 1556 
z
M 1797 3956 
L 1381 3628 
Q 931 4309 372 4634 
L 716 4934 
Q 1422 4513 1797 3956 
z
M 1838 1925 
Q 1581 744 813 -238 
L 409 38 
Q 653 313 990 992 
Q 1328 1672 1428 2156 
L 1838 1925 
z
" transform="scale(0.015625)"/>
     <path id="cn-monthly-increment-ArialUnicodeMS-22cb" d="M 6034 -172 
L 1791 -172 
L 1791 294 
L 2344 294 
L 2344 3853 
L 3425 3853 
Q 3544 4109 3609 4341 
L 1925 4341 
L 1919 4672 
Q 1841 4369 1691 3981 
L 1544 3622 
L 1544 -434 
L 1056 -434 
L 1056 2753 
Q 859 2466 634 2241 
L 238 2516 
Q 1222 3619 1588 5325 
L 2028 5172 
Q 2009 5038 1953 4806 
L 3731 4806 
Q 3772 4997 3781 5338 
L 4275 5253 
Q 4275 5013 4225 4806 
L 5813 4806 
L 5813 4341 
L 4134 4341 
Q 4091 4188 3956 3853 
L 5409 3853 
L 5409 294 
L 6034 294 
L 6034 -172 
z
M 4922 2994 
L 4922 3384 
L 2828 3384 
L 2828 2994 
L 4922 2994 
z
M 4922 2138 
L 4922 2584 
L 2828 2584 
L 2828 2138 
L 4922 2138 
z
M 4922 1241 
L 4922 1716 
L 2828 1716 
L 2828 1241 
L 4922 1241 
z
M 4922 294 
L 4922 825 
L 2828 825 
L 2828 294 
L 4922 294 
z
" transform="scale(0.015625)"/>
    </defs>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2154"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2ee4" transform="translate(100 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-4bc9" transform="translate(200 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3997" transform="translate(300 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3135" transform="translate(400 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-6298" transform="translate(500 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3578" transform="translate(600 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-307d" transform="translate(700 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-6b2c" transform="translate(800 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-19e8" transform="translate(900 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-209c" transform="translate(1000 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3519" transform="translate(1100 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-383c" transform="translate(1200 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3997" transform="translate(1300 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-3534" transform="translate(1400 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-2186" transform="translate(1500 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-358b" transform="translate(1600 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-349f" transform="translate(1700 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-5fb5" transform="translate(1800 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-34c6" transform="translate(1900 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-244f" transform="translate(2000 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-22cb" transform="translate(2100 0)"/>
    <use xlink:href="#cn-monthly-increment-ArialUnicodeMS-11ed" transform="translate(2200 0)"/>
   </g>
  </g>
 </g>
 <defs>
  <clipPath id="cn-monthly-increment-p8441f1c113">
   <rect x="41.899609" y="74.680664" width="552.100391" height="125.615727"/>
  </clipPath>
  <clipPath id="cn-monthly-increment-pab1dc66e22">
   <rect x="41.899609" y="231.396391" width="552.100391" height="125.615727"/>
  </clipPath>
 </defs>
</svg>


## 4. 美股：完整公开组合路径与对照

下面是2015—2024年**公开毛收益**，没有费用、税、汇率换算或外部入金。每种方法初始100美元，组内收益按来源规则累计。最大跌幅只看月末，可能低估日内/日间实际跌幅。16分组参考为同规模各格按月均分资金，不是母指数。

| 规模 | 方法 | 累计毛收益 | 年化毛收益 | 最大月末跌幅 | 最长未恢复（月） |
| --- | --- | --- | --- | --- | --- |
| 大盘 | 新：盈利低扩张＋动量 | 313.73% | 15.26% | -23.31% | 23 |
| 大盘 | 盈利低扩张单独使用 | 391.56% | 17.26% | -24.65% | 23 |
| 大盘 | 动量单独使用 | 235.90% | 12.88% | -24.14% | 26 |
| 大盘 | 同源盈利＋动量 | 260.91% | 13.69% | -22.47% | 23 |
| 大盘 | 初始一半盈利低扩张、一半现金 | 195.78% | 11.45% | -19.38% | 23 |
| 大盘 | 同源盈利单独使用 | 285.92% | 14.46% | -23.42% | 18 |
| 大盘 | 全部16分组参考 | 219.56% | 12.32% | -22.45% | 23 |
| 小盘 | 新：盈利低扩张＋动量 | 228.04% | 12.61% | -36.78% | 26 |
| 小盘 | 盈利低扩张单独使用 | 249.27% | 13.32% | -41.16% | 26 |
| 小盘 | 动量单独使用 | 206.80% | 11.86% | -32.70% | 27 |
| 小盘 | 同源盈利＋动量 | 187.80% | 11.15% | -38.20% | 26 |
| 小盘 | 初始一半盈利低扩张、一半现金 | 124.63% | 8.43% | -24.70% | 26 |
| 小盘 | 同源盈利单独使用 | 168.80% | 10.39% | -44.16% | 26 |
| 小盘 | 全部16分组参考 | 154.42% | 9.79% | -36.08% | 29 |

大盘新组合相对“盈利＋动量”累计多52.82个百分点、年化多1.56个百分点，但最大月末跌幅深0.84个百分点。相对“盈利低扩张”单独使用，新组合年化少2.00个百分点，跌幅只改善1.34个百分点，最长未恢复时间仍23个月。

小盘主期新组合相对“盈利＋动量”年化多1.46个百分点，跌幅改善1.42个百分点；但相对单独动量，收益多0.75个百分点的同时，跌幅加深4.08个百分点。这里有收益与风险交换，不能写成全面更好。

<svg style="display:block;max-width:100%;height:auto" xmlns:xlink="http://www.w3.org/1999/xlink" width="100%" height="auto" viewBox="0 0 604.8 612" xmlns="http://www.w3.org/2000/svg" version="1.1">
 <metadata>
  <rdf:RDF xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:cc="http://creativecommons.org/ns#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
   <cc:Work>
    <dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage"/>
    <dc:date>2026-10-24T13:56:20.490865</dc:date>
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
 <g id="us-big-figure_1">
  <g id="us-big-patch_1">
   <path d="M 0 612 
L 604.8 612 
L 604.8 0 
L 0 0 
z
" style="fill: #fbfaf7"/>
  </g>
  <g id="us-big-axes_1">
   <g id="us-big-patch_2">
    <path d="M 49.819609 213.125661 
L 594 213.125661 
L 594 79.919375 
L 49.819609 79.919375 
z
" style="fill: #fbfaf7"/>
   </g>
   <g id="us-big-matplotlib.axis_1">
    <g id="us-big-xtick_1">
     <g id="us-big-line2d_1">
      <path d="M 124.120824 213.125661 
L 124.120824 79.919375 
" clip-path="url(#us-big-p1eaef6550d)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_2">
      <defs>
       <path id="us-big-m8896d8f95c" d="M 0 0 
L 0 3.5 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="124.120824" y="213.125661" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-big-xtick_2">
     <g id="us-big-line2d_3">
      <path d="M 223.116884 213.125661 
L 223.116884 79.919375 
" clip-path="url(#us-big-p1eaef6550d)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_4">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="223.116884" y="213.125661" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-big-xtick_3">
     <g id="us-big-line2d_5">
      <path d="M 321.977517 213.125661 
L 321.977517 79.919375 
" clip-path="url(#us-big-p1eaef6550d)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_6">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="321.977517" y="213.125661" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-big-xtick_4">
     <g id="us-big-line2d_7">
      <path d="M 420.973577 213.125661 
L 420.973577 79.919375 
" clip-path="url(#us-big-p1eaef6550d)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_8">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="420.973577" y="213.125661" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-big-xtick_5">
     <g id="us-big-line2d_9">
      <path d="M 519.834211 213.125661 
L 519.834211 79.919375 
" clip-path="url(#us-big-p1eaef6550d)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_10">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="519.834211" y="213.125661" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
   </g>
   <g id="us-big-matplotlib.axis_2">
    <g id="us-big-ytick_1">
     <g id="us-big-line2d_11">
      <path d="M 49.819609 202.142799 
L 594 202.142799 
" clip-path="url(#us-big-p1eaef6550d)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_12">
      <defs>
       <path id="us-big-m7e9fe31986" d="M 0 0 
L -3.5 0 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="202.142799" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_1">
      <!-- 0 -->
      <g transform="translate(37.258672 205.782935) scale(0.1 -0.1)">
       <defs>
        <path id="us-big-ArialUnicodeMS-13" d="M 1778 4603 
Q 3272 4603 3272 2259 
Q 3272 1075 2886 498 
Q 2500 -78 1778 -78 
Q 288 -78 288 2259 
Q 288 3444 673 4023 
Q 1059 4603 1778 4603 
z
M 1778 384 
Q 2231 384 2462 823 
Q 2694 1263 2694 2259 
Q 2694 2953 2592 3351 
Q 2491 3750 2286 3945 
Q 2081 4141 1772 4141 
Q 1319 4141 1091 3694 
Q 863 3247 863 2259 
Q 863 1575 966 1175 
Q 1069 775 1272 579 
Q 1475 384 1778 384 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-big-ArialUnicodeMS-13"/>
      </g>
     </g>
    </g>
    <g id="us-big-ytick_2">
     <g id="us-big-line2d_13">
      <path d="M 49.819609 158.153197 
L 594 158.153197 
" clip-path="url(#us-big-p1eaef6550d)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_14">
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="158.153197" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_2">
      <!-- 20 -->
      <g transform="translate(31.697734 161.793334) scale(0.1 -0.1)">
       <defs>
        <path id="us-big-ArialUnicodeMS-15" d="M 3231 0 
L 197 0 
Q 197 388 467 784 
Q 738 1181 1478 1778 
Q 1931 2141 2287 2539 
Q 2644 2938 2644 3341 
Q 2644 3688 2398 3914 
Q 2153 4141 1778 4141 
Q 1400 4141 1144 3908 
Q 888 3675 884 3213 
L 306 3278 
Q 359 3922 764 4262 
Q 1169 4603 1791 4603 
Q 2466 4603 2842 4229 
Q 3219 3856 3219 3328 
Q 3219 2888 2901 2436 
Q 2584 1984 1638 1228 
Q 1141 831 978 544 
L 3231 544 
L 3231 0 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-big-ArialUnicodeMS-15"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-ytick_3">
     <g id="us-big-line2d_15">
      <path d="M 49.819609 114.163595 
L 594 114.163595 
" clip-path="url(#us-big-p1eaef6550d)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_16">
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="114.163595" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_3">
      <!-- 40 -->
      <g transform="translate(31.697734 117.803732) scale(0.1 -0.1)">
       <defs>
        <path id="us-big-ArialUnicodeMS-17" d="M 3263 1094 
L 2644 1094 
L 2644 0 
L 2081 0 
L 2081 1094 
L 97 1094 
L 97 1613 
L 2181 4581 
L 2644 4581 
L 2644 1613 
L 3263 1613 
L 3263 1094 
z
M 2081 1613 
L 2081 3681 
L 2069 3681 
L 647 1613 
L 2081 1613 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-big-ArialUnicodeMS-17"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-text_4">
     <!-- 百分点 -->
     <g transform="translate(25.598125 161.522518) rotate(-90) scale(0.1 -0.1)">
      <defs>
       <path id="us-big-ArialUnicodeMS-490d" d="M 5850 4506 
L 3572 4506 
Q 3538 4184 3372 3725 
L 5088 3725 
L 5088 -409 
L 4581 -409 
L 4581 91 
L 1941 91 
L 1941 -428 
L 1434 -428 
L 1434 3725 
L 2822 3725 
Q 3000 4009 3066 4506 
L 628 4506 
L 628 4991 
L 5850 4991 
L 5850 4506 
z
M 4581 2175 
L 4581 3238 
L 1941 3238 
L 1941 2175 
L 4581 2175 
z
M 4581 575 
L 4581 1691 
L 1941 1691 
L 1941 575 
L 4581 575 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-2495" d="M 5991 3003 
L 5684 2553 
Q 4856 3041 4451 3534 
Q 4047 4028 3781 4831 
L 4319 4984 
Q 4375 4356 4829 3825 
Q 5284 3294 5991 3003 
z
M 2613 4697 
Q 2169 3484 800 2547 
L 416 2919 
Q 1731 3741 2188 4934 
L 2613 4697 
z
M 4872 2931 
Q 4844 1956 4730 1092 
Q 4616 228 4430 7 
Q 4244 -213 3847 -213 
Q 3469 -213 2894 -78 
L 2747 481 
Q 3503 269 3834 269 
Q 4013 269 4128 639 
Q 4244 1009 4341 2463 
L 3138 2463 
Q 2869 263 831 -441 
L 525 -31 
Q 2372 478 2631 2463 
L 1556 2463 
L 1556 2931 
L 4872 2931 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-4348" d="M 5522 4225 
L 3213 4225 
L 3213 3597 
L 4972 3597 
L 4972 1459 
L 1338 1459 
L 1338 3597 
L 2725 3597 
L 2725 5313 
L 3213 5313 
L 3213 4666 
L 5522 4666 
L 5522 4225 
z
M 4513 1900 
L 4513 3156 
L 1825 3156 
L 1825 1900 
L 4513 1900 
z
M 6081 -56 
L 5619 -325 
Q 5188 509 4544 1031 
L 4922 1288 
Q 5672 631 6081 -56 
z
M 1856 1044 
Q 1550 141 763 -453 
L 319 -91 
Q 1059 356 1447 1247 
L 1850 1044 
L 1856 1044 
z
M 4538 -109 
L 4072 -288 
Q 3759 481 3272 997 
L 3681 1197 
Q 4216 653 4538 -109 
z
M 3200 -134 
L 2700 -275 
Q 2519 444 2047 1013 
L 2463 1184 
Q 2925 600 3200 -134 
z
" transform="scale(0.015625)"/>
      </defs>
      <use xlink:href="#us-big-ArialUnicodeMS-490d"/>
      <use xlink:href="#us-big-ArialUnicodeMS-2495" transform="translate(100 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-4348" transform="translate(200 0)"/>
     </g>
    </g>
   </g>
   <g id="us-big-line2d_17">
    <path d="M 74.555082 202.142799 
L 78.753273 204.558873 
L 82.545188 206.049884 
L 86.743379 206.469878 
L 90.806145 207.070829 
L 95.004336 206.231722 
L 99.067102 207.056574 
L 103.265293 206.023442 
L 107.463484 205.694306 
L 111.52625 205.039521 
L 115.724442 204.90104 
L 119.787207 203.914297 
L 123.985399 202.111737 
L 128.18359 197.49908 
L 132.11093 197.267917 
L 136.309121 196.617942 
L 140.371887 196.398516 
L 144.570079 196.810893 
L 148.632844 194.174393 
L 152.831036 193.752067 
L 157.029227 194.450756 
L 161.091993 194.616365 
L 165.290184 193.702775 
L 169.35295 191.201642 
L 173.551141 192.527105 
L 177.749332 191.05043 
L 181.541247 190.53978 
L 185.739438 192.641691 
L 189.802204 193.406314 
L 194.000395 194.004196 
L 198.063161 192.810034 
L 202.261353 189.881001 
L 206.459544 191.73844 
L 210.52231 190.669784 
L 214.720501 191.046973 
L 218.783267 190.180729 
L 222.981458 189.080346 
L 227.179649 185.072579 
L 230.971564 186.321242 
L 235.169755 186.178441 
L 239.232521 185.887734 
L 243.430712 185.903851 
L 247.493478 187.525073 
L 251.69167 189.363625 
L 255.889861 195.785422 
L 259.952627 193.771016 
L 264.150818 189.751617 
L 268.213584 189.930556 
L 272.411775 189.30071 
L 276.609966 189.580227 
L 280.401881 189.778503 
L 284.600072 188.297756 
L 288.662838 188.167768 
L 292.861029 186.855993 
L 296.923795 185.520117 
L 301.121986 184.927208 
L 305.320178 184.82947 
L 309.382944 180.977279 
L 313.581135 179.78242 
L 317.643901 177.434141 
L 321.842092 170.702241 
L 326.040283 172.278048 
L 329.967623 178.038585 
L 334.165815 179.097738 
L 338.228581 176.769577 
L 342.426772 177.169676 
L 346.489538 175.032102 
L 350.687729 165.521969 
L 354.88592 156.175046 
L 358.948686 163.686851 
L 363.146877 167.322934 
L 367.209643 161.288301 
L 371.407834 149.167874 
L 375.606026 146.224025 
L 379.39794 159.436505 
L 383.596132 155.833406 
L 387.658897 157.425521 
L 391.857089 159.717476 
L 395.919855 156.473009 
L 400.118046 150.09722 
L 404.316237 145.605245 
L 408.379003 153.053243 
L 412.577194 152.597549 
L 416.63996 138.761249 
L 420.838151 124.811294 
L 425.036343 116.750093 
L 428.828257 120.828157 
L 433.026449 112.469986 
L 437.089214 116.518039 
L 441.287406 124.344657 
L 445.350172 133.171979 
L 449.548363 151.471605 
L 453.746554 147.633235 
L 457.80932 147.895879 
L 462.007511 137.237392 
L 466.070277 131.535358 
L 470.268468 127.185387 
L 474.46666 143.379463 
L 478.258574 142.497104 
L 482.456766 144.978535 
L 486.519531 146.302541 
L 490.717723 151.790948 
L 494.780488 155.007166 
L 498.97868 145.823896 
L 503.176871 144.86363 
L 507.239637 145.82237 
L 511.437828 152.234092 
L 515.500594 157.629641 
L 519.698785 137.465381 
L 523.896977 133.211933 
L 527.824317 126.492508 
L 532.022508 116.799549 
L 536.085274 128.925435 
L 540.283465 137.898759 
L 544.346231 123.983438 
L 548.544422 119.311137 
L 552.742614 113.228999 
L 556.805379 107.705598 
L 561.003571 105.864375 
L 565.066336 117.66432 
L 569.264528 85.974206 
" clip-path="url(#us-big-p1eaef6550d)" style="fill: none; stroke: #006f73; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="us-big-line2d_18">
    <path d="M 49.819609 202.142799 
L 594 202.142799 
" clip-path="url(#us-big-p1eaef6550d)" style="fill: none; stroke: #656565; stroke-width: 0.7; stroke-linecap: square"/>
   </g>
   <g id="us-big-patch_3">
    <path d="M 49.819609 213.125661 
L 49.819609 79.919375 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="us-big-patch_4">
    <path d="M 49.819609 213.125661 
L 594 213.125661 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="us-big-text_5">
    <!-- 先看增量：新组合相对“盈利 + 动量”的累计收益差 -->
    <g transform="translate(49.819609 73.919375) scale(0.12 -0.12)">
     <defs>
      <path id="us-big-ArialUnicodeMS-23d7" d="M 5978 1050 
Q 5834 238 5676 45 
Q 5519 -147 5275 -147 
L 4191 -147 
Q 3884 -100 3746 106 
Q 3609 313 3609 453 
L 3609 2388 
L 2956 2388 
Q 2872 1259 2420 645 
Q 1969 31 878 -428 
L 569 -19 
Q 1584 422 2020 987 
Q 2456 1553 2456 2388 
L 850 2388 
L 850 2853 
L 3091 2853 
L 3091 3803 
L 1919 3803 
Q 1684 3388 1281 2938 
L 863 3206 
Q 1656 4019 1778 5025 
L 2247 4903 
Q 2231 4741 2100 4269 
L 3091 4269 
L 3091 5363 
L 3578 5369 
L 3578 4269 
L 5253 4269 
L 5253 3803 
L 3603 3803 
L 3603 2853 
L 5759 2853 
L 5759 2388 
L 4097 2388 
L 4097 563 
Q 4097 319 4300 319 
L 5228 319 
Q 5306 338 5370 466 
Q 5434 594 5569 1197 
L 5978 1050 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-499a" d="M 5838 3041 
L 2713 3041 
L 2484 2753 
L 5044 2753 
L 5044 -403 
L 4556 -403 
L 4556 -63 
L 2247 -63 
L 2247 -428 
L 1759 -428 
L 1759 2028 
Q 1181 1575 794 1350 
L 453 1759 
Q 1453 2284 2069 3041 
L 703 3041 
L 703 3475 
L 2381 3475 
Q 2466 3591 2547 3803 
L 1241 3803 
L 1241 4238 
L 2719 4238 
Q 2769 4369 2791 4481 
Q 1438 4403 1119 4403 
L 903 4856 
Q 3616 4878 5141 5234 
L 5350 4856 
Q 4363 4597 3297 4519 
Q 3259 4334 3213 4238 
L 5197 4238 
L 5197 3803 
L 3091 3803 
Q 3025 3591 2963 3475 
L 5838 3475 
L 5838 3041 
z
M 4556 1978 
L 4556 2284 
L 2247 2284 
L 2247 1978 
L 4556 1978 
z
M 4556 1216 
L 4556 1544 
L 2247 1544 
L 2247 1216 
L 4556 1216 
z
M 4556 409 
L 4556 781 
L 2247 781 
L 2247 409 
L 4556 409 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-2b2d" d="M 6150 4122 
L 5806 3738 
L 5538 3916 
L 5538 2328 
L 2613 2328 
L 2613 4006 
Q 2384 3853 2234 3763 
L 1875 4141 
Q 2216 4300 2650 4664 
Q 3084 5028 3250 5313 
L 3653 5019 
Q 3500 4719 2994 4294 
L 5063 4294 
Q 4538 4741 4347 5013 
L 4756 5313 
Q 5306 4622 6150 4122 
z
M 5050 2797 
L 5050 3828 
L 4294 3828 
L 4294 2797 
L 5050 2797 
z
M 5044 3494 
Q 4969 3178 4684 2828 
L 4325 3091 
Q 4597 3397 4653 3675 
L 5044 3494 
z
M 3841 2797 
L 3841 3828 
L 3097 3828 
L 3097 2797 
L 3841 2797 
z
M 3816 3053 
L 3431 2869 
Q 3338 3281 3122 3541 
L 3519 3731 
Q 3731 3534 3816 3053 
z
M 2503 1319 
L 672 647 
L 331 1081 
Q 822 1194 1259 1350 
L 1259 3103 
L 544 3103 
L 544 3572 
L 1259 3572 
L 1259 5141 
L 1747 5141 
L 1747 3572 
L 2456 3572 
L 2456 3103 
L 1747 3103 
L 1747 1538 
L 2503 1806 
L 2503 1319 
z
M 5344 -397 
L 4856 -397 
L 4856 -31 
L 3334 -31 
L 3334 -397 
L 2847 -397 
L 2847 2169 
L 5344 2169 
L 5344 -397 
z
M 4856 1325 
L 4856 1703 
L 3334 1703 
L 3334 1325 
L 4856 1325 
z
M 4856 434 
L 4856 856 
L 3334 856 
L 3334 434 
L 4856 434 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-645e" d="M 5056 3378 
L 1313 3378 
L 1313 5050 
L 5056 5050 
L 5056 3378 
z
M 4569 4403 
L 4569 4609 
L 1797 4609 
L 1797 4403 
L 4569 4403 
z
M 4569 3794 
L 4569 4031 
L 1797 4031 
L 1797 3794 
L 4569 3794 
z
M 5797 2816 
L 581 2816 
L 581 3231 
L 5797 3231 
L 5797 2816 
z
M 6059 -191 
L 341 -191 
L 341 275 
L 2950 275 
L 2950 459 
L 897 459 
L 897 878 
L 2950 878 
L 2950 1044 
L 1125 1044 
L 1125 2669 
L 5269 2669 
L 5269 1044 
L 3438 1044 
L 3438 878 
L 5509 878 
L 5509 459 
L 3438 459 
L 3438 275 
L 6059 275 
L 6059 -191 
z
M 4781 2053 
L 4781 2253 
L 3438 2253 
L 3438 2053 
L 4781 2053 
z
M 2950 2053 
L 2950 2253 
L 1613 2253 
L 1613 2053 
L 2950 2053 
z
M 4781 1459 
L 4781 1697 
L 3438 1697 
L 3438 1459 
L 4781 1459 
z
M 2950 1459 
L 2950 1697 
L 1613 1697 
L 1613 1459 
L 2950 1459 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-19f6" d="M 3516 2675 
L 2875 2675 
L 2875 3316 
L 3516 3316 
L 3516 2675 
z
M 3516 0 
L 2875 0 
L 2875 641 
L 3516 641 
L 3516 0 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-383f" d="M 6041 2938 
L 5300 2938 
L 5300 -397 
L 4813 -397 
L 4813 2938 
L 4109 2938 
L 4109 2216 
Q 4109 700 3334 -359 
L 2906 -72 
Q 3622 853 3622 2456 
L 3622 4709 
Q 4644 4825 5544 5313 
L 5850 4916 
Q 5141 4503 4109 4319 
L 4109 3406 
L 6041 3406 
L 6041 2938 
z
M 3353 4184 
L 525 4184 
L 525 4653 
L 1716 4653 
L 1716 5281 
L 2222 5281 
L 2222 4653 
L 3353 4653 
L 3353 4184 
z
M 3406 2719 
L 2203 2719 
L 2203 2144 
L 3250 2144 
L 3250 1678 
L 2203 1678 
L 2203 1428 
L 2456 1619 
Q 2981 1281 3309 744 
L 2950 416 
Q 2672 931 2203 1281 
L 2203 -397 
L 1716 -397 
L 1716 1253 
Q 1316 625 703 178 
L 347 550 
Q 1003 959 1409 1678 
L 628 1678 
L 628 2144 
L 1716 2144 
L 1716 2719 
L 453 2719 
L 453 3188 
L 1325 3188 
Q 1147 3659 884 3975 
L 1306 4147 
Q 1631 3813 1806 3188 
L 2228 3188 
Q 2422 3559 2584 4147 
L 3047 3969 
Q 2906 3544 2719 3188 
L 3406 3188 
L 3406 2719 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-5153" d="M 2509 1619 
Q 853 1231 622 1147 
L 391 1575 
Q 1022 2209 1306 2625 
L 1294 2638 
Q 1284 2631 1023 2561 
Q 763 2491 609 2438 
L 366 2881 
Q 853 3669 1441 5166 
L 1875 4966 
Q 1300 3650 947 3022 
L 1619 3163 
Q 1797 3416 2047 3922 
L 2503 3719 
Q 1863 2416 1153 1772 
L 1166 1759 
L 2509 2053 
L 2509 1619 
z
M 5919 -91 
L 2150 -91 
L 2150 378 
L 2881 378 
L 2881 4941 
L 5184 4941 
L 5184 378 
L 5919 378 
L 5919 -91 
z
M 4697 3469 
L 4697 4475 
L 3366 4475 
L 3366 3469 
L 4697 3469 
z
M 4697 1972 
L 4697 3028 
L 3366 3028 
L 3366 1972 
L 4697 1972 
z
M 4697 378 
L 4697 1528 
L 3366 1528 
L 3366 378 
L 4697 378 
z
M 2650 691 
L 647 19 
L 409 459 
Q 2306 1044 2650 1172 
L 2650 691 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-2697" d="M 6119 2925 
L 5797 2497 
Q 5525 2603 5015 2934 
Q 4506 3266 4200 3555 
Q 3894 3844 3200 4659 
Q 2319 3578 603 2419 
L 256 2803 
Q 2228 4103 3175 5497 
L 3647 5178 
L 3450 4978 
Q 3994 4306 4803 3698 
Q 5613 3091 6119 2925 
z
M 4691 2597 
L 1638 2597 
L 1638 3084 
L 4691 3084 
L 4691 2597 
z
M 5063 -434 
L 4556 -434 
L 4556 -38 
L 1838 -38 
L 1838 -469 
L 1331 -469 
L 1331 1906 
L 5063 1906 
L 5063 -434 
z
M 4556 447 
L 4556 1441 
L 1838 1441 
L 1838 447 
L 4556 447 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-4987" d="M 3009 1791 
L 2566 1503 
Q 2322 1975 2003 2406 
L 2003 -416 
L 1509 -416 
L 1509 2094 
Q 1313 1497 659 678 
L 275 972 
Q 1053 1969 1459 3603 
L 519 3603 
L 519 4072 
L 1516 4072 
L 1516 5300 
L 2003 5300 
L 2003 4072 
L 2881 4072 
L 2881 3603 
L 2003 3603 
L 2003 2900 
L 2131 2975 
Q 2681 2434 3009 1791 
z
M 5691 -416 
L 5178 -416 
L 5178 38 
L 3659 38 
L 3659 -416 
L 3150 -416 
L 3150 4966 
L 5691 4966 
L 5691 -416 
z
M 5178 3547 
L 5178 4500 
L 3659 4500 
L 3659 3547 
L 5178 3547 
z
M 5178 2059 
L 5178 3078 
L 3659 3078 
L 3659 2059 
L 5178 2059 
z
M 5178 506 
L 5178 1594 
L 3659 1594 
L 3659 506 
L 5178 506 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-2e88" d="M 5856 3616 
L 5247 3616 
L 5247 38 
Q 5206 -163 5042 -273 
Q 4878 -384 4806 -384 
L 4103 -384 
L 3944 103 
Q 4438 63 4678 63 
Q 4716 63 4763 134 
L 4763 3616 
L 2988 3616 
L 2988 4084 
L 4763 4084 
L 4763 5306 
L 5247 5306 
L 5247 4084 
L 5856 4084 
L 5856 3616 
z
M 3175 366 
L 2694 153 
Q 2422 1059 2100 1538 
Q 1609 353 525 -384 
L 153 -13 
Q 1288 719 1813 1984 
Q 1306 2706 628 3256 
L 984 3541 
Q 1794 2828 2009 2497 
Q 2341 3403 2381 4116 
L 359 4116 
L 359 4556 
L 2869 4556 
Q 2844 3303 2328 2028 
Q 2866 1222 3175 366 
z
M 4441 1453 
L 3988 1178 
Q 3663 2072 3091 2700 
L 3444 2950 
Q 4084 2334 4441 1453 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-caf" d="M 1900 4441 
Q 1559 4303 1556 3816 
L 1850 3816 
L 1850 3163 
L 1247 3163 
L 1247 3675 
Q 1247 3897 1273 4061 
Q 1300 4225 1412 4389 
Q 1525 4553 1759 4659 
L 1900 4441 
z
M 928 4441 
Q 588 4303 581 3816 
L 878 3816 
L 878 3163 
L 275 3163 
L 275 3675 
Q 275 3897 301 4061 
Q 328 4225 439 4389 
Q 550 4553 788 4659 
L 928 4441 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-4957" d="M 5650 4178 
Q 5625 2825 5476 2414 
Q 5328 2003 4813 2003 
Q 4644 2003 4422 2041 
L 4306 2534 
Q 4731 2466 4838 2466 
Q 5063 2466 5088 2834 
L 5153 3713 
L 4488 3713 
L 4366 3413 
L 4197 3463 
Q 4066 3006 3738 2625 
Q 3875 2547 4306 2209 
L 3969 1831 
Q 3641 2138 3372 2291 
Q 2800 1913 2047 1778 
L 1759 2228 
Q 2581 2353 2888 2547 
Q 2634 2678 2106 2725 
L 2419 3122 
Q 2784 3097 3322 2859 
Q 3541 3078 3616 3272 
L 2322 3272 
L 2322 3738 
L 3956 3738 
L 4225 4531 
L 2375 4531 
Q 2306 3400 1945 2736 
Q 1584 2072 813 1563 
L 416 1947 
Q 1184 2388 1523 2988 
Q 1863 3588 1869 4531 
L 909 4531 
L 909 5019 
L 4813 5019 
Q 4763 4691 4609 4178 
L 5650 4178 
z
M 6094 -244 
L 378 -244 
L 378 225 
L 1106 225 
L 1106 1656 
L 5381 1656 
L 5381 225 
L 6094 225 
L 6094 -244 
z
M 4897 225 
L 4897 1191 
L 4128 1191 
L 4128 225 
L 4897 225 
z
M 3641 225 
L 3641 1191 
L 2859 1191 
L 2859 225 
L 3641 225 
z
M 2375 225 
L 2375 1191 
L 1594 1191 
L 1594 225 
L 2375 225 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-24b8" d="M 5888 153 
Q 5888 3 5755 -178 
Q 5622 -359 5309 -359 
L 4513 -353 
L 4359 172 
L 5228 134 
Q 5381 172 5381 288 
L 5381 5288 
L 5888 5288 
L 5888 153 
z
M 3950 1259 
L 3525 909 
Q 3119 1706 2559 2169 
L 2559 -428 
L 2075 -428 
L 2075 2144 
Q 1766 1428 794 525 
L 366 831 
Q 1484 1806 2003 3097 
L 622 3097 
L 622 3566 
L 2053 3566 
L 2053 4397 
Q 1469 4281 813 4281 
L 563 4763 
Q 2453 4819 3641 5209 
L 3928 4800 
Q 3109 4544 2541 4453 
L 2541 3566 
L 3891 3566 
L 3891 3097 
L 2541 3097 
L 2541 2547 
L 2706 2669 
Q 3581 1938 3950 1259 
z
M 4647 794 
L 4159 794 
L 4159 4531 
L 4647 4531 
L 4647 794 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-3" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-e" d="M 3384 1997 
L 2131 1997 
L 2131 744 
L 1606 744 
L 1606 1997 
L 353 1997 
L 353 2522 
L 1606 2522 
L 1606 3775 
L 2131 3775 
L 2131 2522 
L 3384 2522 
L 3384 1997 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-2537" d="M 5678 3834 
Q 5613 2631 5508 1595 
Q 5403 559 5328 262 
Q 5253 -34 5048 -161 
Q 4844 -288 4591 -288 
Q 4416 -288 4097 -256 
Q 4016 25 3944 238 
Q 4550 172 4644 172 
Q 4703 172 4812 456 
Q 4922 741 5023 1741 
Q 5125 2741 5159 3391 
L 4359 3391 
Q 4366 1738 3883 889 
Q 3400 41 2528 -384 
L 2156 25 
Q 2716 300 3009 634 
Q 2913 850 2719 1075 
Q 1478 731 763 475 
L 428 959 
Q 678 1172 1014 1786 
Q 1350 2400 1503 2906 
L 353 2906 
L 353 3372 
L 3144 3372 
L 3144 2906 
L 2041 2906 
Q 1500 1597 1125 1125 
L 1141 1113 
L 2444 1484 
Q 2397 1556 2125 1797 
L 2478 2047 
Q 3131 1475 3359 997 
Q 3528 1178 3697 1742 
Q 3866 2306 3866 2888 
L 3866 3391 
L 3194 3391 
L 3194 3834 
L 3866 3834 
L 3866 5319 
L 4353 5325 
L 4353 3834 
L 5678 3834 
z
M 2881 4219 
L 603 4219 
L 603 4659 
L 2881 4659 
L 2881 4219 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-cb0" d="M 1856 4072 
Q 1856 3847 1829 3683 
Q 1803 3519 1692 3355 
Q 1581 3191 1344 3084 
L 1203 3303 
Q 1544 3441 1550 3928 
L 1253 3928 
L 1253 4581 
L 1856 4581 
L 1856 4072 
z
M 884 4072 
Q 884 3847 857 3683 
Q 831 3519 718 3355 
Q 606 3191 372 3084 
L 231 3303 
Q 572 3441 575 3928 
L 281 3928 
L 281 4581 
L 884 4581 
L 884 4072 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-4913" d="M 5644 4281 
Q 5619 1694 5395 673 
Q 5172 -347 4606 -347 
Q 4350 -347 3609 -134 
L 3525 403 
Q 4247 134 4531 134 
Q 4806 134 4976 1142 
Q 5147 2150 5159 3841 
L 3794 3841 
Q 3550 3166 3053 2497 
L 2719 2713 
L 2719 -147 
L 2216 -147 
L 2216 269 
L 1153 269 
L 1153 -250 
L 647 -250 
L 647 4184 
L 1234 4184 
Q 1494 4644 1625 5313 
L 2088 5125 
Q 1903 4444 1741 4184 
L 2719 4184 
L 2719 2881 
Q 3431 3888 3681 5363 
L 4191 5247 
Q 4106 4869 3916 4281 
L 5644 4281 
z
M 2216 2484 
L 2216 3719 
L 1153 3719 
L 1153 2484 
L 2216 2484 
z
M 2216 738 
L 2216 2016 
L 1153 2016 
L 1153 738 
L 2216 738 
z
M 4775 1369 
L 4313 1166 
Q 4034 1925 3444 2669 
L 3841 2931 
Q 4484 2191 4775 1369 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-4fbe" d="M 5997 1025 
L 5581 691 
Q 5316 1013 5197 1119 
L 3431 1056 
L 3431 -403 
L 2944 -403 
L 2944 1063 
L 781 1006 
L 616 1472 
L 1759 1472 
L 2131 1672 
Q 1350 2422 997 2625 
L 1416 2925 
L 1819 2619 
Q 2541 3038 2572 3059 
L 1031 3059 
L 1031 5172 
L 5369 5172 
L 5369 3059 
L 3116 3059 
L 3256 2963 
Q 3006 2791 2163 2303 
Q 2316 2169 2559 1919 
Q 3859 2628 4409 3028 
L 4838 2706 
Q 3569 1909 2619 1484 
L 4750 1528 
L 4116 1900 
L 4513 2194 
Q 5428 1738 5997 1025 
z
M 4884 4341 
L 4884 4703 
L 3450 4703 
L 3450 4341 
L 4884 4341 
z
M 2969 4703 
L 1516 4703 
L 1516 4341 
L 2963 4341 
L 2969 4703 
z
M 4884 3525 
L 4884 3897 
L 3450 3897 
L 3450 3525 
L 4884 3525 
z
M 2969 3525 
L 2969 3897 
L 1516 3897 
L 1516 3525 
L 2969 3525 
z
M 6034 244 
L 5778 -159 
Q 4997 381 3794 588 
L 4078 984 
Q 5275 753 6034 244 
z
M 2650 622 
Q 1806 31 678 -122 
L 325 306 
Q 1581 431 2322 947 
L 2650 622 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-5e30" d="M 2075 4422 
L 1672 4116 
Q 1431 4616 856 5081 
L 1203 5375 
Q 1741 5006 2075 4422 
z
M 5997 2956 
L 4506 2956 
L 4506 -422 
L 4019 -422 
L 4019 2956 
L 2528 2956 
L 2528 3425 
L 4019 3425 
L 4019 5325 
L 4506 5325 
L 4506 3425 
L 5997 3425 
L 5997 2956 
z
M 2853 384 
L 1600 -306 
L 1313 103 
Q 1409 203 1409 372 
L 1409 3116 
L 475 3116 
L 475 3584 
L 1894 3584 
L 1894 391 
L 2853 916 
L 2853 384 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-37c5" d="M 6088 -13 
L 5728 -391 
Q 5000 -66 4391 716 
Q 3878 91 2938 -447 
L 2584 -116 
L 2584 -434 
L 2100 -434 
L 2100 1313 
L 647 825 
L 428 1247 
Q 509 1284 621 1318 
Q 734 1353 763 1369 
L 763 4641 
L 1247 4641 
L 1247 1528 
L 2100 1838 
L 2100 5247 
L 2584 5247 
L 2584 -56 
Q 3647 494 4147 1147 
Q 3669 1850 3463 2719 
Q 3253 2297 2975 1925 
L 2613 2272 
Q 3469 3409 3525 5313 
L 4006 5159 
Q 4006 4703 3916 4166 
L 5813 4166 
L 5813 3700 
L 5422 3700 
Q 5363 2247 4697 1147 
Q 5272 319 6088 -13 
z
M 4947 3700 
L 3816 3700 
L 3763 3500 
Q 3975 2297 4416 1588 
Q 4878 2472 4947 3700 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-4959" d="M 5191 5063 
Q 4775 4500 4072 4000 
L 3706 4341 
Q 4428 4822 4788 5375 
L 5191 5063 
z
M 2675 4306 
L 2259 3994 
Q 1838 4713 1197 5075 
L 1631 5350 
Q 2178 5041 2675 4306 
z
M 5869 3506 
L 531 3506 
L 531 3975 
L 5869 3975 
L 5869 3506 
z
M 6144 2150 
L 5831 1753 
Q 5544 1859 5209 2034 
L 5209 353 
L 5984 353 
L 5984 -116 
L 403 -116 
L 403 353 
L 1203 353 
L 1203 2113 
Q 906 1969 609 1875 
L 288 2284 
Q 1559 2691 2322 3463 
L 2688 3116 
Q 2044 2509 1313 2150 
L 5006 2150 
Q 4272 2588 3738 3169 
L 4128 3481 
Q 4856 2681 6144 2150 
z
M 4691 366 
L 4691 1709 
L 4044 1709 
L 4044 366 
L 4691 366 
z
M 3547 366 
L 3547 1709 
L 2847 1709 
L 2847 366 
L 3547 366 
z
M 2350 353 
L 2350 1684 
L 1703 1684 
L 1703 353 
L 2350 353 
z
" transform="scale(0.015625)"/>
      <path id="us-big-ArialUnicodeMS-307d" d="M 5991 -122 
L 1209 -122 
L 1209 347 
L 3284 347 
L 3284 1178 
L 1863 1178 
Q 1419 619 588 159 
L 300 581 
Q 1531 1266 1888 2169 
L 697 2169 
L 697 2631 
L 2981 2631 
L 2981 3188 
L 1319 3188 
L 1319 3634 
L 2981 3634 
L 2981 4122 
L 947 4122 
L 947 4581 
L 2291 4581 
Q 2069 4831 1563 5088 
L 2069 5350 
Q 2581 5003 2822 4588 
L 3647 4588 
Q 4069 4869 4313 5375 
L 4781 5147 
Q 4534 4741 4347 4603 
L 4347 4588 
L 5581 4588 
L 5575 4122 
L 3463 4122 
L 3463 3634 
L 5209 3634 
L 5209 3188 
L 3463 3188 
L 3463 2631 
L 5838 2631 
L 5838 2169 
L 2413 2169 
Q 2375 2000 2150 1644 
L 5497 1644 
L 5497 1178 
L 3763 1178 
L 3763 347 
L 5991 347 
L 5991 -122 
z
" transform="scale(0.015625)"/>
     </defs>
     <use xlink:href="#us-big-ArialUnicodeMS-23d7"/>
     <use xlink:href="#us-big-ArialUnicodeMS-499a" transform="translate(100 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-2b2d" transform="translate(200 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-645e" transform="translate(300 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-19f6" transform="translate(400 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-383f" transform="translate(500 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-5153" transform="translate(600 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-2697" transform="translate(700 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-4987" transform="translate(800 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-2e88" transform="translate(900 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-caf" transform="translate(1000 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-4957" transform="translate(1033.296875 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-24b8" transform="translate(1133.296875 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-3" transform="translate(1233.296875 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-e" transform="translate(1261.078125 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-3" transform="translate(1319.484375 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-2537" transform="translate(1347.265625 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-645e" transform="translate(1447.265625 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-cb0" transform="translate(1547.265625 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-4913" transform="translate(1580.5625 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-4fbe" transform="translate(1680.5625 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-5e30" transform="translate(1780.5625 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-37c5" transform="translate(1880.5625 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-4959" transform="translate(1980.5625 0)"/>
     <use xlink:href="#us-big-ArialUnicodeMS-307d" transform="translate(2080.5625 0)"/>
    </g>
   </g>
  </g>
  <g id="us-big-axes_2">
   <g id="us-big-patch_5">
    <path d="M 49.819609 400.593832 
L 594 400.593832 
L 594 227.425661 
L 49.819609 227.425661 
z
" style="fill: #fbfaf7"/>
   </g>
   <g id="us-big-matplotlib.axis_3">
    <g id="us-big-xtick_6">
     <g id="us-big-line2d_19">
      <path d="M 124.120824 400.593832 
L 124.120824 227.425661 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_20">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="124.120824" y="400.593832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-big-xtick_7">
     <g id="us-big-line2d_21">
      <path d="M 223.116884 400.593832 
L 223.116884 227.425661 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_22">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="223.116884" y="400.593832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-big-xtick_8">
     <g id="us-big-line2d_23">
      <path d="M 321.977517 400.593832 
L 321.977517 227.425661 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_24">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="321.977517" y="400.593832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-big-xtick_9">
     <g id="us-big-line2d_25">
      <path d="M 420.973577 400.593832 
L 420.973577 227.425661 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_26">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="420.973577" y="400.593832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-big-xtick_10">
     <g id="us-big-line2d_27">
      <path d="M 519.834211 400.593832 
L 519.834211 227.425661 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_28">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="519.834211" y="400.593832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
   </g>
   <g id="us-big-matplotlib.axis_4">
    <g id="us-big-ytick_4">
     <g id="us-big-line2d_29">
      <path d="M 49.819609 389.779583 
L 594 389.779583 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_30">
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="389.779583" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_6">
      <!-- 100 -->
      <g transform="translate(26.136797 393.41972) scale(0.1 -0.1)">
       <defs>
        <path id="us-big-ArialUnicodeMS-14" d="M 2400 0 
L 1838 0 
L 1838 3584 
Q 1416 3184 709 2906 
L 709 3450 
Q 1681 3916 2034 4603 
L 2400 4603 
L 2400 0 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-big-ArialUnicodeMS-14"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(111.21875 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-ytick_5">
     <g id="us-big-line2d_31">
      <path d="M 49.819609 350.326196 
L 594 350.326196 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_32">
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="350.326196" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_7">
      <!-- 200 -->
      <g transform="translate(26.136797 353.966332) scale(0.1 -0.1)">
       <use xlink:href="#us-big-ArialUnicodeMS-15"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(111.21875 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-ytick_6">
     <g id="us-big-line2d_33">
      <path d="M 49.819609 310.872808 
L 594 310.872808 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_34">
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="310.872808" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_8">
      <!-- 300 -->
      <g transform="translate(26.136797 314.512945) scale(0.1 -0.1)">
       <defs>
        <path id="us-big-ArialUnicodeMS-16" d="M 2425 2478 
Q 2850 2397 3067 2067 
Q 3284 1738 3284 1350 
Q 3284 725 2829 323 
Q 2375 -78 1741 -78 
Q 1134 -78 740 275 
Q 347 628 281 1209 
L 844 1288 
Q 928 834 1151 609 
Q 1375 384 1741 384 
Q 2134 384 2407 661 
Q 2681 938 2681 1338 
Q 2681 1722 2432 1975 
Q 2184 2228 1784 2228 
Q 1622 2228 1388 2169 
L 1453 2663 
Q 1678 2663 1809 2684 
Q 1941 2706 2103 2790 
Q 2266 2875 2372 3033 
Q 2478 3191 2478 3425 
Q 2478 3766 2251 3953 
Q 2025 4141 1728 4141 
Q 1388 4141 1173 3925 
Q 959 3709 903 3309 
L 341 3413 
Q 450 4009 823 4306 
Q 1197 4603 1716 4603 
Q 2288 4603 2670 4258 
Q 3053 3913 3053 3413 
Q 3053 2772 2425 2491 
L 2425 2478 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-big-ArialUnicodeMS-16"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(111.21875 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-ytick_7">
     <g id="us-big-line2d_35">
      <path d="M 49.819609 271.419421 
L 594 271.419421 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_36">
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="271.419421" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_9">
      <!-- 400 -->
      <g transform="translate(26.136797 275.059558) scale(0.1 -0.1)">
       <use xlink:href="#us-big-ArialUnicodeMS-17"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(111.21875 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-ytick_8">
     <g id="us-big-line2d_37">
      <path d="M 49.819609 231.966034 
L 594 231.966034 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_38">
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="231.966034" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_10">
      <!-- 500 -->
      <g transform="translate(26.136797 235.606171) scale(0.1 -0.1)">
       <defs>
        <path id="us-big-ArialUnicodeMS-18" d="M 1013 2753 
Q 1431 3041 1881 3041 
Q 2453 3041 2878 2636 
Q 3303 2231 3303 1556 
Q 3303 875 2872 398 
Q 2441 -78 1741 -78 
Q 1169 -78 750 245 
Q 331 569 269 1203 
L 856 1247 
Q 928 813 1162 598 
Q 1397 384 1741 384 
Q 2169 384 2434 707 
Q 2700 1031 2700 1503 
Q 2700 1984 2428 2262 
Q 2156 2541 1728 2541 
Q 1188 2541 897 2100 
L 366 2163 
L 813 4519 
L 3084 4519 
L 3084 3975 
L 1259 3975 
L 1013 2753 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-big-ArialUnicodeMS-18"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(111.21875 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-text_11">
     <!-- 初始 100 美元 -->
     <g transform="translate(20.037188 345.129277) rotate(-90) scale(0.1 -0.1)">
      <defs>
       <path id="us-big-ArialUnicodeMS-24ac" d="M 3084 2803 
Q 2794 2372 2497 2125 
Q 2678 2009 2994 1672 
L 2688 1275 
Q 2309 1703 1813 1966 
L 1813 -469 
L 1325 -469 
L 1325 2009 
Q 1272 1969 1011 1748 
Q 750 1528 531 1394 
L 206 1838 
Q 797 2153 1342 2670 
Q 1888 3188 2075 3647 
L 422 3647 
L 422 4116 
L 1344 4116 
L 1344 5259 
L 1831 5259 
L 1831 4116 
L 2619 4116 
L 2619 3700 
Q 2422 3122 1850 2484 
L 2113 2356 
Q 2388 2591 2663 3091 
L 3084 2803 
z
M 5753 4844 
L 5759 2381 
Q 5759 1803 5667 923 
Q 5575 44 5400 -122 
Q 5225 -288 4863 -288 
Q 4578 -288 4050 -172 
L 3928 378 
Q 4728 197 4825 197 
Q 4975 197 5048 305 
Q 5122 413 5190 1295 
Q 5259 2178 5259 2619 
L 5259 4353 
L 4206 4353 
Q 4206 2600 4090 1853 
Q 3975 1106 3633 612 
Q 3291 119 2572 -306 
L 2203 91 
Q 2825 431 3137 842 
Q 3450 1253 3551 1717 
Q 3653 2181 3669 2881 
L 3700 4353 
L 2847 4353 
L 2847 4844 
L 5753 4844 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-2c5a" d="M 6047 2656 
L 5575 2456 
Q 5481 2788 5388 2975 
L 2719 2713 
L 2619 2981 
Q 2503 2059 2216 1331 
Q 2497 1147 2963 709 
L 2650 288 
Q 2131 825 1984 872 
Q 1525 13 709 -475 
L 347 -134 
Q 1250 472 1581 1106 
Q 1181 1356 588 1528 
Q 891 2266 1172 3591 
L 469 3591 
L 469 4056 
L 1253 4056 
Q 1381 4750 1409 5306 
L 1894 5147 
Q 1825 4497 1741 4056 
L 2731 4056 
L 2663 3244 
Q 2938 3244 3041 3272 
Q 3609 4163 4025 5344 
L 4525 5125 
Q 3866 3672 3566 3272 
L 5191 3391 
Q 4928 3825 4603 4116 
L 4997 4353 
Q 5722 3688 6047 2656 
z
M 2234 3591 
L 1656 3591 
Q 1444 2541 1172 1819 
Q 1459 1719 1784 1556 
Q 2078 2272 2234 3591 
z
M 5563 -416 
L 5075 -416 
L 5075 109 
L 3500 109 
L 3500 -416 
L 3016 -416 
L 3016 2328 
L 5563 2328 
L 5563 -416 
z
M 5075 575 
L 5075 1863 
L 3500 1863 
L 3500 575 
L 5075 575 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-521d" d="M 5972 2209 
L 475 2209 
L 475 2675 
L 2950 2675 
L 2950 3219 
L 1281 3219 
L 1281 3688 
L 2950 3688 
L 2950 4153 
L 844 4153 
L 844 4622 
L 2188 4622 
Q 1956 4941 1619 5141 
L 2053 5381 
Q 2441 5166 2784 4622 
L 3616 4622 
Q 4103 5041 4347 5409 
L 4769 5094 
Q 4534 4769 4306 4634 
L 4306 4622 
L 5581 4622 
L 5581 4153 
L 3475 4153 
L 3475 3688 
L 5159 3688 
L 5159 3219 
L 3475 3219 
L 3475 2675 
L 5972 2675 
L 5972 2209 
z
M 6113 56 
L 5813 -391 
Q 3891 -44 3244 1222 
L 3219 1222 
Q 3034 638 2270 191 
Q 1506 -256 550 -372 
L 288 84 
Q 1106 166 1786 481 
Q 2466 797 2688 1234 
L 769 1234 
L 769 1703 
L 2853 1703 
Q 2906 1909 2906 2175 
L 3406 2088 
Q 3394 1859 3353 1703 
L 5650 1703 
L 5650 1234 
L 3763 1234 
Q 4378 356 6113 56 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-23d2" d="M 5141 4422 
L 1394 4422 
L 1394 4909 
L 5141 4909 
L 5141 4422 
z
M 6009 1166 
Q 5822 -122 5203 -122 
L 4306 -122 
Q 3653 -122 3653 691 
L 3653 2847 
L 2834 2847 
Q 2850 1688 2378 917 
Q 1906 147 838 -428 
L 488 56 
Q 1469 550 1892 1181 
Q 2316 1813 2316 2847 
L 850 2847 
L 850 3334 
L 5672 3334 
L 5672 2847 
L 4159 2847 
L 4159 622 
Q 4159 366 4403 366 
L 5159 366 
Q 5241 366 5308 497 
Q 5375 628 5516 1325 
L 6009 1166 
z
" transform="scale(0.015625)"/>
      </defs>
      <use xlink:href="#us-big-ArialUnicodeMS-24ac"/>
      <use xlink:href="#us-big-ArialUnicodeMS-2c5a" transform="translate(100 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-3" transform="translate(200 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-14" transform="translate(227.78125 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(283.390625 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(339 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-3" transform="translate(394.609375 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-521d" transform="translate(422.390625 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-23d2" transform="translate(522.390625 0)"/>
     </g>
    </g>
   </g>
   <g id="us-big-line2d_39">
    <path d="M 74.555082 389.779583 
L 78.753273 390.796829 
L 82.545188 388.795597 
L 86.743379 389.363681 
L 90.806145 389.612183 
L 95.004336 388.650202 
L 99.067102 389.374189 
L 103.265293 388.235278 
L 107.463484 390.697214 
L 111.52625 391.54673 
L 115.724442 388.722555 
L 119.787207 388.508651 
L 123.985399 388.841088 
L 128.18359 390.354325 
L 132.11093 390.441393 
L 136.309121 387.830651 
L 140.371887 388.109207 
L 144.570079 387.487115 
L 148.632844 386.523765 
L 152.831036 384.877618 
L 157.029227 385.314204 
L 161.091993 385.175907 
L 165.290184 385.985613 
L 169.35295 384.417714 
L 173.551141 384.067032 
L 177.749332 382.915641 
L 181.541247 381.342175 
L 185.739438 381.662481 
L 189.802204 381.212877 
L 194.000395 380.151217 
L 198.063161 379.987284 
L 202.261353 378.304374 
L 206.459544 378.036585 
L 210.52231 376.858078 
L 214.720501 375.332078 
L 218.783267 373.113769 
L 222.981458 372.326813 
L 227.179649 367.747392 
L 230.971564 369.425237 
L 235.169755 370.885369 
L 239.232521 370.809816 
L 243.430712 368.950108 
L 247.493478 369.066162 
L 251.69167 367.773661 
L 255.889861 365.417788 
L 259.952627 364.518147 
L 264.150818 369.142736 
L 268.213584 368.656159 
L 272.411775 373.550082 
L 276.609966 369.589383 
L 280.401881 367.363878 
L 284.600072 365.627187 
L 288.662838 363.809529 
L 292.861029 367.197523 
L 296.923795 362.900844 
L 301.121986 361.973574 
L 305.320178 361.897206 
L 309.382944 360.922442 
L 313.581135 359.559916 
L 317.643901 357.142686 
L 321.842092 353.911983 
L 326.040283 352.89822 
L 329.967623 359.394601 
L 334.165815 366.349909 
L 338.228581 358.234436 
L 342.426772 354.714495 
L 346.489538 351.544131 
L 350.687729 345.086372 
L 354.88592 336.08928 
L 358.948686 340.855791 
L 363.146877 344.349177 
L 367.209643 335.338086 
L 371.407834 329.588382 
L 375.606026 329.415049 
L 379.39794 331.3444 
L 383.596132 329.297851 
L 387.658897 324.884884 
L 391.857089 326.125267 
L 395.919855 321.932051 
L 400.118046 319.6162 
L 404.316237 315.293354 
L 408.379003 321.150757 
L 412.577194 313.99448 
L 416.63996 312.806143 
L 420.838151 307.515572 
L 425.036343 313.086957 
L 428.828257 315.846244 
L 433.026449 310.225474 
L 437.089214 320.168268 
L 441.287406 322.382193 
L 445.350172 330.565076 
L 449.548363 326.190972 
L 453.746554 328.429476 
L 457.80932 335.886644 
L 462.007511 325.588251 
L 466.070277 320.101593 
L 470.268468 323.621219 
L 474.46666 323.895312 
L 478.258574 326.61724 
L 482.456766 324.504166 
L 486.519531 323.200343 
L 490.717723 323.538732 
L 494.780488 317.243813 
L 498.97868 313.095693 
L 503.176871 313.96618 
L 507.239637 319.553553 
L 511.437828 321.967023 
L 515.500594 313.420513 
L 519.698785 305.03683 
L 523.896977 301.628853 
L 527.824317 293.705416 
L 532.022508 288.527085 
L 536.085274 296.555702 
L 540.283465 291.791036 
L 544.346231 283.161907 
L 548.544422 282.25378 
L 552.742614 277.611048 
L 556.805379 273.506102 
L 561.003571 274.390108 
L 565.066336 268.718508 
L 569.264528 266.002239 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #006f73; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="us-big-line2d_40">
    <path d="M 74.555082 389.779583 
L 78.753273 390.363444 
L 82.545188 388.09476 
L 86.743379 388.587507 
L 90.806145 388.728212 
L 95.004336 387.916748 
L 99.067102 388.492776 
L 103.265293 387.539184 
L 107.463484 390.060159 
L 111.52625 391.027128 
L 115.724442 388.227793 
L 119.787207 388.190887 
L 123.985399 388.846659 
L 128.18359 391.187297 
L 132.11093 391.31583 
L 136.309121 388.821678 
L 140.371887 389.139593 
L 144.570079 388.443531 
L 148.632844 387.953106 
L 152.831036 386.382713 
L 157.029227 386.693972 
L 161.091993 386.525968 
L 165.290184 387.49955 
L 169.35295 386.380295 
L 173.551141 385.791856 
L 177.749332 384.905345 
L 181.541247 383.423478 
L 185.739438 383.366752 
L 189.802204 382.779992 
L 194.000395 381.611087 
L 198.063161 381.661358 
L 202.261353 380.503846 
L 206.459544 379.902877 
L 210.52231 378.916061 
L 214.720501 377.322402 
L 218.783267 375.259477 
L 222.981458 374.669903 
L 227.179649 370.80938 
L 230.971564 372.263244 
L 235.169755 373.748992 
L 239.232521 373.725584 
L 243.430712 371.862985 
L 247.493478 371.688231 
L 251.69167 370.065938 
L 255.889861 366.558149 
L 259.952627 366.019843 
L 264.150818 371.365416 
L 268.213584 370.846742 
L 272.411775 375.853644 
L 276.609966 371.842806 
L 280.401881 369.581735 
L 284.600072 368.110655 
L 288.662838 366.316314 
L 292.861029 369.939608 
L 296.923795 365.882553 
L 301.121986 365.061637 
L 305.320178 365.002801 
L 309.382944 364.719027 
L 313.581135 363.57083 
L 317.643901 361.574825 
L 321.842092 359.551663 
L 326.040283 358.255239 
L 329.967623 363.718317 
L 334.165815 370.483639 
L 338.228581 362.785782 
L 342.426772 359.194073 
L 346.489538 356.407138 
L 350.687729 351.655268 
L 354.88592 344.33479 
L 358.948686 347.753864 
L 363.146877 350.595024 
L 367.209643 342.666402 
L 371.407834 339.09081 
L 375.606026 339.445533 
L 379.39794 339.004883 
L 383.596132 337.604643 
L 387.658897 332.906089 
L 391.857089 333.735351 
L 395.919855 330.124114 
L 400.118046 328.951926 
L 404.316237 325.434833 
L 408.379003 329.956243 
L 412.577194 322.881707 
L 416.63996 324.17527 
L 420.838151 321.386985 
L 425.036343 328.404356 
L 428.828257 330.432137 
L 433.026449 326.310621 
L 437.089214 335.527293 
L 441.287406 336.33731 
L 445.350172 342.936783 
L 449.548363 335.280166 
L 453.746554 338.207182 
L 457.80932 345.617238 
L 462.007511 337.230722 
L 466.070277 332.766871 
L 470.268468 337.066778 
L 474.46666 334.436043 
L 478.258574 337.316244 
L 482.456766 334.758061 
L 486.519531 333.216744 
L 490.717723 332.570644 
L 494.780488 325.698812 
L 498.97868 323.197951 
L 503.176871 324.240686 
L 507.239637 329.656084 
L 511.437828 330.919446 
L 515.500594 321.405104 
L 519.698785 316.638404 
L 523.896977 313.993394 
L 527.824317 307.275261 
L 532.022508 303.835613 
L 536.085274 309.689137 
L 540.283465 303.314873 
L 544.346231 297.181818 
L 548.544422 297.111789 
L 552.742614 293.560047 
L 556.805379 290.445866 
L 561.003571 291.660143 
L 565.066336 283.871917 
L 569.264528 286.840093 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #df8f32; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="us-big-line2d_41">
    <path d="M 74.555082 389.779583 
L 78.753273 391.253838 
L 82.545188 389.402165 
L 86.743379 390.28386 
L 90.806145 390.222047 
L 95.004336 389.585467 
L 99.067102 390.63902 
L 103.265293 389.808749 
L 107.463484 391.999553 
L 111.52625 392.722551 
L 115.724442 389.666301 
L 119.787207 389.55769 
L 123.985399 389.992809 
L 128.18359 390.780084 
L 132.11093 390.15634 
L 136.309121 387.245248 
L 140.371887 387.581948 
L 144.570079 387.218709 
L 148.632844 386.304059 
L 152.831036 384.311943 
L 157.029227 384.703429 
L 161.091993 384.587074 
L 165.290184 385.05023 
L 169.35295 382.540651 
L 173.551141 382.376013 
L 177.749332 380.87317 
L 181.541247 378.921659 
L 185.739438 379.394032 
L 189.802204 378.920662 
L 194.000395 378.073151 
L 198.063161 377.872195 
L 202.261353 376.184223 
L 206.459544 376.331964 
L 210.52231 374.751969 
L 214.720501 373.881635 
L 218.783267 371.170638 
L 222.981458 369.743001 
L 227.179649 365.212424 
L 230.971564 367.560057 
L 235.169755 368.794194 
L 239.232521 369.076261 
L 243.430712 367.556402 
L 247.493478 367.576509 
L 251.69167 366.000755 
L 255.889861 365.866955 
L 259.952627 364.530376 
L 264.150818 367.766411 
L 268.213584 366.728672 
L 272.411775 371.502 
L 276.609966 367.619303 
L 280.401881 365.481001 
L 284.600072 363.537267 
L 288.662838 361.452151 
L 292.861029 365.068529 
L 296.923795 360.345128 
L 301.121986 359.019933 
L 305.320178 359.002239 
L 309.382944 356.949605 
L 313.581135 354.713519 
L 317.643901 351.584001 
L 321.842092 347.09193 
L 326.040283 346.427573 
L 329.967623 353.887097 
L 334.165815 360.541193 
L 338.228581 351.581518 
L 342.426772 348.106383 
L 346.489538 344.183263 
L 350.687729 336.436851 
L 354.88592 325.358201 
L 358.948686 331.355722 
L 363.146877 336.275914 
L 367.209643 326.011595 
L 371.407834 317.937207 
L 375.606026 318.268089 
L 379.39794 321.843044 
L 383.596132 317.325687 
L 387.658897 312.774754 
L 391.857089 313.945741 
L 395.919855 308.53266 
L 400.118046 303.318769 
L 404.316237 299.227061 
L 408.379003 307.741408 
L 412.577194 300.926946 
L 416.63996 294.912986 
L 420.838151 284.32199 
L 425.036343 288.075474 
L 428.828257 292.327279 
L 433.026449 285.264588 
L 437.089214 295.971229 
L 441.287406 300.068094 
L 445.350172 310.169692 
L 449.548363 308.223364 
L 453.746554 311.296645 
L 457.80932 320.044454 
L 462.007511 307.136079 
L 466.070277 298.624826 
L 470.268468 302.710119 
L 474.46666 303.520877 
L 478.258574 305.87207 
L 482.456766 302.235391 
L 486.519531 301.400636 
L 490.717723 304.149542 
L 494.780488 297.885865 
L 498.97868 291.794249 
L 503.176871 292.406676 
L 507.239637 298.474374 
L 511.437828 301.60905 
L 515.500594 294.354013 
L 519.698785 281.243644 
L 523.896977 277.269094 
L 527.824317 269.599174 
L 532.022508 262.518297 
L 536.085274 273.093009 
L 540.283465 270.782762 
L 544.346231 259.870138 
L 548.544422 255.573742 
L 552.742614 249.127337 
L 556.805379 243.971273 
L 561.003571 247.341925 
L 565.066336 245.110485 
L 569.264528 235.296941 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #4461aa; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="us-big-line2d_42">
    <path d="M 74.555082 389.779583 
L 78.753273 390.339821 
L 82.545188 388.18903 
L 86.743379 388.443502 
L 90.806145 389.002318 
L 95.004336 387.714937 
L 99.067102 388.109358 
L 103.265293 386.661807 
L 107.463484 389.394876 
L 111.52625 390.370909 
L 115.724442 387.77881 
L 119.787207 387.459613 
L 123.985399 387.689366 
L 128.18359 389.928566 
L 132.11093 390.726446 
L 136.309121 388.416054 
L 140.371887 388.636466 
L 144.570079 387.755522 
L 148.632844 386.743472 
L 152.831036 385.443293 
L 157.029227 385.92498 
L 161.091993 385.76474 
L 165.290184 386.920995 
L 169.35295 386.294778 
L 173.551141 385.75805 
L 177.749332 384.958112 
L 181.541247 383.762691 
L 185.739438 383.930931 
L 189.802204 383.505092 
L 194.000395 382.229284 
L 198.063161 382.102374 
L 202.261353 380.424525 
L 206.459544 379.741206 
L 210.52231 378.964186 
L 214.720501 376.78252 
L 218.783267 375.056901 
L 222.981458 374.910625 
L 227.179649 370.282361 
L 230.971564 371.290417 
L 235.169755 372.976545 
L 239.232521 372.543371 
L 243.430712 370.343814 
L 247.493478 370.555815 
L 251.69167 369.546568 
L 255.889861 364.968621 
L 259.952627 364.505918 
L 264.150818 370.519061 
L 268.213584 370.583646 
L 272.411775 375.598163 
L 276.609966 371.559462 
L 280.401881 369.246755 
L 284.600072 367.717106 
L 288.662838 366.166907 
L 292.861029 369.326516 
L 296.923795 365.456559 
L 301.121986 364.927215 
L 305.320178 364.792173 
L 309.382944 364.895278 
L 313.581135 364.406312 
L 317.643901 362.701371 
L 321.842092 360.732035 
L 326.040283 359.368867 
L 329.967623 364.902104 
L 334.165815 372.158626 
L 338.228581 364.887354 
L 342.426772 361.322607 
L 346.489538 358.904998 
L 350.687729 353.735892 
L 354.88592 346.82036 
L 358.948686 350.355861 
L 363.146877 352.422441 
L 367.209643 344.664578 
L 371.407834 341.239558 
L 375.606026 340.562008 
L 379.39794 340.845755 
L 383.596132 341.270014 
L 387.658897 336.995014 
L 391.857089 338.304793 
L 395.919855 335.331442 
L 400.118046 335.913631 
L 404.316237 331.359648 
L 408.379003 334.560105 
L 412.577194 327.062014 
L 416.63996 330.6993 
L 420.838151 330.709154 
L 425.036343 338.09844 
L 428.828257 339.36521 
L 433.026449 335.186359 
L 437.089214 344.365308 
L 441.287406 344.696292 
L 445.350172 350.96046 
L 449.548363 344.158579 
L 453.746554 345.562306 
L 457.80932 351.728834 
L 462.007511 344.040424 
L 466.070277 341.57836 
L 470.268468 344.53232 
L 474.46666 344.269748 
L 478.258574 347.362409 
L 482.456766 346.772941 
L 486.519531 345.000051 
L 490.717723 342.927921 
L 494.780488 336.601761 
L 498.97868 334.397138 
L 503.176871 335.525684 
L 507.239637 340.632731 
L 511.437828 342.324996 
L 515.500594 332.487013 
L 519.698785 328.830016 
L 523.896977 325.988612 
L 527.824317 317.811659 
L 532.022508 314.535873 
L 536.085274 320.018394 
L 540.283465 312.79931 
L 544.346231 306.453676 
L 548.544422 308.933818 
L 552.742614 306.094758 
L 556.805379 303.04093 
L 561.003571 301.438291 
L 565.066336 292.326531 
L 569.264528 296.707537 
" clip-path="url(#us-big-pa8059fe9ef)" style="fill: none; stroke: #a2557e; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="us-big-patch_6">
    <path d="M 49.819609 400.593832 
L 49.819609 227.425661 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="us-big-patch_7">
    <path d="M 49.819609 400.593832 
L 594 400.593832 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="us-big-legend_1">
    <g id="us-big-line2d_43">
     <path d="M 57.919609 239.942692 
L 66.919609 239.942692 
L 75.919609 239.942692 
" style="fill: none; stroke: #006f73; stroke-width: 2; stroke-linecap: square"/>
    </g>
    <g id="us-big-text_12">
     <!-- 盈利、低扩张 + 动量 -->
     <g transform="translate(83.119609 243.092692) scale(0.09 -0.09)">
      <defs>
       <path id="us-big-ArialUnicodeMS-11ec" d="M 2150 -56 
L 1594 -550 
Q 1244 281 603 763 
L 959 1069 
Q 1669 634 2150 -56 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-21dd" d="M 2188 5153 
Q 1994 4550 1828 4150 
L 1663 3794 
L 1663 -434 
L 1172 -434 
L 1172 2956 
Q 997 2628 622 2253 
L 244 2591 
Q 1125 3463 1741 5363 
L 2188 5153 
z
M 6150 872 
Q 6053 -13 5886 -186 
Q 5719 -359 5478 -359 
Q 4941 -359 4542 559 
Q 4144 1478 4013 2875 
L 2869 2875 
L 2869 1031 
L 4050 1281 
L 4050 788 
L 2175 372 
L 1906 831 
L 2363 928 
L 2363 4594 
Q 4388 4797 5459 5319 
L 5797 4947 
Q 5131 4625 4428 4469 
Q 4419 3966 4469 3341 
L 5894 3341 
L 5894 2875 
L 4500 2875 
Q 4625 1759 4904 978 
Q 5184 197 5478 197 
Q 5559 197 5603 420 
Q 5647 644 5684 1106 
L 6150 872 
z
M 3975 3328 
Q 3938 3875 3928 4353 
Q 3438 4266 2869 4191 
L 2869 3328 
L 3975 3328 
z
M 4263 -250 
L 2188 -250 
L 2188 219 
L 4263 219 
L 4263 -250 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-34f8" d="M 2456 2291 
L 1772 1991 
L 1772 109 
Q 1772 -56 1698 -175 
Q 1625 -294 1483 -342 
Q 1341 -391 781 -391 
L 609 109 
Q 1019 72 1197 72 
Q 1288 72 1288 172 
L 1288 1778 
L 594 1497 
L 269 1906 
Q 763 2050 1288 2297 
L 1288 3597 
L 481 3597 
L 481 4063 
L 1288 4063 
L 1288 5288 
L 1772 5288 
L 1772 4063 
L 2456 4063 
L 2456 3597 
L 1772 3597 
L 1772 2497 
Q 2175 2644 2456 2791 
L 2456 2291 
z
M 4653 4531 
L 4288 4250 
Q 3994 4719 3506 5006 
L 3841 5259 
Q 4428 4941 4653 4531 
z
M 5900 3725 
L 3116 3725 
L 3116 1850 
Q 3116 1103 2942 579 
Q 2769 56 2344 -403 
L 1972 -63 
Q 2631 600 2631 1678 
L 2631 4191 
L 5888 4191 
L 5900 3725 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-31af" d="M 6034 44 
L 5716 -300 
Q 5091 44 4598 736 
Q 4106 1428 4038 2369 
L 3541 2369 
L 3541 263 
L 4513 691 
L 4513 184 
L 3116 -422 
L 2828 -56 
Q 3053 34 3053 197 
L 3053 2369 
L 2534 2369 
L 2534 2834 
L 3053 2834 
L 3053 5141 
L 3541 5141 
L 3541 3547 
Q 4516 3963 5319 4884 
L 5663 4544 
Q 4647 3419 3541 3091 
L 3541 2834 
L 5850 2834 
L 5850 2369 
L 4481 2369 
Q 4594 988 6034 44 
z
M 2534 2284 
Q 2531 1553 2398 795 
Q 2266 38 2083 -184 
Q 1900 -406 1531 -406 
Q 1319 -406 966 -325 
L 872 206 
Q 984 184 1237 114 
Q 1491 44 1619 44 
Q 1728 44 1890 666 
Q 2053 1288 2053 1819 
L 531 1819 
Q 659 2781 738 3681 
L 2069 3681 
L 2069 4422 
L 397 4422 
L 397 4891 
L 2528 4891 
L 2528 3213 
L 1172 3213 
L 1063 2284 
L 2534 2284 
z
" transform="scale(0.015625)"/>
      </defs>
      <use xlink:href="#us-big-ArialUnicodeMS-4957"/>
      <use xlink:href="#us-big-ArialUnicodeMS-24b8" transform="translate(100 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-11ec" transform="translate(200 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-21dd" transform="translate(300 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-34f8" transform="translate(400 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-31af" transform="translate(500 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-3" transform="translate(600 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-e" transform="translate(627.78125 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-3" transform="translate(686.1875 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-2537" transform="translate(713.96875 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-645e" transform="translate(813.96875 0)"/>
     </g>
    </g>
    <g id="us-big-line2d_44">
     <path d="M 57.919609 253.820621 
L 66.919609 253.820621 
L 75.919609 253.820621 
" style="fill: none; stroke: #df8f32; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="us-big-text_13">
     <!-- 盈利 + 动量 -->
     <g transform="translate(83.119609 256.970621) scale(0.09 -0.09)">
      <use xlink:href="#us-big-ArialUnicodeMS-4957"/>
      <use xlink:href="#us-big-ArialUnicodeMS-24b8" transform="translate(100 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-3" transform="translate(200 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-e" transform="translate(227.78125 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-3" transform="translate(286.1875 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-2537" transform="translate(313.96875 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-645e" transform="translate(413.96875 0)"/>
     </g>
    </g>
    <g id="us-big-line2d_45">
     <path d="M 183.376797 239.942692 
L 192.376797 239.942692 
L 201.376797 239.942692 
" style="fill: none; stroke: #4461aa; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="us-big-text_14">
     <!-- 盈利、低扩张单独使用 -->
     <g transform="translate(208.576797 243.092692) scale(0.09 -0.09)">
      <defs>
       <path id="us-big-ArialUnicodeMS-25e4" d="M 5925 947 
L 3353 947 
L 3353 -372 
L 2869 -372 
L 2869 947 
L 347 947 
L 347 1388 
L 2869 1388 
L 2869 1919 
L 1234 1919 
L 1234 4213 
L 2234 4213 
Q 2041 4659 1550 5106 
L 1900 5381 
Q 2347 5050 2747 4359 
L 2547 4219 
L 2547 4213 
L 3328 4213 
Q 3750 4644 4000 5344 
L 4447 5131 
Q 4219 4559 3909 4213 
L 4984 4213 
L 4984 1919 
L 3353 1919 
L 3353 1388 
L 5925 1388 
L 5925 947 
z
M 4500 3316 
L 4500 3744 
L 3353 3744 
L 3353 3316 
L 4500 3316 
z
M 2869 3316 
L 2869 3744 
L 1722 3744 
L 1722 3316 
L 2869 3316 
z
M 4500 2363 
L 4500 2847 
L 3353 2847 
L 3353 2363 
L 4500 2363 
z
M 2869 2363 
L 2869 2847 
L 1722 2847 
L 1722 2363 
L 2869 2363 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-457b" d="M 6069 -84 
L 5569 -313 
Q 5425 156 5313 331 
L 2638 -281 
L 2388 238 
L 3897 506 
L 3897 1569 
L 2656 1569 
L 2656 3975 
L 3897 3975 
L 3897 5294 
L 4384 5294 
L 4384 3975 
L 5563 3975 
L 5563 1569 
L 4384 1569 
L 4384 603 
L 5119 763 
Q 4953 1013 4800 1184 
L 5184 1441 
Q 5800 738 6069 -84 
z
M 5075 2034 
L 5075 3506 
L 4384 3506 
L 4384 2034 
L 5075 2034 
z
M 3897 2034 
L 3897 3506 
L 3144 3506 
L 3144 2034 
L 3897 2034 
z
M 2169 4684 
Q 1866 4100 1778 3988 
Q 2163 3459 2163 2053 
Q 2163 953 2092 511 
Q 2022 69 1820 -151 
Q 1619 -372 1281 -372 
Q 1038 -372 647 -300 
L 453 244 
Q 950 91 1219 91 
Q 1438 91 1531 336 
Q 1625 581 1656 1300 
L 1703 2247 
Q 1259 1538 569 1044 
L 213 1416 
Q 1066 2003 1638 2906 
Q 1600 3309 1459 3513 
Q 1138 3016 684 2713 
L 306 3109 
Q 906 3513 1203 3950 
Q 994 4234 313 4628 
L 609 4997 
Q 1072 4753 1497 4366 
Q 1731 4794 1806 4972 
L 2169 4684 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-220e" d="M 6303 84 
L 6009 -378 
Q 5394 -328 4664 -104 
Q 3934 119 3525 397 
Q 3059 -59 2194 -453 
L 1819 -25 
Q 2713 288 3103 691 
Q 2803 944 2291 1588 
L 2706 1850 
Q 3078 1341 3425 1075 
Q 3641 1409 3688 1931 
L 2234 1931 
L 2234 3719 
L 3713 3719 
L 3713 4141 
L 1875 4141 
L 1684 3669 
L 1684 -469 
L 1184 -469 
L 1184 2772 
Q 981 2431 678 2041 
L 319 2363 
Q 1153 3313 1753 5331 
L 2203 5166 
L 2034 4628 
L 3713 4628 
L 3713 5350 
L 4219 5350 
L 4219 4628 
L 5947 4628 
L 5947 4141 
L 4219 4141 
L 4219 3719 
L 5709 3719 
L 5709 1931 
L 4197 1931 
Q 4106 1203 3841 781 
Q 4734 256 6303 84 
z
M 5191 2419 
L 5191 3250 
L 4219 3250 
L 4219 2419 
L 5191 2419 
z
M 3713 2419 
L 3713 3231 
L 2725 3231 
L 2725 2419 
L 3713 2419 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-47b7" d="M 5472 159 
Q 5472 -66 5340 -219 
Q 5209 -372 5013 -372 
L 4347 -372 
L 4191 128 
L 4722 113 
Q 4966 113 4966 256 
L 4966 1722 
L 3572 1722 
L 3572 13 
L 3084 13 
L 3084 1722 
L 1678 1722 
Q 1584 466 744 -469 
L 331 -159 
Q 794 394 1001 936 
Q 1209 1478 1209 2194 
L 1209 5044 
L 5472 5044 
L 5472 159 
z
M 4966 3641 
L 4966 4575 
L 3572 4575 
L 3572 3641 
L 4966 3641 
z
M 3084 3641 
L 3084 4575 
L 1697 4575 
L 1697 3641 
L 3084 3641 
z
M 4966 2188 
L 4966 3175 
L 3572 3175 
L 3572 2188 
L 4966 2188 
z
M 3084 2188 
L 3084 3175 
L 1697 3175 
L 1697 2188 
L 3084 2188 
z
" transform="scale(0.015625)"/>
      </defs>
      <use xlink:href="#us-big-ArialUnicodeMS-4957"/>
      <use xlink:href="#us-big-ArialUnicodeMS-24b8" transform="translate(100 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-11ec" transform="translate(200 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-21dd" transform="translate(300 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-34f8" transform="translate(400 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-31af" transform="translate(500 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-25e4" transform="translate(600 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-457b" transform="translate(700 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-220e" transform="translate(800 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-47b7" transform="translate(900 0)"/>
     </g>
    </g>
    <g id="us-big-line2d_46">
     <path d="M 183.376797 253.899371 
L 192.376797 253.899371 
L 201.376797 253.899371 
" style="fill: none; stroke: #a2557e; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="us-big-text_15">
     <!-- 动量单独使用 -->
     <g transform="translate(208.576797 257.049371) scale(0.09 -0.09)">
      <use xlink:href="#us-big-ArialUnicodeMS-2537"/>
      <use xlink:href="#us-big-ArialUnicodeMS-645e" transform="translate(100 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-25e4" transform="translate(200 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-457b" transform="translate(300 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-220e" transform="translate(400 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-47b7" transform="translate(500 0)"/>
     </g>
    </g>
   </g>
  </g>
  <g id="us-big-axes_3">
   <g id="us-big-patch_8">
    <path d="M 49.819609 548.100117 
L 594 548.100117 
L 594 414.893832 
L 49.819609 414.893832 
z
" style="fill: #fbfaf7"/>
   </g>
   <g id="us-big-matplotlib.axis_5">
    <g id="us-big-xtick_11">
     <g id="us-big-line2d_47">
      <path d="M 124.120824 548.100117 
L 124.120824 414.893832 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_48">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="124.120824" y="548.100117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_16">
      <!-- 2016 -->
      <g transform="translate(112.998949 562.380391) scale(0.1 -0.1)">
       <defs>
        <path id="us-big-ArialUnicodeMS-19" d="M 838 2363 
Q 1225 2969 1941 2969 
Q 2503 2969 2897 2553 
Q 3291 2138 3291 1491 
Q 3291 838 2898 380 
Q 2506 -78 1856 -78 
Q 1197 -78 733 409 
Q 269 897 269 2144 
Q 269 3369 689 3986 
Q 1109 4603 1906 4603 
Q 2422 4603 2778 4315 
Q 3134 4028 3213 3463 
L 2650 3413 
Q 2497 4141 1875 4141 
Q 1444 4141 1134 3712 
Q 825 3284 825 2363 
L 838 2363 
z
M 1844 384 
Q 2231 384 2472 696 
Q 2713 1009 2713 1453 
Q 2713 1897 2472 2187 
Q 2231 2478 1825 2478 
Q 1453 2478 1184 2204 
Q 916 1931 916 1484 
Q 916 1028 1180 706 
Q 1444 384 1844 384 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-big-ArialUnicodeMS-15"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-14" transform="translate(111.21875 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-19" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-xtick_12">
     <g id="us-big-line2d_49">
      <path d="M 223.116884 548.100117 
L 223.116884 414.893832 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_50">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="223.116884" y="548.100117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_17">
      <!-- 2018 -->
      <g transform="translate(211.995009 562.380391) scale(0.1 -0.1)">
       <defs>
        <path id="us-big-ArialUnicodeMS-1b" d="M 2425 2478 
Q 3284 2203 3284 1306 
Q 3284 716 2862 319 
Q 2441 -78 1778 -78 
Q 1109 -78 689 322 
Q 269 722 269 1325 
Q 269 1759 505 2084 
Q 741 2409 1141 2478 
L 1141 2491 
Q 453 2703 453 3419 
Q 453 3925 815 4264 
Q 1178 4603 1766 4603 
Q 2363 4603 2730 4253 
Q 3097 3903 3097 3406 
Q 3097 2731 2425 2491 
L 2425 2478 
z
M 1778 2700 
Q 2094 2700 2308 2901 
Q 2522 3103 2522 3406 
Q 2522 3716 2305 3928 
Q 2088 4141 1772 4141 
Q 1450 4141 1240 3931 
Q 1031 3722 1031 3438 
Q 1031 3097 1247 2898 
Q 1463 2700 1778 2700 
z
M 1778 384 
Q 2175 384 2440 640 
Q 2706 897 2706 1306 
Q 2706 1716 2432 1978 
Q 2159 2241 1766 2241 
Q 1356 2241 1100 1970 
Q 844 1700 844 1319 
Q 844 922 1108 653 
Q 1372 384 1778 384 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-big-ArialUnicodeMS-15"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-14" transform="translate(111.21875 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-1b" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-xtick_13">
     <g id="us-big-line2d_51">
      <path d="M 321.977517 548.100117 
L 321.977517 414.893832 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_52">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="321.977517" y="548.100117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_18">
      <!-- 2020 -->
      <g transform="translate(310.855642 562.380391) scale(0.1 -0.1)">
       <use xlink:href="#us-big-ArialUnicodeMS-15"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-15" transform="translate(111.21875 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-xtick_14">
     <g id="us-big-line2d_53">
      <path d="M 420.973577 548.100117 
L 420.973577 414.893832 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_54">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="420.973577" y="548.100117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_19">
      <!-- 2022 -->
      <g transform="translate(409.851702 562.380391) scale(0.1 -0.1)">
       <use xlink:href="#us-big-ArialUnicodeMS-15"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-15" transform="translate(111.21875 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-15" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-xtick_15">
     <g id="us-big-line2d_55">
      <path d="M 519.834211 548.100117 
L 519.834211 414.893832 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_56">
      <g>
       <use xlink:href="#us-big-m8896d8f95c" x="519.834211" y="548.100117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_20">
      <!-- 2024 -->
      <g transform="translate(508.712336 562.380391) scale(0.1 -0.1)">
       <use xlink:href="#us-big-ArialUnicodeMS-15"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-15" transform="translate(111.21875 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-17" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
   </g>
   <g id="us-big-matplotlib.axis_6">
    <g id="us-big-ytick_9">
     <g id="us-big-line2d_57">
      <path d="M 49.819609 543.758151 
L 594 543.758151 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_58">
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="543.758151" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_21">
      <!-- -25 -->
      <g transform="translate(28.368047 547.398288) scale(0.1 -0.1)">
       <defs>
        <path id="us-big-ArialUnicodeMS-10" d="M 1925 1375 
L 206 1375 
L 206 1941 
L 1925 1941 
L 1925 1375 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-big-ArialUnicodeMS-10"/>
       <use xlink:href="#us-big-ArialUnicodeMS-15" transform="translate(33.296875 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-18" transform="translate(88.90625 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-ytick_10">
     <g id="us-big-line2d_59">
      <path d="M 49.819609 519.196253 
L 594 519.196253 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_60">
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="519.196253" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_22">
      <!-- -20 -->
      <g transform="translate(28.368047 522.83639) scale(0.1 -0.1)">
       <use xlink:href="#us-big-ArialUnicodeMS-10"/>
       <use xlink:href="#us-big-ArialUnicodeMS-15" transform="translate(33.296875 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(88.90625 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-ytick_11">
     <g id="us-big-line2d_61">
      <path d="M 49.819609 494.634356 
L 594 494.634356 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_62">
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="494.634356" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_23">
      <!-- -15 -->
      <g transform="translate(28.368047 498.274492) scale(0.1 -0.1)">
       <use xlink:href="#us-big-ArialUnicodeMS-10"/>
       <use xlink:href="#us-big-ArialUnicodeMS-14" transform="translate(33.296875 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-18" transform="translate(88.90625 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-ytick_12">
     <g id="us-big-line2d_63">
      <path d="M 49.819609 470.072458 
L 594 470.072458 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_64">
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="470.072458" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_24">
      <!-- -10 -->
      <g transform="translate(28.368047 473.712595) scale(0.1 -0.1)">
       <use xlink:href="#us-big-ArialUnicodeMS-10"/>
       <use xlink:href="#us-big-ArialUnicodeMS-14" transform="translate(33.296875 0)"/>
       <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(88.90625 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-ytick_13">
     <g id="us-big-line2d_65">
      <path d="M 49.819609 445.51056 
L 594 445.51056 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_66">
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="445.51056" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_25">
      <!-- -5 -->
      <g transform="translate(33.928984 449.150697) scale(0.1 -0.1)">
       <use xlink:href="#us-big-ArialUnicodeMS-10"/>
       <use xlink:href="#us-big-ArialUnicodeMS-18" transform="translate(33.296875 0)"/>
      </g>
     </g>
    </g>
    <g id="us-big-ytick_14">
     <g id="us-big-line2d_67">
      <path d="M 49.819609 420.948663 
L 594 420.948663 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-big-line2d_68">
      <g>
       <use xlink:href="#us-big-m7e9fe31986" x="49.819609" y="420.948663" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-big-text_26">
      <!-- 0 -->
      <g transform="translate(37.258672 424.5888) scale(0.1 -0.1)">
       <use xlink:href="#us-big-ArialUnicodeMS-13"/>
      </g>
     </g>
    </g>
    <g id="us-big-text_27">
     <!-- 月末回撤 % -->
     <g transform="translate(22.268438 507.332131) rotate(-90) scale(0.1 -0.1)">
      <defs>
       <path id="us-big-ArialUnicodeMS-3997" d="M 5044 206 
Q 5044 -19 4897 -150 
Q 4750 -281 4500 -281 
L 3725 -281 
L 3531 231 
L 4359 206 
Q 4519 197 4519 341 
L 4519 1594 
L 2363 1594 
Q 2119 463 941 -488 
L 550 -91 
Q 1172 356 1520 920 
Q 1869 1484 1869 2053 
L 1869 5013 
L 5044 5013 
L 5044 206 
z
M 4519 3541 
L 4519 4544 
L 2375 4544 
L 2375 3541 
L 4519 3541 
z
M 4519 2059 
L 4519 3072 
L 2388 3072 
L 2375 2059 
L 4519 2059 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-39ba" d="M 6113 616 
L 5778 184 
Q 4184 888 3475 2644 
L 3475 -428 
L 2969 -428 
L 2956 2606 
Q 2238 1034 659 147 
L 353 581 
Q 1709 1228 2516 2656 
L 1050 2656 
L 1050 3122 
L 2969 3122 
L 2969 3975 
L 744 3975 
L 744 4441 
L 2969 4441 
L 2969 5369 
L 3475 5369 
L 3475 4441 
L 5709 4441 
L 5709 3975 
L 3475 3975 
L 3475 3122 
L 5416 3122 
L 5416 2656 
L 3963 2656 
Q 4675 1159 6113 616 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-296d" d="M 5575 -134 
L 5088 -147 
L 5088 313 
L 1313 313 
L 1313 -191 
L 825 -191 
L 825 4825 
L 5575 4825 
L 5575 -134 
z
M 5088 794 
L 5088 4366 
L 1313 4366 
L 1313 794 
L 5088 794 
z
M 4378 1509 
L 1997 1509 
L 1997 3653 
L 4378 3653 
L 4378 1509 
z
M 3891 1972 
L 3891 3194 
L 2484 3194 
L 2484 1972 
L 3891 1972 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-3733" d="M 6150 -56 
L 5759 -416 
Q 5250 34 4972 563 
Q 4619 -91 4244 -434 
L 3922 -116 
Q 4444 434 4722 1088 
Q 4406 1928 4341 2778 
L 4147 2522 
L 4000 2631 
L 4000 197 
Q 4000 19 3870 -134 
Q 3741 -288 3627 -306 
Q 3513 -325 3122 -325 
L 2950 147 
Q 3200 128 3303 128 
Q 3513 128 3513 281 
L 3513 756 
L 2625 756 
L 2625 -434 
L 2138 -434 
L 2138 2853 
L 3781 2853 
Q 3906 3016 3909 3028 
L 3794 2969 
L 3669 3225 
L 2059 3091 
L 1941 3572 
L 2322 3584 
Q 2559 4044 2619 4238 
L 1831 4238 
L 1831 4703 
L 2791 4703 
L 2791 5275 
L 3291 5275 
L 3291 4703 
L 4231 4703 
L 4231 4238 
L 3116 4238 
Q 2984 3859 2809 3597 
L 3431 3634 
Q 3309 3800 3181 3922 
L 3578 4109 
Q 3891 3806 4103 3413 
Q 4569 4478 4569 5344 
L 5044 5222 
Q 5019 4875 4825 4056 
L 5984 4056 
L 5984 3591 
L 5684 3591 
Q 5644 1978 5247 1088 
Q 5597 350 6150 -56 
z
M 5191 3591 
L 4738 3591 
Q 4738 2694 5006 1716 
Q 5213 2631 5191 3591 
z
M 3513 2059 
L 3513 2388 
L 2625 2388 
L 2625 2059 
L 3513 2059 
z
M 3513 1222 
L 3513 1594 
L 2625 1594 
L 2625 1222 
L 3513 1222 
z
M 2094 3641 
L 1522 3641 
L 1522 2522 
L 2016 2731 
L 2016 2247 
L 1522 2009 
L 1522 172 
Q 1522 -53 1401 -212 
Q 1281 -372 1107 -392 
Q 934 -413 556 -422 
L 397 78 
Q 663 38 806 38 
Q 1038 38 1038 213 
L 1038 1784 
L 481 1509 
L 250 1947 
L 1038 2303 
L 1038 3641 
L 313 3641 
L 313 4109 
L 1038 4109 
L 1038 5288 
L 1522 5288 
L 1522 4109 
L 2094 4109 
L 2094 3641 
z
" transform="scale(0.015625)"/>
       <path id="us-big-ArialUnicodeMS-8" d="M 4325 4659 
L 1838 -159 
L 1369 -159 
L 3872 4659 
L 4325 4659 
z
M 1428 4653 
Q 1856 4653 2137 4343 
Q 2419 4034 2419 3438 
Q 2419 2850 2131 2539 
Q 1844 2228 1434 2228 
Q 1009 2228 739 2540 
Q 469 2853 469 3475 
Q 469 3984 722 4318 
Q 975 4653 1428 4653 
z
M 1441 2619 
Q 1931 2619 1931 3463 
Q 1931 4269 1441 4269 
Q 953 4269 953 3419 
Q 953 2619 1441 2619 
z
M 4250 2253 
Q 4681 2253 4961 1943 
Q 5241 1634 5241 1038 
Q 5241 600 5087 328 
Q 4934 56 4709 -58 
Q 4484 -172 4256 -172 
Q 3831 -172 3561 140 
Q 3291 453 3291 1075 
Q 3291 1584 3544 1918 
Q 3797 2253 4250 2253 
z
M 4263 219 
Q 4756 219 4756 1063 
Q 4756 1869 4263 1869 
Q 3775 1869 3775 1019 
Q 3775 219 4263 219 
z
" transform="scale(0.015625)"/>
      </defs>
      <use xlink:href="#us-big-ArialUnicodeMS-3997"/>
      <use xlink:href="#us-big-ArialUnicodeMS-39ba" transform="translate(100 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-296d" transform="translate(200 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-3733" transform="translate(300 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-3" transform="translate(400 0)"/>
      <use xlink:href="#us-big-ArialUnicodeMS-8" transform="translate(427.78125 0)"/>
     </g>
    </g>
   </g>
   <g id="us-big-line2d_69">
    <path d="M 74.555082 420.948663 
L 78.753273 433.614497 
L 82.545188 420.948663 
L 86.743379 427.849809 
L 90.806145 430.868637 
L 95.004336 420.948663 
L 99.067102 429.712234 
L 103.265293 420.948663 
L 107.463484 450.4478 
L 111.52625 460.626775 
L 115.724442 426.787261 
L 119.787207 424.224247 
L 123.985399 428.207526 
L 128.18359 446.339274 
L 132.11093 447.382525 
L 136.309121 420.948663 
L 140.371887 424.253719 
L 144.570079 420.948663 
L 148.632844 420.948663 
L 152.831036 420.948663 
L 157.029227 425.783883 
L 161.091993 424.25223 
L 165.290184 433.219765 
L 169.35295 420.948663 
L 173.551141 420.948663 
L 177.749332 420.948663 
L 181.541247 420.948663 
L 185.739438 424.234194 
L 189.802204 420.948663 
L 194.000395 420.948663 
L 198.063161 420.948663 
L 202.261353 420.948663 
L 206.459544 420.948663 
L 210.52231 420.948663 
L 214.720501 420.948663 
L 218.783267 420.948663 
L 222.981458 420.948663 
L 227.179649 420.948663 
L 230.971564 434.353772 
L 235.169755 446.019475 
L 239.232521 445.415843 
L 243.430712 430.557739 
L 247.493478 431.484949 
L 251.69167 421.158537 
L 255.889861 420.948663 
L 259.952627 420.948663 
L 264.150818 456.053044 
L 268.213584 452.359528 
L 272.411775 489.508367 
L 276.609966 459.443455 
L 280.401881 442.550068 
L 284.600072 429.367175 
L 288.662838 420.948663 
L 292.861029 446.387727 
L 296.923795 420.948663 
L 301.121986 420.948663 
L 305.320178 420.948663 
L 309.382944 420.948663 
L 313.581135 420.948663 
L 317.643901 420.948663 
L 321.842092 420.948663 
L 326.040283 420.948663 
L 329.967623 462.7549 
L 334.165815 507.514483 
L 338.228581 455.28888 
L 342.426772 432.636958 
L 346.489538 420.948663 
L 350.687729 420.948663 
L 354.88592 420.948663 
L 358.948686 446.087147 
L 363.146877 464.511194 
L 367.209643 420.948663 
L 371.407834 420.948663 
L 375.606026 420.948663 
L 379.39794 430.443657 
L 383.596132 420.948663 
L 387.658897 420.948663 
L 391.857089 426.787996 
L 395.919855 420.948663 
L 400.118046 420.948663 
L 404.316237 420.948663 
L 408.379003 446.2022 
L 412.577194 420.948663 
L 416.63996 420.948663 
L 420.838151 420.948663 
L 425.036343 443.434157 
L 428.828257 454.570336 
L 433.026449 431.885527 
L 437.089214 472.013547 
L 441.287406 480.948703 
L 445.350172 513.973912 
L 449.548363 496.320511 
L 453.746554 505.354866 
L 457.80932 535.451173 
L 462.007511 493.887998 
L 466.070277 471.744452 
L 470.268468 485.949274 
L 474.46666 487.055484 
L 478.258574 498.040882 
L 482.456766 489.51275 
L 486.519531 484.250665 
L 490.717723 485.616363 
L 494.780488 460.210767 
L 498.97868 443.469416 
L 503.176871 446.982604 
L 507.239637 469.532623 
L 511.437828 479.273121 
L 515.500594 444.780353 
L 519.698785 420.948663 
L 523.896977 420.948663 
L 527.824317 420.948663 
L 532.022508 420.948663 
L 536.085274 448.978486 
L 540.283465 432.343899 
L 544.346231 420.948663 
L 548.544422 420.948663 
L 552.742614 420.948663 
L 556.805379 420.948663 
L 561.003571 423.737246 
L 565.066336 420.948663 
L 569.264528 420.948663 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #006f73; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="us-big-line2d_70">
    <path d="M 74.555082 420.948663 
L 78.753273 428.21837 
L 82.545188 420.948663 
L 86.743379 426.83263 
L 90.806145 428.512817 
L 95.004336 420.948663 
L 99.067102 427.797476 
L 103.265293 420.948663 
L 107.463484 450.650902 
L 111.52625 462.043766 
L 115.724442 429.061884 
L 119.787207 428.627057 
L 123.985399 436.353393 
L 128.18359 463.930885 
L 132.11093 465.445262 
L 136.309121 436.059061 
L 140.371887 439.804751 
L 144.570079 431.603721 
L 148.632844 425.825508 
L 152.831036 420.948663 
L 157.029227 424.516951 
L 161.091993 422.590945 
L 165.290184 433.752145 
L 169.35295 420.948663 
L 173.551141 420.948663 
L 177.749332 420.948663 
L 181.541247 420.948663 
L 185.739438 420.948663 
L 189.802204 420.948663 
L 194.000395 420.948663 
L 198.063161 421.467228 
L 202.261353 420.948663 
L 206.459544 420.948663 
L 210.52231 420.948663 
L 214.720501 420.948663 
L 218.783267 420.948663 
L 222.981458 420.948663 
L 227.179649 420.948663 
L 230.971564 433.173063 
L 235.169755 445.665544 
L 239.232521 445.468728 
L 243.430712 429.807602 
L 247.493478 428.338229 
L 251.69167 420.948663 
L 255.889861 420.948663 
L 259.952627 420.948663 
L 264.150818 462.489849 
L 268.213584 458.459156 
L 272.411775 497.368485 
L 276.609966 466.199713 
L 280.401881 448.628618 
L 284.600072 437.196647 
L 288.662838 423.252574 
L 292.861029 451.409698 
L 296.923795 420.948663 
L 301.121986 420.948663 
L 305.320178 420.948663 
L 309.382944 420.948663 
L 313.581135 420.948663 
L 317.643901 420.948663 
L 321.842092 420.948663 
L 326.040283 420.948663 
L 329.967623 458.758713 
L 334.165815 505.581608 
L 338.228581 452.304624 
L 342.426772 427.446349 
L 346.489538 420.948663 
L 350.687729 420.948663 
L 354.88592 420.948663 
L 358.948686 440.732113 
L 363.146877 457.171636 
L 367.209643 420.948663 
L 371.407834 420.948663 
L 375.606026 422.881755 
L 379.39794 420.948663 
L 383.596132 420.948663 
L 387.658897 420.948663 
L 391.857089 425.177646 
L 395.919855 420.948663 
L 400.118046 420.948663 
L 404.316237 420.948663 
L 408.379003 442.346816 
L 412.577194 420.948663 
L 416.63996 426.923647 
L 420.838151 420.948663 
L 425.036343 452.912754 
L 428.828257 462.149286 
L 433.026449 443.375801 
L 437.089214 485.357697 
L 441.287406 489.047323 
L 445.350172 519.107892 
L 449.548363 484.232036 
L 453.746554 497.564578 
L 457.80932 531.31735 
L 462.007511 493.116807 
L 466.070277 472.783989 
L 470.268468 492.370043 
L 474.46666 480.387058 
L 478.258574 493.506361 
L 482.456766 481.85385 
L 486.519531 474.833156 
L 490.717723 471.890173 
L 494.780488 440.589015 
L 498.97868 429.197603 
L 503.176871 433.947257 
L 507.239637 458.61437 
L 511.437828 464.368975 
L 515.500594 421.031193 
L 519.698785 420.948663 
L 523.896977 420.948663 
L 527.824317 420.948663 
L 532.022508 420.948663 
L 536.085274 443.879554 
L 540.283465 420.948663 
L 544.346231 420.948663 
L 548.544422 420.948663 
L 552.742614 420.948663 
L 556.805379 420.948663 
L 561.003571 425.246606 
L 565.066336 420.948663 
L 569.264528 430.979414 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #df8f32; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="us-big-line2d_71">
    <path d="M 74.555082 420.948663 
L 78.753273 439.304751 
L 82.545188 420.948663 
L 86.743379 431.822706 
L 90.806145 431.060369 
L 95.004336 423.209351 
L 99.067102 436.202943 
L 103.265293 425.963107 
L 107.463484 452.982547 
L 111.52625 461.899372 
L 115.724442 424.206277 
L 119.787207 422.866771 
L 123.985399 428.233141 
L 128.18359 437.9427 
L 132.11093 430.249989 
L 136.309121 420.948663 
L 140.371887 424.8879 
L 144.570079 420.948663 
L 148.632844 420.948663 
L 152.831036 420.948663 
L 157.029227 425.229802 
L 161.091993 423.957383 
L 165.290184 429.022273 
L 169.35295 420.948663 
L 173.551141 420.948663 
L 177.749332 420.948663 
L 181.541247 420.948663 
L 185.739438 425.560896 
L 189.802204 420.948663 
L 194.000395 420.948663 
L 198.063161 420.948663 
L 202.261353 420.948663 
L 206.459544 422.316761 
L 210.52231 420.948663 
L 214.720501 420.948663 
L 218.783267 420.948663 
L 222.981458 420.948663 
L 227.179649 420.948663 
L 230.971564 438.962359 
L 235.169755 448.432049 
L 239.232521 450.596392 
L 243.430712 438.934315 
L 247.493478 439.088595 
L 251.69167 426.997629 
L 255.889861 425.970969 
L 259.952627 420.948663 
L 264.150818 445.517438 
L 268.213584 437.638662 
L 272.411775 473.87894 
L 276.609966 444.400557 
L 280.401881 428.166042 
L 284.600072 420.948663 
L 288.662838 420.948663 
L 292.861029 447.158173 
L 296.923795 420.948663 
L 301.121986 420.948663 
L 305.320178 420.948663 
L 309.382944 420.948663 
L 313.581135 420.948663 
L 317.643901 420.948663 
L 321.842092 420.948663 
L 326.040283 420.948663 
L 329.967623 465.201834 
L 334.165815 504.676848 
L 338.228581 451.524126 
L 342.426772 430.908098 
L 346.489538 420.948663 
L 350.687729 420.948663 
L 354.88592 420.948663 
L 358.948686 449.31176 
L 363.146877 472.580016 
L 367.209643 424.038655 
L 371.407834 420.948663 
L 375.606026 422.409113 
L 379.39794 438.188275 
L 383.596132 420.948663 
L 387.658897 420.948663 
L 391.857089 425.88806 
L 395.919855 420.948663 
L 400.118046 420.948663 
L 404.316237 420.948663 
L 408.379003 453.120819 
L 412.577194 427.371818 
L 416.63996 420.948663 
L 420.838151 420.948663 
L 425.036343 433.672708 
L 428.828257 448.086026 
L 433.026449 424.144004 
L 437.089214 460.438757 
L 441.287406 474.326842 
L 445.350172 508.570541 
L 449.548363 501.972629 
L 453.746554 512.390834 
L 457.80932 542.045286 
L 462.007511 498.286808 
L 466.070277 469.434266 
L 470.268468 483.283117 
L 474.46666 486.031531 
L 478.258574 494.001909 
L 482.456766 481.673824 
L 486.519531 478.844063 
L 490.717723 488.162662 
L 494.780488 466.929238 
L 498.97868 446.279092 
L 503.176871 448.355175 
L 507.239637 468.924244 
L 511.437828 479.550573 
L 515.500594 454.956512 
L 519.698785 420.948663 
L 523.896977 420.948663 
L 527.824317 420.948663 
L 532.022508 420.948663 
L 536.085274 452.107886 
L 540.283465 445.300561 
L 544.346231 420.948663 
L 548.544422 420.948663 
L 552.742614 420.948663 
L 556.805379 420.948663 
L 561.003571 429.886246 
L 565.066336 423.969385 
L 569.264528 420.948663 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #4461aa; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="us-big-line2d_72">
    <path d="M 74.555082 420.948663 
L 78.753273 427.924242 
L 82.545188 420.948663 
L 86.743379 423.994338 
L 90.806145 430.682572 
L 95.004336 420.948663 
L 99.067102 425.615423 
L 103.265293 420.948663 
L 107.463484 452.486139 
L 111.52625 463.748801 
L 115.724442 433.837999 
L 119.787207 430.154714 
L 123.985399 432.80589 
L 128.18359 458.644511 
L 132.11093 467.851416 
L 136.309121 441.191304 
L 140.371887 443.734678 
L 144.570079 433.569271 
L 148.632844 421.891008 
L 152.831036 420.948663 
L 157.029227 426.35228 
L 161.091993 424.554693 
L 165.290184 437.525702 
L 169.35295 430.500721 
L 173.551141 424.479647 
L 177.749332 420.948663 
L 181.541247 420.948663 
L 185.739438 422.766243 
L 189.802204 420.948663 
L 194.000395 420.948663 
L 198.063161 420.948663 
L 202.261353 420.948663 
L 206.459544 420.948663 
L 210.52231 420.948663 
L 214.720501 420.948663 
L 218.783267 420.948663 
L 222.981458 420.948663 
L 227.179649 420.948663 
L 230.971564 429.348832 
L 235.169755 443.399411 
L 239.232521 439.78975 
L 243.430712 421.460751 
L 247.493478 423.227365 
L 251.69167 420.948663 
L 255.889861 420.948663 
L 259.952627 420.948663 
L 264.150818 466.584669 
L 268.213584 467.074831 
L 272.411775 505.131888 
L 276.609966 474.480667 
L 280.401881 456.928659 
L 284.600072 445.319581 
L 288.662838 433.554532 
L 292.861029 457.533999 
L 296.923795 428.16344 
L 301.121986 424.146048 
L 305.320178 423.121163 
L 309.382944 423.903667 
L 313.581135 420.948663 
L 317.643901 420.948663 
L 321.842092 420.948663 
L 326.040283 420.948663 
L 329.967623 459.854709 
L 334.165815 510.877748 
L 338.228581 459.750998 
L 342.426772 434.686065 
L 346.489538 420.948663 
L 350.687729 420.948663 
L 354.88592 420.948663 
L 358.948686 442.022771 
L 363.146877 454.341064 
L 367.209643 420.948663 
L 371.407834 420.948663 
L 375.606026 420.948663 
L 379.39794 422.520624 
L 383.596132 424.871021 
L 387.658897 420.948663 
L 391.857089 427.924242 
L 395.919855 420.948663 
L 400.118046 423.994338 
L 404.316237 420.948663 
L 408.379003 437.012144 
L 412.577194 420.948663 
L 416.63996 438.436734 
L 420.838151 438.484109 
L 425.036343 474.011797 
L 428.828257 480.102427 
L 433.026449 460.010512 
L 437.089214 504.1429 
L 441.287406 505.73427 
L 445.350172 535.852389 
L 449.548363 503.148945 
L 453.746554 509.898066 
L 457.80932 539.546732 
L 462.007511 502.580856 
L 466.070277 490.74325 
L 470.268468 504.945891 
L 474.46666 503.683445 
L 478.258574 518.55296 
L 482.456766 515.718798 
L 486.519531 507.19474 
L 490.717723 497.23194 
L 494.780488 466.815762 
L 498.97868 456.215936 
L 503.176871 461.641987 
L 507.239637 486.196669 
L 511.437828 494.333077 
L 515.500594 447.032056 
L 519.698785 429.449214 
L 523.896977 420.948663 
L 527.824317 420.948663 
L 532.022508 420.948663 
L 536.085274 444.429837 
L 540.283465 420.948663 
L 544.346231 420.948663 
L 548.544422 430.871669 
L 552.742614 420.948663 
L 556.805379 420.948663 
L 561.003571 420.948663 
L 565.066336 420.948663 
L 569.264528 436.668277 
" clip-path="url(#us-big-pc148d70ea4)" style="fill: none; stroke: #a2557e; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="us-big-patch_9">
    <path d="M 49.819609 548.100117 
L 49.819609 414.893832 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="us-big-patch_10">
    <path d="M 49.819609 548.100117 
L 594 548.100117 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
  </g>
  <g id="us-big-text_28">
   <!-- 美股大盘组：2015—2024 年公开组合毛收益 -->
   <g transform="translate(48.384 25.9825) scale(0.16 -0.16)">
    <defs>
     <path id="us-big-ArialUnicodeMS-5330" d="M 6041 3725 
Q 5884 2956 5484 2956 
L 5038 2956 
Q 4569 2956 4569 3431 
L 4569 4575 
L 3681 4575 
Q 3672 3913 3630 3656 
Q 3588 3400 3377 3129 
Q 3166 2859 2944 2719 
L 2578 3078 
Q 3188 3506 3188 4019 
L 3188 5044 
L 5050 5044 
L 5050 3559 
Q 5050 3425 5178 3425 
L 5375 3425 
Q 5556 3425 5588 3969 
L 6041 3725 
z
M 2528 206 
Q 2528 -22 2406 -151 
Q 2284 -281 2075 -281 
L 1606 -281 
L 1447 213 
Q 1763 159 1850 159 
Q 2041 159 2041 294 
L 2041 1947 
L 1275 1947 
Q 1284 366 744 -384 
L 325 -56 
Q 794 578 794 1925 
L 794 5031 
L 2528 5031 
L 2528 206 
z
M 2041 3725 
L 2041 4550 
L 1281 4550 
L 1281 3725 
L 2041 3725 
z
M 2041 2413 
L 2041 3256 
L 1281 3256 
L 1281 2413 
L 2041 2413 
z
M 6022 6 
L 5703 -416 
Q 4931 -222 4244 453 
Q 3625 -78 2847 -391 
L 2553 38 
Q 3375 328 3909 825 
Q 3500 1369 3256 2272 
L 2981 2272 
L 2981 2741 
L 5350 2741 
Q 5150 1569 4563 813 
Q 5172 216 6022 6 
z
M 4763 2272 
L 3738 2272 
Q 4003 1503 4238 1153 
Q 4569 1625 4763 2272 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-2bb6" d="M 5972 109 
L 5625 -275 
Q 4584 341 4046 1159 
Q 3509 1978 3322 3250 
Q 3088 1959 2520 1142 
Q 1953 325 909 -244 
L 544 197 
Q 2403 1081 2809 3256 
L 856 3256 
L 856 3744 
L 2853 3744 
Q 2919 4313 2900 5356 
L 3419 5281 
Q 3434 4266 3384 3744 
L 5684 3744 
L 5684 3256 
L 3803 3256 
Q 4003 2125 4512 1389 
Q 5022 653 5972 109 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-4967" d="M 5759 3003 
L 4750 3003 
L 4750 2113 
Q 4750 2047 4639 1878 
Q 4528 1709 4116 1709 
Q 3994 1709 3738 1716 
L 3591 2194 
Q 4019 2156 4153 2156 
Q 4263 2156 4263 2309 
L 4263 3003 
L 2094 3003 
Q 1947 2297 1505 1947 
Q 1063 1597 769 1491 
L 500 1913 
Q 1481 2319 1594 3003 
L 475 3003 
L 475 3444 
L 1594 3444 
L 1594 4722 
L 2578 4722 
Q 2713 4844 2919 5319 
L 3322 5113 
Q 3234 4928 3078 4722 
L 4750 4722 
L 4750 3444 
L 5759 3444 
L 5759 3003 
z
M 4263 3444 
L 4263 4281 
L 2081 4281 
L 2081 3444 
L 4263 3444 
z
M 3616 3841 
L 3353 3513 
Q 2894 3866 2497 3938 
L 2747 4238 
Q 3325 4056 3616 3841 
z
M 3566 2509 
L 3334 2088 
Q 2991 2366 2344 2484 
L 2597 2853 
Q 3034 2819 3566 2509 
z
M 5850 -206 
L 416 -206 
L 416 238 
L 1106 238 
L 1106 1575 
L 5125 1575 
L 5125 238 
L 5850 238 
L 5850 -206 
z
M 4641 238 
L 4641 1131 
L 3975 1131 
L 3975 238 
L 4641 238 
z
M 3488 238 
L 3488 1131 
L 2791 1131 
L 2791 238 
L 3488 238 
z
M 2303 238 
L 2303 1131 
L 1594 1131 
L 1594 238 
L 2303 238 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-ca7" d="M 6438 1428 
L -38 1428 
L -38 1888 
L 6438 1888 
L 6438 1428 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-3103" d="M 5869 1409 
L 3659 1409 
L 3659 -434 
L 3156 -434 
L 3156 1409 
L 659 1409 
L 659 1875 
L 1459 1875 
L 1459 3384 
L 3156 3384 
L 3156 4219 
L 1838 4219 
Q 1425 3363 953 2931 
L 550 3256 
Q 1381 3994 1734 5381 
L 2144 5184 
Q 2122 4997 2022 4684 
L 5606 4684 
L 5606 4219 
L 3659 4219 
L 3659 3384 
L 5294 3384 
L 5294 2919 
L 3659 2919 
L 3659 1875 
L 5869 1875 
L 5869 1409 
z
M 3156 1875 
L 3156 2919 
L 1947 2919 
L 1947 1875 
L 3156 1875 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-23fb" d="M 2553 4934 
Q 2391 4238 1856 3447 
Q 1322 2656 703 2194 
L 325 2572 
Q 941 3003 1428 3715 
Q 1916 4428 2094 5147 
L 2553 4934 
z
M 6119 2566 
L 5741 2188 
Q 5122 2647 4587 3439 
Q 4053 4231 3891 4928 
L 4353 5141 
Q 4534 4416 5021 3705 
Q 5509 2994 6119 2566 
z
M 5472 -122 
L 4984 -347 
Q 4916 -106 4703 347 
L 2897 200 
Q 1791 122 1113 31 
L 909 563 
L 1631 622 
Q 2425 1697 2809 3169 
L 3303 3003 
Q 2875 1572 2222 647 
L 4494 800 
Q 4141 1366 3809 1678 
L 4281 1888 
Q 5069 1134 5472 -122 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-318f" d="M 5797 2541 
L 4331 2541 
L 4331 -366 
L 3847 -366 
L 3847 2541 
L 2400 2541 
Q 2416 397 628 -366 
L 231 19 
Q 1919 609 1919 2541 
L 359 2541 
L 359 3009 
L 1913 3009 
L 1913 4525 
L 603 4525 
L 603 4991 
L 5538 4991 
L 5538 4525 
L 4331 4525 
L 4331 3009 
L 5797 3009 
L 5797 2541 
z
M 3847 3009 
L 3847 4525 
L 2400 4525 
L 2400 3009 
L 3847 3009 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-3e6a" d="M 6041 1259 
Q 5956 569 5728 211 
Q 5500 -147 5044 -147 
L 3322 -147 
Q 2663 -147 2663 494 
L 2663 1434 
L 616 1191 
L 556 1678 
L 2663 1925 
L 2663 2875 
L 897 2669 
L 856 3150 
L 2663 3359 
L 2663 4256 
Q 1838 4141 806 4103 
L 506 4588 
Q 2894 4619 5006 5259 
L 5363 4897 
Q 4622 4569 3150 4319 
L 3150 3406 
L 5141 3628 
L 5141 3150 
L 3150 2925 
L 3150 1984 
L 5709 2259 
L 5753 1772 
L 3150 1447 
L 3150 569 
Q 3150 319 3419 319 
L 5081 319 
Q 5309 319 5420 561 
Q 5531 803 5569 1459 
L 6041 1259 
z
" transform="scale(0.015625)"/>
    </defs>
    <use xlink:href="#us-big-ArialUnicodeMS-521d"/>
    <use xlink:href="#us-big-ArialUnicodeMS-5330" transform="translate(100 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-2bb6" transform="translate(200 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-4967" transform="translate(300 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-5153" transform="translate(400 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-19f6" transform="translate(500 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-15" transform="translate(600 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(655.609375 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-14" transform="translate(711.21875 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-18" transform="translate(766.828125 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-ca7" transform="translate(822.4375 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-15" transform="translate(922.4375 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-13" transform="translate(978.046875 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-15" transform="translate(1033.65625 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-17" transform="translate(1089.265625 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-3" transform="translate(1144.875 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-3103" transform="translate(1172.65625 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-23fb" transform="translate(1272.65625 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-318f" transform="translate(1372.65625 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-5153" transform="translate(1472.65625 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-2697" transform="translate(1572.65625 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-3e6a" transform="translate(1672.65625 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-37c5" transform="translate(1772.65625 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-4959" transform="translate(1872.65625 0)"/>
   </g>
  </g>
  <g id="us-big-text_29">
   <!-- 初始两部分各半，此后不互相转钱。未扣交易成本；对照不是母指数。 -->
   <g style="fill: #555555" transform="translate(48.384 592.757859) scale(0.09 -0.09)">
    <defs>
     <path id="us-big-ArialUnicodeMS-20b3" d="M 5831 4525 
L 4091 4525 
L 4091 3706 
L 5472 3706 
L 5472 122 
Q 5472 -88 5315 -213 
Q 5159 -338 4866 -338 
Q 4722 -338 4459 -306 
L 4294 159 
Q 4644 106 4844 106 
Q 5013 106 5013 238 
L 5013 3263 
L 4063 3263 
L 4019 2747 
Q 4647 2319 4953 1797 
L 4569 1447 
Q 4322 1950 3944 2272 
Q 3663 1159 2975 494 
L 2572 813 
Q 3581 1788 3616 3263 
L 2713 3263 
L 2650 2766 
Q 3050 2519 3347 2119 
L 3009 1772 
Q 2784 2128 2572 2266 
Q 2313 1238 1663 666 
L 1300 984 
Q 2144 1728 2209 3263 
L 1247 3263 
L 1247 -391 
L 763 -391 
L 763 3706 
L 2216 3706 
L 2216 4525 
L 397 4525 
L 397 4991 
L 5831 4991 
L 5831 4525 
z
M 3628 3706 
L 3628 4525 
L 2700 4525 
L 2700 3706 
L 3628 3706 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-6377" d="M 3681 4134 
L 622 4134 
L 622 4603 
L 1941 4603 
L 1941 5313 
L 2444 5313 
L 2444 4603 
L 3681 4603 
L 3681 4134 
z
M 5306 2875 
Q 6038 2188 6038 1400 
Q 6038 922 5795 634 
Q 5553 347 5166 384 
L 4756 422 
L 4628 959 
Q 5088 878 5166 878 
Q 5556 878 5556 1356 
Q 5556 2181 4794 2778 
Q 5006 3238 5416 4581 
L 4544 4581 
L 4544 -428 
L 4056 -428 
L 4056 5050 
L 5906 5050 
L 5906 4622 
Q 5484 3350 5306 2875 
z
M 3909 2450 
L 378 2450 
L 378 2919 
L 1588 2919 
Q 1363 3609 997 3922 
L 1422 4097 
Q 1822 3700 2047 3078 
L 1722 2919 
L 2222 2919 
Q 2700 3578 2797 4116 
L 3244 3922 
Q 3106 3459 2753 2919 
L 3909 2919 
L 3909 2450 
z
M 3316 -403 
L 2828 -403 
L 2828 38 
L 1394 38 
L 1394 -403 
L 909 -403 
L 909 1953 
L 3316 1953 
L 3316 -403 
z
M 2828 506 
L 2828 1484 
L 1394 1484 
L 1394 506 
L 2828 506 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-2693" d="M 6088 2247 
L 5797 1772 
Q 4028 2241 3238 2753 
Q 2069 2156 666 1791 
L 366 2222 
Q 1991 2641 2797 3059 
Q 2259 3491 1953 3963 
Q 1500 3394 1019 3072 
L 594 3397 
Q 1075 3650 1547 4219 
Q 2019 4788 2272 5350 
L 2753 5222 
Q 2666 4966 2491 4728 
L 4916 4728 
L 4916 4313 
Q 4403 3541 3700 3047 
Q 4050 2813 4815 2561 
Q 5581 2309 6088 2247 
z
M 4288 4263 
L 2344 4263 
Q 2656 3803 3244 3309 
Q 3941 3797 4288 4263 
z
M 4788 -403 
L 4281 -403 
L 4281 -31 
L 2181 -31 
L 2181 -416 
L 1678 -416 
L 1678 2009 
L 4788 2009 
L 4788 -403 
z
M 4281 434 
L 4281 1544 
L 2181 1544 
L 2181 434 
L 4281 434 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-25d9" d="M 5819 1288 
L 3406 1288 
L 3406 -428 
L 2913 -428 
L 2913 1281 
L 494 1281 
L 488 1753 
L 2913 1753 
L 2913 2491 
L 903 2491 
L 903 2950 
L 2913 2950 
L 2913 5275 
L 3406 5275 
L 3406 2950 
L 5403 2950 
L 5403 2491 
L 3413 2491 
L 3406 1753 
L 5819 1753 
L 5819 1288 
z
M 5478 4775 
Q 5206 3997 4300 3238 
L 3872 3578 
Q 4756 4178 5050 5056 
L 5478 4775 
z
M 2309 3456 
L 1888 3156 
Q 1463 4272 738 4684 
L 1166 4984 
Q 1819 4591 2309 3456 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-19e8" d="M 3541 0 
Q 3541 -397 3389 -606 
Q 3238 -816 3016 -903 
L 2863 -666 
Q 3213 -516 3216 0 
L 2900 0 
L 2900 641 
L 3541 641 
L 3541 0 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-3df3" d="M 6075 941 
Q 6000 509 5851 132 
Q 5703 -244 5388 -244 
L 4197 -244 
Q 3984 -244 3832 -67 
Q 3681 109 3681 331 
L 3681 5147 
L 4184 5147 
L 4184 2894 
Q 4863 3241 5416 3803 
L 5819 3488 
Q 5178 2809 4184 2363 
L 4184 384 
Q 4213 244 4331 244 
L 5253 244 
Q 5472 266 5556 844 
L 5606 1203 
L 6075 941 
z
M 3481 2875 
L 2534 2875 
L 2534 856 
L 3450 1178 
L 3450 653 
L 588 -366 
L 238 84 
L 884 288 
L 884 3891 
L 1388 3891 
L 1388 453 
L 2003 666 
L 2003 5125 
L 2534 5125 
L 2534 3341 
L 3481 3341 
L 3481 2875 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-269d" d="M 5925 3138 
L 1631 3138 
L 1631 1850 
Q 1631 747 709 -384 
L 281 -56 
Q 1147 881 1147 1869 
L 1147 4666 
Q 3191 4666 5275 5403 
L 5613 5025 
Q 3828 4219 1631 4178 
L 1631 3603 
L 5925 3603 
L 5925 3138 
z
M 5388 -409 
L 4903 -409 
L 4903 97 
L 2644 97 
L 2644 -409 
L 2156 -409 
L 2156 2338 
L 5388 2338 
L 5388 -409 
z
M 4903 563 
L 4903 1869 
L 2644 1869 
L 2644 563 
L 4903 563 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-209c" d="M 5900 4434 
L 3834 4434 
Q 3700 4209 3425 3816 
L 3425 -416 
L 2900 -416 
L 2900 3194 
Q 2281 2363 775 1528 
L 453 1947 
Q 1431 2419 2047 2975 
Q 2663 3531 3219 4434 
L 550 4434 
L 550 4922 
L 5900 4922 
L 5900 4434 
z
M 5941 1838 
L 5550 1503 
Q 4619 2634 3597 3078 
L 3938 3419 
Q 4969 2953 5941 1838 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-2121" d="M 5966 -38 
L 500 -38 
L 500 422 
L 4000 422 
L 4197 1491 
L 1947 1491 
L 1844 1019 
L 1338 1094 
L 2081 4500 
L 756 4500 
L 756 4959 
L 5722 4959 
L 5722 4500 
L 2613 4500 
L 2406 3572 
L 5075 3572 
L 4538 422 
L 5953 422 
L 5966 -38 
z
M 4494 3109 
L 2303 3109 
L 2047 1953 
L 4269 1953 
L 4494 3109 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-61fb" d="M 3047 1306 
L 2163 1069 
L 2163 -397 
L 1678 -397 
L 1678 947 
L 575 678 
Q 425 959 341 1147 
Q 819 1203 1678 1416 
L 1678 2150 
L 709 2150 
L 709 2613 
Q 994 3197 1172 3859 
L 469 3859 
L 469 4300 
L 1288 4300 
Q 1400 4688 1509 5288 
L 2003 5172 
L 1806 4300 
L 2894 4300 
L 2894 3859 
L 1684 3859 
Q 1538 3369 1228 2619 
L 1678 2619 
L 1678 3353 
L 2163 3353 
L 2163 2619 
L 3047 2619 
L 3047 2150 
L 2163 2150 
L 2163 1550 
L 3047 1766 
L 3047 1306 
z
M 5984 2753 
L 4109 2753 
Q 3963 2263 3903 2138 
L 5663 2138 
L 5663 1709 
Q 5438 1394 4825 641 
Q 5125 378 5528 -72 
L 5166 -422 
Q 4631 303 3566 909 
L 3872 1241 
L 4422 928 
Q 4850 1434 5019 1672 
L 3384 1672 
L 3384 2088 
Q 3531 2409 3628 2753 
L 2975 2753 
L 2975 3219 
L 3738 3219 
Q 3803 3453 3884 3963 
L 3144 3963 
L 3144 4422 
L 3922 4434 
Q 3975 4722 4006 5281 
L 4513 5184 
L 4434 4428 
L 5663 4428 
L 5663 3963 
L 4391 3963 
Q 4334 3441 4263 3219 
L 5984 3219 
L 5984 2753 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-6740" d="M 2766 4063 
L 1497 4063 
Q 1384 3722 1253 3488 
L 2681 3488 
L 2681 3022 
L 1900 3022 
L 1900 2363 
L 2759 2363 
L 2759 1894 
L 1900 1894 
L 1900 525 
L 2759 953 
L 2759 428 
L 1581 -178 
L 1319 244 
Q 1416 341 1416 447 
L 1416 1894 
L 488 1894 
L 488 2363 
L 1416 2363 
L 1416 3022 
L 991 3022 
Q 838 2781 628 2559 
L 244 2859 
Q 1066 3772 1331 5313 
L 1784 5166 
Q 1728 4822 1638 4531 
L 2766 4531 
L 2766 4063 
z
M 6156 416 
Q 6125 163 5972 -143 
Q 5819 -450 5566 -450 
Q 5306 -450 4931 -89 
Q 4556 272 4372 609 
Q 3363 -163 2706 -416 
L 2369 -25 
Q 3419 397 4109 1031 
Q 3875 1531 3788 2169 
L 2894 2106 
L 2853 2553 
L 3731 2613 
Q 3691 3134 3700 3303 
L 2944 3263 
L 2894 3725 
L 3694 3769 
L 3694 5241 
L 4178 5241 
L 4178 3794 
L 5672 3897 
L 5709 3444 
L 4178 3334 
Q 4178 3222 4213 2650 
L 5806 2753 
L 5844 2303 
L 4263 2194 
Q 4297 1928 4519 1375 
Q 5156 2088 5216 2188 
L 5606 1925 
Q 5322 1466 4750 922 
Q 5069 391 5538 72 
Q 5578 97 5734 659 
L 6156 416 
z
M 5388 4244 
L 5013 3956 
Q 4700 4497 4256 4763 
L 4556 5044 
Q 5166 4694 5388 4244 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-11ed" d="M 1466 1503 
Q 1847 1503 2117 1231 
Q 2388 959 2388 575 
Q 2388 194 2119 -76 
Q 1850 -347 1472 -347 
Q 1091 -347 820 -76 
Q 550 194 550 575 
Q 550 959 819 1231 
Q 1088 1503 1466 1503 
z
M 1469 44 
Q 1691 44 1845 201 
Q 2000 359 2000 581 
Q 2000 803 1844 958 
Q 1688 1113 1469 1113 
Q 1250 1113 1094 958 
Q 938 803 938 581 
Q 938 359 1092 201 
Q 1247 44 1469 44 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-39b9" d="M 6069 556 
L 5778 153 
Q 4128 931 3513 2456 
L 3513 -428 
L 3028 -416 
L 3028 2406 
Q 2241 1053 738 172 
L 416 569 
Q 1828 1384 2491 2491 
L 775 2491 
L 775 2956 
L 3003 2956 
L 3003 3938 
L 1191 3938 
L 1191 4403 
L 3003 4403 
L 3003 5363 
L 3513 5363 
L 3513 4403 
L 5306 4403 
L 5306 3938 
L 3513 3938 
L 3513 2956 
L 5747 2956 
L 5747 2491 
L 3988 2491 
Q 4616 1263 6069 556 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-34f2" d="M 3041 2169 
L 2125 1875 
L 2125 97 
Q 2094 -150 1922 -294 
Q 1750 -438 1113 -403 
L 947 91 
Q 1253 63 1331 63 
Q 1550 63 1584 102 
Q 1619 141 1619 366 
L 1619 1709 
L 781 1388 
L 453 1825 
Q 653 1866 1619 2169 
L 1619 3609 
L 603 3609 
L 603 4078 
L 1619 4078 
L 1619 5313 
L 2125 5313 
L 2125 4078 
L 3041 4078 
L 3041 3609 
L 2125 3609 
L 2125 2356 
L 3041 2656 
L 3041 2169 
z
M 5716 -275 
L 5228 -275 
L 5228 294 
L 3681 294 
L 3681 -275 
L 3194 -275 
L 3194 4800 
L 5716 4800 
L 5716 -275 
z
M 5228 763 
L 5228 4331 
L 3681 4331 
L 3681 763 
L 5228 763 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-2133" d="M 5759 3969 
L 684 3969 
L 684 4428 
L 2956 4428 
L 2956 5259 
L 3444 5259 
L 3444 4428 
L 5759 4428 
L 5759 3969 
z
M 5722 2450 
L 5306 2131 
Q 4831 2956 3603 3525 
L 4056 3841 
Q 5247 3244 5722 2450 
z
M 2644 3553 
Q 2209 2806 978 2175 
L 634 2559 
Q 1816 3119 2291 3841 
L 2644 3553 
z
M 6053 84 
L 5728 -384 
Q 4272 -9 3250 850 
Q 2447 84 763 -416 
L 447 63 
Q 2134 438 2875 1216 
Q 2388 1741 2016 2656 
L 2456 2847 
Q 2816 2025 3225 1550 
Q 3741 2184 4006 2925 
L 4447 2694 
Q 4094 1797 3584 1209 
Q 4456 472 6053 84 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-38a2" d="M 5544 2266 
Q 5475 1613 5370 1036 
Q 5266 459 5189 212 
Q 5113 -34 4948 -161 
Q 4784 -288 4531 -288 
Q 4384 -288 3775 -153 
L 3669 372 
Q 4366 172 4500 172 
Q 4778 172 5013 1797 
L 4488 1797 
Q 4050 484 2394 -428 
L 2041 -56 
Q 3513 706 3969 1797 
L 3272 1797 
Q 2597 575 800 13 
L 481 409 
Q 2078 878 2706 1797 
L 2094 1797 
Q 1491 1344 844 1119 
L 513 1522 
Q 1744 1928 2297 2644 
L 1509 2644 
L 1509 5006 
L 5063 5006 
L 5063 2644 
L 2875 2644 
Q 2688 2359 2547 2266 
L 5544 2266 
z
M 4581 4084 
L 4581 4538 
L 1991 4538 
L 1991 4084 
L 4581 4084 
z
M 4581 3109 
L 4581 3641 
L 1991 3641 
L 1991 3109 
L 4581 3109 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-349f" d="M 6047 806 
Q 6053 666 5929 261 
Q 5806 -144 5709 -276 
Q 5613 -409 5428 -409 
Q 5159 -409 4751 47 
Q 4344 503 4153 947 
Q 3516 272 2859 -128 
L 2419 213 
Q 3338 709 3922 1409 
Q 3591 2216 3438 3769 
L 1516 3769 
L 1516 2900 
L 3225 2900 
Q 3181 1622 3020 1140 
Q 2859 659 2338 659 
Q 2150 659 1819 709 
L 1606 1241 
Q 2009 1119 2363 1119 
Q 2584 1119 2648 1505 
Q 2713 1891 2725 2431 
L 1509 2431 
Q 1481 1084 1270 496 
Q 1059 -91 728 -459 
L 319 -153 
Q 1000 541 1013 2009 
L 1031 4238 
L 3391 4238 
Q 3359 4997 3359 5319 
L 3841 5319 
Q 3850 4619 3878 4238 
L 5747 4238 
L 5747 3769 
L 3909 3769 
Q 4025 2497 4288 1838 
Q 4734 2413 5106 3431 
L 5550 3284 
Q 5113 2075 4500 1325 
Q 4738 869 5008 498 
Q 5278 128 5409 128 
Q 5450 128 5509 462 
Q 5569 797 5575 1081 
L 6047 806 
z
M 5650 4659 
L 5306 4359 
Q 4688 4859 4063 4928 
L 4447 5275 
Q 5144 5119 5650 4659 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-39bb" d="M 6113 1184 
L 5766 775 
Q 5031 1316 4457 1961 
Q 3884 2606 3444 3922 
L 3444 1613 
L 4678 1613 
L 4678 1147 
L 3444 1147 
L 3444 -428 
L 2956 -428 
L 2956 1147 
L 1728 1147 
L 1728 1613 
L 2950 1613 
L 2950 3872 
Q 2413 2063 659 744 
L 263 1125 
Q 1884 2178 2419 3822 
L 641 3822 
L 641 4288 
L 2956 4288 
L 2956 5294 
L 3444 5294 
L 3444 4288 
L 5728 4288 
L 5728 3822 
L 4019 3822 
Q 4450 2203 6113 1184 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-19f7" d="M 3541 2675 
L 2900 2675 
L 2900 3316 
L 3541 3316 
L 3541 2675 
z
M 3541 0 
Q 3541 -397 3389 -606 
Q 3238 -816 3016 -903 
L 2863 -666 
Q 3213 -516 3216 0 
L 2900 0 
L 2900 641 
L 3541 641 
L 3541 0 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-43f6" d="M 5728 5044 
Q 5644 3916 5483 3577 
Q 5322 3238 4966 3238 
Q 4866 3238 4288 3353 
L 4172 3866 
Q 4628 3716 4809 3716 
Q 5059 3716 5106 3981 
L 5216 4575 
L 4347 4575 
Q 4194 3397 2925 3016 
L 2656 3469 
Q 3713 3625 3847 4575 
L 2963 4575 
L 2950 5044 
L 5728 5044 
z
M 2613 1394 
L 2150 1394 
L 2150 1784 
L 1356 1784 
L 1356 1394 
L 872 1394 
L 872 4903 
L 2613 4903 
L 2613 1394 
z
M 2150 3591 
L 2138 4441 
L 1375 4453 
L 1375 3591 
L 2150 3591 
z
M 2150 2253 
L 2150 3122 
L 1356 3122 
L 1356 2253 
L 2150 2253 
z
M 5538 1178 
L 5050 1178 
L 5050 1522 
L 3641 1522 
L 3641 1178 
L 3156 1178 
L 3156 3053 
L 5538 3053 
L 5538 1178 
z
M 5050 1991 
L 5050 2584 
L 3641 2584 
L 3641 1991 
L 5050 1991 
z
M 1766 928 
Q 1563 325 813 -397 
L 428 -84 
Q 1075 447 1381 1153 
L 1766 928 
z
M 6081 -147 
L 5650 -384 
Q 5359 481 4744 909 
L 5222 1119 
Q 5688 716 6081 -147 
z
M 4666 -103 
L 4219 -300 
Q 4056 416 3475 928 
L 3928 1113 
Q 4369 684 4666 -103 
z
M 3169 -128 
L 2719 -281 
Q 2588 434 2081 941 
L 2534 1094 
Q 2931 659 3169 -128 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-38be" d="M 5006 2822 
L 1491 2822 
L 1491 5056 
L 5006 5056 
L 5006 2822 
z
M 4500 4191 
L 4500 4588 
L 1978 4588 
L 1978 4191 
L 4500 4191 
z
M 4500 3291 
L 4500 3725 
L 1978 3725 
L 1978 3291 
L 4500 3291 
z
M 6144 366 
L 5900 -128 
L 3744 -128 
Q 2825 -128 1797 763 
Q 1513 6 709 -422 
L 434 6 
Q 909 228 1190 637 
Q 1472 1047 1491 1875 
L 1966 1797 
Q 1966 1488 1925 1269 
Q 2419 747 2994 544 
L 2994 2047 
L 634 2047 
L 634 2516 
L 5869 2516 
L 5869 2047 
L 3500 2047 
L 3500 1556 
L 5381 1556 
L 5381 1088 
L 3500 1088 
L 3500 397 
Q 3831 338 4013 341 
L 6144 366 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-3e5c" d="M 5959 2650 
L 5141 2650 
Q 5066 1550 5013 1119 
L 5728 1119 
L 5728 634 
L 4959 634 
Q 4900 -125 4673 -273 
Q 4447 -422 4141 -422 
Q 3784 -422 3359 -353 
L 3169 197 
Q 3822 63 4269 63 
Q 4434 63 4469 634 
L 1478 634 
L 1422 341 
L 922 422 
L 1275 2650 
L 494 2650 
L 494 3138 
L 1325 3138 
Q 1450 4009 1550 5013 
L 5338 5013 
Q 5244 3616 5184 3138 
L 5959 3138 
L 5959 2650 
z
M 4806 4525 
L 2759 4525 
Q 3469 4269 4141 3584 
L 3781 3244 
Q 3269 3859 2297 4269 
L 2578 4525 
L 2003 4525 
L 1825 3138 
L 4684 3138 
L 4806 4525 
z
M 4647 2650 
L 2541 2650 
Q 3459 2188 3938 1516 
L 3559 1203 
Q 3028 1900 2119 2406 
L 2438 2650 
L 1759 2650 
Q 1663 1838 1538 1119 
L 4519 1119 
Q 4653 2413 4647 2650 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-3596" d="M 5997 3938 
Q 5863 3278 5667 3089 
Q 5472 2900 5153 2900 
L 3341 2900 
Q 3003 2900 2817 3079 
Q 2631 3259 2631 3584 
L 2631 5306 
L 3138 5306 
L 3138 4288 
Q 4403 4463 5466 5094 
L 5759 4709 
Q 4706 4056 3144 3834 
L 3150 3584 
Q 3159 3366 3384 3366 
L 5172 3366 
Q 5422 3366 5509 4141 
L 5997 3938 
z
M 2541 2069 
L 1791 1772 
L 1791 91 
Q 1744 -400 1166 -409 
L 716 -416 
L 563 84 
L 959 72 
Q 1306 59 1306 275 
L 1306 1594 
Q 919 1422 628 1319 
L 331 1734 
Q 1016 1941 1306 2059 
L 1306 3591 
L 494 3591 
L 494 4056 
L 1306 4056 
L 1306 5306 
L 1791 5306 
L 1791 4056 
L 2484 4056 
L 2484 3591 
L 1791 3591 
L 1791 2247 
Q 2478 2534 2541 2553 
L 2541 2069 
z
M 5606 -409 
L 5119 -409 
L 5119 -38 
L 3213 -38 
L 3213 -434 
L 2725 -434 
L 2725 2491 
L 5606 2491 
L 5606 -409 
z
M 5119 1472 
L 5119 2022 
L 3213 2022 
L 3213 1472 
L 5119 1472 
z
M 5119 428 
L 5119 1006 
L 3213 1006 
L 3213 428 
L 5119 428 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-37ff" d="M 6138 19 
L 5806 -378 
Q 5031 194 4697 716 
Q 4344 144 3328 -441 
L 2981 -50 
Q 3966 434 4403 1153 
Q 4038 1834 3866 2753 
Q 3678 2356 3353 1919 
L 2950 2203 
Q 3838 3172 3963 5253 
L 4409 5125 
Q 4341 4384 4269 4006 
L 5984 4006 
L 5984 3547 
L 5619 3541 
L 5594 3341 
Q 5441 2113 4978 1191 
Q 5281 672 6138 19 
z
M 5166 3541 
L 4172 3541 
Q 4297 2419 4691 1650 
Q 5038 2513 5166 3541 
z
M 3438 3653 
L 2209 3653 
L 2209 2338 
L 1919 2338 
Q 1900 2269 1753 1931 
L 3225 1931 
L 3225 1472 
L 2913 1472 
Q 2763 991 2503 666 
Q 2947 353 3103 184 
L 2747 -172 
Q 2463 138 2150 313 
Q 1322 -225 563 -428 
L 269 6 
Q 1106 163 1684 563 
Q 1291 756 703 884 
L 1038 1472 
L 403 1472 
L 403 1931 
L 1259 1931 
Q 1328 2056 1466 2553 
L 1747 2484 
L 1747 3653 
L 1716 3653 
Q 1413 2881 678 2456 
L 378 2803 
Q 938 3091 1241 3653 
L 403 3653 
L 403 4122 
L 1747 4122 
L 1747 5228 
L 2209 5228 
L 2209 4122 
L 3438 4122 
L 3438 3653 
z
M 2406 1472 
L 1538 1472 
Q 1422 1241 1369 1153 
Q 1388 1159 2069 884 
Q 2219 1031 2406 1472 
z
M 1625 4441 
L 1288 4159 
Q 1022 4547 575 4813 
L 878 5075 
Q 1394 4844 1625 4441 
z
M 3384 4844 
Q 3097 4409 2669 4172 
L 2322 4481 
Q 2806 4759 3047 5069 
L 3384 4844 
z
M 3303 2888 
L 2944 2578 
Q 2706 3025 2291 3297 
L 2584 3566 
Q 2988 3359 3303 2888 
z
" transform="scale(0.015625)"/>
    </defs>
    <use xlink:href="#us-big-ArialUnicodeMS-24ac"/>
    <use xlink:href="#us-big-ArialUnicodeMS-2c5a" transform="translate(100 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-20b3" transform="translate(200 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-6377" transform="translate(300 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-2495" transform="translate(400 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-2693" transform="translate(500 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-25d9" transform="translate(600 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-19e8" transform="translate(700 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-3df3" transform="translate(800 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-269d" transform="translate(900 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-209c" transform="translate(1000 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-2121" transform="translate(1100 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-4987" transform="translate(1200 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-61fb" transform="translate(1300 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-6740" transform="translate(1400 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-11ed" transform="translate(1500 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-39b9" transform="translate(1600 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-34f2" transform="translate(1700 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-2133" transform="translate(1800 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-38a2" transform="translate(1900 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-349f" transform="translate(2000 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-39bb" transform="translate(2100 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-19f7" transform="translate(2200 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-2e88" transform="translate(2300 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-43f6" transform="translate(2400 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-209c" transform="translate(2500 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-38be" transform="translate(2600 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-3e5c" transform="translate(2700 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-3596" transform="translate(2800 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-37ff" transform="translate(2900 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-11ed" transform="translate(3000 0)"/>
   </g>
   <!-- 月末回撤可能小于真实日内跌幅。 -->
   <g style="fill: #555555" transform="translate(48.384 603.432) scale(0.09 -0.09)">
    <defs>
     <path id="us-big-ArialUnicodeMS-267e" d="M 5925 4434 
L 5113 4434 
L 5113 306 
Q 5113 -88 4969 -248 
Q 4825 -409 4678 -409 
L 3700 -409 
L 3513 122 
Q 3706 100 3872 103 
L 4481 116 
Q 4609 116 4609 269 
L 4609 4434 
L 628 4434 
L 628 4922 
L 5925 4922 
L 5925 4434 
z
M 3756 813 
L 3250 813 
L 3250 1288 
L 1925 1288 
L 1925 813 
L 1441 813 
L 1441 3681 
L 3756 3681 
L 3756 813 
z
M 3250 1772 
L 3250 3194 
L 1925 3194 
L 1925 1772 
L 3250 1772 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-538c" d="M 3419 3494 
L 3003 3231 
L 2809 3591 
L 531 3469 
L 403 3963 
L 844 3975 
Q 1316 4656 1644 5403 
L 2131 5191 
Q 1716 4381 1409 3975 
L 2541 4019 
Q 2359 4294 2144 4500 
L 2572 4738 
Q 3122 4225 3419 3494 
z
M 5978 3675 
Q 5825 2528 5294 2528 
L 4122 2528 
Q 3800 2563 3676 2722 
Q 3553 2881 3553 3009 
L 3553 5222 
L 4038 5222 
L 4038 4197 
Q 4997 4469 5556 4909 
L 5850 4544 
Q 5219 4009 4038 3719 
L 4038 3175 
Q 4066 2994 4366 2994 
L 5209 2994 
Q 5431 2994 5509 3853 
L 5978 3675 
z
M 3059 250 
Q 3059 28 2954 -105 
Q 2850 -238 2701 -277 
Q 2553 -316 1972 -306 
L 1791 184 
Q 2147 147 2297 147 
Q 2572 147 2572 319 
L 2572 922 
L 1234 922 
L 1234 -353 
L 750 -353 
L 750 3091 
L 3059 3091 
L 3059 250 
z
M 2572 2241 
L 2572 2625 
L 1234 2625 
L 1234 2241 
L 2572 2241 
z
M 2572 1388 
L 2572 1772 
L 1234 1772 
L 1234 1388 
L 2572 1388 
z
M 6138 800 
Q 6019 134 5831 -73 
Q 5644 -281 5369 -281 
L 4166 -281 
Q 3859 -281 3718 -92 
Q 3578 97 3578 263 
L 3578 2309 
L 4063 2309 
L 4063 1422 
Q 4950 1625 5606 2113 
L 5941 1753 
Q 5169 1163 4063 941 
L 4063 347 
Q 4063 184 4281 184 
L 5319 184 
Q 5469 184 5544 362 
Q 5619 541 5663 1031 
L 6138 800 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-2e9e" d="M 3475 434 
Q 3475 59 3267 -100 
Q 3059 -259 2634 -259 
L 2244 -250 
Q 2147 -250 2069 -256 
L 1856 269 
Q 2253 238 2528 238 
Q 2841 238 2905 281 
Q 2969 325 2969 434 
L 2969 5234 
L 3475 5234 
L 3475 434 
z
M 5931 1709 
L 5472 1484 
Q 5088 2713 4019 3688 
L 4475 3928 
Q 5584 2922 5931 1709 
z
M 2181 3706 
Q 1769 2356 850 1459 
L 453 1791 
Q 1372 2700 1753 3922 
L 2181 3706 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-211d" d="M 5813 2559 
L 3463 2559 
L 3463 72 
Q 3406 -409 2841 -422 
L 2075 -441 
L 1900 109 
L 2669 72 
Q 2938 59 2938 288 
L 2938 2559 
L 569 2559 
L 569 3047 
L 2938 3047 
L 2938 4459 
L 997 4459 
L 997 4947 
L 5363 4947 
L 5363 4459 
L 3463 4459 
L 3463 3047 
L 5813 3047 
L 5813 2559 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-49ae" d="M 5784 4441 
L 3450 4441 
L 3450 4097 
L 5044 4097 
L 5044 1516 
L 1434 1516 
L 1434 4097 
L 2956 4097 
L 2956 4441 
L 575 4441 
L 575 4909 
L 2956 4909 
L 2956 5344 
L 3450 5344 
L 3450 4909 
L 5784 4909 
L 5784 4441 
z
M 4544 3384 
L 4544 3647 
L 1919 3647 
L 1919 3384 
L 4544 3384 
z
M 4544 2694 
L 4544 2944 
L 1919 2944 
L 1919 2694 
L 4544 2694 
z
M 4544 1959 
L 4544 2253 
L 1919 2253 
L 1919 1959 
L 4544 1959 
z
M 5991 756 
L 409 756 
L 409 1222 
L 5991 1222 
L 5991 756 
z
M 5966 -122 
L 5678 -519 
Q 4703 141 3541 341 
L 3816 709 
Q 4922 547 5966 -122 
z
M 2803 366 
Q 1963 -303 709 -538 
L 453 -84 
Q 1528 53 2472 684 
L 2803 366 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-2e2d" d="M 5791 3513 
L 5306 3513 
L 5306 4103 
L 1063 4103 
L 1063 3513 
L 575 3513 
L 575 4569 
L 3144 4569 
Q 2956 4859 2547 5094 
L 2913 5325 
Q 3375 5066 3591 4666 
L 3384 4581 
L 3384 4569 
L 5791 4569 
L 5791 3513 
z
M 3122 3066 
L 2741 2803 
Q 2453 3331 1856 3731 
L 2181 4006 
Q 2759 3669 3122 3066 
z
M 5894 1684 
L 3634 1684 
Q 3063 131 831 -366 
L 469 72 
Q 2528 400 3109 1684 
L 469 1684 
L 469 2150 
L 3256 2150 
Q 3366 2500 3366 3022 
L 3366 3903 
L 3847 3903 
Q 3847 2459 3756 2150 
L 5894 2150 
L 5894 1684 
z
M 2450 2478 
L 2100 2188 
Q 1769 2722 1191 3084 
L 1503 3372 
Q 2100 3031 2450 2478 
z
M 5947 -13 
L 5613 -391 
Q 4900 422 3566 1006 
L 3816 1363 
Q 5075 866 5947 -13 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-3874" d="M 5044 -178 
L 4538 -178 
L 4538 441 
L 2022 441 
L 2022 -206 
L 1516 -206 
L 1516 4781 
L 5044 4781 
L 5044 -178 
z
M 4538 2881 
L 4538 4313 
L 2022 4313 
L 2022 2881 
L 4538 2881 
z
M 4538 909 
L 4538 2413 
L 2022 2413 
L 2022 909 
L 4538 909 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-2414" d="M 5538 84 
Q 5538 -341 4872 -341 
Q 4713 -341 4481 -331 
L 4294 141 
Q 4619 116 4800 116 
Q 5075 116 5075 281 
L 5075 3725 
L 3450 3725 
Q 3450 3322 3413 2938 
Q 4216 2334 4819 1300 
L 4428 1006 
Q 3994 1759 3263 2413 
Q 2831 1444 1772 872 
L 1478 1281 
Q 2225 1684 2600 2196 
Q 2975 2709 2975 3725 
L 1325 3725 
L 1325 -409 
L 838 -409 
L 838 4191 
L 3009 4191 
L 3009 5275 
L 3469 5275 
L 3469 4191 
L 5538 4191 
L 5538 84 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-605b" d="M 6241 38 
Q 6175 -75 5919 -378 
Q 5316 -34 4970 506 
Q 4625 1047 4453 2041 
Q 4016 291 2450 -366 
L 2069 6 
Q 2934 406 3345 897 
Q 3756 1388 3969 2266 
L 2772 2266 
L 2772 2731 
L 4044 2731 
Q 4081 2978 4122 3756 
L 3553 3756 
Q 3344 3197 3022 2797 
L 2597 3059 
Q 3297 4028 3256 4966 
L 3725 4856 
Q 3725 4641 3675 4225 
L 4128 4225 
L 4128 5403 
L 4616 5363 
L 4616 4225 
L 5728 4225 
L 5728 3756 
L 4603 3756 
Q 4563 3072 4525 2731 
L 5991 2731 
L 5991 2266 
L 4903 2266 
Q 5003 1538 5367 914 
Q 5731 291 6241 38 
z
M 2841 672 
Q 2372 531 1605 234 
Q 838 -63 666 -122 
L 331 306 
L 775 428 
L 775 2669 
L 1259 2669 
L 1259 588 
L 1600 722 
L 1600 3169 
L 825 3169 
L 825 5094 
L 2572 5094 
L 2572 3169 
L 2088 3169 
L 2088 2509 
L 2706 2509 
L 2706 2041 
L 2088 2041 
L 2088 903 
L 2841 1172 
L 2841 672 
z
M 2113 3634 
L 2113 4628 
L 1313 4628 
L 1313 3634 
L 2113 3634 
z
" transform="scale(0.015625)"/>
     <path id="us-big-ArialUnicodeMS-30d4" d="M 2528 1478 
Q 2528 1294 2429 1178 
Q 2331 1063 2187 1048 
Q 2044 1034 1819 1025 
L 1747 1369 
L 1747 -441 
L 1269 -441 
L 1269 3572 
L 1031 3572 
L 1031 891 
L 544 891 
L 544 4038 
L 1269 4038 
L 1269 5306 
L 1753 5306 
L 1753 4038 
L 2528 4038 
L 2528 1478 
z
M 2041 1644 
L 2041 3572 
L 1753 3572 
L 1753 1503 
Q 2041 1484 2041 1644 
z
M 5913 4556 
L 2400 4556 
L 2400 5025 
L 5913 5025 
L 5913 4556 
z
M 5363 2881 
L 3022 2881 
L 3022 4306 
L 5363 4306 
L 5363 2881 
z
M 4878 3347 
L 4878 3841 
L 3506 3841 
L 3506 3347 
L 4878 3347 
z
M 5619 -416 
L 5131 -416 
L 5131 -38 
L 3231 -38 
L 3231 -441 
L 2747 -441 
L 2747 2566 
L 5619 2566 
L 5619 -416 
z
M 5131 1516 
L 5131 2100 
L 4428 2100 
L 4428 1516 
L 5131 1516 
z
M 3944 1516 
L 3944 2100 
L 3231 2100 
L 3231 1516 
L 3944 1516 
z
M 5131 428 
L 5131 1050 
L 4428 1050 
L 4428 428 
L 5131 428 
z
M 3944 428 
L 3944 1050 
L 3231 1050 
L 3231 428 
L 3944 428 
z
" transform="scale(0.015625)"/>
    </defs>
    <use xlink:href="#us-big-ArialUnicodeMS-3997"/>
    <use xlink:href="#us-big-ArialUnicodeMS-39ba" transform="translate(100 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-296d" transform="translate(200 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-3733" transform="translate(300 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-267e" transform="translate(400 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-538c" transform="translate(500 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-2e9e" transform="translate(600 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-211d" transform="translate(700 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-49ae" transform="translate(800 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-2e2d" transform="translate(900 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-3874" transform="translate(1000 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-2414" transform="translate(1100 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-605b" transform="translate(1200 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-30d4" transform="translate(1300 0)"/>
    <use xlink:href="#us-big-ArialUnicodeMS-11ed" transform="translate(1400 0)"/>
   </g>
  </g>
 </g>
 <defs>
  <clipPath id="us-big-p1eaef6550d">
   <rect x="49.819609" y="79.919375" width="544.180391" height="133.206286"/>
  </clipPath>
  <clipPath id="us-big-pa8059fe9ef">
   <rect x="49.819609" y="227.425661" width="544.180391" height="173.168171"/>
  </clipPath>
  <clipPath id="us-big-pc148d70ea4">
   <rect x="49.819609" y="414.893832" width="544.180391" height="133.206286"/>
  </clipPath>
 </defs>
</svg>


<svg style="display:block;max-width:100%;height:auto" xmlns:xlink="http://www.w3.org/1999/xlink" width="100%" height="auto" viewBox="0 0 604.8 612" xmlns="http://www.w3.org/2000/svg" version="1.1">
 <metadata>
  <rdf:RDF xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:cc="http://creativecommons.org/ns#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
   <cc:Work>
    <dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage"/>
    <dc:date>2026-10-24T13:56:20.716318</dc:date>
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
 <g id="us-small-figure_1">
  <g id="us-small-patch_1">
   <path d="M 0 612 
L 604.8 612 
L 604.8 0 
L 0 0 
z
" style="fill: #fbfaf7"/>
  </g>
  <g id="us-small-axes_1">
   <g id="us-small-patch_2">
    <path d="M 49.819609 213.125661 
L 594 213.125661 
L 594 79.919375 
L 49.819609 79.919375 
z
" style="fill: #fbfaf7"/>
   </g>
   <g id="us-small-matplotlib.axis_1">
    <g id="us-small-xtick_1">
     <g id="us-small-line2d_1">
      <path d="M 124.120824 213.125661 
L 124.120824 79.919375 
" clip-path="url(#us-small-pa95c6f6faf)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_2">
      <defs>
       <path id="us-small-m43d5373113" d="M 0 0 
L 0 3.5 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#us-small-m43d5373113" x="124.120824" y="213.125661" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-small-xtick_2">
     <g id="us-small-line2d_3">
      <path d="M 223.116884 213.125661 
L 223.116884 79.919375 
" clip-path="url(#us-small-pa95c6f6faf)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_4">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="223.116884" y="213.125661" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-small-xtick_3">
     <g id="us-small-line2d_5">
      <path d="M 321.977517 213.125661 
L 321.977517 79.919375 
" clip-path="url(#us-small-pa95c6f6faf)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_6">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="321.977517" y="213.125661" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-small-xtick_4">
     <g id="us-small-line2d_7">
      <path d="M 420.973577 213.125661 
L 420.973577 79.919375 
" clip-path="url(#us-small-pa95c6f6faf)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_8">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="420.973577" y="213.125661" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-small-xtick_5">
     <g id="us-small-line2d_9">
      <path d="M 519.834211 213.125661 
L 519.834211 79.919375 
" clip-path="url(#us-small-pa95c6f6faf)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_10">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="519.834211" y="213.125661" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
   </g>
   <g id="us-small-matplotlib.axis_2">
    <g id="us-small-ytick_1">
     <g id="us-small-line2d_11">
      <path d="M 49.819609 199.162538 
L 594 199.162538 
" clip-path="url(#us-small-pa95c6f6faf)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_12">
      <defs>
       <path id="us-small-m29506b5bad" d="M 0 0 
L -3.5 0 
" style="stroke: #000000; stroke-width: 0.8"/>
      </defs>
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="199.162538" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_1">
      <!-- 0 -->
      <g transform="translate(37.258672 202.802675) scale(0.1 -0.1)">
       <defs>
        <path id="us-small-ArialUnicodeMS-13" d="M 1778 4603 
Q 3272 4603 3272 2259 
Q 3272 1075 2886 498 
Q 2500 -78 1778 -78 
Q 288 -78 288 2259 
Q 288 3444 673 4023 
Q 1059 4603 1778 4603 
z
M 1778 384 
Q 2231 384 2462 823 
Q 2694 1263 2694 2259 
Q 2694 2953 2592 3351 
Q 2491 3750 2286 3945 
Q 2081 4141 1772 4141 
Q 1319 4141 1091 3694 
Q 863 3247 863 2259 
Q 863 1575 966 1175 
Q 1069 775 1272 579 
Q 1475 384 1778 384 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-small-ArialUnicodeMS-13"/>
      </g>
     </g>
    </g>
    <g id="us-small-ytick_2">
     <g id="us-small-line2d_13">
      <path d="M 49.819609 172.275077 
L 594 172.275077 
" clip-path="url(#us-small-pa95c6f6faf)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_14">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="172.275077" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_2">
      <!-- 10 -->
      <g transform="translate(31.697734 175.915214) scale(0.1 -0.1)">
       <defs>
        <path id="us-small-ArialUnicodeMS-14" d="M 2400 0 
L 1838 0 
L 1838 3584 
Q 1416 3184 709 2906 
L 709 3450 
Q 1681 3916 2034 4603 
L 2400 4603 
L 2400 0 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-small-ArialUnicodeMS-14"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-ytick_3">
     <g id="us-small-line2d_15">
      <path d="M 49.819609 145.387617 
L 594 145.387617 
" clip-path="url(#us-small-pa95c6f6faf)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_16">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="145.387617" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_3">
      <!-- 20 -->
      <g transform="translate(31.697734 149.027753) scale(0.1 -0.1)">
       <defs>
        <path id="us-small-ArialUnicodeMS-15" d="M 3231 0 
L 197 0 
Q 197 388 467 784 
Q 738 1181 1478 1778 
Q 1931 2141 2287 2539 
Q 2644 2938 2644 3341 
Q 2644 3688 2398 3914 
Q 2153 4141 1778 4141 
Q 1400 4141 1144 3908 
Q 888 3675 884 3213 
L 306 3278 
Q 359 3922 764 4262 
Q 1169 4603 1791 4603 
Q 2466 4603 2842 4229 
Q 3219 3856 3219 3328 
Q 3219 2888 2901 2436 
Q 2584 1984 1638 1228 
Q 1141 831 978 544 
L 3231 544 
L 3231 0 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-small-ArialUnicodeMS-15"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-ytick_4">
     <g id="us-small-line2d_17">
      <path d="M 49.819609 118.500156 
L 594 118.500156 
" clip-path="url(#us-small-pa95c6f6faf)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_18">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="118.500156" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_4">
      <!-- 30 -->
      <g transform="translate(31.697734 122.140293) scale(0.1 -0.1)">
       <defs>
        <path id="us-small-ArialUnicodeMS-16" d="M 2425 2478 
Q 2850 2397 3067 2067 
Q 3284 1738 3284 1350 
Q 3284 725 2829 323 
Q 2375 -78 1741 -78 
Q 1134 -78 740 275 
Q 347 628 281 1209 
L 844 1288 
Q 928 834 1151 609 
Q 1375 384 1741 384 
Q 2134 384 2407 661 
Q 2681 938 2681 1338 
Q 2681 1722 2432 1975 
Q 2184 2228 1784 2228 
Q 1622 2228 1388 2169 
L 1453 2663 
Q 1678 2663 1809 2684 
Q 1941 2706 2103 2790 
Q 2266 2875 2372 3033 
Q 2478 3191 2478 3425 
Q 2478 3766 2251 3953 
Q 2025 4141 1728 4141 
Q 1388 4141 1173 3925 
Q 959 3709 903 3309 
L 341 3413 
Q 450 4009 823 4306 
Q 1197 4603 1716 4603 
Q 2288 4603 2670 4258 
Q 3053 3913 3053 3413 
Q 3053 2772 2425 2491 
L 2425 2478 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-small-ArialUnicodeMS-16"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-ytick_5">
     <g id="us-small-line2d_19">
      <path d="M 49.819609 91.612695 
L 594 91.612695 
" clip-path="url(#us-small-pa95c6f6faf)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_20">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="91.612695" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_5">
      <!-- 40 -->
      <g transform="translate(31.697734 95.252832) scale(0.1 -0.1)">
       <defs>
        <path id="us-small-ArialUnicodeMS-17" d="M 3263 1094 
L 2644 1094 
L 2644 0 
L 2081 0 
L 2081 1094 
L 97 1094 
L 97 1613 
L 2181 4581 
L 2644 4581 
L 2644 1613 
L 3263 1613 
L 3263 1094 
z
M 2081 1613 
L 2081 3681 
L 2069 3681 
L 647 1613 
L 2081 1613 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-small-ArialUnicodeMS-17"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-text_6">
     <!-- 百分点 -->
     <g transform="translate(25.598125 161.522518) rotate(-90) scale(0.1 -0.1)">
      <defs>
       <path id="us-small-ArialUnicodeMS-490d" d="M 5850 4506 
L 3572 4506 
Q 3538 4184 3372 3725 
L 5088 3725 
L 5088 -409 
L 4581 -409 
L 4581 91 
L 1941 91 
L 1941 -428 
L 1434 -428 
L 1434 3725 
L 2822 3725 
Q 3000 4009 3066 4506 
L 628 4506 
L 628 4991 
L 5850 4991 
L 5850 4506 
z
M 4581 2175 
L 4581 3238 
L 1941 3238 
L 1941 2175 
L 4581 2175 
z
M 4581 575 
L 4581 1691 
L 1941 1691 
L 1941 575 
L 4581 575 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-2495" d="M 5991 3003 
L 5684 2553 
Q 4856 3041 4451 3534 
Q 4047 4028 3781 4831 
L 4319 4984 
Q 4375 4356 4829 3825 
Q 5284 3294 5991 3003 
z
M 2613 4697 
Q 2169 3484 800 2547 
L 416 2919 
Q 1731 3741 2188 4934 
L 2613 4697 
z
M 4872 2931 
Q 4844 1956 4730 1092 
Q 4616 228 4430 7 
Q 4244 -213 3847 -213 
Q 3469 -213 2894 -78 
L 2747 481 
Q 3503 269 3834 269 
Q 4013 269 4128 639 
Q 4244 1009 4341 2463 
L 3138 2463 
Q 2869 263 831 -441 
L 525 -31 
Q 2372 478 2631 2463 
L 1556 2463 
L 1556 2931 
L 4872 2931 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-4348" d="M 5522 4225 
L 3213 4225 
L 3213 3597 
L 4972 3597 
L 4972 1459 
L 1338 1459 
L 1338 3597 
L 2725 3597 
L 2725 5313 
L 3213 5313 
L 3213 4666 
L 5522 4666 
L 5522 4225 
z
M 4513 1900 
L 4513 3156 
L 1825 3156 
L 1825 1900 
L 4513 1900 
z
M 6081 -56 
L 5619 -325 
Q 5188 509 4544 1031 
L 4922 1288 
Q 5672 631 6081 -56 
z
M 1856 1044 
Q 1550 141 763 -453 
L 319 -91 
Q 1059 356 1447 1247 
L 1850 1044 
L 1856 1044 
z
M 4538 -109 
L 4072 -288 
Q 3759 481 3272 997 
L 3681 1197 
Q 4216 653 4538 -109 
z
M 3200 -134 
L 2700 -275 
Q 2519 444 2047 1013 
L 2463 1184 
Q 2925 600 3200 -134 
z
" transform="scale(0.015625)"/>
      </defs>
      <use xlink:href="#us-small-ArialUnicodeMS-490d"/>
      <use xlink:href="#us-small-ArialUnicodeMS-2495" transform="translate(100 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-4348" transform="translate(200 0)"/>
     </g>
    </g>
   </g>
   <g id="us-small-line2d_21">
    <path d="M 74.555082 199.162538 
L 78.753273 199.491405 
L 82.545188 201.506046 
L 86.743379 203.438069 
L 90.806145 201.892953 
L 95.004336 201.833736 
L 99.067102 202.643128 
L 103.265293 207.070829 
L 107.463484 203.869503 
L 111.52625 205.657402 
L 115.724442 203.433455 
L 119.787207 202.670418 
L 123.985399 202.303143 
L 128.18359 201.05627 
L 132.11093 204.522413 
L 136.309121 200.874019 
L 140.371887 197.310801 
L 144.570079 198.105639 
L 148.632844 197.851457 
L 152.831036 197.101297 
L 157.029227 195.342756 
L 161.091993 195.004205 
L 165.290184 193.621285 
L 169.35295 194.252002 
L 173.551141 194.378485 
L 177.749332 192.369161 
L 181.541247 192.332343 
L 185.739438 188.899139 
L 189.802204 189.110876 
L 194.000395 188.55363 
L 198.063161 189.685091 
L 202.261353 189.661233 
L 206.459544 188.802074 
L 210.52231 187.005813 
L 214.720501 186.764169 
L 218.783267 190.793843 
L 222.981458 190.097526 
L 227.179649 188.548298 
L 230.971564 189.361388 
L 235.169755 190.853043 
L 239.232521 191.860409 
L 243.430712 196.714268 
L 247.493478 199.519385 
L 251.69167 199.862694 
L 255.889861 197.245286 
L 259.952627 198.13328 
L 264.150818 194.472387 
L 268.213584 194.304302 
L 272.411775 190.4465 
L 276.609966 193.45415 
L 280.401881 194.169153 
L 284.600072 194.655712 
L 288.662838 196.627764 
L 292.861029 195.686161 
L 296.923795 198.62278 
L 301.121986 198.347239 
L 305.320178 198.95342 
L 309.382944 199.728785 
L 313.581135 200.808773 
L 317.643901 195.324554 
L 321.842092 194.472403 
L 326.040283 198.340607 
L 329.967623 202.016856 
L 334.165815 192.022022 
L 338.228581 190.122495 
L 342.426772 190.932721 
L 346.489538 188.146092 
L 350.687729 190.780882 
L 354.88592 190.847894 
L 358.948686 188.849408 
L 363.146877 186.047528 
L 367.209643 191.184163 
L 371.407834 195.744365 
L 375.606026 189.14774 
L 379.39794 183.189362 
L 383.596132 182.256537 
L 387.658897 179.118494 
L 391.857089 178.711481 
L 395.919855 183.486848 
L 400.118046 182.993961 
L 404.316237 186.315432 
L 408.379003 184.604515 
L 412.577194 190.018731 
L 416.63996 190.530064 
L 420.838151 188.804655 
L 425.036343 190.556404 
L 428.828257 180.467607 
L 433.026449 181.517059 
L 437.089214 182.665673 
L 441.287406 181.457348 
L 445.350172 199.215605 
L 449.548363 194.178321 
L 453.746554 191.18171 
L 457.80932 194.967041 
L 462.007511 191.799194 
L 466.070277 193.561039 
L 470.268468 194.748138 
L 474.46666 191.722602 
L 478.258574 202.560321 
L 482.456766 203.996855 
L 486.519531 197.368623 
L 490.717723 192.898406 
L 494.780488 191.262865 
L 498.97868 185.906794 
L 503.176871 190.380791 
L 507.239637 187.78981 
L 511.437828 182.224092 
L 515.500594 164.597785 
L 519.698785 162.105161 
L 523.896977 162.308351 
L 527.824317 151.051882 
L 532.022508 139.8154 
L 536.085274 150.571034 
L 540.283465 120.377566 
L 544.346231 122.137577 
L 548.544422 107.961081 
L 552.742614 98.30963 
L 556.805379 86.732841 
L 561.003571 93.096967 
L 565.066336 85.974206 
L 569.264528 90.980801 
" clip-path="url(#us-small-pa95c6f6faf)" style="fill: none; stroke: #006f73; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="us-small-line2d_22">
    <path d="M 49.819609 199.162538 
L 594 199.162538 
" clip-path="url(#us-small-pa95c6f6faf)" style="fill: none; stroke: #656565; stroke-width: 0.7; stroke-linecap: square"/>
   </g>
   <g id="us-small-patch_3">
    <path d="M 49.819609 213.125661 
L 49.819609 79.919375 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="us-small-patch_4">
    <path d="M 49.819609 213.125661 
L 594 213.125661 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="us-small-text_7">
    <!-- 先看增量：新组合相对“盈利 + 动量”的累计收益差 -->
    <g transform="translate(49.819609 73.919375) scale(0.12 -0.12)">
     <defs>
      <path id="us-small-ArialUnicodeMS-23d7" d="M 5978 1050 
Q 5834 238 5676 45 
Q 5519 -147 5275 -147 
L 4191 -147 
Q 3884 -100 3746 106 
Q 3609 313 3609 453 
L 3609 2388 
L 2956 2388 
Q 2872 1259 2420 645 
Q 1969 31 878 -428 
L 569 -19 
Q 1584 422 2020 987 
Q 2456 1553 2456 2388 
L 850 2388 
L 850 2853 
L 3091 2853 
L 3091 3803 
L 1919 3803 
Q 1684 3388 1281 2938 
L 863 3206 
Q 1656 4019 1778 5025 
L 2247 4903 
Q 2231 4741 2100 4269 
L 3091 4269 
L 3091 5363 
L 3578 5369 
L 3578 4269 
L 5253 4269 
L 5253 3803 
L 3603 3803 
L 3603 2853 
L 5759 2853 
L 5759 2388 
L 4097 2388 
L 4097 563 
Q 4097 319 4300 319 
L 5228 319 
Q 5306 338 5370 466 
Q 5434 594 5569 1197 
L 5978 1050 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-499a" d="M 5838 3041 
L 2713 3041 
L 2484 2753 
L 5044 2753 
L 5044 -403 
L 4556 -403 
L 4556 -63 
L 2247 -63 
L 2247 -428 
L 1759 -428 
L 1759 2028 
Q 1181 1575 794 1350 
L 453 1759 
Q 1453 2284 2069 3041 
L 703 3041 
L 703 3475 
L 2381 3475 
Q 2466 3591 2547 3803 
L 1241 3803 
L 1241 4238 
L 2719 4238 
Q 2769 4369 2791 4481 
Q 1438 4403 1119 4403 
L 903 4856 
Q 3616 4878 5141 5234 
L 5350 4856 
Q 4363 4597 3297 4519 
Q 3259 4334 3213 4238 
L 5197 4238 
L 5197 3803 
L 3091 3803 
Q 3025 3591 2963 3475 
L 5838 3475 
L 5838 3041 
z
M 4556 1978 
L 4556 2284 
L 2247 2284 
L 2247 1978 
L 4556 1978 
z
M 4556 1216 
L 4556 1544 
L 2247 1544 
L 2247 1216 
L 4556 1216 
z
M 4556 409 
L 4556 781 
L 2247 781 
L 2247 409 
L 4556 409 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-2b2d" d="M 6150 4122 
L 5806 3738 
L 5538 3916 
L 5538 2328 
L 2613 2328 
L 2613 4006 
Q 2384 3853 2234 3763 
L 1875 4141 
Q 2216 4300 2650 4664 
Q 3084 5028 3250 5313 
L 3653 5019 
Q 3500 4719 2994 4294 
L 5063 4294 
Q 4538 4741 4347 5013 
L 4756 5313 
Q 5306 4622 6150 4122 
z
M 5050 2797 
L 5050 3828 
L 4294 3828 
L 4294 2797 
L 5050 2797 
z
M 5044 3494 
Q 4969 3178 4684 2828 
L 4325 3091 
Q 4597 3397 4653 3675 
L 5044 3494 
z
M 3841 2797 
L 3841 3828 
L 3097 3828 
L 3097 2797 
L 3841 2797 
z
M 3816 3053 
L 3431 2869 
Q 3338 3281 3122 3541 
L 3519 3731 
Q 3731 3534 3816 3053 
z
M 2503 1319 
L 672 647 
L 331 1081 
Q 822 1194 1259 1350 
L 1259 3103 
L 544 3103 
L 544 3572 
L 1259 3572 
L 1259 5141 
L 1747 5141 
L 1747 3572 
L 2456 3572 
L 2456 3103 
L 1747 3103 
L 1747 1538 
L 2503 1806 
L 2503 1319 
z
M 5344 -397 
L 4856 -397 
L 4856 -31 
L 3334 -31 
L 3334 -397 
L 2847 -397 
L 2847 2169 
L 5344 2169 
L 5344 -397 
z
M 4856 1325 
L 4856 1703 
L 3334 1703 
L 3334 1325 
L 4856 1325 
z
M 4856 434 
L 4856 856 
L 3334 856 
L 3334 434 
L 4856 434 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-645e" d="M 5056 3378 
L 1313 3378 
L 1313 5050 
L 5056 5050 
L 5056 3378 
z
M 4569 4403 
L 4569 4609 
L 1797 4609 
L 1797 4403 
L 4569 4403 
z
M 4569 3794 
L 4569 4031 
L 1797 4031 
L 1797 3794 
L 4569 3794 
z
M 5797 2816 
L 581 2816 
L 581 3231 
L 5797 3231 
L 5797 2816 
z
M 6059 -191 
L 341 -191 
L 341 275 
L 2950 275 
L 2950 459 
L 897 459 
L 897 878 
L 2950 878 
L 2950 1044 
L 1125 1044 
L 1125 2669 
L 5269 2669 
L 5269 1044 
L 3438 1044 
L 3438 878 
L 5509 878 
L 5509 459 
L 3438 459 
L 3438 275 
L 6059 275 
L 6059 -191 
z
M 4781 2053 
L 4781 2253 
L 3438 2253 
L 3438 2053 
L 4781 2053 
z
M 2950 2053 
L 2950 2253 
L 1613 2253 
L 1613 2053 
L 2950 2053 
z
M 4781 1459 
L 4781 1697 
L 3438 1697 
L 3438 1459 
L 4781 1459 
z
M 2950 1459 
L 2950 1697 
L 1613 1697 
L 1613 1459 
L 2950 1459 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-19f6" d="M 3516 2675 
L 2875 2675 
L 2875 3316 
L 3516 3316 
L 3516 2675 
z
M 3516 0 
L 2875 0 
L 2875 641 
L 3516 641 
L 3516 0 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-383f" d="M 6041 2938 
L 5300 2938 
L 5300 -397 
L 4813 -397 
L 4813 2938 
L 4109 2938 
L 4109 2216 
Q 4109 700 3334 -359 
L 2906 -72 
Q 3622 853 3622 2456 
L 3622 4709 
Q 4644 4825 5544 5313 
L 5850 4916 
Q 5141 4503 4109 4319 
L 4109 3406 
L 6041 3406 
L 6041 2938 
z
M 3353 4184 
L 525 4184 
L 525 4653 
L 1716 4653 
L 1716 5281 
L 2222 5281 
L 2222 4653 
L 3353 4653 
L 3353 4184 
z
M 3406 2719 
L 2203 2719 
L 2203 2144 
L 3250 2144 
L 3250 1678 
L 2203 1678 
L 2203 1428 
L 2456 1619 
Q 2981 1281 3309 744 
L 2950 416 
Q 2672 931 2203 1281 
L 2203 -397 
L 1716 -397 
L 1716 1253 
Q 1316 625 703 178 
L 347 550 
Q 1003 959 1409 1678 
L 628 1678 
L 628 2144 
L 1716 2144 
L 1716 2719 
L 453 2719 
L 453 3188 
L 1325 3188 
Q 1147 3659 884 3975 
L 1306 4147 
Q 1631 3813 1806 3188 
L 2228 3188 
Q 2422 3559 2584 4147 
L 3047 3969 
Q 2906 3544 2719 3188 
L 3406 3188 
L 3406 2719 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-5153" d="M 2509 1619 
Q 853 1231 622 1147 
L 391 1575 
Q 1022 2209 1306 2625 
L 1294 2638 
Q 1284 2631 1023 2561 
Q 763 2491 609 2438 
L 366 2881 
Q 853 3669 1441 5166 
L 1875 4966 
Q 1300 3650 947 3022 
L 1619 3163 
Q 1797 3416 2047 3922 
L 2503 3719 
Q 1863 2416 1153 1772 
L 1166 1759 
L 2509 2053 
L 2509 1619 
z
M 5919 -91 
L 2150 -91 
L 2150 378 
L 2881 378 
L 2881 4941 
L 5184 4941 
L 5184 378 
L 5919 378 
L 5919 -91 
z
M 4697 3469 
L 4697 4475 
L 3366 4475 
L 3366 3469 
L 4697 3469 
z
M 4697 1972 
L 4697 3028 
L 3366 3028 
L 3366 1972 
L 4697 1972 
z
M 4697 378 
L 4697 1528 
L 3366 1528 
L 3366 378 
L 4697 378 
z
M 2650 691 
L 647 19 
L 409 459 
Q 2306 1044 2650 1172 
L 2650 691 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-2697" d="M 6119 2925 
L 5797 2497 
Q 5525 2603 5015 2934 
Q 4506 3266 4200 3555 
Q 3894 3844 3200 4659 
Q 2319 3578 603 2419 
L 256 2803 
Q 2228 4103 3175 5497 
L 3647 5178 
L 3450 4978 
Q 3994 4306 4803 3698 
Q 5613 3091 6119 2925 
z
M 4691 2597 
L 1638 2597 
L 1638 3084 
L 4691 3084 
L 4691 2597 
z
M 5063 -434 
L 4556 -434 
L 4556 -38 
L 1838 -38 
L 1838 -469 
L 1331 -469 
L 1331 1906 
L 5063 1906 
L 5063 -434 
z
M 4556 447 
L 4556 1441 
L 1838 1441 
L 1838 447 
L 4556 447 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-4987" d="M 3009 1791 
L 2566 1503 
Q 2322 1975 2003 2406 
L 2003 -416 
L 1509 -416 
L 1509 2094 
Q 1313 1497 659 678 
L 275 972 
Q 1053 1969 1459 3603 
L 519 3603 
L 519 4072 
L 1516 4072 
L 1516 5300 
L 2003 5300 
L 2003 4072 
L 2881 4072 
L 2881 3603 
L 2003 3603 
L 2003 2900 
L 2131 2975 
Q 2681 2434 3009 1791 
z
M 5691 -416 
L 5178 -416 
L 5178 38 
L 3659 38 
L 3659 -416 
L 3150 -416 
L 3150 4966 
L 5691 4966 
L 5691 -416 
z
M 5178 3547 
L 5178 4500 
L 3659 4500 
L 3659 3547 
L 5178 3547 
z
M 5178 2059 
L 5178 3078 
L 3659 3078 
L 3659 2059 
L 5178 2059 
z
M 5178 506 
L 5178 1594 
L 3659 1594 
L 3659 506 
L 5178 506 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-2e88" d="M 5856 3616 
L 5247 3616 
L 5247 38 
Q 5206 -163 5042 -273 
Q 4878 -384 4806 -384 
L 4103 -384 
L 3944 103 
Q 4438 63 4678 63 
Q 4716 63 4763 134 
L 4763 3616 
L 2988 3616 
L 2988 4084 
L 4763 4084 
L 4763 5306 
L 5247 5306 
L 5247 4084 
L 5856 4084 
L 5856 3616 
z
M 3175 366 
L 2694 153 
Q 2422 1059 2100 1538 
Q 1609 353 525 -384 
L 153 -13 
Q 1288 719 1813 1984 
Q 1306 2706 628 3256 
L 984 3541 
Q 1794 2828 2009 2497 
Q 2341 3403 2381 4116 
L 359 4116 
L 359 4556 
L 2869 4556 
Q 2844 3303 2328 2028 
Q 2866 1222 3175 366 
z
M 4441 1453 
L 3988 1178 
Q 3663 2072 3091 2700 
L 3444 2950 
Q 4084 2334 4441 1453 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-caf" d="M 1900 4441 
Q 1559 4303 1556 3816 
L 1850 3816 
L 1850 3163 
L 1247 3163 
L 1247 3675 
Q 1247 3897 1273 4061 
Q 1300 4225 1412 4389 
Q 1525 4553 1759 4659 
L 1900 4441 
z
M 928 4441 
Q 588 4303 581 3816 
L 878 3816 
L 878 3163 
L 275 3163 
L 275 3675 
Q 275 3897 301 4061 
Q 328 4225 439 4389 
Q 550 4553 788 4659 
L 928 4441 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-4957" d="M 5650 4178 
Q 5625 2825 5476 2414 
Q 5328 2003 4813 2003 
Q 4644 2003 4422 2041 
L 4306 2534 
Q 4731 2466 4838 2466 
Q 5063 2466 5088 2834 
L 5153 3713 
L 4488 3713 
L 4366 3413 
L 4197 3463 
Q 4066 3006 3738 2625 
Q 3875 2547 4306 2209 
L 3969 1831 
Q 3641 2138 3372 2291 
Q 2800 1913 2047 1778 
L 1759 2228 
Q 2581 2353 2888 2547 
Q 2634 2678 2106 2725 
L 2419 3122 
Q 2784 3097 3322 2859 
Q 3541 3078 3616 3272 
L 2322 3272 
L 2322 3738 
L 3956 3738 
L 4225 4531 
L 2375 4531 
Q 2306 3400 1945 2736 
Q 1584 2072 813 1563 
L 416 1947 
Q 1184 2388 1523 2988 
Q 1863 3588 1869 4531 
L 909 4531 
L 909 5019 
L 4813 5019 
Q 4763 4691 4609 4178 
L 5650 4178 
z
M 6094 -244 
L 378 -244 
L 378 225 
L 1106 225 
L 1106 1656 
L 5381 1656 
L 5381 225 
L 6094 225 
L 6094 -244 
z
M 4897 225 
L 4897 1191 
L 4128 1191 
L 4128 225 
L 4897 225 
z
M 3641 225 
L 3641 1191 
L 2859 1191 
L 2859 225 
L 3641 225 
z
M 2375 225 
L 2375 1191 
L 1594 1191 
L 1594 225 
L 2375 225 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-24b8" d="M 5888 153 
Q 5888 3 5755 -178 
Q 5622 -359 5309 -359 
L 4513 -353 
L 4359 172 
L 5228 134 
Q 5381 172 5381 288 
L 5381 5288 
L 5888 5288 
L 5888 153 
z
M 3950 1259 
L 3525 909 
Q 3119 1706 2559 2169 
L 2559 -428 
L 2075 -428 
L 2075 2144 
Q 1766 1428 794 525 
L 366 831 
Q 1484 1806 2003 3097 
L 622 3097 
L 622 3566 
L 2053 3566 
L 2053 4397 
Q 1469 4281 813 4281 
L 563 4763 
Q 2453 4819 3641 5209 
L 3928 4800 
Q 3109 4544 2541 4453 
L 2541 3566 
L 3891 3566 
L 3891 3097 
L 2541 3097 
L 2541 2547 
L 2706 2669 
Q 3581 1938 3950 1259 
z
M 4647 794 
L 4159 794 
L 4159 4531 
L 4647 4531 
L 4647 794 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-3" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-e" d="M 3384 1997 
L 2131 1997 
L 2131 744 
L 1606 744 
L 1606 1997 
L 353 1997 
L 353 2522 
L 1606 2522 
L 1606 3775 
L 2131 3775 
L 2131 2522 
L 3384 2522 
L 3384 1997 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-2537" d="M 5678 3834 
Q 5613 2631 5508 1595 
Q 5403 559 5328 262 
Q 5253 -34 5048 -161 
Q 4844 -288 4591 -288 
Q 4416 -288 4097 -256 
Q 4016 25 3944 238 
Q 4550 172 4644 172 
Q 4703 172 4812 456 
Q 4922 741 5023 1741 
Q 5125 2741 5159 3391 
L 4359 3391 
Q 4366 1738 3883 889 
Q 3400 41 2528 -384 
L 2156 25 
Q 2716 300 3009 634 
Q 2913 850 2719 1075 
Q 1478 731 763 475 
L 428 959 
Q 678 1172 1014 1786 
Q 1350 2400 1503 2906 
L 353 2906 
L 353 3372 
L 3144 3372 
L 3144 2906 
L 2041 2906 
Q 1500 1597 1125 1125 
L 1141 1113 
L 2444 1484 
Q 2397 1556 2125 1797 
L 2478 2047 
Q 3131 1475 3359 997 
Q 3528 1178 3697 1742 
Q 3866 2306 3866 2888 
L 3866 3391 
L 3194 3391 
L 3194 3834 
L 3866 3834 
L 3866 5319 
L 4353 5325 
L 4353 3834 
L 5678 3834 
z
M 2881 4219 
L 603 4219 
L 603 4659 
L 2881 4659 
L 2881 4219 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-cb0" d="M 1856 4072 
Q 1856 3847 1829 3683 
Q 1803 3519 1692 3355 
Q 1581 3191 1344 3084 
L 1203 3303 
Q 1544 3441 1550 3928 
L 1253 3928 
L 1253 4581 
L 1856 4581 
L 1856 4072 
z
M 884 4072 
Q 884 3847 857 3683 
Q 831 3519 718 3355 
Q 606 3191 372 3084 
L 231 3303 
Q 572 3441 575 3928 
L 281 3928 
L 281 4581 
L 884 4581 
L 884 4072 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-4913" d="M 5644 4281 
Q 5619 1694 5395 673 
Q 5172 -347 4606 -347 
Q 4350 -347 3609 -134 
L 3525 403 
Q 4247 134 4531 134 
Q 4806 134 4976 1142 
Q 5147 2150 5159 3841 
L 3794 3841 
Q 3550 3166 3053 2497 
L 2719 2713 
L 2719 -147 
L 2216 -147 
L 2216 269 
L 1153 269 
L 1153 -250 
L 647 -250 
L 647 4184 
L 1234 4184 
Q 1494 4644 1625 5313 
L 2088 5125 
Q 1903 4444 1741 4184 
L 2719 4184 
L 2719 2881 
Q 3431 3888 3681 5363 
L 4191 5247 
Q 4106 4869 3916 4281 
L 5644 4281 
z
M 2216 2484 
L 2216 3719 
L 1153 3719 
L 1153 2484 
L 2216 2484 
z
M 2216 738 
L 2216 2016 
L 1153 2016 
L 1153 738 
L 2216 738 
z
M 4775 1369 
L 4313 1166 
Q 4034 1925 3444 2669 
L 3841 2931 
Q 4484 2191 4775 1369 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-4fbe" d="M 5997 1025 
L 5581 691 
Q 5316 1013 5197 1119 
L 3431 1056 
L 3431 -403 
L 2944 -403 
L 2944 1063 
L 781 1006 
L 616 1472 
L 1759 1472 
L 2131 1672 
Q 1350 2422 997 2625 
L 1416 2925 
L 1819 2619 
Q 2541 3038 2572 3059 
L 1031 3059 
L 1031 5172 
L 5369 5172 
L 5369 3059 
L 3116 3059 
L 3256 2963 
Q 3006 2791 2163 2303 
Q 2316 2169 2559 1919 
Q 3859 2628 4409 3028 
L 4838 2706 
Q 3569 1909 2619 1484 
L 4750 1528 
L 4116 1900 
L 4513 2194 
Q 5428 1738 5997 1025 
z
M 4884 4341 
L 4884 4703 
L 3450 4703 
L 3450 4341 
L 4884 4341 
z
M 2969 4703 
L 1516 4703 
L 1516 4341 
L 2963 4341 
L 2969 4703 
z
M 4884 3525 
L 4884 3897 
L 3450 3897 
L 3450 3525 
L 4884 3525 
z
M 2969 3525 
L 2969 3897 
L 1516 3897 
L 1516 3525 
L 2969 3525 
z
M 6034 244 
L 5778 -159 
Q 4997 381 3794 588 
L 4078 984 
Q 5275 753 6034 244 
z
M 2650 622 
Q 1806 31 678 -122 
L 325 306 
Q 1581 431 2322 947 
L 2650 622 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-5e30" d="M 2075 4422 
L 1672 4116 
Q 1431 4616 856 5081 
L 1203 5375 
Q 1741 5006 2075 4422 
z
M 5997 2956 
L 4506 2956 
L 4506 -422 
L 4019 -422 
L 4019 2956 
L 2528 2956 
L 2528 3425 
L 4019 3425 
L 4019 5325 
L 4506 5325 
L 4506 3425 
L 5997 3425 
L 5997 2956 
z
M 2853 384 
L 1600 -306 
L 1313 103 
Q 1409 203 1409 372 
L 1409 3116 
L 475 3116 
L 475 3584 
L 1894 3584 
L 1894 391 
L 2853 916 
L 2853 384 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-37c5" d="M 6088 -13 
L 5728 -391 
Q 5000 -66 4391 716 
Q 3878 91 2938 -447 
L 2584 -116 
L 2584 -434 
L 2100 -434 
L 2100 1313 
L 647 825 
L 428 1247 
Q 509 1284 621 1318 
Q 734 1353 763 1369 
L 763 4641 
L 1247 4641 
L 1247 1528 
L 2100 1838 
L 2100 5247 
L 2584 5247 
L 2584 -56 
Q 3647 494 4147 1147 
Q 3669 1850 3463 2719 
Q 3253 2297 2975 1925 
L 2613 2272 
Q 3469 3409 3525 5313 
L 4006 5159 
Q 4006 4703 3916 4166 
L 5813 4166 
L 5813 3700 
L 5422 3700 
Q 5363 2247 4697 1147 
Q 5272 319 6088 -13 
z
M 4947 3700 
L 3816 3700 
L 3763 3500 
Q 3975 2297 4416 1588 
Q 4878 2472 4947 3700 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-4959" d="M 5191 5063 
Q 4775 4500 4072 4000 
L 3706 4341 
Q 4428 4822 4788 5375 
L 5191 5063 
z
M 2675 4306 
L 2259 3994 
Q 1838 4713 1197 5075 
L 1631 5350 
Q 2178 5041 2675 4306 
z
M 5869 3506 
L 531 3506 
L 531 3975 
L 5869 3975 
L 5869 3506 
z
M 6144 2150 
L 5831 1753 
Q 5544 1859 5209 2034 
L 5209 353 
L 5984 353 
L 5984 -116 
L 403 -116 
L 403 353 
L 1203 353 
L 1203 2113 
Q 906 1969 609 1875 
L 288 2284 
Q 1559 2691 2322 3463 
L 2688 3116 
Q 2044 2509 1313 2150 
L 5006 2150 
Q 4272 2588 3738 3169 
L 4128 3481 
Q 4856 2681 6144 2150 
z
M 4691 366 
L 4691 1709 
L 4044 1709 
L 4044 366 
L 4691 366 
z
M 3547 366 
L 3547 1709 
L 2847 1709 
L 2847 366 
L 3547 366 
z
M 2350 353 
L 2350 1684 
L 1703 1684 
L 1703 353 
L 2350 353 
z
" transform="scale(0.015625)"/>
      <path id="us-small-ArialUnicodeMS-307d" d="M 5991 -122 
L 1209 -122 
L 1209 347 
L 3284 347 
L 3284 1178 
L 1863 1178 
Q 1419 619 588 159 
L 300 581 
Q 1531 1266 1888 2169 
L 697 2169 
L 697 2631 
L 2981 2631 
L 2981 3188 
L 1319 3188 
L 1319 3634 
L 2981 3634 
L 2981 4122 
L 947 4122 
L 947 4581 
L 2291 4581 
Q 2069 4831 1563 5088 
L 2069 5350 
Q 2581 5003 2822 4588 
L 3647 4588 
Q 4069 4869 4313 5375 
L 4781 5147 
Q 4534 4741 4347 4603 
L 4347 4588 
L 5581 4588 
L 5575 4122 
L 3463 4122 
L 3463 3634 
L 5209 3634 
L 5209 3188 
L 3463 3188 
L 3463 2631 
L 5838 2631 
L 5838 2169 
L 2413 2169 
Q 2375 2000 2150 1644 
L 5497 1644 
L 5497 1178 
L 3763 1178 
L 3763 347 
L 5991 347 
L 5991 -122 
z
" transform="scale(0.015625)"/>
     </defs>
     <use xlink:href="#us-small-ArialUnicodeMS-23d7"/>
     <use xlink:href="#us-small-ArialUnicodeMS-499a" transform="translate(100 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-2b2d" transform="translate(200 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-645e" transform="translate(300 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-19f6" transform="translate(400 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-383f" transform="translate(500 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-5153" transform="translate(600 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-2697" transform="translate(700 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-4987" transform="translate(800 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-2e88" transform="translate(900 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-caf" transform="translate(1000 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-4957" transform="translate(1033.296875 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-24b8" transform="translate(1133.296875 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-3" transform="translate(1233.296875 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-e" transform="translate(1261.078125 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-3" transform="translate(1319.484375 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-2537" transform="translate(1347.265625 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-645e" transform="translate(1447.265625 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-cb0" transform="translate(1547.265625 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-4913" transform="translate(1580.5625 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-4fbe" transform="translate(1680.5625 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-5e30" transform="translate(1780.5625 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-37c5" transform="translate(1880.5625 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-4959" transform="translate(1980.5625 0)"/>
     <use xlink:href="#us-small-ArialUnicodeMS-307d" transform="translate(2080.5625 0)"/>
    </g>
   </g>
  </g>
  <g id="us-small-axes_2">
   <g id="us-small-patch_5">
    <path d="M 49.819609 400.593832 
L 594 400.593832 
L 594 227.425661 
L 49.819609 227.425661 
z
" style="fill: #fbfaf7"/>
   </g>
   <g id="us-small-matplotlib.axis_3">
    <g id="us-small-xtick_6">
     <g id="us-small-line2d_23">
      <path d="M 124.120824 400.593832 
L 124.120824 227.425661 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_24">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="124.120824" y="400.593832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-small-xtick_7">
     <g id="us-small-line2d_25">
      <path d="M 223.116884 400.593832 
L 223.116884 227.425661 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_26">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="223.116884" y="400.593832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-small-xtick_8">
     <g id="us-small-line2d_27">
      <path d="M 321.977517 400.593832 
L 321.977517 227.425661 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_28">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="321.977517" y="400.593832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-small-xtick_9">
     <g id="us-small-line2d_29">
      <path d="M 420.973577 400.593832 
L 420.973577 227.425661 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_30">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="420.973577" y="400.593832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
    <g id="us-small-xtick_10">
     <g id="us-small-line2d_31">
      <path d="M 519.834211 400.593832 
L 519.834211 227.425661 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_32">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="519.834211" y="400.593832" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
    </g>
   </g>
   <g id="us-small-matplotlib.axis_4">
    <g id="us-small-ytick_6">
     <g id="us-small-line2d_33">
      <path d="M 49.819609 382.597 
L 594 382.597 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_34">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="382.597" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_8">
      <!-- 100 -->
      <g transform="translate(26.136797 386.237137) scale(0.1 -0.1)">
       <use xlink:href="#us-small-ArialUnicodeMS-14"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(111.21875 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-ytick_7">
     <g id="us-small-line2d_35">
      <path d="M 49.819609 355.927019 
L 594 355.927019 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_36">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="355.927019" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_9">
      <!-- 150 -->
      <g transform="translate(26.136797 359.567156) scale(0.1 -0.1)">
       <defs>
        <path id="us-small-ArialUnicodeMS-18" d="M 1013 2753 
Q 1431 3041 1881 3041 
Q 2453 3041 2878 2636 
Q 3303 2231 3303 1556 
Q 3303 875 2872 398 
Q 2441 -78 1741 -78 
Q 1169 -78 750 245 
Q 331 569 269 1203 
L 856 1247 
Q 928 813 1162 598 
Q 1397 384 1741 384 
Q 2169 384 2434 707 
Q 2700 1031 2700 1503 
Q 2700 1984 2428 2262 
Q 2156 2541 1728 2541 
Q 1188 2541 897 2100 
L 366 2163 
L 813 4519 
L 3084 4519 
L 3084 3975 
L 1259 3975 
L 1013 2753 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-small-ArialUnicodeMS-14"/>
       <use xlink:href="#us-small-ArialUnicodeMS-18" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(111.21875 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-ytick_8">
     <g id="us-small-line2d_37">
      <path d="M 49.819609 329.257038 
L 594 329.257038 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_38">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="329.257038" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_10">
      <!-- 200 -->
      <g transform="translate(26.136797 332.897175) scale(0.1 -0.1)">
       <use xlink:href="#us-small-ArialUnicodeMS-15"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(111.21875 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-ytick_9">
     <g id="us-small-line2d_39">
      <path d="M 49.819609 302.587057 
L 594 302.587057 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_40">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="302.587057" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_11">
      <!-- 250 -->
      <g transform="translate(26.136797 306.227194) scale(0.1 -0.1)">
       <use xlink:href="#us-small-ArialUnicodeMS-15"/>
       <use xlink:href="#us-small-ArialUnicodeMS-18" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(111.21875 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-ytick_10">
     <g id="us-small-line2d_41">
      <path d="M 49.819609 275.917076 
L 594 275.917076 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_42">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="275.917076" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_12">
      <!-- 300 -->
      <g transform="translate(26.136797 279.557213) scale(0.1 -0.1)">
       <use xlink:href="#us-small-ArialUnicodeMS-16"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(111.21875 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-ytick_11">
     <g id="us-small-line2d_43">
      <path d="M 49.819609 249.247095 
L 594 249.247095 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_44">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="249.247095" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_13">
      <!-- 350 -->
      <g transform="translate(26.136797 252.887232) scale(0.1 -0.1)">
       <use xlink:href="#us-small-ArialUnicodeMS-16"/>
       <use xlink:href="#us-small-ArialUnicodeMS-18" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(111.21875 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-text_14">
     <!-- 初始 100 美元 -->
     <g transform="translate(20.037188 345.129277) rotate(-90) scale(0.1 -0.1)">
      <defs>
       <path id="us-small-ArialUnicodeMS-24ac" d="M 3084 2803 
Q 2794 2372 2497 2125 
Q 2678 2009 2994 1672 
L 2688 1275 
Q 2309 1703 1813 1966 
L 1813 -469 
L 1325 -469 
L 1325 2009 
Q 1272 1969 1011 1748 
Q 750 1528 531 1394 
L 206 1838 
Q 797 2153 1342 2670 
Q 1888 3188 2075 3647 
L 422 3647 
L 422 4116 
L 1344 4116 
L 1344 5259 
L 1831 5259 
L 1831 4116 
L 2619 4116 
L 2619 3700 
Q 2422 3122 1850 2484 
L 2113 2356 
Q 2388 2591 2663 3091 
L 3084 2803 
z
M 5753 4844 
L 5759 2381 
Q 5759 1803 5667 923 
Q 5575 44 5400 -122 
Q 5225 -288 4863 -288 
Q 4578 -288 4050 -172 
L 3928 378 
Q 4728 197 4825 197 
Q 4975 197 5048 305 
Q 5122 413 5190 1295 
Q 5259 2178 5259 2619 
L 5259 4353 
L 4206 4353 
Q 4206 2600 4090 1853 
Q 3975 1106 3633 612 
Q 3291 119 2572 -306 
L 2203 91 
Q 2825 431 3137 842 
Q 3450 1253 3551 1717 
Q 3653 2181 3669 2881 
L 3700 4353 
L 2847 4353 
L 2847 4844 
L 5753 4844 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-2c5a" d="M 6047 2656 
L 5575 2456 
Q 5481 2788 5388 2975 
L 2719 2713 
L 2619 2981 
Q 2503 2059 2216 1331 
Q 2497 1147 2963 709 
L 2650 288 
Q 2131 825 1984 872 
Q 1525 13 709 -475 
L 347 -134 
Q 1250 472 1581 1106 
Q 1181 1356 588 1528 
Q 891 2266 1172 3591 
L 469 3591 
L 469 4056 
L 1253 4056 
Q 1381 4750 1409 5306 
L 1894 5147 
Q 1825 4497 1741 4056 
L 2731 4056 
L 2663 3244 
Q 2938 3244 3041 3272 
Q 3609 4163 4025 5344 
L 4525 5125 
Q 3866 3672 3566 3272 
L 5191 3391 
Q 4928 3825 4603 4116 
L 4997 4353 
Q 5722 3688 6047 2656 
z
M 2234 3591 
L 1656 3591 
Q 1444 2541 1172 1819 
Q 1459 1719 1784 1556 
Q 2078 2272 2234 3591 
z
M 5563 -416 
L 5075 -416 
L 5075 109 
L 3500 109 
L 3500 -416 
L 3016 -416 
L 3016 2328 
L 5563 2328 
L 5563 -416 
z
M 5075 575 
L 5075 1863 
L 3500 1863 
L 3500 575 
L 5075 575 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-521d" d="M 5972 2209 
L 475 2209 
L 475 2675 
L 2950 2675 
L 2950 3219 
L 1281 3219 
L 1281 3688 
L 2950 3688 
L 2950 4153 
L 844 4153 
L 844 4622 
L 2188 4622 
Q 1956 4941 1619 5141 
L 2053 5381 
Q 2441 5166 2784 4622 
L 3616 4622 
Q 4103 5041 4347 5409 
L 4769 5094 
Q 4534 4769 4306 4634 
L 4306 4622 
L 5581 4622 
L 5581 4153 
L 3475 4153 
L 3475 3688 
L 5159 3688 
L 5159 3219 
L 3475 3219 
L 3475 2675 
L 5972 2675 
L 5972 2209 
z
M 6113 56 
L 5813 -391 
Q 3891 -44 3244 1222 
L 3219 1222 
Q 3034 638 2270 191 
Q 1506 -256 550 -372 
L 288 84 
Q 1106 166 1786 481 
Q 2466 797 2688 1234 
L 769 1234 
L 769 1703 
L 2853 1703 
Q 2906 1909 2906 2175 
L 3406 2088 
Q 3394 1859 3353 1703 
L 5650 1703 
L 5650 1234 
L 3763 1234 
Q 4378 356 6113 56 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-23d2" d="M 5141 4422 
L 1394 4422 
L 1394 4909 
L 5141 4909 
L 5141 4422 
z
M 6009 1166 
Q 5822 -122 5203 -122 
L 4306 -122 
Q 3653 -122 3653 691 
L 3653 2847 
L 2834 2847 
Q 2850 1688 2378 917 
Q 1906 147 838 -428 
L 488 56 
Q 1469 550 1892 1181 
Q 2316 1813 2316 2847 
L 850 2847 
L 850 3334 
L 5672 3334 
L 5672 2847 
L 4159 2847 
L 4159 622 
Q 4159 366 4403 366 
L 5159 366 
Q 5241 366 5308 497 
Q 5375 628 5516 1325 
L 6009 1166 
z
" transform="scale(0.015625)"/>
      </defs>
      <use xlink:href="#us-small-ArialUnicodeMS-24ac"/>
      <use xlink:href="#us-small-ArialUnicodeMS-2c5a" transform="translate(100 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-3" transform="translate(200 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-14" transform="translate(227.78125 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(283.390625 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(339 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-3" transform="translate(394.609375 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-521d" transform="translate(422.390625 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-23d2" transform="translate(522.390625 0)"/>
     </g>
    </g>
   </g>
   <g id="us-small-line2d_45">
    <path d="M 74.555082 382.597 
L 78.753273 384.055341 
L 82.545188 381.361511 
L 86.743379 380.584717 
L 90.806145 382.099106 
L 95.004336 380.564376 
L 99.067102 379.717158 
L 103.265293 381.310056 
L 107.463484 384.145901 
L 111.52625 387.325503 
L 115.724442 384.275055 
L 119.787207 382.467265 
L 123.985399 385.244367 
L 128.18359 389.827134 
L 132.11093 390.623679 
L 136.309121 386.312974 
L 140.371887 384.68395 
L 144.570079 384.265996 
L 148.632844 384.032356 
L 152.831036 380.947188 
L 157.029227 379.685242 
L 161.091993 379.121575 
L 165.290184 381.503838 
L 169.35295 375.546218 
L 173.551141 374.409779 
L 177.749332 373.914248 
L 181.541247 373.277297 
L 185.739438 372.264377 
L 189.802204 371.198427 
L 194.000395 372.36601 
L 198.063161 370.67292 
L 202.261353 370.184883 
L 206.459544 370.638756 
L 210.52231 365.790894 
L 214.720501 364.935448 
L 218.783267 363.165642 
L 222.981458 362.027725 
L 227.179649 359.478022 
L 230.971564 362.371223 
L 235.169755 362.307589 
L 239.232521 362.163643 
L 243.430712 358.471727 
L 247.493478 357.903822 
L 251.69167 356.779934 
L 255.889861 352.904998 
L 259.952627 354.913888 
L 264.150818 363.311888 
L 268.213584 363.231656 
L 272.411775 370.995879 
L 276.609966 365.051485 
L 280.401881 361.678855 
L 284.600072 363.43551 
L 288.662838 361.717164 
L 292.861029 367.153582 
L 296.923795 362.563492 
L 301.121986 362.056029 
L 305.320178 366.277457 
L 309.382944 366.068454 
L 313.581135 364.267785 
L 317.643901 360.264308 
L 321.842092 357.582946 
L 326.040283 361.092911 
L 329.967623 368.488056 
L 334.165815 383.441994 
L 338.228581 372.98024 
L 342.426772 368.004494 
L 346.489538 364.174614 
L 350.687729 362.133739 
L 354.88592 357.438449 
L 358.948686 359.281143 
L 363.146877 356.709328 
L 367.209643 342.333754 
L 371.407834 335.335954 
L 375.606026 324.547829 
L 379.39794 313.580399 
L 383.596132 310.374013 
L 387.658897 306.039564 
L 391.857089 302.140565 
L 395.919855 300.889122 
L 400.118046 305.30765 
L 404.316237 303.118083 
L 408.379003 305.458137 
L 412.577194 301.466644 
L 416.63996 304.931619 
L 420.838151 300.817181 
L 425.036343 313.151639 
L 428.828257 308.428886 
L 433.026449 308.110384 
L 437.089214 317.724093 
L 441.287406 315.259277 
L 445.350172 330.197233 
L 449.548363 317.605443 
L 453.746554 319.376827 
L 457.80932 331.724118 
L 462.007511 317.684719 
L 466.070277 314.372095 
L 470.268468 321.648777 
L 474.46666 311.416223 
L 478.258574 315.263996 
L 482.456766 321.092912 
L 486.519531 320.995829 
L 490.717723 320.745475 
L 494.780488 311.189613 
L 498.97868 302.718394 
L 503.176871 309.213237 
L 507.239637 315.301884 
L 511.437828 321.570558 
L 515.500594 307.51192 
L 519.698785 293.14212 
L 523.896977 297.393511 
L 527.824317 287.571224 
L 532.022508 280.299264 
L 536.085274 292.792592 
L 540.283465 280.162203 
L 544.346231 285.695117 
L 548.544422 268.054804 
L 552.742614 266.537721 
L 556.805379 262.522628 
L 561.003571 264.805045 
L 565.066336 245.680489 
L 569.264528 260.96283 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #006f73; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="us-small-line2d_46">
    <path d="M 74.555082 382.597 
L 78.753273 383.9901 
L 82.545188 380.8966 
L 86.743379 379.736527 
L 90.806145 381.55744 
L 95.004336 380.034457 
L 99.067102 379.02667 
L 103.265293 379.741191 
L 107.463484 383.212123 
L 111.52625 386.037036 
L 115.724442 383.427781 
L 119.787207 381.771364 
L 123.985399 384.621327 
L 128.18359 389.451452 
L 132.11093 389.560374 
L 136.309121 385.973447 
L 140.371887 385.051302 
L 144.570079 384.475666 
L 148.632844 384.292451 
L 152.831036 381.356102 
L 157.029227 380.443019 
L 161.091993 379.946515 
L 165.290184 382.603125 
L 169.35295 376.520381 
L 173.551141 375.358851 
L 177.749332 375.261934 
L 181.541247 374.632287 
L 185.739438 374.300454 
L 189.802204 373.192499 
L 194.000395 374.47063 
L 198.063161 372.553078 
L 202.261353 372.069773 
L 206.459544 372.694089 
L 210.52231 368.202573 
L 214.720501 367.395065 
L 218.783267 364.825843 
L 222.981458 363.826063 
L 227.179649 361.5837 
L 230.971564 364.315598 
L 235.169755 363.956046 
L 239.232521 363.612256 
L 243.430712 358.957421 
L 247.493478 357.83303 
L 251.69167 356.641036 
L 255.889861 353.285347 
L 259.952627 355.118074 
L 264.150818 364.242331 
L 268.213584 364.195444 
L 272.411775 372.724986 
L 276.609966 366.183928 
L 280.401881 362.669454 
L 284.600072 364.329585 
L 288.662838 362.220019 
L 292.861029 367.843233 
L 296.923795 362.67057 
L 301.121986 362.21777 
L 305.320178 366.318942 
L 309.382944 365.95612 
L 313.581135 363.941202 
L 317.643901 361.025696 
L 321.842092 358.513386 
L 326.040283 361.255968 
L 329.967623 367.92181 
L 334.165815 384.858546 
L 338.228581 374.773624 
L 342.426772 369.637144 
L 346.489538 366.360082 
L 350.687729 363.796512 
L 354.88592 359.087927 
L 358.948686 361.327086 
L 363.146877 359.311114 
L 367.209643 343.916523 
L 371.407834 336.014059 
L 375.606026 326.534588 
L 379.39794 316.749195 
L 383.596132 313.727865 
L 387.658897 310.015947 
L 391.857089 306.197693 
L 395.919855 303.998901 
L 400.118046 308.51521 
L 404.316237 305.666721 
L 408.379003 308.346192 
L 412.577194 303.280614 
L 416.63996 306.644149 
L 420.838151 302.872001 
L 425.036343 314.858944 
L 428.828257 312.137629 
L 433.026449 311.610934 
L 437.089214 320.996779 
L 441.287406 318.771673 
L 445.350172 330.186705 
L 449.548363 318.594224 
L 453.746554 320.960082 
L 457.80932 332.55643 
L 462.007511 319.145477 
L 466.070277 315.483333 
L 470.268468 322.524516 
L 474.46666 312.892175 
L 478.258574 314.589936 
L 482.456766 320.133869 
L 486.519531 321.351711 
L 490.717723 321.988168 
L 494.780488 312.756769 
L 498.97868 305.348099 
L 503.176871 310.95538 
L 507.239637 317.558032 
L 511.437828 324.930846 
L 515.500594 314.368955 
L 519.698785 300.493647 
L 523.896977 304.70473 
L 527.824317 297.115526 
L 532.022508 292.072686 
L 536.085274 302.432286 
L 540.283465 295.791746 
L 544.346231 300.975506 
L 548.544422 286.147559 
L 552.742614 286.545152 
L 556.805379 284.82669 
L 561.003571 285.846577 
L 565.066336 268.13505 
L 569.264528 282.424171 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #df8f32; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="us-small-line2d_47">
    <path d="M 74.555082 382.597 
L 78.753273 384.537561 
L 82.545188 382.134639 
L 86.743379 381.94816 
L 90.806145 382.509806 
L 95.004336 381.876106 
L 99.067102 381.525089 
L 103.265293 384.884968 
L 107.463484 386.622216 
L 111.52625 390.409145 
L 115.724442 386.510461 
L 119.787207 385.465783 
L 123.985399 388.196577 
L 128.18359 392.00836 
L 132.11093 392.722551 
L 136.309121 386.998025 
L 140.371887 384.70088 
L 144.570079 384.705798 
L 148.632844 384.587659 
L 152.831036 381.024583 
L 157.029227 378.875147 
L 161.091993 378.79566 
L 165.290184 380.769606 
L 169.35295 374.294062 
L 173.551141 372.713107 
L 177.749332 372.057096 
L 181.541247 371.469082 
L 185.739438 369.303283 
L 189.802204 367.839208 
L 194.000395 368.64603 
L 198.063161 367.965114 
L 202.261353 367.752226 
L 206.459544 368.381366 
L 210.52231 363.123717 
L 214.720501 362.344033 
L 218.783267 360.706222 
L 222.981458 359.091319 
L 227.179649 356.830827 
L 230.971564 360.159297 
L 235.169755 360.317445 
L 239.232521 360.760273 
L 243.430712 359.940396 
L 247.493478 359.649177 
L 251.69167 358.4465 
L 255.889861 355.837009 
L 259.952627 357.722882 
L 264.150818 364.526099 
L 268.213584 364.91943 
L 272.411775 372.086094 
L 276.609966 366.041077 
L 280.401881 363.162694 
L 284.600072 365.623192 
L 288.662838 363.344182 
L 292.861029 369.840655 
L 296.923795 366.013613 
L 301.121986 366.757947 
L 305.320178 372.544702 
L 309.382944 370.623346 
L 313.581135 369.567291 
L 317.643901 364.408177 
L 321.842092 361.575637 
L 326.040283 367.302723 
L 329.967623 376.030184 
L 334.165815 388.802609 
L 338.228581 378.541884 
L 342.426772 373.57853 
L 346.489538 369.792563 
L 350.687729 369.45602 
L 354.88592 363.870225 
L 358.948686 365.950431 
L 363.146877 362.589958 
L 367.209643 349.124255 
L 371.407834 343.98338 
L 375.606026 337.570813 
L 379.39794 324.083535 
L 383.596132 317.856767 
L 387.658897 311.622605 
L 391.857089 306.818725 
L 395.919855 310.13177 
L 400.118046 311.48015 
L 404.316237 311.16403 
L 408.379003 313.111361 
L 412.577194 311.302877 
L 416.63996 312.907914 
L 420.838151 307.319689 
L 425.036343 317.500646 
L 428.828257 310.966515 
L 433.026449 312.293201 
L 437.089214 321.910337 
L 441.287406 319.134928 
L 445.350172 336.35622 
L 449.548363 321.310666 
L 453.746554 324.719193 
L 457.80932 338.869208 
L 462.007511 325.601016 
L 466.070277 321.183716 
L 470.268468 329.24123 
L 474.46666 315.455182 
L 478.258574 321.19662 
L 482.456766 327.549678 
L 486.519531 325.742212 
L 490.717723 326.115221 
L 494.780488 315.081101 
L 498.97868 304.313328 
L 503.176871 311.506033 
L 507.239637 314.742481 
L 511.437828 318.346199 
L 515.500594 302.599032 
L 519.698785 288.866159 
L 523.896977 294.210712 
L 527.824317 284.555753 
L 532.022508 275.258978 
L 536.085274 289.884531 
L 540.283465 270.864269 
L 544.346231 277.462555 
L 548.544422 257.788749 
L 552.742614 255.873656 
L 556.805379 248.605401 
L 561.003571 254.446212 
L 565.066336 235.296941 
L 569.264528 249.637085 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #4461aa; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="us-small-line2d_48">
    <path d="M 74.555082 382.597 
L 78.753273 383.573121 
L 82.545188 380.588383 
L 86.743379 379.221273 
L 90.806145 381.688405 
L 95.004336 379.252645 
L 99.067102 377.909227 
L 103.265293 377.735143 
L 107.463484 381.669586 
L 111.52625 384.24186 
L 115.724442 382.039649 
L 119.787207 379.468747 
L 123.985399 382.292158 
L 128.18359 387.645909 
L 132.11093 388.524806 
L 136.309121 385.627923 
L 140.371887 384.667021 
L 144.570079 383.826194 
L 148.632844 383.477052 
L 152.831036 380.869794 
L 157.029227 380.495337 
L 161.091993 379.447491 
L 165.290184 382.238071 
L 169.35295 376.798373 
L 173.551141 376.106451 
L 177.749332 375.7714 
L 181.541247 375.085513 
L 185.739438 375.225471 
L 189.802204 374.557645 
L 194.000395 376.08599 
L 198.063161 373.380726 
L 202.261353 372.61754 
L 206.459544 372.896145 
L 210.52231 368.458072 
L 214.720501 367.526863 
L 218.783267 365.625062 
L 222.981458 364.964131 
L 227.179649 362.125217 
L 230.971564 364.583148 
L 235.169755 364.297733 
L 239.232521 363.567013 
L 243.430712 357.003059 
L 247.493478 356.158466 
L 251.69167 355.113368 
L 255.889861 349.972987 
L 259.952627 352.104894 
L 264.150818 362.097676 
L 268.213584 361.543881 
L 272.411775 369.905664 
L 276.609966 364.061894 
L 280.401881 360.195015 
L 284.600072 361.247828 
L 288.662838 360.090147 
L 292.861029 364.466508 
L 296.923795 359.113371 
L 301.121986 357.354111 
L 305.320178 360.010211 
L 309.382944 361.513561 
L 313.581135 358.96828 
L 317.643901 356.120439 
L 321.842092 353.590255 
L 326.040283 354.883099 
L 329.967623 360.945928 
L 334.165815 378.081379 
L 338.228581 367.418595 
L 342.426772 362.430458 
L 346.489538 358.556665 
L 350.687729 354.811459 
L 354.88592 351.006673 
L 358.948686 352.611855 
L 363.146877 350.828698 
L 367.209643 335.543254 
L 371.407834 326.688528 
L 375.606026 311.524846 
L 379.39794 303.077263 
L 383.596132 302.89126 
L 387.658897 300.456523 
L 391.857089 297.462405 
L 395.919855 291.646474 
L 400.118046 299.13515 
L 404.316237 295.072137 
L 408.379003 297.804914 
L 412.577194 291.630412 
L 416.63996 296.955323 
L 420.838151 294.314672 
L 425.036343 308.802633 
L 428.828257 305.891256 
L 433.026449 303.927566 
L 437.089214 313.53785 
L 441.287406 311.383626 
L 445.350172 324.038245 
L 449.548363 313.900221 
L 453.746554 314.034461 
L 457.80932 324.579028 
L 462.007511 309.768422 
L 466.070277 307.560473 
L 470.268468 314.056323 
L 474.46666 307.377264 
L 478.258574 309.331372 
L 482.456766 314.636146 
L 486.519531 316.249447 
L 490.717723 315.375728 
L 494.780488 307.298125 
L 498.97868 301.123461 
L 503.176871 306.920442 
L 507.239637 315.861287 
L 511.437828 324.794917 
L 515.500594 312.424807 
L 519.698785 297.41808 
L 523.896977 300.576311 
L 527.824317 290.586695 
L 532.022508 285.33955 
L 536.085274 295.700652 
L 540.283465 289.460136 
L 544.346231 293.927679 
L 548.544422 278.320859 
L 552.742614 277.201785 
L 556.805379 276.439856 
L 561.003571 275.163879 
L 565.066336 256.064037 
L 569.264528 272.288575 
" clip-path="url(#us-small-paeb1314bb3)" style="fill: none; stroke: #a2557e; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="us-small-patch_6">
    <path d="M 49.819609 400.593832 
L 49.819609 227.425661 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="us-small-patch_7">
    <path d="M 49.819609 400.593832 
L 594 400.593832 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="us-small-legend_1">
    <g id="us-small-line2d_49">
     <path d="M 57.919609 239.942692 
L 66.919609 239.942692 
L 75.919609 239.942692 
" style="fill: none; stroke: #006f73; stroke-width: 2; stroke-linecap: square"/>
    </g>
    <g id="us-small-text_15">
     <!-- 盈利、低扩张 + 动量 -->
     <g transform="translate(83.119609 243.092692) scale(0.09 -0.09)">
      <defs>
       <path id="us-small-ArialUnicodeMS-11ec" d="M 2150 -56 
L 1594 -550 
Q 1244 281 603 763 
L 959 1069 
Q 1669 634 2150 -56 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-21dd" d="M 2188 5153 
Q 1994 4550 1828 4150 
L 1663 3794 
L 1663 -434 
L 1172 -434 
L 1172 2956 
Q 997 2628 622 2253 
L 244 2591 
Q 1125 3463 1741 5363 
L 2188 5153 
z
M 6150 872 
Q 6053 -13 5886 -186 
Q 5719 -359 5478 -359 
Q 4941 -359 4542 559 
Q 4144 1478 4013 2875 
L 2869 2875 
L 2869 1031 
L 4050 1281 
L 4050 788 
L 2175 372 
L 1906 831 
L 2363 928 
L 2363 4594 
Q 4388 4797 5459 5319 
L 5797 4947 
Q 5131 4625 4428 4469 
Q 4419 3966 4469 3341 
L 5894 3341 
L 5894 2875 
L 4500 2875 
Q 4625 1759 4904 978 
Q 5184 197 5478 197 
Q 5559 197 5603 420 
Q 5647 644 5684 1106 
L 6150 872 
z
M 3975 3328 
Q 3938 3875 3928 4353 
Q 3438 4266 2869 4191 
L 2869 3328 
L 3975 3328 
z
M 4263 -250 
L 2188 -250 
L 2188 219 
L 4263 219 
L 4263 -250 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-34f8" d="M 2456 2291 
L 1772 1991 
L 1772 109 
Q 1772 -56 1698 -175 
Q 1625 -294 1483 -342 
Q 1341 -391 781 -391 
L 609 109 
Q 1019 72 1197 72 
Q 1288 72 1288 172 
L 1288 1778 
L 594 1497 
L 269 1906 
Q 763 2050 1288 2297 
L 1288 3597 
L 481 3597 
L 481 4063 
L 1288 4063 
L 1288 5288 
L 1772 5288 
L 1772 4063 
L 2456 4063 
L 2456 3597 
L 1772 3597 
L 1772 2497 
Q 2175 2644 2456 2791 
L 2456 2291 
z
M 4653 4531 
L 4288 4250 
Q 3994 4719 3506 5006 
L 3841 5259 
Q 4428 4941 4653 4531 
z
M 5900 3725 
L 3116 3725 
L 3116 1850 
Q 3116 1103 2942 579 
Q 2769 56 2344 -403 
L 1972 -63 
Q 2631 600 2631 1678 
L 2631 4191 
L 5888 4191 
L 5900 3725 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-31af" d="M 6034 44 
L 5716 -300 
Q 5091 44 4598 736 
Q 4106 1428 4038 2369 
L 3541 2369 
L 3541 263 
L 4513 691 
L 4513 184 
L 3116 -422 
L 2828 -56 
Q 3053 34 3053 197 
L 3053 2369 
L 2534 2369 
L 2534 2834 
L 3053 2834 
L 3053 5141 
L 3541 5141 
L 3541 3547 
Q 4516 3963 5319 4884 
L 5663 4544 
Q 4647 3419 3541 3091 
L 3541 2834 
L 5850 2834 
L 5850 2369 
L 4481 2369 
Q 4594 988 6034 44 
z
M 2534 2284 
Q 2531 1553 2398 795 
Q 2266 38 2083 -184 
Q 1900 -406 1531 -406 
Q 1319 -406 966 -325 
L 872 206 
Q 984 184 1237 114 
Q 1491 44 1619 44 
Q 1728 44 1890 666 
Q 2053 1288 2053 1819 
L 531 1819 
Q 659 2781 738 3681 
L 2069 3681 
L 2069 4422 
L 397 4422 
L 397 4891 
L 2528 4891 
L 2528 3213 
L 1172 3213 
L 1063 2284 
L 2534 2284 
z
" transform="scale(0.015625)"/>
      </defs>
      <use xlink:href="#us-small-ArialUnicodeMS-4957"/>
      <use xlink:href="#us-small-ArialUnicodeMS-24b8" transform="translate(100 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-11ec" transform="translate(200 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-21dd" transform="translate(300 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-34f8" transform="translate(400 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-31af" transform="translate(500 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-3" transform="translate(600 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-e" transform="translate(627.78125 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-3" transform="translate(686.1875 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-2537" transform="translate(713.96875 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-645e" transform="translate(813.96875 0)"/>
     </g>
    </g>
    <g id="us-small-line2d_50">
     <path d="M 57.919609 253.820621 
L 66.919609 253.820621 
L 75.919609 253.820621 
" style="fill: none; stroke: #df8f32; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="us-small-text_16">
     <!-- 盈利 + 动量 -->
     <g transform="translate(83.119609 256.970621) scale(0.09 -0.09)">
      <use xlink:href="#us-small-ArialUnicodeMS-4957"/>
      <use xlink:href="#us-small-ArialUnicodeMS-24b8" transform="translate(100 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-3" transform="translate(200 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-e" transform="translate(227.78125 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-3" transform="translate(286.1875 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-2537" transform="translate(313.96875 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-645e" transform="translate(413.96875 0)"/>
     </g>
    </g>
    <g id="us-small-line2d_51">
     <path d="M 183.376797 239.942692 
L 192.376797 239.942692 
L 201.376797 239.942692 
" style="fill: none; stroke: #4461aa; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="us-small-text_17">
     <!-- 盈利、低扩张单独使用 -->
     <g transform="translate(208.576797 243.092692) scale(0.09 -0.09)">
      <defs>
       <path id="us-small-ArialUnicodeMS-25e4" d="M 5925 947 
L 3353 947 
L 3353 -372 
L 2869 -372 
L 2869 947 
L 347 947 
L 347 1388 
L 2869 1388 
L 2869 1919 
L 1234 1919 
L 1234 4213 
L 2234 4213 
Q 2041 4659 1550 5106 
L 1900 5381 
Q 2347 5050 2747 4359 
L 2547 4219 
L 2547 4213 
L 3328 4213 
Q 3750 4644 4000 5344 
L 4447 5131 
Q 4219 4559 3909 4213 
L 4984 4213 
L 4984 1919 
L 3353 1919 
L 3353 1388 
L 5925 1388 
L 5925 947 
z
M 4500 3316 
L 4500 3744 
L 3353 3744 
L 3353 3316 
L 4500 3316 
z
M 2869 3316 
L 2869 3744 
L 1722 3744 
L 1722 3316 
L 2869 3316 
z
M 4500 2363 
L 4500 2847 
L 3353 2847 
L 3353 2363 
L 4500 2363 
z
M 2869 2363 
L 2869 2847 
L 1722 2847 
L 1722 2363 
L 2869 2363 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-457b" d="M 6069 -84 
L 5569 -313 
Q 5425 156 5313 331 
L 2638 -281 
L 2388 238 
L 3897 506 
L 3897 1569 
L 2656 1569 
L 2656 3975 
L 3897 3975 
L 3897 5294 
L 4384 5294 
L 4384 3975 
L 5563 3975 
L 5563 1569 
L 4384 1569 
L 4384 603 
L 5119 763 
Q 4953 1013 4800 1184 
L 5184 1441 
Q 5800 738 6069 -84 
z
M 5075 2034 
L 5075 3506 
L 4384 3506 
L 4384 2034 
L 5075 2034 
z
M 3897 2034 
L 3897 3506 
L 3144 3506 
L 3144 2034 
L 3897 2034 
z
M 2169 4684 
Q 1866 4100 1778 3988 
Q 2163 3459 2163 2053 
Q 2163 953 2092 511 
Q 2022 69 1820 -151 
Q 1619 -372 1281 -372 
Q 1038 -372 647 -300 
L 453 244 
Q 950 91 1219 91 
Q 1438 91 1531 336 
Q 1625 581 1656 1300 
L 1703 2247 
Q 1259 1538 569 1044 
L 213 1416 
Q 1066 2003 1638 2906 
Q 1600 3309 1459 3513 
Q 1138 3016 684 2713 
L 306 3109 
Q 906 3513 1203 3950 
Q 994 4234 313 4628 
L 609 4997 
Q 1072 4753 1497 4366 
Q 1731 4794 1806 4972 
L 2169 4684 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-220e" d="M 6303 84 
L 6009 -378 
Q 5394 -328 4664 -104 
Q 3934 119 3525 397 
Q 3059 -59 2194 -453 
L 1819 -25 
Q 2713 288 3103 691 
Q 2803 944 2291 1588 
L 2706 1850 
Q 3078 1341 3425 1075 
Q 3641 1409 3688 1931 
L 2234 1931 
L 2234 3719 
L 3713 3719 
L 3713 4141 
L 1875 4141 
L 1684 3669 
L 1684 -469 
L 1184 -469 
L 1184 2772 
Q 981 2431 678 2041 
L 319 2363 
Q 1153 3313 1753 5331 
L 2203 5166 
L 2034 4628 
L 3713 4628 
L 3713 5350 
L 4219 5350 
L 4219 4628 
L 5947 4628 
L 5947 4141 
L 4219 4141 
L 4219 3719 
L 5709 3719 
L 5709 1931 
L 4197 1931 
Q 4106 1203 3841 781 
Q 4734 256 6303 84 
z
M 5191 2419 
L 5191 3250 
L 4219 3250 
L 4219 2419 
L 5191 2419 
z
M 3713 2419 
L 3713 3231 
L 2725 3231 
L 2725 2419 
L 3713 2419 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-47b7" d="M 5472 159 
Q 5472 -66 5340 -219 
Q 5209 -372 5013 -372 
L 4347 -372 
L 4191 128 
L 4722 113 
Q 4966 113 4966 256 
L 4966 1722 
L 3572 1722 
L 3572 13 
L 3084 13 
L 3084 1722 
L 1678 1722 
Q 1584 466 744 -469 
L 331 -159 
Q 794 394 1001 936 
Q 1209 1478 1209 2194 
L 1209 5044 
L 5472 5044 
L 5472 159 
z
M 4966 3641 
L 4966 4575 
L 3572 4575 
L 3572 3641 
L 4966 3641 
z
M 3084 3641 
L 3084 4575 
L 1697 4575 
L 1697 3641 
L 3084 3641 
z
M 4966 2188 
L 4966 3175 
L 3572 3175 
L 3572 2188 
L 4966 2188 
z
M 3084 2188 
L 3084 3175 
L 1697 3175 
L 1697 2188 
L 3084 2188 
z
" transform="scale(0.015625)"/>
      </defs>
      <use xlink:href="#us-small-ArialUnicodeMS-4957"/>
      <use xlink:href="#us-small-ArialUnicodeMS-24b8" transform="translate(100 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-11ec" transform="translate(200 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-21dd" transform="translate(300 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-34f8" transform="translate(400 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-31af" transform="translate(500 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-25e4" transform="translate(600 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-457b" transform="translate(700 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-220e" transform="translate(800 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-47b7" transform="translate(900 0)"/>
     </g>
    </g>
    <g id="us-small-line2d_52">
     <path d="M 183.376797 253.899371 
L 192.376797 253.899371 
L 201.376797 253.899371 
" style="fill: none; stroke: #a2557e; stroke-width: 1.2; stroke-linecap: square"/>
    </g>
    <g id="us-small-text_18">
     <!-- 动量单独使用 -->
     <g transform="translate(208.576797 257.049371) scale(0.09 -0.09)">
      <use xlink:href="#us-small-ArialUnicodeMS-2537"/>
      <use xlink:href="#us-small-ArialUnicodeMS-645e" transform="translate(100 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-25e4" transform="translate(200 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-457b" transform="translate(300 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-220e" transform="translate(400 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-47b7" transform="translate(500 0)"/>
     </g>
    </g>
   </g>
  </g>
  <g id="us-small-axes_3">
   <g id="us-small-patch_8">
    <path d="M 49.819609 548.100117 
L 594 548.100117 
L 594 414.893832 
L 49.819609 414.893832 
z
" style="fill: #fbfaf7"/>
   </g>
   <g id="us-small-matplotlib.axis_5">
    <g id="us-small-xtick_11">
     <g id="us-small-line2d_53">
      <path d="M 124.120824 548.100117 
L 124.120824 414.893832 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_54">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="124.120824" y="548.100117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_19">
      <!-- 2016 -->
      <g transform="translate(112.998949 562.380391) scale(0.1 -0.1)">
       <defs>
        <path id="us-small-ArialUnicodeMS-19" d="M 838 2363 
Q 1225 2969 1941 2969 
Q 2503 2969 2897 2553 
Q 3291 2138 3291 1491 
Q 3291 838 2898 380 
Q 2506 -78 1856 -78 
Q 1197 -78 733 409 
Q 269 897 269 2144 
Q 269 3369 689 3986 
Q 1109 4603 1906 4603 
Q 2422 4603 2778 4315 
Q 3134 4028 3213 3463 
L 2650 3413 
Q 2497 4141 1875 4141 
Q 1444 4141 1134 3712 
Q 825 3284 825 2363 
L 838 2363 
z
M 1844 384 
Q 2231 384 2472 696 
Q 2713 1009 2713 1453 
Q 2713 1897 2472 2187 
Q 2231 2478 1825 2478 
Q 1453 2478 1184 2204 
Q 916 1931 916 1484 
Q 916 1028 1180 706 
Q 1444 384 1844 384 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-small-ArialUnicodeMS-15"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-14" transform="translate(111.21875 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-19" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-xtick_12">
     <g id="us-small-line2d_55">
      <path d="M 223.116884 548.100117 
L 223.116884 414.893832 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_56">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="223.116884" y="548.100117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_20">
      <!-- 2018 -->
      <g transform="translate(211.995009 562.380391) scale(0.1 -0.1)">
       <defs>
        <path id="us-small-ArialUnicodeMS-1b" d="M 2425 2478 
Q 3284 2203 3284 1306 
Q 3284 716 2862 319 
Q 2441 -78 1778 -78 
Q 1109 -78 689 322 
Q 269 722 269 1325 
Q 269 1759 505 2084 
Q 741 2409 1141 2478 
L 1141 2491 
Q 453 2703 453 3419 
Q 453 3925 815 4264 
Q 1178 4603 1766 4603 
Q 2363 4603 2730 4253 
Q 3097 3903 3097 3406 
Q 3097 2731 2425 2491 
L 2425 2478 
z
M 1778 2700 
Q 2094 2700 2308 2901 
Q 2522 3103 2522 3406 
Q 2522 3716 2305 3928 
Q 2088 4141 1772 4141 
Q 1450 4141 1240 3931 
Q 1031 3722 1031 3438 
Q 1031 3097 1247 2898 
Q 1463 2700 1778 2700 
z
M 1778 384 
Q 2175 384 2440 640 
Q 2706 897 2706 1306 
Q 2706 1716 2432 1978 
Q 2159 2241 1766 2241 
Q 1356 2241 1100 1970 
Q 844 1700 844 1319 
Q 844 922 1108 653 
Q 1372 384 1778 384 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-small-ArialUnicodeMS-15"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-14" transform="translate(111.21875 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-1b" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-xtick_13">
     <g id="us-small-line2d_57">
      <path d="M 321.977517 548.100117 
L 321.977517 414.893832 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_58">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="321.977517" y="548.100117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_21">
      <!-- 2020 -->
      <g transform="translate(310.855642 562.380391) scale(0.1 -0.1)">
       <use xlink:href="#us-small-ArialUnicodeMS-15"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-15" transform="translate(111.21875 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-xtick_14">
     <g id="us-small-line2d_59">
      <path d="M 420.973577 548.100117 
L 420.973577 414.893832 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_60">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="420.973577" y="548.100117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_22">
      <!-- 2022 -->
      <g transform="translate(409.851702 562.380391) scale(0.1 -0.1)">
       <use xlink:href="#us-small-ArialUnicodeMS-15"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-15" transform="translate(111.21875 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-15" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-xtick_15">
     <g id="us-small-line2d_61">
      <path d="M 519.834211 548.100117 
L 519.834211 414.893832 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_62">
      <g>
       <use xlink:href="#us-small-m43d5373113" x="519.834211" y="548.100117" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_23">
      <!-- 2024 -->
      <g transform="translate(508.712336 562.380391) scale(0.1 -0.1)">
       <use xlink:href="#us-small-ArialUnicodeMS-15"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(55.609375 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-15" transform="translate(111.21875 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-17" transform="translate(166.828125 0)"/>
      </g>
     </g>
    </g>
   </g>
   <g id="us-small-matplotlib.axis_6">
    <g id="us-small-ytick_12">
     <g id="us-small-line2d_63">
      <path d="M 49.819609 538.645096 
L 594 538.645096 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_64">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="538.645096" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_24">
      <!-- -40 -->
      <g transform="translate(28.368047 542.285233) scale(0.1 -0.1)">
       <defs>
        <path id="us-small-ArialUnicodeMS-10" d="M 1925 1375 
L 206 1375 
L 206 1941 
L 1925 1941 
L 1925 1375 
z
" transform="scale(0.015625)"/>
       </defs>
       <use xlink:href="#us-small-ArialUnicodeMS-10"/>
       <use xlink:href="#us-small-ArialUnicodeMS-17" transform="translate(33.296875 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(88.90625 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-ytick_13">
     <g id="us-small-line2d_65">
      <path d="M 49.819609 509.220988 
L 594 509.220988 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_66">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="509.220988" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_25">
      <!-- -30 -->
      <g transform="translate(28.368047 512.861125) scale(0.1 -0.1)">
       <use xlink:href="#us-small-ArialUnicodeMS-10"/>
       <use xlink:href="#us-small-ArialUnicodeMS-16" transform="translate(33.296875 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(88.90625 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-ytick_14">
     <g id="us-small-line2d_67">
      <path d="M 49.819609 479.79688 
L 594 479.79688 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_68">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="479.79688" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_26">
      <!-- -20 -->
      <g transform="translate(28.368047 483.437016) scale(0.1 -0.1)">
       <use xlink:href="#us-small-ArialUnicodeMS-10"/>
       <use xlink:href="#us-small-ArialUnicodeMS-15" transform="translate(33.296875 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(88.90625 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-ytick_15">
     <g id="us-small-line2d_69">
      <path d="M 49.819609 450.372771 
L 594 450.372771 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_70">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="450.372771" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_27">
      <!-- -10 -->
      <g transform="translate(28.368047 454.012908) scale(0.1 -0.1)">
       <use xlink:href="#us-small-ArialUnicodeMS-10"/>
       <use xlink:href="#us-small-ArialUnicodeMS-14" transform="translate(33.296875 0)"/>
       <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(88.90625 0)"/>
      </g>
     </g>
    </g>
    <g id="us-small-ytick_16">
     <g id="us-small-line2d_71">
      <path d="M 49.819609 420.948663 
L 594 420.948663 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #b0b0b0; stroke-opacity: 0.16; stroke-width: 0.8; stroke-linecap: square"/>
     </g>
     <g id="us-small-line2d_72">
      <g>
       <use xlink:href="#us-small-m29506b5bad" x="49.819609" y="420.948663" style="stroke: #000000; stroke-width: 0.8"/>
      </g>
     </g>
     <g id="us-small-text_28">
      <!-- 0 -->
      <g transform="translate(37.258672 424.5888) scale(0.1 -0.1)">
       <use xlink:href="#us-small-ArialUnicodeMS-13"/>
      </g>
     </g>
    </g>
    <g id="us-small-text_29">
     <!-- 月末回撤 % -->
     <g transform="translate(22.268438 507.332131) rotate(-90) scale(0.1 -0.1)">
      <defs>
       <path id="us-small-ArialUnicodeMS-3997" d="M 5044 206 
Q 5044 -19 4897 -150 
Q 4750 -281 4500 -281 
L 3725 -281 
L 3531 231 
L 4359 206 
Q 4519 197 4519 341 
L 4519 1594 
L 2363 1594 
Q 2119 463 941 -488 
L 550 -91 
Q 1172 356 1520 920 
Q 1869 1484 1869 2053 
L 1869 5013 
L 5044 5013 
L 5044 206 
z
M 4519 3541 
L 4519 4544 
L 2375 4544 
L 2375 3541 
L 4519 3541 
z
M 4519 2059 
L 4519 3072 
L 2388 3072 
L 2375 2059 
L 4519 2059 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-39ba" d="M 6113 616 
L 5778 184 
Q 4184 888 3475 2644 
L 3475 -428 
L 2969 -428 
L 2956 2606 
Q 2238 1034 659 147 
L 353 581 
Q 1709 1228 2516 2656 
L 1050 2656 
L 1050 3122 
L 2969 3122 
L 2969 3975 
L 744 3975 
L 744 4441 
L 2969 4441 
L 2969 5369 
L 3475 5369 
L 3475 4441 
L 5709 4441 
L 5709 3975 
L 3475 3975 
L 3475 3122 
L 5416 3122 
L 5416 2656 
L 3963 2656 
Q 4675 1159 6113 616 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-296d" d="M 5575 -134 
L 5088 -147 
L 5088 313 
L 1313 313 
L 1313 -191 
L 825 -191 
L 825 4825 
L 5575 4825 
L 5575 -134 
z
M 5088 794 
L 5088 4366 
L 1313 4366 
L 1313 794 
L 5088 794 
z
M 4378 1509 
L 1997 1509 
L 1997 3653 
L 4378 3653 
L 4378 1509 
z
M 3891 1972 
L 3891 3194 
L 2484 3194 
L 2484 1972 
L 3891 1972 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-3733" d="M 6150 -56 
L 5759 -416 
Q 5250 34 4972 563 
Q 4619 -91 4244 -434 
L 3922 -116 
Q 4444 434 4722 1088 
Q 4406 1928 4341 2778 
L 4147 2522 
L 4000 2631 
L 4000 197 
Q 4000 19 3870 -134 
Q 3741 -288 3627 -306 
Q 3513 -325 3122 -325 
L 2950 147 
Q 3200 128 3303 128 
Q 3513 128 3513 281 
L 3513 756 
L 2625 756 
L 2625 -434 
L 2138 -434 
L 2138 2853 
L 3781 2853 
Q 3906 3016 3909 3028 
L 3794 2969 
L 3669 3225 
L 2059 3091 
L 1941 3572 
L 2322 3584 
Q 2559 4044 2619 4238 
L 1831 4238 
L 1831 4703 
L 2791 4703 
L 2791 5275 
L 3291 5275 
L 3291 4703 
L 4231 4703 
L 4231 4238 
L 3116 4238 
Q 2984 3859 2809 3597 
L 3431 3634 
Q 3309 3800 3181 3922 
L 3578 4109 
Q 3891 3806 4103 3413 
Q 4569 4478 4569 5344 
L 5044 5222 
Q 5019 4875 4825 4056 
L 5984 4056 
L 5984 3591 
L 5684 3591 
Q 5644 1978 5247 1088 
Q 5597 350 6150 -56 
z
M 5191 3591 
L 4738 3591 
Q 4738 2694 5006 1716 
Q 5213 2631 5191 3591 
z
M 3513 2059 
L 3513 2388 
L 2625 2388 
L 2625 2059 
L 3513 2059 
z
M 3513 1222 
L 3513 1594 
L 2625 1594 
L 2625 1222 
L 3513 1222 
z
M 2094 3641 
L 1522 3641 
L 1522 2522 
L 2016 2731 
L 2016 2247 
L 1522 2009 
L 1522 172 
Q 1522 -53 1401 -212 
Q 1281 -372 1107 -392 
Q 934 -413 556 -422 
L 397 78 
Q 663 38 806 38 
Q 1038 38 1038 213 
L 1038 1784 
L 481 1509 
L 250 1947 
L 1038 2303 
L 1038 3641 
L 313 3641 
L 313 4109 
L 1038 4109 
L 1038 5288 
L 1522 5288 
L 1522 4109 
L 2094 4109 
L 2094 3641 
z
" transform="scale(0.015625)"/>
       <path id="us-small-ArialUnicodeMS-8" d="M 4325 4659 
L 1838 -159 
L 1369 -159 
L 3872 4659 
L 4325 4659 
z
M 1428 4653 
Q 1856 4653 2137 4343 
Q 2419 4034 2419 3438 
Q 2419 2850 2131 2539 
Q 1844 2228 1434 2228 
Q 1009 2228 739 2540 
Q 469 2853 469 3475 
Q 469 3984 722 4318 
Q 975 4653 1428 4653 
z
M 1441 2619 
Q 1931 2619 1931 3463 
Q 1931 4269 1441 4269 
Q 953 4269 953 3419 
Q 953 2619 1441 2619 
z
M 4250 2253 
Q 4681 2253 4961 1943 
Q 5241 1634 5241 1038 
Q 5241 600 5087 328 
Q 4934 56 4709 -58 
Q 4484 -172 4256 -172 
Q 3831 -172 3561 140 
Q 3291 453 3291 1075 
Q 3291 1584 3544 1918 
Q 3797 2253 4250 2253 
z
M 4263 219 
Q 4756 219 4756 1063 
Q 4756 1869 4263 1869 
Q 3775 1869 3775 1019 
Q 3775 219 4263 219 
z
" transform="scale(0.015625)"/>
      </defs>
      <use xlink:href="#us-small-ArialUnicodeMS-3997"/>
      <use xlink:href="#us-small-ArialUnicodeMS-39ba" transform="translate(100 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-296d" transform="translate(200 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-3733" transform="translate(300 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-3" transform="translate(400 0)"/>
      <use xlink:href="#us-small-ArialUnicodeMS-8" transform="translate(427.78125 0)"/>
     </g>
    </g>
   </g>
   <g id="us-small-line2d_73">
    <path d="M 74.555082 420.948663 
L 78.753273 428.993361 
L 82.545188 420.948663 
L 86.743379 420.948663 
L 90.806145 428.998841 
L 95.004336 420.948663 
L 99.067102 420.948663 
L 103.265293 429.285511 
L 107.463484 444.127652 
L 111.52625 460.768928 
L 115.724442 444.803612 
L 119.787207 435.342068 
L 123.985399 449.876761 
L 128.18359 473.861875 
L 132.11093 478.030798 
L 136.309121 455.469595 
L 140.371887 446.943672 
L 144.570079 444.7562 
L 148.632844 443.53338 
L 152.831036 427.386349 
L 157.029227 420.948663 
L 161.091993 420.948663 
L 165.290184 433.28616 
L 169.35295 420.948663 
L 173.551141 420.948663 
L 177.749332 420.948663 
L 181.541247 420.948663 
L 185.739438 420.948663 
L 189.802204 420.948663 
L 194.000395 426.25541 
L 198.063161 420.948663 
L 202.261353 420.948663 
L 206.459544 422.979748 
L 210.52231 420.948663 
L 214.720501 420.948663 
L 218.783267 420.948663 
L 222.981458 420.948663 
L 227.179649 420.948663 
L 230.971564 432.082723 
L 235.169755 431.837838 
L 239.232521 431.283882 
L 243.430712 420.948663 
L 247.493478 420.948663 
L 251.69167 420.948663 
L 255.889861 420.948663 
L 259.952627 428.067583 
L 264.150818 457.827647 
L 268.213584 457.543329 
L 272.411775 485.057472 
L 276.609966 463.992274 
L 280.401881 452.040654 
L 284.600072 458.265729 
L 288.662838 452.176413 
L 292.861029 471.441491 
L 296.923795 455.175551 
L 301.121986 453.377249 
L 305.320178 468.33676 
L 309.382944 467.596113 
L 313.581135 461.21507 
L 317.643901 447.027913 
L 321.842092 437.525948 
L 326.040283 449.96424 
L 329.967623 476.170479 
L 334.165815 529.162877 
L 338.228581 492.089469 
L 342.426772 474.456877 
L 346.489538 460.884898 
L 350.687729 453.652633 
L 354.88592 437.013891 
L 358.948686 443.543863 
L 363.146877 434.430099 
L 367.209643 420.948663 
L 371.407834 420.948663 
L 375.606026 420.948663 
L 379.39794 420.948663 
L 383.596132 420.948663 
L 387.658897 420.948663 
L 391.857089 420.948663 
L 395.919855 420.948663 
L 400.118046 430.575714 
L 404.316237 425.805104 
L 408.379003 430.903595 
L 412.577194 422.206963 
L 416.63996 429.756421 
L 420.838151 420.948663 
L 425.036343 447.808568 
L 428.828257 437.524151 
L 433.026449 436.830571 
L 437.089214 457.765688 
L 441.287406 452.398226 
L 445.350172 484.927588 
L 449.548363 457.507311 
L 453.746554 461.364733 
L 457.80932 488.25258 
L 462.007511 457.679945 
L 466.070277 450.46627 
L 470.268468 466.312202 
L 474.46666 444.029471 
L 478.258574 452.408502 
L 482.456766 465.101733 
L 486.519531 464.890323 
L 490.717723 464.345142 
L 494.780488 443.535999 
L 498.97868 425.088806 
L 503.176871 439.23218 
L 507.239637 452.491008 
L 511.437828 466.14187 
L 515.500594 435.527337 
L 519.698785 420.948663 
L 523.896977 429.709022 
L 527.824317 420.948663 
L 532.022508 420.948663 
L 536.085274 444.567942 
L 540.283465 420.948663 
L 544.346231 431.399719 
L 548.544422 420.948663 
L 552.742614 420.948663 
L 556.805379 420.948663 
L 561.003571 424.821358 
L 565.066336 420.948663 
L 569.264528 444.583562 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #006f73; stroke-width: 2; stroke-linecap: square"/>
   </g>
   <g id="us-small-line2d_74">
    <path d="M 74.555082 420.948663 
L 78.753273 428.633468 
L 82.545188 420.948663 
L 86.743379 420.948663 
L 90.806145 430.482171 
L 95.004336 422.508498 
L 99.067102 420.948663 
L 103.265293 424.64292 
L 107.463484 442.588546 
L 111.52625 457.194087 
L 115.724442 443.703553 
L 119.787207 435.139443 
L 123.985399 449.874498 
L 128.18359 474.847506 
L 132.11093 475.410666 
L 136.309121 456.865311 
L 140.371887 452.097583 
L 144.570079 449.121395 
L 148.632844 448.174124 
L 152.831036 432.992433 
L 157.029227 428.271557 
L 161.091993 425.7045 
L 165.290184 439.439868 
L 169.35295 420.948663 
L 173.551141 420.948663 
L 177.749332 420.948663 
L 181.541247 420.948663 
L 185.739438 420.948663 
L 189.802204 420.948663 
L 194.000395 426.942478 
L 198.063161 420.948663 
L 202.261353 420.948663 
L 206.459544 423.824931 
L 210.52231 420.948663 
L 214.720501 420.948663 
L 218.783267 420.948663 
L 222.981458 420.948663 
L 227.179649 420.948663 
L 230.971564 431.759709 
L 235.169755 430.336842 
L 239.232521 428.976349 
L 243.430712 420.948663 
L 247.493478 420.948663 
L 251.69167 420.948663 
L 255.889861 420.948663 
L 259.952627 427.473202 
L 264.150818 459.955702 
L 268.213584 459.788784 
L 272.411775 490.154093 
L 276.609966 466.867821 
L 280.401881 454.356235 
L 284.600072 460.266328 
L 288.662838 452.756238 
L 292.861029 472.774973 
L 296.923795 454.36021 
L 301.121986 452.748232 
L 305.320178 467.348472 
L 309.382944 466.05682 
L 313.581135 458.883677 
L 317.643901 448.504431 
L 321.842092 439.560566 
L 326.040283 449.324201 
L 329.967623 473.054707 
L 334.165815 533.349761 
L 338.228581 497.447277 
L 342.426772 479.161325 
L 346.489538 467.494931 
L 350.687729 458.368579 
L 354.88592 441.605941 
L 358.948686 449.577383 
L 363.146877 442.40049 
L 367.209643 420.948663 
L 371.407834 420.948663 
L 375.606026 420.948663 
L 379.39794 420.948663 
L 383.596132 420.948663 
L 387.658897 420.948663 
L 391.857089 420.948663 
L 395.919855 420.948663 
L 400.118046 431.020688 
L 404.316237 424.668144 
L 408.379003 430.643753 
L 412.577194 420.948663 
L 416.63996 428.40922 
L 420.838151 420.948663 
L 425.036343 447.454897 
L 428.828257 441.437365 
L 433.026449 440.272706 
L 437.089214 461.02724 
L 441.287406 456.106955 
L 445.350172 481.348546 
L 449.548363 455.714568 
L 453.746554 460.946093 
L 457.80932 486.588621 
L 462.007511 456.93353 
L 466.070277 448.835583 
L 470.268468 464.405461 
L 474.46666 443.105861 
L 478.258574 446.860051 
L 482.456766 459.119122 
L 486.519531 461.812085 
L 490.717723 463.219456 
L 494.780488 442.806443 
L 498.97868 426.423957 
L 503.176871 438.823107 
L 507.239637 453.423279 
L 511.437828 469.72648 
L 515.500594 446.371404 
L 519.698785 420.948663 
L 523.896977 430.096944 
L 527.824317 420.948663 
L 532.022508 420.948663 
L 536.085274 442.136827 
L 540.283465 428.555141 
L 544.346231 439.157321 
L 548.544422 420.948663 
L 552.742614 421.729681 
L 556.805379 420.948663 
L 561.003571 422.934581 
L 565.066336 420.948663 
L 569.264528 446.004673 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #df8f32; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="us-small-line2d_75">
    <path d="M 74.555082 420.948663 
L 78.753273 431.653448 
L 82.545188 420.948663 
L 86.743379 420.948663 
L 90.806145 424.009653 
L 95.004336 420.948663 
L 99.067102 420.948663 
L 103.265293 439.117756 
L 107.463484 448.512209 
L 111.52625 468.990644 
L 115.724442 447.907876 
L 119.787207 442.258607 
L 123.985399 457.025819 
L 128.18359 477.63866 
L 132.11093 481.500765 
L 136.309121 450.544453 
L 140.371887 438.122268 
L 144.570079 438.148866 
L 148.632844 437.51001 
L 152.831036 420.948663 
L 157.029227 420.948663 
L 161.091993 420.948663 
L 165.290184 431.113221 
L 169.35295 420.948663 
L 173.551141 420.948663 
L 177.749332 420.948663 
L 181.541247 420.948663 
L 185.739438 420.948663 
L 189.802204 420.948663 
L 194.000395 424.434831 
L 198.063161 421.492682 
L 202.261353 420.948663 
L 206.459544 423.663625 
L 210.52231 420.948663 
L 214.720501 420.948663 
L 218.783267 420.948663 
L 222.981458 420.948663 
L 227.179649 420.948663 
L 230.971564 433.329151 
L 235.169755 433.917394 
L 239.232521 435.564525 
L 243.430712 432.514932 
L 247.493478 431.431722 
L 251.69167 426.958277 
L 255.889861 420.948663 
L 259.952627 427.876275 
L 264.150818 452.867375 
L 268.213584 454.312247 
L 272.411775 480.638439 
L 276.609966 458.432528 
L 280.401881 447.859009 
L 284.600072 456.897462 
L 288.662838 448.525692 
L 292.861029 472.389992 
L 296.923795 458.331643 
L 301.121986 461.065898 
L 305.320178 482.323103 
L 309.382944 475.265148 
L 313.581135 471.385808 
L 317.643901 452.434196 
L 321.842092 442.029076 
L 326.040283 463.067091 
L 329.967623 495.126756 
L 334.165815 542.045286 
L 338.228581 504.353295 
L 342.426772 486.120791 
L 346.489538 472.213328 
L 350.687729 470.977064 
L 354.88592 450.45807 
L 358.948686 458.09955 
L 363.146877 445.755107 
L 367.209643 420.948663 
L 371.407834 420.948663 
L 375.606026 420.948663 
L 379.39794 420.948663 
L 383.596132 420.948663 
L 387.658897 420.948663 
L 391.857089 420.948663 
L 395.919855 428.498595 
L 400.118046 431.571351 
L 404.316237 430.85096 
L 408.379003 435.288635 
L 412.577194 431.167371 
L 416.63996 434.825011 
L 420.838151 422.090284 
L 425.036343 445.291159 
L 428.828257 430.400853 
L 433.026449 433.424172 
L 437.089214 455.340181 
L 441.287406 449.015442 
L 445.350172 488.260182 
L 449.548363 453.97362 
L 453.746554 461.741143 
L 457.80932 493.986902 
L 462.007511 463.750685 
L 466.070277 453.684322 
L 470.268468 472.046187 
L 474.46666 440.629851 
L 478.258574 453.713728 
L 482.456766 468.191394 
L 486.519531 464.07245 
L 490.717723 464.922482 
L 494.780488 439.777379 
L 498.97868 420.948663 
L 503.176871 437.027761 
L 507.239637 444.262754 
L 511.437828 452.318768 
L 515.500594 420.948663 
L 519.698785 420.948663 
L 523.896977 431.641384 
L 527.824317 420.948663 
L 532.022508 420.948663 
L 536.085274 447.731663 
L 540.283465 420.948663 
L 544.346231 432.710067 
L 548.544422 420.948663 
L 552.742614 420.948663 
L 556.805379 420.948663 
L 561.003571 430.122806 
L 565.066336 420.948663 
L 569.264528 441.978662 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #4461aa; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="us-small-line2d_76">
    <path d="M 74.555082 420.948663 
L 78.753273 426.333275 
L 82.545188 420.948663 
L 86.743379 420.948663 
L 90.806145 433.74815 
L 95.004336 421.111422 
L 99.067102 420.948663 
L 103.265293 420.948663 
L 107.463484 440.83936 
L 111.52625 453.843568 
L 115.724442 442.710221 
L 119.787207 429.712948 
L 123.985399 443.986788 
L 128.18359 471.052843 
L 132.11093 475.496135 
L 136.309121 460.850855 
L 140.371887 455.992982 
L 144.570079 451.742155 
L 148.632844 449.977056 
L 152.831036 436.795986 
L 157.029227 434.902908 
L 161.091993 429.605487 
L 165.290184 443.713349 
L 169.35295 420.948663 
L 173.551141 420.948663 
L 177.749332 420.948663 
L 181.541247 420.948663 
L 185.739438 421.625417 
L 189.802204 420.948663 
L 194.000395 428.275266 
L 198.063161 420.948663 
L 202.261353 420.948663 
L 206.459544 422.243324 
L 210.52231 420.948663 
L 214.720501 420.948663 
L 218.783267 420.948663 
L 222.981458 420.948663 
L 227.179649 420.948663 
L 230.971564 430.746891 
L 235.169755 429.60912 
L 239.232521 426.696197 
L 243.430712 420.948663 
L 247.493478 420.948663 
L 251.69167 420.948663 
L 255.889861 420.948663 
L 259.952627 428.245842 
L 264.150818 462.449555 
L 268.213584 460.554004 
L 272.411775 489.175061 
L 276.609966 469.172762 
L 280.401881 455.937048 
L 284.600072 459.54066 
L 288.662838 455.578099 
L 292.861029 470.557691 
L 296.923795 452.234751 
L 301.121986 446.213081 
L 305.320178 455.304492 
L 309.382944 460.45022 
L 313.581135 451.738129 
L 317.643901 441.990419 
L 321.842092 433.33 
L 326.040283 437.755198 
L 329.967623 458.507302 
L 334.165815 517.159241 
L 338.228581 480.662219 
L 342.426772 463.588615 
L 346.489538 450.329235 
L 350.687729 437.509986 
L 354.88592 424.486805 
L 358.948686 429.981091 
L 363.146877 423.877626 
L 367.209643 420.948663 
L 371.407834 420.948663 
L 375.606026 420.948663 
L 379.39794 420.948663 
L 383.596132 420.948663 
L 387.658897 420.948663 
L 391.857089 420.948663 
L 395.919855 420.948663 
L 400.118046 436.219775 
L 404.316237 427.934367 
L 408.379003 433.507121 
L 412.577194 420.948663 
L 416.63996 431.806159 
L 420.838151 426.421871 
L 425.036343 455.962824 
L 428.828257 450.026528 
L 433.026449 446.022563 
L 437.089214 465.617934 
L 441.287406 461.22547 
L 445.350172 487.028241 
L 449.548363 466.356808 
L 453.746554 466.630525 
L 457.80932 488.130897 
L 462.007511 457.93207 
L 466.070277 453.430061 
L 470.268468 466.675101 
L 474.46666 453.056498 
L 478.258574 457.040924 
L 482.456766 467.85736 
L 486.519531 471.14688 
L 490.717723 469.365367 
L 494.780488 452.895134 
L 498.97868 440.304993 
L 503.176871 452.125037 
L 507.239637 470.355421 
L 511.437828 488.571095 
L 515.500594 463.348439 
L 519.698785 432.74972 
L 523.896977 439.189353 
L 527.824317 420.948663 
L 532.022508 420.948663 
L 536.085274 441.192449 
L 540.283465 428.99957 
L 544.346231 437.72837 
L 548.544422 420.948663 
L 552.742614 420.948663 
L 556.805379 420.948663 
L 561.003571 420.948663 
L 565.066336 420.948663 
L 569.264528 447.489209 
" clip-path="url(#us-small-p2b73023f9e)" style="fill: none; stroke: #a2557e; stroke-width: 1.2; stroke-linecap: square"/>
   </g>
   <g id="us-small-patch_9">
    <path d="M 49.819609 548.100117 
L 49.819609 414.893832 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
   <g id="us-small-patch_10">
    <path d="M 49.819609 548.100117 
L 594 548.100117 
" style="fill: none; stroke: #000000; stroke-width: 0.8; stroke-linejoin: miter; stroke-linecap: square"/>
   </g>
  </g>
  <g id="us-small-text_30">
   <!-- 美股小盘组：2015—2024 年公开组合毛收益 -->
   <g transform="translate(48.384 25.9825) scale(0.16 -0.16)">
    <defs>
     <path id="us-small-ArialUnicodeMS-5330" d="M 6041 3725 
Q 5884 2956 5484 2956 
L 5038 2956 
Q 4569 2956 4569 3431 
L 4569 4575 
L 3681 4575 
Q 3672 3913 3630 3656 
Q 3588 3400 3377 3129 
Q 3166 2859 2944 2719 
L 2578 3078 
Q 3188 3506 3188 4019 
L 3188 5044 
L 5050 5044 
L 5050 3559 
Q 5050 3425 5178 3425 
L 5375 3425 
Q 5556 3425 5588 3969 
L 6041 3725 
z
M 2528 206 
Q 2528 -22 2406 -151 
Q 2284 -281 2075 -281 
L 1606 -281 
L 1447 213 
Q 1763 159 1850 159 
Q 2041 159 2041 294 
L 2041 1947 
L 1275 1947 
Q 1284 366 744 -384 
L 325 -56 
Q 794 578 794 1925 
L 794 5031 
L 2528 5031 
L 2528 206 
z
M 2041 3725 
L 2041 4550 
L 1281 4550 
L 1281 3725 
L 2041 3725 
z
M 2041 2413 
L 2041 3256 
L 1281 3256 
L 1281 2413 
L 2041 2413 
z
M 6022 6 
L 5703 -416 
Q 4931 -222 4244 453 
Q 3625 -78 2847 -391 
L 2553 38 
Q 3375 328 3909 825 
Q 3500 1369 3256 2272 
L 2981 2272 
L 2981 2741 
L 5350 2741 
Q 5150 1569 4563 813 
Q 5172 216 6022 6 
z
M 4763 2272 
L 3738 2272 
Q 4003 1503 4238 1153 
Q 4569 1625 4763 2272 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-2e9e" d="M 3475 434 
Q 3475 59 3267 -100 
Q 3059 -259 2634 -259 
L 2244 -250 
Q 2147 -250 2069 -256 
L 1856 269 
Q 2253 238 2528 238 
Q 2841 238 2905 281 
Q 2969 325 2969 434 
L 2969 5234 
L 3475 5234 
L 3475 434 
z
M 5931 1709 
L 5472 1484 
Q 5088 2713 4019 3688 
L 4475 3928 
Q 5584 2922 5931 1709 
z
M 2181 3706 
Q 1769 2356 850 1459 
L 453 1791 
Q 1372 2700 1753 3922 
L 2181 3706 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-4967" d="M 5759 3003 
L 4750 3003 
L 4750 2113 
Q 4750 2047 4639 1878 
Q 4528 1709 4116 1709 
Q 3994 1709 3738 1716 
L 3591 2194 
Q 4019 2156 4153 2156 
Q 4263 2156 4263 2309 
L 4263 3003 
L 2094 3003 
Q 1947 2297 1505 1947 
Q 1063 1597 769 1491 
L 500 1913 
Q 1481 2319 1594 3003 
L 475 3003 
L 475 3444 
L 1594 3444 
L 1594 4722 
L 2578 4722 
Q 2713 4844 2919 5319 
L 3322 5113 
Q 3234 4928 3078 4722 
L 4750 4722 
L 4750 3444 
L 5759 3444 
L 5759 3003 
z
M 4263 3444 
L 4263 4281 
L 2081 4281 
L 2081 3444 
L 4263 3444 
z
M 3616 3841 
L 3353 3513 
Q 2894 3866 2497 3938 
L 2747 4238 
Q 3325 4056 3616 3841 
z
M 3566 2509 
L 3334 2088 
Q 2991 2366 2344 2484 
L 2597 2853 
Q 3034 2819 3566 2509 
z
M 5850 -206 
L 416 -206 
L 416 238 
L 1106 238 
L 1106 1575 
L 5125 1575 
L 5125 238 
L 5850 238 
L 5850 -206 
z
M 4641 238 
L 4641 1131 
L 3975 1131 
L 3975 238 
L 4641 238 
z
M 3488 238 
L 3488 1131 
L 2791 1131 
L 2791 238 
L 3488 238 
z
M 2303 238 
L 2303 1131 
L 1594 1131 
L 1594 238 
L 2303 238 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-ca7" d="M 6438 1428 
L -38 1428 
L -38 1888 
L 6438 1888 
L 6438 1428 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-3103" d="M 5869 1409 
L 3659 1409 
L 3659 -434 
L 3156 -434 
L 3156 1409 
L 659 1409 
L 659 1875 
L 1459 1875 
L 1459 3384 
L 3156 3384 
L 3156 4219 
L 1838 4219 
Q 1425 3363 953 2931 
L 550 3256 
Q 1381 3994 1734 5381 
L 2144 5184 
Q 2122 4997 2022 4684 
L 5606 4684 
L 5606 4219 
L 3659 4219 
L 3659 3384 
L 5294 3384 
L 5294 2919 
L 3659 2919 
L 3659 1875 
L 5869 1875 
L 5869 1409 
z
M 3156 1875 
L 3156 2919 
L 1947 2919 
L 1947 1875 
L 3156 1875 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-23fb" d="M 2553 4934 
Q 2391 4238 1856 3447 
Q 1322 2656 703 2194 
L 325 2572 
Q 941 3003 1428 3715 
Q 1916 4428 2094 5147 
L 2553 4934 
z
M 6119 2566 
L 5741 2188 
Q 5122 2647 4587 3439 
Q 4053 4231 3891 4928 
L 4353 5141 
Q 4534 4416 5021 3705 
Q 5509 2994 6119 2566 
z
M 5472 -122 
L 4984 -347 
Q 4916 -106 4703 347 
L 2897 200 
Q 1791 122 1113 31 
L 909 563 
L 1631 622 
Q 2425 1697 2809 3169 
L 3303 3003 
Q 2875 1572 2222 647 
L 4494 800 
Q 4141 1366 3809 1678 
L 4281 1888 
Q 5069 1134 5472 -122 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-318f" d="M 5797 2541 
L 4331 2541 
L 4331 -366 
L 3847 -366 
L 3847 2541 
L 2400 2541 
Q 2416 397 628 -366 
L 231 19 
Q 1919 609 1919 2541 
L 359 2541 
L 359 3009 
L 1913 3009 
L 1913 4525 
L 603 4525 
L 603 4991 
L 5538 4991 
L 5538 4525 
L 4331 4525 
L 4331 3009 
L 5797 3009 
L 5797 2541 
z
M 3847 3009 
L 3847 4525 
L 2400 4525 
L 2400 3009 
L 3847 3009 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-3e6a" d="M 6041 1259 
Q 5956 569 5728 211 
Q 5500 -147 5044 -147 
L 3322 -147 
Q 2663 -147 2663 494 
L 2663 1434 
L 616 1191 
L 556 1678 
L 2663 1925 
L 2663 2875 
L 897 2669 
L 856 3150 
L 2663 3359 
L 2663 4256 
Q 1838 4141 806 4103 
L 506 4588 
Q 2894 4619 5006 5259 
L 5363 4897 
Q 4622 4569 3150 4319 
L 3150 3406 
L 5141 3628 
L 5141 3150 
L 3150 2925 
L 3150 1984 
L 5709 2259 
L 5753 1772 
L 3150 1447 
L 3150 569 
Q 3150 319 3419 319 
L 5081 319 
Q 5309 319 5420 561 
Q 5531 803 5569 1459 
L 6041 1259 
z
" transform="scale(0.015625)"/>
    </defs>
    <use xlink:href="#us-small-ArialUnicodeMS-521d"/>
    <use xlink:href="#us-small-ArialUnicodeMS-5330" transform="translate(100 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-2e9e" transform="translate(200 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-4967" transform="translate(300 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-5153" transform="translate(400 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-19f6" transform="translate(500 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-15" transform="translate(600 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(655.609375 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-14" transform="translate(711.21875 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-18" transform="translate(766.828125 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-ca7" transform="translate(822.4375 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-15" transform="translate(922.4375 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-13" transform="translate(978.046875 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-15" transform="translate(1033.65625 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-17" transform="translate(1089.265625 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-3" transform="translate(1144.875 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-3103" transform="translate(1172.65625 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-23fb" transform="translate(1272.65625 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-318f" transform="translate(1372.65625 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-5153" transform="translate(1472.65625 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-2697" transform="translate(1572.65625 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-3e6a" transform="translate(1672.65625 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-37c5" transform="translate(1772.65625 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-4959" transform="translate(1872.65625 0)"/>
   </g>
  </g>
  <g id="us-small-text_31">
   <!-- 初始两部分各半，此后不互相转钱。未扣交易成本；对照不是母指数。 -->
   <g style="fill: #555555" transform="translate(48.384 592.757859) scale(0.09 -0.09)">
    <defs>
     <path id="us-small-ArialUnicodeMS-20b3" d="M 5831 4525 
L 4091 4525 
L 4091 3706 
L 5472 3706 
L 5472 122 
Q 5472 -88 5315 -213 
Q 5159 -338 4866 -338 
Q 4722 -338 4459 -306 
L 4294 159 
Q 4644 106 4844 106 
Q 5013 106 5013 238 
L 5013 3263 
L 4063 3263 
L 4019 2747 
Q 4647 2319 4953 1797 
L 4569 1447 
Q 4322 1950 3944 2272 
Q 3663 1159 2975 494 
L 2572 813 
Q 3581 1788 3616 3263 
L 2713 3263 
L 2650 2766 
Q 3050 2519 3347 2119 
L 3009 1772 
Q 2784 2128 2572 2266 
Q 2313 1238 1663 666 
L 1300 984 
Q 2144 1728 2209 3263 
L 1247 3263 
L 1247 -391 
L 763 -391 
L 763 3706 
L 2216 3706 
L 2216 4525 
L 397 4525 
L 397 4991 
L 5831 4991 
L 5831 4525 
z
M 3628 3706 
L 3628 4525 
L 2700 4525 
L 2700 3706 
L 3628 3706 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-6377" d="M 3681 4134 
L 622 4134 
L 622 4603 
L 1941 4603 
L 1941 5313 
L 2444 5313 
L 2444 4603 
L 3681 4603 
L 3681 4134 
z
M 5306 2875 
Q 6038 2188 6038 1400 
Q 6038 922 5795 634 
Q 5553 347 5166 384 
L 4756 422 
L 4628 959 
Q 5088 878 5166 878 
Q 5556 878 5556 1356 
Q 5556 2181 4794 2778 
Q 5006 3238 5416 4581 
L 4544 4581 
L 4544 -428 
L 4056 -428 
L 4056 5050 
L 5906 5050 
L 5906 4622 
Q 5484 3350 5306 2875 
z
M 3909 2450 
L 378 2450 
L 378 2919 
L 1588 2919 
Q 1363 3609 997 3922 
L 1422 4097 
Q 1822 3700 2047 3078 
L 1722 2919 
L 2222 2919 
Q 2700 3578 2797 4116 
L 3244 3922 
Q 3106 3459 2753 2919 
L 3909 2919 
L 3909 2450 
z
M 3316 -403 
L 2828 -403 
L 2828 38 
L 1394 38 
L 1394 -403 
L 909 -403 
L 909 1953 
L 3316 1953 
L 3316 -403 
z
M 2828 506 
L 2828 1484 
L 1394 1484 
L 1394 506 
L 2828 506 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-2693" d="M 6088 2247 
L 5797 1772 
Q 4028 2241 3238 2753 
Q 2069 2156 666 1791 
L 366 2222 
Q 1991 2641 2797 3059 
Q 2259 3491 1953 3963 
Q 1500 3394 1019 3072 
L 594 3397 
Q 1075 3650 1547 4219 
Q 2019 4788 2272 5350 
L 2753 5222 
Q 2666 4966 2491 4728 
L 4916 4728 
L 4916 4313 
Q 4403 3541 3700 3047 
Q 4050 2813 4815 2561 
Q 5581 2309 6088 2247 
z
M 4288 4263 
L 2344 4263 
Q 2656 3803 3244 3309 
Q 3941 3797 4288 4263 
z
M 4788 -403 
L 4281 -403 
L 4281 -31 
L 2181 -31 
L 2181 -416 
L 1678 -416 
L 1678 2009 
L 4788 2009 
L 4788 -403 
z
M 4281 434 
L 4281 1544 
L 2181 1544 
L 2181 434 
L 4281 434 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-25d9" d="M 5819 1288 
L 3406 1288 
L 3406 -428 
L 2913 -428 
L 2913 1281 
L 494 1281 
L 488 1753 
L 2913 1753 
L 2913 2491 
L 903 2491 
L 903 2950 
L 2913 2950 
L 2913 5275 
L 3406 5275 
L 3406 2950 
L 5403 2950 
L 5403 2491 
L 3413 2491 
L 3406 1753 
L 5819 1753 
L 5819 1288 
z
M 5478 4775 
Q 5206 3997 4300 3238 
L 3872 3578 
Q 4756 4178 5050 5056 
L 5478 4775 
z
M 2309 3456 
L 1888 3156 
Q 1463 4272 738 4684 
L 1166 4984 
Q 1819 4591 2309 3456 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-19e8" d="M 3541 0 
Q 3541 -397 3389 -606 
Q 3238 -816 3016 -903 
L 2863 -666 
Q 3213 -516 3216 0 
L 2900 0 
L 2900 641 
L 3541 641 
L 3541 0 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-3df3" d="M 6075 941 
Q 6000 509 5851 132 
Q 5703 -244 5388 -244 
L 4197 -244 
Q 3984 -244 3832 -67 
Q 3681 109 3681 331 
L 3681 5147 
L 4184 5147 
L 4184 2894 
Q 4863 3241 5416 3803 
L 5819 3488 
Q 5178 2809 4184 2363 
L 4184 384 
Q 4213 244 4331 244 
L 5253 244 
Q 5472 266 5556 844 
L 5606 1203 
L 6075 941 
z
M 3481 2875 
L 2534 2875 
L 2534 856 
L 3450 1178 
L 3450 653 
L 588 -366 
L 238 84 
L 884 288 
L 884 3891 
L 1388 3891 
L 1388 453 
L 2003 666 
L 2003 5125 
L 2534 5125 
L 2534 3341 
L 3481 3341 
L 3481 2875 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-269d" d="M 5925 3138 
L 1631 3138 
L 1631 1850 
Q 1631 747 709 -384 
L 281 -56 
Q 1147 881 1147 1869 
L 1147 4666 
Q 3191 4666 5275 5403 
L 5613 5025 
Q 3828 4219 1631 4178 
L 1631 3603 
L 5925 3603 
L 5925 3138 
z
M 5388 -409 
L 4903 -409 
L 4903 97 
L 2644 97 
L 2644 -409 
L 2156 -409 
L 2156 2338 
L 5388 2338 
L 5388 -409 
z
M 4903 563 
L 4903 1869 
L 2644 1869 
L 2644 563 
L 4903 563 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-209c" d="M 5900 4434 
L 3834 4434 
Q 3700 4209 3425 3816 
L 3425 -416 
L 2900 -416 
L 2900 3194 
Q 2281 2363 775 1528 
L 453 1947 
Q 1431 2419 2047 2975 
Q 2663 3531 3219 4434 
L 550 4434 
L 550 4922 
L 5900 4922 
L 5900 4434 
z
M 5941 1838 
L 5550 1503 
Q 4619 2634 3597 3078 
L 3938 3419 
Q 4969 2953 5941 1838 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-2121" d="M 5966 -38 
L 500 -38 
L 500 422 
L 4000 422 
L 4197 1491 
L 1947 1491 
L 1844 1019 
L 1338 1094 
L 2081 4500 
L 756 4500 
L 756 4959 
L 5722 4959 
L 5722 4500 
L 2613 4500 
L 2406 3572 
L 5075 3572 
L 4538 422 
L 5953 422 
L 5966 -38 
z
M 4494 3109 
L 2303 3109 
L 2047 1953 
L 4269 1953 
L 4494 3109 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-61fb" d="M 3047 1306 
L 2163 1069 
L 2163 -397 
L 1678 -397 
L 1678 947 
L 575 678 
Q 425 959 341 1147 
Q 819 1203 1678 1416 
L 1678 2150 
L 709 2150 
L 709 2613 
Q 994 3197 1172 3859 
L 469 3859 
L 469 4300 
L 1288 4300 
Q 1400 4688 1509 5288 
L 2003 5172 
L 1806 4300 
L 2894 4300 
L 2894 3859 
L 1684 3859 
Q 1538 3369 1228 2619 
L 1678 2619 
L 1678 3353 
L 2163 3353 
L 2163 2619 
L 3047 2619 
L 3047 2150 
L 2163 2150 
L 2163 1550 
L 3047 1766 
L 3047 1306 
z
M 5984 2753 
L 4109 2753 
Q 3963 2263 3903 2138 
L 5663 2138 
L 5663 1709 
Q 5438 1394 4825 641 
Q 5125 378 5528 -72 
L 5166 -422 
Q 4631 303 3566 909 
L 3872 1241 
L 4422 928 
Q 4850 1434 5019 1672 
L 3384 1672 
L 3384 2088 
Q 3531 2409 3628 2753 
L 2975 2753 
L 2975 3219 
L 3738 3219 
Q 3803 3453 3884 3963 
L 3144 3963 
L 3144 4422 
L 3922 4434 
Q 3975 4722 4006 5281 
L 4513 5184 
L 4434 4428 
L 5663 4428 
L 5663 3963 
L 4391 3963 
Q 4334 3441 4263 3219 
L 5984 3219 
L 5984 2753 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-6740" d="M 2766 4063 
L 1497 4063 
Q 1384 3722 1253 3488 
L 2681 3488 
L 2681 3022 
L 1900 3022 
L 1900 2363 
L 2759 2363 
L 2759 1894 
L 1900 1894 
L 1900 525 
L 2759 953 
L 2759 428 
L 1581 -178 
L 1319 244 
Q 1416 341 1416 447 
L 1416 1894 
L 488 1894 
L 488 2363 
L 1416 2363 
L 1416 3022 
L 991 3022 
Q 838 2781 628 2559 
L 244 2859 
Q 1066 3772 1331 5313 
L 1784 5166 
Q 1728 4822 1638 4531 
L 2766 4531 
L 2766 4063 
z
M 6156 416 
Q 6125 163 5972 -143 
Q 5819 -450 5566 -450 
Q 5306 -450 4931 -89 
Q 4556 272 4372 609 
Q 3363 -163 2706 -416 
L 2369 -25 
Q 3419 397 4109 1031 
Q 3875 1531 3788 2169 
L 2894 2106 
L 2853 2553 
L 3731 2613 
Q 3691 3134 3700 3303 
L 2944 3263 
L 2894 3725 
L 3694 3769 
L 3694 5241 
L 4178 5241 
L 4178 3794 
L 5672 3897 
L 5709 3444 
L 4178 3334 
Q 4178 3222 4213 2650 
L 5806 2753 
L 5844 2303 
L 4263 2194 
Q 4297 1928 4519 1375 
Q 5156 2088 5216 2188 
L 5606 1925 
Q 5322 1466 4750 922 
Q 5069 391 5538 72 
Q 5578 97 5734 659 
L 6156 416 
z
M 5388 4244 
L 5013 3956 
Q 4700 4497 4256 4763 
L 4556 5044 
Q 5166 4694 5388 4244 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-11ed" d="M 1466 1503 
Q 1847 1503 2117 1231 
Q 2388 959 2388 575 
Q 2388 194 2119 -76 
Q 1850 -347 1472 -347 
Q 1091 -347 820 -76 
Q 550 194 550 575 
Q 550 959 819 1231 
Q 1088 1503 1466 1503 
z
M 1469 44 
Q 1691 44 1845 201 
Q 2000 359 2000 581 
Q 2000 803 1844 958 
Q 1688 1113 1469 1113 
Q 1250 1113 1094 958 
Q 938 803 938 581 
Q 938 359 1092 201 
Q 1247 44 1469 44 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-39b9" d="M 6069 556 
L 5778 153 
Q 4128 931 3513 2456 
L 3513 -428 
L 3028 -416 
L 3028 2406 
Q 2241 1053 738 172 
L 416 569 
Q 1828 1384 2491 2491 
L 775 2491 
L 775 2956 
L 3003 2956 
L 3003 3938 
L 1191 3938 
L 1191 4403 
L 3003 4403 
L 3003 5363 
L 3513 5363 
L 3513 4403 
L 5306 4403 
L 5306 3938 
L 3513 3938 
L 3513 2956 
L 5747 2956 
L 5747 2491 
L 3988 2491 
Q 4616 1263 6069 556 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-34f2" d="M 3041 2169 
L 2125 1875 
L 2125 97 
Q 2094 -150 1922 -294 
Q 1750 -438 1113 -403 
L 947 91 
Q 1253 63 1331 63 
Q 1550 63 1584 102 
Q 1619 141 1619 366 
L 1619 1709 
L 781 1388 
L 453 1825 
Q 653 1866 1619 2169 
L 1619 3609 
L 603 3609 
L 603 4078 
L 1619 4078 
L 1619 5313 
L 2125 5313 
L 2125 4078 
L 3041 4078 
L 3041 3609 
L 2125 3609 
L 2125 2356 
L 3041 2656 
L 3041 2169 
z
M 5716 -275 
L 5228 -275 
L 5228 294 
L 3681 294 
L 3681 -275 
L 3194 -275 
L 3194 4800 
L 5716 4800 
L 5716 -275 
z
M 5228 763 
L 5228 4331 
L 3681 4331 
L 3681 763 
L 5228 763 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-2133" d="M 5759 3969 
L 684 3969 
L 684 4428 
L 2956 4428 
L 2956 5259 
L 3444 5259 
L 3444 4428 
L 5759 4428 
L 5759 3969 
z
M 5722 2450 
L 5306 2131 
Q 4831 2956 3603 3525 
L 4056 3841 
Q 5247 3244 5722 2450 
z
M 2644 3553 
Q 2209 2806 978 2175 
L 634 2559 
Q 1816 3119 2291 3841 
L 2644 3553 
z
M 6053 84 
L 5728 -384 
Q 4272 -9 3250 850 
Q 2447 84 763 -416 
L 447 63 
Q 2134 438 2875 1216 
Q 2388 1741 2016 2656 
L 2456 2847 
Q 2816 2025 3225 1550 
Q 3741 2184 4006 2925 
L 4447 2694 
Q 4094 1797 3584 1209 
Q 4456 472 6053 84 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-38a2" d="M 5544 2266 
Q 5475 1613 5370 1036 
Q 5266 459 5189 212 
Q 5113 -34 4948 -161 
Q 4784 -288 4531 -288 
Q 4384 -288 3775 -153 
L 3669 372 
Q 4366 172 4500 172 
Q 4778 172 5013 1797 
L 4488 1797 
Q 4050 484 2394 -428 
L 2041 -56 
Q 3513 706 3969 1797 
L 3272 1797 
Q 2597 575 800 13 
L 481 409 
Q 2078 878 2706 1797 
L 2094 1797 
Q 1491 1344 844 1119 
L 513 1522 
Q 1744 1928 2297 2644 
L 1509 2644 
L 1509 5006 
L 5063 5006 
L 5063 2644 
L 2875 2644 
Q 2688 2359 2547 2266 
L 5544 2266 
z
M 4581 4084 
L 4581 4538 
L 1991 4538 
L 1991 4084 
L 4581 4084 
z
M 4581 3109 
L 4581 3641 
L 1991 3641 
L 1991 3109 
L 4581 3109 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-349f" d="M 6047 806 
Q 6053 666 5929 261 
Q 5806 -144 5709 -276 
Q 5613 -409 5428 -409 
Q 5159 -409 4751 47 
Q 4344 503 4153 947 
Q 3516 272 2859 -128 
L 2419 213 
Q 3338 709 3922 1409 
Q 3591 2216 3438 3769 
L 1516 3769 
L 1516 2900 
L 3225 2900 
Q 3181 1622 3020 1140 
Q 2859 659 2338 659 
Q 2150 659 1819 709 
L 1606 1241 
Q 2009 1119 2363 1119 
Q 2584 1119 2648 1505 
Q 2713 1891 2725 2431 
L 1509 2431 
Q 1481 1084 1270 496 
Q 1059 -91 728 -459 
L 319 -153 
Q 1000 541 1013 2009 
L 1031 4238 
L 3391 4238 
Q 3359 4997 3359 5319 
L 3841 5319 
Q 3850 4619 3878 4238 
L 5747 4238 
L 5747 3769 
L 3909 3769 
Q 4025 2497 4288 1838 
Q 4734 2413 5106 3431 
L 5550 3284 
Q 5113 2075 4500 1325 
Q 4738 869 5008 498 
Q 5278 128 5409 128 
Q 5450 128 5509 462 
Q 5569 797 5575 1081 
L 6047 806 
z
M 5650 4659 
L 5306 4359 
Q 4688 4859 4063 4928 
L 4447 5275 
Q 5144 5119 5650 4659 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-39bb" d="M 6113 1184 
L 5766 775 
Q 5031 1316 4457 1961 
Q 3884 2606 3444 3922 
L 3444 1613 
L 4678 1613 
L 4678 1147 
L 3444 1147 
L 3444 -428 
L 2956 -428 
L 2956 1147 
L 1728 1147 
L 1728 1613 
L 2950 1613 
L 2950 3872 
Q 2413 2063 659 744 
L 263 1125 
Q 1884 2178 2419 3822 
L 641 3822 
L 641 4288 
L 2956 4288 
L 2956 5294 
L 3444 5294 
L 3444 4288 
L 5728 4288 
L 5728 3822 
L 4019 3822 
Q 4450 2203 6113 1184 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-19f7" d="M 3541 2675 
L 2900 2675 
L 2900 3316 
L 3541 3316 
L 3541 2675 
z
M 3541 0 
Q 3541 -397 3389 -606 
Q 3238 -816 3016 -903 
L 2863 -666 
Q 3213 -516 3216 0 
L 2900 0 
L 2900 641 
L 3541 641 
L 3541 0 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-43f6" d="M 5728 5044 
Q 5644 3916 5483 3577 
Q 5322 3238 4966 3238 
Q 4866 3238 4288 3353 
L 4172 3866 
Q 4628 3716 4809 3716 
Q 5059 3716 5106 3981 
L 5216 4575 
L 4347 4575 
Q 4194 3397 2925 3016 
L 2656 3469 
Q 3713 3625 3847 4575 
L 2963 4575 
L 2950 5044 
L 5728 5044 
z
M 2613 1394 
L 2150 1394 
L 2150 1784 
L 1356 1784 
L 1356 1394 
L 872 1394 
L 872 4903 
L 2613 4903 
L 2613 1394 
z
M 2150 3591 
L 2138 4441 
L 1375 4453 
L 1375 3591 
L 2150 3591 
z
M 2150 2253 
L 2150 3122 
L 1356 3122 
L 1356 2253 
L 2150 2253 
z
M 5538 1178 
L 5050 1178 
L 5050 1522 
L 3641 1522 
L 3641 1178 
L 3156 1178 
L 3156 3053 
L 5538 3053 
L 5538 1178 
z
M 5050 1991 
L 5050 2584 
L 3641 2584 
L 3641 1991 
L 5050 1991 
z
M 1766 928 
Q 1563 325 813 -397 
L 428 -84 
Q 1075 447 1381 1153 
L 1766 928 
z
M 6081 -147 
L 5650 -384 
Q 5359 481 4744 909 
L 5222 1119 
Q 5688 716 6081 -147 
z
M 4666 -103 
L 4219 -300 
Q 4056 416 3475 928 
L 3928 1113 
Q 4369 684 4666 -103 
z
M 3169 -128 
L 2719 -281 
Q 2588 434 2081 941 
L 2534 1094 
Q 2931 659 3169 -128 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-38be" d="M 5006 2822 
L 1491 2822 
L 1491 5056 
L 5006 5056 
L 5006 2822 
z
M 4500 4191 
L 4500 4588 
L 1978 4588 
L 1978 4191 
L 4500 4191 
z
M 4500 3291 
L 4500 3725 
L 1978 3725 
L 1978 3291 
L 4500 3291 
z
M 6144 366 
L 5900 -128 
L 3744 -128 
Q 2825 -128 1797 763 
Q 1513 6 709 -422 
L 434 6 
Q 909 228 1190 637 
Q 1472 1047 1491 1875 
L 1966 1797 
Q 1966 1488 1925 1269 
Q 2419 747 2994 544 
L 2994 2047 
L 634 2047 
L 634 2516 
L 5869 2516 
L 5869 2047 
L 3500 2047 
L 3500 1556 
L 5381 1556 
L 5381 1088 
L 3500 1088 
L 3500 397 
Q 3831 338 4013 341 
L 6144 366 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-3e5c" d="M 5959 2650 
L 5141 2650 
Q 5066 1550 5013 1119 
L 5728 1119 
L 5728 634 
L 4959 634 
Q 4900 -125 4673 -273 
Q 4447 -422 4141 -422 
Q 3784 -422 3359 -353 
L 3169 197 
Q 3822 63 4269 63 
Q 4434 63 4469 634 
L 1478 634 
L 1422 341 
L 922 422 
L 1275 2650 
L 494 2650 
L 494 3138 
L 1325 3138 
Q 1450 4009 1550 5013 
L 5338 5013 
Q 5244 3616 5184 3138 
L 5959 3138 
L 5959 2650 
z
M 4806 4525 
L 2759 4525 
Q 3469 4269 4141 3584 
L 3781 3244 
Q 3269 3859 2297 4269 
L 2578 4525 
L 2003 4525 
L 1825 3138 
L 4684 3138 
L 4806 4525 
z
M 4647 2650 
L 2541 2650 
Q 3459 2188 3938 1516 
L 3559 1203 
Q 3028 1900 2119 2406 
L 2438 2650 
L 1759 2650 
Q 1663 1838 1538 1119 
L 4519 1119 
Q 4653 2413 4647 2650 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-3596" d="M 5997 3938 
Q 5863 3278 5667 3089 
Q 5472 2900 5153 2900 
L 3341 2900 
Q 3003 2900 2817 3079 
Q 2631 3259 2631 3584 
L 2631 5306 
L 3138 5306 
L 3138 4288 
Q 4403 4463 5466 5094 
L 5759 4709 
Q 4706 4056 3144 3834 
L 3150 3584 
Q 3159 3366 3384 3366 
L 5172 3366 
Q 5422 3366 5509 4141 
L 5997 3938 
z
M 2541 2069 
L 1791 1772 
L 1791 91 
Q 1744 -400 1166 -409 
L 716 -416 
L 563 84 
L 959 72 
Q 1306 59 1306 275 
L 1306 1594 
Q 919 1422 628 1319 
L 331 1734 
Q 1016 1941 1306 2059 
L 1306 3591 
L 494 3591 
L 494 4056 
L 1306 4056 
L 1306 5306 
L 1791 5306 
L 1791 4056 
L 2484 4056 
L 2484 3591 
L 1791 3591 
L 1791 2247 
Q 2478 2534 2541 2553 
L 2541 2069 
z
M 5606 -409 
L 5119 -409 
L 5119 -38 
L 3213 -38 
L 3213 -434 
L 2725 -434 
L 2725 2491 
L 5606 2491 
L 5606 -409 
z
M 5119 1472 
L 5119 2022 
L 3213 2022 
L 3213 1472 
L 5119 1472 
z
M 5119 428 
L 5119 1006 
L 3213 1006 
L 3213 428 
L 5119 428 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-37ff" d="M 6138 19 
L 5806 -378 
Q 5031 194 4697 716 
Q 4344 144 3328 -441 
L 2981 -50 
Q 3966 434 4403 1153 
Q 4038 1834 3866 2753 
Q 3678 2356 3353 1919 
L 2950 2203 
Q 3838 3172 3963 5253 
L 4409 5125 
Q 4341 4384 4269 4006 
L 5984 4006 
L 5984 3547 
L 5619 3541 
L 5594 3341 
Q 5441 2113 4978 1191 
Q 5281 672 6138 19 
z
M 5166 3541 
L 4172 3541 
Q 4297 2419 4691 1650 
Q 5038 2513 5166 3541 
z
M 3438 3653 
L 2209 3653 
L 2209 2338 
L 1919 2338 
Q 1900 2269 1753 1931 
L 3225 1931 
L 3225 1472 
L 2913 1472 
Q 2763 991 2503 666 
Q 2947 353 3103 184 
L 2747 -172 
Q 2463 138 2150 313 
Q 1322 -225 563 -428 
L 269 6 
Q 1106 163 1684 563 
Q 1291 756 703 884 
L 1038 1472 
L 403 1472 
L 403 1931 
L 1259 1931 
Q 1328 2056 1466 2553 
L 1747 2484 
L 1747 3653 
L 1716 3653 
Q 1413 2881 678 2456 
L 378 2803 
Q 938 3091 1241 3653 
L 403 3653 
L 403 4122 
L 1747 4122 
L 1747 5228 
L 2209 5228 
L 2209 4122 
L 3438 4122 
L 3438 3653 
z
M 2406 1472 
L 1538 1472 
Q 1422 1241 1369 1153 
Q 1388 1159 2069 884 
Q 2219 1031 2406 1472 
z
M 1625 4441 
L 1288 4159 
Q 1022 4547 575 4813 
L 878 5075 
Q 1394 4844 1625 4441 
z
M 3384 4844 
Q 3097 4409 2669 4172 
L 2322 4481 
Q 2806 4759 3047 5069 
L 3384 4844 
z
M 3303 2888 
L 2944 2578 
Q 2706 3025 2291 3297 
L 2584 3566 
Q 2988 3359 3303 2888 
z
" transform="scale(0.015625)"/>
    </defs>
    <use xlink:href="#us-small-ArialUnicodeMS-24ac"/>
    <use xlink:href="#us-small-ArialUnicodeMS-2c5a" transform="translate(100 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-20b3" transform="translate(200 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-6377" transform="translate(300 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-2495" transform="translate(400 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-2693" transform="translate(500 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-25d9" transform="translate(600 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-19e8" transform="translate(700 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-3df3" transform="translate(800 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-269d" transform="translate(900 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-209c" transform="translate(1000 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-2121" transform="translate(1100 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-4987" transform="translate(1200 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-61fb" transform="translate(1300 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-6740" transform="translate(1400 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-11ed" transform="translate(1500 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-39b9" transform="translate(1600 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-34f2" transform="translate(1700 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-2133" transform="translate(1800 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-38a2" transform="translate(1900 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-349f" transform="translate(2000 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-39bb" transform="translate(2100 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-19f7" transform="translate(2200 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-2e88" transform="translate(2300 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-43f6" transform="translate(2400 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-209c" transform="translate(2500 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-38be" transform="translate(2600 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-3e5c" transform="translate(2700 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-3596" transform="translate(2800 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-37ff" transform="translate(2900 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-11ed" transform="translate(3000 0)"/>
   </g>
   <!-- 月末回撤可能小于真实日内跌幅。 -->
   <g style="fill: #555555" transform="translate(48.384 603.432) scale(0.09 -0.09)">
    <defs>
     <path id="us-small-ArialUnicodeMS-267e" d="M 5925 4434 
L 5113 4434 
L 5113 306 
Q 5113 -88 4969 -248 
Q 4825 -409 4678 -409 
L 3700 -409 
L 3513 122 
Q 3706 100 3872 103 
L 4481 116 
Q 4609 116 4609 269 
L 4609 4434 
L 628 4434 
L 628 4922 
L 5925 4922 
L 5925 4434 
z
M 3756 813 
L 3250 813 
L 3250 1288 
L 1925 1288 
L 1925 813 
L 1441 813 
L 1441 3681 
L 3756 3681 
L 3756 813 
z
M 3250 1772 
L 3250 3194 
L 1925 3194 
L 1925 1772 
L 3250 1772 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-538c" d="M 3419 3494 
L 3003 3231 
L 2809 3591 
L 531 3469 
L 403 3963 
L 844 3975 
Q 1316 4656 1644 5403 
L 2131 5191 
Q 1716 4381 1409 3975 
L 2541 4019 
Q 2359 4294 2144 4500 
L 2572 4738 
Q 3122 4225 3419 3494 
z
M 5978 3675 
Q 5825 2528 5294 2528 
L 4122 2528 
Q 3800 2563 3676 2722 
Q 3553 2881 3553 3009 
L 3553 5222 
L 4038 5222 
L 4038 4197 
Q 4997 4469 5556 4909 
L 5850 4544 
Q 5219 4009 4038 3719 
L 4038 3175 
Q 4066 2994 4366 2994 
L 5209 2994 
Q 5431 2994 5509 3853 
L 5978 3675 
z
M 3059 250 
Q 3059 28 2954 -105 
Q 2850 -238 2701 -277 
Q 2553 -316 1972 -306 
L 1791 184 
Q 2147 147 2297 147 
Q 2572 147 2572 319 
L 2572 922 
L 1234 922 
L 1234 -353 
L 750 -353 
L 750 3091 
L 3059 3091 
L 3059 250 
z
M 2572 2241 
L 2572 2625 
L 1234 2625 
L 1234 2241 
L 2572 2241 
z
M 2572 1388 
L 2572 1772 
L 1234 1772 
L 1234 1388 
L 2572 1388 
z
M 6138 800 
Q 6019 134 5831 -73 
Q 5644 -281 5369 -281 
L 4166 -281 
Q 3859 -281 3718 -92 
Q 3578 97 3578 263 
L 3578 2309 
L 4063 2309 
L 4063 1422 
Q 4950 1625 5606 2113 
L 5941 1753 
Q 5169 1163 4063 941 
L 4063 347 
Q 4063 184 4281 184 
L 5319 184 
Q 5469 184 5544 362 
Q 5619 541 5663 1031 
L 6138 800 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-211d" d="M 5813 2559 
L 3463 2559 
L 3463 72 
Q 3406 -409 2841 -422 
L 2075 -441 
L 1900 109 
L 2669 72 
Q 2938 59 2938 288 
L 2938 2559 
L 569 2559 
L 569 3047 
L 2938 3047 
L 2938 4459 
L 997 4459 
L 997 4947 
L 5363 4947 
L 5363 4459 
L 3463 4459 
L 3463 3047 
L 5813 3047 
L 5813 2559 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-49ae" d="M 5784 4441 
L 3450 4441 
L 3450 4097 
L 5044 4097 
L 5044 1516 
L 1434 1516 
L 1434 4097 
L 2956 4097 
L 2956 4441 
L 575 4441 
L 575 4909 
L 2956 4909 
L 2956 5344 
L 3450 5344 
L 3450 4909 
L 5784 4909 
L 5784 4441 
z
M 4544 3384 
L 4544 3647 
L 1919 3647 
L 1919 3384 
L 4544 3384 
z
M 4544 2694 
L 4544 2944 
L 1919 2944 
L 1919 2694 
L 4544 2694 
z
M 4544 1959 
L 4544 2253 
L 1919 2253 
L 1919 1959 
L 4544 1959 
z
M 5991 756 
L 409 756 
L 409 1222 
L 5991 1222 
L 5991 756 
z
M 5966 -122 
L 5678 -519 
Q 4703 141 3541 341 
L 3816 709 
Q 4922 547 5966 -122 
z
M 2803 366 
Q 1963 -303 709 -538 
L 453 -84 
Q 1528 53 2472 684 
L 2803 366 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-2e2d" d="M 5791 3513 
L 5306 3513 
L 5306 4103 
L 1063 4103 
L 1063 3513 
L 575 3513 
L 575 4569 
L 3144 4569 
Q 2956 4859 2547 5094 
L 2913 5325 
Q 3375 5066 3591 4666 
L 3384 4581 
L 3384 4569 
L 5791 4569 
L 5791 3513 
z
M 3122 3066 
L 2741 2803 
Q 2453 3331 1856 3731 
L 2181 4006 
Q 2759 3669 3122 3066 
z
M 5894 1684 
L 3634 1684 
Q 3063 131 831 -366 
L 469 72 
Q 2528 400 3109 1684 
L 469 1684 
L 469 2150 
L 3256 2150 
Q 3366 2500 3366 3022 
L 3366 3903 
L 3847 3903 
Q 3847 2459 3756 2150 
L 5894 2150 
L 5894 1684 
z
M 2450 2478 
L 2100 2188 
Q 1769 2722 1191 3084 
L 1503 3372 
Q 2100 3031 2450 2478 
z
M 5947 -13 
L 5613 -391 
Q 4900 422 3566 1006 
L 3816 1363 
Q 5075 866 5947 -13 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-3874" d="M 5044 -178 
L 4538 -178 
L 4538 441 
L 2022 441 
L 2022 -206 
L 1516 -206 
L 1516 4781 
L 5044 4781 
L 5044 -178 
z
M 4538 2881 
L 4538 4313 
L 2022 4313 
L 2022 2881 
L 4538 2881 
z
M 4538 909 
L 4538 2413 
L 2022 2413 
L 2022 909 
L 4538 909 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-2414" d="M 5538 84 
Q 5538 -341 4872 -341 
Q 4713 -341 4481 -331 
L 4294 141 
Q 4619 116 4800 116 
Q 5075 116 5075 281 
L 5075 3725 
L 3450 3725 
Q 3450 3322 3413 2938 
Q 4216 2334 4819 1300 
L 4428 1006 
Q 3994 1759 3263 2413 
Q 2831 1444 1772 872 
L 1478 1281 
Q 2225 1684 2600 2196 
Q 2975 2709 2975 3725 
L 1325 3725 
L 1325 -409 
L 838 -409 
L 838 4191 
L 3009 4191 
L 3009 5275 
L 3469 5275 
L 3469 4191 
L 5538 4191 
L 5538 84 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-605b" d="M 6241 38 
Q 6175 -75 5919 -378 
Q 5316 -34 4970 506 
Q 4625 1047 4453 2041 
Q 4016 291 2450 -366 
L 2069 6 
Q 2934 406 3345 897 
Q 3756 1388 3969 2266 
L 2772 2266 
L 2772 2731 
L 4044 2731 
Q 4081 2978 4122 3756 
L 3553 3756 
Q 3344 3197 3022 2797 
L 2597 3059 
Q 3297 4028 3256 4966 
L 3725 4856 
Q 3725 4641 3675 4225 
L 4128 4225 
L 4128 5403 
L 4616 5363 
L 4616 4225 
L 5728 4225 
L 5728 3756 
L 4603 3756 
Q 4563 3072 4525 2731 
L 5991 2731 
L 5991 2266 
L 4903 2266 
Q 5003 1538 5367 914 
Q 5731 291 6241 38 
z
M 2841 672 
Q 2372 531 1605 234 
Q 838 -63 666 -122 
L 331 306 
L 775 428 
L 775 2669 
L 1259 2669 
L 1259 588 
L 1600 722 
L 1600 3169 
L 825 3169 
L 825 5094 
L 2572 5094 
L 2572 3169 
L 2088 3169 
L 2088 2509 
L 2706 2509 
L 2706 2041 
L 2088 2041 
L 2088 903 
L 2841 1172 
L 2841 672 
z
M 2113 3634 
L 2113 4628 
L 1313 4628 
L 1313 3634 
L 2113 3634 
z
" transform="scale(0.015625)"/>
     <path id="us-small-ArialUnicodeMS-30d4" d="M 2528 1478 
Q 2528 1294 2429 1178 
Q 2331 1063 2187 1048 
Q 2044 1034 1819 1025 
L 1747 1369 
L 1747 -441 
L 1269 -441 
L 1269 3572 
L 1031 3572 
L 1031 891 
L 544 891 
L 544 4038 
L 1269 4038 
L 1269 5306 
L 1753 5306 
L 1753 4038 
L 2528 4038 
L 2528 1478 
z
M 2041 1644 
L 2041 3572 
L 1753 3572 
L 1753 1503 
Q 2041 1484 2041 1644 
z
M 5913 4556 
L 2400 4556 
L 2400 5025 
L 5913 5025 
L 5913 4556 
z
M 5363 2881 
L 3022 2881 
L 3022 4306 
L 5363 4306 
L 5363 2881 
z
M 4878 3347 
L 4878 3841 
L 3506 3841 
L 3506 3347 
L 4878 3347 
z
M 5619 -416 
L 5131 -416 
L 5131 -38 
L 3231 -38 
L 3231 -441 
L 2747 -441 
L 2747 2566 
L 5619 2566 
L 5619 -416 
z
M 5131 1516 
L 5131 2100 
L 4428 2100 
L 4428 1516 
L 5131 1516 
z
M 3944 1516 
L 3944 2100 
L 3231 2100 
L 3231 1516 
L 3944 1516 
z
M 5131 428 
L 5131 1050 
L 4428 1050 
L 4428 428 
L 5131 428 
z
M 3944 428 
L 3944 1050 
L 3231 1050 
L 3231 428 
L 3944 428 
z
" transform="scale(0.015625)"/>
    </defs>
    <use xlink:href="#us-small-ArialUnicodeMS-3997"/>
    <use xlink:href="#us-small-ArialUnicodeMS-39ba" transform="translate(100 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-296d" transform="translate(200 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-3733" transform="translate(300 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-267e" transform="translate(400 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-538c" transform="translate(500 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-2e9e" transform="translate(600 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-211d" transform="translate(700 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-49ae" transform="translate(800 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-2e2d" transform="translate(900 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-3874" transform="translate(1000 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-2414" transform="translate(1100 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-605b" transform="translate(1200 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-30d4" transform="translate(1300 0)"/>
    <use xlink:href="#us-small-ArialUnicodeMS-11ed" transform="translate(1400 0)"/>
   </g>
  </g>
 </g>
 <defs>
  <clipPath id="us-small-pa95c6f6faf">
   <rect x="49.819609" y="79.919375" width="544.180391" height="133.206286"/>
  </clipPath>
  <clipPath id="us-small-paeb1314bb3">
   <rect x="49.819609" y="227.425661" width="544.180391" height="173.168171"/>
  </clipPath>
  <clipPath id="us-small-p2b73023f9e">
   <rect x="49.819609" y="414.893832" width="544.180391" height="133.206286"/>
  </clipPath>
 </defs>
</svg>


### 所有预设时期的增量与反例

下表“跌幅改善”为正表示少跌，为负表示跌得更多。三段历史均已看过，最近20个月不是新前向；短时期年化只是历史折算。

| 时期 | 规模 | 比盈利＋动量年化多/少 | 比盈利＋动量跌幅改善 | 比单独动量年化多/少 | 比单独盈利低扩张年化多/少 |
| --- | --- | --- | --- | --- | --- |
| 1963-07—2014-12 | 大盘 | +0.23 个百分点 | -1.83 个百分点 | -0.49 个百分点 | +0.63 个百分点 |
| 1963-07—2014-12 | 小盘 | +1.26 个百分点 | +5.67 个百分点 | +0.52 个百分点 | -0.42 个百分点 |
| 2015—2024 | 大盘 | +1.56 个百分点 | -0.84 个百分点 | +2.38 个百分点 | -2.00 个百分点 |
| 2015—2024 | 小盘 | +1.46 个百分点 | +1.42 个百分点 | +0.75 个百分点 | -0.71 个百分点 |
| 2025-01—2026-08 | 大盘 | +1.94 个百分点 | -0.98 个百分点 | -1.09 个百分点 | +1.10 个百分点 |
| 2025-01—2026-08 | 小盘 | -2.64 个百分点 | -0.60 个百分点 | -7.35 个百分点 | +7.68 个百分点 |

最近20个月，小盘新组合累计25.38%，盈利＋动量30.23%，单独动量39.08%；新组合月末跌幅−15.72%，单独动量−13.42%。不仅收益落后，跌幅也更深。较早大盘历史新组合最大月末跌幅约−48.56%，最长60个月未恢复，也不能说已经能平稳穿越牛熊。

相对盈利＋动量，考虑相邻月份影响后的月均差额范围如下。全部覆盖零，因此不能仅凭主期年化较高宣布新增条件已稳定有效。

| 时期 | 规模 | 相对盈利＋动量月均差额 | 考虑相邻月份影响后的描述范围 |
| --- | --- | --- | --- |
| 较早618个月 | 大盘 | +0.013 个百分点 | [-0.052, +0.079] |
| 较早618个月 | 小盘 | +0.091 个百分点 | [-0.019, +0.200] |
| 主要120个月 | 大盘 | +0.113 个百分点 | [-0.027, +0.254] |
| 主要120个月 | 小盘 | +0.110 个百分点 | [-0.074, +0.293] |
| 最近已看20个月 | 大盘 | +0.141 个百分点 | [-0.166, +0.447] |
| 最近已看20个月 | 小盘 | -0.196 个百分点 | [-0.399, +0.007] |

## 5. 相关性、风险投入和资金核对

| 时期 | 规模 | 两部分收益相关程度 | 同时下跌月份 |
| --- | --- | --- | --- |
| 较早历史 | 大盘 | 0.769 | 179/618 |
| 较早历史 | 小盘 | 0.876 | 185/618 |
| 2015—2024 | 大盘 | 0.826 | 37/120 |
| 2015—2024 | 小盘 | 0.892 | 39/120 |
| 最近已看20个月 | 大盘 | 0.356 | 4/20 |
| 最近已看20个月 | 小盘 | 0.517 | 4/20 |

主期相关性0.826/0.892仍较高。相对全部16格参考的超出或落后部分，其相关为大盘0.236、小盘−0.192，确有不同起伏；但这种共同参考并非风险完全相同的母指数，不能据此认定独立优势。最近20个月相关降低，跨度很短，且小盘组合反而落后。

大盘主期盈利低扩张单项100美元变491.56，动量变335.90，各半合计413.73美元；盈利＋动量对照360.91美元。小盘单项分别349.27、306.80美元，各半328.04美元，对照287.80美元。新组合金额逐月等于两部分金额之和，完整窗口最大数值误差低于百万分之一单位；没有资金凭空增加。

每个时期只在开始分配一半，此后比例漂移：主期盈利低扩张占比最终大盘59.41%、小盘53.24%。初始半现金对手最终股票占比大盘83.10%、小盘77.74%，较早长历史更接近100%，所以它不代表持续半仓或严格相同风险投入。

公开组合总收益中，分红等沿用来源口径；已卖出损益、现存逐股持仓、成交费用、资金容量和单股贡献均缺少账户级资料，未评价。未解释的部分不能直接称额外独立盈利能力。

## 6. 母指数、费用和能支持的范围

| 必答问题 | 本轮答案与影响 |
| --- | --- |
| 相对母指数的净优势 | 未评价。A股固定抽样和动态财务子池无合格统一母指数；美股来源自定义分组不等于标普500。不会拿别的指数顶替 |
| 相对同池/明确简单对照 | A股列P、动量、两旧法混合、低波动；美股列同32格构造的盈利对照及16格参考，均明确未扣费 |
| 实际个人成本与滑点 | 未评价。缺实际换手、订单、金额和成交；没有凭空扣固定费率冒充净收益 |
| 完整进出/未成交/停牌/退市 | A股保留缺价和停牌权重，未重建完整退出；美股只有来源分组收益，缺本地逐股交易验证 |
| 股票范围选择偏差与修订 | A股固定2014抽样和年度行业代理限制；美股当前CIZ重建与历史原始可见版本限制保留 |
| 是否新增前向策略 | 没有。研究结果及规则候选不等于合格完整策略版本 |
| 是否改LEI技术判定或真实交易 | 没有。属于独立股票组合研究；不把财务指标加进生产技术信号硬过滤 |

这些限制使本轮能够回答“具体组合比哪些旧方法多了什么、少了什么”，还不能回答“个人账户采用后能净赚多少”。没有把未检验项解释成无效，也没有用工程通过代替投资价值。

## 7. 本轮取舍与恢复条件

- **A股保留三项共同评分这一条线索，暂停在已见历史继续调比例。** 相对动量有帮助，相对简单混合增量小、风险未全面改善；费用和完整退出可能吞掉差距。
- **美股保留低扩张条件相对单盈利的有限线索，暂停把各半加动量作为通用分散方案。** 不同规模/时期的反例已经足以拒绝“稳定低相关、必然更好”的说法。
- 最能改变下一决定的证据是：在原负责人的历史合格股票池和退出资料到位后，按本轮冻结对照核真实费用后的增量。当前不重复接管股票池采集，也不先改比例找漂亮结果。

## 8. 复核、复现与文件位置

本地复现记录均在`docs/experiments/raw/existing-factor-strategy-expansion-2026-10-24/`：运行合同`contract.json`；结果前设计`design.json`；逐输入指纹`inputs.json`；冻结代码指纹`freeze.json`。产品报告入口见末尾链接。

执行入口为本报告raw目录的`run.py`，A股`cn_compare.py`，美股`us_compare.py`。正式输入是既有纠正价格、既有财务权重与官方原始CSV；未从归档脚本导入因子实现。现有技术因子自动工作流不适用于本次公开分组/保存报价比较，未声称通过新的正式特征接入。

外盘准确结果目录：`/Volumes/win+mac通用/LeiSignal-新实验结果/existing-factor-strategy-expansion-20261024/existing-factor-strategy-expansion-20261024-20261024T134246-c82447b6601e/result`。包含原始分组复算路径、A股逐股目标/月度情景/机会差额、运行日志与收据；本地`result-locator.json`保存定位和指纹。两份桌面权威源SHA保持：技术体系`df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20`，实现`85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903`。

规范采用`current-standards.json`定位的研究使命1.2.0、问题方法1.3.1、增量1.1.0、原则1.2、执行1.1.0、定义1.2.0、报告模板1.2.1，准确路径/指纹见合同。对象：`reference.french.joint.op_inv@1.0.0`、`reference.french.longonly.mom@1.0.0`；A股`research.cross_section.gross_profit_assets@1.0.0`和`research.cross_section.operating_cash_assets@1.0.0`绑定旧财务设计附件，不冒称已进中央登记。

工程核验：10项合成测试通过；一次固定市场数据批次完成，无新增行情下载或参数搜索。独立复算未调用上述两个比较实现：A股逐股目标误差不超过1.01×10⁻¹⁶、收益/未知权重误差低于3×10⁻¹⁵；美股三期间关键收益、年化、回撤最大差低于10⁻⁹个百分点。机会差额264行和0/−100%情景恒等式也已核验。原始动量来源1196个月，两来源交集758个月；输入初审曾将交集月数误写为动量原段月数，已在`verification.json`明确纠正，结果不受影响。

主控Astra方法复核与Sol执行/独立核数分工记录在`methods-review.md`、`verification.json`；绘图缺字体的首次中间输出保留，最终图用已核字体和月末日期，未改变收益结果。数值可接受、历史价值有限、生产未授权分别成立。

## 9. ARCHIVE

2026-10-24结案：两个有边界的问题已回答，保留有限线索、停止对这批历史调权重，没有新增后台试验或前向账户。报告在实验库按“组合与仓位 / 有条件或证据不足”登记，INDEX补一条。源码未自动提交推送；仅同步本人协调任务元数据。其他AI的股票池、工作台、反转研究及生产路径保持原负责人。

系统待升级既有`K-baseline`只读核到版本12/in_progress；仓外目标数据库未写，未把本轮历史研究算成目标完成。新增成果说明留本地`upgrade-note.md`，沿用该条目的原授权边界。

## 10. 最小决策卡

| 必答项 | 本轮答案 |
| --- | --- |
| 决策与用途 | 是否保留现有因子的新搭配以开发完整低频策略 |
| 基准与增量 | 中国对强单项、简单混合和同池；美国同源盈利＋动量及强单项；主结果如上 |
| 收益来源 | 中国大部分是相近持仓的再取舍；美国是盈利/增长与价格路径组合；无独立盈利能力结论 |
| 代价与执行 | 有错过上涨和更深跌幅；实际费用、退出和母指数净优势待合格资料 |
| 证据与结论 | 已见历史；A股一条小幅线索、美股条件性线索；不认定穿越牛熊或稳定有效 |
| 下一证据与边界 | 原负责人补足历史资格与退出后，按已冻结规则核费用后增量；不在当前历史上调参，不自动进入前向或交易 |

相关报告：[统一组合流程](/library?report=docs%2Fexperiments%2Ffactor-combination-workflow-2026-10-24.md)、[盈利与资产增长原比较](/library?report=docs%2Fexperiments%2Fprofitability-investment-combinations-2026-10-24.md)、[价格修正与财务旧结果](/library?report=docs%2Fexperiments%2Fderived-price-integration-2026-10-20.md)。
