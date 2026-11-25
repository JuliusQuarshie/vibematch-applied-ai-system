# Model Card: VibeMatch 2.0

## 1. System Name

**VibeMatch 2.0** is an explainable, self-checking music recommendation system. It extends **VibeMatch 1.0**, my CodePath AI110 Module 3 Music Recommender Simulation.

**Original Project:** https://github.com/JuliusQuarshie/ai110-module3show-musicrecommendersimulation-starter

**Final Project Repository:** https://github.com/JuliusQuarshie/vibematch-applied-ai-system

---

## 2. Intended and Non-Intended Uses

### Intended Uses

- Demonstrate how a basic music recommender can be improved through input validation, independent evaluation, and a self-correction workflow.
- Explore how scoring weights, available song data, and evaluation rules influence recommendations.
- Show how an automated system can evaluate its own output and decide whether to accept or reject changes.
- Serve as an educational project and portfolio demonstration of applied AI engineering concepts.

### Non-Intended Uses

VibeMatch 2.0 is not intended to replace an actual music streaming recommendation system.

The application uses a small catalog of fictional songs and has not been tested with real listeners. It cannot accurately predict whether someone will enjoy a particular song.

It should not be used to make decisions affecting artists, such as determining playlist promotion, royalties, or compensation.

The system is also not designed to infer personal characteristics from someone's music preferences.

---

## 3. Original Project and New Capabilities

### VibeMatch 1.0 — Original System

My original Module 3 project was a content-based music recommender built with Python.

The system compared songs against user preferences and assigned points using these rules:

- **+2.0 points** for a matching genre.
- **+1.0 point** for a matching mood.
- **Up to +1.0 point** based on energy similarity.
- **Up to +0.5 points** for acoustic similarity.

The recommender ranked songs according to their scores and displayed the top five with explanations.

It also included an experiment comparing different scoring weights and a test suite containing 20 automated tests.

### VibeMatch 2.0 — Applied AI Extension

For the final project, I extended the original recommendation system with several new components.

**Input Validation and Guardrails**

The `src/guardrails.py` module validates user preferences, checks the catalog, identifies duplicate songs, and handles invalid inputs.

**Independent Reliability Evaluation**

The `src/evaluator.py` module evaluates recommendation quality using metrics calculated from song attributes rather than relying on the original weighted scores.

**Self-Correction Workflow**

The `src/agent.py` module introduces a bounded workflow that evaluates recommendations, attempts improvements, checks the revised results, and decides whether to accept or reject each change.

**Logging and Reproducible Evaluation**

The system includes structured logging, an integrated command-line interface, and a reproducible evaluation script comparing VibeMatch 1.0 with VibeMatch 2.0.

These additions allow the system to identify weaknesses in its recommendations instead of assuming that the highest-scoring songs are always the most suitable.

---

## 4. Dataset and Limitations

The dataset is stored in `data/songs.csv` and contains **20 fictional songs**.

The original starter dataset contained 10 songs, and another 10 were added during Module 3 to introduce more genres, moods, and energy levels.

Each song includes attributes such as genre, mood, energy, tempo, valence, danceability, and acousticness.

### Genre Distribution

| Genre | Number of Songs |
|---|---:|
| Pop | 3 |
| Lofi | 3 |
| Rock | 2 |
| Other genres (12 genres) | 1 each |
| **Total** | **20** |

### Dataset Limitations

**Uneven representation**

Pop and lofi each have three songs, while twelve genres have only one.

This means someone requesting pop or lofi has more matching options than someone requesting classical, jazz, or ambient music.

VibeMatch 2.0 reports this as a `LIMITED_GENRE_COVERAGE` limitation. It is informational: it is shown to the user but does not trigger a revision, because no re-ranking can add songs that aren't in the catalog.

**Missing combinations**

Certain combinations of genre, mood, and energy do not exist in the dataset.

For example, there is no ambient song with an angry mood and high energy.

Instead of pretending the catalog contains a suitable match, the system reports these limitations.

**Limited musical diversity**

