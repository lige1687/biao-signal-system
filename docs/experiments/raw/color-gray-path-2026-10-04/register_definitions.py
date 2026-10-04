from pathlib import Path
import json,copy,hashlib
root=Path(__file__).resolve().parents[4];p=root/'docs/research/definitions.v1.json';j=json.loads(p.read_text());base=next(o for o in j['objects'] if o['id']=='research.trend.bull_gray_origin20')
items=[('research.trend.green_share20','20日严格绿色占比','sum(color20[j]==green,j=t-19..t)/20；严格原判色，两条件同时大于；20个连续合格日，否则未知','proportion 0..1',[]),('research.trend.color_switch_frequency20','20日颜色变动比例','sum(color20[j]!=color20[j-1],j=t-18..t)/19；20日19相邻对，灰参与，缺失断开','proportion 0..1',[]),('research.trend.signed_ema20_distance','到EMA20的有符号距离','100*(C[t]/EMA20[t]-1)，沿用旧trend_slope_change_information.ema20_distance计算；本卡是既有基准字段明确命名，非新信息来源','percentage_point',[]),('research.transform.same_day_average_rank','同日平均并列排名比例','当天相同合格池升序平均名次r，(r-1)/(n-1)；n<2未知，同值rank.5无区分；颜色类别不排序','proportion 0..1',[]),('research.trend.color_continuous20_bundle','颜色连续表达的固定组合','B为当前20/60颜色、ret20/ret60/vol20、多头组、旧EMA20上行占比及ETF身份；X为绿色占比20、19对变色频率、带符号EMA20距离。排名是单独描述变换不额外放入模型','mixed fixed feature vector',['research.trend.green_share20@1.0.0','research.trend.color_switch_frequency20@1.0.0','research.trend.signed_ema20_distance@1.0.0','research.trend.ema_direction_persistence20@1.0.0'])]
for oid,name,formula,unit,deps in items:
 assert not any(x['id']==oid for x in j['objects'])
 o=copy.deepcopy(base);o.update(id=oid,name=name,type='feature',scope='四国内宽基ETF的已见日线连续表达与同日选优研究',local_alias=oid.split('.')[-1],dependencies=deps,origin='原颜色/价格的研究表达，用户批准研究，不添加策略动作')
 o['definition'].update(formula=formula,unit=unit,direction='按原值从低到高描述；不预设越高越好，不依评价成绩翻转',transforms='模型使用原始连续值；同日名次单列研究；旧EMA上行占比作控制，不能把绿色比例当同一对象',nan_policy='颜色比例需20连续合格颜色日；252预热后另积满20色，缺失重置；unknown非gray',endpoints='t完整收盘可知，目标t+1..t+21close')
 o['lifecycle']['basis']=['src/lei_signal/research/color_continuous_information.py','src/lei_signal/research/color_continuous_workflow.py'];o['universe'].update(version='color-continuous-four-etf-20261004',eligibility='连续20合格颜色日；共同输入交集；不按未来结果选样',warmup='252连续日后20个合格颜色日',missing='缺报重置，不填色，排名并列不按代码拆分');o['validation'].update(method='合成缺口/并列/前缀，实际样本资格，固定线性与浅树共同样本',tests=['tests/unit/test_color_continuous_information.py'],limitations='四ETF横向分辨率低；同日/重叠结果依赖，历史已见；独立未知期与净收益未测量')
 o['sources']=['docs/experiments/raw/color-gray-path-2026-10-04/ranking-plan-source.md','src/lei_signal/research/color_continuous_information.py','src/lei_signal/research/color_continuous_workflow.py']+base['sources'][-3:]
 j['objects'].append(o)
for o in j['objects']:
 if o['id'] in [x[0] for x in items]+['research.trend.bull_gray_origin20']:
  for s in o['sources']:j['sources'][s]={'path':s,'sha256':hashlib.sha256((root/s).read_bytes()).hexdigest()}
p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
