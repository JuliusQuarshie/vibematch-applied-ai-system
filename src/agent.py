"""
VibeMatch 2.0 evaluate-and-revise workflow.

    validate -> baseline (original scorer) -> evaluate -> [plan -> revise -> re-evaluate -> accept/reject]* -> report

The loop is bounded: at most MAX_REVISIONS attempts, and each strategy is tried at most once.

Revision strategies (both reuse the original score_song(); neither invents songs):

    rebalance_weights  Alternative scoring configuration REBALANCED_WEIGHTS (genre 2.0 -> 1.0,
                       mood 1.0 -> 1.5, energy 1.0 -> 2.0). Targets ENERGY_MISMATCH, OFF_TARGET
                       and MOOD_MISSING, i.e. lists where the genre bonus pulled in songs that
                       miss the requested mood or energy.
    diversity_rerank   Greedy re-ranking: each pick's score is reduced by ARTIST_PENALTY for
                       every earlier pick by the same artist, and by GENRE_PENALTY for every
                       earlier pick of the same non-requested genre. Targets REPEATED_ARTIST,
                       REPEATED_GENRE and DUPLICATE_SONG.

Acceptance policy. The candidate is judged by the independent evaluator (src/evaluator.py),
never by its own weighted score. It is ACCEPTED only if all of these hold:

    Hard constraints (vs. the baseline, so losses cannot accumulate over attempts):
      H1  no duplicate songs and the same list length as the baseline
      H2  genre_matches drops by at most MAX_RELEVANCE_LOSS (1) song
      H3  mood_matches drops by at most MAX_RELEVANCE_LOSS (1) song
    Quality criteria (vs. the currently kept list):
      Q1  the number of warning-level issues strictly decreases
      Q2  energy_violations does not increase
      Q3  mean_energy_distance does not rise by more than ENERGY_SLACK (0.05)

Otherwise the candidate is REJECTED and the previous list is kept. The thresholds trade
relevance against diversity: a user who asked for lofi will accept losing one lofi song to
avoid hearing the same artist twice, but not two.
"""

from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional

from src.evaluator import EvaluationReport, safe_evaluate
from src.guardrails import CatalogError, ValidationError, validate_catalog, validate_k, validate_preferences
from src.logging_config import get_logger, kv
from src.recommender import DEFAULT_WEIGHTS, recommend_songs, score_song

log = get_logger("agent")

MAX_REVISIONS = 3
MAX_RELEVANCE_LOSS = 1
ENERGY_SLACK = 0.05
ARTIST_PENALTY = 1.0
GENRE_PENALTY = 0.3
REBALANCED_WEIGHTS = {"genre": 1.0, "mood": 1.5, "energy": 2.0, "acoustic": 0.5}

STRATEGY_TARGETS = {
    "rebalance_weights": {"ENERGY_MISMATCH", "OFF_TARGET", "MOOD_MISSING"},
    "diversity_rerank": {"REPEATED_ARTIST", "REPEATED_GENRE", "DUPLICATE_SONG"},
}
STRATEGY_ORDER = ("rebalance_weights", "diversity_rerank")  # relevance problems are addressed first


@dataclass
class Config:
    """How a list was produced: which weights and whether diversity re-ranking was applied."""
    weights: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    diversity: bool = False

    def label(self) -> str:
        parts = ["default weights" if self.weights == DEFAULT_WEIGHTS else "rebalanced weights"]
        if self.diversity:
            parts.append("diversity re-ranking")
        return " + ".join(parts)


@dataclass
class Item:
    rank: int
    song: Dict
    score: float           # weighted score under the config's weights; equals the sum of the explanation's points
    explanation: str
    adjustment: str = ""   # set when diversity re-ranking changed this song's effective score


@dataclass
class Attempt:
    number: int
    strategy: str
    targeted_issues: List[str]
    config: str
    titles: List[str]
    evaluation: Dict
    accepted: bool
    reasons: List[str]


@dataclass
class PipelineResult:
    status: str                                   # "ok", "invalid_input", "catalog_error" or "error"
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    prefs: Dict = field(default_factory=dict)
    k: int = 0
    baseline: List[Item] = field(default_factory=list)
    baseline_eval: Optional[EvaluationReport] = None
    final: List[Item] = field(default_factory=list)
    final_eval: Optional[EvaluationReport] = None
    final_config: str = ""
    revision_activated: bool = False
    revision_accepted: bool = False
    attempts: List[Attempt] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    audit: List[str] = field(default_factory=list)

    @property
    def outcome(self) -> str:
        if self.status != "ok":
            return self.status
        if not self.revision_activated:
            return "no revision needed" if not (self.baseline_eval and self.baseline_eval.error) else "evaluation unavailable"
        return "revision accepted" if self.revision_accepted else "revision rejected; baseline kept"

    def to_dict(self) -> Dict:
        def items(xs):
            return [{"rank": i.rank, "id": i.song["id"], "title": i.song["title"], "artist": i.song["artist"],
                     "genre": i.song["genre"], "mood": i.song["mood"], "energy": i.song["energy"],
                     "score": i.score, "explanation": i.explanation, "adjustment": i.adjustment} for i in xs]
        return {
            "status": self.status, "outcome": self.outcome, "errors": self.errors, "warnings": self.warnings,
            "prefs": self.prefs, "k": self.k,
            "baseline": items(self.baseline),
            "baseline_evaluation": self.baseline_eval.to_dict() if self.baseline_eval else None,
            "final": items(self.final),
            "final_evaluation": self.final_eval.to_dict() if self.final_eval else None,
            "final_config": self.final_config,
            "revision_activated": self.revision_activated, "revision_accepted": self.revision_accepted,
            "attempts": [asdict(a) for a in self.attempts],
            "limitations": self.limitations, "audit": self.audit,
        }


