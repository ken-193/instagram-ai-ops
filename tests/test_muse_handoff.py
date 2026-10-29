"""Muse mode: only approved, unmodified reels reach the folder Muse watches; /posted closes the loop."""
import sys
import types

import pytest

from pipeline import approval, ops, state

OWNER = "ken-193"
PID = "IG-20261028-001"
SHA = {"value": "abc"}  # sha256 of the file "downloaded" from Drive


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_DIR", tmp_path)
    monkeypatch.setitem(ops.PUBLISHING, "mode", "muse")
    monkeypatch.setattr(ops, "git_commit", lambda msg: None)
    monkeypatch.setattr(ops, "_sha256", lambda p: SHA["value"])
    for f in ("issue_comment", "close_issue", "push"):
        monkeypatch.setattr(ops.notify, f, lambda *a, **k: None)
    monkeypatch.setattr(approval.notify, "issue_comment", lambda *a, **k: None)
    queue = {}
    drive = types.SimpleNamespace(
        FOLDERS={"11_muse_queue": "Q", "07_published": "DONE"},
        download=lambda fid, dest: dest,
        copy=lambda fid, parent, name: queue.setdefault(name, f"copy-{fid}"),
        rename=lambda *a: None, moves=[],
    )
    drive.move = lambda fid, parent: drive.moves.append((fid, parent))
    monkeypatch.setitem(sys.modules, "pipeline.drive", drive)
    import pipeline
    monkeypatch.setattr(pipeline, "drive", drive, raising=False)
    SHA["value"] = "abc"
    st = state.load(PID)
    state.transition(st, "rendered", "t")
    state.transition(st, "pending_approval", "t")
    st.update(reel_sha256="abc", issue_number=3,
              drive={"folder_id": "F", "files": {"reel.mp4": "R", "caption.txt": "C", "thumbnail.jpg": "T"}})
    state.save(st)
    return queue, drive


def ev(body, login=OWNER):
    return {"comment": {"body": body, "user": {"login": login}},
            "issue": {"number": 3, "title": f"[承認待ち] {PID} 月", "labels": [{"name": "approval"}]}}


def test_unapproved_reel_never_reaches_muse_queue(env):
    queue, _ = env
    with pytest.raises(state.TransitionError):
        ops.publish(PID)
    assert queue == {}


def test_approved_reel_is_handed_off_once(env):
    queue, _ = env
    assert approval.handle(ev("/approve"), OWNER)["approved"]
    ops.publish(PID)
    assert set(queue) == {f"{PID}.mp4", f"{PID}.txt", f"{PID}.jpg"}
    assert state.load(PID)["status"] == "handed_off"
    ops.publish(PID)  # rerun / double trigger
    assert len(queue) == 3


def test_modified_file_is_not_handed_off(env):
    queue, _ = env
    approval.handle(ev("/approve"), OWNER)
    SHA["value"] = "tampered"
    with pytest.raises(state.TransitionError, match="does not match"):
        ops.publish(PID)
    assert queue == {}


def test_posted_requires_handoff_and_instagram_url(env):
    approval.handle(ev("/approve"), OWNER)
    assert not approval.handle(ev("/posted https://www.instagram.com/reel/abc/"), OWNER)["posted"]  # not handed off yet
    ops.publish(PID)
    assert not approval.handle(ev("/posted https://example.com/x"), OWNER)["posted"]
    assert not approval.handle(ev("/posted https://www.instagram.com/reel/abc/", login="stranger"), OWNER)["posted"]
    res = approval.handle(ev("/posted https://www.instagram.com/reel/abc123/?igsh=xyz"), OWNER)
    assert res["posted"]
    st = state.load(PID)
    assert st["status"] == "published" and st["ig"]["permalink"] == "https://www.instagram.com/reel/abc123/"


def test_posted_moves_files_out_of_muse_queue(env):
    queue, drive = env
    approval.handle(ev("/approve"), OWNER)
    ops.publish(PID)
    approval.handle(ev("/posted https://www.instagram.com/reel/abc123/"), OWNER)
    ops.posted(PID)
    moved = dict(drive.moves)
    assert moved["F"] == "DONE"
    for fid in queue.values():
        assert moved[fid] == "F"  # out of 11_Muse投稿キュー, into the published post folder
