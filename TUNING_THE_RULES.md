# Tuning the Rules

How the Word Atlas measures were adjusted, why, and where the adjustments live

## What this paper is about

Word Atlas counts words. It counts how often a word occurs, which words
stand near it, which phrases recur, which passages share rare words
with which other passages. None of that counting is difficult. What
takes care is deciding what to count and what to leave out, and every
one of those decisions is a rule with a setting behind it. This paper
describes the rules that were set, how we found out when a setting was
wrong, how a setting is changed, and where in the project each rule
lives. It is written for someone who reads the pages the atlas
produces, not for someone who reads the code.

The short version is this. The atlas is not a calculator that gives one
right answer. It is a set of rules that give an answer, and the rules
were tuned by reading the answer against the Bible text, noticing where
it looked wrong, tracing the wrong number back to the rule that
produced it, and changing that rule. Every change was made in one
place, tested, kept or thrown away, and the old state was preserved so
it could be brought back. That loop, run perhaps thirty times, is the
whole method.

## The idea of a rule and a setting

Take the simplest measure, weight: how many times a word occurs. Even
that needs rules. Is "day" the same word as "days" and "day's"? Is
"LORD" the same word as "Lord"? Is "the" worth counting at all? Each
answer is a rule. The rule that gathers spellings under one word is
called the stemmer; the rule that leaves out "the" and "of" is the stop
list; the rule about LORD is the capitals rule. Change any of them and
every count on every page changes.

Most rules have a number in them. A neighbor is a word within five
words of another word, inside the same verse: five is a setting. An
echo is a phrase found in two or more books and in no more than six
verses of the whole Bible: six is a setting. Two verses are parallel
when they share at least three content words in the same order and
those words make up at least thirty percent of the shorter verse: three
and thirty are settings. A setting is a decision made once and applied
everywhere, and the point of writing it down as a named number is that
it can be found and changed.

## Where the rules live

The project keeps its rules in two files, and the difference between
them matters.

The first is `atlas_text.py`. Everything in it is applied when the atlas
is built, that is when `build_atlas.py` reads the Bible text and writes
the big table file `atlas.db`. The stop list, the stemmer, the capitals
rule, the window size, the phrase lengths, the echo limit, the choice
between Strong's numbers and English stems as roots, and the rules for
placing and inferring Strong's tags are all here. Changing any of them
means rebuilding the atlas, which takes about a minute. The Rebuild
atlas button in the window does this, and so does running
`build_atlas.py` by hand.

The second is `atlas_pages.py`, which turns the tables into pages. A
few rules are applied here, at the moment a page is asked for, and
changing them needs no rebuild, only a restart of the window. The
parallel rule (three words, thirty percent), the floor under "points
to", the length a run of chapters must reach before the page says a
book "follows the order" of another, the share of a book's verses a
word must appear in before it counts as one of the book's formulas, and
the number of echoes an obs/exp ratio needs before it is printed
without a warning are all here, as named numbers at the top of the file.

The reason for the split is practical. A rule that shapes the tables
has to be applied once to the whole Bible, so it lives with the
builder. A rule that only shapes the reading of a page can be tried and
tried again in seconds, so it lives with the pages. When a rule was
being tuned we preferred, where possible, to put it in the second file
so that trying a value cost nothing.

## Keeping the old state

A rule change that turns out badly must be undoable, and comparing two
states side by side is the only honest way to judge a change. So every
build can be kept under a label: `build_atlas.py --label english`
writes the atlas, then copies it to `builds/english.db` together with
`builds/english.rules.py`, the exact `atlas_text.py` that made it. The
window's Build box lists every kept build, and switching between them
takes a second, so the same page can be read under the old rules and
the new. The Restore rules button copies a kept build's rules back over
the working file, so a rebuild returns to that state.

This is what made the larger changes safe. When Strong's numbers
replaced English stems as the roots, the last English build was kept
first, and every page reviewed afterwards was read against it.

## The loop

Each adjustment followed the same steps, and it is worth stating them
once because they are the method.

First, a page was read against the text. Not skimmed: the reviewer
opened Ezekiel or Mark or Job, looked at the numbers, and asked whether
each one said something true about the book. A number that looked odd
was clicked, because every number on every page can be traced to the
verses that produced it in one click, and the verses said whether the
number was right.

