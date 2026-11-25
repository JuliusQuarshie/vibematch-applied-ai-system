# AI Interactions Log

This document explains how I used AI tools during the development of VibeMatch, from the original Module 3 Music Recommender Simulation to the final VibeMatch 2.0 Applied AI System.

It records the major prompts, implementation work, corrections, testing, and decisions made during development.

---

## VibeMatch 2.0: Applied AI System (Final Project)

**AI Tool:** Claude Code (Claude Opus 5.5) through the VS Code extension.

**Development Date:** November 24, 2026.

### 1. How I Used AI

For my final project, I decided to extend my previous music recommendation system rather than build something entirely new.

VibeMatch 1.0 already ranked songs using genre, mood, energy, and acoustic preferences. However, the original version did not independently evaluate whether its recommendations were suitable or attempt to correct weak results.

I wanted VibeMatch 2.0 to go beyond generating recommendations by introducing reliability evaluation, guardrails, and a workflow that could check and revise its own output.

I used Claude Code as my AI coding assistant to help implement these improvements.

### 2. Main Development Prompt

I provided Claude Code with a detailed specification covering the entire project.

The prompt included the following requirements:

1. Extend VibeMatch 1.0 into an explainable, self-checking music recommender without misrepresenting it as a trained language model.
2. Preserve the original dataset, scoring engine, recommendation explanations, CLI functionality, and automated tests.
3. Implement an evaluation and revision workflow that checks recommendation quality independently of the weighted scoring algorithm.
4. Add input validation, error handling, logging, and safeguards against invalid or conflicting preferences.
5. Implement automated tests covering the new components, including situations where attempted improvements should be rejected.
6. Compare VibeMatch 1.0 and VibeMatch 2.0 using at least five different user profiles.
7. Create a Mermaid system architecture diagram.
8. Produce professional README documentation with reproducible examples.
9. Update the Model Card to explain the system's reliability, limitations, potential biases, and ethical considerations.
10. Maintain an AI interaction log documenting the development process.
11. Organize the work into meaningful Git commits without pushing changes before my approval.
12. Run the tests, verify the results, and report any unresolved problems.

I also emphasized that the evaluation results needed to come from actual program execution rather than fabricated examples.

### 3. What Claude Code Implemented

Claude inspected the original repository before making changes.

The initial 20 automated tests passed, establishing that the original recommender was functioning before the new components were introduced.

The following components were then implemented.

| Component | AI-Assisted Implementation |
|---|---|
| `src/guardrails.py` | Input validation, catalog checks, duplicate handling, and error messages |
| `src/logging_config.py` | Structured logging for application events and failures |
| `src/evaluator.py` | Independent recommendation-quality metrics |
| `src/agent.py` | Bounded evaluation, revision, and acceptance workflow |
| `src/main.py` | Integrated VibeMatch 2.0 CLI with backward-compatible options |
| `src/evaluate.py` | Reproducible comparison of VibeMatch 1.0 and 2.0 |
| `evaluation/results.json` | Machine-readable results from the evaluation |
| `evaluation/summary.md` | Human-readable evaluation findings |
| `diagrams/architecture.mmd` | Mermaid diagram describing the system architecture |
| `tests/` | Additional automated tests for the new functionality |
| `README.md` | Setup instructions, architecture, sample outputs, and evaluation |
| `model_card.md` | Responsible AI documentation, testing results, and limitations |

The original weighted scoring engine was preserved as the baseline so that the upgraded system could be compared against it.

### 4. Testing and Validation

Claude Code ran the automated tests and checked the application at different stages of development.

**Original project verification**

Before implementing the extensions, the existing test suite was executed.

```text
20 passed
```

**Final project verification**

The completed test suite contained 120 tests, consisting of the original 20 tests and 100 additional tests.

```bash
python -m pytest
```

Reported result:

```text
120 passed
```

The tests covered input validation, scoring compatibility, evaluator metrics, revision decisions, rejection of harmful changes, error handling, CLI behavior, and reproducibility.

**Backward compatibility**

The original Module 3 CLI behavior was compared with the new `--v1` and `--experiment` options.

The outputs matched the original version, confirming that the baseline functionality had been preserved.

**Evaluation verification**

The following command generated the comparison results:

```bash
python -m src.evaluate
```

The results were recorded in:

- `evaluation/results.json`
- `evaluation/summary.md`

An automated test checks whether the committed evaluation results match the output produced by the code.

**Architecture verification**

The Mermaid architecture diagram and the README's embedded diagram were checked using `mermaid.parse` with Mermaid 11.4.1.

A deliberately invalid diagram was also tested to confirm that the validation process could detect syntax errors.

**Documentation verification**

The README includes executable sample commands, and `tests/test_readme_examples.py` checks that the examples remain consistent with the actual program behavior.

### 5. AI Suggestions That Needed Correction

Using an AI coding assistant helped speed up development, but some generated decisions and tests still needed to be corrected.

The development process included the following issues.

**Off-target evaluation metric**

An early version of the evaluator classified songs as off-target whenever their genre and mood did not match, even if the user had not specified an energy target.

This risked identifying unavoidable catalog limitations as problems the revision workflow could fix.

The definition was revised to require both a label mismatch and an energy difference outside the accepted tolerance.

This made the metric more consistent with its documented purpose.

**Incorrect automated test expectations**

During development, two of the 115 tests initially failed because their expected results were incorrect.

One test treated three out of five songs as more than 60%, even though that is exactly 60%.

Another expected a diversity-related note even though the proposed revision had correctly been rejected.

The test expectations were corrected rather than modifying working application logic merely to make those tests pass.

An additional test was introduced to verify the rejected-revision behavior.

**Unsuccessful diversity revision**

