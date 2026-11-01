"""Regression for 2026-11-01: a re-render after /approve overwrote the 06 files and posted a
'new version' comment while the approved version sat in the Muse queue."""
import json
import sys
import types

import pytest

from pipeline import approval, ops, state

OWNER, PID = "ken-193", "IG-20261028-001"


@pytest.fixture
def handed_off(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_DIR", tmp_path)
    monkeypatch.setattr(ops, "git_commit", lambda msg: None)
    calls = []
    for f in ("issue_comment", "close_issue", "push", "create_issue"):
        monkeypatch.setattr(ops.notify, f, lambda *a, _f=f, **k: calls.append(_f))
    monkeypatch.setattr(approval.notify, "issue_comment", lambda *a, **k: None)
    drive = types.SimpleNamespace(FOLDERS={"06_pending": "P"}, moves=[], renames=[],
                                  ensure_folder=lambda *a: calls.append("ensure_folder") or "F",
                                  upload=lambda *a: calls.append("upload") or "X")
    drive.move = lambda fid, parent: drive.moves.append((fid, parent))
    drive.rename = lambda fid, name: drive.renames.append((fid, name))
    monkeypatch.setitem(sys.modules, "pipeline.drive", drive)
    import pipeline
    monkeypatch.setattr(pipeline, "drive", drive, raising=False)
    st = state.load(PID)
    for to in ("rendered", "pending_approval"):
        state.transition(st, to, "t")
    st.update(reel_sha256="abc", revision=2, issue_number=3, render_attempts=2,
              drive={"folder_id": "F", "files": {"reel.mp4": "R"}})
    state.approve(st, OWNER, OWNER, "abc")
    state.transition(st, "handed_off", "pipeline", muse={"files": {"reel.mp4": "Q1", "caption.txt": "Q2"}})
    state.save(st)
    return calls, drive


def test_guard_refuses_rerender_of_queued_post(handed_off):
    with pytest.raises(SystemExit, match="handed_off"):
        ops.guard(PID)


def test_submit_touches_nothing_when_post_is_queued(handed_off, tmp_path, monkeypatch):
    calls, _ = handed_off
    post = tmp_path / "posts" / PID
    post.mkdir(parents=True)
    (post / "metadata.json").write_text(json.dumps({"qc_passed": True, "reel_sha256": "new"}))
    monkeypatch.setattr(ops, "ROOT", tmp_path)
    with pytest.raises(SystemExit, match="handed_off"):
        ops.submit(PID)
    assert calls == []  # no Drive upload, no issue comment
    assert state.load(PID)["status"] == "handed_off"


def ev(body, login=OWNER):
    return {"comment": {"body": body, "user": {"login": login}},
            "issue": {"number": 3, "title": f"[承認待ち] {PID}", "labels": [{"name": "approval"}]}}


def test_withdraw_then_rerender_is_allowed(handed_off):
    _, drive = handed_off
    assert not approval.handle(ev("/withdraw 色変更", login="stranger"), OWNER)["withdrawn"]
    res = approval.handle(ev("/withdraw 色変更"), OWNER)
    assert res["withdrawn"]
    ops.withdraw(PID)
    assert ("Q1", "F") in drive.moves and ("Q2", "F") in drive.moves  # out of Muse's folder
    st = state.load(PID)
    assert st["status"] == "revision_requested" and st["withdrawals"][0]["revision"] == 2
    ops.guard(PID)  # now allowed


def test_cannot_withdraw_after_posted(handed_off):
    approval.handle(ev("/posted https://www.instagram.com/reel/abc/"), OWNER)
    assert not approval.handle(ev("/withdraw やっぱり"), OWNER)["withdrawn"]


def test_queue_copy_never_reuses_different_file(monkeypatch):
    from pipeline import drive
    monkeypatch.setattr(drive, "find", lambda name, parent: {"id": "OLD"})
    monkeypatch.setattr(drive, "md5", lambda fid: {"OLD": "aaa", "NEW": "bbb", "SAME": "aaa"}[fid])
    with pytest.raises(RuntimeError, match="different content"):
        drive.copy("NEW", "Q", "IG-1.mp4")
    assert drive.copy("SAME", "Q", "IG-1.mp4") == "OLD"


def test_submit_reuses_recorded_folder_even_if_renamed(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(ops, "git_commit", lambda msg: None)
    for f in ("issue_comment", "push"):
        monkeypatch.setattr(ops.notify, f, lambda *a, **k: None)
    used = []
    drive = types.SimpleNamespace(FOLDERS={"06_pending": "P"}, web_link=lambda *a, **k: "L",
                                  ensure_folder=lambda *a: pytest.fail("must not look the folder up by name"),
                                  upload=lambda src, folder, name: used.append(folder) or "X")
    monkeypatch.setitem(sys.modules, "pipeline.drive", drive)
    import pipeline
    monkeypatch.setattr(pipeline, "drive", drive, raising=False)
    post = tmp_path / "posts" / PID
    (post / "out").mkdir(parents=True)
    for n in ("out/reel.mp4", "out/thumbnail.jpg", "script.md", "caption.txt", "sources.md", "quality_check.md"):
        (post / n).write_text("x")
    (post / "metadata.json").write_text(json.dumps({"qc_passed": True, "reel_sha256": "n", "duration_sec": 50}))
    (post / "script.json").write_text(json.dumps({"title": "t"}))
    monkeypatch.setattr(ops, "ROOT", tmp_path)
    st = state.load(PID)
    st.update(status="revision_requested", issue_number=3, drive={"folder_id": "RENAMED", "files": {}})
    state.save(st)
    ops.submit(PID)
    assert set(used) == {"RENAMED"}
