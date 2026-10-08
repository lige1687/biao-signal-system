"""Offline public-video ASR cache contract; no network or local model invocation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from lei_signal.integrations import bilibili_content as video

DATE = "2026-10-07"
BVID = "BV1xx411c7mD"
OTHER = "BV1yy411c7mD"
AUTHORS = [{"mid": "123", "name": "原作者"}]


def _item(bvid=BVID):
    return {
        "source": "bilibili",
        "url": f"https://www.bilibili.com/video/{bvid}",
        "title": "标题",
        "content": None,
    }


def _view(bvid=BVID, *, mid=123, date=DATE, duration=120):
    published = int(
        datetime.fromisoformat(date + "T12:00:00")
        .replace(tzinfo=ZoneInfo("Asia/Shanghai"))
        .timestamp()
    )
    return {
        "bvid": bvid,
        "owner": {"mid": mid},
        "pubdate": published,
        "duration": duration,
        "cid": 456,
        "title": "核实过的标题",
    }


def _offline(monkeypatch, *, view=None, cdn="https://upos-sz-mirrorcos.bilivideo.com/a.m4a"):
    calls = {"fetch": 0, "download": 0, "asr": 0}

    def fetch(url):
        calls["fetch"] += 1
        if "/view?" in url:
            bvid = url.split("bvid=")[1].split("&")[0]
            return view or _view(bvid)
        return {
            "dash": {
                "audio": [
                    {"bandwidth": 100000, "baseUrl": cdn},
                    {"bandwidth": 200000, "baseUrl": cdn},
                ]
            }
        }

    def download(url, path):
        calls["download"] += 1
        path.write_bytes(b"synthetic audio")
        return video._sha_bytes(b"synthetic audio")

    def asr(audio, output_dir, bvid):
        calls["asr"] += 1
        return {
            "text": "原始语音转写，数字待核对",
            "segments": [{"start": 0.0, "end": 60.0, "text": "原始语音转写，数字待核对"}],
        }

    monkeypatch.setattr(video, "_fetch_json", fetch)
    monkeypatch.setattr(video, "_download_audio", download)
    monkeypatch.setattr(video, "_run_asr", asr)
    monkeypatch.setattr(video, "_model_hash", lambda: "a" * 64)
    return calls


def test_refresh_then_validated_cache_never_repeats_network_or_asr(tmp_path, monkeypatch):
    (tmp_path / "audio").mkdir()
    calls = _offline(monkeypatch)
    fresh = video.collect_video_content([_item()], AUTHORS, DATE, tmp_path, refresh=True)
    assert fresh["errors"] == []
    assert fresh["results"][0]["status"] == "refreshed"
    assert fresh["items"][0]["content_basis"].startswith("本机ASR原始转写")
    assert fresh["results"][0]["coverage"]["fraction"] == 0.5
    assert fresh["items"][0]["video_content"]["segments"][0]["start"] == 0.0
    assert calls == {"fetch": 2, "download": 1, "asr": 1}
    receipt = json.loads((tmp_path / BVID / "receipt.json").read_text())
    assert receipt["metadata"]["owner_mid"] == 123
    assert "bilivideo" not in json.dumps(receipt)
    cached = video.collect_video_content([_item()], AUTHORS, DATE, tmp_path)
    assert cached["results"][0]["status"] == "cached"
    cached_refresh = video.collect_video_content([_item()], AUTHORS, DATE, tmp_path, refresh=True)
    assert cached_refresh["results"][0]["status"] == "cached"
    assert calls == {"fetch": 2, "download": 1, "asr": 1}


@pytest.mark.parametrize(
    "view,reason",
    [
        (_view(mid=999), "author MID mismatch"),
        (_view(date="2026-10-06"), "publication date mismatch"),
        (_view(duration=1801), "overlong video"),
        (_view(bvid=OTHER), "view BVID mismatch"),
    ],
)
def test_public_view_identity_date_and_duration_reject_before_audio(
    tmp_path, monkeypatch, view, reason
):
    (tmp_path / "audio").mkdir()
    calls = _offline(monkeypatch, view=view)
    result = video.collect_video_content([_item()], AUTHORS, DATE, tmp_path, refresh=True)
    assert len(result["items"]) == 1 and reason in result["errors"][0]["reason"]
    assert result["items"][0]["content_basis"].startswith("仅标题简介/音频未读到")
    assert calls["download"] == calls["asr"] == 0


@pytest.mark.parametrize(
    "url",
    [
        "http://www.bilibili.com/video/BV1xx411c7mD",
        "https://evil.example/video/BV1xx411c7mD",
        "https://www.bilibili.com/video/BV1xx411c7mD?token=secret",
        "https://www.bilibili.com/video/BV1xx411c7mD/../../private",
    ],
)
def test_noncanonical_video_url_never_fetches(tmp_path, monkeypatch, url):
    calls = _offline(monkeypatch)
    result = video.collect_video_content(
        [dict(_item(), url=url)], AUTHORS, DATE, tmp_path, refresh=True
    )
    assert len(result["errors"]) == 1 and len(result["items"]) == 1
    assert calls == {"fetch": 0, "download": 0, "asr": 0}


def test_audio_cdn_rejected_before_download(tmp_path, monkeypatch):
    (tmp_path / "audio").mkdir()
    calls = _offline(monkeypatch, cdn="https://bilivideo.com.attacker.test/a.m4a")
    result = video.collect_video_content([_item()], AUTHORS, DATE, tmp_path, refresh=True)
    assert "audio CDN host rejected" in result["errors"][0]["reason"]
    assert calls["download"] == calls["asr"] == 0


def test_no_refresh_no_cache_never_fetches(tmp_path, monkeypatch):
    calls = _offline(monkeypatch)
    result = video.collect_video_content([_item()], AUTHORS, DATE, tmp_path)
    assert "refresh required" in result["errors"][0]["reason"]
    assert calls == {"fetch": 0, "download": 0, "asr": 0}


@pytest.mark.parametrize("change", ["transcript", "audio", "metadata"])
def test_changed_cached_content_is_rejected_without_refresh(tmp_path, monkeypatch, change):
    (tmp_path / "audio").mkdir()
    calls = _offline(monkeypatch)
    video.collect_video_content([_item()], AUTHORS, DATE, tmp_path, refresh=True)
    path = tmp_path / BVID / "receipt.json"
    if change == "audio":
        (tmp_path / "audio" / f"{BVID}.m4a").write_bytes(b"changed audio")
    else:
        receipt = json.loads(path.read_text())
        if change == "transcript":
            receipt["transcript"]["text"] = "changed transcript"
        else:
            receipt["metadata"]["title"] = "changed title"
        path.write_text(json.dumps(receipt))
    result = video.collect_video_content([_item()], AUTHORS, DATE, tmp_path)
    assert len(result["items"]) == 1 and "hash mismatch" in result["errors"][0]["reason"]
    assert calls == {"fetch": 2, "download": 1, "asr": 1}


def test_partial_failure_keeps_other_video_result(tmp_path, monkeypatch):
    (tmp_path / "audio").mkdir()
    calls = _offline(monkeypatch)
    result = video.collect_video_content(
        [dict(_item(), url="https://attacker.test/x"), _item()],
        AUTHORS,
        DATE,
        tmp_path,
        refresh=True,
    )
    assert len(result["errors"]) == 1 and len(result["results"]) == 1
    assert len(result["items"]) == 2
    assert result["items"][0]["content_basis"].startswith("仅标题简介/音频未读到")
    assert result["results"][0]["bvid"] == BVID
    assert calls["asr"] == 1


def test_invalid_cache_keeps_error_evidence_then_refreshes(tmp_path, monkeypatch):
    (tmp_path / "audio").mkdir()
    calls = _offline(monkeypatch)
    video.collect_video_content([_item()], AUTHORS, DATE, tmp_path, refresh=True)
    path = tmp_path / BVID / "receipt.json"
    receipt = json.loads(path.read_text())
    receipt["transcript"]["text"] = "tampered"
    path.write_text(json.dumps(receipt))
    result = video.collect_video_content([_item()], AUTHORS, DATE, tmp_path, refresh=True)
    assert result["results"][0]["status"] == "refreshed"
    assert any("invalid existing cache" in x["reason"] for x in result["errors"])
    backup = result["errors"][0]["invalid_receipt_path"]
    assert json.loads(Path(backup).read_text(encoding="utf-8"))["transcript"]["text"] == "tampered"
    assert calls == {"fetch": 4, "download": 2, "asr": 2}


@pytest.mark.parametrize("target_date", ["", "2026-10-99", "2026-1-7"])
def test_unverifiable_target_date_returns_original_items_without_fetch(
    tmp_path, monkeypatch, target_date
):
    calls = _offline(monkeypatch)
    original = _item()
    result = video.collect_video_content([original], AUTHORS, target_date, tmp_path, refresh=True)
    assert result["items"] == [original]
    assert result["results"] == []
    assert "target_date unavailable" in result["errors"][0]["reason"]
    assert calls == {"fetch": 0, "download": 0, "asr": 0}
