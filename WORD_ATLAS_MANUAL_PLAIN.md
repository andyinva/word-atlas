# Word Atlas: The Easy-to-Read Manual

For version 0.10.70. Andrew Hopkins, with Claude. October 5, 2026.

This is the plain version of the Word Atlas manual. The full manual, WORD_ATLAS_MANUAL.md, describes every table, every rule and every setting in detail and runs to more than four thousand lines. This version is for a person who has never used the program and who may not know the technical words. It explains each term the first time it is used, it uses complete sentences, and it leaves out the finer details that only someone changing the program would need. Where this version says less than the full manual, the full manual is right, and its section numbers are the same as the ones here, so a reader can move from one to the other.

## Part I. What the program is and how to use it

### 1. What Word Atlas is

Word Atlas is a computer program that counts words in the Bible and shows what the counts mean. The name comes from a road atlas. A road atlas has maps at different scales: a map of the whole country, a map of one state, a map of one city. Each scale shows relations that the other scales hide. A word in the Bible works the same way. The word "LORD" is everywhere in the Bible, so at the scale of the whole book it is the largest thing on the map. The word "vine" is rare across the whole Bible, so at that scale it hardly shows. But turn to John chapter 15, where Jesus says "I am the vine," and "vine" is the largest word on that page. Word Atlas lets you look at words at every one of those scales.

The program reads the King James Bible, does its counting once, and stores the results in a file called atlas.db. A file whose name ends in .db is a database, which is a file arranged so that a program can look things up in it very quickly. After that, the program shows you the results as pages, and you turn from page to page as you would in an atlas. The most important habit to form is this: every number on every page can be traced back to the verses that produced it with a single click. When a number looks strange, click it and read the verses.

There are eight kinds of page. A Book page shows one book of the Bible. A Chapter page shows one chapter. A Section page shows one part of a book, such as the second of the five books that make up the Psalms. A Word page shows one word across the whole Bible. A Kin page shows which chapters elsewhere in the Bible are most closely related to a chapter you choose. A Testament page shows, for the Old or the New Testament, which words belong most to which books. A Passage page shows any set of verses you have named, even if they come from several books. A Compare page sets two books side by side, chapter against chapter.

The words the program counts are not the English spellings. They are the Hebrew and Greek words behind the English. This is possible because every word of the King James text the program uses has been tagged with a Strong's number. Strong's numbers come from a reference book made in the nineteenth century by James Strong, who gave every Hebrew and Greek word in the Bible a number, so that a reader who knows no Hebrew or Greek can still tell which original word stands behind an English word. Hebrew words have numbers beginning with H, and Greek words have numbers beginning with G. The divine name, usually printed as "LORD" in capitals, is H3068. Because of these numbers, the program can tell that "the heathen" in one verse and "the nations" in another are the same Hebrew word, and it counts them together.

### 2. What you need

The program is written in Python, a programming language, and it runs on Ubuntu Linux and on Windows. To use the window version you need Python 3 and a package called PyQt6, which is what draws the window. The version that runs from the command line needs nothing beyond Python.

You also need two data files that are not included with the program, because they are large and belong to other projects. The first is bibles.db, the database that the Bible Search Lite program uses. It must contain the King James text and a table that gives the Strong's number for every word. The second is strongs.csv, which is Strong's dictionary in a form the program can read. That file is what lets a page print a Strong's number together with the Hebrew or Greek word it stands for and the English words the King James translators used for it.

### 3. Starting the program

Open a terminal in the project folder and start the program with the command "python word_atlas.py". On Linux you first activate the program's own copy of Python with "source venv/bin/activate"; on Windows the command is "venv\Scripts\activate". If you use the Project Launcher, choosing "Word Atlas" there does the same thing.

The window needs the file atlas.db beside it. If that file is missing, it has to be built first. Building it means reading the whole Bible and computing every table, and it takes about a minute. You can build it by running "python build_atlas.py" in the terminal, or by pressing the Rebuild atlas button in the window. The build prints a running tally as it works and ends by writing atlas.db, which is about 150 megabytes.

### 4. The window, from top to bottom

If you are ever unsure what something in the window does, press F1, or click the question-mark button at the far left of the top bar. This turns on help mode. In help mode you point at any button or box and a note appears saying what it is and what clicking it would do. Help mode ends when you click anywhere, press Escape, or press the button again.

