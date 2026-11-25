# Model Card: VibeMatch 2.0

## 1. System name

**VibeMatch 2.0**: an explainable, self-checking music recommender. It extends **VibeMatch 1.0**,
my CodePath AI110 Module 3 Music Recommender Simulation
(https://github.com/JuliusQuarshie/ai110-module3show-musicrecommendersimulation-starter).

Repository: https://github.com/JuliusQuarshie/vibematch-applied-ai-system

## 2. Intended and non-intended uses

**Intended uses**

- A portfolio and teaching project showing how to wrap a simple recommender in input validation,
  independent quality checks, bounded self-correction and transparent reporting.
- Exploring how scoring weights, catalog coverage and acceptance rules affect recommendations.

**Not intended for**

- Real music recommendation for real listeners. The catalog has 20 fictional songs and there is
  no listening data.
- Any claim about what people will enjoy. The system has never been tested with users.
- Decisions with consequences for people, such as playlist placement, royalties or artist
  promotion.
- Inferring anything about a person from their music taste.

## 3. Original project and new capabilities

**VibeMatch 1.0** scored each song (+2.0 genre match, +1.0 mood match, up to +1.0 energy closeness,
up to +0.5 acoustic fit), returned the top five with per-point explanations, and included a
weight-shift experiment and 20 tests.

**VibeMatch 2.0** keeps that scorer unchanged as the baseline and adds:

- **Guardrails** (`src/guardrails.py`): validation of preferences, `k` and the CSV catalog, with
  actionable error messages, duplicate removal, and warnings for preferences the catalog cannot
  satisfy together.
- **Independent evaluator** (`src/evaluator.py`): quality metrics computed from song attributes,
  never from the weighted score.
- **Bounded revision workflow** (`src/agent.py`): up to three evaluate → revise → re-evaluate →
  accept/reject cycles with an explicit acceptance policy.
- **Structured logging, an integrated CLI, and a reproducible 1.0-vs-2.0 evaluation script.**

## 4. Dataset and limitations

`data/songs.csv` holds 20 fictional songs (10 from the starter, 10 added in Module 3) with genre,
mood, energy, tempo, valence, danceability and acousticness.

| Genre | Songs | Genre | Songs |
|---|---|---|---|
| pop | 3 | lofi | 3 |
| rock | 2 | every other genre (12 genres) | 1 each |

- **Uneven representation.** Pop and lofi have three songs each; twelve of the fifteen genres have
  only one. A pop or lofi fan can get three genre matches; a classical, jazz or ambient fan can get
  at most one, so their lists are mostly filler from other genres. The evaluator reports this as
  `LIMITED_GENRE_COVERAGE` instead of hiding it.
- **Label gaps.** Some combinations don't exist (for example, no ambient song is angry and no
  ambient song is high energy). The system says so rather than pretending a match exists.
- **Fictional, culturally narrow data.** Genre and mood labels are single, hand-assigned words
  from a mostly Western genre vocabulary.
- **Unused features.** Tempo, valence and danceability are loaded and validated but not scored.

## 5. Algorithm and revision workflow

1. **Validate** catalog, `k` (1–10) and preferences. Invalid input returns readable errors.
2. **Baseline**: the original `recommend_songs()` with default weights.
3. **Evaluate** the baseline with the independent evaluator.
4. **Plan**: choose the first untried strategy that targets a current warning:
   - `rebalance_weights` (genre 1.0, mood 1.5, energy 2.0) for `ENERGY_MISMATCH`, `OFF_TARGET`,
     `MOOD_MISSING`;
   - `diversity_rerank` (−1.0 per earlier song by the same artist, −0.3 per earlier song of the
     same non-requested genre) for `REPEATED_ARTIST`, `REPEATED_GENRE`, `DUPLICATE_SONG`.
5. **Revise and re-evaluate.**
6. **Decide** with the acceptance policy:
   - H1–H3 (vs. baseline): no duplicates and same length; genre matches and mood matches may
     each drop by at most one.
   - Q1–Q3 (vs. current list): warnings strictly decrease; energy violations don't increase;
     mean energy gap rises by no more than 0.05.
7. **Stop** when no fixable warnings remain, no untried strategy applies, or three attempts have
   run. Return final songs, explanations, metrics, limitations and an audit trail.

Both strategies only re-rank songs that exist in the catalog. Neither creates or edits songs.

## 6. Reliability evaluation methodology

- **Independent metrics.** Genre and mood matches (each next to the achievable maximum for this
  catalog), mean and max energy distance, energy violations (> 0.30 from target), off-target songs,
  unique artists, max artist repeat, unique genres, duplicates. The evaluator never calls the
  scorer (enforced by a test), so a revision can't pass just by raising its own score.
