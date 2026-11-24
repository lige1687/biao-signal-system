"""Bounded, local-only legacy breadth lineage diagnosis: twenty fixed anchors.

Does not execute provider scripts, fetch data, modify live inputs, or tune signals.
Writes only the two sibling diagnostic artifacts named below.
"""
from __future__ import annotations

import ast
from bisect import bisect_right
from collections import Counter
from datetime import datetime
from decimal import Decimal
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess

import pandas as pd

QA = Path(__file__).resolve().parent
ROOT = QA.parents[2]
BASE = ROOT / '.codex/breadth-reading-coordination-20261101'
CACHE = Path('/Users/yongbiaoli/.lei_signal_lab/cache')
WINDOWS = (20, 50, 200)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_file(ref, path):
    return subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=ROOT, text=True)


def rates(signals):
    return {'eligible': len(signals), 'above': sum(signals.values()),
            'pct': sum(signals.values()) / len(signals) * 100 if signals else None}


def main():
    paths = {
        'live': CACHE / 'a_share_ma_breadth_history.json',
        'legacy_cache_unqualified': CACHE / 'a_share_klines.parquet',
        'tencent_qfq_cache': CACHE / 'a_share_klines_qfq.parquet',
        'qualified_westock': QA / 'qualify-cn-westock-v4.json',
        'westock_rows': BASE / 'cn-westock-candidate-v4/candidate-rows.jsonl.gz',
        'westock_manifest': BASE / 'cn-westock-candidate-v4/manifest.json',
    }
    input_shas = {k: sha(v) for k, v in paths.items()}
    live_rows = json.loads(paths['live'].read_text())
    live = {x['date']: x for x in live_rows}
    qual = json.loads(paths['qualified_westock'].read_text())
    dates = qual['live_comparison_dates']
    assert len(dates) == 20 and len(live) == len(live_rows) == 1288
    assert input_shas['westock_rows'] == qual['producer_combined_sha256']

    # Exact historical implementation, parsed as text; no module execution.
    source_path = 'src/lei_signal/market_context/a_share_breadth.py'
    old_source = git_file('HEAD', source_path)
    old_fetch = next(n for n in ast.parse(old_source).body
                     if isinstance(n, ast.FunctionDef) and n.name == 'fetch_ma_breadth')
    old_cache = {}
    legacy_signals = {d: {w: {} for w in WINDOWS} for d in dates}
    legacy_latest_dates = Counter()
    legacy_latest_day_symbols = []
    df = pd.read_parquet(paths['legacy_cache_unqualified'])
    for symbol, g in df.groupby('symbol', sort=False):
        g = g.sort_values('date')
        ds, ps = g['date'].astype(str).tolist(), g['close'].astype(float).tolist()
        assert len(ds) == len(set(ds))
        old_cache[symbol] = list(zip(ds[-2600:], ps[-2600:]))
        legacy_latest_dates[ds[-1]] += 1
        if ds[-1] == '2026-10-16':
            legacy_latest_day_symbols.append({'symbol': symbol, 'first': ds[0], 'last': ds[-1], 'rows': len(ds)})
        rolling = {w: pd.Series(ps).rolling(w).mean().tolist() for w in WINDOWS}
        for day in dates:
            p = bisect_right(ds, day)
            for w in WINDOWS:
                if p >= w:
                    legacy_signals[day][w][symbol] = ps[p - 1] > rolling[w][p - 1]
    del df
    ns = {'pd': pd, 'datetime': datetime, 'load_kline_cache': lambda: old_cache,
          '_KLINE_KEEP': 2600}
    exec(compile(ast.Module(body=[old_fetch], type_ignores=[]), '<git HEAD fetch only>', 'exec'), ns)
    # Empty requested list deliberately guarantees the old function never calls a provider;
    # its unconditional cache.values() loop still aggregates the real saved cache.
    replay = ns['fetch_ma_breadth']([], use_cache=True)
    assert replay['trading_day'] == '2026-10-16'
    replay_comparison = {f'ma{w}': {'replayed': replay[f'ma{w}_pct'],
                                  'live': live['2026-10-16'][f'ma{w}_pct'],
                                  'exact_equal': replay[f'ma{w}_pct'] == live['2026-10-16'][f'ma{w}_pct']}
                         for w in WINDOWS}
    old_symbol_count = len(old_cache)
    del old_cache

    # Same-target, individual-observation windows on the separately qualified Tencent cache.
    tq = {d: {w: {} for w in WINDOWS} for d in dates}
    t_symbols = set()
    tq_latest = Counter()
    df = pd.read_parquet(paths['tencent_qfq_cache'], columns=['symbol', 'date', 'close'])
    for symbol, g in df.groupby('symbol', sort=False):
        t_symbols.add(symbol)
        g = g.sort_values('date')
        ds = g['date'].astype(str).tolist()
        ps = [Decimal(str(x)) for x in g['close'].astype(float)]
        assert len(ds) == len(set(ds)) and all(x.is_finite() and x > 0 for x in ps)
        tq_latest[ds[-1]] += 1
        for day in dates:
            p = bisect_right(ds, day)
            if not p or ds[p - 1] != day:
                continue
            for w in WINDOWS:
                if p >= w:
                    tq[day][w][symbol] = ps[p - 1] * w > sum(ps[p - w:p], Decimal(0))
    del df

    listing = {}
    for name, prefix, ck, dk in [('sh_main','sh','证券代码','上市日期'),
                                ('sh_star','sh','证券代码','上市日期'),
                                ('sz','sz','A股代码','A股上市日期'),
                                ('bj','bj','证券代码','上市日期')]:
        with (BASE / f'cn-repair-candidate-20261102/listing-evidence/{name}-normalized.csv').open(encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                listing[prefix + row[ck].zfill(6)] = row[dk]
    classify_ast = next(n for n in ast.parse((QA / 'qualify-cn-westock-v4.py').read_text()).body
                        if isinstance(n, ast.FunctionDef) and n.name == 'classify')
    cn = {'math': math, 'DATES': ('2026-10-30',)}
    exec(compile(ast.Module(body=[classify_ast], type_ignores=[]), '<classification only>', 'exec'), cn)
    westock = {d: {w: {} for w in WINDOWS} for d in dates}

    def finish(symbol, rows):
        accepted = sorted((r['date'], Decimal(str(r['numeric']['last'])))
                          for r in rows if cn['classify'](r, listing[symbol]) == 'valid_quote')
        ds = [x[0] for x in accepted]
        ps = [x[1] for x in accepted]
        for day in dates:
            p = bisect_right(ds, day)
            if not p or ds[p - 1] != day:
                continue
            for w in WINDOWS:
                if p >= w:
                    westock[day][w][symbol] = ps[p - 1] * w > sum(ps[p - w:p], Decimal(0))

    current, rows = None, []
    with gzip.open(paths['westock_rows'], 'rt') as f:
        for line in f:
            row = json.loads(line)
            if current is not None and row['symbol'] != current:
                finish(current, rows)
                rows = []
            current = row['symbol']
            rows.append(row)
    if current is not None:
        finish(current, rows)

    bridge = {}
    for day in dates:
        bridge[day] = {}
        for w in WINDOWS:
            wa, ta = westock[day][w], tq[day][w]
            ws = {s: v for s, v in wa.items() if s in t_symbols}
            common = set(wa) & set(ta)
            wc, tc = ({s: wa[s] for s in common}, {s: ta[s] for s in common})
            groups = {k: rates(v) for k, v in [('westock_all', wa), ('westock_tencent_symbols', ws),
                                              ('westock_common_eligible', wc), ('tencent_common_eligible', tc),
                                              ('tencent_same_day', ta), ('legacy_asof_any_last_day', legacy_signals[day][w])]}
            assert groups['westock_all']['eligible'] == qual['days'][day]['all'][f'E{w}']
            assert groups['westock_all']['above'] == qual['days'][day]['all'][f'above{w}']
            a,b,c,d,e = [groups[k]['pct'] for k in ['westock_all','westock_tencent_symbols','westock_common_eligible','tencent_common_eligible','tencent_same_day']]
            observed = live[day][f'ma{w}_pct']
            components = {'extra_current_symbols_pp': a-b,
                          'candidate_only_eligible_within_old_symbols_pp': b-c,
                          'same_symbols_provider_and_window_inputs_pp': c-d,
                          'tencent_only_eligible_composition_pp': d-e,
                          'current_tencent_same_day_to_legacy_live_unattributed_pp': e-observed}
            assert math.isclose(sum(components.values()), a-observed, abs_tol=1e-10)
            bridge[day][str(w)] = {'live': observed, 'groups': groups,
                                  'westock_minus_live_pp': a-observed, 'additive_bridge_pp': components,
                                  'common_eligible_sign_disagreements': sum(wa[s] != ta[s] for s in common),
                                  'legacy_asof_matches_live_exact': groups['legacy_asof_any_last_day']['pct'] == observed}

    repeated = []
    for previous, current in zip(dates, dates[1:]):
        same = [w for w in WINDOWS if live[previous][f'ma{w}_pct'] == live[current][f'ma{w}_pct']]
        if same:
            repeated.append({'previous_stored_day': previous, 'stored_day': current,
                             'identical_windows': same,
                             'westock_change_pp': {str(w): rates(westock[current][w])['pct'] - rates(westock[previous][w])['pct'] for w in same}})
    sources = {}
    for ref in ['d5534723', 'cdbe2083', 'HEAD']:
        content = git_file(ref, source_path)
        evidence = {str(i): line.strip() for i,line in enumerate(content.splitlines(),1)
                    if any(k in line for k in ['threshold =', 'for series in cache.values()',
                                              'trading_day = max(last_dates)', 'today = ',
                                              'append_ma_breadth_history(ma20'])}
        sources[ref] = {'commit': subprocess.check_output(['git','rev-parse',ref],cwd=ROOT,text=True).strip(),
                        'blob_sha256': hashlib.sha256(content.encode()).hexdigest(), 'evidence_lines': evidence}
    bridge_summary = {}
    for w in WINDOWS:
        records = [r[str(w)] for r in bridge.values()]
        bridge_summary[str(w)] = {
            'mean_absolute_component_pp': {k: statistics.mean(abs(r['additive_bridge_pp'][k]) for r in records)
                                           for k in records[0]['additive_bridge_pp']},
            'max_absolute_same_symbol_input_difference_pp': max(abs(r['additive_bridge_pp']['same_symbols_provider_and_window_inputs_pp']) for r in records),
            'same_symbol_sign_disagreements_total': sum(r['common_eligible_sign_disagreements'] for r in records),
            'same_symbol_eligible_range': [min(r['groups']['westock_common_eligible']['eligible'] for r in records),
                                         max(r['groups']['westock_common_eligible']['eligible'] for r in records)],
            'legacy_asof_exact_match_dates': [day for day,r in bridge.items() if r[str(w)]['legacy_asof_matches_live_exact']],
        }
    assert input_shas == {k: sha(v) for k,v in paths.items()}, 'input changed during bounded diagnosis'
    result = {'schema':'diagnose-cn-legacy-v4/1', 'fixed_anchor_dates':dates,
              'input_sha256':input_shas, 'input_files':{k:str(v) for k,v in paths.items()},
              'live_rows':len(live_rows), 'live_unchanged':True,
              'legacy_unqualified_cache_symbols':old_symbol_count,
              'legacy_unqualified_cache_latest_dates':dict(sorted(legacy_latest_dates.items())),
              'legacy_latest_day_symbols':legacy_latest_day_symbols,
              'legacy_saved_cache_exact_function_replay':replay,
              'legacy_replay_vs_live_2026_10_16':replay_comparison,
              'tencent_qfq_symbols':len(t_symbols), 'tencent_qfq_latest_dates':dict(sorted(tq_latest.items())),
              'tencent_qfq_vs_current_list':{'common':len(t_symbols & set(listing)),
                                            'only_in_tencent':len(t_symbols-set(listing)),
                                            'absent_from_tencent_by_market':dict(Counter(s[:2] for s in set(listing)-t_symbols))},
              'repeated_legacy_values':repeated, 'git_code_evidence':sources,
              'twenty_day_bounded_bridge':bridge,
              'twenty_day_bridge_summary':bridge_summary,
              'limits':['The old unqualified cache explains a lineage defect; it is not approved repair data.',
                        'The exact 10/16 replay does not identify historical writer/process or prove every repeated date cause.',
                        'The additive bridge is descriptive input decomposition, not causal attribution of data-source differences.',
                        'Old snapshot membership and vendor revisions at each original run are not recoverable from these current files.',
                        'No source-specific rows were spliced, and no existing observations were replaced.']}
    (QA/'diagnose-cn-legacy-v4.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    lines = ['# A股旧宽度链：有限只读归因（2026-11-02）','',
             f'固定最近20个已有日期；保留全部{len(live_rows)}条旧历史。无网络、无阈值搜索、无缓存修改。','',
             '## 已证明的旧链通路','',
             '- git d5534723：缓存末日距当前不超过2个自然日即跳过刷新；按每股最后一条价聚合；append调用未传代表交易日且函数直接标当前日期。存在旧值被标今天的确定代码通路。',
             '- git cdbe2083/HEAD：append开始传代表日，但仍遍历整个cache.values，聚合不同个股各自最后一价并统一标max(last_dates)。当前请求代码不限制实际聚合样本。',
             f'- 冻结旧 a_share_klines.parquet 共{old_symbol_count}股，其中{legacy_latest_dates["2026-10-15"]}股末日为10-15，只有{legacy_latest_dates["2026-10-16"]}股到10-16；其余更旧。它没有当前qfq资格证明，只用来诊断。',
             '- 直接抽取git HEAD的旧fetch函数，只读注入保存的旧cache并禁止网络，返回交易日10-16。三窗结果与旧live的逐值比较：','',
             '| 窗口 | 旧函数复算 | live 10-16 | 精确相等 |','|---|---:|---:|---|']
    for w in WINDOWS:
        r=replay_comparison[f'ma{w}']
        lines.append(f'| {w} | {r["replayed"]:.12f} | {r["live"]:.12f} | {r["exact_equal"]} |')
    lines += ['', '这是旧序列与混合末日缓存的直接数值锚点；不能据此识别当时实际进程，也不能把其他重复日期一概认定为同一写入事件。', '',
              '其中唯一末日为10-16的保存序列是sh600825（801条，首日2023-06-06），并非由新IPO身份推断的结果。','',
              '## 20日固定输入分解','',
              '桥接顺序为：WeStock全候选 → WeStock仅腾讯qfq旧名单 → 两源共同合格股票 → 同股腾讯输入 → 腾讯全部同日合格样本 → 旧live。每段差值精确相加回总差；同股输入段含供应商价格、复权和有效历史窗口差异，不能进一步假称其中某个原因已单独证明。','',
              '| 日期 | 窗口 | 新减旧pp | 新增名单pp | 旧名单资格差pp | 同股输入pp | 腾讯独有资格pp | 旧链未归因pp |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for day in ['2026-09-10','2026-09-11','2026-09-18','2026-10-16']:
        for w in WINDOWS:
            r=bridge[day][str(w)]; c=r['additive_bridge_pp']
            lines.append('| '+day+' | '+str(w)+' | '+' | '.join(f'{v:+.4f}' for v in [r['westock_minus_live_pp'],*c.values()])+' |')
    lines += ['', '20个固定日期中，同股按相同N个有效观察规则所得供应商输入差非常小：','',
              '| 窗口 | 同股输入差绝对均值pp | 绝对最大pp | 站上/跌破分类不同股票日数 |','|---|---:|---:|---:|']
    for w in WINDOWS:
        s=bridge_summary[str(w)]
        lines.append(f'| {w} | {s["mean_absolute_component_pp"]["same_symbols_provider_and_window_inputs_pp"]:.6f} | {s["max_absolute_same_symbol_input_difference_pp"]:.6f} | {s["same_symbol_sign_disagreements_total"]} |')
    lines += ['', '因此本组旧新宽度大差不能主要归咎于当前两供应商在共同样本上的价格/窗口差。名单组成与旧链观测时点有直接证据；但名单桥接顺序并非唯一，未归因项仍不能当作已识别的单一因果贡献。']
    lines += ['', '## 不能证明与使用边界','',
              '- 当前腾讯qfq3169股和旧日更未合格cache5224股不是同一输入；不能把3169股子样本当成旧历史真实分母。',
              '- 重复数值本身不足以证明前填。JSON逐项列出重复窗口及独立候选的当日变化，以便定位；仅10-16具备上述保存旧cache的精确函数复算证据。',
              '- 原运行的成员名单、下载时点、逐股修订版本没有完整历史快照，20日桥接剩余项不能强行归因为复权或停牌。',
              '- 合适的后续产物是另存透明定义的重建观察序列，并保留旧版。不得拿旧未合格cache修补，也不得把新候选插入旧曲线后宣称全段同口径。','',
              '全部输入SHA、20日×3窗分母/分子/桥接、旧代码行号和重复值清单见同名JSON。']
    (QA/'diagnose-cn-legacy-v4.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'outputs':['diagnose-cn-legacy-v4.json','diagnose-cn-legacy-v4.md'],
                      'replay':replay_comparison,'old_cache_latest_dates':dict(legacy_latest_dates),
                      'repeated_pairs':len(repeated)},ensure_ascii=False))


if __name__ == '__main__':
    main()
