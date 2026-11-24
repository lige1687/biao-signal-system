from datetime import date, timedelta
from decimal import Decimal

import pytest

from lei_signal.market_context.cn_breadth_refresh import (
    QualificationError,
    parse_kline,
    parse_snapshot,
    parse_zero_placeholders,
    qualify_tail,
)


def test_parse_kline_rejects_incomplete_batch_and_zero_placeholder():
    header = (
        "[Batch] 状态: success | 总数: 2 | 成功: 2 | 失败: 0\n"
        "| symbol | date | open | last | high | low | volume | amount | exchange |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    ).encode()
    rows = (
        b"| sh600000 | 2026-11-05 | 10 | 10.1 | 10.2 | 9.9 | 100 | 1000 | 1 |\n"
        b"| bj430047 | 2026-11-05 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |\n"
    )
    parsed = parse_kline(header + rows, ["sh600000", "bj430047"], "2026-11-05")
    assert parsed["sh600000"] == [("2026-11-05", Decimal("10.1"))]
    assert parsed["bj430047"] == []
    assert parse_zero_placeholders(header + rows, ["sh600000", "bj430047"], "2026-11-05") == {
        "2026-11-05": {"bj430047"}
    }
    with pytest.raises(ValueError, match="incomplete"):
        parse_kline(
            header.replace("总数: 2".encode(), "总数: 1".encode()) + rows,
            ["sh600000", "bj430047"],
            "2026-11-05",
        )
    with pytest.raises(ValueError, match="unexpected provider symbol"):
        parse_kline(
            header + b"| sz000001 | 2026-11-05 | 10 | 10 | 10 | 10 | 1 | 1 | 1 |\n",
            ["sh600000", "bj430047"],
            "2026-11-05",
        )


def test_snapshot_requires_same_day_explicit_zero_volume():
    fields = [""] * 40
    fields[3], fields[30], fields[36] = "8.17", "20261105090000", "0"
    raw = ('v_bj430047="' + "~".join(fields) + '";').encode("gbk")
    assert parse_snapshot(raw, "2026-11-05", ["bj430047"]) == {"bj430047"}
    with pytest.raises(ValueError, match="date"):
        parse_snapshot(raw, "2026-11-04", ["bj430047"])


def test_qualify_tail_preserves_old_rows_and_excludes_confirmed_ipo_and_halt():
    calendar = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(201)]
    old = [
        {
            "date": calendar[-2],
            "ma20_pct": 12.3,
            "ma50_pct": 11.2,
            "ma200_pct": 10.1,
            "other_old_field": "preserve",
        }
    ]
    listings = {"sh600000": "2000-01-01", "sz000001": calendar[-1], "bj430047": "2000-01-01"}
    series = {
        "sh600000": [(d, Decimal("10")) for d in calendar],
        "sz000001": [(calendar[-1], Decimal("5"))],
        "bj430047": [],
    }
    candidate, audit = qualify_tail(
        old, listings, calendar, series, calendar[-1], {calendar[-1]: {"bj430047"}}
    )
    assert candidate[0] == old[0]
    assert candidate[1]["ma200_pct"] == 0
    assert audit[calendar[-1]]["confirmed_nontrading"] == 1
    assert audit[calendar[-1]]["ipo_warmup_200"] == 1


def test_unresolved_same_day_quote_fails_entire_candidate():
    old = [{"date": "2026-11-04", "ma20_pct": 1}]
    with pytest.raises(QualificationError) as exc:
        qualify_tail(
            old,
            {"sh600000": "2000-01-01"},
            ["2026-11-04", "2026-11-05"],
            {"sh600000": []},
            "2026-11-05",
        )
    assert exc.value.audit["2026-11-05"]["unresolved"]["missing_same_day_quote"] == ["sh600000"]


def test_later_unresolved_day_keeps_only_continuous_qualified_prefix():
    calendar = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(202)]
    old = [{"date": calendar[-3], "ma20_pct": 1}]
    series = {"sh600000": [(d, Decimal("10")) for d in calendar[:-1]]}
    candidate, audit = qualify_tail(
        old, {"sh600000": "2000-01-01"}, calendar, series, calendar[-1], allow_partial=True
    )
    assert [row["date"] for row in candidate] == [calendar[-3], calendar[-2]]
    assert audit[calendar[-1]]["unresolved"]["missing_same_day_quote"] == ["sh600000"]
