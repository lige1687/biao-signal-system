"""Small synthetic source fixtures; these tests do not certify market history."""
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import pytest
from lei_signal.research.provider_index_input import qualify_provider_index_panel


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(tmp_path):
    dates=['2020-12-18','2020-12-21','2026-06-30']
    rows=[{'date':d,'open':100.,'close':101.,'high':102.,'low':99.} for d in dates]
    sources=[];bars=[]
    for asset,name,code in [('sh000300','沪深300','000300'),('sz399006','创业板指','399006')]:
        csvpath=tmp_path/asset/'bars.csv';csvpath.parent.mkdir()
        with csvpath.open('w') as f:
            w=csv.DictWriter(f,fieldnames=['date','open','close','high','low']);w.writeheader();w.writerows(rows)
        response={'code':0,'data':{asset:{'day':[[r['date'],str(r['open']),str(r['close']),str(r['high']),str(r['low'])] for r in rows], 'qt':{asset:['1',name,code]}}}}
        response_hash=write(tmp_path/asset/'response.json',response)
        request_hash=write(tmp_path/asset/'request.json',{'symbol':asset,'returned_branch':'day'})
        sources.append(dict(asset=asset,name=name,code=code,bars_path=f'{asset}/bars.csv',bars_sha256=hashlib.sha256(csvpath.read_bytes()).hexdigest(),response_path=f'{asset}/response.json',response_sha256=response_hash,request_path=f'{asset}/request.json',request_sha256=request_hash))
        bars.extend(dict(asset=asset,status='quoted',provider_price_known=True,price_series='provider_index_price',action_known=False,open_actionable=False,**r) for r in rows)
    cal={'authority':'exchange_official','publisher':'深圳证券交易所（SZSE）','days':{d:{'is_trading_day':True} for d in dates}}
    calhash=write(tmp_path/'calendar.json',cal)
    manifest={'schema_version':'provider-index-input/1.0','sources':sources,'calendar_path':'calendar.json','calendar_sha256':calhash,'start':dates[0],'end':dates[-1]}
    write(tmp_path/'source-input.json',manifest)
    payload={'calendar':dates,'bars':bars}
    contract={'data':{'qualification':{'adapter':'tencent_index_price/1.0','manifest_path':'source-input.json','calendar_path':'calendar.json'}}, 'universe':{'assets':[s['asset'] for s in sources]}, 'target':{'entry_field':'close','price_measure':'provider_index_price','kind':'forward_return'},'question':{'layer':'factor_information','validation':{'stage':'exploration'}},'publication':{'conclusion':'insufficient'}}
    return payload,contract,manifest


def test_matched_sources_and_semantic_limits(tmp_path):
    p,c,_=fixture(tmp_path);r=qualify_provider_index_panel(p,c,tmp_path)
    assert r['quality']['request_satisfied'] and r['quality']['rows']==6
    assert r['semantics']['price_series_bound']
    assert r['semantics']['opening_actionability']=='unsupported'
    assert r['semantics']['official_index_methodology']=='not_certified'


@pytest.mark.parametrize('change', ['price','hidden','duplicate','status','action','open','flag','calendar'])
def test_bad_panel_vs_original_good(tmp_path,change):
    p,c,_=fixture(tmp_path);bad=deepcopy(p)
    if change=='price':bad['bars'][0]['close']=100.5
    if change=='hidden':bad['bars'][0]['low']=None
    if change=='duplicate':bad['bars'].append(deepcopy(bad['bars'][0]))
    if change=='status':bad['bars'][0]['status']='halt'
    if change=='action':bad['bars'][0]['action_known']=True
    if change=='open':bad['bars'][0]['open_actionable']=True
    if change=='flag':bad['bars'][0]['provider_price_known']=False
    if change=='calendar':bad['calendar'].pop()
    with pytest.raises(ValueError):qualify_provider_index_panel(bad,c,tmp_path)
    assert qualify_provider_index_panel(p,c,tmp_path)['quality']['request_satisfied']


@pytest.mark.parametrize('change', ['identity','branch','hash','pool','path','date','csv','response_code'])
def test_bad_source_binding(tmp_path,change):
    p,c,m=fixture(tmp_path)
    s=m['sources'][0]
    if change in ['identity','branch','response_code']:
        path=tmp_path/s['response_path'];r=json.loads(path.read_text())
        if change=='identity':r['data'][s['asset']]['qt'][s['asset']][1]='错误对象'
        if change=='branch':r['data'][s['asset']]['qfqday']=r['data'][s['asset']].pop('day')
        if change=='response_code':r['code']=1
        s['response_sha256']=write(path,r)
    if change=='hash':s['request_sha256']='0'*64
    if change=='pool':m['sources'].pop()
    if change=='path':s['bars_path']='../outside.csv'
    if change=='date':m['start']='2021-01-01'
    if change=='csv':
        path=tmp_path/s['bars_path'];path.write_text(path.read_text().replace('101.0','101.1'))
        s['bars_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    write(tmp_path/'source-input.json',m)
    with pytest.raises(ValueError):qualify_provider_index_panel(p,c,tmp_path)


@pytest.mark.parametrize('section,field,value', [('target','entry_field','open'),('target','price_measure','total_return'),('question','layer','decision_policy'),('publication','conclusion','supported')])
def test_stronger_claim_rejected(tmp_path,section,field,value):
    p,c,_=fixture(tmp_path);c[section][field]=value
    with pytest.raises(ValueError):qualify_provider_index_panel(p,c,tmp_path)


def test_not_exploration_rejected(tmp_path):
    p,c,_=fixture(tmp_path);c['question']['validation']['stage']='unseen'
    with pytest.raises(ValueError):qualify_provider_index_panel(p,c,tmp_path)


@pytest.mark.parametrize('value',[0,-1,float('nan'),float('inf')])
def test_illegal_panel_prices_and_matched_good_pair(tmp_path,value):
    p,c,_=fixture(tmp_path);bad=deepcopy(p);bad['bars'][0]['close']=value
    with pytest.raises(ValueError,match='positive finite'):
        qualify_provider_index_panel(bad,c,tmp_path)
    assert qualify_provider_index_panel(p,c,tmp_path)['quality']['request_satisfied']


def test_calendar_source_hash_and_identity_are_actual_not_verified_flag(tmp_path):
    p,c,m=fixture(tmp_path)
    calpath=tmp_path/'calendar.json';cal=json.loads(calpath.read_text())
    cal['publisher']='不明来源';m['calendar_sha256']=write(calpath,cal)
    m['verified']=True
    write(tmp_path/'source-input.json',m)
    with pytest.raises(ValueError,match='SZSE'):
        qualify_provider_index_panel(p,c,tmp_path)


def test_schema_adapter_and_absolute_path_rejected(tmp_path):
    p,c,m=fixture(tmp_path)
    c['data']['qualification']['adapter']='other/1.0'
    with pytest.raises(ValueError,match='adapter'):
        qualify_provider_index_panel(p,c,tmp_path)
    c['data']['qualification']['adapter']='tencent_index_price/1.0'
    m['sources'][0]['bars_path']=str(tmp_path/'sh000300'/'bars.csv')
    write(tmp_path/'source-input.json',m)
    with pytest.raises(ValueError,match='relative'):
        qualify_provider_index_panel(p,c,tmp_path)
