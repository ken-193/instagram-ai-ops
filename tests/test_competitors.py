import json

from pipeline import competitors


class Resp:
    def __init__(self, status, data):
        self.status_code, self._d, self.content, self.text = status, data, b"x", json.dumps(data)

    def json(self):
        return self._d


BD = {"business_discovery": {"username": "demo", "followers_count": 1200, "media_count": 40, "media": {"data": [
    {"timestamp": "2026-11-10T10:00:00+0000", "media_type": "VIDEO", "media_product_type": "REELS",
     "like_count": 100, "comments_count": 5, "permalink": "https://www.instagram.com/reel/a/"},
    {"timestamp": "2026-11-12T10:00:00+0000", "media_type": "IMAGE", "media_product_type": "FEED",
     "like_count": 300, "comments_count": 9, "permalink": "https://www.instagram.com/p/b/"},
    {"timestamp": "2026-11-01T10:00:00+0000", "media_type": "VIDEO", "media_product_type": "REELS",
     "comments_count": 1, "permalink": "https://www.instagram.com/reel/c/"}]}}}


def test_discover_and_summarize(monkeypatch):
    monkeypatch.setenv("IG_FB_USER_ID", "123")
    monkeypatch.setenv("IG_FB_ACCESS_TOKEN", "tok")
    seen = {}

    def fake_get(url, params, timeout):
        seen["url"], seen["fields"] = url, params["fields"]
        return Resp(200, BD)
    monkeypatch.setattr(competitors.requests, "get", fake_get)
    bd = competitors.discover("demo", 12)
    assert seen["url"].endswith("/123") and "business_discovery.username(demo)" in seen["fields"]
    row = competitors.summarize(bd, "デモ", "2026-11-15")
    assert row[1] == "@demo" and row[3] == 1200 and row[5] == 3 and row[6] == 2
    assert row[7] == 200 and row[8] == 5 and row[11] == 300 and row[12] == "2026-11-12"
    assert len(row) == len(competitors.HEADER)


def test_discover_error_is_reported(monkeypatch):
    monkeypatch.setenv("IG_FB_USER_ID", "123")
    monkeypatch.setenv("IG_FB_ACCESS_TOKEN", "tok")
    monkeypatch.setattr(competitors.requests, "get",
                        lambda *a, **k: Resp(400, {"error": {"message": "not a business account"}}))
    try:
        competitors.discover("x", 5)
    except RuntimeError as e:
        assert "not a business account" in str(e)
    else:
        raise AssertionError("expected an error")