The top bar is where you choose a page. The Page box lets you pick the kind of page: Book, Chapter, Section, Passage, Word, Kin, Testament or Compare. The boxes to its right change to suit the kind you picked. For a Book page you pick a book. For a Chapter page you also pick a chapter number. For a Section page you pick a part of the book from a list. For a Word page you type a word, such as "day" or "vine", or a Strong's number, such as H3068. For a Compare page you pick a second book in the box marked "with". The Go button opens the page. Two arrow buttons let you turn back and forward through the pages you have already visited, like turning pages in a book.

Three buttons on the top bar write files. Save as text writes the page you are looking at into the reports folder as a plain text file. Save dossier writes everything the program can say about one book into a single text file; section 19 explains what that file contains. Rebuild atlas recomputes every table from the Bible text.

Below the top bar is the Ask row. It holds a box where you can type a short line of notation to ask for a page directly, which section 6 explains, a Build box that lets you choose which copy of the atlas you are looking at, and a Restore rules button that section 9 explains.

The middle of the window is the page itself. It begins with a title, then a build line that says which version of the program and which build of the atlas made the page, then a few notes about the book or chapter, and then one table for each section of the page. Every table has a note above it that explains what its columns mean, and many have a footer below with totals or cautions. Three of the tables are also drawn as pictures: the echo map, the shadow map and the reach-and-depth chart.

The bottom of the window is the verse pane. When you click any row of any table, the verses behind that row appear here. This is the one-click rule mentioned above: no number is ever more than one click away from the text that produced it. A drag bar between the page and the verse pane lets you make either one larger.

### 5. Clicking around

Clicking a row shows its verses in the verse pane. Double-clicking a word in a table opens that word's page. Double-clicking a chapter number in a table, a map or a chart opens that chapter's page. Clicking a bar on the shadow map shows the word's verses in that book. Clicking a point on the reach-and-depth chart shows the word's verses in the chapter where it matters most, and double-clicking opens the word's page. Clicking a cell in the echo map or in a chapter map shows the verses on both sides of the echo. Holding the mouse over a cell, bar or point shows the exact number in a small box.

### 6. The Ask line

The Ask box takes a single line written in a simple notation. Single quotes go around a word, double quotes go around a phrase, and square brackets go around the scale, which can be a book, a chapter, a section or the whole Bible.

Typing 'day' opens the word page for "day" across the Bible. Typing 'day' [Joel] opens the word page for "day" limited to the book of Joel. Typing "the day of the LORD" lists every verse holding that phrase, and adding [Joel] limits the list to Joel. Typing [Joel] opens the book page for Joel, and Joel 2 opens the chapter page for Joel chapter 2. Typing [Psalms: Book II] opens a section page, [New] opens the New Testament page, and [Matthew] x [Mark] opens the Compare page for those two books. Typing Joel 2:1 shows that one verse. Typing Ezekiel 47 -> ? opens the Kin page for Ezekiel 47, which shows the chapters most related to it. Typing 'day' + 'night' [Ezekiel] shows the verses in Ezekiel where "day" and "night" occur near each other.

Capitalized words such as LORD and God keep their capitals; everything else can be typed in lower case. If the program cannot read the line, the status line at the bottom says what it expected.

### 7. Saving pages and dossiers

Save as text writes the page on screen to the reports folder, with every picture printed as its table. Save dossier writes a much larger file: everything the program can say about one book. The button asks whether to trim the chapter pages. Answering Yes keeps, for each chapter, only its leading words, its signature words, its formulas and its synopsis, which is usually enough for a review.

Every saved file begins with a build line under its title, such as "Word Atlas 0.10.70; build 'strongs' made 2026-09-30, roots Strong's numbers, window 5, KJV". A file read weeks later then says exactly what made it. If the atlas was built by an older version of the program, the build line says so and tells you to rebuild.

### 8. The command line

Every page can also be printed as plain text without opening the window, and saved under the reports folder. The command "python3 atlas_query.py book Joel" prints the book page for Joel. Similar commands print a chapter, a word, a kin page, a testament, a section, a passage or a comparison. The command "python3 atlas_query.py dossier Isaiah" writes Isaiah's dossier, and "dossier all" writes a dossier for every book of the Bible.

Three options trim any page for reading at a glance. The option --top 8 keeps only the first eight rows of every table. The option --only 1,2,4a keeps only the sections with those numbers. The option --quiet leaves out the notes and footers. The option --time prints how many seconds each section took to build, which is useful when a page seems slow.

### 9. Builds: rebuilding, keeping and going back

