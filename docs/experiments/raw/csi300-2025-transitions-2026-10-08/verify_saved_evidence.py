"""Read-only qualification of two named CSI300 replacements against frozen candidates."""
from pathlib import Path
from hashlib import sha256
import json, re
import pandas as pd
import openpyxl
from bs4 import BeautifulSoup
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
read=lambda n:json.loads((BASE/n).read_text())
checks=[]
def check(name,ok,evidence):checks.append({"name":name,"passed":bool(ok),"evidence":evidence})
manifest=read("source-manifest.json");sources={s["id"]:s for s in manifest["sources"]}
for sid,s in sources.items():check(sid+":source_hash",sha256((ROOT/s["raw_path"]).read_bytes()).hexdigest()==s["raw_sha256"],s["raw_path"])
bindings=read("saved-input-bindings.json")
for b in bindings:check(Path(b["path"]).name+":unchanged",sha256((ROOT/b["path"]).read_bytes()).hexdigest()==b["sha256"],b["path"])
frame=pd.read_parquet(ROOT/bindings[0]["path"])
facts=read("qualified-facts.json");saved=read("candidate-comparison.json");expected_rows=[]
for e in facts["events"]:
 sid=f"notice-{e['notice_id']}";notice=json.loads((ROOT/sources[sid]["raw_path"]).read_text())["data"]
 content=BeautifulSoup(notice["content"],"html.parser").get_text("",strip=True)
 check(e["id"]+":notice_identity",notice["id"]==e["notice_id"] and notice["publishDate"]==e["index_publication_date"] and notice["contentSource"]=="中证指数有限公司","official notice metadata")
 check(e["id"]+":conditional_effective",f"自{e['removed_name']}退市日起" in content and "沪深300" in content,"effective condition is not bare inferred corporate date")
 attachment=next(x for x in notice["enclosureList"] if x["fileUrl"]==sources[sid+"-adjustments"]["url"])
 check(e["id"]+":attachment_binding",attachment["noticeId"]==e["notice_id"] and attachment["createAt"]==e["attachment_created_date"],"creation date does not replace publication date")
 wb=openpyxl.load_workbook(ROOT/sources[sid+"-adjustments"]["raw_path"],read_only=True,data_only=True)
 rows=[row for sh in wb for row in sh.values if str(row[0]).zfill(6)=="000300"]
 check(e["id"]+":exact_index_removal_addition",rows==[("000300","沪深300",e["removed_code"],e["removed_name"],e["added_code"],e["added_name"])],rows)
 term=sources[e["termination_source"]];text=BeautifulSoup((ROOT/term["raw_path"]).read_bytes(),"html.parser").get_text("",strip=True)
 y,m,d=e["official_effective_date"].split("-");date=f"{y}年{int(m)}月{int(d)}日"
 check(e["id"]+":exchange_condition_resolution",e["removed_name"] in text and (f"自{date}起终止其股票在本所上市交易" in text) and term["public_document_date"]==e["termination_publication_date"],term["raw_path"])
 check(e["id"]+":publication_time_boundary",e["sufficient_public_document_day"]==max(e["index_publication_date"],e["termination_publication_date"])<e["official_effective_date"] and e["earliest_exact_public_timestamp"] is None and e["vendor_historical_arrival"] is None,"sufficient known document day, not earliest or intraday availability")
 sub=frame[(frame.date>=e["source_date_window"][0])&(frame.date<=e["source_date_window"][1])]
 observed=[]
 for date,group in sub.groupby("date"):
  day=str(date.date());codes=set(group.symbol);active=day>=e["official_effective_date"];old=e["removed_code"] in codes;new=e["added_code"] in codes
  row={"event_id":e["id"],"date":day,"candidate_total_rows":len(group),"candidate_unique_codes":len(codes),"old_code":e["removed_code"],"old_present_in_candidate":old,"old_expected_from_qualified_event":not active,"new_code":e["added_code"],"new_present_in_candidate":new,"new_expected_from_qualified_event":active,"pair_status_differences":int(old!=(not active))+int(new!=active),"baseline_note":"pre-effective pair baseline and candidate transition boundary only; other298 members not certified"};expected_rows.append(row);observed.append(row)
 check(e["id"]+":candidate_transition_pair",[r["date"] for r in observed if r["new_present_in_candidate"] and not r["old_present_in_candidate"]]==[e["candidate_transition_date"]],"fixed window includes before and transition dates")
 check(e["id"]+":mismatch_dates_and_count",[r["date"] for r in observed if r["pair_status_differences"]]==e["candidate_mismatched_dates"] and sum(r["pair_status_differences"] for r in observed)==e["candidate_pair_status_differences"],e["candidate_mismatched_dates"])
check("all_nine_observed_rows_recomputed",expected_rows==saved["rows"] and len(expected_rows)==9,"not recomputing market signals")
check("five_dates_ten_pair_status_errors",sum(bool(r["pair_status_differences"]) for r in expected_rows)==saved["mismatch_dates"]==5 and sum(r["pair_status_differences"] for r in expected_rows)==saved["pair_status_differences"]==10,"5 stale included rows plus5 missing included rows")
check("300_counts_do_not_prove_membership_correct",all(r["candidate_unique_codes"]==r["candidate_total_rows"]==300 for r in expected_rows),"candidate counts all300 despite wrong pair on5dates")
check("not_full_chain_or_repair",facts["initial_complete_anchor_available"] is False and facts["full_chain_complete"] is False and facts["all_other_members_verified"] is False and facts["membership_repairs"]==0 and saved["membership_modified"] is False,"bounded source qualification only")
ledger=read("request-ledger.json")
check("inherited_source_budget_not_reset",ledger["inherited_membership_cumulative_bytes"]==ledger["inherited_membership_prior_bytes"]+ledger["raw_response_bytes"]<=ledger["inherited_membership_byte_limit"],"old acquisition costs carried forward")
result={"status":"passed" if all(c["passed"] for c in checks) else "failed","passed":sum(c["passed"] for c in checks),"total":len(checks),"checks":checks,"independent_agent_review":False,"labels":0,"fits":0,"membership_repairs":0,"price_repairs":0}
print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result["status"]=="passed" else 1)
