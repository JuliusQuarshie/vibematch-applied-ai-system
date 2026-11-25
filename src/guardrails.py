"""
Input validation and safety checks for VibeMatch 2.0.

Three kinds of guardrails live here:

1. Catalog guardrails  - load_catalog() / validate_catalog(): missing files, malformed CSVs,
   missing columns, empty catalogs and duplicate songs.
2. Preference guardrails - validate_preferences(): empty input, unknown genres/moods,
   energy outside 0..1, bad types, and conflicting duplicate keys.
3. Feasibility checks - find_conflicts(): preferences that are valid on their own but that
   this catalog cannot satisfy together (e.g. "ambient" + "angry"). These are warnings,
   not errors: the system still recommends, but says plainly what it could not match.

Hard problems raise ValidationError or CatalogError with actionable messages. The CLI
catches them and prints the messages instead of a traceback.
"""

import csv
import difflib
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from src.logging_config import get_logger, kv
from src.recommender import load_songs

log = get_logger("guardrails")

REQUIRED_COLUMNS = (
    "id", "title", "artist", "genre", "mood", "energy",
    "tempo_bpm", "valence", "danceability", "acousticness",
)
KNOWN_PREF_KEYS = ("genre", "mood", "target_energy", "energy", "likes_acoustic")
MAX_K = 10                 # upper bound on list length the CLI will produce
ENERGY_CONFLICT_GAP = 0.35  # a genre whose closest song is further than this from the target is flagged


class ValidationError(ValueError):
    """Raised when user preferences or options are invalid. `errors` holds one message per problem."""

    def __init__(self, errors: Sequence[str]):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


class CatalogError(RuntimeError):
    """Raised when the song catalog cannot be used (missing, malformed or empty)."""


@dataclass
class CatalogReport:
    """Result of loading and cleaning a catalog."""
    songs: List[Dict]
    skipped_rows: List[Tuple[int, str]] = field(default_factory=list)
    duplicates_removed: List[str] = field(default_factory=list)

    @property
    def warnings(self) -> List[str]:
        out = [f"skipped CSV line {line}: {reason}" for line, reason in self.skipped_rows]
        out += [f"removed duplicate song: {d}" for d in self.duplicates_removed]
        return out


@dataclass
class ValidatedPreferences:
    """Cleaned preferences in the dict shape score_song() expects, plus non-fatal findings."""
    prefs: Dict
    warnings: List[str] = field(default_factory=list)   # e.g. ignored unknown keys
    conflicts: List[str] = field(default_factory=list)  # preferences the catalog cannot satisfy together


# --- Catalog guardrails -----------------------------------------------------

def validate_catalog(songs: List[Dict]) -> CatalogReport:
    """
    Removes duplicate songs and rejects empty catalogs.
    A duplicate is a repeated id, or the same (title, artist) pair ignoring case/spacing.
    The first occurrence is kept so results stay deterministic.
    """
    if not songs:
        raise CatalogError("The song catalog is empty. Add at least one valid row to the CSV file.")

    seen_ids, seen_keys = set(), set()
    clean: List[Dict] = []
    removed: List[str] = []
    for song in songs:
        key = (" ".join(song["title"].lower().split()), " ".join(song["artist"].lower().split()))
        if song["id"] in seen_ids:
            removed.append(f"id {song['id']} ('{song['title']}') repeats an earlier id")
            continue
        if key in seen_keys:
            removed.append(f"id {song['id']} ('{song['title']}' by {song['artist']}) repeats an earlier song")
            continue
        seen_ids.add(song["id"])
        seen_keys.add(key)
        clean.append(song)

    for message in removed:
        log.warning(kv("duplicate_song_removed", detail=message))
    return CatalogReport(songs=clean, duplicates_removed=removed)