The atlas is built from rules, and the rules are sometimes changed. To make such changes safe, every build can be kept under a label. The command "python build_atlas.py --label strongs" builds the atlas and keeps a copy under that label, together with a copy of the exact rules file that made it. The Build box in the window lists every kept build, and switching between them takes a second, so the same page can be read under the old rules and the new. The Restore rules button copies a kept build's rules back over the working rules file, so that the next rebuild returns to that state.

You need to rebuild the atlas only when the rules for reading the text change. Most changes to the program change only the pages, not the atlas, and need no rebuild.

### 10. The files in the project folder

The program is made of several Python files, each with one job. The file word_atlas.py is the window. The file atlas_pages.py builds the pages. The file atlas_query.py prints pages as text and writes dossiers. The file build_atlas.py builds the atlas from the Bible text, using the rules in atlas_text.py. The file atlas_sections.py is the table of sections, the parts into which books are divided, which section 28 explains. The file atlas_function.py measures the small grammatical words, which section 24a explains. The file atlas_septuagint.py reads the Greek texts, which section 28d explains. The file atlas_report.py knows what a report looks like, and atlas_results.py asks questions of the results database. The file test_atlas.py is the set of checks run before every change is saved to the shared repository.

Three database files hold the data. The file atlas.db is the atlas itself. The file metadata.db is the catalogue, a small database of decided facts about the books, such as which kind of book each one is and which passages have been named, which section 28b explains. The file lxx.db holds the Greek Old Testament, the Greek New Testament and the tagged Hebrew Old Testament, which section 28c explains.

### 11. What every page has in common

Every page begins with a title, a build line and a few notes, then one table per section. Each section has a number, and the numbers are the same on every page of the same kind, so that "section 4" means echoes on every book page and every chapter page. A letter after the number marks a companion table: 1a is the words behind table 1, and 4a is the partners of the echoes in table 4. A number after a dot marks a repeat: 3.1, 3.2 and 3.3 are the neighbors of three different words.

A table that cannot be measured is not simply left out. It keeps its title and number, and in place of the table it prints one or two sentences saying why it could not be measured and what to read instead. This matters because a reader who found no table might think the program had nothing to say, when in fact the program has something important to say, namely that the measurement is not defined here.

Three kinds of number run through every table, and section 20 explains them: counts scaled to the size of a text, measures of how surprising a count is, and measures of how rare a word is.

## Part II. The pages

### 12. The Book page

The Book page is the longest page and the one to learn first. Its sections run from the words of the book, through its phrases, to its relations with other books, and finally to the book against itself and its own parts. On the command line and in a dossier the page begins with a list of its sections, because the numbering is not something a first reader could guess.

Section 1, Signature words, lists the words this book uses far more often than the rest of its testament does. The word "testament" here means the Old Testament or the New Testament, whichever the book belongs to; a Hebrew word is compared with the rest of the Old Testament and a Greek word with the rest of the New. The words are ranked by keyness, which is a measure of how surprising the count is, explained in section 20. For each word the table gives its count, its rate per thousand words here and in the rest of the testament, how many chapters and books it reaches, and its depth, which is the chapter where it matters most. Isaiah's list begins with Zion, Assyria, Hezekiah, formed, created, woe, isles and righteousness, which a reader of Isaiah will recognize at once.

Section 1a, The words behind section 1, shows the Hebrew or Greek word behind each English word, with Strong's definition and every English spelling the King James uses for it. This is where you learn that the word printed as "formed" in Isaiah is the Hebrew verb for what a potter does with clay.

Section 1b, Signature words against the book's kind, repeats the measurement with a fairer comparison. Instead of the whole testament, each word is compared with the other books of the same kind, which the catalogue assigns: the books of the Law, the History books, the Poetry books, the Prophets, the New Testament narratives, and the Epistles. Against the whole Old Testament, Isaiah's list is full of words that every prophet uses, such as "hosts" and "nations". Against the other prophets, those fall away and the words that make Isaiah Isaiah rise: redeemer, salvation, chosen, created, sing.

Section 1c, Function words against the book's kind, looks at a different kind of word altogether, the small words that carry no subject: "and", "the", "in", "which", "not", and the pronouns. Every writer has habits with these words, and the habits are hard to change on purpose. The table gives the book's rate for each of about two dozen such words beside each book of its kind, and a single number called Delta that says how far apart two books are in these habits. Section 24a explains Delta and how to read it.

Section 1d, Vocabulary richness against the book's kind, asks how wide the book's vocabulary is: how many different words it uses per thousand words, how many words it uses that appear only once in its testament, and how many words it uses that appear in no other book. These are compared with the other books of its kind and with what a book of the same size would be expected to show, because a longer book naturally repeats its words more.

