"""Run one fixed native-component probe; all measured outcomes are artificial."""
import argparse, copy, hashlib, json, os, sys, time
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--local-ledgers',type=Path,required=True);a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);a.local_ledgers.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(a.upstream.resolve()))
    from factorminer.architecture.research_actions import ResearchAction, ResearchActionPlanner, ResearchPlannerConfig, ResearchActionLedger
    from factorminer.architecture.research_skills import ResearchSkillsConfig, compile_skill_pack, write_skill_pack, load_skill_pack, recipe_formula, recipe_variants, EDIT_RECIPES, RECIPE_VERSION, observation_from_action, digest
    from factorminer.architecture.skill_memory import TransferableSkillMemoryPolicy
    from factorminer.architecture.memory_policy import NoMemoryPolicy
    from factorminer.architecture.paper_protocol import PaperProtocol
    import numpy as np, scipy
    start=time.monotonic(); checks=[];results={};inputs={}
    def check(name,condition):
        assert condition,name
        checks.append(name)
    cfg=ResearchPlannerConfig(exploration_probability=0,seed=7)
    offers=[ResearchAction('generate',1),ResearchAction('stop',0)]
    context={'bucket':'fixed-artificial-target'}
    failures=[{'sequence':i+1,'status':'completed','decision':{'chosen':{'kind':'generate','evaluations':1},'context':context},'outcome':{'candidates':[],'library_gain':0}} for i in range(100)]
    inputs['action']={'config':asdict(cfg),'offers':[asdict(x) for x in offers],'records':failures,'context':context,'iteration':0,'quality_threshold':.04}
    planner=ResearchActionPlanner(cfg)
    for name,records,ctx in [('no_history',[],context),('failed_history',failures,context),('foreign_context',failures,{'bucket':'other-target'})]:
        results[name]=planner.plan(offers=offers,records=records,context=ctx,iteration=0,quality_threshold=.04)
    check('empty baseline generates',results['no_history']['chosen']['kind']=='generate')
    check('100 failed proposals cause stop',results['failed_history']['chosen']['kind']=='stop')
    check('foreign bucket failures do not transfer',results['foreign_context']['chosen']['kind']=='generate')
    expected=(1/104)*.02-.0015
    check('independent expected value',abs(results['failed_history']['estimates'][0]['net_value']-expected)<1e-14)
    results['direct_rule']={'input':'same estimated gain and costs','expected_generate_net_value':expected,'chosen':'stop' if expected<=0 else 'generate','reason':'explicit arithmetic baseline; no LLM quality claim'}
    ctx={'scope':'fixed-artificial-target','persistence':'moderate','scale':'stable','quality_band':'high','parent_formula':'$close','parent_quality':.2,'lag1':.3,'scale_cv':.2,'recipe_version':RECIPE_VERSION,'quality_scope':'full','ic_threshold':.04}
    sourcepaths=[];all_records=[]
    for i in range(4):
        path=a.local_ledgers/f'source_{i}';ledger=ResearchActionLedger(path,{'dataset_id':f'artificial-{i}'})
        for seq,(recipe,reward) in enumerate([('smooth_3',.15),('smooth_8',-.1)],1):
            formula=recipe_formula(recipe,'$close');decision={'sequence':seq,'context':context,'chosen':{'kind':'refine','evaluations':1,'parent_formula':'$close','formula':formula,'parent_quality':.2,'recipe_id':recipe},'skill_context':ctx,'selection_probability':.25}
            outcome={'candidates':[{'formula':formula,'parse_ok':True,'quality_scope':'full','quality':.2+reward,'admitted':reward>0}],'evaluations':1}
            ledger.begin(decision);ledger.finish(seq,outcome);all_records.append({'dataset_id':f'artificial-{i}','decision':decision,'outcome':outcome})
        sourcepaths.append(path)
    inputs['procedure_records']=all_records
    pack=compile_skill_pack(sourcepaths);write_skill_pack(pack,a.output/'skill-pack.json')
    loaded=load_skill_pack(a.output/'skill-pack.json');check('native pack construction and readback',pack==loaded)
    proto=PaperProtocol.from_config(SimpleNamespace())
    config=ResearchSkillsConfig(mode='structured');policy=TransferableSkillMemoryPolicy(NoMemoryPolicy(proto),config,proto)
    variants=recipe_variants('$close',EDIT_RECIPES);inputs['variant']={'context':ctx,'variants':variants,'config':asdict(config),'sequence':2,'seed':7}
    def select(name,rows,context=ctx,local=None):
        policy.pack={**pack,'observations':copy.deepcopy(rows)};policy.dataset_id='artificial-new';policy.local=local or {};frozen=copy.deepcopy(policy.pack)
        chosen,guidance=policy.select_research_variant(variants,context=context,sequence=2,seed=7)
        results[name]=guidance;check(name+' frozen memory unchanged',policy.pack==frozen)
        return guidance
    base=select('without_memory',[])
    positive=select('with_scoped_memory',pack['observations'])
    check('without memory uniform',all(abs(v['probability']-.25)<1e-12 for v in base['variants']))
    check('source positive effect increases selected probability',positive['variants'][0]['probability']>.9)
    check('negative procedure reduced',positive['variants'][1]['probability']<.03)
    foreign=select('different_target',pack['observations'],{**ctx,'scope':'foreign-target'})
    unknown=select('unknown_dynamics',pack['observations'],{**ctx,'persistence':'unknown'})
    for name,g in [('foreign',foreign),('unknown',unknown)]:check(name+' no transfer',all(abs(v['probability']-.25)<1e-12 for v in g['variants']))
    one=[copy.deepcopy(r) for r in pack['observations'] if r['dataset_id']=='artificial-0']*50
    single=select('100_rows_one_dataset',one)
    check('one dataset not treated as 100 independent sources',all(abs(v['probability']-.25)<1e-12 for v in single['variants']))
    local=copy.deepcopy(next(r for r in pack['observations'] if r['recipe_id']=='smooth_3'));local.update(event_id='artificial-local-negative',dataset_id='artificial-new',reward=-.4)
    contradictory=select('local_contradiction',pack['observations'],local={local['event_id']:local})
    evidence=contradictory['variants'][0]['evidence']
    check('local contradiction halves source influence',evidence['source_influence']==.5)
    check('contradiction reduces preference',contradictory['variants'][0]['probability']<positive['variants'][0]['probability'])
    legacy={'sequence':1,'status':'completed','decision':{'chosen':{'kind':'refine'}},'outcome':{}}
    check('legacy without applicability not fabricated',observation_from_action(legacy,dataset_id='legacy',campaign_id='legacy') is None)
    bad=copy.deepcopy(pack);bad['observations'][0]['reward']+=1;(a.output/'corrupt-copy.json').write_text(json.dumps(bad))
    try:load_skill_pack(a.output/'corrupt-copy.json')
    except ValueError:checks.append('modified pack rejected')
    else:raise AssertionError('modified pack accepted')
    for name,payload in [('inputs.json',inputs),('results.json',results),('checks.json',{'checks':checks,'count':len(checks),'elapsed_seconds':time.monotonic()-start,'versions':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__},'model_calls':0,'financial_fits':0,'candidate_quality':'unmeasured','financial_increment':'unmeasured'})]:
        (a.output/name).write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    modules=[]
    for name,m in sorted(sys.modules.items()):
        p=Path(getattr(m,'__file__','') or '.')
        if name.startswith('factorminer') and p.is_file():modules.append({'module':name,'path':str(p.resolve().relative_to(a.upstream.resolve())),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    (a.output/'loaded-upstream.json').write_text(json.dumps(modules,indent=2)+'\n')
    print(json.dumps({'checks':len(checks),'status':'passed','native_modules':len(modules),'model_calls':0}))

if __name__=='__main__':main()
