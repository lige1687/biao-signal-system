#!/usr/bin/env python3
"""Task 2 v2：重抽本地官方原文为证据包（主控复核 §11.5 R3 / §12.4 S3 版）。

相对 v1（evidence-bundle.json，保留不覆盖）的登记修正，全部以原文重读为据：

- 515050 上市公告：published_date 由 2019-10-16（上市日）修正为
  **2019-10-11**——公告原文第 1 页载明"上市交易公告书全文于 2019 年 10 月
  11 日……披露"，落款同为二○一九年十月十一日；上市交易日事实仍是
  2019-10-16。公布日期与事实日期分开登记。
- 512890 拆分结果公告：补齐文内第 1 页的权益登记日 **2021-10-21**、拆分日
  **2021-10-22**（ex_date_matches_frozen 由 null 变 true）；published_date
  由 2021-10-13 修正为**落款 2021-10-25**——第 1 页的 10-13 是另一份先前
  安排公告的发布时间，不能当成本份结果公告的可得时间；并登记该局限。
- 时间证据：kind=in_document_date_bound，逐条登记 date_field/refers_to/
  bound（不晚于/不早于/仅成文）；available_at 一律保持 null。
- 每条已核记录附 fact_binding：抽取输出 + fact_tuple_fingerprint 指纹；
  引用 PDF 哈希与 source_fragments 原文片段锚点一并登记。
- summary 附逐项对账：21 条冻结行动（17 分红+3 拆分+1 停牌）中包内
  10 条（9 有官方原文+1 无原文）、包外 11 条；14 只上市需求中 2 只有
  原文、12 只缺。

用法（S3：产物排他保护，导入本模块不写任何文件）：

    python3 task2_extract_facts_v2.py [--schema 1.1|1.2] [--out-dir DIR]

- ``--schema 1.1``（默认）：v1.1 历史格式（绑定字段不含时间字段），
  用于与被协议引用的正式产物做**逐字节复现对照**；
- ``--schema 1.2``：v1.2 格式——按 REQUIRED_BINDING_FIELDS 把已核时间值
  ``time_evidence.published_date`` 一并纳入绑定与抽取输出（返修 S1）；
- ``--out-dir``（默认：正式目录）：落盘目录。**写入一律排他创建**：
  目标已存在且字节相同 → 记录"复现成功"，不覆盖；已存在且字节不同 →
  失败退出并保留旧文件；不存在 → 创建。
- 包内容与落盘目录无关：fact_binding.extraction_output 始终指向该版本的
  正式（协议引用）位置，因此新目录复现产物可与正式产物逐字节比较。

只读既有来源，不联网；读取次数记账 ≤80。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import pdfplumber

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
OFFICIAL_DIR = ROOT / ("docs/experiments/raw/research-fixed-etf-evidence"
                       "-integration-2026-09-13")
ACTION_SRC = (ROOT / "docs/experiments/raw/research-rotation-clean-2026-09-09"
              "/full-pool-preparation/action-sources")
OFFICIAL_515300 = (ROOT / "docs/experiments/raw/research-rotation-clean-2026-09-09"
                   "/full-pool-preparation/515300-official-qualification")
LISTING_DIR = (ROOT / "docs/experiments/raw/research-mixed-evaluation-2026-09-09"
               "/historical-qualification")

sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research.qualification_bundle import (  # noqa: E402
    fact_tuple_fingerprint,
    validate_evidence_bundle,
)

READS: list[str] = []
CN_DIGITS = {"〇": 0, "○": 0, "O": 0, "0": 0, "一": 1, "二": 2, "三": 3,
             "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(p: Path) -> str:
    return sha_bytes(p.read_bytes())


def read_count(p: Path) -> None:
    READS.append(str(p.relative_to(ROOT)))
    if len(READS) > 80:
        raise RuntimeError("原文读取超出 80 上限")


def pdf_text(p: Path) -> str:
    read_count(p)
    with pdfplumber.open(p) as pdf:
        return "\n".join((pg.extract_text() or "") for pg in pdf.pages)


def write_exclusive(path: Path, text: str) -> str:
    """排他写正式产物（S3）：存在且同字节=复现成功不覆盖；异字节=失败。"""
    data = text.encode("utf-8")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        if path.read_bytes() == data:
            return "reproduced"
        raise SystemExit(
            f"拒绝覆盖内容不一致的既有产物（保留原文件）：{path}") from None
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return "created"


def cn_date_to_iso(text: str) -> str | None:
    """中文数字落款日期（二○一九年十月十一日）→ ISO；解析不了返回 None。"""
    m = re.search(r"([〇○O0一二三四五六七八九十]{4,})年([一二三四五六七八九十"
                  r"〇○O0]{1,3})月([一二三四五六七八九十〇○O0]{1,3})日", text)
    if not m:
        return None
    y_s, m_s, d_s = m.groups()

    def cn_num(s: str) -> int | None:
        if s in ("十",):
            return 10
        if "十" in s:
            a, _, b = s.partition("十")
            tens = CN_DIGITS.get(a) if a else 1
            ones = CN_DIGITS.get(b) if b else 0
            if tens is None or ones is None:
                return None
            return tens * 10 + ones
        if len(s) == 4:  # 年份逐位
            ds = [CN_DIGITS.get(c) for c in s]
            if None in ds:
                return None
            return ds[0] * 1000 + ds[1] * 100 + ds[2] * 10 + ds[3]
        return CN_DIGITS.get(s)

    y, mo, d = cn_num(y_s), cn_num(m_s), cn_num(d_s)
    if None in (y, mo, d):
        return None
    return date(y, mo, d).isoformat()


def build(out_dir: Path, schema: str) -> int:
    READS.clear()  # 读取记账按次运行重置（跨进程/多次生成字节稳定）
    frozen = {
        e["event_id"]: e
        for e in json.loads(
            (ACTION_SRC / "normalized-actions.json").read_text(encoding="utf-8")
        )["events"]
    }

    records: list[dict] = []
    extraction_records: dict[str, dict] = {}
    conflicts: list[dict] = []
    time_bound = schema >= "1.2"  # v1.2：已核时间值纳入绑定（返修 S1）

    def bound_value(rec: dict, field: str):
        if field.startswith("time_evidence."):
            return (rec.get("time_evidence") or {}).get(field.split(".", 1)[1])
        return rec["facts"][field]

    def time_evidence(published: str | None, date_field: str, refers_to: str,
                      bound: str, basis: str) -> dict:
        return {
            "kind": "in_document_date_bound" if published else "unknown",
            "available_at": None,
            "published_date": published,
            "not_before": None, "not_after": None,
            "date_field": date_field if published else None,
            "refers_to": refers_to if published else None,
            "bound": bound if published else None,
            "timezone": "Asia/Shanghai",
            "basis": basis if published else "explicit missing（本地无官方原文）",
        }

    def finalize(rec: dict, bound_fields: list[str]) -> dict:
        """登记抽取输出与事实指纹（已核记录的事实绑定）。"""
        if not rec["facts_verified"]:
            return rec
        entry = {f: bound_value(rec, f) for f in bound_fields}
        extraction_records[rec["record_id"]] = entry
        rec["fact_binding"] = {
            "method": ("task2_extract_facts_v2.py：官方原文（PDF/抽取文本）"
                       "逐字段抽取，与冻结行动独立比对；引用 PDF 哈希与原文"
                       "片段锚点随记录登记"),
            "extraction_output": {
                "path": str((OFFICIAL_DIR / f"task2-extraction-v{schema}.json")
                            .relative_to(ROOT)),
                "sha256": "填于写出后",  # 占位，写出后统一回填
            },
            "fields": bound_fields,
            "fingerprint": fact_tuple_fingerprint(
                rec["instrument_id"], rec["event_id"], rec["fact_type"], entry),
        }
        return rec

    # ---- 1) 515300 六份官方分红公告（抽取文本 + 引用 PDF 双源） ----
    DIV_TEXTS = [
        ("515300_20231214_MO7U", "515300-cash_dividend-2023-12-19"),
        ("515300_20240618_QXY9", "515300-cash_dividend-2024-06-21"),
        ("515300_20240913_SAOV", "515300-cash_dividend-2024-09-20"),
        ("515300_20241128_QVEK", "515300-cash_dividend-2024-12-03"),
        ("515300_20250612_HGW2", "515300-cash_dividend-2025-06-17"),
        ("515300_20250915_NN2J", "515300-cash_dividend-2025-09-18"),
    ]
    DIV_BOUND = ["announcement_sent_date", "cash_per_10_shares_announced",
                 "cash_per_share_computed", "record_date", "ex_date",
                 "pay_date"]
    if time_bound:
        DIV_BOUND = DIV_BOUND + ["time_evidence.published_date"]
    for stem, event_id in DIV_TEXTS:
        txt_path = OFFICIAL_515300 / "sources" / f"{stem}.txt"
        pdf_path = OFFICIAL_515300 / "sources" / f"{stem}.pdf"
        text = txt_path.read_text(encoding="utf-8", errors="replace")
        read_count(txt_path)

        def grab_groups(pattern: str, src: str):
            m = re.search(pattern, src)
            return m.groups() if m else None

        sent_g = grab_groups(
            r"公告送出日期[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
            text)
        sent_iso = (date(int(sent_g[0]), int(sent_g[1]),
                         int(sent_g[2])).isoformat() if sent_g else None)
        sent_frag = (re.search(r"公告送出日期[：:]\s*\d{4}\s*年\s*\d{1,2}\s*月"
                               r"\s*\d{1,2}\s*日", text).group(0)
                     if sent_g else None)
        code = re.search(r"基金主代码\s*(\d{6})", text)
        code = code.group(1) if code else None
        m10 = re.search(r"分红方案.*?）\s*\n?\s*([0-9]+\.[0-9]+)", text, re.S)
        per10 = m10.group(1) if m10 else None
        record_g = grab_groups(
            r"权益登记日\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
        record_iso = (date(int(record_g[0]), int(record_g[1]),
                           int(record_g[2])).isoformat() if record_g else None)
        ex_g = grab_groups(
            r"除息日\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
        ex_iso = (date(int(ex_g[0]), int(ex_g[1]), int(ex_g[2])).isoformat()
                  if ex_g else None)
        pay_g = grab_groups(
            r"现金红利发放日\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
            text)
        pay_iso = (date(int(pay_g[0]), int(pay_g[1]),
                        int(pay_g[2])).isoformat() if pay_g else None)

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
                per10 is not None
                and abs(float(per10) / 10.0
                        - float(fev.get("cash_per_unit", -1))) <= 1e-9
            ),
        }
        facts_verified = all(checks.values())

        rec = {
            "record_id": f"515300-{stem}",
            "instrument_id": "515300.SS",
            "fact_type": "cash_dividend",
            "event_id": event_id,
            "facts": {
                "announcement_sent_date": sent_iso,
                "fund_main_code": code,
                "cash_per_10_shares_announced": per10,
                "cash_per_share_computed": per_share,
                "record_date": record_iso,
                "ex_date": ex_iso,
                "pay_date": pay_iso,
                "field_checks": checks,
            },
            "source": {"path": str(txt_path.relative_to(ROOT)),
                       "sha256": sha(txt_path),
                       "pdf_path": str(pdf_path.relative_to(ROOT)),
                       "pdf_sha256": sha(pdf_path)},
            "locator": {"page": 1,
                        "section": "公告基本信息/与分红相关的其他信息"},
            "short_supporting_text": (
                f"公告送出日期：{sent_iso}；本次分红方案（单位：元/10份基金份额）"
                f"{per10}；除息日 {ex_iso}"),
            "source_fragments": [x for x in (sent_frag,) if x],
            "time_evidence": time_evidence(
                sent_iso, "公告送出日期", "本现金分红公告全文", "not_before",
                "文内『公告送出日期』字段指本公告文件的送出日期：公告内容"
                "不早于该日送出/成文；原文未自证当日完成对外披露，精确公布"
                "时刻未知，available_at 保持 null"),
            "facts_verified": facts_verified,
            "historical_availability_verified": False,
            "allowed_for": (["description", "fact_verification"]
                            if facts_verified else []),
            "limitations": [
                "金额/日期与冻结行动一致，不构成历史可得性证明",
                "文内基金全称含『红利低波动』字样而主代码为 515300；主代码与"
                "除息日/金额均与冻结行动一致，全称疑点登记于 conflicts，"
                "不在本轮自动裁决",
            ],
        }
        read_count(pdf_path)  # 引用 PDF 原件核对（哈希另行登记）
        records.append(finalize(rec, DIV_BOUND))

    # 冻结 515300 第 7 条：无官方原文（保持未核登记）
    seventh = "515300-cash_dividend-2025-12-15"
    fev = frozen[seventh]
    rec = {
        "record_id": "515300-no-original-20251215",
        "instrument_id": "515300.SS",
        "fact_type": "cash_dividend",
        "event_id": seventh,
        "facts": {
            "ex_date_frozen": fev.get("ex_date"),
            "cash_per_unit_frozen": fev.get("cash_per_unit"),
            "official_original": "missing_locally",
        },
        "source": {"path": str((ACTION_SRC / "normalized-actions.json")
                               .relative_to(ROOT)),
                   "sha256": sha(ACTION_SRC / "normalized-actions.json")},
        "locator": {"page": None, "section": "events（冻结记录，非官方原文）"},
        "short_supporting_text": "冻结行动值仅有二手表格来源；本地无官方公告原文",
        "source_fragments": [],
        "time_evidence": time_evidence(None, "", "", "", ""),
        "facts_verified": False,
        "historical_availability_verified": False,
        "allowed_for": [],
        "limitations": ["缺官方公告原文；本轮不核、不补、不改冻结值"],
    }
    records.append(rec)

    # ---- 2) 三份官方拆分 PDF ----
    SPLITS = [
        ("512890", "512890-split-2021-10-22"),
        ("515050", "515050-split-2026-05-13"),
        ("515880", "515880-split-2026-02-03"),
    ]
    SPLIT_BOUND = ["split_ratio_announced", "record_date", "ex_date"]
    if time_bound:
        SPLIT_BOUND = SPLIT_BOUND + ["time_evidence.published_date"]
    for sym, event_id in SPLITS:
        pdf_path = ACTION_SRC / f"{sym}-official-split.pdf"
        text = pdf_text(pdf_path)
        ratio_m = re.search(r"1[：:]\s*(\d)", text)
        ratio = int(ratio_m.group(1)) if ratio_m else None
        ex_m = (re.search(r"(?:份额拆分)?(?:除权日|份额拆分日)[：:]?\s*(\d{4})"
                          r"\s*年?\s*(\d{1,2})\s*月?\s*(\d{1,2})\s*日?", text)
                or re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
                             r"（份额拆分日）", text))
        ex_iso = (date(int(ex_m.group(1)), int(ex_m.group(2)),
                       int(ex_m.group(3))).isoformat() if ex_m else None)
        rec_m = (re.search(r"(?:份额拆分)?权益登记日[：:]?\s*(\d{4})\s*年?\s*"
                           r"(\d{1,2})\s*月?\s*(\d{1,2})\s*日?", text)
                 or re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
                              r"（权益登记日）", text))
        rec_iso = (date(int(rec_m.group(1)), int(rec_m.group(2)),
                        int(rec_m.group(3))).isoformat() if rec_m else None)
        ratio_frag = ratio_m.group(0) if ratio_m else None
        sign_cn = cn_date_to_iso(text)
        sign_m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*$",
                           text.strip())
        if sign_cn:
            sign_iso = sign_cn
            sign_frag = next(
                (x for x in re.findall(
                    r"[〇○O0一二三四五六七八九十]{4,}年[一二三四五六七八九十"
                    r"〇○O0]{1,3}月[一二三四五六七八九十〇○O0]{1,3}日", text)
                 if cn_date_to_iso(x) == sign_iso), None)
        elif sign_m:
            sign_iso = (date(int(sign_m.group(1)), int(sign_m.group(2)),
                             int(sign_m.group(3))).isoformat())
            sign_frag = sign_m.group(0)
        else:
            sign_iso, sign_frag = None, None
        name_m = re.search(r"([\u4e00-\u9fff（）]+ETF)", text)
        fev = frozen.get(event_id, {})
        checks = {
            "ratio_matches_frozen": ratio == fev.get("split_ratio"),
            "ex_date_matches_frozen": (ex_iso == fev.get("effective_date"))
            if ex_iso else None,
            "record_date_from_pdf": rec_iso is not None,
        }
        facts_verified = (
            all(v for v in checks.values() if v is not None)
            and ratio is not None)
        if sym == "512890":
            te = time_evidence(
                sign_iso, "公告落款日期", "本拆分结果公告全文", "not_before",
                "本份为拆分【结果】公告：落款 2021-10-25，内容不早于该日成文；"
                "第 1 页的 2021-10-13 是另一份先前【安排】公告的发布时间，"
                "不属于本文件；除权日前的事前知情依据（先前安排公告原文）"
                "不在本包，本文件不证明拆分安排在 2021-10-22 前已知")
            limitations = [
                "拆分结果（比例/登记日/拆分日）已核；历史可得性未证明",
                "事前知情依据（2021-10-13 发布的先前安排公告）原文缺，"
                "登记于剩余资料清单",
            ]
        else:
            te = time_evidence(
                sign_iso, "公告落款日期", "本份额拆分实施安排公告全文",
                "document_dated",
                "文内落款日期指本公告成文日期；落款早于除权日、与事前安排"
                "公告性质一致，但成文不等于当日完成对外披露，精确公布时刻"
                "未知，available_at 保持 null")
            limitations = ["拆分安排（比例/登记日/除权日）已核；历史可得性未证明"]
        rec = {
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
            "source": {"path": str(pdf_path.relative_to(ROOT)),
                       "sha256": sha(pdf_path)},
            "locator": {"page": 1, "section": "份额拆分安排/拆分比例"},
            "short_supporting_text": (
                f"拆分比例 1:{ratio}；权益登记日 {rec_iso}；除权/拆分日 "
                f"{ex_iso}；落款 {sign_iso}"),
            "source_fragments": [x for x in
                                 (ratio_frag,
                                  rec_m.group(0) if rec_m else None,
                                  ex_m.group(0) if ex_m else None, sign_frag)
                                 if x],
            "time_evidence": te,
            "facts_verified": facts_verified,
            "historical_availability_verified": False,
            "allowed_for": (["description", "fact_verification"]
                            if facts_verified else []),
            "limitations": limitations,
        }
        records.append(finalize(rec, SPLIT_BOUND))

    # ---- 3) 两份上市公告 PDF ----
    listing_bound = ["listing_trade_date"]
    if time_bound:
        listing_bound = listing_bound + ["time_evidence.published_date"]
    for sym, spec in {
        "515050": {
            "trade_re": r"于\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日.*?上市",
        },
        "562590": {
            "trade_re": r"上市时间[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*"
                        r"(\d{1,2})\s*日",
            "pub_re": r"公告日期[：:]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*"
                      r"(\d{1,2})\s*日",
        },
    }.items():
        pdf_path = LISTING_DIR / "sources" / f"{sym}-listing.pdf"
        text = pdf_text(pdf_path)
        tm = re.search(spec["trade_re"], text, re.S)
        trade_iso = (date(int(tm.group(1)), int(tm.group(2)),
                          int(tm.group(3))).isoformat() if tm else None)
        if sym == "515050":
            pub_g = re.search(r"全文于\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*"
                              r"(\d{1,2})\s*日", text)
            pub_iso = (date(int(pub_g.group(1)), int(pub_g.group(2)),
                            int(pub_g.group(3))).isoformat()
                       if pub_g else None)
            sign_iso = cn_date_to_iso(text)
            te = time_evidence(
                pub_iso, "公告落款及全文上网披露日期",
                "本上市交易公告书提示性公告全文", "not_later_than",
                "公告原文载明『上市交易公告书全文于 2019 年 10 月 11 日在本公司"
                "网站……和中国证监会基金电子披露网站……披露』，落款同为"
                f" {sign_iso}：公告内容不晚于 2019-10-11 日终已公开；精确到"
                "时刻的 available_at 不据此填写")
            frag = pub_g.group(0) if pub_g else None
            limitations = [
                "上市交易日 2019-10-16 已核（第 1 页『将于 2019 年 10 月 16 日"
                "在上海证券交易所上市』），区别于成立日/募集日",
                "公布日期 2019-10-11 与上市交易日 2019-10-16 是两个不同日期，"
                "分别登记；历史可得性证明仍归时间资格层",
            ]
        else:
            pm = re.search(spec["pub_re"], text)
            pub_iso = (date(int(pm.group(1)), int(pm.group(2)),
                            int(pm.group(3))).isoformat() if pm else None)
            te = time_evidence(
                pub_iso, "公告日期（文内字段）", "本上市交易公告书",
                "document_dated",
                "文内『公告日期』字段指本公告书成文日期；原文未自证当日完成"
                "对外披露，精确公布时刻未知，available_at 保持 null")
            frag = pm.group(0) if pm else None
            limitations = [
                "上市交易日已核（文内『上市时间』），尚需与快照首报价日期"
                "相容性核对",
                "历史可得性未证明",
            ]
        name_m = re.search(r"基金简称[“\"]([^\n”\"]+)", text)
        rec = {
            "record_id": f"{sym}-listing-announcement",
            "instrument_id": f"{sym}.SS",
            "fact_type": "listing",
            "event_id": f"{sym}-listing",
            "facts": {
                "listing_trade_date": trade_iso,
                "fund_name_seen": name_m.group(1) if name_m else None,
                "note": "上市交易日为官方上市(交易)公告书记载；区别于基金成立日/募集日",
            },
            "source": {"path": str(pdf_path.relative_to(ROOT)),
                       "sha256": sha(pdf_path)},
            "locator": {"page": 1,
                        "section": "上市交易公告书（提示性公告/基本信息）"},
            "short_supporting_text": (
                f"上市时间/将于 {trade_iso} 在上海证券交易所上市；公告/披露日期 "
                f"{pub_iso}"),
            "source_fragments": [frag],
            "time_evidence": te,
            "facts_verified": trade_iso is not None,
            "historical_availability_verified": False,
            "allowed_for": ["listing_evidence_bridge"] if trade_iso else [],
            "limitations": limitations,
        }
        records.append(finalize(rec, listing_bound))

    # ---- 冲突/疑点表（不自动裁决） ----
    conflicts.append({
        "conflict_id": "identity-515300-name-wording",
        "instrument_id": "515300.SS",
        "description": ("六份公告文内基金全称含『嘉实沪深300红利低波动』字样，"
                        "而冻结行动主代码为 515300；主代码、除息日、金额逐字段一致"),
        "resolution_this_round": ("不自动裁决；疑点保留，已核范围仅限主代码/"
                                  "日期/金额"),
        "affected": "515300 全部六条官方记录（对应事实不因已核字段而整体无条件通过）",
    })

    # ---- 抽取输出（事实绑定锚点）先写，供 fact_binding 引用哈希 ----
    extraction_payload = {
        "schema_version": f"task2-extraction/{schema}",
        "generated_by": "task2_extract_facts_v2.py",
        "note": "已核记录的绑定字段取值；证据包 fact_binding.extraction_output 指向本文件",
        "records": extraction_records,
    }
    extraction_text = (json.dumps(extraction_payload, indent=1,
                                  ensure_ascii=False) + "\n")
    extraction_sha = sha_bytes(extraction_text.encode("utf-8"))
    for r in records:
        if "fact_binding" in r:
            r["fact_binding"]["extraction_output"]["sha256"] = extraction_sha

    # ---- 逐项对账（R3：不再混总） ----
    halt = [e for e in frozen.values() if e.get("type") == "trading_halt"]
    in_bundle = {r["event_id"] for r in records if r["fact_type"] != "listing"}
    pool = ["159652.SZ", "510300.SS", "512400.SS", "512890.SS", "513870.SS",
            "515050.SS", "515130.SS", "515170.SS", "515300.SS", "515880.SS",
            "516220.SS", "518850.SS", "562590.SS", "588000.SS"]
    listing_with_original = sorted(
        r["instrument_id"] for r in records if r["fact_type"] == "listing")

    bundle = {
        "schema_version": f"fixed-etf-evidence-bundle/{schema}",
        "synthetic": False,
        "generated_by": ("task2_extract_facts_v2.py（R3 登记修正版；v1.0 包"
                         " evidence-bundle.json 保留不覆盖）"),
        "reads": {"count": len(READS), "limit": 80, "files": READS},
        "records": records,
        "conflicts": conflicts,
        "summary": {
            "records": len(records),
            "facts_verified_true": sum(
                1 for r in records if r["facts_verified"]),
            "published_date_non_null": sum(
                1 for r in records if r["time_evidence"].get("published_date")),
            "by_type": {
                t: sum(1 for r in records if r["fact_type"] == t)
                for t in sorted({r["fact_type"] for r in records})
            },
            "reconciliation": {
                "pool_products": len(pool),
                "listing_needs": len(pool),
                "listing_originals_available": listing_with_original,
                "listing_originals_missing_count": len(pool)
                - len(listing_with_original),
                "frozen_actions_total": len(frozen),
                "frozen_actions_by_type": {
                    t: sum(1 for e in frozen.values() if e.get("type") == t)
                    for t in sorted({e.get("type") for e in frozen.values()})},
                "halt_actions": len(halt),
                "bundle_action_records": len(in_bundle),
                "bundle_action_records_with_official_original": sum(
                    1 for r in records
                    if r["fact_type"] != "listing" and r["facts_verified"]),
                "frozen_actions_in_bundle": len(in_bundle & set(frozen)),
                "frozen_actions_not_in_bundle": sorted(set(frozen) - in_bundle),
            },
        },
    }
    bundle_text = (json.dumps(bundle, indent=1, ensure_ascii=False) + "\n")

    # ---- 排他落盘（S3）：先抽取输出，再证据包 ----
    out_dir.mkdir(parents=True, exist_ok=True)
    outcomes = {}
    for name, text_ in (
            (f"task2-extraction-v{schema}.json", extraction_text),
            (f"evidence-bundle-v{schema}.json", bundle_text)):
        outcomes[name] = write_exclusive(out_dir / name, text_)

    # ---- 自检（仅 v1.2：满足 REQUIRED_BINDING_FIELDS 的新格式） ----
    if time_bound:
        res = validate_evidence_bundle(
            bundle, root=ROOT,
            universe={f"{p[:6]}.SS" if ".SS" in p else p for p in pool})
        status = (f"validated={len(res['validated'])} "
                  f"unresolved={len(res['unresolved'])} "
                  f"rejected={len(res['rejected'])}")
        for r in res["rejected"]:
            status += f"\n  REJ {r['record_id']} {r['reasons'][:2]}"
        if res["rejected"] or len(res["validated"]) != 11:
            print("自检失败：", status, file=sys.stderr)
            return 1
    else:
        status = "v1.1 历史格式复现（不含时间字段绑定，不作新消费格式）"

    print(f"schema={schema} out_dir={out_dir}")
    for name, outcome in outcomes.items():
        print(f"  {name}: {outcome}")
    print(status)
    print(json.dumps(bundle["summary"]["reconciliation"], ensure_ascii=False,
                     indent=1))
    print("reads:", len(READS), "/80")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", choices=("1.1", "1.2"), default="1.1",
                        help="1.1=历史格式复现；1.2=时间值纳入绑定（返修 S1）")
    parser.add_argument("--out-dir", default=None,
                        help="落盘目录（默认正式目录；写入一律排他，"
                             "同字节复现成功不覆盖，异字节拒绝并保留旧文件）")
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir) if args.out_dir else OFFICIAL_DIR
    return build(out_dir, args.schema)


if __name__ == "__main__":
    raise SystemExit(main())
