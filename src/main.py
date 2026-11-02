"""
Command line runner for the Music Recommender Simulation.

Usage:
    python -m src.main               # baseline top-5 for every profile
    python -m src.main --experiment  # compare baseline vs. shifted weights
"""

import argparse

from src.recommender import load_songs, recommend_songs, DEFAULT_WEIGHTS

# Taste profiles used for evaluation. Keys match what score_song reads.
PROFILES = {
    "High-Energy Pop": {"genre": "pop", "mood": "happy", "target_energy": 0.85},
    "Chill Lofi": {"genre": "lofi", "mood": "chill", "target_energy": 0.35, "likes_acoustic": True},
    "Intense Rock": {"genre": "rock", "mood": "intense", "target_energy": 0.90},
    # Contradictory: a calm genre paired with an aggressive mood and very high energy.
    "Contradictory (Ambient + Angry + 0.95)": {"genre": "ambient", "mood": "angry", "target_energy": 0.95},
}

# Weight-shift experiment: halve genre, double energy. Baseline weights are untouched.
EXPERIMENT_WEIGHTS = {**DEFAULT_WEIGHTS, "genre": 1.0, "energy": 2.0}


def format_weights(weights: dict) -> str:
    return ", ".join(f"{name}={value}" for name, value in weights.items())


def print_recommendations(name: str, prefs: dict, songs: list, k: int, weights: dict = None) -> None:
    """Prints a ranked list with title, artist, score and reasons."""
    print("=" * 72)
    print(f"Profile: {name}")
    print(f"Prefs:   {prefs}")
    print("-" * 72)
    for rank, (song, score, explanation) in enumerate(recommend_songs(prefs, songs, k, weights), start=1):
        print(f"{rank}. {song['title']} by {song['artist']}  [{song['genre']}, {song['mood']}]  Score: {score:.2f}")
        for reason in explanation.split("; "):
            print(f"     - {reason}")
    print()


def print_experiment(name: str, prefs: dict, songs: list, k: int) -> None:
    """Prints baseline and experiment rankings side by side (titles + scores)."""
    base = recommend_songs(prefs, songs, k)
    shifted = recommend_songs(prefs, songs, k, EXPERIMENT_WEIGHTS)
    print("=" * 72)
    print(f"Profile: {name}")
    print(f"{'#':<3}{'Baseline':<34}{'Experiment':<34}")
    for rank, (b, e) in enumerate(zip(base, shifted), start=1):
        left = f"{b[0]['title']} ({b[1]:.2f})"
        right = f"{e[0]['title']} ({e[1]:.2f})"
        print(f"{rank:<3}{left:<34}{right:<34}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Content-based music recommender")
    parser.add_argument("--experiment", action="store_true", help="compare baseline vs. shifted weights")
    parser.add_argument("-k", type=int, default=5, help="number of recommendations per profile")
    args = parser.parse_args()

    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}\n")

    if args.experiment:
        print(f"Baseline weights:   {format_weights(DEFAULT_WEIGHTS)}")
        print(f"Experiment weights: {format_weights(EXPERIMENT_WEIGHTS)}\n")
        for name, prefs in PROFILES.items():
            print_experiment(name, prefs, songs, args.k)
        return

    for name, prefs in PROFILES.items():
        print_recommendations(name, prefs, songs, args.k)


if __name__ == "__main__":
    main()
