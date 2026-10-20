"""Record the controller's complete reading; no title or keyword auto-approval."""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
packet_path = HERE / "review-packet.json"
assert hashlib.sha256(packet_path.read_bytes()).hexdigest() == "b1c077a57c70560791d7752094b497b5d23657d90d0ce77a4cc0977dffc78e46"
packet = json.loads(packet_path.read_text())
# These decisions were made after reading every page. The mapping is an auditable
# record, not a rule that may classify future notices by their title.
approved = {
    0: ("unrelated_business", "只改担保方名称、土地编号和监事会日期；未改年度四项金额。",
        [(1, "因“中信信"), (2, "因遗漏了会议召开时间")]),
    2: ("unrelated_business", "说明项目工艺与四项商业风险；没有重述年度资产、收入、成本或经营现金。",
        [(1, "有关事项补充说明如下"), (2, "4、原材料价格波动风险")]),
    3: ("cleared", "回购前后总股数不变，更正的是限售和非限售分类。此决定仅放行年度盈利字段，股份/流通股研究必须采用更正版本。",
        [(2, "总股本 648,299,953 100 8,564,544 639,735,409 100"), (2, "除上述内容外，原公告其他内容不变")]),
    5: ("cleared", "更正可转债股数变化的起始日和期间数量，年末总数不变。未改年度四项金额，不据此放行股份变化研究。",
        [(1, "相关数据未按规定时间填写"), (1, "除上述更正内容外，原公告其他内容不变")]),
    6: ("cleared", "理财产品到期年份2023改2024；本金、已取得收益和赎回状态未变。仅说明这份公告没有改年度四项金额，期限风险仍真实存在。",
        [(1, "“理财期限”日期输入错误"), (3, "除上述更正内容外，原公告中的其他内容不变")]),
    7: ("unrelated_business", "财务资助需再经股东大会批准，改的是审批要求；不是修订已公布年度报表。",
        [(1, "在董事会审议通过后还需提交公司股东大会审"), (1, "其他内容")]),
    8: ("unrelated_business", "股价异常波动把跌幅改涨幅，不涉及四项会计字段；价格事件分析应保留这项更正。",
        [(1, "收盘价格涨幅偏离值累计超过"), (1, "其他内容均保持不变")]),
    10: ("unrelated_business", "更正合资方名称，注册资本5000万元及公司45%持股均不变；没有更改年度报表数。",
         [(1, "珠海航空城发展集团有限公司持有其 55%的股权"), (1, "除上述内容更正外")]),
    11: ("unrelated_business", "股东大会网络投票起始年份2016改2017，不改会计数。",
         [(1, "“网络投票"), (1, "原公告内容不变")]),
    14: ("unrelated_business", "业绩说明会改网络举办地址，全部三页仅是参会安排，未修订财务金额。",
         [(1, "原公告中业绩说明会召开的地点有误"), (1, "除上述更正内容外，公告中的其他内容不变")]),
    15: ("unrelated_business", "补充通信网络合作内容与公司判断，未更正年度数值；不把公司的无影响判断当未来结果保证。",
         [(1, "对公司 2019 年度财务状况、经营业绩不构成影响")]),
    16: ("unrelated_business", "只更正股东大会互联网投票起始年份，其他内容不变。",
         [(1, "互联网投票系统进行网络投票的时间标注错误"), (1, "除上述更正内容外")]),
    18: ("unrelated_business", "补充股东个人质押与业绩承诺补偿安排，提及承诺数不等于修改年度实际数；保留质押和履约风险。",
         [(1, "因股东质押股份涉及重大资产重组业绩承诺股份补偿"), (2, "将对以上盈利承诺未实现数")]),
}
pending = {
    1: "2016预盈补充投资收益和政府补助；不是普通业务文字。先核对应年度正式报表与预告范围，不能用未审计预告替代报表。",
    4: "2020收入预测及退市警示标准，保留收入口径和正式年报对接待核状态。",
    9: "2020收入、游戏项目费用化、资产减值及金融工具估值变化。不能仅因标题为预告而清除相关财务风险。",
    12: "2015会计估计生效日变化明确影响当年利润；虽称不用追溯旧年度，仍需核2015及后续年度字段影响。",
    13: "2018盈利预测把总额误写成增加数。正式年度字段是否已经消除对应疑问，需要绑定实际正式报表。",
    17: "2023扣非净利润预测上限减少4500万元；不直接推断年度资产、成本和现金均不受影响。",
    19: "2018年报补充理财89280万元、薪酬增加和支付、往来款细项；应读取同日更正年报作逐字段比较，不能整份放行。",
}
assert set(approved) | set(pending) == set(range(20))
decisions, held, extraction = [], [], []
for index, row in enumerate(packet["selected"]):
    source = row["source"]["source_identity"]
    text_binding = row["prepared"]["notice_text"]
    source_bytes = Path(source["path"]).read_bytes()
    assert hashlib.sha256(source_bytes).hexdigest() == source["sha256"]
    assert hashlib.sha256(Path(text_binding["path"]).read_bytes()).hexdigest() == text_binding["sha256"]
    saved = json.loads(Path(text_binding["path"]).read_text())
    fresh = PdfReader(source["path"])
    assert len(fresh.pages) == len(saved)
    normalize = lambda value: re.sub(r"\s+", "", value)
    page_checks = [normalize(page.extract_text()) == normalize(saved[i]["text"])
                   for i, page in enumerate(fresh.pages)]
    assert all(page_checks), (index, "saved text differs from independent PDF extraction")
    extraction.append({"code": row["code"], "announcement_id": row["announcement_id"],
                       "pages": len(saved), "all_pages_match": all(page_checks),
                       "source_sha256": source["sha256"],
                       "notice_text_sha256": text_binding["sha256"]})
    common = {"cohort_code": row["code"], "announcement_id": row["announcement_id"],
              "publication_date": row["queue"]["publication_date"],
              "source_sha256": source["sha256"], "notice_text_path": text_binding["path"],
              "notice_text_sha256": text_binding["sha256"], "pages_read": list(range(1, len(saved) + 1))}
    if index not in approved:
        held.append({**common, "controller_accepted": False, "reason": pending[index]})
        continue
    disposition, basis, quotes = approved[index]
    for page, quote in quotes:
        assert quote in saved[page - 1]["text"], (index, page, quote)
    decisions.append({
        **common, "controller_accepted": True, "disposition": disposition,
        "affected_years": None, "affected_fields": None, "continuing_scope": "cleared",
        "whole_notice_cleared": True, "root_basis": basis,
        "evidence": [{"page": page, "exact_quote": quote} for page, quote in quotes],
        "review_scope": "Only this exact notice's relevance to annual assets/revenue/cost/CFO. Not a company-wide risk clearance, nor permission for value/share/event factors.",
    })
review = {"schema": "financial-notice-review/1", "reviewer": "root; complete text and independently extracted original PDF",
          "created_at": datetime.now().astimezone().isoformat(),
          "decisions": decisions, "held_outside_applied_decisions": held,
          "independent_pdf_text_checks": extraction,
          "selected_count": 20, "market_outcomes_read": False,
          "source_packet_sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest()}
with (HERE / "controller-notice-review.json").open("x") as stream:
    json.dump(review, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps({"accepted": len(decisions), "held": len(held),
                  "independent_pdf_pages": sum(item["pages"] for item in extraction)}))
