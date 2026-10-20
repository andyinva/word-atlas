# Ransom and rest: the two strips and the Passage page

Written by Eval_data/ransom_rest_report.py on 2026-10-20 for the paper "Abram and Abraham". The lists and the passage are those of ransom_rest_lists.py: "ransom" 44 roots, "rest" 34, and the named passage "Ransom and rest", 48 ranges. The strip tables are read from the heat rows of reports/results.db (the same rows the Reader's heat page draws), the Passage page and the stations are counted on each run; the reading notes at the end are written by hand (Eval_data/ransom_rest_notes.md) and should be read against them.

Each strip is a z-score of the list's share of a 10-verse window against every book of the same language, from `python3 atlas_heat.py BOOK --families --lists ransom,rest`, over Genesis, Exodus, Leviticus, Numbers, Deuteronomy, Ruth, 1 Samuel, 2 Samuel, 1 Kings, 1 Chronicles, Job, Psalms, Isaiah, Jeremiah, Hosea, Zechariah, Matthew, Mark, Acts, Hebrews, 1 Peter, Revelation. A **hit** is a hot window at z 2 or more covering the chapter; **near** is one at z 1.5 to 2; a **miss** is neither. The counting rules of atlas_pos.py apply: gloss rules keep a root's other senses out (paqad's census, kofer's villages, mul's 'fended off', karah's feast), and a chapter rule keeps nega' out of the chapters of leprosy.

## The ransom strip: 11 hits in 10 windows, 0 near, 2 misses of 13 predicted chapters

A hot window that crosses a chapter line is credited to both chapters, so the hits are counted by chapter and the windows once each.

| chapter | result | peak z | words in the hot window |
|---|---|---|---|
| Genesis 12 | hit | +2.2 at 13:2 | 'touch (plague, strike)', 'plague (stroke)', 'silver' |
| Genesis 20 | miss |  |  |
| Exodus 30 | hit | +10.4 at 30:13 | 'shekel' 6, 'atonement (make)' 4, 'heave offering (terumah)' 3, 'atonement' 2 |
| Exodus 38 | hit | +5.2 at 38:22 | 'silver' 10, 'shekel' 7 |
| Leviticus 5 | hit | +10.2 at 6:1 | 'trespass (offering)' 9, 'atonement (make)' 8, 'trespass' 8, 'touch (plague, strike)' 3 |
| Leviticus 27 | hit | +9.2 at 27:18 | 'shekel' 12, 'redeem (kinsman)' 12, 'silver' 7, 'redeem' 2 |
| Numbers 3 | hit | +9.5 at 3:49 | 'cover' 6, 'redemption (Num 3:49)' 4, 'shekel' 4, 'silver' 4 |
| Numbers 18 | hit | +6.0 at 18:13 | 'heave offering (terumah)' 9, 'redeem' 6, 'shekel' 2, 'trespass (offering)' |
| 1 Samuel 5 | hit | +2.3 at 6:5 | 'trespass (offering)' 3, 'plague', 'touch (plague, strike)' |
| 1 Samuel 6 | hit | +2.3 at 6:5 | 'trespass (offering)' 3, 'plague', 'touch (plague, strike)' |
| 2 Samuel 24 | hit | +3.4 at 24:21 | 'buy (acquire)' 4, 'plague' 2, 'silver', 'shekel' |
| Jeremiah 32 | hit | +8.9 at 32:12 | 'buy (acquire)' 6, 'purchase' 5, 'silver' 3, 'redemption (right of)' 2 |
| Hosea 3 | miss |  |  |

## The rest strip: 17 hits in 13 windows, 4 near, 8 misses of 29 predicted chapters

A hot window that crosses a chapter line is credited to both chapters, so the hits are counted by chapter and the windows once each.

| chapter | result | peak z | words in the hot window |
|---|---|---|---|
| Genesis 17 | hit | +11.7 at 17:10 | 'covenant' 13, 'circumcise' 11, 'Almighty (Shaddai)' |
| Genesis 21 | hit | +3.9 at 22:4 | 'burnt offering' 6, 'covenant' 2, 'Moriah' |
| Genesis 22 | hit | +3.9 at 22:4 | 'burnt offering' 6, 'covenant' 2, 'Moriah' |
| Genesis 23 | miss |  |  |
| Exodus 25 | hit | +5.9 at 25:18 | 'ark' 8 |
| Exodus 35 | hit | +2.2 at 35:17 | 'ark', 'burnt offering', 'offer willingly' |
| Exodus 36 | near | +1.8 at 37:4 | 'ark' 3 |
| Numbers 10 | hit | +3.9 at 10:32 | 'ark' 2, 'covenant', 'rest (resting place)', 'rest' |
| Deuteronomy 12 | hit | +5.9 at 12:10 | 'burnt offering' 4, 'freewill offering' 2, 'inheritance' 2, 'rest (resting place)' |
| Ruth 1 | miss |  |  |
| Ruth 3 | hit | +3.0 at 3:5 | 'threshing floor' 3, 'rest' |
| Ruth 4 | miss |  |  |
| 1 Samuel 1 | miss |  |  |
| 1 Samuel 2 | miss |  |  |
| 2 Samuel 6 | hit | +6.7 at 6:9 | 'ark' 16, 'burnt offering' 2, 'threshing floor', 'rest' |
| 2 Samuel 7 | hit | +6.7 at 6:9 | 'ark' 16, 'burnt offering' 2, 'threshing floor', 'rest' |
| 1 Kings 8 | hit | +6.6 at 8:6 | 'ark' 8, 'rest' 2, 'covenant' 2 |
| 1 Chronicles 21 | hit | +5.0 at 21:27 | 'burnt offering' 6, 'threshing floor' 5 |
| 1 Chronicles 22 | hit | +5.0 at 21:27 | 'burnt offering' 6, 'threshing floor' 5 |
| 1 Chronicles 23 | near | +1.8 at 23:4 | 'rest', 'ark', 'covenant' |
| 1 Chronicles 24 | miss |  |  |
| 1 Chronicles 25 | miss |  |  |
| 1 Chronicles 26 | miss |  |  |
| 1 Chronicles 27 | near | +1.5 at 27:32 | 'rest (resting place)', 'ark', 'covenant' |
| 1 Chronicles 28 | hit | +3.7 at 29:13 | 'offer willingly' 7, 'perfect (whole)' 2, 'willing', 'burnt offering' |
| 1 Chronicles 29 | hit | +3.7 at 29:13 | 'offer willingly' 7, 'perfect (whole)' 2, 'willing', 'burnt offering' |
| Psalms 132 | hit | +4.6 at 132:10 | 'rest (resting place)' 2, 'ark', 'covenant' |
| Isaiah 54 | near | +1.7 at 54:6 | 'marry (be husband)' 2, 'covenant' |
| Isaiah 62 | hit | +3.3 at 62:2 | 'marry (be husband)' 4, 'covenant', 'visit' |

## The expected discoveries

| chapter | strip | result | peak z | words |
|---|---|---|---|---|
| Leviticus 25 | ransom | hit | +9.0 at 25:53 | 'redeem (kinsman)' 10, 'redemption (right of)' 9, 'buy (acquire)' 7, 'purchase' 3 |
| Numbers 35 | ransom | hit | +4.1 at 35:29 | 'redeem (kinsman)' 6, 'ransom' 2, 'atonement (make)' |
| Psalms 49 | ransom | hit | +4.5 at 49:11 | 'redeem' 3, 'ransom', 'redemption' |
| Isaiah 43 | ransom | near | +1.6 at 42:24 | 'make restitution', 'redeem (kinsman)', 'ransom' |
| Job 33 | ransom | near | +1.8 at 33:21 | 'cover', 'ransom', 'redeem' |
| Zechariah 11 | ransom | hit | +2.0 at 11:9 | 'silver' 2, 'buy (acquire)', 'trespass' |
| Hosea 13 | ransom | hit | +2.5 at 13:14 | 'redeem', 'redeem (kinsman)', 'trespass', 'make restitution' |
| Mark 10 | ransom | hit | +2.3 at 10:41 | 'ransom' |
| Acts 1 | ransom | miss |  |  |

## Windows the strips light that the paper did not name

The strongest 20 of each strip at z 2 or more, outside the predicted chapters.

**ransom**

| window | z | words |
|---|---|---|
| Matthew 26:69-27:18 | +12.5 | 'silver (money)' 4, 'buy' |
| Ruth 3:4-4:17 | +10.1 | 'redeem (kinsman)' 20, 'buy (acquire)' 6, 'redemption (right of)' 2 |
| Exodus 21:21-22:23 | +9.2 | 'make restitution' 18, 'silver' 6, 'smite (plague)' 2, 'ransom' |
| Leviticus 25:7-26:5 | +9.0 | 'redeem (kinsman)' 10, 'redemption (right of)' 9, 'buy (acquire)' 7, 'purchase' 3 |
| Matthew 24:51-25:21 | +8.0 | 'buy' 2, 'silver (money)' |
| Revelation 17:17-18:20 | +6.5 | 'plague' 2, 'buy', 'silver' |
| Numbers 4:48-5:17 | +6.1 | 'trespass (offering)' 3, 'trespass' 2, 'redeem (kinsman)', 'atonement' |
| Leviticus 16:2-26 | +5.9 | 'atonement (make)' 9, 'mercy seat' 7, 'cover' |
| Leviticus 6:23-7:14 | +5.8 | 'trespass (offering)' 4, 'atonement (make)' 2, 'touch (plague, strike)', 'cover' |
| Revelation 13:3-14:12 | +5.7 | 'plague' 3, 'buy' 3 |
| Numbers 16:38-17:6 | +5.5 | 'plague' 5, 'atonement (make)' 2, 'cover' |
| Matthew 28:3-20 | +5.2 | 'silver (money)' 2 |
| Exodus 25:11-29 | +5.1 | 'mercy seat' 7 |
| 1 Peter 1:9-2:2 | +5.1 | 'silver (money)', 'redeem' |
| Exodus 29:19-45 | +4.9 | 'heave offering (terumah)' 4, 'atonement (make)' 3, 'cover', 'atonement' |
| Numbers 7:4-8:5 | +4.8 | 'silver' 28, 'shekel' 26, 'mercy seat' |
| Mark 15:37-16:10 | +4.7 | 'buy' 2 |
| Leviticus 14:10-34 | +4.7 | 'trespass (offering)' 9, 'atonement (make)' 6 |
| Mark 6:28-46 | +4.6 | 'buy' 2 |
| Genesis 47:7-27 | +4.5 | 'silver' 6, 'buy (acquire)' 4 |

**rest**

| window | z | words |
|---|---|---|
| Hebrews 3:9-5:3 | +14.6 | 'rest' 8, 'rest (give)' 3 |
| 1 Chronicles 15:15-16:27 | +8.8 | 'ark' 12, 'covenant' 7, 'burnt offering' 2, 'inheritance' |
| Numbers 35:28-36:13 | +8.6 | 'inheritance' 17 |
| Hebrews 7:27-9:26 | +8.6 | 'covenant' 12, 'ark', 'inheritance' |
| Exodus 40:11-30 | +6.0 | 'ark' 5, 'burnt offering' 2 |
| 1 Samuel 3:16-6:9 | +5.9 | 'ark' 28, 'covenant' 4 |
| 1 Chronicles 12:38-14:7 | +5.7 | 'ark' 9, 'perfect (whole)', 'threshing floor' |
| Deuteronomy 9:22-10:17 | +5.7 | 'ark' 5, 'inheritance' 4, 'covenant', 'circumcise' |
| Job 22:14-23:4 | +5.4 | 'Almighty (Shaddai)' 4 |
| Genesis 9:3-22 | +5.4 | 'covenant' 7 |
| Psalms 105:1-20 | +5.3 | 'covenant' 2, 'inheritance', 'rest' |
| Numbers 26:65-27:18 | +5.2 | 'inheritance' 6, 'visit' |
| Job 27:1-22 | +5.2 | 'Almighty (Shaddai)' 4, 'inheritance' |
| Job 34:3-21 | +5.2 | 'Almighty (Shaddai)' 2, 'visit', 'willing' |
| Numbers 18:15-19:1 | +5.0 | 'inheritance' 6, 'threshing floor' 2, 'covenant' |
| 1 Samuel 6:6-7:10 | +4.8 | 'ark' 10, 'burnt offering' 4, 'rest', 'whole (burnt)' |
| Numbers 28:1-30:5 | +4.8 | 'burnt offering' 30, 'freewill offering' |
| 1 Chronicles 16:28-17:6 | +4.6 | 'ark' 3, 'covenant' 2, 'burnt offering' 2 |
| Numbers 26:45-63 | +4.6 | 'inheritance' 6 |
| Genesis 34:12-30 | +4.6 | 'circumcise' 5, 'perfect (whole)' |

## Since the last run

Nothing moved, or there was no previous run to compare with.

## The Passage page

`python3 atlas_query.py passage Ransom and rest` (saved to reports/passage_ransom_and_rest.txt): 796 verses, 22,436 words, 54 chapters in 18 books. Its signature words, measured against the rest of the first book's testament, check the lists. Strongest: ark H727, abraham H85, abram H87, sacks H572, sarah H8283, money H3701, naomi H5281, hannah H2584, sarai H8297, ornan H771, dagon H1712, shekel H8255.

**List roots the page finds key** (keyness 10 or more; rank among the page's 554 signature words):

- ransom: silver H3701 (rank 6, keyness 76.1); shekel H8255 (rank 12, keyness 60.1); buy (acquire) H7069 (rank 15, keyness 46.5); purchase H4736 (rank 16, keyness 43.5); heave offering (terumah) H8641 (rank 27, keyness 28.1); redemption (Num 3:49) H6302 (rank 31, keyness 26.4); plague H4046 (rank 34, keyness 22.1); trespass (offering) H817 (rank 40, keyness 20.6); redeem (kinsman) H1350 (rank 44, keyness 20.1); plague H5063 (rank 56, keyness 17.1); redemption (right of) H1353 (rank 109, keyness 10.4)
- rest: ark H727 (rank 1, keyness 200.3); offer willingly H5068 (rank 17, keyness 43.5); marry (be husband) H1166 (rank 22, keyness 31.2); circumcise H4135 (rank 26, keyness 30.2); covenant H1285 (rank 32, keyness 25.6); threshing floor H1637 (rank 37, keyness 21.0); rest (resting place) H4496 (rank 42, keyness 20.5); Moriah H4179 (rank 82, keyness 13.2); burnt offering H5930 (rank 85, keyness 13.1)

**Weak links** (Hebrew list roots the page does not find key; the Greek roots cannot be judged on a page measured against the Old Testament):

- ransom: ransom H3724, atonement (make) H3722, atonement H3725, mercy seat H3727, redeem H6299, redemption H6306, redemption H6304, buy (bargain) H3739, make restitution H7999, trespass H816, guiltiness H819, plague (stroke) H5061, smite (plague) H5062, touch (plague, strike) H5060, barren H6135, cover H3680, covering H3682, covering (of the holy things) H4372
- rest: rest H5117, rest H4494, visit H6485, husband (owner) H1167, freewill offering H5071, willing H5081, whole (burnt) H3632, perfect (whole) H8003, inheritance H5159, Almighty (Shaddai) H7706

**The page's key Hebrew words the lists lack** (keyness 20 or more, names included; the paper decides which belong): abraham H85, abram H87, sacks H572, sarah H8283, naomi H5281, hannah H2584, sarai H8297, ornan H771, dagon H1712, eli H5941, araunah H728, emerods H2914, heth H2845, ephron H6085, abimelech H40, wife H802, hagar H1904, ruth H7327, cart H5699, hanameel H2601, mahlon H4248, boaz H1162, isaac H3327, hophni H2652, levites H3881.

## The stations table: the last column filled

The strip words in each station range, counted from the original text (lxx.db) as the strips count them. The other columns are the paper's to fill.

| station | ransom words | rest words | held by | struck | paid, to whom | covered | rest |
|---|---|---|---|---|---|---|---|
| Genesis 12:10-20 | touch (plague, strike), plague (stroke) | - | | | | | |
| Genesis 15:1-21 | - | perfect (whole), covenant | | | | | |
| Genesis 16:1-16 | - | - | | | | | |
| Genesis 17:1-27 | purchase 4, silver 4 | covenant 13, circumcise 11, Almighty (Shaddai) | | | | | |
| Genesis 20:1-18 | touch (plague, strike), silver, covering | marry (be husband), husband (owner) | | | | | |
| Genesis 21:1-7 | - | visit, circumcise | | | | | |
| Genesis 22:1-19 | - | burnt offering 6, Moriah | | | | | |
| Genesis 23:1-20 | silver 5, shekel 2, purchase | - | | | | | |
| Genesis 26:1-11 | trespass (offering), touch (plague, strike) | - | | | | | |
| Genesis 42:25-44:34 | silver 19, make restitution | rest, Almighty (Shaddai) | | | | | |
| Exodus 25:1-9 | heave offering (terumah) 3, silver | offer willingly | | | | | |
| Exodus 30:11-16 | shekel 5, heave offering (terumah) 3, atonement (make) 2, ransom, plague, silver, atonement | - | | | | | |
| Exodus 35:4-29 | heave offering (terumah) 5, silver 2, covering (of the holy things), mercy seat | willing 2, offer willingly 2, ark, burnt offering, freewill offering | | | | | |
| Exodus 36:1-7 | heave offering (terumah) 2 | freewill offering | | | | | |
| Exodus 38:21-31 | shekel 7, silver 2 | visit 2 | | | | | |
| Exodus 40:34-38 | cover | - | | | | | |
| Leviticus 5:14-19 | trespass (offering) 5, trespass 3, shekel 2, atonement (make) 2, silver, make restitution | - | | | | | |
| Numbers 3:40-51 | redemption (Num 3:49) 4, shekel 4, silver 4, redemption | - | | | | | |
| Numbers 8:5-22 | atonement (make) 3, plague | burnt offering | | | | | |
| Numbers 16:41-50 | plague 5, atonement (make) 2, cover | - | | | | | |
| Numbers 31:48-54 | atonement (make), heave offering (terumah), shekel | visit 2 | | | | | |
| Numbers 10:33-36 | - | ark 2, covenant, rest (resting place), rest | | | | | |
| Deuteronomy 10:1-9 | - | ark 5, inheritance 2, covenant | | | | | |
| Deuteronomy 12:8-11 | heave offering (terumah) | rest (resting place), inheritance, rest, burnt offering | | | | | |
| Ruth 1:1-22 | - | Almighty (Shaddai) 2, visit, rest (resting place) | | | | | |
| Ruth 3:1-1 | - | rest | | | | | |
| Ruth 4:1-22 | redeem (kinsman) 13, buy (acquire) 6, redemption (right of) 2 | inheritance 3 | | | | | |
| 1 Samuel 1:1-2:11 | barren | willing | | | | | |
| 1 Samuel 4:1-6:21 | trespass (offering) 4, smite (plague) 3, plague 2, touch (plague, strike) | ark 34, covenant 4, burnt offering 2, rest | | | | | |
| 2 Samuel 6:1-23 | - | ark 15, burnt offering 2, threshing floor | | | | | |
| 2 Samuel 7:1-29 | redeem 2, plague (stroke) | rest 2, ark | | | | | |
| 2 Samuel 24:18-25 | buy (acquire) 4, plague 2, silver, shekel | threshing floor 3, burnt offering 3 | | | | | |
| 1 Chronicles 21:18-22:1 | silver 2, buy (acquire) 2, plague, shekel | burnt offering 6, threshing floor 4 | | | | | |
| 1 Chronicles 28:1-10 | - | rest (resting place), ark, covenant, perfect (whole) | | | | | |
| 1 Chronicles 29:1-20 | silver 7 | offer willingly 7, perfect (whole) 2 | | | | | |
| 1 Kings 8:1-11 | - | ark 8, covenant 2, rest | | | | | |
| 1 Kings 8:54-66 | - | burnt offering 2, rest (resting place), perfect (whole) | | | | | |
| 1 Kings 10:21-21 | silver | - | | | | | |
| 2 Chronicles 3:1-1 | - | Moriah, threshing floor | | | | | |
| Psalms 132:1-18 | - | rest (resting place) 2, ark, covenant | | | | | |
| Isaiah 54:1-17 | redeem (kinsman) 2, barren | marry (be husband) 2, covenant, inheritance | | | | | |
| Isaiah 62:1-5 | - | marry (be husband) 4 | | | | | |
| Jeremiah 31:31-34 | - | covenant 4, marry (be husband) | | | | | |
| Jeremiah 32:1-44 | buy (acquire) 9, silver 5, purchase 5, redemption (right of) 2, shekel, make restitution | visit, covenant | | | | | |
| Hosea 3:1-5 | buy (bargain), silver | - | | | | | |
| Hebrews 10:1-18 | - | covenant | | | | | |
| 1 Peter 1:13-2:10 | silver (money), redeem | - | | | | | |
| Revelation 21:1-27 | plague | foundation 3, Almighty | | | | | |

## Reading notes

Written by hand, not counted: check each figure in them against the tables above, which this run counted or read afresh.

*Notes as of 2026-10-18, after the gloss and chapter rules, the buying words, the stations Numbers 16:41-50 and Genesis 42:25-44:34, and goren and terumah. Edit this file freely; ransom_rest_report.py puts it into the write-up word for word.*

**Reading the misses.**

- Genesis 12 lights only since 'touch' (naga' H5060, which shares its root with the plague noun) joined the ransom list. Genesis 20 still misses: its 'touch' (20:6), 'silver' and 'covering' are one each, too few in a window of ten verses. The thread is there in the story but thin in the words, and the paper should say so rather than lean on the words.
- 2 Samuel 24 lights since 'buy' (qanah) joined the list, as 1 Chronicles 21 already did. Hosea 3 still misses with karah 'buy' in the list: 3:2 is one verse of buying in a five-verse chapter.
- Genesis 23 is a ransom chapter in the words (silver, shekel, buy, purchase), not a rest chapter.
- Ruth misses under rest (its rest words, menuchah 1:9 and manoach 3:1, are two) but Ruth 3 to 4 is one of the hottest ransom windows, with the kinsman's redeem twenty times. Ruth belongs to the ransom strip: rest is what Naomi blesses, redemption is what the book does.
- 1 Samuel 1 and 2 miss: Hannah's chapters have 'barren', 'willing' and 'visited' once each. The barren-visited pattern is a story shape, not a density.
- 1 Chronicles 24 to 27 miss: the courses, singers, porters and officers. The strip lights the two ends of the predicted block (21 to 22, 28 to 29), where the floor is bought and the offering made, and not the registers between.

**The discoveries.**

- Acts 1:18-19 misses because Acts names the price 'the reward of iniquity' (misthos), not silver; Judas's silver lights in Matthew 26 to 27 instead, the hottest ransom window of the run, with 1 Peter 1:18 ('not redeemed with silver') beside it.
- Exodus 21 to 22, the law of restitution ('make restitution', silver, the ransom for the goring ox's owner), is the legal form of what the stories do, and was on no one's list.
- Numbers 16:46-48 (Aaron with the censer 'between the dead and the living') and Genesis 44 (Judah offering himself in Benjamin's place, 44:33) are ransoms in person, like the Levites of Numbers 8:19; both are now stations.
- Leviticus 16 lights under ransom on its own atonement words, found by the strip without being asked.
- Hebrews 3 to 4, 'there remaineth therefore a rest to the people of God', is the hottest rest window of the run by a wide margin: the rest thread that begins with the ark seeking a resting place ends in the chapter that says the rest was never the land.
- Genesis 34, the circumcision of Shechem, lights on 'circumcise': the rite used as a trap, a foil for Genesis 17.

**Second senses still in the strips.** ba'al H1167 is the ox's 'owner' in Exodus 21 to 22; Shaddai H7706 is Job's diction (discount Job when reading the rest strip); shalam H7999 is the law of damages and recompense; arown H727 is Joseph's coffin in Genesis 50:26; agorazo G59 is ordinary buying in the Gospels; 'inheritance' H5159 lights the land allotments; naga' H5060 is touching the unclean in Leviticus 11 and Numbers 19, though it also brings in Isaiah 6:7, Isaiah 52 to 53 and Exodus 12:22.

**Shaddai in the rest strip.** Shaddai H7706 stays in the list as it is, but 31 of its 48 uses are Job's, the Almighty of the speeches, and the Job windows of the rest strip that light on 'Almighty' alone are to be discounted. The patriarchal uses count: Jacob's 'God Almighty give you mercy before the man' (Genesis 43:14), in the Joseph station, is one of them.

**Three formulas of the stations.** The Passage page's signature formulas find three that belong to the stations themselves. 'She is my sister': six verses, all in the stations (Genesis 12:19; 20:2, 5, 12; 26:7, 9), and in no other verse of the Bible. 'The lad': Isaac on Moriah (Genesis 22:5, 12) and Benjamin in the Joseph station (43:8; 44:22-34), fourteen verses, the son offered and the son offered for. 'An offering': the wave offering shared by the freewill gold of Exodus 35:22 and the Levites waved in Numbers 8:11-21, five verses and no others.

**The Passage page.** The ransom list's law words (the kaphar family, cover, nega', shalam) are weak in the stations: they run hot in the law chapters, while the stations are narrative and carry silver, shekel, buy, the kinsman's redeem, the trespass offering and maggefah. The narrative thread is carried by the vocabulary of price and purchase, and the vocabulary of atonement and covering belongs to the law that interprets it, which is the division Hebrews makes when it reads the stories through Leviticus 16. The 'covering' idea rests on Genesis 20:16 (kesut) and Leviticus 16, not on a word running through the stations.

**The stations.** In Genesis 17 'silver' and 'purchase' are the servants 'bought with money', circumcised with the house (17:12, 13, 23, 27): the one chapter where the ransom words and the covenant words stand together. In Numbers 31:48-54 'visit' is 'the sum of the men' and 'there lacketh not one', which TAHOT does not gloss as the census.

**Added after these notes were first written.** goren H1637, the threshing floor, joined the rest list, and terumah H8641, the heave offering, joined the ransom list (the half-shekel is a terumah in Exodus 30:13-15, and so is the captains' gold in Numbers 31:52).

Re-running after any change: `python3 ransom_rest_lists.py`, then `python3 Eval_data/ransom_rest_report.py`.
