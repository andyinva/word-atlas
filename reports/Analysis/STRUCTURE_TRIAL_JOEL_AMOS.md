# Structure trial: morphology, cola, inclusio and chiasm

*2026-10-19. A trial on lxx.db only; atlas.db is not touched. Scripts:
Eval_data/morph_accents_import.py (the import) and
Eval_data/structure_experiment.py (the experiment). The chiasm part did
not find the published structures, so, as asked, the trial stops before
Joel and Amos.*

## 1. The morphology columns

The full morphology codes were already in lxx.db (tokens.morph: `Vqp3ms`
for the TAHOT, `V-AAI-3S` for TAGNT), so nothing new had to be fetched.
The import spells them out into seven columns beside `pos`. `stem` holds
the Hebrew and Aramaic stem (qal, niphal, piel ...) and `voice` the Greek
voice, since the two do different work. The Septuagint corpus is left
alone.

| column | TAHOT tokens filled | GNT tokens filled | values |
|---|---:|---:|---|
| stem | 73,731 | . | qal, niphal, piel, pual, hiphil, hophal, hithpael ...; Aramaic peal, pael, haphel ... |
| voice | . | 28,573 | active, middle, passive, middle or passive, deponent ... |
| tense | 73,731 | 28,573 | Hebrew form (perfect, imperfect, sequential imperfect ...); Greek tense |
| mood | 73,731 | 28,573 | indicative, imperative, cohortative, jussive, subjunctive, optative, infinitive, participle |
| person | 106,197 | 25,732 | 1, 2, 3 (verbs, pronouns, pronoun suffixes) |
| gender | 246,680 | 76,186 | masculine, feminine, common, neuter |
| number | 246,680 | 101,287 | singular, plural, dual |

Amos 5:2 as a check: נָֽפְלָה `Vqp3fs` is qal, perfect, indicative, 3,
feminine, singular; מְקִימָֽהּ `Vhrmsc` is hiphil, participle, masculine,
singular, with its suffix `Sp3fs` as 3, feminine, singular.

## 2. The accents and the half-verses

**lxx.db has no accents, but the TAHOT carries them.** build_tahot.py
strips the cantillation marks (U+0591 to U+05AF) when it builds lxx.db.
The TAHOT source files keep the full Masoretic accents (Amos 5:2 has the
atnach on יִשְׂרָאֵ֑ל, word 6), so no other source is needed. The import
reads the four source files again and stores, for every verse, the word
that ends the first half-verse, in a new table `verse_cola` keyed by
verse_id. Its word numbers are those of tokens.word_no.

| dividing accent | verses |
|---|---:|
| atnach | 21,236 |
| tipcha (stands in for the atnach in a short verse) | 1,394 |
| ole we-yored (Job, Psalms, Proverbs: outranks the atnach) | 407 |
| revia mugrash (short verse in the three books) | 15 |
| none found | 209 (153 in Psalms, mostly titles; 46 in Job) |

The accents do not say which verses are poetry: the atnach divides prose
verses too. The `poetic` flag therefore comes from a short layout table in
the import (Psalms, Proverbs, Song, Lamentations, Job without its prose
frame, and Joel and Amos with their prose verses named). It follows the
usual BHS layout as far as I know it and should be checked against a
printed BHS. Joel has 67 of its 73 verses flagged as poetry, and Amos 126
of 146.

## 3. The chiasm and inclusio test on the published cases

These settings were fixed before the run and not tuned afterwards:

