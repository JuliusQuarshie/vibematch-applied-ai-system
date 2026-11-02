# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeMatch 1.0**

---

## 2. Intended Use

VibeMatch is a simple music recommendation system that suggests five songs based on a user's preferences. It considers their favorite genre, preferred mood, target energy level, and whether they enjoy acoustic music.

The goal is to demonstrate how recommendation systems can use song features and user preferences to rank music. Each recommendation includes a score and an explanation of how that score was calculated.

This project is meant for learning and experimentation, not for use as a real streaming service. The catalog is small, the songs are fictional, and the system doesn't learn from users' actual listening habits.

---

## 3. How the Model Works

VibeMatch uses a weighted scoring system. Instead of randomly recommending songs, it compares each song's features with the user's preferences.

Each song can earn:

- **2 points** if its genre matches the user's favorite genre.
- **1 point** if its mood matches the user's preferred mood.
- **Up to 1 point** based on how close its energy level is to the user's target.
- **Up to 0.5 points** for acoustic similarity, if the user provides that preference.

After calculating the scores, the program sorts the songs from highest to lowest and returns the top five recommendations. Songs with identical scores are sorted alphabetically by title.

I built the scoring logic in Python with help from Claude Code and made sure each recommendation includes reasons explaining the points awarded. The weights can also be adjusted to compare how different scoring rules affect the recommendations.

---

## 4. Data

The dataset contains **20 fictional songs** stored in `data/songs.csv`. The starter repository originally had 10 songs, and another 10 were added to introduce more variety.

The dataset includes:

- **15 genres**, including pop, lofi, rock, hip hop, reggae, jazz, classical, metal, and others.
- **13 moods**, including happy, chill, intense, relaxed, angry, nostalgic, and sad.
- Numerical features such as energy, tempo, valence, danceability, and acousticness.

The additional songs helped introduce different combinations of genres, moods, and energy levels.

However, 20 songs are not enough to represent the variety of music people listen to. Some genres have only one song, and the dataset does not include real listening histories, user feedback, or songs from many musical traditions.

---

## 5. Strengths

One thing VibeMatch does well is recommending songs when the user's preferences are clear.

For example, the Chill Lofi profile received three lofi songs at the top of its recommendations, with energy levels close to the requested value. The Intense Rock profile also received *Storm Runner*, a rock song with an intense mood and energy of 0.91, as its highest-ranked recommendation.

The Chill Lofi and Intense Rock profiles had no songs in common in their top five, which shows that the algorithm can distinguish between very different preferences.

Another strength is that users can see why songs were recommended. Instead of only displaying a ranked list, the system explains which features contributed to each score.

The results are also consistent. Running the same profile with the same dataset and weights produces the same ranking.

---

## 6. Limitations and Bias

The biggest weakness I noticed was how much influence the genre weight had on the final rankings.

Since a matching genre earns two points, a song can rank highly even when its mood and energy do not match what the user wants.

This happened with the contradictory profile, which requested ambient music, an angry mood, and energy of 0.95. The system recommended *Spacewalk Thoughts* first, even though its energy was only 0.28. It ranked first mainly because its genre matched.

I also noticed other limitations:

- **Exact matching:** A song labeled `indie pop` does not receive genre points when the user selects `pop`, even though those genres are related.
- **Uneven representation:** Pop and lofi have more songs than most other genres, giving those preferences more matching options.
- **Limited variety:** The system can recommend several songs from the same genre or artist because it does not enforce diversity.
- **Unused features:** Tempo, valence, and danceability are available in the dataset but are not used when calculating scores.
- **Simple user profiles:** Each user can select only one favorite genre and mood, which does not reflect how varied people's music preferences can be.

These limitations show how a recommendation system can produce mathematically correct rankings that do not necessarily reflect what someone would enjoy listening to.

---

## 7. Evaluation

I evaluated VibeMatch using four different user profiles:

| Profile | Genre | Mood | Energy |
|---|---|---|---|
| High-Energy Pop | Pop | Happy | 0.85 |
| Chill Lofi | Lofi | Chill | 0.35 |
| Intense Rock | Rock | Intense | 0.90 |
| Contradictory | Ambient | Angry | 0.95 |

The Chill Lofi profile also included a preference for acoustic music.

### Results

The first three profiles produced recommendations that made sense based on their selected preferences.

Their top recommendations matched the requested genres, moods, and energy levels, with scores of 3.97, 4.43, and 3.99 respectively.

High-Energy Pop and Intense Rock shared two songs in their top five: *Gym Hero* and *Basement Riot*. This was interesting because the profiles requested different genres, but both preferred high-energy music.

The contradictory profile revealed a problem. *Spacewalk Thoughts*, a low-energy ambient song, ranked above songs that better matched the requested angry mood and high energy.

### Weight Experiment

To understand this issue, I compared the original scoring weights with an alternative version.

I changed:

- Genre weight from **2.0 to 1.0**
- Energy weight from **1.0 to 2.0**

I ran the experiment with Claude Code using:

`python -m src.main --experiment`

The changes affected the results:

- **Contradictory profile:** *Spacewalk Thoughts* fell outside the top five, while *Iron Lung Parade* became the top recommendation.
- **High-Energy Pop:** *Rooftop Lights* moved from fourth to third because its mood and energy were closer to the user's preferences.
- **Chill Lofi:** *Spacewalk Thoughts* moved from fourth to third, ahead of *Focus Flow*.
- **Intense Rock:** The ranking stayed the same, but *Gym Hero* came within 0.02 points of the second-ranked rock song.

This experiment showed that changing the weights can improve recommendations for one type of user while making them less suitable for another.

### Automated Testing

I used Claude Code to write and run a `pytest` suite that checks the system's behavior.

The test suite covered CSV loading, numerical conversions, scoring rules, recommendation explanations, ranking order, empty datasets, and tie-breaking.

**All 20 tests passed** during the final implementation run.

---

## 8. Future Work

If I continued developing VibeMatch, I would focus on making its recommendations more flexible and realistic.

Some improvements I would consider are:

- **Related genre matching:** Give partial points when genres are similar, such as pop and indie pop.
- **More song features:** Include tempo, valence, and danceability in the scoring formula.
- **Recommendation diversity:** Avoid recommending too many songs from the same artist or genre.
- **More flexible profiles:** Allow users to select multiple favorite genres and moods.
- **Larger dataset:** Add more songs from different genres, cultures, and musical styles.

I would also like to explore how user feedback, such as likes and skips, could help the system improve its recommendations over time.

---

## 9. Personal Reflection

What stood out to me most during this project was how much the weights affected the recommendations. Before working through the scoring system, I understood that recommendations depended on user preferences, but I hadn't really considered how much difference assigning two points to genre instead of one could make.

The contradictory profile was probably the clearest example. It asked for an angry, high-energy song, but the system recommended a calm ambient track simply because the genre matched. The program wasn't necessarily calculating anything incorrectly. It was following the rules we had given it. That helped me understand why designing the scoring logic matters just as much as writing the code.

I used Claude Code to help implement the recommender, generate tests, run the evaluation profiles, and document the results. The score explanations were particularly useful because they let me connect each ranking to the actual rules instead of just accepting the output. For example, they showed that *Spacewalk Thoughts* topped the contradictory profile only because of its +2.00 genre match, since its energy only earned +0.33.

Another thing I found interesting was how limitations appeared even with only 20 songs. Some genres had more options than others, and certain songs repeatedly appeared in the recommendations. It made me realize that recommendation quality depends not only on the algorithm but also on the data available.

If I extended the project, I would want users to choose multiple genres and moods instead of being limited to one of each. The weights can already be changed in code, so I would also add an interactive interface where users could adjust them and decide whether genre, mood, or energy matters most to them.

Overall, this project gave me a better understanding of how a relatively simple Python algorithm can produce personalized recommendations, and why those recommendations still need to be evaluated instead of assuming the highest score always means the best choice.