Sections 1e and 1f appear on New Testament books only, and they measure the book's Greek against the Septuagint, which is the Greek translation of the Old Testament that the New Testament's writers read. Section 1e lists the Greek words the book uses far more than the Septuagint does, and section 1f lists the book's words that belong more to the Septuagint than to the rest of the New Testament, which is a measure of how much a writer sounds like the Greek Bible. Section 28d explains these.

Section 2, Signature formulas, lists the set phrases of two to five words that the book uses far more than the rest of the Bible does, such as "in that day" and "the Holy One of Israel" in Isaiah. Because the words are counted as Hebrew or Greek roots, "the heathen" and "the nations" are one formula.

Sections 3.1, 3.2 and so on, Neighbors, show, for a few key words, which other words occur near them more often than chance would predict. The measure is called pull, and section 23 explains it.

Section 4, Echoes, is the first table about the book's relations with other books. An echo is a run of three or more words found in this book and in one other book, and in no more than six verses of the whole Bible, so that a common phrase such as "the Lord of hosts" does not count. Echoes are what quotation, allusion and shared idiom look like when counted. An echo of five or more words found in exactly two verses of the Bible is given the grade "quotation", which is the strongest evidence the method has that one passage is repeating another.

Section 4a, Echo partners, totals the echoes by partner book and says, for each partner, how many echoes it would be expected to share by chance given its length, and whether it is dated earlier or later than this book. Section 4a2, Who reads whom, lists the three best echoes with each partner, with the verse on each side, so that the reader can judge the direction of borrowing. Section 4b, Echoes by chapter, says where in the book the echoes fall. Section 4c, the Echo map, draws the chapters of the book against the chief partner books as a grid of shaded cells. Section 4d, the Sharing table, marks every verse of the book by whether it has a parallel in each of the book's two chief partners; on the Gospel of Mark this is the classic map of which verses Matthew and Luke share.

Section 4e, Septuagint echoes, finds echoes across the two testaments in Greek, by matching the Greek New Testament against the Greek Old Testament, and section 4f lists the echoes found through the English wording that the Greek does not confirm. Section 28d explains both.

Section 5, Reach and depth, is a chart with one point for each signature word. Reach, across the chart, is how many chapters of the book the word touches. Depth, up the chart, is how strongly it belongs to its deepest chapter. Words at the top right belong to the whole book; words at the top left belong to one chapter only.

Section 6, Echoes within the book, turns the echo method inward. It is a grid of chapters against chapters, shaded by the rare phrasing each pair shares, and it shows where a book repeats itself: Exodus 25 to 31, the instructions for the tabernacle, against Exodus 35 to 40, the building of it. Section 6a gives each chapter's closest chapter in the book. Section 6b lists the book's refrains, which are phrases found in three or more of its chapters. Section 6c, Kin within the book, finds chapters that share rare words in any order, which catches a story retold in different phrasing. Section 6d, Shared vocabulary, finds chapters that draw on the same uncommon words.

Section 7, Sections, appears for a book that has been divided into parts in atlas_sections.py, and section 28 explains those divisions. For each part it gives the size and the leading words, which are the words most distinctive of that part against the rest of the book. Section 7a is the echo map summed to parts, 7b is the within-book map summed to parts, 7c is the reach-and-depth chart with parts as its unit, and 7d is the function-word table by part, with each part's Delta from the rest of the book. Section 7x lists any parts that cross into another book.

### 13. The Chapter page

The Chapter page opens with the chapter's leading words, which are the words whose deepest chapter in the whole book is this one. Then come the same sections as the book page, numbered the same way, run over the chapter alone: its signature words, the words behind them, its formulas, its neighbors, its echoes and their partners, and the Septuagint echoes of its own verses.

Two sections are special to the chapter page. Section 5, Synopsis, prints the chapter verse by verse with its closest parallels in the book's two chief partner books, which is the chapter laid out as a synopsis of the Gospels lays out Matthew, Mark and Luke in columns. Section 6, Kin, lists the eight chapters elsewhere in the Bible that share the most rare words with this one.

### 14. The Section page

A Section page runs the book page's tables over one part of a book alone: Book II of the Psalter, or Ezekiel's temple vision, or the second half of Isaiah. It is reached from the Page box by choosing Section, then a book, then the part. A section that crosses from one book into another, such as the Succession Narrative, which runs from 2 Samuel 9 into 1 Kings 2, has a page of the same kind that measures its parts as one text; section 28 explains these.

