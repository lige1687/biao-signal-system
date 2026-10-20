"""Independent closed-form hold check plus price provenance and unchanged-share days."""
import hashlib
import json
from pathlib import Path
import pandas as pd

P=Path(__file__).resolve().parent
S=P.parent/'research-broad-etf-plan-2026-09-08/legacy-baseline/inputs'
mapping={'沪深300':'portfolio_split/sh000300_close.parquet','上证50':'portfolio_split/sh000016_close.parquet',
         '中证白酒':'portfolio_split/sz399997_close.parquet','国证地产':'portfolio_split/sz399393_close.parquet',
         '创业板指':'siphon_detector/cyb_399006_close.parquet','证券公司':'siphon_detector/sec_399975_close.parquet',
         '新能车':'portfolio_split/sz399976_close.parquet','中证医疗':'portfolio_split/sz399989_close.parquet',
         '国证有色':'portfolio_split/sz399395_close.parquet'}
prices=pd.DataFrame({name:pd.read_parquet(S/file)['close'] for name,file in mapping.items()})
prices=prices.loc['2015-06-16':'2026-08-18'].dropna()
d=pd.read_csv(P/'legacy-reconcile/daily.csv',parse_dates=['date'])
trades=pd.read_csv(P/'legacy-reconcile/trades.csv',parse_dates=['date'])
hold=(prices/prices.iloc[0]).mean(axis=1)/1.001
reported=d[d.account=='A_true_buy_once_hold'].groupby('date').equity.first()
hold_error=float((hold-reported).abs().max())
assert hold_error<1e-12
price_error=0.; unchanged_count=0; unchanged_error=0.
for (acct,name),g in d.groupby(['account','asset']):
    g=g.set_index('date').sort_index()
    price_error=max(price_error,float((g.price-prices[name]).abs().max()))
    tx=trades[(trades.account==acct)&(trades.asset==name)]
    delta=g.shares.diff().iloc[1:]
    no_trade=delta.loc[~delta.index.isin(tx.date)]
    unchanged_count+=len(no_trade)
    unchanged_error=max(unchanged_error,float(no_trade.abs().max()))
assert price_error<1e-8 and unchanged_error<1e-12
x={'scope':'Independent closed-form true hold for all days; original-price matching and no-trade share invariance in all three ledgers. Not a separate full rebalance decision engine.',
   'rows':len(prices),'true_hold_equity_max_error':hold_error,'true_hold_end':float(hold.iloc[-1]),
   'source_price_max_error':price_error,'nontrade_asset_days':unchanged_count,'nontrade_share_change_max':unchanged_error,
   'source_hashes':{str(S/f):hashlib.sha256((S/f).read_bytes()).hexdigest() for f in mapping.values()},
   'reviewed_output_hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [P/'legacy-reconcile/daily.csv',P/'legacy-reconcile/trades.csv']},
   'passed':True}
(P/'root-legacy-check.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in x.items() if 'hash' not in k},ensure_ascii=False))
