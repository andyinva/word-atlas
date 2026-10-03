#!/usr/bin/env python3
"""
atlas_heat.py

Hot spots and cool spots in a book: where the wording runs dense, varied,
rare, hammering or full of action, and where it runs thin.

THE IDEA
    Slide a window of verses (default 10) through a book one verse at a
    time. Score every window on five measures. Compare each score with
    ordinary windows from the whole Bible in the same language (z-score:
    0 = ordinary, +2 = far above, -2 = far below). A run of windows at +2
    or more is a hot spot for that measure; -2 or less a cool spot.

THE FIVE MEASURES
    (density)   share of the KJV's words that are content words, not
                "and, the, of, unto". Graphic description packs content
                words tightly; genealogies and law run thinner.
    (variety)   how many different words are used, counted in steady
                runs of 50 content words (moving-average type-token
                ratio), so long and short windows compare fairly. A
                description keeps reaching for new words; a ritual
                repeats the same ones.
    (rare)      share of content words used 10 times or fewer in the
                whole Bible (--rare changes the limit). Vivid poetry
                reaches for unusual vocabulary.
    (hammer)    share of the window's content words taken by its single
                most repeated word: the "vertical" or depth idea. Emotional
                rhetoric hammers a word. The divine-speech words of the
                voice formulas ("saith the Lord GOD of hosts") are not
                counted, so formulas do not drown the measure, and
                neither are the most common words of the language (the
                top 100 by use, --hammer-skip): words like 'have', 'God'
                and 'great' are repeated everywhere and say little. The
                report and the chart name the hammered word.
                --hammer-window N measures hammer over N verses around
                each window instead (30 is about a chapter), to catch
                repetition spread more widely, such as Revelation's
                sevens.
    (action)    share of content words that are verbs (the KJV tagging
                marks every Hebrew and Greek verb with a tense code).
                High = driving narrative or command; low = static
                description or lists.

    (feeling)   share of content words that are feeling words: the
                reviewed list in metadata.db (atlas_feelings.py). Only
                present once that list has been imported. The report names
                the categories behind each feeling hot spot.
                --families adds one strip per family as well: emotion,
                senses, body, violence, sacred, wealth, harlotry.

    The variety, rare, hammer, action and feeling measures count the Hebrew and
    Greek words behind the KJV (Strong's numbers); a Hebrew word rendered
    by several English words counts once. Density counts English words.

SCALES (--scale)
    z           (default) distance from the ordinary average, in spreads.
                Fits density, variety, rare, hammer and action, which form
                a bell curve.
    percentile  the share of ordinary windows that score lower: 50% is
                ordinary, 99.5% hotter than all but 1 window in 200. Needs
                no bell curve, so it suits the count strips (feeling and
                its families), where most ordinary windows score zero and z
                runs to +18. Best for the chart's colors.
    g2          log-likelihood (Dunning's G squared, the atlas's keyness
                measure) for the strips that count words: how surprising
                the window's count is, given the ordinary rate. 10.83 is
                strong evidence. Best for deciding what is a real hot spot.
                Variety and hammer stay on z.
    All three set the same z-like number behind the scenes, so the
    colors, --threshold and the spot lists read the same way on each:
    +2 is about the top 2.3%, and on g2 the default threshold 3.29 is
    G2 10.83.

ORDINARY
    Ordinary is the whole Bible in the same language: Old Testament
    windows for an Old Testament book, New Testament windows for a New
    Testament book. --norm book compares a book with itself instead, which
    shows its own peaks even when the whole book runs hot.

OUTPUT
    A text report (build line first): the hot and cool spots for each
    measure, then a chapter table. --svg writes a strip chart: one strip
    per measure along the book, red for hot, gray for ordinary, blue for
    cool, chapter marks underneath. Point at any cell for its verses and
    score.

Usage:
    python atlas_heat.py Ezekiel
    python atlas_heat.py Revelation --svg reports/heat_revelation.svg
    python atlas_heat.py Ezekiel --window 15 --threshold 1.5
    python atlas_heat.py Ezekiel --norm book
    python atlas_heat.py Ezekiel --families --svg reports/heat_ezekiel_feelings.svg
    python atlas_heat.py Revelation --hammer-window 30
    python atlas_heat.py Revelation --norm book --families --scale percentile
    python atlas_heat.py Revelation --families --scale g2
    python atlas_heat.py Ezekiel --out reports/heat_ezekiel.txt --svg reports/heat_ezekiel.svg
"""

import argparse
import sqlite3
import bisect
import math
import statistics
from statistics import NormalDist
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

# Folder this script lives in, so default paths work on Ubuntu and Windows.
SCRIPT_DIR = Path(__file__).resolve().parent

# The five measures, in report and chart order.
MEASURES = ["density", "variety", "rare", "hammer", "action"]

# Words of the divine-speech formulas, left out of (hammer) only:
# said/saith, LORD, Lord (Adonai), GOD (as in "Lord GOD"), hosts.
VOICE_ROOTS = {"H559", "H3068", "H136", "H3069", "H6635", "G3004", "G2036"}

