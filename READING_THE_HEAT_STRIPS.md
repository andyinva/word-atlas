# Reading the Heat Strips

`atlas_heat.py --svg` draws a picture of one book as a set of colored
strips stacked on top of each other. This page explains what you are
looking at.

## The picture as a whole

Read each strip from left to right, the way you read the book. The left
edge is chapter 1 and the right edge is the last chapter. Chapter numbers
run along the bottom.

Each thin vertical slice of a strip is one **window**: ten verses in a
row (or whatever `--window` is set to). The next slice moves one verse
further along, so neighboring slices share most of their verses. That is
why the colors change smoothly instead of jumping.

Point at any slice to see its verses and its exact score.

## What the colors mean

Every slice is compared with **ordinary** text. By default, ordinary means
all the windows of the Old Testament (for an Old Testament book) or of
the New Testament (for a New Testament book). With `--norm book`, ordinary
means the book itself.

| Color | Meaning |
|---|---|
| **Gray** | Ordinary. This stretch is about like typical text. |
| **Red** | Above ordinary: more of whatever the strip measures. The deeper the red, the further above. |
| **Blue** | Below ordinary: less of whatever the strip measures. The deeper the blue, the further below. |

The depth of the color comes from the **z-score**, a measure of how
unusual a value is:

- **z = 0**: exactly ordinary (gray)
- **z = +1 or -1**: a little off ordinary (pale red or pale blue)
- **z = +2 or -2**: clearly unusual. About 1 window in 20 reaches this by chance. The text report lists these as **hot spots** (red) and **cool spots** (blue).
- **z = +3 or -3 and beyond**: strongly unusual (the deepest red or blue)

Red is not "good" and blue is not "bad." Red only means *more* and blue
only means *less*. Whether more is interesting depends on the strip.

## Three scales (`--scale`)

The colors always mean the same thing (gray ordinary, red more, blue less),
but you can choose how "how far from ordinary" is measured.

**z** (the default). Distance from the ordinary average, in spreads.
This fits density, variety, rare, hammer and action. It works poorly for
the feeling strips: most ordinary windows have none of those words, so a
handful can produce a z of +18.

**percentile**. The share of ordinary windows that score lower. 50% is
ordinary, 99% is hotter than 99 ordinary windows in 100, and the score
can never go past 100%. This needs no bell curve, so it is the fairest
scale for the feeling strips and the best one for the picture. On the
feeling strips, a window with none of the words is set to exactly 50%
(gray), because most text has none of them: "none here" is ordinary, not
a finding.

