"""
Word Atlas - the ask line
=========================

Turns one line written in the Word Atlas notation into something the
program can do.  The same marks that the reports use to write a finding
down can be typed to ask for it:

    'day'                      word page, whole Bible
    'day' [Joel]               word page with its neighbors in Joel
    'day' + 'night' [Ezekiel]  the verses where the two words meet
    "the day of the LORD"      the verses holding a formula, whole Bible
    "the day of the LORD" [Joel]      ... within Joel
    [Joel]                     the book page
    [Joel 2]                   the chapter page
    Ezekiel 47 -> ?            the kin page for a chapter
    Ezekiel 47:1-12 -> ?       the kin page for a verse range
    Joel 2:1                   one verse

The result is a small dict naming the action and its arguments; the
window and the command line carry it out.  Nothing here touches the
database, so the parser is easy to test on its own.

Author: Andrew Hopkins (with Claude)
"""

import re

# A scale in square brackets: [Joel], [Joel 2], [Bible], [Bible - Joel]
SCALE = re.compile(r"\[\s*([^\]]+?)\s*\]")
# A single-quoted word: 'day', 'LORD'
WORD = re.compile(r"'([^']+)'")
# A double-quoted formula: "the day of the LORD"
PHRASE = re.compile(r'"([^"]+)"')
# A reference or passage: Joel 2, Joel 2:1, Ezekiel 47:1-12, 1 Samuel 3
PASSAGE = re.compile(r"^\s*((?:[1-3]\s+)?[A-Za-z][A-Za-z ]*?)\s+(\d+)(?::(\d+)(?:-(\d+))?)?\s*$")


class AskError(ValueError):
    """The line could not be understood; the message says what was expected."""


def split_scale(text):
    """
    Pull the [scale] out of a line.  Returns (rest of line, book, chapter,
    minus_book).  [Bible] and no scale both give book=None.
    [Bible - Joel] gives minus_book="Joel".
    """
    m = SCALE.search(text)
    if not m:
        return text.strip(), None, None, None
    inside = m.group(1)
    rest = (text[:m.start()] + text[m.end():]).strip()
    minus = None
    if "-" in inside:
        left, right = [part.strip() for part in inside.split("-", 1)]
        if left.lower() == "bible":
            return rest, None, None, right
        inside = left
    if inside.lower() == "bible":
        return rest, None, None, minus
    # A testament as a scale: [Old], [New], [OT], [NT], [New Testament]
    key = inside.lower().replace("testament", "").strip()
    if key in ("old", "new", "ot", "nt"):
        return rest, "Old Testament" if key in ("old", "ot") else "New Testament", None, minus
    pm = re.match(r"^((?:[1-3]\s+)?[A-Za-z][A-Za-z ]*?)(?:\s+(\d+))?$", inside)
    if not pm:
        raise AskError(f"Could not read the scale [{inside}]; expected [Book], [Book chapter] or [Bible].")
    return rest, pm.group(1).strip(), int(pm.group(2)) if pm.group(2) else None, minus


