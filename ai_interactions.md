# AI Interactions Log

This log records how AI assistance was used to build VibeMatch. It covers the final project
(VibeMatch 2.0) and keeps the original Module 3 entry below unchanged. Only real interactions
are recorded; nothing here is a reconstructed or invented conversation.

---

## VibeMatch 2.0: Applied AI System (final project)

**Tool:** Claude Code (model: Claude Opus 5.5) in the VS Code extension, working directly in this
repository. A single working session, 2026-11-24.

### Major development prompt

One long specification prompt from me, with twelve sections:

1. Project goal: extend VibeMatch into an explainable, self-checking system; be transparent that
   the core is weighted content-based scoring, not a language model.
2. Preserve the dataset, loader, scorer, explanations, CLI, profiles and existing tests.
3. Implement a 10-step evaluate-and-revise workflow with independent metrics (no circular
   evaluation), bounded attempts, and honest handling of preferences the catalog can't satisfy.
4. Guardrails for empty/unknown/out-of-range input, malformed or empty CSVs, invalid `k`,
   duplicates, conflicting preferences and evaluation failures, plus logging without personal data.
5. Tests for all new behaviour, including rejected revisions and bounded termination.
6. A reproducible 1.0 vs 2.0 evaluation on at least five profiles, with no fabricated results.
7. to 10. A Mermaid architecture diagram, README, model card and this log.
11. Logical local commits, and no push without approval.
12. A final verification checklist and report.

### What the AI did

| Area | Work |
|---|---|
| Inspection | Read the source, tests, data, README, model card and this log; installed `pytest` in a local `.venv` and confirmed the original 20 tests passed before any change. |
| Guardrails | Wrote `src/guardrails.py` and `src/logging_config.py`; added an optional, backward-compatible `skipped` argument to `load_songs()`. |
| Evaluator | Wrote `src/evaluator.py` with metrics computed from song attributes only. |
| Workflow | Wrote `src/agent.py` (strategies, acceptance policy H1–H3 / Q1–Q3, bounded loop, failure handling). |
| CLI | Rewrote `src/main.py`: 2.0 is the default; `--v1` and `--experiment` keep the original behaviour. |
| Evaluation | Wrote `src/evaluate.py` and generated `evaluation/results.json` and `evaluation/summary.md`. |
| Tests | Added 100 tests across `test_guardrails.py`, `test_evaluator.py`, `test_agent.py`, `test_cli.py`, `test_evaluate_script.py` and `test_readme_examples.py`. |
| Docs | Wrote `diagrams/architecture.mmd`, rewrote `README.md` and `model_card.md`, and updated this file. |

### Validation evidence (commands actually run)

- `python -m pytest`: the original suite passed (20) before changes. The final run passed 120
  tests (20 original + 100 new).
- The original `python -m src.main` and `--experiment` output from the last Module 3 commit was
  diffed against the new `--v1` and `--experiment` output, and they were identical.
- Milestone commits were checked out into a temporary git worktree and their tests run there, so
  each commit is self-consistent (guardrails milestone: 57 passed).
- `python -m src.evaluate` was run and its output committed. A test checks that the committed files
  still match what the code produces.
- `diagrams/architecture.mmd` and the README's inline diagram were parsed with `mermaid.parse`
  (mermaid 11.4.1, run in a temporary Node.js install outside the repo). A deliberately broken
  diagram was rejected by the same check, confirming the check works.
- Every README sample run is re-executed by `tests/test_readme_examples.py`.

### AI suggestions that were revised during development

These are corrections that happened during the session. They are recorded because they show
where AI output needed checking.

- **Off-target metric.** The first version counted a song as off-target whenever its genre and
  mood didn't match, even with no energy target. That would have flagged unavoidable filler songs
  in sparse genres as fixable problems. It was narrowed to "no label match **and** outside the
  energy tolerance", matching the documented definition.
- **Two wrong tests.** After the first test run, 2 of 115 tests failed. Both were test mistakes,
  not code bugs: one assumed 3 of 5 songs was "more than 60%", and one expected a diversity note
  on a list where the revision had (correctly) been rejected. The tests were fixed and a new test
  was added for the rejected case. The code was not changed to fit the tests.
- **Results not tuned.** The first evaluation showed the diversity strategy failing to remove
  Chill Lofi's repeated artist. The penalty could have been raised to produce an "accepted"
  result. It was left as designed and the failure is reported in the README and model card.
- **Commit message accuracy.** The first milestone commit message stated the wrong number of
  guardrail tests (41 instead of 37). The local, unpushed message was corrected.
- **First-person claims.** Draft README text described decisions in my voice ("I chose…") that
  the AI had made. It was rewritten in a neutral voice, and the personal reflection was left for
  me to write.

### Suggestions accepted or rejected by me

**[TO COMPLETE: Julius]** Record which AI proposals you reviewed and kept or changed, for example
the one-slot relevance-loss rule, making 2.0 the default CLI mode, removing the unused `pandas`
and `streamlit` from `requirements.txt`, or deleting the empty "Design Pattern (SF10)" template
section from this file.

---

## Module 3: Agentic Workflow (SF8)

**What task did you give the agent?**

I asked Claude Code (running in VS Code) to complete all five phases of the project in one pass: understand the starter, extend the dataset, implement the recommender and CLI, run evaluation profiles and a weight-shift experiment, write tests, and fill in the README and model card using only real program output.

**Prompts used:**

One long prompt listing the five phases, the scoring rule (+2.0 genre, +1.0 mood, `max(0, 1 - |song_energy - target_energy|)` for energy), required tests, and rules: don't fabricate output or test results, don't delete starter files, and don't push without approval.

**What did the agent generate or change?**

- `data/songs.csv` — appended 10 fictional songs (ids 11–20) using the existing header.
- `src/recommender.py` — implemented `load_songs`, `score_song`, `recommend_songs`, and the starter `Recommender` class; added `DEFAULT_WEIGHTS` and an optional `weights` argument for experiments.
- `src/main.py` — fixed the import (`from recommender` → `from src.recommender`) so `python -m src.main` runs; added 4 profiles and an `--experiment` flag.
- `tests/test_scoring.py` (new, 18 tests) and `pytest.ini` (new, so `pytest` can import `src`).
- `README.md`, `model_card.md`, this file.
- Commands run: `python -m src.main`, `python -m src.main --experiment`, `python -m pytest` (20 passed).

**What did you verify or fix manually?**

- Agent self-checks: the starter `main.py` import would have crashed under `python -m src.main`; the agent found and fixed it. It also removed a leftover placeholder line it had written in `Recommender.recommend` before running anything.
- I asked Claude Code for a critical review before submission, then directed the fixes: removing a leftover AI comment, correcting a claim about how the CLI output was copied into the README, fixing a contradiction in the model card about adjustable weights, and making sure the docs describe the AI assistance accurately.

