"""Independent source-field arithmetic; not a scored factor or effect test."""
import hashlib
import json
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parent
BASE = Path(json.loads((RAW / "storage-plan.json").read_text())["output"])
FACTS = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/personal-lowfreq-system-audit-20261018/personal-lowfreq-system-audit-20261018-20261019T005338-7bfb5ca1b315/result/sources/aapl-companyfacts.json")
ADSH = "0000320193-20-000096"
TAG_NAMES = {
    "revenue": "RevenueFromContractWithCustomerExcludingAssessedTax",
    "cost": "CostOfGoodsAndServicesSold",
    "selling_admin": "SellingGeneralAndAdministrativeExpense",
    "interest": "InterestExpense",
    "reported_operating_income": "OperatingIncomeLoss",
    "research_development": "ResearchAndDevelopmentExpense",
    "total_stockholders_equity": "StockholdersEquity",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert sha(FACTS) == "73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43"
    doc = json.loads(FACTS.read_text())["facts"]["us-gaap"]
    chosen = {}
    for name, tag in TAG_NAMES.items():
        values = [
            x for x in doc[tag]["units"]["USD"]
            if x["accn"] == ADSH and x["end"] == "2020-09-26"
            and x.get("start") in (None, "2019-09-29")
        ]
        assert len(values) == 1, (name, values)
        chosen[name] = {"tag": tag, **values[0]}
    values = {k: v["val"] for k, v in chosen.items()}
    numerator = values["revenue"] - values["cost"] - values["selling_admin"] - values["interest"]
    assert values["revenue"] - values["cost"] - values["selling_admin"] - values["research_development"] == values["reported_operating_income"]
    assert numerator - values["reported_operating_income"] == values["research_development"] - values["interest"]
    sub_path = BASE / "fsds-candidate-panel/submissions.csv"
    num_path = BASE / "fsds-candidate-panel/statement-facts.csv"
    assert sha(sub_path) == "065c80c6fe6edae076c2f326770a54b18b0f6e1caccdfb9fc72fb10811ace327"
    assert sha(num_path) == "be3ce99d4c1ab38cd907b5613e6b092b91b6b01cb15400a7b21c9ba7831d1093"
    sub = pd.read_csv(sub_path, dtype=str, keep_default_na=False)
    sub = sub[sub.adsh.eq(ADSH)].to_dict("records")
    assert len(sub) == 1
    num = pd.read_csv(num_path, dtype=str, keep_default_na=False)
    current = num[num.adsh.eq(ADSH) & num.ddate.eq("20200930")]
    matches = {}
    for name, item in chosen.items():
        rows = current[current.tag.eq(item["tag"])]
        vals = {float(x) for x in rows.value if x}
        if vals:
            assert vals == {float(item["val"])}, (name, vals)
        matches[name] = {"fsds_primary_values": sorted(vals), "agrees": vals == {float(item["val"])}}
    assert matches["interest"]["fsds_primary_values"] == []
    result = {
        "purpose": "one annual filing field/period/availability counterexample, no OP score or returns",
        "accession": ADSH,
        "original_period": ["2019-09-29", "2020-09-26"],
        "fsds_period": sub[0]["period"],
        "fsds_num_ddate": "20200930",
        "filed": sub[0]["filed"],
        "accepted_raw_timezone_not_assumed": sub[0]["accepted"],
        "same_accession_companyfacts": chosen,
        "primary_statement_comparison": matches,
        "arithmetic_usd": {
            "revenue_less_cost_less_sga_less_interest": numerator,
            "reported_operating_income": values["reported_operating_income"],
            "difference_explained_by_rd_less_interest": numerator - values["reported_operating_income"],
        },
        "conclusion": "Primary-only FSDS omits this interest fact; a missing field is not zero. Reported operating income is a different formula. FSDS dates are rounded. Common book-equity denominator is not certified; no profitability score constructed.",
        "input_sha256": {str(x): sha(x) for x in [FACTS, sub_path, num_path]},
        "script_sha256": sha(__file__),
        "effect_runs": 0,
    }
    target = RAW / "aapl-source-case.json"
    with target.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"output": str(target), "sha256": sha(target), "arithmetic_usd": result["arithmetic_usd"]}))


if __name__ == "__main__":
    main()
