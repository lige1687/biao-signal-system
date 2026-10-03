"""Prepare two fixed risk-use drafts without future outcome values or fitting."""
from pathlib import Path
import copy, json, hashlib, datetime
import numpy as np
from lei_signal.research.trend_slope_change_information import prepare_slope_observations
from lei_signal.research.ema_only_wait_age_information import prepare_sequence_observations
from lei_signal.research.top_structure_information import qualify_top_panel, _known
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent

def write(p,x):
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    for tag,prepare in [('slope',prepare_slope_observations),('age',prepare_sequence_observations)]:
        base=json.loads((OUT/tag/'original-draft.json').read_text());payload=json.loads((ROOT/base['data']['path']).read_text())
        assert sha(ROOT/base['data']['path'])==base['data']['sha256']
        quality=qualify_top_panel(payload,base,ROOT)
        prepared=prepare(payload,base,compute_labels=False);rows=prepared['observations']
        assert all(r['y'] is None for r in rows)
        cal=payload['calendar'];index={d:i for i,d in enumerate(cal)};bykey={(b['asset'],b['date']):b for b in payload['bars']}
        for row in rows:
            i=index[row['date']];end=i+21
            row['risk_path_available']=end<len(cal) and all(_known(bykey.get((row['asset'],d),{})) for d in cal[i+1:end+1])
            row['risk_end']=cal[end] if end<len(cal) else None
        folds=[]
        for fold in base['split']['folds']:
            train=[r for r in rows if r['eligible'] and r['risk_path_available'] and r['date']<=fold['train_end'] and r['risk_end']<fold['eval_start']]
            ev=[r for r in rows if r['eligible'] and r['risk_path_available'] and fold['eval_start']<=r['date']<=fold['eval_end'] and r['risk_end']<=fold['eval_end']]
            ranks={}
            for name,cols in [('B1',base['evaluator']['baseline_features']),('B2',base['evaluator']['baseline_features']+['added'])]:
                a=np.array([[r['features'][k] for k in cols] for r in train]);a=np.column_stack([np.ones(len(a)),a]);ranks[name]={'rank':int(np.linalg.matrix_rank(a)),'columns_with_intercept':a.shape[1]}
            folds.append({'fold':fold,'train':len(train),'evaluation':len(ev),'train_dates':len({r['date'] for r in train}),'evaluation_dates':len({r['date'] for r in ev}),'rank':ranks,'per_asset':{a:{'train':sum(r['asset']==a for r in train),'evaluation':sum(r['asset']==a for r in ev)} for a in base['universe']['assets']}})
        q={'data_sha256':base['data']['sha256'],'outcome_values_used_for_design':False,'counts':{'assets':4,'observations':len(rows),'dates':len({r['date'] for r in rows}),'episodes':None},'coverage':prepared['coverage'],'scientific_support':{'folds':folds,'feature_ready':sum(r['eligible'] for r in rows),'model_feature_count':11,'feature_and_path_available':sum(r['eligible'] and r['risk_path_available'] for r in rows),'risk_path_missing':sum(r['eligible'] and not r['risk_path_available'] for r in rows)},'source_quality':quality['quality'],'source_warnings':quality['warnings'],'note':'Risk path presence checked without computing future minima/returns; old same feature formula reused. Dates/rows are not independent events.'}
        qpath=OUT/tag/'qualification.json';write(qpath,q)
        d=copy.deepcopy(base);family='technical-daily-'+tag+'-risk-2026-10-03';ref='research.risk.'+('slope_change60_20' if tag=='slope' else 'ema_only_wait_age20')+'@1.0.0';kind='slope_change_risk_information' if tag=='slope' else 'ema_only_wait_age_risk_information'
        use=('在当前斜率、涨跌和波动已知后，斜率变化是否额外提示未来下探' if tag=='slope' else '在当前价格和D01抵扣盒距离已知后，当前等待日龄是否额外提示未来下探')
        d['question'].update(question_id=family,hypothesis_family=family,factor_refs=[ref],decision_use=use)
        d['question']['target']['kind']='mae';d['question']['target']['price_basis']='close_to_close_path'
        d['question']['trial_history']='旧S01/Q01收益各4拟合已封存；旧风险分组已见，新用途为控制既有信息后的风险预测。D01风险旧结果保留，Q风险B1包含其距离。不把已见历史/换目标变新验证，不重跑收益。'
        d['question']['auxiliary_metrics']=['period/asset/leave-one-asset-out common predictions','20/60date joint-block sensitivity','previous5/10/20/60/120 returns and risks referenced, not rerun']
        d['feature'].update(kind=kind,definition_ref=ref)
        d['target']={'kind':'mae','start_offset':1,'end_offset':21,'entry_field':'close','path_field':'close','unit':'percentage_point','price_measure':'economic_price'}
        d['evaluator']['minimum_training_rows']=22
        d['history']={'family':family,'ledger_path':'will_be_fixed_by_freeze','changed_after_results_reason':'Separate risk use fixed before new risk predictions; earlier return results and raw risk groups known and retained, no target tuning.'}
        d['dependence'].update(seed=20261003,block_length=20,draws=1000)
        d['budget']={'scientific_variants':1,'execution_seconds':7200,'max_rows':6000}
        d['publication']={'report_path':f'docs/experiments/technical-{tag}-risk-forecast-artifact-2026-10-03.md','category':'模块与信号','claimed_scope':'partial','conclusion':'insufficient'}
        d.pop('descriptive_protocol',None)
        sample=d['research_design']['sample_fit'];sample.update(qualification_artifact=str(qpath.relative_to(ROOT)),qualification_sha256=sha(qpath),outcome_values_used_for_design=False,**q['counts'],paired_support=json.dumps(folds,ensure_ascii=False),rationale='固定已有背景后只加一个既有表达；资格只核输入/成熟路径与秩，未看风险数值；保留均值以防复杂模型失效',decision='estimate')
        mapping=d['research_design']['claim_mapping'];mapping.update(decision_use=use,proxy_definition=json.dumps(json.loads((OUT/tag/'definition-card.json').read_text())['definition'],ensure_ascii=False),tested_scope='四ETF有限已见历史的mae20风险用途，不证明完整趋势/等待/退出',unresolved_uses=['完整持仓/退出资金价值','真正未见新资料','供应商当时到达与行动完整性'])
        reasons={'universe_fit':'四只固定国内宽基ETF源身份和经济价可核，但历史到达及行动完整性仍有限，不能外推全体ETF','proxy_fidelity':'两表达公式保持原样，风险用途单列；不是完整时钟、稳定上行或作者唯一标定','method_fit':'各10已知字段和一个表达，固定OLS及简单成熟均值，同资产比重、相同观察，两阶段；样本/秩见本次不含目标值资格','conclusion_scope':'只检验mae20风险信息；既有收益阴性不重做，后期仍已见，资金和交易效果未测量'}
        for k,v in reasons.items():d['controller_review'][k]={'reason':v,'source_refs':[str(qpath.relative_to(ROOT)),'docs/experiments/raw/technical-daily-risk-2026-10-03/brief.json']}
        d['sources'] += [{'path':str(qpath.relative_to(ROOT)),'sha256':sha(qpath)},{'path':'docs/experiments/raw/technical-daily-risk-2026-10-03/brief.json','sha256':sha(OUT/'brief.json')}]
        write(OUT/tag/'workflow-draft.json',d)
        print(tag,json.dumps({'scheduled':len(rows),'feature_ready':q['scientific_support']['feature_ready'],'folds':folds},ensure_ascii=False))
if __name__=='__main__':main()
