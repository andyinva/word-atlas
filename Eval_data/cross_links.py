#!/usr/bin/env python3
"""
cross_links.py

The cross-reference check across the two testaments.

validate_links.py tests the heat companions one testament at a time, so
the New Testament books whose kinship of matter lies in the Old (Hebrews
with the Psalms, Matthew with the prophets, Revelation with Daniel and
Ezekiel) are tested only against other New Testament books.  Here every
window of the Bible looks for its companions in both testaments at once,
and the OpenBible cross references, which cross between the testaments
freely, are the check.  (Sefaria's links are the Hebrew Bible only, so
they cannot speak to this.)

HOW THE TWO TESTAMENTS ARE PUT SIDE BY SIDE
    A Hebrew window and a Greek window cannot be compared word by word:
    their Strong's numbers are different words.  The heat strips can be
    compared, because each window is scored against ordinary in its own
    testament (the testament baseline): a Greek window that is as far
    above ordinary Greek in density and rare words as a Hebrew window is
    above ordinary Hebrew counts as alike.  So the companions here are
    kinship of manner relative to each testament, as in validate_links.py,
    and the strips both testaments have are used (the Greek-only fruit and
    flesh lists are left out, and feeling, which its families repeat).

THREE TESTS
    Crossing      How often a window's companions fall in the other
                  testament, against how often they would if companions
                  were drawn at random from the whole Bible.
    Linked        For the companions that cross, how often a cross
                  reference joins the window to its companion, against a
                  random window from the companion's book.
    Leans across  For every book, the book of the other testament its
                  crossing companions fall in most, and the OpenBible links
                  between the two against the number expected (obs/exp,
                  with a 95% range), sorted into kinds as in
                  validate_links.py; with the partners the readers would
                  name, by ratio and by size.

OUTPUT
    Eval_data/results/links_cross.txt    the report
    Eval_data/results/links_cross.json   the numbers

Usage (with the venv on, since it needs numpy, scipy and scikit-learn):
    python3 Eval_data/cross_links.py
    python3 Eval_data/cross_links.py --k 30 --min-votes 5
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

# This script lives in word_atlas/Eval_data, beside validate_links.py.
EVAL_DIR = Path(__file__).resolve().parent
ATLAS_DIR = EVAL_DIR.parent
sys.path.insert(0, str(EVAL_DIR))

from eval_load import WindowData                                   # noqa: E402
from isolation import WindowTable, Shape, companions               # noqa: E402
from validate_links import (VerseIds, LinkWeb, linked, ratio_range, kind_of,   # noqa: E402
                            MIN_EXPECTED, CONFIRMED, MATTER_LINE, AS_EXPECTED)

# Strips left out of the shared set: feeling repeats its families.
LEAVE_OUT = {"feeling"}


class CrossCheck:
    """Companions drawn from the whole Bible, tested against the OpenBible links."""

    def __init__(self, args):
        self.args = args
        self.rng = np.random.default_rng(args.seed)
        self.data = WindowData()
        # The strips both testaments have, in the Old Testament's order.
        old = self.data.book(self.data.books("Old")[0])["measures"]
        new = set(self.data.book(self.data.books("New")[0])["measures"])
        self.strips = [s for s in old if s in new and s not in LEAVE_OUT]
        # Every window of the Bible, each scored against its own testament.
        self.table = WindowTable(self.data, None, "testament", "g2z", self.strips)
        testament_of = {e["book"]: e["testament"] for e in self.data.index["books"]}
        self.testament = np.array([testament_of[b] for b in self.table.book])
        self.book_testament = {b: testament_of[b] for b in self.table.books}
        # Each window's first and last verse_id.
        start, end = [], []
        for name in self.table.books:
            d = self.data.book(name)
            start += d["windows"]["start_id"]
            end += d["windows"]["end_id"]
        self.start_id, self.end_id = np.array(start), np.array(end)

    def fit(self):
        """The companions, as isolation.py finds them, over the whole Bible."""
        shape = Shape(self.table.X, 6.0)
        W = shape.whiten(self.table.X)
        _, self.idx = companions(self.table, W, self.args.k)
        self.crossing = self.testament[self.idx] != self.testament[:, None]

    # ------------------------------------------------------------------
    def crossing_test(self) -> dict:
        """Share of companions in the other testament, against random companions."""
        out = {}
        n_all = len(self.table)
        for t in ("Old", "New"):
            mine = self.testament == t
            other = int((self.testament != t).sum())
            # Random companions come from every window but the book's own.
            own_book = self.table.counts[self.table.book_index[mine]]
            chance = float(np.mean(other / (n_all - own_book)))
            share = float(self.crossing[mine].mean())
            out[t] = {"share": round(share, 4), "chance": round(chance, 4),
                      "ratio": round(share / chance, 3) if chance else None,
                      "windows": int(mine.sum())}
        return out

    def linked_test(self, web: LinkWeb) -> dict:
        """For crossing companions: linked share, against a random window of the companion's book."""
        draws, rng = self.args.draws, self.rng
        first = np.array(self.table.starts)
        count = self.table.counts
        obs_rows, rand_rows, testaments = [], [], []
        for i in range(len(self.table)):
            js = self.idx[i][self.crossing[i]]
            if len(js) == 0:
                continue
            targets = web.window_targets(self.start_id[i], self.end_id[i])
            hit = linked(targets, self.start_id[js], self.end_id[js])
            # Random partners from the same book as each companion.
            books = self.table.book_index[js]
            picks = first[books][:, None] + (rng.random((len(js), draws)) * count[books][:, None]).astype(int)
            rhit = linked(targets, self.start_id[picks.ravel()], self.end_id[picks.ravel()])
            obs_rows.append(hit.mean())
            rand_rows.append(rhit.mean())
            testaments.append(self.testament[i])
        obs, rand, testaments = np.array(obs_rows), np.array(rand_rows), np.array(testaments)
        out = {}
        for key, mask in (("all", np.ones(len(obs), bool)), ("Old", testaments == "Old"),
                          ("New", testaments == "New")):
            o, r = obs[mask], rand[mask]
            if len(o) == 0:
                continue
            # Bootstrap over windows for the range of the ratio.
            ratios = []
            for _ in range(self.args.boots):
                pick = rng.integers(0, len(o), len(o))
                rs = r[pick].mean()
                ratios.append(o[pick].mean() / rs if rs else np.nan)
            out[key] = {"windows": int(mask.sum()),
                        "companion_rate": round(float(o.mean()), 4),
                        "random_rate": round(float(r.mean()), 4),
                        "ratio": round(float(o.mean() / r.mean()), 2) if r.mean() else None,
                        "ratio_low": round(float(np.nanpercentile(ratios, 2.5)), 2),
                        "ratio_high": round(float(np.nanpercentile(ratios, 97.5)), 2)}
        return out

    def leans_across(self, web: LinkWeb, ids: VerseIds) -> list:
        """Each book's lean into the other testament, with obs/exp from the links."""
        books = self.table.books
        book_of = {vid: b for (b, c, v), vid in ids.ids.items() if b in self.book_testament}
        # Links from each book to each book of the other testament.
        counts = defaultdict(int)
        for a, targets in web.links.items():
            ba = book_of.get(a)
            if ba is None:
                continue
            for t in targets:
                bb = book_of.get(t)
                if bb is not None and self.book_testament[bb] != self.book_testament[ba]:
                    counts[(ba, bb)] += 1
        out_links, in_links = defaultdict(int), defaultdict(int)
        for (ba, bb), n in counts.items():
            out_links[ba] += n
            in_links[bb] += n
        # All crossing links from one testament (the expected counts share
        # them out by how many each book of the other testament receives).
        from_testament = defaultdict(int)
        for (ba, bb), n in counts.items():
            from_testament[self.book_testament[ba]] += n
        # Links each book receives from one testament: in_from[(book, testament)].
        in_from = defaultdict(int)
        for (ba, bb), n in counts.items():
            in_from[(bb, self.book_testament[ba])] += n

        rows = []
        for bi, name in enumerate(books):
            mine = self.table.book_index == bi
            cross_idx = self.idx[mine][self.crossing[mine]]
            if len(cross_idx) == 0:
                continue
            t = self.book_testament[name]
            others = [o for o in books if self.book_testament[o] != t]
            near = Counter(self.table.book_index[cross_idx])
            lean = books[near.most_common(1)[0][0]]
            total_in = sum(in_from[(o, t)] for o in others)
            expect = {o: out_links[name] * in_from[(o, t)] / total_in if total_in else 0.0
                      for o in others}
            ratio = {o: counts[(name, o)] / expect[o] if expect[o] else 0.0 for o in others}
            measured = [o for o in others if expect[o] >= MIN_EXPECTED]
            order = sorted(measured, key=lambda o: -ratio[o])
            excess = max(measured, key=lambda o: counts[(name, o)] - expect[o]) if measured else None
            row = {"book": name, "testament": t, "leans_to": lean,
                   "crossing_share": round(float(self.crossing[mine].mean()), 3),
                   "observed": counts[(name, lean)], "expected": round(expect[lean], 1),
                   "obs_exp": None, "range": None, "rank": None, "of": len(order),
                   "by_ratio": order[0] if order else None,
                   "by_ratio_obs_exp": round(ratio[order[0]], 2) if order else None,
                   "by_ratio_links": counts[(name, order[0])] if order else None,
                   "by_size": excess,
                   "by_size_obs_exp": round(ratio[excess], 2) if excess else None,
                   "by_size_excess": round(counts[(name, excess)] - expect[excess]) if excess else None}
            if lean in order:
                low, high = ratio_range(counts[(name, lean)], expect[lean])
                row.update(obs_exp=round(ratio[lean], 2), range=[round(low, 2), round(high, 2)],
                           rank=order.index(lean) + 1, kind=kind_of(ratio[lean], low, high))
            else:
                row["kind"] = "too few"
            rows.append(row)
        return rows