All songs are fictional, and the genre labels represent only a small range of musical traditions.

**Unused features**

Tempo, valence, and danceability are included in the dataset but are not currently used in calculating recommendation scores.

---

## 5. Algorithm and Revision Workflow

VibeMatch 2.0 follows a structured process for generating and evaluating recommendations.

### Step 1: Validate Input

The system checks the user's preferences, requested number of songs, and available catalog data.

Invalid inputs produce readable error messages rather than causing ordinary input errors to crash the program.

The requested number of recommendations, `k`, must be between 1 and 10.

### Step 2: Generate Baseline Recommendations

The system uses the original VibeMatch 1.0 scoring algorithm to rank songs.

This creates the initial recommendation list.

### Step 3: Evaluate Recommendation Quality

The independent evaluator checks the recommendations for issues such as:

- Poor energy matches.
- Missing preferred moods.
- Repeated artists or genres.
- Duplicate songs.
- Limited catalog coverage.
- Songs that do not closely match the stated preferences.

### Step 4: Plan an Improvement

If the evaluator identifies a problem that may be fixable, the system selects an appropriate revision strategy.

**Rebalance Weights**

For energy mismatches, off-target recommendations, or missing preferred moods, the system can use:

| Feature | Revised Weight |
|---|---:|
| Genre | 1.0 |
| Mood | 1.5 |
| Energy | 2.0 |

This gives more importance to mood and energy similarity.

**Diversity Re-Ranking**

For repeated artists, repeated genres, or duplicate songs, the system can apply ranking penalties.

- **−1.0 point** for another song from an artist already selected.
- **−0.3 points** for another song from the same non-requested genre.

These penalties encourage more variety when applicable.

### Step 5: Evaluate the Revised Results

The system calculates the same reliability metrics for the new recommendations.

### Step 6: Accept or Reject the Revision

A revision is accepted only if it meets the defined requirements.

The system checks that:

- No duplicate songs are introduced.
- The recommendation list keeps the expected length.
- Genre and mood matches do not each decrease by more than one.
- The number of warnings decreases.
- Energy violations do not increase.
- Mean energy distance does not increase by more than 0.05.

If the revision fails these conditions, the system keeps the previous recommendation list.

### Step 7: Stop and Return Results

The workflow stops when:

- No fixable issues remain.
- No appropriate unused strategy is available.
- Three revision attempts have been completed.

The system then returns the recommendations, explanations, quality metrics, limitations, and an audit trail.

**An important design decision is that the system never invents new songs during revision.** It only re-ranks songs already present in the catalog.

---

## 6. Reliability Evaluation Methodology

I evaluated VibeMatch 2.0 using several measures that are independent of the original recommendation score.

### Evaluation Metrics

- Number of matching genres.
- Number of matching moods.
- Average energy distance from the user's target.
- Maximum energy distance.
- Number of energy violations.
- Number of off-target recommendations.
- Number of unique artists.
- Maximum artist repetition.
- Number of unique genres.
- Number of duplicate songs.

The evaluator does not call the original scoring function when calculating these metrics.

This separation is important because a revised ranking should not automatically be considered better simply because its weighted score increased.

### Evaluation Process

The evaluation script compares VibeMatch 1.0 and VibeMatch 2.0 using five profiles:

1. High-Energy Pop.
2. Chill Lofi.
3. Intense Rock.
4. Contradictory Preferences.
5. Limited Genre Coverage — Classical.

The evaluation can be reproduced using:

```bash
python -m src.evaluate
```

Results are saved in the `evaluation/` directory.

### Automated Tests

The final system includes **120 automated pytest tests** covering the recommendation engine, guardrails, evaluator, revision workflow, and failure handling.

The latest reported test run completed successfully:

```text
120 passed
```

The tests also include scenarios where a proposed revision makes recommendations worse and must be rejected.

---

## 7. Measured Results

The following results are from `evaluation/summary.md`, using five recommendations per profile.

