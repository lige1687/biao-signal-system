"""Pure adapter for the fixed annual operating-profitability measurement.

This function validates only its supplied values. Callers must independently bind
and qualify a consistent USD annual filing/accession, explicit zero preferred
equity, a complete equity balance identity, interest reported below operating
income, timely availability, and issuer identity. It does not validate source
documents, accounting periods, publication timing, or issuer identity.
"""

import math
from decimal import Decimal


def _finite_amount(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def operating_profitability_after_da(
    operating_income,
    nonoperating_interest_expense,
    inclusive_common_equity,
    *,
    financials_qualified,
):
    """Return (reported operating income - interest expense) / common equity.

    ``financials_qualified`` must be exactly ``True`` and all amounts must be
    finite numeric values (booleans are not amounts). Interest cannot be
    negative and equity must be positive. Negative or zero operating results
    are retained without clipping or winsorization. Missing or invalid inputs
    return ``None``; no sign changes, absolute values, or imputation are used.

    Source, timing, and statement qualification remain the caller's
    responsibility; see this module's documentation for required bindings.
    """
    if financials_qualified is not True:
        return None
    if not all(_finite_amount(value) for value in (
        operating_income, nonoperating_interest_expense, inclusive_common_equity
    )):
        return None
    oi, interest, equity = map(float, (
        operating_income, nonoperating_interest_expense, inclusive_common_equity
    ))
    if interest < 0 or equity <= 0:
        return None
    result = (oi - interest) / equity
    return result if math.isfinite(result) else None