class CrossReport:
    """The text report."""

    KINDS = (("confirmed", f"Confirmed by OpenBible (obs/exp {CONFIRMED:g} or more, above 1 across "
                           "its range)"),
             ("more", f"More than expected, but under {CONFIRMED:g}"),
             ("as expected", f"As expected (whole range within {1 / AS_EXPECTED:.2f} to {AS_EXPECTED:g})"),
             ("register", f"A lean of register, not of matter (below {MATTER_LINE:g} across its range)"),
             ("cannot tell", "Cannot tell (the range spans 1 and is wide)"),
             ("too few", f"Too few links to rank (under {MIN_EXPECTED:g} expected)"))

    def __init__(self, check: CrossCheck, web: LinkWeb, crossing: dict, linked_: dict, leans: list):
        self.c, self.web, self.crossing, self.linked, self.leans = check, web, crossing, linked_, leans

    def render(self) -> str:
        c = self.c
        out = ["CROSS-REFERENCE CHECK ACROSS THE TESTAMENTS",
               f"{len(c.table):,} windows of {c.table.window} verses from both testaments, "
               f"{c.args.k} companions each, found on {len(c.strips)} shared strips "
               f"(each window scored against its own testament).",
               f"Check: {self.web.name}, {self.web.pairs:,} verse links.", "",
               "CROSSING  (how often companions fall in the other testament)"]
        for t in ("Old", "New"):
            x = self.crossing[t]
            other = "New" if t == "Old" else "Old"
            out.append(f"  {t} Testament windows: {100 * x['share']:5.1f}% of companions in the {other}; "
                       f"random companions {100 * x['chance']:5.1f}%; ratio {x['ratio']}")
        out += ["", "LINKED  (crossing companions joined by a cross reference, against a random window "
                    "of the companion's book)"]
        for key, label in (("all", "all crossing companions"), ("Old", "from Old Testament windows"),
                           ("New", "from New Testament windows")):
            if key in self.linked:
                x = self.linked[key]
                out.append(f"  {label:<28} linked {100 * x['companion_rate']:5.1f}%   random "
                           f"{100 * x['random_rate']:5.1f}%   ratio {x['ratio']} "
                           f"(95% range {x['ratio_low']} to {x['ratio_high']})")
        for t, title in (("New", "NEW TESTAMENT BOOKS LEANING INTO THE OLD"),
                         ("Old", "OLD TESTAMENT BOOKS LEANING INTO THE NEW")):
            rows = [r for r in self.leans if r["testament"] == t]
            kinds = Counter(r["kind"] for r in rows)
            out += ["", f"{title}  ({len(rows)} books; " +
                    ", ".join(f"{kinds[k]} {k}" for k, _ in self.KINDS if kinds[k]) + ")"]
            for kind, label in self.KINDS:
                members = [r for r in rows if r["kind"] == kind]
                if not members:
                    continue
                out.append(f"  {label}")
                for r in members:
                    if r["obs_exp"] is not None:
                        ratio = f"{r['obs_exp']:5.2f} ({r['range'][0]:.2f} to {r['range'][1]:.2f})"
                        rank = f"rank {r['rank']:>2} of {r['of']}"
                    else:
                        ratio, rank = "  -" + " " * 17, "unranked    "
                    out.append(f"    {r['book']:<16} leans to {r['leans_to']:<16} {rank}  obs/exp {ratio}"
                               f"  {r['observed']} links, {r['expected']:g} expected;"
                               f" {100 * r['crossing_share']:.0f}% of its companions cross")
                    partners = []
                    if r["by_ratio"] and r["by_ratio"] != r["leans_to"]:
                        partners.append(f"by ratio {r['by_ratio']} {r['by_ratio_obs_exp']:.2f} "
                                        f"({r['by_ratio_links']} links)")
                    if r["by_size"] and r["by_size"] not in (r["leans_to"], r["by_ratio"]):
                        partners.append(f"by size {r['by_size']} {r['by_size_obs_exp']:.2f} "
                                        f"(+{r['by_size_excess']} links over expected)")
                    if partners:
                        out.append(f"{'':<22}OpenBible's partner: " + "; ".join(partners))
        out += ["", "HOW TO READ THIS",
                "  The companions are chosen by manner of writing: density, variety, rare words,",
                "  repetition, action, the feeling families, the names and numbers, each measured",
                "  against ordinary in the window's own testament. A Greek window finds a Hebrew",
                "  companion when it stands as far from ordinary Greek, in the same directions, as the",
                "  Hebrew window stands from ordinary Hebrew. No word is shared between them.",
                "  crossing: the share of companions in the other testament. Random: the share a",
                "        companion drawn at random from the rest of the Bible would have.",
                "  linked: as in links_old and links_new, for the companions that cross only.",
                "  leans to: the book of the other testament where most of a book's crossing",
                "        companions fall.",
                "  obs/exp: the cross references between the two books against the number expected",
                "        from how many links the book sends into the other testament and how many the",
                "        other book receives from this one. The range is the 95% range, counting links",
                "        as a Poisson count; links come in clusters, so read it as a guide.",
                "  partner by ratio / by size: the book of the other testament with the highest",
                "        obs/exp, and the one with the most links above expected (the kinship a",
                "        commentary would name). A lean of register beside a different partner is",
                "        likeness of manner only; the partner is the kinship of matter."]
        return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-reference check across the two testaments")
    parser.add_argument("--k", type=int, default=20, help="companions per window (default 20)")
    parser.add_argument("--min-votes", type=int, default=1, help="OpenBible links with at least this many votes")
    parser.add_argument("--draws", type=int, default=5, help="random partners per companion (default 5)")
    parser.add_argument("--boots", type=int, default=300)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--atlas", type=Path, default=ATLAS_DIR / "atlas.db")
    parser.add_argument("--cross", type=Path, default=ATLAS_DIR / "cross_references.db")
    parser.add_argument("--out", type=Path, default=EVAL_DIR / "results")
    args = parser.parse_args()
    if not args.cross.exists():
        sys.exit(f"cross_references.db not found at {args.cross}.")

    check = CrossCheck(args)
    check.fit()
    print(f"{len(check.table):,} windows from both testaments, {args.k} companions each, "
          f"{len(check.strips)} shared strips")
    ids = VerseIds(args.atlas)
    web = LinkWeb.openbible(args.cross, ids, args.min_votes)
    print(f"  {web.name}: {web.pairs:,} verse links")
    crossing = check.crossing_test()
    linked_ = check.linked_test(web)
    leans = check.leans_across(web, ids)
    text = CrossReport(check, web, crossing, linked_, leans).render()
    print("\n" + text)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "links_cross.txt").write_text(text + "\n", encoding="utf-8")
    (args.out / "links_cross.json").write_text(json.dumps(
        {"k": args.k, "strips": check.strips, "web": web.name, "crossing": crossing,
         "linked": linked_, "leans": leans}, indent=1), encoding="utf-8")
    print(f"\nWritten to {args.out / 'links_cross.txt'} and .json")


if __name__ == "__main__":
    main()
