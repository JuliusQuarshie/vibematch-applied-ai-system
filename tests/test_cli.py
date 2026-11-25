import json

from src.main import main


def test_default_run_covers_all_profiles(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert out.count("VibeMatch 2.0 | Profile:") == 5
    assert "Audit trail:" in out


def test_custom_preferences(capsys):
    assert main(["--genre", "rock", "--mood", "intense", "--energy", "0.9", "-k", "3"]) == 0
    out = capsys.readouterr().out
    assert "1. Storm Runner by Voltline" in out
    assert "Outcome: no revision needed" in out


def test_invalid_input_prints_actionable_errors(capsys):
    assert main(["--genre", "popp", "--energy", "2"]) == 2
    out = capsys.readouterr().out
    assert "Did you mean 'pop'?" in out
    assert "must be between 0 and 1" in out


def test_invalid_k(capsys):
    assert main(["--genre", "pop", "-k", "abc"]) == 2
    assert "k must be a whole number" in capsys.readouterr().out


def test_missing_catalog_file(capsys):
    assert main(["--data", "nope.csv"]) == 1
    assert "not found" in capsys.readouterr().err


def test_malformed_catalog(tmp_path, capsys):
    path = tmp_path / "bad.csv"
    path.write_text("name,artist\nx,y\n")
    assert main(["--data", str(path)]) == 1
    assert "missing required column" in capsys.readouterr().err


def test_unknown_profile(capsys):
    assert main(["--profile", "Nope"]) == 2
    assert "unknown profile" in capsys.readouterr().err


def test_json_output_is_valid(capsys):
    assert main(["--profile", "Chill Lofi", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    result = data["results"]["Chill Lofi"]
    assert result["outcome"] == "revision rejected; baseline kept"
    assert len(result["final"]) == 5


def test_v1_mode_still_prints_original_output(capsys):
    assert main(["--v1"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Loaded songs: 20")
    assert "1. Spacewalk Thoughts by Orbit Bloom  [ambient, chill]  Score: 2.33" in out


def test_experiment_mode_still_works(capsys):
    assert main(["--experiment"]) == 0
    assert "Experiment weights: genre=1.0, mood=1.0, energy=2.0, acoustic=0.5" in capsys.readouterr().out


def test_list_vocabulary(capsys):
    assert main(["--list"]) == 0
    assert "Genres: ambient" in capsys.readouterr().out


def test_log_file_is_written(tmp_path, capsys):
    log = tmp_path / "run.log"
    assert main(["--profile", "Intense Rock", "--log-level", "INFO", "--log-file", str(log)]) == 0
    assert "event=baseline_evaluated" in log.read_text()


def test_bad_log_level(capsys):
    assert main(["--log-level", "LOUD"]) == 2
