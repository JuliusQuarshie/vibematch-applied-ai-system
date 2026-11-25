"""
Command line interface for VibeMatch.

VibeMatch 2.0 (default) runs the full validate -> recommend -> evaluate -> revise workflow:

    python -m src.main                                   # every built-in profile
    python -m src.main --profile "Chill Lofi"            # one built-in profile
    python -m src.main --genre pop --mood happy --energy 0.8 --no-acoustic -k 5
    python -m src.main --genre rock --json               # machine-readable output
    python -m src.main --list                            # show known genres and moods

The original Module 3 (VibeMatch 1.0) behaviour is still available:

    python -m src.main --v1                              # baseline top-k for the original profiles
    python -m src.main --experiment                      # baseline vs. shifted weights

Exit codes: 0 success, 1 catalog problem, 2 invalid input.
"""

import argparse
import json
import sys
from typing import Dict, List

from src.agent import PipelineResult, run_pipeline
from src.guardrails import CatalogError, load_catalog
from src.logging_config import configure_logging
from src.recommender import DEFAULT_WEIGHTS, load_songs, recommend_songs

# Original Module 3 taste profiles. Keys match what score_song reads.
PROFILES = {
    "High-Energy Pop": {"genre": "pop", "mood": "happy", "target_energy": 0.85},
    "Chill Lofi": {"genre": "lofi", "mood": "chill", "target_energy": 0.35, "likes_acoustic": True},
    "Intense Rock": {"genre": "rock", "mood": "intense", "target_energy": 0.90},
    # Contradictory: a calm genre paired with an aggressive mood and very high energy.
    "Contradictory (Ambient + Angry + 0.95)": {"genre": "ambient", "mood": "angry", "target_energy": 0.95},
}

# VibeMatch 2.0 adds a profile for a genre with a single song in the catalog.
EVALUATION_PROFILES = {
    **PROFILES,
    "Limited Coverage (Classical)": {"genre": "classical", "mood": "sad", "target_energy": 0.20, "likes_acoustic": True},
}

# Weight-shift experiment from Module 3: halve genre, double energy. Baseline weights are untouched.
EXPERIMENT_WEIGHTS = {**DEFAULT_WEIGHTS, "genre": 1.0, "energy": 2.0}

DEFAULT_DATA = "data/songs.csv"


# --- VibeMatch 1.0 output (unchanged from Module 3) -------------------------

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


# --- VibeMatch 2.0 output ---------------------------------------------------

def _fmt_prefs(prefs: Dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in prefs.items()) or "(none)"


def _ratio(metrics: Dict, name: str) -> str:
    if metrics.get(name) is None:
        return "n/a"
    return f"{metrics[name]}/{metrics['achievable_' + name]} achievable"


def quality_line(result: PipelineResult, which: str = "final") -> str:
    report = result.final_eval if which == "final" else result.baseline_eval
    if report is None or report.error:
        return "quality could not be checked"
    m = report.metrics
    gap = "n/a" if m["mean_energy_distance"] is None else f"{m['mean_energy_distance']:.3f}"
    return (f"verdict={report.verdict} | genre {_ratio(m, 'genre_matches')} | mood {_ratio(m, 'mood_matches')} | "
            f"mean energy gap {gap} | artists {m['unique_artists']}/{m['n']} | genres {m['unique_genres']}")