### 14a. The Passage page

A passage is any set of verse ranges in any books, which you name and store in the catalogue with the script atlas_passages.py. A Passage page measures the whole set as one text: its signature words, its formulas and its echoes with the books outside it. It is the page for a study that does not follow chapter boundaries, such as "the harlot city" in Ezekiel 16 and 23 together with Revelation 17 to 19.

### 15. The Word page

The Word page is one word across the whole Bible. Section 1 is the shadow map: one bar per book, in the order of the Bible, showing how much the word belongs to each book. Section 2 is its neighbors, and section 3 is the formulas it lives in. When the typed word stands for more than one Strong's number, the page uses the commonest and lists the others.

### 16. The Kin page

The Kin page answers the question "which chapters elsewhere are most like this one?" for a chapter or a range of verses. Two verses are kin when they share three or more rare words in any order, where rare means one in two thousand words or rarer. Ezekiel 47:12 and Revelation 22:2, which both speak of a river, trees, fruit, leaves and months, are kin although they share no phrase. Section 26 explains the measure.

### 17. The Testament page

The Testament page is for the Old or the New Testament as a whole. Section 1 lists, book by book, the words most at home in each book. Section 2, the home map, is a grid of books against their top words. Section 3 answers, for any Strong's number, whose word it is: the book where it is most at home and the share of its occurrences that fall there.

### 18. The Compare page

The Compare page sets two books side by side, chapter against chapter. Section 1 is a grid of the first book's chapters down the side and the second book's across the top, shaded by the rare phrasing each pair of chapters shares. Sections 2 and 3 give, for each chapter of each book, its closest chapter in the other book. Sections 4 and 5 count the verses of each book that have a parallel in the other. Section 6 prints those parallel verses side by side. A footer says whether one book follows the other's order, which on Matthew against Mark is part of the classic argument that Mark was written first.

### 19. The dossier and the results database

A dossier is everything the program can say about one book in one text file. It holds the book page with every section, the book's rows of its testament page, its Compare pages against its chief partners, the page of every section of the book, every chapter page, and the word pages of its ten most distinctive words. Isaiah's dossier is more than three megabytes of text. Since version 0.10.66 the file begins with a list of every page in it, with the line number where each page starts and how many lines it runs, so that a reader with the file open in an editor can go straight to the page wanted.

Since version 0.10.68 the dossier command can also write every page into a database called results.db, with the option --results. Every number on every page then becomes a row that a question can reach. The script atlas_results.py asks the first questions: which New Testament book has the highest share of Septuagint words, how far every part of every book stands from the rest of its book in its function words, where the two Greek taggings disagree, which tables declined to measure and why, and what changed between two runs. Each answer is printed and also saved as a text file under the reports folder.

## Part III. The measures

### 20. Three kinds of number

Three kinds of number appear in the tables, and a reader who can tell them apart can read any page.

The first is a scaled count. A raw count is unfair between texts of different sizes: a long book will have more of everything. Dividing a count by the size of the text and multiplying up to a round figure puts texts of different sizes on one scale. That is what "per 1,000 words" means wherever it appears. The one danger is that a very small text, scaled up to a thousand words, can look remarkable by accident, which is why parts under a thousand words are marked "few" and their rows are to be read lightly.

The second is keyness, a measure of how surprising a count is. Suppose a word occurs twenty times in a book of ten thousand words and a hundred times in the rest of the testament, which has five hundred thousand words. The book uses it ten times as often as the rest does. Keyness turns that comparison into a single number that also takes into account how many occurrences there are, because ten times the rate on two occurrences means little and ten times the rate on two hundred means a great deal. The formula is one statisticians call log-likelihood, and the numbers to remember are these: a keyness above about four means the surplus is probably not chance, above about seven it is very probably not chance, and above about eleven it is almost certainly not chance. The tables use these lines as floors, below which a row is not printed.

The third is rarity, a measure of how uncommon a word is across the whole Bible. A word that is one in a thousand has a rarity of about seven, and a word that is one in a hundred thousand has a rarity of about eleven and a half. Rarity is what gives an echo its weight: a shared run of rare words is strong evidence of a connection, and a shared run of common words is weak evidence, so the echo tables add up the rarity of the words involved rather than merely counting them.

### 21. Words: spellings, roots and tags

