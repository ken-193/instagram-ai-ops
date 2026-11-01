import json
from pathlib import Path

import pytest

from pipeline import approval, state
from pipeline.render.engine import wrap_jp
from pipeline.schema import validate

ROOT = Path(__file__).resolve().parents[1]
OWNER = "ken-193"


@pytest.fixture(autouse=True)
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_DIR", tmp_path)
    monkeypatch.setattr(approval.notify, "issue_comment", lambda *a, **k: None)


def pending(sha="abc123"):
    st = state.load("IG-20261028-001")
    state.transition(st, "rendered", "pipeline")
    state.transition(st, "pending_approval", "pipeline", reel_sha256=sha, revision=1)
    state.save(st)
    return st


def event(body, login=OWNER, labels=("approval",)):
    return {"comment": {"body": body, "user": {"login": login}},
            "issue": {"number": 1, "title": "[承認待ち] IG-20261028-001 月", "labels": [{"name": l} for l in labels]}}


def test_unapproved_post_cannot_be_published():
    st = pending()
    with pytest.raises(state.TransitionError):
        state.assert_publishable(st, 2, "abc123")


def test_only_owner_can_approve():
    pending()
    res = approval.handle(event("/approve", login="someone-else"), OWNER)
    assert res["approved"] is False
    assert state.load("IG-20261028-001")["status"] == "pending_approval"


def test_owner_approval_then_publishable():
    pending()
    res = approval.handle(event("/approve"), OWNER)
    assert res["approved"] is True
    st = state.load("IG-20261028-001")
    assert st["status"] == "approved" and st["approved_sha256"] == "abc123"
    state.assert_publishable(st, 2, "abc123")


def test_double_approve_is_ignored():
    pending()
    assert approval.handle(event("/approve"), OWNER)["approved"] is True
    second = approval.handle(event("/approve"), OWNER)
    assert second["approved"] is False  # second tap cannot trigger a second publish


def test_file_swapped_after_approval_is_blocked():
    pending()
    approval.handle(event("/approve"), OWNER)
    st = state.load("IG-20261028-001")
    with pytest.raises(state.TransitionError, match="does not match"):
        state.assert_publishable(st, 2, "different-sha")


def test_published_post_cannot_publish_again():
    pending()
    approval.handle(event("/approve"), OWNER)
    st = state.load("IG-20261028-001")
    state.transition(st, "publishing", "pipeline")
    state.transition(st, "published", "pipeline", ig={"media_id": "1"})
    with pytest.raises(state.TransitionError):
        state.assert_publishable(st, 2, "abc123")
    with pytest.raises(state.TransitionError):
        state.transition(st, "publishing", "pipeline")


def test_reject_is_terminal():
    pending()
    approval.handle(event("/reject 微妙"), OWNER)
    assert state.load("IG-20261028-001")["status"] == "rejected"
    assert approval.handle(event("/approve"), OWNER)["approved"] is False


def test_revise_records_request():
    pending()
    approval.handle(event("/revise 冒頭をもっと速く"), OWNER)
    st = state.load("IG-20261028-001")
    assert st["status"] == "revision_requested"
    assert st["revision_requests"][0]["text"] == "冒頭をもっと速く"


def test_non_approval_issue_ignored():
    pending()
    assert approval.handle(event("/approve", labels=("bug",)), OWNER)["approved"] is False


def test_publish_attempt_limit():
    pending()
    approval.handle(event("/approve"), OWNER)
    st = state.load("IG-20261028-001")
    st["publish_attempts"] = 2
    with pytest.raises(state.TransitionError, match="limit"):
        state.assert_publishable(st, 2, "abc123")


def test_sample_script_is_valid():
    from pipeline.render.scenes import SCENES
    s = json.loads((ROOT / "posts/IG-20261028-001/script.json").read_text(encoding="utf-8"))
    assert validate(s, set(SCENES)) == []


def test_schema_rejects_unsourced_verified_claim():
    from pipeline.render.scenes import SCENES
    s = json.loads((ROOT / "posts/IG-20261028-001/script.json").read_text(encoding="utf-8"))
    s["fact_checks"].append({"claim": "x", "status": "verified", "source_ids": []})
    s["fact_checks"].append({"claim": "y", "status": "estimate"})
    errs = validate(s, set(SCENES))
    assert any("verified claims need source_ids" in e for e in errs)
    assert any("estimates need 'method'" in e for e in errs)


def test_wrap_never_splits_inside_chunks():
    assert wrap_jp("世界中の海辺が|毎日、巨大な満ち引きに|襲われる。", 13) == ["世界中の海辺が毎日、", "巨大な満ち引きに襲われる。"]
    assert wrap_jp("渦潮発電で、|世界の|エネルギー首都に！？", 10) == ["渦潮発電で、世界の", "エネルギー首都に！？"]


def test_render_survives_zero_scale_text():
    from pipeline.render.engine import C, Canvas
    for ss in (1, 2):
        cv = Canvas(ss)
        cv.rich_line(540, 500, [("見た目 約2倍", C["ink"])], 78, scale=0.001)
        cv.text(540, 500, "x", 0.2, C["ink"])


def test_qc_flags_characters_missing_from_heading_font():
    from pipeline.qc import missing_glyphs
    s = json.loads((ROOT / "posts/IG-20261101-001/script.json").read_text(encoding="utf-8"))
    assert missing_glyphs(s) == []
    s["scenes"][2]["params"]["headline"] = ["1人あたり 約0.5㎡"]
    assert missing_glyphs(s) == ["㎡"]
