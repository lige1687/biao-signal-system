"""B站 UP主投稿源：wbi 签名 + cookie 持久化 + CC/AI 字幕抓取。

2026-08-27 实测结论（探针脚本）：
- ``x/space/wbi/arc/search`` 必须带 wbi 签名 + buvid3 cookie，否则 -352 风控；
- 匿名请求连续过快会触发 IP 级风控（连正确签名也 -352），恢复需等待；
  → 请求间隔 ≥2s、cookie 落盘跨日复用、-352 退避 30s 重试 1 次；
- ``x/web-interface/view`` 免签名取 cid；
- ``x/player/wbi/v2`` 的 AI 字幕（ai_zh）匿名不可见，配 ``BILI_SESSDATA``
  后可见（降级路径：无字幕用标题+简介）。
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests

from lei_signal.newsfeed.models import NewsItem
from lei_signal.newsfeed.normalize import compute_dedupe_key
from lei_signal.newsfeed.sources import NewsSourceError

_MIXIN_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61,
    26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20,
    34, 44, 52,
]

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

#: 请求间隔（秒）：匿名态防 -352 的关键约束，勿调小。
_SLEEP = 2.0
#: -352 / 非 JSON 风控响应的退避重试。
_RETRY_BACKOFF = 30.0

_SUBTITLE_MAX_CHARS = 20000


def extract_mixin_key(img_url: str, sub_url: str) -> str:
    """从 nav 返回的 wbi_img URL 提取 32 位 mixin key（打乱重排取前 32）。"""
    img = img_url.rsplit("/", 1)[1].split(".")[0]
    sub = sub_url.rsplit("/", 1)[1].split(".")[0]
    return "".join((img + sub)[i] for i in _MIXIN_TAB)[:32]


def _ts_to_iso(seconds: int) -> str:
    return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone().isoformat(
        timespec="seconds"
    )


class BilibiliClient:
    """带 cookie 持久化与 wbi 签名的最小客户端。"""

    def __init__(self, cookie_path: Path, sessdata: str | None = None) -> None:
        self._cookie_path = Path(cookie_path)
        self._cookie_path.parent.mkdir(parents=True, exist_ok=True)
        self._sessdata = (sessdata or "").strip()
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": _UA, "Referer": "https://www.bilibili.com/"}
        )
        self._mixin_key: str | None = None
        self._ensure_session()

    # ---------------- session / cookie ----------------

    def _ensure_session(self) -> None:
        self._load_cookies()
        if self._sessdata:
            self._session.cookies.set("SESSDATA", self._sessdata, domain=".bilibili.com")
        if "buvid3" not in self._session.cookies:
            try:
                self._session.get("https://www.bilibili.com/", timeout=15)
                self._save_cookies()
            except requests.RequestException as exc:
                raise NewsSourceError(f"bilibili 取 buvid3 失败: {exc}") from exc

    def _load_cookies(self) -> None:
        if not self._cookie_path.is_file():
            return
        try:
            data = json.loads(self._cookie_path.read_text("utf-8"))
            for name, value in (data or {}).items():
                self._session.cookies.set(name, value, domain=".bilibili.com")
        except (ValueError, OSError):
            # cookie 文件损坏：当作无 cookie 重建。
            pass

    def _save_cookies(self) -> None:
        data = {c.name: c.value for c in self._session.cookies}
        self._cookie_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=1), "utf-8"
        )

    # ---------------- wbi ----------------

    def _fetch_mixin_key(self) -> str:
        resp = self._session.get(
            "https://api.bilibili.com/x/web-interface/nav", timeout=15
        )
        payload = resp.json()
        wbi = ((payload.get("data") or {}).get("wbi_img")) or {}
        img_url, sub_url = wbi.get("img_url", ""), wbi.get("sub_url", "")
        if not img_url or not sub_url:
            raise NewsSourceError(f"bilibili nav 无 wbi_img: code={payload.get('code')}")
        return extract_mixin_key(img_url, sub_url)

    def _wbi_sign(self, params: dict) -> dict:
        if self._mixin_key is None:
            self._mixin_key = self._fetch_mixin_key()
        signed = dict(params)
        signed["wts"] = int(time.time())
        qs = urllib.parse.urlencode(sorted(signed.items()))
        signed["w_rid"] = hashlib.md5((qs + self._mixin_key).encode()).hexdigest()
        return signed

    # ---------------- 请求 ----------------

    def _get_json(self, url: str, params: dict, *, signed: bool = True) -> dict:
        final_params = self._wbi_sign(params) if signed else dict(params)
        last_err = "unknown"
        for attempt in range(2):
            time.sleep(_SLEEP)
            try:
                resp = self._session.get(url, params=final_params, timeout=20)
            except requests.RequestException as exc:
                raise NewsSourceError(f"bilibili 请求失败: {exc}") from exc
            if resp.status_code == 200 and "json" in resp.headers.get(
                "content-type", ""
            ):
                payload = resp.json()
                if payload.get("code") == 0:
                    return payload
                last_err = f"code={payload.get('code')} {payload.get('message')}"
                if payload.get("code") != -352:
                    raise NewsSourceError(f"bilibili 业务失败: {last_err}")
            else:
                last_err = f"HTTP {resp.status_code} 非 JSON（风控页）"
            if attempt == 0:
                time.sleep(_RETRY_BACKOFF)
        raise NewsSourceError(f"bilibili 风控拦截（-352/非 JSON），退避重试仍失败: {last_err}")

    # ---------------- 业务 ----------------

    def fetch_up_videos(self, mid: int, limit: int = 5) -> list[dict]:
        """UP主最新投稿（按发布时间倒序）：bvid/title/description/created(秒)。"""
        payload = self._get_json(
            "https://api.bilibili.com/x/space/wbi/arc/search",
            {
                "mid": mid,
                "ps": max(1, min(limit, 10)),
                "pn": 1,
                "order": "pubdate",
                "platform": "web",
                "web_location": "1550101",
            },
        )
        vlist = (((payload.get("data") or {}).get("list") or {}).get("vlist")) or []
        return [
            {
                "bvid": v.get("bvid"),
                "title": (v.get("title") or "").strip(),
                "description": (v.get("description") or "").strip(),
                "created": int(v.get("created") or 0),
            }
            for v in vlist
            if v.get("bvid")
        ]

    def fetch_video_detail(self, bvid: str) -> dict:
        """view 接口（免签名）：cid/aid/title/desc/pubdate/owner_name。"""
        time.sleep(_SLEEP)
        try:
            resp = self._session.get(
                "https://api.bilibili.com/x/web-interface/view",
                params={"bvid": bvid},
                timeout=20,
            )
            payload = resp.json()
        except (requests.RequestException, ValueError) as exc:
            raise NewsSourceError(f"bilibili view 失败({bvid}): {exc}") from exc
        data = payload.get("data") or {}
        if payload.get("code") != 0 or not data:
            raise NewsSourceError(
                f"bilibili view 业务失败({bvid}): code={payload.get('code')}"
            )
        return {
            "aid": data.get("aid"),
            "cid": data.get("cid"),
            "title": (data.get("title") or "").strip(),
            "desc": (data.get("desc") or "").strip(),
            "pubdate": int(data.get("pubdate") or 0),
            "owner_name": ((data.get("owner") or {}).get("name") or "").strip(),
        }

    def fetch_subtitle_text(self, aid: int, cid: int) -> str | None:
        """抓字幕正文（优先人工 zh-CN，次 AI ai_zh）。无字幕/失败返回 None。"""
        payload = self._get_json(
            "https://api.bilibili.com/x/player/wbi/v2", {"aid": aid, "cid": cid}
        )
        subs = (((payload.get("data") or {}).get("subtitle") or {}).get("subtitles")) or []
        if not subs:
            return None
        chosen = None
        for s in subs:
            lan = s.get("lan") or ""
            if lan == "zh-CN":
                chosen = s
                break
            if chosen is None or (lan == "ai_zh" and chosen.get("lan") != "zh-CN"):
                chosen = s
        if chosen is None:
            return None
        url = chosen.get("subtitle_url") or ""
        if url.startswith("//"):
            url = "https:" + url
        if not url:
            return None
        time.sleep(_SLEEP)
        try:
            resp = self._session.get(url, timeout=20)
            body = resp.json().get("body") or []
        except (requests.RequestException, ValueError):
            return None
        text = " ".join(
            (line.get("content") or "") for line in body if isinstance(line, dict)
        ).strip()
        return text[:_SUBTITLE_MAX_CHARS] or None


def fetch_new_up_items(
    client: BilibiliClient,
    mid: int,
    name: str,
    since_iso: str | None,
    *,
    lookback_iso: str | None = None,
) -> tuple[list[NewsItem], str | None]:
    """拉某 UP主 新投稿并组装 NewsItem（content=字幕全文，无字幕为 None）。

    新水位 = 保留视频的最大 published_at（ISO）。lookback_iso 用于首跑
    限制回看范围（published_at >= lookback_iso 才保留）。
    """
    videos = client.fetch_up_videos(mid, limit=5)
    items: list[NewsItem] = []
    newest: str | None = None
    for v in videos:
        if not v["created"]:
            continue
        published = _ts_to_iso(v["created"])
        if since_iso is not None and published <= since_iso:
            continue
        if lookback_iso is not None and published < lookback_iso:
            continue
        newest = published if newest is None else max(newest, published)
        detail = client.fetch_video_detail(v["bvid"])
        subtitle = None
        if detail.get("aid") and detail.get("cid"):
            subtitle = client.fetch_subtitle_text(int(detail["aid"]), int(detail["cid"]))
        items.append(
            NewsItem(
                source="bilibili",
                source_name=detail.get("owner_name") or name,
                title=v["title"] or detail.get("title") or v["bvid"],
                summary=(v["description"] or detail.get("desc") or "")[:500] or None,
                content=subtitle,
                url=f"https://www.bilibili.com/video/{v['bvid']}",
                published_at=published,
                category="blogger",
                dedupe_key=compute_dedupe_key("bilibili", v["bvid"], v["title"]),
            )
        )
    return items, newest


__all__ = ["BilibiliClient", "extract_mixin_key", "fetch_new_up_items"]