- **Units.** One unit is a verse, compared by its content lexemes (Strong's numbers).
- **Rarity.** A pair weight counts only words rarer than one verse in seven (idf 2.0 or more).
- **Theme words.** Words found in more than a third of the passage's verses are set aside as theme words.
- **Shuffles.** 1000 shuffles of the passage's verses, seed 1.
- **Verdict.** A structure counts as "found" when three things hold: the chain beats 95% of the shuffles, it recovers at least half the published pairs, and its centre falls in the published centre.

| passage | published centre | chain pairs | chain score | shuffled median | p | pairs recovered | chain's centre | verdict |
|---|---|---:|---:|---:|---:|---:|---|---|
| Amos 5:1-17 (de Waard 1977) | 5:8 "YHWH is his name" | 3 | 34.1 | 41.1 | 0.913 | 2 of 4 | 5:5-6 | not found |
| Genesis 6:10-9:19 (Wenham 1978) | 8:1 "God remembered Noah" | 20 | 345.0 | 351.8 | 0.599 | 3 of 14 | 8:11 | not found |
| Genesis 6-9 (chapter bounds) | 8:1 | 24 | 384.6 | 410.8 | 0.850 | 3 of 14 | 8:11 | not found |

| passage | best inclusio | frame words | p |
|---|---|---|---:|
| Amos 5:1-17 | 5:6 / 5:14 | seek, live | 0.732 |
| Genesis 6:10-9:19 | 7:13 / 9:18 | Shem, Ham, Japheth | 0.177 |
| Genesis 6-9 | 7:13 / 9:18 | Shem, Ham, Japheth | 0.224 |

**The script does not find either published structure unprompted.** Its
results instead:

**Amos 5:1-17.** The chain found is 5:3/5:16 ("thus saith the Lord"),
then 5:4/5:14 ("seek ... live"), then 5:5/5:6 (Beth-el, seek). The outer
two are de Waard's lament pair and seek-and-live pair. His inner two,
justice overturned (5:7 / 5:10-13) and the Creator against the destroyer
(5:8 / 5:9), share no lexeme:

- **Justice overturned.** 5:7's righteousness (tsedaqah, H6666) and 5:12's righteous (tsaddiq, H6662) are one root but two Strong's numbers.
- **The Creator and the destroyer.** 5:8 and 5:9 are tied by form: both open with a hymnic participle. They share no word.

The chain scores below the median of the shuffles.

**Genesis 6:10-9:19.** The outer frame of Wenham's palistrophe is there in
the words:

- Noah and his sons, 6:10 / 9:18;
- the flood to destroy all flesh, 6:17 / 9:15;
- the covenant, 6:18-19 / 9:10-11.

The inner half, with the day counts (seven, seven, forty, a hundred and
fifty) and the turn at 8:1, is not found. The chain fills its middle with
the animal lists (7:14 / 8:19, 7:21 / 8:17) and the two dove verses
(8:10 / 8:12), which puts its centre at 8:11, the olive leaf.

**Why the verse shuffle works against the chain.** Shared words cluster
in neighbouring verses. A nested chain can use only one cluster, while a
shuffle scatters the strong pairs, and a nested chain can then pick up
more of them. So the shuffles score higher than the real order in all
three passages.

| passage | mean pair weight, verses 1 or 2 apart | mean pair weight, further apart |
|---|---:|---:|
| Amos 5:1-17 | 4.38 | 1.10 |
| Genesis 6:10-9:19 | 5.96 | 3.21 |
| Genesis 6-9 | 6.11 | 2.80 |

The test fails for two reasons. Two of Amos's pairs are bound by root and
form rather than by the same lexeme. And the null model asked for (verse
shuffles) penalises any text whose repetition is local, which all
narrative and most poetry is. Section 4 lists what would address both. It
is left for a decision rather than tuned here, since tuning until the
published answer appears would no longer be "unprompted".

**The other two parts.** The verb counts and the cola measure are written
and were run on the test passage only, to check that they work:

- **Verbs.** Amos 5:1-17 has 65 verbs, 9 of them imperatives, and 19 second-person verbs, all plural.
- **Cola.** 35% of its 17 verses repeat a word across the atnach, against 14% for halves paired at random within the passage.

Joel and Amos as whole books have not been run.

## 4. What would make the test fairer (not done)

1. **A null that keeps local cohesion.** Shuffle blocks of two or three verses instead of single verses, or count only pairs at least three verses apart.
2. **Roots instead of Strong's numbers,** so that tsedaqah and tsaddiq, or mishpat and shaphat, match. TAHOT gives no root field; a root table would be needed.
3. **Form as a second pair weight.** For example, verses that open with a participle, from the new mood column.
4. **Half-verses as units** where a centre is half a verse: Amos 5:8's "YHWH is his name" is the last two words of 5:8.