# The families of feeling words (see atlas_feelings.py), for --families.
FAMILY_NAMES = ["emotion", "senses", "body", "violence", "sacred", "wealth", "harlotry"]

# Headwords for words the KJV renders with the same English as another
# word: zoon (the four living creatures) is "beast" in the KJV, like
# therion (the beast from the sea), and the two must not look alike.
GLOSS_OVERRIDES = {
    "G2226": "living creature",
}

# A token joins an earlier unit of the same root up to this many positions
# back in the same verse ("eat it up" = one word, katesthio).
MERGE_GAP = 2

# The run length for (variety): type-token ratio over 50 content words.
VARIETY_SPAN = 50


# ===========================================================================
# One verse, reduced to what the measures need
# ===========================================================================
@dataclass
class Verse:
    """The counts one verse contributes to a window."""
    verse_id: int
    book: str
    chapter: int
    verse: int
    english_words: int = 0           # every KJV token
    english_content: int = 0         # KJV tokens that are not stop words
    units: list = field(default_factory=list)   # content Strong's roots, in order
    english: list = field(default_factory=list) # the KJV words behind each unit, same order
    verbs: int = 0                   # content units that are verbs

    @property
    def ref(self) -> str:
        return f"{self.chapter}:{self.verse}"


class VerseLoader:
    """Reads atlas.db once and builds a Verse for every verse of the Bible."""

    def __init__(self, atlas_path: Path):
        if not atlas_path.exists():
            sys.exit(f"atlas.db not found at {atlas_path}. Run build_atlas.py first.")
        conn = sqlite3.connect(atlas_path)
        try:
            self.settings = dict(conn.execute("SELECT key, value FROM settings"))
            # Book order and testament.
            self.books = [b for (b,) in conn.execute("SELECT book FROM books ORDER BY order_index")]
            self.testament = dict(conn.execute("SELECT book, testament FROM books"))
            # How often each root occurs in the whole Bible, for (rare).
            self.weight = dict(conn.execute("SELECT root, weight FROM words"))
            self.glosses = {r: f for r, f in conn.execute("SELECT root, form FROM words") if f}

            self.verses: dict[int, Verse] = {}
            for vid, book, ch, vs in conn.execute(
                    "SELECT verse_id, book, chapter, verse FROM verses ORDER BY verse_id"):
                self.verses[vid] = Verse(vid, book, int(ch), int(vs))

            # Walk every token in order. A Hebrew or Greek word rendered by
            # several English words appears as tokens with the same root:
            # those are joined into one unit. They need not be side by side:
            # "eat it up" (katesthio, Revelation 10:9) puts a pronoun between
            # "eat" and "up", so a token joins a unit of the same root that
            # it follows within MERGE_GAP positions in the same verse.
            # Every occurrence of each root, function uses included, and how
            # many of those were content uses: for the hammer skip list.
            self.occurrences: Counter = Counter()
            self.content_uses: Counter = Counter()
            # Uses of each root rendered only with stop words, for the skip list.
            self.function_uses: Counter = Counter()
            open_units: list[dict] = []     # units that a later token may still join
            for vid, pos, root, is_stop, morph, surface in conn.execute(
                    "SELECT verse_id, position, root, is_stop, morph, surface FROM tokens "
                    "ORDER BY verse_id, position"):
                v = self.verses.get(vid)
                if v is None:
                    continue
                v.english_words += 1
                if not is_stop:
                    v.english_content += 1
                # Close units this token can no longer join, oldest first,
                # so each verse keeps its units in text order.
                while open_units and (open_units[0]["vid"] != vid
                                      or pos - open_units[0]["last"] > MERGE_GAP):
                    self._close(open_units.pop(0))
                tagged = bool(root) and root[0] in "HG" and root[1:2].isdigit()
                if not tagged:
                    continue
                unit = next((u for u in open_units if u["root"] == root), None)
                if unit is not None:
                    # Same Hebrew/Greek word continued: update its flags.
                    unit["content"] |= not is_stop
                    unit["verb"] |= morph is not None
                    unit["words"].append(surface or "")
                    unit["last"] = pos
                else:
                    open_units.append({"verse": v, "vid": vid, "root": root, "last": pos,
                                       "content": not is_stop, "verb": morph is not None,
                                       "words": [surface or ""]})
            for unit in open_units:
                self._close(unit)
        except sqlite3.OperationalError as err:
            sys.exit(f"Query on atlas.db failed: {err}")
        finally:
            conn.close()

    def _close(self, unit: dict) -> None:
        """Add a finished unit to its verse. A verb always counts as content."""
        self.occurrences[unit["root"]] += 1
        if not unit["content"]:
            # Every English word for it here is a stop word ("is", "unto").
            self.function_uses[unit["root"]] += 1
        if unit["content"] or unit["verb"]:
            self.content_uses[unit["root"]] += 1
            unit["verse"].units.append(unit["root"])
            unit["verse"].english.append(" ".join(unit["words"]).lower())
            if unit["verb"]:
                unit["verse"].verbs += 1

    def headwords(self, book: str) -> dict[str, str]:
        """
        One English headword per Strong's number for a book: the KJV's
        most common rendering of it in that book ('opened' for G455 in
        Revelation, whether a verse says opened or openeth; 'poured out'
        for G1632). One number then always shows one word in a report.
        GLOSS_OVERRIDES wins where the KJV uses one English word for two
        different Greek or Hebrew words.
        """
        said: dict[str, Counter] = defaultdict(Counter)
        for v in self.verses_of(book):
            for u, e in zip(v.units, v.english):
                said[u][e] += 1
        heads = {u: c.most_common(1)[0][0] for u, c in said.items()}
        heads.update({r: g for r, g in GLOSS_OVERRIDES.items() if r in heads})
        return heads

    def verses_of(self, book: str) -> list[Verse]:
        return [v for v in self.verses.values() if v.book == book]

    def language_of(self, book: str) -> str:
        return "Hebrew" if self.testament[book] == "Old" else "Greek"


