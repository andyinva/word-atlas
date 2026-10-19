# Structure trial: the finished note

*2026-10-19, revised after the reviewer's reading. This closes the trial begun in STRUCTURE_TRIAL_JOEL_AMOS.md (first chiasm test) and STRUCTURE_TRIAL_V2.md (second test). The third and final test, with its rules fixed in advance, finds none of the five test passages by the full verdict. That includes the two easy cases, though Psalm 8 is found in substance (section 3). As agreed, the trial stops here whatever the outcome. **Trial closed.***

Full tables:
- reports/Analysis/structure_tests_v3.md (the five passages);
- reports/Analysis/structure_joel_amos.md (verbs and half-verses, Joel and Amos whole).

## 1. What went into the atlas

All of this is in lxx.db only; atlas.db is read, never written.

| piece | where | what it gives |
|---|---|---|
| morphology columns | atlas_morph.py, run by build_tahot.py and build_gnt.py | stem, voice, tense, mood, person, gender, number on every Hebrew and Greek token |
| half-verses | the same, table verse_cola | for every Hebrew verse the word that ends the first half: the atnach (21,236 verses), the ole we-yored of Job, Psalms and Proverbs, or the stand-in of a short verse |
| poetry flag | the same, POETRY_LAYOUT | poetic books, plus Joel and Amos with their prose verses named; still to be checked against a printed BHS |
| root families | the same, table root_families | each Strong's number linked to its root through the "from H..." links of atlas.db's lexicon: 14,059 numbers, 9,092 families |
| verb counts and half-verse measure | sections 7v and 7p of every book page and dossier (atlas_grammar.py); also Eval_data/structure_experiment.py, `--parts verbs,cola` | the verb side of the thou and ye strips, and a first measure of parallelism |

### The verb counts, Joel and Amos

| book | verbs | imperatives | cohortative / jussive | 1st person | 2nd singular | 2nd plural | singular share of 2nd |
|---|---:|---:|---:|---:|---:|---:|---:|
| Joel | 250 | 43 | 4 | 19 | 7 | 48 | 13% |
| Amos | 525 | 43 | 4 | 89 | 23 | 56 | 29% |

**Joel.** Joel speaks to "ye" throughout: 48 plural against 7 singular, and 43 imperatives in three chapters.

**Amos.** Amos's "thou" is in particular places:
- **Amos 7:** 13 singular and no plural, all in the Amaziah story ("O thou seer, go, flee thee away").
- **Amos 9:** 3 singular and no plural.
- **Amos 4 and 5:** these carry the plural ("ye"), 16 and 23 verbs.
- **Amos 1 to 2:** almost no second person; these are oracles about the nations in the third person. Chapter 1 has none and 14 first-person verbs ("I will send a fire"); chapter 2 has 3 plural, where Israel is turned to ("ye gave the Nazarites wine").

### The half-verses of the poetic verses

| book | poetic verses | the second half repeats a word of the first | the same, halves paired at random | part-of-speech likeness | the same, at random |
|---|---:|---:|---:|---:|---:|
| Joel | 67 | 33% | 13% | 0.45 | 0.43 |
| Amos | 126 | 30% | 12% | 0.49 | 0.42 |

**Shared words.** In both books the two halves of a verse share a word about two and a half times as often as halves picked at random. That is the parallelism measured from the words alone.

**Parts of speech.** The likeness of word classes is only a little above chance. Hebrew halves are alike in word classes whether they belong together or not.

**Amos 1.** No verse of Amos 1 repeats a word across the atnach. Its oracles keep the repetition for the refrain ("for three transgressions ... and for four"), not within the verse.

## 2. The third test, as fixed before the run

Everything from the second test stands:
- half-verse units;
- matching by root family;
- participle and imperative openings as a form weight;
- symmetry around each candidate centre;
- the rotation null and the same-book window null;
- the three-part verdict: beat 95% of both nulls, recover at least half the published pairs, and put the centre in the published centre.

Changed for the third test:
- the minimum gap is two units, not three;
- the theme rule is back, applied inside every stretch, the passage and each null window alike: families in more than a third of that stretch's units are set aside;
- the tolerance is one unit under fifty units, two from there on;
- the report says whether the same centre wins with the form weight taken out.

Two easy cases were added: Genesis 11:1-9 (centre 11:5, "the LORD came down") and Psalm 8 (the refrain at 8:1 and 8:9).

## 3. The verdicts

| passage | units | best centre | rotation p | windows p | pairs | centre | verdict |
|---|---:|---|---:|---:|---:|---|---|
| Genesis 11:1-9 (Babel) | 18 | 11:6 | 1.000 | 0.644 | 0 of 4 | no (11:5) | not found |
| Psalm 8 | 18 | 8:5a | 0.056 (lowest possible) | 0.123 | 1 of 1 | yes (inside the frame) | not found |
| Amos 5:1-17 | 34 | between 5:9b and 5:10a | 0.353 | 0.611 | 3 of 4 | yes on the test's rule | not found |
| Genesis 6:10-9:19 | 156 | 8:2a | 0.269 | **0.043** | 4 of 14 | no (8:1) | not found |
| Genesis 6-9 | 194 | 8:2a | 0.139 | **0.043** | 4 of 14 | no (8:1) | not found |

**Babel and Psalm 8 do not pass the full verdict, so the Amos result cannot be read as a result about Amos.** What can be said is narrower and still worth saying. Three of de Waard's four pairs are in the words, and the fourth (5:8 / 5:9) is a pair of form. By this measure the arrangement does not stand out from the rest of Amos. Whether Amos 5 is a chiasm stays open.

