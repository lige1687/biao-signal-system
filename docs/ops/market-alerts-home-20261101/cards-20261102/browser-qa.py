import json, subprocess, time
from pathlib import Path
ROOT=Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
OUT=ROOT/'docs/ops/market-alerts-home-20261101/cards-20261102'
TAB='FE5A77D5A868975E08870503611B3DDC'
results={}
def call(*args):
    r=subprocess.run(['bb-browser',*args,'--tab',TAB,'--json'],cwd=ROOT,text=True,capture_output=True,check=True)
    data=json.loads(r.stdout)
    return data.get('result',data)
def ev(js):
    data=call('eval',js)
    return data.get('result',data)
def pause(): time.sleep(.25)
def close():
    if ev('Boolean(document.querySelector("dialog[open]"))'):
        ev('document.querySelector("dialog").dispatchEvent(new Event("cancel",{cancelable:true}))');pause()
def open_card(id):
    close()
    ev(f'(()=>{{const b=document.querySelector("[data-observation-id={id}] .hoc-detail");b.focus();return true}})()')
    ev('document.activeElement.click()');pause()
def snapshot():
    return ev('(()=>({open:document.querySelector("dialog")?.matches(":modal"),title:document.querySelector("dialog h2")?.innerText,text:document.querySelector("dialog")?.innerText,chart:document.querySelector("dialog .op-chart")?.getAttribute("aria-label"),svg:document.querySelectorAll("dialog .op-chart svg").length,overflow:document.querySelector("dialog")?.scrollWidth>document.querySelector("dialog")?.clientWidth}))()')
original=ev('({pins:localStorage.getItem("ws.marketPins.v1"),seen:localStorage.getItem("lei.marketObservationSeen.v1")})')
(OUT/'browser-storage-before.json').write_text(json.dumps(original,ensure_ascii=False,indent=2))
try:
    for id in ['vix','hy-oas','cn-financing','turnover-concentration']:
        open_card(id);results[id]=snapshot()
        assert results[id]['open'] and not results[id]['overflow'],results[id]
        if id!='cn-financing': assert results[id]['svg']==1,results[id]
        else: assert '融资买入额' in results[id]['text'] and '尚未接通' in results[id]['text']
        call('press','Tab')
        assert ev('document.querySelector("dialog").contains(document.activeElement)')
        close()
        assert ev(f'document.activeElement?.closest("[data-observation-id]")?.dataset.observationId === "{id}"')
    ev('document.querySelector(".ol-trigger").click()');pause()
    ev('Array.from(document.querySelectorAll(".ol-pin")).find(b=>b.getAttribute("aria-label")==="放到首页：AAII个人投资者调查").click()');pause()
    results['pin_after_add']=ev('localStorage.getItem("ws.marketPins.v1")')
    assert 'aaii' in json.loads(results['pin_after_add'])
    call('reload');time.sleep(1)
    assert ev('Boolean(document.querySelector("[data-observation-id=aaii]"))')
    open_card('aaii');results['aaii']=snapshot();close()
    ev('document.querySelector(".ol-trigger").click()');pause()
    all_ids=ev('([...document.querySelectorAll(".ol-item")].filter(n=>!n.querySelector(".ol-pin").disabled).map(n=>n.querySelector(".ol-row-main").getAttribute("aria-controls").replace("ol-detail-","")))')
    ev(f'(()=>{{localStorage.setItem("ws.marketPins.v1",JSON.stringify({json.dumps(all_ids)}));window.dispatchEvent(new StorageEvent("storage",{{key:"ws.marketPins.v1"}}));return true;}})()')
    time.sleep(2)
    results['all_cards']=ev('([...document.querySelectorAll(".hoc-card")].map(n=>({id:n.dataset.observationId,text:n.innerText,error:!!n.querySelector("[role=alert]"),svg:n.querySelectorAll("svg").length})))')
    assert len(results['all_cards'])==20
    assert not any(r['error'] for r in results['all_cards']),results['all_cards']
    assert ev('document.documentElement.scrollWidth<=innerWidth')
    baker=next(r for r in results['all_cards'] if r['id']=='baker-wurgler')
    assert '2025-12' in baker['text'] and '较早资料' in baker['text'] and '百分点' not in baker['text']
    open_card('baker-wurgler');results['baker-wurgler']=snapshot();close()
    # Remove via the real control, then confirm selection survives a reload.
    ev('document.querySelector("[data-observation-id=baker-wurgler] .hoc-remove").click()');pause()
    assert 'baker-wurgler' not in json.loads(ev('localStorage.getItem("ws.marketPins.v1")'))
    # Explicitly empty is a supported user preference, not an invitation to reset defaults.
    ev('(()=>{localStorage.setItem("ws.marketPins.v1","[]");location.reload();return true})()');time.sleep(1)
    results['empty_preserved']=ev('({cards:document.querySelectorAll(".hoc-card").length,pins:localStorage.getItem("ws.marketPins.v1"),library:!!document.querySelector(".ol-trigger")})')
    assert results['empty_preserved']=={'cards':0,'pins':'[]','library':True}
    results['keyboard']='Native modal state, cancel-event handler and focus returned for four defaults verified. CLI Enter/Escape key dispatch lacks virtual key codes; physical keyboard interaction not exercised (native Mac locked).'
finally:
    close()
    ev(f'(()=>{{const before={json.dumps(original)};for(const [k,v] of [["ws.marketPins.v1",before.pins],["lei.marketObservationSeen.v1",before.seen]]){{if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v)}}window.dispatchEvent(new StorageEvent("storage",{{key:"ws.marketPins.v1"}}));return true}})()')
    pause()
    results['restored']=ev('({pins:localStorage.getItem("ws.marketPins.v1"),seen:localStorage.getItem("lei.marketObservationSeen.v1")})')
    assert results['restored']==original
    (OUT/'browser-qa.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps({'status':'passed','default_dialogs':4,'all_cards':len(results.get('all_cards',[])),'storage_restored':results['restored']},ensure_ascii=False))
