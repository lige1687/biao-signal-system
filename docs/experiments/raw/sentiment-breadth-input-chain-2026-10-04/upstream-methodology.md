# How this dataset was built and validated

## Reconstruction
Membership is stored as a **snapshot + change log**: the `current` list is the index on
2026-06-30; each change event `{date, added, removed}` comes from Wikipedia's
"List of S&P 500 companies" selected-changes table. `members_asof(D)` rewinds the snapshot by
undoing every event newer than `D` — deterministic, no lookahead, no interpolation.

## Validation (2016 → 2026)
For each mid-year date, the reconstructed membership was joined against fetchable daily price
history (Alpaca SIP), counting how many members had data — the residual "delisted hole" that
silently shrinks most survivorship-free attempts:

| as-of | members | fetchable | coverage |
|---|---|---|---|
| 2016-06-30 | 509 | 509 | 100% |
| 2017-06-30 | 509 | 509 | 100% |
| 2018-06-30 | 507 | 507 | 100% |
| 2019-06-30 | 507 | 507 | 100% |
| 2020-06-30 | 507 | 507 | 100% |
| 2021-06-30 | 507 | 507 | 100% |
| 2022-06-30 | 504 | 504 | 100% |
| 2023-06-30 | 504 | 504 | 100% |
| 2024-06-30 | 504 | 504 | 100% |
| 2025-06-30 | 504 | 504 | 100% |
| 2026-06-01 | 504 | 503 | 100% (one name IPO'd later that month) |

Counts >500 are correct: the index holds multiple share classes for some constituents.

## Why it matters (measured)
On this universe, replayed 2017 → mid-2026 with next-open fills and costs, a leadership-
rotation rule compounded +638% vs SPY's +282% — **with the honesty rider that through
end-2025 it ran roughly even with SPY** (the gap concentrates in 2025–2026 leadership
regimes). Same harness, same window, classic 12-1 momentum variants did +241% to +310% with
deeper drawdowns. The point of publishing the rider next to the headline is the same as the
point of this dataset: a backtest you can't audit is a story.
Full context: https://coil.trade/learn/best-ai-trading-strategy

## Events before 2016
The change log extends to 1976-07-01 as carried by the source. These early events are
included verbatim but were NOT validated against price data. Treat pre-2016 reconstruction
as best-effort.
