"""Check one issuer counterexample against the original saved request and response."""
from pathlib import Path
from hashlib import sha256
from decimal import Decimal, ROUND_HALF_UP
import json, re, unicodedata
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
read=lambda n: json.loads((BASE/n).read_text())
checks=[]
def check(name, ok, evidence): checks.append({"name":name,"passed":bool(ok),"evidence":evidence})
norm=lambda t:re.sub(r"[\s\x00]+", "", unicodedata.normalize("NFKC", t))
bindings=read("saved-input-bindings.json")
for b in bindings: check("unchanged:"+Path(b["path"]).name,sha256((ROOT/b["path"]).read_bytes()).hexdigest()==b["sha256"],b["path"])
f=read("qualified-facts.json"); texts={}
for s in read("source-manifest.json")["sources"]:
    check(s["id"]+":source_hash",sha256((ROOT/s["raw_path"]).read_bytes()).hexdigest()==s["raw_sha256"],s["raw_path"])
    check(s["id"]+":text_hash",sha256((ROOT/s["text_path"]).read_bytes()).hexdigest()==s["text_sha256"],s["text_path"])
    texts[s["id"]]=norm((ROOT/s["text_path"]).read_text())
check("issuer_notice_amount", all(x in texts["issuer-html"] for x in ["601989",f["announcement_id"],"A股每股现金红利0.003元","含税"]),"issuer-html")
check("date_row", "A股2022/8/22-2022/8/232022/8/23" in texts["issuer-page"],"issuer original PDF A-share row")
gross=(Decimal(f["total_shares"])*Decimal(f["cash_per_share_cny_gross"])).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
check("gross_cash_recomputed", gross==Decimal(f["announced_total_cash_cny_gross"]) and f"{gross:,.2f}" in texts["issuer-html"],str(gross))
b=ROOT/"docs/experiments/raw/b02-targeted-gap-batch-2026-10-05/run-01"
d=json.loads((b/"raw/factor-2-sh-601989-client-decoded.json").read_text())
n=json.loads((b/"normalized/factor/factor-2-sh-601989.json").read_text())
w=(b/"raw/factor-2-sh-601989-wire.bin").read_bytes()
p=(b/"raw/factor-2-sh-601989-client-decoded-protocol.txt").read_bytes()
request=(b/"raw/factor-2-sh-601989-request-wire.bin").read_bytes()
expected_request={"code":"sh.601989","start_date":f["fixed_query_start"],"end_date":f["fixed_query_end"]}
check("original_request_window",d["request"]==expected_request and all(v.encode() in request for v in expected_request.values()),d["request"])
check("successful_saved_response",d["error_code"]=="0" and d["response_completed_and_decoded"] is True,"success does not establish event completeness")
check("raw_and_protocol_bytes_equal",w==p,"this saved wire response is plaintext and identical to decoded-protocol")
record=json.loads(next(x for x in p.decode().split("\x01") if x.startswith('{"record":')))["record"]
check("original_rows_not_lost_by_normalization",record==d["rows"] and [dict(zip(d["fields"],row)) for row in record]==n["records"],"raw protocol, client serialization, normalized records")
dates=[row[d["fields"].index("dividOperateDate")] for row in record]
check("saved_two_dates",dates==f["fixed_query_saved_event_dates"],dates)
check("official_event_inside_request_but_absent",f["fixed_query_start"]<=f["ex_date"]<=f["fixed_query_end"] and f["ex_date"] not in dates,"incomplete dated cash-dividend coverage established for this fixed response")
check("limits_preserved",all(f[k] is False for k in ["complete_dividend_event_coverage","actual_account_credit_verified","original_inputs_modified","old_sina_price_repaired"]),"does not establish cause or cumulative factor arithmetic")
result={"status":"passed" if all(c["passed"] for c in checks) else "failed","passed":sum(c["passed"] for c in checks),"total":len(checks),"checks":checks,"scientific_result":"fixed response is not a complete dividend-event inventory","independent_agent_review":False,"labels":0,"fits":0}
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(0 if result["status"]=="passed" else 1)