def print_result(name: str, result: PipelineResult) -> None:
    print("=" * 72)
    print(f"VibeMatch 2.0 | Profile: {name}")
    if result.status != "ok":
        print("Could not produce recommendations:")
        for err in result.errors:
            print(f"  - {err}")
        print()
        return
    print(f"Input:   {_fmt_prefs(result.prefs)}  (k={result.k})")
    print(f"Outcome: {result.outcome}  [final config: {result.final_config}]")
    print("-" * 72)
    for item in result.final:
        s = item.song
        print(f"{item.rank}. {s['title']} by {s['artist']}  [{s['genre']}, {s['mood']}, energy {s['energy']:.2f}]  "
              f"Score: {item.score:.2f}")
        for reason in item.explanation.split("; "):
            if reason:
                print(f"     - {reason}")
        if item.adjustment:
            print(f"     * {item.adjustment}")

    if result.revision_accepted:
        before = [i.song["title"] for i in result.baseline]
        after = [i.song["title"] for i in result.final]
        removed = [t for t in before if t not in after]
        added = [t for t in after if t not in before]
        print("Changed from baseline: " + (f"removed {removed}, added {added}" if removed or added else "re-ordered only"))
        print(f"Baseline quality: {quality_line(result, 'baseline')}")
    print(f"Quality: {quality_line(result)}")
    issues = result.final_eval.warnings if result.final_eval else []
    for issue in issues:
        print(f"Issue:   {issue.message}")
    for warning in result.warnings:
        print(f"Note:    {warning}")
    for limit in result.limitations:
        print(f"Limit:   {limit}")
    print("Audit trail:")
    for step in result.audit:
        print(f"  - {step}")
    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VibeMatch 2.0: explainable, self-checking music recommender")
    parser.add_argument("--data", default=DEFAULT_DATA, help="path to the song CSV (default: data/songs.csv)")
    parser.add_argument("-k", default="5", help="number of recommendations (1-10, default 5)")
    parser.add_argument("--profile", help="run one built-in profile by name")
    parser.add_argument("--genre", help="favorite genre, e.g. pop")
    parser.add_argument("--mood", help="preferred mood, e.g. happy")
    parser.add_argument("--energy", help="target energy between 0 and 1, e.g. 0.8")
    acoustic = parser.add_mutually_exclusive_group()
    acoustic.add_argument("--acoustic", dest="likes_acoustic", action="store_const", const=True, help="prefer acoustic songs")
    acoustic.add_argument("--no-acoustic", dest="likes_acoustic", action="store_const", const=False, help="prefer non-acoustic songs")
    parser.add_argument("--json", action="store_true", help="print results as JSON")
    parser.add_argument("--list", action="store_true", help="list the genres and moods in the catalog")
    parser.add_argument("--v1", action="store_true", help="original Module 3 output (baseline only)")
    parser.add_argument("--experiment", action="store_true", help="Module 3 weight-shift experiment")
    parser.add_argument("--log-level", default="WARNING", help="DEBUG, INFO, WARNING (default) or ERROR")
    parser.add_argument("--log-file", help="also write log records to this file")
    return parser


def main(argv: List[str] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        configure_logging(args.log_level, args.log_file)
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2

    if args.v1 or args.experiment:
        try:
            k = int(args.k)
        except ValueError:
            print(f"Error: k must be a whole number (got '{args.k}').", file=sys.stderr)
            return 2
        try:
            songs = load_songs(args.data)
        except FileNotFoundError:
            print(f"Error: catalog file not found: '{args.data}'.", file=sys.stderr)
            return 1
        print(f"Loaded songs: {len(songs)}\n")
        if args.experiment:
            print(f"Baseline weights:   {format_weights(DEFAULT_WEIGHTS)}")
            print(f"Experiment weights: {format_weights(EXPERIMENT_WEIGHTS)}\n")
            for name, prefs in PROFILES.items():
                print_experiment(name, prefs, songs, k)
        else:
            for name, prefs in PROFILES.items():
                print_recommendations(name, prefs, songs, k)
        return 0

    try:
        catalog = load_catalog(args.data)
    except CatalogError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    if args.list:
        print("Genres: " + ", ".join(sorted({s["genre"] for s in catalog.songs})))
        print("Moods:  " + ", ".join(sorted({s["mood"] for s in catalog.songs})))
        return 0

    custom = {"genre": args.genre, "mood": args.mood, "target_energy": args.energy, "likes_acoustic": args.likes_acoustic}
    custom = {key: value for key, value in custom.items() if value is not None}
    if custom and args.profile:
        print("Error: use either --profile or --genre/--mood/--energy/--acoustic, not both.", file=sys.stderr)
        return 2
    if custom:
        runs = {"Custom": custom}
    elif args.profile:
        if args.profile not in EVALUATION_PROFILES:
            print(f"Error: unknown profile '{args.profile}'. Choose one of: {', '.join(EVALUATION_PROFILES)}.",
                  file=sys.stderr)
            return 2
        runs = {args.profile: EVALUATION_PROFILES[args.profile]}
    else:
        runs = EVALUATION_PROFILES

    results = {name: run_pipeline(prefs, catalog.songs, args.k) for name, prefs in runs.items()}

    if args.json:
        payload = {"catalog_warnings": catalog.warnings,
                   "results": {name: r.to_dict() for name, r in results.items()}}
        print(json.dumps(payload, indent=2))
    else:
        print(f"Loaded songs: {len(catalog.songs)}" + (f" ({len(catalog.warnings)} catalog warning(s))" if catalog.warnings else ""))
        for warning in catalog.warnings:
            print(f"Catalog: {warning}")
        print()
        for name, result in results.items():
            print_result(name, result)

    return 2 if any(r.status == "invalid_input" for r in results.values()) else \
        1 if any(r.status in ("catalog_error", "error") for r in results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
