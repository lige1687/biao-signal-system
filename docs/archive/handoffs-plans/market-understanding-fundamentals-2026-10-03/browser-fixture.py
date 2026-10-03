"""Synthetic-only local UI check. No provider, database, credentials or external calls.
Run from repo: python3 docs/archive/handoffs-plans/market-understanding-fundamentals-2026-10-03/browser-fixture.py --root . --port 8774
Open /market-understanding?fixture=normal|empty|missing|wrong|failure|inconsistent|slow. GET /__finish ends own server.
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
import argparse, json, mimetypes, threading, time
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--port',type=int,default=8774);args=ap.parse_args()
root=(args.root/'web/dist').resolve(); scenario='normal'
def row(metric,market,label,value,unit,**kw):
 d=dict(metric_id=metric,label=label,market=market,universe='人工验证对象，无真实行情',value=value,unit=unit,change=0,comparison_period='前20个有效观测日',observation_date='2026-09-29',published_at=None,publication_precision='unknown',fetched_at=None,source_name='人工测试来源',source_url=None,quality_status='time_unverified',quality_reason='人工资料仅检查界面',reading='人工资料：只用于界面检查，不用于投资判断。',limitations=['人工测试，不是真实市场数据'],definition_version='synthetic-ui/1')
 d.update(kw);return d
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def send(self,code,payload,kind='application/json'):
  body=json.dumps(payload,ensure_ascii=False).encode() if kind=='application/json' else payload
  self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
 def do_GET(self):
  global scenario
  q=urlparse(self.path)
  if q.path=='/__finish': self.send(200,{'finished':True});threading.Thread(target=self.server.shutdown,daemon=True).start();return
  if q.path=='/api/fundamentals/observations':
   market=parse_qs(q.query).get('market',['cn'])[0]
   if scenario=='slow': time.sleep(3)
   if scenario=='failure': self.send(503,{'detail':'synthetic failure'});return
   if scenario=='missing': self.send(404,{'detail':'endpoint absent'});return
   items=[row('margin_balance','cn','融资余额（人工）',0,'亿元'),row('margin_buy','cn','融资买入额（人工）',None,'亿元',quality_status='missing'),row('stock_turnover','cn','股票成交额（人工）',100,'亿元',quality_status='current')] if market=='cn' else [row('vix','us','VIX（人工）',20,'指数点',quality_status='current',published_at='2026-09-30',publication_precision='date'),row('naaim','us','NAAIM（人工）',70,'%',quality_status='stale',observation_date='2026-05-11'),row('aaii','us','AAII（人工）',-2,'百分点',quality_status='delayed',observation_date='2026-09-24')]
   if scenario=='inconsistent' and market=='cn':
    items[0].update(value=None,quality_status='current');items[1].update(value=10,quality_status='current',change_unit='%')
   self.send(200,dict(market=('us' if market=='cn' else 'cn') if scenario=='wrong' else market,generated_at='2026-10-03T09:00:00+08:00',items=[] if scenario=='empty' else items,errors=['synthetic-source-error'] if market=='us' else []));return
  if q.path.startswith('/api/'):
   self.send(503,{'detail':'unrelated API intentionally disabled for synthetic UI check'});return
  if q.path in ['/','/market-understanding','/fundamentals']:
   scenario=parse_qs(q.query).get('fixture',['normal'])[0]
   raw=(root/'index.html').read_text().replace('<body>','<body><div style="padding:8px;background:#7a4500;color:white;text-align:center;font:14px sans-serif">人工资料验收页面 · 不是真实行情 · 场景 '+scenario+'</div>')
   self.send(200,raw.encode(),'text/html');return
  p=(root/unquote(q.path.lstrip('/'))).resolve()
  if p.is_relative_to(root) and p.is_file(): self.send(200,p.read_bytes(),mimetypes.guess_type(str(p))[0] or 'application/octet-stream')
  else: self.send(404,{'detail':'fixture only'})
server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
print(f'synthetic UI only http://127.0.0.1:{args.port}',flush=True)
server.serve_forever();server.server_close();print('fixture server stopped',flush=True)