- **Issue severity.** Warnings are fixable in principle; info issues are catalog limitations that
  are only reported.
- **Comparison.** `python -m src.evaluate` runs five profiles (High-Energy Pop, Chill Lofi,
  Intense Rock, Contradictory, Limited Coverage/Classical) through 1.0 and 2.0 and records, per
  metric, whether 2.0 is better, worse or the same. Output is deterministic and committed in
  `evaluation/`.
- **Automated tests.** 120 pytest tests (latest run: 120 passed), including tests that force
  harmful revisions and check they are rejected.

## 7. Measured results

From `evaluation/summary.md` (k=5):

| Profile | Revision | Decision | Warnings 1.0 → 2.0 | Notable metric changes |
|---|---|---|---|---|
| High-Energy Pop | not activated | n/a | 0 → 0 | none |
| Chill Lofi | activated | rejected | 1 → 1 | none; LoRoom repeat remains |
| Intense Rock | not activated | n/a | 0 → 0 | none |
| Contradictory (Ambient + Angry + 0.95) | activated | accepted | 1 → 0 | mean energy gap 0.156 → 0.030, energy violations 1 → 0; genre matches 1 → 0, unique genres 5 → 4 |
| Limited Coverage (Classical) | activated | rejected | 1 → 1 | none; *Neon Heartbreak* energy gap 0.44 remains |

**Interpretation.** 2.0 changed one list out of five. That change is a trade-off: it fixed the
energy mismatch 1.0 was known for, but removed the only song in the requested genre. Two attempts
were rejected because they didn't remove the issue they targeted. In these cases the honest output
is the original list plus a clear statement of what is wrong with it.

**What these numbers are not.** They measure agreement between a list and the stated preferences.
They are not measurements of listener satisfaction, accuracy against real listening behaviour, or
quality as judged by people. No user study was done.

## 8. Potential biases and filter bubbles

- **Genre dominance.** With default weights, a genre match alone (+2.0) is worth as much as a
  perfect mood and energy match combined (+2.0). A genre-matching song with the wrong mood and a
  poor energy fit can outrank a song that fits everything except the genre label, as the 1.0
  contradictory profile showed. The revision workflow softens this only when the evaluator detects a
  concrete problem.
- **Filter bubble.** The system only recommends what matches stated preferences. It never
  deliberately introduces new genres. Diversity re-ranking spreads artists and filler genres but
  does not challenge the user's stated taste.
- **Representation bias.** Users whose favourite genre has more catalog songs get measurably
  "better" lists (3/3 genre matches for pop vs. 1/1 for classical with four filler songs). That
  reflects the data, not the user.
- **Evaluator bias.** The evaluator's idea of "good" (exact labels, a 0.30 energy tolerance,
  artist variety) is a design choice. A listener who loves one artist might see repeated artists
  as a feature.

## 9. Limitations of deterministic scoring

- Same input, same output: reproducible and testable, but it can't learn, personalise over time
  or explore.
- Exact string matching: no partial credit for related genres or moods ("indie pop" vs. "pop",
  "melancholy" vs. "sad").
- Thresholds (energy tolerance, penalties, one-slot loss rule) were set by reasoning, not fitted
  to data, and a different choice changes outcomes. For example, a larger artist penalty would
  remove the Chill Lofi repeat at the cost of a lofi song.

## 10. Guardrails and failure handling

- Invalid preferences (empty input, unknown genre/mood with suggestions, energy outside 0–1,
  non-numeric/NaN/boolean energy, conflicting `energy` and `target_energy`, bad `likes_acoustic`)
  produce all error messages at once and exit code 2.
- Invalid `k` is rejected; `k` larger than the catalog is reduced with a note.
- Missing, empty or malformed catalog files produce a clear error and exit code 1. Malformed rows
  are skipped and reported. Duplicate songs are removed.
- If the evaluator or a revision step raises an exception, it is logged with a traceback and the
  user gets the baseline with a note, never a crash and never a silently unchecked "improved"
  list.
- Logging is structured (`event=... key=value`). At INFO level, only which preference fields were
  supplied is logged, not their values.

## 11. Ethical considerations

- **Honesty about what the system is.** It is a rule-based scorer with a rule-based checker. It is
  not a learned model and does not understand music or people. The README and this card say so.
- **No overclaiming.** Results are framed as rule-based agreement metrics, and failures and
  trade-offs are reported alongside successes.
- **Transparency to the user.** Every list shows why each song was chosen, what was changed, what
  could not be satisfied, and why a revision was kept or rejected.