Second, the odd number was traced to a rule. A wrong count of "night"
in Ezekiel traced to the window rule; a phrase list full of "and he
said unto" traced to the phrase rule; a signature list full of ordinary
Greek verbs traced to the rule that compared a Greek word against the
whole Bible.

Third, the rule was changed in one place, the page was rebuilt or
reopened, and the number was read again. Sometimes several values were
tried in a row and the results written into a comment beside the
setting, so the file itself records what each value gave. The
parallel share, for instance, carries a note of what Mark's counts were
at 0.5, 0.4, 0.34 and 0.3.

Fourth, the change was kept if it made the page truer and dropped if it
did not. "Truer" meant that the page now said what a careful reader of
the book already knows, or said something new that the verses bore out
when read. Two filters tried on the parallel rule (requiring a rare
"anchor" word, dropping the commonest words) were dropped because they
lost real parallels without sharpening the false ones.

## The adjustments, in the order they were made

### Words and their spellings

The first pages, Joel and Malachi, showed stemmer leaks: "hundred"
counted as "hundr", "counsel" as "counsell", "leaves" folded into
"leave". Each was an exception added to the stemmer's table, or a new
suffix rule, and the pages gained a "form" column so the commonest real
spelling is printed instead of the stem. This was tuning by list: the
rule was fine, its exceptions were incomplete.

### The window and the stop list

A neighbor is a word within a window of the head word. Five words
either side, never crossing a verse, was chosen at the start and never
changed, but the verse pane had to be made to apply the same rule, so
that clicking a neighbor row shows exactly the meetings the count was
made from. The mismatch of five meetings against seven verses was the
first sign that two parts of the program were counting differently, and
the fix was to make one count and show it in both places. The stop
list was set once, with the rule that LORD, God and Lord are never on
it, and it too has not moved.

### Echoes and their weight

The first echo lists were long and full of idiom. Three rules came in
one after another: an echo must have at least three words; it may occur
in no more than six verses in the whole Bible, or it is idiom rather
than echo; and the prophetic voice tags ("thus saith the LORD") are set
aside before an echo is judged to have enough substance. Echoes were
then given a weight, the summed rarity of their words, so that one
striking shared sentence counts for more than a dozen shared
commonplaces. Rarity itself is a rule: a word's rarity is the negative
logarithm of its share of all words, so a word that is one in a
thousand scores about seven and one in a hundred thousand about eleven
and a half.

### Kin

The first kin measure compared whole chapters as bags of words, and
long chapters won every time because they hold more words. It was
replaced by a verse-pair rule: a verse elsewhere is kin when it shares
three or more rare words with one verse here, rare meaning one in two
thousand or rarer. The pair's score is the summed rarity of the shared
words, raised by up to half when the words come in the same order in
both verses. A bug that counted a repeated word twice in the order
bonus was found by reading an Ezekiel 47 page and fixed by removing
duplicates before the comparison.

### Spread and local words

A word used forty times in one chapter and a word used forty times
across a whole book have the same keyness, but they are not the same
kind of word. Spread multiplies keyness by the share of the book's
chapters the word reaches, and a word in under a fifth of them is
marked "local". Twenty percent is the setting.

### Direction and dates

When the partner table began to say which books share echoes with a
book, the natural next question was which came first. A table of
conventional dates was added, rounded and openly disputed for many
books, and each partner is labelled earlier, contemporary or later,
with a slack of twenty-five years counting as contemporary. Later, for
books whose own date is the disputed one (Job, Joel, Jonah, Daniel and
others), a footer was added saying that the labels are a hypothesis
resting on one date.

### The parallel rule, four times over

The sharing table (4d) tags every verse of a book by whether it has a
parallel in each of the book's two chief partners. For a Gospel this is
the classic source map. The rule for "parallel" was changed four times,
and the sequence is the best example of the loop.