# ===========================================================================
# A window of verses and its five scores
# ===========================================================================
@dataclass
class Window:
    """Consecutive verses of one book with their measures."""
    verses: list
    scores: dict = field(default_factory=dict)
    z: dict = field(default_factory=dict)
    hammer_word: str = ""
    hammer_english: str = ""        # how the KJV renders the hammered word here
    # The wider span hammer is measured over (--hammer-window); None = the window itself.
    hammer_verses: list | None = None
    # (count, out of) behind each share, for the log-likelihood scale.
    counts: dict = field(default_factory=dict)
    # Each measure's score as printed: "+2.31", "99.2%" or "G2 +25.3".
    shown: dict = field(default_factory=dict)
    feeling_words: Counter = field(default_factory=Counter)

    @property
    def span(self) -> str:
        return f"{self.verses[0].ref}-{self.verses[-1].ref}"

    @property
    def middle(self) -> Verse:
        return self.verses[len(self.verses) // 2]


class Scorer:
    """Computes the five measures for a window."""

    def __init__(self, weight: dict, rare_limit: int, feelings: dict | None = None,
                 families: list | None = None, hammer_skip: set | None = None):
        self.weight = weight
        self.rare_limit = rare_limit
        # Words hammer ignores: the voice formulas and the most common words.
        self.hammer_skip = VOICE_ROOTS | (hammer_skip or set())
        # root -> (category, family), from metadata.db; empty if not imported.
        self.feelings = feelings or {}
        self.families = families or []

    def score(self, window: Window) -> None:
        words = sum(v.english_words for v in window.verses)
        content_en = sum(v.english_content for v in window.verses)
        units = [u for v in window.verses for u in v.units]
        verbs = sum(v.verbs for v in window.verses)
        n = len(units)

        s = window.scores
        c = window.counts
        c["density"] = (content_en, words)
        s["density"] = content_en / words if words else 0.0
        s["variety"] = self._mattr(units)
        rare = sum(1 for u in units if self.weight.get(u, 0) <= self.rare_limit)
        c["rare"] = (rare, n)
        s["rare"] = rare / n if n else 0.0
        # Hammer may look over a wider span than the window (--hammer-window).
        h_units = units if window.hammer_verses is None else \
            [u for v in window.hammer_verses for u in v.units]
        counts = Counter(u for u in h_units if u not in self.hammer_skip)
        if counts:
            word, top = counts.most_common(1)[0]
            s["hammer"] = top / len(h_units)
            window.hammer_word = word if top >= 3 else ""
        else:
            s["hammer"] = 0.0
        c["action"] = (verbs, n)
        s["action"] = verbs / n if n else 0.0

        if self.feelings:
            hits = [self.feelings[u] for u in units if u in self.feelings]
            c["feeling"] = (len(hits), n)
            s["feeling"] = len(hits) / n if n else 0.0
            window.feeling_words = Counter(u for u in units if u in self.feelings)
            for family in self.families:
                k = sum(1 for _, f in hits if f == family)
                c[family] = (k, n)
                s[family] = k / n if n else 0.0

    @staticmethod
    def _mattr(units: list) -> float:
        """Moving-average type-token ratio over runs of VARIETY_SPAN words."""
        if not units:
            return 0.0
        if len(units) <= VARIETY_SPAN:
            return len(set(units)) / len(units)
        # Slide a run of 50 along the window, keeping counts as we go.
        counts = Counter(units[:VARIETY_SPAN])
        ratios = [len(counts) / VARIETY_SPAN]
        for i in range(VARIETY_SPAN, len(units)):
            gone = units[i - VARIETY_SPAN]
            counts[gone] -= 1
            if counts[gone] == 0:
                del counts[gone]
            counts[units[i]] += 1
            ratios.append(len(counts) / VARIETY_SPAN)
        return statistics.fmean(ratios)


def windows_of(verses: list, size: int, step: int, hammer_span: int = 0) -> list[Window]:
    """
    Windows of `size` verses, moving `step` verses at a time, within one
    book. With hammer_span, each window also gets the wider run of verses
    (centered on the same verse) that hammer is measured over.
    """
    if len(verses) <= size:
        windows = [Window(verses)]
        starts = [0]
    else:
        starts = list(range(0, len(verses) - size + 1, step))
        windows = [Window(verses[i:i + size]) for i in starts]
    if hammer_span > size:
        half = hammer_span // 2
        for w, i in zip(windows, starts):
            middle = i + len(w.verses) // 2
            lo = max(0, min(middle - half, len(verses) - hammer_span))
            w.hammer_verses = verses[lo:lo + hammer_span]
    return windows


# Glosses of place and position words ("before", "midst"): repeated as
# connective tissue, not for emphasis, so hammer skips them.
PLACE_GLOSSES = {"before", "after", "among", "midst", "against", "upon", "under",
                 "beside", "about", "round", "behind", "above", "without",
                 "within", "toward", "through", "between", "beneath"}


def most_common_roots(loader: "VerseLoader", language: str, how_many: int) -> tuple[set, str]:
    """
    The words hammer skips (--hammer-skip) in one language (H or G):
      * the most used Strong's numbers, by the atlas's own weight
        ('have', 'God', 'great')
      * words the KJV renders only with stop words at least half the time
        (the forms of "to be": 'is', 'art'). A rendering with one content
        word ("burnt offering", "mercy seat") does not count as a stop use
      * place and position words such as 'before' and 'midst'
    """
    prefix = "H" if language == "Hebrew" else "G"
    roots = [r for r in loader.occurrences if r[:1] == prefix]
    ranked = sorted(roots, key=lambda r: loader.weight.get(r) or 0, reverse=True)
    common = set(ranked[:how_many])
    function = {r for r in roots if loader.function_uses[r] >= loader.occurrences[r] / 2}
    place = {r for r in roots if loader.glosses.get(r, "") in PLACE_GLOSSES}
    voice = {r for r in VOICE_ROOTS if r[:1] == prefix}
    skip = common | function | place
    # A summary for the report header, so two runs can be told apart:
    # if these numbers differ, the runs' hammer results are not comparable.
    summary = (f"{len(skip | voice)} words skipped ({len(common)} most used, "
               f"{len(function - common)} more function words, "
               f"{len(place - common - function)} more place words, {len(voice)} voice-formula words)")
    return skip, summary


# ===========================================================================
# Ordinary, and the three scales for measuring a window against it
# ===========================================================================
# Every scale sets two things on each window for each measure:
#   w.z[m]      a z-like number (0 = ordinary, +2 = far above, -2 = far
#               below), which the spots, the colors and the chapter table use,
#               so all three scales are read the same way;
#   w.shown[m]  the score as the scale itself states it, for printing.

class Scale:
    """The z scale (--scale z): distance from the ordinary average, in spreads."""

    name = "z"

    def __init__(self, reference: list[Window], label: str):
        self.label = label                     # what "ordinary" is
        self.count = len(reference)            # how many ordinary windows
        self.sampling = ""                     # how they were taken, for the header
        self.mean = {m: statistics.fmean(w.scores[m] for w in reference) for m in MEASURES}
        self.spread = {m: statistics.stdev(w.scores[m] for w in reference) for m in MEASURES}

    def z_of(self, w: Window, m: str) -> float:
        sd = self.spread[m]
        return (w.scores[m] - self.mean[m]) / sd if sd else 0.0

    def apply(self, windows: list[Window]) -> None:
        for w in windows:
            for m in MEASURES:
                self.set(w, m)

    def set(self, w: Window, m: str) -> None:
        w.z[m] = self.z_of(w, m)
        w.shown[m] = f"z {w.z[m]:+.2f}"

    def ordinary_line(self, m: str) -> str:
        return f"ordinary {self.mean[m]:.3f}, spread {self.spread[m]:.3f}"

    def threshold_text(self, t: float) -> str:
        return f"spots at z {t:+.1f} and beyond"

    def chapter_cell(self, ws: list[Window], m: str) -> str:
        return f"{statistics.fmean(w.z[m] for w in ws):+9.2f}"

    chapter_note = "average z of the windows centered in each chapter"
    legend = ("cool (z -3)", "ordinary", "hot (z +3)")


class PercentileScale(Scale):
    """
    The percentile scale (--scale percentile): the share of ordinary windows
    that score lower. 50% is ordinary; 99% means hotter than 99 ordinary
    windows in 100. It needs no bell curve, so it suits the count strips,
    where most ordinary windows score zero. Ties count half; and on the
    feeling strips a window with none of the words is set to exactly 50%
    (gray), because "none here" is ordinary, not a finding. Those strips
    therefore show red or gray, almost never blue.
    """

    name = "percentile"

    def __init__(self, reference: list[Window], label: str):
        super().__init__(reference, label)
        # Every ordinary score of each measure, sorted, for ranking.
        self.sorted = {m: sorted(w.scores[m] for w in reference) for m in MEASURES}

    def percentile(self, value: float, m: str) -> float:
        ranked = self.sorted[m]
        below = bisect.bisect_left(ranked, value)
        equal = bisect.bisect_right(ranked, value) - below
        return 100.0 * (below + 0.5 * equal) / len(ranked)

    # Strips where "none here" is shown as exactly ordinary (50%, gray):
    # most text has none of these words, so a zero is not a finding.
    ZERO_IS_ORDINARY = {"feeling", *FAMILY_NAMES}

    def set(self, w: Window, m: str) -> None:
        pct = self.percentile(w.scores[m], m)
        if m in self.ZERO_IS_ORDINARY and w.scores[m] == 0:
            pct = 50.0
        # The z that a bell curve would give the same percentile, so a
        # threshold of 2 means the top or bottom 2.3% on every scale.
        share = min(max(pct / 100.0, 0.0005), 0.9995)
        w.z[m] = NormalDist().inv_cdf(share)
        w.shown[m] = f"{pct:.1f}%"

    def ordinary_line(self, m: str) -> str:
        return f"ordinary (median) {statistics.median(self.sorted[m]):.3f}"

    def threshold_text(self, t: float) -> str:
        share = 100 * (1 - NormalDist().cdf(t))
        return f"spots in the top and bottom {share:.1f}% of ordinary windows"

    def chapter_cell(self, ws: list[Window], m: str) -> str:
        pct = statistics.fmean(self.percentile(w.scores[m], m) for w in ws)
        return f"{pct:8.1f}%"

    chapter_note = "average percentile of the windows centered in each chapter"
    legend = ("cool (bottom 0.1%)", "ordinary (50%)", "hot (top 0.1%)")


class LogLikelihoodScale(Scale):
    """
    The log-likelihood scale (--scale g2): for the strips that count words
    (density, rare, action and the feeling strips), how surprising the
    window's count is, given the ordinary rate. It is Dunning's G squared,
    the keyness measure used everywhere else in the atlas: 3.84 is good
    evidence (p < 0.05), 10.83 strong evidence (p < 0.001). It weighs the
    size of the window as well as the rate, so a few words in a short
    window count for less than the same rate in a long one.

    The z-like number is the square root of G squared with its sign, which
    is how far a bell curve would put the same evidence: G2 10.83 = 3.29.
    Variety and hammer do not count words this way, so they stay on z.
    """

    name = "g2"
    COUNTED = {"density", "rare", "action", "feeling", *FAMILY_NAMES}

    def __init__(self, reference: list[Window], label: str):
        super().__init__(reference, label)
        # Ordinary totals: words of the kind, and words in all, per measure.
        self.total = {}
        for m in MEASURES:
            if m in self.COUNTED:
                self.total[m] = (sum(w.counts[m][0] for w in reference),
                                 sum(w.counts[m][1] for w in reference))

    @staticmethod
    def g2(k: int, n: int, big_k: int, big_n: int) -> float:
        """Signed G squared: k of n in the window against big_k of big_n ordinary."""
        if n == 0 or big_n == 0:
            return 0.0
        both = k + big_k
        e1 = n * both / (n + big_n)
        e2 = big_n * both / (n + big_n)
        value = 0.0
        if k > 0 and e1 > 0:
            value += k * math.log(k / e1)
        if big_k > 0 and e2 > 0:
            value += big_k * math.log(big_k / e2)
        value *= 2
        return value if k / n >= big_k / big_n else -value

    def set(self, w: Window, m: str) -> None:
        if m not in self.COUNTED:
            super().set(w, m)
            return
        k, n = w.counts[m]
        value = self.g2(k, n, *self.total[m])
        w.z[m] = math.copysign(math.sqrt(abs(value)), value)
        w.shown[m] = f"G2 {value:+.1f}"

    def ordinary_line(self, m: str) -> str:
        if m not in self.COUNTED:
            return super().ordinary_line(m) + " (z scale)"
        k, n = self.total[m]
        return f"ordinary rate {k / n:.4f} ({k:,} of {n:,})" if n else "no ordinary text"

    def threshold_text(self, t: float) -> str:
        return (f"spots at G2 {t * t:.2f} and beyond on the counted strips "
                f"(z {t:+.2f} on variety and hammer)")

    chapter_note = "average z-equivalent (signed square root of G2) of the windows in each chapter"
    legend = ("cool (G2 -9)", "ordinary", "hot (G2 +9)")


SCALES = {"z": Scale, "percentile": PercentileScale, "g2": LogLikelihoodScale}

# The usual threshold for each scale, in z-like units: the top or bottom
# 2.3% for z and percentile; strong evidence (G2 10.83) for log-likelihood.
DEFAULT_THRESHOLD = {"z": 2.0, "percentile": 2.0, "g2": math.sqrt(10.83)}


# ===========================================================================
# Hot and cool spots
# ===========================================================================
@dataclass
class Spot:
    """A run of windows past the threshold on one measure."""
    measure: str
    first: Window
    last: Window
    peak: Window
    hot: bool

    def span(self, book: str) -> str:
        a, b = self.first.verses[0], self.last.verses[-1]
        if a.chapter == b.chapter:
            return f"{book} {a.chapter}:{a.verse}-{b.verse}"
        return f"{book} {a.ref}-{b.ref}"


def find_spots(windows: list[Window], measure: str, threshold: float) -> list[Spot]:
    """Group neighboring windows past the threshold into spots."""
    spots = []
    for hot in (True, False):
        run = []
        for w in windows + [None]:          # None closes the last run
            past = w is not None and (w.z[measure] >= threshold if hot
                                      else w.z[measure] <= -threshold)
            if past:
                run.append(w)
            elif run:
                peak = max(run, key=lambda x: x.z[measure]) if hot else \
                    min(run, key=lambda x: x.z[measure])
                spots.append(Spot(measure, run[0], run[-1], peak, hot))
                run = []
    return spots


# ===========================================================================
# The text report
# ===========================================================================
class HeatReport:

    def __init__(self, book: str, windows: list[Window], norms: Scale, loader: VerseLoader, args,
                 feelings: dict | None = None):
        self.feelings = feelings or {}
        # One English headword per Strong's number (see VerseLoader.headwords).
        self.heads = loader.headwords(book)
        self.book = book
        self.windows = windows
        self.norms = norms
        self.loader = loader
        self.args = args

    def build_line(self) -> str:
        """The atlas's own build line when it can be had, else a short one."""
        try:
            from atlas_pages import Atlas
            return Atlas(str(self.args.atlas)).build_line()
        except Exception:
            s = self.loader.settings
            return f"Word Atlas build '{s.get('label', 'unlabelled')}' made {s.get('built', '?')}."

    def feeling_detail(self, spot: "Spot", measure: str) -> str:
        """The categories and words behind a feeling hot spot, across its windows."""
        words = Counter()
        w_list = self.windows[self.windows.index(spot.first):self.windows.index(spot.last) + 1]
        seen = set()
        for w in w_list:
            for v in w.verses:
                if v.verse_id in seen:
                    continue
                seen.add(v.verse_id)
                for u in v.units:
                    cat_fam = self.feelings.get(u)
                    if cat_fam and (measure == "feeling" or cat_fam[1] == measure):
                        words[u] += 1
        cats = Counter()
        for u, n in words.items():
            cats[self.feelings[u][0]] += n
        top_cats = ", ".join(f"{c} {n}" for c, n in cats.most_common(3))
        # Distinct glosses: two Strong's numbers can share one English gloss.
        glosses = []
        for u, _ in words.most_common():
            g = self.heads.get(u) or self.loader.glosses.get(u, u)
            if g not in glosses:
                glosses.append(g)
        top_words = ", ".join(f"'{g}'" for g in glosses[:4])
        return f"{top_cats}; {top_words}"

    def gloss(self, root: str) -> str:
        return f"'{self.loader.glosses.get(root, root)}' {root}" if root else ""

    def render(self) -> str:
        a = self.args
        out = [f"HOT AND COOL SPOTS: {self.book}",
               self.build_line(),
               f"Heat window: {a.window} verses, moving 1 verse at a time "
               f"(not the build line's word window of {self.loader.settings.get('window', '?')}); "
               f"{self.norms.threshold_text(a.threshold)} (scale: {self.norms.name}).",
               f"Hammer: over {a.hammer_window or a.window} verses; {a.skip_summary}.",
               f"Ordinary = {self.norms.label} ({self.norms.count:,} windows{self.norms.sampling}).",
               ""]

        # Each measure's spots, hot first, in text order.
        for m in MEASURES:
            spots = find_spots(self.windows, m, a.threshold)
            hot = [s for s in spots if s.hot]
            cool = [s for s in spots if not s.hot]
            out.append(f"({m})  {self.norms.ordinary_line(m)}")
            for label, group in (("hot", hot), ("cool", cool)):
                if not group:
                    out.append(f"  {label}: none")
                    continue
                for s in sorted(group, key=lambda s: s.first.verses[0].verse_id):
                    extra = ""
                    # Only a hot spot has a hammered word; on a cool spot
                    # the top word is weak by definition, so it is not named.
                    if m == "hammer" and s.hot and s.peak.hammer_word:
                        extra = f"  hammered: '{s.peak.hammer_english}' {s.peak.hammer_word}"
                    if s.hot and (m == "feeling" or m in FAMILY_NAMES):
                        extra = "  " + self.feeling_detail(s, m)
                    out.append(f"  {label:<5}{s.span(self.book):<28}"
                               f"peak {s.peak.shown[m]:>10} at {s.peak.middle.ref}{extra}")
            out.append("")

        out.extend(self._chapter_table())
        out.extend(["NOTES",
                    "  Scales (--scale): z = distance from ordinary in spreads; percentile =",
                    "  share of ordinary windows scoring lower; g2 = how surprising a word",
                    "  count is (G2 3.84 good evidence, 10.83 strong). The spots and colors",
                    "  use the same z-like units on all three, so +2 always means about the",
                    "  top 2.3% and +3.29 means G2 10.83.",
                    "  Spots overlap because windows overlap: a spot's verses run from its",
                    "  first window's start to its last window's end.",
                    "  On the z scale, families that are rare everywhere (harlotry, wealth)",
                    "  have a tiny ordinary spread, so their z can run far past 3; the",
                    "  percentile and g2 scales are built for such counts."])
        return "\n".join(out)

    def _chapter_table(self) -> list[str]:
        """Each chapter's average score on the chosen scale."""
        by_chapter = defaultdict(list)
        for w in self.windows:
            by_chapter[w.middle.chapter].append(w)
        out = [f"CHAPTERS  ({self.norms.chapter_note})",
               "  ch " + "".join(f"{m:>9}" for m in MEASURES) + "   most hammered"]
        for ch in sorted(by_chapter):
            ws = by_chapter[ch]
            cells = "".join(self.norms.chapter_cell(ws, m) for m in MEASURES)
            words = Counter((w.hammer_word, w.hammer_english) for w in ws if w.hammer_word)
            top = ""
            if words:
                root, english = words.most_common(1)[0][0]
                top = f"'{english}' {root}"
            out.append(f"  {ch:>3}{cells}   {top}")
        out.append("")
        return out


# ===========================================================================
# The strip chart (SVG, no extra packages needed)
# ===========================================================================
class StripChart:
    """
    One strip per measure along the book. Colors run blue (cool) through
    gray (ordinary) to red (hot), clamped at z = 3.
    """

    COOL = (0x2a, 0x78, 0xd6)
    MID = (0xf0, 0xef, 0xec)
    HOT = (0xe3, 0x49, 0x48)
    INK = "#2b2b29"
    MUTED = "#6b6a66"
    SURFACE = "#fcfcfb"

    def __init__(self, book: str, windows: list[Window], norms: Scale, args,
                 glosses: dict | None = None):
        # English glosses for Strong's numbers, shown in the hammer tooltips.
        self.glosses = glosses or {}
        self.book = book
        self.windows = windows
        self.norms = norms
        self.args = args

    def color(self, z: float) -> str:
        t = max(-3.0, min(3.0, z)) / 3.0
        end = self.HOT if t > 0 else self.COOL
        t = abs(t)
        rgb = [round(m + (e - m) * t) for m, e in zip(self.MID, end)]
        return "#%02x%02x%02x" % tuple(rgb)

    def render(self) -> str:
        n = len(self.windows)
        left, plot_w = 90, 1100
        cell = plot_w / n
        strip_h, gap, top = 34, 8, 56
        height = top + len(MEASURES) * (strip_h + gap) + 90
        width = left + plot_w + 30
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
                 f'viewBox="0 0 {width} {height}" font-family="sans-serif">',
                 f'<rect width="100%" height="100%" fill="{self.SURFACE}"/>',
                 f'<text x="{left}" y="24" font-size="16" fill="{self.INK}">'
                 f'Hot and cool spots: {escape(self.book)}</text>',
                 f'<text x="{left}" y="42" font-size="11" fill="{self.MUTED}">'
                 f'Window {self.args.window} verses. Scale {self.norms.name}. '
                 f'Ordinary = {escape(self.norms.label)}. '
                 f'Point at a cell for its verses and score.</text>']

        for row, m in enumerate(MEASURES):
            y = top + row * (strip_h + gap)
            parts.append(f'<text x="{left - 8}" y="{y + strip_h / 2 + 4}" font-size="12" '
                         f'text-anchor="end" fill="{self.INK}">{m}</text>')
            for i, w in enumerate(self.windows):
                tip = f"{self.book} {w.span}  ({m}) {w.shown[m]}"
                if m == "hammer":
                    tip += (f"  word {w.hammer_word} '{w.hammer_english}'" if w.hammer_word
                            else "  no repeated word")
                parts.append(f'<rect x="{left + i * cell:.2f}" y="{y}" width="{cell + 0.05:.2f}" '
                             f'height="{strip_h}" fill="{self.color(w.z[m])}">'
                             f'<title>{escape(tip)}</title></rect>')

        # Chapter marks under the strips.
        axis_y = top + len(MEASURES) * (strip_h + gap)
        starts = {}
        for i, w in enumerate(self.windows):
            starts.setdefault(w.middle.chapter, i)
        every = 1 if len(starts) <= 30 else 5
        for ch, i in starts.items():
            x = left + i * cell
            parts.append(f'<line x1="{x:.1f}" y1="{axis_y - 4}" x2="{x:.1f}" y2="{axis_y + 2}" '
                         f'stroke="{self.MUTED}" stroke-width="1"/>')
            if ch == 1 or ch % every == 0:
                parts.append(f'<text x="{x:.1f}" y="{axis_y + 14}" font-size="10" '
                             f'text-anchor="middle" fill="{self.MUTED}">{ch}</text>')
        parts.append(f'<text x="{left - 8}" y="{axis_y + 14}" font-size="10" text-anchor="end" '
                     f'fill="{self.MUTED}">chapter</text>')

        # Legend: a small color scale.
        ly = axis_y + 40
        for k in range(61):
            z = -3 + k * 0.1
            parts.append(f'<rect x="{left + k * 4}" y="{ly}" width="4.2" height="12" '
                         f'fill="{self.color(z)}"/>')
        for z, label in zip((-3, 0, 3), self.norms.legend):
            parts.append(f'<text x="{left + (z + 3) * 40}" y="{ly + 26}" font-size="10" '
                         f'text-anchor="middle" fill="{self.MUTED}">{label}</text>')
        parts.append("</svg>")
        return "\n".join(parts)