The initial evaluation showed that the diversity strategy did not eliminate the repeated artist in the Chill Lofi recommendations.

Increasing the diversity penalty could potentially have produced an accepted revision, but that would have meant tuning the revision strategy after seeing the results.

Instead, the result was preserved and documented as a limitation.

**Incorrect commit message**

One early local commit message reported 41 guardrail tests when the actual number was 37.

The message was corrected before the changes were pushed.

**Unverified first-person claims**

Some generated documentation initially described AI-made implementation decisions as though I had personally made them.

These statements were revised so the documentation could distinguish my project direction and evaluation decisions from Claude Code's implementation work.

### 6. AI Suggestions I Accepted or Revised

The independent evaluator and the rule that a revision is kept only when it measurably improves the results were not AI suggestions. They were requirements in my original prompt. The suggestions below came from Claude Code during development.

**Suggestion I accepted: Tests that verify the README examples**

Claude Code added `tests/test_readme_examples.py`, which re-runs every CLI example shown in the README and checks that the documented output matches the actual program output.

I kept this approach because it makes the documentation verifiable. Sample outputs can easily become outdated when the code changes. With this test in place, any change to the recommendations, explanations, or audit trail makes the test suite fail until the README is updated.

**Suggestion I revised: AI-generated documentation**

Claude Code drafted the README, Model Card, and this log. I reviewed the drafts and requested changes to generic language, unfinished placeholders, exaggerated first-person claims, and wording that made it sound like Claude had independently owned the entire project.

I wanted the documentation to reflect my actual role in directing and reviewing an AI-assisted project: I defined the requirements and reviewed the results, while Claude Code helped implement, test, and document the system.

**Another decision: Preserve the original recommendation system**

The original VibeMatch scoring implementation stays available through the `--v1` and `--experiment` options.

This made it possible to compare the old and new versions using the same dataset and user preferences. It also shows that the final project extends my Module 3 work rather than replacing it.

### 7. What the Evaluation Revealed

The full comparison of the five profiles is in `evaluation/summary.md`. In short, only the contradictory profile received an accepted revision: mean energy distance fell from 0.156 to 0.030, but the revised list lost the only song matching the requested ambient genre. The Chill Lofi and Limited Coverage revisions were rejected because they did not reduce the warning count, and the other two profiles needed no revision.

This showed me that improving one metric can introduce a trade-off elsewhere, and that rejecting a proposed change is sometimes the more reliable outcome.

### 8. My Role and What I Learned

My role in this project was to define the intended system, provide implementation constraints, guide the AI-assisted workflow, and review the development results against the assignment requirements.

Claude Code helped implement the Python modules, generate automated tests, execute evaluation commands, and draft documentation.

What I found most interesting was how the new evaluation layer changed the way I thought about recommendations.

During Module 3, I focused on scoring songs and understanding why some ranked higher than others.

For this final project, I wanted the system to go further by recognizing when those rankings might be misleading and checking whether an alternative would actually improve the results.

The evaluation also made it clear that reliability does not mean every problem can be automatically fixed. Sometimes the available data is simply too limited.

This project helped me better understand how validation, independent evaluation, feedback, and transparent reporting contribute to a more reliable applied AI system.

---

## Module 3: Agentic Workflow (SF8)

### What Task Did I Give the Agent?

For the original Music Recommender Simulation, I asked Claude Code to complete the five required development phases in a coordinated workflow.

The work involved understanding the starter repository, extending the dataset, implementing the scoring algorithm, creating the CLI, evaluating different user profiles, running a scoring experiment, writing tests, and preparing the README and Model Card.

### Prompts Used

I provided a detailed prompt containing the implementation requirements.

The scoring rules included:

- +2.0 points for a genre match.
- +1.0 point for a mood match.
- Energy similarity using `max(0, 1 - abs(song_energy - target_energy))`.

The prompt also required automated tests, documentation based on actual outputs, and preservation of the starter project files.

I instructed the agent not to fabricate test results or push changes without approval.

### What Did the Agent Generate or Change?

**Dataset**

Claude Code added 10 fictional songs to `data/songs.csv`, expanding the catalog from 10 to 20 songs while preserving the original CSV structure.

**Recommendation engine**

The `src/recommender.py` module was updated with:

- `load_songs()`
- `score_song()`
- `recommend_songs()`
- The existing `Recommender` class
- Configurable scoring weights

**CLI application**

The `src/main.py` import was corrected to support execution through:

```bash
python -m src.main
```

Four evaluation profiles and a `--experiment` option were also added.

**Automated testing**

The agent created `tests/test_scoring.py` with 18 additional tests and added `pytest.ini` to support test discovery.

The completed Module 3 project passed 20 tests.

**Documentation**

Claude Code assisted with the README, Model Card, and AI interaction log using actual outputs from the recommender.

### What Did I Review or Fix?

The AI-assisted implementation process identified an import problem in the starter application that prevented the CLI from running correctly.

Claude Code also corrected a leftover placeholder in the recommender before final verification.

Before submitting Module 3, I requested a critical review of the repository.

Based on that review, I directed several documentation corrections:

- Removing a leftover AI comment.
- Correcting an inaccurate statement about how CLI output was copied into the README.
- Fixing a contradiction involving adjustable scoring weights.
- Revising overly generic language.
- Restoring natural first-person reflections while keeping AI assistance accurately documented.

This review process helped ensure that the final submission accurately reflected the implemented project rather than simply accepting every generated statement.

---

## Final Note

AI assistance was an important part of both projects, especially for implementation, testing, debugging, and documentation.

However, the purpose of using AI was not just to generate code. I wanted to understand how the recommendation system worked, how its outputs could be evaluated, and why some proposed improvements needed to be rejected.

VibeMatch 2.0 builds on that process by making reliability evaluation and revision decisions part of the application itself.