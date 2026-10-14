#!/usr/bin/env python3
"""
heat_explore.py

Questions to ask of heat_reports.json, the file that gathers every
book's heat reports (run_heat.py --all --one) into one place.  Each
book holds four reports: the book against itself (percentile scale),
against its testament (z scale), against its testament on the
log-likelihood scale (g2), and the names report (names and numbers
strips with the families, g2 scale, an Old Testament book against its
own kind).  The names report carries every strip, so it is the one most
questions read; --report picks another.

    python3 heat_explore.py summary                 every strip: its strongest spots in the Bible
    python3 heat_explore.py book Daniel             one book: every strip's hot spots, dates, feasts
    python3 heat_explore.py strip persons           one strip: its hot spots across the Bible, strongest first
    python3 heat_explore.py strip numbers --top 30
    python3 heat_explore.py word Babylon            every spot whose words include one
    python3 heat_explore.py chapters Ezekiel        the chapter table of one book
    python3 heat_explore.py compare Ezekiel Revelation     two books, strip by strip
    python3 heat_explore.py csv reports/heat_chapters.csv  every chapter of every book, one row each
    python3 heat_explore.py book Daniel --report 2  the g2 report against the testament (0 self, 1 testament, 2 g2, 3 names)

The file is reports/heat_reports.json unless --json says otherwise.
Nothing is written except by csv.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

# Folder this script lives in, so default paths work on Ubuntu and Windows.
SCRIPT_DIR = Path(__file__).resolve().parent

# The four reports of a book, in the order run_heat.py writes them.
REPORT_NAMES = ["self", "testament", "g2", "names"]

# A chapter is called hot on a strip at this z-equivalent (G2 10.83).
HOT_AT = 3.29


class Spot:
    """One hot or cool spot of one strip in one book, as the file holds it."""

    def __init__(self, book, strip, data, hot=True):
        self.book = book
        self.strip = strip
        self.hot = hot
        self.start = data["start"]
        self.end = data["end"]
        self.peak = data["peak"]["value"]
        self.at = data["peak"]["at"]
        self.scale = data["peak"]["scale"]
        # The words behind the spot: names and numbers, feeling words, or
        # the hammered word, whichever kind of strip this is.
        words = data.get("words") or []
        self.words = [(w["word"], w.get("count")) for w in words if isinstance(w, dict) and "word" in w]
        if "hammered" in data:
            self.words = [(data["hammered"]["word"], None)]
        self.families = data.get("families") or {}

    @property
    def span(self):
        return f"{self.book} {self.start}-{self.end}"

    def words_text(self, how_many=4):
        """'Jeremiah 51, Baruch 16, Zedekiah 14'."""
        parts = [f"{w} {n}" if n else w for w, n in self.words[:how_many]]
        if self.families and not parts:
            parts = [f"{f} {n}" for f, n in self.families.items()]
        return ", ".join(parts)

    def line(self, with_book=True):
        where = self.span if with_book else f"{self.start}-{self.end}"
        return f"  {where:<26} peak {self.scale} {self.peak:+7.1f} at {self.at:<7} {self.words_text()}"


class HeatFile:
    """heat_reports.json read once, with the questions the commands ask."""

    def __init__(self, path):
        if not path.exists():
            sys.exit(f"{path} not found. Make it from the reports of run_heat.py --all --one.")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.generated = data.get("generated", "?")
        self.books = data["books"]                       # in Bible order
        self.by_name = {b["book"].lower(): b for b in self.books}

    def book(self, name):
        """A book's entry, by any capitalization of its name."""
        entry = self.by_name.get(name.lower())
        if entry is None:
            sys.exit(f"No book '{name}' in the file. Books: " + ", ".join(b["book"] for b in self.books))
        return entry

    @staticmethod
    def report(entry, which):
        """One of a book's four reports, by number (0 to 3) or name."""
        reports = entry["reports"]
        index = REPORT_NAMES.index(which) if which in REPORT_NAMES else int(which)
        if index >= len(reports):
            sys.exit(f"{entry['book']} has {len(reports)} reports in the file, not {index + 1}.")
        return reports[index]

    def strips(self, entry, which):
        """The strips of one report: [(name, [hot Spot, ...], [cool Spot, ...]), ...]."""
        out = []
        for s in self.report(entry, which)["strips"]:
            hot = [Spot(entry["book"], s["name"], h) for h in s.get("hot", [])]
            cool = [Spot(entry["book"], s["name"], c, hot=False) for c in s.get("cool", [])]
            out.append((s["name"], hot, cool))
        return out

    def all_spots(self, which):
        """Every hot spot of every book, by strip name."""
        spots = defaultdict(list)
        for entry in self.books:
            for name, hot, _ in self.strips(entry, which):
                spots[name].extend(hot)
        return spots

    def hot_chapters(self, entry, which):
        """strip -> (hot chapters, chapters) for one book's report."""
        chapters = self.report(entry, which)["chapters"]
        counts = {}
        for ch in chapters:
            for strip, value in ch["values"].items():
                hot, total = counts.get(strip, (0, 0))
                counts[strip] = (hot + (1 if (value or 0) >= HOT_AT else 0), total + 1)
        return counts


