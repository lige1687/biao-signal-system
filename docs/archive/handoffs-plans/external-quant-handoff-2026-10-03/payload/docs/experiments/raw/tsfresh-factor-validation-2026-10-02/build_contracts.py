"""Create fixed designs from a known workflow shape, with no outcome inspection."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
BASE = ROOT / 'docs/experiments/raw/semantic-mining-2026-10-02/trend-effect/freeze-01/contract.json'
FAMILY = 'tsfresh-factor-validation-2026-10-02'
REFS = ['research.external.mean_abs_log_change20@1.0.0',
        'research.external.return_autocorrelation20_lag1@1.0.0']
FIELDS = ['mean_abs_log_change20', 'return_autocorrelation20_lag1']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def make():
    template = json.loads(BASE.read_text())
    for key in ('bindings', 'freeze', 'rehearsal', 'calendar', 'descriptive_protocol'):
        template.pop(key, None)
    template['feature'] = dict(kind='tsfresh_price_information', lookback=20,
        bar_frequency='daily_quote', missing_policy='segmented', warmup=252,
        definition_ref=REFS[0], definition_refs=REFS)
    q = template['question']
    q.update(question_id=FAMILY, hypothesis_family=FAMILY, factor_refs=REFS,
        joint_structure='同日四ETF及相邻20日表达、未来20日目标重叠；全部历史已见',
        added_information='固定20日平均绝对对数变化和相邻收益联系，无阈值筛选',
        decision_use='对未来20交易间隔涨跌，两个外部价格表达是否补充既有价格、趋势与波动背景？',
        auxiliary_metrics=['MSE','asset/year paired errors','leave_one_asset_out_no_refit',
                           'remove_20_largest_signed_daily_improvements','block60_saved_predictions'],
        dependence='同日ETF及相邻20日未来目标重叠；同步整段20日抽取，60日敏感性不重拟合',
        trial_history='四ETF全部历史已见；首次冻结本问题四组固定比较，未看本问题未来效果数值')
    q['method']['reason'] = '固定零惩罚线性预测；仅较早成熟历史训练，简单历史平均并列，无选窗口或模型'
    q['baseline'] = 'B0较早训练平均；B1固定10项价格/趋势/波动与ETF身份背景'
    q['primary_metric']['threshold_reason'] = '固定同观察预测误差比较，无事后效果门槛'
    template['budget'] = dict(scientific_variants=4, execution_seconds=7200, max_rows=6000)
    template['history'] = dict(family=FAMILY,
        ledger_path='docs/experiments/raw/research-workflow-ledgers-2026-09-29/'+hashlib.sha256(json.dumps(FAMILY,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24]+'/attempts.jsonl', changed_after_results_reason='首次冻结，未看本问题效果；四组事前登记，同一账本不重置预算')
    template['publication'] = dict(report_path='', category='模块与信号', claimed_scope='partial', conclusion='insufficient')
    template['permissions'] = dict(real_labels=True, effect_authorized=True, real_fits=4,
        paid_requests=0, production=False)
    template['stability_protocol'] = dict(primary='joint', variants=['joint','amplitude','serial','factor_only'],
        remove_dates='B1 minus B2 squared-loss improvement averaged equally across ETFs; signed descending top20 dates',
        leave_one_asset_out='aggregation of saved predictions only; no refit', block60='1000draws same seed; no refit',
        primary_uncertainty='paired sqrt(mean square loss) difference from the same date draws; MSE companion intervals also retained')
    # Keep the physical source chain, drop previous study interpretation/design files.
    template['sources'] = [s for s in template['sources'] if not any(z in s['path'] for z in
        ('semantic-mining-', 'trend_slope_change_information.py', 'test_trend_slope_change_information.py'))]
    extra = [RAW/'protocol.json', RAW/'qualification.json', RAW/'controller-pre-freeze-review.json',
        RAW/'analyze_saved.py', ROOT/'src/lei_signal/research/tsfresh_price_information.py',
        ROOT/'tests/unit/test_tsfresh_price_information.py',
        ROOT/'.agents/skills/lei-quant-tools/scripts/tsfresh_calculators.py',
        ROOT/'.agents/skills/lei-quant-tools/scripts/tsfresh-LICENSE.txt']
    bypath={s['path']:s for s in template['sources']}
    for path in extra:
        if path.exists():
            rel=str(path.relative_to(ROOT)); bypath[rel]=dict(path=rel,sha256=sha(path))
    template['sources'] = list(bypath.values())
    qual_path=RAW/'qualification.json'
    qual=json.loads(qual_path.read_text()) if qual_path.exists() else None
    reasons={
        'universe_fit':'四只国内宽基ETF的已有名义OHLC与经济价格重建来源，逐行重新核验；历史到达和全部行动完整性未知，因此只作有限回顾比较。',
        'proxy_fidelity':'两项20日固定表达按tsfresh0.21.2函数正文计算；只描述价格路径，未把外部数学表达称为LEI原作者交易定义。',
        'method_fit':'先固定两折较早训练与较晚评价，剔除未成熟训练标签，评价目标止于同一期；固定零惩罚线性预测适合本轮有限问题，并列更简单历史平均。',
        'conclusion_scope':'结论仅是四ETF既有历史的未来涨跌预测误差差额；所有日期、ETF及少数日期集中检查均用保存预测，不据结果选窗口或升级为交易策略。'}
    review_paths=[str((RAW/'protocol.json').relative_to(ROOT)),str(qual_path.relative_to(ROOT)),
                  str((RAW/'controller-pre-freeze-review.json').relative_to(ROOT))]
    template['controller_review']={k:dict(reason=v,source_refs=review_paths) for k,v in reasons.items()}
    template['research_design'] = dict(claim_mapping=dict(
        original_statement='外部时序计算表达可能补充已有价格背景，需用未来涨跌误差检查',
        source_section='tsfresh0.21.2 mean_abs_change/autocorrelation fixed functions；用户2026-10-02研究授权',
        proxy_definition='mean(abs(diff(100*ln(C[-21:])))); autocorrelation(diff(100*ln(C[-21:])),lag=1)',
        preserved_conditions=['t及以前完整经济收盘价格','252连续有效OHLC共同资格','两表达共同可计算观察'],
        omitted_conditions=['LEI完整规则执行','真实到账/到达时间证明','全部ETF总体','未见历史确认'],
        decision_use=q['decision_use'], observation_time='t日收盘后', intended_action_time='无交易，随后20间隔涨跌研究',
        application_scope='external_price_information', tested_scope='四ETF全部已见历史的固定价格表达',
        unresolved_uses=['账户收益与成交风险','独立未见历史','更大独立ETF市场总体']),
        sample_fit=dict(qualification_artifact=str(qual_path.relative_to(ROOT)),
            qualification_sha256=sha(qual_path) if qual else '0'*64, outcome_values_used_for_design=False,
            unit='ETF×安排交易日；相邻观察相关',
            assets=qual['counts']['assets'] if qual else 4,
            observations=qual['counts']['observations'] if qual else 4340,
            dates=qual['counts']['dates'] if qual else 1085, episodes=None,
            paired_support='同一B0/B1/B2且全部四比较要求两候选已知；未知观察保留',
            dependence='同日相关ETF、相邻特征与未来目标重叠', model_feature_count=12,
            rationale=reasons['method_fit'], decision='estimate'))
    configs=[('joint',template['evaluator']['baseline_features'],FIELDS),
        ('amplitude',template['evaluator']['baseline_features'],FIELDS[:1]),
        ('serial',template['evaluator']['baseline_features'],FIELDS[1:]),
        ('factor_only',template['evaluator']['baseline_features'][7:],FIELDS)]
    for ident,baseline,added in configs:
        c=copy.deepcopy(template)
        c['question']['question_id']=FAMILY+'-'+ident
        c['evaluator'].update(baseline_features=baseline,added_features=added)
        c['research_design']['sample_fit']['model_feature_count']=len(baseline)+len(added)
        c['publication']['report_path']=f'docs/experiments/tsfresh-{ident}-forecast-artifact-2026-10-02.md'
        if ident=='factor_only':
            c['question']['baseline']='B0较早训练平均；B1只有三项ETF身份；B2三项身份加两候选，供候选独立表现对照'
        path=RAW/f'draft-{ident}.json'
        path.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    return template

if __name__=='__main__':
    make()
