"""Optional FactorMiner procedure suggestion; research evidence is not certified.

This entry reads a frozen native skill pack and proposes one of four typed edits.
It does not evaluate formulas, call a model, or change project research history.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

UPSTREAM_COMMIT = '75e056067a90ed6c4cf2e1737df773eed79abce8'
RAW = Path('docs/experiments/raw/factorminer-experience-actions-2026-10-04')


def _json(path):
    return json.loads(Path(path).read_text())


def _engine(upstream, provenance):
    root=Path(upstream).resolve()
    spec=_json(provenance)
    if spec['upstream_commit'] != UPSTREAM_COMMIT:
        raise ValueError('This component is checked only at the frozen upstream commit')
    for item in spec['files']:
        relative=Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe provenance path')
        path=(root/relative).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Upstream source differs from checked original')
    if 'factorminer' in sys.modules:
        loaded=Path(sys.modules['factorminer'].__file__).resolve()
        if not loaded.is_relative_to(root):
            raise ValueError('Another FactorMiner source is already loaded')
    sys.path.insert(0,str(root))
    from factorminer.architecture import research_skills, skill_memory, memory_policy, paper_protocol
    return research_skills,skill_memory,memory_policy,paper_protocol


def recommend(payload, *, upstream, provenance, skill_pack=None):
    """Propose a native edit from measured scoped records; no financial adoption."""
    if set(payload)!={'schema','context','sequence','seed','dataset_id'} or payload['schema']!='experience-choice/1':
        raise ValueError('Expected experience-choice/1 with exact context, sequence, seed')
    for key in ['sequence','seed']:
        if isinstance(payload[key],bool) or not isinstance(payload[key],int) or payload[key]<0:
            raise ValueError('sequence and seed must be nonnegative integers')
    if not isinstance(payload['dataset_id'],str) or not payload['dataset_id']:
        raise ValueError('Current dataset identity required to exclude self-transfer')
    ctx=payload['context']
    required={'scope','persistence','scale','quality_band','parent_formula','parent_quality','lag1','scale_cv','recipe_version','quality_scope','ic_threshold'}
    if not isinstance(ctx,dict) or set(ctx)!=required:
        raise ValueError('Exact native applicability context required; do not invent missing history')
    if not isinstance(ctx['scope'],str) or not ctx['scope']:
        raise ValueError('scope must name the exact target and timing convention')
    for key in ['parent_quality','ic_threshold','lag1','scale_cv']:
        value=ctx[key]
        if value is None and key in ['lag1','scale_cv']:continue
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value):
            raise ValueError('Context numbers must be finite')
    if ctx['quality_scope']!='full' or ctx['parent_quality']<0 or ctx['ic_threshold']<0:
        raise ValueError('Native full discovery IC required; project RMSE cannot be substituted')
    rs,sm,mp,pp=_engine(upstream,provenance)
    if ctx['recipe_version']!=rs.RECIPE_VERSION:
        raise ValueError('Recipe version differs from the checked component')
    variants=rs.recipe_variants(ctx['parent_formula'],rs.EDIT_RECIPES)
    if len(variants)!=4:
        raise ValueError('Parent formula must compile in the native typed DSL')
    from types import SimpleNamespace
    protocol=pp.PaperProtocol.from_config(SimpleNamespace())
    policy=sm.TransferableSkillMemoryPolicy(mp.NoMemoryPolicy(protocol),rs.ResearchSkillsConfig(mode='structured'),protocol)
    policy.dataset_id=payload['dataset_id']
    if skill_pack:
        pack=rs.load_skill_pack(skill_pack)
        # Public native loader checks bytes and lineage, not market-data eligibility.
        for row in pack['observations']:
            if row['context_key']!=rs.context_key(row['context']):
                raise ValueError('Memory context fingerprint is inconsistent')
            if row['status']=='measured' and (isinstance(row['reward'],bool) or not isinstance(row['reward'],(int,float)) or not math.isfinite(row['reward'])):
                raise ValueError('Measured reward must be finite')
        policy.pack=pack
    choice,guidance=policy.select_research_variant(variants,context=ctx,sequence=payload['sequence'],seed=payload['seed'])
    return {'schema':'experience-choice-result/1','status':'research_unqualified','upstream_commit':UPSTREAM_COMMIT,'selected':choice,'guidance':guidance,'limitations':['These are native discovery-IC procedure suggestions, not project financial validation','Distinct dataset IDs do not prove independent market samples','Four fixed edits; no new LLM hypothesis or formula mining','Sequence and seed must be frozen before selection; no rerolling for a preferred edit']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--upstream',type=Path,required=True)
    p.add_argument('--provenance',type=Path,required=True);p.add_argument('--skill-pack',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Output exists; evidence may not be overwritten')
    result=recommend(_json(a.input),upstream=a.upstream,provenance=a.provenance,skill_pack=a.skill_pack)
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'recommendation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':result['status'],'selected_recipe':result['selected']['recipe_id']}))

if __name__=='__main__':main()