The King James text spells one Hebrew word many ways. The verb behind "forgive", "leave", "let" and "suffer" in the New Testament is one Greek word, G863, which the translators rendered fourteen ways. The program counts by the Strong's number, which it calls the root, so all fourteen are one word. Where a word has no Strong's number, which happens with a few words the translators supplied, the program falls back to the English stem, which is the word with its endings removed.

The tagging that gives each word its number is not perfect, and the program applies a few rules to it when building the atlas. The most important is called the gloss rule: where a word has no tag but the dictionary says that the tagged word next to it is normally translated by both words together, the untagged word is absorbed into its neighbor. The build line on every page reports how many words that rule absorbed.

### 22. Formulas, echoes, quotation grade and refrains

A formula is a set phrase of two to five words that a text uses at least twice. A signature formula is one the text uses far more than the rest of the Bible does. An echo is a run of three or more words found in two different books and in no more than six verses of the whole Bible. The program finds echoes as formulas first and then grows each one to the longest run the two places actually share, so an echo may be a whole sentence. A quotation-grade echo is one of five or more words found in exactly two verses of the Bible. A refrain is a phrase that recurs in three or more chapters of one book, such as "the Holy One of Israel" in Isaiah; refrains are listed on their own so that they do not inflate the maps.

Between the Old and New Testaments, where a Hebrew number never matches a Greek one, echoes are found by the English wording instead and are marked "by English". This is weaker evidence, because the King James translators may have used the same English for two different originals. The Septuagint layer, described in section 28d, finds the same echoes in Greek, which is the stronger test.

### 23. Neighbors, pull and shadow

Two words are neighbors when they occur within five words of each other in the same verse. Pull is a measure of how much more often two words are neighbors than chance would predict, given how common each is. "Day" and "gloominess" in Joel have a high pull, because they occur together in a book where neither is common. The shadow of a word is its share of all the words in a text: "LORD" casts a large shadow over the Bible, and "vine" a small one, except in John 15.

### 24. Reach, depth, spread and home

Reach is how many chapters of a book a word touches. Depth is the highest keyness a word reaches in any one chapter, and the deepest chapter is that chapter. A word with high depth and low reach is local, a word that belongs to one chapter, such as "cubits" in Ezekiel 40. Spread is keyness scaled by the share of chapters a word reaches, so that a word found everywhere in a book scores higher than one found in a corner. A word's home is the book that uses it most, by rate, and a book's home words are the words it prefers most.

### 24a. Function words and Delta

Function words are the small words that carry no subject: in Greek, words such as "and", "but", "for", "not", "the", "in", "to", and the pronouns "I", "we" and "you"; in Hebrew, the prefixes that mean "and", "the", "in", "to" and "from", the particles that mark the object or mean "not", "that" and "which", and the pronoun endings. Every writer uses these at rates that are hard to change on purpose, which is why scholars have used them for a hundred years to ask whether two texts come from the same hand.

The program counts twenty-three such words in Greek and twenty-seven in Hebrew. For the Greek New Testament it counts them in the King James tagging; for the Hebrew Old Testament it reads a tagged Hebrew text called the TAHOT, which breaks every Hebrew word into its prefix, root and suffix, so that the prefixes can be counted.

Delta is a single number that says how far apart two texts are in their use of these words. It was devised by the scholar John Burrows. For each function word, the program finds the text's rate, turns it into a score that says how unusual that rate is compared with all the books of the testament, and then takes the average difference between the two texts' scores. Zero would mean identical habits. To make the number readable, every table prints two yardsticks beside it. Two different books of the testament are, on average, about 1.10 apart. The two halves of one book are about 0.67 apart. A pair of texts near the second figure are as alike as one book's halves; a pair near the first are as different as two unrelated books. A third yardstick allows for size: a short run of chapters cut from any book stands further from the rest of that book than a long one does, simply because small samples wobble, and the table prints the figure for a part of the size in question.

One caution, which the program learned the hard way on the prophetic stories of Kings, is that Delta measures the kind of text before it measures the hand. A list stands far from a story, and a law code stands far from a narrative, whoever wrote them. The largest Deltas in the whole Bible are 1 Chronicles' genealogies against its stories and Ezekiel's temple measurements against its oracles. Only a comparison of like with like measures the writer.

### 25. Parallels, the sharing table and the synopsis

Two verses are parallel when they share at least three content words in the same order, making up at least thirty percent of the shorter verse, or when they share a quotation-grade echo. Before parallels are counted, a book's own formulaic words, those found in more than a tenth of its verses, are set aside, so that "thus saith the Lord" does not pair every oracle of Ezekiel with some verse of Jeremiah. The sharing table marks every verse of a book by which of its two chief partners it has a parallel in, and the synopsis prints a chapter's verses beside their parallels.