| Profile | Revision Attempted | Final Decision | Warnings (Before → After) |
|---|---|---|---|
| High-Energy Pop | No | Not needed | 0 → 0 |
| Chill Lofi | Yes | Rejected | 1 → 1 |
| Intense Rock | No | Not needed | 0 → 0 |
| Contradictory | Yes | Accepted | 1 → 0 |
| Limited Coverage — Classical | Yes | Rejected | 1 → 1 |

### High-Energy Pop

The original recommendations did not trigger any reliability warnings.

No revision was necessary.

### Chill Lofi

The evaluator identified repeated artists and attempted a revision.

However, the proposed change did not reduce the warning count (1 → 1), so it was rejected.

The repetition involving LoRoom remained in the final recommendations.

### Intense Rock

The original recommendations satisfied the evaluator's requirements.

No revision was necessary.

### Contradictory Preferences

This profile requested ambient music, an angry mood, and energy of 0.95.

The original system ranked a calm ambient song highly because the genre matched.

VibeMatch 2.0 identified the energy mismatch and accepted a revised recommendation list.

The results changed as follows:

| Metric | VibeMatch 1.0 | VibeMatch 2.0 |
|---|---:|---:|
| Reliability warnings | 1 | 0 |
| Mean energy distance | 0.156 | 0.030 |
| Energy violations | 1 | 0 |
| Genre matches | 1 | 0 |
| Unique genres | 5 | 4 |

This was a meaningful improvement in energy matching.

However, it also introduced a trade-off because the revised list no longer included a song matching the requested ambient genre.

### Limited Genre Coverage — Classical

The evaluator identified a limitation caused by the small dataset.

An attempted revision was rejected because it did not reduce the warning count (1 → 1).

The final list retained a song with an energy gap of 0.44.

### Overall Findings

VibeMatch 2.0 accepted a revision for **one out of five evaluated profiles**.

Two attempted revisions were rejected, while two profiles did not require changes.

These results show that the system does not automatically accept every revision.

However, they do not establish that VibeMatch 2.0 is more enjoyable for real listeners.

The evaluation measures agreement with predefined rules and user preferences, not actual listener satisfaction.

---

## 8. Potential Biases and Filter Bubbles

### Genre Dominance

In the original scoring system, matching the genre awards two points.

This is equal to the maximum combined score for mood and energy.

As a result, a song can rank highly simply because its genre matches, even if its energy and mood do not.

The revised workflow attempts to address this problem when the evaluator detects a significant mismatch.

### Filter Bubbles

The system primarily recommends songs matching the preferences provided by the user.

It does not intentionally introduce unfamiliar musical styles.

Diversity re-ranking can reduce some repetition, but it does not solve the broader problem of repeatedly recommending similar music.

### Representation Bias

Some genres are represented by more songs than others.

A pop listener has more genre-matching options than someone requesting classical music.

This difference comes from the dataset, not from anything about the users.

### Evaluator Bias

The system's definition of recommendation quality is based on predefined rules.

For example, the evaluator considers repeated artists a possible problem.

However, someone who particularly enjoys one artist might prefer receiving several songs from that artist.

This means the evaluator's rules are not universally correct for every listener.

---

## 9. Limitations of Deterministic Scoring

VibeMatch 2.0 uses deterministic scoring, meaning the same inputs and dataset produce the same outputs.

This makes the system easier to test and reproduce.

However, it has several limitations.

**No learning from experience**

The system does not learn from listening habits, likes, or skips.

**Exact matching**

Related genres and moods do not receive partial credit.

For example, `indie pop` and `pop` are treated as different genres.

**Manually selected thresholds**

The energy tolerance, diversity penalties, and revision acceptance rules were chosen through reasoning rather than trained using real listener data.

Changing these values could produce different outcomes.

For example, applying a stronger artist repetition penalty could improve diversity while removing a song that otherwise closely matches the user's preferences.

---

## 10. Guardrails and Failure Handling

VibeMatch 2.0 includes guardrails designed to make the application more reliable.

### Input Validation

The system checks for:

