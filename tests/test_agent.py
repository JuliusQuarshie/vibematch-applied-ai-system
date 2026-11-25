import re

import pytest

from src import agent
from src.agent import MAX_REVISIONS, Config, decide, generate, run_pipeline
from src.evaluator import EvaluationReport, Issue, evaluate
from src.main import EVALUATION_PROFILES
from src.recommender import recommend_songs


# --- baseline preservation --------------------------------------------------

def test_baseline_is_exactly_the_original_recommender(real_catalog):
    for prefs in EVALUATION_PROFILES.values():
        result = run_pipeline(prefs, real_catalog, 5)
        original = recommend_songs(prefs, real_catalog, 5)
        assert [(i.song["id"], i.score, i.explanation) for i in result.baseline] == \
               [(s["id"], sc, ex) for s, sc, ex in original]


def test_generate_without_diversity_matches_recommend_songs(real_catalog):
    prefs = {"genre": "pop", "target_energy": 0.7}
    items = generate(prefs, real_catalog, 4, Config())
    assert [i.song["id"] for i in items] == [s["id"] for s, _, _ in recommend_songs(prefs, real_catalog, 4)]


# --- revision decisions on synthetic catalogs -------------------------------

@pytest.fixture
def repeat_artist_catalog(make_song):
    return [
        make_song(1, "X One", artist="X", energy=0.80),
        make_song(2, "X Two", artist="X", energy=0.78),
        make_song(3, "Y One", artist="Y", energy=0.70),
        make_song(4, "Rock", artist="Z", genre="rock", mood="sad", energy=0.80),
    ]


def test_diversity_revision_is_accepted_when_it_fixes_repeats(repeat_artist_catalog):
    result = run_pipeline({"genre": "pop", "mood": "happy", "target_energy": 0.8}, repeat_artist_catalog, 2)
    assert [i.song["title"] for i in result.baseline] == ["X One", "X Two"]
    assert result.revision_activated and result.revision_accepted
    assert [i.song["title"] for i in result.final] == ["X One", "Y One"]
    assert result.final_eval.metrics["max_artist_repeat"] == 1
    assert result.attempts[0].strategy == "diversity_rerank"
    assert result.outcome == "revision accepted"


def test_revision_that_hurts_relevance_is_rejected(monkeypatch, make_song):
    catalog = [make_song(i, f"X{i}", artist="X", energy=0.8) for i in range(1, 4)] + \
              [make_song(10 + i, f"R{i}", artist=f"R{i}", genre="rock", mood="sad", energy=0.8) for i in range(3)]
    monkeypatch.setattr(agent, "ARTIST_PENALTY", 10.0)  # force a diversity pass that swaps in off-genre songs
    result = run_pipeline({"genre": "pop", "mood": "happy", "target_energy": 0.8}, catalog, 3)
    attempt = result.attempts[0]
    assert attempt.strategy == "diversity_rerank" and not attempt.accepted
    assert any(r.startswith("H2 failed") for r in attempt.reasons)
    assert result.final == result.baseline and result.outcome == "revision rejected; baseline kept"


def _report(warnings=0, **metrics):
    base = {"n": 5, "genre_matches": 3, "mood_matches": 2, "mean_energy_distance": 0.10,
            "energy_violations": 0, "duplicate_songs": 0}
    base.update(metrics)
    return EvaluationReport(metrics=base, issues=[Issue("REPEATED_ARTIST", "warning", "x")] * warnings)


def test_decide_accepts_a_strict_improvement():
    accepted, reasons = decide(_report(0), _report(1), _report(1))
    assert accepted and reasons == ["Q1 passed: warnings 1 -> 0"]


@pytest.mark.parametrize("candidate, rule", [
    (_report(0, duplicate_songs=1), "H1"),
    (_report(0, n=4), "H1"),
    (_report(0, genre_matches=1), "H2"),
    (_report(0, mood_matches=0), "H3"),
    (_report(1), "Q1"),
    (_report(0, energy_violations=1), "Q2"),
    (_report(0, mean_energy_distance=0.20), "Q3"),
])
def test_decide_rejects_each_policy_violation(candidate, rule):
    accepted, reasons = decide(candidate, _report(1), _report(1))
    assert not accepted
    assert any(r.startswith(rule) for r in reasons)