The first rule was a run of four adjacent words with two content words
shared between the books. It tagged too many Synoptic verses as
"neither", and worse, it went the wrong way: a verse with a real
parallel in paraphrase failed while a verse sharing only a stock
phrase passed. The second rule replaced runs with overlap: the content
words the two verses share in the same order, anything allowed between,
must number at least three and make up at least forty percent of the
shorter verse. This is how a synopsis is compiled by hand. It went
into `atlas_pages.py` so that values could be tried without rebuilding,
and the footer was made to print the whole-book tallies at two other
shares beside the chosen one, so a reader can see how firm the counts
are. Reading those three lines against the accepted figures for Mark
settled the share at thirty percent.

Then the Ezekiel page showed the rule failing in a new way. A prophet
has no triple tradition, but Ezekiel showed 359 verses with a parallel
in both Jeremiah and Leviticus, and chapter 12, which is oracles and
nothing else, showed eighteen of twenty-eight. The rule was counting
formulas: "thus saith the Lord GOD" clears three content words in order
against some verse of Jeremiah every time. The fourth adjustment sets
aside, before counting, a book's own formulaic words, defined as the
roots in more than a tenth of its verses, and the page says which words
were set aside. Ezekiel's "both" fell to seventy-three and chapter 12
to three; Mark's figures moved a little, because "Jesus" and "saying"
no longer count, and the great omission stayed where it was.

### Points to, and following an order

The echo-by-chapter table says which partner chapters each chapter's
echoes lead to. The first version listed one; the review asked for
three, with a floor so that a chapter with almost nothing from a
partner does not point at random. The floor is a tenth of the chapter's
echo weight. Then each chief partner was given its own best chapter
first, so a chapter with two strong Matthew pointers still shows its
Mark pointer.

From the pointers a sentence is derived: "follows the order of Matthew
from chapter 5 to 16". The first rule took the longest run of chapters
whose pointers never go backwards, breaking the run at any chapter with
no pointer. The Matthew page showed that a single chapter with no Mark
pointer (25, which points only to Luke) broke a run that plainly
continued, so the rule was changed to pass over such chapters and name
them. Then the Ezekiel page showed the opposite failure: five Jeremiah
pointers with a six-chapter hole produced a "follows the order" line
that was not a finding. The rule now requires the run to be dense: more
pointers than skipped chapters, or five or more with no gap wider than
two. On the Gospels the rule was safe because pointers were dense; on a
prophet it was not, and only reading a prophet's page showed that.

### Strong's numbers as roots

The largest change replaced English stems with Strong's numbers as the
roots of tagged words, so that "straightway" and "immediately" become
one Greek word and "LORD" and "Lord" become two Hebrew ones. It came in
several rules, each tuned by reading.

Placing the tags. The tagged source counts words differently from the
KJV rows in places, so each tag is placed by looking for its word near
where its position says, allowing for the drift found so far in the
verse. A word given two numbers takes the rarer, since the frequent
numbers are the grammatical ones. About 99.7 percent of tags land.

Inferring the rest. A word the tagger left untagged takes the number
its spelling usually carries in the same book, or failing that the same
testament, but only when tagging is the rule for that spelling: at
least three tagged occurrences, one number holding at least half of
them, and tagged occurrences outnumbering untagged ones. The first
version inferred at testament scope only and gave "behold" and "hast"
wrong numbers; requiring tagging to be the norm fixed that, and adding
book scope first let Ezekiel's untagged "side" join the number it
carries nearly every time in Ezekiel.

Absorbing two-word renderings. An untagged word that stands beside the
same tagged word at least sixty percent of the time, five or more
times, is folded into it: "chief" into priests, "burnt" into offering,
"thus" into saith, "round" into about. These are the KJV's two-word
renderings of single Hebrew and Greek words, and the absorbed token is
set aside like a stop word so the number is not counted twice.

Capitals. The original capitals rule kept any all-capital word as its
own token, which was harmless in English builds and harmful in
Strong's builds, where "THE KING OF THE JEWS" looked rare and headed
every echo list. Only the divine names keep their capitals now.

The same-testament baseline. The first Strong's pages had section 1
full of ordinary Greek verbs, because a Greek number can occur only in
the twenty-seven New Testament books and every Greek word is therefore
far above its rate in a Bible that is three quarters Hebrew. Matthew's
list described Koine Greek rather than Matthew. The fix compares a
Strong's number with the rest of its own testament, an English stem
with the rest of the Bible, and says so in the column heading. With
that one change the lists became the characteristic vocabulary of each
evangelist that scholars compiled by hand a century ago, which was the
strongest confirmation the atlas has had that its rules were right.

