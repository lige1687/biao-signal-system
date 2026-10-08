"""Compare saved official annual notice with saved exchange calendar; no downloads."""
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = ROOT / 'docs/experiments/raw/research-calendar-completion-2026-09-10'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(name, data):
    (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    calendar_path = BASE / 'calendar-merged/calendar.json'
    notice_path = BASE / 'publication-probe/sse_2026_annual_notice.html'
    evidence_path = BASE / 'publication-evidence.json'
    assert sha(calendar_path) == 'aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1'
    calendar = json.loads(calendar_path.read_text())
    text = BeautifulSoup(notice_path.read_bytes(), 'html.parser').get_text(' ', strip=True)
    assert '上证公告〔2025〕45号' in text and '2025年12月22日' in text
    # Freeze source identities before comparing calendar values.
    dump('input-manifest.json', {'inputs': {str(p.relative_to(ROOT)): sha(p) for p in (calendar_path, notice_path, evidence_path)}, 'run_sha256': sha(Path(__file__)),
                                'source_url': 'http://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml', 'published_at': '2025-12-22', 'new_http_requests': 0,
                                'scope': 'Scheduled trading-day equivalence January1-June30,2026 only; February already checked by original study.'})
    # Manual transcription is independently compared against an extraction from
    # the saved original text, before either is compared with the SZSE flags.
    expected = [('01-01', '01-03'), ('02-15', '02-23'), ('04-04', '04-06'), ('05-01', '05-05'), ('06-19', '06-21'), ('09-25', '09-27'), ('10-01', '10-07')]
    parsed = []
    for start_m, start_d, end_m, end_d in re.findall(r'(\d+)月(\d+)日（星期.）至(?:(\d+)月)?(\d+)日（星期.）休市', text):
        parsed.append((f'{int(start_m):02}-{int(start_d):02}', f'{int(end_m or start_m):02}-{int(end_d):02}'))
    assert parsed == expected, parsed
    closed = set()
    for a, b in parsed:
        day, end = dt.date.fromisoformat('2026-' + a), dt.date.fromisoformat('2026-' + b)
        while day <= end:
            closed.add(day)
            day += dt.timedelta(days=1)
    rows = []
    day, end = dt.date(2026, 1, 1), dt.date(2026, 6, 30)
    while day <= end:
        planned = day.weekday() < 5 and day not in closed
        saved = calendar['days'][day.isoformat()]['is_trading_day']
        rows.append({'date': day.isoformat(), 'sse_planned_open': planned, 'szse_saved_open': saved, 'match': planned == saved, 'new_beyond_original_february_check': day.month != 2})
        day += dt.timedelta(days=1)
    mismatches = [r for r in rows if not r['match']]
    result = {'status': 'completed_bounded_schedule_equivalence', 'date_count': len(rows), 'new_date_count': sum(r['new_beyond_original_february_check'] for r in rows),
              'sse_planned_open_days': sum(r['sse_planned_open'] for r in rows), 'szse_saved_open_days': sum(r['szse_saved_open'] for r in rows), 'mismatches': mismatches,
              'parsed_closure_ranges': parsed, 'source_publication': '2025-12-22',
              'qualification_remaining': ['No systematic scan for later exceptional closure amendments.', 'Annual-notice-vs-calendar equivalence is not evidence every security traded on those dates.', 'Before2026 historical SSE calendar and historical announcement availability remain unqualified.', 'D-MAE six frozen originals and original independent review requirements remain unchanged.']}
    assert len(rows) == 181 and result['new_date_count'] == 153
    dump('daily-comparison.json', rows)
    dump('result.json', result)
    dump('manifest.json', {'artifacts': {p.name: sha(p) for p in HERE.iterdir() if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
