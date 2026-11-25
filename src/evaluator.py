"""
Independent reliability evaluator for VibeMatch 2.0.

The evaluator never looks at the weighted recommendation score. It judges a list of songs
directly against the user's stated preferences and the catalog, so the revision workflow
cannot "improve" a list just by making the scorer's number go up (circular evaluation).

Metrics (all computed from song attributes only):
    genre_matches / mood_matches   songs whose genre / mood equals the request
    achievable_genre_matches       min(k, songs of that genre in the catalog) - the best any list could do
    mean_energy_distance           mean |song energy - target energy| (lower is better)
    max_energy_distance            worst single song
    energy_violations              songs further than ENERGY_TOLERANCE from the target
    off_target                     songs matching neither genre nor mood AND outside the energy tolerance
    unique_artists / max_artist_repeat / unique_genres
    duplicate_songs                the same song id listed twice (a hard error)

Issues are labelled "warning" (the workflow may try to fix them) or "info" (a catalog
limitation the workflow cannot fix, which is reported to the user instead).
"""

from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from src.logging_config import get_logger, kv

log = get_logger("evaluator")

ENERGY_TOLERANCE = 0.30      # a song this far from the target energy counts as an energy violation
GENRE_DOMINANCE_SHARE = 0.6  # one non-requested genre filling more than this share of the list is flagged


@dataclass
class Issue:
    code: str
    severity: str  # "warning" (fixable in principle) or "info" (catalog limitation)
    message: str


@dataclass
class EvaluationReport:
    metrics: Dict
    issues: List[Issue] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def verdict(self) -> str:
        """'good' = no warnings, 'acceptable' = 1-2 warnings, 'poor' = 3+ or a hard error."""
        if self.error or self.metrics.get("duplicate_songs", 0):
            return "poor"
        n = len(self.warnings)
        return "good" if n == 0 else "acceptable" if n <= 2 else "poor"

    def issue_codes(self) -> List[str]:
        return sorted({i.code for i in self.issues})

    def to_dict(self) -> Dict:
        return {
            "verdict": self.verdict,
            "metrics": self.metrics,
            "issues": [asdict(i) for i in self.issues],
            "error": self.error,
        }


def compute_metrics(songs: List[Dict], prefs: Dict, catalog: List[Dict]) -> Dict:
    """Computes the independent quality metrics for one recommendation list."""
    n = len(songs)
    genre, mood, target = prefs.get("genre"), prefs.get("mood"), prefs.get("target_energy")

    genre_hits = [s["genre"] == genre for s in songs] if genre else []
    mood_hits = [s["mood"] == mood for s in songs] if mood else []
    distances = [abs(s["energy"] - target) for s in songs] if target is not None else []

    off_target = 0
    for i, song in enumerate(songs):
        matches_label = (genre_hits and genre_hits[i]) or (mood_hits and mood_hits[i])
        far = bool(distances) and distances[i] > ENERGY_TOLERANCE
        if not matches_label and far:
            off_target += 1

    artists = Counter(s["artist"] for s in songs)
    genres = Counter(s["genre"] for s in songs)
    ids = Counter(s["id"] for s in songs)

    metrics = {
        "n": n,
        "genre_matches": sum(genre_hits) if genre else None,
        "achievable_genre_matches": min(n, sum(1 for s in catalog if s["genre"] == genre)) if genre else None,
        "mood_matches": sum(mood_hits) if mood else None,
        "achievable_mood_matches": min(n, sum(1 for s in catalog if s["mood"] == mood)) if mood else None,
        "mean_energy_distance": round(sum(distances) / n, 4) if distances and n else None,
        "max_energy_distance": round(max(distances), 4) if distances else None,
        "energy_violations": sum(d > ENERGY_TOLERANCE for d in distances) if distances else 0,
        "off_target": off_target,
        "unique_artists": len(artists),
        "max_artist_repeat": max(artists.values()) if artists else 0,
        "unique_genres": len(genres),
        "duplicate_songs": sum(c - 1 for c in ids.values()),
    }
    return metrics