Renderings. Because one number can stand behind many English words
(aphiemi is leave, forgive, let and suffer), the signature table's note
column now says how many renderings a root has, so the one spelling
printed does not hide the others.

### Formulas on roots

The last measure still on English wording was the formula. With the
roots in place, a formula became a run of units in which each tagged
content word stands as its Strong's number, so "the heathen" and "the
nations" are one formula and "thus saith the Lord GOD" is found however
a translator renders it. Each formula carries its commonest English
wording for display, read off the verses it is found in, so the tables
still read as English while the counting is done on the Hebrew and
Greek. This was the step your reading of the 1a tables pointed to: once
every number showed its lemma, the phrases were the one thing left
being counted in translation.

### Small guards

Two more came from the Job page. An obs/exp ratio built on fewer than
twenty echoes is printed in brackets and marked "few", because a small
book with a few shared idioms always posts a high ratio. And the
concentration line under the signature words is followed by the same
figure with proper names set aside, since a book named after its hero
will always have him first. A name, for this purpose, is a word the
text prints with a capital inside verses more often than not, which is
a rule read off the text rather than a list.

### The later adjustments

After the formulas moved to roots the work went on book by book, and
each book added a rule or two. Ezekiel showed that the partner table
rewarded volume, so a "who reads whom" table now gives each partner's
best echoes with both references, and an echo of five or more words
found in exactly two verses of the Bible is marked quotation grade.
Building that table showed that a Hebrew root and a Greek root never
match, so every echo between the testaments had silently vanished;
those are now found by English wording as before. Revelation showed
that the parallel rule, made for the Synoptics, missed a five-word
borrowing inside a long verse, so a quotation-grade echo now counts as
a parallel, and the sharing table steps aside when it fits a book too
poorly to mean anything. Genesis showed a formula that tidied down to
one word ("and joseph") and chapters whose leading words were all
elsewhere, so both are handled. Leviticus showed that the commonest
spelling of a root across the Bible can be the wrong label for a
chapter (H1540 is "captive" everywhere but "uncover" in Leviticus 18),
so a page now uses its own scope's spelling. And Exodus, whose two
halves mirror each other chapter for chapter, showed that every echo
section compared a book with other books and none with itself, so a
book page now ends with a map of the book against itself. The same
page fixed "father in law", which had been splitting into "father" and
"law", by letting absorption reach across one stop word and run before
inference.

