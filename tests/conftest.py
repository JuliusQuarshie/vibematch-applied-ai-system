import pytest

HEADER = "id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness\n"


def song(id, title, artist="A", genre="pop", mood="happy", energy=0.8, acousticness=0.2):
    return {"id": id, "title": title, "artist": artist, "genre": genre, "mood": mood, "energy": energy,
            "tempo_bpm": 120.0, "valence": 0.5, "danceability": 0.5, "acousticness": acousticness}


@pytest.fixture
def make_song():
    return song


@pytest.fixture
def real_catalog():
    from src.recommender import load_songs
    return load_songs("data/songs.csv")


@pytest.fixture
def write_csv(tmp_path):
    def _write(body, header=HEADER, name="songs.csv"):
        path = tmp_path / name
        path.write_text(header + body)
        return str(path)
    return _write
