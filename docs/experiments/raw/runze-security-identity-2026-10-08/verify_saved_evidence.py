"""Read only official saved source and selected original helper AST; never import the data producer."""
import ast,hashlib,json,re
from pathlib import Path
import pandas as pd
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    f=json.loads((BASE/'qualified-facts.json').read_text()); src=json.loads((BASE/'source-manifest.json').read_text())['sources'][0];checks=[]
    def check(k,v):checks.append({'check':k,'passed':bool(v)})
    check('source_original_hash',sha(ROOT/src['raw_path'])==src['raw_sha256'])
    check('text_hash',sha(ROOT/src['text_path'])==src['text_sha256'])
    text=re.sub(r'\s+','',(ROOT/src['text_path']).read_text())
    for name,term in [('printed_announcement_number','公告编号：2025-028'),('effective_open_date','公司股票自2025年2月17日开市起启用变更后的证券简称及证券代码'),('entity_continues','公司法人主体存续'),('holder_class_and_quantity','投资者持有股份的证券类别和持有数量与代码变更完成前一致'),('tax_holding_period_continues','持股期限自其取得“300114”股份时开始计算'),('mapping_terms','原证券代码“300114”变更为“302132”')]:check(name,term in text)
    q=ROOT/f['input_preparer']['path']; before=sha(q);check('original_preparer_hash',before==f['input_preparer']['sha256'])
    tree=ast.parse(q.read_text()); selected=[]
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CODE_RENAMES' for t in node.targets):selected.append(node)
        if isinstance(node,ast.FunctionDef) and node.name in {'canonical_member','dated_member'}:selected.append(node)
    assert len(selected)==3
    ns={'pd':pd};exec(compile(ast.Module(body=selected,type_ignores=[]),str(q),'exec'),ns)
    check('mapping_only_expected_pair',ns['CODE_RENAMES']=={'302132':('300114',pd.Timestamp('2025-02-17'))})
    check('prechange_code',ns['dated_member']('300114',pd.Timestamp('2025-02-14'))=='300114')
    check('effective_day_code',ns['dated_member']('300114',pd.Timestamp('2025-02-17'))=='302132')
    check('afterchange_code',ns['dated_member']('300114',pd.Timestamp('2025-02-18'))=='302132')
    check('canonical_identity_same',ns['canonical_member']('300114')==ns['canonical_member']('302132')=='300114')
    check('unrelated_code_unchanged',ns['dated_member']('600837',pd.Timestamp('2025-02-17'))=='600837')
    check('preparer_not_modified',sha(q)==before)
    result={'checks':checks,'count':len(checks),'passed':all(x['passed'] for x in checks),'script_sha256':sha(Path(__file__)),'only_selected_ast_executed':['CODE_RENAMES','canonical_member','dated_member'],'entire_pipeline_executed':False,'independent_agent_review':False,'price_repairs':0}
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