def test_decide_allows_one_slot_of_relevance_loss_and_reports_it():
    accepted, reasons = decide(_report(0, genre_matches=2), _report(1), _report(1))
    assert accepted and any("trade-off: genre_matches 3 -> 2" in r for r in reasons)


def test_decide_rejects_unevaluable_candidate():
    bad = EvaluationReport(metrics={"n": 5}, error="boom")
    assert decide(bad, _report(1), _report(1)) == (False, ["candidate could not be evaluated: boom"])


# --- real-catalog profiles (documented in evaluation/) ----------------------

def test_contradictory_profile_revision_is_accepted(real_catalog):
    result = run_pipeline(EVALUATION_PROFILES["Contradictory (Ambient + Angry + 0.95)"], real_catalog, 5)
    assert result.revision_accepted and result.final_config == "rebalanced weights"
    assert "Spacewalk Thoughts" not in [i.song["title"] for i in result.final]
    assert result.final_eval.metrics["energy_violations"] == 0
    assert any("both 'ambient' and 'angry'" in l for l in result.limitations)


def test_chill_lofi_diversity_attempt_is_rejected(real_catalog):
    result = run_pipeline(EVALUATION_PROFILES["Chill Lofi"], real_catalog, 5)
    assert result.revision_activated and not result.revision_accepted
    assert result.final == result.baseline


def test_coherent_profile_needs_no_revision(real_catalog):
    result = run_pipeline(EVALUATION_PROFILES["Intense Rock"], real_catalog, 5)
    assert not result.revision_activated and result.outcome == "no revision needed"


def test_limited_coverage_is_explained_not_invented(real_catalog):
    result = run_pipeline(EVALUATION_PROFILES["Limited Coverage (Classical)"], real_catalog, 5)
    assert sum(i.song["genre"] == "classical" for i in result.final) == 1
    assert any("only 1 'classical'" in l for l in result.limitations)
    assert all(i.song in real_catalog for i in result.final)


# --- bounded loop, determinism, explanations -------------------------------

def test_workflow_stops_at_max_revisions(real_catalog):
    calls = []

    def always_retry(report, tried):
        calls.append(1)
        return "diversity_rerank"

    result = run_pipeline(EVALUATION_PROFILES["Chill Lofi"], real_catalog, 5, planner=always_retry)
    assert len(result.attempts) == MAX_REVISIONS
    assert any("maximum of 3" in step for step in result.audit)
    assert len(calls) == MAX_REVISIONS + 1  # one extra check to report the limit


def test_zero_revisions_allowed_returns_baseline(real_catalog):
    result = run_pipeline(EVALUATION_PROFILES["Contradictory (Ambient + Angry + 0.95)"], real_catalog, 5,
                          max_revisions=0)
    assert result.attempts == [] and result.final == result.baseline


def test_each_strategy_is_tried_at_most_once(real_catalog):
    for prefs in EVALUATION_PROFILES.values():
        strategies = [a.strategy for a in run_pipeline(prefs, real_catalog, 5).attempts]
        assert len(strategies) == len(set(strategies))


def test_results_are_deterministic(real_catalog):
    for prefs in EVALUATION_PROFILES.values():
        assert run_pipeline(prefs, real_catalog, 5).to_dict() == run_pipeline(prefs, real_catalog, 5).to_dict()


def test_explanation_points_add_up_to_score(real_catalog):
    for prefs in EVALUATION_PROFILES.values():
        result = run_pipeline(prefs, real_catalog, 5)
        for item in result.baseline + result.final:
            points = [float(p) for p in re.findall(r"\(\+(\d+\.\d+)\)", item.explanation)]
            assert sum(points) == pytest.approx(item.score, abs=0.01 * len(points))
            assert item.song["genre"] in item.explanation or "genre" not in result.prefs


