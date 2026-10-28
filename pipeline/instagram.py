"""Instagram API with Instagram Login (graph.instagram.com) — Reels publishing + insights.

STATUS: written against Meta's documented flow but NOT yet exercised against the live API
(the development sandbox cannot reach graph.instagram.com). The first real run must be watched.

Env: IG_USER_ID, IG_ACCESS_TOKEN (long-lived, 60 days), IG_API_VERSION (e.g. v23.0)
Permissions: instagram_business_basic, instagram_business_content_publish, instagram_business_manage_insights
Account: Instagram professional account (Business or Creator).
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests

GRAPH = "https://graph.instagram.com"
RUPLOAD = "https://rupload.facebook.com/ig-api-upload"
REEL_METRICS = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions",
                "ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]


class IGError(Exception):
    pass


def _v():
    return os.environ.get("IG_API_VERSION", "v23.0")


def _env(name):
    v = os.environ.get(name, "")
    if not v:  # Actions passes '' for secrets that are not set
        raise KeyError(name)
    return v.strip()


def _tok():
    return _env("IG_ACCESS_TOKEN")


def _uid():
    return _env("IG_USER_ID")


def _req(method, url, **kw):
    kw.setdefault("timeout", 60)
    r = requests.request(method, url, **kw)
    try:
        data = r.json()
    except ValueError:
        data = {"raw": r.text[:500]}
    if r.status_code >= 400 or "error" in data:
        raise IGError(f"{method} {url.split('?')[0]} -> {r.status_code}: {data}")
    return data


def publishing_limit() -> dict:
    return _req("GET", f"{GRAPH}/{_v()}/{_uid()}/content_publishing_limit",
                params={"fields": "quota_usage,config", "access_token": _tok()})


def create_reel_container(caption: str, thumb_offset_ms: int = 0, share_to_feed: bool = True) -> str:
    d = _req("POST", f"{GRAPH}/{_v()}/{_uid()}/media", data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption,
        "share_to_feed": str(share_to_feed).lower(), "thumb_offset": thumb_offset_ms, "access_token": _tok()})
    return d["id"]


def upload_video(container_id: str, video: Path) -> None:
    size = video.stat().st_size
    with open(video, "rb") as f:
        d = _req("POST", f"{RUPLOAD}/{_v()}/{container_id}", data=f, timeout=900, headers={
            "Authorization": f"OAuth {_tok()}", "offset": "0", "file_size": str(size)})
    if not d.get("success", True):
        raise IGError(f"upload not successful: {d}")


def container_status(container_id: str) -> dict:
    return _req("GET", f"{GRAPH}/{_v()}/{container_id}", params={"fields": "status_code,status", "access_token": _tok()})


def wait_finished(container_id: str, timeout_s: int = 600, every: int = 10) -> str:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        st = container_status(container_id).get("status_code")
        if st in ("FINISHED", "PUBLISHED"):
            return st
        if st in ("ERROR", "EXPIRED"):
            raise IGError(f"container {container_id} status {st}")
        time.sleep(every)
    raise IGError(f"container {container_id} not ready after {timeout_s}s")


def publish(container_id: str) -> str:
    return _req("POST", f"{GRAPH}/{_v()}/{_uid()}/media_publish",
                data={"creation_id": container_id, "access_token": _tok()})["id"]


def media(media_id: str) -> dict:
    return _req("GET", f"{GRAPH}/{_v()}/{media_id}",
                params={"fields": "id,permalink,timestamp,caption,media_type", "access_token": _tok()})


def recent_media(limit: int = 10) -> list[dict]:
    return _req("GET", f"{GRAPH}/{_v()}/{_uid()}/media",
                params={"fields": "id,permalink,timestamp,caption", "limit": limit, "access_token": _tok()})["data"]


def insights(media_id: str) -> dict:
    """Returns {metric: value or None}. Metrics the API refuses are recorded as None (never guessed)."""
    out: dict = {}
    try:
        d = _req("GET", f"{GRAPH}/{_v()}/{media_id}/insights",
                 params={"metric": ",".join(REEL_METRICS), "access_token": _tok()})
        for item in d.get("data", []):
            out[item["name"]] = item.get("values", [{}])[0].get("value", item.get("total_value", {}).get("value"))
    except IGError:
        for m in REEL_METRICS:  # fall back one by one so one deprecated metric doesn't lose the rest
            try:
                d = _req("GET", f"{GRAPH}/{_v()}/{media_id}/insights", params={"metric": m, "access_token": _tok()})
                item = d["data"][0]
                out[m] = item.get("values", [{}])[0].get("value", item.get("total_value", {}).get("value"))
            except (IGError, KeyError, IndexError):
                out[m] = None
    for m in REEL_METRICS:
        out.setdefault(m, None)
    return out


def refresh_token() -> dict:
    return _req("GET", f"{GRAPH}/refresh_access_token",
                params={"grant_type": "ig_refresh_token", "access_token": _tok()})
