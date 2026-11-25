import math

import pytest

from src.guardrails import (
    MAX_K, CatalogError, ValidationError, find_conflicts, load_catalog,
    validate_catalog, validate_k, validate_preferences,
)


# --- preferences ------------------------------------------------------------

def test_valid_preferences_are_normalized(real_catalog):
    v = validate_preferences({"genre": "  POP ", "mood": "Happy", "target_energy": "0.8", "likes_acoustic": "no"},
                             real_catalog)
    assert v.prefs == {"genre": "pop", "mood": "happy", "target_energy": 0.8, "likes_acoustic": False}
    assert v.warnings == [] and v.conflicts == []


def test_starter_energy_key_is_accepted(real_catalog):
    assert validate_preferences({"energy": 0.4}, real_catalog).prefs == {"target_energy": 0.4}


@pytest.mark.parametrize("raw", [{}, {"genre": "", "mood": "   "}, {"likes_acoustic": True}])
def test_empty_or_insufficient_input_is_rejected(raw, real_catalog):
    with pytest.raises(ValidationError) as err:
        validate_preferences(raw, real_catalog)
    assert "at least one of genre, mood or target_energy" in str(err.value)


def test_non_dict_input_is_rejected(real_catalog):
    with pytest.raises(ValidationError):
        validate_preferences(None, real_catalog)


def test_unknown_genre_suggests_close_match(real_catalog):
    with pytest.raises(ValidationError) as err:
        validate_preferences({"genre": "popp"}, real_catalog)
    assert "Unknown genre 'popp'. Did you mean 'pop'?" in err.value.errors[0]


def test_unknown_mood_lists_known_moods(real_catalog):
    with pytest.raises(ValidationError) as err:
        validate_preferences({"mood": "spooky"}, real_catalog)
    assert "Unknown mood 'spooky'" in err.value.errors[0]
    assert "Known moods:" in err.value.errors[0]


@pytest.mark.parametrize("energy", [1.5, -0.1, "loud", True, math.nan, math.inf])
def test_bad_energy_is_rejected(energy, real_catalog):
    with pytest.raises(ValidationError) as err:
        validate_preferences({"genre": "pop", "target_energy": energy}, real_catalog)
    assert "target_energy" in err.value.errors[0]


def test_energy_boundaries_are_valid(real_catalog):
    assert validate_preferences({"target_energy": 0}, real_catalog).prefs["target_energy"] == 0.0
    assert validate_preferences({"target_energy": 1}, real_catalog).prefs["target_energy"] == 1.0


def test_conflicting_energy_keys_are_rejected(real_catalog):
    with pytest.raises(ValidationError) as err:
        validate_preferences({"target_energy": 0.2, "energy": 0.9}, real_catalog)
    assert "Conflicting energy values" in err.value.errors[0]


def test_all_errors_are_reported_together(real_catalog):
    with pytest.raises(ValidationError) as err:
        validate_preferences({"genre": "zzz", "mood": "qqq", "target_energy": 7, "likes_acoustic": "maybe"},
                             real_catalog)
    assert len(err.value.errors) == 4


def test_unknown_keys_are_ignored_with_warning(real_catalog):
    v = validate_preferences({"genre": "rock", "tempo": 120}, real_catalog)
    assert v.prefs == {"genre": "rock"}
    assert v.warnings == ["Ignored unknown preference 'tempo'."]


# --- conflicts --------------------------------------------------------------

def test_contradictory_profile_is_flagged(real_catalog):
    conflicts = find_conflicts({"genre": "ambient", "mood": "angry", "target_energy": 0.95}, real_catalog)
    assert any("both 'ambient' and 'angry'" in c for c in conflicts)
    assert any("far from energy 0.95" in c for c in conflicts)


def test_coherent_profile_has_no_conflicts(real_catalog):
    assert find_conflicts({"genre": "pop", "mood": "happy", "target_energy": 0.85}, real_catalog) == []


# --- k ----------------------------------------------------------------------

@pytest.mark.parametrize("k", [0, -1, MAX_K + 1, "abc", 2.5, True, None])
def test_invalid_k_is_rejected(k):
    with pytest.raises(ValidationError):
        validate_k(k, 20)


def test_k_is_clamped_to_catalog_size_with_warning():
    k, warnings = validate_k(5, 3)
    assert k == 3 and "only has 3" in warnings[0]


def test_string_k_from_cli_is_accepted():
    assert validate_k("4", 20) == (4, [])


# --- catalog ----------------------------------------------------------------

def test_duplicates_are_removed_keeping_first(make_song):
    songs = [make_song(1, "A"), make_song(1, "B"), make_song(2, " a ", artist="a"), make_song(3, "C")]
    report = validate_catalog(songs)
    assert [s["title"] for s in report.songs] == ["A", "C"]
    assert len(report.duplicates_removed) == 2


def test_empty_catalog_raises():
    with pytest.raises(CatalogError, match="empty"):
        validate_catalog([])


def test_load_catalog_missing_file():
    with pytest.raises(CatalogError, match="not found"):
        load_catalog("data/nope.csv")


def test_load_catalog_missing_column(write_csv):
    path = write_csv("1,T,A,pop,happy\n", header="id,title,artist,genre,mood\n")
    with pytest.raises(CatalogError, match="missing required column"):
        load_catalog(path)


def test_load_catalog_completely_empty_file(write_csv):
    with pytest.raises(CatalogError, match="no header"):
        load_catalog(write_csv("", header=""))


def test_load_catalog_only_bad_rows(write_csv):
    with pytest.raises(CatalogError, match="no valid song rows"):
        load_catalog(write_csv("1,T,A,pop,happy,loud,100,0.5,0.5,0.5\n"))


def test_load_catalog_reports_skipped_and_duplicate_rows(write_csv):
    path = write_csv(
        "1,Good,A,pop,happy,0.5,100,0.5,0.5,0.5\n"
        "2,Broken,A,pop,happy,0.5\n"
        "3,Good,A,pop,happy,0.6,100,0.5,0.5,0.5\n"
    )
    report = load_catalog(path)
    assert [s["id"] for s in report.songs] == [1]
    assert report.skipped_rows[0][0] == 3
    assert any("skipped CSV line 3" in w for w in report.warnings)
    assert any("duplicate" in w for w in report.warnings)


def test_real_catalog_loads_cleanly():
    report = load_catalog("data/songs.csv")
    assert len(report.songs) == 20 and report.warnings == []