**Psalm 8 is found in substance and fails on the verdict's floor.**
- **The frame is found.** The refrain is the outermost mirror pair (8:1a / 8:9b: "excellent", "name", "earth", 19.8 of the 23.9 points), and the centre falls inside the frame at 8:5a ("thou hast made him a little lower than the angels").
- **Rotation null.** The centre beats every one of the 17 rotations. But with 18 units the smallest p a rotation null can give is 1/18 = 0.056, so this null cannot reach 0.05 for a passage under twenty units, however clean the frame.
- **Window null.** Against 4,766 stretches of the same length in the Psalter it is not unusual (p 0.12). That is a true statement about the Psalter, not a miss: refrains and repeated openings are common in the Psalms, and a frame of one shared line is ordinary there.
- **The lesson.** Inclusio and chiasm are different claims and need different instruments. An inclusio test should score the frame alone against the frames of other windows, not the whole mirror. The chiasm test was asked a question it was not built for.

**Babel was mis-chosen as an easy case.** Fokkelman's structure is carried as much by sound-play (nilbenah against nabelah, levenah against laben) and by the repeated "come, let us" as by shared words, and a test of shared words cannot hear sound-play. The score at the published centre is close to the best: 29.7 between 11:5a and 11:5b against 31.3 at 11:6. But the true order scores below every rotation of itself. The words that carry the chiasm are not in the test's vocabulary:
- **"Build" dropped out.** Strong's derives ben "son" (H1121) and bayit "house" (H1004) from banah "build" (H1129). The family is then so common that it falls below the rarity floor, and "build" (11:4, 5, 8) drops out of the test.
- **"All" is too common to count.** "The whole earth" of 11:1 and 11:9 is kol, below the floor, so the frame rests on "earth" and "language" alone. That pair is only reachable from a centre near 11:5, and the 11:6 centre wins by a point and a half.

The root table that won the justice pair in Amos loses the building in Babel. That second loss is the useful finding. The fix it reveals is to stop a family absorbing children far more frequent than its root: cap pooling by frequency, or pool only when both members are below the rarity floor. That would keep righteousness with righteous and keep "build" out of the family of "son".

**Genesis 6-9 is the one case where the book-level null spoke twice and the same way.** Against the rest of Genesis the flood stretch is near or just past the conventional threshold in both later tests. In the second test the windows p was 0.055 for chapters 6-9 and 0.066 for 6:10-9:19, just short. In the third it was 0.043 in both sets of bounds. Both times the centre is at 8:2, one verse after "God remembered Noah".

What it fails is the rotation null, and that null is unsuited to a framed passage. The flood's strength is a frame of rare words at its two ends (Noah's sons at 6:10 and 9:18). Rotating the passage brings the two ends together, and the units beside them then pair across the seam as the inner pairs of a new centre. The null that keeps local cohesion also manufactures symmetry out of an inclusio.

So the flood result can be stated as it stands. Compared with the rest of its book, the flood narrative shows a measurable mirror in its words, centred within a verse of "God remembered Noah", at the edge of the conventional threshold. The instrument cannot say more than that, and the rotation result should not be held against it.

## 4. What the chiasm test can and cannot see

It can see:
- **Frames of rare words between distant units:**
  - the Psalm 8 refrain;
  - Noah's sons at 6:10 and 9:18;
  - "the flood to destroy all flesh" at 6:17 and 9:11;
  - the lament and seek-and-live pairs of Amos 5;
  - a pair joined only by root, righteousness with righteous, through the root table.
- **That form never decided a centre.** In all five passages the same centre won with the form weight taken out. Form pairs are ordinary in Hebrew (a participle opens about one half-verse in thirty-five), and they add to a centre's score without choosing it.

It cannot see:
1. **Structures carried by common words.** The rarity floor drops very common words that a chiasm can be built on, such as kol "all". The Strong's families make it worse by pooling a root with its most frequent derivatives, as "build" with "son" and "house".
2. **Short passages, and framed ones, by the rotation null.** Under twenty units the rotation null cannot reach 0.05 at all. For a passage framed by rare words at its ends, rotation pairs the frame across the seam and so builds symmetry the passage does not have.
3. **An exact centre.** Neighbouring centres score within a few points of each other (Babel 31.3 against 29.7, the flood at 8:2 against 8:1). A centre one verse out fails the verdict even when the mirror is there.
4. **Theme words at half-verse scale.** The theme rule set nothing aside in any of the five passages. No family reaches a third of the units once verses are split in two.

If the work is taken up again, it needs rethinking rather than tuning:
- **separate instruments for inclusio and chiasm**, the inclusio scoring the frame alone against the frames of other windows;
- **the window null without the rotation null**;
- **frequency-aware root families**, which do not pool a root with children far more frequent than itself;
- **a vocabulary that keeps "all" and "build"**;
- **a centre scored by its distance from the published one** instead of in or out.

## 5. Where the trial ends

The morphology, the half-verses, the root families, the verb counts and the half-verse measure are kept. The chiasm test stays in the experiment script as an instrument with known limits:
- `--chiasm v3` is the default;
- `--chiasm v2` and `--chiasm v1` run the earlier tests.

The atlas does not yet support any claim that a passage is or is not a chiasm. The one qualification is the flood: there the book-level null spoke twice and the same way, and the mirror in its words can be stated as above, at the edge of the threshold. Joel and Amos as whole books were run for the verbs and the half-verses only. Those two measures are now sections 7v and 7p of every book page, so they reach every dossier (atlas_grammar.py).