# ===========================================================================
# The commands
# ===========================================================================
def summary(heat, args):
    """Every strip: its strongest hot spots in the Bible and the books with most hot chapters."""
    spots = heat.all_spots(args.report)
    shares = defaultdict(list)
    for entry in heat.books:
        for strip, (hot, total) in heat.hot_chapters(entry, args.report).items():
            if hot:
                shares[strip].append((hot / total, hot, total, entry["book"]))
    print(f"heat_reports.json made {heat.generated}; {len(heat.books)} books; "
          f"the {REPORT_NAMES[int(args.report) if args.report.isdigit() else REPORT_NAMES.index(args.report)]} report\n")
    for strip in spots:
        print(f"({strip})  strongest hot spots")
        for spot in sorted(spots[strip], key=lambda s: -s.peak)[:args.top]:
            print(spot.line())
        best = sorted(shares[strip], reverse=True)[:5]
        if best:
            print("  most hot chapters: " + ", ".join(f"{b} {h}/{t}" for _, h, t, b in best))
        print()


def book(heat, args):
    """One book: every strip's hot and cool spots, then its dates and feasts."""
    entry = heat.book(args.book)
    rep = heat.report(entry, args.report)
    print(f"{entry['book']}: {rep['ordinary']['text']}")
    print(f"  {rep['heat_window']['text']}\n")
    for name, hot, cool in heat.strips(entry, args.report):
        print(f"({name})  {rep_ordinary(rep, name)}")
        for spot in hot:
            print("  hot" + spot.line(with_book=False)[3:])
        if not hot:
            print("  hot: none")
        if cool:
            print(f"  cool: " + "; ".join(f"{c.start}-{c.end}" for c in cool))
        print()
    for kind in ("dates", "feasts"):
        found = rep.get(kind) or []
        print(f"{kind.upper()}  ({len(found)} verses)")
        print("  " + "; ".join(f"{v['ref']} {', '.join(v.get('words') or [v.get('text', '')])}"
                               for v in found) if found else "  none")
        print()


def rep_ordinary(rep, name):
    """The ordinary line of one strip in a report, when the file holds it."""
    for s in rep["strips"]:
        if s["name"] == name:
            return (s.get("ordinary") or {}).get("text", "")
    return ""


def strip(heat, args):
    """One strip across the Bible: hot spots strongest first, then the books by hot chapters."""
    spots = heat.all_spots(args.report).get(args.strip)
    if spots is None:
        sys.exit(f"No strip '{args.strip}'. Strips: " + ", ".join(heat.all_spots(args.report)))
    print(f"({args.strip})  {len(spots)} hot spots in {len(heat.books)} books; the {args.top} strongest\n")
    for spot in sorted(spots, key=lambda s: -s.peak)[:args.top]:
        print(spot.line())
    print("\nbooks by share of hot chapters")
    shares = []
    for entry in heat.books:
        hot, total = heat.hot_chapters(entry, args.report).get(args.strip, (0, 0))
        if hot:
            shares.append((hot / total, hot, total, entry["book"]))
    for share, hot, total, name in sorted(shares, reverse=True)[:args.top]:
        print(f"  {name:<18}{hot:>3} of {total:<4} chapters hot ({share:.0%})")