- Empty preferences.
- Unknown genres or moods.
- Energy values outside the 0–1 range.
- Non-numeric or invalid energy values.
- Conflicting `energy` and `target_energy` values.
- Invalid acoustic preferences.
- Invalid values of `k`.

Invalid preferences generate clear messages and exit code `2`.

### Dataset Validation

The system handles missing, empty, or malformed CSV files.

Malformed rows can be skipped and reported, while duplicate songs are removed.

Catalog-level failures produce readable messages and exit code `1`.

If `k` exceeds the available number of songs, the requested count is reduced with an explanation.

### Evaluation Failure Handling

If the evaluator or a revision step raises an unexpected exception, the system records the error and returns the baseline recommendations with a warning.

This prevents a failed revision from being presented as a successful improvement.

### Structured Logging

The application uses structured event logging.

At the INFO level, it records which preference fields were supplied without logging their actual values.

This allows the system to track important actions while limiting unnecessary collection of user information.

---

## 11. Ethical Considerations

### Transparency

VibeMatch 2.0 explains how recommendations are generated and why proposed revisions are accepted or rejected.

Users can see the reasoning behind the recommendations rather than receiving unexplained results.

### Honest Representation

The system uses a rule-based recommendation engine and a rule-based evaluator.

It is not a trained machine-learning model or a large language model, and it does not understand music in the way people do.

Its advanced workflow demonstrates applied AI engineering concepts through deterministic evaluation and self-correction.

### Avoiding Misleading Claims

The evaluation results are presented as measurements of rule-based recommendation quality.

They are not treated as evidence that real users would prefer the revised recommendations.

### Privacy

The system does not require accounts or store listening histories.

Its standard logs avoid recording the actual values of music preferences.

### Fairness

If a similar ranking system were used on a real platform, the dataset and algorithm could influence which artists receive exposure.

Uneven genre representation and overly restrictive scoring rules could disadvantage some artists or musical styles.

---

## 12. Future Improvements

If I continued developing VibeMatch, I would consider several improvements.

- Expand the dataset with more songs from different musical styles and cultures.
- Support partial matching between related genres and moods.
- Include tempo, valence, and danceability in the scoring algorithm.
- Allow users to select multiple genres and moods.
- Give users control over how much recommendation diversity they want.
- Collect optional feedback through likes, skips, or ratings.
- Compare the evaluator's quality measurements with actual human preferences.
- Add additional revision strategies while preserving the existing acceptance and rejection checks.

A future version could also include a graphical interface that allows users to adjust their preferences and view the system's evaluation results interactively.

---

## 13. Responsible AI Reflection

### 1. How I Collaborated with AI During Development

I used Claude Code as my coding assistant to extend my original Music Recommender Simulation into VibeMatch 2.0. Instead of starting another project from scratch, I wanted to build on what I had already developed in Module 3.

I provided Claude with specific requirements for the system, including input validation, reliability evaluation, an improvement workflow, automated testing, and documentation. Claude helped implement these components, execute the tests, and generate the evaluation results.

My role involved defining what I wanted the system to accomplish, guiding the implementation requirements, reviewing its progress, and checking whether the results aligned with the assignment. I also used AI to help identify gaps in the documentation and ensure the project did not simply look complete without demonstrating actual functionality.

### 2. One AI Suggestion I Accepted

One suggestion I accepted was Claude Code's addition of an automated test, `tests/test_readme_examples.py`, that re-runs the CLI examples shown in the README and checks that the documented output matches what the program actually prints.

I kept this approach because it makes the documentation verifiable. Sample outputs in a README can easily become outdated when the code changes, and nobody notices until a reviewer runs the command and gets something different. With this test, if the recommendations, explanations, or audit trail change, the test suite fails until the README is updated. That fit the goal of the project, which was to make the system's claims checkable instead of just trusting them.

### 3. One AI Suggestion I Revised

The main thing I revised was the AI-generated documentation. Claude Code drafted the README, Model Card, and AI interaction log, and I reviewed those drafts before accepting them.