### 26. Kin and shared vocabulary

Kin is the measure for dependence that runs through imagery rather than quotation. Two verses are kin when they share three or more rare words in any order. The pair's score is the summed rarity of the shared words, raised by up to half when the words come in the same order in both verses. Shared vocabulary asks less: not the same rare words in one pair of verses, but two chapters drawing on the same uncommon words anywhere in them, which catches a story told twice or a source with a vocabulary of its own.

### 27. Dates

The echo partner table labels every partner book "earlier", "contemporary" or "later" than the book in hand, and it does so under two sets of dates, because scholars disagree. The conventional dates take the books' own claims about their period, so that Isaiah is eighth century throughout. The critical dates are the ones most university scholarship uses, so that the second half of Isaiah is sixth century and comes after Jeremiah. Where the two sets place a partner on different sides, the table says "disputed". The program does not choose between the two; it lets the reader see that the direction of borrowing depends on the choice.

### 28. Sections and divisions

A section is a part of a book that a reader knows and the chapter numbers do not show: the five books of the Psalter, each closed by a doxology; Ezekiel's oracles against Judah, against the nations, and of restoration; the two halves of Isaiah. A division is one way of dividing a book into sections, and a book may have more than one. The Psalter is five books, and also a set of collections such as the psalms of Asaph, and also the block of psalms that prefer the name God to the name LORD. All of these are written in a plain table in the file atlas_sections.py, and the book page's section 7 and the Section pages read it.

A few sections cross from one book into another. The Succession Narrative, the story of David's court, runs from 2 Samuel 9 to 1 Kings 2. The Elijah stories run from 1 Kings 17 into 2 Kings 1, and the Elisha stories fill 2 Kings 2 to 8 and 13. The Ark Narrative is 1 Samuel 4 to 6 with 2 Samuel 6. These are written in a second table, and each has a page of its own that measures its parts as one text against the rest of the books it touches.

### 28a. The English bridge

Where two texts do not share a tagging, so that a Hebrew number can never match a Greek one, the program compares them by the King James English instead. This is the English bridge. It lets echoes be found between the testaments and between the Hebrew and Aramaic chapters of Daniel and Ezra. The pages mark every such result "by English", because the translators' choice of words can make a match that is not in the original, and the Greek matching of section 28d is the firmer test wherever it is available.

### 28b. The catalogue

The catalogue is the small database metadata.db. It holds the decided facts about the books that no counting could supply: which kind each book is, for the comparisons of section 1b; the named passages; the Septuagint's own list of books and the map from its verse numbering to the English one, which differ in Psalms and Jeremiah; and a table of equivalents, which are pairs of Strong's numbers that two different taggings use for the same Greek word. The catalogue is kept as text in a backup file so that it travels with the program in the shared repository.

### 28c. The Greek and Hebrew texts

Beside the King James, the program holds three original-language texts in the database lxx.db. The first is the Septuagint, the Greek translation of the Old Testament made in the centuries before Christ, in the edition of Alfred Rahlfs, with every word keyed by its Strong's number or, where it has none, by its dictionary form. The second is the Greek New Testament, from a project called the TAGNT at Tyndale House in Cambridge, which holds every word of every major edition, parsed and glossed; the program uses the words of the Textus Receptus, which is the Greek the King James translators had. The third is the Hebrew Old Testament, from the same project's TAHOT, tagged element by element so that the prefixes and suffixes of each Hebrew word can be counted; this is what the Hebrew function-word tables read.

### 28d. The Septuagint layer

The New Testament's writers read the Old Testament mostly in Greek, in the Septuagint, and quoted it in Greek. Because the program holds the Septuagint and the Greek New Testament side by side, both keyed by the same numbers, it can find a quotation as a run of Greek words shared between an Old Testament verse and a New Testament verse, rather than guessing from the English.

Section 4e, Septuagint echoes, lists those runs. For a New Testament book it shows which Septuagint verses the book's Greek repeats, and for an Old Testament book it shows which New Testament verses repeat the book's Greek. Each run is printed in Greek with a word-for-word English gloss, its length, its grade, and the verses on both sides. Where the two texts differ by a single word inside an otherwise identical run, the run is bridged across the gap and the differing words are shown in brackets, so that a quotation which changes one word, as Hebrews 10:5 changes "ears" to "body" in quoting Psalm 40, shows as one run with the change visible. Hebrews chapter 1 comes out as the chain of psalm quotations it is, with Psalm 45 in twenty words and Psalm 110 in fourteen.

