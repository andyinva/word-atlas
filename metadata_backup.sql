-- Word Atlas metadata.db backup (plain SQL; restore with atlas_backup.py)
-- written: 2026-09-27 15:34
BEGIN TRANSACTION;
CREATE TABLE books (
    book_num       INTEGER PRIMARY KEY,     -- 1 = Genesis ... 66 = Revelation
    name           TEXT NOT NULL UNIQUE,
    testament      TEXT NOT NULL CHECK (testament IN ('OT', 'NT')),
    genre          TEXT NOT NULL,
    baseline_group TEXT NOT NULL,
    source_note    TEXT NOT NULL DEFAULT ''
);
INSERT INTO "books" VALUES(1,'Genesis','OT','Law','Law','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(2,'Exodus','OT','Law','Law','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(3,'Leviticus','OT','Law','Law','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(4,'Numbers','OT','Law','Law','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(5,'Deuteronomy','OT','Law','Law','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(6,'Joshua','OT','History','History','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(7,'Judges','OT','History','History','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(8,'Ruth','OT','History','History','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(9,'1 Samuel','OT','History','History','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(10,'2 Samuel','OT','History','History','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(11,'1 Kings','OT','History','History','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(12,'2 Kings','OT','History','History','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(13,'1 Chronicles','OT','History','History','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(14,'2 Chronicles','OT','History','History','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(15,'Ezra','OT','History','History','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(16,'Nehemiah','OT','History','History','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(17,'Esther','OT','History','History','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(18,'Job','OT','Poetry','Poetry','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(19,'Psalms','OT','Poetry','Poetry','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(20,'Proverbs','OT','Poetry','Poetry','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(21,'Ecclesiastes','OT','Poetry','Poetry','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(22,'Song of Solomon','OT','Poetry','Poetry','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(23,'Isaiah','OT','Major Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(24,'Jeremiah','OT','Major Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(25,'Lamentations','OT','Major Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(26,'Ezekiel','OT','Major Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(27,'Daniel','OT','Major Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(28,'Hosea','OT','Minor Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(29,'Joel','OT','Minor Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(30,'Amos','OT','Minor Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(31,'Obadiah','OT','Minor Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(32,'Jonah','OT','Minor Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(33,'Micah','OT','Minor Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(34,'Nahum','OT','Minor Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(35,'Habakkuk','OT','Minor Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(36,'Zephaniah','OT','Minor Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(37,'Haggai','OT','Minor Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(38,'Zechariah','OT','Minor Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(39,'Malachi','OT','Minor Prophets','Prophecy','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(40,'Matthew','NT','Gospels','NT Narrative','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(41,'Mark','NT','Gospels','NT Narrative','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(42,'Luke','NT','Gospels','NT Narrative','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(43,'John','NT','Gospels','NT Narrative','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(44,'Acts','NT','NT History','NT Narrative','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(45,'Romans','NT','Pauline Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(46,'1 Corinthians','NT','Pauline Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(47,'2 Corinthians','NT','Pauline Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(48,'Galatians','NT','Pauline Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(49,'Ephesians','NT','Pauline Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(50,'Philippians','NT','Pauline Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(51,'Colossians','NT','Pauline Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(52,'1 Thessalonians','NT','Pauline Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(53,'2 Thessalonians','NT','Pauline Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(54,'1 Timothy','NT','Pauline Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(55,'2 Timothy','NT','Pauline Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(56,'Titus','NT','Pauline Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(57,'Philemon','NT','Pauline Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(58,'Hebrews','NT','General Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(59,'James','NT','General Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(60,'1 Peter','NT','General Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(61,'2 Peter','NT','General Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(62,'1 John','NT','General Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(63,'2 John','NT','General Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(64,'3 John','NT','General Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(65,'Jude','NT','General Epistles','Epistles','seed: standard canon grouping (editable)');
INSERT INTO "books" VALUES(66,'Revelation','NT','Apocalyptic','Prophecy','seed: standard canon grouping (editable)');
CREATE TABLE corpora (
    corpus      TEXT PRIMARY KEY,
    language    TEXT NOT NULL CHECK (language IN ('Hebrew', 'Greek')),
    description TEXT NOT NULL DEFAULT '',
    source_note TEXT NOT NULL DEFAULT ''
);
INSERT INTO "corpora" VALUES('hebrew-ot','Hebrew','KJV Old Testament keyed by Hebrew Strong''s numbers (atlas.db)','seed');
INSERT INTO "corpora" VALUES('greek-nt','Greek','KJV New Testament keyed by Greek Strong''s numbers (atlas.db)','seed');
INSERT INTO "corpora" VALUES('greek-lxx','Greek','Rahlfs 1935 Septuagint keyed by Strong''s numbers or lemmas (read by septuagint_bridge.py; not yet in atlas.db)','seed');
CREATE TABLE lxx_books (
    code        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    book_num    INTEGER REFERENCES books(book_num),
    variant     TEXT NOT NULL DEFAULT '',
    preferred   INTEGER NOT NULL DEFAULT 0 CHECK (preferred IN (0, 1)),
    canon_order INTEGER NOT NULL DEFAULT 0,
    chapters    INTEGER NOT NULL DEFAULT 0,
    verses      INTEGER NOT NULL DEFAULT 0,
    source_note TEXT NOT NULL DEFAULT ''
);
INSERT INTO "lxx_books" VALUES('Gen','Genesis',1,'',1,1,50,1531,'scanned');
INSERT INTO "lxx_books" VALUES('Exod','Exodus',2,'',1,2,40,1165,'scanned');
INSERT INTO "lxx_books" VALUES('Lev','Leviticus',3,'',1,3,27,859,'scanned');
INSERT INTO "lxx_books" VALUES('Num','Numbers',4,'',1,4,36,1287,'scanned');
INSERT INTO "lxx_books" VALUES('Deut','Deuteronomy',5,'',1,5,34,959,'scanned');
INSERT INTO "lxx_books" VALUES('JoshB','Joshua',6,'B text',1,6,24,659,'scanned');
INSERT INTO "lxx_books" VALUES('JoshA','Joshua',6,'A text',0,7,3,96,'scanned');
INSERT INTO "lxx_books" VALUES('JudgB','Judges',7,'B text',1,8,21,617,'scanned');
INSERT INTO "lxx_books" VALUES('JudgA','Judges',7,'A text',0,9,21,618,'scanned');
INSERT INTO "lxx_books" VALUES('Ruth','Ruth',8,'',1,10,4,85,'scanned');
INSERT INTO "lxx_books" VALUES('1Sam','1 Samuel',9,'',1,11,31,773,'scanned');
INSERT INTO "lxx_books" VALUES('2Sam','2 Samuel',10,'',1,12,24,696,'scanned');
INSERT INTO "lxx_books" VALUES('1Kgs','1 Kings',11,'',1,13,22,825,'scanned');
INSERT INTO "lxx_books" VALUES('2Kgs','2 Kings',12,'',1,14,25,723,'scanned');
INSERT INTO "lxx_books" VALUES('1Chr','1 Chronicles',13,'',1,15,29,930,'scanned');
INSERT INTO "lxx_books" VALUES('2Chr','2 Chronicles',14,'',1,16,36,833,'scanned');
INSERT INTO "lxx_books" VALUES('1Esdr','1 Esdras',NULL,'',0,17,9,434,'scanned');
INSERT INTO "lxx_books" VALUES('2Esdr','2 Esdras (Ezra-Nehemiah)',15,'Ezra-Nehemiah in one book (Nehemiah = chapters 11-23)',1,18,23,672,'scanned');
INSERT INTO "lxx_books" VALUES('Esth','Esther',17,'',1,19,10,252,'scanned');
INSERT INTO "lxx_books" VALUES('Jdt','Judith',NULL,'',0,20,16,340,'scanned');
INSERT INTO "lxx_books" VALUES('TobBA','Tobit (BA text)',NULL,'',0,21,14,248,'scanned');
INSERT INTO "lxx_books" VALUES('TobS','Tobit (Sinaiticus text)',NULL,'',0,22,14,232,'scanned');
INSERT INTO "lxx_books" VALUES('1Macc','1 Maccabees',NULL,'',0,23,16,924,'scanned');
INSERT INTO "lxx_books" VALUES('2Macc','2 Maccabees',NULL,'',0,24,15,555,'scanned');
INSERT INTO "lxx_books" VALUES('3Macc','3 Maccabees',NULL,'',0,25,7,228,'scanned');
INSERT INTO "lxx_books" VALUES('4Macc','4 Maccabees',NULL,'',0,26,18,479,'scanned');
INSERT INTO "lxx_books" VALUES('Ps','Psalms',19,'',1,27,151,2534,'scanned');
INSERT INTO "lxx_books" VALUES('Odes','Odes',NULL,'',0,28,14,289,'scanned');
INSERT INTO "lxx_books" VALUES('Prov','Proverbs',20,'',1,29,31,939,'scanned');
INSERT INTO "lxx_books" VALUES('Eccl','Ecclesiastes',21,'',1,30,12,222,'scanned');
INSERT INTO "lxx_books" VALUES('Song','Song of Solomon',22,'',1,31,8,117,'scanned');
INSERT INTO "lxx_books" VALUES('Job','Job',18,'',1,32,42,1083,'scanned');
INSERT INTO "lxx_books" VALUES('Wis','Wisdom of Solomon',NULL,'',0,33,19,435,'scanned');
INSERT INTO "lxx_books" VALUES('Sir','Sirach',NULL,'',0,34,51,1366,'scanned');
INSERT INTO "lxx_books" VALUES('PsSol','Psalms of Solomon',NULL,'',0,35,18,310,'scanned');
INSERT INTO "lxx_books" VALUES('Hos','Hosea',28,'',1,36,14,197,'scanned');
INSERT INTO "lxx_books" VALUES('Mic','Micah',33,'',1,37,7,105,'scanned');
INSERT INTO "lxx_books" VALUES('Amos','Amos',30,'',1,38,9,146,'scanned');
INSERT INTO "lxx_books" VALUES('Joel','Joel',29,'',1,39,4,73,'scanned');
INSERT INTO "lxx_books" VALUES('Jonah','Jonah',32,'',1,40,4,48,'scanned');
INSERT INTO "lxx_books" VALUES('Obad','Obadiah',31,'',1,41,1,21,'scanned');
INSERT INTO "lxx_books" VALUES('Nah','Nahum',34,'',1,42,3,47,'scanned');
INSERT INTO "lxx_books" VALUES('Hab','Habakkuk',35,'',1,43,3,56,'scanned');
INSERT INTO "lxx_books" VALUES('Zeph','Zephaniah',36,'',1,44,3,53,'scanned');
INSERT INTO "lxx_books" VALUES('Hag','Haggai',37,'',1,45,2,38,'scanned');
INSERT INTO "lxx_books" VALUES('Zech','Zechariah',38,'',1,46,14,211,'scanned');
INSERT INTO "lxx_books" VALUES('Mal','Malachi',39,'',1,47,3,55,'scanned');
INSERT INTO "lxx_books" VALUES('Isa','Isaiah',23,'',1,48,66,1289,'scanned');
INSERT INTO "lxx_books" VALUES('Jer','Jeremiah',24,'',1,49,52,1298,'scanned');
INSERT INTO "lxx_books" VALUES('Bar','Baruch',NULL,'',0,50,5,141,'scanned');
INSERT INTO "lxx_books" VALUES('EpJer','Letter of Jeremiah',NULL,'',0,51,1,73,'scanned');
INSERT INTO "lxx_books" VALUES('Lam','Lamentations',25,'',1,52,6,151,'scanned');
INSERT INTO "lxx_books" VALUES('Ezek','Ezekiel',26,'',1,53,48,1267,'scanned');
INSERT INTO "lxx_books" VALUES('BelOG','Bel and the Dragon (Old Greek)',NULL,'',0,54,1,37,'scanned');
INSERT INTO "lxx_books" VALUES('BelTh','Bel and the Dragon (Theodotion)',NULL,'',0,55,1,42,'scanned');
INSERT INTO "lxx_books" VALUES('DanOG','Daniel',27,'Old Greek',0,56,12,413,'scanned');
INSERT INTO "lxx_books" VALUES('DanTh','Daniel',27,'Theodotion',1,57,12,424,'scanned');
INSERT INTO "lxx_books" VALUES('SusOG','Susanna (Old Greek)',NULL,'',0,58,1,37,'scanned');
INSERT INTO "lxx_books" VALUES('SusTh','Susanna (Theodotion)',NULL,'',0,59,1,64,'scanned');
CREATE TABLE lxx_chapter_map (
    book_num    INTEGER NOT NULL REFERENCES books(book_num),
    eng_chapter INTEGER NOT NULL,
    lxx_chapter INTEGER NOT NULL,
    source_note TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (book_num, eng_chapter)
);
INSERT INTO "lxx_chapter_map" VALUES(24,50,27,'Babylon oracle; confirmed in septuagint_bridge.py');
INSERT INTO "lxx_chapter_map" VALUES(24,51,28,'Babylon oracle; confirmed in septuagint_bridge.py');
CREATE TABLE meta_info (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT INTO "meta_info" VALUES('schema_version','3');
CREATE TABLE passage_ranges (
    passage_id    INTEGER NOT NULL REFERENCES passages(passage_id) ON DELETE CASCADE,
    book_num      INTEGER NOT NULL REFERENCES books(book_num),
    chapter_start INTEGER NOT NULL,
    verse_start   INTEGER NOT NULL,
    chapter_end   INTEGER NOT NULL,
    verse_end     INTEGER NOT NULL,
    UNIQUE (passage_id, book_num, chapter_start, verse_start)
);
INSERT INTO "passage_ranges" VALUES(1,26,16,1,16,63);
INSERT INTO "passage_ranges" VALUES(1,26,23,1,23,49);
INSERT INTO "passage_ranges" VALUES(1,66,17,1,19,21);
INSERT INTO "passage_ranges" VALUES(2,23,1,1,39,999);
INSERT INTO "passage_ranges" VALUES(3,23,40,1,66,999);
INSERT INTO "passage_ranges" VALUES(4,26,16,1,16,999);
INSERT INTO "passage_ranges" VALUES(4,26,23,1,23,999);
INSERT INTO "passage_ranges" VALUES(5,66,17,1,19,999);
INSERT INTO "passage_ranges" VALUES(6,23,23,1,23,999);
INSERT INTO "passage_ranges" VALUES(6,26,26,1,28,19);
INSERT INTO "passage_ranges" VALUES(7,23,13,1,14,23);
INSERT INTO "passage_ranges" VALUES(7,23,47,1,47,999);
INSERT INTO "passage_ranges" VALUES(7,24,50,1,51,999);
INSERT INTO "passage_ranges" VALUES(8,34,3,1,3,999);
INSERT INTO "passage_ranges" VALUES(9,23,13,1,14,23);
INSERT INTO "passage_ranges" VALUES(9,23,23,1,23,999);
INSERT INTO "passage_ranges" VALUES(9,23,47,1,47,999);
INSERT INTO "passage_ranges" VALUES(9,24,50,1,51,999);
INSERT INTO "passage_ranges" VALUES(9,26,26,1,28,19);
INSERT INTO "passage_ranges" VALUES(9,34,3,1,3,999);
INSERT INTO "passage_ranges" VALUES(10,23,1,21,1,31);
INSERT INTO "passage_ranges" VALUES(10,24,2,1,3,999);
INSERT INTO "passage_ranges" VALUES(10,26,16,1,16,999);
INSERT INTO "passage_ranges" VALUES(10,26,23,1,23,999);
INSERT INTO "passage_ranges" VALUES(10,28,1,1,3,999);
CREATE TABLE passages (
    passage_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    source_note TEXT NOT NULL DEFAULT ''
);
INSERT INTO "passages" VALUES(1,'Harlot city','Harlot-city passages in Ezekiel and Revelation','seed: example passage');
INSERT INTO "passages" VALUES(2,'Isaiah 1-39','','entered with atlas_passages.py');
INSERT INTO "passages" VALUES(3,'Isaiah 40-66','','entered with atlas_passages.py');
INSERT INTO "passages" VALUES(4,'Ezekiel harlot','Jerusalem and Samaria as harlots','entered with atlas_passages.py');
INSERT INTO "passages" VALUES(5,'Revelation harlot','Babylon the harlot','entered with atlas_passages.py');
INSERT INTO "passages" VALUES(6,'Tyre oracles','Tyre','entered with atlas_passages.py');
INSERT INTO "passages" VALUES(7,'Babylon oracles','Babylon','entered with atlas_passages.py');
INSERT INTO "passages" VALUES(8,'Nineveh oracle','Nineveh','entered with atlas_passages.py');
INSERT INTO "passages" VALUES(9,'Gentile cities','Oracles against Tyre, Babylon and Nineveh','entered with atlas_passages.py');
INSERT INTO "passages" VALUES(10,'Israel harlot','Israel, Judah and Jerusalem as harlots','entered with atlas_passages.py');
CREATE TABLE verse_tags (
    book_num    INTEGER NOT NULL REFERENCES books(book_num),
    chapter     INTEGER NOT NULL,
    verse       INTEGER NOT NULL,
    tag_type    TEXT NOT NULL,
    tag_value   TEXT NOT NULL,
    source_note TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (book_num, chapter, verse, tag_type, tag_value)
);
CREATE INDEX idx_verse_tags_type_value
    ON verse_tags (tag_type, tag_value);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('passages',10);
COMMIT;
