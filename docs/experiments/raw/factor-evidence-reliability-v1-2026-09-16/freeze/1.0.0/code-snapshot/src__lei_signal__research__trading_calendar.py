"""研究专用交易日历适配器（第二轮）。

与 ``data/calendar.py`` 的关系
------------------------------
``data/calendar.py::WeekdayCalendar`` 是**周一至周五近似且节假日表为空**
（`:74`、`:115`），本模块**不修改也不替换它**，只为研究层提供一个有来源、
可追溯、能诚实说「不知道」的日历。

两个必须分开的问题
------------------
1. **事后确认某日是否开市** —— 本模块能回答（在已覆盖月份内）。
   历史日期对齐用这个。
2. **当时是否已经知道后续开休市安排** —— 需要额外的**发布时间证据**。
   逐日交易标志本身只给结果，不给该安排的发布时刻。若通过
   ``publication_evidence`` 提供了某年年度通知的发布日期，
   :meth:`TradingCalendar.schedule_known_at` 才能对该年的日期作答；
   没有证据的年份一律返回未知，**不得假设同样提前公布**。

绝不回退
--------
未覆盖的日期返回 ``unknown`` 与原因，**不回退为普通工作日**。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

TRADING = "trading"
CLOSED = "closed"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class DayStatus:
    day: str
    status: str
    reason: str
    source_month: str | None = None

    @property
    def is_trading(self) -> bool:
        """仅在**确认为交易日**时为真；unknown 一律为假，不当作开市。"""
        return self.status == TRADING

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "status": self.status,
            "reason": self.reason,
            "source_month": self.source_month,
        }


@dataclass(frozen=True)
class CoverageReport:
    start: str
    end: str
    covered_months: tuple[str, ...]
    missing_months: tuple[str, ...]
    trading_days_known: int
    closed_days_known: int
    day_incomplete_months: tuple[str, ...] = ()
    """**查询区间内**逐日记录不完整的月份。

    只核区间与该月的交集：查询一个月的部分区间时，不因区间外缺日误判。
    整月完整性见 ``month_incomplete_months``，两者不混为一谈。
    """

    month_incomplete_months: tuple[str, ...] = ()
    """整月记录不完整的月份（无论查询区间）。信息性单列。"""

    invalid_records: tuple[dict, ...] = ()
    """被剔除的非法日期记录（如 2026-01-99）。显式列出，不悄悄消失。"""

    @property
    def complete(self) -> bool:
        """只有「月份全覆盖」且「覆盖月份内逐日完整」才算完整。"""
        return not self.missing_months and not self.day_incomplete_months

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "covered_months": list(self.covered_months),
            "missing_months": list(self.missing_months),
            "day_incomplete_months": list(self.day_incomplete_months),
            "month_incomplete_months": list(self.month_incomplete_months),
            "invalid_records": list(self.invalid_records),
            "trading_days_known": self.trading_days_known,
            "closed_days_known": self.closed_days_known,
            "complete": self.complete,
        }


class TradingCalendar:
    """由已核验来源构造的交易日历。只读。"""

    def __init__(self, payload: dict, publication_evidence: dict | None = None):
        self._payload = payload
        self._pub = publication_evidence or {}
        self._annual_by_year: dict[int, dict] = {
            int(n["year"]): n
            for n in self._pub.get("annual_notices", [])
            if n.get("year") and n.get("published_at")
        }
        # 非法日期键（如 "2026-01-99"）一律剔除并显式记录——
        # 非法日期不能进入有效日历集合，也不能补足覆盖数量。
        from datetime import date as _date

        valid: dict[str, dict] = {}
        invalid: list[dict] = []
        for key, rec in payload["days"].items():
            ok = False
            if isinstance(key, str) and len(key) == 10:
                try:
                    _date.fromisoformat(key)
                    ok = True
                except ValueError:
                    ok = False
            if ok:
                valid[key] = rec
            else:
                invalid.append({"key": key, "record": rec})
        self._days: dict[str, dict] = valid
        self._invalid_records: tuple[dict, ...] = tuple(invalid)
        self._invalid_keys: frozenset[str] = frozenset(b["key"] for b in invalid)
        self._covered = {m for m in payload.get("months_requested", [])}
        failed = set(payload.get("months_failed", []))
        self._covered -= failed
        self.authority: str = payload.get("authority", "unknown")
        self.publisher: str = payload.get("publisher", "unknown")

    @classmethod
    def from_file(
        cls, path: Path | str, publication_evidence_path: Path | str | None = None
    ) -> TradingCalendar:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        pub = None
        if publication_evidence_path is not None:
            pub = json.loads(
                Path(publication_evidence_path).read_text(encoding="utf-8")
            )
        return cls(payload, pub)

    # -- 问题 1：事后确认是否开市 ---------------------------------------

    def status(self, day: str | date) -> DayStatus:
        key = day.isoformat() if isinstance(day, date) else str(day)[:10]
        if key in self._invalid_keys:
            return DayStatus(
                day=key,
                status=UNKNOWN,
                reason="来源含非法日期记录，已剔除；该日状态未知，不推断",
            )
        rec = self._days.get(key)
        if rec is not None:
            return DayStatus(
                day=key,
                status=TRADING if rec["is_trading_day"] else CLOSED,
                reason=f"{self.publisher} 官方标志 jybz={rec['source_flag']}",
                source_month=rec.get("source_month"),
            )
        month = key[:7]
        if month in self._covered:
            # 已取该月却没有这一天：来源本身未列出，仍然是未知，不猜。
            return DayStatus(
                day=key,
                status=UNKNOWN,
                reason=f"{month} 已取但来源未列出该日期；不推断，不回退为工作日",
                source_month=month,
            )
        return DayStatus(
            day=key,
            status=UNKNOWN,
            reason=f"{month} 不在已取月份内；未知，不回退为工作日",
        )

    def is_trading_day(self, day: str | date) -> bool:
        """**仅**确认为交易日才返回 True。未知按不开市处理是错的，

        所以调用方应先用 :meth:`status` 区分 closed 与 unknown，
        本方法只用于「确定开市才做某事」的场景。
        """
        return self.status(day).is_trading

    # -- 问题 2：当时是否已知后续安排 -------------------------------------

    def schedule_known_at(self, day: str | date, as_of: str) -> DayStatus:
        """该日的开休市安排在 ``as_of`` 时点是否已经公布。

        只有该年的年度通知发布日期有登记证据时才作答；否则返回未知。
        ``as_of`` 与发布日期均按日期比较（日内时刻不做推断）。
        """
        key = day.isoformat() if isinstance(day, date) else str(day)[:10]
        year = int(key[:4])
        notice = self._annual_by_year.get(year)
        if notice is None:
            return DayStatus(
                day=key,
                status=UNKNOWN,
                reason=(
                    f"未登记 {year} 年年度休市通知的发布日期；"
                    "逐日交易标志只给结果不给发布时刻。"
                    "不得假设该年同样提前公布——若规则要提前利用未来开休市安排，"
                    "必须先取得该年公告发布时间"
                ),
            )
        published = str(notice["published_at"])[:10]
        known = str(as_of)[:10] >= published
        return DayStatus(
            day=key,
            status=TRADING if known else CLOSED,
            reason=(
                f"{year} 年安排由《{notice.get('title', '年度通知')}》"
                f"（{notice.get('document_number', '编号未记')}）于 {published} 公布，"
                f"发布方 {notice.get('publisher', '未记')}；"
                f"as_of={str(as_of)[:10]} "
                f"{'不早于' if known else '早于'}发布日期。"
                "注意：本证据的发布方可能与逐日标志的发布方不同"
            ),
            source_month=published,
        )

    def schedule_known_from(self, day: str | date) -> str | None:
        """该日所属年度安排的最早可知日期；无证据返回 ``None``。"""
        key = day.isoformat() if isinstance(day, date) else str(day)[:10]
        notice = self._annual_by_year.get(int(key[:4]))
        return str(notice["published_at"])[:10] if notice else None

    # -- 覆盖 -------------------------------------------------------------

    def coverage(self, start: str, end: str) -> CoverageReport:
        # 起止倒置时原实现返回 complete=True 且零覆盖——一个闸门函数
        # 出现「静默假通过」比报错危险得多，因此显式拒绝。
        if start[:10] > end[:10]:
            raise ValueError(
                f"起止倒置：start={start!r} 晚于 end={end!r}；"
                "不返回空覆盖冒充已核对"
            )
        y, m = (int(x) for x in start[:7].split("-"))
        ey, em = (int(x) for x in end[:7].split("-"))
        needed = []
        while (y, m) <= (ey, em):
            needed.append(f"{y:04d}-{m:02d}")
            m += 1
            if m == 13:
                y, m = y + 1, 1
        missing = tuple(sorted(set(needed) - self._covered))
        inrange = {d: r for d, r in self._days.items() if start <= d <= end}
        covered = tuple(sorted(set(needed) & self._covered))
        # 逐日完整性：用**真实日期集合**核对，不用字符串前缀计数——
        # 非法日期键在加载时已剔除，不能补足数量。
        # 区间完整性只看「查询区间 ∩ 该月」；整月完整性单列。
        import calendar as _cal
        from datetime import date, timedelta

        day_incomplete: list[str] = []
        month_incomplete: list[str] = []
        for ym in covered:
            y, m = (int(x) for x in ym.split("-"))
            last_day = _cal.monthrange(y, m)[1]
            month_dates = {
                f"{ym}-{d:02d}" for d in range(1, last_day + 1)
            }
            # 整月完整性（信息性，不影响区间判定）
            if not month_dates <= set(self._days):
                month_incomplete.append(ym)
            # 区间与该月的交集
            lo = max(start, f"{ym}-01")
            hi = min(end, f"{ym}-{last_day:02d}")
            if lo > hi:
                continue
            d0, d1 = date.fromisoformat(lo[:10]), date.fromisoformat(hi[:10])
            expected_in_range: set[str] = set()
            cur = d0
            while cur <= d1:
                expected_in_range.add(cur.isoformat())
                cur += timedelta(days=1)
            if not expected_in_range <= set(self._days):
                day_incomplete.append(ym)
        return CoverageReport(
            start=start,
            end=end,
            covered_months=covered,
            missing_months=missing,
            trading_days_known=sum(1 for r in inrange.values() if r["is_trading_day"]),
            closed_days_known=sum(
                1 for r in inrange.values() if not r["is_trading_day"]
            ),
            day_incomplete_months=tuple(day_incomplete),
            month_incomplete_months=tuple(month_incomplete),
            invalid_records=self._invalid_records,
        )

    def days_in_month(self, month: str) -> tuple[str, ...]:
        """某月已记录的全部日期（无论开休市），升序。"""
        return tuple(sorted(d for d in self._days if d.startswith(month)))

    def trading_days(self, start: str, end: str) -> tuple[str, ...]:
        """区间内**已确认为交易日**的日期，升序。未知日期不包含在内。"""
        return tuple(
            sorted(
                d
                for d, rec in self._days.items()
                if rec["is_trading_day"] and start <= d <= end
            )
        )

    def closed_days(self, start: str, end: str) -> tuple[str, ...]:
        """区间内**已确认为非交易日**的日期，升序。未知日期不包含在内。"""
        return tuple(
            sorted(
                d
                for d, rec in self._days.items()
                if not rec["is_trading_day"] and start <= d <= end
            )
        )

    def classify_absence(
        self,
        day: str | date,
        *,
        symbols_with_quote: int,
        symbols_expected: int,
        halted_symbols: int = 0,
    ) -> dict:
        """区分「休市」与「单产品缺报价」——这是两件事，不能混为一谈。"""
        st = self.status(day)
        if st.status == UNKNOWN:
            verdict = "unknown_calendar"
            note = "日历未知，无法判断缺报价是休市还是产品原因"
        elif st.status == CLOSED:
            verdict = "market_closed"
            note = "全市场休市；此日无报价属正常，不计入产品缺失"
        elif symbols_with_quote == 0:
            verdict = "trading_day_but_pool_empty"
            note = "官方为交易日却整池零报价——数据缺口，需追查"
        elif symbols_with_quote < symbols_expected:
            gap = symbols_expected - symbols_with_quote
            if halted_symbols and halted_symbols >= gap:
                verdict = "partial_quotes_explained_by_halt"
                note = (
                    f"交易日内 {gap} 只无报价，已有 {halted_symbols} 条登记停牌可解释；"
                    "属已知事件，非未解释缺口"
                )
            else:
                verdict = "partial_quotes"
                note = (
                    f"交易日内 {gap} 只无报价（未上市/停牌/数据缺失），非休市；"
                    f"其中可由登记停牌解释的 {halted_symbols} 条"
                )
        else:
            verdict = "complete"
            note = "交易日且全部产品有报价"
        return {
            "day": st.day,
            "calendar_status": st.status,
            "verdict": verdict,
            "note": note,
            "symbols_with_quote": symbols_with_quote,
            "symbols_expected": symbols_expected,
            "halted_symbols": halted_symbols,
        }

    def to_source_record(self) -> dict:
        """来源表条目：发布方、覆盖、限制、许可等。"""
        return {
            "publisher": self.publisher,
            "authority": self.authority,
            "endpoint_template": self._payload.get("endpoint_template"),
            "field_semantics": self._payload.get("field_semantics"),
            "months_requested": self._payload.get("months_requested"),
            "months_failed": self._payload.get("months_failed"),
            "requests_used": self._payload.get("requests_used"),
            "day_count": self._payload.get("day_count"),
            "trading_day_count": self._payload.get("trading_day_count"),
            "limitations": self._payload.get("limitations"),
            "publication_evidence": {
                "years_with_annual_notice": sorted(self._annual_by_year),
                "what_this_does_not_answer": self._pub.get(
                    "what_this_does_not_answer", []
                ),
            },
            "fetched_calls": [
                {
                    "url": c["url"],
                    "requested_at": c["requested_at"],
                    "returned_at": c["returned_at"],
                    "http_status": c["http_status"],
                    "body_sha256": c["body_sha256"],
                }
                for c in self._payload.get("calls", [])
            ],
        }


__all__ = [
    "TRADING",
    "CLOSED",
    "UNKNOWN",
    "DayStatus",
    "CoverageReport",
    "TradingCalendar",
]
