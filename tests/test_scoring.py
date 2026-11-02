import pytest

from src.recommender import (
    DEFAULT_WEIGHTS,
    energy_closeness,
    load_songs,
    recommend_songs,
    score_song,
)

HEADER = "id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness\n"


def make_song(**overrides):
    song = {
        "id": 1, "title": "Song", "artist": "Artist", "genre": "pop", "mood": "happy",
        "energy": 0.8, "tempo_bpm": 120.0, "valence": 0.8, "danceability": 0.8, "acousticness": 0.2,
    }
    song.update(overrides)
    return song


# --- load_songs -------------------------------------------------------------

def test_load_real_catalog_has_20_songs_with_numbers():
    songs = load_songs("data/songs.csv")
    assert len(songs) == 20
    first = songs[0]
    assert first["title"] == "Sunrise City"
    assert isinstance(first["id"], int)
    for field in ("energy", "tempo_bpm", "valence", "danceability", "acousticness"):
        assert isinstance(first[field], float)


def test_load_skips_invalid_rows(tmp_path, capsys):
    path = tmp_path / "songs.csv"
    path.write_text(
        HEADER
        + "1,Good,A,pop,happy,0.5,100,0.5,0.5,0.5\n"
        + "2,BadEnergy,A,pop,happy,loud,100,0.5,0.5,0.5\n"
        + "3,OutOfRange,A,pop,happy,1.7,100,0.5,0.5,0.5\n"
        + "4,,A,pop,happy,0.5,100,0.5,0.5,0.5\n"
    )
    songs = load_songs(str(path))
    assert [s["title"] for s in songs] == ["Good"]
    assert "skipping line 3" in capsys.readouterr().err


def test_load_header_only_returns_empty_list(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text(HEADER)
    assert load_songs(str(path)) == []


def test_load_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_songs("data/does_not_exist.csv")


# --- score_song -------------------------------------------------------------

def test_genre_and_mood_match_add_weights():
    prefs = {"genre": "pop", "mood": "happy"}
    score, reasons = score_song(prefs, make_song())
    assert score == pytest.approx(3.0)
    assert any("genre matches 'pop'" in r for r in reasons)
    assert any("mood matches 'happy'" in r for r in reasons)


def test_genre_match_is_case_insensitive():
    score, _ = score_song({"genre": "POP "}, make_song())
    assert score == pytest.approx(2.0)


def test_mismatch_gives_zero_and_explains_why():
    score, reasons = score_song({"genre": "rock", "mood": "sad"}, make_song())
    assert score == 0.0
    assert "genre 'pop' is not 'rock' (+0.00)" in reasons
    assert "mood 'happy' is not 'sad' (+0.00)" in reasons


def test_energy_closeness_values():
    assert energy_closeness(0.8, 0.8) == pytest.approx(1.0)
    assert energy_closeness(0.3, 0.8) == pytest.approx(0.5)
    assert energy_closeness(0.0, 1.0) == pytest.approx(0.0)


def test_closer_energy_scores_higher():
    prefs = {"target_energy": 0.4}
    near, _ = score_song(prefs, make_song(energy=0.45))
    far, _ = score_song(prefs, make_song(energy=0.9))
    assert near > far


def test_starter_energy_key_is_accepted():
    a, _ = score_song({"energy": 0.8}, make_song())
    b, _ = score_song({"target_energy": 0.8}, make_song())
    assert a == b == pytest.approx(1.0)


def test_acoustic_preference():
    song = make_song(acousticness=0.9)
    likes, reasons = score_song({"likes_acoustic": True}, song)
    dislikes, _ = score_song({"likes_acoustic": False}, song)
    assert likes == pytest.approx(0.45)
    assert dislikes == pytest.approx(0.05)
    assert reasons == ["acoustic fit 0.90 (+0.45)"]


def test_empty_prefs_score_zero_with_no_reasons():
    assert score_song({}, make_song()) == (0.0, [])


def test_custom_weights_do_not_change_defaults():
    before = dict(DEFAULT_WEIGHTS)
    score, _ = score_song({"genre": "pop"}, make_song(), {"genre": 1.0})
    assert score == pytest.approx(1.0)
    assert DEFAULT_WEIGHTS == before


# --- recommend_songs --------------------------------------------------------

@pytest.fixture
def catalog():
    return [
        make_song(id=1, title="Far", genre="rock", mood="sad", energy=0.1),
        make_song(id=2, title="Best", genre="pop", mood="happy", energy=0.8),
        make_song(id=3, title="Middle", genre="pop", mood="sad", energy=0.5),
    ]


def test_ranking_is_descending(catalog):
    results = recommend_songs({"genre": "pop", "mood": "happy", "target_energy": 0.8}, catalog, k=3)
    scores = [score for _, score, _ in results]
    assert scores == sorted(scores, reverse=True)
    assert [s["title"] for s, _, _ in results] == ["Best", "Middle", "Far"]


def test_top_k_limits_results(catalog):
    assert len(recommend_songs({"genre": "pop"}, catalog, k=2)) == 2
    assert len(recommend_songs({"genre": "pop"}, catalog, k=10)) == 3
    assert recommend_songs({"genre": "pop"}, catalog, k=0) == []


def test_empty_catalog_returns_empty_list():
    assert recommend_songs({"genre": "pop"}, [], k=5) == []


def test_explanation_is_joined_reasons(catalog):
    _, _, explanation = recommend_songs({"genre": "pop", "mood": "happy"}, catalog, k=1)[0]
    assert explanation == "genre matches 'pop' (+2.00); mood matches 'happy' (+1.00)"


def test_ties_are_broken_by_title():
    songs = [make_song(id=1, title="Zebra"), make_song(id=2, title="Apple")]
    results = recommend_songs({"genre": "pop"}, songs, k=2)
    assert [s["title"] for s, _, _ in results] == ["Apple", "Zebra"]