# --- Candidate generation ---------------------------------------------------

def _items_from_ranked(ranked) -> List[Item]:
    return [Item(rank=i, song=s, score=sc, explanation=ex) for i, (s, sc, ex) in enumerate(ranked, start=1)]


def generate(prefs: Dict, catalog: List[Dict], k: int, config: Config) -> List[Item]:
    """Produces a ranked list for a config. Without diversity this is exactly recommend_songs()."""
    if not config.diversity:
        return _items_from_ranked(recommend_songs(prefs, catalog, k, config.weights))

    scored = []
    for song in catalog:
        score, reasons = score_song(prefs, song, config.weights)
        scored.append((song, score, "; ".join(reasons)))
    remaining = sorted(scored, key=lambda t: (-t[1], t[0]["title"].lower(), t[0]["id"]))
    picked: List[Item] = []
    artist_count: Dict[str, int] = {}
    genre_count: Dict[str, int] = {}
    requested_genre = prefs.get("genre")

    while remaining and len(picked) < k:
        def adjusted(entry):
            song, score, _ = entry
            penalty = ARTIST_PENALTY * artist_count.get(song["artist"], 0)
            if song["genre"] != requested_genre:
                penalty += GENRE_PENALTY * genre_count.get(song["genre"], 0)
            return score - penalty

        best = min(remaining, key=lambda t: (-adjusted(t), t[0]["title"].lower(), t[0]["id"]))
        remaining.remove(best)
        song, score, explanation = best
        penalty = round(score - adjusted(best), 4)
        note = ""
        if penalty > 0:
            note = f"diversity penalty -{penalty:.2f} (artist/genre already in list); effective {score - penalty:.2f}"
        picked.append(Item(rank=len(picked) + 1, song=song, score=score, explanation=explanation, adjustment=note))
        artist_count[song["artist"]] = artist_count.get(song["artist"], 0) + 1
        genre_count[song["genre"]] = genre_count.get(song["genre"], 0) + 1
    return picked


def apply_strategy(strategy: str, config: Config) -> Config:
    if strategy == "rebalance_weights":
        return Config(weights=dict(REBALANCED_WEIGHTS), diversity=config.diversity)
    if strategy == "diversity_rerank":
        return Config(weights=dict(config.weights), diversity=True)
    raise ValueError(f"unknown strategy {strategy}")


def plan_next(report: EvaluationReport, tried: List[str]) -> Optional[str]:
    """Picks the first untried strategy whose targets overlap the current warning codes."""
    codes = {i.code for i in report.warnings}
    for strategy in STRATEGY_ORDER:
        if strategy not in tried and STRATEGY_TARGETS[strategy] & codes:
            return strategy
    return None


# --- Acceptance policy ------------------------------------------------------

def decide(candidate: EvaluationReport, current: EvaluationReport, baseline: EvaluationReport) -> (bool, List[str]):
    """Applies the documented acceptance policy. Returns (accepted, reasons)."""
    c, cur, base = candidate.metrics, current.metrics, baseline.metrics
    failures, passes = [], []

    if candidate.error:
        return False, [f"candidate could not be evaluated: {candidate.error}"]
    if c["duplicate_songs"] or c["n"] != base["n"]:
        failures.append("H1 failed: duplicate songs or list length changed")
    for name, code in (("genre_matches", "H2"), ("mood_matches", "H3")):
        if base.get(name) is not None and c[name] < base[name] - MAX_RELEVANCE_LOSS:
            failures.append(f"{code} failed: {name} fell from {base[name]} to {c[name]} "
                            f"(more than {MAX_RELEVANCE_LOSS} lost)")

    before, after = len(current.warnings), len(candidate.warnings)
    if after < before:
        passes.append(f"Q1 passed: warnings {before} -> {after}")
    else:
        failures.append(f"Q1 failed: warnings did not decrease ({before} -> {after})")
    if c["energy_violations"] > cur["energy_violations"]:
        failures.append(f"Q2 failed: energy violations rose {cur['energy_violations']} -> {c['energy_violations']}")
    if cur.get("mean_energy_distance") is not None and \
            c["mean_energy_distance"] > cur["mean_energy_distance"] + ENERGY_SLACK:
        failures.append(f"Q3 failed: mean energy distance rose {cur['mean_energy_distance']:.3f} -> "
                        f"{c['mean_energy_distance']:.3f} (slack {ENERGY_SLACK})")

    if failures:
        return False, failures
    for name in ("genre_matches", "mood_matches"):
        if base.get(name) is not None and c[name] < base[name]:
            passes.append(f"trade-off: {name} {base[name]} -> {c[name]} (within the allowed loss of {MAX_RELEVANCE_LOSS})")
    return True, passes


