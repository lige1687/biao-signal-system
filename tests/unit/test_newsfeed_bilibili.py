"""B站源单元测试：wbi 签名固定向量、cookie 持久化、风控重试、字幕解析。"""
from __future__ import annotations

import hashlib
import urllib.parse

import pytest

from lei_signal.newsfeed.sources import bilibili as bili
from lei_signal.newsfeed.sources.bilibili import BilibiliClient, extract_mixin_key

# 合成长度与真实一致（各 32 hex）的假 key 对，锁算法形状。
_IMG_URL = "https://i0.hdslb.com/bfs/wbi/7cd084941338484aae1ad9425b84077c.png"
_SUB_URL = "https://i0.hdslb.com/bfs/wbi/e8e414bae3b4a1c9e8e414bae3b4a1c9.png"


def test_extract_mixin_key() -> None:
    key = extract_mixin_key(_IMG_URL, _SUB_URL)
    assert len(key) == 32
    full = "7cd084941338484aae1ad9425b84077c" + "e8e414bae3b4a1c9e8e414bae3b4a1c9"
    assert key == "".join(full[i] for i in bili._MIXIN_TAB)[:32]


def test_wbi_sign_structure(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(bili.time, "sleep", lambda *_: None)
    monkeypatch.setattr(bili.time, "time", lambda: 1750000000)
    client = BilibiliClient(tmp_path / "c.json")
    client._mixin_key = extract_mixin_key(_IMG_URL, _SUB_URL)
    params = {"mid": 1372241958, "ps": 5, "pn": 1}
    signed = client._wbi_sign(params)
    assert signed["wts"] == 1750000000
    mk = extract_mixin_key(_IMG_URL, _SUB_URL)
    expected = hashlib.md5(
        (urllib.parse.urlencode(sorted({"mid": 1372241958, "ps": 5, "pn": 1,
                                        "wts": 1750000000}.items()))
         + mk).encode()
    ).hexdigest()
    assert signed["w_rid"] == expected


def test_cookie_persistence_roundtrip(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(bili.time, "sleep", lambda *_: None)

    cookie_file = tmp_path / "cookies.json"
    client = BilibiliClient(cookie_file)
    client._session.cookies.set("buvid3", "XYZ", domain=".bilibili.com")
    client._save_cookies()

    client2 = BilibiliClient(cookie_file)
    assert "buvid3" in client2._session.cookies


def test_get_json_retry_on_352(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(bili.time, "sleep", lambda s: sleeps.append(s))

    calls = {"n": 0}

    class Resp:
        status_code = 200
        headers = {"content-type": "application/json"}

        def json(self):
            return {"code": -352, "message": "风控校验失败"}

    def fake_get(*a, **k):
        calls["n"] += 1
        return Resp()

    client = BilibiliClient(tmp_path / "c.json")
    client._session.cookies.set("buvid3", "X", domain=".bilibili.com")
    client._mixin_key = "k" * 32
    monkeypatch.setattr(client._session, "get", fake_get)
    with pytest.raises(bili.NewsSourceError):
        client._get_json("https://api.bilibili.com/x", {})
    assert calls["n"] == 2  # 重试一次
    assert bili._RETRY_BACKOFF in sleeps


def test_fetch_subtitle_text_prefers_manual_zh(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(bili.time, "sleep", lambda *_: None)
    client = BilibiliClient(tmp_path / "c.json")
    client._mixin_key = "k" * 32

    def fake_signed_get(url, params=None, timeout=None):
        if "player/wbi/v2" in url:
            class PlayerResp:
                status_code = 200
                headers = {"content-type": "application/json"}

                def json(self):
                    return {"code": 0, "data": {"subtitle": {"subtitles": [
                        {"lan": "ai_zh", "subtitle_url": "//aisub.example.com/x.json"},
                        {"lan": "zh-CN", "subtitle_url": "//sub.example.com/y.json"},
                    ]}}}

            return PlayerResp()

        class SubResp:
            status_code = 200
            headers = {"content-type": "application/json"}

            def json(self):
                return {"body": [
                    {"content": "大家好"}, {"content": "今天讲英伟达财报"},
                ]}

        return SubResp()

    monkeypatch.setattr(client._session, "get", fake_signed_get)
    text = client.fetch_subtitle_text(aid=1, cid=2)
    assert text == "大家好 今天讲英伟达财报"