def load_catalog(csv_path: str) -> CatalogReport:
    """
    Loads a catalog through the original load_songs() and applies catalog guardrails.
    Raises CatalogError with a readable message for a missing file, a missing header,
    missing required columns, or a catalog with no usable rows.
    """
    if not os.path.isfile(csv_path):
        raise CatalogError(f"Catalog file not found: '{csv_path}'. Check the --data path.")

    with open(csv_path, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), None)
    if not header:
        raise CatalogError(f"Catalog file '{csv_path}' is empty (no header row).")
    missing = [c for c in REQUIRED_COLUMNS if c not in [h.strip() for h in header]]
    if missing:
        raise CatalogError(f"Catalog file '{csv_path}' is missing required column(s): {', '.join(missing)}.")

    skipped: List[Tuple[int, str]] = []
    songs = load_songs(csv_path, skipped=skipped)
    for line, reason in skipped:
        log.warning(kv("csv_row_skipped", line=line, reason=reason))
    if not songs:
        raise CatalogError(
            f"Catalog file '{csv_path}' has no valid song rows "
            f"({len(skipped)} row(s) were skipped as malformed)."
        )

    report = validate_catalog(songs)
    report.skipped_rows = skipped
    log.info(kv("catalog_loaded", songs=len(report.songs), skipped=len(skipped),
                duplicates=len(report.duplicates_removed)))
    return report


# --- Preference guardrails --------------------------------------------------

def _vocabulary(songs: List[Dict], attr: str) -> List[str]:
    return sorted({s[attr].lower() for s in songs})


def _unknown_value_message(kind: str, value: str, known: List[str]) -> str:
    suggestion = difflib.get_close_matches(value, known, n=1, cutoff=0.6)
    hint = f" Did you mean '{suggestion[0]}'?" if suggestion else ""
    return f"Unknown {kind} '{value}'.{hint} Known {kind}s: {', '.join(known)}."


def _parse_energy(value, key: str) -> Tuple[Optional[float], Optional[str]]:
    if isinstance(value, bool):
        return None, f"{key} must be a number between 0 and 1, not a true/false value."
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, f"{key} must be a number between 0 and 1 (got '{value}')."
    if math.isnan(number) or math.isinf(number):
        return None, f"{key} must be a finite number between 0 and 1."
    if not 0.0 <= number <= 1.0:
        return None, f"{key} must be between 0 and 1 (got {number}). Example: 0.8 for high energy."
    return number, None


def _parse_bool(value) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "yes", "y", "1"):
        return True
    if text in ("false", "no", "n", "0"):
        return False
    return None


