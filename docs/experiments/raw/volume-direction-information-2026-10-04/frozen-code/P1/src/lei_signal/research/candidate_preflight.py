"""Research-only structural readiness and partition reuse. No outcome data accepted."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import itertools
import json

IDENTITY_FIELDS = {'data','contract','target','baseline','horizon','evaluator','thresholds','features'}
ROW_FIELDS = {'id','question','symbol','date','stratum','x','eligible','features','selected_nonoverlap'}
CANDIDATE_FIELDS = {'candidate_id','question','context'}

def _encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)

def _hash(value):
    return hashlib.sha256(_encoded(value).encode()).hexdigest()

def _typed_member(value,menu):
    return any(type(value) is type(v) and value==v for v in menu)

def _classify(context,features):
    outcomes=[None if features[t['field']] is None else features[t['field']]==t['value']
              for t in context['terms']]
    if context['logic']=='and':
        return False if False in outcomes else None if None in outcomes else True
    return True if True in outcomes else None if None in outcomes else False

def _swap(value):
    return None if value is None else not value

class PreflightRegistry:
    """One frozen evaluation identity. Attempts retained; result caching is caller-owned.

    ``eligible`` is an externally certified endpoint availability flag, never a
    historical trading filter. Rows intentionally reject all result-value fields.
    """
    def __init__(self,identity,menus,minimum_each,rows):
        if not isinstance(identity,dict) or set(identity)!=IDENTITY_FIELDS or any(v in ('',None) for v in identity.values()):
            raise ValueError('Bind all eight evaluation identity dimensions')
        self.identity=deepcopy(identity);self.menus=deepcopy(menus);self.minimum=deepcopy(minimum_each)
        if set(menus)!=set(minimum_each):raise ValueError('Menu/threshold questions differ')
        for question,fields in menus.items():
            if not fields or any(not isinstance(values,list) or not values or
                                 any(type(v) not in [bool,str] for v in values) or
                                 len({_encoded([type(v).__name__,v]) for v in values})!=len(values)
                                 for values in fields.values()):raise ValueError('Closed scalar feature menu required')
            if type(minimum_each[question]) is not int or minimum_each[question]<1:raise ValueError('Positive raw count threshold required')
        self.rows=deepcopy(rows);seen=set()
        for row in self.rows:
            if not isinstance(row,dict) or not {'id','question','symbol','stratum','x','eligible','features'}<=set(row) or set(row)-ROW_FIELDS:
                raise ValueError('Only explicit structural row fields accepted')
            if row['question'] not in menus:raise ValueError('Unknown question')
            for key in ['id','question','symbol','stratum']:
                if not isinstance(row[key],str) or not row[key]:raise ValueError('Structural IDs/strata must be strings')
            if 'date' in row and (not isinstance(row['date'],str) or not row['date']):
                raise ValueError('Optional date must be a nonempty string')
            key=(row['question'],row['id'])
            if key in seen:raise ValueError('Duplicate structural row ID')
            seen.add(key)
            if type(row['x']) is not bool and row['x'] is not None:raise ValueError('X must be bool or unknown')
            if type(row['eligible']) is not bool:raise ValueError('Eligible must be bool')
            if 'selected_nonoverlap' in row and type(row['selected_nonoverlap']) is not bool and row['selected_nonoverlap'] is not None:
                raise ValueError('Selected flag must be bool or unknown')
            fields=menus[row['question']]
            if not isinstance(row['features'],dict) or set(row['features'])!=set(fields):raise ValueError('Only closed menu features accepted')
            for field,value in row['features'].items():
                if value is not None and not _typed_member(value,fields[field]):raise ValueError('Feature outside typed menu')
        # Actual structural rows, menus and thresholds bound in addition to caller identity.
        self.cache_identity=_hash({'identity':identity,'menus':menus,'minimum_each':minimum_each,'rows':self.rows})
        self._attempts=[]

    def inspect(self,candidate):
        if not isinstance(candidate,dict) or set(candidate)!=CANDIDATE_FIELDS:raise ValueError('Candidate must contain identity/question/context only')
        question=candidate['question'];context=candidate['context']
        if question not in self.menus or not isinstance(candidate['candidate_id'],str) or not candidate['candidate_id']:raise ValueError('Invalid candidate identity')
        if any(old['candidate_id']==candidate['candidate_id'] for old in self._attempts):
            raise ValueError('Candidate ID must be unique; revisions need a new ID')
        if not isinstance(context,dict) or set(context)!={'logic','terms'} or context['logic'] not in ['and','or'] or not isinstance(context['terms'],list) or not 1<=len(context['terms'])<=2:
            raise ValueError('Expected one/two closed menu AND/OR terms')
        fields=self.menus[question]
        names=[]
        for term in context['terms']:
            if not isinstance(term,dict) or set(term)!={'field','value'} or term['field'] not in fields or not _typed_member(term['value'],fields[term['field']]):raise ValueError('Invalid typed menu term')
            names.append(term['field'])
        if len(set(names))!=len(names):raise ValueError('One term per field')
        # Include unknown in every field's exhaustive domain; equality of observed
        # partitions alone is never promoted to globally equivalent conditions.
        ordered=sorted(fields)
        signature=tuple(_classify(context,dict(zip(ordered,values)))
                        for values in itertools.product(*(fields[k]+[None] for k in ordered)))
        sample=[r for r in self.rows if r['question']==question]
        parts={k:[] for k in ['context','complement','unknown']}
        for row in sample:
            classification=_classify(context,row['features'])
            parts['unknown' if classification is None else 'context' if classification else 'complement'].append(row)
        partition_ids={k:[r['id'] for r in values] for k,values in parts.items()}
        sets={k:frozenset(v) for k,v in partition_ids.items()}
        reuse=None
        for old in self._attempts:
            if old['question']!=question:continue
            if all(sets[k]==old['_sets'][k] for k in sets):orientation=1
            elif sets['unknown']==old['_sets']['unknown'] and sets['context']==old['_sets']['complement'] and sets['complement']==old['_sets']['context']:orientation=-1
            else:continue
            if orientation==1 and signature==old['_signature']:relation='exact'
            elif orientation==-1 and signature==tuple(_swap(v) for v in old['_signature']):relation='global_complement'
            else:relation='dataset_equivalent' if orientation==1 else 'dataset_complement'
            reuse={'source_candidate_id':old['candidate_id'],'relation':relation,'orientation':orientation}
            break
        counts={};layers={};eligible_layers={}
        for name,values in parts.items():
            counts[name]={'all':len(values),'eligible':sum(r['eligible'] for r in values)}
            layers[name]=[]
            for key in sorted({(r['symbol'],r['stratum']) for r in values}):
                group=[r for r in values if (r['symbol'],r['stratum'])==key]
                tc=sum(r['eligible'] and r['x'] is True for r in group)
                fc=sum(r['eligible'] and r['x'] is False for r in group)
                layers[name].append({'key':list(key),'all':len(group),'eligible':sum(r['eligible'] for r in group),
                                     'x_true':tc,'x_false':fc,'x_unknown':sum(r['eligible'] and r['x'] is None for r in group),
                                     'comparable':min(tc,fc)>=self.minimum[question]})
            eligible_layers[name]=[g['key'] for g in layers[name] if g['comparable']]
        common=sorted(set(map(tuple,eligible_layers['context'])) & set(map(tuple,eligible_layers['complement'])))
        result={'candidate_id':candidate['candidate_id'],'question':question,'cache_identity':self.cache_identity,
                'truth_signature':_hash(signature),'partition_ids':partition_ids,'counts':counts,'layers':layers,
                'eligible_layers':eligible_layers,'common_layers':[list(k) for k in common],
                'readiness':'background_comparison' if common else 'description_only','reuse':reuse,
                'meaning':'Structural availability only; insufficient comparison is not factor invalidity'}
        self._attempts.append({**result,'_signature':signature,'_sets':sets})
        return deepcopy(result)

def remap_result(source,candidate,orientation):
    """Reuse newly computed evaluator result; swap full sides and common delta only.

    X-true minus X-false within a side stays unchanged. Candidate's scientific
    expectation/lineage is always retained separately from mathematical reuse.
    """
    if type(orientation) is not int or orientation not in [1,-1]:raise ValueError('Orientation must be +1/-1')
    result=deepcopy(source)
    if orientation==-1:
        result['context'],result['complement']=result['complement'],result['context']
        for key in ['partition_counts','partition_ids']:
            result[key]['context'],result[key]['complement']=result[key]['complement'],result[key]['context']
        value=result['common_strata_interaction']['delta_difference_pp']
        result['common_strata_interaction']['delta_difference_pp']=None if value is None else -value
    result['candidate']=deepcopy(candidate)
    context=candidate['context']
    result['semantic_key']=json.dumps([candidate['question'],context['logic'],
          sorted((t['field'],str(t['value'])) for t in context['terms'])],ensure_ascii=False)
    return result
