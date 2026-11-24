import gzip
import json

import pytest

from lei_signal.research import focus_gap_fetch as gap


class FakeResponse:
    error_code = "0"
    error_msg = "success"

    def __init__(self, fields, rows):
        self.fields = ",".join(fields)
        self.rows = iter(rows)
        self.current = None

    def next(self):
        self.current = next(self.rows, None)
        return self.current is not None

    def get_row_data(self):
        return self.current


def daily(day="2026-10-26", code="sh.600000", amount="150000000.00"):
    row = ["" for _ in gap.SOURCE_FIELDS]
    row[0], row[1] = day, code
    row[gap.SOURCE_FIELDS.index("amount")] = amount
    row[gap.SOURCE_FIELDS.index("adjustflag")] = "3"
    row[gap.SOURCE_FIELDS.index("tradestatus")] = "1"
    return row


def test_daily_response_preserves_amount_and_unadjusted_flag(tmp_path):
    row = daily()
    payload = gap.collect_response(FakeResponse(gap.SOURCE_FIELDS, [row]),
                                   "sh.600000", gap.SOURCE_FIELDS, "daily")
    ref = gap.save_response(tmp_path, "sh.600000", "daily", payload)
    saved = (tmp_path / "daily-sh-600000.json.gz").read_bytes()
    assert gap.sha256(saved) == ref["compressed_sha256"]
    assert gap.sha256(gzip.decompress(saved)) == ref["payload_sha256"]
    assert json.loads(gzip.decompress(saved))["data"][0] == row
    assert payload["query"]["adjustflag"] == "3"
    assert payload["query"]["start_date"] == "2026-10-26"


@pytest.mark.parametrize("rows,fields", [
    ([daily(code="sz.000001")], gap.SOURCE_FIELDS),
    ([daily(day="2026-10-23")], gap.SOURCE_FIELDS),
    ([daily(), daily()], gap.SOURCE_FIELDS),
    ([daily()[:-1]], gap.SOURCE_FIELDS),
    ([daily()], gap.SOURCE_FIELDS[:-1]),
])
def test_rejects_wrong_identity_date_order_width_or_schema(rows, fields):
    with pytest.raises(ValueError):
        gap.collect_response(FakeResponse(fields, rows), "sh.600000", gap.SOURCE_FIELDS, "daily")


def test_factor_events_are_separate_and_coverage_counts_missing_rows(tmp_path):
    code = "sh.600000"
    factor = [code, "2026-10-28", "0.5", "2", "1"]
    refs = []
    for kind, fields, rows in (("daily", gap.SOURCE_FIELDS, [daily()]),
                               ("factor", gap.ADJUSTMENT_FIELDS, [factor])):
        payload = gap.collect_response(FakeResponse(fields, rows), code, fields, kind)
        refs.append(gap.save_response(tmp_path, code, kind, payload))
    summary = gap.coverage(refs, tmp_path, [code])
    assert summary["factorEventRows"] == 1
    assert summary["byDate"]["2026-10-26"]["validAmountCodes"] == 1
    assert summary["byDate"]["2026-10-27"]["noQuoteRowAmongSuccessfulDailyCodes"] == 1
    assert summary["dailyQueryFailedCodes"] == []