def validate_preferences(raw: Optional[Dict], songs: List[Dict]) -> ValidatedPreferences:
    """
    Validates raw user preferences against the catalog vocabulary.

    Returns ValidatedPreferences with normalized values (lowercase genre/mood, float energy,
    bool likes_acoustic). Raises ValidationError listing every problem found, so a user can
    fix all of them at once.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(raw, dict):
        raise ValidationError(["Preferences must be a dictionary of genre, mood, target_energy, likes_acoustic."])

    prefs: Dict = {}
    for key in sorted(set(raw) - set(KNOWN_PREF_KEYS)):
        warnings.append(f"Ignored unknown preference '{key}'.")

    for kind in ("genre", "mood"):
        value = raw.get(kind)
        if value is None:
            continue
        if not isinstance(value, str):
            errors.append(f"{kind} must be text (got {type(value).__name__}).")
            continue
        value = " ".join(value.strip().lower().split())
        if not value:
            continue  # blank means "no preference"
        known = _vocabulary(songs, kind)
        if value not in known:
            errors.append(_unknown_value_message(kind, value, known))
        else:
            prefs[kind] = value

    energies = {}
    for key in ("target_energy", "energy"):
        if raw.get(key) is not None and raw.get(key) != "":
            number, problem = _parse_energy(raw[key], key)
            if problem:
                errors.append(problem)
            else:
                energies[key] = number
    if len(energies) == 2 and energies["target_energy"] != energies["energy"]:
        errors.append(
            f"Conflicting energy values: target_energy={energies['target_energy']} and "
            f"energy={energies['energy']}. Provide only one."
        )
    elif energies:
        prefs["target_energy"] = next(iter(energies.values()))

    if raw.get("likes_acoustic") is not None and raw.get("likes_acoustic") != "":
        parsed = _parse_bool(raw["likes_acoustic"])
        if parsed is None:
            errors.append(f"likes_acoustic must be true or false (got '{raw['likes_acoustic']}').")
        else:
            prefs["likes_acoustic"] = parsed

    if not errors and not any(k in prefs for k in ("genre", "mood", "target_energy")):
        errors.append(
            "No usable preferences were given. Provide at least one of genre, mood or "
            "target_energy (0-1), for example: --genre pop --mood happy --energy 0.8."
        )

    if errors:
        log.info(kv("validation_failed", error_count=len(errors), fields=",".join(sorted(raw)) or "none"))
        raise ValidationError(errors)

    conflicts = find_conflicts(prefs, songs)
    log.info(kv("validation_passed", fields=",".join(sorted(prefs)), warnings=len(warnings), conflicts=len(conflicts)))
    log.debug(kv("validated_prefs", prefs=prefs))
    return ValidatedPreferences(prefs=prefs, warnings=warnings, conflicts=conflicts)


def validate_k(k, catalog_size: int) -> Tuple[int, List[str]]:
    """
    Validates the requested list length. Must be an integer from 1 to MAX_K.
    If k exceeds the catalog size it is reduced to the catalog size with a warning.
    """
    if isinstance(k, bool):
        raise ValidationError(["k must be a whole number, not true/false."])
    try:
        as_float = float(k)
    except (TypeError, ValueError):
        raise ValidationError([f"k must be a whole number between 1 and {MAX_K} (got '{k}')."])
    if not as_float.is_integer():
        raise ValidationError([f"k must be a whole number between 1 and {MAX_K} (got {k})."])
    value = int(as_float)
    if not 1 <= value <= MAX_K:
        raise ValidationError([f"k must be between 1 and {MAX_K} (got {value})."])
    warnings: List[str] = []
    if value > catalog_size:
        warnings.append(f"Requested {value} songs but the catalog only has {catalog_size}; returning {catalog_size}.")
        value = catalog_size
    return value, warnings


# --- Feasibility checks -----------------------------------------------------

def find_conflicts(prefs: Dict, songs: List[Dict]) -> List[str]:
    """
    Returns human-readable warnings for preferences this catalog cannot satisfy together.
    The pipeline surfaces these instead of pretending a perfect match exists.
    """
    warnings: List[str] = []
    genre, mood, target = prefs.get("genre"), prefs.get("mood"), prefs.get("target_energy")
    genre_songs = [s for s in songs if genre and s["genre"] == genre]

    if genre and mood and not any(s["mood"] == mood for s in genre_songs):
        moods = sorted({s["mood"] for s in genre_songs})
        warnings.append(
            f"No song in the catalog is both '{genre}' and '{mood}'. "
            f"'{genre}' songs here are: {', '.join(moods)}."
        )
    if genre and target is not None and genre_songs:
        closest = min(abs(s["energy"] - target) for s in genre_songs)
        if closest > ENERGY_CONFLICT_GAP:
            energies = ", ".join(f"{s['energy']:.2f}" for s in genre_songs)
            warnings.append(
                f"Every '{genre}' song is far from energy {target:.2f} "
                f"(closest gap {closest:.2f}; available: {energies})."
            )
    if mood and target is not None:
        mood_songs = [s for s in songs if s["mood"] == mood]
        if mood_songs and min(abs(s["energy"] - target) for s in mood_songs) > ENERGY_CONFLICT_GAP:
            warnings.append(f"No '{mood}' song in the catalog has energy near {target:.2f}.")
    return warnings