I requested changes to generic language, unfinished placeholders, exaggerated first-person claims, and wording that made it sound like Claude had independently owned the entire project. Some drafts described decisions in my voice that I had not actually made, while others made the AI sound like the only one responsible for the work.

I wanted the documentation to reflect my actual role: I defined the requirements, directed the work, and reviewed the results, while Claude Code helped implement, test, and document the system. Revising the drafts was important because accurate documentation is part of what makes an AI-assisted project trustworthy.

### 4. What the System Does Well and Where It Still Struggles

I think VibeMatch 2.0 is stronger than the original version because it does more than recommend songs. It can identify problems in its recommendations, explain those problems, and attempt corrections without blindly accepting every change.

The automated tests also help establish that the system behaves consistently under different conditions. The final implementation passed 120 tests, including checks for invalid inputs, evaluation failures, and harmful revisions.

However, the evaluation results showed that the system still has limitations. Only one of the five evaluated profiles received an accepted revision. For the contradictory profile, the revised recommendations had a much better energy match, but the system lost the only song matching the user's requested genre.

This demonstrates that improving one aspect of a recommendation does not necessarily improve the entire experience.

The dataset is another limitation. With only 20 fictional songs, there are situations where the system simply cannot find enough suitable recommendations, regardless of how the algorithm is adjusted.

### 5. What I Learned About Building and Evaluating a Reliable Applied AI System

The biggest lesson I took from this project is that getting a system to produce an output is different from making sure that output is useful and reliable.

In Module 3, I focused mainly on understanding how features and weights affected song rankings. This final project introduced another layer: evaluating those rankings and deciding whether a proposed improvement should actually be accepted.

I found the contradictory profile particularly interesting. The original system recommended a calm ambient song for someone requesting angry, high-energy music because the genre match carried more weight. VibeMatch 2.0 identified that energy mismatch and produced a different recommendation. However, the new ranking introduced another trade-off by removing the requested genre.

That made me realize that reliability cannot always be reduced to a single score. Different evaluation criteria can conflict, and the rules used to judge quality are themselves design decisions.

Working with Claude Code also showed me the importance of providing clear requirements and verifying results. AI can speed up implementation, but it still needs direction, constraints, and testing.

If I continued developing VibeMatch, I would focus on expanding the music catalog, supporting more flexible preferences, and allowing users to provide feedback on the recommendations.

Overall, this project helped me understand the difference between building an algorithm that works and designing a system that can explain its decisions, recognize its limitations, and respond appropriately when its results are not ideal.

---

## Appendix: VibeMatch 1.0 Reflection (Module 3)

What stood out to me most during the original project was how much the weights affected the recommendations. Before working through the scoring system, I understood that recommendations depended on user preferences, but I hadn't really considered how much difference assigning two points to genre instead of one could make.

The contradictory profile was probably the clearest example. It asked for an angry, high-energy song, but the system recommended a calm ambient track simply because the genre matched. The program wasn't necessarily calculating anything incorrectly. It was following the rules we had given it. That helped me understand why designing the scoring logic matters just as much as writing the code.

I used Claude Code to help implement the original recommender, generate tests, run the evaluation profiles, and document the results. The score explanations were particularly useful because they let me connect each ranking to the actual rules instead of just accepting the output. For example, they showed that *Spacewalk Thoughts* topped the contradictory profile because of its +2.00 genre match, while its energy only earned +0.33.

Another thing I found interesting was how limitations appeared even with only 20 songs. Some genres had more options than others, and certain songs repeatedly appeared in the recommendations. It made me realize that recommendation quality depends not only on the algorithm but also on the data available.

If I extended the original project, I wanted users to be able to choose multiple genres and moods instead of being limited to one of each. I was also interested in adding an interactive interface where users could adjust scoring weights and decide whether genre, mood, or energy mattered most to them.

Overall, Module 3 gave me a better understanding of how a relatively simple Python algorithm can produce personalized recommendations, and why those recommendations still need to be evaluated instead of assuming the highest score always means the best choice.