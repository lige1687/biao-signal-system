"""Qualify the existing reference display; never alter saved returns or infer costs."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[4]
D=Path(__file__).resolve().parent
REL=Path("web/public/research/us-factor-reference-curves-20261022/index.html")
old=(D/"previous-index.html").read_text()
s=old.replace("<title>美股公开因子组合累计曲线</title>","<title>美股因子 · 净超额收益核验</title>")
s=s.replace("<h1>美股公开因子组合累计曲线</h1>","<h1>美股因子 · 净超额收益核验</h1>")
s=s.replace('<p class="lead">展示三种公开分组中，低分组、中间组、高分组和三组平均的月度收益连乘路径。只呈现已有组合结果，不代表逐股选股或个人账户回测。</p>', '<p class="lead">收益评价须对齐事先指定的母指数或被动投资基准，并扣个人交易费用。当前公开组合资料缺少所需成本和基准绑定，净超额收益尚未评价。</p>')
panel="""<section class="card net-status" aria-label="净超额收益资格">
<h2>净超额收益：未评价</h2>
<ul><li><strong>对应母指数／被动基准：</strong>尚未绑定。原B是三组资金分配参照。</li><li><strong>个人交易费用：</strong>缺组合成交／换手资料与适用账户费表，无法从公开月收益还原。</li><li><strong>前向市场状态效果：</strong>尚未测试。先冻结只用当时可得资料的规则，再评价后续结果。</li></ul>
<p>缺项期间不提供数值净收益或净超额；已有毛收益仅作下方文献参考。</p>
<a href="http://localhost:5188/library?report=docs%2Fexperiments%2Fnet-excess-forward-requirements-2026-10-23.md">查看口径与前向试验状态</a>
</section>
<details class="gross-reference"><summary>展开文献毛收益参考（未扣个人费用）</summary>
"""
s=s.replace('<section class="card">',panel+'<section class="card">',1)
s=s.replace('</main>','</details></main>',1)
s=s.replace('</style>','.net-status{border-color:#d2a852;margin-bottom:20px;background:#fffdf7}.net-status h2{margin:0 0 12px;font-size:23px}.net-status ul{padding-left:20px}.net-status li{margin:9px 0}.net-status p{color:#72591f}.gross-reference>summary{cursor:pointer;padding:14px 0;font-weight:650;color:#445671}.gross-reference:not([open])>.card{display:none}</style>',1)
s=s.replace('四个公开组合的月末累计净值曲线','四个公开组合的月末累计毛收益，未扣个人费用')
s=s.replace('期初净值 100','期初累计值 100')
s=s.replace('期间累计涨跌（旧统计）','期间毛收益（未扣个人费用）')
s=s.replace('三组平均 B','三组分配参照 B')
s=s.replace('高分组的旧比较（每月差额）：','高分组相对分配参照的毛收益差额：')
s=s.replace('月末净值','月末累计值')
s=s.replace('基准 B 每月资金','分配参照 B 每月资金')
(ROOT/REL).write_text(s)
assert 'net-status' in s and '<details class="gross-reference">' in s
receipt={"revision":"2026-10-23-net-excess-qualification","before_sha256":hashlib.sha256(old.encode()).hexdigest(),"after_sha256":hashlib.sha256(s.encode()).hexdigest(),"numeric_saved_data_unchanged":True,"net_returns_estimated":False,"default":"netexcess_unavailable; gross_reference_collapsed"}
(D/"display-revision.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n")
