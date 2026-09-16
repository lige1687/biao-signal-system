"""No model/network/business database writes. Probe existing production helpers."""
import json
from pathlib import Path
from types import SimpleNamespace
from lei_signal.api.routes.agent import _comparison_reply, _deterministic_reply
from lei_signal.copilot.resolve import parse_request, detect_stance

symbol = '515880.SS'
def history(day, verdict, n=0):
    return [SimpleNamespace(role='assistant', meta_json=json.dumps({
        'resolved_symbol': symbol, 'evidence_card': {'facts': {
            'as_of': day, 'verdict_cn': verdict, 'buy_point_candidate_n': n,
            'display_name': '通信ETF'}}}))]

def context(day, verdict, n=0):
    return {'display_name': '通信ETF', 'as_of': day, 'evidence_card': {
        'facts': {'verdict_cn': verdict, 'buy_point_candidate_n': n}}}

results = {
    'same_day_changed': _comparison_reply(history('2026-09-16', '观察中'), symbol,
        context('2026-09-16', '可执行', 1), '和刚才相比有什么变化？'),
    'date_regressed': _comparison_reply(history('2026-09-16', '观察中'), symbol,
        context('2026-09-15', '观察中'), '和刚才相比有什么变化？'),
    'unrelated_question': _deterministic_reply(history('2026-09-16', '观察中'), symbol,
        context('2026-09-16', '观察中'), '如果换成ATR止损，胜率会有什么变化？'),
    'news_question': _deterministic_reply(history('2026-09-16', '观察中'), symbol,
        context('2026-09-16', '观察中'), '今天有什么新消息？'),
    'budgets': {m: parse_request(m)['budget'] for m in [
        '成交量有一万股', '一万股值多少钱', '我有一万二千元',
        '我有1万美元', '我没有一万元预算', '我有一万元闲钱']},
    'stances': {m: detect_stance(m) for m in [
        '如果重仓会怎样？', '我没有重仓', '我担心被套，暂时没持仓', '我已经持有了。']},
}
Path(__file__).with_name('results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
print(json.dumps(results, ensure_ascii=False, indent=2))