Section 4f lists the echoes found through the English that no Greek run confirms. These are quotations not made in the Septuagint's words, either because the writer translated from the Hebrew himself, as Matthew sometimes did, or because the English finder paired two verses that only sound alike in the King James.

Sections 1e and 1f, on New Testament books, measure the book's Greek vocabulary against the Septuagint. Section 1f's footer ranks every New Testament book by the share of its words that belong to the Septuagint more than to the New Testament. Revelation and Hebrews stand highest, and the letters of John lowest, which matches what scholars have long said about which writers sound like the Greek Bible.

### 29. What the program cannot see

The program counts shared wording, shared roots and shared rare words. It finds verbatim repetition, formulas, quotation, allusion carried by rare words, and the distinctive vocabulary of a book or a part. It does not find a story retold in ordinary words: the three stories in Genesis of a wife passed off as a sister share only "sister", "wife" and "took", which every chapter of Genesis has. It does not find an idea expressed in different words. It cannot tell which of two books borrowed from the other; it can only lay the shared material out with the dates beside it. And it depends on its tagging, which was made by people and has mistakes, some of which the program now finds and marks.

## Part IV. What the books showed

The full manual carries a long chapter on each book that was read through the program, written as the reviews were done. A few of the findings give the flavor.

The Psalter's five books, which everyone agrees on, come out in the tables as a reader would expect, and the refrains "amen and amen" at the end of Books I, II and III fall exactly on the seams. The block of psalms that prefer the name God to the name LORD stands out on the shadow map of H3068 as a gap.

Isaiah divides at chapter 40 in its vocabulary and in its partners: the first half keeps company with 2 Kings, with which it shares the whole Hezekiah story, and with Micah, Hosea and Amos; the second half keeps company with the Psalms and with Job, and is the part the New Testament quotes. Yet the two halves share their function-word habits to the degree that one book's halves usually do, once the pronouns are set aside, so the small-word test does not decide the old question of whether one prophet wrote the book.

Jeremiah's three sources, as scholars have divided them, come out as three rows of a table with different partners and different leading words. Ezekiel against Revelation shows a book that borrows phrases rather than verses, with "four corners of the earth", "the sides of the pit" and the river of life. Hebrews is a chain of Old Testament quotations, and the program lists them in Greek, in order, with the one in chapter 13 that the first version missed because its words were common ones.

The Succession Narrative, read as one text across 2 Samuel and 1 Kings, is written in the grammatical habits of the books that hold it, whatever its origin; the stories of Elijah and Elisha, which at first seemed to stand apart from the rest of Kings, turned out to stand apart only as any story stands apart from the lists and formulas around it, which the program's own control test showed, and which the full manual keeps on the page as a lesson in how a result can change under test.

## Part V. The rules and how they were set

### 39. Rules and settings

Nearly every number on a page depends on a rule: how wide the window is within which two words count as neighbors, how many words a formula needs, how many verses an echo may occur in, what floor a keyness must pass. Each rule is a named setting in one file, with a comment beside it saying what it decides, what reading set it, and what to expect if it is moved. The full manual lists every rule in section 42.

### 41. The method

The program was built in a loop. A page was read against the text by a reviewer who asked whether each number said something true about the book. An odd number was traced to its rule. The rule was changed in one place and the page read again. The change was kept if it made the page truer. Two people did this with different jobs: one read the pages against the books and against what scholars have said, and the other traced each wrong number to its rule and changed it. Several of the reviews became the chapters of Part IV.

Since version 0.10.63 a test script is run before every change is saved. It builds every kind of page on a few books and fails on any error, builds the same pages twice under different conditions to make sure the output is the same, checks that the particular mistakes earlier reviews found have not come back, and checks that the program, the manual and the improvements list all name the same version.

### 43. Changing the tables

The sections of a book, the dates of the books, and the words the function-word layer counts are all plain tables in Python files, written to be edited by a reader rather than a programmer. Adding a new division of a book is a few lines in atlas_sections.py, and the pages pick it up at once. The full manual's section 43 shows how.

## Where to go from here

Open the program, choose Book and Joel, and press Go. Read section 1, then click a row and read the verses. Then type 'day' [Joel] in the Ask box and look at the neighbors. Then open the Compare page for Matthew against Mark and look at the order line in the footer. By then the pages will have begun to read as the manual says they do, and the full manual will be the place for the questions that come next.
