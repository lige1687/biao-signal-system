import json
from pathlib import Path
from types import SimpleNamespace as R
from lei_signal.copilot.resolve import parse_request, detect_stance, detect_fact_correction
from lei_signal.api.routes.agent import _user_background

rows = [
    R(role='user', content='我已经持有了。', meta_json='{}', message_id=1, question_id=None),
    R(role='user', content='改看510300', meta_json='{}', message_id=2, question_id=None),
    R(role='assistant', content='答第二个问题',
      meta_json=json.dumps({'resolved_symbol': '510300.SS'}), message_id=3, question_id=2),
]
result = {
    'hypothetical_budget': parse_request('如果我有一万元，能不能买？')['budget'],
    'third_party_budget': parse_request('朋友有一万元闲钱')['budget'],
    'cash_misread_as_holding': detect_stance('我手里有一万元闲钱'),
    'complex_partial': parse_request('我有两万三千五')['budget'],
    'unanswered_cross_binding': _user_background(rows, '510300.SS'),
    'correction': detect_fact_correction('我已经不持有了'),
}
Path(__file__).with_name('background.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