The Mark dossier then raised a question the pages could not answer:
why "sick" stood in Mark's signature words as an untagged English
stem when the Greek word for sick has a number. Counting the untagged
words across the whole build answered it, and the answer was two
rules rather than one. Twelve percent of the content words had no
number, and more than half of those were forty-odd English grammar
words the stop list had never included (hath, shalt, hast, against,
therefore, thereof, because, mine, himself), which Hebrew and Greek
carry as endings or prefixes and the tagger rightly leaves alone; the
atlas had been counting them as neighbours and kin for months. They
went on the stop list. The "sick" cases were the other rule: the
tagger gives one number to one English word, so where one Greek word
became three English ones ("sick of the palsy", paralytikos) the
number sits on "palsy" and "sick" is left bare, and no share rule
could catch it because "sick" has three different partners in Mark
alone. The dictionary already loaded for the lexicon settles each
case on its own: when a bare word stands within two stop words of a
placed tag whose KJV gloss names that word, it is absorbed into it.
That one rule took fourteen thousand words ("burnt offering", "round
about", "went out", "cut off", "young men", "fine linen", "came to
pass") and left three percent of the content words without a number,
nearly all of them words the text really does split between two
roots ("went" between H3212 and H1980).

## How the shaping works

Looking back over the whole run, there is a shape to it that is worth
stating plainly, because it is the method more than any one rule is.

The atlas was not designed and then tested. It was shaped by reading
it against books whose structure is already known. Each round took one
book, produced its pages, and read them the way a commentator would:
does the signature list name the words a handbook on this book would
name, does the chapter outline fall where the chapter divisions fall,
do the partners and pointers reach the passages the cross-references
reach. Where the page agreed with what is known, the rules behind it
were confirmed. Where it disagreed, one of two things was true: the
page had found something real that the reader had not known, and the
verses settled that in a click; or a rule was wrong for this kind of
book, and the wrong number could be traced to it. Known results were
the calibration, and the books were chosen to be different from one
another so that each would test a different rule. The Gospels tested
the parallel rule because whole verses are shared; Ezekiel tested it
because formulas are shared instead; Job tested the same-testament
baseline because its Hebrew is unusual; Revelation tested the echo
tables because it borrows phrases, not verses; Genesis tested the
names; Leviticus tested the spellings; Exodus tested whether a book
could be compared with itself.

Two people did this, with different jobs. One read the pages against
the text and against what scholars have said about the book, and wrote
down what looked right, what looked wrong and what was missing. The
other traced each wrong number to its rule, changed the rule in one
place, ran the page again, and reported what moved. The reviewer never
needed to read the code and the builder never needed to decide what
Ezekiel ought to say; the page was the meeting point. The reviews grew
longer as the pages grew richer, and by the later rounds a review was
itself a piece of writing about the book, with the fixes at the end.

The rhythm was always the same: a page, a review, the fixes, a
rebuild if the rules that make the tables had changed, a commit with a
short message saying what changed, and then the next book. Nothing was
changed without a page to show why, and nothing was kept without a
page to show it was better. Because the old build was always beside
the new, a change that broke something was caught by the next review
rather than by accident months later, and the two builds could be
compared page for page until the breakage was found.

The pages also suggested their own next features. Depth came from a
reviewer wanting to know where a word mattered most; the who-reads-whom
table came from having combed forty-eight chapter pages by hand for
the partner names; the map of a book against itself came from seeing
Exodus's two halves and having no section that could show them. In
each case the need was stated in terms of the page ("this section
would be writable from the book page if..."), and that is the form a
request should take: not a rule to change, but a thing the page ought
to show and does not yet.

So the shaping is a loop with a book at its centre. Choose a book
whose structure is known, read its pages against that knowledge, trace
every disagreement to a rule or to a discovery, change the rule or
keep the discovery, and move to a book that will strain something
else. The vocabulary grew the same way, one word at a time as a page
used a term the list had not defined. After thirty rounds the rules
files are a record of every decision and the pages read as a
description of each book that a careful reader would recognise, which
is the test the whole thing was built to pass.

## What the process taught

A few things became clear across the thirty or so changes.

A rule that is right for one kind of book can be wrong for another. The
order rule and the parallel rule were both tuned on the Gospels, where
pointers are dense and formulas are few, and both failed on Ezekiel. The
fix in each case was not a special case for prophets but a more honest
general rule, one that asks whether the evidence is dense enough or
whether the shared words are the book's own boilerplate.

A wrong number is more useful than a right one, provided it can be
traced. The verse pane, which shows the verses behind any number in one
click, was the tool that made every trace possible, and the decision to
keep every count and its display drawn from one source, so that two
parts of the program cannot disagree, paid for itself several times.

Settings should be visible and their trials recorded. Every named
number in the two rules files carries a comment saying what it does
and, where values were tried, what each value gave. The files are the
lab notebook.

And keeping the old build beside the new is what makes a large change
possible at all. The Strong's build changed more than the previous two
rounds together; some of it was a real gain and some of it broke things
that had been working. Only by reading each page under both builds
could the two be told apart, and the gains kept while the breakage was
repaired.

## Where to look

The build-time rules, with their comments and trial notes, are at the
top of `atlas_text.py`: the stop list, the divine capitals, the window,
the phrase lengths, the echo limit, ROOTS, the tag-placing span, the
inference and absorption thresholds, the parallel settings and the book
dates. The page-time rules are at the top of `atlas_pages.py`: the
table sizes, the local share, the order-run minimum, the trial shares,
the formulaic share, the home-word settings and the obs/exp minimum.
Kept builds and their rules are under `builds/`. The README describes
each measure and each phase; `HOW_WORD_ATLAS_GREW.md` tells the story of
the program; the cheat sheet explains the window; and help mode (the ?
button, or F1) explains any number on any page while you point at it.