def parse(line):
    """
    Read one line of notation and return what to do.

    Returns a dict with an "action" key and its arguments:
        {"action": "word", "word": ..., "book": ...}
        {"action": "pair", "word": ..., "pair": ..., "book": ..., "chapter": ...}
        {"action": "phrase", "phrase": ..., "book": ..., "chapter": ...}
        {"action": "book", "book": ...}
        {"action": "chapter", "book": ..., "chapter": ...}
        {"action": "kin", "book": ..., "chapter": "47" or "47:1-12"}
        {"action": "verse", "reference": "Joel 2:1"}
    Raises AskError with a plain message when the line makes no sense.
    """
    text = line.strip()
    if not text:
        raise AskError("Type something to ask, for example 'day' [Joel].")

    # Kin: a passage followed by -> ?
    if "->" in text:
        left, right = [part.strip() for part in text.split("->", 1)]
        if right not in ("?", ""):
            raise AskError("After -> put a question mark: Ezekiel 47 -> ?")
        pm = PASSAGE.match(left)
        if not pm:
            raise AskError("Before -> put a chapter or verse range: Ezekiel 47 -> ? or Ezekiel 47:1-12 -> ?")
        book, chapter, v1, v2 = pm.group(1).strip(), pm.group(2), pm.group(3), pm.group(4)
        span = chapter + (f":{v1}-{v2 or v1}" if v1 else "")
        return {"action": "kin", "book": book, "chapter": span}

    rest, book, chapter, minus = split_scale(text)

    # Two words meeting: 'day' + 'night'
    words = WORD.findall(rest)
    if "+" in rest and len(words) == 2:
        return {"action": "pair", "word": words[0], "pair": words[1], "book": book,
                "chapter": chapter}
    if "+" in rest:
        raise AskError("A pair needs two quoted words: 'day' + 'night' [Ezekiel].")

    # A formula in double quotes
    phrases = PHRASE.findall(rest)
    if phrases:
        return {"action": "phrase", "phrase": phrases[0].strip(), "book": book, "chapter": chapter}

    # A single word
    if len(words) == 1:
        return {"action": "word", "word": words[0], "book": book}
    if len(words) > 1:
        raise AskError("One word at a time: 'day' [Joel], or a pair with +.")

    # Nothing but a scale: the testament, book or chapter page
    if not rest and book in ("Old Testament", "New Testament"):
        return {"action": "testament", "testament": book.split()[0]}
    if not rest and book:
        if chapter:
            return {"action": "chapter", "book": book, "chapter": chapter}
        return {"action": "book", "book": book}
    if not rest and minus:
        raise AskError("[Bible - Book] only makes sense after a word or formula.")

    # A bare reference: Joel 2:1, or Joel 2 (the chapter page)
    pm = PASSAGE.match(rest)
    if pm:
        book, chapter, v1, v2 = pm.group(1).strip(), pm.group(2), pm.group(3), pm.group(4)
        if v1 and not v2:
            return {"action": "verse", "reference": f"{book} {chapter}:{v1}"}
        if v1:
            return {"action": "kin", "book": book, "chapter": f"{chapter}:{v1}-{v2}"}
        return {"action": "chapter", "book": book, "chapter": int(chapter)}

    raise AskError("Could not read that.  Try 'day' [Joel], \"the day of the LORD\", "
                   "'day' + 'night' [Ezekiel], [Joel 2], or Ezekiel 47 -> ?")


def describe(line):
    """A one-line plain-English reading of an ask line, for the status bar."""
    a = parse(line)
    kind = a["action"]
    if kind == "testament":
        return f"the {a['testament']} Testament page: where each word is at home"
    if kind == "word":
        return f"the word page for '{a['word']}'" + (f" with its neighbors in {a['book']}" if a["book"] else "")
    if kind == "pair":
        return f"verses where '{a['word']}' and '{a['pair']}' meet" + (f" in {a['book']}" if a["book"] else "")
    if kind == "phrase":
        return f'verses holding "{a["phrase"]}"' + (f" in {a['book']}" if a["book"] else "")
    if kind == "book":
        return f"the book page for {a['book']}"
    if kind == "chapter":
        return f"the chapter page for {a['book']} {a['chapter']}"
    if kind == "kin":
        return f"the kin page for {a['book']} {a['chapter']}"
    return f"the verse {a['reference']}"


if __name__ == "__main__":
    # A few lines to try, so the parser can be checked without the window
    for sample in ["'day'", "'day' [Joel]", "'day' + 'night' [Ezekiel]",
                   '"the day of the LORD"', '"the day of the LORD" [Joel]',
                   "[Joel]", "[Joel 2]", "Ezekiel 47 -> ?", "Ezekiel 47:1-12 -> ?",
                   "Joel 2:1", "1 Samuel 3", "'seal' [Bible - Revelation]"]:
        print(f"{sample:<34} {parse(sample)}")
