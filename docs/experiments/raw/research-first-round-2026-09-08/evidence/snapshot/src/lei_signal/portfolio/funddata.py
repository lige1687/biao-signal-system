"""持仓基金外部数据抓取（天天基金/东财公开接口）。

三个能力，全部带 UA/Referer 与轻量限速（东财高并发会临时封禁，运维手册
已有先例），解析为纯数据结构返回，不做任何落库（落库在调用方）：

1. search_fund_code(name)：基金名称 -> 候选代码列表（模糊搜索）
2. fetch_nav_history(code)：单位净值历史（最近 N 天，倒序）
3. fetch_nav_full(code)：成立以来全量净值（单位/累计/当日增长率，画图用）
4. fetch_top10_holdings(code)：最新季报前十大持仓 + 市场分类

接口口径（2026-09-04 实测）：
- 搜索  fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx
- 净值  api.fund.eastmoney.com/f10/lsjz（JSON，LSJZList[].DWJZ/FSRQ）
- 持仓  fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc（JS 套 HTML
  表格，一行 = [序号, 代码, 名称, --, --, 股吧行情, 占净值%, 持股数(百万),
  市值(百万)]；返回体含同年多个季度段，取第一段 = 最新季报）
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
_THROTTLE_SEC = 0.8  # 请求间隔；东财封禁阈值未知，保守取 <1s

_last_request_at = 0.0


def _get(url: str, referer: str | None = None) -> str:
    global _last_request_at
    wait = _THROTTLE_SEC - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    if referer:
        req.add_header("Referer", referer)
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    _last_request_at = time.monotonic()
    return body


# ── 名称规范化（对齐东财命名与截图口感的差异） ─────────────────────

_STRIP_TOKENS = (
    "人民币", "(QDII-LOF)", "(QDII-FOF)", "(QDII-ETF)", " ", "　",
)


def normalize_fund_name(name: str) -> str:
    """去掉影响匹配的修饰词，保留 A/C 份额字母（份额不同代码不同，不能丢）。"""
    out = name
    for token in _STRIP_TOKENS:
        out = out.replace(token, "")
    return out.strip()


def search_fund_code(name: str) -> list[dict]:
    """名称模糊搜索 -> [{code, name}]，按返回顺序（相关性）。

    CATEGORYDESC=基金 的才是基金本体；指数/股票混在搜索结果里要滤掉。
    """
    url = (
        "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx"
        f"?m=1&key={urllib.parse.quote(name)}"
    )
    raw = _get(url)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    out: list[dict] = []
    for item in payload.get("Datas", []):
        if item.get("CATEGORYDESC") != "基金":
            continue
        code, cname = item.get("CODE"), item.get("NAME")
        if code and cname:
            out.append({"code": str(code), "name": str(cname)})
    return out


def match_fund_code(name: str) -> tuple[str, str] | None:
    """名称 -> (code, 东财全名)。规范名精确等值优先，其次互为包含。

    匹配失败返回 None，不猜（宁可待补不可错绑——错绑代码会让净值/持仓
    全错）。
    """
    target = normalize_fund_name(name)
    for cand in search_fund_code(target):
        cand_norm = normalize_fund_name(cand["name"])
        if cand_norm == target:
            return cand["code"], cand["name"]
    for cand in search_fund_code(target):
        cand_norm = normalize_fund_name(cand["name"])
        if target in cand_norm or cand_norm in target:
            return cand["code"], cand["name"]
    return None


# ── 净值 ────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class NavPoint:
    date: str      # YYYY-MM-DD
    unit_nav: float


def fetch_nav_history(code: str, page_size: int = 40) -> list[NavPoint]:
    """单位净值历史，最新在前。QDII 净值 T+1~T+2 发布，缺日属正常。"""
    url = (
        "http://api.fund.eastmoney.com/f10/lsjz"
        f"?fundCode={urllib.parse.quote(code)}&pageIndex=1&pageSize={page_size}"
    )
    raw = _get(url, referer="http://fund.eastmoney.com/")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    out: list[NavPoint] = []
    for row in payload.get("Data", {}).get("LSJZList", []):
        date, dwjz = row.get("FSRQ"), row.get("DWJZ")
        if not date or not dwjz:
            continue
        try:
            out.append(NavPoint(date=date, unit_nav=float(dwjz)))
        except (TypeError, ValueError):
            continue
    return out


# ── 全历史净值（pingzhongdata，一次请求拿成立以来全量） ─────────────

@dataclass(frozen=True, slots=True)
class FundNavFull:
    code: str
    name: str                    # 东财官方基金名
    dates: list[str]             # YYYY-MM-DD，升序
    unit_nav: list[float]        # 单位净值（分红除息日会人为跳水）
    acc_nav: list[float]         # 累计净值（分红加回，看长期涨跌幅用它）
    day_pct: list[float | None]  # 当日净值增长率 %（东财 equityReturn 口径）


_NAME_RE = re.compile(r'fS_name\s*=\s*"([^"]+)"')
_NET_WORTH_RE = re.compile(r"Data_netWorthTrend\s*=\s*(\[.*?\]);", re.S)
_ACC_WORTH_RE = re.compile(r"Data_ACWorthTrend\s*=\s*(\[.*?\]);", re.S)


def _ms_to_date(ms: int) -> str:
    """东财净值时间戳是北京时间零点（如 1536076800000 -> 2018-09-05）。"""
    return datetime.fromtimestamp(ms / 1000, tz=timezone(timedelta(hours=8))).strftime(
        "%Y-%m-%d")


def parse_pingzhong_body(code: str, raw: str) -> FundNavFull | None:
    """解析 fund.eastmoney.com/pingzhongdata/{code}.js 响应体（纯函数，供单测）。

    主序列取 Data_netWorthTrend（单位净值 + 当日增长率），Data_ACWorthTrend
    按时间戳合并进同一条日期轴；两边都缺的日期只保留单位净值侧。
    """
    m_name = _NAME_RE.search(raw)
    m_net = _NET_WORTH_RE.search(raw)
    m_acc = _ACC_WORTH_RE.search(raw)
    if not (m_name and m_net):
        return None
    try:
        net_rows = json.loads(m_net.group(1))
        acc_rows = json.loads(m_acc.group(1)) if m_acc else []
    except json.JSONDecodeError:
        return None
    acc_by_ms: dict[int, float] = {}
    for row in acc_rows:
        try:
            acc_by_ms[int(row[0])] = float(row[1])
        except (TypeError, ValueError, IndexError):
            continue
    dates: list[str] = []
    unit_nav: list[float] = []
    acc_nav: list[float] = []
    day_pct: list[float | None] = []
    for row in net_rows:
        try:
            ms, nav = int(row["x"]), float(row["y"])
        except (KeyError, TypeError, ValueError):
            continue
        ret = row.get("equityReturn")
        try:
            ret_val = float(ret) if ret not in ("", None) else None
        except (TypeError, ValueError):
            ret_val = None
        acc = acc_by_ms.get(ms)
        if acc is None:
            continue  # 累计净值缺行（极早期数据）——该日两条线都无法对齐，跳过
        dates.append(_ms_to_date(ms))
        unit_nav.append(nav)
        acc_nav.append(acc)
        day_pct.append(ret_val)
    if not dates:
        return None
    return FundNavFull(
        code=code, name=m_name.group(1),
        dates=dates, unit_nav=unit_nav, acc_nav=acc_nav, day_pct=day_pct,
    )


def fetch_nav_full(code: str) -> FundNavFull | None:
    """成立以来全量净值（单位 + 累计 + 当日增长率），一次请求。

    lsjz 分页接口单页只回 20 行，拼一年历史要十几个请求；pingzhongdata
    一个请求给全量，适合画图。失败/无数据返回 None，不猜。
    """
    raw = _get(
        f"http://fund.eastmoney.com/pingzhongdata/{urllib.parse.quote(code)}.js",
        referer="http://fund.eastmoney.com/",
    )
    return parse_pingzhong_body(code, raw)


# ── 季报前十大持仓 ─────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class FundStockHolding:
    stock_code: str
    stock_name: str
    market: str          # cn / hk / us / other
    weight_pct: float    # 占基金净值 %


def classify_market(stock_code: str) -> str:
    """按代码形态分类市场：6 位数字=A股，5 位数字=港股，含字母=美股。"""
    code = stock_code.strip()
    if code.isdigit():
        if len(code) == 6:
            return "cn"
        if len(code) == 5:
            return "hk"
        return "other"
    if re.fullmatch(r"[A-Za-z.]+", code):
        return "us"
    return "other"


_ROW_CELLS_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_QUARTER_RE = re.compile(r"(\d{4})年(\d)季度股票投资明细")
_DATE_RE = re.compile(r"截止至：<font[^>]*>([\d-]+)</font>")


def fetch_top10_holdings(
    code: str, *, year: int | None = None, quarter: int | None = None
) -> tuple[str, str, list[FundStockHolding]] | None:
    """最新（或指定）季报前十大 -> (report_quarter, report_date, rows)。

    返回体同年多季度连排，第一段即最新；无持仓数据的基金（债基等）
    返回 None。
    """
    params = f"type=jjcc&code={urllib.parse.quote(code)}&topline=10"
    if year:
        params += f"&year={year}"
        if quarter:
            params += f"&month={quarter * 3}"
    raw = _get(
        f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx?{params}",
        referer="http://fundf10.eastmoney.com/",
    )
    m = _QUARTER_RE.search(raw)
    d = _DATE_RE.search(raw)
    if not m or not d:
        return None
    report_quarter = f"{m.group(1)}Q{m.group(2)}"
    report_date = d.group(1)
    # 只取第一段（最新季度）：按季度标题切分
    sections = _QUARTER_RE.split(raw)
    # split 后: [前缀, y1, q1, 段1, y2, q2, 段2, ...]；段1 是 3 个捕获组之后
    first_section = sections[3] if len(sections) > 3 else raw
    rows: list[FundStockHolding] = []
    for tr in re.findall(r"<tr>(.*?)</tr>", first_section, re.S):
        cells = [_TAG_RE.sub("", c).strip() for c in _ROW_CELLS_RE.findall(tr)]
        # [序号, 代码, 名称, --, --, 股吧行情, 占净值%, 持股数, 市值]
        if len(cells) < 7 or not cells[1]:
            continue
        try:
            weight = float(cells[6].rstrip("%"))
        except (TypeError, ValueError):
            continue
        stock_code = cells[1].strip()
        rows.append(FundStockHolding(
            stock_code=stock_code,
            stock_name=cells[2],
            market=classify_market(stock_code),
            weight_pct=weight,
        ))
    if not rows:
        return None
    return report_quarter, report_date, rows