def word(heat, args):
    """Every hot spot, on any strip, whose words include the one asked for."""
    wanted = args.word.lower()
    found = []
    for name, spots in heat.all_spots(args.report).items():
        for spot in spots:
            if any(wanted == w.lower() or wanted in w.lower() for w, _ in spot.words):
                found.append(spot)
    print(f"'{args.word}' is behind {len(found)} hot spots\n")
    for spot in sorted(found, key=lambda s: -s.peak):
        print(f"  {spot.strip:<16}" + spot.line().lstrip())


def chapters(heat, args):
    """The chapter table of one book: each chapter's z-equivalent on every strip."""
    entry = heat.book(args.book)
    rep = heat.report(entry, args.report)
    names = list(rep["chapters"][0]["values"])
    width = {n: max(8, len(n) + 1) for n in names}
    print(f"{entry['book']}  ({rep.get('chapters_note', '')})")
    print("  ch " + "".join(f"{n:>{width[n]}}" for n in names) + "   most hammered")
    for ch in rep["chapters"]:
        cells = "".join(f"{(ch['values'].get(n) or 0):>{width[n]}.2f}" for n in names)
        hammered = ch.get("most_hammered") or {}
        print(f"  {ch['chapter']:>3}{cells}   {hammered.get('word', '')}")


def compare(heat, args):
    """Two books strip by strip: hot chapters and the strongest spot of each."""
    entries = [heat.book(b) for b in args.books]
    counts = [heat.hot_chapters(e, args.report) for e in entries]
    spots = [dict((name, hot) for name, hot, _ in heat.strips(e, args.report)) for e in entries]
    names = list(counts[0])
    print(f"  {'strip':<16}" + "".join(f"{e['book']:>22}" for e in entries) + "   strongest spot in each")
    for name in names:
        cells = ""
        for c in counts:
            hot, total = c.get(name, (0, 0))
            cells += f"{hot:>12} of {total:<6}"
        best = []
        for e, s in zip(entries, spots):
            top = max(s.get(name, []), key=lambda x: x.peak, default=None)
            best.append(f"{top.start}-{top.end} ({top.peak:+.0f})" if top else "-")
        print(f"  {name:<16}{cells}   " + "  |  ".join(best))


def write_csv(heat, args):
    """Every chapter of every book as one row: book, chapter, then a column per strip."""
    names = []
    rows = []
    for entry in heat.books:
        rep = heat.report(entry, args.report)
        for ch in rep["chapters"]:
            for n in ch["values"]:
                if n not in names:
                    names.append(n)
            rows.append((entry["book"], ch["chapter"], ch["values"], (ch.get("most_hammered") or {}).get("word", "")))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["book", "chapter"] + names + ["most_hammered"])
        for book_name, chapter, values, hammered in rows:
            writer.writerow([book_name, chapter] + [values.get(n, "") for n in names] + [hammered])
    print(f"{len(rows)} chapter rows written to {args.out}")


def main(argv=None):
    # The options every command takes, so they can stand after the command.
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--json", type=Path, default=SCRIPT_DIR / "reports" / "heat_reports.json")
    shared.add_argument("--report", default="names",
                        help="which of a book's four reports: self, testament, g2, names (default), or 0 to 3")
    shared.add_argument("--top", type=int, default=8, help="how many spots or books to list (default 8)")
    parser = argparse.ArgumentParser(description="Questions to ask of heat_reports.json.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("summary", parents=[shared], help="every strip's strongest spots in the Bible")
    p = commands.add_parser("book", parents=[shared], help="one book, every strip"); p.add_argument("book")
    p = commands.add_parser("strip", parents=[shared], help="one strip across the Bible"); p.add_argument("strip")
    p = commands.add_parser("word", parents=[shared], help="the spots a word is behind"); p.add_argument("word")
    p = commands.add_parser("chapters", parents=[shared], help="one book's chapter table"); p.add_argument("book")
    p = commands.add_parser("compare", parents=[shared], help="two or more books strip by strip")
    p.add_argument("books", nargs="+")
    p = commands.add_parser("csv", parents=[shared], help="every chapter of every book as rows")
    p.add_argument("out", type=Path)
    args = parser.parse_args(argv)

    heat = HeatFile(args.json)
    {"summary": summary, "book": book, "strip": strip, "word": word, "chapters": chapters,
     "compare": compare, "csv": write_csv}[args.command](heat, args)


if __name__ == "__main__":
    main()
