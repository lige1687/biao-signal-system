"""Qualify a single public-source example, not an investable universe or factor test."""
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from diagnose_saved_momentum import HERE, verified_existing_output

TAGS = ['RevenueFromContractWithCustomerExcludingAssessedTax', 'OperatingIncomeLoss',
        'CostOfGoodsAndServicesSold', 'Assets', 'StockholdersEquity',
        'NetCashProvidedByUsedInOperatingActivities']


def run():
    out = verified_existing_output()
    target = out / 'quality-source-qualification.json'
    assert not target.exists()
    receipts = json.loads((HERE / 'quality-source-fetch.json').read_text())['attempts']
    for item in receipts:
        if item.get('ok'):
            assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    facts = json.loads((out / 'sources/aapl-companyfacts.json').read_text())
    submissions = json.loads((out / 'sources/aapl-submissions.json').read_text())
    assert facts['cik'] == 320193 and 'Apple' in facts['entityName']
    recent = submissions['filings']['recent']
    filings = {acc: {k:v[i] for k,v in recent.items()}
               for i,acc in enumerate(recent['accessionNumber'])}

    def pick_annual(cutoff_day, trim_future=False):
        # No same-day decision is evaluated. Filing date is a date, not a clock.
        # Require both reported filing date and reported acceptance strictly earlier.
        cutoff = datetime.fromisoformat(cutoff_day+'T00:00:00+00:00')
        eligible = [f for f in filings.values() if f['form'] in ('10-K','10-K/A')
                    and f['filingDate'] < cutoff_day
                    and datetime.fromisoformat(f['acceptanceDateTime'].replace('Z','+00:00')) < cutoff]
        chosen = max(eligible, key=lambda f:(f['reportDate'],f['filingDate'],f['acceptanceDateTime']))
        values = {}
        for tag in TAGS:
            rows = facts['facts']['us-gaap'][tag]['units']['USD']
            if trim_future:
                rows = [x for x in rows if x.get('filed','9999') < cutoff_day]
            matches = [x for x in rows if x['accn'] == chosen['accessionNumber']
                       and x['end'] == chosen['reportDate'] and x['form'] == chosen['form']]
            if tag not in ('Assets','StockholdersEquity'):
                matches = [x for x in matches if x.get('start')
                           and 330 <= (date.fromisoformat(x['end'])-date.fromisoformat(x['start'])).days <= 400]
            unique = {json.dumps(x,sort_keys=True):x for x in matches}
            # Distinct filing-year/frame annotations may still encode an identical fact.
            numeric = {(x.get('start'),x['end'],x['val'],x['accn']) for x in unique.values()}
            assert len(numeric) == 1, (tag, chosen['accessionNumber'], matches)
            values[tag] = sorted(unique.values(),key=lambda x:json.dumps(x,sort_keys=True))[0]
        return {'decision_day':cutoff_day,
                'filing':{k:chosen[k] for k in ['accessionNumber','form','reportDate','filingDate',
                                               'acceptanceDateTime','primaryDocument']},
                'facts':values}

    examples = [pick_annual(d) for d in ['2023-10-31','2023-11-07','2024-06-28']]
    assert examples[0]['filing']['reportDate'] == '2022-09-24'
    assert examples[1]['filing']['reportDate'] == examples[2]['filing']['reportDate'] == '2023-09-30'
    assert pick_annual('2024-06-28') == pick_annual('2024-06-28',trim_future=True)
    chosen = examples[2]
    revenue = chosen['facts'][TAGS[0]]['val']
    profit = chosen['facts']['OperatingIncomeLoss']['val']
    assert revenue == 383285000000 and profit == 114301000000
    stats = {}
    for tag in TAGS:
        rows = facts['facts']['us-gaap'][tag]['units']['USD']
        by_period = defaultdict(set)
        for x in rows:
            by_period[(x.get('start'),x['end'])].add(x['val'])
        stats[tag] = {'rows':len(rows),'first_period_end':min(x['end'] for x in rows),
                      'last_period_end':max(x['end'] for x in rows),
                      'later_filed_rows_excluded_at_20240628':sum(x['filed'] >= '2024-06-28' for x in rows),
                      'same_period_distinct_values_count':sum(len(v)>1 for v in by_period.values()),
                      'comment':'不同值仅是需核对的多版本/上下文线索，未自动判成会计重述'}
    result = {'status':'completed_source_probe','scope':'one deliberately selected company, 6 fields, 3 date checks; not cross-sectional performance',
              'entity':facts['entityName'],'cik':facts['cik'],'source_type':'SEC extracted XBRL + filing metadata snapshot',
              'examples':examples,'field_coverage':stats,
              'illustrative_operating_margin':profit/revenue,
              'ratio_role':'same-filing arithmetic example only; not French OP, no new registered factor, no return claim',
              'future_records_do_not_change_cutoff_example':True,
              'source_qualification':{'identity':'confirmed in both official API responses',
                                     'period_and_units':'explicit start/end/USD and same accession',
                                     'filing_publication':'filingDate and acceptanceDateTime supplied by SEC; exact first public dissemination clock not independently verified',
                                     'retrieval':'recorded current acquisition, not claimed historical local receipt',
                                     'versions':'accession/date distinguish filings, full historical completeness and corrections not certified',
                                     'original_document':'SEC archive HTML returned HTTP403; underlying statement not independently read',
                                     'membership':'one-company example only; historical membership and exited entities absent',
                                     'industry':'current SEC classification cannot stand in for historical industry',
                                     'prices_and_corporate_actions':'not acquired or qualified for this example'},
              'conclusion':'Public source path is real and the date-aware example works; quality/value factor performance remains not evaluated.'}
    verified_existing_output()
    with target.open('x') as f: json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                      'source_status':result['conclusion'],'margin':result['illustrative_operating_margin'],
                      'chosen_filings':[x['filing'] for x in examples]},ensure_ascii=False))


if __name__ == '__main__':
    run()
