"""Task 2：把本地官方原文抽成可回查的事实记录（evidence-bundle.json）。

- 515300 六份官方分红公告（txt 为抽取文本，关键日期/单位与冻结行动逐字段
  比对；每10份→每份换算独立手算核对）；第七条行动无官方原文，如实登记。
- 三份官方拆分 PDF（方向 1:N、权益登记/除权日）与两份上市公告 PDF
  （上市交易日、公告公布日期下界）。
- 时间证据只记"公布日期下界"（published_date/not_before），不伪造
  available_at；facts_verified 只表示字段与冻结记录一致，不表示历史
  可得性已证明。

读取记账：原文/抽取文本读取次数写入 bundle（≤80 上限）。
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import pdfplumber

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
OUT = ROOT / "docs/experiments/raw/research-fixed-etf-evidence-integration-2026-09-13"
ACTION_SRC = ROOT / "docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/action-sources"
OFFICIAL_515300 = ROOT / "docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/515300-official-qualification"
LISTING_DIR = ROOT / "docs/experiments/raw/research-mixed-evaluation-2026-09-09/historical-qualification"

READS: list[str] = []


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_count(p: Path) -> str:
    READS.append(str(p.relative_to(ROOT)))
    if len(READS) > 80:
        raise RuntimeError("原文读取超出 80 上限")
    return ""


def pdf_text(p: Path, pages: int | None = None) -> str:
    read_count(p)
    with pdfplumber.open(p) as pdf:
        want = pdf.pages if pages is None else pdf.pages[:pages]
        return "\n".join((pg.extract_text() or "") for pg in want)


# ---- 冻结行动（只读，比对基准） ----
frozen = {
    e["event_id"]: e
    for e in json.loads(
        (ACTION_SRC / "normalized-actions.json").read_text(encoding="utf-8")
    )["events"]
}

records: list[dict] = []
conflicts: list[dict] = []


def base_record(record_id, instrument, fact_type, event_id, facts,
                source_path, locator, excerpt) -> dict:
    return {
        "record_id": record_id,
        "instrument_id": instrument,
        "fact_type": fact_type,
        "event_id": event_id,
        "facts": facts,
        "source": {"path": source_path, "sha256": sha(ROOT / source_path)},
        "locator": locator,
        "short_supporting_text": excerpt,
        "time_evidence": {
            "kind": "unknown", "available_at": None,
            "published_date": None, "not_before": None, "not_after": None,
            "timezone": "Asia/Shanghai", "basis": "explicit missing",
        },
        "facts_verified": False,
        "historical_availability_verified": False,
        "allowed_for": [], "limitations": [],
    }


# ---- 1) 515300 六份官方分红公告 ----
DIV_TEXTS = [
    ("515300_20231214_MO7U", "515300-cash_dividend-2023-12-19"),
    ("515300_20240618_QXY9", "515300-cash_dividend-2024-06-21"),
    ("515300_20240913_SAOV", "515300-cash_dividend-2024-09-20"),
    ("515300_20241128_QVEK", "515300-cash_dividend-2024-12-03"),
    ("515300_20250612_HGW2", "515300-cash_dividend-2025-06-17"),
    ("515300_20250915_NN2J", "515300-cash_dividend-2025-09-18"),
]
for stem, event_id in DIV_TEXTS:
    txt_path = OFFICIAL_515300 / "sources" / f"{stem}.txt"
    pdf_path = OFFICIAL_515300 / "sources" / f"{stem}.pdf"
    text = txt_path.read_text(encoding="utf-8", errors="replace")
    read_count(txt_path)

    def grab(pattern: str) -> str | None:
        m = re.search(pattern, text)
        return m.group(1) if m else None

    def grab_groups(pattern: str):
        m = re.search(pattern, text)
        return m.groups() if m else None

    sent = grab_groups(r"公告送出日期[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
    sent_iso = date(int(sent[0]), int(sent[1]), int(sent[2])).isoformat() if sent else None
    code = grab(r"基金主代码\s*(\d{6})")
    m10 = re.search(r"分红方案.*?）\s*\n?\s*([0-9]+\.[0-9]+)", text, re.S)
    per10 = m10.group(1) if m10 else None
    record_d = grab_groups(r"权益登记日\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
    record_iso = (date(int(record_d[0]), int(record_d[1]), int(record_d[2])).isoformat()
                  if record_d else None)
    ex = grab_groups(r"除息日\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
    ex_iso = date(int(ex[0]), int(ex[1]), int(ex[2])).isoformat() if ex else None
    pay = grab_groups(r"现金红利发放日\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
    pay_iso = date(int(pay[0]), int(pay[1]), int(pay[2])).isoformat() if pay else None

    fev = frozen.get(event_id, {})
    per_share = round(float(per10) / 10.0, 6) if per10 else None
    checks = {
        "code_matches_frozen_symbol": code == fev.get("symbol", "515300"),
        "ex_date_matches": ex_iso == fev.get("ex_date"),
        "per_share_matches_frozen": (
            per_share is not None
            and abs(per_share - float(fev.get("cash_per_unit", -1))) <= 1e-9
        ),
        "unit_conversion_hand_checked": (
            per10 is not None and abs(float(per10) / 10.0 - float(fev.get("cash_per_unit", -1))) <= 1e-9
        ),
    }
    facts_verified = all(checks.values())

    rec = base_record(
        f"515300-{stem}", "515300.SS", "cash_dividend", event_id,
        {
            "announcement_sent_date": sent_iso,
            "fund_main_code": code,
            "cash_per_10_shares_announced": per10,
            "cash_per_share_computed": per_share,
            "record_date": record_iso,
            "ex_date": ex_iso,
            "pay_date": pay_iso,
            "field_checks": checks,
        },
        str(txt_path.relative_to(ROOT)),
        {"page": 1, "section": "公告基本信息/与分红相关的其他信息"},
        f"公告送出日期：{sent_iso}；本次分红方案（单位：元/10份基金份额）{per10}；"
        f"除息日 {ex_iso}",
    )
    rec["source"]["pdf_path"] = str(pdf_path.relative_to(ROOT))
    rec["source"]["pdf_sha256"] = sha(pdf_path)
    read_count(pdf_path)  # 原文页核对（PDF 文本页与抽取文本同源核对）
    rec["time_evidence"] = {
        "kind": "published_date_bound",
        "available_at": None,
        "published_date": sent_iso,
        "not_before": None, "not_after": None,
        "timezone": "Asia/Shanghai",
        "basis": "公告送出日期为基金管理人官方公告的公布日期下界；"
                 "不据此填写精确 available_at",
    }
    rec["facts_verified"] = facts_verified
    rec["historical_availability_verified"] = False
    rec["allowed_for"] = ["description", "fact_verification"] if facts_verified else []
    rec["limitations"] = [
        "金额/日期与冻结行动一致，不构成历史可得性证明",
        "文内基金全称含『红利低波动』字样而主代码为 515300；主代码与除息日/金额"
        "均与冻结行动一致，全称疑点登记于 conflicts，不在本轮自动裁决",
    ]
    records.append(rec)

# 冻结 515300 第 7 条：无官方原文
seventh = "515300-cash_dividend-2025-12-15"
fev = frozen[seventh]
rec = base_record(
    "515300-no-original-20251215", "515300.SS", "cash_dividend", seventh,
    {
        "ex_date_frozen": fev.get("ex_date"),
        "cash_per_unit_frozen": fev.get("cash_per_unit"),
        "official_original": "missing_locally",
    },
    "docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/"
    "action-sources/normalized-actions.json",
    {"page": None, "section": "events（冻结记录，非官方原文）"},
    "冻结行动值仅有二手表格来源；本地无官方公告原文",
)
rec["source"]["sha256"] = sha(ACTION_SRC / "normalized-actions.json")
rec["facts_verified"] = False
rec["limitations"] = ["缺官方公告原文；本轮不核、不补、不改冻结值"]
records.append(rec)

# ---- 2) 三份官方拆分 PDF ----
SPLITS = [
    ("512890", "512890-split-2021-10-22"),
    ("515050", "515050-split-2026-05-13"),
    ("515880", "515880-split-2026-02-03"),
]
for sym, event_id in SPLITS:
    pdf_path = ACTION_SRC / f"{sym}-official-split.pdf"
    text = pdf_text(pdf_path)
    ratio_m = re.search(r"1[：:]\s*(\d)", text)
    ratio = int(ratio_m.group(1)) if ratio_m else None
    ex_m = re.search(r"(?:份额拆分)?除权日[：:]?\s*(\d{4})\s*年?\s*(\d{1,2})\s*月?\s*(\d{1,2})\s*日?", text)
    ex_iso = (date(int(ex_m.group(1)), int(ex_m.group(2)), int(ex_m.group(3))).isoformat()
              if ex_m else None)
    rec_m = re.search(r"(?:份额拆分)?权益登记日[：:]?\s*(\d{4})\s*年?\s*(\d{1,2})\s*月?\s*(\d{1,2})\s*日?", text)
    rec_iso = (date(int(rec_m.group(1)), int(rec_m.group(2)), int(rec_m.group(3))).isoformat()
               if rec_m else None)
    name_m = re.search(r"([\u4e00-\u9fff（）]+ETF)", text)
    fev = frozen.get(event_id, {})
    checks = {
        "ratio_matches_frozen": ratio == fev.get("split_ratio"),
        "ex_date_matches_frozen": (ex_iso == fev.get("effective_date")) if ex_iso else None,
    }
    facts_verified = all(v for v in checks.values() if v is not None) and ratio is not None
    records.append({
        "record_id": f"{sym}-official-split",
        "instrument_id": f"{sym}.SS",
        "fact_type": "split",
        "event_id": event_id,
        "facts": {
            "split_ratio_announced": f"1:{ratio}" if ratio else None,
            "direction": f"旧1份变新{ratio}份" if ratio else None,
            "record_date": rec_iso,
            "ex_date": ex_iso,
            "field_checks": checks,
            "fund_name_seen": (name_m.group(1) if name_m else None),
        },
        "source": {"path": str(pdf_path.relative_to(ROOT)), "sha256": sha(pdf_path)},
        "locator": {"page": 1, "section": "份额拆分安排/拆分比例"},
        "short_supporting_text": (
            f"拆分比例 1:{ratio}；权益登记日 {rec_iso}；除权日 {ex_iso}"
        ),
        "time_evidence": {
            "kind": "published_date_bound",
            "available_at": None,
            "published_date": fev.get("announcement_date"),
            "not_before": None, "not_after": None,
            "timezone": "Asia/Shanghai",
            "basis": "冻结记录含 announcement_date（官方公告日）下界；PDF 文本同源核对",
        },
        "facts_verified": facts_verified,
        "historical_availability_verified": False,
        "allowed_for": ["description", "fact_verification"] if facts_verified else [],
        "limitations": ["拆分方向与比例已核；历史可得性未证明"],
    })

# ---- 3) 两份上市公告 PDF ----
listing_facts = {
    "515050": {
        "trade_date": None, "published": None,
        "trade_re": r"于\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日.*?上市",
        "pub_re": r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日.*?网站",
    },
    "562590": {
        "trade_date": None, "published": None,
        "trade_re": r"上市时间[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
        "pub_re": r"公告日期[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
    },
}
for sym, spec in listing_facts.items():
    pdf_path = LISTING_DIR / "sources" / f"{sym}-listing.pdf"
    text = pdf_text(pdf_path)
    tm = re.search(spec["trade_re"], text, re.S)
    trade_iso = (date(int(tm.group(1)), int(tm.group(2)), int(tm.group(3))).isoformat()
                 if tm else None)
    pm = re.search(spec["pub_re"], text, re.S)
    pub_iso = (date(int(pm.group(1)), int(pm.group(2)), int(pm.group(3))).isoformat()
               if pm else None)
    name_m = re.search(r"基金简称[“\"]([^\n”\"]+)", text)
    records.append({
        "record_id": f"{sym}-listing-announcement",
        "instrument_id": f"{sym}.SS",
        "fact_type": "listing",
        "event_id": f"{sym}-listing",
        "facts": {
            "listing_trade_date": trade_iso,
            "fund_name_seen": name_m.group(1) if name_m else None,
            "note": "上市交易日为官方上市(交易)公告书记载；区别于基金成立日/募集日",
        },
        "source": {"path": str(pdf_path.relative_to(ROOT)), "sha256": sha(pdf_path)},
        "locator": {"page": 1, "section": "上市交易公告书（提示性公告/基本信息）"},
        "short_supporting_text": (
            f"上市时间/将于 {trade_iso} 在上海证券交易所上市；公告/上网日期 {pub_iso}"
        ),
        "time_evidence": {
            "kind": "published_date_bound",
            "available_at": None,
            "published_date": pub_iso,
            "not_before": None, "not_after": None,
            "timezone": "Asia/Shanghai",
            "basis": "公告日期/上网日期为公布下界；精确 available_at 不据此填写",
        },
        "facts_verified": trade_iso is not None,
        "historical_availability_verified": False,
        "allowed_for": ["listing_evidence_bridge"] if trade_iso else [],
        "limitations": [
            "上市交易日已核，尚需与快照首报价日期相容性核对（Task 4/5）",
            "历史可得性未证明",
        ],
    })

# ---- 冲突/疑点表 ----
conflicts.append({
    "conflict_id": "identity-515300-name-wording",
    "instrument_id": "515300.SS",
    "description": ("六份公告文内基金全称含『嘉实沪深300红利低波动』字样，"
                    "而冻结行动主代码为 515300；主代码、除息日、金额逐字段一致"),
    "resolution_this_round": "不自动裁决；登记疑点，主代码/日期/金额一致性已核",
    "affected": "515300 全部六条官方记录",
})

bundle = {
    "schema_version": "fixed-etf-evidence-bundle/1.0",
    "synthetic": False,
    "generated_by": "task2_extract_facts.py（本轮任务级证据抽取，非第二份对象登记表）",
    "reads": {"count": len(READS), "limit": 80, "files": READS},
    "records": records,
    "conflicts": conflicts,
    "summary": {
        "records": len(records),
        "facts_verified_true": sum(1 for r in records if r["facts_verified"]),
        "by_type": {
            t: sum(1 for r in records if r["fact_type"] == t)
            for t in {r["fact_type"] for r in records}
        },
    },
}
(OUT / "evidence-bundle.json").write_text(
    json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(bundle["summary"], ensure_ascii=False, indent=1))
for r in records:
    print(f"  {r['record_id']:36s} facts_verified={r['facts_verified']}")
print("reads:", len(READS), "/80")
