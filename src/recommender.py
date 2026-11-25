import csv
import sys
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

# Baseline scoring weights. Experiments pass their own dict instead of editing this one.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "genre": 2.0,     # exact genre match
    "mood": 1.0,      # exact mood match
    "energy": 1.0,    # multiplied by energy closeness (0..1)
    "acoustic": 0.5,  # multiplied by acoustic fit (0..1), only if user sets likes_acoustic
}

INT_FIELDS = ("id",)
FLOAT_FIELDS = ("energy", "tempo_bpm", "valence", "danceability", "acousticness")
UNIT_FIELDS = ("energy", "valence", "danceability", "acousticness")  # must be in [0, 1]


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    @staticmethod
    def _prefs(user: UserProfile) -> Dict:
        """Converts a UserProfile into the prefs dict used by score_song."""
        return {
            "genre": user.favorite_genre,
            "mood": user.favorite_mood,
            "target_energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
        }

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Returns the top k Song objects for the user, best first."""
        ranked = recommend_songs(self._prefs(user), [asdict(s) for s in self.songs], k)
        lookup = {(s.id, s.title): s for s in self.songs}
        return [lookup[(song["id"], song["title"])] for song, _, _ in ranked]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Returns a readable explanation of why a song got its score."""
        score, reasons = score_song(self._prefs(user), asdict(song))
        return f"Score {score:.2f}: " + "; ".join(reasons)


def load_songs(csv_path: str, skipped: Optional[List[Tuple[int, str]]] = None) -> List[Dict]:
    """
    Loads songs from a CSV file into dicts with numeric fields converted.
    Rows with missing or invalid values are skipped with a warning on stderr.
    If a `skipped` list is passed, (line_number, reason) is appended for each skipped row
    so callers (see src/guardrails.py) can report data-quality problems.
    Raises FileNotFoundError if the file does not exist.
    Required by src/main.py
    """
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):  # line 1 is the header
            try:
                song = {key: (value or "").strip() for key, value in row.items() if key}
                for field in INT_FIELDS:
                    song[field] = int(song[field])
                for field in FLOAT_FIELDS:
                    song[field] = float(song[field])
                for field in UNIT_FIELDS:
                    if not 0.0 <= song[field] <= 1.0:
                        raise ValueError(f"{field}={song[field]} is outside 0..1")
                if not song["title"] or not song["genre"] or not song["mood"]:
                    raise ValueError("title, genre and mood are required")
            except (KeyError, ValueError) as err:
                print(f"Warning: skipping line {line_no} in {csv_path}: {err}", file=sys.stderr)
                if skipped is not None:
                    skipped.append((line_no, str(err)))
                continue
            song["genre"] = song["genre"].lower()
            song["mood"] = song["mood"].lower()
            songs.append(song)
    return songs


def energy_closeness(song_energy: float, target_energy: float) -> float:
    """Returns 1.0 for a perfect energy match, falling linearly to 0.0 at a gap of 1.0."""
    return max(0.0, 1.0 - abs(song_energy - target_energy))


def score_song(user_prefs: Dict, song: Dict, weights: Optional[Dict[str, float]] = None) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.

    user_prefs keys (all optional): genre, mood, target_energy (or energy), likes_acoustic.
    Returns (score, reasons) where reasons explains every point awarded or missed.
    Required by recommend_songs() and src/main.py
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    score = 0.0
    reasons: List[str] = []

    genre = str(user_prefs.get("genre", "")).strip().lower()
    if genre:
        if song["genre"].lower() == genre:
            score += w["genre"]
            reasons.append(f"genre matches '{genre}' (+{w['genre']:.2f})")
        else:
            reasons.append(f"genre '{song['genre']}' is not '{genre}' (+0.00)")

    mood = str(user_prefs.get("mood", "")).strip().lower()
    if mood:
        if song["mood"].lower() == mood:
            score += w["mood"]
            reasons.append(f"mood matches '{mood}' (+{w['mood']:.2f})")
        else:
            reasons.append(f"mood '{song['mood']}' is not '{mood}' (+0.00)")

    target = user_prefs.get("target_energy", user_prefs.get("energy"))
    if target is not None:
        target = min(1.0, max(0.0, float(target)))
        points = w["energy"] * energy_closeness(song["energy"], target)
        score += points
        reasons.append(f"energy {song['energy']:.2f} vs target {target:.2f} (+{points:.2f})")

    likes_acoustic = user_prefs.get("likes_acoustic")
    if likes_acoustic is not None:
        fit = song["acousticness"] if likes_acoustic else 1.0 - song["acousticness"]
        points = w["acoustic"] * fit
        score += points
        label = "acoustic" if likes_acoustic else "non-acoustic"
        reasons.append(f"{label} fit {fit:.2f} (+{points:.2f})")

    return round(score, 4), reasons


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    weights: Optional[Dict[str, float]] = None,
) -> List[Tuple[Dict, float, str]]:
    """
    Scores every song, ranks by score (highest first) and returns the top k.
    Ties are broken by title then id so the order is deterministic.
    Returns a list of (song_dict, score, explanation) tuples.
    Required by src/main.py
    """
    if k <= 0 or not songs:
        return []
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, weights)
        scored.append((song, score, "; ".join(reasons)))
    scored.sort(key=lambda item: (-item[1], item[0]["title"].lower(), item[0]["id"]))
    return scored[:k]