# --- Pipeline ---------------------------------------------------------------

def _add_limitations(result: PipelineResult, report: EvaluationReport) -> None:
    """Copies catalog-limitation (info) issues into the result, skipping ones already stated."""
    for issue in report.issues:
        core = issue.message.rstrip(".")
        if issue.severity == "info" and not any(core in known for known in result.limitations):
            result.limitations.append(issue.message)


def run_pipeline(
    raw_prefs: Dict,
    catalog: List[Dict],
    k=5,
    max_revisions: int = MAX_REVISIONS,
    planner: Callable[[EvaluationReport, List[str]], Optional[str]] = plan_next,
) -> PipelineResult:
    """
    Runs the full VibeMatch 2.0 workflow and never raises for ordinary bad input:
    problems come back as status="invalid_input"/"catalog_error" with readable messages.
    """
    result = PipelineResult(status="ok")
    audit = result.audit

    try:
        report = validate_catalog(catalog)
    except CatalogError as err:
        log.error(kv("catalog_rejected", reason=str(err)))
        return PipelineResult(status="catalog_error", errors=[str(err)])
    songs = report.songs
    result.warnings += report.warnings

    try:
        k, k_warnings = validate_k(k, len(songs))
        validated = validate_preferences(raw_prefs, songs)
    except ValidationError as err:
        return PipelineResult(status="invalid_input", errors=err.errors)
    result.k, result.prefs = k, validated.prefs
    result.warnings += k_warnings + validated.warnings
    result.limitations += validated.conflicts
    audit.append(f"validated input: fields={sorted(validated.prefs)}, k={k}, catalog={len(songs)} songs")

    try:
        config = Config()
        baseline = generate(result.prefs, songs, k, config)
    except Exception as exc:  # noqa: BLE001
        log.exception(kv("baseline_failed", error_type=type(exc).__name__))
        return PipelineResult(status="error", errors=[f"Could not generate recommendations ({type(exc).__name__})."])

    base_eval = safe_evaluate([i.song for i in baseline], result.prefs, songs)
    result.baseline, result.baseline_eval = baseline, base_eval
    result.final, result.final_eval, result.final_config = baseline, base_eval, config.label()
    audit.append(f"baseline ({config.label()}): verdict={base_eval.verdict}, "
                 f"warnings={[i.code for i in base_eval.warnings]}")
    log.info(kv("baseline_evaluated", verdict=base_eval.verdict, warnings=len(base_eval.warnings)))

    _add_limitations(result, base_eval)

    if base_eval.error:
        audit.append("evaluation failed; returning the baseline without quality checks")
        result.warnings.append(base_eval.error)
        return result

    current_items, current_eval, tried = baseline, base_eval, []
    try:
        for number in range(1, max_revisions + 1):
            strategy = planner(current_eval, tried)
            if strategy is None:
                break
            result.revision_activated = True
            tried.append(strategy)
            targets = sorted(STRATEGY_TARGETS.get(strategy, set()) & {i.code for i in current_eval.warnings})
            new_config = apply_strategy(strategy, config)
            candidate = generate(result.prefs, songs, k, new_config)
            cand_eval = safe_evaluate([i.song for i in candidate], result.prefs, songs)
            accepted, reasons = decide(cand_eval, current_eval, base_eval)
            result.attempts.append(Attempt(
                number=number, strategy=strategy, targeted_issues=targets, config=new_config.label(),
                titles=[i.song["title"] for i in candidate], evaluation=cand_eval.to_dict(),
                accepted=accepted, reasons=reasons))
            audit.append(f"attempt {number}: {strategy} targeting {targets} -> "
                         f"{'ACCEPTED' if accepted else 'REJECTED'} ({'; '.join(reasons)})")
            log.info(kv("revision_" + ("accepted" if accepted else "rejected"), attempt=number,
                        strategy=strategy, warnings_before=len(current_eval.warnings),
                        warnings_after=len(cand_eval.warnings)))
            if accepted:
                config, current_items, current_eval = new_config, candidate, cand_eval
                result.revision_accepted = True
                if not current_eval.warnings:
                    break
        else:
            if planner(current_eval, tried) is not None:
                audit.append(f"stopped after the maximum of {max_revisions} revision attempts")
                log.warning(kv("revision_limit_reached", max_revisions=max_revisions))
    except Exception as exc:  # noqa: BLE001 - a failed revision must never lose the baseline
        log.exception(kv("revision_failed", error_type=type(exc).__name__))
        audit.append(f"revision step failed ({type(exc).__name__}); kept the best list found so far")

    if not result.revision_activated:
        audit.append("no fixable issues found; baseline kept")
    result.final, result.final_eval, result.final_config = current_items, current_eval, config.label()
    _add_limitations(result, current_eval)
    audit.append(f"final ({config.label()}): verdict={current_eval.verdict}, outcome={result.outcome}")
    return result
