import json

from src.evaluate import build_report, main, render_markdown


def test_report_covers_required_profiles():
    report = build_report()
    names = [p["profile"] for p in report["profiles"]]
    assert len(names) >= 5
    for required in ("High-Energy Pop", "Chill Lofi", "Intense Rock", "Contradictory", "Limited Coverage"):
        assert any(required in n for n in names)
    for p in report["profiles"]:
        assert {"input", "baseline_titles", "final_titles", "comparison", "revision_activated",
                "revision_accepted", "audit"} <= set(p)


def test_report_is_reproducible(tmp_path, capsys):
    main(["--out-dir", str(tmp_path / "a")])
    main(["--out-dir", str(tmp_path / "b")])
    for name in ("results.json", "summary.md"):
        assert (tmp_path / "a" / name).read_text() == (tmp_path / "b" / name).read_text()
    json.loads((tmp_path / "a" / "results.json").read_text())


def test_committed_evaluation_matches_current_code():
    """evaluation/ must be regenerated whenever behaviour changes."""
    report = build_report()
    with open("evaluation/results.json", encoding="utf-8") as f:
        assert json.load(f) == json.loads(json.dumps(report))
    with open("evaluation/summary.md", encoding="utf-8") as f:
        assert f.read() == render_markdown(report)


def test_summary_states_metrics_are_not_user_satisfaction():
    assert "not measurements of listener satisfaction" in render_markdown(build_report())
