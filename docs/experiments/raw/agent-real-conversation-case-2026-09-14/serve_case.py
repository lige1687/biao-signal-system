"""Isolated business DB, actual development routes/model, existing local ETF bars."""
import sys,tempfile,json,hashlib,os
from pathlib import Path
DEV=Path('/Users/yongbiaoli/lei-agent-ux-20260913');sys.path.insert(0,str(DEV/'src'))
from lei_signal.env import load_env
for key in list(os.environ):
 if key.startswith(('ARK_','GLM_','DEEPSEEK_','ANTHROPIC_')):os.environ.pop(key)
load_env(path='/Users/yongbiaoli/Desktop/lei-signal-lab/.env')
import pandas as pd
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from lei_signal.api.routes import agent,plans,opportunities,symbols,copilot
from lei_signal.api.services import AnalysisService
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.data.providers import PriceData
from lei_signal.data.symbols import resolve_symbol
from lei_signal.data.validation import validate_bars
from lei_signal.plans.llm import load_ark_config
OUT=Path(__file__).parent;TEMP=tempfile.TemporaryDirectory(prefix='lei-case-');db=str(Path(TEMP.name)/'case.db')
from lei_signal.storage.sqlite_store import connect
connect(db).close()
P=Path('/Users/yongbiaoli/.lei_signal_lab/cache/510300.SS.bars.parquet');bars=pd.read_parquet(P)
def local_analyze(symbol,**kwargs):
 if symbol not in ('510300','510300.SS'):raise ValueError('Case limited to 510300')
 info=resolve_symbol(symbol);frame,report=validate_bars(bars.copy(),symbol=info.symbol,provider='existing_local_cache',adjusted=True)
 return analyze_bars(info.symbol,frame,price_data=PriceData(symbol=info.symbol,display_name='沪深300ETF',bars=frame,report=report,info=info))
service=AnalysisService(analyze_fn=local_analyze,sqlite_path=db,cache_root=str(Path(TEMP.name)/'cache'),ttl_seconds=3600)
e=service.get('510300.SS');assert e.result is not None,e.error
app=FastAPI();app.state.analysis_service=service
for k in ['plans_db_path','watchlist_db_path','portfolio_db_path']:setattr(app.state,k,db)
app.state.quote_provider=None;app.state.friendly_name_provider=False
for r in [agent.router,plans.router,opportunities.router,symbols.router,copilot.router]:app.include_router(r)
@app.get('/api/health')
def health():return {'status':'ok','case':'isolated'}
app.mount('/assets',StaticFiles(directory=DEV/'web/dist/assets'),name='assets')
@app.get('/{path:path}')
def index(path:str):return FileResponse(DEV/'web/dist/index.html')
c=load_ark_config();assert c,'No model configured'
(OUT/'case-environment.json').write_text(json.dumps({'development':str(DEV),'temporary_db':db,'model':c.model,'bars':str(P),'bars_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'rows':len(bars),'last_bar':str(bars.index.max()),'api':'http://127.0.0.1:8016','local_bars_only':True,'real_model':True},ensure_ascii=False,indent=2))
uvicorn.run(app,host='127.0.0.1',port=8016,log_level='warning')
