"""Freeze a bounded new 60-day state question; never inspect outcome values."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
R = Path(__file__).resolve().parent
REF = 'research.trend.green_black60_state@1.0.0'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def put(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')

def main():
    from lei_signal.research.green_black_state_information import build_qualification, BASELINE_FEATURES
    base = json.loads((ROOT/'docs/experiments/raw/technical-daily-risk-2026-10-03/slope/freeze-01/contract.json').read_text())
    brief = {
        'question': '60日双均线方向的绿/黑/灰，在20日状态及已知价格变化之后，是否改善随后60个交易间隔的收益与收盘下探判断？',
        'mode':'research', 'delivery_mode':'final_only',
        'decision_use':'验证趋势状态的有限信息用途，不制定买卖、结束趋势或仓位规则',
        'primary_targets':['forward_return60','close_mae60'],
        'auxiliary_horizons':[5,10,20,60,120],
        'auxiliary_metrics':['mean_return','up_probability','return_over_5_probability','mae','mfe','peak_to_trough','mae_over_5_10_15_probabilities'],
        'groups':['all','color60 green/black/gray','color20 x color60','single SMA60 direction x EMA60 confirmation','first observed color60 transition','fixed nonoverlap stride121 from first scheduled date'],
        'robustness':['year','ETF','leave-one-ETF-out saved predictions','synchronous date blocks60/120 draws1000 seed20261003'],
        'budget':{'core_batches':1,'followup_batches_max':3,'real_OLS_fits_max':8,'market_requests':0,'paid_requests':0,'execution_seconds':7200},
        'old_evidence':'20日八轮旧研究复用；本轮20状态只是60问题的固定背景，不重跑旧20优化；所有2022-2026H1已见历史不冒充全新验证',
        'source_semantics':'体系§2.2月/季/半年20/60/120；§2.7绿色向上黑色向下灰色不明确、20主60辅；日线短期与周线中长期是频率维度，不等同20日/60日。60严格颜色为原判据的研究尺度代理，非生产新增规则。',
        'definition':'green iff C>EMA_N and C>C[t-N]; black iff both strict below; equality/disagreement gray; missing unknown. EMA uses first N closes SMA seed; no future;252 contiguous warmup.',
        'limits':['固定4ETF有限历史','历史供应商到达未认证','公司行动记录完整性未证实','数据再分发许可未确认不上传行情','分类不硬套排名分位','完整LEI条件未包括','资金/线上收益未测量'],
        'coordination_scope_commit':'13bc7cbd24bda4d40b47a3262bc742fe0dcde200',
        'base_commit':'2126a758ad539d97818e2aa4399385110af00f5b',
        'strategy_sha256':{'体系':'df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20','实现':'85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903'},
    }
    put(R/'brief.json', brief)
    registry_path=ROOT/'docs/research/definitions.v1.json'
    registry=json.loads(registry_path.read_text())
    if any(c['id']==REF.split('@')[0] for c in registry['objects']):
        raise SystemExit('definition already exists: refuse overwrite')
    card=deepcopy(next(c for c in registry['objects'] if c['id']=='research.risk.slope_change60_20'))
    card.update(id=REF.split('@')[0],name='60日SMA/EMA严格同向的绿黑灰趋势状态',type='state_signal',dependencies=[],
                component_definition_refs=[],local_alias='G60-green-black',spec_anchor=['桌面技术体系§2.2、§2.7','技术实现§4.2'],
                scope='四只国内宽基ETF已见日线的60周期方向状态信息',origin='20日严格方向判据扩到原文60辅助组的固定研究代理，不增删策略原文、不替完整LEI或生产颜色')
    card['definition']={'formula':'G_N(t): C_t>EMA_N(t) AND C_t>C_(t-N); B_N(t): both strict below; gray: ready but neither; unknown: missing or <252 contiguous bars',
                        'parameters':{'N':60,'baseline_N':20,'warmup':252,'primary_horizon':60},'unit':'categorical green/black/gray/unknown',
                        'direction':'原文表示道路方向；未来收益/风险价值由本轮检验','transforms':'EMA_N用前N收盘均值播种，alpha=2/(N+1)，经济OHLC沿现有来源资格',
                        'nan_policy':'缺价或行动未知分段重置；unknown不填gray','endpoints':'只用t及以前；正式目标t+1..t+61收盘共61点60间隔，辅助期限如brief'}
    card['validation']['tests']=['tests/unit/test_green_black_state_information.py']
    card['validation']['limitations']='色彩是既有价格的确定表达；不含排列/时钟/回调/结构/周线/交易动作；非独立新原始信息；已见资料'
    card['status'].update(definition_clarity='fixed_research_scale_proxy',implementation='synthetic_tests_required',effectiveness='not_evaluated')
    paths=['docs/experiments/raw/green-black-state-information-2026-10-03/brief.json','src/lei_signal/research/green_black_state_information.py','tests/unit/test_green_black_state_information.py',
           'docs/experiments/raw/volume-information-2026-09-30/execution/source-manifest.json',
           'docs/research/strategy-source-snapshots/2026-09-30/LEI 技术交易体系.md','docs/research/strategy-source-snapshots/2026-09-30/LEI 技术实现.md']
    card['sources']=paths
    card['lifecycle']={'state':'research_ready','basis':paths[:3],'verification_scope':'源码与合成测试、无目标值来源/样本资格；效果由冻结合同'}
    registry['objects'].append(card)
    for p in paths: registry['sources'][p]={'path':p,'sha256':sha(ROOT/p)}
    put(registry_path,registry)
    payload=json.loads((ROOT/base['data']['path']).read_text())
    for name,kind in [('return','forward_return'),('risk','mae')]:
        c=deepcopy(base)
        for k in ['bindings','freeze','rehearsal','calendar']:c.pop(k,None)
        ident='green-black-state60-'+name+'-2026-10-03'
        q=c['question'];q.update(question_id=ident,hypothesis_family=ident,factor_refs=[REF],
            target={'kind':kind,'horizon':60,'start_offset':1,'end_offset':61,'price_basis':'close_to_close' if kind=='forward_return' else 'close_to_close_path'},
            baseline='B0训练成熟平均；B1为20日绿黑分类、近20/60涨跌、波动及ETF身份；另保留每ETF训练均值',
            added_information='60日绿色与黑色两个分类指示；灰色为共同参考，未知保留',
            decision_use=brief['decision_use'],joint_structure='同日四ETF、长颜色段与重叠60日结果；未知不能当灰',
            auxiliary_metrics=brief['auxiliary_metrics']+brief['robustness'],
            trial_history=brief['old_evidence'],method={'name':'prediction_ols','reason':'固定少量字段同日期比较；分类onehot没有强行黑<灰<绿顺序；零调参且并列简单均值'},
            added_information_reason='60日方向可能与20日不同，但近期涨跌已有，检验仅是确定表达的模型帮助')
        c['feature']={'kind':'green_black_state60_information','lookback':60,'bar_frequency':'daily_quote','missing_policy':'segmented','warmup':252,'definition_ref':REF}
        c['target']={'kind':kind,'start_offset':1,'end_offset':61,'entry_field':'close','unit':'percentage_point','price_measure':'economic_price'}
        if kind=='mae':c['target']['path_field']='close'
        c['evaluator'].update(baseline_features=list(BASELINE_FEATURES),added_features=['color60_green','color60_black'],minimum_training_rows=22)
        c['dependence'].update(block_length=60)
        c['history']={'family':ident,'changed_after_results_reason':'60状态为用户明确的新尺度信息用途；20旧研究不重跑，历史全已见。'}
        c['sources']=[s for s in c['sources'] if not any(x in s['path'] for x in ('semantic-mining','technical-daily-risk','trend_slope_change','test_trend_slope'))]
        c['sources'] += [{'path':p,'sha256':sha(ROOT/p)} for p in paths if p not in {s['path'] for s in c['sources']}]
        c['publication'].update(report_path='docs/experiments/green-black-'+name+'-artifact-2026-10-03.md',conclusion='insufficient')
        qual=build_qualification(payload,c,ROOT)
        qp=R/name/'qualification.json';put(qp,qual)
        qp_rel=str(qp.relative_to(ROOT))
        count=qual['counts']
        c['research_design']={'claim_mapping':{'original_statement':'黑绿工具以20组为主60组辅助，绿色向上黑色向下灰色不明确','source_section':'体系§2.2/§2.7及实现§4.2',
            'proxy_definition':json.dumps(card['definition'],ensure_ascii=False),'preserved_conditions':['同周期双方向','严格比较','灰色及未知保留','t收盘可知'],
            'omitted_conditions':['均线排列','时钟及结构','周线/小时','完整持仓/退出与账户动作'], 'decision_use':q['decision_use'],
            'observation_time':'完整t收盘后','intended_action_time':'无交易，目标起于下一收盘','application_scope':'trend_road_information',
            'tested_scope':'四ETF60日状态的后续60日有限历史信息','unresolved_uses':brief['limits']},
            'sample_fit':{'qualification_artifact':qp_rel,'qualification_sha256':sha(qp),'outcome_values_used_for_design':False,
            'unit':'ETF×安排交易日，非独立事件',**count,'paired_support':json.dumps(qual['scientific_support'],ensure_ascii=False),
            'dependence':'同日资产及持续状态、60日路径高度相关','model_feature_count':10,
            'rationale':'资格仅看来源、过去状态、日历及列秩；每色各期支持见原表。两个固定分类列检验对既有价格的表达价值，均值防止弱背景误导', 'decision':'estimate'}}
        for key in c['controller_review']:
            reasons={'universe_fit':'四固定国内ETF身份与经济OHLC可逐行核；历史到达和行动完整性有限，不扩大范围',
                     'proxy_fidelity':'60严格方向是20原判据的同周期研究尺度代理，保留灰未知；不含全系统判断，不改原文',
                     'method_fit':'分类指标而非连续排序；固定背景和两候选列，训练只用先成熟资料，简单平均并列，样本秩和支持已审',
                     'conclusion_scope':'较晚年份全已见，只能有限历史证据；预测和分组不等于资金增量，不接管转黑重置趋势研究'}
            c['controller_review'][key]={'reason':reasons[key],'source_refs':[qp_rel,paths[0]]}
        put(R/name/'draft.json',c)
        print(name,count,'support',qual['scientific_support'].get('folds'))

if __name__=='__main__':main()