def test_diversity_adjustment_is_explained(repeat_artist_catalog):
    prefs = {"genre": "pop", "mood": "happy", "target_energy": 0.8}
    items = generate(prefs, repeat_artist_catalog, 3, Config(diversity=True))
    assert [i.song["title"] for i in items] == ["X One", "Y One", "X Two"]
    assert items[2].adjustment.startswith("diversity penalty -1.00")
    assert items[0].adjustment == "" and items[1].adjustment == ""


def test_unfixable_repeat_is_rejected_not_hidden(repeat_artist_catalog):
    # k=3: the only alternatives are worse, so re-ranking just reorders and the repeat remains.
    result = run_pipeline({"genre": "pop", "mood": "happy", "target_energy": 0.8}, repeat_artist_catalog, 3)
    assert not result.revision_accepted
    assert any(r.startswith("Q1 failed") for r in result.attempts[0].reasons)
    assert "REPEATED_ARTIST" in result.final_eval.issue_codes()


# --- failure handling -------------------------------------------------------

def test_invalid_input_returns_errors_instead_of_raising(real_catalog):
    result = run_pipeline({"genre": "polka", "target_energy": 3}, real_catalog, 5)
    assert result.status == "invalid_input" and len(result.errors) == 2 and result.final == []


def test_invalid_k_returns_errors(real_catalog):
    assert run_pipeline({"genre": "pop"}, real_catalog, 0).status == "invalid_input"


def test_empty_catalog_returns_catalog_error():
    result = run_pipeline({"genre": "pop"}, [], 5)
    assert result.status == "catalog_error" and "empty" in result.errors[0]


def test_duplicate_songs_never_reach_the_output(real_catalog):
    doubled = real_catalog + [dict(s, id=s["id"] + 100) for s in real_catalog]
    result = run_pipeline({"genre": "pop"}, doubled, 5)
    assert result.final_eval.metrics["duplicate_songs"] == 0
    assert len({(i.song["title"], i.song["artist"]) for i in result.final}) == 5
    assert any("duplicate" in w for w in result.warnings)


def test_revision_crash_keeps_baseline_and_logs(monkeypatch, real_catalog, caplog):
    original = agent.generate

    def flaky(prefs, catalog, k, config):
        if config.weights != Config().weights or config.diversity:
            raise RuntimeError("simulated failure")
        return original(prefs, catalog, k, config)

    monkeypatch.setattr(agent, "generate", flaky)
    with caplog.at_level("ERROR", logger="vibematch"):
        result = run_pipeline(EVALUATION_PROFILES["Contradictory (Ambient + Angry + 0.95)"], real_catalog, 5)
    assert result.status == "ok" and result.final == result.baseline
    assert any("revision step failed" in s for s in result.audit)
    assert any("revision_failed" in r.getMessage() for r in caplog.records)


def test_evaluation_crash_returns_baseline_with_warning(monkeypatch, real_catalog):
    monkeypatch.setattr(agent, "safe_evaluate",
                        lambda *a: EvaluationReport(metrics={"n": 5}, error="Evaluation failed (X)."))
    result = run_pipeline(EVALUATION_PROFILES["High-Energy Pop"], real_catalog, 5)
    assert result.status == "ok" and result.final == result.baseline
    assert "Evaluation failed (X)." in result.warnings
    assert result.outcome == "evaluation unavailable"


def test_logs_record_decisions_but_not_preference_values(real_catalog, caplog):
    with caplog.at_level("INFO", logger="vibematch"):
        run_pipeline(EVALUATION_PROFILES["Contradictory (Ambient + Angry + 0.95)"], real_catalog, 5)
    messages = [r.getMessage() for r in caplog.records if r.levelname == "INFO"]
    assert any("event=revision_accepted" in m for m in messages)
    assert any("event=validation_passed" in m for m in messages)
    assert not any("ambient" in m or "angry" in m for m in messages)
