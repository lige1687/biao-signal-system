"""Public Bilibili video audio to local, uncorrected ASR evidence.

Default operation reads validated local receipts only. Refresh explicitly fetches
public metadata/audio and runs the already-installed local speech recognizer.
No cookies, account state, model downloads, or trading interpretation are used.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

from lei_signal.integrations.storage_health import VideoStorageRejected, preflight_video_storage

_VIDEO_URL = re.compile(r"https://www\.bilibili\.com/video/(BV[A-Za-z0-9]{10})/?\Z")
_BVID = re.compile(r"BV[A-Za-z0-9]{10}\Z")
_CDN_SUFFIXES = (".bilivideo.com", ".bilivideo.cn", ".akamaized.net")
_MAX_BYTES = 100 * 1024 * 1024
_MAX_DURATION = 1800
_MODEL = Path(__file__).resolve().parents[3] / "data/cache/video-models/whisper-small-mlx"
_ASR = Path("/Users/yongbiaoli/.local/bin/mlx_whisper")
_TZ = ZoneInfo("Asia/Shanghai")


class VideoContentError(ValueError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise VideoContentError("HTTP redirect refused")


def _opener():
    return build_opener(ProxyHandler({}), HTTPSHandler(), _NoRedirect())


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _validate_url(url: str) -> str:
    match = _VIDEO_URL.fullmatch(url) if isinstance(url, str) else None
    if not match:
        raise VideoContentError("video URL must be exact public Bilibili BV URL")
    return match.group(1)


def _validate_cdn(url: str) -> None:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if (
        parts.scheme != "https"
        or parts.username
        or parts.password
        or parts.port not in {None, 443}
        or not any(host.endswith(s) for s in _CDN_SUFFIXES)
    ):
        raise VideoContentError("audio CDN host rejected")


def _fetch_json(url: str) -> dict:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != "api.bilibili.com":
        raise VideoContentError("metadata endpoint rejected")
    request = Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}
    )
    with _opener().open(request, timeout=20) as response:
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise VideoContentError("metadata response too large")
    data = json.loads(body)
    if (
        not isinstance(data, dict)
        or data.get("code") != 0
        or not isinstance(data.get("data"), dict)
    ):
        raise VideoContentError("public API did not return valid data")
    return data["data"]


def _download_audio(url: str, destination: Path) -> str:
    _validate_cdn(url)
    preflight_video_storage(destination.parent, _MODEL)
    request = Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}
    )
    digest = hashlib.sha256()
    size = 0
    try:
        with _opener().open(request, timeout=20) as response, destination.open("wb") as output:
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > _MAX_BYTES:
                raise VideoContentError("audio exceeds 100 MiB")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > _MAX_BYTES:
                    raise VideoContentError("audio exceeds 100 MiB")
                digest.update(chunk)
                output.write(chunk)
    except OSError as exc:
        # HTTP errors often echo the signed CDN URL; do not retain it in results.
        raise VideoContentError("audio download failed") from exc
    if size == 0:
        raise VideoContentError("empty audio")
    return digest.hexdigest()


def _run_asr(audio: Path, output_dir: Path, bvid: str) -> dict:
    preflight_video_storage(audio.parent, _MODEL)
    binary = str(_ASR) if _ASR.is_file() else shutil.which("mlx_whisper")
    weights = _MODEL / "weights.npz"
    if not binary or not weights.is_file():
        raise VideoContentError("local mlx_whisper or model weights unavailable")
    subprocess.run(
        [
            binary,
            str(audio),
            "--model",
            str(_MODEL),
            "--language",
            "zh",
            "--output-format",
            "json",
            "--output-dir",
            str(output_dir),
            "--output-name",
            bvid,
            "--verbose",
            "False",
        ],
        check=True,
        timeout=720,
        capture_output=True,
        text=True,
    )
    result_path = output_dir / f"{bvid}.json"
    return json.loads(result_path.read_text(encoding="utf-8"))


def _model_hash() -> str:
    weights = _MODEL / "weights.npz"
    if not weights.is_file():
        raise VideoContentError("local model weights unavailable")
    digest = hashlib.sha256()
    with weights.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _author_mids(authors: list[dict]) -> set[int]:
    out = set()
    for author in authors:
        try:
            mid = int(author["mid"])
            if mid > 0:
                out.add(mid)
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _qualified(view: dict, bvid: str, target_date: str, mids: set[int]) -> dict:
    if view.get("bvid") != bvid:
        raise VideoContentError("view BVID mismatch")
    try:
        mid = int(view["owner"]["mid"])
        cid = int(view["cid"])
        published = datetime.fromtimestamp(int(view["pubdate"]), _TZ)
        duration = int(view["duration"])
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise VideoContentError("incomplete public view metadata") from exc
    if mid not in mids:
        raise VideoContentError("author MID mismatch")
    if published.date().isoformat() != target_date:
        raise VideoContentError("publication date mismatch")
    if cid <= 0 or duration <= 0 or duration > _MAX_DURATION:
        raise VideoContentError("invalid or overlong video")
    return {
        "bvid": bvid,
        "cid": cid,
        "owner_mid": mid,
        "title": str(view.get("title") or bvid)[:500],
        "duration_seconds": duration,
        "published_at": published.isoformat(),
        "public_url": f"https://www.bilibili.com/video/{bvid}",
    }


def _transcript(raw: dict, duration: int) -> dict:
    if not isinstance(raw, dict):
        raise VideoContentError("ASR JSON malformed")
    segments = []
    for segment in raw.get("segments") or []:
        try:
            start, end = float(segment["start"]), float(segment["end"])
            text = str(segment["text"]).strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise VideoContentError("ASR segment malformed") from exc
        if start < 0 or end < start or end > duration + 3:
            raise VideoContentError("ASR segment time outside video")
        segments.append({"start": start, "end": end, "text": text})
    full = str(raw.get("text") or "").strip() or " ".join(s["text"] for s in segments).strip()
    if not full or not segments:
        raise VideoContentError("ASR transcript empty or unsegmented")
    covered = min(duration, sum(s["end"] - s["start"] for s in segments))
    return {
        "text": full,
        "segments": segments,
        "coverage": {
            "seconds": round(covered, 2),
            "duration_seconds": duration,
            "fraction": round(covered / duration, 4),
        },
    }


def _cached(path: Path, bvid: str, target_date: str, mids: set[int]) -> dict:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != 1:
        raise VideoContentError("cache schema mismatch")
    metadata = receipt.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("bvid") != bvid:
        raise VideoContentError("cache video identity mismatch")
    if (
        metadata.get("owner_mid") not in mids
        or metadata.get("published_at", "")[:10] != target_date
    ):
        raise VideoContentError("cached author or date mismatch")
    transcript = receipt.get("transcript")
    if not isinstance(transcript, dict) or receipt.get("transcript_sha256") != _sha_bytes(
        _canonical(transcript)
    ):
        raise VideoContentError("cached transcript hash mismatch")
    if (
        not transcript.get("text")
        or not transcript.get("segments")
        or not transcript.get("coverage")
    ):
        raise VideoContentError("cached transcript incomplete")
    if not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("audio_sha256"))) or not re.fullmatch(
        r"[0-9a-f]{64}", str(receipt.get("model_sha256"))
    ):
        raise VideoContentError("cached audio or model hash missing")
    core = {
        key: receipt[key]
        for key in (
            "schema_version",
            "metadata",
            "audio_sha256",
            "model_sha256",
            "transcript",
            "transcript_sha256",
            "receipt",
        )
    }
    if receipt.get("receipt_sha256") != _sha_bytes(_canonical(core)):
        raise VideoContentError("cached receipt hash mismatch")
    audio_path = path.parent.parent / "audio" / f"{bvid}.m4a"
    if (
        not audio_path.is_file()
        or audio_path.stat().st_size > _MAX_BYTES
        or _sha_bytes(audio_path.read_bytes()) != receipt["audio_sha256"]
    ):
        raise VideoContentError("cached audio hash mismatch")
    if _model_hash() != receipt["model_sha256"]:
        raise VideoContentError("cached model hash mismatch")
    return receipt


def _fresh(item: dict, bvid: str, target_date: str, mids: set[int], directory: Path) -> dict:
    # Check before metadata work or any mkdir; an absent external disk must not
    # silently turn the logical audio link into a new internal directory.
    preflight_video_storage(directory / "audio", _MODEL)
    view_url = "https://api.bilibili.com/x/web-interface/view?" + urlencode({"bvid": bvid})
    metadata = _qualified(_fetch_json(view_url), bvid, target_date, mids)
    play_url = "https://api.bilibili.com/x/player/playurl?" + urlencode(
        {"bvid": bvid, "cid": metadata["cid"], "fnval": 4048, "fourk": 1}
    )
    play = _fetch_json(play_url)
    audio_streams = (play.get("dash") or {}).get("audio") or []
    if not audio_streams:
        raise VideoContentError("public playurl has no DASH audio")
    audio_streams = sorted(audio_streams, key=lambda x: int(x.get("bandwidth") or 0))
    audio_url = audio_streams[0].get("baseUrl") or audio_streams[0].get("base_url")
    if not isinstance(audio_url, str):
        raise VideoContentError("audio URL missing")
    _validate_cdn(audio_url)
    video_dir = directory / bvid
    video_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = directory / "audio"
    if not audio_dir.is_dir():
        raise VideoContentError("preconfigured audio directory unavailable")
    audio_path = audio_dir / f"{bvid}.m4a"
    audio_sha = _download_audio(audio_url, audio_path)
    transcript = _transcript(_run_asr(audio_path, video_dir, bvid), metadata["duration_seconds"])
    model_sha = _model_hash()
    receipt = {
        "schema_version": 1,
        "metadata": metadata,
        "audio_sha256": audio_sha,
        "model_sha256": model_sha,
        "transcript": transcript,
        "transcript_sha256": _sha_bytes(_canonical(transcript)),
        "receipt": {
            "method": "public DASH audio -> local mlx_whisper",
            "status": "local ASR uncorrected",
            "caveat": "数字需听音与画面核对；本文不构成交易建议。",
        },
    }
    receipt["receipt_sha256"] = _sha_bytes(_canonical(receipt))
    receipt_path = video_dir / "receipt.json"
    temporary = video_dir / "receipt.json.tmp"
    temporary.write_bytes(_canonical(receipt))
    temporary.replace(receipt_path)
    return receipt


def collect_video_content(
    items: list[dict],
    authors: list[dict],
    target_date: str,
    directory: Path,
    *,
    refresh: bool = False,
) -> dict:
    """Return enriched eligible items and per-video receipts/errors.

    Without ``refresh`` this function never makes network or ASR calls.
    """
    try:
        parsed_date = datetime.strptime(target_date, "%Y-%m-%d")
        if parsed_date.date().isoformat() != target_date:
            raise ValueError("noncanonical date")
    except (TypeError, ValueError):
        return {
            "items": [dict(item) for item in items],
            "errors": [
                {
                    "url": "",
                    "reason": "target_date unavailable or invalid; video content not checked",
                }
            ],
            "results": [],
        }
    directory = Path(directory)
    mids = _author_mids(authors)
    result: dict = {"items": [], "errors": [], "results": []}
    for item in items:
        if item.get("source") != "bilibili":
            result["items"].append(dict(item))
            continue
        url = item.get("url")
        try:
            bvid = _validate_url(url)
            if (
                isinstance(item.get("content"), str)
                and item["content"].strip()
                and not item.get("video_content")
            ):
                original = dict(item)
                original["content_basis"] = item.get("content_basis") or (
                    "来源已保存正文或字幕，完整范围尚未核实"
                )
                result["items"].append(original)
                result["results"].append(
                    {"bvid": bvid, "status": "source_text", "basis": original["content_basis"]}
                )
                continue
            receipt_path = directory / bvid / "receipt.json"
            receipt = None
            if receipt_path.is_file():
                try:
                    receipt = _cached(receipt_path, bvid, target_date, mids)
                except (VideoContentError, OSError, ValueError, KeyError) as exc:
                    if not refresh:
                        raise
                    evidence = {
                        "url": str(url)[:200],
                        "reason": f"invalid existing cache: {str(exc)[:250]}",
                    }
                    result["errors"].append(evidence)
                    # Keep the bad receipt unchanged if new writes are blocked.
                    # Even the evidence backup must wait for storage approval.
                    preflight_video_storage(directory / "audio", _MODEL)
                    try:
                        invalid_bytes = receipt_path.read_bytes()
                        invalid_sha = _sha_bytes(invalid_bytes)
                        backup = receipt_path.with_name(f"receipt.invalid-{invalid_sha}.json")
                        if not backup.exists():
                            backup.write_bytes(invalid_bytes)
                        evidence["invalid_receipt_path"] = str(backup)
                        evidence["invalid_receipt_sha256"] = invalid_sha
                        audio_path = directory / "audio" / f"{bvid}.m4a"
                        if audio_path.is_file() and audio_path.stat().st_size <= _MAX_BYTES:
                            evidence["observed_audio_sha256"] = _sha_bytes(audio_path.read_bytes())
                    except OSError:
                        evidence["evidence_note"] = "invalid cache observed; backup unavailable"
            if receipt is not None:
                status = "cached"
            elif refresh:
                receipt = _fresh(item, bvid, target_date, mids, directory)
                status = "refreshed"
            else:
                raise VideoContentError("no validated cache; refresh required")
            transcript = receipt["transcript"]
            enriched = dict(item)
            enriched["content"] = transcript["text"]
            enriched["content_basis"] = "本机ASR原始转写，未人工校正；数字需听音和画面核对"
            enriched["video_content"] = {
                "bvid": bvid,
                "status": status,
                "receipt_path": str(receipt_path),
                "transcript_sha256": receipt["transcript_sha256"],
                "coverage": transcript["coverage"],
                "segments": transcript["segments"],
            }
            result["items"].append(enriched)
            result["results"].append(
                {
                    "bvid": bvid,
                    "status": status,
                    "receipt_path": str(receipt_path),
                    "transcript_text": transcript["text"],
                    "segments": transcript["segments"],
                    "coverage": transcript["coverage"],
                }
            )
        except (
            VideoContentError,
            VideoStorageRejected,
            OSError,
            ValueError,
            KeyError,
            subprocess.SubprocessError,
        ) as exc:
            result["errors"].append({"url": str(url or "")[:200], "reason": str(exc)[:300]})
            original = dict(item)
            original["content_basis"] = (
                item.get("content_basis") or "来源已保存正文或字幕，完整范围尚未核实"
                if item.get("content")
                else "仅标题简介/音频未读到；不能概括完整视频内容"
            )
            result["items"].append(original)
    return result
