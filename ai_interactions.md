# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agentic Workflow (SF8)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

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
- Commands run: `python -m src.main`, `python -m src.main --experiment`, `python -m pytest` (20 passed). The CLI output in the README was pasted in by script from the saved terminal output rather than retyped.

**What did you verify or fix manually?**

- Agent self-checks: the starter `main.py` import would have crashed under `python -m src.main`; the agent found and fixed it. It also removed a leftover placeholder line it had written in `Recommender.recommend` before running anything.
- <!-- Julius: add what you personally checked, e.g. re-ran the commands, read the scoring code, compared README output to your terminal, edited the reflection. -->

---

## Design Pattern (SF10)

> Document how AI helped you choose or implement a design pattern.

**Which design pattern did you use?**

<!-- e.g., Strategy, Factory, Observer, etc. -->

**How did AI help you brainstorm or implement it?**

<!-- Describe the conversation or suggestions that led to your decision -->

**How does the pattern appear in your final code?**

<!-- Point to the relevant class or method -->
