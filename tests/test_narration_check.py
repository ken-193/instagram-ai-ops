"""Reading check: expected reading vs. what speech recognition heard (compared as katakana)."""
from pipeline import narration_check as nc


def test_same_reading_written_differently_is_exact():
    r = nc.compare("たどり着いたのは……。なると。", "たどり着いたのは鳴門。")
    assert r["exact"] and r["ok"]
    assert nc.compare("10個、100個、せん個、1万個。", "10個、100個、1000個、1万個。")["exact"]


def test_misreading_is_reported():
    r = nc.compare("まずは、つき。約38万キロ。", "まずはガツ。約38万キロ。")
    assert not r["exact"] and "ガ" in r["diff"]
