"""Publish flow with Instagram / Drive / git mocked: verifies ordering and no-duplicate guarantees."""
import sys
import types

import pytest

from pipeline import ops, state


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_DIR", tmp_path)
    log = []
    monkeypatch.setattr(ops, "git_commit", lambda msg: log.append(("commit", msg, state.load("IG-20261028-001")["status"])))
    monkeypatch.setattr(ops, "full_caption", lambda d: "もしも月が今の半分の距離に来たら…？ #もしも")
    monkeypatch.setattr(ops, "_sha256", lambda p: "abc")
    monkeypatch.setattr(ops.notify, "issue_comment", lambda *a, **k: None)
    monkeypatch.setattr(ops.notify, "close_issue", lambda *a, **k: None)
    monkeypatch.setattr(ops.notify, "push", lambda *a, **k: None)

    drive = types.SimpleNamespace(download=lambda fid, dest: dest, move=lambda *a: None,
                                  FOLDERS={"07_published": "x"})
    ig = types.SimpleNamespace(calls=[], status="FINISHED", fail_upload=False)

    def create(caption):
        ig.calls.append("create")
        log.append(("ig_create", None, state.load("IG-20261028-001")["status"]))
        return "C1"

    def upload(cid, path):
        ig.calls.append("upload")
        if ig.fail_upload:
            raise RuntimeError("network reset")

    ig.publishing_limit = lambda: {}
    ig.create_reel_container = create
    ig.upload_video = upload
    ig.wait_finished = lambda cid: "FINISHED"
    ig.publish = lambda cid: ig.calls.append("publish") or "M1"
    ig.media = lambda mid: {"permalink": "https://instagram.com/reel/x", "timestamp": "2026-10-28T00:00:00+0000"}
    ig.container_status = lambda cid: {"status_code": ig.status}
    ig.recent_media = lambda n: []
    monkeypatch.setitem(sys.modules, "pipeline.drive", drive)
    monkeypatch.setitem(sys.modules, "pipeline.instagram", ig)
    import pipeline
    monkeypatch.setattr(pipeline, "drive", drive, raising=False)
    monkeypatch.setattr(pipeline, "instagram", ig, raising=False)

    st = state.load("IG-20261028-001")
    for to in ("rendered", "pending_approval"):
        state.transition(st, to, "t")
    st.update(reel_sha256="abc", drive={"folder_id": "F", "files": {"reel.mp4": "R"}}, issue_number=1)
    state.approve(st, "ken-193", "ken-193", "abc")
    state.save(st)
    return log, ig


def test_publishing_state_committed_before_instagram_call(env):
    log, ig = env
    ops.publish("IG-20261028-001")
    first_ig = next(i for i, e in enumerate(log) if e[0] == "ig_create")
    assert any(e[0] == "commit" and e[2] == "publishing" for e in log[:first_ig])
    assert state.load("IG-20261028-001")["status"] == "published"
    assert ig.calls.count("publish") == 1


def test_rerun_after_publish_does_nothing(env):
    log, ig = env
    ops.publish("IG-20261028-001")
    ops.publish("IG-20261028-001")
    assert ig.calls.count("create") == 1 and ig.calls.count("publish") == 1


def test_upload_error_reconciles_without_new_container(env):
    log, ig = env
    ig.fail_upload = True
    ig.status = "IN_PROGRESS"
    with pytest.raises(SystemExit):
        ops.publish("IG-20261028-001")
    assert state.load("IG-20261028-001")["status"] == "publish_unknown"
    # a later manual run reconciles the same container once Instagram finishes processing
    ig.fail_upload = False
    ig.status = "FINISHED"
    ops.publish("IG-20261028-001")
    assert ig.calls.count("create") == 1
    assert state.load("IG-20261028-001")["status"] == "published"
