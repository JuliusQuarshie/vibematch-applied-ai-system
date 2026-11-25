import pytest

from src import evaluator
from src.evaluator import ENERGY_TOLERANCE, compute_metrics, evaluate, safe_evaluate


def test_metrics_on_a_hand_checked_list(make_song):
    prefs = {"genre": "pop", "mood": "happy", "target_energy": 0.8}
    songs = [
        make_song(1, "A", artist="X", genre="pop", mood="happy", energy=0.8),
        make_song(2, "B", artist="X", genre="pop", mood="sad", energy=0.6),
        make_song(3, "C", artist="Y", genre="rock", mood="angry", energy=0.2),
    ]
    catalog = songs + [make_song(4, "D", genre="pop")]
    m = compute_metrics(songs, prefs, catalog)
    assert m["genre_matches"] == 2 and m["achievable_genre_matches"] == 3
    assert m["mood_matches"] == 1
    assert m["mean_energy_distance"] == pytest.approx((0 + 0.2 + 0.6) / 3, abs=1e-4)
    assert m["max_energy_distance"] == pytest.approx(0.6)
    assert m["energy_violations"] == 1
    assert m["off_target"] == 1               # song C matches nothing and is far in energy
    assert m["unique_artists"] == 2 and m["max_artist_repeat"] == 2
    assert m["unique_genres"] == 2 and m["duplicate_songs"] == 0


def test_metrics_are_none_for_unrequested_fields(make_song):
    m = compute_metrics([make_song(1, "A")], {"target_energy": 0.5}, [make_song(1, "A")])
    assert m["genre_matches"] is None and m["mood_matches"] is None


def test_repeated_artist_is_detected(make_song):
    songs = [make_song(1, "A", artist="Same"), make_song(2, "B", artist="Same")]
    report = evaluate(songs, {"genre": "pop"}, songs)
    assert "REPEATED_ARTIST" in report.issue_codes()
    assert report.verdict == "acceptable"


def test_repeated_unrequested_genre_is_detected(make_song):
    songs = [make_song(i, f"S{i}", artist=f"A{i}", genre="rock" if i < 5 else "pop") for i in range(1, 6)]
    report = evaluate(songs, {"genre": "pop"}, songs)
    assert "REPEATED_GENRE" in report.issue_codes()


def test_requested_genre_repeating_is_not_an_issue(make_song):
    songs = [make_song(i, f"S{i}", artist=f"A{i}", genre="pop") for i in range(1, 6)]
    assert "REPEATED_GENRE" not in evaluate(songs, {"genre": "pop"}, songs).issue_codes()


def test_energy_tolerance_boundary(make_song):
    prefs = {"target_energy": 0.5}
    inside = [make_song(1, "In", energy=0.5 + ENERGY_TOLERANCE - 0.01)]
    outside = [make_song(2, "Out", energy=0.5 + ENERGY_TOLERANCE + 0.01)]
    assert "ENERGY_MISMATCH" not in evaluate(inside, prefs, inside).issue_codes()
    assert "ENERGY_MISMATCH" in evaluate(outside, prefs, outside).issue_codes()


def test_low_quality_list_is_poor(make_song):
    prefs = {"genre": "pop", "mood": "happy", "target_energy": 0.9}
    bad = [make_song(i, f"S{i}", artist="Same", genre="folk", mood="sad", energy=0.1) for i in range(1, 4)]
    catalog = bad + [make_song(9, "Good", genre="pop", mood="happy", energy=0.9)]
    report = evaluate(bad, prefs, catalog)
    assert report.verdict == "poor"
    assert {"ENERGY_MISMATCH", "OFF_TARGET", "MOOD_MISSING", "REPEATED_ARTIST"} <= set(report.issue_codes())


def test_good_list_has_no_warnings(real_catalog):
    top = [s for s in real_catalog if s["title"] in ("Storm Runner", "Basement Riot", "Gym Hero")]
    report = evaluate(top, {"genre": "rock", "target_energy": 0.9}, real_catalog)
    assert report.warnings == [] and report.verdict == "good"


def test_catalog_limitations_are_info_not_warnings(real_catalog):
    songs = [s for s in real_catalog if s["genre"] == "classical"] + real_catalog[:4]
    report = evaluate(songs, {"genre": "classical", "mood": "angry"}, real_catalog)
    info = {i.code for i in report.issues if i.severity == "info"}
    assert {"LIMITED_GENRE_COVERAGE", "UNSATISFIABLE_COMBINATION"} <= info


def test_duplicate_song_makes_verdict_poor(make_song):
    s = make_song(1, "A")
    report = evaluate([s, s], {"genre": "pop"}, [s])
    assert report.metrics["duplicate_songs"] == 1 and report.verdict == "poor"


def test_empty_list_is_flagged():
    assert evaluate([], {"genre": "pop"}, []).issue_codes() == ["EMPTY_RESULT"]


def test_safe_evaluate_catches_failures_and_logs(caplog, make_song):
    broken = [{"id": 1, "title": "no energy field"}]
    with caplog.at_level("ERROR", logger="vibematch"):
        report = safe_evaluate(broken, {"target_energy": 0.5}, broken)
    assert report.error and "could not be checked" in report.error
    assert report.verdict == "poor"
    assert any("evaluation_failed" in r.getMessage() for r in caplog.records)


def test_evaluator_does_not_use_weighted_scores(monkeypatch, make_song):
    """Guards against circular evaluation: evaluation must not call the scorer."""
    import src.recommender as rec
    monkeypatch.setattr(rec, "score_song", lambda *a, **k: pytest.fail("evaluator used score_song"))
    songs = [make_song(1, "A")]
    evaluator.evaluate(songs, {"genre": "pop", "target_energy": 0.8}, songs)