def detect_issues(songs: List[Dict], prefs: Dict, catalog: List[Dict], metrics: Dict) -> List[Issue]:
    """Turns metrics into labelled issues with readable messages."""
    issues: List[Issue] = []
    n = metrics["n"]
    genre, mood, target = prefs.get("genre"), prefs.get("mood"), prefs.get("target_energy")

    if n == 0:
        return [Issue("EMPTY_RESULT", "warning", "No recommendations were produced.")]

    if metrics["duplicate_songs"]:
        issues.append(Issue("DUPLICATE_SONG", "warning", "The same song appears more than once."))

    for artist, count in sorted(Counter(s["artist"] for s in songs).items()):
        if count > 1:
            issues.append(Issue("REPEATED_ARTIST", "warning", f"{artist} appears {count} times in the list."))

    for g, count in sorted(Counter(s["genre"] for s in songs).items()):
        if g != genre and count > 1 and count / n > GENRE_DOMINANCE_SHARE:
            issues.append(Issue("REPEATED_GENRE", "warning",
                                f"'{g}' fills {count} of {n} slots although it was not requested."))

    if target is not None:
        for s in songs:
            gap = abs(s["energy"] - target)
            if gap > ENERGY_TOLERANCE:
                issues.append(Issue("ENERGY_MISMATCH", "warning",
                                    f"'{s['title']}' has energy {s['energy']:.2f}, {gap:.2f} from the target {target:.2f}."))

    if metrics["off_target"]:
        issues.append(Issue("OFF_TARGET", "warning",
                            f"{metrics['off_target']} song(s) match neither the requested genre, mood nor energy."))

    if mood and metrics["mood_matches"] == 0 and metrics["achievable_mood_matches"]:
        issues.append(Issue("MOOD_MISSING", "warning",
                            f"No '{mood}' song made the list although the catalog has {metrics['achievable_mood_matches']}+."))

    # Catalog limitations: reported, not "fixed".
    if genre:
        available = sum(1 for s in catalog if s["genre"] == genre)
        if available < n:
            issues.append(Issue("LIMITED_GENRE_COVERAGE", "info",
                                f"The catalog has only {available} '{genre}' song(s); "
                                f"{n - available} slot(s) had to be filled from other genres."))
    if mood:
        available = sum(1 for s in catalog if s["mood"] == mood)
        if available == 0:
            issues.append(Issue("MOOD_NOT_IN_CATALOG", "info", f"No song in the catalog is tagged '{mood}'."))
    if genre and mood and not any(s["genre"] == genre and s["mood"] == mood for s in catalog):
        issues.append(Issue("UNSATISFIABLE_COMBINATION", "info",
                            f"No song in the catalog is both '{genre}' and '{mood}'."))
    return issues


def evaluate(songs: List[Dict], prefs: Dict, catalog: List[Dict]) -> EvaluationReport:
    """Evaluates a recommendation list. May raise on malformed input; see safe_evaluate()."""
    metrics = compute_metrics(songs, prefs, catalog)
    return EvaluationReport(metrics=metrics, issues=detect_issues(songs, prefs, catalog, metrics))


def safe_evaluate(songs: List[Dict], prefs: Dict, catalog: List[Dict]) -> EvaluationReport:
    """
    Wraps evaluate() so an unexpected failure never crashes the pipeline.
    On failure it logs the exception and returns a report with `error` set; the agent then
    keeps the baseline list and says that quality could not be checked.
    """
    try:
        return evaluate(songs, prefs, catalog)
    except Exception as exc:  # noqa: BLE001 - deliberate safety net
        log.exception(kv("evaluation_failed", error_type=type(exc).__name__))
        return EvaluationReport(metrics={"n": len(songs)}, issues=[],
                                error=f"Evaluation failed ({type(exc).__name__}); quality could not be checked.")
