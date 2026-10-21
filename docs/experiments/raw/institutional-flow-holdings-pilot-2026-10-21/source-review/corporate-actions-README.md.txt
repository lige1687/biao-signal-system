---
license: apache-2.0
language:
  - en
pretty_name: US Corporate Actions — dividends and splits, point-in-time
size_categories:
  - 100K<n<1M
task_categories:
  - tabular-regression
  - time-series-forecasting
tags:
  - finance
  - sec
  - edgar
  - xbrl
  - dividends
  - stock-splits
  - corporate-actions
  - point-in-time
  - ziplime
configs:
  - config_name: dividends
    data_files:
      - split: train
        path: "data/dividends/*.parquet"
  - config_name: splits
    data_files:
      - split: train
        path: "data/splits/*.parquet"
  - config_name: adjustment_factors
    data_files:
      - split: train
        path: "data/adjustment_factors/*.parquet"
  - config_name: pit
    data_files:
      - split: train
        path: "data/pit/*.parquet"
---

# US Corporate Actions — dividends and splits

**391 639 dividends from 3 327 filers · 5 619 splits from 3 814 filers ·
2005 to 2026**

Built to close a specific hole. A filing states shares and earnings per share
as of the day it was made; every price series is adjusted for splits since.
Multiply one by the other and the answer is wrong by the split factor — on
Deckers that turned a 6.9% earnings yield into 41.7%, a P/E of 1.8.

The pipeline lives in [`recipe/`](recipe/) at the same revision as the data.
See [PIPELINE.md](PIPELINE.md) for the method.

## Read this before anything else

**There are no ex-dates, record dates or pay dates here, and there is no free
source for them.** SEC's structured data carries only numeric facts; the
date-typed XBRL facts exist inside filings but not in the bulk data sets, and
the XBRL API returns 404 for them. What this dataset has is what can be had
from public filings: how much per share, over which fiscal period, known from
when — and split ratios recovered from the trace a split leaves in restated
figures.

If you need an ex-date calendar, this is not it, and nothing free is.

## The adjustment factor

This is the table most people want. Multiply an as-filed per-share figure by
`cumulative_split_factor` to put it on the same basis as a split-adjusted price
series.

```python
import polars as pl

factors = pl.read_parquet("data/adjustment_factors/*.parquet")

# Deckers: a 6-for-1 split detected between 2024-08-01 and 2024-10-31
factors.filter(pl.col("cik") == "0000910521")
# valid_from    valid_to      cumulative_split_factor  splits_after
# null          2024-10-31    6.0                      1
# 2024-10-31    null          1.0                      0
```

Shares outstanding filed before that window need multiplying by six; earnings
per share need dividing by it. Apple carries 28.0 before its 2014 seven-for-one
(7 × 4), 4.0 between the two, and 1.0 today.

## Splits, and how confident to be

No free feed of US splits exists. What exists, in a dataset that keeps every
filing's own version of a period, is the trace: a split forces the company to
restate every earlier per-share figure by the ratio. Two filings covering the
same quarter, one before and one after, differ by exactly that factor.

That is stronger than the obvious signal. A jump in shares outstanding looks
identical for a two-for-one split and an equity raise that doubled the count;
only a split reaches back and rewrites the past.

| Confidence | Rows | What it means |
|---|---|---|
| `high` | 514 | the filer tagged the conversion ratio, or both methods found it |
| `medium` | 3 728 | inferred from four or more restated figures |
| `low` | 1 377 | inferred from two or three |

Verified against the ratios filers tagged themselves: the two methods agree for
**73%** of the companies where both exist, and the inferred method reaches
seven times as many companies.

Each split carries a **window**, not a date: `detected_after` is the last
filing that still used the old figures, `detected_before` the first that used
the new. Deckers' September 2024 split lands in 2024-08-01 → 2024-10-31. That
is as precise as filings allow, and a date invented inside that window would be
a fiction.

Reverse splits outnumber forward ones almost three to one — 3 933 to 1 686 —
which is what the SEC filer universe actually looks like once you leave the
index names: shells consolidate to keep a listing far more often than
successful companies split.

## Dividends

Per-share amounts as filings stated them, for a fiscal period.

| | |
|---|---|
| `declared` | 276 299 — a decision made in the period |
| `cash_paid` | 115 340 — cash that moved in the period |
| common / preferred | 369 413 / 22 226 |
| restated later | 223 583 rows are a second or later report of the same period |
| subsequent events | 769 declared after the period closed, disclosed in the filing that follows |

Declared and paid are kept apart rather than merged: they are different facts,
and a company can declare in one quarter and pay in the next. Preferred
dividends are included because a preferred coupon ranks ahead of the common
holder, and a yield computed without it is wrong for exactly the companies
where it matters.

`period_start` is derived from `period_end` and `quarters`; a dividend fact
dated to an instant is dropped rather than assigned a day it did not cover.

## Configs

| Config | Rows | What one row is |
|---|---|---|
| `dividends` | 391 639 | one per-share dividend a filing stated for one period |
| `splits` | 5 619 | one split, with the window it must have happened in |
| `adjustment_factors` | 9 433 | one span and the factor that puts an as-filed figure on today's basis |
| `pit` | 397 258 | one point-in-time action event, plus a Delta table for ziplime |

`entity_id` in `pit` is the issuer CIK, the same key used across the family, so
this joins directly to
[company-fundamentals](https://huggingface.co/datasets/ZipLime/company-fundamentals),
[insider-trading](https://huggingface.co/datasets/ZipLime/insider-trading) and
[security-master](https://huggingface.co/datasets/ZipLime/security-master).

## Known gaps

* **No dividend dates.** See above. The period is the finest granularity
  available.
* **A split window is a window.** Typically one quarter wide.
* **Splits before 2009 are not visible.** The restatement trace needs XBRL, and
  XBRL starts in 2009 Q1. A company that split in 2006 shows no split here.
* **Stock dividends under 18% are not detected.** A five percent stock dividend
  and a five percent restatement leave the same trace, so nothing between 0.85
  and 1.18 is admitted as a split rather than risk phantom factors.
* **Special and irregular dividends are not separated** from regular ones. The
  filing usually does not distinguish them either.
* **Low-confidence splits are published, not hidden.** Filter on `confidence`
  if a wrong factor would be worse than a missing one.

## Provenance and updates

Derived entirely from
[ZipLime/company-fundamentals](https://huggingface.co/datasets/ZipLime/company-fundamentals),
which is itself SEC XBRL — US Government work, public domain. No source of its
own is fetched.

Rebuilt weekly, Monday 08:10 UTC, after the dataset it reads.