- **Privacy.** No accounts, no stored history. Logs avoid preference values except at DEBUG.
- **Artist fairness (at scale).** In a real system, ranking rules like these decide which artists
  get heard. Genre dominance and catalog coverage would systematically favour well-represented
  genres.

## 12. Future improvements

- A larger, more diverse catalog, and partial credit for related genres and moods.
- Use valence, tempo and danceability, and support multi-genre and multi-mood profiles.
- Let users set how much diversity they want, instead of a fixed penalty.
- Validate the evaluator's notion of "good" against real user feedback (skips, likes, ratings)
  before claiming any satisfaction benefit.
- More revision strategies (e.g., related-genre substitution) with the same accept/reject
  discipline.

## 13. Responsible AI reflection

> **Julius: the items marked [TO COMPLETE] need your own answers before submission.** The facts
> listed under them are drawn from the development record (`ai_interactions.md` and git history)
> to help you answer. Please don't submit them unedited as your personal reflection.

**1. How I collaborated with AI during development.**

Facts from the record: for 2.0, I gave Claude Code (in VS Code) a detailed specification covering
goals, the workflow steps, guardrails, test areas, evaluation profiles, documentation and commit
milestones, plus rules (don't fabricate results, don't push without approval). Claude Code
inspected the existing repo, implemented the modules and tests, ran them, generated the evaluation
and drafted the docs. In Module 3, I asked Claude Code for a critical review before submission and
directed the fixes.

**[TO COMPLETE]** In your own words, how did you divide the work with the AI, and how did you check
its output?

**2. One AI suggestion that was accepted.**

Candidate examples from this session, if you agree with them:
(a) allowing a revision to lose at most one genre or mood match, which is what let the
Contradictory revision through;
(b) keeping the 1.0 output available via `--v1`/`--experiment` and making 2.0 the default CLI mode;
(c) a test that re-runs the README examples so the documentation can't drift from the real output.

**[TO COMPLETE]** Which suggestion did you accept, and why?

**3. One AI suggestion that was rejected or revised.**

Revisions that happened during development (see `ai_interactions.md`): the AI's first definition
of an "off-target" song counted label mismatches even when no energy target was given, and it was
narrowed to require an energy miss. Two of the AI's own new tests were wrong (one expected a
diversity note on a list where the revision had been correctly rejected) and were corrected
instead of changing the code to fit them. A commit message with a wrong test count was corrected
before anything was pushed.

**[TO COMPLETE]** Name a suggestion *you* rejected or changed (from this list or your own review),
and why.

**4. What the system does well and where it still struggles.**

Does well: rejects bad input with specific, fixable messages; never crashes on the tested failure
cases; explains every score; catches and reports energy mismatches, repeated artists and catalog
gaps; refuses revisions that don't measurably help; produces identical results on every run.

Struggles: it improved only one of five evaluation lists, and that improvement cost the requested
genre. It can't fix problems caused by the tiny catalog (Classical, Chill Lofi). Its idea of
"quality" is a set of hand-written rules that have never been checked against real listeners.

**5. What I learned about building and evaluating a reliable applied AI system.**

**[TO COMPLETE]** Your own takeaways.

---

## Appendix: VibeMatch 1.0 reflection (Module 3, unchanged)


What stood out to me most during this project was how much the weights affected the recommendations. Before working through the scoring system, I understood that recommendations depended on user preferences, but I hadn't really considered how much difference assigning two points to genre instead of one could make.

The contradictory profile was probably the clearest example. It asked for an angry, high-energy song, but the system recommended a calm ambient track simply because the genre matched. The program wasn't necessarily calculating anything incorrectly. It was following the rules we had given it. That helped me understand why designing the scoring logic matters just as much as writing the code.

I used Claude Code to help implement the recommender, generate tests, run the evaluation profiles, and document the results. The score explanations were particularly useful because they let me connect each ranking to the actual rules instead of just accepting the output. For example, they showed that *Spacewalk Thoughts* topped the contradictory profile only because of its +2.00 genre match, since its energy only earned +0.33.

Another thing I found interesting was how limitations appeared even with only 20 songs. Some genres had more options than others, and certain songs repeatedly appeared in the recommendations. It made me realize that recommendation quality depends not only on the algorithm but also on the data available.

If I extended the project, I would want users to choose multiple genres and moods instead of being limited to one of each. The weights can already be changed in code, so I would also add an interactive interface where users could adjust them and decide whether genre, mood, or energy matters most to them.

Overall, this project gave me a better understanding of how a relatively simple Python algorithm can produce personalized recommendations, and why those recommendations still need to be evaluated instead of assuming the highest score always means the best choice.