**g2**. Log-likelihood (Dunning's G squared), the same keyness measure
used everywhere else in the atlas. For the strips that count words, it
asks how surprising this window's count is, given the ordinary rate.
3.84 is good evidence and 10.83 strong evidence. It also weighs the
amount of text, so a few words in a short window count for less. It is
the best scale for deciding which hot spots are real. Variety and hammer
do not count words this way, so they stay on z.

Behind the scenes all three use the same z-like number for the colors
and for `--threshold`. A threshold of 2 is about the top or bottom 2.3%
on any scale. On g2 the default threshold is 3.29, which is G2 10.83.

| Question | Scale |
|---|---|
| What does the book look like? | percentile |
| Which hot spots can I trust? | g2 |
| Matching the reports made so far | z |

## The five wording strips

These measure how the text is written, whatever it is about.

**density**
How packed the text is with content words (nouns, verbs, descriptive
words) instead of small words like "and, the, of, unto."
- Red: tightly packed description. Revelation runs red here through most of the book.
- Blue: thinner, more connective prose, such as dialogue or argument.

**variety**
How many *different* words are used, counted in steady runs of 50 words
so long and short stretches compare fairly.
- Red: the writer keeps reaching for new words, as in a rich description or a catalog of goods.
- Blue: the same words come around again and again, as in measurements, borders and rituals. Ezekiel 40-48 (the temple and the land) is deep blue.

**rare**
How many of the words are used 10 times or fewer in the whole Bible.
- Red: unusual vocabulary. Ezekiel 27 (Tyre's ship and cargo) and Revelation 21 (the jewels of the city) are the peaks.
- Blue: everyday vocabulary.

**hammer**
How much of the window is taken up by one repeated word. This is the
"vertical" or depth idea. Some words are not counted, because they repeat
everywhere and say little: the divine-speech formula words ("saith the
Lord GOD"), the 100 most used words of the language ('have', 'God',
'great'), words the KJV mostly renders as small function words (the forms
of "to be"), and place words such as 'before' and 'midst'. The word is
named in the KJV's own English for that stretch, so ekcheo shows as
'poured out' in Revelation 16.
- Red: one word is being driven home. The text report and the chart's tooltip name the word, so you can tell rhetoric ('feed' in Ezekiel 34, 'beast' in Revelation 13) from bookkeeping ('cubits' in Ezekiel 40, 'sealed' in Revelation 7).
- Blue: no single word dominates.

`--hammer-window 30` measures hammer over about a chapter instead of ten
verses, for repetition that is spread out. `--hammer-skip 0` counts the
common words again.

**action**
How many of the words are verbs.
- Red: driving narrative or a stream of commands.
- Blue: still, descriptive text: lists, visions, inventories. Revelation 18's cargo list and Revelation 21's city are deep blue.

## The feeling strips

These appear once the reviewed feeling-word list has been imported into
metadata.db (`atlas_feelings.py import`). They measure what kind of
charged words the text uses.

**feeling**
All the feeling words together, whatever their category.
- Red: a highly charged stretch. Ezekiel 16 and 23, and Revelation 18, are among the hottest.

With `--families`, seven more strips break that down:

| Strip | Counts words of | Red example |
|---|---|---|
| **emotion** | anger, grief, fear, joy, love, shame | Ezekiel 16:42-63 (shame), Revelation 18 (weeping, mourning) |
| **senses** | color, sound, smell | Ezekiel 1 (voice, brightness, sapphire), Revelation 8-9 (trumpets) |
| **body** | flesh, bones, breasts, loins, womb | Ezekiel 37 (the dry bones) |
| **violence** | sword, blood, slay, death, grave | Ezekiel 21 (the sword song), Ezekiel 32 (the slain in the pit) |
| **sacred** | altar, censer, lampstand, golden vessels, temple | Revelation 8 (altar and censer), Revelation 15-16 (temple and vials), Ezekiel 43-44 |
| **wealth** | trade goods: gold, silver, jewels, merchants | Ezekiel 27, Revelation 18, Revelation 21 |
| **harlotry** | harlot, whoredom, fornication, lewdness | Ezekiel 16 and 23, Revelation 17 |

**Blue on the feeling strips:** these strips can show more than ordinary
but hardly less. Most ordinary text has few or none of these words, so
"ordinary" already sits near zero, and a window can't fall below nothing.
Read them as red or gray: red is a finding, gray is not. On the z scale
"none here" can look pale blue; on the percentile scale it is gray.

Sacred and wealth were split so that gold in the temple (the golden
lampstands, censer and bowls) is not counted as merchandise. In Revelation
this keeps Babylon's wealth (chapter 18) apart from the furniture of
worship (chapters 1, 8, 15-16).

**Very large numbers:** harlotry and wealth are rare everywhere, so even
a few such words make a window far above ordinary. Their z-scores can run
to +10 or +20. Read those as "far above ordinary," not as a precise size.
The color stops getting deeper at 3.

## Reading strips together

The real value comes from reading the strips against each other. A
stretch that is red on several strips at once has a distinct character.
For example:

- **Ezekiel 27 and Revelation 18** are both red on density, rare, wealth and grief, and blue on action. That is the signature of a merchant's lament: a still, richly worded catalog of lost goods, mourned aloud.
- **Ezekiel 40-48** is blue on variety and action and red on hammer: measured, repetitive and static.

## Reading the text report beside the picture

The text report (`--out`) holds the same information as lists:

- the **hot** and **cool** spots for each strip, with their verses and peak score
- for **hammer**, the repeated word
- for **feeling** strips, the categories and words behind each hot spot
- a **chapter table** giving each chapter's average z on every strip

## Commands

    python run_heat.py                                (the standard set for Ezekiel and Revelation)
    python run_heat.py Joel Malachi                   (the standard set for other books)
    python atlas_heat.py Ezekiel --svg reports/heat_ezekiel.svg
    python atlas_heat.py Ezekiel --families --svg reports/heat_ezekiel_feelings.svg
    python atlas_heat.py Ezekiel --norm book          (compare the book with itself)
    python atlas_heat.py Ezekiel --window 15          (wider, smoother windows)
    python atlas_heat.py Ezekiel --threshold 1.5      (list milder spots too)
    python atlas_heat.py Revelation --hammer-window 30 (hammer over about a chapter)
    python atlas_heat.py Revelation --families --scale percentile
    python atlas_heat.py Revelation --families --scale g2
