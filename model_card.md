# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**VibeMatch 1.0**

---

## 2. Intended Use  

VibeMatch suggests the top 5 songs from a small catalog that best match a user's stated taste: favorite genre, favorite mood, a target energy level, and optionally whether they like acoustic sound. Every suggestion comes with a list of reasons showing how many points each preference contributed.

It assumes the user can describe their taste with a single genre, a single mood, and one energy number. It is built for **classroom exploration** of how scoring-based recommenders work.

**Not intended for:** real users or a real streaming product, judging the quality of real artists, any decision that affects people (e.g., which artists get paid or promoted), or users whose taste spans many genres or changes over time. The catalog is fictional.

---

## 3. How the Model Works  

Each song in the catalog has a genre, a mood, and an energy level from 0 (very calm) to 1 (very intense), plus a few other numbers like acousticness.

For each song, VibeMatch hands out points:

- **2 points** if the song's genre is the user's favorite genre.
- **1 point** if the song's mood is the user's favorite mood.
- **Up to 1 point** for energy: a perfect match gets the full point, and the score drops the further the song's energy is from what the user wants.
- **Up to 0.5 points** for acoustic sound, but only if the user said whether they like acoustic music.

All songs are sorted from most to fewest points and the top 5 are shown. If two songs tie, they are ordered alphabetically by title so the result is always the same.

Compared to the starter, I implemented all of the scoring, added the energy-closeness formula and the optional acoustic bonus, made every rule produce a readable reason (including when it gives 0 points), and made the weights adjustable so experiments don't change the default behavior.

---

## 4. Data  

- **20 songs** in `data/songs.csv`: the 10 starter songs plus 10 fictional songs I added.
- **Genres (15):** pop (3), lofi (3), rock (2), and one each of ambient, jazz, synthwave, indie pop, hip hop, r&b, metal, country, edm, classical, reggae, folk.
- **Moods (13):** happy, chill, intense, relaxed, moody, focused, confident, romantic, angry, nostalgic, euphoric, sad, melancholy.
- The added songs were chosen to fill gaps: low-energy sad songs (classical, folk), very high-energy aggressive songs (metal, rock/angry), and genres missing from the starter (hip hop, r&b, country, reggae, edm).
- **Missing:** real listening data, lyrics, language, release year, non-Western genres, and more than one or two songs for most genres. All songs and artists are fictional.

---

## 5. Strengths  

- **Clear, consistent profiles work well.** Chill Lofi's top 3 are all lofi songs with energy 0.35–0.42, and Intense Rock's #1 is *Storm Runner* (rock, intense, 0.91) with a score of 3.99 out of 4.
- **Opposite profiles stay separate.** Chill Lofi and Intense Rock share no songs in their top 5.
- **Explanations are transparent.** Every point is listed, so it's easy to see exactly why a song ranked where it did, including when the ranking is bad.
- **Deterministic.** The same input always gives the same output.

---

## 6. Limitations and Bias 

- **Genre dominance.** Genre is worth 2 points, the same as a perfect mood + energy match combined. For the contradictory profile (ambient + angry + 0.95 energy), the #1 result was *Spacewalk Thoughts*, a chill song with energy 0.28, only because it is ambient.
- **Exact label matching.** `indie pop` gets no credit from a `pop` profile, so *Rooftop Lights* (happy, energy 0.76) ranks below *Neon Heartbreak* (pop but sad) for the High-Energy Pop profile.
- **Uneven catalog coverage.** Lofi and pop each have 3 songs; 12 genres have only 1. Users of rare genres get one match and then filler picked mostly by energy.
- **Filter bubble.** Results repeat the same genre and sometimes the same artist (2 of the top 3 for Chill Lofi are by LoRoom). There is no diversity rule.
- **Ignored features.** Tempo, valence, and danceability are loaded but not used in scoring.
- **One-dimensional users.** A profile only holds one genre and one mood; people who like several styles can't be represented.

---

## 7. Evaluation  

**Profiles tested** (all in `src/main.py`):

1. High-Energy Pop — pop, happy, energy 0.85
2. Chill Lofi — lofi, chill, energy 0.35, likes acoustic
3. Intense Rock — rock, intense, energy 0.90
4. Contradictory — ambient, angry, energy 0.95 (a calm genre with an aggressive mood)

**What I looked for:** whether the #1 song matched all preferences, whether the rest of the top 5 made sense, and whether opposite profiles got different songs.

**Results:**
- Profiles 1–3 each got a #1 song matching genre, mood, and energy (scores 3.97, 4.43, 3.99).
- High-Energy Pop and Intense Rock overlapped on two songs (*Gym Hero*, *Basement Riot*) because both want high energy; their order flipped depending on which profile got the genre bonus.
- The contradictory profile exposed genre dominance: a 0.28-energy ambient song beat a metal/angry/0.97-energy song.

**Weight-shift experiment** (genre 2.0 → 1.0, energy 1.0 → 2.0, run with `python -m src.main --experiment`):
- Contradictory: *Spacewalk Thoughts* dropped from #1 to outside the top 5; *Iron Lung Parade* became #1.
- High-Energy Pop: *Rooftop Lights* (indie pop, happy) moved from #4 to #3 above *Neon Heartbreak* (pop, sad).
- Chill Lofi: *Spacewalk Thoughts* (ambient, chill) moved from #4 to #3 above *Focus Flow* (lofi, focused).
- Intense Rock: same order, but the pop song *Gym Hero* came within 0.02 points of the #2 rock song.

**Surprise:** one weight change fixed the contradictory case but almost erased genre for the rock fan. There isn't one set of weights that's best for every profile.

**Automated tests:** 20 pytest tests (loading, conversion, invalid rows, scoring rules, explanations, ranking, top-k, empty catalog, tie-breaking). All 20 passed on the last run.

---

## 8. Future Work  

- **Partial genre/mood matching** — e.g., give `indie pop` half credit for `pop`, or group moods like chill/relaxed.
- **Use tempo, valence, and danceability** with normalized closeness scores (tempo divided by a max BPM).
- **Diversity rule** — limit how many songs from one artist or genre can appear in the top 5.
- **Multiple favorite genres/moods** per user, with their own weights.
- **Bigger, more balanced catalog** so rare-genre users aren't stuck with filler.

---

## 9. Personal Reflection  

<!-- Julius: rewrite this section in your own words before submitting. -->

The biggest lesson was that the weights *are* the model. The code is a few if-statements and one formula, but whether a calm ambient song or an angry metal song comes first for the same user depends entirely on whether genre is worth 1 or 2 points. Printing the reason for every point made it easy to see when a ranking was "technically correct but wrong."

It was also surprising how quickly bias appeared in only 20 songs: the genres that happened to have more songs in the data got better recommendations. Real music apps have the same problem at a much bigger scale, and their users usually can't see the reasons behind what they're shown.