# ===========================================================================
# Command line
# ===========================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description="Word Atlas hot and cool spots")
    parser.add_argument("book", help="a book name as atlas.db spells it, e.g. Ezekiel")
    parser.add_argument("--window", type=int, default=10, help="verses per window (default 10)")
    parser.add_argument("--scale", choices=sorted(SCALES), default="z",
                        help="z (default), percentile, or g2 (log-likelihood for the counted strips)")
    parser.add_argument("--threshold", type=float, default=None,
                        help="spot threshold in z-like units (default 2; 3.29 = G2 10.83 for g2)")
    parser.add_argument("--rare", type=int, default=10,
                        help="a word is rare at this many uses in the Bible or fewer (default 10)")
    parser.add_argument("--norm", choices=["bible", "book"], default="bible",
                        help="ordinary = the Bible in the same language (default) or the book itself")
    parser.add_argument("--hammer-skip", type=int, default=100,
                        help="hammer ignores this many of the most used words (default 100, 0 = none)")
    parser.add_argument("--hammer-window", type=int, default=0,
                        help="measure hammer over this many verses around each window (e.g. 30)")
    parser.add_argument("--families", action="store_true",
                        help="add one strip per feeling-word family (needs the feeling list)")
    parser.add_argument("--atlas", type=Path, default=SCRIPT_DIR / "atlas.db")
    parser.add_argument("--metadata", type=Path, default=SCRIPT_DIR / "metadata.db")
    parser.add_argument("--out", type=Path, help="also write the report to this file")
    parser.add_argument("--svg", type=Path, help="write the strip chart to this SVG file")
    args = parser.parse_args()
    if args.threshold is None:
        args.threshold = DEFAULT_THRESHOLD[args.scale]

    loader = VerseLoader(args.atlas)
    # Accept any capitalization of the book name.
    names = {b.lower(): b for b in loader.books}
    book = names.get(args.book.lower())
    if book is None:
        sys.exit(f"Unknown book '{args.book}'. Use the name as atlas.db spells it.")

    # The feeling-word list, when it has been reviewed and imported.
    from atlas_feelings import load_feeling_words
    feelings = load_feeling_words(args.metadata)
    families = []
    if feelings:
        MEASURES.append("feeling")
        if args.families:
            families = FAMILY_NAMES
            MEASURES.extend(families)
    elif args.families:
        print("Note: no feeling words in metadata.db yet (atlas_feelings.py), so no families.\n")

    skip, args.skip_summary = most_common_roots(loader, loader.language_of(book), args.hammer_skip) \
        if args.hammer_skip else (set(), "only the voice-formula words skipped")
    scorer = Scorer(loader.weight, args.rare, feelings, families, skip)
    windows = windows_of(loader.verses_of(book), args.window, 1, args.hammer_window)
    for w in windows:
        scorer.score(w)
    # One English headword per Strong's number for the whole report.
    heads = loader.headwords(book)
    for w in windows:
        w.hammer_english = heads.get(w.hammer_word, "")

    if args.norm == "book":
        norms = SCALES[args.scale](windows, f"{book} itself")
        norms.sampling = ", one starting at every verse"
    else:
        # Ordinary windows: every book of the same language, side by side
        # (step = half a window, so they overlap less and count faster).
        language = loader.language_of(book)
        reference = []
        for b in loader.books:
            if loader.language_of(b) == language:
                reference.extend(windows_of(loader.verses_of(b), args.window,
                                            max(1, args.window // 2), args.hammer_window))
        for w in reference:
            scorer.score(w)
        testament = "Old" if language == "Hebrew" else "New"
        step = max(1, args.window // 2)
        norms = SCALES[args.scale](reference, f"every {testament} Testament book ({language})")
        # Ordinary windows start every half window, not every verse:
        # neighbors then share half their verses instead of nine tenths,
        # and the average and spread come out the same.
        norms.sampling = f", one starting every {step} verses"
    norms.apply(windows)

    text = HeatReport(book, windows, norms, loader, args, feelings).render()
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"\nWritten to {args.out}")
    if args.svg:
        args.svg.parent.mkdir(parents=True, exist_ok=True)
        args.svg.write_text(StripChart(book, windows, norms, args, loader.glosses).render(), encoding="utf-8")
        print(f"Strip chart written to {args.svg}")


if __name__ == "__main__":
    main()
