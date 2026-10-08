from pathlib import Path
import sys,json
from dataclasses import asdict
B=Path(__file__).resolve().parent
sys.path.insert(0,str(B/'v1-source'))
from test_order_planning import *
d=decision(free=200,held=(350,100),prices=(2,1),sellable=(100,100),c=FLOOR)
p=plan_p1(d,frozen_at=FREEZE,opening_at=OPEN,actions=['2026-01-06T08:00:00+08:00'])
o=p.orders[0]
high=SaleResult(o.order_id,'filled',100,'1.8',OPEN,PAY,'high')
low=SaleResult(o.order_id,'filled',100,'.5',OPEN,PAY,'low')
a=later_buys(d,p,high,frozen_at=NEXTFREEZE,opening_at=NEXT)
b=later_buys(d,p,low,frozen_at=NEXTFREEZE,opening_at=NEXT)
assert a.orders[0].quantity==300 and cost(300,1,FLOOR)-D('174.82')==D('130.48')
assert a.orders[0].order_id==b.orders[0].order_id and a.orders[0].quantity!=b.orders[0].quantity
assert a.status=='ready'
x={'command':'python3 -B '+str(B/'prove_v1_defects.py'),'exit_code':0,'old_defects_reproduced':3,'old_actual_current_cash':'174.82','wrong_buy_cost':'305.3','overspend':'130.48','high':asdict(a),'low':asdict(b),'initial_known_action':'2026-01-06T08:00:00+08:00','later_forgotten_action_wrongly_ready':True}
(B/'v1-defect-reproductions.json').write_text(json.dumps(x,default=str,indent=2)+'\n');print('3 v1 defects reproduced')
